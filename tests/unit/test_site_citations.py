"""Citations off the documentation site (record 0089; plan 18).

The site cites nothing (0089 item 1): ``docs/_ext/ema_citations.py`` drops each citation, a semicolon-separated
part of a parenthesis that starts with an id, a spec file name, or a section mark (item 3), and the build fails on
any left (item 4). Here: the filter's known answers, from 0089's Context; the check's; and the source check (plan 18,
question 2), that every docstring and comment in ``src/ema/`` cites only in parentheses (item 2).
"""

import ast
import io
import re
import runpy
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs" / "_ext"))

import ema_citations
from ema_citations import ALLOWED, find_citations, strip_citations, strip_metadata

from tests.unit import test_record_ids

# --- the filter (0089 item 3) ------------------------------------------------------------------------------------

DROPPED = [
    # A parenthesis of citations only goes, with the space before it.
    ("only the main process writes it (0015).", "only the main process writes it."),
    ("What every design generator does (designs.md, Generators; C20-C27).", "What every design generator does."),
    ("the point (G9) and the line", "the point and the line"),
    ("committed before it returns (§3.3); no row", "committed before it returns; no row"),
    ("the store (data_model.md §3.2).", "the store."),
    ("the store (``data_model.md`` §3.2).", "the store."),
    ("the root (`architecture.md` §10).", "the root."),
    ("the guide (../design/trust.md, What needs the user's yes).", "the guide."),
    ("its intervals (V3–V5; 0040, 0041).", "its intervals."),
    ("the cap (record 0070, item 2).", "the cap."),
    ("one line's numbers (CL2-CL6).", "one line's numbers."),
    ("the fit (PM3; LM2).", "the fit."),
    ("a model (M1–M21).", "a model."),
    # A build step, a review round, a layer (record 0090).
    ("the runner (step 07) starts", "the runner starts"),
    ("with the shared types (step T); the runner", "with the shared types; the runner"),
    ("Fork caveat (review round 1): flock", "Fork caveat: flock"),
    ("The runner, a serial loop (layer 3b; 0015; AR4).", "The runner, a serial loop."),
    ("the list (steps 04 and 05; build step 08's).", "the list."),
    # A part that starts with a citation goes whole, words after it included.
    ("its degrees (C5's rate tolerances; C6 leaves both out, contracts.md; record 0077).", "its degrees."),
    # Words in their own part stay, in the parenthesis.
    ("naming both (RequestError; 0061, 0062).", "naming both (RequestError)."),
    ("naming both (0061; RequestError).", "naming both (RequestError)."),
    ("(see f(x); 0032)", "(see f(x))"),
    # A parenthesis may span lines; a newline before it goes too, so the sentence closes up.
    ("Each line (records 0034,\n0035, 0038). Next", "Each line. Next"),
    ("at the end\n(0015). Next", "at the end. Next"),
    # But not a blank line: the parenthesis is then a paragraph of its own, left empty.
    ("one.\n\n(0015)\n", "one.\n\n\n"),
    # A part that goes on in a blockquote, or in a comment, on the next line.
    (
        "> the CLI (`ema.cli` doesn't import it;\n> `architecture.md` §10), and",
        "> the CLI (`ema.cli` doesn't import it), and",
    ),
    ("#   (the environment;\n#   trust.md, What needs a yes)", "#   (the environment)"),
    # An unmatched parenthesis is text, and what follows it is still read.
    ("on (0, 1] the fit (0015).", "on (0, 1] the fit."),
    # A quotation's semicolon doesn't split the part it is in.
    ('the name (shared.md: "the name; each axis").', "the name."),
    ('the name ("the name; each axis"; shared.md).', 'the name ("the name; each axis").'),
    ("the name (shared.md: “the name; each axis”).", "the name."),
    # But only quotation marks that pair up: an odd one is text, and the split is at every semicolon.
    ('x (0015: a 6" pipe; a note kept) y', "x (a note kept) y"),
    ("x (C3: “a; the rest) y", "x (the rest) y"),
    # A code comment.
    (
        "import ema.reference_models  # not re-exported by `ema` (architecture.md §2)",
        "import ema.reference_models  # not re-exported by `ema`",
    ),
]

