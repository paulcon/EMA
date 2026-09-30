# 0038. Report each coordinate line's Gram spectrum, and its decay rate as an observation

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 6, coordinate lines' spec; its
"Decide:" line on the per-line estimate; OD-12 for coordinate lines, recorded with the others at the end of
step 6).

## Context

- **U2** (accepted) says coordinate lines' report has "numbers: one estimate per line with its variability
  interval (for example, the spectrum's decay rate; which one is for the coordinate lines spec, step 6)".
- **`designs.md`** (accepted) says lines have evenly spaced points because "Evenly spaced points are what the
  lines' Fourier spectra need."
- **The transform.** In coordinate lines' interview (2026-09-30), three spectra of a line's n evenly spaced
  values were computed on the reference models:
  - a plain Fourier transform of the mirrored line (DCT-I), which can't tell an exactly linear line from a
    kink (both decay like k⁻²);
  - a sine transform of the detrended line, whose decay exponent is about 1 for a jump, 2 for a kink, and 3
    or more for a smooth line;
  - the Gram spectrum, the coefficients in the polynomials orthonormal on the n points (discrete Legendre),
    whose decay is geometric for an analytic line, algebraic for a kink or jump, flat for noise, and zero
    past a polynomial's degree: the same spectrum, in one dimension, as the polynomial model's decay of its
    coefficients (0012).

  The owner chose the Gram spectrum, with its decay rate in decades per degree as the per-line number.
- **The interval.** A line is deterministic, so resampling it means nothing; what can change is its
  resolution. Offered an interval spanned by the rates on the line and on its nested subline of (n + 1)/2
  points, the owner chose no interval: the rate is an observation (0034), and refinement is the analyst's
  check, a rerun at 2n − 1 points that reuses every run (G11). A result with observations only is valid
  (0036).

## Decision

We will report, for each coordinate line, its Gram spectrum (a figure) and its decay rate (an observation, with
no variability interval), as `../design/diagnostics/coordinate_lines.md` defines them.

- **U2's "What they get,"** its numbers bullet, reads: "numbers: for each line, its range, the degrees of its
  Gram spectrum above a floor, and the spectrum's decay rate, as observations, with no variability interval
  (0038);".
- **`designs.md`'s** sentence reads: "Evenly spaced points are what the lines' spectra need (Gram polynomials,
  `diagnostics/coordinate_lines.md`)."
- **OD-12, for coordinate lines:** none (the rate is an observation). Recorded with the other diagnostics' at
  the end of step 6.
- **TODO step 6's "Decide:" line** on the per-line estimate in coordinate lines' report is settled here.

## Alternatives considered

- **DCT-I (v1's note: "Fourier transform"):** the simplest; can't separate a linear line from a kink.
- **The detrended sine transform's exponent:** an order of smoothness, stable under refinement; says nothing of
  a polynomial approximation's convergence along the line.
- **A subline interval:** no new runs, and its direction separates an analytic line (its rate rises toward a
  limit) from a kink (it halves); needs n odd, and an interval with the estimate always at one end.
- **The rates on the even- and odd-indexed sublines:** more spread; the odd subline isn't end to end.

## Consequences

- **`../design/use_cases.md`** (accepted): U2's numbers bullet, as above.
- **`../design/designs.md`** (accepted): the sentence above.
- **`../design/reference_models.md`** (draft): R7's "The expected spectra along each line depend on the
  transform the coordinate lines spec chooses" names the Gram spectrum.
- **`../design/architecture.md`** (draft, step 9): `fourier.py` becomes the Gram spectrum; the coordinate lines
  row.
- **`../../TODO.md`:** step 6's "Decide:" line on coordinate lines is settled.
- **The lines diagnostic** (the next spec) decides whether random and given lines use the same spectrum and
  rate.
- **Good:** one spectrum for lines and the polynomial model; no threshold on smoothness (P2). **Bad:** at one n,
  a kink and an analytic line can have close rates (R7 at n = 17: 0.181 and 0.196); only a rerun at 2n − 1
  tells them apart, and the report shows no interval that says so.
