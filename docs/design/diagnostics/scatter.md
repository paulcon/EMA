# Scatter

**Status:** accepted. **Updated:** 2026-10-01 (step 11); 2026-10-02 (the figures' limits, cards, and captions, 0076;
the mock's symbols and line, 0073; review round 1 of applying 0066–0085); 2026-10-03 (0086 item 6). **Module:**
`ema/diagnostics/scatter.py`. **Depends on:** `shared.md`; `../designs.md`; records 0012, 0032, 0034, 0035, 0037,
0042, 0044, 0048, 0049, 0051, 0052, 0073, 0076, 0086.

> The model prediction against each model parameter, over a uniform design (U1). Written from an interview on
> 2026-09-30 (TODO step 6). Everything not stated here follows `shared.md`.

## Summary

| | |
|---|---|
| **User provides** | a model parameter space, n (200), seed (0), sampler (`random`), the model prediction |
| **Design** | uniform (`../designs.md`): n points of the sampler, mapped to the space |
| **Compute** | the mean and standard deviation of the model prediction; for each varied model parameter, its rank correlation with the model prediction and its binned first-order index; bootstrap intervals |
| **Plots** | for each varied model parameter, the model prediction against it, with the bin means; a histogram of the model prediction |
| **Report** | three tables of estimates with variability intervals; the shared observations; the figures |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `space` | model parameter space | required | the ranges varied, and the values held (`../designs.md`) | yes |
| `n` | integer ≥ 1 | 200 | the number of points | yes |
| `seed` | integer ≥ 0 | 0 | the design's seed, and the bootstrap's (`shared.md`) | yes |
| `sampler` | name | `random` (0032) | the sampler | yes |
| `prediction` | model prediction name | the only one (0022) | the model prediction analyzed | no |

- **Which model parameters:** the space says which vary; there is no separate parameter. To scatter fewer, hold
  the others in the space (0023, 0033).
- **A space with no varied model parameter** is refused before building: a scatter needs one.
- **Nested** in n with the same seed, space, and sampler (G4): scatter at n = 300 reuses the runs of n = 200
  (U3), and a convergent design with the same seed starts with them (U5).

## Computation

Let the n_u usable runs (`shared.md`, the precheck) have values y_k and points x_k.

**About the model prediction:**

- **Mean:** ȳ = (1/n_u) Σ y_k.
- **Standard deviation:** s = √(Σ (y_k − ȳ)² / (n_u − 1)).

**For each varied model parameter x_i:**

- **Rank correlation:** Spearman's ρ_i between x_i and y over the usable runs, with average ranks for ties. The
  ranks are the same in model parameter units and in unit coordinates, log scale or not.
- **Binned first-order index** (the correlation ratio η², Pearson 1905; as a given-data estimate of the
  first-order Sobol index, Plischke, Borgonovo and Smith 2013):
  1. B = ⌊√n_u⌋ bins.
  2. Sort the usable runs by x_i (stable: ties keep the design's order), and split them into B consecutive
     groups as equal as possible; the first n_u mod B groups have one more run (numpy's `array_split`).
  3. η² = Σ_b n_b (ȳ_b − ȳ)² / Σ_k (y_k − ȳ)², with n_b and ȳ_b each group's size and mean.
  4. **Adjusted for its bias:** S_i = 1 − (1 − η²)(n_u − 1)/(n_u − B). η² is the R² of y regressed on the B
     bin indicators, and this is the adjusted R²; without it, a model parameter with no effect reads about
     (B − 1)/(n_u − 1), 0.065 at n = 200.
  5. **Reported as computed:** S_i can be negative for a model parameter with little or no effect (R1's c at
     n = 200: as low as −0.06 over designs). It is not clipped.

**Changes of units** (P6): y → a·y + b, with a > 0, gives ȳ → a·ȳ + b and s → a·s, and leaves every ρ_i and S_i
unchanged: exactly under a·y, within C5's tolerances under the shift (0048). A log scale changes no estimate:
ρ_i and S_i depend only on the order of x_i.

**Failed runs** and runs missing the model prediction are left out of every estimate (P6), counted in the
header and the note (`shared.md`), and drawn in the strip below each panel.

## Uncertainty

OD-12, for scatter: **the bootstrap over the usable runs** (`../uncertainty.md`, The bootstrap), with the tag
`SCATTER_BOOT_TAG`. Its differences:

- **On distinct runs:** the binned index, with ⌊√m⌋ bins over a resample's m distinct runs (about 0.63·n_u),
  ties in the design's order. The mean, standard deviation, and rank correlations are recomputed as drawn. A
  resample repeats runs; copies of one run fall in the same bin and make the bin means vary more than distinct
  runs would, and the adjustment assumes distinct runs. On R2 at n = 200, plain resamples shift the index up by
  0.04–0.05 (x₃: estimate −0.005, interval [−0.044, 0.227]); distinct runs remove the shift, and their widths are
  closest to the index's true spread over designs.
- **Undefined:** ρ and S on a resample whose y values are all equal (0/0); S on a resample with fewer than 2
  distinct runs. The mean and standard deviation are never undefined.
- **Three tables,** each with one line under it (`shared.md`): the model prediction (mean, standard deviation)
  and the rank correlations ("bootstrap over the n_u usable runs, 1000 resamples, 0.5th to 99.5th percentiles,
  seed s"), and the binned index ("… recomputed on the distinct runs of each resample").

## Minimum runs and degenerate cases

- **Fewest usable runs:** 10 (`SCATTER_MIN_RUNS`): 3 bins of 3–4 runs, a rank correlation, a standard deviation,
  and a bootstrap, with room to spare. Below it: counts and a note, no estimates (P6); the shared observations
  stay. Figures: the panels, with their strips and no bin means; the histogram (0051), except with one usable
  run (0076 item 9). At small n the intervals are wide (R1's binned index varies by 0.23 over designs at n = 10),
  and say so.
- **All runs failed, or no usable run:** counts by kind and the note; no estimates or observations
  (`shared.md`). Figures: the panels, with only their strips; no histogram (0051).
- **Constant:** the note, the observations, no estimates (0035). Figures: the panels, with their strips; no
  histogram (0051). R4b is not constant: estimates, and a relative spread of about 8·10⁻¹³.
- **A resample with fewer than 2 distinct runs:** its binned index is undefined, and dropped (above).
- **Runs not usable:** estimates from the usable runs only; the per-model-parameter strips show where the others
  are. Two-model-parameter views (a failure map of pairs) are not in v2.0 (0037).

## Figures

**`scatter_<name>.png`,** one per varied model parameter, in the model spec's order (a model parameter named
`histogram`, in any case, is drawn as `scatter-<name>.png`, so it can't overwrite the histogram's file, also on a
case-insensitive disk; 0076 items 10, 13):

- **x axis:** the model parameter, in its units, on a log axis for a log range (`shared.md`).
- **y axis:** the model prediction; the same limits in every scatter figure of the report, so they compare: the
  usable runs' range with 5% added at each end; with no range (constant, one usable run, none), matplotlib's
  (0076 item 7).
- **Points:** one marker per usable run.
- **Bin means:** the B groups of the binned index as a step line: each group's mean ȳ_b, drawn from its
  smallest to its largest x_i. The index is the variance of this line over the variance of y; for R2's x₂ it
  traces the U of sin² x₂ that the rank correlation misses. Drawn only with estimates (the stored result's;
  0076 item 8).
- **Runs not usable:** × in the strip below the axes, at their x_i (`shared.md`).
- **Title:** the model parameter's name; the estimates are in the tables, not on the figure.
- **Caption:** "y against each model parameter, with the means of the 14 bins of the binned index." with
  estimates, else "y against each model parameter." (0076 item 8).
- **Data card:** as in `shared.md`, with `"parameter"`, the y limits, and the panel's `"bins"`: one `{"x_lo",
  "x_hi", "n", "mean"}` per group of the index (0076 item 7).

**`scatter_histogram.png`,** only when the usable runs' y has a range: none with no usable run, a constant model
prediction, or one usable run (its one bin would have no width; 0076 item 9):

- ⌊√n_u⌋ equal-width bins from the minimum to the maximum of the usable runs' y (`SCATTER_HIST_BINS` rule, the
  same as the index's).
- **x axis:** the model prediction, `name [units]`; **y axis:** "number of runs".
- **Caption:** "y over the n_u usable runs, B bins.", adding "The k runs not usable are not in it." when k > 0.
- **Data card:** `"edges"` and `"counts"`, the bin edges and counts.

## Mock report

On R2 (Ishigami), U1's request: n = 200, seed 1. The numbers are computed: the design from
`default_rng(1).random((200, 3))`, which is the `random` sampler's rows (0032), and the bootstrap from the
stream above; checked at step 11 by `../../checks/scatter.py`.

```markdown
# Scatter: R2, y

| | |
|---|---|
| Model version | R2@8e41 |
| Model prediction | y |
| Space | x1 [-3.142, 3.142]; x2 [-3.142, 3.142]; x3 [-3.142, 3.142] |
| Held | none |
| Design | uniform, n = 200, sampler random 1 (rate ½), seed 1 |
| Runs | 200: 200 new, 0 reused; 0 failed; 0 missing y; 200 usable |

## Estimates

Each variability interval shows how much its estimate changes when the runs behind it change, by the method named
under its table; it is not a confidence interval, and carries no coverage probability.

| Model prediction | Estimate | Variability interval |
|---|---|---|
| Mean | 3.582 | [2.906, 4.232] |
| Standard deviation | 3.826 | [3.275, 4.299] |

Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles,
seed 1.

| Model parameter | Rank correlation ρ | Variability interval |
|---|---|---|
| x1 | 0.4185 | [0.2651, 0.5489] |
| x2 | 0.02173 | [-0.1663, 0.1955] |
| x3 | -0.009447 | [-0.2193, 0.1803] |

Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles,
seed 1.

| Model parameter | Binned first-order index Sᵢ | Variability interval |
|---|---|---|
| x1 | 0.2944 | [0.1888, 0.4248] |
| x2 | 0.4068 | [0.2816, 0.5257] |
| x3 | -0.004922 | [-0.07658, 0.103] |

14 bins. Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, the
index recomputed on the distinct runs of each resample, 0.5th to 99.5th percentiles, seed 1.

## Observations

| Of the 200 usable runs | y |
|---|---|
| Minimum | -9.094 |
| Maximum | 12.85 |
| (max - min) / max\|y\| | 1.708 |

## Figures

![y against x1](scatter_x1.png) ![y against x2](scatter_x2.png) ![y against x3](scatter_x3.png)

y against each model parameter, with the means of the 14 bins of the binned index. Data cards:
`scatter_x1.json`, `scatter_x2.json`, `scatter_x3.json`.

![Histogram of y](scatter_histogram.png)

y over the 200 usable runs, 14 bins. Data card: `scatter_histogram.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R2@8e41; request: scatter,
space as above, n = 200, sampler random 1, seed 1, prediction y; runs: 200; approvals: 5b7e (200 new runs).
```

(For comparison, the true values: mean 3.5, standard deviation 3.721; ρ 0.4374, 0, 0; first-order indices
0.3139, 0.4424, 0.)

## Expected answers

Each at n = 20,000 (`KNOWN_ANSWER_N`, `shared.md`), seed 0, `random` sampler. The tolerance is 5
(`KNOWN_ANSWER_SDS`, `shared.md`) × the estimate's standard deviation over 100 designs (seeds 1–100) at that n,
recomputed at step 11 by `../../checks/scatter.py` (its output, with sizes and seeds: `scatter.out`).

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R1 | mean; standard deviation | 10; 2.160 (√(14/3)) | 0.089; 0.045 | analytic |
| R1 | ρ: a, b, c, k | 0.8073, −0.2525, 0, 0.5156 | 0.012, 0.034, 0.036, 0.027 | quasi-Monte Carlo (8 × 2²² scrambled Sobol points; c: 0 by symmetry) |
| R1 | S: a, b, c, k | 9/14, 1/14, 0, 4/14 | 0.017, 0.018, 0.004, 0.026 | analytic |
| R2 | mean; standard deviation | 3.5; 3.721 | 0.12; 0.11 | analytic |
| R2 | ρ: x1, x2, x3 | 0.4374, 0, 0 | 0.026, 0.038, 0.043 | quasi-Monte Carlo, as R1's (x2, x3: 0 by symmetry) |
| R2 | S: x1, x2, x3 | 0.3139, 0.4424, 0 | 0.022, 0.027, 0.006 | analytic |
| R10 | mean; standard deviation | 0; 2.550 (√6.5) | 0.094; 0.070 | analytic |
| R10 | ρ: a, b, c, e | 0.7980, 0, 0.000, 0 | 0.017, 0.036, 0.040, 0.034 | quasi-Monte Carlo, as R1's (b, e: 0 by symmetry) |
| R10 | S: a, b, c, e | 0.6154, 0.0385, 0, 0 | 0.021, 0.013, 0.006, 0.004 | analytic |
| R4a | notes; estimates | the "constant" note; none | exact | trivial |
| R4b | estimates; relative spread | present; about 8·10⁻¹³ | the spread within 1% | analytic (0035) |
| R5, y and z | every estimate | equal to scatter computed on the usable runs alone | exact | by construction (U3) |
| R5, n = 200 | runs not usable, by kind | the design's points with a + b > 1 (error), a, b < −0.8 (timeout); for z, also b > 0.8 (missing) | exact | by construction |
| R2, n = 200, seed 1 | the report | the mock report above | golden report (`shared.md`: structure, and numbers within one unit in the 4th digit) | this spec |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `SCATTER_N` | 200 | the default number of points | v1's default; U1's example |
| `SCATTER_MIN_RUNS` | 10 | the fewest usable runs for estimates | every estimate defined with room to spare |
| `SCATTER_BOOT_TAG` | 2³² + 1 | the spawn key of scatter's bootstrap stream | the first diagnostic tag above `SPAWN_TAG_BASE` (`shared.md`) |
| `SCATTER_HIST_BINS` | ⌊√n_u⌋ | the number of bins of the binned index and the histogram | the usual balance of bias and resolution; one rule for both |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| SC1 | The design is uniform with the request's n, seed, sampler, and space; a space with no varied model parameter is refused before building. | The design equals `uniform(...)` bit for bit; a space holding every model parameter: refused. |
| SC2 | The mean and the standard deviation (ddof 1) of the usable runs, each with its interval. | R1, R2, R10 at n = 20,000 (Expected answers). |
| SC3 | One rank correlation per varied model parameter (Spearman, average ranks), unchanged by the log scale. | R1 with k log vs a fixture with k linear over the same unit coordinates: identical ρ. |
| SC4 | One binned index per varied model parameter: ⌊√n_u⌋ equal-count bins, stable order, adjusted, not clipped. | A hand-computed fixture of 12 runs; R1's c at n = 200, seeds where it is negative. |
| SC5 | Intervals: 1000 resamples from scatter's stream, the same for every estimate; the binned index on each resample's distinct runs; the 0.5th and 99.5th percentiles; undefined resamples dropped and counted. | A fixture with a two-valued y at n = 10: the count in the line under the table. Changing `SCATTER_BOOT_TAG` changes the intervals, not the design (S8). |
| SC6 | Fewer than 10 usable runs: counts and a note, no estimates; the observations stay. | R5 in a space where 9 runs are usable; 10 usable. |
| SC7 | y → a·y + b (a a power of 2) maps the mean and standard deviation as stated, and leaves ρ, S, and the notes unchanged: exactly under a·y; within C5's tolerances under the shift (0048). | R2 with a = 2⁻¹⁰, b = 3. |
| SC8 | One figure per varied model parameter, with the bin-means step line and the strip of runs not usable, and one histogram with ⌊√n_u⌋ bins. | R5 at n = 200: 2 scatter figures and a histogram; the strip's count equals the header's. |
| SC9 | Estimates use the usable runs only. | R5, y and z (Expected answers). |
| SC10 | The known answers at n = 20,000, seed 0, within their tolerances; the golden report on R2 at n = 200, seed 1. | Expected answers. |

## Tests it implies

- None beyond the requirements above and the contracts (`../contracts.md`).

## What this spec asks of other documents

- **Reference models (step 11):** the expected answers above, recomputed by `../../checks/scatter.py`.
