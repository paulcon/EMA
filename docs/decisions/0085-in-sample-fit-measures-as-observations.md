# 0085. Report a fit's in-sample relative residual and R² as observations, without intervals

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

## Context

The linear model and the polynomial model give the fit's relative residual and R² as estimates, with bootstrap
variability intervals (`uncertainty.md`, the table's rows for the two fits; records 0040, 0041). The bootstrap
recomputes each estimate on each resample of the usable runs; these two are recomputed "as drawn", duplicates
included (`uncertainty.md`, Rules, item 2), while the leave-one-out error is recomputed on each resample's distinct
runs.

In the owner's session after the demo's rehearsal, a client noticed that in three polynomial-model evaluations (on
the Ishigami function, degrees 6, 8, and 10) the in-sample relative residual and R² fell outside their own
intervals, every time: for example a relative residual of 0.001229 against [0.001034, 0.001169]. The leave-one-out
error sat inside its interval every time.

The cause is the bootstrap's duplicates. A resample of n runs holds about 0.63·n distinct runs, so each refit
has fewer distinct points per coefficient than the fit it varies, and its in-sample residual is smaller: the
fit "sees" fewer points to miss. The whole bootstrap distribution of an in-sample measure therefore sits on the
optimistic side of the full fit's value, by an amount that grows with the number of coefficients P against the
number of distinct runs. The specs knew of the in-sample residual's bias (`linear_model.md`: "The relative residual's
interval shows variability, not the in-sample residual's bias at small n"), but not that the interval can miss
its own estimate. An interval that excludes its estimate invites exactly the misreading the client flagged. It
also conflicts with what a variability interval says it is (`EXPLAIN_INTERVALS`: "how much its estimate changes
when the runs behind it change"): here it mostly shows the resampling's own bias.

**Measured** 75 evaluations through the workspace, at
the diagnostics' defaults (level 2, so the fit uses about 8P runs) with seeds 0–3, on R1, R2 (Ishigami), R3
(borehole), R7, R10, and R11, at the linear model and the polynomial model of degree 2 and 3; and Ishigami at
degrees 6, 8, and 10 (seed 0). The count of evaluations whose estimate falls outside its own interval:

| Case | Runs | Relative residual | R² | Leave-one-out error |
|---|---|---|---|---|
| Polynomial, degrees 6, 8, 10, on Ishigami | 672–2,287 | 3 of 3 | 3 of 3 | 0 of 3 |
| Linear model on R11 (seeds 0–3) | 24 | 1 of 4 | 1 of 4 | 0 of 4 |
| Linear model on R1, R2, R3, R7, R10 | 32–72 | 0 of 20 | 0 of 20 | 0 of 20 |
| Polynomial, degrees 2 and 3, on R2, R3, R7, R11 | 48–1,320 | 0 of 32 | 0 of 32 | 0 of 32 |
| Polynomial, degree 3, on R1 and R10 (exactly polynomial) | 280 | 1 of 8 | 0 of 8 | 2 of 8 |

The bias shows when the fit is good (a small residual, so a narrow interval) and has many coefficients: the
resampling's optimism then exceeds the interval's width, as on Ishigami at high degree, every time. The last row
is another matter: R1 and R10 are polynomials of degree 1 and 2, every measure is at rounding (about 10⁻¹⁵), and
inside or outside is noise, the leave-one-out error included. The relative residual is "above" its interval and R²
"below" its, as the optimism predicts.

## Decision

We will:

1. **Report the in-sample relative residual and R² as observations, not estimates,** in both fits: at level L in
   the fit's observations, as the per-level table already reports them at every level, with no interval. The
   leave-one-out error stays the fit's estimate with its bootstrap interval (recomputed on each resample's
   distinct runs), as the measure of how the fit varies with the runs and of its error on runs it didn't see.
2. **Say why, once, under the fit's observations:** "In-sample measures: refitting a resample's repeated runs
   makes the fit look better than it is, so they have no variability interval; the leave-one-out error's
   interval shows how the fit varies."
3. **Keep everything else of the bootstrap:** the coefficients (and the polynomial model's Sobol indices and √E_k)
   keep their intervals: they aren't measures of the fit's own error, and C5's and V-tests keep covering them.
   Whether their intervals have a like bias (a coefficient refit on duplicated runs) is a question for a later
   measurement, not this record.

## Alternatives considered

- **"none: reason" for their intervals** (record 0041's form): keeps them estimates with an interval that never
  exists. "none" is for an interval a method fails to give on one evaluation (too few defined resamples), not one
  that is wrong by construction; observations say it plainly.
- **Recompute them on each resample's distinct runs**, as the leave-one-out error is: fewer distinct points per
  coefficient makes the in-sample fit look better still.
- **A different method for them:** a residual bootstrap (the design fixed, so no duplicates) or a bias-corrected
  percentile interval. Possible later, each a new estimator with its own spec and known answers (V-tests); not a
  fix.
- **Leave them as they are, with a note:** an interval that misses its estimate keeps misleading readers, human or
  not.

## Consequences

- Spec edits on acceptance: `uncertainty.md` (the two fits' rows: estimates with intervals become the
  coefficients and the leave-one-out error, and for the polynomial model the Sobol indices and √E_k; the relative
  residual and R² move to observations); `linear_model.md` and `polynomial_model.md` (Compute, the Estimates
  and Observations sections, the known answers' tables, the mock reports, and the line under the observations);
  `shared.md` if its Estimates/Observations rules name them.
- Code: both diagnostics' tables (`linear_model.py`, `polynomial_model.py`, `_fits.py`); their golden reports
  and known-answer tests; the contract's C5 and C11 checks over them (estimates fewer, observations more). About 2
  hours with tests, plus a review.
- The bootstrap's work is unchanged (the relative residual and R² are cheap beside the refits), so no time is
  saved.
- Results stored before the change keep their intervals; a reproduce of one (U8) under the new code reports the
  difference as a version difference, as any change to a diagnostic does.
