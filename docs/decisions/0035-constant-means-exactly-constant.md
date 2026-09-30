# 0035. Call a model prediction constant only when every usable run gives the same value

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 6, the diagnostic specs' shared parts).

## Context

- **P6** (accepted) says: "When a diagnostic evaluation has too few usable runs, or a model prediction that is
  constant to rounding, its diagnostic result holds counts and a note, and no estimates. Every tolerance on a
  model prediction, including 'constant to rounding', is relative to that model prediction's range, so
  changing its units (y → a·y + b, with a > 0) changes no note." Its "Tested by" includes "a constant model
  prediction, and a constant plus 1e-12 noise each give counts and a note".
- **The two can't both hold.** A constant plus rounding noise has a range equal to the noise, so a tolerance
  relative to the range can't call it constant. Reference model R4b, 2.5 + 10⁻¹²·sin(40·(a + b + c)), makes the
  case concrete (`../design/reference_models.md`).
- **v1** called a model prediction constant when its range was at most 10⁻⁹·max|y|: relative to its magnitude,
  not its range (`_shape.py`, `FLAT_RTOL`). The lessons learned say "relative to the output's range", which
  doesn't match v1's code. A tolerance relative to magnitude is invariant under y → a·y, but not under shifts:
  R4b minus 2.5 is a pure 10⁻¹² wiggle.
- **v1's lesson G1:** with no flatness test, a diagnostic reported a 50% interaction share on 10⁻¹⁵ noise
  (`../notes/v1/lessons_learned_answers_2026-09-27.md`, "No data, no claims").
- In the step 6 interview, the owner chose, from a tolerance relative to magnitude (10⁻⁹, 10⁻¹⁰, or 10⁻¹²)
  and exact equality, exact equality.

## Decision

We will call a model prediction **constant** only when every usable run gives the same value, as a double.
There is no flatness tolerance.

- A constant model prediction gives counts and a note, and no estimates (P6, unchanged).
- A model prediction that varies, however little, is analyzed like any other: R4b gets estimates of its
  wiggle.
- Every tolerance on a model prediction stays relative to its range (P6, unchanged).
- **P6's statement** reads: "When a diagnostic evaluation has too few usable runs, or a model prediction that
  is constant (the same value in every usable run), its diagnostic result holds counts and a note, and no
  estimates. Every tolerance on a model prediction is relative to that model prediction's range, so changing
  its units (y → a·y + b, with a > 0) changes no note."
- **P6's "Enforced by":** "The minimum number of usable runs is a named constant, documented in each
  diagnostic's spec" (the flatness tolerance is gone).
- **P6's "Tested by":** "too few runs, all runs failed, and a constant model prediction each give counts and a
  note, with no estimates; a constant plus a 10⁻¹² wiggle (R4b) gives estimates."

## Alternatives considered

- **Relative to magnitude, 10⁻¹⁰:** flags R4a and R4b, but not 10⁶ + 10⁻³·f, with a margin of 10; a shift can
  change the note.
- **Relative to magnitude, 10⁻⁹ (v1):** the same, with 10⁶ + 10⁻³·f exactly at the edge.
- **Relative to magnitude, 10⁻¹²:** tighter; rounding in a large sum (10⁻¹³ to 10⁻¹⁰ relative) may not pass.
- **Relative to the range:** impossible, above.

## Consequences

- **Good:** no threshold to choose, defend, or revise; the note is invariant under every change of units that
  keeps distinct values distinct; each report describes the runs as they are.
- **Bad:** a model prediction that varies only by rounding gets estimates, which can look like structure
  (v1's G1). Every report's observations include the relative spread, (max − min)/max|y|, of the runs (0034),
  so the reader can see the case: R4b's is 8·10⁻¹³ (`../design/diagnostics/shared.md`).
- **`../design/principles.md`** (accepted): P6's statement, "Enforced by", and "Tested by", as above.
- **`../design/reference_models.md`:** R4b's expected answers are estimates, not a note.
- **`../design/contracts.md`** (step 7): the degenerate case "constant to rounding (about 10⁻¹⁵ relative)"
  expects estimates. The unit-invariance check uses changes of units that keep distinct values distinct in
  floating point: scalings by powers of 2, and shifts small enough not to merge values.
- **`../design/glossary.md`:** no change; the "note" row's "a constant model prediction" now means exactly
  constant.
