"""Run batches built directly, and the toy diagnostic, for the diagnostic contract and the diagnostics' tests.

contracts.md, The contract model (0045): d = 3 (a, b, c log, h held), f = a + b² + 0.05·a·log₁₀ c, y = f, z = f + 1
missing where b > 0.5; d = 1, f = a + a², z missing where a > 1.5; d = 20, f = x1 + x2² + 0.1·x3·x4, z missing where
x1 > 0.5. A point run's replicate r is f(x)·(1 + r·2⁻³⁰). Failures are masks over the design's rows, set by the
fixture with a kind and a reason per run (no model runs).

``prepare`` makes a diagnostic evaluation's request, design, and context the way the workspace will (§7, steps 2-3);
``batch`` builds its runs; ``evaluate`` runs ``ema.diagnostics.base.evaluate`` with a provenance and a result id.
``Toy`` is the contract's toy (kept here, not registered): it keeps every promise.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ema import plotting
from ema.designs import generators
from ema.diagnostics import base
from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
    DiagnosticBase,
    DiagnosticParameter,
    Integer,
    Transform,
)
from ema.numerics import intervals
from ema.numerics.intervals import Estimator
from ema.types.design import Design, DesignIdentity
from ema.types.identity import ID_DTYPE, reuse_key, sha256_hex
from ema.types.model import ModelSpec
from ema.types.requests import Request
from ema.types.results import (
    DiagnosticResult,
    EstimateTable,
    Figure,
    MeasuredNoisy,
    Observation,
    ObservationTable,
)
from ema.types.runs import FailureKind, RunBatch, RunColumns, RunKey, RunStatus
from ema.types.space import ModelParameterSpace
from tests.support.designs import CONTRACT, CONTRACT_SPACE, D1, D1_SPACE, D20, D20_SPACE, model_version_id

MODELS: dict[int, tuple[ModelSpec, dict[str, Any]]] = {
    3: (CONTRACT, CONTRACT_SPACE),
    1: (D1, D1_SPACE),
    20: (D20, D20_SPACE),
}
#: Fixed versions, so a test's result ids and reports don't depend on the installed libraries.
VERSIONS = {"ema": "2.0.0", "numpy": "2.3.1", "scipy": "1.16.0", "matplotlib": "3.10.0"}
APPROVAL = sha256_hex("an approval")


def f(spec: ModelSpec, points: np.ndarray) -> np.ndarray:
    """The contract model's f at complete points (contracts.md)."""
    x = {p.name: points[:, j] for j, p in enumerate(spec.parameters)}
    if spec is D1:
        return x["a"] + x["a"] ** 2
    if spec is D20:
        return x["x1"] + x["x2"] ** 2 + 0.1 * x["x3"] * x["x4"]
    return x["a"] + x["b"] ** 2 + 0.05 * x["a"] * np.log10(x["c"])


def z_missing(spec: ModelSpec, points: np.ndarray) -> np.ndarray:
    """Where z is missing (0045): b > 0.5 at d = 3; the first model parameter in its top quarter otherwise."""
    if spec is CONTRACT:
        return points[:, 1] > 0.5
    return points[:, 0] > (1.5 if spec is D1 else 0.5)


@dataclasses.dataclass
class Case:
    """One prepared diagnostic evaluation: what the workspace has before resolving its runs."""

    diagnostic: Any
    spec: ModelSpec
    request: Request
    identity: DesignIdentity
    design: Design
    ctx: AnalysisContext
    model_version_id: str

    def f(self) -> np.ndarray:
        """The contract model's y on this design: f, times (1 + r·2⁻³⁰) for replicate r (0045)."""
        return f(self.spec, self.design.points) * (1.0 + self.design.replicates * 2.0**-30)

    @property
    def first_varied(self) -> np.ndarray:
        """The design's unit coordinate of its first varied model parameter, in [-1, 1] (for failure masks)."""
        varied = self.ctx.space.varied(self.spec)
        if not varied:
            n = len(self.design)
            return -1.0 + 2.0 * self.design.replicates / max(n - 1, 1)
        return self.ctx.space.to_unit(self.spec, self.design.points)[:, 0]


