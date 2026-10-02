"""The Gram spectrum of a line and its decay rate (coordinate_lines.md, Computation; lines.md; 0038; CL2, CL3).

A line's n values y_j sit at evenly spaced unit coordinates s_j = -1 + 2j/(n - 1). Its Gram coefficients are
c_k = (1/n) sum_j y_j G_k(s_j), with G_0 ... G_(n-1) the Gram polynomials, orthonormal under the average over the
n points; the tail T(k) = sqrt(sum_(j >= k) c_j^2); the decay rate is minus the least-squares slope of
log10 T(k) over k = 1 ... k*. The window K = floor((n - 1)/2), the floor (1e-10 of the line's range, through
``ema.numerics.tolerance``), and the fewest degrees for a rate (3) are coordinate lines' constants: the caller
passes T up to K, the floor, and the minimum (record 0068 item 4).
"""

import math
from functools import lru_cache

import numpy as np

from ema.numerics._vector import matvec, norm
from ema.numerics.tolerance import is_constant


def _lanczos(n: int) -> np.ndarray:
    """Build the Gram polynomials' values ``G[j, k] = G_k(s_j)`` ``(n, n)``, with (1/n) G^T G = I.

    The Lanczos process on diag(s) from the vector of ones, with full reorthogonalization (two passes), as
    coordinate_lines.md specifies; not the three-term recurrence, which loses orthonormality in doubles. Each
    new vector is divided by its norm, a positive number, so each G_k keeps a positive leading coefficient.
    The norm is ``_vector.norm``, not BLAS's, and the products go through ``_vector.matvec``: at k = 1 the
    projection is a one-row product, which numpy sends to ``ddot`` (record 0068 item 1).
    """
    s = -1 + 2 * np.arange(n) / (n - 1)
    Q = np.zeros((n, n))
    Q[:, 0] = 1 / math.sqrt(n)
    for k in range(1, n):
        w = s * Q[:, k - 1]
        done = Q[:, :k]
        for _ in range(2):
            w -= matvec(done, matvec(done.T, w))
        Q[:, k] = w / norm(w)
    return Q * math.sqrt(n)


@lru_cache(maxsize=16)
def _basis(n: int) -> np.ndarray:
    """Return the Gram basis for n points, built once per n, read-only."""
    G = _lanczos(n)
    G.flags.writeable = False
    return G


def gram_coefficients(y: np.ndarray) -> np.ndarray:
    """Return the Gram coefficients c_0 ... c_(n-1) of a line's n evenly spaced values (CL2).

    An orthogonal transform: y_j = sum_k c_k G_k(s_j), c_0 is the mean, and sum_(k >= 1) c_k^2 the variance
    (ddof 0). A constant line's coefficients are exactly (y_0, 0, ..., 0), so it has 0 degrees above any floor
    (CL6).

    Parameters
    ----------
    y
        The line's values ``(n,)``, in the order of its points, n >= 2.

    Returns
    -------
    numpy.ndarray
        ``(n,)``, c_k at index k.

    Raises
    ------
    ValueError
        For fewer than 2 values.

    Examples
    --------
    >>> c = gram_coefficients(np.array([1.0, 2.0, 3.0]))
    >>> [round(float(v), 12) for v in c[:2]]
    [2.0, 0.816496580928]
    """
    y = np.asarray(y, dtype=np.float64)
    if y.ndim != 1 or len(y) < 2:
        raise ValueError(f"a Gram spectrum needs a line of at least 2 values, not shape {y.shape}")
    if is_constant(y):  # exactly (y_0, 0, ..., 0); Lanczos would leave rounding, and the floor is 0 (0068 item 2)
        c = np.zeros(len(y))
        c[0] = y[0]
        return c
    return matvec(_basis(len(y)).T, y) / len(y)


def tail(c: np.ndarray) -> np.ndarray:
    """Return the tail T(k) = sqrt(sum_(j >= k) c_j^2), indexed by degree k = 0 ... n - 1.

    T(1) is the line's standard deviation (ddof 0); T(0), which includes c_0, is kept so that index k is degree
    k, and is not used by the rate. Each sum is numpy's pairwise sum.

    Examples
    --------
    >>> tail(np.array([5.0, 3.0, 0.0, 4.0])).tolist()
    [7.0710678118654755, 5.0, 4.0, 4.0]
    """
    c = np.asarray(c, dtype=np.float64)
    squares = c * c
    return np.array([math.sqrt(float(np.sum(squares[k:]))) for k in range(len(c))])


def degrees_above_floor(T: np.ndarray, floor: float) -> int:
    """Return k*: the degrees k = 1, 2, ... whose tail is above ``floor``, counted until the first that isn't.

    Parameters
    ----------
    T
        The tail, indexed by degree, up to the window: ``tail(c)[: K + 1]``.
    floor
        The absolute floor: ``tolerance(y, LINE_RATE_FLOOR)``, a fraction of the line's range (P6).

    Examples
    --------
    >>> degrees_above_floor(np.array([9.0, 1.0, 0.5, 1e-11]), 1e-10)
    2
    """
    k_star = 0
    for k in range(1, len(T)):
        if not T[k] > floor:
            break
        k_star = k
    return k_star


def decay_rate(T: np.ndarray, k_star: int, min_degrees: int) -> tuple[float, float] | None:
    """Return the decay rate and the intercept of the fitted line, or None when k* < ``min_degrees`` (CL3).

    The rate is minus the least-squares slope of log10 T(k) against k over k = 1 ... k*, in decades per degree;
    the intercept is the fitted line's log10 T at k = 0. The slope is computed in closed form, with numpy's
    pairwise sums.

    Examples
    --------
    >>> rate, intercept = decay_rate(np.array([1.0, 0.1, 0.001, 0.00001]), 3, 3)
    >>> round(rate, 12), round(intercept, 12)
    (2.0, 1.0)
    """
    if k_star < min_degrees:
        return None
    k = np.arange(1, k_star + 1, dtype=np.float64)
    logT = np.log10(np.asarray(T[1 : k_star + 1], dtype=np.float64))
    dk = k - np.mean(k)
    slope = float(np.sum(dk * (logT - np.mean(logT)))) / float(np.sum(dk * dk))
    return -slope, float(np.mean(logT)) - slope * float(np.mean(k))
