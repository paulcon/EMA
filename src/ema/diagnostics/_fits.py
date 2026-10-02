"""What the fits over a convergent design share: the linear model's now, the polynomial model's when it adopts them.

linear_model.md and polynomial_model.md (Computation, Uncertainty, the per-level table); uncertainty.md (the
bootstrap; 0040, 0041, 0051); designs.md (Samplers); record 0078. Private: a diagnostic imports it; the package
doesn't register it.

A fit's values are one array, ``[coefficients..., relative residual, R², LOO error]``, NaN where undefined (record
0068 item 8), so one function serves the estimate on level L's usable runs, each level's column, and each resample.
"""

import math
from collections.abc import Mapping, Sequence

import numpy as np

from ema.numerics import fitting
from ema.numerics.intervals import Estimator
from ema.types.results import Observation, ObservationTable

#: The values after the coefficients, in order.
FIT_KEYS = ("relative_residual", "r2", "loo")


def fit_values(A: np.ndarray, y: np.ndarray, *, held_out: bool = True) -> np.ndarray:
    """Return ``[coefficients..., relative residual, R², LOO error]`` of y's least-squares fit on A's columns.

    linear_model.md, Computation: the fit by QR, ‖r‖ / ‖y - ȳ‖, 1 - ‖r‖² / ‖y - ȳ‖², and the LOO error by PRESS.
    NaN where undefined: every value when A's rank is below its columns (0051), the last three for a constant y,
    the LOO error with fewer runs than columns plus one or a run of leverage 1 (``ema.numerics.fitting``). Without
    ``held_out``, the LOO error is left off (a resample as drawn doesn't use it).
    """
    found = fitting.least_squares(A, y)
    tail = [fitting.relative_residual(y, found), fitting.r2(y, found)]
    if held_out:
        tail.append(fitting.press(A, y, found))
    return np.concatenate([found.coefficients, tail])


def loo_error(A: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Return ``[LOO error]`` of y's least-squares fit on A's columns, by PRESS; NaN where undefined."""
    return np.array([fitting.press(A, y, fitting.least_squares(A, y))])


def estimators(A: np.ndarray, y: np.ndarray, labels: Sequence[str]) -> tuple[Estimator, Estimator]:
    """Return the bootstrap's two estimators over design rows: the fit as drawn, and LOO on distinct runs.

    uncertainty.md, The bootstrap, step 2: the coefficients, relative residual, and R² are refitted on each
    resample as drawn ("fit", ``labels`` then the two); the LOO error on its distinct runs ("loo"), since a
    left-out run's copy would stay in the fit. ``A`` and ``y`` are the whole design's rows; each resample indexes
    them.
    """
    as_drawn = Estimator(
        "fit", (*labels, *FIT_KEYS[:2]), lambda rows: fit_values(A[rows], y[rows], held_out=False), False
    )
    distinct = Estimator("loo", (FIT_KEYS[2],), lambda rows: loo_error(A[rows], y[rows]), True)
    return as_drawn, distinct


def level_of(rows: np.ndarray, sizes: Sequence[int]) -> np.ndarray:
    """Return each design row's level: the first l with row < n_l (designs.md, Convergent; G7)."""
    return np.searchsorted(np.asarray(sizes), rows, side="right").astype(np.int64)


def per_level(
    A: np.ndarray,
    y: np.ndarray,
    usable: np.ndarray,
    sizes: Sequence[int],
    minimum: int,
    rows: Sequence[tuple[str, str]],
    title: str,
    units: Mapping[str, str] | None = None,
) -> ObservationTable:
    """Return the table of the fit at each level: its usable runs among its first n_l points, then its values.

    linear_model.md (The levels, as observations; LM5): a level with fewer than ``minimum`` usable runs, or a value
    that is undefined, has "none". ``rows`` are each value's (key, label), the coefficients' then ``FIT_KEYS``'.
    ``units`` gives a key's units (the coefficients' are the model prediction's), stored in each of its cells with a
    number; the report leaves them out when ``title`` names them (record 0078 item 2, Review round 1).
    """
    units = units or {}
    columns: list[tuple[Observation, ...]] = []
    for n_l in sizes:
        take = np.flatnonzero(usable[:n_l])
        values = fit_values(A[take], y[take]) if len(take) >= minimum else np.full(len(rows), math.nan)
        cells = [
            Observation(key, label, float(v), units.get(key, ""))
            if math.isfinite(v)
            else Observation(key, label, "none", "")
            for (key, label), v in zip(rows, values, strict=True)
        ]
        columns.append((Observation("usable", "Usable runs", f"{len(take)} of {n_l}", ""), *cells))
    table_rows = tuple(zip(*columns, strict=True))
    heading = "The fit at each level"
    return ObservationTable("levels", title, (heading, *(f"Level {k}" for k in range(len(sizes)))), table_rows)


def bins(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ⌊√n⌋ equal-width bins' edges and counts over the values (scatter's histogram rule; at least 1)."""
    k = max(1, math.isqrt(len(values)))
    counts, edges = np.histogram(values, bins=k)
    return edges, counts
