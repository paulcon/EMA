"""No vector-vector BLAS: identical bytes at 8 memory offsets, and no ``.dot(`` or stray ``@`` (P4; record 0068
item 1 and its review round 1).

On this Mac's Accelerate, a vector-vector BLAS product (``x @ y`` of two 1-D arrays, a one-row matrix times a
vector, ``np.dot``, ``x.dot(y)``, ``np.vecdot``, ``np.tensordot``, ``np.linalg.norm``) depends on its operands'
addresses mod 64, among 16-byte-aligned ones too (docs/notes/blas_determinism_2026-10-01.md). Ruff's banned-api
catches the named calls; ``test_no_dot_method_and_one_matmul`` catches ``.dot(`` and ``@``, which Ruff can't; the
offset tests catch the rest, here and on OpenBLAS.

The fits' and the bootstrap's own temporaries come from numpy's small-block cache, so moving the inputs and
Python's heap doesn't move them: ``scramble_heap`` empties the cache and moves malloc before each call. The
negative controls put BLAS back (``np.dot``, ``np.linalg.norm``) in ``fitting`` and ``stats`` and show the same
tests then fail: the tests have the power to see it. Arrays stay under 1,009 bytes, since macOS's malloc aligns
larger blocks to 512 bytes.
"""

import ast
import math
from pathlib import Path

import numpy as np
import pytest

import ema
from ema.numerics import fitting, gram, stats
from ema.numerics._vector import dot, matvec, norm
from ema.numerics.basis import TotalDegree
from ema.numerics.fitting import least_squares, press, r2, relative_residual
from ema.numerics.intervals import Bootstrap, Estimator
from ema.numerics.stats import binned_index, rank_correlation
from ema.numerics.tolerance import tolerance
from ema.types.streams import spawned
from tests.support.numerics import OFFSETS, at_offset, coordinate_line, r7_unit, scramble_heap

SRC = Path(ema.__file__).parent

#: Where ``@`` may appear in ``src/ema``, and how often: only ``_vector.matvec``, which sends a one-row product to
#: ``dot``. A new matrix product goes through ``matvec``, or is reviewed and listed here (record 0068).
MATMUL_ALLOWED = {"numerics/_vector.py": 1}

#: The fits' fixtures (n, seed): the BLAS negative control varies on several of them (measured 2026-10-02).
FIT_FIXTURES = [(n, seed) for n in (40, 50, 60, 70, 90) for seed in (1, 2, 3)]


def same_bytes(results: list[bytes]) -> bool:
    return all(r == results[0] for r in results)


def blas_dot(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.dot(x, y))


def blas_norm(x: np.ndarray) -> float:
    return float(np.linalg.norm(x))


@pytest.fixture
def blas_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """The negative control: vector-vector BLAS put back in the fits and scatter's estimates."""
    monkeypatch.setattr(fitting, "dot", blas_dot)
    monkeypatch.setattr(fitting, "norm", blas_norm)
    monkeypatch.setattr(stats, "dot", blas_dot)


# --------------------------------------------------------------------------------------------------------------
# What Ruff can't see: `.dot(` and `@`


def products(source: str) -> list[tuple[int, str]]:
    """Every ``.dot(`` call (but ``_vector.dot``) and every ``@`` or ``@=`` in a module's source, as (line, kind)."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "dot":
            receiver = node.func.value
            if not (isinstance(receiver, ast.Name) and receiver.id == "_vector"):
                found.append((node.lineno, ".dot("))
        elif isinstance(node, ast.BinOp | ast.AugAssign) and isinstance(node.op, ast.MatMult):
            found.append((node.lineno, "@"))
    return sorted(found)


def test_products_finds_dot_methods_and_matmul() -> None:
    """The negative control for the next test: each form is found, ``_vector.dot`` and decorators aren't."""
    source = "x.dot(y)\nz = a @ b\nw @= v\n_vector.dot(a, b)\nnp.dot(a, b)\n@decorator\ndef f(): pass\n"
    assert products(source) == [(1, ".dot("), (2, "@"), (3, "@"), (5, ".dot(")]


def test_no_dot_method_and_one_matmul() -> None:
    """Record 0068 item 1: no ``.dot(`` in ``src/ema``, and ``@`` only where ``MATMUL_ALLOWED`` says."""
    dots, matmuls = [], {}
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        found = products(path.read_text(encoding="utf-8"))
        dots += [f"{rel}:{line}" for line, kind in found if kind == ".dot("]
        if count := sum(kind == "@" for _, kind in found):
            matmuls[rel] = count
    assert not dots, f".dot( is vector-vector BLAS on 1-D arrays: use ema.numerics._vector (0068): {dots}"
    assert matmuls == MATMUL_ALLOWED, f"@ outside _vector.matvec: route it through matvec (0068): {matmuls}"


# --------------------------------------------------------------------------------------------------------------
# Identical bytes at 8 offsets


