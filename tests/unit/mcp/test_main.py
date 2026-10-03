"""``python -m ema.mcp`` (architecture.md §8; records 0081 item 3, 0086 item 11): kept, and without the ``ema[mcp]``
extra it prints the same message as ``ema mcp`` and exits 2, instead of an ``ImportError``'s traceback.
"""

import sys

from ema.cli import EXTRA_MISSING
from ema.mcp.__main__ import main


def test_without_the_extra_it_says_what_to_install_as_ema_mcp_does(monkeypatch, tmp_path, capsys):
    """0086 item 11: the import of the server fails; the message is ``ema mcp``'s, on stderr; exit 2."""
    monkeypatch.setitem(sys.modules, "ema.mcp.server", None)  # import fails, with or without the SDK installed
    assert main(["--root", str(tmp_path)]) == 2
    ran = capsys.readouterr()
    assert ran.out == "" and ran.err.startswith(EXTRA_MISSING + " (")


def test_the_docstring_no_longer_calls_it_provisional():
    """0086 item 11: ``python -m ema.mcp`` is kept, no longer provisional."""
    import ema.mcp.__main__ as entry

    assert entry.__doc__ is not None and "provisional" not in entry.__doc__


def test_its_message_is_the_clis():
    """0086 item 11: ``ema.mcp`` may not import ``ema.cli`` (AR1), so it mirrors the message; the two are equal."""
    from ema.mcp import __main__ as entry

    assert entry.EXTRA_MISSING == EXTRA_MISSING
