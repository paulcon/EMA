# Uncertainty

**Status:** accepted. **Updated:** 2026-10-01. **Depends on:** OD-4 (0004), OD-12 (0040); records 0017, 0034–0036,
0038, 0041, 0042, 0049, 0051, 0052; `diagnostics/shared.md` and the six diagnostic specs.

> The interval methods EMA uses, what each interval means, and which method each v2.0 diagnostic uses. Written
> from record 0040's table and the diagnostic specs' Uncertainty sections (TODO step 7, 2026-09-30). Each
> diagnostic's spec holds its own details and numbers; this page holds what they share, the bootstrap (its one
> home, 0052), and the seam for later methods.

## What an interval means in EMA

A **variability interval** shows how much an estimate changes when the runs behind it change: when they are
resampled, when the design is refined, or when some runs are held out (0004). Its method and settings are
always reported with it. It measures how much the estimate depends on the runs the diagnostic used; it is not
a statement about uncertainty in the model, its model parameters, or the system the model represents.

It is not a confidence interval or a credible interval: it carries no coverage probability, even when its
method makes confidence intervals under assumptions EMA doesn't check (here, that the runs are independent
draws and the estimate smooth enough in them). Reports, figures, and messages say "variability interval"; each
report with estimates says the difference once, in the sentence that opens its Estimates section
(`EXPLAIN_INTERVALS`, `diagnostics/shared.md`, Estimates; S4; 0042).

A number whose spec gives it no interval is an **observation** (0034): it describes the runs, not the model over
its model parameter space. A diagnostic result may hold observations only (0036). An estimate whose method gives
no interval in one diagnostic evaluation stays an estimate, with "none" and the reason (0041; Rules, below).

## Methods

| Method | What varies | Assumptions | Cost | In v2.0 |
|---|---|---|---|---|
| bootstrap | the usable runs, resampled with replacement | the runs are draws from one distribution over the model parameter space (uniform and convergent designs) | no new runs; one recomputation of each estimate per resample | scatter; linear and polynomial models (0040) |
| none | nothing | | none | the point run, coordinate lines, lines: their numbers are observations (0040) |
| subsampling the levels | subsets of n_(L−1) runs drawn without replacement from level L's | a rate for the estimate, to rescale the spread (the sampler's r) | no new runs | later, behind the interface (`diagnostics/linear_model.md`) |
| convergence over the levels | the design's levels, nested | none | the runs of the earlier levels | not an interval method: the levels' estimates are observations, in the per-level tables; nested levels share runs, and their span understated the spread over designs about fourfold (R3, `diagnostics/linear_model.md`) |
| cross-validation, held-out error | runs left out of a fit | | refits, or none by PRESS | not an interval method: the fits' leave-one-out error is an estimate, with a bootstrap interval |

## The bootstrap

This section is the bootstrap's one home: its steps, and its constants with their reasons (0052). A diagnostic
whose spec chooses it states only its differences: which estimates use distinct runs, what is undefined, and its
tag (Per diagnostic, below). None of the six changes a step or a constant.

1. **Resamples:** `BOOTSTRAP_RESAMPLES` = 1000, each n_u indices drawn with replacement from the n_u usable
   runs, in the design's order, by
   `Generator(PCG64(SeedSequence(seed, spawn_key=(tag,)))).integers(0, n_u, (1000, n_u))`, with `seed` the
   request's and `tag` the diagnostic's (`SCATTER_BOOT_TAG`, `LINEAR_BOOT_TAG`, `POLY_BOOT_TAG`; below). Every
   estimate in a diagnostic evaluation uses the same resamples.
2. **As drawn, or on distinct runs:** each estimate is recomputed on each resample as drawn, duplicates
   included, except an estimate whose formula assumes distinct runs, which is recomputed on the resample's
   distinct runs (about 0.63·n_u of them). In v2.0 these are scatter's binned index (copies of one run fall in
   one bin, and the bias adjustment assumes distinct runs) and the fits' leave-one-out error (a left-out run's
   copy stays in the fit). The diagnostic's spec names them, and so does the line under their table.
3. **Undefined resamples:** a resample on which an estimate is undefined (0/0; a fit's matrix of rank below its
   terms, by the rank rule below; too few distinct runs for leave-one-out) is dropped for that estimate, and
   counted.
4. **Interval:** the 0.5th and 99.5th percentiles (`BOOTSTRAP_PERCENTILES`) of the estimate's defined
   resampled values, by numpy's `percentile` with linear interpolation. Not the full range: the extremes come
   from the most degenerate resamples, and widen with the number of resamples toward the observed range (on
   R2's mean, scatter's design, resampled from `default_rng(0)`: [2.72, 4.45] at 1000, [2.31, 4.71] at 10⁵, and
   [−9.09, 12.85] over all resamples), while the percentiles are stable at 1000.
