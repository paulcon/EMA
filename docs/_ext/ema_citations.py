"""Citations off the documentation site (record 0089): drop them when the site is built, and fail on any left.

The repository cites ids in parentheses (0089 item 2): "(0015)", "(designs.md, Generators; C20-C27)", "(§3.3)". The
site cites nothing (item 1), so this extension drops each semicolon-separated part of a parenthesis that starts with
a citation, and the parenthesis when nothing is left (item 3): in every docstring (``autodoc-process-docstring``,
which autosummary's summaries also go through), and in every Markdown page (``source-read``), where it also cuts a
guide's opening metadata paragraph to its status. At ``build-finished`` it scans every HTML page's text, code
included, and warns once per page with a citation left (item 4); ``-W`` makes that an error. A reference model's id
(R1-R11) is a name a user types, not a citation, and stays.
"""

import html
import re
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

#: A spec id's prefix (CONTRIBUTING.md, Ids), but R: a reference model's id is its name (0089 item 1).
_PREFIX = r"(?:AR|OD-|PT|SC|CL|LN|LM|PM|[PUMGSVCQWITE])"
_SPEC = rf"{_PREFIX}\d+[a-z]?"
#: A spec file, with its path if it has one ("data_model.md", "../design/trust.md").
_FILE = r"[\w./-]*\w\.md\b"
#: A build step ("step 06", "steps 04 and 05", "step T", "build step"), a review round ("review round 1"), or a
#: layer ("layer 3b"), which are citations too (record 0090). A guide's own step, with one digit ("step 6"), is not.
_INTERNAL = r"[Ss]teps? (?:\d{2}|[A-Z])\b|[Bb]uild steps?\b|(?:[Rr]eview )?[Rr]ounds? \d+\b|[Ll]ayers? \d[a-z]?\b"

#: What a citation starts with, after any space, a blockquote's or a comment's mark on a new line, and backticks:
#: a record ("0015", "record 0070", "records 0034"), a spec id, a spec file, a section mark, or a build step, a
#: review round, or a layer (0090).
_STARTS = re.compile(rf"[\s>#]*`*(?:records?\s+\d|0\d{{3}}\b|{_SPEC}(?![\w])|{_FILE}|§|{_INTERNAL})")

#: A citation anywhere in a text (0089 item 1), bare or in parentheses.
_CITATION = re.compile(
    "|".join(
        [
            r"\brecords?\s+\d+(?:\s*[–-]\s*\d+)?",
            r"(?<![\w.,-])0\d{3}(?!\w|[.,]\d)",
            rf"(?<![\w.-]){_SPEC}(?:\s*[–-]\s*{_PREFIX}?\d+[a-z]?)?(?![\w])",
            rf"(?<![\w/.-]){_FILE}",
            r"§\s?\d[\d.]*",
            rf"\b(?:{_INTERNAL})",
        ]
    )
)

#: Text the check doesn't read: a URL, a Markdown link's target (shown as its words, not its address), and a
#: ``noqa`` comment's Ruff rule codes ("S110").
_UNREAD = re.compile(r"https?://\S+|(?<=\])\([^()\s]*\)|noqa:\s*[A-Z]+\d+(?:,\s*[A-Z]+\d+)*")

#: Text that looks like a citation but is data, each with its reason (0089 item 4).
ALLOWED: dict[str, str] = {
    "report.md": "the report's file name, which a user opens",
    "tools.md": "ema.mcp's data file, named where the server reads it",
    "V32": "a numpy dtype code (32 raw bytes), not a variability interval requirement",
    "S32": "a numpy dtype code (32 bytes of text), not a shared diagnostic requirement",
}

#: A Markdown page's metadata paragraph: the first paragraph after its title, when it starts with its status.
_METADATA = re.compile(r"\A(# [^\n]*\n\n)\*\*Status:\*\* ([^.\n]*)\.(?:[^\n]|\n(?!\n))*")


