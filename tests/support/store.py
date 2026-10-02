"""A small world for the store's tests (data_model.md; contracts.md, the store contract): a toy model version, its
approvals and runs, and diagnostic results whose ids are their reuse keys' hashes.

Nothing here runs a model: runs are built as ``collect`` would return them, with their keys computed by
``RunKey.make`` (data_model.md §3.4).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

import numpy as np

from ema.store import BatchCall, Store
from ema.types.design import DesignIdentity, DesignStructure
from ema.types.identity import TrackedFile, batch_call_id, id_array, reuse_key, sha256_hex
from ema.types.model import ModelSpec
from ema.types.requests import Request, TestRunRequest
from ema.types.results import Counts, DiagnosticResult, MeasuredNoisy, Note, Provenance
from ema.types.runs import FailureKind, Price, Run, RunKey, RunStatus

VERSIONS = {"ema": "2.0.0.dev0", "numpy": "2.3.1", "scipy": "1.16.0", "matplotlib": "3.10.0"}
SPEC_PATH = "/models/toy/model.json"


def spec(name: str = "toy", description: str = "A toy model.") -> ModelSpec:
    """A Python function's spec: model parameters a, b, and h; model predictions y and z."""
    return ModelSpec.from_json(
        f"""{{
      "name": "{name}", "description": "{description}", "interface": "python_function", "function": "model.py:f",
      "parameters": [
        {{"name": "a", "units": "m", "description": "a", "nominal": 1.0}},
        {{"name": "b", "units": "", "description": "b", "nominal": 0.0}},
        {{"name": "h", "units": "s", "description": "h", "nominal": 0.5}}
      ],
      "predictions": [
        {{"name": "y", "units": "K", "description": "y"}},
        {{"name": "z", "units": "K", "description": "z"}}
      ]
    }}"""
    )


FILES = (TrackedFile("model.py", "c0" * 32, False),)


@contextmanager
def opened(store_class: type[Store] = Store) -> Iterator[Store]:
    """A fresh workspace's store in a temporary directory, closed and removed afterwards."""
    with tempfile.TemporaryDirectory() as tmp:
        store = store_class.open(os.path.join(tmp, "ws"))
        try:
            yield store
        finally:
            store.close()


def load(store: Store, model: ModelSpec | None = None) -> str:
    """Record a loading of ``model`` (the toy by default); return its model version id."""
    return store.record_loading(model or spec(), SPEC_PATH, FILES)


def keys(mv: str, points: Sequence[Sequence[float]], replicate: int = 0, attempt: int = 0) -> list[RunKey]:
    return [RunKey.make(mv, p, replicate, attempt) for p in points]


def request(seed: int = 1, prediction: str = "y", diagnostic: str = "scatter") -> Request:
    return Request(diagnostic, prediction, {"a": [0.0, 2.0], "b": [-1.0, 1.0], "h": 0.5}, {"n": 3, "seed": seed})


def identity(mv: str, req: Request | None = None) -> DesignIdentity:
    req = req or request()
    assert req.space is not None
    return DesignIdentity(mv, "uniform", req.space, {"n": 3}, int(req.params["seed"]), "random", "1", "1")


def approve(
    store: Store,
    mv: str,
    new_keys: Sequence[RunKey],
    *,
    answer: bool = True,
    req: Request | TestRunRequest | None = None,
    reused: int = 0,
) -> str:
    """Record an approval of ``new_keys`` (answered ``answer``); return its id."""
    req = req or request()
    test_run = isinstance(req, TestRunRequest)
    time_s = None if reused == 0 else 0.25 * len(new_keys)
    price = Price.make(new=len(new_keys), reused=reused, time_s=time_s, from_runs=reused)
    return store.record_approval(
        model_version_id=mv,
        asked_for="test_run" if test_run else "diagnostic_evaluation",
        request=req,
        design=None if test_run else identity(mv, req),  # type: ignore[arg-type]
        price=price,
        question=f"Run {price.text}? [y/N]",
        answer=answer,
        points=new_keys,
    )


def ok_run(key: RunKey, mv: str, approval: str, *, y: float | None = 1.5, z: float | None = 2.5, **kw: Any) -> Run:
    """An ok run at ``key``; a model prediction given as None is missing, with a reason."""
    predictions = {"y": y, "z": z}
    missing = {name: f"out.txt: pattern not found for {name}" for name, v in predictions.items() if v is None}
    fields: dict[str, Any] = {
        "run_id": key.run_id,
        "model_version_id": mv,
        "point": key.point,
        "replicate": key.replicate,
        "attempt": key.attempt,
        "status": RunStatus.OK,
        "kind": None,
        "reason": None,
        "stderr_tail": None,
        "exit_code": None,
        "predictions": predictions,
        "missing": missing,
        "time_s": 0.25,
        "batch_call_id": None,
        "host": "host-1",
        "program": "/usr/bin/python3",
        "approval_id": approval,
    }
    fields.update(kw)
    return Run(**fields)


