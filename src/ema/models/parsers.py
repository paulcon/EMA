"""Output parsers: a command-line model's model predictions, read from its files (0027; M11, C45; trust.md, T9).

Three kinds, each returning one scalar or a reason: ``regex`` (a pattern with one group, or a group named
``value``; the first or the last match), ``json`` (a dotted key whose integer parts index lists), and ``csv`` (a
column by header or index, a row, a delimiter). ``file`` is relative to the run directory, or ``stdout`` or
``stderr``. A parser that finds no file, match, key, column, or row, or reads a value that isn't a finite number,
makes its model prediction missing, with a reason ("plate.out: pattern not found"). A file is read only when its
resolved path lies inside the run directory: a link out of it is "outside the run directory", and the file outside
is never read (0030).

Read v1 at v1-final (``src/ema/core/models/parsers.py``) for the three kinds' rules; rewritten for v2's reasons,
registry, and the run directory's bounds. v1's ``python`` kind is not in v2 (a wrapper script writes JSON).
"""

import csv
import json
import math
import os
import re
from typing import Protocol

from ema.models.files import is_within, open_regular
from ema.types.model import CsvParser, JsonParser, ParserSpec, RegexParser

#: The files a parser's ``file`` of ``stdout`` or ``stderr`` names: the call's streams.
STREAMS = {"stdout": "stdout.txt", "stderr": "stderr.txt"}

Reading = tuple[float | None, str | None]


class OutputParser(Protocol):
    """An output parser kind (architecture.md §5; C45).

    Attributes
    ----------
    kind : str
        Its name in a model spec's ``parser.kind``.
    """

    kind: str

    def read(self, settings: ParserSpec, run_dir: str) -> Reading:
        """Return the value, or None with the reason; never follow a link out of the run directory."""
        ...


def read_inside(directory: str, file: str, last: int | None = None) -> tuple[bytes | None, str | None]:
    """Read a file of a run or batch directory only when its resolved path lies inside it (T9; M13).

    Parameters
    ----------
    directory
        The run or batch directory.
    file
        Relative to it, with "/"; or ``stdout`` or ``stderr``, the call's streams.
    last
        Read only the file's last ``last`` bytes; the whole file when None.

    Returns
    -------
    tuple
        The bytes, or None with the reason: "<file>: not found", "<file>: outside the run directory", or
        "<file>: couldn't be read: ...".
    """
    path = os.path.join(directory, *STREAMS.get(file, file).split("/"))
    if not os.path.lexists(path):
        return None, f"{file}: not found"
    if not is_within(path, directory):
        return None, f"{file}: outside the run directory"
    try:
        with open_regular(path) as f:
            if last is not None:
                f.seek(max(0, os.fstat(f.fileno()).st_size - last))
            return f.read(), None
    except FileNotFoundError:
        return None, f"{file}: not found"
    except OSError as e:
        return None, f"{file}: couldn't be read: {e.strerror}"


def _text(run_dir: str, file: str) -> tuple[str | None, str | None]:
    data, reason = read_inside(run_dir, file)
    return (None, reason) if data is None else (data.decode("utf-8", errors="replace"), None)


#: A number as text: ASCII decimal digits, an optional sign, point, and exponent ("+1.5E+03", ".5"), or a spelling
#: of infinity or NaN (read, then refused as not finite). No ``_`` and no other script's digits, which ``float``
#: would accept (record 0071).
_NUMBER = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[+-]?(?:inf|infinity|nan)", re.IGNORECASE)


def finite(raw: object, file: str) -> Reading:
    """Read a value as a finite number, or say why it isn't one (M11): JSON's ``true`` isn't a number.

    Text is a number only in ``_NUMBER``'s syntax, surrounding whitespace aside.
    """
    value: float | None = None
    if isinstance(raw, str):
        text = raw.strip(" \t\r\n")
        value = float(text) if _NUMBER.fullmatch(text) else None
    elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            value = float(raw)
        except OverflowError:
            value = math.inf
    try:
        shown = raw if isinstance(raw, str) else json.dumps(raw)
    except (ValueError, RecursionError):  # an integer too long to show, or nested too deeply
        shown = type(raw).__name__
    if len(shown) > 40:
        shown = shown[:39] + "…"
    if value is None:
        return None, f"{file}: {shown!r} is not a number"
    if not math.isfinite(value):
        return None, f"{file}: {shown!r} is not a finite number"
    return value, None


