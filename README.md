# EMA v2

EMA (Exploratory Model Analysis) runs diagnostics on computational models to look for exploitable structure,
and reports the results with figures, numbers, and their intervals.

This is v2, a rebuild (decision 0002). For now the repository holds the design documents: there is no code
yet. The order of work is `TODO.md`, and where things stand is `STATUS.md`.

v1 is at `../EMA-v1` (GitHub `pauls-code-projects/EMA-v1`, tag `v1-final`), for reference only. Its working
notes, including the lessons learned that led to v2, are in `docs/notes/v1/`.

## What goes where

| Kind | Says | Changes | Where |
|---|---|---|---|
| Spec | what to build | edited while `draft`; once `accepted`, changed only through a decision record | `docs/design/` |
| Decision record | why one choice was made, and what else was considered | written once; replaced, never edited | `docs/decisions/` |
| Plan | how one build step will be done, and its stop condition | written before the step; its status block updated as it goes | `docs/plans/` |
| Status | what's done, in progress, next, and still open | at the end of every step | `STATUS.md` |
| Guide | how a user does one task | outlines now; full text once the code exists | `docs/guides/` |
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
README.md                     this file
CLAUDE.md                     instructions for Claude Code
TODO.md                       what to do by hand before coding, in order
STATUS.md                     done, in progress, next, open decisions
LICENSE                       MIT (0060)
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
docs/decisions/               README.md (how, and the index), 0000-template.md, 0001…, 0002…
docs/plans/                   README.md, _template.md
docs/guides/                  get_started.md, add_a_model.md, run_a_diagnostic.md, add_a_diagnostic.md (outlines)
docs/checks/                  step 11's scripts for the expected answers, and their outputs
docs/notes/
  decision_workflow.md        how open decisions, decision records, and specs fit together
  adding_a_use_case.md        how to add a use case, with a template
  adding_a_reference_model.md how to add a reference model, what it can be used for, a template
  consistency_review_*.md     consistency reviews of the design documents, and what came of them
  v1/                         v1's working notes and the lessons learned (not maintained)
```
