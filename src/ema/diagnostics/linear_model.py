"""The linear model: a least-squares fit of the model prediction in unit coordinates, over a convergent design.

diagnostics/linear_model.md (LM1-LM10); uncertainty.md (the bootstrap over level L; 0040, 0041, 0052); records
0012, 0051, 0068 (``ema.numerics.fitting``), 0073 (plain Unicode text; a table's title under it), 0075 (the base),
0078 (this step's choices), and 0085 (the in-sample measures as observations). The fit y ≈ β₀ + Σ βᵢ uᵢ on level
L's usable runs gives the coefficients and how well it predicts runs it wasn't fitted to (the LOO error by PRESS),
each with a variability interval; how well it fits (the relative residual and R²), and the same fit at each level,
are observations.
"""

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.designs import samplers
from ema.diagnostics import _fits
from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
    DecimalText,
    DiagnosticBase,
    DiagnosticParameter,
    Integer,
    Name,
    Transform,
    estimate,
    identity,
    interval_info,
    register,
    seed_parameter,
)
from ema.numerics import fitting
from ema.numerics.tolerance import is_constant
from ema.plotting import (
    axis,
    axis_label,
    card_points,
    histogram,
    hline,
    intervals,
    line,
    new_figure,
    points,
    save,
    strip,
)
from ema.types.design import DesignIdentity
from ema.types.errors import RequestError
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult, Estimate, EstimateTable, Figure, Note, ObservationTable
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace, Scale

#: The default error factor per level: just above 1/√2, so the points about double per level (linear_model.md).
LINEAR_ALPHA = "0.7072"
#: The default last level: about 8(d + 1) points (U4; G7).
LINEAR_LEVEL = 2
#: The spawn key of the linear model's bootstrap stream: the next diagnostic tag after scatter's (shared.md).
LINEAR_BOOT_TAG = 2**32 + 2


def linear_nmin(d: int) -> int:
    """Return ``LINEAR_NMIN``, the default size of level 0: 2(d + 1), twice the coefficients, as U4 assumes."""
    return 2 * (d + 1)


def linear_min_runs(d: int) -> int:
    """Return ``LINEAR_MIN_RUNS``, the fewest usable runs for estimates: 2(d + 1) (linear_model.md)."""
    return 2 * (d + 1)


_COEFFICIENT_KEYS = ("intercept", "slope")
_LOO_LABEL = "Leave-one-out error, relative"
_LEVEL_LABELS = {"relative_residual": "Relative residual", "r2": "R²", "loo": "Leave-one-out error"}


