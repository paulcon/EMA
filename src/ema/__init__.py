"""EMA: diagnostics that find exploitable structure in computational models.

The root package only re-exports, lazily (PEP 562), so ``import ema.types`` loads nothing else (AR7). So far
its public names are the errors (architecture.md §2); the workspace, ``ask``, and the result types join them
with their build steps.
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

__all__ = [
    "AmbiguousId",
    "ApprovalDeclined",
    "CannotAsk",
    "DesignTooLarge",
    "EMAError",
    "ModelChanged",
    "NotFound",
    "PandocMissing",
    "PathRefused",
    "PdfFailed",
    "RequestError",
    "SpecError",
    "WorkspaceBusy",
    "WorkspaceVersion",
]


def __getattr__(name: str) -> Any:
    """Import a re-exported name on first use (PEP 562)."""
    if name in _EXPORTS:
        return getattr(importlib.import_module(_EXPORTS[name]), name)
    raise AttributeError(f"module 'ema' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List the module's names, with the re-exported ones."""
    return sorted(set(globals()) | set(_EXPORTS))
