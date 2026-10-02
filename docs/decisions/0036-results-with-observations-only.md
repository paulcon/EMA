# 0036. Let a diagnostic result hold observations without estimates or a note

**Date:** 2026-09-30. **Status:** accepted; its "only the point run" amended by 0038 and 0040 (coordinate lines and lines). **Resolves:** none (TODO step 6, the point run's spec).

## Context

- **P6's "Enforced by"** (accepted) says: "`DiagnosticResult` refuses to be built with neither estimates nor a
  note". The check keeps a diagnostic result from being empty: when there are no estimates, a note says why.
- **Record 0034** (accepted) added observations, and left P2's enforcement unchanged.
- **The point run** (`../design/diagnostics/point_run.md`, draft) reports only observations (OD-12: no interval
  method). On a deterministic model it has no note: one distinct value is its ordinary answer, and U7 says
  "on a deterministic reference model, the repeats measure no variation, and no note is added". Its diagnostic
  result has observations, no estimates, and no note, which P6's check refuses.

## Decision

We will count observations in P6's check. P6's "Enforced by" reads: "`DiagnosticResult` refuses to be built
with no estimates, no observations, and no note."

- A diagnostic result with no estimates still needs a note, unless its spec says its numbers are observations
  only. Only the point run's spec says so in v2.0.

## Alternatives considered

- **Give the point run a note on a deterministic model** ("no variation measured"): keeps P6's check, but U7
  says no note is added, and a note is a caveat about the data, which "no variation" isn't.
- **Make the point run's standard deviation an estimate:** it would need an interval method, and its interval
  would be poor from 5 runs; in the interview, the owner chose observations only.

## Consequences

- **`../design/principles.md`** (accepted): P6's "Enforced by", as above.
- **`../design/contracts.md`** (step 7): the diagnostic contract checks that every diagnostic result has an
  estimate, an observation, or a note, and that a diagnostic whose spec promises estimates has estimates or a
  note.
- **`../design/architecture.md`** (step 9): the check in `DiagnosticResult`'s constructor.
