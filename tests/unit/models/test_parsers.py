"""The output parsers' registry and dispatch (0027, 0065; architecture.md §5, parsers.py). Each kind's known
answers and failures are C45's (``tests/contracts/model.py``)."""

import pytest

from ema.models import parsers
from ema.types.model import CsvParser, JsonParser, RegexParser


def test_the_three_kinds_are_registered():
    assert parsers.names() == ("csv", "json", "regex")
    assert all(parsers.get(k).kind == k for k in parsers.names())


def test_register_get_and_unregister():
    class Fake:
        kind = "fake"

        def read(self, settings, run_dir):
            return 1.0, None

    parsers.register(Fake())
    try:
        assert "fake" in parsers.names() and parsers.get("fake").read(None, "") == (1.0, None)
        with pytest.raises(ValueError, match="registered"):
            parsers.register(Fake())
    finally:
        parsers.unregister("fake")
    with pytest.raises(KeyError, match="no output parser of kind fake"):
        parsers.get("fake")


def test_read_dispatches_by_the_settings_kind(tmp_path):
    (tmp_path / "out.txt").write_text("v = 3\n")
    (tmp_path / "out.json").write_text('{"v": 4}')
    (tmp_path / "out.csv").write_text("v\n5\n")
    (tmp_path / "stderr.txt").write_text("v = 6\n")
    assert parsers.read(RegexParser("out.txt", r"v = (\S+)"), str(tmp_path)) == (3.0, None)
    assert parsers.read(JsonParser("out.json", "v"), str(tmp_path)) == (4.0, None)
    assert parsers.read(CsvParser("out.csv", "v"), str(tmp_path)) == (5.0, None)
    assert parsers.read(RegexParser("stderr", r"v = (\S+)"), str(tmp_path)) == (6.0, None)


def test_a_file_that_isnt_regular_is_missing_never_waited_on(tmp_path):
    import os

    os.mkfifo(tmp_path / "out.txt")
    value, reason = parsers.read(RegexParser("out.txt", r"v = (\S+)"), str(tmp_path))
    assert value is None and reason == "out.txt: couldn't be read: not a regular file"
