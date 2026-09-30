# Reference models

**Status:** draft. **Updated:** 2026-09-30. **Depends on:** records 0009, 0021, 0022, 0024, 0027, 0030.

> The models v2 is developed and verified against, each with the answers a correct diagnostic must give. With
> these, "done" means "matches what was worked out independently", not "the tests Claude wrote pass". Each
> diagnostic spec's "Expected answers" table refers to these ids.
>
> The list below was settled in an interview on 2026-09-30, at the start of TODO step 6, so the diagnostic
> specs could use it. Each diagnostic spec adds the expected answers it needs; step 11 collects them here,
> checks each against an independent source, and accepts this file. How to add a model: `../notes/adding_a_reference_model.md`. Where v1 has the same function
> (`../EMA-v1`, `src/ema/testfunctions/library.py`), v1's `truth.py` is one independent source.

| Id | Model | Interface | d | Structure it has | Why it's here | Source of the expected answers |
|---|---|---|---|---|---|---|
| R1 | linear, with a log range | Python | 4 | exactly linear in unit coordinates; one model parameter with no effect | the linear model's exact coefficients; a deterministic point run | analytic |
| R2 | Ishigami | Python | 3 | interactions; one model parameter with no first-order effect | the standard sensitivity test (U1, U4) | analytic Sobol indices |
| R3 | borehole, with a log range | Python | 8 | a few important model parameters; smooth; units | a realistic engineering formula | brute force |
| R4a, R4b | constant; constant with a 10⁻¹² wiggle | Python | 3 | none | no data, no estimates (P6) | trivial |
| R5 | fails in known regions | Python | 2 | errors, timeouts, and one missing model prediction, in known regions | failed runs (U3) | by construction |
| R6a, R6b | R1 with noise, declared deterministic | Python | 4 | known noise: visible, and at a solver tolerance | the point run's measured variation (U7, P7) | by construction |
| R7 | a kink and a jump at known places | Python | 4 | one feature per coordinate line; a diagonal kink | nonsmooth features (U2) | by construction |
| R8 | R7 as a command-line program | command line | 6 | R7's, and two model parameters with no effect | the input-deck path (U2) | R7's |
| R9 | a real simulator | command line | | | later (below) | |
| R10 | a sparse Legendre polynomial | Python | 4 | exact coefficients, with one interaction | exact recovery of a polynomial (U4) | analytic |
| R11 | a product of Runge-type functions | Python | 2 | analytic, with a known rate of coefficient decay | the decay of the polynomial model's coefficients (0012) | Gauss–Legendre quadrature |

- **Nominal values** are at the centers of the ranges (the geometric center for a log range), so coordinate
  lines through the nominal point share it when n is odd (`designs.md`, G12). A test that needs the anchor off
  center gives it.
- **Model predictions:** one, named `y`, unless a model says otherwise. Units are empty (dimensionless) except
  R3's.
- **The shared rules** (a constant model prediction, 0035; the minimum runs) are in `diagnostics/shared.md`;
  R4a and R4b test them.
- **Size:** within the budget of 1,000 source lines for reference models (`scope.md`).

## The models

ψₖ is the orthonormal Legendre polynomial of degree k on [−1, 1], under the uniform measure: ψ₁(u) = √3·u,
ψ₂(u) = √5·(3u² − 1)/2.

### R1 Linear, with a log range

f = 5 + 3a − b + 0·c + 2·log₁₀(k)

| Model parameter | Range | Scale | Nominal |
|---|---|---|---|
| a | [0, 2] | linear | 1 |
| b | [−1, 1] | linear | 0 |
| c | [10, 20] | linear | 15 |
| k | [1, 100] | log | 10 |

- In unit coordinates, f = 10 + 3u_a − u_b + 0·u_c + 2u_k exactly, so the linear model's coefficients are 3,
  −1, 0, 2, with intercept 10, only when k's log scale is honored (0024). c has no effect.
- R1(nominal) = 10. v1's `linear` is R1 without k.

### R2 Ishigami

