# 0024. Put scales in the model parameter space, and a model parameter's limits in the model spec

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 4; the scales left open by 0005).

## Context

Record 0005 made the model parameter space part of the design, and left scales (linear or log: whether a design
spreads a model parameter evenly in its value or in its logarithm) to the model interface. The architecture
draft keeps `scale` on `ModelParameter` (`../design/architecture.md` §3). v1 kept it on the input, excluded it
from the version hash, and so an edited scale silently changed the stored spec for every campaign of that model
version; its lessons conclude "the input box and scales belong to the design, not the model"
(`../notes/v1/lessons_learned_2026-09-27.md` §4).

A model may be defined only for some values of a model parameter: a conductivity must be positive, a porosity
between 0 and 1. v1 checked `positive`, `nonnegative`, and `bounds` constraints on inputs and outputs at every
run, and stored a point outside as `invalid_input` and an output outside as `constraint_violation`, each with
its own reuse rule (`../../../EMA-v1/src/ema/core/checks.py`). The glossary (accepted) lists "bounds" as a
standard term for model parameter ranges, which belong to the design.

v1's inputs were continuous only.

## Decision

- **Scales belong to the space.** A design's model parameter space says which model parameters are spread in
  their logarithm. A model parameter has no scale, and changing a scale never changes a model version.
- **Limits belong to the model.** A model parameter may have limits: a lower and an upper value outside which
  the model isn't defined; either may be left out, and each may be strict ("> 0") or not ("≥ 0").
  A space that crosses a limit is refused when its design is built, with the model parameter and the limit
  named. No run is ever refused at its point, so v2.0 has no `invalid_input` status.
- **No constraints on model predictions.** A non-finite value is a missing model prediction, with its reason
  (0022).
- **Continuous only.** Every model parameter takes real values. A held integer setting still works, since its
  nominal value is written as an integer when it is one (the number format, this spec).

## Alternatives considered

- **A default scale on the model parameter, overridable in the space:** convenient for a model parameter that
  is always spread in its logarithm, but a spec field that doesn't decide a run, which is how v1's edited
  scales went unnoticed.
- **Scale on the model parameter only (the architecture draft):** one place, but another scale for one study
  means another model spec.
- **v1's checks at every run:** two more statuses (`invalid_input`, `constraint_violation`) and a reuse rule for
  each, for a problem the design can refuse before any run.
- **No limits in v2.0:** the model fails where it isn't defined, with its own reason; but a log scale, or a
  space of physically meaningless values, is caught only by failed runs.
- **An integer kind:** designs would need rounding rules, and lines and spectra would mean something else in
  each diagnostic. Later: one small step in the designs, plus a line in each diagnostic spec.

## Consequences

- **`../design/model_interface.md`:** a model parameter has a name, units, a description, a nominal value
  (inside its limits), and optional limits; no scale, no constraints.
- **`../design/glossary.md`** (accepted): a row for **limits**, "the values of a model parameter outside which
  the model isn't defined, given in the model spec; a model parameter space must stay inside them (0024)",
  with standard terms "bounds, constraints, domain of definition"; and a row for **scale**, "whether a design
  spreads a model parameter evenly in its value (linear) or its logarithm (log); part of the model parameter
  space (0024)".
- **`../design/designs.md`** (step 5): the space carries each model parameter's scale; a log scale needs a
  positive range; a space that crosses a limit is refused, before any run.
- **`../design/architecture.md`** (step 9): `ModelParameter` loses `scale` and `constraint`, and gains
  `limits`; `Scale` moves to the space's module; `RunStatus` has no `INVALID_INPUT`.
- **Versions:** limits are part of the model version (item 10 of the step 4 interview decides the rest of
  what the version covers).