KEPT = [
    "a reference model (R2, Ishigami)",
    'print(ws.load_model(ema.reference_models.path("R2")))',
    "a tolerance of 0.0001",
    "MAX_DESIGN_POINTS = 10000000",
    "EMA 2.0.0.dev1",
    "on 2026-10-27",
    "log10 T(k): the rate",
    "the coordinate (x1)",
    "in (m/s)",
    "(R9, a real simulator, comes later)",
    "numpy's PCG64 (its default)",
    "(`ema.cli` doesn't import `ema.reference_models`, `architecture.md` §10)",  # words first: kept, then found
    "[the model interface spec](https://github.com/paulcon/EMA/blob/main/docs/design/model_interface.md)",
    "[the next guide](add_a_model.md)",  # a link's target, not a parenthesis
    "except OSError:  # noqa: BLE001, S110  (a stream the model closed)",  # Ruff's rule codes
    "on step 6's result, loaded in step 3 (the Python function's steps 4–6)",  # a guide's own steps (0090)
]


@pytest.mark.parametrize(("text", "expected"), DROPPED)
def test_strip_drops_citations(text, expected):
    assert strip_citations(text) == expected


@pytest.mark.parametrize("text", KEPT)
def test_strip_keeps_words_and_data(text):
    assert strip_citations(text) == text


def test_strip_is_idempotent():
    for text, _ in DROPPED:
        once = strip_citations(text)
        assert strip_citations(once) == once


METADATA = """# Get started

**Status:** outline. **Updated:** 2026-10-02 (0080: a run's shown text). **Use cases:** U1, U5, U9. **Specs:**
`../design/architecture.md` §7–§8, `../design/trust.md`. **Tested:** its blocks run (C53; record 0060).

> Outline now.
"""


def test_the_metadata_paragraph_keeps_its_status_only():
    assert strip_metadata(METADATA) == "# Get started\n\n**Status:** outline.\n\n> Outline now.\n"


def test_the_metadata_paragraph_with_other_fields():
    source = "# Add a diagnostic\n\n**Status:** outline. **For:** EMA's owner (C1),\nand Claude Code.\n\nText.\n"
    assert strip_metadata(source) == "# Add a diagnostic\n\n**Status:** outline.\n\nText.\n"


def test_a_page_without_metadata_is_unchanged():
    source = "# EMA\n\nEMA runs diagnostics.\n\n**Status:** later in the page is not the metadata.\n"
    assert strip_metadata(source) == source


# --- the check (0089 item 4) -------------------------------------------------------------------------------------

FOUND = [
    ("Only W6 deletes a result's rows.", "W6"),
    ("Each line, records 0034, 0035.", "records 0034"),
    ("as data_model.md says", "data_model.md"),
    ("as §3 says", "§3"),
    ("CL2 to CL6 give each line", "CL2"),
    ("AR5 says so", "AR5"),
    ("OD-17 asked", "OD-17"),
    ("its PT1 rows", "PT1"),
    ("C53–C55 test it", "C53–C55"),
    ("see record 7", "record 7"),
    ("as decided in 0074.", "0074"),
    ("step 07 built it", "step 07"),
    ("Layer 5: the command line", "Layer 5"),
    ("in review round 2", "review round 2"),
    ("the PDF build step's list", "build step"),
    ("made at step T", "step T"),
    # A known limit (plan 18, Notes): a guide's own step 10 or later reads as a build step.
    ("see step 10 of this guide", "step 10"),
    ("0074, 0075.", "0075"),
    ("(`ema.cli` doesn't import `ema.reference_models`, `architecture.md` §10)", "architecture.md"),
]


@pytest.mark.parametrize(("text", "citation"), FOUND)
def test_find_finds_citations(text, citation):
    assert citation in find_citations(text)


@pytest.mark.parametrize("text", [t for t in KEPT if "architecture.md" not in t])
def test_find_finds_no_data(text):
    assert find_citations(text) == []


def test_find_finds_no_allowlisted_entry():
    assert all(reason.strip() for reason in ALLOWED.values()), "each allowlist entry gives its reason"
    for entry in ALLOWED:
        assert find_citations(entry) == [], entry


