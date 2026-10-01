# Linear model

**Status:** accepted. **Updated:** 2026-10-01. **Module:** `ema/diagnostics/linear_model.py`. **Depends on:**
`shared.md`; `../designs.md`; records 0012, 0032, 0033, 0034, 0035, 0041, 0042.

> A least-squares linear fit of the model prediction in unit coordinates, over a convergent design: its
> coefficients, how well it fits, and how well it predicts runs it wasn't fitted to (0012, U4). Written from an
> interview on 2026-09-30 (TODO step 6). Everything not stated here follows `shared.md`.

## Summary

| | |
|---|---|
| **User provides** | a model parameter space, n_min (2(d + 1)), alpha (0.7072), level (2), seed (0), sampler (`random`), the model prediction |
| **Design** | convergent (`../designs.md`): levels 0 … L, level l the first n_l points of one uniform design |
| **Compute** | the least-squares fit y ≈ β₀ + Σ βᵢ uᵢ over the usable runs of level L; its relative residual and R²; its leave-one-out error; bootstrap intervals; the same fit at each level, as observations |
| **Plots** | the 1-D shadow (y against w·u); the slopes with their intervals; a histogram of the residuals |
| **Report** | two tables of estimates with variability intervals (the coefficients; the fit), the leave-one-out error with its interval, the shared observations, the per-level table, the figures |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `space` | model parameter space | required | the ranges varied, and the values held (`../designs.md`) | yes |
| `n_min` | integer ≥ 1 | 2(d + 1) | the size of level 0 | yes |
| `alpha` | decimal in (0, 1) | 0.7072 | the error factor per level (`../designs.md`, Convergent) | yes |
| `level` | integer ≥ 0 | 2 | L, the last level | yes |
| `seed` | integer ≥ 0 | 0 | the design's seed, and the bootstrap's (`shared.md`) | yes |
| `sampler` | name | `random` | the sampler (0032); convergent needs a nested one | yes |
| `prediction` | model prediction name | the only one | the model prediction analyzed (0022) | no |

- **d** is the number of varied model parameters; the fit has d + 1 coefficients.
- **The defaults** (interview, 2026-09-30): n_min = 2(d + 1), twice the coefficients, as U4 assumes; alpha =
  0.7072, just above 1/√2, so the points about double per level (r = ½ for `random`: 18, 36, 72, 144, 288,
  576, 1151 at d = 8); level 2, so 8(d + 1) points: 72 at d = 8, 32 at d = 3. With alpha = 0.5 the error
  halves per level and the points grow 4× (18, 72, 288).
- **A small n_min** is accepted (`../designs.md` refuses only sizes that aren't strictly increasing): the
  estimates need 2(d + 1) usable runs at level L (below), and a smaller level has "none" in the per-level table.
- **Nested** in level with the same space, seed, and sampler (G7): level 3 after level 2 reuses every run, and
  the design's first points are a scatter's with the same seed (U5).
- **A space with no varied model parameter** is refused before building.

## Computation

Let the n_u usable runs of level L (`shared.md`, the precheck) have values y_k and unit coordinates
u_k ∈ [−1, 1]^d (`../designs.md`: through the logarithm for a log range).

**The fit** (interview, 2026-09-30):

- **Model:** y ≈ β₀ + Σᵢ βᵢ uᵢ, by least squares over the usable runs, computed from a QR factorization of
  A = [1, U] (n_u × (d + 1)).
- **In unit coordinates:** a slope βᵢ is half the change in y across model parameter i's range, in y's units, so
  slopes compare across model parameters. R1's are exact (10; 3, −1, 0, 2) only when k's log scale is honored
  (0024). In model parameter units the slopes wouldn't compare (R3: 1430 m³/yr per meter of rw, 1.4·10⁻⁷ per
  m²/yr of Tu).
- **Its limit** as n grows is the least-squares fit over the space, under the uniform distribution in unit
  coordinates: βᵢ → 3·E[y·uᵢ], β₀ → E[y] (the expected answers use this).

