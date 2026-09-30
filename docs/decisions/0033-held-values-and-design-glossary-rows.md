# 0033. Let a space hold a model parameter at a value, and add design words to the glossary

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 5: held values left open by 0023;
the glossary row for "design generator").

## Context

- **Held values.** Record 0023 holds a model parameter that a space leaves out at its nominal value, and left
  to `../design/designs.md` whether a space can hold one at another value. Nominal values are part of the model
  version (0029), so changing one to hold a model parameter elsewhere makes a new model version, and no stored
  run is reused. In the step 5 interview, the owner chose to let a space give a number in place of a range: a
  held value, inside the limits. The accepted glossary's "model parameter" row says "a design that doesn't
  vary it holds it at its nominal value (0003, 0023)", which now has an exception.
- **Design words.** TODO step 5 asks for a glossary row for "design generator". The interview added two words
  that are public names or appear in reports: "sampler" (0032) and "nested" (U3–U5, `designs.md`).
- **The sampler's rate.** Record 0032 (accepted) lists the sampler interface as `name`, `version`,
  `unit_rows`, `nested`, and `balanced_sizes`. The interview then made the convergent design's alpha an error
  factor (`../notes/v1/ema-redesign.md`: "error factor alpha"): n_l = ⌈n_min · alpha^(−l/r)⌉, where r is the
  rate at which an estimate's error from the sampler's points is assumed to fall (½ for random points, about
  1 for Sobol). The sampler has to declare r.

## Decision

- **Held values:** a model parameter space may give a number in place of a range, which holds that model
  parameter at that value for the design; it must be inside the limits. A model parameter the space leaves
  out is still held at its nominal value (0023).
- **The glossary** (accepted) changes:
  - **model parameter:** "one of a model's variables whose value a design sets; a design that doesn't vary it
    holds it at its nominal value, or at a held value its model parameter space gives (0003, 0023, 0033)".
  - **design generator** (new): "what makes a design from a model parameter space (or, for the point design, a
    point) and its diagnostic parameters, with its size computed before it is built; v2.0 has point, uniform,
    convergent, and lines (given, coordinate, or random); a new kind of design is a new design generator
    (`designs.md`)". Standard terms: "sampling scheme, design of experiments method".
  - **sampler** (new): "what makes the points of a uniform or convergent design in the unit cube, with the rate
    at which an estimate's error is assumed to fall; part of the design's identity; v2.0 has `random` (0032)".
    Standard terms: "random number generator, quasi-Monte Carlo sequence, low-discrepancy sequence".
  - **nested** (new): "said of two designs when the smaller one's points are points of the larger, so the
    larger reuses the smaller's runs; `designs.md` says which designs are nested, and in what". Standard terms:
    "nested designs, extensible sequence, sequential design".
- **The sampler interface** of 0032 gains `rate`, r; `random` declares ½.

## Alternatives considered

- **Nominal only** (no held values): one way to give a model parameter a value, but holding one elsewhere
  makes a new model version and reuses nothing.
- **Held values written as a zero-width range** (the architecture draft): the same meaning, but a range whose
  ends are equal reads as a mistake; the space's JSON form uses a number.
- **A separate "held value" row:** the amended "model parameter" row and `designs.md` say enough.
- **"sampler" and "nested" at step 9, or not at all:** both are already in the designs spec, a public field,
  and the use cases.
- **alpha as a growth factor** (the first draft of `designs.md`): doubling is exact (alpha = 2), but the
  request isn't in terms of error, and the rate would be implicit.
- **The exponent fixed at 2** (n_l = ⌈n_min · alpha^(−2l)⌉): simplest, but a later Sobol sampler would
  over-sample, or need a record to change the rule.

## Consequences

- **`../design/glossary.md`:** the rows above, applied when this record is accepted.
- **`../design/designs.md`:** the space's JSON form takes a number as a held value; the Samplers section lists
  `rate`; the convergent design's sizes use it.
- **Reports** (step 6): the header lists held model parameters with their values, nominal or held.
- **Architecture** (step 9): the design generator registry is the seam for new kinds of design; the space's
  type has no zero-width ranges.
- Record 0032 stays as accepted; this record extends its interface.
