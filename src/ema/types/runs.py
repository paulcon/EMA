"""Runs: one stored run, a new run's key, a resolved design, stored runs as columns, a run batch, and the price.

architecture.md §3 (runs.py); data_model.md §4.3, §5.6, §5.8, Q1, Q2, Q7, Q15; P3; C47, C56; record 0070.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.types._values import finite_doubles
from ema.types.design import Design
from ema.types.identity import ID_DTYPE, hex_ids, id_array, point_hash, run_id
from ema.types.text import duration


class _Coded(Enum):
    """An enumeration whose members have integer codes, their index (record 0070, item 2)."""

    @property
    def code(self) -> int:
        """The member's code in ``RunColumns``: its index in the enumeration."""
        return list(type(self)).index(self)

    @classmethod
    def from_code(cls, code: int) -> Any:
        """Return the member with this code.

        Raises
        ------
        ValueError
            For a code that isn't a member's.
        """
        members = list(cls)
        if not 0 <= code < len(members):
            raise ValueError(f"no {cls.__name__} has code {code!r}")
        return members[code]


class RunStatus(_Coded):
    """A run's status (data_model.md §4.3): ``ok`` or ``failed``, with a kind.

    An ok run finished cleanly and read at least one model prediction (0043). Codes: ok 0, failed 1.
    """

    OK = "ok"
    FAILED = "failed"


class FailureKind(_Coded):
    """Why a run failed (model_interface.md, Failures): ``error``, ``timeout``, or ``unread`` (0043).

    Codes: error 0, timeout 1, unread 2; -1 in ``RunColumns.kind`` for an ok run.
    """

    ERROR = "error"
    TIMEOUT = "timeout"
    UNREAD = "unread"

    @classmethod
    def from_code(cls, code: int) -> "FailureKind | None":
        """Return the kind with this code; None for -1, an ok run's (``ValueError`` for any other code)."""
        return None if code == -1 else super().from_code(code)


def _freeze_map(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(mapping))


def _frozen(array: np.ndarray) -> np.ndarray:
    """Return a read-only view that nothing else can write through (record 0070, item 8 and review round 1).

    An array no one can write is shared; one that owns its data is made read-only in place, the caller's array
    too (no copy: 10^7 ids are 320 MB); a writable view of another array's data is copied.
    """
    chain = [array]
    while isinstance(chain[-1].base, np.ndarray):
        chain.append(chain[-1].base)
    if any(a.flags.writeable for a in chain):
        if array.base is None:
            array.flags.writeable = False
        else:
            array = array.copy()
            array.flags.writeable = False
    out = array.view()
    out.flags.writeable = False
    return out


def _read_only(array: Any, dtype: Any, ndim: int, n: int | None, what: str) -> np.ndarray:
    given = np.asarray(array)
    integral = dtype is not None and np.dtype(dtype).kind == "i"
    if integral and given.size and given.dtype.kind not in "iu":
        raise ValueError(f"{what}: integers, not {given.dtype}")
    if integral and given.size and not np.can_cast(given.dtype, dtype) and int(given.max()) > np.iinfo(dtype).max:
        raise ValueError(f"{what}: integers up to {np.iinfo(dtype).max:,}, not {int(given.max()):,}")
    out = np.asarray(given, dtype=dtype)
    if out.ndim != ndim or (n is not None and out.shape[0] != n):
        raise ValueError(f"{what}: shape {out.shape}, expected {ndim} dimensions with {n} rows")
    return _frozen(out)


def _ids(array: np.ndarray | Sequence[str], n: int | None, what: str) -> np.ndarray:
    """Read ids by ``id_array``'s one rule, as a read-only ``ID_DTYPE`` array; an ``ID_DTYPE`` array is not copied."""
    if not (isinstance(array, np.ndarray) and array.dtype == ID_DTYPE):
        try:
            array = id_array(array)
        except ValueError as error:
            raise ValueError(f"{what}: {error}") from error
    return _read_only(array, ID_DTYPE, 1, n, what)


