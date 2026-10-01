# What every diagnostic shares

**Status:** accepted. **Updated:** 2026-10-01 (0054, 0055). **Depends on:** P1, P2, P4, P5, P6; records 0004, 0010,
0018, 0022, 0034, 0035, 0040, 0042, 0044, 0049, 0051, 0052, 0054, 0055.

> The parts of a diagnostic's spec that are the same for all six: the report's layout, how numbers are
> written, the precheck, how runs that aren't usable are counted and drawn, and where a diagnostic's own
> random draws come from. Each diagnostic spec cites this file, and states only what differs. Written from an
> interview on 2026-09-30 (TODO step 6).

## The report

One report per diagnostic evaluation, in Markdown with TeX math and PNG figures (0018), in this order:

1. **Title:** `# <Diagnostic>: <model>, <model prediction>`.
2. **Header,** a table:
   - **Model version:** its name and hash.
   - **Model prediction:** the one analyzed (0022): name, description, and units.
   - **Space:** each varied model parameter's range and units, with "log" for a log range.
   - **Held:** each held model parameter and its value, marked "held value" or "nominal" (0023, 0033).
   - **Design:** the design generator and its parameters, with the sampler, its version, and the seed where
     the design has them.
   - **The diagnostic's own rows,** only where its spec adds them, after Design: the polynomial model's Fit
     (degree, basis, and number of terms).
   - **Runs:** the total; new and reused; failed, by kind (error, timeout, unread); missing this model
     prediction; usable.
3. **Notes,** only if there are any.
4. **Estimates:** one sentence explaining variability intervals (`EXPLAIN_INTERVALS`, below), then tables of
   estimates, each with its variability interval.
5. **Observations** (0034): numbers read or computed directly from the usable runs, with no interval.
6. **Figures:** each PNG, its caption, and the name of its data card.
7. **Provenance** (P5): EMA's version, the library versions, the model version, the request, the runs used,
   and the approval of its new runs (0054).

- **An empty section is left out** (S1, 0051), with its opening sentence: a report with no estimates has no
  Estimates section, and no explanation of intervals. Each diagnostic spec's degenerate cases list the figures
  it still draws.
- **A repeated request** (the same reuse key, `../data_model.md`) returns the stored diagnostic result, so the
  header's new and reused counts are those of the diagnostic evaluation that made it, and the report is
  byte-identical (U1, U2, U8).
- **Numbers** (0044): every computed number in the report is `format(x, ".4g")` of the stored double, with an
  ASCII minus: 0.3139, 2236, 1.2e-07, -0.009447. Counts, sizes, seeds, degrees, and levels are printed in full;
  ids and hashes are not numbers. The diagnostic result and the data cards keep full doubles. A narrow interval
  may print both ends the same.
- **Ids** (0055) are written as their first 12 hex digits (a model version as `name@` and 12); the mocks'
  shorter ids are placeholders.
- **Units:** a number with units is followed by them ("412.3 K"); dimensionless numbers have none.

### Estimates

- **One explanation per report** (0042): the Estimates section opens with `EXPLAIN_INTERVALS`:

  > Each variability interval shows how much its estimate changes when the runs behind it change, by the method
  > named under its table; it is not a confidence interval, and carries no coverage probability.

  It is the only place generated text says "confidence interval" (the glossary's terminology test). A report
  with no Estimates section has no such sentence.
- **One method per table.** Under each table, one line states its interval method and settings (0004). A table
  whose estimates use two methods is split.

  ```markdown
  | Model parameter | Rank correlation | Variability interval |
  |---|---|---|
  | E | 0.1012 | [0.0114, 0.1893] |
  | L | 0.8134 | [0.7768, 0.8446] |

  Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles,
  seed 1.
  ```

  (The numbers in this example are placeholders; each diagnostic's spec chooses its method, OD-12, and the
  bootstrap is specified in `../uncertainty.md`.)
- **No interval:** when an estimate's method gives none (for example, fewer than 201 of the 1000 resamples
  defined, `../uncertainty.md`), its interval cell says "none", and the line under the table says why (0042).

### Observations

Every report's Observations section has, for the model prediction over the usable runs:

| Of the n usable runs | y |
|---|---|
| Minimum | … |
| Maximum | … |
| (max - min) / max\|y\| | … |

- The relative spread shows when a model prediction varies only at rounding level (0035): R4b's is 8·10⁻¹³.
  It is 0 when the model prediction is constant.
