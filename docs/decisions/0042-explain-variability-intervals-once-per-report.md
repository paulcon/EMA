# 0042. Explain variability intervals once per report, and fix three step-6 slips

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (step 7's third consistency check).

## Context

A third check of `../design/uncertainty.md` and `../design/contracts.md` against the other specs (TODO step 7,
2026-10-01) found four disagreements between accepted documents, each there before step 7:

- **The terminology test forbids the reports' own sentence.** The glossary's terminology test checks the text EMA
  generates, golden reports included, for words that are always wrong there, among them "confidence interval"
  (record 0008). `../design/diagnostics/shared.md` (Estimates) has every line under an estimates table end "Not
  confidence intervals.", as do the mock reports in scatter, the linear model, and the polynomial model, and
  `../design/uncertainty.md` repeats it. Every golden report would fail the test. Record 0004 asks that reports
  say near every interval which method made it, and that "the first report a user sees … explain the
  difference" from confidence intervals.
- **Scatter's mock report** (`../design/diagnostics/scatter.md`, Mock report) has three estimates tables and two
  lines under them: the mean and standard deviation table has none. `shared.md`'s S4 and scatter's own text
  ("three tables, each with one line under it") require one.
- **`shared.md`'s example of "none"** ("No interval: when an estimate's method gives none (for example, too few
  runs to resample)") can't occur: below a diagnostic's minimum there are no estimates at all (S6). The case
  that occurs is fewer than 201 of the 1000 resamples defined (`../design/uncertainty.md`, Rules).
- **The glossary's "observation" row** says "with no variability interval". Record 0041 made an estimate whose
  interval is "none" stay an estimate, and drew the line at "a number whose spec gives it a variability
  interval"; the observation row doesn't say so.

## Decision

We will:

1. **Explain variability intervals once per report.** A report with an Estimates section opens it with one
   sentence (`EXPLAIN_INTERVALS`): "Each variability interval shows how much its estimate changes when the runs
   behind it change, by the method named under its table; it is not a confidence interval, and carries no
   coverage probability." The line under each estimates table names the method and its settings, and no
   longer ends "Not confidence intervals." A report with no Estimates section (the point run, coordinate lines,
   lines) has no such sentence. The terminology test allows "confidence interval" in generated text only in
   that sentence, once per report.
2. **Add the missing line** under scatter's mean and standard deviation table in its mock report: "Variability
   intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles, seed 1."
3. **Replace `shared.md`'s example of "none"** with "for example, fewer than 201 of the 1000 resamples defined
   (`../uncertainty.md`)".
4. **Amend the glossary's "observation" row** to "a number whose spec gives it no variability interval, read or
   computed directly from a diagnostic evaluation's usable runs, …" (the rest unchanged), the counterpart of
   0041's estimate row.

## Alternatives considered

- **Allow "Not confidence intervals." in every line:** the smallest change (an exception to the test), but the
  phrase then repeats under every table, three or four times per report.
- **Reword every line** ("No coverage probability."): removes the term from reports, and the explanation 0004
  asked for moves to the get-started guide, away from the numbers.
- **Leave scatter's mock report, `shared.md`'s example, and the observation row:** each is a slip, and a golden
  report built from scatter's mock would fail S4.

## Consequences

- **`../design/diagnostics/shared.md`:** the Estimates bullets (one line per table names its method and
  settings; the report's one sentence; the example of "none"), the example table's line, and S4's wording;
  `EXPLAIN_INTERVALS` in its named constants.
- **Mock reports:** scatter (its three lines, one added), the linear model (three lines), the polynomial model
  (four lines): "Not confidence intervals." removed, and the sentence at the top of each Estimates section.
- **`../design/glossary.md`:** the terminology test's paragraph (the one allowed sentence); the "observation"
  row.
- **`../design/uncertainty.md`:** "What an interval means" and the bootstrap's step 6 (the line under the
  table).
- **`../design/contracts.md`:** C11 checks the sentence: once in a report with an Estimates section, absent in
  one without.
- **Tests:** the terminology test's one exception, checked to match `EXPLAIN_INTERVALS` exactly; the golden
  reports (step 11) follow the amended mocks.
