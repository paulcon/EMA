"""The reference models' functions, run in the test's process on a generator's design (until the workspace's step).

roadmap step 09: until step 14, the diagnostics' known-answer tests build run batches from a reference model's
function on the generator's design, as the contract does. ``model(id)`` loads a reference model's spec
(``load_spec``: its model version id as the workspace would compute it); ``prepare`` makes the request, design, and
context; ``batch`` calls the function at each design row: an exception is a failed run (``error``), a call past the
spec's ``timeout_s`` a failed run (``timeout``, stopped by an interval timer), and a non-finite value a missing
model prediction. R8, a program, runs through the runner (step 11).
"""

from __future__ import annotations

import importlib.util
import math
import signal
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from ema import reference_models
from ema.designs import generators
from ema.diagnostics import base
from ema.diagnostics.base import AnalysisContext
from ema.models.spec import LoadedModel, load_spec
from ema.numerics import intervals
from ema.types.design import Design
from ema.types.identity import ID_DTYPE
from ema.types.results import MeasuredNoisy
from ema.types.runs import FailureKind, RunBatch, RunColumns, RunKey, RunStatus
from tests.support.diagnostics import APPROVAL, Case


def model(id: str) -> LoadedModel:
    """Load a reference model's spec, as ``load_model`` would."""
    return load_spec(reference_models.path(id))


def function(id: str) -> Callable[..., Any]:
    """Import a reference model's Python function from its file (never for R8, a program)."""
    loaded = model(id)
    file, _, name = loaded.spec.interface.function.partition(":")  # type: ignore[union-attr]
    path = Path(loaded.model_dir) / file
    spec = importlib.util.spec_from_file_location(f"reference_{id.lower()}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


def prepare(
    diagnostic: Any,
    id: str,
    *,
    space: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
    prediction: str | None = None,
    measured_noisy: Sequence[MeasuredNoisy] = (),
) -> Case:
    """The request (the reference space unless given; none for the point run), the design, and the context."""
    loaded = model(id)
    if diagnostic.takes_space and space is None:
        space = reference_models.space(id)
    request = base.make_request(diagnostic, loaded.spec, space, prediction, dict(params or {}))
    parsed = base.request_space(request, loaded.spec)
    ident = diagnostic.design_identity(
        parsed if diagnostic.takes_space else None, request.params, loaded.spec, loaded.model_version_id
    )
    design = generators.get(ident.kind).build(ident, loaded.spec)
    method = None if diagnostic.interval_method is None else intervals.get(diagnostic.interval_method)
    ctx = AnalysisContext(request, loaded.spec, parsed, method, tuple(measured_noisy), None)
    return Case(diagnostic, loaded.spec, request, ident, design, ctx, loaded.model_version_id)


class _Timeout(Exception):
    pass


def _call(fn: Callable[..., Any], x: dict[str, float], timeout_s: float) -> Any:
    def stop(signum: int, frame: Any) -> None:
        raise _Timeout

    previous = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        return fn(**x)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def batch(case: Case, id: str, *, design: Design | None = None, fn: Callable[..., Any] | None = None) -> RunBatch:
    """Run a reference model's function at each design row (a repeated point is called again), in design order."""
    design = design or case.design
    fn = fn or function(id)
    spec = case.spec
    names = [p.name for p in spec.parameters]
    predictions = [p.name for p in spec.predictions]
    n = len(design)
    values = {p: np.full(n, np.nan) for p in predictions}
    status = np.full(n, RunStatus.OK.code)
    kind = np.full(n, -1)
    ids, reasons = [], {}
    missing: dict[str, dict[str, str]] = {p: {} for p in predictions}
    for i in range(n):
        run_id = RunKey.make(case.model_version_id, design.points[i], int(design.replicates[i]), 0).run_id
        ids.append(run_id)
        x = dict(zip(names, (float(v) for v in design.points[i]), strict=True))
        try:
            out = _call(fn, x, spec.timeout_s)
        except _Timeout:
            status[i], kind[i] = RunStatus.FAILED.code, FailureKind.TIMEOUT.code
            reasons[run_id] = f"timeout after {spec.timeout_s:g} s"
            continue
        except Exception as error:  # noqa: BLE001  # a model's exception is a failed run (M1)
            status[i], kind[i] = RunStatus.FAILED.code, FailureKind.ERROR.code
            reasons[run_id] = f"{type(error).__name__}: {error}"
            continue
        read = out if isinstance(out, Mapping) else {predictions[0]: out}
        for p in predictions:
            value = read.get(p)
            if value is not None and math.isfinite(float(value)):
                values[p][i] = float(value)
            else:
                missing[p][run_id] = f"{p} is not a finite number" if p in read else f"{p} is not returned"
        if all(math.isnan(values[p][i]) for p in predictions):
            status[i], kind[i] = RunStatus.FAILED.code, FailureKind.UNREAD.code
            reasons[run_id] = "no model prediction read"
            for p in predictions:
                missing[p].pop(run_id, None)
    runs = RunColumns(
        run_ids=ids,
        points=np.array(design.points),
        replicates=np.array(design.replicates),
        status=status,
        kind=kind,
        values=values,
        reasons=reasons,
        stderr_tails={},
        missing=missing,
        time_s=np.zeros(n),
        host=np.array(["here"] * n),
        program=np.array(["python"] * n),
        batch_call_ids=np.zeros(n, dtype=ID_DTYPE),
        approval_ids=[APPROVAL] * n,
    )
    return RunBatch(design=design, runs=runs, new=np.zeros(n, dtype=bool))
