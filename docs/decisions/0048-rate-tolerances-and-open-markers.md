# 0048. Loosen decay-rate tolerances to what rounding allows, and draw values below a spectrum's axis as open markers

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q6).

## Context

- **Rates under a shift.** CL8 and LN7 say y → a·y + b leaves the decay rates "within 10⁻⁹". C5 holds a
  dimensionless number to 10⁻⁹ (`UNITS_RTOL`) under y + b. Measured on R2's and R7's lines (Lanczos with full
  reorthogonalization, 2026-10-01, 36 cases):
  - k* never changed.
  - Under 2⁻¹⁰·y + 3, rates changed by at most 6·10⁻¹³ at n = 17, but by up to 6.7·10⁻⁷ at n = 33 and
    1.2·10⁻⁶ at n = 65.
  - Under y + 3·max|y|, they changed by up to 1.6·10⁻⁹.

  The large changes come where a line's tail reaches the 10⁻¹⁰ floor before the window ends (R2's x₁): the
  bits a shift loses are then a large share of the smallest tail values.
- **CL3's fixture** (y = Σ 10⁻ᵏ G_k at n = 33, "rate 1 within 10⁻⁹"). It reaches the floor at k* = 10. Its
  error is 1.1·10⁻⁸ or 7·10⁻¹⁰, depending on the Gram basis's details.
- **Open markers.** Coordinate lines draw "an exact zero (a parity zero)" as an open marker on the bottom
  edge of an axis starting at `SPECTRUM_YMIN` = 10⁻¹⁷. The polynomial model draws a √E_k "below 10⁻¹⁷ of the
  largest" that way, with R11's odd degrees and R10's degree 3 as examples, and PM9 tests "R11 at p = 10: 5
  open markers". But:
  - A Lanczos basis gives parity zeros of 3·10⁻¹⁸ to 4·10⁻¹⁷, not exact zeros.
  - R11's odd √E_k from a 20,000-run fit are about 10⁻⁴ of the largest (Monte Carlo error).
  - R10's degree 3 is 1.7·10⁻¹⁶.

  So PM9's test can't pass.
- **SC7, LM7, and PM8** say "unchanged" under a·y + b, while C5 gives tolerances under a shift.

## Decision

We will:

1. **Hold decay rates under a shift to 10⁻⁵** (`RATE_SHIFT_TOL`), with k* unchanged.
   - Under a power-of-2 scaling alone they stay within 10⁻¹² (`UNITS_LOG_TOL`).
   - This applies to CL8, LN7, and C5's rule for a number computed through a logarithm.
   - The worst measured change is 1.2·10⁻⁶.
2. **Keep CL3's fixture** (y = Σ 10⁻ᵏ G_k at n = 33, rate 1) and compare its rate within 10⁻⁶.
3. **Draw as an open marker on the bottom edge any value below a spectrum panel's lower limit**
   (`SPECTRUM_YMIN`, 10⁻¹⁷ of the panel's scale), whether an exact zero or rounding. One rule serves coordinate
   lines, lines, and the polynomial model. The figure tests use a constructed spectrum with one value below
   the limit, not a fitted model.
4. **Reword SC7, LM7, and PM8** from "unchanged" to "exactly under a·y; within C5's tolerances under the
   shift".

## Alternatives considered

- **Keep 10⁻⁹ and test at n = 17,** where it holds (6·10⁻¹³). Not chosen: the requirement would say nothing at
  n = 33 or 65, where it fails.
- **Exempt rates under a shift,** as C6 does near the floor. Not chosen: a tolerance still catches a wrong
  rate.
- **A fixture y = Σ 2⁻ᵏ G_k within 10⁻⁹** (error 3·10⁻¹³): not chosen; the owner kept the rate-1 fixture
  with a looser tolerance.
- **Open markers for exact zeros only:** not chosen; rounding-level values below the axis would be clipped
  with no mark.

## Consequences

- **`../design/diagnostics/coordinate_lines.md`** (accepted):
  - CL8: "within `RATE_SHIFT_TOL` = 10⁻⁵ under the shift, 10⁻¹² under a·y alone".
  - CL3's test: "rate 1 within 10⁻⁶".
  - Figure: the open-marker rule as Decision 3.
  - A constants row for `RATE_SHIFT_TOL`.
- **`../design/diagnostics/lines.md`** (accepted): LN7 as CL8; its spectrum figure follows Decision 3.
- **`../design/diagnostics/polynomial_model.md`** (accepted): the open-marker rule as Decision 3, without the
  R11 and R10 examples; PM9's test uses a constructed spectrum; PM8 as Decision 4.
- **`../design/diagnostics/scatter.md`, `linear_model.md`** (accepted): SC7 and LM7 as Decision 4.
- **`../design/contracts.md`** (accepted): C5's rule for numbers computed through a logarithm adds
  `RATE_SHIFT_TOL` under the shift. `UNITS_RTOL`'s "why" column no longer says "as CL8 and LN7".
