# Coordinate lines

**Status:** accepted. **Updated:** 2026-10-01. **Module:** `ema/diagnostics/coordinate_lines.py`. **Depends on:**
`shared.md`; `../designs.md`; records 0012, 0034, 0035, 0036, 0038, 0044, 0048, 0051, 0052.

> The model prediction along one line per varied model parameter, through an anchor, and the spectrum of each
> line (U2). Written from an interview on 2026-09-30 (TODO step 6). Everything not stated here
> follows `shared.md`.

## Summary

| | |
|---|---|
| **User provides** | a model parameter space, n (17), the anchor (nominal), the model prediction |
| **Design** | coordinate lines (`../designs.md`): one line per varied model parameter, n evenly spaced points end to end, through the anchor |
| **Compute** | for each line, its Gram spectrum (the discrete Legendre coefficients on its n points) and the spectrum's decay rate, as observations; no estimates |
| **Plots** | for each line, one PNG: the model prediction along it, and its Gram spectrum |
| **Report** | observations: for each line, its range, the degrees of its spectrum above the floor, and its decay rate; the shared observations; a note per constant line; the figures |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| `space` | model parameter space | required | the ranges varied, and the values held (`../designs.md`) | yes |
| `n` | integer ≥ 7 | 17 | the number of points on each line, end to end | yes |
| `anchor` | mapping of model parameter names to values | `{}` (the nominal point) | the point every line passes through; unnamed model parameters at their nominal values, held ones at their held values (`../designs.md`) | yes |
| `prediction` | model prediction name | the only one | the model prediction analyzed (0022) | no |

- **Which model parameters:** every varied one gets a line, in the model spec's order; there is no separate
  parameter. To leave one out, hold it in the space (0023, 0033). A space with no varied model parameter is
  refused before building.
- **n ≥ 7** (`COORD_MIN_N`), refused below before building: a rate needs 3 degrees in the window, K = ⌊(n − 1)/2⌋
  ≥ 3. Any n ≥ 7 is accepted, even or odd. The default, 17 = 2⁴ + 1, is U2's; reruns at 33 and 65 reuse every
  run (G11). U2 (d = 6, the anchor at the centers): 97 distinct points.
- **No seed:** coordinate lines make no random draws. The request's seed, 0, is recorded (`shared.md`).
- **The anchor and the lines** (`../designs.md`, Coordinate lines): the header's Design row gives the anchor's
  values, and which lines contain it: "all 6 lines share the anchor's run" (n odd, the anchor at the center of
  each range); "lines through the anchor: a, b, e" (the anchor off center along the others' model
  parameters); or "lines through the
  anchor: none (n is even)". Each line's panel marks the anchor's value with a vertical dotted line, whether
  or not it is one of the line's points.
- **An anchor on another point of a line** is refused before building (0051): an anchor equal, bit for bit, to
  a point of a coordinate line along which it is off center (an end at lo or hi, or another grid point), naming
  the model parameter. The analyst gives another anchor, as when a nominal value is outside its range
  (`../designs.md`). So a line along which the anchor is off center shares no point with the others.
- **Nested** in n → 2n − 1 with the same space and anchor (G11): coordinate lines at 33 reuse the 17-point
  lines' runs.

## Computation

Let a line have n points, evenly spaced end to end (`../designs.md`, Lines), at unit coordinates
s_j = −1 + 2j/(n − 1), j = 0 … n − 1, along its model parameter (through its logarithm for a log range), with
values y_j.

**The Gram spectrum:**

- **Gram polynomials** G_0 … G_(n−1) (Gram 1883; also called discrete Chebyshev polynomials): G_k has degree
  k and a positive leading coefficient, and they are orthonormal under the average over the n points:
  (1/n) Σ_j G_k(s_j) G_l(s_j) = δ_kl. G_0 = 1. At low degree they are close to the orthonormal Legendre
  polynomials ψ_k (`../reference_models.md`). The top degrees are small at the points near the ends, beyond
  about |s| = √(1 − (k/n)²) (the saturated region of discrete orthogonal polynomials, Rakhmanov 1996), so they
  respond little to features there: with R7's kink at a = 0.6 and n = 65, the coefficients above degree 56
  fall by up to five decades.
