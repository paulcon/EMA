"""A diagnostic result and its parts: estimates, observations, notes, figures, counts, and provenance.

architecture.md §3 (results.py); diagnostics/shared.md (S1–S4); uncertainty.md (an interval or "none" with its
reason, 0041); data_model.md §5.9, §5.11, §5.12; C17 and I11 (strict canonical JSON, every double exact); 0036,
0054, 0055, 0063; record 0070.

Numbers only (P2): a result holds full doubles and EMA's notes; ``ema.report`` writes them with ``fmt``.
"""

import dataclasses
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.types._values import finite_doubles, is_number
from ema.types.design import DesignIdentity, DesignStructure, Line, _freeze
from ema.types.identity import ID_DTYPE, canonical_json, hex_ids, id_array
from ema.types.requests import Request
from ema.types.runs import FailureKind
from ema.types.text import parse_timestamp, timestamp_text


def _finite(value: Any, what: str) -> float:
    if not is_number(value) or not math.isfinite(float(value)):
        raise ValueError(f"{what} must be a finite number, not {value!r}")
    return float(value)


def _count(value: Any, what: str) -> int:
    if not is_number(value) or float(value) != int(value) or int(value) < 0:
        raise ValueError(f"{what} must be an integer >= 0, not {value!r}")
    return int(value)


def _utc(when: datetime | None) -> datetime | None:
    """Return a stored timestamp's datetime: UTC, to the millisecond (data_model.md §3.2); refuse a naive one."""
    return None if when is None else parse_timestamp(timestamp_text(when))


@dataclass(frozen=True)
class Estimate:
    """A number whose spec gives it a variability interval (0004, 0041): its value, and its interval or "none".

    Attributes
    ----------
    key : str
        Stable, not shown: "mean", "std", "slope", "S_T" (C5).
    label : str
        The row's name: "E", "mean", "S_T,a".
    value : float
        A finite double; where a value can't be computed there is no estimate (uncertainty.md, Rules).
    interval : tuple of float or None
        The interval's ends, lo <= hi; None: "none" (0041).
    reason : str or None
        Why the interval is "none"; given exactly when it is.
    """

    key: str
    label: str
    value: float
    interval: tuple[float, float] | None
    reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _finite(self.value, f"estimate {self.label}"))
        if self.interval is None:
            if not self.reason:
                raise ValueError(f"estimate {self.label}: a 'none' interval needs its reason (0041)")
            return
        lo, hi = (_finite(v, f"estimate {self.label}'s interval") for v in self.interval)
        if lo > hi or self.reason is not None:
            raise ValueError(f"estimate {self.label}: an interval is [lo, hi] with lo <= hi, and no reason")
        object.__setattr__(self, "interval", (lo, hi))


@dataclass(frozen=True)
class IntervalInfo:
    """An estimates table's interval method and settings: the line under the table (S4; uncertainty.md).

    Attributes
    ----------
    method : str
        "bootstrap", or a fake's name (C19).
    settings : Mapping[str, Any]
        Resamples, percentiles, seed, distinct runs ...; JSON data. Read-only, nested values included.
    n_usable : int
        The usable runs the intervals are from.
    undefined : Mapping[str, int]
        Undefined resamples per estimate, when any (V4). Read-only.
    """

    method: str
    settings: Mapping[str, Any]
    n_usable: int
    undefined: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "settings", _freeze(self.settings))
        undefined = {k: _count(v, f"undefined resamples of {k}") for k, v in self.undefined.items()}
        object.__setattr__(self, "undefined", MappingProxyType(undefined))
        object.__setattr__(self, "n_usable", _count(self.n_usable, "n_usable"))


@dataclass(frozen=True)
class EstimateTable:
    """One table of estimates, all with one interval method (S4).

    Attributes
    ----------
    key : str
        Stable, not shown: "rank_correlation", "sobol_total" (C5).
    title : str
        Its title.
    columns : tuple of str
        Its column headings.
    estimates : tuple of Estimate
        Its rows.
    units : str
        The estimates' units; "" when dimensionless.
    interval : IntervalInfo
        The line under the table.
    """

    key: str
    title: str
    columns: tuple[str, ...]
    estimates: tuple[Estimate, ...]
    units: str
    interval: IntervalInfo

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "estimates", tuple(self.estimates))


