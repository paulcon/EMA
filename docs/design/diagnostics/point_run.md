# Point run

**Status:** accepted. **Updated:** 2026-10-01 (the seed row, 0061); 2026-10-02 (the mean and standard deviation
from the deviations, 0075). **Module:** `ema/diagnostics/point_run.py`. **Depends on:**
`shared.md`; P7; records 0011, 0021, 0022, 0034, 0035, 0036, 0044, 0049, 0051, 0052.

> The model prediction at one point, and its measured variation over repeated runs there (0012, P7, 0011).
> Written from an interview on 2026-09-30 (TODO step 6). Everything not stated here follows `shared.md`.

## Summary

| | |
|---|---|
| **User provides** | a point x (nominal), repeats (4), the model prediction (the only one, if one); a seed (0) is recorded and changes nothing |
| **Design** | point (`../designs.md`): x, with replicates 0 to repeats |
| **Compute** | no estimates; observations of the runs at the point; whether the model prediction varies; if it does, the model version is recorded as measured noisy in that model prediction |
| **Plots** | the deviation from replicate 0 against the replicate number |
| **Report** | observations; the note on later diagnostic results when the model prediction varies |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `x` | mapping of model parameter names to values | `{}` (the nominal point) | the point; unnamed model parameters at their nominal values; each value inside its limits (G9) | yes |
| `repeats` | integer ≥ 0 | 4 | the number of runs after replicate 0: replicates 1 to `repeats` | yes |
| `prediction` | model prediction name | the only one | the model prediction analyzed (0022) | no |
| `seed` | integer ≥ 0 | 0 | recorded; the point run makes no random draws (0061) | no |

- **The point's model parameter space** (0049): the user gives `x`, not a space (U7), and EMA builds the space
  that holds every model parameter at the point's value, with none varied (`../designs.md`, Point). The
  header's **Space** row shows it, with no Held row: every model parameter's value, marked "given" or
  "nominal", every one held.
- **The seed** changes nothing: the point run makes no random draws. The request's seed, 0 by default, is
  recorded (`shared.md`), and a request with another seed is another diagnostic evaluation with the same numbers
  (C8, 0061).
- **Replicates** (0011): replicate 0 is the ordinary run at x, reused when stored (for example, the test run at
  the nominal point); replicates 1 to `repeats` are new runs the first time, and reused when the same repeats
  are asked for again. A point run with more repeats reuses the fewer (G4).
- **Other model predictions:** a point run analyzes one. A second point run at the same x and repeats, for
  another model prediction, reuses every run, and costs nothing.

## Computation

Let U be the usable runs among replicates 0 to k = `repeats` (`shared.md`, the precheck), with values y_r.

**Observations** (0034), of the runs at the point:

| Observation | Definition | Needs |
|---|---|---|
| Replicate 0 | y₀, or "failed (<kind>)" or "missing" | replicate 0 |
| Mean | the mean of y_r over U | 1 usable run |
| Standard deviation | over U, with ddof = 1 | 2 usable runs |
| Distinct values | the number of distinct doubles among the y_r in U | 1 usable run |
| Minimum, maximum, (max − min)/max\|y\| | as in `shared.md` | 1 usable run |

An observation whose "Needs" isn't met is shown as "none".

**From the deviations** (0075 item 24): the mean and the standard deviation are computed from the deviations from
the first usable value, d_r = y_r − y_f: mean = y_f + mean(d), standard deviation = std(d, ddof 1). numpy's
`mean` and `std` of the values themselves round for a value with no short binary form (R1 at a = 0.3, 11 runs:
mean 7.900000000000002, standard deviation 1.9·10⁻¹⁵); from the deviations a constant gives its value and 0
exactly, and the numbers stay bit for bit under a·y with a a power of 2 (C5).

**Varies** (exact, as 0035): the model prediction varies at x when two usable runs differ as doubles
(distinct values ≥ 2), or when at least one run is usable and at least one isn't (the failures vary). There is
no tolerance, so a difference of one unit in the last place counts.

**Measured noisy:** when the model prediction varies, the diagnostic result records it (the model version,
the model prediction, x, the number of runs, and the standard deviation), and the model version is recorded
as measured noisy in that model prediction (P7, U7).

