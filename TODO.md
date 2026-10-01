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
- [x] **3. Scope.** `docs/design/scope.md`.
  - You: the in and out lists for v2.0, the size budgets, and which v1 modules to port.
  - Decided: OD-1 (0002), OD-2 (0006), OD-5 (0012), OD-6 (0014), OD-7 (0016, 0019), OD-8 (0017), OD-14
    (0013); records 0001, 0015, 0018, 0020, 0021 accepted.

## What v2 does

- [x] **4. Model interface.** `docs/design/model_interface.md`.
  - Decided: OD-9 (0022), OD-10 (0023), OD-11 (0026), OD-20 (0027); records 0024, 0025, and 0028–0031
    accepted.
  - Also: a run's three phases, and the open platform question (0015); run directories and the keep setting
    (0020); scalar output parsers, and `noisy: true` refused (0021).
- [x] **5. Designs.** `docs/design/designs.md`.
  - Decided: OD-13 (0032); record 0033 accepted (held values; glossary rows for design generator, sampler,
    and nested; the sampler's rate).
- [x] **6. Diagnostic specs**, one per v2.0 diagnostic, from `docs/design/diagnostics/_template.md`.
  - You: draw each mock report by hand, and fill in the expected answers.
  - Decided (`scatter.md`): the per-model-parameter estimates in scatter's report are Spearman's rank
    correlation and a bias-adjusted binned first-order index, with bootstrap intervals.
  - Decided (0038): the per-line number in coordinate lines' report is the decay rate of its Gram spectrum, an
    observation with no interval.
  - Decided (`point_run.md`): the point run's measured variation (U7) is observations only; "varies" is exact
    (two usable runs differ as doubles, as 0035), with no tolerance.
  - Decided: OD-12 (0040): the bootstrap for scatter and the linear and polynomial models; none for the point
    run, coordinate lines, and lines.
- [ ] **7. Uncertainty; contracts and degenerate cases.** `docs/design/uncertainty.md`, `contracts.md`.
  - Decided: OD-12 (0040); `uncertainty.md` is written from its table.
  - Claude can help: draft the negative control for each promise.

## How v2 is built

- [ ] **8. Data model.** `docs/design/data_model.md` (from the template).
  - Claude can help: check that every question in its §2 has a query, and that the tables match the model
    interface and designs specs.
  - Also: each run's host (0015) and run directory (0020); model predictions in their own table, with no blob
    store (0021).
- [ ] **9. Architecture and the workspace layer.** `docs/design/architecture.md` (formerly `api_spec_draft.md`).
  - Also: drop the `Executor` classes (0015); drop `ema.experimental` from v2.0 (0017); the MCP tools and the
    server's instructions (0016, 0019); asking for a PDF (0018); the run-directory lookup (0020); within the
    budgets in `scope.md`.
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
  - Decide: OD-17 (Python version), OD-18 (uv, docs, CI), OD-19 (eval budget: needed, the MCP server is in
    v2.0, 0016).
  - Plan: pandoc and LaTeX as an optional install, in staged steps (0018).
  - Finish `CLAUDE.md` (the one-line principles, the commands) and `STATUS.md`.
- [ ] **13. Guides as outlines.** `docs/guides/`: get started, add a model, run a diagnostic, add a diagnostic.
  - You: walk through each against `ema.workspace` on paper. Any awkward step means the workspace's functions
    change before any code exists.

## Before the first line of code

- [ ] Every spec needed by the first build step is `accepted`.
- [ ] Claude Code has checked the specs against each other for contradictions, and you've resolved them.
- [ ] The first plan (`docs/plans/01-…`) is written and approved: probably `ema.types` and the design
      generators, with their contracts.
