# 0063. Store a design's structure with its result, check a rebuilt design per range, and pin `duration()`'s edges

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none ("Before the first line of code", `TODO.md`).

## Context

A third review checked record 0062's application (`../notes/consistency_review_2026-10-01_before_code.md`).
Its plain errors are corrected in place (0052). Three findings change what 0062 decided:

- **A replay across generator versions has no design to give the diagnostic.** 0062 replays from the stored
  runs' points and rebuilds nothing when the identity's generator or sampler version isn't today's. But a
  diagnostic receives a `RunBatch` with a `Design`, and four diagnostics read the design's structure, not
  only its points:

  | Diagnostic | Needs beyond points | Recoverable without the generator? |
  |---|---|---|
  | linear and polynomial models | the levels n₀ … n_L | from G7's closed form, if the sampler's rate is known |
  | coordinate lines | rows per line, the anchor, which lines contain it | only by re-implementing the generator's rules |
  | given lines | rows per line; the ends | the ends are each line's first and last rows |
  | random lines | rows, ends, and the drawn anchor and direction | no: the anchor is a stream draw |

  Nothing stored holds this structure today: the provenance holds the identity, the request, and the run ids,
  and the data cards go with a deleted result. `designs.md` ("Recorded with the design, for each line: its
  anchor, its direction, and its two ends") and `data_model.md` (the identity stored so `reproduce` doesn't
  depend on today's code) say more than is stored. Nor does any spec say which points a diagnostic reads in a
  replay.
- **`GOLDEN_UNIT_TOL` doesn't cover every range in the rebuild check.** 0062 argued 10⁻¹² for the golden
  requests' log ranges (|ln lo|, |ln hi| ≤ 64, ln hi − ln lo ≥ 1). A replay's check applies to any space, and a
  narrow or far log range moves further in unit coordinates when `log` and `exp` differ by their last bits
  (measured: [10⁹, 1.01·10⁹] up to 1.0·10⁻¹¹; [e⁶³, e^63.01] up to 2.0·10⁻¹¹; [1, 1.001] up to 4·10⁻¹²). A
  replay on another machine would falsely report "design points differ". Held coordinates have no unit
  coordinate, and replicates weren't compared.
- **`duration()`'s edges:** "rounded first" could leave 3599 s as "about 60 min"; ties have no rule (Python's
  `round` gives 2.5 s → "about 2 s"); and one significant digit gives "about 1e-05 s".

## Decision

We will:

1. **Store a design's structure with its diagnostic result** (amends 0062 item 2): `Provenance` gains
   `design_structure`, holding a convergent design's level sizes n₀ … n_L, and each line's anchor, direction
   (in unit coordinates), two ends, and rows. A replay builds its `Design` from the stored identity, the stored
   runs' points and replicates (Q15), and this structure, with no generator; the diagnostic reads that
   design's points. Rebuilding with today's generator, when its and the sampler's versions are the identity's,
   is only a check.
2. **Check a rebuilt design coordinate by coordinate, per range:** a linear-range coordinate within
   `GOLDEN_UNIT_TOL`; a log-range coordinate within max(`GOLDEN_UNIT_TOL`, 32·2⁻⁵²·(1 + |ln lo| + |ln hi|)/(ln hi −
   ln lo)) in unit coordinates, which covers every case measured with a margin of 2–4; held coordinates and
   replicates exactly. Rows beyond these go into `provenance_differences`, as 0062 says.
3. **Pin `duration()`'s edges:** each rounding is half up; a value that rounds to its unit's limit is written in
   the next unit (3599 s is "about 1 h"); under 0.01 s is "under 0.01 s". A known-answer test fixes the strings:
   0.004 s "under 0.01 s", 0.04 s "about 0.04 s", 0.2 s "about 0.2 s", 2.5 s "about 3 s", 4.4 s "about 4 s",
   9.96 s "about 10 s", 59.7 s "about 1 min", 90 s "about 2 min", 3599 s "about 1 h", 7200 s "about 2 h",
   11,520 s "about 3 h 12 min".

## Alternatives considered

- **Build with today's generator for the structure only, using the stored points** (about 10 lines): a version
  bump means the structure or the draws changed, so it risks a silent mismatch, or a crash on the row count.
- **Refuse a replay across generator versions for the four diagnostics that need structure** (about 5 lines):
  breaks U8 in exactly U8's case, which 0062 fixed.
- **Derive the structure from the request, the spec, and the points** (60–80 lines): duplicates the
  generators' rules, which drift, and can't recover random lines' anchors.
- **One tolerance for the rebuild check,** wider than 10⁻¹² (say 10⁻¹⁰): simpler, but still not enough for
  every range, and loose for the common ones.

Storing the structure costs about 30–50 lines (the type, its JSON, W5, and the C17 and C51 checks), and at
most 3/n of the points' size. The schema isn't shipped, so it is cheapest now.

## Consequences

- **`../design/architecture.md`:** `Provenance.design_structure`; `Design` built from stored parts for a
  replay; `read_batch` and `reproduce`; `RunColumns.points`' comment; `duration()`'s comment.
- **`../design/data_model.md`:** §5.9 (the provenance's JSON holds the structure); Replay; the identity's
  "so `reproduce` doesn't depend on today's code" made true by the structure.
- **`../design/designs.md`:** "Recorded with the design" says where: in the result's provenance.
- **`../design/contracts.md`:** C51 replays across a generator version bump (a test generator registered at two
  versions); C17's round trip covers the structure.
- **0062:** status "accepted; item 2 amended by 0063", and the index with it.
