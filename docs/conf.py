"""Sphinx configuration: the guides and the API reference (record 0059, item 5).

Built locally with ``uv run sphinx-build -W --keep-going docs docs/_build/html``; published at
https://paulcon.github.io/EMA/ by ``.github/workflows/docs.yml``, started by hand (record 0088), without its citations
(record 0089: ``_ext/ema_citations.py``). The design documents, decision records, notes, plans, and step 11's checks
are excluded: they are read in the repository.
"""

import importlib.metadata
import sys
from pathlib import Path

# The site's own extensions: citations dropped, and the build failed on any left (record 0089); and no inline type
# read from an attribute's first line (plan 18).
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))

project = "EMA"
author = "Paul G Constantine"
copyright = "2026, Paul G Constantine"
release = importlib.metadata.version("ema")
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "ema_citations",
    "ema_inline_types",
]

# No page's source is published: a guide's Markdown holds its citations (record 0089 item 3).
html_copy_source = False
html_show_sourcelink = False

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
root_doc = "index"
exclude_patterns = [
    "_build",
    "design",
    "decisions",
    "notes",
    "plans",
    "checks",
    "README.md",
]

# The guides cite the design documents by relative path, as code, not as links.
myst_heading_anchors = 3

# The API reference: one page per module, generated from the docstrings into docs/_autosummary/ (ignored by git).
autosummary_generate = True
autodoc_default_options = {"members": True, "show-inheritance": True}
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_class_signature = "mixed"
autodoc_preserve_defaults = True

# NumPy-style docstrings. A dataclass's fields are described once, in its "Attributes" section (rendered as
# fields of the class, not as separate entries): autodoc documents no undocumented members.
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_ivar = True
napoleon_use_rtype = False

html_theme = "furo"
html_title = f"EMA {release}"