@dataclass(frozen=True)
class Run:
    """One stored run (data_model.md §5.6, §5.8), with its model predictions folded in.

    Built with §5.6's and §5.8's checks: ``kind`` and ``reason`` are None exactly when ``ok``; a failed run has no
    model predictions; an ok run reads at least one (0043), and each missing one (None) has its reason, never NaN.

    Attributes
    ----------
    run_id : str
        Its id (data_model.md §3.4).
    model_version_id : str
        The model version that ran.
    point : tuple of float
        Every model parameter, in the spec's order.
    replicate : int
        0, or the point run's repeats 1, 2, ... (0011).
    attempt : int
        0 for the first run at its key; 1, 2, ... for each retry (0010).
    status : RunStatus
        ok or failed.
    kind : FailureKind or None
        A failed run's kind.
    reason : str or None
        A failed run's one-line reason.
    stderr_tail : str or None
        The last 15 lines of stderr, or of the traceback.
    exit_code : int or None
        The program's exit code; -N for signal N; None for a Python function, a program that couldn't start, or a
        timeout.
    predictions : Mapping[str, float or None]
        Every model prediction of an ok run, None where missing; empty for a failed run. Read-only.
    missing : Mapping[str, str]
        Each missing model prediction's reason. Read-only.
    time_s : float
        The call's time, or a batch call's share (0025).
    batch_call_id : str or None
        Its batch call (0025).
    host : str
        Where it ran (0015).
    program : str
        The program's resolved path; for a Python function, the child's interpreter (0029).
    approval_id : str
        The approval it was made under (C48).
    """

    run_id: str
    model_version_id: str
    point: tuple[float, ...]
    replicate: int
    attempt: int
    status: RunStatus
    kind: FailureKind | None
    reason: str | None
    stderr_tail: str | None
    exit_code: int | None
    predictions: Mapping[str, float | None]
    missing: Mapping[str, str]
    time_s: float
    batch_call_id: str | None
    host: str
    program: str
    approval_id: str

    __hash__ = None  # type: ignore[assignment]  # it holds read-only mappings

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", finite_doubles(self.point, "a run's point"))
        predictions = {k: None if v is None else float(v) for k, v in self.predictions.items()}
        object.__setattr__(self, "predictions", _freeze_map(predictions))
        object.__setattr__(self, "missing", _freeze_map(self.missing))
        if self.replicate < 0 or self.attempt < 0 or not (math.isfinite(self.time_s) and self.time_s >= 0):
            raise ValueError(f"run {self.run_id}: a replicate, an attempt, and a time are >= 0")
        ok = self.status is RunStatus.OK
        if ok != (self.kind is None) or ok != (self.reason is None):
            raise ValueError(f"run {self.run_id}: a kind and a reason exactly when it failed")
        if not ok and (predictions or self.missing):
            raise ValueError(f"run {self.run_id}: a failed run has no model predictions")
        absent = {k for k, v in predictions.items() if v is None}
        if ok and (len(absent) == len(predictions) or absent != set(self.missing)):
            raise ValueError(
                f"run {self.run_id}: an ok run reads a model prediction, and each missing one has a reason"
            )
        if any(v is not None and not math.isfinite(v) for v in predictions.values()):
            raise ValueError(f"run {self.run_id}: a model prediction's value is finite; a missing one is None")


@dataclass(frozen=True)
class RunKey:
    """A new run to make: its key (data_model.md §3.4) and its id, known before the run.

    Attributes
    ----------
    point : tuple of float
        A complete point, in the spec's order.
    point_hash : str
        The point's hash.
    replicate : int
        Its replicate.
    attempt : int
        Its attempt (C47).
    run_id : str
        Its run's id.
    """

    point: tuple[float, ...]
    point_hash: str
    replicate: int
    attempt: int
    run_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", finite_doubles(self.point, "a run key's point"))

    @classmethod
    def make(cls, model_version_id: str, point: Sequence[float], replicate: int, attempt: int) -> "RunKey":
        """Build a key, computing its point hash and run id (data_model.md §3.4).

        Raises
        ------
        ValueError
            For a non-finite coordinate, or a negative replicate or attempt.
        """
        doubles = finite_doubles(point, "a run key's point")
        digest = point_hash(doubles)
        return cls(doubles, digest, replicate, attempt, run_id(model_version_id, digest, replicate, attempt))


