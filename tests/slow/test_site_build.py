"""The docs build fails on a citation left on a page (slow tier; record 0089 item 4; plan 18, task 1).

A negative control: a tiny Sphinx project in a temporary directory, with ``ema_citations`` and one module, built with
``-W --keep-going`` as the docs command builds the site. A citation that is a word of a sentence fails the build and
names its page; the same docstring citing in parentheses builds, and its page shows no citation.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]

CONF = f"""
import sys
sys.path.insert(0, {str(ROOT / "docs" / "_ext")!r})
sys.path.insert(0, {{here!r}})
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "ema_citations", "ema_inline_types"]
html_copy_source = False
html_show_sourcelink = False
"""

INDEX = """Toy
===

.. automodule:: toy
   :members:
"""


def build(tmp_path: Path, docstring: str) -> subprocess.CompletedProcess[str]:
    # An attribute's docstring with a colon in its parenthesis: napoleon would read it as a type and a description.
    attribute = "#: Rows per statement when reading many (§6, §8: Q1, Q7).\nROWS = 1000\n"
    # And one whose colon is outside any parenthesis, which napoleon itself would read as a type (ema_inline_types).
    attribute += "\n#: The largest design built: more points are refused.\nMAX = 10\n"
    (tmp_path / "toy.py").write_text(
        f'"""{docstring}"""\n\n{attribute}\n\ndef f():\n    """Return one (C5)."""\n    return 1\n'
    )
    (tmp_path / "conf.py").write_text(CONF.format(here=str(tmp_path)))
    (tmp_path / "index.rst").write_text(INDEX)
    cmd = [sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", str(tmp_path), str(tmp_path / "_build")]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_a_citation_in_a_sentence_fails_the_build(tmp_path):
    done = build(tmp_path, "The toy store. Only W6 deletes its rows.")
    assert done.returncode != 0
    assert "W6" in done.stderr and "index" in done.stderr


def test_citations_in_parentheses_build_and_are_dropped(tmp_path):
    done = build(tmp_path, "The toy store. Only deleting a result removes its rows (W6; data_model.md §3).")
    assert done.returncode == 0, done.stderr
    page = (tmp_path / "_build" / "index.html").read_text(encoding="utf-8")
    assert "removes its rows." in page and "Return one." in page and "Rows per statement when reading many." in page
    assert "The largest design built: more points are refused." in page
    assert not [c for c in ("W6", "data_model", "C5", "§", "Q1") if c in page]
    # No type read from the attribute's first line, which holds a colon (ema_inline_types).
    assert ">Type<" not in page
    # Sphinx 9.1 makes an empty _sources/ even when it copies no source.
    assert not [p for p in (tmp_path / "_build").glob("_sources/**/*") if p.is_file()]
