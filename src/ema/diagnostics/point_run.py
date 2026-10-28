"""The point run: the model prediction at one point, and its measured variation over repeated runs there.

Observations only, no interval method, no random draws (diagnostics/point_run.md, PT1-PT9; P7, U7; records 0011,
0034, 0035, 0036, 0049, 0051, 0061); when the model prediction varies, the result records the model version as
measured noisy in it (``MeasuredNoisy``; C52), and every later result for it carries the note (``evaluate``).
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
    DiagnosticBase,
    DiagnosticParameter,
    Integer,
    Point,
    Transform,
    identity,
    register,
    seed_parameter,
)
from ema.plotting import axis, card_points, hline, new_figure, points, save, strip
from ema.types.design import DesignIdentity
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult, Figure, MeasuredNoisy, Note, Observation, ObservationTable
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace

#: The default number of repeats: 5 runs (point_run.md, Named constants).
POINT_RUN_REPEATS = 4
#: The fewest usable runs for observations: one run is the point's value.
POINT_RUN_MIN_RUNS = 1
#: A failure kind's code to its name.
_KINDS = {kind.code: kind.value for kind in FailureKind}
#: A placeholder id: ``evaluate`` fills in the measured-noisy record's result id and model version.
_UNSET = "0" * 64


class PointRun(DiagnosticBase):
    """The point run (point_run.md): replicates 0 to ``repeats`` at x; observations of them; "varies" exactly."""

    name = "point_run"
    title = "Point run"
    summary = "the model prediction at one point, and its variation over repeated runs there"
    takes_space = False
    parameters = (
        DiagnosticParameter(
            "x",
            "mapping of model parameter names to values",
            {},
            "{} (the nominal point)",
            "the point; unnamed model parameters at their nominal values; each value inside its limits.",  # (G9)
            "yes",
            {"a": 1.5},
            Point(),
        ),
        DiagnosticParameter(
            "repeats",
            "integer ≥ 0",
            POINT_RUN_REPEATS,
            str(POINT_RUN_REPEATS),
            "the number of runs after replicate 0: replicates 1 to repeats.",
            "yes",
            2,
            Integer(0),
        ),
        seed_parameter("recorded; the point run makes no random draws.", "no"),
    )
    interval_method = None
    spawn_tags = ()
    has_estimates = False
    constant_note = False  # one distinct value is its answer for a deterministic model (PT6)
    nesting = ("repeats",)
    TRANSFORMS = MappingProxyType(
        {
            ("shared", "replicate_0"): (Transform.AFFINE, False),
            ("shared", "kind"): (Transform.UNCHANGED, False),
            ("shared", "mean"): (Transform.AFFINE, False),
            ("shared", "std"): (Transform.SCALED, False),
            ("shared", "distinct"): (Transform.UNCHANGED, False),
        }
    )

    def observation_scope(self, n_usable: int, batch: RunBatch) -> str:
        """Return "Of the 5 runs at the point" (C10)."""
        return f"Of the {len(batch.design)} runs at the point"

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return the one panel's strip, over every run (PT9)."""
        return {("point_run", 0): np.ones(len(batch.design), dtype=bool)}

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return the nominal point with 9 repeats: 10 runs, enough for the contract's failure masks."""
        return {"x": {}, "repeats": 9, "seed": 0}

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return ``POINT_RUN_MIN_RUNS``."""
        return POINT_RUN_MIN_RUNS, "one run is the point's value"

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the point design's identity: its space holds every model parameter at x (0049; G9)."""
        x = dict(params["x"])
        at = ModelParameterSpace.at_point(spec, x)
        at.validate(spec)
        params_ = {"x": x, "repeats": int(params["repeats"])}
        return identity("point", at, params_, spec, model_version_id, seed=int(params["seed"]))

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return the observations at the point, and the measured-noisy record when the prediction varies (PT3)."""
        p, units = ctx.request.prediction, ctx.prediction.units
        repeats = int(ctx.request.params["repeats"])
        notes: tuple[Note, ...] = (
            (Note("no_repeats", "No repeats: the variation was not measured."),) if not repeats else ()
        )
        usable = batch.usable(p)
        y = batch.runs.values[p]
        values = y[usable]
        if not len(values):
            return Computation(notes=notes)
        row0 = int(np.flatnonzero(batch.design.replicates == 0)[0])
        if usable[row0]:
            first = Observation("replicate_0", "Replicate 0", float(y[row0]), units)
        else:
            first = Observation("kind", "Replicate 0", _kind(batch, row0), "")
        mean, std = _moments(values)
        distinct = len(np.unique(values))
        rows = (
            (first,),
            (Observation("mean", "Mean", mean, units),),
            (Observation("std", "Standard deviation (ddof 1)", std, units if isinstance(std, float) else ""),),
            (Observation("distinct", "Distinct values", distinct, ""),),
        )
        measured = None
        if distinct >= 2 or not usable.all():  # varies, exactly (0035)
            point = tuple(float(v) for v in batch.design.points[row0])
            measured = MeasuredNoisy(
                _UNSET, _UNSET, p, point, len(batch.design), std if isinstance(std, float) else None, None
            )
        table = ObservationTable("shared", "", ("", p), rows)
        return Computation(observations=(table,), notes=notes, measured_noisy=measured)

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw ``point_run.png``: y_r - y_0 (or the mean, when replicate 0 isn't usable) against r (PT9)."""
        p, units = ctx.request.prediction, ctx.prediction.units
        usable = batch.usable(p)
        y = batch.runs.values[p]
        reps = batch.design.replicates
        row0 = int(np.flatnonzero(reps == 0)[0])
        fig, (ax,) = new_figure(1)
        if usable[row0]:
            base, of = float(y[row0]), f"{p}(replicate 0)"
        else:  # the stored mean (P1), so a constant y's deviations are exactly 0
            base, of = _stored_mean(result) if usable.any() else 0.0, "the mean of the usable runs"
        deviation = y[usable] - base
        points(ax, reps[usable], deviation, joined=True)
        hline(ax, 0.0)
        kinds: list[Any] = [
            FailureKind.from_code(int(batch.runs.kind[r]))
            if batch.runs.status[r] == RunStatus.FAILED.code
            else "missing"
            for r in np.flatnonzero(~usable)
        ]
        entries = strip(ax, reps[~usable], kinds, False, run_ids=batch.runs.run_ids[~usable])
        panel = {
            "x": axis(ax, "x", "replicate", "", integer=True),
            "y": axis(ax, "y", f"{p} − {of}", units),
            "points": card_points(batch.runs.run_ids[usable], replicate=reps[usable], y=y[usable], deviation=deviation),
            "not_usable": entries,
        }
        last = int(reps.max())
        caption = f"{p} - {of} against the replicate number, 0 to {last}."
        card = {"panels": [panel], "deviation_from": base if usable.any() else None}
        return (save(fig, card, out_dir, "point_run", caption),)


def _moments(values: np.ndarray) -> tuple[float, float | str]:
    """Return the mean and the standard deviation (ddof 1, "none" below 2 values), from the deviations from values[0].

    Exact for a constant: mean values[0], standard deviation 0, where ``np.mean`` and ``np.std`` round (7.9 ten times
    has the mean 7.900000000000002); and bit for bit under y -> a·y with a a power of 2 (point_run.md, Degenerate
    cases; C5; record 0075, Review round 1).
    """
    deviations = values - values[0]
    mean = float(values[0] + np.mean(deviations))
    return mean, float(np.std(deviations, ddof=1)) if len(values) >= 2 else "none"


def _stored_mean(result: DiagnosticResult) -> float:
    """Return the result's Mean observation."""
    return next(float(o.value) for t in result.observations for row in t.rows for o in row if o.key == "mean")


def _kind(batch: RunBatch, row: int) -> str:
    """Return a run's kind as the report shows it: "failed (error)", or "missing" for one missing the prediction."""
    if batch.runs.status[row] == RunStatus.FAILED.code:
        return f"failed ({_KINDS[int(batch.runs.kind[row])]})"
    return "missing"


register(PointRun())
