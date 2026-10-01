# EMA v2 status

**Updated:** 2026-10-01. Update this file at the end of every step, in the same commit as the work.

## Now

- Writing the design documents by hand (`TODO.md`): steps 1–7 done.
- Consistency review of the design documents done (2026-10-01): plain errors corrected in place; ten
  decisions (Q1–Q10) and the inputs for steps 8–10 in `docs/notes/consistency_review_2026-10-01.md`.
- Next: the review's decisions, then step 8, the data model (`docs/design/data_model.md`).

## Done

- 2026-09-27: lessons learned from v1 (`docs/notes/v1/lessons_learned_2026-09-27.md`,
  `docs/notes/v1/lessons_learned_answers_2026-09-27.md`).
- 2026-09-28: data model template (`docs/design/data_model.md`), architecture draft
  (`docs/design/architecture.md`), this skeleton.
- 2026-09-28: OD-1 decided: rebuild in a new repository named `EMA`; v1 kept as `EMA-v1`, tag `v1-final`.
- 2026-09-28: purpose accepted (`docs/design/purpose.md`).
- 2026-09-29: OD-2, OD-3, and OD-4 decided (records 0003–0006); the glossary and the purpose page's wording
  follow them. How decisions are made is summarized in `docs/notes/decision_workflow.md`.
- 2026-09-29: principles accepted (`docs/design/principles.md`, P1–P8; record 0007), from an interview on the
  14 candidates: three dropped, two held for steps 9 and 10. Glossary rows added for "noisy" and "replicate";
  "approval" narrowed to runs.
- 2026-09-29: "sample models" renamed "reference models", ids R1… (record 0009); in the glossary, "simulation
  code" is a standard term for a model, no longer one to avoid.
- 2026-09-29: P8 dropped (record 0008): the terminology test checks only public names and generated text,
  for a short list of words; in prose, the glossary's Avoid column is advice.
- 2026-09-29: glossary accepted (`docs/design/glossary.md`), after a check against the accepted specs and
  records: rows reconciled with P2 and P5–P7; rows added for model spec, point, price, store, failed run,
  input deck, output parser, and heuristic threshold; American spelling. TODO step 1 done: purpose,
  principles, and glossary accepted; OD-3 and OD-4 decided.