5. **Reported as computed:** the interval is not recentered on the estimate, shifted, or clipped. An estimate with
   a bias (the fitted polynomial's Sobol indices, `diagnostics/polynomial_model.md`) has an interval that carries
   it. On R2 the estimate was inside its interval for every estimate of scatter at n = 200 (50 designs) and the
   polynomial model at p = 4 (30 designs; a scratch script, 2026-09-30); the rule doesn't depend on it.
6. **The line under the table** (`shared.md`, S4) states: the method, the number of usable runs, the
   resamples, the percentiles, the seed, "recomputed on the distinct runs of each resample" where it applies,
   and the number of undefined resamples when there are any; the explanation of variability intervals is the
   Estimates section's opening sentence, not repeated under each table (0042).

## Rules

- **Every estimate** has a value, an interval or "none" with the reason, the method, and the method's settings
  (0004, 0041); with "none" it stays an estimate, not an observation. Only the interval may be "none". Where a
  value can't be computed, there is no estimate, and a note says why: the polynomial model reports no Sobol
  estimates when the fitted polynomial is constant (`diagnostics/polynomial_model.md`, 0049). The diagnostic
  result stores estimates with full doubles, and a "none" interval as null with its reason; the report prints
  them (`shared.md`).
- **"None" in an interval cell:** when fewer than `BOOTSTRAP_MIN_DEFINED` = 201 resamples are defined for that
  estimate. With m defined values, numpy puts the 0.5th percentile at position 0.005·(m − 1) in sorted order:
  4.995 at m = 1000, between the 5th and 6th smallest; below 1 when m ≤ 200, so each end would lie between the
  most extreme resample and the next, and depend on the most extreme one, close to the full range that step 4 of
  the bootstrap rejects as an interval. The line under the table gives the reason: "none: k of 1000 resamples
  defined, fewer than 201".
- **Below a diagnostic's minimum** there are no estimates at all (P6, S6), so "none" in a cell is a guard for
  pathological data: at each diagnostic's minimum, the undefined share is at most about 2% for a rank-deficient fit
  (2.01% at 6 runs), and up to 34% for the linear model's leave-one-out error at d = 1 (2(d + 1) = 4 runs; table
  below); a model prediction with one run differing from the rest leaves 63% to 68% defined (from n = 4 up).
- **Rank** (0051): a fit's matrix A has rank below its terms when its rank, by numpy's `matrix_rank` rule, is
  below them: the number of singular values above max(n, P)·ε·σ_max, with n × P the shape of A, σ_max its
  largest singular value, and ε the double's machine epsilon. The rule decides both fits' notes on the usable
  runs and their undefined resamples (`diagnostics/linear_model.md`, `diagnostics/polynomial_model.md`). There
  is no other rank tolerance: a near-deficient fit gets wide intervals, which say so.
- **Seeds:** a diagnostic's own draws come from its spawned stream, with tags from `SPAWN_TAG_BASE` = 2³² up, above
  every design stream's spawn key (`shared.md`, Random draws in a diagnostic; S8). A diagnostic with no draws has
  no tag, and records the request's seed (0 by default). Same request, same runs: the same intervals, bit for bit
  (P4).
- **No user settings in v2.0:** the method, the resamples, and the percentiles are named constants, not
  diagnostic parameters, so they are not part of a request's identity. Changing a default is a decision
  record, and a new EMA version in provenance (P5). An `interval` diagnostic parameter comes with a second
  method (below).
- **No checks against a rate or threshold:** no diagnostic compares an observed rate with the sampler's r, or an
  interval with a threshold (P2, 0017, 0040). No diagnostic needs two levels for its intervals (0040).

## The interval-method interface

One interface, with the bootstrap its only implementation in v2.0 (0040); subsampling the levels comes later
behind it (`diagnostics/linear_model.md`).

- **Takes:** the usable runs, as indices in the design's order, with their levels when the design has them;
  the estimators, each a pure function from a set of run indices to its values, marked "as drawn" or "distinct
  runs"; and the diagnostic's spawned stream.
- **Gives:** for each estimate, its interval or "none" with the reason, the count of undefined resamples, and
  the method's name and settings, from which the report writes the line under the table; the diagnostic
  result also records the spawn tag, which the line leaves out (0041).
- **Doesn't:** read the store, make runs, or know which diagnostic calls it (layer 1, `architecture.md`).
- **Tested by** a fake method registered in the tests: it replaces the bootstrap in each diagnostic with
  intervals (scatter, the linear and polynomial models), and the report's lines name it
  (`diagnostics/linear_model.md`, `diagnostics/polynomial_model.md`); C19 and C30 in `contracts.md`.

