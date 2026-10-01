# 0023. Hold a model parameter at its nominal value when a design's space leaves it out

**Date:** 2026-09-30. **Status:** accepted; its held values amended by 0033. **Resolves:** OD-10.

## Context

The owner's 2026-09-23 notes ask "what parameters are available in the model that are not design variables
and how to access them": numeric settings the analyst usually doesn't vary, such as a mesh size, a solver
tolerance, or a load held fixed in a study.

In v1 there was no such concept. Every input needed a range in every design (`check_ranges`), and settings
the analyst didn't vary stayed as literal text in the template or the code
(`../../../EMA-v1/docs/guides/input_deck_model.md`). Varying one later meant making it an input: a new model
version.

Record 0005 made the model parameter space a property of the design, not of the model. Whether a model
parameter varies can then also be a property of the design. The architecture draft already says a
zero-width range means "held at this value" (`../design/architecture.md` §3).

## Decision

We will treat a variable the analyst usually doesn't vary as an ordinary model parameter, held by the designs
that don't vary it.

- **Declared as a model parameter**, with its nominal value, like any other. The model spec has no separate
  list of fixed values or constants.
- **Held at nominal.** A design's model parameter space may name a subset of the model parameters. Every model
  parameter it leaves out is held at its nominal value.
- **Every point is complete:** it has a value for every model parameter, held ones included. Runs are keyed by
  the complete point (P3), so two spaces that hold a model parameter at the same value share runs at their
  common points.
- **Non-numeric settings** (a solver's name, a scheme) stay literal in the model's files; changing one changes
  a tracked file, and so the model version (P3).

Holding a model parameter at a value other than its nominal (a zero-width range) is for `designs.md` (step 5).

## Alternatives considered

- **Literal in the model's files (v1):** nothing new in the spec, but varying the value later means making it
  a model parameter, a new model version, and no reuse of runs.
- **A `constants` mapping on the spec:** filled into the template or passed to the function, never varied by a
  design. One more field, and a second way to give the model a value.
- **Every model parameter in every space (v1):** explicit, but a 20-parameter model needs 20 ranges for a
  3-parameter study.

## Consequences

- **`../design/model_interface.md`:** "What a model takes" has no fixed values or constants; a point has a
  value for every model parameter.
- **`../design/designs.md`** (step 5): a space may name a subset of the model parameters; design generators
  hold the rest at nominal; whether a zero-width range holds one at another value. Figures skip held model
  parameters.
- **`../design/glossary.md`** (accepted): the "model parameter" row adds "a design that doesn't vary it holds
  it at its nominal value (0023)"; the "point" row says a point has a value for every model parameter,
  including the held ones.
- **Reports and provenance** (steps 6, 8): the header lists the held model parameters and their values, since
  they decide the runs as much as the varied ones.
- **Versions (this spec, item 10):** whether a nominal value is part of the model version. It no longer decides
  what a run does, since the point carries the value.
- **`../../STATUS.md`:** OD-10 moves to "Decided", naming this record, when it is accepted (0001).