@dataclass(frozen=True)
class Observation:
    """A number read or computed directly from the usable runs, with no interval (0034).

    Attributes
    ----------
    key : str
        Stable, not shown: "min", "max", "spread", "rate", "kind" (C5).
    label : str
        Its row's name.
    value : float or int or str
        A finite number (an integer kept as one), or a run's kind for the point run's rows.
    units : str
        Its units; "" when dimensionless.
    """

    key: str
    label: str
    value: float | int | str
    units: str

    def __post_init__(self) -> None:
        value = self.value
        if isinstance(value, str):
            return
        if isinstance(value, (int, np.integer)) and is_number(value):
            object.__setattr__(self, "value", int(value))
        else:
            object.__setattr__(self, "value", _finite(value, f"observation {self.label}"))


@dataclass(frozen=True)
class ObservationTable:
    """One table of observations; its title says what it is of: "Of the 200 usable runs" (0034).

    Attributes
    ----------
    key : str
        Stable, not shown: "shared", "line_rates".
    title : str
        Its title.
    columns : tuple of str
        Its column headings.
    rows : tuple of tuple of Observation
        Its rows.
    """

    key: str
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Observation, ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))


@dataclass(frozen=True)
class Note:
    """A caveat about the data (shared.md, Notes), rendered by EMA, numbers by ``fmt``.

    Attributes
    ----------
    code : str
        "not_usable", "reused_failed", "too_few", "all_failed", "no_usable", "constant", "measured_noisy", or a
        diagnostic's own.
    text : str
        The note.
    """

    code: str
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class Figure:
    """One figure: its PNG and data card, file names in the result's directory (shared.md, Figures).

    Attributes
    ----------
    name : str
        Its name.
    png : str
        The PNG's file name.
    card : str
        The data card's file name.
    caption : str
        Its caption.
    """

    name: str
    png: str
    card: str
    caption: str


@dataclass(frozen=True)
class Counts:
    """The header's runs (S2): rows, distinct runs, new and reused, failed by kind, missing, usable.

    Every failure kind is present (0 when none). New and reused runs add to the runs, and so do the failed, the
    missing, and the usable (record 0070).

    Attributes
    ----------
    rows : int
        The design's rows.
    runs : int
        Distinct runs.
    new : int
        Runs made by this diagnostic evaluation.
    reused : int
        Stored runs it reused.
    failed : Mapping[FailureKind, int]
        Failed runs by kind. Read-only.
    missing : int
        Ok runs missing this model prediction.
    usable : int
        Runs usable for this model prediction.
    """

    rows: int
    runs: int
    new: int
    reused: int
    failed: Mapping[FailureKind, int]
    missing: int
    usable: int

    def __post_init__(self) -> None:
        for name in ("rows", "runs", "new", "reused", "missing", "usable"):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        failed = {kind: _count(self.failed.get(kind, 0), f"failed {kind.value}") for kind in FailureKind}
        if set(self.failed) - set(FailureKind):
            raise ValueError(f"failed runs are counted by FailureKind: {list(self.failed)!r}")
        object.__setattr__(self, "failed", MappingProxyType(failed))
        if self.new + self.reused != self.runs or sum(failed.values()) + self.missing + self.usable != self.runs:
            raise ValueError(f"counts don't add up to the runs: {self!r}")
        if self.runs > self.rows:
            raise ValueError(f"more runs than design rows: {self.runs} > {self.rows}")


@dataclass(frozen=True)
class MeasuredNoisy:
    """One point run that measured a model version noisy in one model prediction (data_model.md §5.11).

    Attributes
    ----------
    result_id : str
        The point run's diagnostic result.
    model_version_id : str
        The model version.
    prediction : str
        The model prediction.
    point : tuple of float
        x.
    runs : int
        The runs at the point.
    std : float or None
        The standard deviation, ddof 1; None with one usable run.
    made_at : datetime or None
        Set by W5, read by Q10; UTC, to the millisecond.
    """

    result_id: str
    model_version_id: str
    prediction: str
    point: tuple[float, ...]
    runs: int
    std: float | None
    made_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", finite_doubles(self.point, "a measured-noisy point"))
        object.__setattr__(self, "runs", _count(self.runs, "runs"))
        if self.std is not None:
            object.__setattr__(self, "std", _finite(self.std, "std"))
        object.__setattr__(self, "made_at", _utc(self.made_at))


