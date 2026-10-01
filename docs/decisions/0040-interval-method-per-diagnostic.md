# 0040. Bootstrap the fits and the scatter; no intervals for points and lines

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** OD-12.

## Context

OD-12 asks for the interval method of each v2.0 diagnostic, with options bootstrap, convergence,
cross-validation, and held-out error. A variability interval says how much an estimate changes when the runs
behind it change (0004); a number with none is an observation (0034), and a diagnostic result may hold
observations only (0036).

Each diagnostic spec chose its method in its interview (TODO step 6, 2026-09-30), with numbers computed on the
reference models; all six specs are accepted:

- **Point run** (`../design/diagnostics/point_run.md`): its numbers describe the runs at one point, not a
  property of the model.
- **Scatter** (`scatter.md`): the bootstrap, with the binned index recomputed on each resample's distinct runs;
  `shared.md` set the bootstrap's defaults (1000 resamples, the 0.5th to 99.5th percentiles), after a computed
  comparison on R2 of percentiles against the full range.
- **Coordinate lines** (`coordinate_lines.md`, 0038): the decay rate is an observation; an interval from a
  nested subline, recommended in the interview, was declined.
- **Lines** (`lines.md`): as coordinate lines.
- **Linear model** (`linear_model.md`): the bootstrap over level L; the span of nested levels was about a
  quarter of the spread over designs, so the levels are observations. Subsampling the levels is planned as a
  later method, with its seams kept.
- **Polynomial model** (`polynomial_model.md`): as the linear model; refits as drawn, LOO on distinct runs.

`../design/designs.md` (accepted) left two questions for OD-12: whether a diagnostic needs two or more levels of
a convergent design for its interval, and whether it checks the observed rate against the sampler's r.

## Decision

We will use these interval methods in v2.0:

| Diagnostic | Method | Estimates with intervals | Spawn tag |
|---|---|---|---|
| point run | none | none: observations only | none |
| scatter | bootstrap over the usable runs | mean, standard deviation, rank correlations; the binned index on each resample's distinct runs | 2³² + 1 |
| coordinate lines | none | none: each line's spectrum and decay rate are observations | none |
| lines | none | none: as coordinate lines | none |
| linear model | bootstrap over the usable runs of level L | coefficients, relative residual, R²; LOO on each resample's distinct runs | 2³² + 2 |
| polynomial model | bootstrap over the usable runs of level L | relative residual, R², Sobol indices, √E_k; LOO on each resample's distinct runs | 2³² + 3 |

- **The bootstrap** has `shared.md`'s defaults: 1000 resamples from the diagnostic's own spawned stream, the
  same for every estimate, the 0.5th and 99.5th percentiles, undefined resamples dropped and counted.
- **No diagnostic needs two levels** of a convergent design for its interval: the fits' intervals come from
  level L alone, and the earlier levels are observations.
- **No diagnostic checks an observed rate** against the sampler's r: a check compares with a threshold, which is
  interpretation (P2, 0017).
- **One interval-method interface,** with the bootstrap its only implementation in v2.0; subsampling the levels
  (`linear_model.md`) is a later method behind it.
- Convergence and cross-validation are not interval methods in v2.0; the fits' LOO error is an estimate with a
  bootstrap interval, not a method for other estimates' intervals.

## Alternatives considered

- **Intervals for the point run** (the spread of its replicates): its numbers describe one point's runs; a
  deterministic model's replicates agree exactly (0011), and a noisy one's spread is itself the observation (P7).
- **Intervals for the lines' rates** from a nested subline or the even and odd sublines: no new runs, but a
  proxy, not the variability of the rate over runs (`coordinate_lines.md`); declined in the interview.
- **Convergence over the levels** for the fits (U4's example): nested levels share runs, so their span
  understated the spread over designs about fourfold (`linear_model.md`).
- **Subsampling the levels** (Politis and Romano 1994): planned for later, behind the interface.

## Consequences

- **`STATUS.md`:** OD-12 moves to "Decided", naming this record, when it is accepted (0001).
- **`../../TODO.md`:** step 6 is done; step 7's "Decide: OD-12" becomes "Decided: OD-12 (0040)".
- **`../design/designs.md`** (accepted): "are for OD-12 (step 7)" and the matching line in "What this spec asks
  of other documents" are answered: no diagnostic needs two levels, and none checks the rate (0040).
- **`../design/uncertainty.md`** (step 7): written from this table, with the interval-method interface, the
  bootstrap's defaults, the distinct-runs rule, and the spawn tags.
- **`../design/use_cases.md`** (accepted): U4's "(for example, convergence over the design's levels, OD-12)"
  is an example only, and stays as history; the polynomial model's intervals are the bootstrap's.
- **Tests:** S8 (spawn tags), SC, LM, and PM's interval requirements; the fake interval method in the
  interface's test.