@dataclass(frozen=True, eq=False)
class Resolution:
    """A design resolved against the store (Q1): what pricing, approval, and running share.

    Attributes
    ----------
    design : Design
        The design resolved.
    model_version_id : str
        Its model version.
    row_runs : numpy.ndarray
        ``(n,)`` of ``ID_DTYPE``: each design row's stored run id, or zeros when new. Read-only.
    row_keys : numpy.ndarray
        ``(n,)`` integers: each new row's index into ``new_keys``, or -1 when stored. Read-only.
    new_keys : tuple of RunKey
        The distinct (point, replicate) keys to run, attempts set (C47).
    reused_failed : int
        How many of the stored runs reused had failed (0010).
    """

    design: Design
    model_version_id: str
    row_runs: np.ndarray
    row_keys: np.ndarray
    new_keys: tuple[RunKey, ...]
    reused_failed: int

    def __post_init__(self) -> None:
        n = len(self.design)
        row_runs = _ids(self.row_runs, n, "row_runs")
        row_keys = _read_only(self.row_keys, np.int64, 1, n, "row_keys")
        object.__setattr__(self, "row_runs", row_runs)
        object.__setattr__(self, "row_keys", row_keys)
        object.__setattr__(self, "new_keys", tuple(self.new_keys))
        if n and (row_keys.min() < -1 or row_keys.max() >= len(self.new_keys)):
            raise ValueError("row_keys must index new_keys, or be -1 for a stored row")
        zero = row_runs == np.zeros(1, dtype=ID_DTYPE)
        if not np.array_equal(zero, row_keys >= 0):
            raise ValueError("a new row's row_runs entry is zeros, and a stored row's is its run's id")
        if self.reused_failed < 0:
            raise ValueError(f"reused_failed must be >= 0, not {self.reused_failed}")


@dataclass(frozen=True, eq=False)
class RunColumns:
    """Stored runs, one row each, in the order asked for (Q7, Q15): columns, not a ``Run`` per row.

    Every array is ``(n,)`` (``points`` ``(n, d)``) and read-only; ids are ``ID_DTYPE``; failed runs and missing
    model predictions are NaN in ``values``. Status and kind are codes (``RunStatus.code``,
    ``FailureKind.code``; -1 for an ok run's kind).

    Attributes
    ----------
    run_ids : numpy.ndarray
        ``(n,)`` ids.
    points : numpy.ndarray or None
        ``(n, d)``: Q7 fills it, and Q15 for a replay (0062).
    replicates : numpy.ndarray
        ``(n,)`` integers.
    status : numpy.ndarray
        ``(n,)`` ``RunStatus`` codes.
    kind : numpy.ndarray
        ``(n,)`` ``FailureKind`` codes; -1 when ok.
    values : Mapping[str, numpy.ndarray]
        Model prediction to ``(n,)`` doubles; NaN where missing or failed.
    reasons : Mapping[str, str]
        Failed run id (hex) to its one-line reason.
    stderr_tails : Mapping[str, str]
        Failed run id (hex) to its stderr tail; Q7 fills it, Q15 leaves it empty (0061).
    missing : Mapping[str, Mapping[str, str]]
        Model prediction to ok run id (hex) to why it is missing.
    time_s : numpy.ndarray
        ``(n,)`` doubles.
    host : numpy.ndarray
        ``(n,)`` strings.
    program : numpy.ndarray
        ``(n,)`` strings.
    batch_call_ids : numpy.ndarray
        ``(n,)`` ids, or zeros.
    approval_ids : numpy.ndarray
        ``(n,)`` ids.
    """

    run_ids: np.ndarray
    points: np.ndarray | None
    replicates: np.ndarray
    status: np.ndarray
    kind: np.ndarray
    values: Mapping[str, np.ndarray]
    reasons: Mapping[str, str]
    stderr_tails: Mapping[str, str]
    missing: Mapping[str, Mapping[str, str]]
    time_s: np.ndarray
    host: np.ndarray
    program: np.ndarray
    batch_call_ids: np.ndarray
    approval_ids: np.ndarray

    def __post_init__(self) -> None:
        run_ids = _ids(self.run_ids, None, "run_ids")
        n = run_ids.shape[0]
        set_ = object.__setattr__
        set_(self, "run_ids", run_ids)
        if self.points is not None:
            set_(self, "points", _read_only(self.points, np.float64, 2, n, "points"))
        for name, dtype in (("replicates", np.int64), ("status", np.int64), ("kind", np.int64), ("time_s", np.float64)):
            set_(self, name, _read_only(getattr(self, name), dtype, 1, n, name))
        for name in ("host", "program"):
            set_(self, name, _read_only(getattr(self, name), None, 1, n, name))
        for name in ("batch_call_ids", "approval_ids"):
            set_(self, name, _ids(getattr(self, name), n, name))
        values = {k: _read_only(v, np.float64, 1, n, f"values[{k!r}]") for k, v in self.values.items()}
        set_(self, "values", MappingProxyType(values))
        set_(self, "reasons", _freeze_map(self.reasons))
        set_(self, "stderr_tails", _freeze_map(self.stderr_tails))
        set_(self, "missing", MappingProxyType({k: _freeze_map(v) for k, v in self.missing.items()}))
        if not (np.isin(self.status, (0, 1)).all() and np.isin(self.kind, (-1, 0, 1, 2)).all()):
            raise ValueError("a status code is 0 or 1, a kind code -1, 0, 1, or 2 (record 0070, item 2)")
        if not np.array_equal(self.kind == -1, self.status == RunStatus.OK.code):
            raise ValueError("a run has a kind exactly when it failed")
        failed = self.status != RunStatus.OK.code
        for name, column in self.values.items():
            if not np.isnan(column[failed]).all():
                raise ValueError(f"values[{name!r}]: a failed run's value is NaN (architecture.md §3)")

    def __len__(self) -> int:
        """Return the number of rows."""
        return int(self.run_ids.shape[0])


