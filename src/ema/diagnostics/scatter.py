"""Scatter: the model prediction against each varied model parameter, over a uniform design (U1).

The estimates: the mean and the standard deviation (ddof 1) of the usable runs, and for each varied model
parameter, Spearman's rank correlation with the model prediction and the binned first-order index with ⌊√n_u⌋
equal-count bins, adjusted for its bias and not clipped (diagnostics/scatter.md, SC1-SC10; records 0032, 0035, 0048,
0051, 0068 items 11 and 18 (``rank_correlation``, ``binned_index``), 0073 items 1, 3, 4 (Unicode symbols, a table's
title under it, ``seed`` and ``distinct`` in the interval settings), 0075, 0076). Their variability intervals: the
bootstrap over the usable runs from scatter's stream (``SCATTER_BOOT_TAG``; uncertainty.md, the bootstrap), the
binned index recomputed on each resample's distinct runs (V3). Its random draws and data cards follow the shared rules
(shared.md; S8, S9); the precheck and the shared observations and notes are the base's.
"""

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.designs import samplers
from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
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
from ema.numerics.intervals import Estimator, Interval
from ema.numerics.stats import binned_indices, rank_correlations
from ema.plotting import axis, bin_means, card_points, histogram, new_figure, points, save, strip, title
from ema.types.design import DesignIdentity
from ema.types.errors import RequestError
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult, EstimateTable, Figure
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace, Scale

#: The default number of points (scatter.md, Named constants).
SCATTER_N = 200
#: The fewest usable runs for estimates: 3 bins of 3-4 runs, a rank correlation, a standard deviation, a bootstrap.
SCATTER_MIN_RUNS = 10
#: The spawn key of scatter's bootstrap stream: the first diagnostic tag above ``SPAWN_TAG_BASE`` (shared.md, S8).
SCATTER_BOOT_TAG = 2**32 + 1
#: The histogram's figure name (scatter.md, Figures).
HISTOGRAM = "scatter_histogram"
#: The share of the model prediction's range added above and below it in every scatter figure's y axis.
_Y_MARGIN = 0.05

_MOMENTS = ("Model prediction", "Estimate", "Variability interval")
_RHO = ("Model parameter", "Rank correlation ρ", "Variability interval")
_INDEX = ("Model parameter", "Binned first-order index Sᵢ", "Variability interval")


def scatter_bins(n_usable: int) -> int:
    """Return ``SCATTER_HIST_BINS``, ⌊√n_u⌋: the bins of the binned index and of the histogram (scatter.md).

    Examples
    --------
    >>> scatter_bins(200)
    14
    """
    return math.isqrt(n_usable)


def figure_name(parameter: str) -> str:
    """Return a varied model parameter's figure name, ``scatter_<name>``.

    A model parameter named ``histogram``, in any case (``Histogram``), is drawn as ``scatter-<name>``, so it doesn't
    overwrite the histogram on a case-insensitive file system either (record 0076 item 10, Review round 1): a model
    parameter's name is an identifier, so no other name gives a ``-``.
    """
    return f"scatter-{parameter}" if parameter.casefold() == "histogram" else f"scatter_{parameter}"