- **Every later diagnostic result** for that model version that analyzes that model prediction carries a note
  (`shared.md`, Notes), one line per point run that measured it, most recent first:

  ```markdown
  - heat@b204 was measured noisy in T_max by point run 9d1e (11 runs at the nominal point): standard
    deviation 1.1e-07 K, 6.2e-10 of the range of T_max in this diagnostic's runs (176.6 K).
  ```

  The fraction is the standard deviation divided by the later result's own range, max − min over its usable
  runs, so it is units-free (P6). When that range is 0, or the standard deviation is "none" (the failures
  vary, with one usable run), the note gives what there is, and says why the fraction is missing.
- **Earlier diagnostic results** are unchanged: a stored diagnostic result and its report never change
  (P4, U8). A repeated request made before the point run returns the stored result, without the note.
- **Other model predictions** of that model version get no note from this point run.

**The point run's own report** has no "constant" note (the exception in `shared.md`): for a deterministic
model, one distinct value is the ordinary answer, and U7 adds no note. Its Notes section has the shared notes
on runs not usable, a note from an earlier point run if there is one, and, with `repeats = 0`, "No repeats:
the variation was not measured."

## Uncertainty

None (OD-12, for the point run): every number is an observation of the runs at the point, not an estimate of
a property of the model, so there is no interval method.

## Minimum runs and degenerate cases

- **Fewest usable runs** (`POINT_RUN_MIN_RUNS`): 1 for the value, the mean, and the distinct values; 2 for the standard deviation;
  and for "varies", 2 usable runs, or 1 usable and 1 not.
- **All runs failed:** counts by kind, and the note; no observations. The model prediction is not recorded as
  varying, even when the failures are of different kinds.
- **Replicate 0 failed, others usable:** its row says "failed (<kind>)" (or "missing"); the model prediction
  varies (the failures vary); the figure's deviations are from the stored mean of the usable runs (P1), and its
  y label says so.
- **Constant:** distinct values 1, the mean the value and the standard deviation 0, exactly (From the deviations,
  above); no note (above). The figure's deviations are all 0, also from the mean.
- **`repeats = 0`:** one run; the note "No repeats: the variation was not measured."; the model version is not
  recorded as measured noisy.
- **x outside the limits, or an unknown name:** refused before any run (G9).
- **Figures** (0051): `point_run.png` in every case. With all runs failed, it has the strip only, one × per
  run; with `repeats = 0`, one point at 0; constant, every point at 0.

## Figures

**`point_run.png`**, one panel:

- **x axis:** the replicate number, 0 to k, integers.
- **y axis:** y_r − y₀, labeled `T_max − T_max(replicate 0) [K]`; when replicate 0 isn't usable, y_r − the mean
  of the usable runs, labeled so.
- **Points:** one marker per usable run, joined in replicate order, so a drift from call to call (state kept in
  a long-lived child, 0026) shows as a trend; a line at 0.
- **Runs not usable:** × in the strip below the axes, at their replicate numbers (`shared.md`).
- **Data card:** as in `shared.md`, with each point's replicate number and run id.

## Mock report

On R6a at the nominal point, with the default 4 repeats. The values are plausible: R6a draws its noise from
fresh entropy (`../reference_models.md`), so no two point runs agree. Replicate 0 is the test run, reused.