def _plain(x: Any) -> Any:
    """JSON data from a result's parts: tuples as lists, enums as values, timestamps as text, ids as hex."""
    if hasattr(x, "canonical"):
        return x.canonical()
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {f.name: _plain(getattr(x, f.name)) for f in dataclasses.fields(x) if f.name != "shown"}
    if isinstance(x, Enum):
        return x.value
    if isinstance(x, Mapping):
        return {(k.value if isinstance(k, Enum) else k): _plain(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [_plain(v) for v in x]
    if isinstance(x, datetime):
        return timestamp_text(x)
    if isinstance(x, np.ndarray):
        return list(hex_ids(x))
    return x


def _measured_noisy(d: Mapping[str, Any]) -> MeasuredNoisy:
    made_at = d["made_at"]
    return MeasuredNoisy(**{**d, "made_at": None if made_at is None else parse_timestamp(made_at)})


def _structure(d: Mapping[str, Any]) -> DesignStructure:
    levels, lines = d["levels"], d["lines"]
    return DesignStructure(
        levels=None if levels is None else tuple(int(n) for n in levels),
        lines=None if lines is None else tuple(Line(**line) for line in lines),
    )


@dataclass(frozen=True, eq=False)
class Provenance:
    """What a diagnostic result was computed from (P5; data_model.md §5.9): enough to replay it (0055, 0063).

    Equal when its canonical JSON is (it holds an array).

    Attributes
    ----------
    ema, numpy, scipy, matplotlib : str
        The versions.
    model_version_id : str
        The model version.
    request : Request
        The canonical request.
    design : DesignIdentity
        The design's identity.
    run_ids : numpy.ndarray
        ``(n,)`` of ``ID_DTYPE``: one per design row, in design order; hex text in JSON. Read-only.
    approval_id : str or None
        Its own new runs' approval (0054); None with no new runs.
    spawn_tags : tuple of int
        The diagnostic's spawn tags (0041).
    measured_noisy_read : tuple of MeasuredNoisy
        Each measured-noisy record read, newest first, in full.
    design_structure : DesignStructure
        The design's levels and lines, so a replay needs no generator (0063).
    """

    ema: str
    numpy: str
    scipy: str
    matplotlib: str
    model_version_id: str
    request: Request
    design: DesignIdentity
    run_ids: np.ndarray
    approval_id: str | None
    spawn_tags: tuple[int, ...]
    measured_noisy_read: tuple[MeasuredNoisy, ...]
    design_structure: DesignStructure

    def __post_init__(self) -> None:
        ids = self.run_ids
        if not (isinstance(ids, np.ndarray) and ids.dtype == ID_DTYPE):
            ids = id_array(list(ids))
        ids = np.asarray(ids).view()
        if ids.ndim != 1:
            raise ValueError(f"a provenance's run ids are (n,), not {ids.shape}")
        ids.flags.writeable = False
        object.__setattr__(self, "run_ids", ids)
        object.__setattr__(self, "spawn_tags", tuple(_count(t, "a spawn tag") for t in self.spawn_tags))
        object.__setattr__(self, "measured_noisy_read", tuple(self.measured_noisy_read))

    def canonical(self) -> Mapping[str, Any]:
        """Return every field as plain JSON data (data_model.md §5.12): ids as hex text, tuples as lists."""
        return {f.name: _plain(getattr(self, f.name)) for f in dataclasses.fields(self)}

    @classmethod
    def from_canonical(cls, form: Mapping[str, Any]) -> "Provenance":
        """Rebuild a provenance from ``canonical()``'s data (or its JSON, loaded)."""
        return cls(
            **{
                **form,
                "request": Request(**form["request"]),
                "design": DesignIdentity(**form["design"]),
                "spawn_tags": tuple(form["spawn_tags"]),
                "measured_noisy_read": tuple(_measured_noisy(m) for m in form["measured_noisy_read"]),
                "design_structure": _structure(form["design_structure"]),
            }
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Provenance):
            return NotImplemented
        return canonical_json(self.canonical()) == canonical_json(other.canonical())

    __hash__ = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ResultSummary:
    """A diagnostic result as a listing or a returned result shows it (§7): prints as its text.

    Attributes
    ----------
    result_id : str
        The result's id.
    short_id : str
        The shortest unique prefix (Q11).
    model_version : str
        The model version's label.
    diagnostic : str
        The diagnostic.
    prediction : str
        The model prediction.
    runs : int
        Distinct runs.
    failed : int
        Failed runs, of every kind.
    made_at : datetime
        When the result was stored.
    text : str
        "Diagnostic result 3f2a: scatter on beam@91c0…, T_max; 200 runs: 200 new, 0 reused, 0 failed; report: ema
        report 3f2a"; build it with ``make``.
    """

    result_id: str
    short_id: str
    model_version: str
    diagnostic: str
    prediction: str
    runs: int
    failed: int
    made_at: datetime
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "made_at", _utc(self.made_at))

    def __str__(self) -> str:
        return self.text

    @classmethod
    def make(
        cls, result: "DiagnosticResult", *, short_id: str, model_version: str, made_at: datetime
    ) -> "ResultSummary":
        """Summarize a result with EMA's text (architecture.md §7, What is shown)."""
        c = result.counts
        failed = sum(c.failed.values())
        text = (
            f"Diagnostic result {short_id}: {result.diagnostic} on {model_version}, {result.prediction}; "
            f"{c.runs} runs: {c.new} new, {c.reused} reused, {failed} failed; report: ema report {short_id}"
        )
        return cls(
            result.result_id,
            short_id,
            model_version,
            result.diagnostic,
            result.prediction,
            c.runs,
            failed,
            made_at,
            text,
        )


@dataclass(frozen=True, eq=False)
class DiagnosticResult:
    """What one diagnostic evaluation produced: numbers, notes, and figures, with its provenance (P2, P5).

    Refuses to be built with no estimate, observation, or note (0036), or with a provenance of another model
    version, diagnostic, model prediction, or number of rows. Equal when its ``to_json`` is (C17; I11). Prints as
    its ``shown`` text when the workspace set it.

    Attributes
    ----------
    result_id : str
        The SHA-256 of its reuse key (data_model.md §3.4).
    diagnostic : str
        The diagnostic's name.
    title : str
        The diagnostic's title, for the report's (S1).
    model_version_id : str
        The model version.
    prediction : str
        The model prediction analyzed.
    counts : Counts
        The header's runs (S2).
    header_rows : tuple of tuple of str
        The diagnostic's own header rows (S1): the polynomial model's Fit.
    notes : tuple of Note
        Its notes, in order.
    estimates : tuple of EstimateTable
        Its estimates.
    observations : tuple of ObservationTable
        Its observations (0034).
    figures : tuple of Figure
        Its figures.
    extra : tuple of EstimateTable
        Estimates kept in the result and its data cards, not the report: the polynomial model's coefficients
        (0041).
    measured_noisy : MeasuredNoisy or None
        The point run's record, when it measured variation (C52).
    provenance : Provenance
        Required (P5).
    shown : ResultSummary or None
        Set by the workspace when it returns the result; not stored, not compared, not in ``to_json``.
    """

    result_id: str
    diagnostic: str
    title: str
    model_version_id: str
    prediction: str
    counts: Counts
    header_rows: tuple[tuple[str, str], ...]
    notes: tuple[Note, ...]
    estimates: tuple[EstimateTable, ...]
    observations: tuple[ObservationTable, ...]
    figures: tuple[Figure, ...]
    extra: tuple[EstimateTable, ...]
    measured_noisy: MeasuredNoisy | None
    provenance: Provenance
    shown: ResultSummary | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "header_rows", tuple((str(a), str(b)) for a, b in self.header_rows))
        for name in ("notes", "estimates", "observations", "figures", "extra"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if not (self.estimates or self.observations or self.notes):
            raise ValueError("a diagnostic result holds an estimate, an observation, or a note (0036)")
        p = self.provenance
        if (p.model_version_id, p.request.diagnostic, p.request.prediction) != (
            self.model_version_id,
            self.diagnostic,
            self.prediction,
        ):
            raise ValueError("a result's provenance is of its own model version, diagnostic, and model prediction")
        if p.run_ids.shape[0] != self.counts.rows:
            raise ValueError(f"the provenance names {p.run_ids.shape[0]} runs for {self.counts.rows} design rows")

    def to_json(self) -> str:
        """Return the result as canonical strict JSON, its provenance included (C17, I11).

        Every double is written exactly; a "none" interval is null, with its reason (0041); ``shown`` is left out.
        """
        return canonical_json(_plain(self))

    @classmethod
    def from_json(cls, text: str) -> "DiagnosticResult":
        """Load a result written by ``to_json`` (or the ``result`` object of an export's ``result.json``, E5).

        Raises
        ------
        ValueError
            For text that isn't strict JSON, or isn't a diagnostic result.
        """

        def strict(constant: str) -> Any:
            raise ValueError(f"not strict JSON: {constant}")

        try:
            d = json.loads(text, parse_constant=strict)
            return cls(
                result_id=d["result_id"],
                diagnostic=d["diagnostic"],
                title=d["title"],
                model_version_id=d["model_version_id"],
                prediction=d["prediction"],
                counts=Counts(
                    **{**d["counts"], "failed": {FailureKind(k): v for k, v in d["counts"]["failed"].items()}}
                ),
                header_rows=tuple(tuple(row) for row in d["header_rows"]),
                notes=tuple(Note(**n) for n in d["notes"]),
                estimates=tuple(_estimate_table(t) for t in d["estimates"]),
                observations=tuple(_observation_table(t) for t in d["observations"]),
                figures=tuple(Figure(**f) for f in d["figures"]),
                extra=tuple(_estimate_table(t) for t in d["extra"]),
                measured_noisy=None if d["measured_noisy"] is None else _measured_noisy(d["measured_noisy"]),
                provenance=Provenance.from_canonical(d["provenance"]),
            )
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise ValueError(f"not a diagnostic result: {error}") from error

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DiagnosticResult):
            return NotImplemented
        return self.to_json() == other.to_json()

    __hash__ = None  # type: ignore[assignment]

    def __str__(self) -> str:
        if self.shown is not None:
            return self.shown.text
        return f"Diagnostic result {self.result_id[:12]}: {self.diagnostic}, {self.prediction}"


