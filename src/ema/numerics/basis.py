"""The polynomial model's basis: orthonormal Legendre terms of total degree at most p (polynomial_model.md; C29).

The basis is one of the four seams (architecture.md §4): a registry (``register``, ``get``, ``names``,
``unregister``; 0065), its v2.0 implementation ``total_degree``, and a fake registered in the tests. Any other
name is refused, "basis X comes in a later version" (PM1).

Ported from EMA v1 at v1-final: src/ema/core/legendre.py (``total_degree_indices``, ``n_terms``,
``legendre_basis``), re-reviewed against polynomial_model.md: the terms and their order are v1's; the gradient,
the hold-out split, and the term cap are not in v2.0.
"""

import itertools
import math
from typing import Protocol

import numpy as np
from numpy.polynomial import legendre

from ema.types.errors import RequestError


class Basis(Protocol):
    """A set of polynomial terms orthonormal on [-1, 1]^d under the uniform measure (C29).

    Attributes
    ----------
    name : str
        Part of the polynomial model's request identity (``basis``).
    """

    name: str

    def terms(self, d: int, degree: int) -> np.ndarray:
        """Return the multi-indices ``(P, d)``, the constant first, in the basis's stated order."""
        ...

    def n_terms(self, d: int, degree: int) -> int:
        """Return P without building the terms."""
        ...

    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray:
        """Return the terms at points ``Z`` ``(n, d)`` in [-1, 1]^d, as ``(n, P)``."""
        ...


_REGISTRY: dict[str, Basis] = {}


def register(basis: Basis) -> None:
    """Add a basis to the registry.

    Raises
    ------
    ValueError
        When its name is taken.
    """
    if basis.name in _REGISTRY:
        raise ValueError(f"basis {basis.name} is already registered")
    _REGISTRY[basis.name] = basis


def unregister(name: str) -> None:
    """Remove a basis from the registry (0065 item 1): for the tests, and a later plugin mechanism.

    Raises
    ------
    ValueError
        When no basis has that name.
    """
    if name not in _REGISTRY:
        raise ValueError(f"no basis {name} is registered")
    del _REGISTRY[name]


def get(name: str) -> Basis:
    """Return the basis named ``name``.

    Raises
    ------
    RequestError
        "basis X comes in a later version", for a name with no implementation (PM1).
    """
    if name not in _REGISTRY:
        raise RequestError(f"basis {name} comes in a later version")
    return _REGISTRY[name]


def names() -> tuple[str, ...]:
    """Return the registered bases' names, sorted."""
    return tuple(sorted(_REGISTRY))


class TotalDegree:
    """The ``total_degree`` basis: psi_alpha(u) = prod_i psi_(alpha_i)(u_i), for every alpha of total degree <= p.

    PM2.

    psi_k is the orthonormal Legendre polynomial of degree k on [-1, 1] under the uniform measure,
    sqrt(2k + 1) P_k (reference_models.md: psi_1(u) = sqrt(3) u, psi_2(u) = sqrt(5)(3u^2 - 1)/2). The terms are
    ordered by total degree, then by the exponents in the model spec's order, largest first (v1's order).

    Examples
    --------
    >>> TotalDegree().terms(2, 2).tolist()
    [[0, 0], [1, 0], [0, 1], [2, 0], [1, 1], [0, 2]]
    """

    name: str = "total_degree"

    def terms(self, d: int, degree: int) -> np.ndarray:
        """Return the C(d + p, p) multi-indices of total degree at most p, ``(P, d)`` int64, in the stated order.

        Each multiset of t model parameters, chosen with repetition, is one term of degree t, so only the P terms
        are built (filtering all (p + 1)^d candidates takes hours at d = 20).

        Raises
        ------
        ValueError
            For d < 1 or a degree below 0.
        """
        if d < 1 or degree < 0:
            raise ValueError(f"a basis needs d >= 1 and a degree >= 0, not d = {d}, degree {degree}")
        rows = []
        for t in range(degree + 1):
            for chosen in itertools.combinations_with_replacement(range(d), t):
                alpha = [0] * d
                for j in chosen:
                    alpha[j] += 1
                rows.append(tuple(alpha))
        rows.sort(key=lambda a: (sum(a), tuple(-k for k in a)))
        return np.array(rows, dtype=np.int64).reshape(len(rows), d)

    def n_terms(self, d: int, degree: int) -> int:
        """Return P = C(d + p, p)."""
        return math.comb(d + degree, degree)

    def evaluate(self, Z: np.ndarray, terms: np.ndarray) -> np.ndarray:
        """Return the matrix ``(n, P)`` of the terms at the points ``Z`` ``(n, d)`` (unit coordinates).

        Raises
        ------
        ValueError
            When the terms' width isn't Z's.
        """
        Z = np.asarray(Z, dtype=np.float64)
        terms = np.asarray(terms, dtype=np.int64)
        if Z.ndim != 2 or terms.ndim != 2 or terms.shape[1] != Z.shape[1]:
            raise ValueError(f"terms of shape {terms.shape} don't fit points of shape {Z.shape}")
        top = int(terms.max()) if terms.size else 0
        # psi[k][:, j] = sqrt(2k + 1) P_k(Z[:, j]): unit variance under the uniform measure.
        psi = [math.sqrt(2 * k + 1) * legendre.legval(Z, [0] * k + [1]) for k in range(top + 1)]
        Phi = np.ones((Z.shape[0], terms.shape[0]))
        for t, alpha in enumerate(terms.tolist()):
            for j, k in enumerate(alpha):
                if k:
                    Phi[:, t] *= psi[k][:, j]
        return Phi


register(TotalDegree())
