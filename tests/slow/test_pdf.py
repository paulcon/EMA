"""The PDF (0018, 0059 item 8; T10): the report's numbers and figures are in it; text EMA didn't write is not TeX.

Slow tier; skipped when ``to_pdf`` raises ``PandocMissing`` (as on the workflow's runners), and the text checks
when ``pdftotext`` isn't installed.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from ema import plotting
from ema.report import render, to_pdf
from ema.report.pdf import READER
from ema.types.errors import PandocMissing
from ema.types.results import Figure, Note
from tests.support.results import otable
from tests.unit.report.test_golden import linear_r3, scatter_r2
from tests.unit.report.test_render import ATTACK

pytestmark = pytest.mark.slow


def write_report(directory: Path, build) -> Path:
    spec, result = build()
    for figure in result.figures:
        fig, (ax,) = plotting.new_figure(1)
        plotting.points(ax, np.arange(5.0), np.arange(5.0) ** 2)
        plotting.axis(ax, "x", "x1", "")
        plotting.axis(ax, "y", "y", "")
        plotting.save(fig, {"panels": []}, str(directory), figure.name, figure.caption)
    path = directory / "report.md"
    path.write_text(render(result, spec), encoding="utf-8")
    return path


def pdf_or_skip(report: Path) -> Path:
    try:
        return Path(to_pdf(str(report)))
    except PandocMissing as error:
        pytest.skip(f"no PDF: {error}")


def pdf_text(pdf: Path) -> str:
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext isn't installed")
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


@pytest.mark.parametrize("build", [scatter_r2, linear_r3])
def test_the_pdf_holds_the_numbers_and_figures(tmp_path, build):
    """0018: a test checks that the PDF contains the report's numbers; 0059: it holds every figure."""
    pdf = pdf_or_skip(write_report(tmp_path, build))
    assert pdf == tmp_path / "report.pdf" and pdf.read_bytes().startswith(b"%PDF")
    text = pdf_text(pdf)
    _, result = build()
    for table in result.estimates:
        for estimate in table.estimates:
            assert format(estimate.value, ".4g") in text
    if shutil.which("pdfimages"):
        listing = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True, check=True).stdout
        assert len(listing.splitlines()) - 2 >= len(result.figures)


def test_text_ema_didnt_write_is_not_tex(tmp_path):
    """T10: a description and units `$\\input{/etc/hosts}$ ...` print as written; the PDF holds no line of /etc/hosts."""
    from tests.support.results import make_result, make_spec, shared

    spec = make_spec("t10", [("a", "", 1.0)], ("_T_", ATTACK, ATTACK))
    result = make_result(
        spec,
        diagnostic="scatter",
        title="Scatter",
        space={"a": [0, 2]},
        params={"n": 20, "seed": 0},
        kind="uniform",
        design_params={"n": 20},
        seed=0,
        sampler="random",
        rows=20,
        runs=20,
        new=20,
        usable=20,
        observations=[shared(20, "_T_", 1.0, 2.0, 0.5, ATTACK)],
    )
    (tmp_path / "report.md").write_text(render(result, spec), encoding="utf-8")
    text = pdf_text(pdf_or_skip(tmp_path / "report.md"))
    assert r"\input{/etc/hosts}" in text and "_T_" in text
    assert not [line for line in hosts_lines() if line in text]


def hosts_lines() -> list[str]:
    return [
        line.strip()
        for line in Path("/etc/hosts").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_raw_tex_math_and_dashes_in_a_report_print_as_written(tmp_path):
    """T10 (review round 1): a report with unescaped raw TeX and TeX math (as a hand-edited report could hold) makes
    a PDF that prints them as written: pandoc's reader passes nothing to lualatex as TeX, and "--" stays two dashes."""
    (tmp_path / "report.md").write_text(
        "# Raw\n\nraw: \\input{/etc/hosts}\n\nmath: $\\input{/etc/hosts}$ and a -- b\n", encoding="utf-8"
    )
    text = pdf_text(pdf_or_skip(tmp_path / "report.md"))
    assert text.count(r"\input{/etc/hosts}") == 2 and "$" in text and "a -- b" in text
    assert not [line for line in hosts_lines() if line in text]


def test_no_block_marker_in_a_results_text_makes_a_block(tmp_path):
    """T10, record 0073 item 2 (review round 1): pandoc reads the report's own blocks only; a note's lines, a table's
    title, and a caption that start with a list, rule, or definition marker stay text."""
    from tests.unit.report.test_render import ABC, MARKERS, simple

    note = Note("n", "\n".join(["first", *MARKERS]))
    title = otable("x", ("Line", "Range"), [("0", 1.5)], title="1. Decay rate: 2")
    figure = Figure("scatter_a", "scatter_a.png", "scatter_a.json", "- y against a")
    report = render(simple(notes=[note], observations=[title], figures=[figure]), ABC)
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc isn't installed")
    done = subprocess.run(
        ["pandoc", "-f", READER, "-t", "json"], input=report, capture_output=True, text=True, check=True
    )
    blocks = json.loads(done.stdout)["blocks"]

    def kinds(items):
        for block in items:
            yield block["t"]
            if block["t"] == "BulletList":
                for item in block["c"]:
                    yield from kinds(item)

    found = list(kinds(blocks))
    assert found.count("BulletList") == 1  # the Notes section's list, with one item
    assert not {"OrderedList", "HorizontalRule", "DefinitionList", "BlockQuote", "CodeBlock"} & set(found)
    assert found.count("Header") == 5  # the title; Notes, Observations, Figures, Provenance