- Labels say what an observation is of ("of the 200 usable runs"), not a property of the model (0034).
- Each diagnostic's spec adds its own observations.

### Notes

A note is a caveat about the data (glossary). Shared notes, in this order:

- **Runs not usable:** the count by kind, then the most frequent one-line reasons, verbatim, with counts (at
  most 5; the rest summed), ordered by count, descending, ties broken by the first run in design order with
  that reason (0051); then the number of usable runs the estimates use, and the call that lists them all:

  ```markdown
  - 34 of 200 runs are not usable for T_max: 30 failed (error), 4 failed (timeout).
    Most frequent reasons:
      27  exited with code 3
       4  timeout after 600 s
       3  solver.cfg: max iterations reached
    Estimates use the 166 usable runs. `ws.failed_runs("3f2a")` lists each one.
  ```

- **Reused failed runs** (0010): how many of the reused runs had failed before, and that `retry_failed` runs
  them again (U3).
- **Too few usable runs:** "k usable runs; <diagnostic> needs at least m (<why>)". No estimates (P6).
- **All runs failed:** the counts, and no estimates or observations (P6).
- **No usable run** (0051): some runs are ok, but none read the model prediction analyzed: "No run is usable for
  z: 0 failed, 200 missing z." No estimates or observations, as when all runs failed (P6).
- **Constant:** "T_max is the same in all k usable runs: <value>." No estimates (P6, 0035). The point run
  has no such note: one distinct value is its ordinary answer for a deterministic model (`point_run.md`).
- **Measured noisy** (P7, U7): one line per point run that measured the model version noisy in this model
  prediction, with the standard deviation as a fraction of this result's range (`point_run.md`).

## The precheck

One precheck, in the diagnostic base, before `compute` (P6):

- **Usable runs:** a run is usable when it is `ok` and the analyzed model prediction was read (0022, M4). A
  failed run, or one missing this model prediction, is not usable, and is counted by kind.
- **Minimum:** each diagnostic's spec states its own minimum number of usable runs, as a formula in d and its
  diagnostic parameters, with the reason. There is no shared floor. Below it: counts, a note, and no
  estimates.
- **Constant** (0035): the model prediction is constant when every usable run gives the same value, as a
  double. There is no flatness tolerance. Then: counts, the note, the observations, and no estimates.
- **Every other tolerance** on a model prediction is relative to its range (P6), and is a named constant in
  the spec that uses it.

## Random draws in a diagnostic

- A diagnostic's own random draws (bootstrap resamples, cross-validation folds) come from
  `SeedSequence(seed, spawn_key=(tag, …))`, where `seed` is the request's seed and `tag` is a fixed integer per
  diagnostic and estimator, named in that diagnostic's spec. Tags start at 2³², above every design stream's
  spawn key (random lines use j = 0, 1, …). `SeedSequence` stores a key above 2³² − 1 as two 32-bit words
  (2³² + 1 as (1, 1)), so a tag's stream is distinct from every design stream only while design streams spawn
  no children. **Design streams spawn no children of their own** (P4, 0051; C8).
- Designs without a seed (point, given lines, coordinate lines) still have the request's seed, 0 by default,
  for the diagnostic's own draws, and it is recorded (P5).
- v1's `seed + 1` is not used: it is the design stream of the request with the next seed.

| Diagnostic | Tag | Stream |
|---|---|---|
| point run | none | no random draws |
| scatter | 2³² + 1 | the bootstrap's resamples (`scatter.md`) |
| coordinate lines | none | no random draws (`coordinate_lines.md`) |
| lines | none | no draws of its own; random lines' anchors and directions are the design's streams (`lines.md`) |
| linear model | 2³² + 2 | the bootstrap's resamples (`linear_model.md`) |
| polynomial model | 2³² + 3 | the bootstrap's resamples (`polynomial_model.md`) |

## Bootstrap

The bootstrap's steps and its constants (`BOOTSTRAP_RESAMPLES`, `BOOTSTRAP_PERCENTILES`) have one home,
`../uncertainty.md` (The bootstrap; 0052). A diagnostic whose spec chooses it (OD-12) states only its
differences: which estimates use distinct runs, what is undefined, and its tag (above).

## Golden reports

A diagnostic spec's mock report is its **golden report** (0044); there is no separate golden file. The golden
report's test renders the report on the mock's reference model and request, and parses it. It has the mock's
sections, rows, labels, and notes, and each number is within one unit in the 4th significant digit of the
mock's. Ids, hashes, dates, and library versions are not compared. Within one machine, reruns are still exact:
the data cards are byte-identical (S10).

