# 18. Citations off the documentation site

**Status:** approved (2026-10-27, by the owner; both questions answered yes). **Branch:** `build-18-site-citations`. **Updated:** 2026-10-27.

## Goal

The published site (`https://paulcon.github.io/EMA/`) shows no record id, spec id, spec file name, or section mark
on any page, and its build fails if one gets through; the repository keeps every citation, each in parentheses.

## Implements

- Record 0089, items 1–5: the site cites nothing (reference model ids kept, as names); citations in parentheses in
  `ema`'s docstrings and comments and in the guides; `docs/conf.py`'s filter (docstrings, guides, `index.md`, the
  guides' metadata paragraph, no published sources); the build's check, with its allowlist.
- Record 0088 item 1, as amended by 0089 (the site's content).
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
- `uv run sphinx-build -W --keep-going docs docs/_build/html`: passes, its check included; no `_sources/` in the
  output.
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

> Filled in during the step.
