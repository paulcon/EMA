"""What the workspace returns about models, diagnostics, reports, and runs (architecture.md §3, summaries.py).

Each prints as its ``text``, EMA's rendering (P1; AR3), which the workspace writes; sequences become tuples and
mappings read-only (record 0070).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ema.types.design import _freeze
from ema.types.model import ModelSpec
from ema.types.runs import FailureKind, RunStatus


def _tuples(obj: object, *names: str) -> None:
    for name in names:
        object.__setattr__(obj, name, tuple(getattr(obj, name)))


class _Shown:
    """Prints as its ``text``."""

    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class ModelSummary(_Shown):
    """A loaded model, as listed (U1).

    Attributes
    ----------
    name : str
        The model's name.
    model_version : str
        Its current model version's label.
    parameters : tuple of str
        Its model parameters' names.
    predictions : tuple of str
        Its model predictions' names.
    spec_path : str
        The spec file its name means now (0054).
    text : str
        EMA's text.
    """

    name: str
    model_version: str
    parameters: tuple[str, ...]
    predictions: tuple[str, ...]
    spec_path: str
    text: str

    def __post_init__(self) -> None:
        _tuples(self, "parameters", "predictions")


@dataclass(frozen=True)
class ModelDescription(_Shown):
    """A model described: its model parameters, units, nominal values, limits, and model predictions (U1).

    Attributes
    ----------
    model : ModelSummary
        Its summary.
    spec : ModelSpec
        Its model spec.
    text : str
        EMA's text.
    """

    model: ModelSummary
    spec: ModelSpec
    text: str


@dataclass(frozen=True)
class Proposal(_Shown):
    """A model spec an MCP client drafted, validated and rendered; nothing saved (U9).

    Attributes
    ----------
    spec : ModelSpec
        The spec.
    path : str
        The absolute path ``save_model``'s confirmation would show (T6).
    spec_text : str
        The file's exact text.
    missing_files : tuple of str
        Files it names that don't exist yet.
    text : str
        EMA's text.
    """

    spec: ModelSpec
    path: str
    spec_text: str
    missing_files: tuple[str, ...]
    text: str

    def __post_init__(self) -> None:
        _tuples(self, "missing_files")


@dataclass(frozen=True)
class Report:
    """A diagnostic result's report: prints as its Markdown (S1).

    Attributes
    ----------
    result_id : str
        The result.
    markdown : str
        The report.
    path : str
        ``<workspace>/results/<result id>/report.md``.
    pdf : str or None
        The PDF's path, when asked for (0018).
    """

    result_id: str
    markdown: str
    path: str
    pdf: str | None

    def __str__(self) -> str:
        return self.markdown


@dataclass(frozen=True)
class LoadingSummary(_Shown):
    """What loading a model spec did (U6; 0054).

    Attributes
    ----------
    model : ModelSummary
        The model loaded.
    new_version : bool
        Whether it made a new model version.
    replaced : str or None
        What the name meant before: "was heat@b204… at /old/dir".
    changed_files : tuple of str
        "solver.cfg changed" (U6).
    warnings : tuple of str
        Unlisted imports (M17).
    text : str
        EMA's text.
    """

    model: ModelSummary
    new_version: bool
    replaced: str | None
    changed_files: tuple[str, ...]
    warnings: tuple[str, ...]
    text: str

    def __post_init__(self) -> None:
        _tuples(self, "changed_files", "warnings")


@dataclass(frozen=True)
class DiagnosticParameterInfo:
    """One diagnostic parameter, described (C55).

    Attributes
    ----------
    name : str
        Its name.
    type : str
        "integer ≥ 1", "integer ≥ 0", "decimal in (0, 1)", ...
    default : Any
        Its default; None when it has none.
    default_text : str
        "2(d + 1)", "the only one".
    meaning : str
        What it is.
    changes_design : str
        "yes", "no", or the spec's wording.
    json_schema : Mapping[str, Any]
        For the MCP server (C55). Read-only, nested values included.
    """

    name: str
    type: str
    default: Any | None
    default_text: str
    meaning: str
    changes_design: str
    json_schema: Mapping[str, Any]

    __hash__ = None  # type: ignore[assignment]  # it holds read-only mappings

    def __post_init__(self) -> None:
        object.__setattr__(self, "json_schema", _freeze(self.json_schema))


@dataclass(frozen=True)
class DiagnosticSummary(_Shown):
    """A diagnostic, described (U1; C55).

    Attributes
    ----------
    name : str
        Its name.
    summary : str
        One line.
    takes_space : bool
        False for the point run (U7).
    parameters : tuple of DiagnosticParameterInfo
        Its diagnostic parameters.
    text : str
        EMA's text.
    """

    name: str
    summary: str
    takes_space: bool
    parameters: tuple[DiagnosticParameterInfo, ...]
    text: str

    def __post_init__(self) -> None:
        _tuples(self, "parameters")


@dataclass(frozen=True)
class RunInfo(_Shown):
    """One run, as ``failed_runs``, ``run_dirs``, and ``test_model`` show it (U3; 0020).

    Attributes
    ----------
    run_id : str
        Its id.
    short_id : str
        Its shortest unique prefix (Q11).
    row : int or None
        Its design row, when shown for a result.
    point : Mapping[str, float]
        Model parameter to value. Read-only.
    replicate : int
        Its replicate.
    status : RunStatus
        ok or failed.
    kind : FailureKind or None
        A failed run's kind; None exactly when ok.
    reason : str or None
        A failed run's reason, or why a model prediction is missing.
    stderr_tail : str or None
        A failed run's last 15 lines of stderr, shown in text as quoted model output (trust.md; 0061).
    predictions : Mapping[str, float or None]
        An ok run's model predictions; None where missing. Read-only.
    run_dir : str or None
        Its directory; None when not kept (0020).
    batch_dir : str or None
        Its batch call's directory, when kept (0025).
    text : str
        EMA's text.
    """

    run_id: str
    short_id: str
    row: int | None
    point: Mapping[str, float]
    replicate: int
    status: RunStatus
    kind: FailureKind | None
    reason: str | None
    stderr_tail: str | None
    predictions: Mapping[str, float | None]
    run_dir: str | None
    batch_dir: str | None
    text: str

    __hash__ = None  # type: ignore[assignment]  # it holds read-only mappings

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", MappingProxyType(dict(self.point)))
        object.__setattr__(self, "predictions", MappingProxyType(dict(self.predictions)))
        if (self.status is RunStatus.OK) != (self.kind is None):
            raise ValueError(f"run {self.short_id}: a kind exactly when it failed")
