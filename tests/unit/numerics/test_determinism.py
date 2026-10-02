"""Identical bytes at 8 memory offsets: the Lanczos basis, the fits, and the bootstrap (P4; record 0068 item 1).

On this Mac's Accelerate, a vector-vector BLAS product (``x @ y`` of two 1-D arrays, ``np.linalg.norm``,
``np.dot``) depends on its operands' addresses mod 64 (docs/notes/blas_determinism_2026-10-01.md); Ruff's
banned-api catches the named calls, and this test catches the rest, here and on OpenBLAS.

Probed 2026-10-02 by putting ``np.dot`` back in ``_vector.dot``: the helpers' test and the Lanczos test fail (the
basis varies at n = 9 or 17). The fits' and the bootstrap's tests still pass then: the vectors they take inner
products of are numpy's own temporaries, always 16-byte aligned, where the measured ddot repeats; those two tests
guard the placement of their inputs. Arrays stay under 1,009 bytes and the heap is moved by 520-632 bytes between
runs, since macOS's malloc aligns larger blocks to 512 bytes.
"""

import math

import numpy as np

from ema.numerics import gram
from ema.numerics._vector import dot, norm
from ema.numerics.basis import TotalDegree
from ema.numerics.fitting import least_squares, press, r2, relative_residual
from ema.numerics.intervals import Bootstrap, Estimator
from ema.numerics.stats import binned_index, rank_correlation
from ema.numerics.tolerance import tolerance
from ema.types.streams import spawned
from tests.support.numerics import OFFSETS, at_offset, coordinate_line, r7_unit


def same_bytes(results: list[bytes]) -> bool:
    return all(r == results[0] for r in results)


def test_helpers_are_address_invariant() -> None:
    x = np.random.default_rng(0).standard_normal(129)
    keep: list[bytearray] = []
    assert same_bytes([np.float64(dot(at_offset(x, o, keep), at_offset(x[::-1], o, keep))).tobytes() for o in OFFSETS])
    assert same_bytes([np.float64(norm(at_offset(x, o, keep))).tobytes() for o in OFFSETS])
    assert norm(x) == math.sqrt(dot(x, x))


def test_lanczos_basis_and_spectrum() -> None:
    keep: list[bytearray] = []
    for n in (9, 17, 33, 65, 129):
        bases = []
        for o in OFFSETS:
            keep.append(bytearray(520 + 16 * o))  # move the heap between builds
            bases.append(gram._lanczos(n).tobytes())
        assert same_bytes(bases), f"the Lanczos basis varies at n = {n}"
        y = coordinate_line(r7_unit, 4, 2, n)
        spectra = [gram.tail(gram.gram_coefficients(at_offset(y, o, keep))).tobytes() for o in OFFSETS]
        assert same_bytes(spectra)


def test_fits() -> None:
    keep: list[bytearray] = []
    Z = 2 * np.random.default_rng(1).random((80, 3)) - 1
    b = TotalDegree()
    A = b.evaluate(Z, b.terms(3, 2))
    y = np.sin(Z[:, 0]) + Z[:, 1] * Z[:, 2]
    out = []
    for o in OFFSETS:
        keep.append(bytearray(520 + 16 * o))  # move the heap, so the fits' own arrays move too
        Ao, yo = at_offset(A, o, keep), at_offset(y, o, keep)
        fit = least_squares(Ao, yo)
        numbers = [relative_residual(yo, fit), r2(yo, fit), press(Ao, yo, fit), tolerance(yo, 1e-10)]
        numbers += [rank_correlation(Z[:, 0], yo), binned_index(Z[:, 0], yo, 8)]
        out.append(fit.coefficients.tobytes() + fit.leverages.tobytes() + np.array(numbers).tobytes())
    assert same_bytes(out)


def test_bootstrap() -> None:
    keep: list[bytearray] = []
    Z = 2 * np.random.default_rng(2).random((80, 3)) - 1
    y = np.exp(Z[:, 0]) + Z[:, 1]
    b = TotalDegree()
    A = b.evaluate(Z, b.terms(3, 2))
    out = []
    for o in OFFSETS:
        keep.append(bytearray(520 + 16 * o))
        Ao, yo = at_offset(A, o, keep), at_offset(y, o, keep)

        def refit(idx: np.ndarray, Ao: np.ndarray = Ao, yo: np.ndarray = yo) -> np.ndarray:
            fit = least_squares(Ao[idx], yo[idx])
            return np.array([relative_residual(yo[idx], fit), press(Ao[idx], yo[idx], fit)])

        usable = at_offset(np.arange(80), o, keep)
        result = Bootstrap().intervals(usable, None, [Estimator("fit", ("rel", "loo"), refit, False)], spawned(0, 7))
        out.append(repr(result).encode())
    assert same_bytes(out)
