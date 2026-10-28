"""``export``: a diagnostic result's runs, design, result, and report, for another tool (export.md, E1-E6).

Writes ``runs.csv`` (one row per design row, in design order, every number as ``%.17g``, a missing value an empty
cell), ``result.json`` (strict JSON: the format, the design, the model version's spec, the column dictionary, and
the result with its provenance, which ``DiagnosticResult.from_json`` reads back equal), and ``report/``, a copy of
the result's directory. A directory that isn't empty is refused before anything is written (E1;
records 0053, 0061).
"""

import csv
import json
import os
import shutil
from typing import Any

import numpy as np

from ema.report import to_pdf
from ema.store import Store
from ema.types.errors import PathRefused
from ema.types.identity import hex_ids
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult
from ema.types.runs import FailureKind, RunStatus
from ema.types.space import ModelParameterSpace
from ema.workspace import _evaluate

#: The export's format version (export.md, result.json's ``export_format``).
EXPORT_FORMAT = 1
#: EMA's columns, in order (E2); every name starts with ``ema_`` (M21).
EMA_COLUMNS = (
    ("ema_row", "the design row, from 0"),
    ("ema_run_id", "the run's id"),
    ("ema_replicate", "the replicate"),
    ("ema_status", "ok or failed"),
    ("ema_kind", "error, timeout, or unread; empty when ok"),
    ("ema_reason", "the one-line reason a run failed; empty when ok"),
    ("ema_new", "true when this result's own diagnostic evaluation made the run"),  # (E6)
    ("ema_time_s", "the run's time in seconds (a batch call's share)"),
    ("ema_run_dir", "the kept run directory; empty when not kept"),
    ("ema_host", "the host the run ran on"),
    ("ema_program", "the resolved program path"),
)
#: A failure kind's code to its name; an ok run's -1 has none.
_KINDS = {k.code: k.value for k in FailureKind}


def _number(x: float) -> str:
    """Write a double as ``%.17g``, which reads back bit for bit; a missing value (NaN) as an empty cell (E3)."""
    return "" if np.isnan(x) else f"{x:.17g}"


def _columns(spec: ModelSpec, space: ModelParameterSpace) -> dict[str, Any]:
    """Return the column dictionary (export.md): each column's kind, units, and description; a model parameter's range."""
    out: dict[str, Any] = {name: {"kind": "ema", "units": "", "description": text} for name, text in EMA_COLUMNS}
    for p in spec.parameters:
        entry: dict[str, Any] = {"kind": "model parameter", "units": p.units, "description": p.description}
        if p.name in space.ranges:
            r = space.ranges[p.name]
            entry.update(scale=r.scale.value, range=[r.lo, r.hi])
        else:
            entry["held"] = space.held.get(p.name, p.nominal)
        out[p.name] = entry
    for q in spec.predictions:
        out[q.name] = {"kind": "model prediction", "units": q.units, "description": q.description}
    out["ema_missing"] = {"kind": "ema", "units": "", "description": "each model prediction missing from an ok run, "
                          "with its reason, in the model spec's order"}  # fmt: skip
    return out


def export(store: Store, result: DiagnosticResult, directory: str, *, pdf: bool = False) -> str:
    """Write a result's export into a new or empty directory, and return its absolute path (E1-E6).

    With ``pdf``, the report's PDF is made first, beside the stored report (as ``report(pdf=True)`` makes it), so
    ``report/`` holds ``report.pdf`` too, and a PDF that can't be made leaves the directory untouched (0081 item 31).

    Raises
    ------
    PathRefused
        For a directory that isn't empty, or a path that is a file, naming it; nothing is written.
    PandocMissing, PdfFailed
        With ``pdf``, when the PDF can't be made; nothing is written.
    """
    target = os.path.abspath(directory)
    if os.path.lexists(target) and (not os.path.isdir(target) or os.listdir(target)):
        raise PathRefused(f"{target} isn't an empty directory: an export never overwrites a file")  # (E1)
    source = _evaluate.result_directory(store, result)
    if pdf:
        to_pdf(os.path.join(source, "report.md"))
    spec = store.model_version(result.model_version_id).spec
    runs = store.result_runs(result.result_id)
    assert runs.points is not None
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as error:  # a read-only or full file system, say: EMA's error, naming why (record 0080, n3)
        raise PathRefused(f"{target} can't be made: {error.strerror or error}; nothing exported") from None
    ids = hex_ids(runs.run_ids)
    approval = result.provenance.approval_id
    approvals = hex_ids(runs.approval_ids)
    names = [p.name for p in spec.predictions]
    header = [c for c, _ in EMA_COLUMNS] + [p.name for p in spec.parameters] + names + ["ema_missing"]
    with open(os.path.join(target, "runs.csv"), "x", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        for row, run_id in enumerate(ids):
            ok = int(runs.status[row]) == RunStatus.OK.code
            kind = int(runs.kind[row])
            run_dir = store.layout.run_dir(run_id)
            missing = [f"{n}: {runs.missing[n][run_id]}".replace(";", ",") for n in names
                       if ok and run_id in runs.missing.get(n, {})]  # fmt: skip
            writer.writerow([
                row, run_id, int(runs.replicates[row]), "ok" if ok else "failed",
                _KINDS.get(kind, ""), runs.reasons.get(run_id, ""),
                "true" if approval is not None and approvals[row] == approval else "false",
                _number(float(runs.time_s[row])), run_dir if os.path.isdir(run_dir) else "",
                str(runs.host[row]), str(runs.program[row]),
                *(_number(float(x)) for x in runs.points[row]),
                *(_number(float(runs.values[n][row])) for n in names),
                "; ".join(missing),
            ])  # fmt: skip
    space = ModelParameterSpace.parse(result.provenance.design.canonical()["space"])
    document = {
        "export_format": EXPORT_FORMAT,
        "design": dict(result.provenance.design.canonical()),
        "spec": json.loads(spec.versioned_json()),
        "columns": _columns(spec, space),
        "result": json.loads(result.to_json()),
    }
    with open(os.path.join(target, "result.json"), "x", encoding="utf-8") as f:
        f.write(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    shutil.copytree(source, os.path.join(target, "report"))
    return target