def test_find_agrees_with_the_user_text_test():
    """The patterns agree with ``test_record_ids.py``'s (0089 item 4), on its own cases."""
    cited = ["the point (G9).", "(I2, I4)", "the root (T5; 0057, 0061)", "(see 0019, C55)", "(AR3)", "§8"]
    assert all(find_citations(t) for t in cited)
    assert all(test_record_ids.ANY_ID.search(t) for t in cited)
    assert find_citations("as decided in 0074.") and test_record_ids.ANY_ID.search("as decided in 0074.")
    data = ["R², R2, r2", "(R9, a real simulator, comes later)", "(C)", "(x1)", "(m/s)", "0123456789"]
    data += ["2.0.0.dev1, 1e-12, 600 s, ₀₁₂"]
    assert not any(find_citations(t) for t in data)
    assert not any(test_record_ids.ANY_ID.search(t) for t in data)


def test_every_drop_leaves_nothing_to_find():
    for text, _ in DROPPED:
        assert find_citations(strip_citations(text)) == [], text


# --- docs/conf.py (0089 item 3) ----------------------------------------------------------------------------------


def test_conf_loads_the_extension_and_publishes_no_source():
    conf = runpy.run_path(str(ROOT / "docs" / "conf.py"))
    assert "ema_citations" in conf["extensions"] and "ema_inline_types" in conf["extensions"]
    assert conf["html_copy_source"] is False
    assert conf["html_show_sourcelink"] is False
    assert ema_citations.setup  # the extension's entry point


# --- docs/_ext/ema_inline_types.py (plan 18, review round 1) -----------------------------------------------------


def test_an_inline_type_napoleon_added_is_undone():
    import ema_inline_types as types

    lines = ["The largest design built: more points are refused."]
    types._save(None, "data", "ema.x.MAX", None, None, lines)
    napoleon = ["more points are refused.", "", ":type: The largest design built"]
    types._restore(None, "data", "ema.x.MAX", None, None, napoleon)
    assert napoleon == ["The largest design built: more points are refused."]


def test_other_docstrings_are_left_as_napoleon_made_them():
    import ema_inline_types as types

    function = ["Return one.", "", ":returns: one"]
    types._save(None, "function", "ema.x.f", None, None, list(function))
    types._restore(None, "function", "ema.x.f", None, None, function)
    assert function == ["Return one.", "", ":returns: one"]
    typed = [":type: int", "", "The rows."]  # a docstring's own type stays, as napoleon made it
    types._save(None, "attribute", "ema.x.C.n", None, None, list(typed))
    made = ["The rows.", "", ":type: int"]
    types._restore(None, "attribute", "ema.x.C.n", None, None, made)
    assert made == ["The rows.", "", ":type: int"]
    attribute = ["The rows."]  # napoleon added no type: nothing to undo
    types._save(None, "attribute", "ema.x.C.rows", None, None, attribute)
    after = ["The rows.", ""]
    types._restore(None, "attribute", "ema.x.C.rows", None, None, after)
    assert after == ["The rows.", ""]


# --- the source (0089 item 2; plan 18, question 2) ---------------------------------------------------------------


def _comment_blocks(source: str) -> list[tuple[int, str]]:
    """Each run of comments on consecutive lines, joined, with its first line: a parenthesis may span them."""
    blocks: list[tuple[int, list[str]]] = []
    last = -2
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type != tokenize.COMMENT:
            continue
        line = tok.start[0]
        text = re.sub(r"^#+:?\s?", "", tok.string)  # a "#:" comment is read without its mark, as autodoc reads it
        if line == last + 1 and blocks:
            blocks[-1][1].append(text)
        else:
            blocks.append((line, [text]))
        last = line
    return [(line, "\n".join(texts)) for line, texts in blocks]


def _docstrings(source: str) -> list[tuple[int, str]]:
    nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, nodes) and (doc := ast.get_docstring(node, clean=False)) is not None:
            found.append((getattr(node, "lineno", 1), doc))
    return found


def source_citations() -> list[str]:
    """Every citation left in ``src/ema/``'s docstrings and comments once the filter has dropped the cited ones."""
    found = []
    paths = sorted((ROOT / "src" / "ema").rglob("*.py"))
    assert len(paths) > 60, "the scan found too little"
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for line, text in _docstrings(source) + _comment_blocks(source):
            for citation in find_citations(strip_citations(text)):
                found.append(f"{path.relative_to(ROOT)}:{line}: {citation}")
    return found


def test_the_source_cites_in_parentheses_only():
    found = source_citations()
    assert not found, f"{len(found)} citations that are words of a sentence:\n" + "\n".join(found)