def prepare(
    diagnostic: Any,
    d: int = 3,
    *,
    params: Mapping[str, Any] | None = None,
    prediction: str | None = "y",
    measured_noisy: Sequence[MeasuredNoisy] = (),
    interval_method: Any = None,
    on_progress: Any = None,
) -> Case:
    """Make the request (the diagnostic's example request, changed by ``params``), the design, and the context."""
    spec, space = MODELS[d]
    given = {**diagnostic.example_request(d), **(params or {})}
    request = base.make_request(diagnostic, spec, space if diagnostic.takes_space else None, prediction, given)
    mv = model_version_id(spec)
    parsed = base.request_space(request, spec)
    ident = diagnostic.design_identity(parsed if diagnostic.takes_space else None, request.params, spec, mv)
    design = generators.get(ident.kind).build(ident, spec)
    if interval_method is None and diagnostic.interval_method is not None:
        interval_method = intervals.get(diagnostic.interval_method)
    ctx = AnalysisContext(request, spec, parsed, interval_method, tuple(measured_noisy), on_progress)
    return Case(diagnostic, spec, request, ident, design, ctx, mv)


def batch(
    case: Case,
    *,
    y: np.ndarray | None = None,
    z: np.ndarray | None = None,
    failed: np.ndarray | None = None,
    kinds: Sequence[FailureKind] | None = None,
    reasons: Sequence[str] | None = None,
    missing_y: np.ndarray | None = None,
    new: np.ndarray | None = None,
    design: Design | None = None,
) -> RunBatch:
    """The run batch on the case's design: y and z (the contract model's by default), with failures set by masks.

    ``failed`` rows are failed runs, kind ``kinds[i % len(kinds)]`` and reason ``reasons[i % len(reasons)]`` for
    the i-th failed run; ``missing_y`` rows are ok runs with y missing and z read. Run ids are the runs' real ids.
    """
    design = design or case.design
    n = len(design)

    def fy() -> np.ndarray:  # the contract model's, when y or z isn't given
        return f(case.spec, design.points) * (1.0 + design.replicates * 2.0**-30)

    y = fy() if y is None else np.array(y, dtype=float)
    z = np.where(z_missing(case.spec, design.points), np.nan, fy() + 1.0) if z is None else np.array(z, dtype=float)
    failed = np.zeros(n, dtype=bool) if failed is None else np.asarray(failed, dtype=bool)
    missing_y = np.zeros(n, dtype=bool) if missing_y is None else np.asarray(missing_y, dtype=bool)
    kinds = list(kinds or [FailureKind.ERROR])
    reasons = list(reasons or ["exited with code 3"])
    keys = [RunKey.make(case.model_version_id, design.points[i], int(design.replicates[i]), 0) for i in range(n)]
    ids = [k.run_id for k in keys]
    status = np.where(failed, RunStatus.FAILED.code, RunStatus.OK.code)
    kind = np.full(n, -1)
    reason_of: dict[str, str] = {}
    for i, row in enumerate(np.flatnonzero(failed)):
        kind[row] = kinds[i % len(kinds)].code
        reason_of[ids[row]] = reasons[i % len(reasons)]
    y = np.where(failed | missing_y, np.nan, y)
    if (missing_y & np.isnan(z)).any():
        z = np.where(missing_y & np.isnan(z), fy() + 1.0, z)
    z = np.where(failed, np.nan, z)
    missing = {
        "y": {ids[i]: "y = (\\S+) not found in out.txt" for i in np.flatnonzero(~failed & np.isnan(y))},
        "z": {ids[i]: "z is not finite" for i in np.flatnonzero(~failed & np.isnan(z))},
    }
    runs = RunColumns(
        run_ids=ids,
        points=np.array(design.points),
        replicates=np.array(design.replicates),
        status=status,
        kind=kind,
        values={"y": y, "z": z},
        reasons=reason_of,
        stderr_tails={},
        missing=missing,
        time_s=np.zeros(n),
        host=np.array(["here"] * n),
        program=np.array(["python"] * n),
        batch_call_ids=np.zeros(n, dtype=ID_DTYPE),
        approval_ids=[APPROVAL] * n,
    )
    return RunBatch(design=design, runs=runs, new=np.zeros(n, dtype=bool) if new is None else new)


