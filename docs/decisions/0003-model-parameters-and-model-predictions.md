# 0003. Call a model's variables model parameters, and what EMA analyzes model predictions

**Date:** 2026-09-28. **Status:** accepted. **Resolves:** OD-3, in part (the word for the region a design
samples stays open).

## Context

v1 called a model's variables *inputs*, the region a design samples the *input box*, and the quantities it
analyzed *outputs*; the code used `qoi` (quantity of interest). The owner's redesign notes
(`../notes/v1/ema-redesign.md`, "Objects") call the variables `ModelParameter`s. `../design/architecture.md` §3
asks for one pair of words, and suggests `ModelParameter`.

In v1, a glossary enforced by a terminology test kept about 84,000 words of documentation consistent
(`../notes/v1/lessons_learned_2026-09-27.md` §12). v2's glossary follows the same rule: one word per idea, in
the owner's nomenclature, linked to the standard terms. `../design/purpose.md` now uses "model parameters" and
"model predictions".

Two uses of "output" were mixed together in v1. A command-line program writes files, logs, and fields: its
outputs. EMA reads a few quantities out of those files, with parsers, and analyzes them. With one word for
both, a spec can't say "the program wrote its outputs, but the prediction didn't parse".

EMA's users are domain scientists and engineers, not specialists in uncertainty quantification
(`../design/purpose.md`, "Who uses it").

## Decision

We will use these terms, in the documents, in messages, and in code:

- **Model parameter:** one of a model's variables whose value a design sets. The class is `ModelParameter`.
- **Model prediction:** a quantity that EMA reads from a run and analyzes. Each has a name, units, and a shape
  (OD-9). In code, the word is `prediction` (for example, `PredictionSpec` and `prediction=`), not `output` or
  `qoi`.
- **Model output:** anything a run produces: a Python function's return value, or the files, logs, and
  streams a command-line program writes. Model predictions are read from model outputs; for a command-line
  model, by its output parsers (OD-20).

"Input", "input parameter", "output" (for a model prediction), and "QoI" go to the glossary's Avoid column.
"Input deck" and "input file" stay: they name a simulator's own files, not EMA's model parameters.

The word for the region a design samples ("model parameter ranges", or "box") is not decided here. It becomes
its own open decision.

## Alternatives considered

- **Input and output (v1):** the most common words, and what v1's documents, tests, and code used. But
  "input" collides with a simulator's input deck and input files, "output" means both what a program writes
  and what EMA analyzes, and v1's words keep v1's concepts in view (decision 0002).
- **Factor and response (design of experiments):** precise for statisticians, but unfamiliar to many
  domain scientists.
- **Quantity of interest (QoI) for model predictions:** standard in uncertainty quantification, and v1's code
  name. But it is jargon from a field EMA's users don't have to know, and EMA is not a UQ package
  (`../design/purpose.md`). It stays in the glossary as a standard term that "model prediction" relates to.
- **"Model prediction" as the only word, with no "model output":** simpler, but it loses the difference
  between what a program writes and what EMA analyzes, which the model interface and the parsers need.

## Consequences

- **Glossary:** rows for "model parameter", "model prediction", and "model output", each linked to the
  standard terms (input, factor; quantity of interest, response). The "model" row becomes "maps model
  parameter values to model predictions". The region row (now "ranges / box (OD-3)") moves to the new open
  decision.
- **`STATUS.md`:** OD-3 moves to "Decided", naming this record, and a new OD row holds the region word.
- **Code names in `../design/architecture.md`:** `OutputSpec` becomes `PredictionSpec`; `ModelSpec.outputs`
  and `RunRecord.outputs` become `predictions`; every `qoi` argument and field becomes `prediction`
  (`RunBatch.y`, `Diagnostic.compute`, `Workspace.estimate`, `run`, `list_results`, `ResultSummary`); the
  comment "(n, d) means n points in d inputs" says model parameters. `parsers.py` keeps "output parsers": they
  read model outputs.
- **`../design/data_model.md`:** the `outputs` table, and the `inputs` and `input_hash` columns of `runs`, are
  renamed when that spec is written (step 8).
- **Other specs:** "input" and "output" in `contracts.md`, `principles.md`, `model_interface.md`, `scope.md`,
  and the guides are reworded as each is written.
- **A terminology test,** like v1's `test_terminology.py`, checks the Avoid column, and allows "input deck",
  "input file", and "output parser".
- **"Parameter" alone is ambiguous** once the glossary defines diagnostic parameters (a diagnostic's
  settings, such as n or the seed). The glossary has to say when the short form is allowed.
- **"Prediction" reads oddly for some quantities,** such as a solver's iteration count or a residual. The
  definition covers them, but a user may need the glossary to see that.
- **OD-10 (fixed parameters)** decides whether a variable a design never sets is still a model parameter; the
  definition here may change with it.
