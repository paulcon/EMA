# 0041. Let an estimate's interval be "none", give the polynomial coefficients intervals, and keep spawn tags out of the report

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (step 7's consistency check).

## Context

A check of `../design/uncertainty.md` and `../design/contracts.md` against the other specs (TODO step 7,
2026-09-30) found three disagreements between accepted documents. Each was there before step 7:

- **"None" as an interval.** `../design/diagnostics/shared.md` (Estimates) lets an estimate's interval cell say
  "none" with the reason, and `../design/uncertainty.md` adds a case: fewer than 201 of the 1000 resamples
  defined (`BOOTSTRAP_MIN_DEFINED`). The glossary defines an estimate as "a number with its variability interval
  and the method that made the interval", and an observation as a number "with no variability interval";
  `../design/purpose.md` says "Reports include variability intervals for all estimates". Read literally, an
  estimate with "none" is an observation, and the purpose page's promise fails in that case.
- **The polynomial model's coefficients.** `../design/diagnostics/polynomial_model.md` stores all P coefficients
  in the diagnostic result and a data card, not in the report, and refits them on every bootstrap resample. Record
  0034 says "a number that stands for a property of the model over the space (a mean, a correlation, a
  coefficient) is an estimate, with an interval". Record 0040's table gives the polynomial model's intervals to
  the relative residual, R², the Sobol indices, √E_k, and LOO, not the coefficients. So the coefficients'
  status is undecided.
- **The spawn tag in the report.** `../design/diagnostics/linear_model.md` (Later: intervals by subsampling the
  levels) keeps as a seam "the method, its settings, and its spawn tag named in the result and under each
  table". Every accepted mock report's line under a table (`shared.md`, scatter, linear model, polynomial model)
  names the seed but not the tag.

## Decision

We will:

1. **Let an estimate's interval be "none", with its reason.** An estimate is a number whose spec gives it a
   variability interval; when its method gives none for a diagnostic evaluation (`shared.md`, Estimates;
   `../design/uncertainty.md`, Rules), its interval is "none", with the reason in the line under the table. It
   stays an estimate, not an observation. The glossary's "estimate" row says so. `purpose.md` is unchanged: it
   states the goal, and the rules for "none" are in `uncertainty.md`.
2. **Give the polynomial model's coefficients bootstrap intervals in the diagnostic result.** Each of the P
   coefficients is an estimate with its interval, from the resamples already drawn, stored in the diagnostic
   result and the coefficients' data card; the report still leaves them out (its Sobol indices and √E_k summarize
   them). This adds the coefficients to record 0040's polynomial model row.
3. **Keep the spawn tag in the diagnostic result and its provenance, not in the line under the table.** The line
   names the method, its settings, and the seed, as every mock report shows. `linear_model.md`'s seam reads "the
   method, its settings, and its spawn tag named in the result, and the method and its settings under each
   table".

## Alternatives considered

- **Amend `purpose.md` too** ("variability intervals for all estimates, or the reason there is none"): more
  exact, but the purpose page states goals, and `uncertainty.md` holds the rules.
- **No "none" for estimates:** an estimate with no interval moves to the observations, with a note. It changes
  `shared.md`'s rule, and splits one table's numbers between two sections depending on the runs.
- **The coefficients as observations:** stored with no interval, as an exception to 0034's sentence. Their
  intervals cost 2P doubles from refits already made.
- **The tag under each table** ("stream 2³² + 1"): changes four accepted specs' mock reports and the golden
  reports, for a number that matters to reproduction (provenance), not to reading the table.

## Consequences

- **`../design/glossary.md`:** the "estimate" row becomes "a number with its variability interval and the method
  that made the interval; the interval is "none", with the reason, when the method gives none for that
  diagnostic evaluation (`uncertainty.md`)".
- **`../design/diagnostics/polynomial_model.md`:** the coefficients, in the diagnostic result and their data card,
  each with its interval; the report unchanged.
- **`../design/diagnostics/linear_model.md`:** the seam's wording, as above.
- **`../design/uncertainty.md`:** the polynomial model's row lists the coefficients (in the result, not the
  report); the Rules cite this record.
- **Record 0040** stays accepted; this record adds the coefficients to its polynomial model row.
- **Tests:** PM's known answers include the coefficients' intervals in the result; C17's round trip covers a
  "none" interval (stored as null, with its reason).
