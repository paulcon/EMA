"""``ema.report.to_pdf``'s refusals that need no pandoc (0059 item 8; record 0073 item 10); the PDFs themselves are
the slow tier's (tests/slow/test_pdf.py)."""

import shutil

import pytest

from ema.report import to_pdf
from ema.types.errors import PandocMissing, PdfFailed


def test_pandoc_missing_names_what_to_install(tmp_path, monkeypatch):
    (tmp_path / "report.md").write_text("# Scatter: r2, y\n", encoding="utf-8")
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "pandoc" else real(name, *a, **k))
    with pytest.raises(PandocMissing, match="pandoc"):
        to_pdf(str(tmp_path / "report.md"))
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "lualatex" else real(name, *a, **k))
    with pytest.raises(PandocMissing, match="lualatex"):
        to_pdf(str(tmp_path / "report.md"))


def test_a_missing_figure_fails_before_pandoc(tmp_path, monkeypatch):
    """0059: pandoc drops a figure it can't find with exit 0, so to_pdf checks first."""
    (tmp_path / "report.md").write_text("# Scatter: r2, y\n\n![a](scatter_a.png)\n", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/usr/bin/{name}")
    with pytest.raises(PdfFailed, match="scatter_a.png"):
        to_pdf(str(tmp_path / "report.md"))


def test_pdf_failed_names_latexs_error_line_first():
    """Review round 1: LaTeX's "!" line is the error, even after a line that mentions "Error" in passing."""
    from ema.report.pdf import _failure

    stderr = "Error producing PDF.\n(./report.tex\n! Undefined control sequence.\nl.42 \\foo\n"
    failure = _failure(stderr)
    assert isinstance(failure, PdfFailed) and str(failure).endswith("! Undefined control sequence.")
    assert str(_failure("Error producing PDF.\nsomething\n")).endswith("Error producing PDF.")


def test_the_reader_turns_off_tex_math_and_smart_punctuation():
    """T10 (review round 1): `$\\input{...}$` would reach lualatex as math, and "--" would print as a dash."""
    from ema.report.pdf import READER

    assert READER.startswith("markdown-")
    off = set(READER.removeprefix("markdown-").split("-"))
    assert {"raw_tex", "raw_html", "raw_attribute", "tex_math_dollars", "smart"} <= off


def test_the_pdfs_figures_fit_the_page():
    """Record 0081 item 30: several figures on a line get half the width each (two to a row), one alone 60%; a
    figure inside text, and the report's own Markdown, are left as they are; implicit figures are off."""
    from ema.report.pdf import READER, _sized

    text = "a\n\n![P](scatter_P.png) ![L](scatter_L.png) ![E](scatter_E.png)\n\nb\n\n![h](h.png)\n\nc ![x](x.png) d\n"
    sized = _sized(text)
    assert "![P](scatter_P.png){width=48%} ![L](scatter_L.png){width=48%} ![E](scatter_E.png){width=48%}" in sized
    assert "![h](h.png){width=60%}" in sized and "c ![x](x.png) d" in sized
    assert "-implicit_figures" in READER