**How well it fits:**

- **Relative residual:** ‖r‖ / ‖y − ȳ‖, with r = y − Aβ over the usable runs: units-free (P6), 0 for an exactly
  linear model prediction, 1 when the slopes explain nothing. U4's "residual norm", made relative.
- **R²:** 1 − ‖r‖² / ‖y − ȳ‖², the square's complement; reported beside it (interview, 2026-09-30).

**How well it predicts runs it wasn't fitted to:**

- **Leave-one-out (LOO) error** (PRESS; Allen 1974): each run's residual when the fit leaves that run out is
  r_k / (1 − h_kk), where h_kk is the run's leverage, the diagonal of the hat matrix A(AᵀA)⁻¹Aᵀ, computed as the
  squared row norms of Q from the QR factorization. No refits and no random draws. The LOO error is
  √(Σ_k (r_k / (1 − h_kk))²) / ‖y − ȳ‖.
- **Why:** the in-sample residual is optimistic at small n, and LOO tracks the error on new runs. Over 50
  designs: R3 at 18 runs, in-sample 0.151, LOO 0.333, error on 10⁵ fresh points 0.316; at 72 runs, 0.213,
  0.249, 0.247. 10-fold cross-validation gave the same (0.348, 0.250), with folds to seed (interview,
  2026-09-30). A value above 1 means the fit predicts new runs worse than their mean does.

**The levels, as observations** (interview, 2026-09-30): the fit on each level's usable runs among its first
n_l points: its size, its coefficients, relative residual, R², and LOO error. The estimates are level L's; the
earlier levels show how they move as the runs double. There is no check of the observed rate against the
sampler's r (`../designs.md` asked): a check would compare with a threshold, which is interpretation (P2). A
level with fewer than 2(d + 1) usable runs has "none" in its column.

**Changes of units** (P6): y → a·y + b, with a > 0, gives β₀ → a·β₀ + b and βᵢ → a·βᵢ, and leaves the relative
residual, R², the LOO error, and the notes unchanged. A log scale is part of the unit coordinates, so it changes
the fit (R1 with k linear is not exactly linear).

**Failed runs** and runs missing the model prediction are left out of every estimate (P6), counted in the
header and the note (`shared.md`), and drawn in the shadow's strip.

## Uncertainty

OD-12, for the linear model: **the bootstrap over the usable runs of level L** (interview, 2026-09-30),
`shared.md`'s defaults.

- **Resamples:** 1000 (`BOOTSTRAP_RESAMPLES`), each n_u indices drawn with replacement from the usable runs by
  `Generator(PCG64(SeedSequence(seed, spawn_key=(LINEAR_BOOT_TAG,)))).integers(0, n_u, (1000, n_u))`. Every
  estimate uses the same resamples.
- **Coefficients, relative residual, R²:** refitted on each resample as drawn, duplicates included.
- **LOO error:** recomputed on each resample's distinct runs (about 0.63·n_u of them), as scatter's binned index:
  a left-out run's copy would stay in the fit, and make it optimistic. On R3 at 72 runs (LOO 0.249, standard
  deviation 0.026 over designs), the median over resamples is 0.232 as drawn and 0.263 on distinct runs; on R7
  at 40, 0.725, 0.691, and 0.767 (interview, 2026-09-30).
- **Interval:** the 0.5th and 99.5th percentiles of the defined resampled values (`shared.md`, Bootstrap).
- **Undefined resamples:** a resample whose A has rank below d + 1, or whose distinct runs are fewer than d + 2
  for LOO, is dropped for that estimate, and the line under the table says how many of the 1000, when any are.
- **Three tables,** each with one line under it (`shared.md`): the coefficients; the fit (relative residual and
  R²); the LOO error ("… recomputed on the distinct runs of each resample").
- **Why not the levels:** nested levels share runs, so their estimates move together. Over 100 designs, the span
  of levels L − 1 and L was about a quarter of the estimates' spread over designs (R3's slope for rw: width 2.8
  against a standard deviation of 2.92; the bootstrap's width was 13.9, about 4.7 standard deviations).
