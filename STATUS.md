# EMA v2 status

**Updated:** 2026-09-29. Update this file at the end of every step, in the same commit as the work.

## Now

- Writing the design documents by hand (`TODO.md`), step 1: purpose accepted; glossary rows drafted from
  records 0003–0006; principles accepted (P1–P8, record 0007); the glossary's review is next.

## Done

- 2026-09-27: lessons learned from v1 (`docs/notes/v1/lessons_learned_2026-09-27.md`,
  `docs/notes/v1/lessons_learned_answers_2026-09-27.md`).
- 2026-09-28: data model template (`docs/design/data_model.md`), architecture draft
  (`docs/design/architecture.md`), this skeleton.
- 2026-09-28: OD-1 decided: rebuild in a new repository named `EMA`; v1 kept as `EMA-v1`, tag `v1-final`.
- 2026-09-28: purpose accepted (`docs/design/purpose.md`).
- 2026-09-29: OD-2, OD-3, and OD-4 decided (records 0003–0006); the glossary and the purpose page's wording
  follow them. How decisions are made is summarised in `docs/notes/decision_workflow.md`.
- 2026-09-29: principles accepted (`docs/design/principles.md`, P1–P8; record 0007), from an interview on the
  14 candidates: three dropped, two held for steps 9 and 10. Glossary rows added for "noisy" and "replicate";
  "approval" narrowed to runs.

## Next

- Step 1 of `TODO.md`: review and accept the glossary; add P1–P8 to `CLAUDE.md`, one line each.
- Steps 2–3: use cases; scope, including "Not in v2.0": diagnostic campaigns and studies that vary the model
  parameter space (records 0005, 0006).

## Specs

| Spec | Status |
|---|---|
| `docs/design/purpose.md` | accepted |
| `docs/design/principles.md` | accepted |
| `docs/design/glossary.md` | candidates listed |
| `docs/design/scope.md` | empty |
| `docs/design/use_cases.md` | empty |
| `docs/design/model_interface.md` | empty |
| `docs/design/designs.md` | empty |
| `docs/design/diagnostics/` | template only |
| `docs/design/uncertainty.md` | empty |
| `docs/design/contracts.md` | empty |
| `docs/design/data_model.md` | template |
| `docs/design/architecture.md` | draft |
| `docs/design/trust.md` | empty |
| `docs/design/sample_models.md` | empty |

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
| OD-5 | Diagnostics in v2.0 | from point run, scatter, coordinate lines, random lines, linear model, polynomial model | <3–4 of them> | scope, diagnostic specs |
| OD-6 | Model interfaces in v2.0 | Python function; command line; both | both | model interface |
| OD-7 | Agent in v2.0 | none; MCP server; own chat loop | none in v2.0, MCP after | scope, architecture |
| OD-8 | Experimental interpretation in v2.0 | none; a separate labelled section | none in v2.0 | scope, architecture |
| OD-9 | Multiple outputs | in the schema and code from day 1; in the schema only; later | in the schema from day 1 | model interface, data model |
| OD-10 | Fixed parameters (not design variables) | a parameter with no range; a separate mapping on the spec | <…> | model interface |
| OD-11 | Python models isolated by default | yes; no; only models the agent writes | <…> | model interface, trust, principles (held candidate) |
| OD-12 | The interval method for each v2.0 diagnostic | bootstrap; convergence; cross-validation; held-out error | <per diagnostic> | uncertainty, diagnostic specs |
| OD-13 | Uniform sampling | own seeded stream; `scipy.stats.qmc`; both | <…> | designs |
| OD-14 | Quadrature and sparse grids | in v2.0; later; never | later | designs, scope |
| OD-15 | Budgets | per call; per workspace; none in v2.0 | per call | workspace, data model |
| OD-16 | `Workspace` object or module functions | object; functions | object | architecture |
| OD-17 | Python version (the package stays `ema`) | 3.12, 3.13, 3.14 | <…> | setup |
| OD-18 | Tooling | uv and a lockfile; docs in Sphinx or MkDocs; CI | uv; <…> | setup |
| OD-19 | Monthly budget for live evals, once an agent exists | <$ …> | <…> | agent |
| OD-20 | Output parsers for command-line models in v2.0 | from v1's five kinds | <…> | model interface |

The open items in `docs/design/architecture.md` §12 and the `<…>` in `docs/design/data_model.md` join this table when
you reach those steps.

## Decided

| Id | Decision | Record | Date |
|---|---|---|---|
| OD-1 | Rebuild in a new repository named `EMA`; v1 renamed `EMA-v1` and kept for reference (tag `v1-final`) | 0002 (proposed) | 2026-09-28 |
| OD-2 | The unit of work is the diagnostic evaluation, with its report; diagnostic campaigns come in a later version | 0006 | 2026-09-29 |
| OD-3 | "Model parameter", "model prediction", and "model output"; the region a design samples is the model parameter space, a property of the design | 0003, 0005 | 2026-09-29 |
| OD-4 | "Variability interval": how much an estimate changes when the runs behind it change; not a confidence interval | 0004 | 2026-09-28 |
