"""The order of one diagnostic evaluation, the test run, and a result's directory (architecture.md §7).

Steps 1-9 of "One diagnostic evaluation, in order": the model's current loading and files (U6, M16), the request
(G15, M6), the design (G5), resolving it (Q1), a repeated request (C50, I7), the run lock, the price, the approval,
and the new runs (P3, W3, C48, C49), the batch in design order (C56), the analysis, the report, and W5 (C51). The
test run follows steps 1, 4, and 6 for one point (0049). A result's directory missing from the store is rebuilt from
it (data_model.md §6). Records 0054, 0055, 0063, 0072, 0074, 0075, 0080.
"""

import dataclasses
import os
import shutil
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from ema.approval import _fenced, ask_approval
from ema.designs import generators
from ema.designs.generators import MAX_DESIGN_POINTS
from ema.diagnostics import base
from ema.diagnostics.base import AnalysisContext, Diagnostic
from ema.models.files import check_files
from ema.models.processes import ModelProcesses
from ema.models.spec import LoadedModel, stored_model
from ema.numerics import intervals
from ema.report.render import render
from ema.runner import price as price_runs
from ema.runner import read_batch, replay_batch, resolve, run_new
from ema.store import Store
from ema.types.design import Design
from ema.types.errors import CannotAsk, DesignTooLarge, NotFound
from ema.types.identity import ID_DTYPE, reuse_key, sha256_hex
from ema.types.model import ModelSpec
from ema.types.requests import Approver, Progress, Request, TestRunRequest
from ema.types.results import DiagnosticResult, MeasuredNoisy, Provenance
from ema.types.runs import FailureKind, Price, Resolution, Run, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace
from ema.types.summaries import RunInfo
from ema.types.text import fmt

_CANNOT_ASK = "nobody can be asked to approve new runs: nothing was asked, and no run made (P3)"


@dataclasses.dataclass(frozen=True)
class Prepared:
    """Steps 1-3: the model as loaded, its model version's spec, the diagnostic, the request, its space, the design."""

    model: LoadedModel
    spec: ModelSpec
    diagnostic: Diagnostic
    request: Request
    space: ModelParameterSpace
    design: Design


def loaded(store: Store, name: str) -> tuple[LoadedModel, ModelSpec]:
    """Return a model name's current loading as a loaded model (Q3, Q14; 0054), and its model version's spec.

    The runs use the stored spec with the loading's settings (``keep``, ``batch_size``, ``timeout_s``); the
    analysis and the report use the model version's spec as stored, so a rebuild or a replay from the store reads
    the same spec (P1, S10).

    Raises
    ------
    NotFound
        When no model of that name is loaded, naming the models there are.
    """
    loading = store.current_loading(name)
    if loading is None:
        names = ", ".join(store.model_names()) or "none yet: load_model loads one"
        raise NotFound(f"no model {name!r} is loaded; the models are {names}")
    version = store.model_version(loading.model_version_id)
    spec = dataclasses.replace(
        version.spec, keep=loading.keep, batch_size=loading.batch_size, timeout_s=loading.timeout_s
    )
    return stored_model(spec, version.files, loading.spec_path), version.spec


def prepare(
    store: Store,
    model: str,
    diagnostic: str,
    space: Mapping[str, Any] | ModelParameterSpace | None,
    prediction: str | None,
    params: Mapping[str, Any],
) -> Prepared:
    """Prepare steps 1-3: the model and its files checked (U6, M16), the request (G15, M6), the design (G5).

    Raises
    ------
    NotFound
        For a model or diagnostic that isn't there.
    ModelChanged
        When a tracked file changed since loading, naming it.
    RequestError
        For a space or a diagnostic parameter refused; ``DesignTooLarge`` over the cap (G5).
    """
    loaded_model, spec = loaded(store, model)
    check_files(loaded_model)
    d = base.get(diagnostic)
    request = base.make_request(d, spec, space, prediction, params)
    parsed = base.request_space(request, spec)
    identity = d.design_identity(parsed if d.takes_space else None, request.params, spec, loaded_model.model_version_id)
    generator = generators.get(identity.kind)
    size = generator.size(identity, spec)
    if size > MAX_DESIGN_POINTS:
        raise DesignTooLarge(f"the design has {size:,} points, over the cap of {MAX_DESIGN_POINTS:,} (G5)")
    return Prepared(loaded_model, spec, d, request, parsed, generator.build(identity, spec))


def row_run_ids(resolution: Resolution) -> np.ndarray:
    """Each design row's run id: its stored run's, or its new key's, through ``row_keys`` (step 7; C56)."""
    ids = np.array(resolution.row_runs, dtype=ID_DTYPE)
    new = np.flatnonzero(resolution.row_keys >= 0)
    if len(new):
        keys = np.array([bytes.fromhex(k.run_id) for k in resolution.new_keys], dtype=ID_DTYPE)
        ids[new] = keys[resolution.row_keys[new]]
    return ids


