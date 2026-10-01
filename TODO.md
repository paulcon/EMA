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

- [x] **8. Data model.** `docs/design/data_model.md`. Records: 0054, 0055.
- [x] **9. Architecture and the workspace layer.** `docs/design/architecture.md` (formerly `api_spec_draft.md`).
  Records: 0056 (OD-16; "One-way layers" as architecture rules AR1–AR7).
- [x] **10. Trust boundary.** `docs/design/trust.md`. Records: 0057 (the held principle answered by T1–T10;
  "model" as the one word, with no glossary row).
- [x] **11. Reference models with expected answers.** `docs/design/reference_models.md`. Records: 0058.

## Setup

- [x] **12. Repository and tooling.** Records: 0059 (OD-17, OD-18: Python 3.13 and newer, uv and a
  lockfile, Sphinx, checks on GitHub Actions by hand, PDFs with lualatex). uv and its Pythons 3.14 and 3.13
  installed on the owner's Mac; pandoc and LaTeX already were.
- [ ] **13. Guides as outlines.** `docs/guides/`: get started, add a model, run a diagnostic, add a diagnostic.
  - You: walk through each against `ema.workspace` on paper. Any awkward step means the workspace's functions
    change before any code exists.
  - Get started, step 1: install EMA with uv on Python 3.13 or newer; pandoc and a LaTeX with lualatex as an
    optional install, in staged steps (0018, 0059).

## Before the first line of code

- [ ] Every spec needed by the first build step is `accepted`.
- [ ] Claude Code has checked the specs against each other for contradictions, and you've resolved them.
- [ ] The first plan (`docs/plans/01-…`) is written and approved: the repository's scaffolding (0059:
      `.python-version`, `pyproject.toml`, `uv.lock`, `conftest.py`, `docs/conf.py`, `docs/index.md`,
      `.github/workflows/checks.yml`), and probably `ema.types` and the design generators, with their contracts.
