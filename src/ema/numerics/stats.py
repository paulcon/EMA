"""Scatter's estimates for one varied model parameter: Spearman's rank correlation and the binned index.

scatter.md, Computation.

Both depend on x only through its order, so they are the same in model parameter units and in unit coordinates,
log scale or not. Each is NaN where it is undefined (uncertainty.md, Per diagnostic).
"""

import math

import numpy as np

from ema.numerics._vector import centered, dot


def _pair(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 1 or x.shape != y.shape:
        raise ValueError(f"x of shape {x.shape} and y of shape {y.shape} don't pair")
    return x, y


def _columns(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if X.ndim != 2 or y.ndim != 1 or X.shape[0] != y.shape[0]:
        raise ValueError(f"X of shape {X.shape} and y of shape {y.shape} don't pair: X is (n, d), y (n,)")
    return X, y


def average_ranks(A: np.ndarray) -> np.ndarray:
    """Return each row's ranks, 1 to n, ties given their average rank: ``scipy.stats.rankdata``'s "average".

    Each value is a multiple of 1/2, exact. Written with numpy alone: scipy's ``rankdata`` costs about 0.1 ms a
    call in its array-API layer, and scatter's bootstrap ranks 1000 resamples (record 0076).

    Parameters
    ----------
    A
        ``(d, n)``, finite.

    Examples
    --------
    >>> average_ranks(np.array([[3.0, 1.0, 3.0, 2.0]])).tolist()
    [[3.5, 1.0, 3.5, 2.0]]
    """
    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    d, n = A.shape
    if not A.size:
        return np.empty((d, n))
    at = np.argsort(A, axis=1, kind="stable") + (np.arange(d) * n)[:, None]  # each row's order, as flat indices
    s = A.ravel()[at]
    starts = np.ones((d, n), dtype=bool)  # where a run of equal values starts, in each sorted row
    np.not_equal(s[:, 1:], s[:, :-1], out=starts[:, 1:])
    group = np.cumsum(starts.ravel()) - 1  # each row starts a run, so no run spans two rows
    counts = np.bincount(group)
    first = (np.cumsum(counts) - counts) % n  # each run's first position in its row
    ranks = np.empty(d * n)
    ranks[at.ravel()] = (first + (counts + 1) / 2.0)[group]
    return ranks.reshape(d, n)


def rank_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Return Spearman's rho between x and y, with average ranks for ties; NaN when x or y is constant (0/0).

    Examples
    --------
    >>> rank_correlation(np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.0, 3.0, 2.0, 4.0]))
    0.8
    """
    x, y = _pair(x, y)
    return float(rank_correlations(x[:, None], y)[0])


def rank_correlations(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Return Spearman's rho between each column of X and y: ``rank_correlation`` per column, in one pass.

    y is ranked once. The centered ranks are multiples of 1/2, so their products and sums are exact while the sums
    of squares, about n³/12 in quarters, fit in a double's 53 bits (n ≲ 3·10⁵): each value is then the one
    ``rank_correlation`` gives for its column, bit for bit, whatever the order of the sums (scatter's bootstrap
    calls it 1000 times; record 0076 item 11, amending 0068 item 11). Beyond that, the sums round, and the two may
    differ in the last bits.

    Parameters
    ----------
    X
        ``(n, d)``.
    y
        ``(n,)``.

    Returns
    -------
    numpy.ndarray
        ``(d,)``; NaN for a constant column, and everywhere for a constant y.
    """
    X, y = _columns(X, y)
    R = average_ranks(np.vstack((y, X.T))) - (len(y) + 1) / 2.0  # the mean rank, exactly
    squares = np.sum(R * R, axis=1)
    numerator = np.sum(R[1:] * R[0], axis=1)
    denominator = np.sqrt(squares[1:] * squares[0])
    return np.divide(numerator, denominator, out=np.full(X.shape[1], math.nan), where=denominator != 0)


def binned_index(x: np.ndarray, y: np.ndarray, bins: int) -> float:
    """Return the binned first-order index S, the correlation ratio adjusted for its bias (scatter.md, steps 1-5).

    The runs are sorted by x (stable: ties keep the design's order) and split into ``bins`` consecutive groups as
    equal as possible, the first n mod B one run larger (numpy's ``array_split``); eta² = sum_b n_b (ybar_b -
    ybar)² / sum_k (y_k - ybar)²; S = 1 - (1 - eta²)(n - 1)/(n - B), not clipped. NaN when y is constant (0/0) or
    n <= B (fewer than 2 distinct runs).

    Parameters
    ----------
    x, y
        ``(n,)`` each, in the design's order.
    bins
        B, floor(sqrt(n)) in scatter (the caller's rule).

    Raises
    ------
    ValueError
        For fewer than 1 bin, or more bins than runs.

    Examples
    --------
    >>> round(binned_index(np.arange(6.0), np.array([1.0, 1.0, 1.0, 3.0, 3.0, 3.0]), 2), 12)
    1.0
    """
    x, y = _pair(x, y)
    return float(binned_indices(x[:, None], y, bins)[0])


def binned_indices(X: np.ndarray, y: np.ndarray, bins: int) -> np.ndarray:
    """Return the binned index S of each column of X: ``binned_index`` per column, in one pass (record 0076).

    y is centered once; each column's stable order sorts the deviations, and each group's sum is
    ``np.add.reduceat``'s: its first value plus numpy's pairwise sum of the rest, the same at every memory offset
    (measured; C7 checks scatter's). A group's mean may differ from ``np.mean``'s in its last bit.

    Parameters
    ----------
    X
        ``(n, d)``, in the design's order.
    y
        ``(n,)``.
    bins
        B.

    Returns
    -------
    numpy.ndarray
        ``(d,)``; NaN everywhere when y is constant or n <= B.

    Raises
    ------
    ValueError
        For fewer than 1 bin, or more bins than runs.
    """
    X, y = _columns(X, y)
    n, d = X.shape
    if not 1 <= bins <= n:
        raise ValueError(f"{bins} bins for {n} runs: need 1 to {n}")
    deviations = centered(y)
    total = dot(deviations, deviations)
    if total == 0 or n <= bins:
        return np.full(d, math.nan)
    q, r = divmod(n, bins)
    k = np.arange(bins)
    sizes = q + (k < r)  # array_split's: the first n mod B one larger
    order = np.argsort(np.ascontiguousarray(X.T), axis=1, kind="stable")
    means = np.add.reduceat(deviations[order], k * q + np.minimum(k, r), axis=1) / sizes
    between = np.array([math.fsum(row) for row in (sizes * means**2).tolist()])
    return 1 - (1 - between / total) * (n - 1) / (n - bins)
