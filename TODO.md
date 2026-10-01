# EMA v2: what to do by hand before coding

Rewritten 2026-09-28. Paths are relative to the repository's root. `README.md` describes the layout and the id
scheme; open decisions are the OD rows in `STATUS.md`.

Work in order: each step depends on the ones above it. "You" means by hand. "Claude can help" means Claude
Code drafts, interviews you, or checks consistency, and you decide.

A step is done when its files are marked `accepted`, and its OD rows are decided with records in
`docs/decisions/`.

## Foundations

- [x] **1. Purpose, principles, glossary.** `docs/design/purpose.md`, `principles.md`, `glossary.md`.
  Records: 0003–0005, 0007–0009 (OD-3, OD-4).
- [x] **2. Use cases.** `docs/design/use_cases.md`. Records: 0010, 0011.
- [x] **3. Scope.** `docs/design/scope.md`. Records: 0001, 0002, 0006, 0012–0021 (OD-1, OD-2,
  OD-5–OD-8, OD-14).

## What v2 does

- [x] **4. Model interface.** `docs/design/model_interface.md`. Records: 0022–0031 (OD-9–OD-11, OD-20).
- [x] **5. Designs.** `docs/design/designs.md`. Records: 0032, 0033 (OD-13).
- [x] **6. Diagnostic specs,** one per v2.0 diagnostic, from `docs/design/diagnostics/_template.md`. Records:
  0034–0040 (OD-12).
- [x] **7. Uncertainty; contracts and degenerate cases.** `docs/design/uncertainty.md`, `contracts.md`.
  Records: 0041, 0042.
- [x] **Consistency review** of every design document (`docs/notes/consistency_review_2026-10-01.md`).
  Records: 0043–0052 (OD-15, OD-19).

## How v2 is built

- [ ] **8. Data model.** `docs/design/data_model.md` (from the template).
  - First: the export spec, `docs/design/export.md` (0050): what an export holds, its files and columns, and
    reading it back; the data model stores what it reads.
  - Claude can help: check that every question in its §2 has a query, and that the tables match the model
    interface and designs specs.
  - Also: each run's host (0015) and run directory (0020); model predictions in their own table, with no blob
    store (0021).
  - Also, from `contracts.md` (step 7): invariants I1… for C46–C52 and C56; the template's I4 against 0010 (a
    failed run reused, a retry stored beside it); the store test at `tests/contracts/store.py`; a run's failure
    kind and reason, host, and resolved program path; whether a stored result is reused after a named constant
    such as `BOOTSTRAP_RESAMPLES` changes; the polynomial coefficients with their intervals (0041).
  - Also, the asks the consistency review (2026-10-01) found missing here:
    `docs/notes/consistency_review_2026-10-01.md`, "Step 8 inputs" (design identity, the stored-result reuse
    key, model name → model version, the current run at a key, approvals, hashing and ids, and the asks the
    specs and records make of this step).
- [ ] **9. Architecture and the workspace layer.** `docs/design/architecture.md` (formerly `api_spec_draft.md`).
  - Also: drop the `Executor` classes (0015); drop `ema.experimental` from v2.0 (0017); the MCP tools and the
    server's instructions (0016, 0019); asking for a PDF (0018); the run-directory lookup (0020); within the
    budgets in `scope.md`.
  - Also: the asks in `docs/notes/consistency_review_2026-10-01.md`, "Step 9 inputs" (renames to the
    glossary's words, the interfaces the specs name, the approval module, the MCP tool set, the name count).
  - Decide: OD-16 (`Workspace` object), and §12's items still open (where `version_hash` lives; whether
    `report` imports `diagnostics`); the rest of §12 is settled by records.
  - Decide: the held principle "One-way layers" (`docs/design/principles.md`, Candidates).
- [ ] **10. Trust boundary.** `docs/design/trust.md`.
  - Decide: the held principle "User code runs isolated, without EMA's secrets" (`docs/design/principles.md`,
    Candidates), after OD-11.
  - Decide: whether "user code" (what the trust boundary runs) gets a glossary row; the specs also say "model
    code" and "model programs" (`docs/notes/consistency_review_2026-10-01.md`, "Step 10 inputs").
- [ ] **11. Reference models with expected answers.** `docs/design/reference_models.md`.
  - Claude can help: compute reference values with v1's `testfunctions/truth.py`, or by brute force, as an
    independent check on yours.

## Setup

- [ ] **12. Repository and tooling.**
  - Done by `move_v1_start_v2.sh`: v1 renamed to `EMA-v1` (tag `v1-final`); this repository created as `EMA`,
    with v1's notes in `docs/notes/v1/`.
  - Decide: OD-17 (Python version), OD-18 (uv, docs, CI). Live evals are later (OD-19, 0050).
  - Plan: pandoc and LaTeX as an optional install, in staged steps (0018).
  - Finish `CLAUDE.md` (the commands) and `STATUS.md`.
- [ ] **13. Guides as outlines.** `docs/guides/`: get started, add a model, run a diagnostic, add a diagnostic.
  - You: walk through each against `ema.workspace` on paper. Any awkward step means the workspace's functions
    change before any code exists.

## Before the first line of code

- [ ] Every spec needed by the first build step is `accepted`.
- [ ] Claude Code has checked the specs against each other for contradictions, and you've resolved them.
- [ ] The first plan (`docs/plans/01-…`) is written and approved: probably `ema.types` and the design
      generators, with their contracts.