def test_helpers_are_address_invariant() -> None:
    x = np.random.default_rng(0).standard_normal(129)
    M = np.random.default_rng(1).standard_normal((3, 129))
    keep: list[object] = []
    assert same_bytes([np.float64(dot(at_offset(x, o, keep), at_offset(x[::-1], o, keep))).tobytes() for o in OFFSETS])
    assert same_bytes([np.float64(norm(at_offset(x, o, keep))).tobytes() for o in OFFSETS])
    for rows in (M[:1], M):  # one row: dot, not ddot; three: gemv
        assert same_bytes([matvec(at_offset(rows, o, keep), at_offset(x, o, keep)).tobytes() for o in OFFSETS])
    assert norm(x) == math.sqrt(dot(x, x))
    assert matvec(M[:1], x).tolist() == [dot(M[0], x)]


def lanczos_bases(n: int) -> list[bytes]:
    keep: list[object] = []
    bases = []
    for o in OFFSETS:
        scramble_heap(o, keep)  # move the heap and numpy's cache between builds
        bases.append(gram._lanczos(n).tobytes())
    return bases


def test_lanczos_basis_and_spectrum() -> None:
    keep: list[object] = []
    for n in (9, 17, 33, 65, 129):
        assert same_bytes(lanczos_bases(n)), f"the Lanczos basis varies at n = {n}"
        y = coordinate_line(r7_unit, 4, 2, n)
        spectra = [gram.tail(gram.gram_coefficients(at_offset(y, o, keep))).tobytes() for o in OFFSETS]
        assert same_bytes(spectra)


def test_lanczos_negative_control(monkeypatch: pytest.MonkeyPatch) -> None:
    """With BLAS's norm put back in the Lanczos process, the basis varies at some n."""
    monkeypatch.setattr(gram, "norm", blas_norm)
    assert any(not same_bytes(lanczos_bases(n)) for n in (9, 17, 33, 65, 129))


def fit_numbers(n: int, seed: int) -> dict[str, list[bytes]]:
    """Each fit number's bytes at the 8 offsets, the inputs moved and the heap scrambled before each fit.

    rho is computed on ranks, half-integers whose products and sums are exact: it can't vary, and is checked
    with the rest.
    """
    keep: list[object] = []
    Z = 2 * np.random.default_rng(seed).random((n, 3)) - 1
    b = TotalDegree()
    A = b.evaluate(Z, b.terms(3, 2))
    y = np.sin(3 * Z[:, 0]) + Z[:, 1] * Z[:, 2] + 0.1 * np.cos(5 * Z[:, 2])
    out: dict[str, list[bytes]] = {}
    for o in OFFSETS:
        scramble_heap(o, keep)
        Ao, yo = at_offset(A, o, keep), at_offset(y, o, keep)
        fit = least_squares(Ao, yo)
        numbers = {
            "coefficients": fit.coefficients,
            "leverages": fit.leverages,
            "relative_residual": relative_residual(yo, fit),
            "r2": r2(yo, fit),
            "press": press(Ao, yo, fit),
            "tolerance": tolerance(yo, 1e-10),
            "rho": rank_correlation(Z[:, 0], yo),
            "S": binned_index(Z[:, 0], yo, 8),
        }
        for name, value in numbers.items():
            out.setdefault(name, []).append(np.asarray(value, dtype=np.float64).tobytes())
    return out


def test_fits() -> None:
    for n, seed in FIT_FIXTURES:
        for name, results in fit_numbers(n, seed).items():
            assert same_bytes(results), f"{name} varies with memory placement at n = {n}, seed {seed}"


def test_fits_negative_control(blas_back: None) -> None:
    """With BLAS put back, the same fixtures give other bytes at some offsets: each reduction is seen."""
    varies: set[str] = set()
    for n, seed in FIT_FIXTURES:
        varies |= {name for name, results in fit_numbers(n, seed).items() if not same_bytes(results)}
    assert {"relative_residual", "r2", "press", "S"} <= varies, f"only {sorted(varies)} varied"


def bootstrap_results(n: int, seed: int) -> list[bytes]:
    """The bootstrap's intervals at the 8 offsets, refitting on each resample, the heap scrambled before each."""
    keep: list[object] = []
    Z = 2 * np.random.default_rng(seed).random((n, 3)) - 1
    y = np.exp(Z[:, 0]) + Z[:, 1] + 0.1 * np.sin(4 * Z[:, 2])
    b = TotalDegree()
    A = b.evaluate(Z, b.terms(3, 2))
    out = []
    for o in OFFSETS:
        scramble_heap(o, keep)
        Ao, yo = at_offset(A, o, keep), at_offset(y, o, keep)

        def refit(idx: np.ndarray, Ao: np.ndarray = Ao, yo: np.ndarray = yo) -> np.ndarray:
            fit = least_squares(Ao[idx], yo[idx])
            return np.array([relative_residual(yo[idx], fit), r2(yo[idx], fit), press(Ao[idx], yo[idx], fit)])

        usable = at_offset(np.arange(n), o, keep)
        estimators = [Estimator("fit", ("rel", "r2", "loo"), refit, False)]
        out.append(repr(Bootstrap().intervals(usable, None, estimators, spawned(0, 7))).encode())
    return out


def test_bootstrap() -> None:
    assert same_bytes(bootstrap_results(40, 2))


def test_bootstrap_negative_control(blas_back: None) -> None:
    """With BLAS put back in the refits, the bootstrap's intervals vary with memory placement."""
    assert not same_bytes(bootstrap_results(40, 2))
