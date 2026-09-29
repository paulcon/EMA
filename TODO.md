# EMA v2: what to do by hand before coding

Rewritten 2026-09-28. Paths are relative to the repository's root. `README.md` describes the layout and the id
scheme; open decisions are the OD rows in `STATUS.md`.

Work in order: each step depends on the ones above it. "You" means by hand. "Claude can help" means Claude
Code drafts, interviews you, or checks consistency, and you decide.

A step is done when its files are marked `accepted`, and its OD rows are decided with records in
`docs/decisions/`.

## Foundations

- [x] **1. Purpose, principles, glossary.** `docs/design/purpose.md`, `principles.md`, `glossary.md`.
  - You: write the purpose page; choose at most 10 principles from the candidates; settle the words.
  - Decide: OD-3 (parameter and box), OD-4 (the word for intervals).
  - Claude can help: interview you on each candidate principle; check the glossary against the other specs.
- [x] **2. Use cases.** `docs/design/use_cases.md`.
  - You: 3–5 scenarios: what the analyst types, what EMA asks, the report they get, and the checks that say it
    works.
- [ ] **3. Scope.** `docs/design/scope.md`.
  - You: the in and out lists for v2.0, the size budgets, and which v1 modules to port.
  - Decided: OD-1, rebuild in a new repository (record 0002, proposed: accept or edit it).
  - Decide: OD-2, OD-5, OD-6, OD-7, OD-8, OD-14.
  - Also: accept or edit decision record 0001 (how decisions are recorded).

## What v2 does

- [ ] **4. Model interface.** `docs/design/model_interface.md`.
  - Decide: OD-9 (multiple outputs), OD-10 (fixed parameters), OD-11 (isolation), OD-20 (parsers).
- [ ] **5. Designs.** `docs/design/designs.md`.
  - Decide: OD-13 (uniform sampling).
  - Decide: a glossary row for "design generator".
- [ ] **6. Diagnostic specs**, one per v2.0 diagnostic, from `docs/design/diagnostics/_template.md`.
  - You: draw each mock report by hand, and fill in the expected answers.
  - Decide: the per-model-parameter estimate in scatter's report (U1: for example, a rank correlation).
  - Decide: the per-line estimate in coordinate lines' report (U2: for example, the spectrum's decay rate).
  - Decide: the point run's measured variation (U7): which numbers, and what its tolerance for "varies" is
    relative to (P6), since one point has no range.
- [ ] **7. Uncertainty; contracts and degenerate cases.** `docs/design/uncertainty.md`, `contracts.md`.
  - Decide: OD-12 (the interval method per diagnostic).
  - Decide: whether every diagnostic's report adds U3's failure map (failed and usable runs in each pair of
    model parameters) when runs fail, or only scatter's.
  - Claude can help: draft the negative control for each promise.

## How v2 is built

- [ ] **8. Data model.** `docs/design/data_model.md` (from the template).
  - Claude can help: check that every question in its §2 has a query, and that the tables match the model
    interface and designs specs.
- [ ] **9. Architecture and the workspace layer.** `docs/design/architecture.md` (formerly `api_spec_draft.md`).
  - Decide: OD-15 (budgets), OD-16 (`Workspace` object), and its §12 items.
  - Decide: the held principle "One-way layers" (`docs/design/principles.md`, Candidates).
- [ ] **10. Trust boundary.** `docs/design/trust.md`.
  - Decide: the held principle "User code runs isolated, without EMA's secrets" (`docs/design/principles.md`,
    Candidates), after OD-11.
  - Decide: whether "user code" (what the trust boundary runs) gets a glossary row.
- [ ] **11. Reference models with expected answers.** `docs/design/reference_models.md`.
  - Claude can help: compute reference values with v1's `testfunctions/truth.py`, or by brute force, as an
    independent check on yours.

## Setup

- [ ] **12. Repository and tooling.**
  - Done by `move_v1_start_v2.sh`: v1 renamed to `EMA-v1` (tag `v1-final`); this repository created as `EMA`,
    with v1's notes in `docs/notes/v1/`.
  - Decide: OD-17 (Python version), OD-18 (uv, docs, CI), OD-19 (eval budget, if there's an agent).
  - Finish `CLAUDE.md` (the one-line principles, the commands) and `STATUS.md`.
- [ ] **13. Guides as outlines.** `docs/guides/`: get started, add a model, run a diagnostic, add a diagnostic.
  - You: walk through each against `ema.workspace` on paper. Any awkward step means the workspace's functions
    change before any code exists.

## Before the first line of code

- [ ] Every spec needed by the first build step is `accepted`.
- [ ] Claude Code has checked the specs against each other for contradictions, and you've resolved them.
- [ ] The first plan (`docs/plans/01-…`) is written and approved: probably `ema.types` and the design
      generators, with their contracts.