def _close(text: str, start: int) -> int:
    """Find the parenthesis that closes the one at ``start``: its index, or -1 when none does."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parts(inner: str) -> list[str]:
    """``inner`` split at its semicolons outside any nested parenthesis and any quotation ("a; b", “a; b”).

    Quotation marks count only when they pair up: an odd ``"`` (a 6" pipe), or a “ without its ”, is text, and the
    split is at every semicolon, so no part swallows the rest of the parenthesis.
    """
    straight = inner.count('"') % 2 == 0
    curly = inner.count("“") == inner.count("”")
    parts, depth, quoted, opened, last = [], 0, False, 0, 0
    for i, ch in enumerate(inner):
        depth += (ch == "(") - (ch == ")")
        quoted ^= straight and ch == '"'
        opened += curly and ((ch == "“") - (ch == "”"))
        if ch == ";" and depth == 0 and not quoted and opened <= 0:
            parts.append(inner[last:i])
            last = i + 1
    return [*parts, inner[last:]]


def _trim(out: list[str]) -> None:
    """Drop the space before a dropped parenthesis, and one line break, but not a blank line."""
    text = "".join(out).rstrip(" \t")
    if text.endswith("\n") and not text.endswith("\n\n") and text.rstrip("\n \t"):
        text = text[:-1].rstrip(" \t")
    out[:] = [text]


def strip_citations(text: str) -> str:
    """``text`` without its citations: each part of a parenthesis that starts with one, and the parenthesis if empty.

    A parenthesis may span lines and hold others. A Markdown link's target (``[words](page.md)``) is not a
    parenthesis.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        j = text.find("(", i)
        if j < 0:
            out.append(text[i:])
            break
        end = _close(text, j)
        if end < 0:  # an unmatched "(", as in "(0, 1]": text, and the rest is read on
            out.append(text[i : j + 1])
            i = j + 1
            continue
        out.append(text[i:j])
        if j > 0 and text[j - 1] == "]":
            out.append(text[j : end + 1])
            i = end + 1
            continue
        inner = strip_citations(text[j + 1 : end])
        parts = _parts(inner)
        kept = [p for p in parts if not _STARTS.match(p)]
        if not kept:
            _trim(out)
        elif len(kept) == len(parts):
            out.append(f"({inner})")
        else:
            out.append("(" + "; ".join(p.strip() for p in kept) + ")")
        i = end + 1
    return "".join(out)


def strip_metadata(source: str) -> str:
    """Cut a Markdown page's metadata paragraph, if it has one, to its status ("**Status:** outline.")."""
    return _METADATA.sub(r"\1**Status:** \2.", source, count=1)


def find_citations(text: str) -> list[str]:
    """Every citation in ``text`` (0089 item 1), but the allowlisted, in order."""
    found = (m.group().strip() for m in _CITATION.finditer(_UNREAD.sub(" ", text)))
    return [c for c in found if c not in ALLOWED and c.rpartition("/")[2] not in ALLOWED]


def _docstring(app: Sphinx, what: str, name: str, obj: object, options: object, lines: list[str]) -> None:
    lines[:] = strip_citations("\n".join(lines)).split("\n")


def _page(app: Sphinx, docname: str, source: list[str]) -> None:
    source[0] = strip_citations(strip_metadata(source[0]))


def _page_text(page: str) -> str:
    """Read an HTML page's text: its scripts, styles, and tags removed, its entities read."""
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


def _check(app: Sphinx, exception: Exception | None) -> None:
    if exception is not None or app.builder.format != "html":
        return
    out = Path(app.outdir)
    for path in sorted(out.rglob("*.html")):
        if "_static" in path.relative_to(out).parts:
            continue
        found = [" ".join(c.split()) for c in find_citations(_page_text(path.read_text(encoding="utf-8")))]
        if found:
            shown = ", ".join(dict.fromkeys(found))
            page = path.relative_to(out).as_posix()
            logger.warning(f"{page}: {len(found)} citation(s) on the page (record 0089): {shown}")


def setup(app: Sphinx) -> dict[str, Any]:
    """Connect the filter and the check (0089 items 3 and 4)."""
    # Before napoleon (priority 500), which reads "words: words" in an attribute's docstring as a type and a
    # description, and would split a parenthesis that holds a colon.
    app.connect("autodoc-process-docstring", _docstring, priority=400)
    app.connect("source-read", _page)
    app.connect("build-finished", _check)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