class Scatter(DiagnosticBase):
    """Scatter (scatter.md): the uniform design's runs, their moments, and each varied model parameter's ρ and S."""

    name = "scatter"
    title = "Scatter"
    summary = (
        "the model prediction against each varied model parameter, over a uniform design: its mean and standard "
        "deviation, and each model parameter's rank correlation and binned first-order index, with variability "
        "intervals"
    )
    takes_space = True
    parameters = (
        DiagnosticParameter(
            "n", "integer ≥ 1", SCATTER_N, str(SCATTER_N), "the number of points.", "yes", 30, Integer(1)
        ),
        seed_parameter("the design's seed, and the bootstrap's.", "yes"),
        DiagnosticParameter(
            "sampler", "name", "random", "random", "the sampler.", "yes", "sobol", Name(samplers.names)
        ),
    )
    interval_method = "bootstrap"
    spawn_tags = (SCATTER_BOOT_TAG,)
    has_estimates = True
    constant_note = True
    nesting = ("n",)
    TRANSFORMS = MappingProxyType(
        {
            ("moments", "mean"): (Transform.AFFINE, False),
            ("moments", "std"): (Transform.SCALED, False),
        }
    )

    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]:
        """Return the declared change under y -> a·y + b (C5): ρ and S are unchanged; the moments as declared."""
        if table_key in ("rank_correlation", "binned_index"):
            return Transform.UNCHANGED, False
        return super().transform(table_key, key)

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return each scatter figure's one panel, whose strip holds every run that isn't usable (S9)."""
        every = np.ones(len(batch.design), dtype=bool)
        return {(f.name, 0): every for f in result.figures if f.name != HISTOGRAM}

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return 20 points, seed 3: enough usable runs under the contract's failure masks, a cheap bootstrap."""
        return {"n": 20, "seed": 3, "sampler": "random"}

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return ``SCATTER_MIN_RUNS``."""
        return SCATTER_MIN_RUNS, "3 bins of 3 to 4 runs, a rank correlation, a standard deviation, and a bootstrap"

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the uniform design's identity (SC1); a space with no varied model parameter is refused.

        Raises
        ------
        RequestError
            For a space that holds every model parameter: a scatter needs one varied.
        """
        if space is None or not space.varied(spec):
            raise RequestError("scatter needs a varied model parameter: the space holds every one")
        return identity(
            "uniform",
            space,
            {"n": int(params["n"])},
            spec,
            model_version_id,
            seed=int(params["seed"]),
            sampler=str(params["sampler"]),
        )

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return the three estimates tables (SC2-SC5, SC9); nothing below the minimum or when constant (SC6)."""
        p = ctx.request.prediction
        usable = np.flatnonzero(batch.usable(p))
        if not estimates_allowed or not len(usable):
            return Computation()
        names = ctx.space.varied(ctx.spec)
        X = _varied_columns(batch, ctx)
        y = np.asarray(batch.runs.values[p], dtype=np.float64)

        def drawn(rows: np.ndarray) -> np.ndarray:
            """Return the mean, the standard deviation, and each ρ, on a resample as drawn."""
            yb = y[rows]
            return np.concatenate(([np.mean(yb), np.std(yb, ddof=1)], rank_correlations(X[rows], yb)))

        def binned(rows: np.ndarray) -> np.ndarray:
            """Return each S, with ⌊√m⌋ bins over the m runs given (a resample's distinct runs)."""
            return binned_indices(X[rows], y[rows], scatter_bins(len(rows)))

        moments_rho = drawn(usable)
        index = binned(usable)
        estimators = [
            Estimator("drawn", ("mean", "std", *names), drawn, distinct=False),
            Estimator("binned", names, binned, distinct=True),
        ]
        if ctx.interval_method is None:
            raise ValueError("scatter's intervals need an interval method (uncertainty.md; C19)")
        found = ctx.interval_method.intervals(
            usable, None, estimators, ctx.stream(self.spawn_tags[0]), ctx.on_step("bootstrap")
        )
        n_u = len(usable)
        units = ctx.prediction.units
        drawn_iv, index_iv = found["drawn"], found["binned"]
        moments = EstimateTable(
            "moments",
            _MOMENTS[0],
            _MOMENTS,
            (
                estimate("mean", "Mean", float(moments_rho[0]), drawn_iv[0]),
                estimate("std", "Standard deviation", float(moments_rho[1]), drawn_iv[1]),
            ),
            units,
            interval_info(ctx, n_u),
        )
        rho = _table("rank_correlation", _RHO[0], _RHO, names, moments_rho[2:], drawn_iv[2:], ctx, n_u)
        title_ = f"{scatter_bins(n_u)} bins."
        s = _table("binned_index", title_, _INDEX, names, index, index_iv, ctx, n_u, distinct="the index")
        return Computation(estimates=(moments, rho, s))

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw ``scatter_<name>.png`` per varied model parameter and ``scatter_histogram.png`` (SC8; 0051).

        The bin means only with estimates; the histogram only when the usable runs' y has a range (not with no
        usable run, one, or a constant model prediction).
        """
        p, units = ctx.request.prediction, ctx.prediction.units
        usable = batch.usable(p)
        y = np.asarray(batch.runs.values[p], dtype=np.float64)
        yu = y[usable]
        ids = batch.runs.run_ids
        n_u = int(usable.sum())
        bins = scatter_bins(n_u)
        varies = n_u > 0 and float(np.max(yu)) > float(np.min(yu))
        extent = None
        if varies:
            lo, hi = float(np.min(yu)), float(np.max(yu))
            extent = (lo - _Y_MARGIN * (hi - lo), hi + _Y_MARGIN * (hi - lo))
        out = ~usable
        kinds: list[Any] = [
            FailureKind.from_code(int(batch.runs.kind[r]))
            if batch.runs.status[r] == RunStatus.FAILED.code
            else "missing"
            for r in np.flatnonzero(out)
        ]
        with_means = bool(result.estimates)
        caption = f"{p} against each model parameter"
        caption += f", with the means of the {bins} bins of the binned index." if with_means else "."
        made = []
        names = ctx.space.varied(ctx.spec)
        X = _varied_columns(batch, ctx)
        for j, name in enumerate(names):
            x = X[:, j]
            log = ctx.space.ranges[name].scale is Scale.LOG
            fig, (ax,) = new_figure(1)
            points(ax, x[usable], yu)
            panel: dict[str, Any] = {}
            if with_means:
                panel["bins"] = _bin_means(ax, x[usable], yu, bins)
            entries = strip(ax, x[out], kinds, log, run_ids=ids[out])
            title(ax, name)
            panel.update(
                {
                    "x": axis(ax, "x", name, ctx.spec.parameter(name).units, log=log),
                    "y": axis(ax, "y", p, units, extent=extent),
                    "points": card_points(ids[usable], x=x[usable], y=yu),
                    "not_usable": entries,
                }
            )
            made.append(save(fig, {"parameter": name, "panels": [panel]}, out_dir, figure_name(name), caption))
        if varies:
            made.append(_histogram(yu, bins, p, units, result.counts.runs - result.counts.usable, out_dir))
        return tuple(made)


def _varied_columns(batch: RunBatch, ctx: AnalysisContext) -> np.ndarray:
    """Return the design's ``(n, d)`` values of the varied model parameters, in model parameter units.

    ρ and S depend on x only through its order, the same in these units and in unit coordinates (scatter.md).
    """
    columns = [p.name for p in ctx.spec.parameters]
    return np.asarray(batch.design.points, dtype=np.float64)[:, [columns.index(n) for n in ctx.space.varied(ctx.spec)]]


def _table(
    key: str,
    title_: str,
    columns: tuple[str, ...],
    names: tuple[str, ...],
    values: np.ndarray,
    found: tuple[Interval, ...],
    ctx: AnalysisContext,
    n_u: int,
    *,
    distinct: str | None = None,
) -> EstimateTable:
    """Return one varied model parameter per row, its estimate keyed by its name, the undefined resamples counted."""
    rows = tuple(estimate(n, n, float(v), iv) for n, v, iv in zip(names, values, found, strict=True))
    undefined = {n: iv.undefined for n, iv in zip(names, found, strict=True)}
    return EstimateTable(
        key, title_, columns, rows, "", interval_info(ctx, n_u, distinct=distinct, undefined=undefined)
    )


def _bin_means(ax: Any, x: np.ndarray, y: np.ndarray, bins: int) -> list[dict[str, Any]]:
    """Draw the binned index's groups as a step line, and return the card's groups: x range, size, and mean.

    The groups are the index's: the usable runs sorted by x (stable), split as ``array_split`` splits them.
    """
    groups = np.array_split(np.argsort(x, kind="stable"), bins)
    lo = np.array([float(np.min(x[g])) for g in groups])
    hi = np.array([float(np.max(x[g])) for g in groups])
    means = np.array([float(np.mean(y[g])) for g in groups])
    bin_means(ax, lo, hi, means)
    return [
        {"x_lo": float(a), "x_hi": float(b), "n": len(g), "mean": float(m)}
        for a, b, g, m in zip(lo, hi, groups, means, strict=True)
    ]


def _histogram(y: np.ndarray, bins: int, p: str, units: str, not_usable: int, out_dir: str) -> Figure:
    """Draw ``scatter_histogram.png``: ⌊√n_u⌋ equal-width bins from the minimum to the maximum of y."""
    counts, edges = np.histogram(y, bins=bins, range=(float(np.min(y)), float(np.max(y))))
    fig, (ax,) = new_figure(1)
    histogram(ax, edges, counts)
    panel = {
        "x": axis(ax, "x", p, units),
        "y": axis(ax, "y", "number of runs", "", integer=True),
        "edges": edges,
        "counts": counts,
    }
    caption = f"{p} over the {len(y)} usable runs, {bins} bin{'' if bins == 1 else 's'}."
    if not_usable == 1:
        caption += " The 1 run not usable is not in it."
    elif not_usable:
        caption += f" The {not_usable} runs not usable are not in it."
    return save(fig, {"panels": [panel]}, out_dir, HISTOGRAM, caption)


register(Scatter())