f = sin x₁ + 7 sin² x₂ + 0.1 x₃⁴ sin x₁ (Ishigami and Homma, 1990), with x₁, x₂, x₃ in [−π, π], linear,
nominal 0.

| | first-order | total |
|---|---|---|
| x₁ | 0.3139 | 0.5576 |
| x₂ | 0.4424 | 0.4424 |
| x₃ | 0 | 0.2437 |

Analytic, under the uniform distribution on the space (checked 2026-09-30 from the closed-form variances).

### R3 Borehole, with a log range

The water flow through a borehole, in m³/yr (Harper and Gupta, 1983), v1's `borehole`, with v1's ranges and
units:

| Model parameter | Range | Scale | Units | Nominal |
|---|---|---|---|---|
| rw | [0.05, 0.15] | linear | m | 0.1 |
| r | [100, 50000] | log | m | 2236.06797749979 |
| Tu | [63070, 115600] | linear | m²/yr | 89335 |
| Hu | [990, 1110] | linear | m | 1050 |
| Tl | [63.1, 116] | linear | m²/yr | 89.55 |
| Hl | [700, 820] | linear | m | 760 |
| L | [1120, 1680] | linear | m | 1400 |
| Kw | [9855, 12045] | linear | m/yr | 10950 |

- r spans 2.7 decades, so it has a log range, with its nominal at the geometric center, √(100 · 50000).
- A design uniform in log r puts a different distribution on r than the literature's (uniform in r), so the
  literature's Sobol indices don't apply: R3's answers come from brute force, by v1's `truth.py` method, under
  the uniform distribution in unit coordinates.

### R4a, R4b Constant

- **R4a:** f = 2.5.
- **R4b:** f = 2.5 + 10⁻¹²·sin(40·(a + b + c)), a constant plus a deterministic 10⁻¹² wiggle.

a, b, c in [−1, 1], linear, nominal 0. On R4a, every diagnostic gives counts and a note, and no estimates
(the point run: one distinct value, and no note). R4b is not constant (0035): every diagnostic gives
estimates of its wiggle, and a relative spread of about 8·10⁻¹³ (`diagnostics/shared.md`).

### R5 Fails in known regions

Two model predictions: y = a + b², and z = a − b; a, b in [−1, 1], linear, nominal 0; `timeout_s` = 0.2.

| Region | What the function does | Run |
|---|---|---|
| a + b > 1 | raises `ValueError("no convergence")` | failed, `error` (1/8 of the space) |
| a < −0.8 and b < −0.8 | sleeps 5 s | failed, `timeout` (1/100 of the space) |
| b > 0.8, elsewhere | returns y, and z as NaN | ok: y usable, z missing with its reason (M4, 0022) |
| elsewhere | returns y and z | ok |

- The error region depends on a and b together: each one-model-parameter strip shows its projection, and a
  later two-model-parameter plot its shape (0037).
- The timeouts cost 0.2 s each, so tests that reach them are in the slow tier.
- Expected: exactly the points in each region fail, by kind; each diagnostic's estimates equal those computed
  from the usable runs alone.

### R6a, R6b R1 with noise, declared deterministic

- **R6a:** f = R1 + 0.05·ε.
- **R6b:** f = R1·(1 + 10⁻⁸·ε), noise at a solver tolerance, like U7's heat solver.

ε is standard normal, from a numpy `Generator` seeded from fresh entropy, like a real noisy model. (Seeded 0
when the child starts, replicate 1 in a fresh child would repeat the draw of a replicate 0 made in an earlier
one, and hide the noise; point run interview, 2026-09-30.) Tests on R6 check sampling bounds, never golden
bytes. Model parameters, space, and nominal values as R1. Both specs are deterministic: `noisy: true` is
refused (0021, M18).

Expected, for the point run at the nominal point with k repeats: R6a's standard deviation ≈ 0.05, and R6b's
≈ 10⁻⁷ (= 10⁻⁸·R1(nominal)), each within a sampling bound (`diagnostics/point_run.md`); on R1, no variation
and no note.

### R7 A kink and a jump at known places

