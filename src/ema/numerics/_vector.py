"""Inner products, norms, and matrix-vector products, without vector-vector BLAS (record 0068 item 1; P4).

On Accelerate, BLAS's ``ddot`` (behind ``x @ y`` of two 1-D arrays, a one-row matrix times a vector,
``np.dot``, ``x.dot(y)``, ``np.vecdot``, ``np.linalg.vecdot``, ``np.tensordot``, and ``np.linalg.norm`` of a
vector) depends on its operands' addresses mod 64, even among 16-byte-aligned ones, so the same numbers can give
results that differ in the last bits (docs/notes/blas_determinism_2026-10-01.md). numpy's pairwise ``np.sum`` of
the elementwise product doesn't. Every inner product and norm of 1-D arrays in ``ema.numerics`` goes through
``dot`` and ``norm``, and every matrix-vector product through ``matvec``, the one ``@`` in ``ema`` (record 0068,
Review round 1). Ruff's banned-api rule (TID251) refuses the named BLAS calls in ``src/ema``, and
``tests/unit/numerics/test_determinism.py`` refuses ``.dot(`` and any other ``@``.
"""

import math

import numpy as np

from ema.numerics.tolerance import is_constant


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


def matvec(M: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Return ``M @ x`` for a 2-D M and a 1-D x: BLAS's gemv, or ``dot`` when M has one row.

    numpy sends a one-row matrix times a vector to ``ddot`` (record 0068 item 1), as at the Lanczos process's
    first step or a fit with one term; gemv, with two rows or more, repeats at every offset (measured).

    Examples
    --------
    >>> matvec(np.array([[1.0, 2.0]]), np.array([3.0, 4.0])).tolist()
    [11.0]
    """
    if M.shape[0] == 1:
        return np.array([dot(M[0], x)])
    return M @ x


def centered(y: np.ndarray) -> np.ndarray:
    """Return y - mean(y); exactly zeros when every value is the same double (0035), where the mean may round.

    So 0/0 on a constant y is detected exactly (uncertainty.md, the bootstrap's step 3), not left to rounding.

    Examples
    --------
    >>> centered(np.full(3, 0.1)).tolist()
    [0.0, 0.0, 0.0]
    """
    if is_constant(y):
        return np.zeros(len(y))
    return y - np.mean(y)
