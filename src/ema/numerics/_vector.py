"""Inner products and norms of 1-D arrays, without vector-vector BLAS (record 0068 item 1; P4).

On Accelerate, BLAS's ``ddot`` (behind ``x @ y`` of two 1-D arrays, ``np.dot``, ``np.vecdot``, and
``np.linalg.norm`` of a vector) depends on its operands' addresses mod 64, so the same numbers can give results
that differ in the last bits (docs/notes/blas_determinism_2026-10-01.md). numpy's pairwise ``np.sum`` of the
elementwise product doesn't. Every inner product and norm of 1-D arrays in ``ema.numerics`` goes through these
two; Ruff's banned-api rule (TID251) refuses the named BLAS calls in ``src/ema``.
"""

import math

import numpy as np


def dot(x: np.ndarray, y: np.ndarray) -> float:
    """Return the inner product of two 1-D arrays, ``sum(x * y)`` by numpy's pairwise sum.

    Examples
    --------
    >>> dot(np.array([1.0, 2.0]), np.array([3.0, 4.0]))
    11.0
    """
    return float(np.sum(x * y))


def norm(x: np.ndarray) -> float:
    """Return the Euclidean norm of a 1-D array, ``sqrt(dot(x, x))``.

    Examples
    --------
    >>> norm(np.array([3.0, 4.0]))
    5.0
    """
    return math.sqrt(dot(x, x))


def centered(y: np.ndarray) -> np.ndarray:
    """Return y - mean(y); exactly zeros when every value is the same double (0035), where the mean may round.

    So 0/0 on a constant y is detected exactly (uncertainty.md, the bootstrap's step 3), not left to rounding.

    Examples
    --------
    >>> centered(np.full(3, 0.1)).tolist()
    [0.0, 0.0, 0.0]
    """
    if len(y) and (y == y[0]).all():
        return np.zeros(len(y))
    return y - np.mean(y)
