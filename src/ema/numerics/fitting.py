"""Least-squares fits by QR, the rank rule, and how well a fit fits and predicts.

linear_model.md and polynomial_model.md, Computation; uncertainty.md, Rules: Rank; 0051; PM2, PM3.

The relative residual, R², and the leave-one-out (LOO) error are undefined (NaN) on 0/0: a constant y, a fit of
rank below its terms, or, for LOO, fewer runs than terms plus one (uncertainty.md, the bootstrap's step 3). There
is no k-fold cross-validation, and no rank tolerance but the matrix_rank rule.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.linalg import lapack

from ema.numerics._vector import centered, dot, matvec, norm


@dataclass(frozen=True, eq=False)
class Fit:
    """A least-squares fit of y on the columns of A ``(n, P)``.

    When its rank is below P, the fit is undefined, and its arrays are NaN (record 0068 item 8).

    Attributes
    ----------
    coefficients : numpy.ndarray
        ``(P,)``, read-only.
    residuals : numpy.ndarray
        ``(n,)``, y - A·coefficients, read-only.
    rank : int
        A's rank by the matrix_rank rule (0051).
    leverages : numpy.ndarray
        ``(n,)``, the hat matrix's diagonal, the squared row norms of Q, read-only.
    """

    coefficients: np.ndarray
    residuals: np.ndarray
    rank: int
    leverages: np.ndarray

    def __post_init__(self) -> None:
        for name in ("coefficients", "residuals", "leverages"):
            values = np.array(getattr(self, name), dtype=np.float64)
            values.flags.writeable = False
            object.__setattr__(self, name, values)


def _rank_of(singular_values: np.ndarray, shape: tuple[int, int]) -> int:
    """Count the singular values above max(n, P)·eps·sigma_max (numpy's matrix_rank rule; 0051)."""
    if singular_values.size == 0:
        return 0
    tol = singular_values.max() * max(shape) * np.finfo(np.float64).eps
    return int(np.count_nonzero(singular_values > tol))


def rank(A: np.ndarray) -> int:
    """Return A's rank by numpy's matrix_rank rule: its singular values above max(n, P)·eps·sigma_max (0051).

    Examples
    --------
    >>> rank(np.array([[1.0, 2.0], [2.0, 4.0], [0.0, 0.0]]))
    1
    """
    A = np.asarray(A, dtype=np.float64)
    return _rank_of(np.linalg.svd(A, compute_uv=False), A.shape)


def least_squares(A: np.ndarray, y: np.ndarray) -> Fit:
    """Fit y by least squares on A's columns, from A's QR factorization (PM2).

    The rank is computed from R's singular values, which are A's in exact arithmetic, by the matrix_rank rule with
    A's shape; below P (fewer than P runs, or runs that don't determine every term), the fit is undefined, with
    NaN arrays and its rank (record 0068 item 8).

    Parameters
    ----------
    A
        ``(n, P)``.
    y
        ``(n,)``.

    Raises
    ------
    ValueError
        When the shapes don't fit.

    Examples
    --------
    >>> fit = least_squares(np.array([[1.0, -1.0], [1.0, 0.0], [1.0, 1.0]]), np.array([1.0, 2.0, 3.0]))
    >>> fit.coefficients.round(12).tolist(), fit.rank
    ([2.0, 1.0], 2)
    """
    A = np.asarray(A, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if A.ndim != 2 or y.shape != (A.shape[0],):
        raise ValueError(f"A of shape {A.shape} and y of shape {y.shape} don't fit")
    n, P = A.shape
    Q, R = np.linalg.qr(A)
    r = _rank_of(np.linalg.svd(R, compute_uv=False), (n, P))
    if r < P:
        return Fit(np.full(P, math.nan), np.full(n, math.nan), r, np.full(n, math.nan))
    # LAPACK's dtrtrs, which scipy.linalg.solve_triangular calls after about 80 µs of checks: the same numbers, and
    # the bootstrap's 1000 refits a third faster (record 0079). R is nonsingular here: its rank is P.
    coefficients, info = lapack.dtrtrs(R, matvec(Q.T, y))  # one term: a one-row product (0068 item 1)
    if info < 0:  # LAPACK's convention: argument -info is illegal
        raise ValueError(f"dtrtrs: argument {-info} is illegal")
    if info > 0:  # R[info - 1, info - 1] is 0; the rank rule refuses such an R first
        raise np.linalg.LinAlgError(f"R is singular: dtrtrs info {info}")
    residuals = y - matvec(A, coefficients)
    leverages = np.sum(Q * Q, axis=1)
    return Fit(coefficients, residuals, r, leverages)


def _spread(y: np.ndarray) -> float:
    """||y - ybar||, exactly 0 for a constant y."""
    return norm(centered(y))


def _finite(value: float) -> float:
    return value if math.isfinite(value) else math.nan


def relative_residual(y: np.ndarray, fit: Fit) -> float:
    """Return ||r|| / ||y - ybar||: 0 for an exact fit, 1 when the fit explains nothing; NaN when undefined.

    Examples
    --------
    >>> A = np.array([[1.0, -1.0], [1.0, 0.0], [1.0, 1.0]])
    >>> y = np.array([0.0, 1.0, 0.0])
    >>> round(relative_residual(y, least_squares(A, y)), 12)
    1.0
    """
    spread = _spread(np.asarray(y, dtype=np.float64))
    if spread == 0:
        return math.nan
    return _finite(norm(fit.residuals) / spread)


def r2(y: np.ndarray, fit: Fit) -> float:
    """Return R² = 1 - ||r||² / ||y - ybar||²; NaN when undefined."""
    deviations = centered(np.asarray(y, dtype=np.float64))
    total = dot(deviations, deviations)
    if total == 0:
        return math.nan
    return _finite(1 - dot(fit.residuals, fit.residuals) / total)


def press(A: np.ndarray, y: np.ndarray, fit: Fit) -> float:
    """Return the LOO error by PRESS: sqrt(sum_k (r_k / (1 - h_kk))²) / ||y - ybar|| (Allen 1974; PM3).

    No refits: each run's residual when the fit leaves it out is r_k / (1 - h_kk), with h_kk its leverage. NaN
    with fewer than P + 1 runs, a constant y, an undefined fit, or a run of leverage 1 (record 0068 item 9).
    """
    n, P = np.shape(A)
    y = np.asarray(y, dtype=np.float64)
    spread = _spread(y)
    if n < P + 1 or spread == 0 or fit.rank < P:
        return math.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        loo = fit.residuals / (1 - fit.leverages)
    return _finite(norm(loo) / spread)
