"""EMA: diagnostics that find exploitable structure in computational models.

The root package only re-exports, lazily (PEP 562), so ``import ema.types`` loads nothing else (AR7): the
workspace (``open_workspace``, ``Workspace``, ``ResultRef``), ``ask``, the terminal approver, the result types the
workspace returns, and the errors (architecture.md §2, §6, §7).
"""

import importlib
from typing import Any

#: Each re-exported name and the module that defines it.
_EXPORTS: dict[str, str] = {
    name: "ema.types.errors"
    for name in (
        "EMAError",
        "SpecError",
        "RequestError",
        "DesignTooLarge",
        "ApprovalDeclined",
        "CannotAsk",
        "ModelChanged",
        "NotFound",
        "AmbiguousId",
        "WorkspaceBusy",
        "WorkspaceVersion",
        "PandocMissing",
        "PdfFailed",
        "PathRefused",
    )
}
_EXPORTS["ask"] = "ema.approval"
_EXPORTS.update(dict.fromkeys(("open_workspace", "Workspace", "ResultRef"), "ema.workspace"))
_EXPORTS.update(
    dict.fromkeys(
        ("DiagnosticResult", "Provenance", "ResultSummary", "Reproduction", "Estimate", "EstimateTable",
         "Observation", "ObservationTable", "Note", "Figure", "Counts"),
        "ema.types.results",
    )
)  # fmt: skip
_EXPORTS.update(
    dict.fromkeys(
        ("ModelSummary", "ModelDescription", "Proposal", "Report", "LoadingSummary", "DiagnosticSummary",
         "DiagnosticParameterInfo", "RunInfo"),
        "ema.types.summaries",
    )
)  # fmt: skip
_EXPORTS.update(dict.fromkeys(("Price",), "ema.types.runs"))
_EXPORTS.update(dict.fromkeys(("ApprovalRequest", "ConfirmationRequest", "Progress"), "ema.types.requests"))

__all__ = [
    "AmbiguousId",
    "ApprovalDeclined",
    "ApprovalRequest",
    "CannotAsk",
    "ConfirmationRequest",
    "Counts",
    "DesignTooLarge",
    "DiagnosticParameterInfo",
    "DiagnosticResult",
    "DiagnosticSummary",
    "EMAError",
    "Estimate",
    "EstimateTable",
    "Figure",
    "LoadingSummary",
    "ModelChanged",
    "ModelDescription",
    "ModelSummary",
    "NotFound",
    "Note",
    "Observation",
    "ObservationTable",
    "PandocMissing",
    "PathRefused",
    "PdfFailed",
    "Price",
    "Progress",
    "Proposal",
    "Provenance",
    "Report",
    "Reproduction",
    "RequestError",
    "ResultRef",
    "ResultSummary",
    "RunInfo",
    "SpecError",
    "Workspace",
    "WorkspaceBusy",
    "WorkspaceVersion",
    "ask",
    "open_workspace",
]


def __getattr__(name: str) -> Any:
    """Import a re-exported name on first use (PEP 562)."""
    if name in _EXPORTS:
        return getattr(importlib.import_module(_EXPORTS[name]), name)
    raise AttributeError(f"module 'ema' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List the module's names, with the re-exported ones."""
    return sorted(set(globals()) | set(_EXPORTS))