## Per diagnostic

| Diagnostic | Estimates with intervals | Method | On distinct runs | Undefined when | Tag | Minimum usable runs |
|---|---|---|---|---|---|---|
| point run | none: observations only | none | | | none | 1 (`POINT_RUN_MIN_RUNS`) |
| scatter | mean, standard deviation, rank correlations, binned indices | bootstrap | binned index | ρ and S: y constant on the resample (0/0); S: fewer than 2 distinct runs; the mean and standard deviation: never | 2³² + 1 | 10 |
| coordinate lines | none: each line's spectrum, degrees, and rate are observations (0038) | none | | | none | 1 (`COORD_MIN_RUNS`); a line's rate needs all its runs |
| lines | none: as coordinate lines | none | | | none | 1, as coordinate lines |
| linear model | coefficients, relative residual, R², LOO error | bootstrap over level L | LOO error | A of rank below d + 1; for LOO, fewer than d + 2 distinct runs (`diagnostics/linear_model.md`); R², the relative residual, and the LOO error, y constant on the resample (0/0, by step 3 of the bootstrap) | 2³² + 2 | 2(d + 1) |
| polynomial model | relative residual, R², Sobol indices, √E_k, LOO error; the coefficients, in the result and their data card, not the report (0041) | bootstrap over level L | LOO error | A of rank below P; for LOO, fewer than P + 1 distinct runs (`diagnostics/polynomial_model.md`); R², the relative residual, the LOO error, and the Sobol indices, y or the fitted polynomial constant on the resample (0/0, by step 3 of the bootstrap) | 2³² + 3 | 2P |

**Undefined resamples at the minimum** (the chance a resample of n runs has too few distinct runs; exact, from
the number of distinct values in n draws with replacement from n, 2026-09-30):

| Fit at its minimum | Runs | Rank below the terms | LOO undefined |
|---|---|---|---|
| linear, d = 1 | 4 | 1.6% | 34% |
| linear, d = 3 | 8 | 2.0% | 19% |
| linear, d = 8 | 18 | 0.9% | 5.7% |
| linear, d = 20 | 42 | 0.1% | 0.5% |
| polynomial, d = 2, p = 2 | 12 | 1.6% | 11% |
| polynomial, d = 1, p = 10 | 22 | 0.6% | 3.7% |
| polynomial, d = 8, p = 2 | 90 | 0.001% | 0.004% |

Scatter's rank correlations and binned indices are undefined only on a resample whose y values are all equal,
which needs a model prediction with very few distinct values: with one run differing from the rest, a share
(1 − 1/n)ⁿ of resamples, 35% at n = 10, rising toward 37% as n grows.

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `BOOTSTRAP_RESAMPLES` | 1000 | resamples per bootstrap | each end varies by about 3% of the interval's width between reseeds at this size (scatter interview; recomputed in the 2026-10-01 consistency check) |
| `BOOTSTRAP_PERCENTILES` | (0.5, 99.5) | the interval's ends | the owner's choice: wide, and still converging as resamples grow (scatter interview) |
| `BOOTSTRAP_MIN_DEFINED` | 201 | the fewest defined resamples an interval is made from | below it, each end depends on the most extreme resample |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| V1 | The bootstrap draws its resamples from the diagnostic's spawned stream; the same request and runs give the same intervals, bit for bit. | Twice on R2, each bootstrapping diagnostic; changing its tag changes the intervals, not the design (S8). |
| V2 | Every estimate in a diagnostic evaluation uses the same resamples. | A recording estimator: the index sets it receives are identical across estimates. |
| V3 | An estimate marked "distinct runs" receives each resample's distinct indices, once each, in the design's order. | A recording estimator, on a resample with known duplicates. |
| V4 | Undefined resamples are dropped per estimate and counted; the count is in the result and in the line under the table. | Scatter's two-valued fixture at n = 10 (SC5); linear model at 2(d + 1), d = 1. |
| V5 | The interval is numpy's linear-interpolation percentiles (0.5, 99.5) of the defined values, not recentered or clipped. | A fixture estimator whose resampled values are 0, 1, …, 999: [4.995, 994.005]. |
| V6 | "None" in an interval cell exactly under the rule above, with the reason in the line under the table. | Fixture estimators defined on 0, 200, and 201 of the 1000 resamples: none, none, an interval. |
| V7 | A fake interval method replaces the bootstrap, and the report's lines name it. | The fake method on scatter and the linear and polynomial models. |

## What this spec asks of other documents

- **Architecture (step 9):** `Estimate` records the method and its settings, the undefined count, and the reason
  for "none"; not a confidence `level` (0004); `numerics/intervals.py` holds the interface and the bootstrap,
  and no `convergence_interval` (0040).