@dataclass(frozen=True, eq=False)
class RunBatch:
    """The runs a diagnostic receives, one row per design row, in design order (C56).

    Attributes
    ----------
    design : Design
        The design; a replay's is built from the stored points (0063).
    runs : RunColumns
        Each row's run.
    new : numpy.ndarray
        ``(n,)`` bools: made by this diagnostic evaluation (E6). Read-only.
    """

    design: Design
    runs: RunColumns
    new: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.design)
        object.__setattr__(self, "new", _read_only(self.new, np.bool_, 1, n, "new"))
        if len(self.runs) != n:
            raise ValueError(f"a run batch has one run per design row: {len(self.runs)} runs, {n} rows")

    def usable(self, prediction: str) -> np.ndarray:
        """Return ``(n,)`` bools: the rows whose run is ok and read ``prediction`` (0022; shared.md, the precheck).

        Raises
        ------
        KeyError
            For a model prediction the runs don't hold.
        """
        if prediction not in self.runs.values:
            raise KeyError(f"no model prediction {prediction!r} in this run batch")
        return (self.runs.status == RunStatus.OK.code) & ~np.isnan(self.runs.values[prediction])

    def run_id(self, row: int) -> str:
        """Return the id of the run at design row ``row``, as 64 hex digits."""
        return hex_ids(self.runs.run_ids[row : row + 1])[0]


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


@dataclass(frozen=True)
class Price:
    """What a diagnostic evaluation's or the test run's new runs cost (P3; Q2): prints as its text.

    Attributes
    ----------
    new : int
        New runs.
    reused : int
        Stored runs reused.
    reused_failed : int
        Of the reused, how many had failed (0010, C47).
    time_s : float or None
        The time estimated, ``new`` times the stored runs' mean; None: "time unknown", with no stored run.
    from_runs : int
        The stored runs the time is from (Q2).
    text : str
        "96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)"; build it with ``make``.
    """

    new: int
    reused: int
    reused_failed: int
    time_s: float | None
    from_runs: int
    text: str

    def __post_init__(self) -> None:
        if (
            min(self.new, self.reused, self.reused_failed) < 0
            or not self.reused_failed <= self.reused <= self.from_runs
        ):
            raise ValueError(f"a price's counts are >= 0, with reused_failed <= reused <= from_runs (Q2): {self}")
        if (self.time_s is None) != (self.from_runs == 0):
            raise ValueError("a price has a time exactly when it is estimated from stored runs (P3)")
        if self.time_s is not None and not (math.isfinite(self.time_s) and self.time_s >= 0):
            raise ValueError(f"a price's time is finite and >= 0, not {self.time_s}")

    def __str__(self) -> str:
        return self.text

    @classmethod
    def make(cls, *, new: int, reused: int, reused_failed: int = 0, time_s: float | None, from_runs: int) -> "Price":
        """Build a price with EMA's text (architecture.md §3; U1, U2; 0010).

        "<new> new runs, <reused> reused[, of which <k> failed], " then "time unknown", or the time as
        ``duration`` writes it and "(from <m> stored runs)"; "run" in the singular for 1.

        Raises
        ------
        ValueError
            For a negative count, more failed than reused, or a time without stored runs (or none with them).

        Examples
        --------
        >>> Price.make(new=96, reused=1, time_s=11_520.0, from_runs=1).text
        '96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)'
        """
        parts = [f"{_plural(new, 'new run')}", f"{reused} reused"]
        if reused_failed:
            parts.append(f"of which {reused_failed} failed")
        if time_s is None or from_runs == 0:
            parts.append("time unknown")
        else:
            parts.append(f"{duration(time_s)} (from {_plural(from_runs, 'stored run')})")
        return cls(new, reused, reused_failed, time_s, from_runs, ", ".join(parts))