def failed_run(key: RunKey, mv: str, approval: str, *, kind: FailureKind = FailureKind.ERROR, **kw: Any) -> Run:
    fields: dict[str, Any] = {
        "status": RunStatus.FAILED,
        "kind": kind,
        "reason": "exited with code 2",
        "stderr_tail": "Traceback (most recent call last):\nValueError: bad",
        "exit_code": 2,
        "predictions": {},
        "missing": {},
        **kw,
    }
    return ok_run(key, mv, approval, **fields)


def record_runs(store: Store, runs: Sequence[Run]) -> None:
    """Record each run as a call of its own."""
    for run in runs:
        store.record_call([run])


def record_batch(store: Store, runs: Sequence[Run], time_s: float = 1.0) -> BatchCall:
    """Record ``runs`` as one batch call; return it."""
    call = BatchCall(batch_call_id([r.run_id for r in runs]), len(runs), time_s)
    store.record_call([replace(r, batch_call_id=call.batch_call_id) for r in runs], call)
    return call


def made(
    store: Store, mv: str, points: Sequence[Sequence[float]], *, replicate: int = 0, req: Request | None = None
) -> tuple[str, list[Run]]:
    """Approve (for ``req``, the default request by default) and make ok runs at ``points``; return the approval and
    the runs."""
    ks = keys(mv, points, replicate)
    approval = approve(store, mv, ks, req=req)
    runs = [ok_run(k, mv, approval, y=float(i), z=-float(i)) for i, k in enumerate(ks)]
    record_runs(store, runs)
    return approval, runs


def result(
    mv: str,
    runs_by_row: Sequence[Run],
    *,
    approval: str | None,
    req: Request | None = None,
    noisy: MeasuredNoisy | None = None,
    read: Sequence[MeasuredNoisy] = (),
    note: str = "a note",
    versions: dict[str, str] | None = None,
) -> DiagnosticResult:
    """A diagnostic result over ``runs_by_row`` (one run per design row), its id its reuse key's hash.

    New runs are those made under ``approval``; the counts are computed from the runs, for the request's model
    prediction.
    """
    req = req or request()
    versions = versions or VERSIONS
    run_ids = id_array([r.run_id for r in runs_by_row])
    rid = sha256_hex(reuse_key(mv, req, run_ids, versions))
    distinct = {r.run_id: r for r in runs_by_row}
    failed = {k: sum(r.kind is k for r in distinct.values()) for k in FailureKind}
    ok = [r for r in distinct.values() if r.status is RunStatus.OK]
    missing = sum(r.predictions.get(req.prediction) is None for r in ok)
    new = sum(r.approval_id == approval for r in distinct.values())
    counts = Counts(len(runs_by_row), len(distinct), new, len(distinct) - new, failed, missing, len(ok) - missing)
    if noisy is not None:
        noisy = replace(noisy, result_id=rid)
    provenance = Provenance(
        ema=versions["ema"],
        numpy=versions["numpy"],
        scipy=versions["scipy"],
        matplotlib=versions["matplotlib"],
        model_version_id=mv,
        request=req,
        design=identity(mv, req),
        run_ids=run_ids,
        approval_id=approval if new else None,
        spawn_tags=(3,),
        measured_noisy_read=tuple(read),
        design_structure=DesignStructure(levels=None, lines=None),
    )
    return DiagnosticResult(
        result_id=rid,
        diagnostic=req.diagnostic,
        title="Scatter",
        model_version_id=mv,
        prediction=req.prediction,
        counts=counts,
        header_rows=(),
        notes=(Note("too_few", note),),
        estimates=(),
        observations=(),
        figures=(),
        extra=(),
        measured_noisy=noisy,
        provenance=provenance,
    )


def noisy_record(mv: str, point: Sequence[float], *, std: float | None = 0.125, prediction: str = "y") -> MeasuredNoisy:
    """A point run's measured-noisy record, as the diagnostic makes it (no ``made_at``: W5 sets it)."""
    return MeasuredNoisy("00" * 32, mv, prediction, tuple(point), 4, std, None)


def store_result(store: Store, res: DiagnosticResult) -> DiagnosticResult:
    """Put the result's directory in place, then record it (data_model.md §6, W5)."""
    with store.result_directory(res.result_id) as directory:
        write_report(directory, f"# {res.title}\n")
    return store.record_result(res)


def write_report(directory: str, text: str) -> None:
    with open(os.path.join(directory, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)


def ids(runs: Sequence[Run]) -> np.ndarray:
    return id_array([r.run_id for r in runs])
