"""Diagnostic results built by hand, for the report's tests (record 0073): a spec, a request, a design identity, and
the result's tables, with a provenance that passes ``DiagnosticResult``'s cross-checks.

The tables follow the conventions ``ema.report`` reads (docs/plans/08-figures-and-reports.md, The API the
diagnostics call): an estimates table's columns are the row heading, then a value and an interval heading per
estimate of a row; an observations table's are the row heading, then one per observation of a row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ema.designs import generators, samplers
from ema.types.design import DesignIdentity, DesignStructure, Line
from ema.types.identity import id_array, sha256_hex
from ema.types.model import ModelParameter, ModelSpec, PredictionSpec, PythonFunction
from ema.types.requests import Request
from ema.types.results import (
    Counts,
    DiagnosticResult,
    Estimate,
    EstimateTable,
    Figure,
    IntervalInfo,
    MeasuredNoisy,
    Note,
    Observation,
    ObservationTable,
    Provenance,
)
from ema.types.runs import FailureKind
from ema.types.space import ModelParameterSpace


def make_spec(
    name: str,
    parameters: Sequence[tuple[str, str, float]],
    prediction: tuple[str, str, str] = ("y", "", ""),
) -> ModelSpec:
    """A Python-function spec: (name, units, nominal) per model parameter; the prediction's (name, units, description)."""
    return ModelSpec(
        name=name,
        description="a model built in the report's tests",
        interface=PythonFunction(function="model.py:f"),
        parameters=tuple(
            ModelParameter(n, units=u, description=f"model parameter {n}", nominal=v) for n, u, v in parameters
        ),
        predictions=(PredictionSpec(name=prediction[0], units=prediction[1], description=prediction[2]),),
    )


def run_ids(rows: int, runs: int) -> np.ndarray:
    """``rows`` run ids with ``runs`` distinct: the first ``runs`` distinct, then repeats of the first ones."""
    distinct = [sha256_hex(f"run {i}") for i in range(runs)]
    return id_array([distinct[i % runs] for i in range(rows)])


def settings(seed: int, distinct: str | None = None) -> dict[str, Any]:
    """The bootstrap's settings, as a diagnostic records them: the method's, the seed, and what is on distinct runs."""
    out: dict[str, Any] = {"resamples": 1000, "percentiles": [0.5, 99.5], "min_defined": 201, "seed": seed}
    if distinct is not None:
        out["distinct"] = distinct
    return out


def etable(
    key: str,
    columns: Sequence[str],
    rows: Sequence[tuple[Any, ...]],
    *,
    n_usable: int,
    seed: int,
    units: str = "",
    title: str | None = None,
    distinct: str | None = None,
    method: str = "bootstrap",
    undefined: Mapping[str, int] | None = None,
) -> EstimateTable:
    """An estimates table: each row is (label, value, lo, hi, value, lo, hi, ...); lo None gives "none"."""
    estimates = []
    for row in rows:
        label, cells = row[0], row[1:]
        for j in range(0, len(cells), 3):
            value, lo, hi = cells[j : j + 3]
            interval = None if lo is None else (lo, hi)
            reason = hi if lo is None else None
            estimates.append(
                Estimate(key=f"{key}_{j // 3}", label=label, value=value, interval=interval, reason=reason)
            )
    info = IntervalInfo(method=method, settings=settings(seed, distinct), n_usable=n_usable, undefined=undefined or {})
    return EstimateTable(key, title or columns[0], tuple(columns), tuple(estimates), units, info)


def otable(
    key: str, columns: Sequence[str], rows: Sequence[tuple[Any, ...]], *, title: str | None = None, units: str = ""
) -> ObservationTable:
    """An observations table: each row is (label, value, ...)."""
    out = []
    for row in rows:
        label, values = row[0], row[1:]
        out.append(
            tuple(Observation(key=f"{key}_{j}", label=label, value=v, units=units) for j, v in enumerate(values))
        )
    return ObservationTable(key, title or columns[0], tuple(columns), tuple(out))


def shared(n_usable: int, prediction: str, lo: float, hi: float, spread: float, units: str = "") -> ObservationTable:
    """The shared observations (shared.md, Observations; C10)."""
    title = f"Of the {n_usable} usable runs"
    rows = (
        (Observation("min", "Minimum", lo, units),),
        (Observation("max", "Maximum", hi, units),),
        (Observation("spread", "(max - min) / max|y|", spread, ""),),
    )
    return ObservationTable("shared", title, (title, prediction), rows)


def make_result(
    spec: ModelSpec,
    *,
    diagnostic: str,
    title: str,
    space: Mapping[str, Any] | None,
    params: Mapping[str, Any],
    kind: str,
    design_params: Mapping[str, Any],
    seed: int,
    rows: int,
    runs: int,
    new: int,
    usable: int,
    failed: Mapping[FailureKind, int] | None = None,
    missing: int = 0,
    sampler: str | None = None,
    header_rows: Sequence[tuple[str, str]] = (),
    notes: Sequence[Note] = (),
    estimates: Sequence[EstimateTable] = (),
    observations: Sequence[ObservationTable] = (),
    figures: Sequence[Figure] = (),
    levels: tuple[int, ...] | None = None,
    lines: tuple[Line, ...] | None = None,
    noisy: bool = False,
) -> DiagnosticResult:
    """A diagnostic result with a provenance that passes the result's cross-checks (record 0070 item 21)."""
    model_version_id = sha256_hex(f"model version {spec.name}")
    prediction = spec.predictions[0].name
    request = Request(diagnostic=diagnostic, prediction=prediction, space=space, params=dict(params))
    design_space = (
        ModelParameterSpace.parse(space).canonical()
        if space is not None
        else ModelParameterSpace.at_point(spec, design_params.get("x", {})).canonical()
    )
    identity = DesignIdentity(
        model_version_id=model_version_id,
        kind=kind,
        space=dict(design_space),
        params=dict(design_params),
        seed=seed,
        sampler=sampler,
        sampler_version=None if sampler is None else samplers.get(sampler).version,
        generator_version=generators.get(kind).version,
    )
    result_id = sha256_hex(f"result {spec.name} {diagnostic}")
    provenance = Provenance(
        ema="2.0.0",
        numpy="2.3.1",
        scipy="1.16.0",
        matplotlib="3.10.0",
        model_version_id=model_version_id,
        request=request,
        design=identity,
        run_ids=run_ids(rows, runs),
        approval_id=sha256_hex("approval") if new else None,
        spawn_tags=(),
        measured_noisy_read=(),
        design_structure=DesignStructure(levels=levels, lines=lines),
    )
    failed = dict(failed or {})
    counts = Counts(rows=rows, runs=runs, new=new, reused=runs - new, failed=failed, missing=missing, usable=usable)
    measured = None
    if noisy:
        point = tuple(p.nominal for p in spec.parameters)
        measured = MeasuredNoisy(result_id, model_version_id, prediction, point, runs, 0.039, None)
    return DiagnosticResult(
        result_id=result_id,
        diagnostic=diagnostic,
        title=title,
        model_version_id=model_version_id,
        prediction=prediction,
        counts=counts,
        header_rows=tuple(header_rows),
        notes=tuple(notes),
        estimates=tuple(estimates),
        observations=tuple(observations),
        figures=tuple(figures),
        extra=(),
        measured_noisy=measured,
        provenance=provenance,
    )