class _Regex:
    kind = "regex"

    def read(self, settings: ParserSpec, run_dir: str) -> Reading:
        assert isinstance(settings, RegexParser)
        text, reason = _text(run_dir, settings.file)
        if text is None:
            return None, reason
        pattern = re.compile(settings.pattern)
        found = None
        for found in pattern.finditer(text):
            if settings.match == "first":
                break
        if found is None:
            return None, f"{settings.file}: pattern not found"
        raw = found.group("value") if "value" in pattern.groupindex else found.group(1)
        return (None, f"{settings.file}: the group matched nothing") if raw is None else finite(raw, settings.file)


class _Json:
    kind = "json"

    def read(self, settings: ParserSpec, run_dir: str) -> Reading:
        assert isinstance(settings, JsonParser)
        text, reason = _text(run_dir, settings.file)
        if text is None:
            return None, reason
        try:  # an integer read as a double: one too long for Python's int is infinite, so not finite (M1)
            node = json.loads(text, parse_int=float)
        except RecursionError:
            return None, f"{settings.file}: not JSON (nested too deeply)"
        except ValueError as e:
            return None, f"{settings.file}: not JSON ({getattr(e, 'msg', e)})"
        for part in settings.key.split("."):
            try:
                node = node[int(part)] if isinstance(node, list) else node[part]
            except (KeyError, IndexError, ValueError, TypeError):
                return None, f"{settings.file}: no key {settings.key}"
        return finite(node, settings.file)


class _Csv:
    kind = "csv"

    def read(self, settings: ParserSpec, run_dir: str) -> Reading:
        assert isinstance(settings, CsvParser)
        text, reason = _text(run_dir, settings.file)
        if text is None:
            return None, reason
        try:
            rows = [r for r in csv.reader(text.splitlines(), delimiter=settings.delimiter) if r]
        except csv.Error as e:
            return None, f"{settings.file}: not CSV ({e})"
        column = settings.column
        if isinstance(column, str):
            header = [h.strip() for h in rows[0]] if rows else []
            if column not in header:
                return None, f"{settings.file}: no column {column}"
            rows, column = rows[1:], header.index(column)
        try:
            raw = rows[settings.row][column]
        except IndexError:
            return None, f"{settings.file}: no row {settings.row}, column {settings.column}"
        return finite(raw, settings.file)


_REGISTRY: dict[str, OutputParser] = {}
_KINDS = {RegexParser: "regex", JsonParser: "json", CsvParser: "csv"}


def register(parser: OutputParser) -> None:
    """Register an output parser kind.

    Raises
    ------
    ValueError
        For a kind already registered.
    """
    if parser.kind in _REGISTRY:
        raise ValueError(f"an output parser of kind {parser.kind} is registered")
    _REGISTRY[parser.kind] = parser


def get(kind: str) -> OutputParser:
    """Return the output parser of a kind.

    Raises
    ------
    KeyError
        For a kind not registered.
    """
    if kind not in _REGISTRY:
        raise KeyError(f"no output parser of kind {kind} ({', '.join(names())})")
    return _REGISTRY[kind]


def names() -> tuple[str, ...]:
    """Return the registered kinds, sorted."""
    return tuple(sorted(_REGISTRY))


def unregister(kind: str) -> None:
    """Remove a kind (tests only, 0065).

    Raises
    ------
    KeyError
        For a kind not registered.
    """
    del _REGISTRY[kind]


def read(settings: ParserSpec, run_dir: str) -> Reading:
    """Read one model prediction with the parser its settings name (M11).

    Parameters
    ----------
    settings
        The model prediction's parser settings.
    run_dir
        The run directory.

    Returns
    -------
    tuple
        The value, or None with the reason.
    """
    return get(_KINDS[type(settings)]).read(settings, run_dir)


for _parser in (_Regex(), _Json(), _Csv()):
    register(_parser)
