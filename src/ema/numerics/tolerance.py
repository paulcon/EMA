"""P6's one tolerance function, and its one test of "constant" (0035), which has no tolerance.

principles.md, P6; diagnostics/shared.md, The precheck; 0035.

Every tolerance on a model prediction is relative to its range, so changing a model prediction's units
(y -> a·y + b, a > 0) scales every tolerance by a, and changes no note. Diagnostics use no absolute tolerance on
model predictions. A model prediction is constant only when every value is the same double.
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


def is_constant(y: np.ndarray) -> bool:
    """Return True when every value of y is the same double (0035; P6): no flatness tolerance.

    The one test of "constant" in ``ema``: a constant y gives the diagnostics' note, and makes R², the relative
    residual, the LOO error, the Sobol indices, rho, and S undefined on a resample (uncertainty.md, the
    bootstrap's step 3). A y that varies, however little (R4b's 1e-12 wiggle), is not constant. An empty y is
    not constant: too few runs decides that case. Values compare with ``==``, so -0.0 and 0.0 are the same.

    Examples
    --------
    >>> is_constant(np.full(20, 0.1)), is_constant(np.array([2.5, 2.5 + 1e-12]))
    (True, False)
    """
    y = np.asarray(y, dtype=np.float64)
    return y.size > 0 and bool(np.all(y == y.flat[0]))