class LinearModel(DiagnosticBase):
    """The linear model (linear_model.md): the fit, its intervals by the bootstrap, the levels, three figures."""

    name = "linear_model"
    title = "Linear model"
    summary = "a least-squares linear fit in unit coordinates over a convergent design: coefficients, fit, LOO error"
    takes_space = True
    parameters = (
        DiagnosticParameter(
            "n_min",
            "integer ≥ 1",
            lambda d, _: linear_nmin(d),
            "2(d + 1)",
            "the size of level 0.",
            "yes",
            10,
            Integer(1),
        ),
        DiagnosticParameter(
            "alpha",
            "decimal in (0, 1)",
            LINEAR_ALPHA,
            LINEAR_ALPHA,
            "the error factor per level (designs.md, Convergent).",
            "yes",
            0.5,
            DecimalText(0.0, 1.0),
        ),
        DiagnosticParameter(
            "level", "integer ≥ 0", LINEAR_LEVEL, str(LINEAR_LEVEL), "L, the last level.", "yes", 3, Integer(0)
        ),
        seed_parameter("the design's seed, and the bootstrap's.", "yes"),
        DiagnosticParameter(
            "sampler",
            "name",
            "random",
            "random",
            "the sampler; convergent needs a nested one.",
            "yes",
            "sobol",
            Name(samplers.names),
        ),
    )
    interval_method = "bootstrap"
    spawn_tags = (LINEAR_BOOT_TAG,)
    has_estimates = True
    constant_note = True
    nesting = ("level",)
    TRANSFORMS = MappingProxyType(
        {
            **{(table, "intercept"): (Transform.AFFINE, False) for table in ("coefficients", "levels")},
            **{(table, "slope"): (Transform.SCALED, False) for table in ("coefficients", "levels")},
            **{("levels", key): (Transform.UNCHANGED, False) for key in _LEVEL_LABELS},
            ("loo", "loo"): (Transform.UNCHANGED, False),
            ("levels", "usable"): (Transform.UNCHANGED, False),
        }
    )

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return the defaults with seed 0: 8, 16, 32 runs at d = 3 (record 0078 item 11)."""
        return {"seed": 0}

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return ``LINEAR_MIN_RUNS``: 2(d + 1)."""
        return linear_min_runs(d), f"twice its {d + 1} coefficients"

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return the shadow's strip, over every run of level L: the design's rows (C12)."""
        return {("linear_model_shadow", 0): np.ones(len(batch.design), dtype=bool)}

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the convergent design's identity (LM1); a space with no varied model parameter is refused."""
        if space is None or not space.varied(spec):
            raise RequestError("linear model needs a space that varies at least one model parameter")
        levels = {"n_min": int(params["n_min"]), "alpha": str(params["alpha"]), "level": int(params["level"])}
        return identity(
            "convergent", space, levels, spec, model_version_id, seed=int(params["seed"]), sampler=params["sampler"]
        )

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return the fit on level L's usable runs with its intervals (LM2-LM4), and the fit at each level (LM5).

        The coefficients and the LOO error are estimates; the relative residual and R² are observations, level L's in
        the per-level table, with the line that says why they have no interval (record 0085).
        """
        p, units = ctx.request.prediction, ctx.prediction.units
        names = ctx.space.varied(ctx.spec)
        d = len(names)
        usable = batch.usable(p)
        rows = np.flatnonzero(usable)
        if not len(rows):
            return Computation()
        A = _design_matrix(ctx, batch)
        y = np.asarray(batch.runs.values[p], dtype=np.float64)
        sizes = batch.design.levels or (len(batch.design),)
        labels = ("Intercept", *names)
        keys = (_COEFFICIENT_KEYS[0], *[_COEFFICIENT_KEYS[1]] * d)
        observations: tuple[ObservationTable, ...] = ()
        if not (len(rows) >= 2 and is_constant(y[rows])):  # a constant's fits are of one value (record 0078 item 3)
            level_rows = [*zip(keys, labels, strict=True), *_LEVEL_LABELS.items()]
            minimum = linear_min_runs(d)
            in_units = f"Coefficients in {units}. " if units else ""
            title = f"{in_units}{_fits.LEVELS_SENTENCE} {_fits.IN_SAMPLE_SENTENCE}"  # record 0085's line
            per_key = {key: units for key in _COEFFICIENT_KEYS}  # in the cells; the title names them (0078 item 2)
            observations = (_fits.per_level(A, y, usable, sizes, minimum, level_rows, title, per_key),)
        if not estimates_allowed:
            return Computation(observations=observations)
        values = _fits.fit_values(A[rows], y[rows])
        if not math.isfinite(values[0]):
            rank = fitting.least_squares(A[rows], y[rows]).rank  # the rank that left the fit undefined
            text = (
                f"The usable runs' unit coordinates have rank {rank} with the constant, "
                f"below the fit's {d + 1} coefficients: no fit."
            )
            return Computation(observations=observations, notes=(Note("rank_deficient", text),))
        method = ctx.interval_method
        assert method is not None  # the registry's bootstrap, or a test's fake (C19)
        found = method.intervals(
            rows,
            _fits.level_of(rows, sizes),
            _fits.estimators(A, y, keys),
            ctx.stream(self.spawn_tags[0]),  # LINEAR_BOOT_TAG (S8)
            ctx.on_step("bootstrap"),
        )
        n_u = len(rows)
        drawn = [
            (estimate(key, label, float(v), iv), iv.undefined)
            for key, label, v, iv in zip(keys, labels, values[: d + 1], found["coefficients"], strict=True)
        ]
        tables = [_table("coefficients", _equation(ctx, names), "Coefficient", drawn, units, ctx, n_u)]
        notes: tuple[Note, ...] = ()
        if math.isfinite(values[-1]):
            (loo_iv,) = found["loo"]
            loo = [(estimate("loo", _LOO_LABEL, float(values[-1]), loo_iv), loo_iv.undefined)]
            tables.append(_table("loo", "Held out", "Held out", loo, "", ctx, n_u, distinct="the error"))
        else:  # uncertainty.md, Rules: where a value can't be computed, no estimate, and a note (record 0078 item 5)
            notes = (_loo_note(A[rows], y[rows]),)
        return Computation(estimates=tuple(tables), observations=observations, notes=notes)

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw the shadow, the slopes, and the residuals (LM8), from the runs and the stored coefficients only."""
        table = next((t for t in result.estimates if t.key == "coefficients"), None)
        if table is None:
            return ()  # no fit: no figures (0051)
        p, units = ctx.request.prediction, ctx.prediction.units
        names = ctx.space.varied(ctx.spec)
        beta = np.array([e.value for e in table.estimates])
        usable = batch.usable(p)
        U = ctx.space.to_unit(ctx.spec, batch.design.points)
        y = np.asarray(batch.runs.values[p], dtype=np.float64)
        ids = batch.runs.run_ids
        out: list[Figure] = []
        size = math.sqrt(float(np.sum(beta[1:] * beta[1:])))
        if size > 0.0:
            out.append(_shadow(batch, ctx, out_dir, beta, size, U, y, usable))
        out.append(_slopes(table, ctx, out_dir, names, units))
        residuals = y[usable] - (beta[0] + np.sum(U[usable] * beta[1:], axis=1))
        edges, counts = _fits.bins(residuals)
        fig, (ax,) = new_figure(1)
        histogram(ax, edges, counts)
        panel = {
            "x": axis(ax, "x", f"residual of {p}", units),
            "y": axis(ax, "y", "number of runs", "", integer=True),
            "points": card_points(ids[usable], residual=residuals),
        }
        caption = f"The residuals of the {len(residuals)} usable runs, {len(counts)} bins."
        card = {"panels": [panel], "edges": edges, "counts": counts}
        out.append(save(fig, card, out_dir, "linear_model_residuals", caption))
        return tuple(out)


