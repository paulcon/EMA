# 0058. Drop the kink-line known answer, and set two tolerances from step 11's checks

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (TODO step 11, reference models).

## Context

Step 11 recomputed every expected answer in the six diagnostic specs with separate scripts
(`../checks/`, written from the specs). Plain errors were corrected in place (0052). Three findings change an
accepted spec's expected answers beyond a plain error:

- **R7's given line along the kink** (`../design/diagnostics/lines.md`: through a = e = 0.3, direction
  (a, e) = (1, −1), n = 17) is expected to be exactly constant: the "constant line" note and no rate. It is,
  only if the anchor's 0.3 becomes exactly 0.3 in unit coordinates. `../design/designs.md` gives the map from
  unit coordinates to values (0047), not the way back. The usual inverse, 2(x − lo)/(hi − lo) − 1, gives
  0.30000000000000004; then a + e − 0.6 reaches 2⁻⁵² on some points, y takes the values 1 and 1 + 2⁻⁵², and by
  0035 the line isn't constant: it gets a rate of 0.029 from rounding. The form (2x − (lo + hi))/(hi − lo) gives
  0.3, but brings a value back through x → z → x less often (8% of random values miss, against none).
  The row was LN5's test of "a constant line has a note" when other lines vary. As written it had one line, so
  it tested a constant diagnostic result (the shared note only), not a constant line among others.
- **R3's coordinate-line rates at n = 17** (`../design/diagnostics/coordinate_lines.md`) were left to step 11
  with a tolerance of 10⁻⁶ before they were computed. Along r, y varies by only 10⁻³ of itself, so rounding is a
  large share of the spectrum's small tail values:
  - a Lanczos implementation in doubles differs from exact rational arithmetic by up to 5.5·10⁻⁶, and an
    orthonormal basis from QR by 2.0·10⁻⁵;
  - y may differ in its last bit between machines (the model's `log` and the arithmetic around it; P4
    promises the same result only for the same runs). One ulp in each y moves the exact rate by up to
    7.5·10⁻⁵ with the worst signs, and two ulps by 1.5·10⁻⁴;
  - along the other lines one ulp moves the rate by at most 4.1·10⁻⁶ (Tu), and k* never moves.
- **R11's relative residual and LOO error at p = 10** (`../design/diagnostics/polynomial_model.md`): by the spec's
  own rule (|mean − expected| + 5 standard deviations over seeds 1–100), the tolerance recomputes as 9.4·10⁻⁴
  and 9.6·10⁻⁴, not 8.2·10⁻⁴: 17% above. Seed 0 passes either way (0.01646 and 0.01659 against 0.01672). A
  standard deviation estimated from 100 designs is itself uncertain by about 7%, so step 11 kept every
  recomputed tolerance within 15% of the spec's, as scatter's check does; this is the only one outside it.

## Decision

We will:

1. **Drop R7's kink-line row** from `lines.md`'s Expected answers, and the sentence on it in its "Degenerate
   cases", leaving `designs.md`'s maps unchanged. LN5's constant line is tested on R10 with two given lines
   through the nominal point: line 0 with direction (a, e) = (1, 1), along which y is linear (k* = 1, no rate),
   and line 1 along e, which has no effect, so y = −√5/4 on all of it, whatever the inverse map. The expected
   answer: one note, "y is the same in all 17 usable runs along line 1: -0.559." (written as S3 writes
   numbers), and "none: constant" for line 1 only. `../design/reference_models.md` drops R7's sentence about
   the kink line.
2. **Give R3's coordinate-line rates a tolerance of 2·10⁻⁴:** two ulps at the worst signs, and Lanczos's
   error; k* exact.
3. **Give R11's relative residual and LOO error a tolerance of 9.6·10⁻⁴,** by the spec's rule.

## Alternatives considered

- **Loosen the kink-line answer:** either the constant note, or a rate with a relative spread under 10⁻¹⁵.
  Keeps a test of rounding-level variation in lines, but an answer with two outcomes tests little that R4b
  doesn't.
- **Pin the inverse map in `designs.md`** (z = (2x − (lo + hi))/(hi − lo), and a coordinate whose direction
  component is 0 keeps the anchor's value): one more rule in an accepted spec, chiefly for this test.
- **R3 at 10⁻⁵, with the test computing the exact answer from EMA's own stored runs:** removes the machine's
  last bits, but leaves Lanczos's 5.5·10⁻⁶ under a margin of 2.
- **R3 at 10⁻⁴:** covers one ulp (7.5·10⁻⁵ and Lanczos's 5.5·10⁻⁶) with a margin of only 1.25.
- **2·10⁻⁴ along r only, 10⁻⁵ elsewhere:** tighter where it can be, but two tolerances in one row; k* exact
  guards every line.

## Consequences

- **`../design/diagnostics/lines.md`:** the kink-line row replaced by R10's two given lines; the "Degenerate
  cases" sentence, LN5's test, and the step 11 ask follow.
- **`../design/diagnostics/coordinate_lines.md`:** the R3 row's tolerance 2·10⁻⁴.
- **`../design/diagnostics/polynomial_model.md`:** the R11 row's tolerance 9.6·10⁻⁴ (both).
- **`../design/reference_models.md`:** R7's "Given lines" keeps the (1, 1) line only.
- **`../checks/`:** `gram_rates.py` checks R10's two lines, and R3's rates by Lanczos and by QR against exact,
  with the effect of one and two ulps in y at the worst signs; `truths.py` no longer checks the kink line.
