"""Golden reports (diagnostics/shared.md, Golden reports; record 0044): a spec's mock report is the golden report.

``mock_report(name)`` reads the Markdown block under a diagnostic spec's "Mock report" heading. ``differences(
rendered, mock)`` parses both and lists how they differ: the sections in order; the title's diagnostic and model
prediction; each table's headings, row labels, and cells; each paragraph and note; and the Provenance line. Numbers
written with a decimal point or an exponent compare within one unit in the 4th significant digit; integers (counts,
seeds, sizes, which S3 prints in full) compare exactly. Ids (12 hex digits, or an approval's), model version labels,
the model's name, and the Provenance line's EMA and library versions are not compared (0044, 0061); its request's
parameters are compared as a set (record 0073 item 6: sorted, where the mocks follow each spec's order). Text is
compared as rendered: Markdown's backslash escapes are removed (trust.md T10), whitespace collapsed, and images
compared by their file only (record 0073 item 7).

The diagnostic steps (09-13) call ``differences`` in their golden report tests.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

DESIGN = Path(__file__).resolve().parents[2] / "docs" / "design" / "diagnostics"

_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e[+-]\d+)?(?![\w])")
_VERSION = re.compile(r"\b[\w-]+@[0-9a-f]{4,64}\b")
_ID = re.compile(r"\b[0-9a-f]{12}\b|(?<=approvals: )[0-9a-f]{4,64}\b")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def mock_report(spec: str) -> str:
    """Return the Markdown block under "## Mock report" in ``docs/design/diagnostics/<spec>.md``."""
    text = (DESIGN / f"{spec}.md").read_text(encoding="utf-8")
    after = text.split("## Mock report", 1)[1]
    return after.split("```markdown\n", 1)[1].split("\n```", 1)[0] + "\n"


@dataclass
class Parsed:
    """A report's parts: its title and, per section (the header's is ""), its blocks in order."""

    title: str
    sections: dict[str, list[tuple[str, object]]] = field(default_factory=dict)


def unescape(text: str) -> str:
    """Text as rendered: backslash escapes removed, images reduced to their file, whitespace collapsed."""
    text = _IMAGE.sub(lambda m: f"[image {m.group(1)}]", text)
    text = re.sub(r"\\(.)", r"\1", text)
    return " ".join(text.split())


def _cells(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip())[1:-1]
    return [unescape(c) for c in cells]


def parse(markdown: str) -> Parsed:
    """Split a report into its title and sections; each section's blocks are tables, paragraphs, and notes."""
    lines = markdown.split("\n")
    assert lines[0].startswith("# "), f"a report starts with its title: {lines[0]!r}"
    parsed = Parsed(title=unescape(lines[0][2:]))
    section = ""
    parsed.sections[section] = []
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = unescape(line[3:])
            assert section not in parsed.sections, f"section {section} twice"
            parsed.sections[section] = []
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.fullmatch(r"\|(-+\|)+", lines[i].strip()):
                    rows.append(_cells(lines[i]))
                i += 1
            parsed.sections[section].append(("table", rows))
        elif line.startswith("- "):
            item = [line[2:]]
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                item.append(lines[i])
                i += 1
            parsed.sections[section].append(("note", unescape(" ".join(item))))
        elif line.strip():
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("|", "## ", "- ")):
                para.append(lines[i])
                i += 1
            parsed.sections[section].append(("paragraph", unescape(" ".join(para))))
        else:
            i += 1
    return parsed


def _close(got: str, want: str) -> bool:
    """Integers exactly (S3: in full); other numbers within one unit in the 4th significant digit (0044)."""
    if not any(c in t for t in (got, want) for c in ".e"):
        return int(got) == int(want)
    a, b = float(got), float(want)
    if a == b:
        return True
    scale = max(abs(a), abs(b))
    return abs(a - b) <= 10 ** (math.floor(math.log10(scale)) - 3) * 1.0000001


def _skeleton(text: str) -> tuple[str, list[str]]:
    text = _ID.sub("<id>", _VERSION.sub("<version>", text))
    numbers = [m.group() for m in _NUMBER.finditer(text)]
    return _NUMBER.sub("<n>", text), numbers


def same_text(got: str, want: str) -> bool:
    """Equal with numbers compared as ``_close`` does, and ids and model version labels not compared."""
    (g, gn), (w, wn) = _skeleton(got), _skeleton(want)
    return g == w and len(gn) == len(wn) and all(_close(a, b) for a, b in zip(gn, wn, strict=True))


def _title(text: str) -> tuple[str, str]:
    """The title's diagnostic and model prediction; the model's name is not compared (0061)."""
    head, _, rest = text.partition(": ")
    return head, rest.rpartition(", ")[2]


def provenance(line: str) -> str:
    """The Provenance line as compared: without the EMA and library versions, the request's parameters sorted."""
    parts = []
    for part in line.split("; "):
        if part.startswith(("EMA ", "numpy ")):
            continue
        if part.startswith("request: "):
            head, *params = part.removeprefix("request: ").split(", ")
            part = "request: " + ", ".join([head, *sorted(params)])
        parts.append(part)
    return "; ".join(parts)


def differences(rendered: str, mock: str, *, skip: tuple[str, ...] = ()) -> list[str]:
    """List how a rendered report differs from its mock, as 0044 compares them; empty when it matches.

    The header's Model version row and the sections named in ``skip`` are compared by their presence only; the
    Provenance line by ``provenance``.
    """
    got, want = parse(rendered), parse(mock)
    found: list[str] = []
    if _title(got.title) != _title(want.title):
        found.append(f"title: {got.title!r}, not {want.title!r}")
    if list(got.sections) != list(want.sections):
        found.append(f"sections: {list(got.sections)}, not {list(want.sections)}")
        return found
    for name, blocks in want.sections.items():
        if name in skip:
            continue
        mine = got.sections[name]
        if [k for k, _ in mine] != [k for k, _ in blocks]:
            found.append(f"{name or 'header'}: blocks {[k for k, _ in mine]}, not {[k for k, _ in blocks]}")
            continue
        for (kind, g), (_, w) in zip(mine, blocks, strict=True):
            if kind != "table":
                if name == "Provenance":
                    g, w = provenance(str(g)), provenance(str(w))
                if not same_text(str(g), str(w)):
                    found.append(f"{name}: {kind} {g!r}, not {w!r}")
                continue
            g_rows, w_rows = list(g), list(w)  # type: ignore[call-overload]
            if len(g_rows) != len(w_rows):
                found.append(f"{name}: a table of {len(g_rows)} rows, not {len(w_rows)}: {g_rows[0]}")
                continue
            for gr, wr in zip(g_rows, w_rows, strict=True):
                if gr and wr and gr[0] == wr[0] == "Model version":
                    continue
                if len(gr) != len(wr) or not all(same_text(a, b) for a, b in zip(gr, wr, strict=True)):
                    found.append(f"{name}: row {gr}, not {wr}")
    return found
