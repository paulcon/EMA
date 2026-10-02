"""P6's one tolerance function: every tolerance on a model prediction is relative to its range.

principles.md, P6; diagnostics/shared.md, The precheck.

So changing a model prediction's units (y -> a·y + b, a > 0) scales every tolerance by a, and changes no note.
Diagnostics use no absolute tolerance on model predictions.
"""

import math

import numpy as np


def tolerance(values: np.ndarray, rel: float) -> float:
    """Return ``rel`` times the range of the values, max - min (P6).

    Parameters
    ----------
    values
        A model prediction's values over the runs the tolerance is for (a line's, a diagnostic's usable runs).
    rel
        The named constant from the spec that uses it (``LINE_RATE_FLOOR`` = 1e-10, ...), >= 0.

    Raises
    ------
    ValueError
        For no values, a non-finite value, or a negative or non-finite ``rel``.

    Examples
    --------
    >>> tolerance(np.array([2.0, -1.0, 5.0]), 0.5)
    3.0
    """
    values = np.asarray(values, dtype=np.float64)
    if not (math.isfinite(rel) and rel >= 0):
        raise ValueError(f"a relative tolerance is finite and >= 0, not {rel}")
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("a tolerance needs at least one value, each finite")
    return rel * float(np.max(values) - np.min(values))