def result_id(case: Case, run_batch: RunBatch) -> str:
    """The result's id: the SHA-256 of its reuse key (data_model.md §3.4)."""
    return sha256_hex(reuse_key(case.model_version_id, case.request, run_batch.runs.run_ids, VERSIONS))


def evaluate(
    case: Case, run_batch: RunBatch, out_dir: str | Path, *, ctx: AnalysisContext | None = None
) -> DiagnosticResult:
    """Run ``base.evaluate`` as the workspace's step 8 will: a provenance, a result id, a result directory."""
    ctx = ctx or case.ctx
    approval = APPROVAL if run_batch.new.any() else None
    provenance = base.make_provenance(
        run_batch, ctx, case.diagnostic, case.model_version_id, approval_id=approval, versions=VERSIONS
    )
    return base.evaluate(case.diagnostic, run_batch, ctx, provenance, result_id(case, run_batch), str(out_dir))


# --------------------------------------------------------------------------------------------------------------
# The toy: the mean and standard deviation of y, with bootstrap intervals, on a uniform design

TOY_TAG = 2**32 + 99


class Toy(DiagnosticBase):
    """The diagnostic contract's toy: it keeps every promise (contracts.md, Negative controls)."""

    name = "toy"
    title = "Toy"
    summary = "the mean and standard deviation of the usable runs, with variability intervals"
    takes_space = True
    parameters = (
        DiagnosticParameter("n", "integer ≥ 1", 40, "40", "the number of points.", "yes", 30, Integer(1)),
        base.seed_parameter("the design's seed, and the bootstrap's.", "yes"),
    )
    interval_method = "bootstrap"
    spawn_tags = (TOY_TAG,)
    has_estimates = True
    constant_note = True
    nesting = ("n",)
    TRANSFORMS = MappingProxyType(
        {
            ("moments", "mean"): (Transform.AFFINE, False),
            ("moments", "std"): (Transform.SCALED, False),
            ("toy_counts", "usable_share"): (Transform.UNCHANGED, False),
        }
    )

    def example_request(self, d: int) -> Mapping[str, Any]:
        return {"n": 40, "seed": 3}

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        return 5, "a standard deviation from at least 5 runs"

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        assert space is not None
        return base.identity(
            "uniform", space, {"n": params["n"]}, spec, model_version_id, seed=params["seed"], sampler="random"
        )

    # The parts the broken toys change, one each

    def values(self, run_batch: RunBatch, ctx: AnalysisContext) -> tuple[np.ndarray, np.ndarray]:
        """The model prediction's values and the usable rows' indices."""
        p = ctx.request.prediction
        return run_batch.runs.values[p], np.flatnonzero(run_batch.usable(p))

    def moments(self, y: np.ndarray, idx: np.ndarray) -> np.ndarray:
        return np.array([np.mean(y[idx]), np.std(y[idx], ddof=1)])

    def stream(self, ctx: AnalysisContext) -> np.random.Generator:
        return ctx.stream(self.spawn_tags[0])

    def method(self, ctx: AnalysisContext) -> Any:
        return ctx.interval_method

    def compute(self, run_batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        y, idx = self.values(run_batch, ctx)
        if not len(idx):
            return Computation()
        title = "Of the design's rows"
        share = Observation("usable_share", "Usable share", len(idx) / len(run_batch.design), "")
        obs = ObservationTable("toy_counts", title, (title, "share"), ((share,),))
        if not estimates_allowed:
            return Computation(observations=(obs,))
        mean, std = self.moments(y, idx)
        est = Estimator("moments", ("mean", "std"), lambda i: self.moments(y, i), distinct=False)
        found = self.method(ctx).intervals(idx, None, [est], self.stream(ctx), ctx.on_step("bootstrap"))["moments"]
        units = ctx.prediction.units
        table = EstimateTable(
            "moments",
            "Moment",
            ("Moment", "Value", "Variability interval"),
            (
                base.estimate("mean", "Mean", float(mean), found[0]),
                base.estimate("std", "Standard deviation", float(std), found[1]),
            ),
            units,
            base.interval_info(ctx, len(idx)),
        )
        return Computation(estimates=(table,), observations=(obs,))

    def strips(self, run_batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        return {("toy", 0): np.ones(len(run_batch.design), dtype=bool)}

    def not_usable(self, usable: np.ndarray) -> np.ndarray:
        return ~usable

    def figures(
        self, run_batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        p = ctx.request.prediction
        name = ctx.space.varied(ctx.spec)[0]
        j = [q.name for q in ctx.spec.parameters].index(name)
        log = ctx.space.ranges[name].scale.value == "log"
        usable = run_batch.usable(p)
        x, y, ids = run_batch.design.points[:, j], run_batch.runs.values[p], run_batch.runs.run_ids
        fig, (ax,) = plotting.new_figure(1)
        plotting.points(ax, x[usable], y[usable])
        out = self.not_usable(usable)
        kinds = [FailureKind.from_code(int(k)) if k >= 0 else "missing" for k in run_batch.runs.kind[out]]
        strip = plotting.strip(ax, x[out], kinds, log, run_ids=ids[out])
        panel = {
            "x": plotting.axis(ax, "x", name, ctx.spec.parameter(name).units, log=log),
            "y": plotting.axis(ax, "y", p, ctx.prediction.units),
            "points": plotting.card_points(ids[usable], x=x[usable], y=y[usable]),
            "not_usable": strip,
        }
        return (plotting.save(fig, {"panels": [panel]}, out_dir, "toy", f"{p} against {name}."),)


class NoFigures:
    """A diagnostic with its figures left out: for the checks about numbers and notes, which don't read the figures
    (a PNG costs about 0.1 s). Every other attribute is the diagnostic's own."""

    def __init__(self, diagnostic: Any) -> None:
        self._diagnostic = diagnostic

    def __getattr__(self, name: str) -> Any:
        return getattr(self._diagnostic, name)

    def figures(self, *args: Any, **kwargs: Any) -> tuple[Figure, ...]:
        return ()


def read_only_at_offset(values: np.ndarray, offset: int, keep: list[Any]) -> np.ndarray:
    """``at_offset``'s copy, made read-only through its whole chain of bases, so the types keep it where it is
    (``RunColumns`` copies a writable view, record 0070)."""
    from tests.support.numerics import at_offset

    out = at_offset(np.asarray(values), offset, keep)
    chain = [out]
    while isinstance(chain[-1].base, np.ndarray):
        chain.append(chain[-1].base)
    for array in chain:
        array.flags.writeable = False
    return out


def batch_at_offset(run_batch: RunBatch, offset: int, keep: list[Any]) -> RunBatch:
    """The same run batch with its points, replicates, and values at ``offset`` bytes past a 64-byte boundary."""
    runs, design = run_batch.runs, run_batch.design
    placed = Design(
        identity=design.identity,
        points=read_only_at_offset(design.points, offset, keep),
        replicates=read_only_at_offset(design.replicates, offset, keep),
        levels=design.levels,
        lines=design.lines,
    )
    columns = dataclasses.replace(
        runs,
        points=None if runs.points is None else read_only_at_offset(runs.points, offset, keep),
        values={k: read_only_at_offset(v, offset, keep) for k, v in runs.values.items()},
    )
    return RunBatch(design=placed, runs=columns, new=run_batch.new)
