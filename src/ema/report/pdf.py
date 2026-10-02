"""A report's PDF, through pandoc and lualatex (0018; 0059 item 8; trust.md T10; record 0073 item 10).

The text is set in DejaVu Serif and code in DejaVu Sans Mono, each from the four files matplotlib ships, named
one by one, so no TeX text font is needed. pandoc reads the report with raw TeX, raw HTML, and raw attributes off,
the second guard after the report's escaping (T10). It runs in a temporary directory holding a copy of the report
and its figures, so a path with ``%``, ``#``, or ``~`` (which lualatex can't take), or a figure pandoc would drop
with exit 0, doesn't spoil the PDF (0059's pitfalls).
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib

from ema.types.errors import PandocMissing, PdfFailed

#: pandoc's reader: Markdown with raw TeX, raw HTML, and raw attributes off (T10).
READER = "markdown-raw_tex-raw_html-raw_attribute"
#: Seconds for one PDF; one takes about 4 s (0059).
PDF_TIMEOUT_S = 300
_FONTS = {
    "main": ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf"),
    "mono": (
        "DejaVuSansMono.ttf",
        "DejaVuSansMono-Bold.ttf",
        "DejaVuSansMono-Oblique.ttf",
        "DejaVuSansMono-BoldOblique.ttf",
    ),
}
_IMAGE = re.compile(r"!\[(?:\\.|[^\]\\])*\]\(([^)\s]+)\)")
_MISSING = (re.compile(r"File `([^']+)' not found"), re.compile(r'The font "([^"]+)" cannot be found'))
_INSTALL = "install pandoc and a LaTeX with lualatex (the get-started guide's optional step)"


def _font_options(directory: Path, kind: str) -> list[str]:
    regular, bold, italic, bold_italic = _FONTS[kind]
    options = f"Path={directory}/,BoldFont={bold},ItalicFont={italic},BoldItalicFont={bold_italic}"
    return ["-V", f"{kind}font={regular}", "-V", f"{kind}fontoptions={options}"]


def _failure(stderr: str) -> Exception:
    """``PandocMissing`` for a missing package or font, naming it; ``PdfFailed`` with LaTeX's error line otherwise."""
    for pattern in _MISSING:
        found = pattern.search(stderr)
        if found:
            return PandocMissing(f"lualatex lacks {found.group(1)}: install it, or {_INSTALL}")
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    error = next((line for line in lines if line.startswith("!") or "Error" in line), lines[-1] if lines else "")
    return PdfFailed(f"the PDF wasn't made: {error}")


def to_pdf(report_path: str) -> str:
    """Make ``report.pdf`` beside a report's Markdown, with pandoc and lualatex (0018, 0059 item 8).

    Parameters
    ----------
    report_path
        The report's Markdown file; its figures are in its directory.

    Returns
    -------
    str
        The PDF's path: the report's, with the suffix ``.pdf``.

    Raises
    ------
    PandocMissing
        When pandoc or lualatex isn't found, or lualatex lacks a package or font; it says what to install.
    PdfFailed
        When a figure is missing, or lualatex stops for any other reason (with LaTeX's error line), or pandoc
        couldn't place a figure.
    """
    for tool in ("pandoc", "lualatex"):
        if shutil.which(tool) is None:
            raise PandocMissing(f"a PDF needs {tool}, which isn't found: {_INSTALL}")
    report = Path(report_path)
    text = report.read_text(encoding="utf-8")
    figures = sorted(set(_IMAGE.findall(text)))
    for name in figures:
        if Path(name).is_absolute() or ".." in Path(name).parts or not (report.parent / name).is_file():
            raise PdfFailed(f"the report's figure {name} is missing from {report.parent}")
    fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    with tempfile.TemporaryDirectory(prefix="ema-pdf-") as tmp:
        work = Path(tmp).resolve()
        if set(str(work)) & set("%#~ "):
            raise PdfFailed(f"the temporary directory's path {work} has a character lualatex can't take")
        (work / "fonts").mkdir()
        for name in _FONTS["main"] + _FONTS["mono"]:
            shutil.copyfile(fonts / name, work / "fonts" / name)
        (work / "report.md").write_text(text, encoding="utf-8")
        for name in figures:
            (work / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report.parent / name, work / name)
        command = [
            "pandoc",
            "report.md",
            "-f",
            READER,
            "--pdf-engine=lualatex",
            "-V",
            "geometry:margin=2cm",
            *_font_options(work / "fonts", "main"),
            *_font_options(work / "fonts", "mono"),
            "-o",
            "report.pdf",
        ]
        try:
            done = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=PDF_TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired as error:
            raise PdfFailed(f"the PDF wasn't made in {PDF_TIMEOUT_S} s") from error
        if done.returncode != 0 or not (work / "report.pdf").is_file():
            raise _failure(done.stderr)
        if "Could not fetch resource" in done.stderr or "Could not convert image" in done.stderr:
            raise PdfFailed(f"a figure is missing from the PDF: {done.stderr.strip()}")
        out = report.with_suffix(".pdf")
        shutil.copyfile(work / "report.pdf", out)
    return str(out)
