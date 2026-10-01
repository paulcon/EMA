# What every diagnostic shares

**Status:** draft. **Updated:** 2026-09-30. **Depends on:** P1, P2, P4, P5, P6; records 0004, 0010, 0018,
0022, 0034 (proposed), 0035 (proposed).

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
4. **Estimates:** tables of estimates, each with its variability interval.
5. **Observations** (0034): numbers read or computed directly from the usable runs, with no interval.
6. **Figures:** each PNG, its caption, and the name of its data card.
7. **Provenance** (P5): EMA's version, the library versions, the model version, the request, the runs used,
   and the approvals.

- **A repeated request** returns the stored diagnostic result, so the header's new and reused counts are those
  of the diagnostic evaluation that made it, and the report is byte-identical (U1, U2, U8).
- **Numbers** are written with 4 significant digits, as Python's `format(x, ".4g")`: 0.3139, 2236, 1.2e-07.
  The diagnostic result and the data cards keep full doubles. A narrow interval may print both ends the same.
- **Units:** a number with units is followed by them ("412.3 K"); dimensionless numbers have none.

### Estimates

- **One method per table.** Under each table, one line states its interval method and settings, and that the
  intervals are not confidence intervals (0004). A table whose estimates use two methods is split.

  ```markdown
  | Model parameter | Rank correlation | Variability interval |
  |---|---|---|
  | E | 0.1012 | [0.0114, 0.1893] |
  | L | 0.8134 | [0.7768, 0.8446] |

  Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles,
  seed 1. Not confidence intervals.
  ```

  (The numbers in this example are placeholders; each diagnostic's spec chooses its method, OD-12, and the
  bootstrap's defaults are below.)
- **No interval:** when an estimate's method gives none (for example, too few runs to resample), its interval
  cell says "none", and the line under the table says why.

### Observations

Every report's Observations section has, for the model prediction over the usable runs:

| Of the n usable runs | y |
|---|---|
| Minimum | … |
| Maximum | … |
| (max − min) / max\|y\| | … |

- The relative spread shows when a model prediction varies only at rounding level (0035): R4b's is 8·10⁻¹³.
  It is 0 when the model prediction is constant.
- Labels say what an observation is of ("of the 200 usable runs"), not a property of the model (0034).
- Each diagnostic's spec adds its own observations.

### Notes

A note is a caveat about the data (glossary). Shared notes, in this order:

- **Runs not usable:** the count by kind, then the most frequent one-line reasons, verbatim, with counts (at
  most 5; the rest summed), the number of usable runs the estimates use, and the call that lists them all:

  ```markdown
  - 34 of 200 runs are not usable for T_max: 30 failed (error), 4 failed (timeout).
    Most frequent reasons:
      27  exited with code 3
       3  solver.cfg: max iterations reached
       4  timeout after 600 s
    Estimates use the 166 usable runs. `ws.failed_runs("3f2a")` lists each one.
  ```

- **Reused failed runs** (0010): how many of the reused runs had failed before, and that `retry_failed` runs
  them again (U3).
- **Too few usable runs:** "k usable runs; <diagnostic> needs at least m (<why>)". No estimates (P6).
- **All runs failed:** the counts, and no estimates or observations (P6).
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
  spawn key (random lines use j = 0, 1, …), so no draw shares a stream with a design (P4).
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

The defaults for any diagnostic whose spec chooses the bootstrap (OD-12), set in scatter's interview
(2026-09-30); a spec that differs says so.

- **Resamples:** 1000 (`BOOTSTRAP_RESAMPLES`), each drawn with replacement from the usable runs, from the
  diagnostic's own stream (above). Every estimate in a diagnostic uses the same resamples.
- **Interval:** the 0.5th and 99.5th percentiles of the resampled estimates (`BOOTSTRAP_PERCENTILES`), by
  numpy's `percentile` with linear interpolation. Not the full range: the extremes come from the most
  degenerate resamples, and widen with the number of resamples toward the observed range (on R2's mean:
  [2.72, 4.45] at 1000, [2.31, 4.71] at 10⁵, and [−9.09, 12.85] over all resamples), while the percentiles
  are stable at 1000.
- **Undefined resamples** (an estimate that is 0/0 on a resample) are dropped, and the line under the table
  says how many of the 1000 were, when any were.
- **Duplicates:** an estimate that duplicated runs bias (scatter's binned index) is recomputed on each
  resample's distinct runs; its spec says so, and so does the line under its table.

## Figures

- **One PNG per figure,** with one or more panels, and a data card beside it (JSON).
- **Axes:** a model parameter on the x axis is in its own units, on a log axis for a log range; the model
  prediction on the y axis is on a linear axis; every axis is labeled `name [units]` (`name` alone when
  dimensionless), with mathtext for symbols (0018).
- **Runs not usable:** in a panel with a model parameter on the x axis, every run that isn't usable is one
  marker (×) in a strip below the axes, at its x, with the count in the strip's label. The data card gives
  each one's kind.
- **Data card:** the figure's name; for each panel, each axis (label, units, scale, limits) and every plotted
  value, each point with its run id, so each point traces to a stored run (P1); the runs not usable, with
  their kind. About 100 bytes per point.
- **Byte identity:** the data cards are byte-identical on rerun and reproduction (0018); the PNGs are not held
  to it. Reproduce (U8) compares data cards.
- **Held model parameters** have no panel (`designs.md`).

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `REPORT_DIGITS` | 4 | significant digits of every number in a report | readable, and deterministic (interview, 2026-09-30) |
| `NOTE_MAX_REASONS` | 5 | the most failure reasons a note lists verbatim | enough for the usual few causes; `failed_runs` has the rest |
| `SPAWN_TAG_BASE` | 2³² | the smallest spawn key a diagnostic's own draws use | above every design stream's key (random lines' j) |
| `BOOTSTRAP_RESAMPLES` | 1000 | resamples per bootstrap | percentiles stable to about 0.01 of the interval at this size (scatter interview) |
| `BOOTSTRAP_PERCENTILES` | (0.5, 99.5) | the interval's ends | the owner's choice: wide, and still converging as resamples grow (scatter interview) |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| S1 | Every report has the sections above, in that order; empty Notes are left out. | A report for each diagnostic on R1: the section headings, in order. |
| S2 | The header states the model version, the model prediction, the space with scales, the held model parameters with their values, the design with its seed, and the run counts by kind. | U3's `r1` on R5: 200 runs, failed by kind, missing z, usable; a held value and a nominal one. |
| S3 | Every number in the report is `format(x, ".4g")` of the stored double. | Parse the report's numbers, compare with the diagnostic result. |
| S4 | Each estimates table is followed by one line naming its interval method and settings. | Every table in each diagnostic's report on R2. |
| S5 | A model prediction is constant only when every usable run gives the same double; then counts, a note, and the observations, with no estimates. | R4a: the note, for every diagnostic; R4b: estimates, and a relative spread of 8·10⁻¹³. |
| S6 | Fewer usable runs than a diagnostic's minimum give counts and a note, with no estimates. | Each diagnostic one run below, and at, its minimum. |
| S7 | The note on runs not usable counts them by kind, and lists at most 5 reasons verbatim, with counts. | R5, y and z: counts by kind; a fixture with 7 distinct reasons: 5 listed, the rest summed. |
| S8 | A diagnostic's own random draws come from its spawned streams; changing its tag changes its intervals, and not its design. | Two tags, one request: the same design, different resamples. |
| S9 | Every plotted point has its run id in the data card, and every run that isn't usable appears once, with its kind. | Scatter on R5: counts in the card equal the header's. |
| S10 | Data cards are byte-identical on rerun. | Each diagnostic, twice. |

## What this file asks of other documents

- **Records 0034 and 0035** (proposed): the glossary's "observation" row and P2's list; P6's flatness wording.
- **Reference models:** R4b's expected answers are estimates (0035).
- **Uncertainty (step 7):** the rule for "none" in an interval cell; the spawn tags' range.
- **Contracts (step 7):** S1–S10 in the diagnostic contract; the unit-invariance check keeps distinct values
  distinct (0035); no failure map of pairs (0037).
- **Data model (step 8):** a repeated request returns the stored diagnostic result.
- **Architecture (step 9):** `DiagnosticResult.observations` (0034); the precheck in the diagnostic base; the
  report renderer's section order.
