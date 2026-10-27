# EMA v2 status

**Updated:** 2026-10-27. Update this file at the end of every step, in the same commit as the work.

## Now

- **The demo build (records 0066–0087), merged into `main` (be08260); the `demo` branch deleted
  (2026-10-27):** every build step of the roadmap (01–16, and T, the rest of `ema.types`), built autonomously and
  reviewed by independent agents; the six diagnostics, the workspace (U1–U8; the get-started guide passes), the CLI
  (`ema`), and the MCP server (`ema mcp --root DIR`), checked end to end through a real MCP client. Records
  0066–0087 are accepted and applied to the specs. EMA `2.0.0.dev1`; 11,040 code lines of a budget of 12,000
  (0084, 0086); the fast tier 50–70 s of a 90 s budget (0086); every test passes (2,127 in the slow tier). Log of
  every wave and review round: `docs/notes/demo_build.md`. The demo's instructions: `docs/notes/demo_mcp.md`; its
  root, `~/ema_demo`, rebuilt under `2.0.0.dev1` with four models loaded, and reset by
  `docs/notes/demo/reset_demo.sh`, which moves the earlier workspace and exports to `archive/` in the root (now
  `ema_workspace.pre0086/`, `exports.pre0086/`, and one workspace of the four loadings only). Not done: step 17's
  guides' full text and the release.
- Writing the design documents by hand (`TODO.md`): steps 1–13 done.
- "Before the first line of code" (`TODO.md`) done: the specs checked against each other, and the contradictions
  resolved (records 0061–0064). The first plan written: `docs/plans/01-scaffolding-and-designs.md`
  (approved; its six questions answered, four of them as record 0065, accepted and applied); a draft
  order of the later steps in `docs/notes/build_roadmap.md`.

## Done

One line per step; what each decided is in its records (`docs/decisions/README.md`, the index).

- 2026-09-27: lessons learned from v1 (`docs/notes/v1/lessons_learned_2026-09-27.md`, and its answers).
- 2026-09-28: data model template, architecture draft, and this skeleton; OD-1 (record 0002).
- 2026-09-29: step 1, purpose, principles (P1–P7), and glossary accepted; records 0003–0005, 0007–0009.
- 2026-09-29: step 2, use cases accepted (U1–U8); records 0010, 0011.
- 2026-09-29: step 3, scope accepted, with size budgets; records 0001, 0002, 0006, 0012–0021 (U9
  with 0016).
- 2026-09-30: step 4, model interface accepted (M1–M20); records 0022–0031.
- 2026-09-30: step 5, designs accepted (G1–G17); records 0032, 0033.
- 2026-09-30: step 6, diagnostic specs accepted (`shared.md`, S1–S10, and the six diagnostics); records
  0034–0040.
- 2026-10-01: step 7, uncertainty (V1–V7) and contracts (C1–C56) accepted; records 0041, 0042.
- 2026-10-01: consistency review of every design document by ten independent reviewers
  (`docs/notes/consistency_review_2026-10-01.md`): plain errors corrected in place; records 0043–0052 accepted
  and applied; `docs/design/export.md` added (empty); OD-15 and OD-19 decided (0050).
- 2026-10-01: export spec accepted (`docs/design/export.md`, E1–E7), from an interview; record 0053 (the `ema_`
  prefix reserved, M21; export through MCP).
