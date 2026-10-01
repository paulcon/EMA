# 0022. Let a model have several scalar model predictions, and analyze one per diagnostic evaluation

**Date:** 2026-09-30. **Status:** accepted; its data-model consequence and glossary row amended by 0043. **Resolves:** OD-9.

## Context

A simulation code often reports several quantities from one run: a peak temperature and a heat flux, a drag
and a lift. Record 0021 limits v2.0 to scalar model predictions, and stores them in their own table, keyed by
run and name. It leaves open how many a model may have.

v1 allowed exactly one output per model ("v1 supports exactly one output",
`../../../EMA-v1/src/ema/core/spec.py`); a second quantity needed a second model spec, and a second run at
every point. v1's answers recommend designing several outputs in from the start, since adding them later
changes the spec, the store, and every diagnostic's input
(`../notes/v1/lessons_learned_answers_2026-09-27.md`, "How might I design the database to manage models with
multiple outputs?").

With several model predictions, a run can read some and not others: an output parser finds `T_max` but not
`q_out`. The glossary (accepted) defines a failed run as "a run that produced no model predictions".

## Decision

We will let a model spec list one or more scalar model predictions, in the spec and the code from v2.0.

- **One run produces all of them.** A second model prediction costs no new runs.
- **Per model prediction.** A run keeps the model predictions it read. One it couldn't read (an output parser
  that fails, a missing key, a non-finite value) is NaN, with its own reason. A run with none read is a failed
  run. A diagnostic evaluation counts a run as not usable (P6) when the model prediction it analyzes is
  missing.
- **One per diagnostic evaluation.** A diagnostic evaluation analyzes one model prediction, named by
  `prediction=`; the name may be left out when the model has only one. Each gets its own diagnostic result
  and report.

## Alternatives considered

- **Several in the schema, one in the code:** the spec and store take a list, and v2.0 refuses more than one.
  It saves little now, since 0021 already gives model predictions their own table.
- **One per model, later (v1):** the simplest spec, but a simulator with two quantities runs twice, and adding
  more later changes the spec, the store, and every diagnostic's input.
- **The whole run fails when any model prediction is missing:** the glossary stays as it is, but a good model
  prediction is lost because another didn't parse.
- **All model predictions in one diagnostic evaluation and report:** fewer commands, but longer reports, and
  one result id holds several sets of estimates and notes.

## Consequences

- **`../design/model_interface.md`:** "What a model returns" lists the model predictions, with a reason per
  missing one.
- **`../design/glossary.md`** (accepted): the "failed run" row reads "a run that produced none of its model
  predictions …"; the "model prediction" row's "(OD-9)" becomes "(0021, 0022)", and says a missing model
  prediction is NaN with its reason.
- **`../design/data_model.md`** (step 8): model predictions keyed by run and name, each with a status and a
  reason; a run's status is failed only when all are missing.
- **`../design/architecture.md`** (step 9): `qoi` becomes `prediction` (0003), on `Workspace.run`,
  `estimate`, `list_results`, and `ResultSummary`; `RunBatch.y(prediction)` is NaN where that model
  prediction is missing.
- **Diagnostic specs** (step 6) and **`../design/contracts.md`** (step 7): the precheck counts usable runs per
  model prediction; the diagnostic contract has a run with one model prediction missing and another read.
- **Use cases:** U1–U4 have one model prediction and work as written; U5's export has a column per model
  prediction.
- **`../../STATUS.md`:** OD-9 moves to "Decided", naming this record, when it is accepted (0001).
