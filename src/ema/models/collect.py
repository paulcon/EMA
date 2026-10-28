"""Collect a call's runs: model predictions from files only, status and kind, and each run's ``run.json`` (M19).

A command-line model's model predictions come from its output parsers, a Python function's from the
``predictions.json`` its call wrote (model_interface.md, A run; M13; 0028); each is read only from inside the run
directory (trust.md, T9). A run is ``ok`` when its call finished cleanly and read at least one model prediction;
else ``failed``, kind ``error`` (it raised, crashed, exited nonzero or by a signal, couldn't start, or EMA couldn't
write its own file), ``timeout``, or ``unread`` (model_interface.md, Failures; M4, M12; 0043). Nothing here raises
for a point (M1). ``keep_or_remove`` applies the spec's ``keep`` setting after the runs are
stored, and ``discard`` deletes a stopped call's directories (0020, 0028; M14).
"""

import functools
import json
import math
import os
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from ema.models.files import remove_tree, write_own
from ema.models.parsers import read, read_inside
from ema.models.prepare import PreparedCall
from ema.models.sandbox import describe_exit
from ema.models.spec import LoadedModel
from ema.types.identity import batch_call_id
from ema.types.model import CommandLine, Keep, PythonFunction
from ema.types.runs import FailureKind, Run, RunKey, RunStatus

if TYPE_CHECKING:  # never at run time: only ema.runner imports the execute phase (AR4)
    from ema.models.execute import ExecutedCall

#: Lines of stderr, or of the traceback, kept with a failed run (model_interface.md, Failures).
STDERR_TAIL_LINES = 15
#: Bytes read from the end of ``stderr.txt`` for its tail.
_TAIL_BYTES = 1 << 16
#: Characters of a reason kept on its one line.
_REASON_CHARS = 500


def _one_line(text: str) -> str:
    line = " ".join(text.split())
    return line if len(line) <= _REASON_CHARS else line[: _REASON_CHARS - 1] + "…"


def stderr_tail(call_dir: str) -> str | None:
    """Return the last 15 lines of a call's ``stderr.txt``, read only inside its directory; None when it has none."""
    path = os.path.join(call_dir, "stderr.txt")
    data, _ = read_inside(call_dir, "stderr.txt", _TAIL_BYTES) if os.path.lexists(path) else (None, None)
    if not data:
        return None
    lines = data.decode("utf-8", errors="replace").rstrip().splitlines()[-STDERR_TAIL_LINES:]
    return "\n".join(lines) or None


def _failure(call: "ExecutedCall", spec_command: bool) -> tuple[FailureKind, str] | None:
    if call.timed_out:
        return FailureKind.TIMEOUT, f"timeout after {call.prepared.timeout_s:g} s"
    if call.error is not None:
        return FailureKind.ERROR, _one_line(call.error)
    if spec_command and call.exit_code not in (0, None):
        assert call.exit_code is not None
        return FailureKind.ERROR, describe_exit(call.exit_code, "")
    return None


def _from_predictions_file(run_dir: str, names: Sequence[str]) -> tuple[dict[str, float], dict[str, str]] | str:
    """Read a Python function's ``predictions.json`` (M13, 0028), or say why it can't be read."""
    data, reason = read_inside(run_dir, "predictions.json")
    if data is None:
        return f"predictions.json: couldn't be read ({reason})"
    try:  # an integer read as a double, so one beyond a double's range is infinite, not an error (M1)
        content = json.loads(data, parse_int=float)
    except (ValueError, RecursionError):
        content = None
    values = content.get("predictions") if isinstance(content, dict) else None
    missing = content.get("missing") if isinstance(content, dict) else None
    if not isinstance(values, dict) or not isinstance(missing, dict):
        return "predictions.json: not EMA's model predictions"
    read_: dict[str, float] = {}
    why: dict[str, str] = {}
    for name in names:
        value = values.get(name)
        if isinstance(value, float) and math.isfinite(value):
            read_[name] = value
        elif name in values:
            why[name] = "predictions.json: not a finite number"
        else:
            reason = missing.get(name)
            why[name] = _one_line(reason) if isinstance(reason, str) and reason else "not in predictions.json"
    return read_, why


def _read(model: LoadedModel, run_dir: str) -> tuple[dict[str, float], dict[str, str]] | str:
    names = [p.name for p in model.spec.predictions]
    if isinstance(model.spec.interface, PythonFunction):
        return _from_predictions_file(run_dir, names)
    read_: dict[str, float] = {}
    why: dict[str, str] = {}
    for prediction in model.spec.predictions:
        assert prediction.parser is not None
        value, reason = read(prediction.parser, run_dir)
        if value is None:
            why[prediction.name] = _one_line(reason or "not read")
        else:
            read_[prediction.name] = value
    return read_, why


