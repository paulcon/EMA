"""Scatter's estimates for one varied model parameter: Spearman's rank correlation and the binned index.

scatter.md, Computation.

Both depend on x only through its order, so they are the same in model parameter units and in unit coordinates,
log scale or not. Each is NaN where it is undefined (uncertainty.md, Per diagnostic).
"""

import math

import numpy as np
from scipy.stats import rankdata

from ema.numerics._vector import centered, dot


def _pair(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 1 or x.shape != y.shape:
        raise ValueError(f"x of shape {x.shape} and y of shape {y.shape} don't pair")
    return x, y


def rank_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Return Spearman's rho between x and y, with average ranks for ties; NaN when x or y is constant (0/0).

    Examples
    --------
    >>> rank_correlation(np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.0, 3.0, 2.0, 4.0]))
    0.8
    """
    x, y = _pair(x, y)
    rx = rankdata(x)
    ry = rankdata(y)
    rx -= np.mean(rx)
    ry -= np.mean(ry)
    denominator = math.sqrt(dot(rx, rx) * dot(ry, ry))
    if denominator == 0:
        return math.nan
    return dot(rx, ry) / denominator


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
    n = len(y)
    if not 1 <= bins <= n:
        raise ValueError(f"{bins} bins for {n} runs: need 1 to {n}")
    deviations = centered(y)
    total = dot(deviations, deviations)
    if total == 0 or n <= bins:
        return math.nan
    groups = np.array_split(deviations[np.argsort(x, kind="stable")], bins)
    between = math.fsum(len(g) * float(np.mean(g)) ** 2 for g in groups)
    return 1 - (1 - between / total) * (n - 1) / (n - bins)