```markdown
# Point run: R6a, y

| | |
|---|---|
| Model version | R6a@5c02 |
| Model prediction | y |
| Space | the point a = 1, b = 0, c = 15, k = 10 (all nominal); every model parameter held |
| Design | point, repeats = 4 (replicates 0–4) |
| Runs | 5: 4 new, 1 reused; 0 failed; 0 missing y; 5 usable |

## Observations

| Of the 5 runs at the point | y |
|---|---|
| Replicate 0 | 10.03 |
| Mean | 9.982 |
| Standard deviation (ddof 1) | 0.03903 |
| Distinct values | 5 |
| Minimum | 9.939 |
| Maximum | 10.03 |
| (max - min) / max\|y\| | 0.009281 |

The model prediction varies at this point, so R6a@5c02 is recorded as measured noisy in y.

## Figures

![Deviation from replicate 0](point_run.png)

y - y(replicate 0) against the replicate number, 0 to 4. Data card: `point_run.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R6a@5c02; request: point run,
x = {}, repeats = 4, prediction y, seed 0; runs: 5 (replicates 0–4); approvals: a41f (4 new runs).
```

On R1, the same request gives replicate 0 = 10, mean 10, standard deviation 0, distinct values 1, relative
spread 0, no note, and no "measured noisy" line.

## Expected answers

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R1, nominal, repeats 4 | replicate 0; mean; standard deviation; distinct values | 10; 10; 0; 1 | exact | analytic (log₁₀ 10 = 1 exactly in IEEE doubles) |
| R1, nominal, repeats 4 | varies; notes | no; none | exact | analytic |
| R4a, repeats 4 | distinct values; notes | 1; none (no "constant" note) | exact | trivial |
| R6a, nominal, repeats 100 | standard deviation | 0.05 | within [0.6735, 1.3603] × 0.05 | χ² with 100 degrees of freedom, two-sided probability 10⁻⁶ |
| R6a, nominal, repeats 4 | varies | yes | exact | by construction (equal draws have probability 0) |
| R6b, nominal, repeats 100 | standard deviation | 10⁻⁷ | within [0.6735, 1.3603] × 10⁻⁷ | as R6a |
| R6b, nominal, repeats 4 | varies | yes | exact | by construction |
| R5, x = {a: 0.9, b: 0.9}, repeats 4 | runs; observations | 5 failed (error); none | exact | by construction (a + b > 1) |
| R5, nominal, prediction z, repeats 4 | runs usable for z | 5 | exact | by construction |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `POINT_RUN_REPEATS` | 4 | the default number of repeats | 5 runs: enough to see variation and a rough spread; U7 asks for 10 when it wants more |
| `POINT_RUN_MIN_RUNS` | 1 | the fewest usable runs for observations | one run is the point's value (P6 names each diagnostic's minimum, 0035) |

There are no tolerances: "varies" is exact (0035).

## Requirements

| Id | Requirement | Test |
|---|---|---|
| PT1 | With the defaults, the design is the nominal point with replicates 0–4; replicate 0 is reused when stored, and a rerun makes no new runs. | After `test_model` on R1: the price is 4 new, 1 reused; a rerun: 0 new. U7: 10 repeats after the test run: 10 new, 1 reused. |
| PT2 | The report has the observations above and no estimates. | R1 and R6a: the Observations table's rows; the Estimates section absent. |
| PT3 | The model prediction varies exactly when two usable runs differ as doubles, or some runs are usable and some aren't. | R1: no; R6a, R6b: yes; a fixture whose replicate 2 fails: yes; one whose replicate 3 differs by one unit in the last place: yes. |
| PT4 | When it varies, the model version is recorded as measured noisy in that model prediction, and every later diagnostic result for it carries the note, with the standard deviation as a fraction of that result's range. | Point run on R6a, then scatter on R6a: the note, with the fraction computed from scatter's range; scatter on R1: no note. |
| PT5 | Earlier diagnostic results, and results for another model prediction, are unchanged. | Scatter on R6a before the point run: its report is byte-identical after; R5's z gets no note from a point run on y. |
| PT6 | The point run's own report has no "constant" note. | R1 and R4a: Notes absent. |
| PT7 | With `repeats = 0`: one run, the note, no standard deviation, and nothing recorded as noisy. | R6a with `repeats = 0`. |
| PT8 | With every run failed: counts by kind, the note, and no observations. | R5 at a = b = 0.9. |
| PT9 | The figure has one point per usable run in replicate order, and one × per run not usable. | R5 fixture with replicate 0 failed: the y label names the mean, and the strip has one ×. |

## Tests it implies

- The R6 tests check sampling bounds only, never golden bytes: the point run has no golden report.
- `shared.md`'s S1–S10, with the point run's exceptions: the header's Space row holds every model parameter, with
  no Held row (0049), and there is no "constant" note.
- The diagnostic contract (`../contracts.md`): y → a·y + b (with a a power of 2) scales every observation as
  expected and changes no note.
- The store contract's exception for the point run's replicates (P7, 0011).

## What this spec asks of other documents

- **Data model (step 8):** a model version's "measured noisy" record, per model prediction, with the point run
  that measured it; the notes on later diagnostic results read it when they are made.
- **Architecture (step 9):** `run` takes no model parameter space for the point run (U7).
