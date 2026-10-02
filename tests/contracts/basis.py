"""The basis contract: C29 (contracts.md), over ``total_degree`` and a fake tensor-product basis.

The fake is registered by the fixture through the basis registry's own ``register`` and removed with
``unregister`` (0065 item 1). The broken toy (unnormalized Legendre terms) fails ``check_basis``;
``test_every_check_fails_on_its_broken_toy`` is the meta-test. C29's last clause, the basis name in a request's
identity, is checked with the polynomial model's request (step 13; record 0068).
"""

from __future__ import annotations

import inspect
import itertools
import math
import sys
from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest

from ema.numerics import basis
from tests.support.numerics import gauss_legendre_grid

#: C29's tolerance on the Gauss-Legendre Gram matrix.
ORTHONORMAL_TOL = 1e-13
CASES = ((1, 1), (1, 10), (2, 4), (3, 3), (4, 2))


def check_basis(b: Any) -> None:
    """C29: P terms in the stated order, the constant first, orthonormal under the uniform measure on [-1, 1]^d
    (Gauss-Legendre Gram matrix within 1e-13 of I); a name."""
    assert isinstance(b.name, str) and b.name
    for d, p in CASES:
        terms = b.terms(d, p)
        assert terms.ndim == 2 and terms.shape[1] == d
        assert terms.shape[0] == b.n_terms(d, p), "n_terms differs from the terms built"
        assert not terms[0].any(), "the constant term isn't first"
        assert len({tuple(t) for t in terms.tolist()}) == len(terms), "a repeated term"
        assert np.array_equal(terms, b.terms(d, p)), "the order isn't stable"
        nodes, weights = gauss_legendre_grid(d, p + 2)
        Phi = b.evaluate(nodes, terms)
        assert Phi.shape == (len(nodes), len(terms))
        gram = Phi.T @ (weights[:, None] * Phi)
        assert np.max(np.abs(gram - np.eye(len(terms)))) <= ORTHONORMAL_TOL, f"not orthonormal at d={d}, p={p}"


# --------------------------------------------------------------------------------------------------------------
# The fake, and the broken toy


class FakeTensor:
    """Tensor-product Legendre terms, each one-variable degree at most p: another index set, same functions."""

    name = "fake_tensor"

    def terms(self, d: int, degree: int) -> np.ndarray:
        rows = sorted(itertools.product(range(degree + 1), repeat=d), key=lambda a: (sum(a), tuple(-k for k in a)))
        return np.array(rows, dtype=np.int64).reshape(-1, d)

    def n_terms(self, d: int, degree: int) -> int:
        return (degree + 1) ** d

    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray:
        return basis.TotalDegree().evaluate(Z, terms)


class BrokenUnnormalized(FakeTensor):
    """Unnormalized Legendre terms: P_k rather than sqrt(2k + 1) P_k."""

    name = "broken_unnormalized"

    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray:
        scale = np.prod(np.sqrt(2 * terms + 1.0), axis=1)
        return super().evaluate(Z, terms) / scale


BROKEN: dict[str, list[Any]] = {"check_basis": [BrokenUnnormalized()]}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=["total_degree", "fake_tensor"])
def b(request: pytest.FixtureRequest) -> Iterator[Any]:
    if request.param == "fake_tensor":
        basis.register(FakeTensor())
        try:
            yield basis.get("fake_tensor")
        finally:
            basis.unregister("fake_tensor")
    else:
        yield basis.get(request.param)


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)


def test_the_fake_is_unregistered_afterwards() -> None:
    assert basis.names() == ("total_degree",)


def test_the_fake_counts() -> None:
    assert FakeTensor().n_terms(3, 2) == math.prod((3, 3, 3))