def make_runs(
    store: Store,
    processes: ModelProcesses,
    model: LoadedModel,
    design: Design,
    *,
    asked_for: str,
    request: Request | TestRunRequest,
    retry_failed: bool,
    approve: Approver | None,
    on_progress: Callable[[Progress], None] | None,
) -> tuple[Resolution, str | None]:
    """Make steps 4 and 6: resolve the design; with new keys, take the run lock, resolve again, price, ask, and run.

    Returns the latest resolution and the approval id, None when no new run was asked for (C50). The lock is held
    while the approval waits for its answer: one process makes runs at a time (data_model.md §10).

    Raises
    ------
    CannotAsk
        With new runs and ``approve=None``, before the lock: nothing asked or recorded.
    ApprovalDeclined
        On a no: no runs made.
    WorkspaceBusy
        When another process holds the run lock.
    """
    resolution = resolve(design, model, store, retry_failed=retry_failed)
    if not resolution.new_keys:
        return resolution, None
    if approve is None:
        raise CannotAsk(_CANNOT_ASK)
    with store.run_lock():
        resolution = resolve(design, model, store, retry_failed=retry_failed)
        if not resolution.new_keys:
            return resolution, None
        price = price_runs(resolution, store)
        approval = ask_approval(
            store=store,
            model=model,
            asked_for=asked_for,
            request=request,
            design=design.identity,
            resolution=resolution,
            price=price,
            approve=approve,
        )
        run_new(model, resolution, approval, store, processes, on_progress=on_progress)
    return resolution, approval


def price(store: Store, prepared: Prepared, *, retry_failed: bool) -> Price:
    """Price a prepared diagnostic evaluation (Q1, Q2; P3): no lock, nothing written."""
    resolution = resolve(prepared.design, prepared.model, store, retry_failed=retry_failed)
    return price_runs(resolution, store)


def context(
    request: Request,
    spec: ModelSpec,
    measured_noisy: tuple[MeasuredNoisy, ...],
    on_progress: Callable[[Progress], None] | None,
) -> AnalysisContext:
    """Return the analysis's context: the request's space, the diagnostic's interval method from its registry (C19)."""
    name = base.get(request.diagnostic).interval_method
    method = None if name is None else intervals.get(name)
    return AnalysisContext(request, spec, base.request_space(request, spec), method, measured_noisy, on_progress)


def write_report(directory: str, result: DiagnosticResult, spec: ModelSpec) -> str:
    """Write ``report.md`` into a result's directory (S1-S4); a pure function of the result and spec (P1)."""
    path = os.path.join(directory, "report.md")
    with open(path, "wb") as f:
        f.write(render(result, spec).encode("utf-8"))
    return path


def run(
    store: Store,
    processes: ModelProcesses,
    prepared: Prepared,
    *,
    retry_failed: bool,
    approve: Approver | None,
    on_progress: Callable[[Progress], None] | None,
) -> DiagnosticResult:
    """Run steps 4-9 of one diagnostic evaluation (architecture.md §7): its result, stored, or the stored one (C50)."""
    p = prepared
    resolution, approval = make_runs(
        store, processes, p.model, p.design, asked_for="diagnostic_evaluation", request=p.request,
        retry_failed=retry_failed, approve=approve, on_progress=on_progress,
    )  # fmt: skip
    mv = p.model.model_version_id
    run_ids = row_run_ids(resolution)
    versions = base.library_versions()
    result_id = sha256_hex(reuse_key(mv, p.request, run_ids, versions))
    if approval is None:
        found = store.find_result(result_id)
        if found is not None:  # a repeated request: nothing computed, written, or asked (C50, I7)
            return found
    batch = read_batch(p.design, run_ids, store, new_approval=approval)
    ctx = context(p.request, p.spec, store.measured_noisy(mv, p.request.prediction), on_progress)
    provenance = base.make_provenance(batch, ctx, p.diagnostic, mv, approval_id=approval, versions=versions)
    with store.result_directory(result_id) as directory:
        result = base.evaluate(p.diagnostic, batch, ctx, provenance, result_id, directory)
        write_report(directory, result, p.spec)
    return store.record_result(result)


def test_run(store: Store, processes: ModelProcesses, model: LoadedModel, *, approve: Approver | None) -> Run:
    """The test run at the nominal point, replicate 0 (0049): priced and approved like any new run; stored, no question.

    Its design has one row and no identity; its approval has no design (W3).
    """
    point = tuple(p.nominal for p in model.spec.parameters)
    design = Design(None, np.array([point], dtype=np.float64), np.zeros(1, dtype=np.int64), None, None)
    resolution, _ = make_runs(
        store, processes, model, design, asked_for="test_run", request=TestRunRequest(point), retry_failed=False,
        approve=approve, on_progress=None,
    )  # fmt: skip
    return store.get_run(bytes(row_run_ids(resolution)[0]).hex())


def shown(store: Store, result: DiagnosticResult) -> DiagnosticResult:
    """Set a result's ``shown``: its short id and EMA's text (architecture.md §7, What is shown; Q8, Q11)."""
    for summary in store.list_results(
        model_version_id=result.model_version_id, diagnostic=result.diagnostic, prediction=result.prediction
    ):
        if summary.result_id == result.result_id:
            object.__setattr__(result, "shown", summary)  # not stored, not compared (§3)
            break
    return result