f = max(0, a + e − 0.6) + 1[b > 0.2] + 1/(1 + 4c²); a, b, c, e in [−1, 1], linear, nominal 0.

| Through the nominal point, along | Feature |
|---|---|
| a (e = 0) | a kink at a = 0.6 |
| b | a jump of height 1 at b = 0.2 |
| c | none: analytic, with poles at c = ±i/2 |
| e (a = 0) | a kink at e = 0.6 |

- **Given lines:** the line through the nominal point with direction (a, e) = (1, 1) crosses the kink at
  a = e = 0.3. The line through a = e = 0.3 with direction (1, −1) lies on the kink, so f is constant along it
  (to rounding).
- **Off the grids:** 0.6 and 0.2 are not multiples of 1/8, 1/16, or 1/32, so no point of a coordinate line
  with n = 17, 33, or 65 falls on a feature.
- The expected spectra along each line are Gram spectra (0038); their decay rates are in
  `diagnostics/coordinate_lines.md`, "Expected answers".

### R8 R7 as a command-line program

y = R7(a, b, c, e) + 0·f + 0·g; six model parameters in [−1, 1], linear, nominal 0, so U2's coordinate lines
with n = 17 have 97 distinct points.

- **Command:** `[<python>, "r8.py", "x.in"]`, with the interpreter's resolved path recorded (M19).
- **Input deck:** `x.in` from `x.in.template` (`a = $a`, one line per model parameter).
- **Output parser:** regex on `out.txt`, `y = (\S+)` (0027).
- **Shared file:** `table.dat`, holding R7's constants (0.6 and 0.2), stored once, read-only, and linked into
  each run directory (0030).
- **Expected:** R7's answers; along f and g, constant lines (counts and a note, no estimate).

### R9 A real simulator: later

Not in v2.0's reference models: it needs a third-party install (staged steps for the owner), and has no
analytic answers. Later, one of SWMM, MODFLOW, or Cantera could be a guide example, with v1 at the same seed as
the source of numbers: an install plan, about 50 lines of model spec and parser, and golden reports. R8
already exercises the command-line path.

### R10 A sparse Legendre polynomial

f = 2·ψ₁(a) + 0.5·ψ₂(b) + 1.5·ψ₁(a)·ψ₁(c); a, b, c, e in [−1, 1], linear, nominal 0; e has no effect.

| | coefficient² | first-order | total |
|---|---|---|---|
| a | 4 | 0.6154 | 0.9615 |
| b | 0.25 | 0.0385 | 0.0385 |
| c | | 0 | 0.3462 |
| e | | 0 | 0 |

- The variance is 4 + 0.25 + 2.25 = 6.5; the a·c term's 2.25 counts toward the totals of a and c.
- A polynomial model of degree 2 or more recovers the three coefficients exactly, and zeros elsewhere.
- v1's `legendre_sparse` is R10 without the a·c term.

### R11 A product of Runge-type functions

f = g(a)·g(b), g(u) = 1/(1 + 4u²); a, b in [−1, 1], linear, nominal 0.

- g's poles are at ±i/2, so its orthonormal Legendre coefficients c_k (k even; zero for odd k) decay
  geometrically: c_k / c_(k+2) → −φ², φ = (1 + √5)/2 (the Bernstein ellipse through the poles). By quadrature:
  c₀ = 0.5536, c₂ = −0.2446, c₄ = 0.09474, c₆ = −0.03637; the ratio is −2.58 at k = 2 and −2.617 at k = 18.
- f's coefficients are c_j·c_k, so the energy at each total degree, and the Sobol indices, are exact from the
  1-D coefficients, computed by Gauss–Legendre quadrature.
- Along a coordinate line through the nominal point, f is g(u)·g(0) = g(u): the smooth line with a known
  analytic strip, for coordinate lines and lines.

## Expected answers

> Per model, the quantities the diagnostics in v2.0 must reproduce, with tolerances and sources. Each
> diagnostic spec's "Expected answers" table lists its own; step 11 gathers them here, and checks each against
> an independent source.

<…>
