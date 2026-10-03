# Contributing to EMA

How the project is organized, and how a change gets in. For what EMA does and how to use it, see `README.md`.

EMA v2 is a rebuild (record 0002), written spec first: the specs in `docs/design/` say what to build, decision
records say why, and the code and its tests cite both by id. `CLAUDE.md` holds the working rules for Claude Code
sessions on this repository; they apply to people too.

## Development

```bash
git clone https://github.com/pauls-code-projects/EMA.git && cd EMA
uv sync --extra mcp
```

Python 3.13 or newer; developed on 3.14 (record 0059). The checks:

| Check | Command | When |
|---|---|---|
| Fast tier and import contracts | `uv run pytest -q -n auto && uv run lint-imports` | after every edit (90 s budget, 0086) |
| Full tests | `uv run pytest -q --slow -n auto` | before a step is done |
| Lint and types | `uv run ruff check && uv run ruff format --check && uv run mypy` | before a step is done |
| Docs | `uv run sphinx-build -W --keep-going docs docs/_build/html` | before a step is done |

GitHub Actions (`.github/workflows/checks.yml`) runs only when started by hand.

## How a change gets in

- **Build only from accepted specs.** Each file in `docs/design/` has a status line. A spec that is `draft`, or
  silent on what a change needs, is settled first.
- **Decisions are recorded.** A change to what an accepted spec says needs a decision record in `docs/decisions/`,
  drafted as `proposed` and applied once accepted (`docs/decisions/README.md`;
  `docs/notes/decision_workflow.md`).
- **Cite ids** in docstrings, tests, and commit messages (below). Text users see cites none (records 0086, 0087).
- **Tests first,** from the spec's contract checks and known answers.
- **One build step at a time,** each with a plan in `docs/plans/` and a stop condition.
- **Size budgets** (`docs/design/scope.md`) are constraints: going over one is a decision to propose.
- **`STATUS.md`** is updated at the end of each step, in the same commit as the work.

## What goes where

| Kind | Says | Changes | Where |
|---|---|---|---|
| Spec | what to build | edited while `draft`; once `accepted`, changed only through a decision record | `docs/design/` |
| Decision record | why one choice was made, and what else was considered | written once; replaced, never edited | `docs/decisions/` |
| Plan | how one build step will be done, and its stop condition | written before the step; its status block updated as it goes | `docs/plans/` |
| Status | what's done, in progress, next, and still open | at the end of every step | `STATUS.md` |
| Order of work | the steps, in order | as steps are added or done | `TODO.md` |
| Guide | how a user does one task | outlines now; full text at step 17 | `docs/guides/` |
| Notes | background: v1's lessons and working notes; short guides to how the project works | not maintained | `docs/notes/` |

## Ids

Everything that code or tests may cite has an id, so a docstring, a test, or a commit can point to it.

| Prefix | What | Defined in |
|---|---|---|
| P | principle | `docs/design/principles.md` |
| U | use case | `docs/design/use_cases.md` |
| OD | open decision | `STATUS.md` |
| — | decision record, cited by its 4 digits (record 0007, or 0007) | `docs/decisions/` |
| M | model-interface requirement | `docs/design/model_interface.md` |
| G | design generator requirement | `docs/design/designs.md` |
| S | requirement shared by every diagnostic | `docs/design/diagnostics/shared.md` |
| PT, SC, CL, LN, LM, PM | requirement of one diagnostic: point run, scatter, coordinate lines, lines, linear model, polynomial model | `docs/design/diagnostics/<name>.md` |
| V | variability interval requirement | `docs/design/uncertainty.md` |
| AR | architecture rule | `docs/design/architecture.md` |
| C | contract promise | `docs/design/contracts.md` |
| T | trust-boundary rule | `docs/design/trust.md` |
| E | export requirement | `docs/design/export.md` |
| Q, W, I | data-model question, write, invariant | `docs/design/data_model.md` |
| R | reference model | `docs/design/reference_models.md` |

## Files

```text
README.md                     what EMA does, installing it, getting started
CONTRIBUTING.md               this file
CLAUDE.md                     instructions for Claude Code
TODO.md                       the order of work: by hand before coding (done), then the build
STATUS.md                     done, in progress, next, open decisions
LICENSE                       MIT (0060)
pyproject.toml                the package, its dependencies, and the tools' settings (0059)
src/ema/                      the code (docs/design/architecture.md)
tests/                        contracts, unit, and slow tests (docs/design/contracts.md), their shared helpers
                              (support/), and the test models (models/)
docs/design/
  purpose.md                  why EMA exists, and for whom
  principles.md               P1…
  glossary.md
  scope.md                    v2.0 in and out; size budgets; what to port from v1
  use_cases.md                U1…
  model_interface.md          M1…
  designs.md                  G1…
  diagnostics/_template.md    one spec per diagnostic, in the five-row table format
  diagnostics/shared.md       what every diagnostic shares: report layout, precheck, figures (S1…)
  uncertainty.md              V1…; one interval method per diagnostic
  contracts.md                C1…, and the degenerate cases
  data_model.md               Q1…, W1…, I1…: the store's tables, reads, writes, and invariants
  architecture.md             packages, layers, modules, and their public names
  trust.md                    T1…
  export.md                   the export's files and their read-back (0050)
  reference_models.md         R1…, their truths, and an index of expected answers (0052)
docs/decisions/               README.md (how, and the index), 0000-template.md, 0001…
docs/plans/                   README.md, _template.md, one plan per build step (01–04, 06–16, T; 04 is steps 04–05)
docs/guides/                  get_started.md, add_a_model.md, run_a_diagnostic.md, add_a_diagnostic.md (outlines)
docs/checks/                  step 11's scripts for the expected answers, and their outputs
docs/notes/
  decision_workflow.md        how open decisions, decision records, and specs fit together
  adding_a_use_case.md        how to add a use case, with a template
  adding_a_reference_model.md how to add a reference model, what it can be used for, a template
  consistency_review_*.md     consistency reviews of the design documents, and what came of them
  build_roadmap.md            the order of the build steps
  demo_build.md               the demo build's log: every wave and review round
  demo_mcp.md                 the MCP demo: setup and script; demo/ holds its beam model
  v1/                         v1's working notes and the lessons learned (not maintained)
```

## v1

v1 is at GitHub `pauls-code-projects/EMA-v1` (tag `v1-final`), for reference only: read it when a plan says to,
and copy code from it only when a plan names the file to port. Its working notes, including the lessons learned
that led to v2, are in `docs/notes/v1/`.