def _estimate_table(d: Mapping[str, Any]) -> EstimateTable:
    return EstimateTable(
        key=d["key"],
        title=d["title"],
        columns=tuple(d["columns"]),
        estimates=tuple(
            Estimate(**{**e, "interval": None if e["interval"] is None else tuple(e["interval"])})
            for e in d["estimates"]
        ),
        units=d["units"],
        interval=IntervalInfo(**d["interval"]),
    )


def _observation_table(d: Mapping[str, Any]) -> ObservationTable:
    return ObservationTable(
        key=d["key"],
        title=d["title"],
        columns=tuple(d["columns"]),
        rows=tuple(tuple(Observation(**o) for o in row) for row in d["rows"]),
    )


def _version_item(item: str) -> str:
    name, sep, detail = item.partition(": ")
    return f"{name} ({detail})" if sep else item


@dataclass(frozen=True)
class Reproduction:
    """What replaying a stored diagnostic result found (U8; 0055, 0062, 0063): prints as its text.

    Attributes
    ----------
    result_id : str
        The result replayed.
    result : DiagnosticResult
        The replayed result.
    identical : bool or None
        None: no original to compare (a provenance alone, its result deleted and not given).
    differences : tuple of str
        What differs: "2 estimates", "data card scatter_E", "report".
    provenance_differences : tuple of str
        "numpy: 2.3.1 here, 2.4.0 there", and the rebuilt design's checks ("design points differ at rows 3, 17").
    text : str
        U8's message; build it with ``make``.
    """

    result_id: str
    result: DiagnosticResult
    identical: bool | None
    differences: tuple[str, ...]
    provenance_differences: tuple[str, ...]
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "differences", tuple(self.differences))
        object.__setattr__(self, "provenance_differences", tuple(self.provenance_differences))

    def __str__(self) -> str:
        return self.text

    @classmethod
    def make(
        cls,
        result: DiagnosticResult,
        *,
        short_id: str,
        identical: bool | None,
        differences: tuple[str, ...],
        provenance_differences: tuple[str, ...],
    ) -> "Reproduction":
        """Build the reproduction with U8's text.

        "Diagnostic result 3f2a: identical (estimates, intervals, notes, figures' data cards)."; or "Differs: 2
        estimates."; or, with no original, "Diagnostic result 3f2a: replayed from its provenance, with no original
        to compare."; then "Provenance differs in numpy (2.3.1 here, 2.4.0 there)." for the versions (items
        "name: detail"), and each other provenance difference as its own sentence.
        """
        if identical is None:
            sentences = [f"Diagnostic result {short_id}: replayed from its provenance, with no original to compare."]
        elif identical:
            sentences = [f"Diagnostic result {short_id}: identical (estimates, intervals, notes, figures' data cards)."]
        else:
            sentences = [f"Differs: {', '.join(differences)}." if differences else "Differs."]
        versions = [_version_item(i) for i in provenance_differences if ": " in i]
        if versions:
            sentences.append(f"Provenance differs in {', '.join(versions)}.")
        sentences += [f"{i[:1].upper()}{i[1:]}." for i in provenance_differences if ": " not in i]
        return cls(
            result.result_id, result, identical, tuple(differences), tuple(provenance_differences), " ".join(sentences)
        )
