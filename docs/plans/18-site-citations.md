# 18. Citations off the documentation site

**Status:** done, for the owner's review (2026-10-28). **Approved:** 2026-10-27, by the owner; both questions answered yes. **Branch:** `build-18-site-citations`. **Updated:** 2026-10-27.

## Goal

The published site (`https://paulcon.github.io/EMA/`) shows no record id, spec id, spec file name, or section mark
on any page, and its build fails if one gets through; the repository keeps every citation, each in parentheses.

## Implements

- Record 0089, items 1–5: the site cites nothing (reference model ids kept, as names); citations in parentheses in
  `ema`'s docstrings and comments and in the guides; `docs/conf.py`'s filter (docstrings, guides, `index.md`, the
  guides' metadata paragraph, no published sources); the build's check, with its allowlist.
- Record 0088 item 1, as amended by 0089 (the site's content); record 0090 (build steps, review rounds, and layers
  are citations), accepted during the step.
- CLAUDE.md's and `CONTRIBUTING.md`'s "Cite ids" (0089).

## Out of scope for this step

- The guides' full text (step 17, under 0089 item 2's rule); here they are reworded only where an id is a word of a
  sentence, or a spec is named where the reader is sent to it.
- Tests' docstrings and comments, and the specs, records, plans, and notes: none is on the site.
- Text users see outside the site: already cites none (0086 item 6, 0087 item 2; `tests/unit/test_record_ids.py`,
  unchanged).
- Redeploying the site: the owner starts `docs.yml` after the merge (0088 item 2).

## Measured before the step (2026-10-27, on `main` at 11e6c93)

Counted with a draft of item 3's filter, on the site as built and on the source:

| Where | Citations | Left after the filter (to reword) |
|---|---|---|
| The site, the API reference's 57 pages and `index.md` | about 2,150 | about 370 |
| The site, the four guides | about 190 | about 50 |
| `ema`'s docstrings, published or not | | about 410 |
| `ema`'s comments | | about 60 |

The pages with the most left: `ema.store.store` (55), `ema.types.results`, `ema.runner`, `ema.workspace` (about
25 each), `ema.diagnostics.base`, `ema.approval` (20 each), `ema.types.runs` (18), `ema.mcp.server`,
`ema.diagnostics.polynomial_model` (16 each). Code lines exclude docstrings and comments, so `scope.md`'s source-line
budget is not touched.

## Tasks

1. **Tests first** (shown for review before any code): `tests/unit/test_site_citations.py`, importing the extension
   from `docs/_ext/`.
   - `strip_citations`, known answers from 0089's Context: "writes it (0015)." → "writes it."; "does (designs.md,
     Generators; C20-C27)." → "does."; "(RequestError; 0061, 0062)" → "(RequestError)"; "(§3.3)" dropped; a
     parenthesis spanning lines ("(records 0034,\n0035, 0038)") dropped whole; a code comment's "# not re-exported by
     `ema` (architecture.md §2)" → "# not re-exported by `ema`"; and kept as they are: "(R2, Ishigami)",
     `path("R2")`, "0.0001", "10000000", "2.0.0.dev1", "2026-10-27", "T(k)", "(x1)", "(m/s)".
   - The guides' metadata paragraph → "**Status:** outline."; a guide without one is unchanged.
   - `find_citations`: finds "only W6 deletes", "records 0034", "data_model.md", "§3", "CL2"; finds none of the kept
     cases above, nor an allowlisted entry; agrees with `test_record_ids.py`'s `test_the_pattern` on every case it
     lists, but the bare ids 0089 item 1 adds.
   - The source check (question 2): every docstring and comment in `src/ema/`, after `strip_citations`, has no
     citation `find_citations` finds; in the fast tier, under a second.
   - A negative control, in the slow tier: a tiny Sphinx project in a temporary directory, with the extension and a
     docstring whose citation is a word of the sentence; `sphinx-build -W --keep-going` exits nonzero and names the
     page; without it, exits 0. (This also confirms that a warning raised at `build-finished` fails a `-W` build; if
     it doesn't, the check moves to `env-check-consistency`, or to a `doctree-resolved` scan, and the plan's notes say
     so.)
