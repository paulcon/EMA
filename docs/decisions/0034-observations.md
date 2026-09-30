# 0034. Report numbers without intervals as observations

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 6, the diagnostic specs' shared parts).

## Context

- **P2** (accepted) says a diagnostic result "holds only estimates, counts, notes, and figures". The glossary
  (accepted) defines an estimate as "a number with its variability interval and the method that made the
  interval", and a diagnostic result as "estimates, counts, notes, and figures, and the provenance recorded
  with them".
- **U1** (accepted) asks for "the observed minimum and maximum of the runs, as observations, not estimates".
  An interval on an extreme is poorly behaved (a bootstrap of the maximum never exceeds it), and the observed
  maximum is a fact about the runs, not a claim about the model.
- **The point run** reports the model prediction at its point: a run's value, read, not estimated.
- Neither is a count, and neither has a variability interval, so neither fits P2's list.

## Decision

We will add a fifth kind of number to a diagnostic result: the **observation**.

- **Glossary row** (new): "**observation**: a number read or computed directly from a diagnostic evaluation's
  usable runs, with no variability interval, such as a run's model prediction, or the minimum and maximum of
  the runs; it describes the runs, not the model over its model parameter space (0034)". Standard terms:
  "observed value, sample statistic, summary statistic".
- **The glossary's "diagnostic result" row:** "estimates, observations, counts, notes, and figures, and the
  provenance recorded with them".
- **P2's statement:** "A diagnostic result holds only estimates, observations, counts, notes, and figures."
- **Wording:** an observation's label says what it is of ("the minimum of the runs"), never a property of the
  model ("the minimum of T_max").
- **Reports** show observations in their own section, after the estimates (`../design/diagnostics/shared.md`).
- Whether a number is an estimate or an observation is fixed in each diagnostic's spec. A number that stands
  for a property of the model over the space (a mean, a correlation, a coefficient) is an estimate, with an
  interval.

## Alternatives considered

- **Estimates only:** no new word, but the observed extremes would need intervals that mislead, or would be
  dropped, and the point run's value would need an interval made from its repeats even when there are none.
- **Widen "counts":** no new word, but "count" would then mean any number without an interval, which isn't
  what the word says.

## Consequences

- **`../design/glossary.md`** (accepted): the new row, and the "diagnostic result" row, as above.
- **`../design/principles.md`** (accepted): P2's statement, as above. Its enforcement is unchanged:
  `DiagnosticResult` still has no field for a verdict.
- **`../design/diagnostics/shared.md`:** the report's Observations section; each diagnostic spec says which of
  its numbers are observations.
- **`../design/architecture.md`** (step 9): `DiagnosticResult` gains an `observations` field beside its
  estimates.
- **`../design/contracts.md`** (step 7): the diagnostic contract's degenerate cases apply to observations too
  (all runs failed: no observations; too few runs: those that need more runs than there are are left out).
