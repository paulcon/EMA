# 0017. Leave experimental interpretation out of v2.0

**Date:** 2026-09-29. **Status:** accepted; its report contents amended by 0034 (observations). **Resolves:** OD-8.

## Context

In v1, interpretation (flags, advice, synthesis, findings, surrogates, and the checks that police the agent's
prose) made up about 5,500 of 28,000 source lines, caused most eval failures and most of the reliability
work, and took six phases to split out as "experimental" at the end
(`../notes/v1/lessons_learned_2026-09-27.md` §1, §3).

P2 (accepted) says a diagnostic result holds no interpretation, and that if EMA produces any, it is labeled
experimental and kept in its own section. The architecture draft has an `ema.experimental` package and a
`Report.experimental` field (`../design/architecture.md` §6, §9).

## Decision

We will produce no interpretation in v2.0: no `ema.experimental` package, no `interpret()`, no
interpretations table, and no experimental section in reports. Reports hold estimates with variability
intervals, counts, notes, and figures only (P2).

## Alternatives considered

- **A separate, labeled section in v2.0:** keeps P2's machinery exercised from the start, but adds a package,
  named thresholds, a table, a renderer, and their tests before the diagnostics themselves are verified.

## Consequences

- **`../design/scope.md`:** the interpretation row says none; "Not in v2.0" lists interpretation, advice, and
  next steps, as later, under P2's rules.
- **`../design/principles.md`:** P2 is unchanged; its statement covers this ("if EMA produces any"). The parts
  of its enforcement that concern `ema.experimental` apply when the package is added.
- **`../design/architecture.md`** (step 9): §9 (`ema.experimental`), `Report.experimental`, and the
  `--experimental` flags are removed from v2.0. §6's "additivity and low-dimensional structure" in the
  polynomial model's report are reported as numbers with intervals (such as the interaction share), or not
  at all (step 6).
- Adding interpretation later is a decision with its own record, a spec, and P2's tests.
- **`STATUS.md`:** OD-8 moves to "Decided", naming this record, when it is accepted (0001).