2. **The extension,** `docs/_ext/ema_citations.py` (Ruff's rules; not in `ema`, so outside mypy's `files` and the
   budget): `strip_citations`, `find_citations`, the allowlist (each entry with its reason), and `setup(app)`
   connecting `autodoc-process-docstring`, `source-read` (the guides and `index`), and `build-finished` (every `.html`
   page's text, code included, and `searchindex.js`). `docs/conf.py` adds `docs/_ext` to `sys.path`, loads it, sets
   `html_copy_source = False` and `html_show_sourcelink = False`, and its docstring cites 0089.
3. **Build, and list what the check finds.** The first build fails with the list of the inline citations; the
   plan's notes record its count by page against the table above.
4. **Reword, package by package,** each citation into a parenthesis at the end of its clause or sentence, keeping
   what the sentence says (0089 item 2); in this order, with a docs build after each: `ema.store`, `ema.types`,
   `ema.runner` and `ema.approval`, `ema.workspace`, `ema.diagnostics`, `ema.mcp` and `ema.cli`, `ema.models`,
   `ema.designs`, `ema.numerics`, `ema.plotting` and `ema.report`, `ema.reference_models`, `ema` itself. Then the
   guides and `index.md`: a sentence that sends the reader to a spec links it on GitHub in words ("the model
   interface spec"). Then the private docstrings and comments the site doesn't show (question 1), until the source
   check passes.
5. **A fresh agent's review** of the rendered site (every page) and of 40 reworded docstrings drawn at random: does
   any page cite, read oddly where a citation was dropped, or lose meaning; does any reworded docstring say something
   its old text didn't. Fixes, and a second round if the first finds anything major (the owner's rule: rerun until
   the findings are minor).
6. **`STATUS.md`** (Done; Now), `TODO.md` (step 18 checked), this plan's status and notes.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`: the fast tier under 90 s (0086 item 2), with the new unit tests.
- `uv run pytest -q --slow -n auto`: both tiers, the negative control included.
- `uv run ruff check && uv run ruff format --check && uv run mypy`.
- `uv run sphinx-build -W --keep-going docs docs/_build/html`: passes, its check included; no file in `_sources/`
  (Sphinx 9.1 makes the directory, empty).
- `ema`'s code lines against `scope.md`'s 12,000 (unchanged by design; measured to confirm).
- `git diff main --stat -- src/` touches docstrings and comments only: an AST comparison of every changed module,
  docstrings removed, matches `main`'s.

## Stop condition

The checks pass and the review's findings are minor. Stop on the branch, report the counts and the review, and wait
for the owner's review; the owner merges, and starts `docs.yml`.

## Questions for the owner

Answered 2026-10-27:

1. **The private docstrings and comments** (about 100 rewordings of the 470), which 0089 item 2's rule covers but
   the site's check can't see: **reworded in this step** (task 4).
2. **A source check for them:** **added**, a fast-tier test that runs `find_citations` over every docstring and
   comment in `src/ema/` after `strip_citations` (task 1), so a new private docstring can't break the rule unseen.
   0089 decides only the site's check; this test is one the record allows.

## Notes

- **Tasks 1–2** (2026-10-27): the tests, reviewed by the owner before the code, then `docs/_ext/ema_citations.py`
  (163 lines). One case added after review: a Markdown link's target (`[words](page.md)`) is not a parenthesis, and
  the check doesn't read it, nor a URL. Sphinx 9.1 counts a warning raised at `build-finished` before it sets the exit
  status, so `-W` fails the build there (no fallback needed); it makes `_sources/` even with `html_copy_source`
  false, empty, so the check is "no file in `_sources/`". A warning names its page in the message: as a `location`,
  Sphinx reads the path as a document name.
- **Task 3, the first build with the check:** 399 citations on 43 pages, against the estimated 420. The most:
  `ema.store.store` 55, `ema.types.results` 28, `ema.workspace` and `ema.runner` 25 each, `ema.types.runs` and
  `ema.approval` 20 each, `ema.diagnostics.base` 19, `ema.mcp.server` 16, `ema.diagnostics.polynomial_model` 14;
  the guides 25 (`add_a_diagnostic` 9, `get_started` 7, `run_a_diagnostic` 6, `add_a_model` 3), `index.md` 8. The
  source check: 477 citations in 52 files (`store/store.py` 81, `runner.py` 46, `types/results.py` 31). Look-alikes
  to decide in task 4: `report.md`, the file a user opens (allowlisted if it stays), and `tools.md`, `ema.mcp`'s
  data file, named in comments.
- **Task 4** (2026-10-27): 469 citations reworded in 52 files of `src/ema/` (385 lines added, 342 removed; code
  unchanged, by an AST comparison of every file with `main`), by five agents in parallel on disjoint packages, and
  the guides by hand (a guide that sends its reader to another links it; one that sends a reader to a project file
  links it on GitHub, in words). Found on the way: Ruff's D401 had skipped summaries that began with an id, so
  about 30 moved to the imperative ("Return …", "Check …"); napoleon reads "words: words" in a `#:` comment as a
  type and a description, so the filter runs before it (priority 400; a case in the slow control); a `noqa`
  comment's rule codes aren't read (`S110`); `V32` and `S32` (numpy dtype codes) allowlisted. Code lines: 11,040,
  as on `main`. The docs build passes; both tiers pass (2,201 passed, 1 skipped).
- **`searchindex.js` isn't scanned** (task 2 said it would be): its text is the pages', already checked, and it
  holds the guides' source file names (`guides/get_started.md`), which aren't citations a visitor reads.
- **Review round 1** (task 5; a fresh agent; every page, 40 docstrings drawn with `random.Random(18)`, the 140
  dropped parts that hold words): no page cites; the sample adds or drops no claim, and every id is still cited.
  Fixed: the check missed a record id before a full stop ("in 0074."); an unmatched "(" ("(0, 1]") stopped the
  filter for the rest of a text (both with tests); three dropped parts a reader needs (`types/model.py`,
  `Workspace.run`'s `space`, `types/results.py`); wording in `runner.py`, `mcp/server.py`, `designs/lines.py`,
  `workspace/__init__.py`, `diagnostics/base.py`, two titles; `scatter.py`'s S8, S9 back on the sentence they
  support; three guide sentences that named a use case or a guide the cut metadata had introduced.
- **Known limits of the filter,** none met in today's sources: it would drop a parenthesis of id-like data
  ("(T1, T2)"), or one in inline code or math (` ``(P3)`` `, `$f(P1)$`), silently, since the check then finds
  nothing.
- **Asked of the owner** (outside 0089, or already on `main`), 2026-10-28:
  - internal words 0089 item 1 doesn't list ("step 06", "review round 1", "Layer 3b"): **record 0090**, accepted
    2026-10-28 and applied: the filter's and the check's patterns, with 11 known answers (a guide's own "step 6"
    kept); the 13 module summaries that opened with a layer ("The runner, … (layer 3b; …)"); the get-started guide's
    "the PDF build step's"; the source check's helper reads a `#:` comment without its mark, as autodoc does;
  - the site's rendering bugs, already on `main`: **fixed in this step.** Napoleon's "Type:" lines on 34 attribute
    and property entries: `docs/_ext/ema_inline_types.py` restores a docstring napoleon gave an inline type (EMA's
    docstrings give none), with a case in the slow control; autosummary's cut at "..." in eight summaries: "…";
    `Provenance`'s four version attributes, one line each; `run_a_diagnostic`'s raw `<reason>`, in a code span.
- **Review round 2** (a fresh agent; round 1's fixes, every page read fresh, 0090's patterns, the inline-types
  extension): no page cites; 0090's patterns drop only build steps, review rounds, and layers; round 1's fixes hold.
  Fixed: the slow control didn't exercise `ema_inline_types` (its attribute's colon was in a dropped parenthesis):
  an attribute with a colon outside one, and fast tests of the two handlers (the control now fails without the
  extension, checked); a quotation's semicolon split its part (`figures.save`); two more summaries cut at "...";
  two one-letter descriptions docutils read as a list; `LineAnalysis`'s `n, K`; `WORKER`'s value, the builder's
  absolute path (`:meta hide-value:`); `index.md`'s captions, one per table; four guide pointers. Known limit, with
  a test: a guide's own step 10 or later reads as a build step. Left for the owner: v1 provenance ("Ported from
  EMA v1", five pages) and `ema.types.identity`'s chronology; words outside 0089 and 0090 ("glossary", "the slow
  tier's", "the handshake era"); `ema.report.render`'s page shows the function; `Bootstrap.settings`'s Examples
  as a heading; `ema.report.pdf`'s "--" as a dash; `INK` and `MUTED`'s shared comment. Both tiers pass (2,221
  passed, 1 skipped).
- **Review round 3** (a short one, on round 2's fixes and any major issue): none major. Fixed: quotation marks
  count in `_parts` only when they pair up (an odd `"`, as in "a 6\" pipe", or a “ without its ”, would have let one
  part swallow the rest of its parenthesis), and “curly” ones count too, with tests; the index's first table's
  caption; a test of `ema_inline_types`'s guard for a docstring's own type. Not taken: rewording `figures.save` to
  say the card holds each panel's axes and values, since `save` adds only the figure's name (the caller gives the
  rest). Known limit added: a citation nested in a parenthesis inside a quotation is dropped from the quotation.
- **At the end:** 469 citations reworded, and 13 layer summaries, in 52 files of `src/ema/` (code unchanged, by AST;
  11,040 code lines, as on `main`); the four guides and `index.md`; two extensions in `docs/_ext/` (`ema_citations`,
  `ema_inline_types`); 95 fast tests and 2 slow ones. Three review rounds, the last with nothing major.
