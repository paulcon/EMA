# EMA v2 status

**Updated:** 2026-09-30. Update this file at the end of every step, in the same commit as the work.

## Now

- Writing the design documents by hand (`TODO.md`): steps 1–4 done; step 5 (designs) next.

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

## Next

- Step 5: designs (OD-13, and a glossary row for "design generator"), with what `model_interface.md` asks of
  them: spaces that name a subset of the model parameters, scales in the space, limits refused, and
  zero-width ranges (0023, 0024).

## Specs

| Spec | Status |
|---|---|
| `docs/design/purpose.md` | accepted |
| `docs/design/principles.md` | accepted |
| `docs/design/glossary.md` | accepted |
| `docs/design/scope.md` | accepted |
| `docs/design/use_cases.md` | accepted |
| `docs/design/model_interface.md` | accepted |
| `docs/design/designs.md` | empty |
| `docs/design/diagnostics/` | template only |
| `docs/design/uncertainty.md` | empty |
| `docs/design/contracts.md` | empty |
| `docs/design/data_model.md` | template |
| `docs/design/architecture.md` | draft |
| `docs/design/trust.md` | empty |
| `docs/design/reference_models.md` | empty |

Statuses: empty → draft → accepted. Claude Code builds only from accepted specs.

## Open decisions

> One row per decision still to make. When you decide one:
> 1. write a decision record in `docs/decisions/`;
> 2. update the specs it affects;
> 3. move the row to "Decided" below.
>
> Do all three in one commit. "Blocks" lists the steps of the TODO that can't finish without it.

| Id | Question | Options | Suggested | Blocks |
|---|---|---|---|---|
| OD-12 | The interval method for each v2.0 diagnostic | bootstrap; convergence; cross-validation; held-out error | <per diagnostic> | uncertainty, diagnostic specs |
| OD-13 | Uniform sampling | own seeded stream; `scipy.stats.qmc`; both | <…> | designs |
| OD-15 | Budgets | per call; per workspace; none in v2.0 | per call | workspace, data model |
| OD-16 | `Workspace` object or module functions | object; functions | object | architecture |
| OD-17 | Python version (the package stays `ema`) | 3.12, 3.13, 3.14 | <…> | setup |
| OD-18 | Tooling | uv and a lockfile; docs in Sphinx or MkDocs; CI | uv; <…> | setup |
| OD-19 | Monthly budget for live evals, once an agent exists | <$ …> | <…> | agent |

The open items in `docs/design/architecture.md` §12 and the `<…>` in `docs/design/data_model.md` join this table when
you reach those steps.

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
| OD-14 | Quadrature and sparse grids in a later version | 0013 | 2026-09-29 |
| OD-20 | Three output parser kinds, each returning one scalar: regex, json, and csv; no python parser (a wrapper script writing JSON instead) | 0027 | 2026-09-30 |