## Figures

- **One PNG per figure,** with one or more panels, and a data card beside it (JSON).
- **Axes:** a model parameter on the x axis is in its own units, on a log axis for a log range; the model
  prediction on the y axis is on a linear axis; every axis is labeled `name [units]` (`name` alone when
  dimensionless), with mathtext for symbols (0018).
- **Runs not usable:** in a panel with a model parameter on the x axis, every run that isn't usable is one
  marker (×) in a strip below the axes, at its x, with the count in the strip's label. The data card gives
  each one's kind.
- **Data card:** the figure's name; for each panel, each axis (label, units, scale, and `extent`, its shown
  interval, 0049) and every plotted value, each point with its run id, so each point traces to a stored run
  (P1); the runs not usable, with their kind. About 100 bytes per point.
- **Byte identity:** the data cards are byte-identical on rerun and reproduction (0018); the PNGs are not held
  to it. Reproduce (U8) compares data cards.
- **Held model parameters** have no panel (`../designs.md`).

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `REPORT_DIGITS` | 4 | significant digits of every computed number in a report (S3, 0044) | readable, and deterministic |
| `NOTE_MAX_REASONS` | 5 | the most failure reasons a note lists verbatim | enough for the usual few causes; `failed_runs` has the rest |
| `SPAWN_TAG_BASE` | 2³² | the smallest spawn key a diagnostic's own draws use | above every design stream's key (random lines' j) |
| `EXPLAIN_INTERVALS` | the sentence above | the one explanation of variability intervals per report | 0004 asks reports to explain the difference from confidence intervals; once per report keeps the terminology test's exception to one sentence (0042) |
| `KNOWN_ANSWER_N` | 20,000 | the design size of the diagnostics' known-answer tests | tolerances of 0.004–0.12 (scatter) and 0.006–0.9 (the linear model) at 5 standard deviations (0052) |
| `KNOWN_ANSWER_SDS` | 5 | a known answer's tolerance, in standard deviations over designs | a test at a fixed seed that a correct estimator passes with room to spare (0052) |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| S1 | Every report has the sections above, in that order; an empty section is left out, with its opening sentence (0051). | A report for each diagnostic on R1: the section headings, in order. |
| S2 | The header states the model version, the model prediction, the space with scales, the held model parameters with their values, the design with its seed, and the run counts by kind. | U3's `r1` on R5: 200 runs, failed by kind, missing z, usable. R1 with one model parameter held at a value and one at nominal: the held rows (0051). |
| S3 | Every computed number in the report is `format(x, ".4g")` of the stored double, with an ASCII minus; counts, sizes, seeds, degrees, and levels are printed in full; ids and hashes are not numbers (0044). | Parse the report's numbers, skipping ids and hashes; compare with the diagnostic result. |
| S4 | Each estimates table is followed by one line naming its interval method and settings; the Estimates section opens with `EXPLAIN_INTERVALS`, the report's only use of "confidence interval" (0042). | Every table in each diagnostic's report on R2; the sentence once in each report with estimates, and absent from the point run's and the lines' reports. |
| S5 | A model prediction is constant only when every usable run gives the same double; then counts, a note, and the observations, with no estimates. | R4a: the note, for every diagnostic but the point run (PT6, 0051); R4b: estimates, and a relative spread of 8·10⁻¹³. |
| S6 | Fewer usable runs than a diagnostic's minimum give counts and a note, with no estimates. | Each diagnostic one run below, and at, its minimum. |
| S7 | The note on runs not usable counts them by kind, and lists at most 5 reasons verbatim, with counts. | R5, y and z: counts by kind; a fixture with 7 distinct reasons: 5 listed, the rest summed. |
| S8 | A diagnostic's own random draws come from its spawned streams; changing its tag changes its intervals, and not its design. | Two tags, one request: the same design, different resamples. |
| S9 | Every plotted point has its run id in the data card, and every run that isn't usable appears once, with its kind. | Scatter on R5: counts in the card equal the header's. |
| S10 | Data cards are byte-identical on rerun. | Each diagnostic, twice. |

## What this file asks of other documents

- **Reference models:** R4b's expected answers are estimates (0035).
- **Data model (step 8):** a repeated request returns the stored diagnostic result.
- **Architecture (step 9):** `DiagnosticResult.observations` (0034); the precheck in the diagnostic base; the
  report renderer's section order.