def _record(run: Run, call: "ExecutedCall", model: LoadedModel) -> bytes:
    names = [p.name for p in model.spec.parameters]
    interface = model.spec.interface
    record: dict[str, Any] = {
        "run_id": run.run_id, "model_version_id": run.model_version_id,
        "point": dict(zip(names, run.point, strict=True)), "replicate": run.replicate, "attempt": run.attempt,
        "status": run.status.value, "kind": None if run.kind is None else run.kind.value, "reason": run.reason,
        "stderr_tail": run.stderr_tail, "exit_code": run.exit_code, "predictions": dict(run.predictions),
        "missing": dict(run.missing), "time_s": run.time_s, "batch_call_id": run.batch_call_id, "host": run.host,
        "program": run.program, "approval_id": run.approval_id,
        "command": list(interface.command) if isinstance(interface, CommandLine) else None,
        "function": interface.function if isinstance(interface, PythonFunction) else None,
        "call_dir": call.prepared.call_dir,
    }  # fmt: skip
    return (json.dumps(record, indent=2, allow_nan=False) + "\n").encode()


def _make_run(
    model: LoadedModel,
    call: "ExecutedCall",
    key: RunKey,
    failed: tuple[FailureKind, str] | None,
    read_: Mapping[str, float],
    why: Mapping[str, str],
    tail: str | None,
    batch_id: str | None,
) -> Run:
    ok = failed is None
    return Run(
        run_id=key.run_id, model_version_id=model.model_version_id, point=key.point, replicate=key.replicate,
        attempt=key.attempt, status=RunStatus.OK if ok else RunStatus.FAILED,
        kind=None if failed is None else failed[0], reason=None if failed is None else failed[1],
        stderr_tail=None if ok else tail, exit_code=call.exit_code,
        predictions={p.name: read_.get(p.name) for p in model.spec.predictions} if ok else {},
        missing=dict(why) if ok else {}, time_s=call.time_s / len(call.prepared.keys), batch_call_id=batch_id,
        host=call.host, program=call.program, approval_id=call.prepared.approval_id,
    )  # fmt: skip


def collect(model: LoadedModel, call: "ExecutedCall") -> tuple[Run, ...]:
    """Read a call's runs, and write each one's ``run.json`` (M1, M4, M12, M13, M19; 0043).

    Parameters
    ----------
    model
        The loaded model.
    call
        The executed call.

    Returns
    -------
    tuple of Run
        One per key, in the call's order. Never raises for a point (M1): a run EMA couldn't write ``run.json`` for
        is failed, kind ``error``, "run.json: couldn't be written: ...".
    """
    prepared = call.prepared
    batch = isinstance(model.spec.interface, PythonFunction) and model.spec.interface.batch
    batch_id = batch_call_id([k.run_id for k in prepared.keys]) if batch else None
    failure = _failure(call, isinstance(model.spec.interface, CommandLine))
    tail = functools.cache(lambda: stderr_tail(prepared.call_dir))  # read once, for a failed run only
    runs = []
    for i, (key, run_dir) in enumerate(zip(prepared.keys, prepared.run_dirs, strict=True)):
        run_failure = failure
        read_: Mapping[str, float] = {}
        why: Mapping[str, str] = {}
        if run_failure is None and i < len(call.run_errors) and call.run_errors[i] is not None:
            run_failure = FailureKind.ERROR, _one_line(str(call.run_errors[i]))
        if run_failure is None:
            found = _read(model, run_dir)
            if isinstance(found, str):
                run_failure = FailureKind.ERROR, found
            else:
                read_, why = found
                if not read_:
                    reasons = "; ".join(f"{name}: {reason}" for name, reason in why.items())
                    run_failure = FailureKind.UNREAD, _one_line(f"no model prediction read ({reasons})")

        run_tail = None if run_failure is None else tail()
        run = _make_run(model, call, key, run_failure, read_, why, run_tail, batch_id)
        try:
            write_own(run_dir, "run.json", _record(run, call, model))
        except OSError as e:
            failed = FailureKind.ERROR, f"run.json: couldn't be written: {e.strerror}"
            run = _make_run(model, call, key, failed, {}, {}, tail(), batch_id)
        runs.append(run)
    return tuple(runs)


def kept(model: LoadedModel, run: Run) -> bool:
    """Tell whether ``keep`` keeps a run's directory (0020, 0028; M14).

    ``all``; ``incomplete``, a failed run's or one with a model prediction missing; or ``none``.
    """
    if model.spec.keep is Keep.ALL:
        return True
    if model.spec.keep is Keep.NONE:
        return False
    return run.status is RunStatus.FAILED or bool(run.missing)


def keep_or_remove(model: LoadedModel, call: PreparedCall, runs: Sequence[Run]) -> None:
    """Delete the run directories ``keep`` doesn't keep, after the runs are stored (I5, M14).

    Without following links; a batch directory goes with the last of its runs' directories (data_model.md §5.7).

    Parameters
    ----------
    model
        The loaded model, with its ``keep`` setting.
    call
        The prepared call.
    runs
        Its runs, from ``collect``.
    """
    keep = [kept(model, run) for run in runs]
    for run_dir, keeping in zip(call.run_dirs, keep, strict=True):
        if not keeping:
            remove_tree(run_dir)
    if call.call_dir not in call.run_dirs and not any(keep):
        remove_tree(call.call_dir)


def discard(call: PreparedCall) -> None:
    """Delete a stopped call's directories, without following links: a stopped run is not stored (0028; M14)."""
    for directory in (*call.run_dirs, call.call_dir):
        remove_tree(directory)
