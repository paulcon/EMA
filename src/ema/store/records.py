"""The store's own rows (data_model.md §10; architecture.md §5): one frozen dataclass per concept.

Rows that ``ema.types`` already has a class for are returned as that class (``Run``, ``DiagnosticResult``,
``MeasuredNoisy``, ``DesignIdentity``); these are the rest (record 0056).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from ema.types.design import DesignIdentity
from ema.types.identity import TrackedFile
from ema.types.model import Keep, ModelSpec
from ema.types.requests import Request, TestRunRequest
from ema.types.runs import RunStatus


@dataclass(frozen=True)
class ModelVersion:
    """One model version (data_model.md §5.1; Q14): its spec and tracked files.

    Attributes
    ----------
    model_version_id : str
        Its hash (§3.4).
    name : str
        The model's name.
    spec : ModelSpec
        The spec as the model version covers it (``versioned_json``): its settings are the defaults; the loading's
        are in ``Loading`` (0029).
    files : tuple of TrackedFile
        Its tracked files, sorted by path.
    created_at : datetime
        When it was first loaded.
    """

    model_version_id: str
    name: str
    spec: ModelSpec
    files: tuple[TrackedFile, ...]
    created_at: datetime


@dataclass(frozen=True)
class Loading:
    """One ``load_model`` (data_model.md §5.2; Q3): what a model name means, from then on (0054).

    Attributes
    ----------
    loading : int
        Its number, increasing.
    name : str
        The model's name.
    model_version_id : str
        The model version loaded.
    spec_path : str
        The spec file loaded, absolute; its directory is the model's directory.
    keep : Keep
        Which run directories are kept (0020, 0028).
    batch_size : int or None
        Runs per batch call; None: all new runs in one call (0025).
    timeout_s : float
        Seconds per run.
    loaded_at : datetime
        When.
    """

    loading: int
    name: str
    model_version_id: str
    spec_path: str
    keep: Keep
    batch_size: int | None
    timeout_s: float
    loaded_at: datetime


@dataclass(frozen=True)
class Confirmation:
    """One question to save a drafted model spec, and its answer (data_model.md §5.3; W2, Q12; T3).

    Attributes
    ----------
    confirmation : int
        Its number, increasing.
    spec_path : str
        The absolute path shown (T6).
    spec_sha256 : str
        The hash of the file's bytes as shown.
    question : str
        The text shown, in full.
    answer : bool
        Yes or no.
    asked_at : datetime
        When.
    """

    confirmation: int
    spec_path: str
    spec_sha256: str
    question: str
    answer: bool
    asked_at: datetime


@dataclass(frozen=True)
class Approval:
    """One price shown and its answer (data_model.md §5.4; W3, Q12; P3, T3).

    Attributes
    ----------
    approval_id : str
        Its id (§3.4).
    model_version_id : str
        The model version priced.
    asked_for : str
        "diagnostic_evaluation" or "test_run" (0049).
    request : Request or TestRunRequest
        The canonical request, or the test run's.
    design : DesignIdentity or None
        The design's identity; None for the test run.
    new : int
        New runs priced: the number of its approved points.
    reused : int
        Stored runs reused.
    reused_failed : int
        Of the reused, how many failed (C47).
    time_s : float or None
        The time estimated; None: "unknown".
    question : str
        The text shown, in full.
    answer : bool
        Yes or no.
    asked_at : datetime
        When.
    """

    approval_id: str
    model_version_id: str
    asked_for: str
    request: Request | TestRunRequest
    design: DesignIdentity | None
    new: int
    reused: int
    reused_failed: int
    time_s: float | None
    question: str
    answer: bool
    asked_at: datetime


@dataclass(frozen=True)
class ApprovedPoint:
    """One point and replicate an approval answered yes covers (data_model.md §5.5; P3, I4).

    Attributes
    ----------
    approval_id : str
        The approval.
    point_hash : str
        The point's hash.
    replicate : int
        The replicate.
    """

    approval_id: str
    point_hash: str
    replicate: int


@dataclass(frozen=True)
class BatchCall:
    """One call of a batch Python function, over several runs (data_model.md §5.7; W4, Q9; 0025).

    Attributes
    ----------
    batch_call_id : str
        The SHA-256 of its runs' ids, in call order (``ema.types.batch_call_id``).
    size : int
        Its runs.
    time_s : float
        Its whole time.
    """

    batch_call_id: str
    size: int
    time_s: float


class CurrentKey(NamedTuple):
    """A stored key's current run, as Q1's key-only read returns it (``Store.current_keys``; C46, C47).

    A named tuple, not a frozen dataclass: Q1 builds one per design point, up to 10⁶ (§6).

    Attributes
    ----------
    run_id : str
        The current run's id.
    attempt : int
        Its attempt, the highest at its key (I2).
    status : RunStatus
        Whether it was ok or failed (a failed run is new only with ``retry_failed``, C47).
    """

    run_id: str
    attempt: int
    status: RunStatus


@dataclass(frozen=True)
class RunUsed:
    """One design row of a diagnostic result, and the run it used (data_model.md §5.10; C56).

    Attributes
    ----------
    result_id : str
        The diagnostic result.
    row : int
        The design row, from 0 (``ema_row``).
    run_id : str
        The run it used.
    """

    result_id: str
    row: int
    run_id: str


@dataclass(frozen=True)
class Coverage:
    """Which of one call's keys an approval covers and has no run for yet (Q13; P3, I4; record 0056).

    Attributes
    ----------
    approval_id : str
        The approval.
    model_version_id : str
        The model version it priced.
    answer : bool
        Its answer.
    covered : tuple of bool
        One per key asked about, in order: an approved point and replicate of this approval (answered yes), with
        no run of this approval there yet.
    """

    approval_id: str
    model_version_id: str
    answer: bool
    covered: tuple[bool, ...]

    @property
    def complete(self) -> bool:
        """Tell whether every key asked about is covered."""
        return all(self.covered)
