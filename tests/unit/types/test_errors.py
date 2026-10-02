"""The errors and whether trying again can help (architecture.md §3, errors.py)."""

import pytest

import ema
from ema.types import errors

RETRYABLE = {
    "EMAError": False,
    "SpecError": False,
    "RequestError": False,
    "DesignTooLarge": False,
    "ApprovalDeclined": True,
    "CannotAsk": False,
    "ModelChanged": False,
    "NotFound": False,
    "AmbiguousId": False,
    "WorkspaceBusy": True,
    "WorkspaceVersion": False,
    "PandocMissing": False,
    "PdfFailed": False,
    "PathRefused": False,
}
PARENT = {"DesignTooLarge": "RequestError", "CannotAsk": "ApprovalDeclined"}


@pytest.mark.parametrize("name", sorted(RETRYABLE))
def test_each_error_says_whether_retrying_can_help(name):
    cls = getattr(errors, name)
    assert cls.retryable is RETRYABLE[name]
    assert issubclass(cls, getattr(errors, PARENT.get(name, "EMAError")))
    assert issubclass(cls, Exception)


def test_the_root_re_exports_the_errors_lazily():
    """AR7: ``ema`` re-exports, and imports nothing until a name is asked for."""
    for name in RETRYABLE:
        assert getattr(ema, name) is getattr(errors, name)
    assert set(RETRYABLE) <= set(dir(ema))
    with pytest.raises(AttributeError):
        _ = ema.not_a_name