- **Coefficients:** c_k = (1/n) Σ_j y_j G_k(s_j), k = 0 … n − 1. This is an orthogonal transform of the n
  values, like a DFT: y_j = Σ_k c_k G_k(s_j) exactly, c_0 is the line's mean, and Σ_(k≥1) c_k² is its variance
  (ddof 0). It is perfectly conditioned; Runge's instability is in evaluating the interpolant between the
  points, which EMA never does.
- **Computed** by the Lanczos process on the n points with full reorthogonalization, from the start vector of
  ones. Not by the Gram polynomials' three-term recurrence: in doubles it loses orthonormality (10⁻⁸ at
  n = 33, 10³ at n = 65). Lanczos agrees with exact rational arithmetic to 10⁻¹⁶ of the line's range at
  n = 17, 65, and 129 (a scratch script, 2026-09-30).
- **Why Gram:** the coefficients' decay tells a polynomial approximation's convergence along the line: geometric
  for an analytic line, algebraic for a kink or a jump, flat at the level of noise, and zero past the degree
  of a polynomial. It is the same spectrum, in one dimension, as the polynomial model's decay of its
  coefficients (0012). A plain Fourier transform of the mirrored line (DCT-I) can't tell an exactly linear line
  from a kink (both decay like k⁻²), and a sine transform of the detrended line gives an order of smoothness
  (k⁻¹ jump, k⁻² kink, k⁻³ smooth), but not a polynomial's convergence.

**The decay rate**, in decades per degree:

1. **Tail:** T(k) = √(Σ_(j≥k) c_j²), k = 1 … n − 1, the size of the spectrum from degree k up. T(1) is the line's
   standard deviation (ddof 0). The tail smooths over parity zeros: a line even about its center has c_k = 0
   for every odd k.
2. **Window:** degrees 1 … K, K = ⌊(n − 1)/2⌋ (`LINE_RATE_WINDOW`), since the top degrees see only the middle of
   the line.
3. **Floor:** the degrees k ≤ K with T(k) > 10⁻¹⁰ · (max_j y_j − min_j y_j), the line's range
   (`LINE_RATE_FLOOR`; P6). T is nonincreasing, so these are degrees 1 … k*. The floor keeps rounding out of the
   fit: rounding is about 10⁻¹⁶ of |y|, so it stays below the floor unless the line's range is below about
   10⁻⁶ of |y| (the shared observation (max − min)/max|y| shows that case).
4. **Rate:** minus the least-squares slope of log₁₀ T(k) against k over k = 1 … k*, when k* ≥ 3
   (`LINE_RATE_MIN_DEGREES`). With k* < 3 there is no rate, and k* says why: an exactly linear line (R1) has
   k* = 1, a quadratic one (R10 along b) k* = 2, each a polynomial of that degree to 10⁻¹⁰ of its range.

What it gives on the reference models (a scratch script, 2026-09-30; n = 9, 17, 33, 65, 129; in brackets,
k*/K at n = 33; R6a and R6b from one draw of their noise):

