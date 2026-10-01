# EMA v2 status

**Updated:** 2026-10-01. Update this file at the end of every step, in the same commit as the work.

## Now

- Writing the design documents by hand (`TODO.md`): steps 1–7 done; the consistency review's decisions
  (records 0043–0052) applied.
- Next: the export spec (`docs/design/export.md`, 0050), then step 8, the data model.

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

## Next

- The export spec (`docs/design/export.md`, 0050): what an export holds, its files and columns, and reading
  it back.
- Step 8, the data model (`docs/design/data_model.md`, from its template): `TODO.md` step 8, with the review's
  "Step 8 inputs".

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
| `docs/design/export.md` | empty (before step 8, 0050) |
| `docs/design/reference_models.md` | draft (the list; expected answers at step 11) |

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
| OD-16 | `Workspace` object or module functions | object; functions | object | architecture |
| OD-17 | Python version (the package stays `ema`) | 3.12, 3.13, 3.14 | <…> | setup |
| OD-18 | Tooling | uv and a lockfile; docs in Sphinx or MkDocs; CI | uv; <…> | setup |

The items still open in `docs/design/architecture.md` §12 (the rest are struck, with their records) and the
`<…>` in `docs/design/data_model.md` join this table when you reach those steps.

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
| OD-19 | 0050 | 2026-10-01 |
| OD-20 | 0027 | 2026-09-30 |