def _loo_note(A: np.ndarray, y: np.ndarray) -> Note:
    """Return the note for a LOO error that is undefined while the fit is defined (record 0078 item 5).

    It names a usable run of leverage 1 only when one has exactly 1 (PRESS's r/(1 - h) divides by 0); otherwise
    (an overflow) it says only that the error is undefined on these runs (Review round 1).
    """
    text = "The leave-one-out error is undefined on these runs."
    if np.any(fitting.least_squares(A, y).leverages == 1):
        text = "The leave-one-out error is undefined: a usable run has leverage 1."
    return Note("loo_undefined", text)


def _table(
    key: str,
    title: str,
    heading: str,
    rows: list[tuple[Estimate, int]],
    units: str,
    ctx: AnalysisContext,
    n_usable: int,
    distinct: str | None = None,
) -> EstimateTable:
    """Return an estimates table, its line naming the method, the seed, and each estimate's undefined resamples."""
    info = interval_info(ctx, n_usable, distinct=distinct, undefined={e.label: n for e, n in rows})
    columns = (heading, "Estimate", "Variability interval")
    return EstimateTable(key, title, columns, tuple(e for e, _ in rows), units, info)


def _design_matrix(ctx: AnalysisContext, batch: RunBatch) -> np.ndarray:
    """Return A = [1, U]: every design row's unit coordinates, a log range through its logarithm (0024)."""
    U = ctx.space.to_unit(ctx.spec, batch.design.points)
    return np.column_stack([np.ones(len(U)), U])


