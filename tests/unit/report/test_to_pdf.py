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
