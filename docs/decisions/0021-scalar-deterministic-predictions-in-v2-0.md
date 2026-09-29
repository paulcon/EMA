# 0021. Analyze scalar model predictions of models not declared noisy in v2.0

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** none (TODO step 3, scope; P7's "Open").

## Context

P7 (accepted) treats a model as deterministic unless its spec says it is noisy, or repeated runs measure
variation, and leaves "whether noisy models are in v2.0" to scope. U7 needs only the point run and its note,
whatever scope decides. A model declared noisy would run each design point several times, and each of the six
diagnostics (0012) would need a rule for its replicates, and known answers with noise.

Simulation codes often write arrays: fields over a mesh, time series. v1 stored arrays in a blob store but
analyzed scalars; U5 notes that array model predictions would need another export format. How many scalar model
predictions a model has is OD-9 (step 4). Record 0020 keeps each run's model output in its run directory, so
arrays stay available for inspection by hand.

## Decision

In v2.0, EMA stores and analyzes **scalar** model predictions only, of models **not declared noisy**.

- **Arrays** are not model predictions in v2.0: there is no blob store, and no output parser returns an array.
  An array a model writes stays in its run directory (0020).
- **A model spec with `noisy: true` is refused** at loading, with a message that models declared noisy come in
  a later version. The point run still measures the noise of a model not declared noisy, and later diagnostic
  results carry the note (P7, 0011, U7).

What keeps the later versions cheap:
- model predictions are stored in their own table, keyed by run and name, so array values can be added later
  as blobs (step 8);
- the store key already has a replicate number (P7), and the model spec has the `noisy` field.

Estimated effort later: arrays take one or two build steps (a blob store, array output parsers, an export
format, and a way to choose a scalar from an array); models declared noisy take about one build step (a repeat
count in each design), plus a section on replicates in each of the six diagnostic specs, with known answers.

## Alternatives considered

- **Store arrays, analyze scalars:** arrays kept in the store, but a blob store and array parsers before any
  diagnostic uses them, while the run directory already keeps them (0020).
- **Models declared noisy in v2.0:** a rule for replicates in each diagnostic, and known answers with noise,
  before the first release.

## Consequences

- **`../design/scope.md`:** "In v2.0" says scalar model predictions of models not declared noisy; "Not in
  v2.0" lists array model predictions and models declared noisy, as later.
- **`../design/principles.md`:** P7's "Open" is settled by this record; its statement is unchanged.
- **`../design/model_interface.md`** (step 4): output parsers return scalars; `noisy: true` is refused.
- **`../design/data_model.md`** (step 8): a table of model predictions keyed by run and name; no blob store.
- **`../design/architecture.md`** (step 9): `store/blobs.py` is not in v2.0.
- **`../design/use_cases.md`:** U7 works as written.
