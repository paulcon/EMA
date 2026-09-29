# 0006. Make the diagnostic evaluation, with its report, the unit of work

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** OD-2.

## Context

In v1, the campaign became the unit of work, not the diagnostic. Budgets, justification, synthesis, reuse,
next steps, findings, and reports all hung off the campaign (`../notes/v1/lessons_learned_2026-09-27.md` §3,
pattern 3). The concepts multiplied past what one person could review: campaign, diagnostic, design, flag,
factual flag, interpretation, finding, next step, synthesis, disagreement, reuse, surrogate, and more (same
section, pattern 5). The plain Python and command-line paths inherited the campaign machinery, and getting
started was hard; the owner's own note asked "What is a campaign file?" (same file, §5).

The owner's redesign note says: "Instead of a diagnostic campaign, do just one diagnostic with report at a
time" (`../notes/v1/ema-notes.md`). The lessons learned describe the essential workflow as: choose a model,
choose a diagnostic and its design parameters, run the design, compute values and intervals, report (§13).

`../design/purpose.md` describes the same flow: "The user chooses a diagnostic … Once a diagnostic completes,
EMA produces a report." Decision 0005 puts studies that vary the model parameter space out of scope for v2.0,
as a job for a diagnostic campaign in a later version.

Budgets and approvals can attach to either unit (`../notes/v1/lessons_learned_2026-09-27.md` §15).

## Decision

We will make the **diagnostic evaluation**, with its report, the unit of work in v2.0.

- **Diagnostic:** a formula or method that produces the diagnostic result for a given model and design.
- **Diagnostic evaluation:** one execution of a diagnostic for a particular model and design, which produces
  the numbers of the diagnostic result.

What follows from it:

- **One request is one diagnostic evaluation.** It names a model, a diagnostic, a model parameter space, and
  the diagnostic parameters. EMA builds one design, prices it, asks for approval before any new runs, runs
  it, computes one diagnostic result, and produces one report.
- **Every public entry point works on this unit:** each workspace call, CLI command, approval, and report is
  about one diagnostic evaluation.
- **Nothing groups diagnostic evaluations in v2.0.** There is no campaign object, table, file, or report.
- **Runs are shared through the store, not through a grouping.** Runs are stored by model version and point,
  so a later diagnostic evaluation reuses earlier runs without anything tying the two evaluations together.
- **Diagnostic campaigns are deferred.** A campaign is a set of diagnostic evaluations planned, budgeted,
  compared, or reported together, including a study that varies the model parameter space (0005). It comes in a later
  version, with its own decision record.

## Alternatives considered

- **The campaign as the unit (v1):** it supports planning several diagnostic evaluations together, one budget, synthesis
  across diagnostics, and comparisons such as varying the model parameter space. But in v1 every feature hung
  off it, it multiplied the concepts, and the simple path inherited its machinery.
- **Both, with campaigns optional in v2.0:** keeps the door open, but adds a concept, its tables, and its
  reports before the core is trusted, which is the order of work v1's lessons warn against.
- **The design as the unit** (several diagnostic evaluations sharing one design): diagnostics mostly need different
  designs, and run reuse through the store already gives the saving this would.

## Consequences

- **`../design/scope.md`:** "Not in v2.0" lists diagnostic campaigns, studies that vary the model parameter
  space, and synthesis or comparison across diagnostic evaluations.
- **`STATUS.md`:** OD-2 moves to "Decided", naming this record.
- **`../design/architecture.md` §7** already has no campaign object; it stays that way. `Workspace.run` and
  `estimate` each handle one diagnostic evaluation.
- **`../design/data_model.md`:** no `campaigns` table. Question Q5 ("How many new runs has this <campaign /
  budget> used?") is reworded for per-request budgets, and any per-workspace total (OD-15). Results need
  stable ids, so a later campaign can refer to existing results without rewriting them.
- **Budgets:** a budget attaches to one request. Whether there is also a per-workspace budget stays open
  (OD-15).
- **Approvals:** the user approves each diagnostic evaluation's new runs separately. Work with several
  diagnostic evaluations means several prompts; that is the price of the simpler unit.
- **Reports:** one per diagnostic evaluation. There is no combined report in v2.0; a user who wants one assembles it
  from the separate reports or the exports.
- **Glossary:** "diagnostic" is redefined as the formula or method, and "diagnostic evaluation" is added.
  Neither collides with "run" (one evaluation of a model). "Result" becomes "diagnostic result": what a
  diagnostic evaluation produces. "Campaign" is not defined in v2.0's glossary.
- **`../design/purpose.md`** (accepted) changes its wording only: where it means one execution, it says
  "diagnostic evaluation" (the time to complete one, reuse of runs across them, what is recorded to reproduce
  one), and "results" becomes "diagnostic results". Where it means the method ("diagnostics are derived from
  numerical methods"), it keeps "diagnostic".
- **Code names in `../design/architecture.md`:** following 0003's rule that code uses the glossary's words,
  `DiagnosticRun` becomes `DiagnosticEvaluation`. Whether `Workspace.run`, which performs one, keeps its
  name is for the architecture spec.
- **Model predictions (OD-9):** whether one request analyzes one model prediction or several is decided with
  multiple outputs, not here.