- 2026-09-29: use cases accepted (`docs/design/use_cases.md`, U1–U8), from an interview. U1–U4 in full (a
  cheap Python model; a slow command-line simulator; failed runs; a polynomial fit); U5–U8 short (reuse and
  export; a changed model; hidden noise; reproducing a diagnostic result). Open decisions are marked OD-n,
  with the suggested option assumed; the last section lists what the use cases ask of the later specs. New
  "Decide:" lines on TODO steps 6 and 7. Records 0010 (reuse failed runs unless the user asks to retry; the
  glossary's "failed run" row) and 0011 (the point run may repeat a deterministic model; resolves a conflict
  inside P7, and the glossary's "replicate" row). How to add a use case: `docs/notes/adding_a_use_case.md`.
  TODO step 2 done.

- 2026-09-29: scope accepted (`docs/design/scope.md`), from an interview. Records 0001 and 0002 accepted
  (an OD row moves to "Decided" only when its record is accepted). Records 0012–0021 accepted: six
  diagnostics, including a lines diagnostic for random or given lines, and the decay of the polynomial
  model's coefficients (0012, OD-5); quadrature and sparse grids later (0013, OD-14); Python and command-line
  models, no formula models (0014, OD-6); serial runs, ready for parallel and remote runs (0015); an MCP
  server with use case U9 (0016, OD-7), and P1 clarified for MCP clients (0019); no interpretation (0017,
  OD-8); Markdown reports with TeX math, and PDFs through pandoc (0018); model output kept in run
  directories (0020); scalar model predictions of models not declared noisy (0021, settles P7's "Open").
  Size budgets set: 8,000 source lines, 20 workspace names, 15 CLI commands, 10 MCP tools. U7 and the
  use cases' asks of scope updated to match. TODO step 3 done.

- 2026-09-30: model interface accepted (`docs/design/model_interface.md`), from an interview. Records
  0022–0031 accepted: several scalar model predictions per model, each read or missing with its own reason,
  one analyzed per diagnostic evaluation (0022, OD-9); no fixed values or constants: a model parameter a
  space leaves out is held at its nominal value (0023, OD-10); scales in the model parameter space, limits
  (`gt`, `ge`, `lt`, `le`) on the model parameter, checked when a design is built, continuous only (0024);
  a batch Python function (0025); every Python model in an isolated long-lived child (0026, OD-11); regex,
  json, and csv output parsers (0027, OD-20); runs collected from files, `keep` as all, incomplete, or none,
  a stopped run's directory deleted (0028); the model version covers the spec but `keep`, `batch_size`, and
  `timeout_s`, and the files the spec names, hashed before each call; 0015's platform question settled for
  v2.0 (0029); large files stored once, read-only, and linked (0030); a glossary row for "run directory",
  and P3's wording on tracked files (0031). Glossary rows added for limits, scale, and run directory; scope's
  "Running" row allows a batch call; U2's model spec follows the new spec. Requirements M1–M20. TODO step 4
  done.

- 2026-09-30: designs accepted (`docs/design/designs.md`), from an interview. Record 0032 accepted (OD-13):
  uniform points from numpy's PCG64 raw stream (the `random` sampler), behind a sampler interface, with
  Sobol, Halton, Latin hypercube, and minimum-distance samplers listed for later. Record 0033 accepted: a
  space may hold a model parameter at a value other than its nominal; glossary rows for design generator,
  sampler, and nested, and the "model parameter" row amended; the sampler declares the rate its error is
  assumed to fall at. The space is a hyperrectangle with a per-name JSON form; default seed 0; designs capped
  at 10,000,000 points, with seams for chunked designs later; the convergent design's alpha is an error
  factor, n_l = ⌈n_min · alpha^(−l/r)⌉, rounded up exactly; lines evenly spaced end to end in unit
  coordinates, refinable n → 2n − 1; coordinate lines share a centered anchor when n is odd; random lines
  each from their own stream. Requirements G1–G17. TODO step 5 done.

- 2026-09-30: diagnostic specs accepted (`docs/design/diagnostics/`), from interviews, one per diagnostic,
  with the shared parts in `shared.md` (S1–S10): the point run (PT1–PT9), scatter (SC1–SC10), coordinate
  lines (CL1–CL10), lines (LN1–LN9), the linear model (LM1–LM10), and the polynomial model (PM1–PM12), each with
  a computed mock report and expected answers. The reference model list R1–R11 settled first
  (`reference_models.md`, draft until step 11). Records 0034–0040 accepted: observations (0034); constant means
  exactly constant (0035); a result with observations only (0036); no failure map of pairs (0037); coordinate
  lines' Gram spectrum and decay rate as observations (0038); the polynomial model's fit plots, its shadows
  later with the active subspace (0039); OD-12, the interval method per diagnostic (0040). U1's and U7's
  "Decide:" lines settled in scatter's and the point run's specs. TODO step 6 done.

- 2026-09-30: uncertainty and contracts accepted (`docs/design/uncertainty.md`, V1–V7; `docs/design/contracts.md`,
  C1–C56), from an interview. Uncertainty, from record 0040: what a variability interval means; the methods (the
  bootstrap; none; subsampling the levels later; convergence and cross-validation not interval methods); the
  bootstrap's steps; an interval cell says "none" when fewer than 201 of the 1000 resamples are defined
  (`BOOTSTRAP_MIN_DEFINED`); intervals reported as computed, not recentered or clipped; no user settings for the
  method in v2.0; the interval-method interface; the per-diagnostic table, with the share of undefined resamples at
  each fit's minimum. Contracts: only the promises every implementation keeps, each citing the spec requirements it
  generalizes, with a conforming toy and one broken toy per check; diagnostic (C1–C19), design generator (C20–C27),
  sampler, basis, and interval method (C28–C30), model adapter (C31–C45), and, provisional until steps 8, 9, and
  13, store (C46–C52, C56), workspace and MCP (C53–C55); the diagnostic contract runs on run batches built directly
  from a test-only contract model, with the degenerate cases listed; changes of units exact under 2^±40 (numbers
  computed through a logarithm within 10⁻¹²), within 10⁻⁹ under a shift, a large-offset check at 10⁻⁶; test tiers:
  the fast tier's 30 s a size budget (`scope.md`), the slow tier's 10 min a target, with no patched constants.
  README: the V prefix. Checked against the other specs before the commit, and corrected in place: the fast tier's
  budget follows `scope.md`; "constant to rounding" is 0035's 10⁻¹⁵, not 10⁻¹²; C30 keeps only what any interval
  method promises (V1, V3, V4), with four broken toys; the exceptions the diagnostic specs make (no Estimates
  section, the point run's labels and Point row, strips per panel, `degree` with `n_min` given); P2's, P3's, and
  P5's named tests; the sampler's identity (C28); the limit named (C27); facts and citations (1848 × 231, f
  defined, ids); asks of steps 8 and 9. Record 0041 accepted and applied: an estimate's interval may be "none",
  with the reason (the glossary's "estimate" row); the polynomial model's coefficients have bootstrap intervals in
  the result and their data card, not the report; the spawn tag is in the result, not the line under a table
  (`linear_model.md`'s seam); 0040 marked as amended. Checked a third time (2026-10-01) and corrected in place:
  `uncertainty.md` (observations against 0041; LOO's 0/0 case; a Sobol value of "none"; two percentages; V7 over
  scatter too; citation paths) and `contracts.md` (the point run's replicate rows in C2; C1's case at a minimum of
  1; the relative spread under a shift; strips along every axis the specs draw them on, and per line; C30's V1 toy;
  C51's provenance; the declarations C11, C12, and C14 need; C37's failed calls; C47's price and note; S7's 5
  reasons; the figure rules; spawn tags recorded; sharper broken toys); PM5 names the coefficients' intervals.
  Record 0042 accepted and applied: each report with estimates opens its Estimates section with one sentence
  explaining variability intervals (`EXPLAIN_INTERVALS`, `shared.md`, S4), in place of "Not confidence intervals."
  under each table, which the terminology test forbade (the glossary's test allows that one sentence); scatter's
  missing line under its mean and standard deviation table; the mock reports of scatter and the linear and
  polynomial models; `shared.md`'s example of "none"; the glossary's "observation" row. TODO step 7 done.

## Next

- Step 8: the data model (`docs/design/data_model.md`, from its template): every question in its §2 with a
  query; tables matching the model interface and designs specs; each run's host (0015) and run directory
  (0020); model predictions in their own table (0021); invariants I1… for the store contract's C46–C52 and
  C56, and the other asks in `contracts.md` (What this spec asks): the template's I4 against 0010, the store test
  at `tests/contracts/store.py`, a run's failure kind, reason, host, and program path, and whether a stored
  result is reused after a named constant changes; the polynomial coefficients' intervals (0041); and the
  review's "Step 8 inputs" (`docs/notes/consistency_review_2026-10-01.md`).

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
| `docs/design/contracts.md` | accepted (C46–C56 provisional until steps 8, 9, and 13) |
| `docs/design/data_model.md` | template |
| `docs/design/architecture.md` | draft |
| `docs/design/trust.md` | empty |
| `docs/design/reference_models.md` | draft (the list; expected answers at step 11) |

Statuses: empty → draft → accepted (a template is filled in to become a draft; guides are outlines until the
code exists). Claude Code builds only from accepted specs.

## Open decisions

> One row per decision still to make. When you decide one:
> 1. write a decision record in `docs/decisions/`;
> 2. update the specs it affects;
> 3. move the row to "Decided" below.
>
> Do all three in one commit. "Blocks" lists the steps of the TODO that can't finish without it.

| Id | Question | Options | Suggested | Blocks |
|---|---|---|---|---|
| OD-15 | Budgets | per call; per workspace; none in v2.0 | per call | workspace, data model |
| OD-16 | `Workspace` object or module functions | object; functions | object | architecture |
| OD-17 | Python version (the package stays `ema`) | 3.12, 3.13, 3.14 | <…> | setup |
| OD-18 | Tooling | uv and a lockfile; docs in Sphinx or MkDocs; CI | uv; <…> | setup |
| OD-19 | Monthly budget for live evals of the MCP server (0016) | <$ …> | <…> | setup (12); the MCP build step |

The items still open in `docs/design/architecture.md` §12 (the rest are struck, with their records) and the
`<…>` in `docs/design/data_model.md` join this table when you reach those steps.

## Decided

| Id | Decision | Record | Date |
|---|---|---|---|
| OD-1 | Rebuild in a new repository named `EMA`; v1 renamed `EMA-v1` and kept for reference (tag `v1-final`) | 0002 | 2026-09-28 |
| OD-2 | The unit of work is the diagnostic evaluation, with its report; diagnostic campaigns come in a later version | 0006 | 2026-09-29 |
| OD-3 | "Model parameter", "model prediction", and "model output"; the region a design samples is the model parameter space, a property of the design | 0003, 0005 | 2026-09-29 |
| OD-4 | "Variability interval": how much an estimate changes when the runs behind it change; not a confidence interval | 0004 | 2026-09-28 |
| OD-5 | Six diagnostics: point run, scatter, coordinate lines, lines (random or given), linear model, polynomial model (with the decay of its coefficients) | 0012 | 2026-09-29 |
| OD-6 | A Python function and a command-line simulation code; no formula models | 0014 | 2026-09-29 |
| OD-7 | An MCP server in v2.0: run and read, and set up models from specs; P1 clarified for MCP clients; use case U9 | 0016, 0019 | 2026-09-29 |
| OD-8 | No experimental interpretation in v2.0 | 0017 | 2026-09-29 |
| OD-9 | Several scalar model predictions per model, in the spec and code from v2.0; a missing one is NaN with its reason; a diagnostic evaluation analyzes one | 0022 | 2026-09-30 |
| OD-10 | No fixed values or constants: a model parameter that a design's space leaves out is held at its nominal value; every point is complete | 0023 | 2026-09-30 |
| OD-11 | Every Python model runs in an isolated child process, one long-lived child per model version, with a timeout; no in-process option; no memory or CPU limits in v2.0 | 0026 | 2026-09-30 |
| OD-12 | The bootstrap (1000 resamples, 0.5–99.5 percentiles) for scatter and the linear and polynomial models; no intervals for the point run, coordinate lines, and lines, whose numbers are observations | 0040 (amended by 0041) | 2026-09-30 |
| OD-13 | Uniform points from numpy's PCG64 raw stream (the `random` sampler), behind a sampler interface; Sobol, Halton, Latin hypercube, and minimum-distance samplers later | 0032 | 2026-09-30 |
| OD-14 | Quadrature and sparse grids in a later version | 0013 | 2026-09-29 |
| OD-20 | Three output parser kinds, each returning one scalar: regex, json, and csv; no python parser (a wrapper script writing JSON instead) | 0027 | 2026-09-30 |
