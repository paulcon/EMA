# EMA v2: what to do by hand before coding

Rewritten 2026-09-28; the build's section added 2026-10-03. Paths are relative to the repository's root. `CONTRIBUTING.md` describes the layout and the id
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
- [x] **13. Guides as outlines.** `docs/guides/`: get started, add a model, run a diagnostic, add a diagnostic.
  Records: 0060 (install from GitHub with uv; get started tested; MIT license; C53–C55 accepted).

## Before the first line of code

- [x] Every spec needed by the first build step is `accepted` (with record 0065 applied).
- [x] Claude Code has checked the specs against each other for contradictions, and you've resolved them.
  `docs/notes/consistency_review_2026-10-01_before_code.md`; records 0061–0064.
- [x] The first plan (`docs/plans/01-scaffolding-and-designs.md`) is written and approved (record 0065): the
      repository's scaffolding (0059: `.python-version`, `pyproject.toml`, `uv.lock`, `conftest.py`,
      `docs/conf.py`, `docs/index.md`, `.github/workflows/checks.yml`; `pyproject.toml` with `license = "MIT"`,
      0060), the parts of `ema.types` that designs need, and the design generators, with their contracts. The
      later steps' order is a draft in `docs/notes/build_roadmap.md`.

## The build

- [x] **Build steps 01–16 and T,** built autonomously on the `demo` branch (record 0066), from the plans in
  `docs/plans/` (04 covers steps 04 and 05), each reviewed and fixed by independent agents; the log is
  `docs/notes/demo_build.md`. Records: 0067–0082, 0084, 0085. The MCP demo: `docs/notes/demo_mcp.md`.
- [x] **The build's records accepted and applied.** Records 0066–0085 accepted (0084's budget raised to 11,000)
  and applied to the specs, then reviewed in two rounds; what was left answered in an interview, record 0086 (the
  budgets 12,000 source lines and a 90 s fast tier, and twelve smaller items), and its review's follow-ups,
  record 0087; both accepted and applied. `demo` pushed to GitHub (`origin/demo`).
- [ ] **Review `demo` and decide on merging it into `main`.** You.
- [x] **18. Citations off the documentation site** (record 0089; `docs/plans/18-site-citations.md`), before step
  17: the site's build drops the citations, and fails on any left; docstrings reworded so each citation is in
  parentheses.
- [ ] **17. Guides and release** (`docs/notes/build_roadmap.md`): the guides' full text, the README, the wheel's
  contents, and the budgets audited; its plan (`docs/plans/17-*.md`) is still to write.
