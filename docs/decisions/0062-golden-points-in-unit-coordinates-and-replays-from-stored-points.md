# 0062. Compare golden points across machines in unit coordinates, replay from the stored points, and settle five details for step 01

**Date:** 2026-10-01. **Status:** accepted; item 2 amended, and item 5's rounding refined, by 0063. **Resolves:** none ("Before the first line of code", `TODO.md`).

## Context

A second round of three independent reviews checked the fixes from the consistency check and record 0061's
application (`../notes/consistency_review_2026-10-01_before_code.md`). Their plain errors are corrected in place
(0052). Two findings show that 0061 itself is wrong in two places, and five leave a detail that build step 01
would otherwise decide:

- **Golden points "within 1 ulp" can't hold** (0061 item 3). A log-range point is exp(ln lo + (ln hi − ln
  lo)·u), and `log` can differ in its last bit between machines too. One ulp in ln hi moves a point of [10⁹,
  10¹²] by up to 64 of its own ulps (recomputed by two reviewers). Random lines' points, clipped along their
  directions, got no promise at all, and "ulp" was never said to be measured against what.
- **A replay that stops on a point mismatch** (0061 item 5) makes U8 fail where it matters: on a colleague's
  machine, any result over a log range or random lines would stop with an error, and after an EMA release that
  bumps a generator's version every older result would be refused. U8 expects a "Differs" report instead.
- **Another sampler version:** 0061 refuses an identity of another generator version, but says nothing of the
  sampler's version, which is part of the identity too (C28).
- **Given lines' fixed coordinates:** now that anchors go through the map back, a coordinate whose direction
  component is 0 can come back off by an ulp (0.3 on [−1, 1] returns as 0.30000000000000004; 8–13% of values
  miss). Coordinate lines have an exact rule; given lines have none. 0058 offered the rule with the inverse map.
- **`duration()`'s rounding:** 0061's rule names the units, not the rounding: how 0.2 s, 59.7 s, or 2 h with no
  minutes are written. Users see these strings, and U9 compares them.
- **Which `log` and `exp`:** step 01 must choose `math`'s or numpy's.
- **The JSON shapes behind the approval id and the reuse key** (`data_model.md` §3.4) are listed, not shaped.

## Decision

We will:

1. **Compare golden points across machines in unit coordinates** (amends 0061 item 3). On one machine, every
   design's points are bit for bit (P4). Across machines, the `random` sampler's unit rows and points in linear
   ranges stay bit for bit; points in log ranges and random lines' points are compared in unit coordinates, by
   the map back, within `GOLDEN_UNIT_TOL` = 10⁻¹² absolute, coordinate by coordinate. That covers `log` and
   `exp` differing by their last bits for any range with |ln lo|, |ln hi| ≤ 64 and ln hi − ln lo ≥ 1 (a few ulps of 64,
   about 10⁻¹³ in z), which the golden requests use. A change in numpy's `standard_normal` stream moves the points far more, and fails the
   test. The generators use numpy's `log` and `exp`. P4 opens with "On one machine", and `data_model.md`'s
   "Across machines" names random lines too.
2. **Replay from the stored runs' points** (amends 0061 item 5). A replay hands the diagnostic the stored runs'
   points (Q15 fills them for a replay), so it reproduces what was computed. When the identity's generator and
   sampler versions are today's, it also rebuilds the design and compares it in unit coordinates within
   `GOLDEN_UNIT_TOL`; rows beyond that are named in `provenance_differences` ("design points differ at rows 3,
   17"). With another version, nothing is rebuilt, and `provenance_differences` names the versions. A replay
   never raises for either. U8 says so.
3. **Refuse an identity of another sampler version** when building a design, as of another generator version,
   naming both (`RequestError`).
4. **Keep given lines' fixed coordinates exact:** a coordinate whose direction component is 0 keeps the
   anchor's value, bit for bit, as coordinate lines' do.
5. **Round `duration()` first, then choose the unit:** under 10 s, one significant digit ("about 0.2 s",
   "about 4 s"); under a minute, whole seconds; under an hour, whole minutes ("about 40 min"); otherwise hours
   and whole minutes ("about 3 h 12 min"; "about 2 h" when the minutes are 0). So 59.7 s is "about 1 min".
6. **Shape the two hashed objects** as canonical JSON objects with named keys: the approval's `{"model_version_id",
   "for", "request", "new", "reused", "n_before"}`, and the reuse key's `{"model_version_id", "request",
   "run_ids", "versions"}`, `versions` an object of EMA's and the libraries' versions by name.

## Alternatives considered

- **A ulp tolerance that grows with |ln x|** ((2 + |ln lo| + |ln hi|)·2⁻⁵³ relative): exact in its reasoning,
  but harder to state and test than one absolute tolerance in unit coordinates, and random lines would still
  need their own.
- **Leave log ranges and random lines unpinned across machines:** simplest, but a numpy stream change would go
  unnoticed until reuse quietly stopped.
- **Keep 0061's error on a mismatch, and say in U8 that a replay needs the same machine and versions:** honest,
  but U8's colleague usually has another machine, and the stored points are what the result was computed from.
- **`math.log` and `math.exp`:** the same last-bit question, and a loop over points.

## Consequences

- **`../design/designs.md`:** Determinism and G1 (its test in unit coordinates, `GOLDEN_UNIT_TOL`); the
  identity refusal names the sampler version; given lines' fixed coordinates, with G10's test; the map back's
  known answers in G10's test (linear [0.1, 0.7] and [0.3, 1.1] at lo, log [10⁻⁶, 10] at hi: exactly −1 or 1).
- **`../design/principles.md`:** P4 opens with "On one machine".
- **`../design/data_model.md`:** "Across machines" names random lines; Replay uses the stored points, and the
  rebuild's check goes into the differences; §3.4 shapes the approval's and the reuse key's objects.
- **`../design/architecture.md`:** `reproduce`'s steps; Q15's points for a replay; `duration()`'s rule; the
  generators' refusal; `GOLDEN_UNIT_TOL` in `designs/generators.py`.
- **`../design/use_cases.md`:** U8 says a replay on another machine, or after a generator's version changes,
  reports the design's differences rather than refusing.
- **0061:** status "accepted; items 3 and 5 amended by 0062", and the index with it.
