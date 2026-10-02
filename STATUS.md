# EMA v2 status

**Updated:** 2026-10-01. Update this file at the end of every step, in the same commit as the work.

## Now

- Writing the design documents by hand (`TODO.md`): steps 1–13 done.
- Next: "Before the first line of code" (`TODO.md`): the specs checked against each other, and the first plan.

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

## Next

- "Before the first line of code" (`TODO.md`): a consistency check of the specs, and the first plan
  (`docs/plans/01-…`).
- For the first plan of `ema.numerics`: the coordinate lines' Lanczos basis must be the same bit for bit on
  every call (C7). With numpy on Accelerate (this Mac), the matrix products in its reorthogonalization gave two
  different bases in 50 calls in one process (step 11's round 3 review). Build the basis without BLAS
  reductions, or from the exact Gram basis rounded to doubles and cached per n, and test it.

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
