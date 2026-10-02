"""The orthonormal Legendre basis of total degree (polynomial_model.md, the fit; PM2; C29's own tests)."""

import math

import numpy as np
import pytest

from ema.numerics import basis
from ema.numerics.basis import TotalDegree
from ema.types.errors import RequestError
from tests.support.numerics import gauss_legendre_grid, psi1, psi2


def test_one_variable_terms_are_the_reference_models_psi() -> None:
    """reference_models.md: psi_1(u) = sqrt(3) u, psi_2(u) = sqrt(5)(3u^2 - 1)/2."""
    u = np.linspace(-1, 1, 11)
    Phi = TotalDegree().evaluate(u[:, None], np.array([[0], [1], [2]]))
    assert np.array_equal(Phi[:, 0], np.ones(11))
    assert np.allclose(Phi[:, 1], psi1(u), rtol=0, atol=1e-15)
    assert np.allclose(Phi[:, 2], psi2(u), rtol=0, atol=1e-15)


@pytest.mark.parametrize("d", range(1, 9))
@pytest.mark.parametrize("p", range(1, 5))
def test_p_terms(d: int, p: int) -> None:
    """PM2: P = C(d + p, p) for d = 1 ... 8, p = 1 ... 4; each term of total degree at most p, once."""
    b = TotalDegree()
    terms = b.terms(d, p)
    assert terms.shape == (math.comb(d + p, p), d) == (b.n_terms(d, p), d)
    assert terms.dtype == np.int64 and (terms >= 0).all() and (terms.sum(axis=1) <= p).all()
    assert len({tuple(t) for t in terms.tolist()}) == len(terms)


def test_the_stated_order() -> None:
    """polynomial_model.md: by total degree, then the exponents in the model spec's order, largest first."""
    assert TotalDegree().terms(2, 2).tolist() == [[0, 0], [1, 0], [0, 1], [2, 0], [1, 1], [0, 2]]
    assert TotalDegree().terms(3, 1).tolist() == [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    degrees = TotalDegree().terms(4, 3).sum(axis=1)
    assert (np.diff(degrees) >= 0).all()


def test_a_product_term() -> None:
    Z = np.array([[0.3, -0.7], [1.0, 1.0]])
    Phi = TotalDegree().evaluate(Z, np.array([[1, 1], [2, 1]]))
    assert np.allclose(Phi[:, 0], psi1(Z[:, 0]) * psi1(Z[:, 1]), rtol=1e-15)
    assert np.allclose(Phi[:, 1], psi2(Z[:, 0]) * psi1(Z[:, 1]), rtol=1e-15)


@pytest.mark.parametrize(("d", "p"), [(1, 10), (2, 6), (3, 4)])
def test_orthonormal_by_quadrature(d: int, p: int) -> None:
    """C29: the Gauss-Legendre Gram matrix within 1e-13 of I."""
    b = TotalDegree()
    nodes, weights = gauss_legendre_grid(d, p + 1)
    Phi = b.evaluate(nodes, b.terms(d, p))
    assert np.abs(Phi.T @ (weights[:, None] * Phi) - np.eye(b.n_terms(d, p))).max() <= 1e-13


def test_d20_p3_counts_without_building() -> None:
    assert TotalDegree().n_terms(20, 3) == 1771
    assert TotalDegree().terms(20, 3).shape == (1771, 20)


def test_refusals() -> None:
    with pytest.raises(ValueError):
        TotalDegree().terms(0, 2)
    with pytest.raises(ValueError):
        TotalDegree().terms(2, -1)
    with pytest.raises(ValueError):
        TotalDegree().evaluate(np.zeros((3, 2)), np.zeros((1, 3), dtype=np.int64))


def test_registry() -> None:
    """architecture.md §4: register, get, names, unregister (0065); a name with no implementation is later."""
    assert basis.names() == ("total_degree",)
    assert isinstance(basis.get("total_degree"), TotalDegree)
    with pytest.raises(RequestError, match="basis hyperbolic_cross comes in a later version"):
        basis.get("hyperbolic_cross")
    with pytest.raises(ValueError):
        basis.register(TotalDegree())
    with pytest.raises(ValueError):
        basis.unregister("hyperbolic_cross")