def _equation(ctx: AnalysisContext, names: tuple[str, ...]) -> str:
    """Return the coefficients table's title: the fit's form, and its log ranges (record 0078 item 7)."""
    logs = [n for n in names if ctx.space.ranges[n].scale is Scale.LOG]
    which = f" ({logs[0]} through its logarithm)" if len(logs) == 1 else ""
    if len(logs) > 1:
        which = f" ({', '.join(logs)} through their logarithms)"
    p = ctx.request.prediction
    return f"{p} ≈ intercept + Σ slope·u, u the unit coordinates in [-1, 1]{which}."


def _kinds(batch: RunBatch, rows: np.ndarray) -> list[Any]:
    """Each run's kind for the strip: its failure's, or "missing" for an ok run missing this model prediction."""
    runs = batch.runs
    return [
        FailureKind.from_code(int(runs.kind[r])) if runs.status[r] == RunStatus.FAILED.code else "missing" for r in rows
    ]


def _shadow(
    batch: RunBatch,
    ctx: AnalysisContext,
    out_dir: str,
    beta: np.ndarray,
    size: float,
    U: np.ndarray,
    y: np.ndarray,
    usable: np.ndarray,
) -> Figure:
    """Draw y against w·u, w = β/‖β‖, with the fitted line β₀ + ‖β‖·(w·u) and the strip of runs not usable."""
    p, units = ctx.request.prediction, ctx.prediction.units
    names = ctx.space.varied(ctx.spec)
    ids = batch.runs.run_ids
    w = beta[1:] / size
    t = np.sum(U * w, axis=1)
    fig, (ax,) = new_figure(1)
    points(ax, t[usable], y[usable])
    ends = np.array([np.min(t[usable]), np.max(t[usable])])
    line(ax, ends, beta[0] + size * ends)
    not_usable = np.flatnonzero(~usable)
    entries = strip(ax, t[not_usable], _kinds(batch, not_usable), False, run_ids=ids[not_usable])
    panel = {
        "x": axis(ax, "x", "w·u", ""),
        "y": axis(ax, "y", p, units),
        "points": card_points(ids[usable], w_u=t[usable], y=y[usable]),
        "not_usable": entries,
    }
    card = {"panels": [panel], "w": [{"parameter": n, "w": float(v)} for n, v in zip(names, w, strict=True)],
            "intercept": float(beta[0]), "norm": size}  # fmt: skip
    caption = f"{p} against w·u, the unit coordinates projected on the direction of the slopes, with the fitted line."
    return save(fig, card, out_dir, "linear_model_shadow", caption)


def _slopes(table: EstimateTable, ctx: AnalysisContext, out_dir: str, names: tuple[str, ...], units: str) -> Figure:
    """Draw each slope with its variability interval as a bar, in the model spec's order, and a line at 0."""
    slopes = table.estimates[1:]
    x = np.arange(len(slopes), dtype=float)
    values = np.array([e.value for e in slopes])
    lo = np.array([e.interval[0] if e.interval else e.value for e in slopes])
    hi = np.array([e.interval[1] if e.interval else e.value for e in slopes])
    fig, (ax,) = new_figure(1)
    intervals(ax, x, values, lo, hi)
    hline(ax, 0.0)
    ax.set_xticks(x, [axis_label(n, "") for n in names])  # escaped: a spec's names print literally (T10)
    ax.tick_params(axis="x", labelsize=8.0, labelrotation=90.0 if len(names) > 8 else 0.0)
    panel = {
        "x": axis(ax, "x", "model parameter", ""),
        "y": axis(ax, "y", "slope", units),
        "points": [
            {"parameter": n, "slope": e.value, "interval": None if e.interval is None else list(e.interval)}
            for n, e in zip(names, slopes, strict=True)
        ],
    }
    per = f"in {units} per half-range" if units else "per half-range"
    caption = f"Each slope with its variability interval, {per}."
    return save(fig, {"panels": [panel]}, out_dir, "linear_model_coefficients", caption)


register(LinearModel())