def result_directory(store: Store, result: DiagnosticResult) -> str:
    """Return a stored result's directory, rebuilt from the store when a file of it is missing (data_model.md §6).

    The report and the data cards are rebuilt byte-identical (P1, S10): the figures are drawn again from the stored
    result and its stored runs, replayed from its provenance (U8), and the report rendered from the result and its
    model version's spec.
    """
    directory = store.layout.result_dir(result.result_id)
    names = ["report.md", *(f.png for f in result.figures), *(f.card for f in result.figures)]
    if all(os.path.isfile(os.path.join(directory, n)) for n in names):
        return directory
    if os.path.lexists(directory):  # incomplete: rebuilt whole, as the store keeps a directory that has a row
        shutil.rmtree(directory)
    spec = store.model_version(result.model_version_id).spec
    prov = result.provenance
    batch = replay_batch(prov, store)
    ctx = context(prov.request, spec, prov.measured_noisy_read, None)
    with store.result_directory(result.result_id) as tmp:
        base.get(result.diagnostic).figures(batch, dataclasses.replace(result, figures=()), ctx, tmp)
        write_report(tmp, result, spec)
    return directory


def replay(store: Store, provenance: Provenance, result_id: str, directory: str) -> tuple[DiagnosticResult, RunBatch]:
    """Recompute a result from its provenance and the stored runs into ``directory``, writing no record (U8, 0055).

    Returns the replayed result and its batch, whose design is built from the stored points (0062, 0063).
    """
    spec = store.model_version(provenance.model_version_id).spec
    batch = replay_batch(provenance, store)
    ctx = context(provenance.request, spec, provenance.measured_noisy_read, None)
    result = base.evaluate(base.get(provenance.request.diagnostic), batch, ctx, provenance, result_id, directory)
    write_report(directory, result, spec)
    return result, batch


# --------------------------------------------------------------------------------------------------------------
# What a run shows (U3, 0020, 0061; trust.md, Model output and the MCP client)


def run_info(
    store: Store,
    spec: ModelSpec,
    *,
    run_id: str,
    row: int | None,
    point: tuple[float, ...],
    replicate: int,
    status: RunStatus,
    kind: FailureKind | None,
    reason: str | None,
    stderr_tail: str | None,
    predictions: Mapping[str, float | None],
    batch_call_id: str | None,
) -> RunInfo:
    """Describe one run with EMA's text: its status, values or reason, point, and kept directories (U3; 0020).

    Numbers by ``fmt`` (S3); the reason and the stderr tail are the model's own output, quoted (trust.md).
    """
    layout = store.layout
    run_dir = layout.run_dir(run_id)
    batch_dir = None if batch_call_id is None else layout.run_dir(batch_call_id)
    short = store.short("run", run_id)
    where = (
        f"Run {short}"
        + ("" if row is None else f", row {row}")
        + ("" if replicate == 0 else f", replicate {replicate}")
    )
    if status is RunStatus.OK:
        values = [f"{n} = {fmt(v)}" if v is not None else f"{n} missing" for n, v in predictions.items()]
        line = f"{where}: ok; {', '.join(values)}"
        if reason:
            line += f" ({reason})"
    else:
        line = f"{where}: failed ({kind.value if kind else 'error'}): {reason}"
    line += f"; at {', '.join(f'{p.name} = {fmt(v)}' for p, v in zip(spec.parameters, point, strict=True))}"
    kept = run_dir if os.path.isdir(run_dir) else None
    if kept:
        line += f"; run directory: {kept}"
    lines = [line]
    if stderr_tail:
        lines += ["Its stderr's last lines (the model's own output, quoted):", _fenced(stderr_tail)]
    return RunInfo(
        run_id=run_id,
        short_id=short,
        row=row,
        point={p.name: v for p, v in zip(spec.parameters, point, strict=True)},
        replicate=replicate,
        status=status,
        kind=kind,
        reason=reason,
        stderr_tail=stderr_tail,
        predictions=dict(predictions),
        run_dir=kept,
        batch_dir=batch_dir if batch_dir is not None and os.path.isdir(batch_dir) else None,
        text="\n".join(lines),
    )


def info_of(store: Store, spec: ModelSpec, run: Run, row: int | None = None, prediction: str | None = None) -> RunInfo:
    """Describe a stored run (Q9); with ``prediction``, an ok run's reason is why that one is missing."""
    missing = [f"{n}: {r}" for n, r in run.missing.items() if prediction in (None, n)]
    reason = run.reason if run.status is RunStatus.FAILED else ("; ".join(missing) or None)
    return run_info(
        store, spec, run_id=run.run_id, row=row, point=run.point, replicate=run.replicate, status=run.status,
        kind=run.kind, reason=reason, stderr_tail=run.stderr_tail, predictions=run.predictions,
        batch_call_id=run.batch_call_id,
    )  # fmt: skip