| Line, through the nominal point | 9 | 17 | 33 | 65 | 129 |
|---|---|---|---|---|---|
| R7 along c (R11's g), analytic, poles at ±i/2 | 0.155 | 0.196 | 0.209 [16/16] | 0.214 | 0.211 |
| R3 along L, analytic | 0.967 | 0.990 | 0.990 [10/16] | 0.990 | 0.992 |
| R3 along r (log range) | 3.139 | 3.143 | 3.151 [4/16] | 3.153 | 3.157 |
| R2 along x1, sin (entire) | 0.277 | 0.493 | 0.700 [15/16] | 0.692 | 0.693 |
| R7 along a, a kink at 0.6 | 0.264 | 0.181 | 0.110 [16/16] | 0.056 | 0.031 |
| R7 along b, a jump at 0.2 | 0.134 | 0.069 | 0.037 [16/16] | 0.020 | 0.010 |
| R6a along a, noise 0.05 | 0.548 | 0.155 | 0.043 [16/16] | 0.013 | 0.004 |
| R6b along a, noise 10⁻⁸·y | 2.430 | 0.615 | 0.169 [16/16] | 0.050 | 0.013 |
| R1 along a, linear | none | none | none [1/16] | none | none |
| R10 along b, quadratic | none | none | none [2/16] | none | none |

- An analytic line's rate converges as n grows: R7's c line to log₁₀ ρ = log₁₀ φ = 0.2090, where ρ is the
  parameter of the Bernstein ellipse through its poles. A kink, a jump, or noise halves it with each
  refinement n → 2n − 1. At one n the two can be close (at n = 17: 0.196 analytic, 0.181 kink); refining tells
  them apart, and reuses every run (G11).
- **Changes of units** (P6): y → a·y + b, with a > 0, gives c_k → a·c_k for k ≥ 1 and scales the range by a, so
  the degrees above the floor are unchanged, and the rate is, within 10⁻¹² under a·y alone and within
  `RATE_SHIFT_TOL` under the shift (0048). A log range changes nothing: the line is uniform in unit coordinates,
  and the spectrum is in them.

**Observations for each line** (0034), in the model spec's order, one table:

| Observation | Definition |
|---|---|
| Usable | the line's usable runs, "17 of 17" |
| Range | max − min of the line's usable runs, in the model prediction's units: which model parameters move y at the anchor, one at a time |
| Degrees above the floor | "k* of K" |
| Decay rate | as above, in decades per degree; or "none" and why |

**Runs not usable on a line:** a line with any run that isn't usable has no spectrum, no degrees, and no rate
("none: 2 runs not usable"); its range is over its usable runs, and its panel shows the others in the strip
(`shared.md`). The spectrum is defined on the complete evenly spaced line. Considered and not chosen: the
polynomials orthonormal on the usable points (an interior gap moved R7's analytic rate from 0.196 to 0.207), and
the longest evenly spaced segment (one interior gap leaves 8 of 17 points).

**A constant line** (the per-line form of 0035): every usable run on the line gives the same double. Its range
is 0, its degrees 0 of K, its rate "none: constant", and the report has a note for it, after the shared notes:
"y is the same in all 17 usable runs along f: 1." (R8 along f and g; R2 along x3 through the nominal point,
where y = 0 exactly.)

## Uncertainty

OD-12, for coordinate lines: **none**. The decay rate is an observation of the n runs on its line (0034), with
no variability interval, like the point run's numbers. Refinement is the analyst's check: a rerun at 2n − 1
points per line reuses every run (G11), and its rates show whether they converge.

- A diagnostic result with observations only, and no estimates, is valid (0036).
- Considered and not chosen: an interval spanned by the rates on the line and on its nested subline of
  (n + 1)/2 points (no new runs, needs n odd); and one over the even- and odd-indexed sublines.

## Minimum runs and degenerate cases

- **Fewest usable runs:** 1 (`COORD_MIN_RUNS`), for the shared observations; there are no estimates. Each line
  needs all its n ≥ 7 runs usable for a rate (above).
- **All runs failed:** counts by kind and the note; no observations (`shared.md`).
- **Constant** (every usable run of the diagnostic the same double; 0035): the shared note and observations;
  each line's row has its usable count, range 0, and "none: constant"; no per-line notes, since the shared note
  covers them.
- **A constant line,** when others vary: its note (above).
- **k* < 3:** no rate; k* in its column.
- **Runs not usable on a line:** no spectrum or rate for that line (above).
- **The anchor on no line** (n even, or off center): the header says so (Parameters); nothing else changes.
- **An anchor on another point of a line:** refused before building (Parameters, 0051).
- **Figures** (0051): one PNG per varied model parameter in every case, with the same layout. A line's top panel
  shows its usable runs and the strip of the others; its spectrum panel is empty, with the reason, when the line
  has no spectrum (all runs failed or some not usable: "no spectrum: 17 runs not usable"; constant: "no
  spectrum: constant").

## Figures

**`coordinate_lines_<name>.png`,** one per varied model parameter, in the model spec's order, with two panels:

- **Top, the line:**
  - **x axis:** the model parameter, in its units, on a log axis for a log range (`shared.md`).
  - **y axis:** the model prediction, with this line's own limits, so each line's shape shows (R3's r line
    varies by 0.27% of y); the Range column compares the lines.
  - **Points:** one marker per usable run, joined in order along the line.
  - **The anchor:** a vertical dotted line at its value, whether or not it is one of the line's points.
  - **Runs not usable:** × in the strip below the axes, at their values (`shared.md`).
- **Bottom, the spectrum:**
  - **x axis:** the degree k, 1 … n − 1.
  - **y axis:** |c_k| / the line's range, on a log axis, labeled `|c_k| / range`; from 10⁻¹⁷
    (`SPECTRUM_YMIN`) up.
  - **Points:** one marker per degree; any value below the panel's lower limit (`SPECTRUM_YMIN`), whether an
    exact zero (a parity zero of an even or odd line) or rounding, as an open marker on the bottom edge (0048).
  - **The fit:** the line 10^(β − r·k) over k = 1 … k*, labeled "tail fit"; it is fitted to T(k), so it lies on
    or above the markers.
  - **The floor:** 10⁻¹⁰, dashed. **Outside the window:** the degrees above K, shaded.
  - **No spectrum** (runs not usable on the line, or a constant line): the panel is kept, empty, with the reason
    as text ("no spectrum: 2 runs not usable"; "no spectrum: constant"), so every line has the same layout.
- **Title:** the model parameter's name; the numbers are in the table, not on the figure.
- **Data card:** as in `shared.md`; and for the spectrum, each c_k (signed, full doubles), each T(k), K, k*,
  the floor, and the fit's intercept β and rate r.

## Mock report

U2 on R8 (R7 as a command-line program), n = 17, after the interrupted evaluation and its rerun. The numbers
are computed (a scratch script, 2026-09-30; step 11 checks them); the hashes are placeholders.

```markdown
# Coordinate lines: R8, y

| | |
|---|---|
| Model version | R8@2c7a |
| Model prediction | y |
| Space | a [-1, 1]; b [-1, 1]; c [-1, 1]; e [-1, 1]; f [-1, 1]; g [-1, 1] |
| Held | none |
| Design | coordinate lines, n = 17, anchor a = 0, b = 0, c = 0, e = 0, f = 0, g = 0 (all nominal); all 6 lines share the anchor's run |
| Runs | 97: 56 new, 41 reused; 0 failed; 0 missing y; 97 usable |

## Notes

- y is the same in all 17 usable runs along f: 1.
- y is the same in all 17 usable runs along g: 1.

## Observations

| Of the 97 usable runs | y |
|---|---|
| Minimum | 0.2 |
| Maximum | 2 |
| (max - min) / max\|y\| | 0.9 |

| Model parameter | Usable | Range | Degrees above the floor | Decay rate (decades per degree) |
|---|---|---|---|---|
| a | 17 of 17 | 0.4 | 8 of 8 | 0.1811 |
| b | 17 of 17 | 1 | 8 of 8 | 0.06916 |
| c | 17 of 17 | 0.8 | 8 of 8 | 0.1957 |
| e | 17 of 17 | 0.4 | 8 of 8 | 0.1811 |
| f | 17 of 17 | 0 | 0 of 8 | none: constant |
| g | 17 of 17 | 0 | 0 of 8 | none: constant |

Decay rate: minus the least-squares slope of log₁₀ of the Gram spectrum's tail against the degree, over the
degrees whose tail is above 10⁻¹⁰ of the line's range, at most K = 8. Observations of the 17 runs on each line;
no variability intervals.

## Figures

![y along a](coordinate_lines_a.png) ![y along b](coordinate_lines_b.png) ![y along c](coordinate_lines_c.png)
![y along e](coordinate_lines_e.png) ![y along f](coordinate_lines_f.png) ![y along g](coordinate_lines_g.png)

y along each model parameter through the anchor (dotted), and the line's Gram spectrum, |c_k| / range, with
the tail fit and the floor of 10⁻¹⁰. Data cards: `coordinate_lines_a.json`, `coordinate_lines_b.json`,
`coordinate_lines_c.json`, `coordinate_lines_e.json`, `coordinate_lines_f.json`, `coordinate_lines_g.json`.

## Provenance

EMA 2.0.0; numpy 2.3.1, scipy 1.16.0, matplotlib 3.10.0; model version R8@2c7a; request: coordinate lines,
space as above, n = 17, anchor {}, prediction y, seed 0; runs: 97; approvals: 0a17 (1 new run, the test
run), 1c9e (96 new runs; stopped after 40), 7d03 (56 new runs).
```

At n = 17 the kink along a (0.1811) and the analytic line along c (0.1957) are close. A rerun at n = 33 reuses
the 97 runs and makes 96 new ones; its rates are 0.1103 (a, e), 0.0375 (b), and 0.2088 (c): the kink and the
jump halve, and the analytic line moves toward log₁₀ φ = 0.2090.

## Expected answers

Through the nominal point unless stated. "Exact rational arithmetic" is an independent computation of the
Gram coefficients from the runs' doubles, in Python's `fractions` with the monic three-term recurrence
(β_k = k²(n² − k²)/((n − 1)²(4k² − 1)) on s_j), then the rate in doubles; it agreed with Lanczos to 10⁻¹⁶ of the
range (scratch script, 2026-09-30). Step 11 recomputes every value with it.

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| R7 and R8, n = 17 | rate along a, b, c, e | 0.1811, 0.06916, 0.1957, 0.1811 | 10⁻⁶ | exact rational arithmetic |
| R7 and R8, n = 33 | rate along a, b, c, e | 0.1103, 0.0375, 0.2088, 0.1103 | 10⁻⁶ | exact rational arithmetic |
| R7 along c (R11's g), n = 33, 65, 129 | rate | log₁₀ φ = 0.2090 | 0.01 | analytic: the Bernstein ellipse through the poles ±i/2 (computed: 0.2088, 0.2136, 0.2112) |
| R7 along a and b, n = 17 → 33 → 65 → 129 | each rate over the one before | 0.61, 0.51, 0.55 (a); 0.54, 0.52, 0.52 (b) | within [0.45, 0.65] | brute force (scratch script) |
| R7 along c, n = 17 → 33 → 65 → 129 | each rate over the one before | 1.07, 1.02, 0.99 | within [0.95, 1.1] | brute force |
| R8 along f and g | notes; rate | one note each; none: constant | exact | by construction |
| R8, n = 17 | the report | the mock report above | golden report (`shared.md`: structure, and numbers within one unit in the 4th digit) and data cards | this spec |
| R1, every line (k on a log range) | k*; rate | 1; none | exact | analytic: linear in unit coordinates |
| R10 along a, b, c, e | k* | 1, 2, 0, 0 (c and e constant: notes) | exact | analytic |
| R2 along x3 | note | "y is the same in all 17 usable runs along x3: 0" | exact | analytic (sin 0 = 0) |
| R3, n = 17 | rate along each line | from exact rational arithmetic (step 11) | 10⁻⁶ | exact rational arithmetic |
| R4a | notes; each line | the shared "constant" note only; none: constant | exact | trivial |
| R4b | each line | a rate with k* ≥ 3; no note | exact | 0035 |
| R5, prediction z, n = 17 | line along b | 15 of 17 usable (b = 0.875 and 1 missing); none: 2 runs not usable | exact | by construction |
| R2, y → 2⁻¹⁰·y + 3 | rates; k*; notes; ranges | rates within `RATE_SHIFT_TOL` = 10⁻⁵ of the unscaled; k* and notes identical; ranges × 2⁻¹⁰ | as stated | P6 |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `LINE_RATE_FLOOR` | 10⁻¹⁰ | the tail T(k) is fitted while above this fraction of the line's range | ten decades to fit; keeps rounding out unless the line's range is below about 10⁻⁶ of \|y\|; at 10⁻¹³, R3's r line lets rounding in |
| `LINE_RATE_WINDOW` | ½ | the fit uses degrees 1 … ⌊(n − 1)/2⌋ | analytic lines converge (0.196, 0.209, 0.214), and kinks halve with each refinement; with every degree, R7's analytic line doesn't converge (0.246, 0.255, 0.225) |
| `LINE_RATE_MIN_DEGREES` | 3 | the fewest degrees a rate is fitted to | a slope from at least 3 points |
| `COORD_N` | 17 | the default number of points per line | U2's; 2⁴ + 1, so reruns at 33 and 65 reuse every run |
| `COORD_MIN_N` | 7 | the smallest n accepted | K = ⌊(n − 1)/2⌋ ≥ `LINE_RATE_MIN_DEGREES` |
| `SPECTRUM_YMIN` | 10⁻¹⁷ | the spectrum panel's lower y limit; a value below it is an open marker on the bottom edge (0048) | below double rounding of \|c_k\| / range for a line at the scale of its values |
| `RATE_SHIFT_TOL` | 10⁻⁵ | how far a decay rate may move under y → a·y + b; under a·y alone, 10⁻¹² (`UNITS_LOG_TOL`, `../contracts.md`) | where a line's tail reaches the floor before the window ends, a shift's lost bits are a large share of the smallest tail values: the worst change measured on R2's and R7's lines (n = 17 to 65) was 1.2·10⁻⁶ (0048) |
| `COORD_MIN_RUNS` | 1 | the fewest usable runs for a diagnostic result with observations | the shared observations need one; there are no estimates |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| CL1 | The design is coordinate lines with the request's n, anchor, and space; n < 7, a space with no varied model parameter, or an anchor equal to a point of a line along which it is off center (0051) is refused before building. | The design equals `coordinate_lines(...)` bit for bit; n = 6: refused; a space holding every model parameter: refused; n = 17 with the anchor at b's lo: refused, naming b. |
| CL2 | Each line's Gram coefficients are orthonormal-basis coefficients on its n points: y is recovered, c_0 is the mean, Σ_(k≥1) c_k² is the variance (ddof 0), and they agree with exact rational arithmetic. | R7's lines at n = 17, 65, 129: agreement within 10⁻¹⁴ of the line's range; (1/n)GᵀG = I within 10⁻¹³. |
| CL3 | The decay rate: the tail over degrees 1 … k*, k* ≤ ⌊(n − 1)/2⌋, above 10⁻¹⁰ of the line's range; minus the least-squares slope of log₁₀ T(k); none when k* < 3. | A fixture y = Σ_k 10⁻ᵏ G_k at n = 33: rate 1 within 10⁻⁶ (0048); R1: k* = 1, none; R10 along b: k* = 2. |
| CL4 | One row per varied model parameter, in the model spec's order: usable, range, k* of K, rate. | R8 at n = 17 (the mock report). |
| CL5 | A line with any run not usable has no spectrum, k*, or rate; its range is over its usable runs. | R5, z, along b. |
| CL6 | A constant line: range 0, 0 of K, "none: constant", and a note; a constant diagnostic result: the shared note only. | R8 along f and g; R10 along c and e; R4a. |
| CL7 | The Design row says which lines contain the anchor. | 6 model parameters: n = 17, centered: "all 6 lines share the anchor's run"; the anchor off center in b: "lines through the anchor: a, c, e, f, g"; n = 16: "none (n is even)". |
| CL8 | y → a·y + b (a a power of 2) leaves the rates within `RATE_SHIFT_TOL` = 10⁻⁵ under the shift, 10⁻¹² under a·y alone (0048), and k* and the notes unchanged, and scales the ranges by a. | R2 with a = 2⁻¹⁰, b = 3. |
| CL9 | One PNG per varied model parameter, with the line and its spectrum; the data card's c_k equal the result's; a line with no spectrum keeps its empty panel, with the reason. | R8 at n = 17: 6 PNGs, 2 with "no spectrum: constant"; R5's z: the × strip's count equals the header's; a constructed spectrum with one value below `SPECTRUM_YMIN`: 1 open marker on the bottom edge (0048). |
| CL10 | The known answers and the golden report. | Expected answers. |

## Tests it implies

- `shared.md`'s S4 has no table to check: coordinate lines have no Estimates section.
- The exact-rational computation of "Expected answers" is a test helper (about 30 lines), not part of `ema`.

## What this spec asks of other documents

- **Architecture (step 9):** `fourier.py` becomes the Gram spectrum (`gram.py`); the diagnostics table's
  coordinate lines row.
- **Reference models (step 11):** step 11 recomputes the rates in "Expected answers".
