# 0047. State the unit-coordinate maps, the order of a line's points, and how alpha is read from a float

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q5).

## Context

- **`../design/designs.md`** (accepted) gives:
  - the linear map, lo + (hi − lo)·u;
  - that a log range goes through `exp` (bit for bit only on one machine);
  - the unit coordinates in [−1, 1], through the logarithm for a log scale.

  G10 and C21 require an end on a face to be exactly lo or hi, and every point inside the closed ranges.
- **Open:**
  - the log formula;
  - the map between u ∈ [0, 1) and z ∈ [−1, 1];
  - which end of a line is t = 0;
  - how alpha, "read as the decimal it is written as", is read from a Python float.
- **Measured (2026-10-01):**
  - exp(ln lo + (ln hi − ln lo)·u) at u = 1 − 2⁻⁵³ exceeds hi in 13% of random ranges.
  - exp(ln b) ≠ b for 52% of doubles b, so an end needs an explicit assignment.
  - lo + (hi − lo)·1 = hi in all of 2·10⁶ ranges, while ½(lo + hi) + ½(hi − lo)·1 misses hi in 13%.
  - The lines mock report reproduces only when t = 0 is the end reached against the line's direction.

## Decision

We will state in `designs.md`:

1. **The maps.**
   - z = 2u − 1, and u = (z + 1)/2.
   - Linear range: x = lo + (hi − lo)·u.
   - Log range: x = exp(ln lo + (ln hi − ln lo)·u), clamped to [lo, hi].
   - A point on a face of the space has that coordinate set to lo or hi exactly, not computed.
   - Lines are built in z and mapped through u.
2. **The order of a line's points.** t = 0 is the end reached by moving from the anchor against the line's
   direction, so the points run along the direction. A coordinate line runs from lo to hi.
3. **alpha from a float.** A float alpha is read as `Fraction(repr(alpha))`: the shortest decimal that
   round-trips, which is the decimal typed (0.7072 → 7072/10000). The JSON form keeps its text, and the request
   records that decimal string.

## Alternatives considered

- **Leave the formulas to the design generators' build plan,** with G10 and C21 as the requirements. Not
  chosen: golden points and the lines mock depend on the exact formulas, so the spec should name them.
- **t = 0 along the direction:** points against the direction. Not chosen: the lines mock report's figures and
  data cards are drawn the other way, and "along the direction" is the natural reading.
- **Require alpha as a string or `Fraction`** in the Python API: no conversion implied, but awkward in a
  notebook.

## Consequences

- **`../design/designs.md`** (accepted):
  - Unit coordinates and Determinism: Decision 1.
  - Lines: Decision 2.
  - Exact rounding: Decision 3.
  - G10's test adds a log range whose naive end misses hi.
- **`../design/contracts.md`** (accepted): C21's negative control names the case. A log-range map without the
  clamp or the exact end puts a point outside the closed range.
- **`../design/diagnostics/lines.md`** and **`coordinate_lines.md`:** unchanged; their mocks already follow
  Decision 2.
- **`../design/architecture.md`** (step 9): `ema.types` holds alpha as a `Fraction`, built from the JSON text or
  from `repr` of a float.
