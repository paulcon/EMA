"""The errors EMA raises on purpose (architecture.md §3, errors.py).

Each carries ``retryable`` as a class attribute, so the interfaces can say whether trying again can help.
"""

from typing import ClassVar


class EMAError(Exception):
    """The base of every error EMA raises on purpose."""

    retryable: ClassVar[bool] = False


class SpecError(EMAError):
    """A model spec doesn't validate; the message names the field."""


class RequestError(EMAError):
    """A space, a diagnostic parameter, or a design's identity is refused (G14, G15, G18, M6)."""


class DesignTooLarge(RequestError):
    """A design's size is over ``MAX_DESIGN_POINTS``; the message names the size and the cap (G5)."""


class ApprovalDeclined(EMAError):
    """The answer was no, or none came; nothing ran (P3)."""

    retryable: ClassVar[bool] = True


class CannotAsk(ApprovalDeclined):
    """Nobody can be asked (``approve=None`` or ``confirm=None``); nothing was asked or recorded."""

    retryable: ClassVar[bool] = False


class ModelChanged(EMAError):
    """A tracked file changed since loading, or during an evaluation (U6, M16); the message names it."""


class NotFound(EMAError):
    """No such model, diagnostic, result, or run."""


class AmbiguousId(EMAError):
    """An id prefix names several ids, which the message lists (Q11)."""


class WorkspaceBusy(EMAError):
    """Another process holds the run lock, named in the message."""

    retryable: ClassVar[bool] = True


class WorkspaceVersion(EMAError):
    """The workspace's schema is newer than this EMA (data_model.md §11)."""


class PandocMissing(EMAError):
    """A PDF was asked for without pandoc or lualatex, or lualatex lacks a package or font (0018, 0059)."""


class PdfFailed(EMAError):
    """lualatex stopped for another reason, or a figure is missing from the PDF (0059)."""


class PathRefused(EMAError):
    """An MCP path argument, or a drafted spec's file, is refused (trust.md, T5, T7)."""
