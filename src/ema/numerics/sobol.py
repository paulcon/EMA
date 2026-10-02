"""Sobol indices and the root energy per degree of a fitted polynomial in an orthonormal basis.

Sudret 2008; polynomial_model.md, Computation; PM4; 0049.

Under the uniform distribution in unit coordinates the terms are orthonormal, so each coefficient squared is the
variance its term carries, and V = sum_(alpha != 0) c_alpha^2 is the polynomial's variance. These are the indices of
the fitted polynomial, not of the model.
"""

import math

import numpy as np


def _variances(coef: np.ndarray, terms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coef = np.asarray(coef, dtype=np.float64)
    terms = np.asarray(terms, dtype=np.int64)
    if terms.ndim != 2 or coef.shape != (terms.shape[0],):
        raise ValueError(f"coefficients of shape {coef.shape} don't fit terms of shape {terms.shape}")
    return coef * coef, terms


def sobol_indices(coef: np.ndarray, terms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the first-order and total Sobol indices of the fitted polynomial, each ``(d,)``, in the terms' order.

    First-order S_i: the share of V in the terms in u_i alone; total T_i: the share in the terms that involve u_i.
    When V = 0 (the fitted polynomial is constant) both are NaN: there are no indices (0049). A fit to a constant y
    has coefficients at rounding level, not exact zeros, so the caller treats a constant y as undefined itself
    (uncertainty.md, the bootstrap's step 3).

    Parameters
    ----------
    coef
        ``(P,)``, the coefficients.
    terms
        ``(P, d)``, their multi-indices.

    Examples
    --------
    >>> first, total = sobol_indices(np.array([1.0, 1.0, 1.0, 1.0]), np.array([[0, 0], [1, 0], [0, 1], [1, 1]]))
    >>> first.round(12).tolist(), total.round(12).tolist()
    ([0.333333333333, 0.333333333333], [0.666666666667, 0.666666666667])
    """
    squares, terms = _variances(coef, terms)
    involved = terms > 0
    constant = ~involved.any(axis=1)
    V = float(np.sum(squares[~constant]))
    d = terms.shape[1]
    if V == 0:
        return np.full(d, math.nan), np.full(d, math.nan)
    alone = involved & (involved.sum(axis=1) == 1)[:, None]
    first = np.array([float(np.sum(squares[alone[:, i]])) / V for i in range(d)])
    total = np.array([float(np.sum(squares[involved[:, i]])) / V for i in range(d)])
    return first, total


def degree_energy(coef: np.ndarray, terms: np.ndarray) -> np.ndarray:
    """Return sqrt(E_k) for k = 1 ... p: E_k is the sum of c_alpha^2 over the terms of total degree k.

    p is the terms' largest total degree.

    sqrt(E_k) is the standard deviation of the polynomial's degree-k part, in y's units; E_1 + ... + E_p = V.

    Examples
    --------
    >>> degree_energy(np.array([5.0, 3.0, 4.0, 2.0]), np.array([[0, 0], [1, 0], [0, 1], [1, 1]])).tolist()
    [5.0, 2.0]
    """
    squares, terms = _variances(coef, terms)
    degree = terms.sum(axis=1)
    top = int(degree.max()) if degree.size else 0
    return np.array([math.sqrt(float(np.sum(squares[degree == k]))) for k in range(1, top + 1)])
