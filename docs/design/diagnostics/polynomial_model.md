# Polynomial model

**Status:** accepted. **Updated:** 2026-10-01 (step 11, 0058); 2026-10-02 (the build's choices: the constants'
factor, the notes, V = 0, the figures' cards, R2's known answer without intervals, 0079; the mock's Provenance
line, 0073; the in-sample relative residual and R² as observations, 0085). **Module:**
`ema/diagnostics/polynomial_model.py`. **Depends on:** `shared.md`; `linear_model.md`; `../designs.md`;
`../uncertainty.md`; records 0012, 0032, 0033, 0034, 0035, 0039, 0041, 0042, 0044, 0048, 0049, 0051, 0052, 0058,
0073, 0079, 0085.

> A least-squares polynomial fit of the model prediction in unit coordinates, over a convergent design: how well
> it fits, how its variance splits among the model parameters (Sobol indices), and how fast its coefficients
> decay (0012, U4). Written from an interview on 2026-09-30 (TODO step 6). Everything not stated here follows
> `shared.md`; where it follows the linear model, it says so.

## Summary

| | |
|---|---|
| **User provides** | a model parameter space, degree p (2), n_min (2P), alpha (0.7072), level (2), seed (0), sampler (`random`), basis (`total_degree`), the model prediction |
| **Design** | convergent (`../designs.md`): levels 0 … L, level l the first n_l points of one uniform design |
| **Compute** | the least-squares fit over the usable runs of level L, in the orthonormal Legendre terms of total degree ≤ p; its leave-one-out error; the Sobol indices of the fitted polynomial; the root energy at each degree; bootstrap intervals for these; its in-sample relative residual and R², and the fit at each level, as observations (0085) |
| **Plots** | y against the fitted and the held-out predictions; the Sobol indices with their intervals; the root energy against the degree; a histogram of the residuals |
| **Report** | three tables of estimates with variability intervals (the LOO error; the Sobol indices; the root energy per degree), the shared observations, the per-level table (with the relative residual and R², no interval), the figures |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `space` | model parameter space | required | the ranges varied, and the values held (`../designs.md`) | yes |
| `degree` | integer ≥ 1 | 2 | p, the largest total degree of a term | yes (through n_min's default) |
| `n_min` | integer ≥ 1 | 2P | the size of level 0 | yes |
| `alpha` | decimal in (0, 1) | 0.7072 | the error factor per level (`../designs.md`, Convergent) | yes |
| `level` | integer ≥ 0 | 2 | L, the last level | yes |
| `seed` | integer ≥ 0 | 0 | the design's seed, and the bootstrap's (`shared.md`) | yes |
| `sampler` | name | `random` | the sampler (0032); convergent needs a nested one | yes |
| `basis` | name | `total_degree` | the set of terms; v2.0 accepts only `total_degree` | no |
| `prediction` | model prediction name | the only one | the model prediction analyzed (0022) | no |

- **d** is the number of varied model parameters; **P** = C(d + p, p) is the number of terms, and of
  coefficients.
- **The defaults**, as the linear model's with P in place of d + 1: n_min = 2P, twice the coefficients, as U4
  assumes; alpha = 0.7072, so the points about double per level; level 2, so about 8P points (exactly 8P for P ≤
  237; G7's formula decides):

  | d, p | P | level 0 (2P) | level 2 (8P) | cond(A) at 2P, median of 50 designs |
  |---|---|---|---|---|
  | 3, 2 | 10 | 20 | 80 | 5.7 |
  | 8, 2 (U4's r2) | 45 | 90 | 360 | 6.6 |
  | 8, 3 (U4's r3) | 165 | 330 | 1320 | 8.8 |
  | 3, 8 | 165 | 330 | 1320 | 89 |
  | 2, 10 | 66 | 132 | 528 | 163 |

- **Degree:** 2 by default, the smallest step past the linear model, and U5's; degree 3 is an explicit request
  (U3, U4), and its price is in the approval (P3). p = 1 is accepted: it gives the linear fit's Sobol indices,
  with coefficients scaled by ψ₁(u) = √3·u rather than the linear model's slopes.
- **The basis:** `total_degree` is the only value v2.0 accepts; any other is refused with "basis X comes in a later
  version", as `sampler` is (0032): the diagnostic reads any well-formed name, and the registry refuses one it
  lacks when the design is built, before any run (0079 items 2, 19). Its "Changes the design?" stays "no": C14
  passes a "no" whose other value is refused as coming later, and the promise is tested with a second basis
  registered (C29's fake): the same design bit for bit, and another request, so another reuse key (0079 item
  20). Later index sets (hyperbolic cross, which has 53 terms (Π(αᵢ + 1) ≤ p + 1)
  against 165 at d = 8, p = 3; a sparse fit by orthogonal matching pursuit) are about 30–80 lines each, with a
  record and known answers. The basis is not part of the design, but is part of the request's identity.
- **A small n_min** is accepted (`../designs.md` refuses only sizes that aren't strictly increasing): the
  estimates need 2P usable runs at level L (below), and a smaller level has "none" in the per-level table.
- **Nested** in level with the same space, seed, and sampler (G7), and across degrees: a convergent design's
  points are the first points of one uniform design, so degree 3 after degree 2 with the same seed reuses the
  degree-2 runs (U4), and a scatter's (U5).
- **A space with no varied model parameter** is refused before building.
- **The header** adds a Fit row after Design (`shared.md`): "degree 2, total_degree basis: 45 terms".

## Computation

Let the n_u usable runs of level L (`shared.md`, the precheck) have values y_k and unit coordinates
u_k ∈ [−1, 1]^d (`../designs.md`: through the logarithm for a log range).

**The fit:**

- **Terms:** ψ_α(u) = Π_i ψ_(α_i)(u_i) for every multi-index α with |α| = Σ α_i ≤ p, where ψ_k is the orthonormal
  Legendre polynomial of degree k on [−1, 1] under the uniform measure (`../reference_models.md`). Under the
  uniform distribution on unit coordinates the terms are orthonormal, so the fitted polynomial's mean is c_0 and
  its variance is Σ_(α≠0) c_α²: each coefficient squared is the variance its term carries.
- **Order of the terms:** by total degree, then by the exponents in the model spec's order, largest first (v1's
  `total_degree_indices`).
- **Model:** y ≈ Σ_α c_α ψ_α(u), by least squares over the usable runs, from a QR factorization of
  A = [ψ_α(u_k)] (n_u × P).

- **The coefficients** are in the diagnostic result and a data card, all P of them with their multi-indices,
  each an estimate with its bootstrap interval (0041), and not in the report: the Sobol indices and the decay
  summarize them. (On R3 at p = 2 and 360 runs, the 10 largest of 45 carry 99.8% of Σc²; which terms are largest
  depends on the runs.)

**How well it fits,** as the linear model (`linear_model.md`):

- **Relative residual:** ‖r‖ / ‖y − ȳ‖, with r = y − Ac over the usable runs; and **R²:** 1 − ‖r‖² / ‖y − ȳ‖².
  Both are observations (0085), level L's in the per-level table, with no variability interval (Uncertainty).
- **Leave-one-out (LOO) error** by PRESS: √(Σ_k (r_k / (1 − h_kk))²) / ‖y − ȳ‖, with the leverages h_kk the
  squared row norms of Q. No refits and no random draws. U4's "cross-validated error".
- **Why:** on R3 at p = 2, over 50 designs, the LOO error at 90, 180, and 360 runs is 0.051, 0.041, 0.038, and
  the error on 10⁵ fresh points 0.053, 0.041, 0.037; the in-sample residual is 0.022, 0.028, 0.032.

**Sobol indices of the fitted polynomial** (Sudret 2008):

- **From the coefficients:** with V = Σ_(α≠0) c_α², the polynomial's variance,
  - **first-order:** S_i = Σ c_α² / V over the terms in u_i alone (α_i > 0, every other α_j = 0);
  - **total:** T_i = Σ c_α² / V over the terms that involve u_i (α_i > 0).
- **Of the polynomial, not the model:** these are exactly the Sobol indices of the fitted polynomial under the
  uniform distribution in unit coordinates, and the report's table says so. They converge to the model's as
  the fit does; at low degree they can be far from them, and R² and LOO beside them show how far the fit is.
  On R2 at 8P runs (analytic first 0.314, 0.442, 0; total 0.558, 0.442, 0.244):

  | p | R² | first | total |
  |---|---|---|---|
  | 2 | 0.23 | 0.728, 0.065, 0.066 | 0.794, 0.168, 0.180 |
  | 4 | 0.81 | 0.295, 0.432, 0.009 | 0.542, 0.470, 0.258 |
  | 6 | 0.985 | 0.319, 0.439, 0.000 | 0.559, 0.442, 0.242 |
  | 10 | 1.000 | 0.314, 0.442, 0.000 | 0.558, 0.442, 0.244 |

- **Not chosen:** normalizing by the sample variance of y instead of V. In the limit those are lower bounds on
  the model's indices (each group of terms is a projection of the model's ANOVA component), but they carry the
  sample variance's error even when the fit is exact (R2 at p = 10: total of x1 0.605), and they are about
  S_i·R², which the report already allows.
- **Which:** the first-order and total index of each varied model parameter, in the model spec's order (U4's
  lean set). No interaction share and no pair indices; the pair sums are in the coefficients, in the result.
- **Units:** none, and y → a·y + b leaves them unchanged (P6).

**The decay of the coefficients** (0012):

- **Total degree:** a term ψ_α has total degree k = |α|, the sum of its one-variable degrees. On R3 at p = 2,
  degree 1 has 8 terms (ψ₁(rw), …, ψ₁(Kw)), and degree 2 has 36 (8 squares ψ₂(rw), …, and 28 products
  ψ₁(rw)·ψ₁(Hu), …).
- **Root energy at degree k:** √E_k, with E_k = Σ_(|α|=k) c_α², for k = 1 … p: the standard deviation of the
  polynomial's degree-k part, in y's units. E_1 + … + E_p = V. Along one model parameter it is |c_k|, coordinate
  lines' spectrum (`coordinate_lines.md`).
- **Why per degree, in y's units:** least-squares coefficients converge to the model's own Legendre
  coefficients, so √E_k estimates the model's energy at degree k whatever p is, except that the top degrees
  absorb aliasing at small n. R3's first three agree to 3 digits at p = 3, 4, and 5 (44.47, 10.41, 1.549 m³/yr),
  so U4's degree 2 and degree 3 give matching rows. Shares E_k / V would change with p.
- **No rate:** a tail rate over k = 1 … p depends on the window, not only on the model (R3: 0.735, 0.809, 0.858 at
  p = 3, 4, 5; R11's exact spectrum 0.125 over 1 … 4, against its limit log₁₀ φ = 0.209), it has no value at the
  default p = 2, and R2's energy rises up to degree 4. The reader sees the decay in the table and the figure;
  rerunning at p + 1 is the check (the runs are reused up to the new level's size).

What it gives (mean over 20 designs at 8P runs; a scratch script, 2026-09-30):

| Model | p | √E_1 … √E_p |
|---|---|---|
| R3 | 3 | 44.47, 10.41, 1.549 m³/yr |
| R11 | 6 | 0.002, 0.194, 0.005, 0.091, 0.006, 0.049 (odd degrees 0 exactly in the model) |
| R2 | 8 | 1.62, 0.60, 1.88, 1.96, 1.18, 1.36, 0.37, 0.35 |
| R7, a kink and a jump | 8 | 0.454, 0.312, 0.148, 0.138, 0.058, 0.092, 0.027, 0.077 |
| R10 | 3 | 2.000, 1.581, 3·10⁻¹⁶ |

**Changes of units** (P6), for the whole fit: y → a·y + b, with a > 0, gives c_0 → a·c_0 + b, c_α → a·c_α, and
√E_k → a·√E_k, and leaves the relative residual, R², the LOO error, the Sobol indices, and the notes unchanged
(exactly under a·y; within C5's tolerances under the shift, 0048). A log scale is part of the unit coordinates,
so it changes the fit.

**Failed runs** and runs missing the model prediction are left out of every estimate (P6), counted in the
header and the note (`shared.md`), and drawn in the fit figure's strip.

**The levels, as observations** (as the linear model's): the fit on each level's usable runs among its first n_l
points: its usable runs, relative residual, R², LOO error, and each model parameter's total index (4 + d rows).
The estimates are level L's; the earlier levels show whether the fit and the ranking settle as the runs double.
No check of the observed rate against the sampler's r (P2). A level with fewer than 2P usable runs, with A of
rank below P, or where a number is 0/0 (a constant model prediction) has "none" in its column (0079 item 8).
Under the table, after "Each level is fitted on the usable runs among its first points.", the linear model's
line on the in-sample measures (`linear_model.md`, 0085).

## Uncertainty

OD-12, for the polynomial model: **the bootstrap over the usable runs of level L**, as the linear model's
(`linear_model.md`): `../uncertainty.md`'s bootstrap (The bootstrap), from the polynomial model's stream
(`POLY_BOOT_TAG`). What differs (0052):

- **On distinct runs:** the LOO error, as the linear model's. The coefficients, Sobol indices, and √E_k are
  refitted on each resample as drawn, duplicates included (the pairs bootstrap). The as-drawn estimates share one
  refit per resample; the LOO error is a second, on distinct runs, skipped below P + 1 distinct runs (0079 item 7).
- **No interval for the relative residual and R²** (0085), as the linear model's: refits on repeated runs look
  better than the fit, by more as P grows against the distinct runs (on Ishigami at degrees 6, 8, and 10, both
  fell outside their own intervals every time; the LOO error never did). They are observations, in the
  per-level table.
- **Undefined resamples:** a resample whose A has rank below P (numpy's `matrix_rank` rule, as at level L, below),
  or whose distinct runs are fewer than P + 1 for LOO. The LOO error and the Sobol indices are also undefined on
  a resample whose y or fitted polynomial is constant (0/0, `../uncertainty.md`'s bootstrap step 3; each
  resample's y as drawn is tested with `is_constant`, 0068 item 10). They are counted per estimate, keyed by a
  short name ("leave-one-out error", "rw first-order", "rw total", "√E_2"); the report prints those that aren't 0
  (0079 item 7).
- **Checked** against the spread over 200 designs (R3, p = 2, 360 runs; a scratch script, 2026-09-30): the
  intervals' widths are 0.85–2.3 times 5.15 standard deviations over designs, across the 20 estimates.
  Refitting on distinct runs gave 0.66–1.7, and was not chosen, so that the two fits' bootstraps stay alike.
- **The bias of squared coefficients:** each c_α² sits above its limit by about Var(c_α), and a resample adds
  that again, so the interval of a model parameter with no effect sits just above 0 (R3's r, total: 4.3·10⁻⁵
  [1.7·10⁻⁵, 2.2·10⁻⁴], as in the mock report below). The indices are reported as computed, the indices of the
  fitted polynomial, always in [0, 1]. Not chosen: subtracting s²·[(AᵀA)⁻¹]_αα from each c_α² (closer to the
  limit on average, R2's x3 first-order at p = 4: 0.0042 against 0.0091, limit 0; but no longer the
  polynomial's own index, and s² treats a deterministic model's misfit as noise).
- **Why not the levels:** as the linear model's; the levels are observations (below).

### The analysis's cost and progress

- **No cap on the number of terms:** any P whose design is under the 10⁷-point cap (`../designs.md`). The
  bootstrap's 1000 refits each cost about 2·n_u·P² flops (at 8P runs, measured on a
  laptop, 2026-09-30):

  | d, p | P | 1000 refits |
  |---|---|---|
  | 8, 2 | 45 | 0.4 s |
  | 8, 3 | 165 | 14 s |
  | 8, 4 | 495 | 2.2 min |
  | 20, 3 | 1771 | 54 min |

- **Progress:** the analysis reports its progress through the same `on_progress(Progress)` callback as runs, with
  its `done`, `total`, and `text` (`../architecture.md`): "bootstrap: 230 of 1000 refits, about 6 min left", the
  time left from the refits so far, about once a second. The CLI shows it as a progress line, and the MCP server as
  progress notifications.
- **The matrix's size:** before the bootstrap starts, the progress shows A's shape and memory ("A: 14161 × 1771,
  200 MB"). There is no refusal: memory is the user's to judge (d = 20, p = 4 at the defaults is 84,964 ×
  10,626, 7.2 GB). If numpy can't allocate it, the diagnostic evaluation fails with that reason, and keeps its
  runs.
- **The price is unchanged** (P3): runs and their time. An analysis-time estimate in the price, from timing one
  fit of the design's shape before asking, was considered and not chosen (it needs a record changing P3's
  enforcement and the glossary's "price").
- **Interrupted** during the analysis: every run is stored, no diagnostic result is; a rerun reuses the runs and
  recomputes.

## Minimum runs and degenerate cases

- **Fewest usable runs:** 2P (`POLY_MIN_RUNS`), as the linear model's 2(d + 1): a bootstrap resample then keeps
  about 1.26P distinct runs, above P. Below it: counts and a note, no estimates (P6); the shared observations
  and the per-level table stay. U3's r2 (68 usable runs, 84 coefficients) gets the precheck's note (`shared.md`;
  0079 item 5): "68 usable runs; polynomial model needs at least 168 (twice its 84 coefficients at degree 3)."
- **All runs failed:** counts by kind and the note; no estimates or observations (`shared.md`).
- **Constant:** the note, the observations, no estimates (0035). R4b is not constant: estimates of its wiggle.
- **Exactly a polynomial of degree ≤ p** (R1 at any p, R10 at p ≥ 2): relative residual and LOO at rounding
  (about 10⁻¹⁵), R² = 1, the exact coefficients, and intervals of about that width.
- **A at level L with rank below P** (usable runs that don't determine every term, as when failures leave
  fewer than P distinct values along a model parameter of degree p): no estimates, and a note: "The 40 usable
  runs don't determine the degree-2 polynomial: A has rank 9 of 10." (0079 item 9). The observations stay, and
  the Fit header row is written in every case. A's rank is numpy's `matrix_rank` rule: the number of singular
  values above max(n_u, P)·ε·σ_max, ε the double's machine epsilon (0051).
- **The LOO error undefined on the usable runs** (a run of leverage 1): no Held out table, "none" in the
  per-level table's LOO row, and a note: "The leave-one-out error is undefined: a usable run has leverage 1."
  (`../uncertainty.md`, Rules; 0079 items 10, 22).
- **V = 0** (every fitted c_α with α ≠ 0 exactly 0, though y varies; only in a contrived design, such as R11's
  space at degree 1 with 8 runs at (±0.375, ±0.375), y = 0, and at (±1, ±1), y = 1, where the ψ₁ coefficients
  come out exactly 0 on some LAPACKs): the fit's numbers, no Sobol estimates, and a note: "The fitted
  polynomial is constant (V = 0), so it has no Sobol indices." (0049). The decay table stays, every √E_k 0
  (0079 items 11, 21).
- **Runs not usable:** estimates from the usable runs of level L; each level's column in the per-level table
  uses its usable runs among its first n_l points.
- **Figures** (0051): with no estimates (too few usable runs, all runs failed, constant, or A of rank below P),
  none: every figure needs the fit, so the report has no Figures section. With V = 0: the fit and residual
  figures; no Sobol figure, and no decay figure (every √E_k is 0, so its axis has no scale).

## Figures

**`polynomial_model_fit.png`** (0039), two panels with the same axes:

- **Left, in sample:** each usable run of level L at (ŷ_k, y_k), ŷ_k the fitted polynomial at its point; the
  line y = ŷ.
- **Right, held out:** each usable run at (ŷ₋ₖ, y_k), ŷ₋ₖ = y_k − r_k / (1 − h_kk), the prediction of the fit
  without run k (PRESS; no refits); the line y = ŷ. The spread here is the LOO error's.
- **Axes:** x `fitted name [units]` and `held-out prediction of name [units]`; y the model prediction.
- **Runs not usable:** × in the strip below each panel, at the fitted polynomial's value at their point (they
  were not fitted, so it is a held-out prediction in both panels).
- **Not a shadow** (0039): the polynomial model's shadows come with the active subspace, later.
- **Data card:** each point's run id, y, ŷ, and ŷ₋ₖ, every usable run in each panel; a held-out prediction that
  isn't finite (a leverage of 1) is null, and that run is not drawn in the right panel; the runs not usable with
  their kind and ŷ; and the coefficients, each with its multi-index, term, value, and interval (0079 items 13,
  25).

**`polynomial_model_sobol.png`:**

- For each varied model parameter, in the model spec's order, two points side by side, the first-order and the
  total index, each with its variability interval as a bar; a legend for the two, its swatches a dot with its
  bar, as the series are drawn (0079 item 25).
- **x axis:** "model parameter", with the names as ticks. **y axis:** `Sobol index of the fitted polynomial`,
  linear, [0, 1].
- **Data card:** each index and its interval.

**`polynomial_model_decay.png`:**

- √E_k against the degree k = 1 … p, with intervals as bars; **y axis** log, `root energy at degree k [units]`;
  **x axis** `total degree k`, integers.
- A degree whose √E_k is below the panel's lower limit, 10⁻¹⁷ of the largest (`SPECTRUM_YMIN`, as coordinate
  lines'), whether an exact zero or rounding, is an open marker on the bottom edge (0048).
- **Data card:** each degree's number of terms, √E_k, and its interval; the lower limit, and the degrees drawn
  as open markers (0079 item 13).

**`polynomial_model_residuals.png`:** as the linear model's: ⌊√n_u⌋ equal-width bins of r = y − ŷ over the usable
runs of level L; **x axis** `residual of name [units]`, **y axis** the number of runs; the data card has the bin
edges and counts.

## Mock report

U4's r2 on R3 (the borehole, 8 model parameters, as U4's lens model): p = 2 and the defaults, seed 3, after the
linear model's mock report (`linear_model.md`), so its 72 runs are reused: n_min = 90, alpha = 0.7072, level 2,
360 runs. The numbers are computed: the design from `default_rng(3).random((360, 8))` (the `random` sampler's
rows, 0032), the bootstrap from the polynomial model's stream; checked at step 11 by
`../../checks/polynomial_model.py`.

```markdown
# Polynomial model: R3, y

| | |
|---|---|
| Model version | R3@c05e |
| Model prediction | y: water flow through the borehole, m³/yr |
| Space | rw [0.05, 0.15] m; r [100, 5e+04] m, log; Tu [6.307e+04, 1.156e+05] m²/yr; Hu [990, 1110] m; Tl [63.1, 116] m²/yr; Hl [700, 820] m; L [1120, 1680] m; Kw [9855, 1.204e+04] m/yr |
| Held | none |
| Design | convergent, n_min = 90, alpha = 0.7072, level 2: 90, 180, 360 points; sampler random 1 (rate ½), seed 3 |
| Fit | degree 2, total_degree basis: 45 terms |
| Runs | 360: 288 new, 72 reused; 0 failed; 0 missing y; 360 usable |

## Estimates

Each variability interval shows how much its estimate changes when the runs behind it change, by the method named
under its table; it is not a confidence interval, and carries no coverage probability.

| Held out | Estimate | Variability interval |
|---|---|---|
| Leave-one-out error, relative | 0.04192 | [0.03645, 0.05058] |

Variability intervals: bootstrap over the 360 usable runs, 1000 resamples, the error recomputed on the distinct
runs of each resample, 0.5th to 99.5th percentiles, seed 3.

| Sobol indices of the fitted polynomial | First-order | Variability interval | Total | Variability interval |
|---|---|---|---|---|
| rw | 0.8304 | [0.8248, 0.8361] | 0.8673 | [0.8625, 0.8721] |
| r | 5.622e-06 | [1.007e-07, 6.983e-05] | 4.257e-05 | [1.703e-05, 0.0002161] |
| Tu | 3.38e-06 | [1.725e-07, 8.413e-05] | 4.465e-05 | [1.64e-05, 0.0002891] |
| Hu | 0.04188 | [0.03938, 0.04421] | 0.05421 | [0.05085, 0.05717] |
| Tl | 1.369e-06 | [3.161e-08, 5.496e-05] | 1.397e-05 | [8.325e-06, 0.0002055] |
| Hl | 0.04149 | [0.03906, 0.04369] | 0.05415 | [0.05143, 0.0564] |
| L | 0.03857 | [0.03655, 0.04051] | 0.05012 | [0.04713, 0.05265] |
| Kw | 0.009238 | [0.00811, 0.01044] | 0.01251 | [0.01103, 0.01412] |

Of the degree-2 polynomial fitted to the runs, under the uniform distribution in unit coordinates (r through its
logarithm). Variability intervals: bootstrap over the 360 usable runs, 1000 resamples, 0.5th to 99.5th
percentiles, seed 3.

| Total degree k | Terms | Root energy √E_k | Variability interval |
|---|---|---|---|
| 1 | 8 | 44.67 m³/yr | [44.22, 45.08] m³/yr |
| 2 | 36 | 10.37 m³/yr | [9.843, 10.96] m³/yr |

√E_k: the standard deviation of the fitted polynomial's terms of total degree k. Variability intervals:
bootstrap over the 360 usable runs, 1000 resamples, 0.5th to 99.5th percentiles, seed 3.

## Observations

| Of the 360 usable runs | y |
|---|---|
| Minimum | 10.24 m³/yr |
| Maximum | 225.2 m³/yr |
| (max - min) / max\|y\| | 0.9545 |

| The fit at each level | Level 0 | Level 1 | Level 2 |
|---|---|---|---|
| Usable runs | 90 of 90 | 180 of 180 | 360 of 360 |
| Relative residual | 0.02633 | 0.03296 | 0.03526 |
| R² | 0.9993 | 0.9989 | 0.9988 |
| Leave-one-out error | 0.05555 | 0.04664 | 0.04192 |
| Total index of rw | 0.8705 | 0.8651 | 0.8673 |
| r | 0.0003875 | 0.0001167 | 4.257e-05 |
| Tu | 0.0008148 | 7.24e-05 | 4.465e-05 |
| Hu | 0.04762 | 0.05401 | 0.05421 |
| Tl | 0.0003035 | 2.474e-05 | 1.397e-05 |
| Hl | 0.05415 | 0.05433 | 0.05415 |
| L | 0.04878 | 0.05239 | 0.05012 |
| Kw | 0.01158 | 0.01201 | 0.01251 |

Each level is fitted on the usable runs among its first points.
In-sample measures: refitting a resample's repeated runs makes the fit look better than it is, so they have no variability interval; the leave-one-out error's interval shows how the fit varies.

## Figures

![y against the fitted and held-out predictions](polynomial_model_fit.png)

y against the fitted polynomial (left) and against each run's held-out prediction (right), with the line
y = ŷ. Data card: `polynomial_model_fit.json`.

![Sobol indices](polynomial_model_sobol.png)

The first-order and total Sobol indices of the fitted polynomial, with their variability intervals. Data card:
`polynomial_model_sobol.json`.

![Root energy per degree](polynomial_model_decay.png)

√E_k against the total degree k, with variability intervals, in m³/yr. Data card: `polynomial_model_decay.json`.

![Residuals](polynomial_model_residuals.png)

The residuals of the 360 usable runs, 18 bins. Data card: `polynomial_model_residuals.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R3@c05e; request: polynomial model,
space as above, degree 2, basis total_degree, n_min = 90, alpha = 0.7072, level 2, sampler random 1, seed 3,
prediction y; runs: 360; approvals: 4b1d (288 new runs).
```

(For comparison, by quadrature: the degree-2 polynomial over the space has relative residual 0.0341 and total
indices 0.8668, 0, 0, 0.0537, 0, 0.0537, 0.0516, 0.0126; the model's own are 0.8669, 0, 0, 0.0540, 0, 0.0540,
0.0522, 0.0128. The tiny indices of r, Tu, and Tl sit above 0 by the bias of squared coefficients (Uncertainty).)

## Expected answers

Each at n_min = 5000, alpha = 0.5, level 1 (20,000 runs), seed 0, `random` sampler, as the linear model's
(`KNOWN_ANSWER_N`, `shared.md`). The expected values are the limits as the runs grow: the coefficients of the
degree-p projection of the model, by tensor Gauss–Legendre quadrature of each term (40 points per model
parameter), or analytic. The tolerance is |mean over 100 designs (seeds 1–100) − expected| + 5
(`KNOWN_ANSWER_SDS`, `shared.md`) × the standard deviation over them, rounded up to 2 digits: the mean of a
squared quantity sits above a zero by its bias (R11's odd degrees: 3·10⁻⁵ to 1.3·10⁻⁴), so 5 standard deviations
alone would not cover it. Recomputed, both parts, at step 11 by `../../checks/polynomial_model.py` (60 points per model
parameter; its output: `polynomial_model.out`). R2's and R11's expected values are given to 6 digits, since 4
would put some of them off by more than their tolerance.

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R1, p = 2 | coefficients | ψ₁ terms √3, −1/√3, 0, 2/√3 (a, b, c, k); c_0 = 10; the rest 0 | 10⁻¹² | analytic: linear in unit coordinates |
| R1, p = 2 | relative residual; R²; LOO | 0; 1; 0 | 10⁻¹² | analytic |
| R1, p = 2 | first-order = total | 9/14 = 0.6429, 1/14 = 0.07143, 0, 4/14 = 0.2857 | 10⁻¹² | analytic (V = 14/3) |
| R1, p = 2 | √E_1; √E_2 | √(14/3) = 2.160; 0 | 10⁻¹² | analytic |
| R10, p = 2 | coefficients | ψ₁(a): 2; ψ₂(b): 0.5; ψ₁(a)ψ₁(c): 1.5; the rest 0 | 10⁻¹² | analytic: exact recovery (U4) |
| R10, p = 2 | relative residual; R²; LOO | 0; 1; 0 | 10⁻¹² | analytic |
| R10, p = 2 | first-order; total | 4/6.5, 0.25/6.5, 0, 0; 6.25/6.5, 0.25/6.5, 2.25/6.5, 0 (0.6154, 0.03846, 0, 0; 0.9615, 0.03846, 0.3462, 0) | 10⁻¹² | analytic (`../reference_models.md`) |
| R10, p = 2 | √E_1; √E_2 | 2; √2.5 = 1.581 | 10⁻¹² | analytic |
| R2, p = 10 | first-order (x1, x2, x3) | 0.313905, 0.442411, 0 | 4.1·10⁻⁵, 5.1·10⁻⁵, 10⁻⁵ | analytic (Ishigami); the degree-10 projection's agree to 10⁻⁵ |
| R2, p = 10 | total | 0.557589, 0.442411, 0.243684 | 5.1·10⁻⁵, 5.1·10⁻⁵, 4.1·10⁻⁵ | analytic |
| R2, p = 10 | √E_1 … √E_10 | 1.62542, 0.594723, 1.88396, 1.95229, 1.18024, 1.35741, 0.364431, 0.339391, 0.0502251, 0.0459147 | 1.9, 2.4, 2.2, 2.4, 2.2, 2.6, 3.2, 2.7, 3.2, 3.2 (·10⁻⁴) | quadrature |
| R11, p = 10 | first-order; total (a, b) | 0.448617, 0.448617; 0.551383, 0.551383 | 2.9·10⁻⁴, 3.3·10⁻⁴; 3.3·10⁻⁴, 2.9·10⁻⁴ | quadrature: the degree-10 projection's |
| R11, p = 10 | √E_1 … √E_10 | 0, 0.191472, 0, 0.0952851, 0, 0.0434089, 0, 0.0189107, 0, 0.00802035 | 1.1, 2.1, 1.7, 3.2, 2.7, 4.1, 3.2, 4.6, 3.9, 5.3 (·10⁻⁴) | quadrature (`../reference_models.md`: c_j·c_k) |
| R2, p = 10 | relative residual; LOO | 0.00137138; the same | 7.5·10⁻⁵ (both) | quadrature: √(1 − V/Var y), the degree-10 truncation's error |
| R11, p = 10 | relative residual; LOO | 0.0167170; the same | 9.6·10⁻⁴ (both; 0058) | quadrature, as R2's |
| R4a | notes; estimates | the "constant" note; none | exact | trivial |
| R4b | estimates | present | exact | 0035 |
| R5, y and z | every estimate and observation | equal to the polynomial model computed on the usable runs alone | exact | by construction (U3) |
| R3, p = 2, seed 3, defaults | the report | the mock report above | golden report (`shared.md`: structure, and numbers within one unit in the 4th digit) | this spec |

- **No brute-force known answers:** R3's Sobol indices and √E_k, from a degree-5 fit, were dropped; every
  expected value above is analytic or by quadrature. R3 keeps only the golden report, a regression check, not an
  independent answer.
- **Observations:** the relative residual and R² are observations (level L's column of the per-level table,
  0085); their known answers are checked as the estimates' are.
- **Time:** these tests are in the slow tier. R2's at p = 10 compute no intervals (a test interval method that
  gives every interval "none", through V7's seam; `../contracts.md`, Test tiers): the estimates don't depend on
  the interval method, and the bootstrap's 1000 refits of 20,000 × 286, each as drawn and again on its distinct
  runs for LOO (twice the 0.46 s per refit as drawn first measured), took about 0.9 s each under load, about
  15 min (0079 items 15, 16). The tests then take about as long as R11's
  bootstrap; the bootstrap's own known answers are the golden report's and PM5's, and R1, R10, and R11 at
  20,000 runs run it as users do.

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `POLY_DEGREE` | 2 | the default degree | the smallest step past the linear model; U5's |
| `POLY_NMIN` | 2 (n_min = 2P) | the factor of P in the default size of level 0, 2·C(d + p, p) of the parsed degree (0079 item 5) | twice the coefficients, as U4 assumes |
| `POLY_ALPHA` | 0.7072 | the default error factor per level | as the linear model's: the points about double per level |
| `POLY_LEVEL` | 2 | the default last level | as the linear model's: about 8P points (G7) |
| `POLY_MIN_RUNS` | 2 (2P runs) | the factor of P in the fewest usable runs for estimates (0079 item 5) | resamples keep about 1.26P distinct runs |
| `POLY_BOOT_TAG` | 2³² + 3 | the spawn key of the polynomial model's bootstrap stream | the next diagnostic tag after the linear model's (`shared.md`) |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| PM1 | The design is convergent with the request's n_min (2P by default), alpha, level, seed, sampler, and space; a space with no varied model parameter, a degree below 1, or a basis other than `total_degree` is refused before building. | The design equals `convergent(...)` bit for bit; degree 0; `basis="hyperbolic_cross"`: refused as later. |
| PM2 | The fit is least squares, by QR, in the orthonormal Legendre terms of total degree ≤ p in unit coordinates, over the usable runs of level L, the terms in the stated order. | R10 at p = 2: the three coefficients within 10⁻¹², the rest below 10⁻¹²; P = C(d + p, p) for d = 1 … 8, p = 1 … 4. |
| PM3 | The relative residual, R², and the LOO error by PRESS, as the linear model's; the relative residual and R² as observations, with no interval (0085). | A fixture of 12 runs in d = 2, p = 2: LOO equal to explicit refits within 10⁻¹². |
| PM4 | The Sobol indices are the first-order and total indices of the fitted polynomial, from its coefficients over V; √E_k per total degree k = 1 … p. | R1 and R10 at p = 2 (Expected answers); a fixture whose coefficients are set by hand. |
| PM5 | Intervals: 1000 resamples from the polynomial model's stream, the same for every estimate, the P coefficients included (in the result, 0041); refits as drawn; LOO on each resample's distinct runs; the 0.5th and 99.5th percentiles; undefined resamples dropped and counted. | Changing `POLY_BOOT_TAG` changes the intervals, not the design (S8); a fixture at 2P runs: the count under the table. |
| PM6 | The per-level table: each level fitted on its usable runs among its first n_l points: usable runs, relative residual, R², LOO, and total indices; "none" below 2P. | R3 at the defaults (the mock report); R5 where level 0 has too few usable runs. |
| PM7 | Fewer than 2P usable runs, or A of rank below P: counts and a note, no estimates; the observations stay. | R5 in a space where 2P − 1 runs are usable; 2P; a fixture whose usable runs take p values along one model parameter. |
| PM8 | y → a·y + b (a a power of 2) maps c_0, the c_α, and √E_k as stated, and leaves the relative residual, R², LOO, the Sobol indices, and the notes unchanged: exactly under a·y; within C5's tolerances under the shift (0048). | R2 at p = 4 with a = 2⁻¹⁰, b = 3. |
| PM9 | Four figures: the fit's two panels with their strips, the Sobol indices with intervals, √E_k on a log axis with values below its lower limit as open markers on the bottom edge (0048), the residual histogram with ⌊√n_u⌋ bins. | R5 at the defaults: each strip's count equals the header's; a constructed spectrum with one value below `SPECTRUM_YMIN`: 1 open marker (0048). |
| PM10 | Progress: the analysis calls `on_progress` with the refits done and the total, and reports A's shape and size before the bootstrap; an interrupt keeps every run and stores no diagnostic result. | A recording callback on R2 at p = 4: 1000 refits counted, monotone; an interrupt raised from the callback, then a rerun: 0 new runs, the same estimates (its counts and approval are the rerun's, 0054). |
| PM11 | Nesting: level L + 1 after level L reuses every run; degree p + 1 after degree p with the same seed reuses the runs of the smaller design. | R3: degree 3, level 1 after degree 2, level 2 makes 300 new runs (U4). |
| PM12 | The known answers at 20,000 runs, and the golden report. | Expected answers. |

## What this spec asks of other documents

- **Reference models (step 11):** the expected answers above, recomputed by `../../checks/polynomial_model.py`; R11's
  and R2's degree-10 projections by quadrature.
- **Architecture (step 9):** the polynomial model's row (no active subspace or shadows, 0039); the basis
  interface beside the sampler's; `on_progress` for the analysis phase, with A's size; the CLI's progress line
  and the MCP server's progress notifications.
- **Data model (step 8):** all P coefficients and their multi-indices in the diagnostic result, each with its
  interval (0041).