- 2026-10-01: step 8, data model accepted (`docs/design/data_model.md`: Q1–Q12, W1–W6, I1–I12), from an
  interview and an independent consistency check; records 0054 (the reuse key, a result's own approval, the
  latest loading of a name) and 0055 (replay from a provenance, ids in reports, 0054's example), applied to
  `contracts.md` (C46–C52 and C56 cite I1–I12), `shared.md`, `coordinate_lines.md`, `model_interface.md`,
  and the glossary.
- 2026-10-01: step 9, architecture accepted (`docs/design/architecture.md`: layers, architecture rules
  AR1–AR7, every module's public names; 19 workspace names, 13 CLI commands, 10 MCP tools; about 7,860 source
  lines estimated), from an interview and four independent consistency reviews (31, 17, 15, then 11 findings,
  all fixed); OD-16 decided; record 0056 (the layers as architecture rules, a `Workspace` object, figures as
  MCP resources, the use cases typed against the workspace, store reads Q13–Q15, a `Store` per thread),
  applied to `principles.md`, `use_cases.md`, `data_model.md`, `contracts.md`, `model_interface.md`, the
  README, and 0016's status.
- 2026-10-01: step 10, trust boundary accepted (`docs/design/trust.md`: who is trusted, what needs a yes,
  rules T1–T10), from an interview and five independent consistency reviews (28, 26, 21, 10, then 8
  findings, all fixed); record 0057 (a model's allowlisted environment with `pass_env`, for both kinds of
  model; `ema mcp --root`, required; a spec's paths and strings checked; the first approval shows the
  environment; text EMA didn't write escaped; the held principle answered by T1–T10; "model" as the one
  word, with no glossary row), applied to `model_interface.md`, `principles.md`, `glossary.md`, `scope.md`,
  `architecture.md` (about 7,940 source lines), `use_cases.md`, `export.md`, `data_model.md`,
  `diagnostics/shared.md`, `contracts.md`, the guide outlines, `CLAUDE.md`, and 0029's status.
- 2026-10-01: step 11, reference models accepted (`docs/design/reference_models.md`): every expected answer
  in the six diagnostic specs recomputed by separate scripts (`docs/checks/`, from the specs: quadrature,
  exact rational arithmetic, quasi-Monte Carlo, and v1 as a second source), with three independent reviews
  (6, 2, then 2 findings, all fixed); about 20 plain errors corrected in place (brute-force values replaced by
  quadrature, expected values printed to the digits their tolerances need, R1 along c a constant line, R3's
  coordinate-line rates filled); record 0058 (R7's kink-line row dropped for R10's two given lines; R3's
  rate tolerance 2·10⁻⁴; R11's 9.6·10⁻⁴).
- 2026-10-01: step 12, repository and tooling, from an interview and three independent reviews (21, 14, then 9
  findings, all fixed); OD-17 and OD-18 decided; record 0059 (Python 3.13 and newer, developed on 3.14; uv and
  `uv.lock`; Ruff, mypy, import-linter, pytest; a Sphinx site built locally; checks on GitHub Actions started by
  hand, Linux on 3.14 and on 3.13 at the lowest bounds; PDFs with lualatex and matplotlib's DejaVu fonts,
  `PdfFailed`; import-linter sees standard-library imports), applied to `CLAUDE.md` (the commands),
  `architecture.md`, `contracts.md`, `trust.md`, `scope.md`, `TODO.md`, and 0018's status. uv and its Pythons
  installed on this Mac (staged steps; an old `~/pyvenv.cfg` renamed, which had hidden uv's Pythons).
- 2026-10-01: step 13, guides as outlines (`docs/guides/`: get started, add a model, run a diagnostic, add a
  diagnostic), each walked through `ema.workspace` on paper (no new workspace function), from an interview; record
  0060 (install from GitHub with uv; get started in Python, its blocks tested on R2 under C53;
  `ema.reference_models.path` gives the model spec; `ema report` prints its path on stderr; add-a-diagnostic for
  outside contributors too; the MIT license, `LICENSE`; C53–C55 accepted), applied to `architecture.md`,
  `contracts.md`, `trust.md`, `model_interface.md`, `reference_models.md`, `docs/plans/_template.md`, `README.md`,
  `TODO.md`, and the decisions index; three independent reviews (28, 11, then 9 findings, all fixed).
- 2026-10-01: the specs checked against each other before code, by eight independent reviewers (76 findings),
  then three rounds on the fixes (33, 9, then 7; `docs/notes/consistency_review_2026-10-01_before_code.md`):
  plain errors corrected in place; records 0061 (a `seed` parameter for every diagnostic; "user", not
  "analyst"; generators called with a design's identity; model parameter values hashed as doubles; the map
  back to unit coordinates; `ema.cli` over `ema.mcp`; the stderr tail in `RunInfo`; `remove_tree`; and smaller
  rules), 0062 (golden points across machines compared in unit coordinates; replays from the stored runs'
  points; five details for step 01), 0063 (a design's structure stored with its result; the rebuild check per
  range; `duration()`'s edges), and 0064 (the source-line budget raised to 8,300; `architecture.md` §11 about
  8,200), applied to the specs and guides; "amended by" marks on 0006, 0010, 0017, 0028, 0031, 0035, 0036,
  0042, 0044, 0049, 0056, 0058, 0061, and 0062.
- 2026-10-01: plan 01 written (`docs/plans/01-scaffolding-and-designs.md`), with a draft roadmap of the later
  build steps (`docs/notes/build_roadmap.md`), after three independent reviews (22, 17, then 8 findings, all
  fixed); its questions answered by the owner; record 0065 (`unregister` in every registry; malformed design
  requests refused, G18; four more words in the terminology test; a given line's anchor at the geometric center
  and its direction as given), applied to `architecture.md`, `designs.md`, `contracts.md`, the glossary, and
  0008's status.
- 2026-10-01–02: the demo build on `demo` (record 0066): steps 01–16 and T built in waves, each reviewed and fixed
  by independent agents; provisional choices in records 0067–0082 and 0084; the final integrated review and the
  demo's rehearsal passed; record 0085 (a fit's in-sample measures as observations) after the owner's rehearsals.
- 2026-10-02: records 0066–0085 accepted by the owner (0084's budget raised to 11,000) and applied to the specs
  (f012505); reviewed in two rounds by fresh agents (2 major, 20 minor, 25 nits; then 1 major, 6 minor, 15 nits),
  the plain findings fixed in place, the rest as record 0086, answered by the owner in an interview.
- 2026-10-03: records 0086 (the budgets 12,000 source lines and a 90 s fast tier; model names; `files` and
  `pass_env` sorted before hashing; notes' line breaks; no ids in text users see; one per-level key; the version
  raised when a diagnostic's output changes, `2.0.0.dev1`; `python -m ema.mcp` kept; and smaller items) and 0087
  (three follow-ups from its review) accepted and applied; the demo root rebuilt; `demo` pushed to GitHub.
- 2026-10-27: the GitHub repository moved to `paulcon/EMA` (the old account and its `EMA-v1` deleted; v1 is
  local only, at `../EMA-v1`); `demo`, merged into `main`, deleted.
- 2026-10-27: record 0088 (the Sphinx site published at `https://paulcon.github.io/EMA/` by
  `.github/workflows/docs.yml`, started by hand from `main`), applied to `docs/conf.py`, `README.md`,
  `pyproject.toml`'s `[project.urls]`, and 0059's status (5f1c6e9). Its three staged steps run the same day, at the
  owner's request: `main` pushed, Pages turned on with Actions as its source, and the site first deployed by run
  40585077681 (55 s; an earlier run's deploy failed with GitHub's 500, and its rerun on the artifact's metadata);
  `paulcon.github.io` itself unchanged.

## Next

- Step 18: citations off the documentation site (record 0089), its plan `docs/plans/18-site-citations.md`; then
  step 17.
- Step 17: the guides' full text and the release.
- The BLAS question for `ema.numerics` is settled (`docs/notes/blas_determinism_2026-10-01.md`; record 0068 item 1,
  accepted: no 1-D BLAS products or norms).

## Specs

| Spec | Status |
|---|---|
| `docs/design/purpose.md` | accepted |
| `docs/design/principles.md` | accepted |
| `docs/design/glossary.md` | accepted |
| `docs/design/scope.md` | accepted |
| `docs/design/use_cases.md` | accepted |
| `docs/design/model_interface.md` | accepted |
| `docs/design/designs.md` | accepted |
| `docs/design/diagnostics/` | accepted: `shared.md` and the six diagnostics |
| `docs/design/uncertainty.md` | accepted |
| `docs/design/contracts.md` | accepted (C53–C55 with the guides, 0060) |
| `docs/design/data_model.md` | accepted (Q1–Q15, W1–W6, I1–I12) |
| `docs/design/architecture.md` | accepted (AR1–AR7) |
| `docs/design/trust.md` | accepted (T1–T10) |
| `docs/design/export.md` | accepted (E1–E7) |
| `docs/design/reference_models.md` | accepted (the expected answers checked by `docs/checks/`) |

Statuses: empty → draft → accepted (a template is filled in to become a draft; guides are outlines until the
code exists). Claude Code builds only from accepted specs.

## Open decisions

> One row per decision still to make. When you decide one:
> 1. write a decision record in `docs/decisions/`;
> 2. update the specs it affects;
> 3. move the row to "Decided" below.
>
> Do all three in one commit (`docs/decisions/README.md`). "Blocks" lists the steps of the TODO that can't
> finish without it.

| Id | Question | Options | Suggested | Blocks |
|---|---|---|---|---|
| — | none open | | | |

## Decided

What each decided is the record's title (`docs/decisions/README.md`).

| Id | Record | Date |
|---|---|---|
| OD-1 | 0002 | 2026-09-28 |
| OD-2 | 0006 | 2026-09-29 |
| OD-3 | 0003, 0005 | 2026-09-29 |
| OD-4 | 0004 | 2026-09-28 |
| OD-5 | 0012 | 2026-09-29 |
| OD-6 | 0014 | 2026-09-29 |
| OD-7 | 0016, 0019 | 2026-09-29 |
| OD-8 | 0017 | 2026-09-29 |
| OD-9 | 0022 | 2026-09-30 |
| OD-10 | 0023 | 2026-09-30 |
| OD-11 | 0026 | 2026-09-30 |
| OD-12 | 0040 (amended by 0041) | 2026-09-30 |
| OD-13 | 0032 | 2026-09-30 |
| OD-14 | 0013 | 2026-09-29 |
| OD-15 | 0050 | 2026-10-01 |
| OD-16 | 0056 | 2026-10-01 |
| OD-17 | 0059 | 2026-10-01 |
| OD-18 | 0059 | 2026-10-01 |
| OD-19 | 0050 | 2026-10-01 |
| OD-20 | 0027 | 2026-09-30 |