- **The relative residual's interval** shows variability, not the in-sample residual's bias at small n (R3 at 72
  runs: 0.213 on average, against 0.230 over the space); the LOO error carries the held-out view.

### Later: intervals by subsampling the levels

A convergent design allows another interval method (the owner's proposal, interview 2026-09-30): fit on many
subsets of n₀ = n_(L−1) runs drawn without replacement from the n₁ = n_L usable runs, and read the variability
from the spread of those estimates.

- **Its name and theory:** subsampling (Politis and Romano 1994; Politis, Romano and Wolf 1999), the delete-d
  jackknife (Wu 1986; Shao and Wu 1989), and, for n₀ = n₁/2, half-sampling (McCarthy 1969). The spread at n₀
  describes an estimate from n₀ runs; for a √n-rate estimator it is rescaled by √(n₀/(n₁ − n₀)), in general
  ((n₀/n₁)^(−2r) − 1)^(−1/2) with the sampler's r. At doubling levels (alpha ≈ 1/√2) the factor is 1.
- **Checked** on R3's slope for rw at 72 runs (standard deviation 2.92 over 100 designs): subsets of 36 had a
  spread of 3.18; subsets of 18, rescaled, 3.72 (2 runs per coefficient). The minimum and maximum over subsets
  grow with the number of subsets (width 18.3 over 300 subsets), so the method would use percentiles or a
  stated number of subsets.
- **Seams kept in v2.0:** one interval-method interface (usable runs in design order with their levels, an
  estimator, its own spawned stream → intervals and the line under the table), with the bootstrap its only
  implementation; each estimator a pure function of a set of run indices; the convergent design's levels,
  sizes, and the sampler's r in the diagnostic result; the method, its settings, and its spawn tag named in the
  result, and the method and its settings under each table (0041).
- **Effort later:** an `interval` diagnostic parameter (part of the request's identity; v2.0 accepts only
  `bootstrap`, as `sampler` accepts only `random`), about 40–60 lines, a record, and known answers comparing the
  subset spread with the spread over designs on R3 and R7.

## Minimum runs and degenerate cases

- **Fewest usable runs:** 2(d + 1) (`LINEAR_MIN_RUNS`), the default n_min: a resample then keeps about 1.3(d + 1)
  distinct runs, so few are rank-deficient. Below it: counts and a note, no estimates (P6); the shared
  observations and the per-level table stay.
- **All runs failed:** counts by kind and the note; no estimates or observations (`shared.md`).
- **Constant:** the note, the observations, no estimates (0035). R4b is not constant: estimates of its wiggle.
- **Exactly linear** (R1): relative residual and LOO at rounding (about 10⁻¹⁵), R² = 1, and intervals of about
  that width.
- **A slope vector of exact zeros** (only when every usable run's y is the same, which the constant case
  catches first): no shadow.
- **Runs not usable:** estimates from the usable runs of level L; each level's column in the per-level table
  uses its usable runs among its first n_l points.

## Figures

**`linear_model_shadow.png`** (U4's 1-D shadow; interview, 2026-09-30):

- **x axis:** w·u, the usable runs' unit coordinates projected on w = β/‖β‖ (the slopes, normalized): the
  direction in which the fit rises. Labeled `w·u`; dimensionless, within [−√d, √d].
- **y axis:** the model prediction, `name [units]`.
- **Points:** one marker per usable run of level L; the fitted line β₀ + ‖β‖·(w·u).
- **Runs not usable:** × in the strip below the axes, at their w·u (`shared.md`).
- **Data card:** w, β₀, ‖β‖, and each point's w·u, y, and run id.

**`linear_model_coefficients.png`:**

- One point per slope βᵢ, with its variability interval as a bar, in the model spec's order, and a line at 0;
  the intercept only in the table (its scale differs).
- **y axis:** `slope [units of y]`, per half-range of each model parameter.
- **Data card:** each slope and its interval.

**`linear_model_residuals.png`:**

- ⌊√n_u⌋ equal-width bins of r = y − ŷ over the usable runs of level L (the rule of scatter's histogram).
- **x axis:** `residual of name [units]`; **y axis:** the number of runs.
- **Data card:** the bin edges and counts.

## Mock report

On R3 (the borehole, 8 model parameters, as U4's lens model) with the defaults and U4's seed 3: n_min = 18,
alpha = 0.7072, level 2, 72 runs. The numbers are computed: the design from `default_rng(3).random((72, 8))`
(the `random` sampler's rows, 0032), the bootstrap from the stream above (a scratch script, 2026-09-30; step 11
checks them).

```markdown
# Linear model: R3, y

| | |
|---|---|
| Model version | R3@c05e |
| Model prediction | y: water flow through the borehole, m³/yr |
| Space | rw [0.05, 0.15] m; r [100, 5e+04] m, log; Tu [6.307e+04, 1.156e+05] m²/yr; Hu [990, 1110] m; Tl [63.1, 116] m²/yr; Hl [700, 820] m; L [1120, 1680] m; Kw [9855, 1.204e+04] m/yr |
| Held | none |
| Design | convergent, n_min = 18, alpha = 0.7072, r = 0.5, level 2: 18, 36, 72 points; sampler random 1, seed 3 |
| Runs | 72: 72 new, 0 reused; 0 failed; 0 missing y; 72 usable |

## Estimates

Each variability interval shows how much its estimate changes when the runs behind it change, by the method named
under its table; it is not a confidence interval, and carries no coverage probability.

| Coefficient | Estimate | Variability interval |
|---|---|---|
| Intercept | 78.27 m³/yr | [74.39, 82.02] m³/yr |
| rw | 69.19 m³/yr | [62.31, 77.66] m³/yr |
| r | 3.089 m³/yr | [−4.032, 9.424] m³/yr |
| Tu | 0.7283 m³/yr | [−7.785, 7.972] m³/yr |
| Hu | 9.323 m³/yr | [1.944, 16.68] m³/yr |
| Tl | −0.2023 m³/yr | [−6.665, 5.679] m³/yr |
| Hl | −16.3 m³/yr | [−23.51, −10.14] m³/yr |
| L | −11.39 m³/yr | [−18.83, −4.943] m³/yr |
| Kw | 7.478 m³/yr | [1.701, 14.31] m³/yr |

y ≈ intercept + Σ slope·u, u the unit coordinates in [−1, 1] (r through its logarithm). Variability intervals:
bootstrap over the 72 usable runs, 1000 resamples, 0.5th to 99.5th percentiles, seed 3.

| Fit | Estimate | Variability interval |
|---|---|---|
| Relative residual ‖r‖ / ‖y − mean‖ | 0.2335 | [0.1631, 0.2641] |
| R² | 0.9455 | [0.9302, 0.9734] |

Variability intervals: bootstrap over the 72 usable runs, 1000 resamples, 0.5th to 99.5th percentiles, seed 3.

| Held out | Estimate | Variability interval |
|---|---|---|
| Leave-one-out error, relative | 0.2716 | [0.2168, 0.336] |

Variability intervals: bootstrap over the 72 usable runs, 1000 resamples, the error recomputed on the distinct
runs of each resample, 0.5th to 99.5th percentiles, seed 3.

## Observations

| Of the 72 usable runs | y |
|---|---|
| Minimum | 10.24 m³/yr |
| Maximum | 181.9 m³/yr |
| (max − min) / max\|y\| | 0.9437 |

| The fit at each level | Level 0 | Level 1 | Level 2 |
|---|---|---|---|
| Usable runs | 18 of 18 | 36 of 36 | 72 of 72 |
| Intercept | 79.67 | 77.82 | 78.27 |
| rw | 69.78 | 71.31 | 69.19 |
| r | 6.095 | 1.948 | 3.089 |
| Tu | 5.239 | −1.636 | 0.7283 |
| Hu | 18.79 | 12.09 | 9.323 |
| Tl | −4.137 | −5.668 | −0.2023 |
| Hl | −21.19 | −16.9 | −16.3 |
| L | −18.25 | −14.83 | −11.39 |
| Kw | 12.38 | 8.034 | 7.478 |
| Relative residual | 0.1408 | 0.2038 | 0.2335 |
| R² | 0.9802 | 0.9584 | 0.9455 |
| Leave-one-out error | 0.2934 | 0.2879 | 0.2716 |

Coefficients in m³/yr. Each level is fitted on the usable runs among its first points.

## Figures

![y against w·u](linear_model_shadow.png)

y against w·u, the unit coordinates projected on the direction of the slopes, with the fitted line. Data card:
`linear_model_shadow.json`.

![Slopes](linear_model_coefficients.png)

Each slope with its variability interval, in m³/yr per half-range. Data card: `linear_model_coefficients.json`.

![Residuals](linear_model_residuals.png)

The residuals of the 72 usable runs, 8 bins. Data card: `linear_model_residuals.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R3@c05e; request: linear model, space
as above, n_min = 18, alpha = 0.7072, level 2, sampler random 1, seed 3, prediction y; runs: 72; approvals:
e810 (72 new runs).
```

(For comparison, over the space: intercept 77.75; slopes 71.50, −0.15, 0.01, 16.08, 0.16, −16.10, −15.63,
7.74; relative residual 0.2303. The small slopes of r, Tu, and Tl are within their intervals of 0.)

## Expected answers

Each at n_min = 5000, alpha = 0.5, level 1 (20,000 runs), seed 0, `random` sampler. The tolerance is 5 × the
estimate's standard deviation over 100 designs (seeds 1–100) at 20,000 runs, computed by a scratch script on
2026-09-30; step 11 recomputes it with a separate script.

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R1 | intercept; slopes a, b, c, k | 10; 3, −1, 0, 2 | 10⁻¹² | analytic: exactly linear in unit coordinates |
| R1 | relative residual; R²; LOO | 0; 1; 0 | 10⁻¹² | analytic |
| R2 | intercept; slopes x1, x2, x3 | 3.5; (3/π)(1 + 0.02π⁴) = 2.815, 0, 0 | 0.11; 0.18, 0.22, 0.24 | analytic |
| R2 | relative residual; R² | 0.8995; 0.1908 | 0.010; 0.018 | analytic (Ishigami's variance 13.84) |
| R7 | intercept; slopes a, b, c, e | 1.068; 0.2230, 0.72, 0, 0.2230 | 0.016; 0.024, 0.025, 0.024, 0.029 | analytic (a and e: 3·E[max(0, a + e − 0.6)·a]; c: 0 by symmetry) |
| R7 | relative residual; R² | 0.6739; 0.5458 | 0.014; 0.019 | analytic |
| R10 | intercept; slopes a, b, c, e | 0; 2√3 = 3.464, 0, 0, 0 | 0.060; 0.12, 0.098, 0.13, 0.10 | analytic |
| R10 | relative residual; R² | √(2.5/6.5) = 0.6202; 4/6.5 = 0.6154 | 0.016; 0.020 | analytic |
| R3 | intercept; slopes; relative residual | 77.75; 71.50, −0.15, 0.01, 16.08, 0.16, −16.10, −15.63, 7.74; 0.2303 | 0.32; 0.91, 0.68, 0.64, 0.73, 0.69, 0.87, 0.70, 0.64; 0.0064 | brute force (2·10⁶ points; step 11 recomputes) |
| each of R2, R3, R7, R10 | LOO error | the relative residual's value | the relative residual's tolerance | its limit as n grows |
| R4a | notes; estimates | the "constant" note; none | exact | trivial |
| R4b | estimates | present | exact | 0035 |
| R5, y and z | every estimate | equal to the linear model computed on the usable runs alone | exact | by construction (U3) |
| R3, defaults, seed 3 | the report | the mock report above | byte-identical (golden report) | this spec |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `LINEAR_NMIN` | 2(d + 1) | the default size of level 0 | twice the coefficients, as U4 assumes (interview, 2026-09-30) |
| `LINEAR_ALPHA` | 0.7072 | the default error factor per level | just above 1/√2: the points about double per level (interview, 2026-09-30) |
| `LINEAR_LEVEL` | 2 | the default last level | U4's: 8(d + 1) points (interview, 2026-09-30) |
| `LINEAR_MIN_RUNS` | 2(d + 1) | the fewest usable runs for estimates | resamples keep about 1.3(d + 1) distinct runs, so few are rank-deficient (interview, 2026-09-30) |
| `LINEAR_BOOT_TAG` | 2³² + 2 | the spawn key of the linear model's bootstrap stream | the next diagnostic tag after scatter's (`shared.md`) |
| `KNOWN_ANSWER_N` | 20,000 | the size of the known-answer designs | as scatter's: tolerances of 0.006–0.9 at 5 standard deviations |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| LM1 | The design is convergent with the request's n_min, alpha, level, seed, sampler, and space; a space with no varied model parameter is refused before building. | The design equals `convergent(...)` bit for bit; a space holding every model parameter: refused. |
| LM2 | The fit is least squares in unit coordinates, over the usable runs of level L, by QR. | R1 at the defaults: 10; 3, −1, 0, 2 within 10⁻¹²; R1 with k given a linear range: not exact. |
| LM3 | The relative residual, R², and the LOO error by PRESS, each as defined. | A hand-computed fixture of 6 runs in d = 1; LOO equal to explicit refits within 10⁻¹². |
| LM4 | Intervals: 1000 resamples from the linear model's stream, the same for every estimate; LOO on each resample's distinct runs; the 0.5th and 99.5th percentiles; undefined resamples dropped and counted. | Changing `LINEAR_BOOT_TAG` changes the intervals, not the design (S8); a fixture at 2(d + 1) runs: the count under the table. |
| LM5 | The per-level table: each level fitted on its usable runs among its first n_l points; "none" below 2(d + 1). | R3 at the defaults (the mock report); R5 where level 0 has too few usable runs. |
| LM6 | Fewer than 2(d + 1) usable runs: counts and a note, no estimates; the observations stay. | R5 in a space where 2d + 1 runs are usable; 2(d + 1). |
| LM7 | y → a·y + b (a a power of 2) maps the coefficients as stated, and leaves the relative residual, R², the LOO error, and the notes unchanged. | R2 with a = 2⁻¹⁰, b = 3. |
| LM8 | Three figures: the shadow on w = β/‖β‖ with its strip, the slopes with their intervals, the residual histogram with ⌊√n_u⌋ bins. | R5 at the defaults: the strip's count equals the header's. |
| LM9 | Nesting: level L + 1 after level L reuses every run; the first points are a scatter's with the same seed. | R3: level 3 after level 2 makes 72 new runs; U5. |
| LM10 | The known answers at 20,000 runs, and the golden report. | Expected answers. |

## Tests it implies

- The known-answer tests and the golden report in "Expected answers" (slow tier at 20,000 runs).
- `shared.md`'s S1–S10.
- The diagnostic contract (`../contracts.md`, step 7): all runs failed; 2d + 1 and 2(d + 1) usable runs; a
  constant model prediction; R4b; y → a·y + b; d = 1 and d = 20.
- The interval-method seam: a fake method registered in the tests replaces the bootstrap, and the report's
  lines name it.

## What this spec asks of other documents

- **`shared.md`:** the linear model's spawn tag, 2³² + 2 (applied).
- **Uncertainty (step 7):** the linear model's bootstrap, LOO on distinct runs, and why not the levels; the
  interval-method interface, and subsampling as a later method.
- **`../designs.md`'s questions for OD-12** (step 7): the linear model needs one level for its intervals, and
  checks no rate against r.
- **Reference models (step 11):** the expected answers above; R3's by a separate brute-force script.
- **Architecture (step 9):** the interval-method interface; estimators as functions of run indices.
