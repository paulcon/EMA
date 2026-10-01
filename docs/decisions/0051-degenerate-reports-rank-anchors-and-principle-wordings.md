# 0051. Settle the review's smaller rules: empty sections, rank, anchors, spawn streams, and four wordings

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q9).

## Context

The consistency review (`../notes/consistency_review_2026-10-01.md`) found twelve smaller gaps between accepted
specs:

1. **S1:** every report has its sections, leaving out only an empty Notes. Nothing says what a diagnostic with
   no estimates (constant, too few usable runs, all failed) shows, or which figures it still draws.
2. **No usable run:** every run is ok but none read the analyzed model prediction. That is neither "all runs
   failed" nor clearly "too few usable runs".
3. **Rank:** "A has rank below P" (PM7, the undefined-resample rules) has no numerical rule. In floating point,
   A is almost never exactly rank-deficient.
4. **P6 and S5's test** say every diagnostic gives the constant note. The point run doesn't (PT6, C4, 0036).
5. **Spawn streams:** `SeedSequence` stores the tag 2³² + 1 as the words (1, 1), the same stream as child 1 of
   random line 1's stream. Tags are distinct only while design streams spawn no children, and no rule says so.
6. **The anchor:** `designs.md` says a line whose anchor is off center "shares no point with the others".
   That is false when the anchor sits at a range's end, or exactly on another grid point: that line's point
   equals the anchor bit for bit. G12's counts and CL7's header then miscount.
7. **S2's test:** "U3's `r1` on R5 … a held value and a nominal one". R5 has two model parameters, so that
   leaves none varied, and scatter refuses it.
8. **The order of reasons** in the note on runs not usable is unstated; the example lists 27, 3, 4.
9. **P7:** "a model measured as noisy" carries a note. The point run records noise per model prediction.
10. **P3:** "has no other lookup". 0020 also looks runs up by run id.
11. **P4:** "EMA picks one [seed]". `designs.md` says the seed is 0.
12. **C49:** nothing checks that a run stopped partway isn't stored (`model_interface.md`). If it were stored as
    failed, 0010 would reuse it.

## Decision

We will:

1. **Leave out an empty section** (S1), with its opening sentence: no explanation of intervals when there are
   no estimates. Each diagnostic spec's degenerate-case section lists the figures it still draws. For example,
   scatter draws its panels with strips but no histogram for a constant y, and the fits draw no shadow without a
   fit.
2. **Add a note for no usable run:** "No run is usable for z: 0 failed, 200 missing z." There are no estimates
   or observations, as when all runs failed. `contracts.md` gains the degenerate case "z missing in every run".
3. **Use numpy's `matrix_rank` rule:** A's rank is the number of singular values above max(n, P)·ε·σ_max (ε
   the double's machine epsilon). `uncertainty.md` names it for both fits' notes and undefined resamples.
4. **Except the point run from the constant note.**
   - P6 reads: "…its diagnostic result holds counts and a note, and no estimates; the point run, whose answer is
     the value itself, reports it as an observation (0036)".
   - S5's test reads: "for every diagnostic but the point run (PT6)".
5. **Make it a rule that design streams spawn no children of their own** (`shared.md`). C8 adds: "no
   registered stream's spawn key, as 32-bit words, equals another's or a design stream's".
6. **Refuse an anchor that equals, bit for bit, a point of a coordinate line along which it is off center**
   (an end at lo or hi, or another grid point), naming the model parameter. The analyst gives another anchor,
   as when a nominal value is outside its range. `designs.md`'s wording, G12, and CL7 then hold as written.
   The contracts' degenerate case "a nominal value or an anchor at a range's end" expects this refusal for
   coordinate lines.
7. **Split S2's test:** R5 (U3's `r1`) for the counts by kind and missing z; R1, with one held value and one
   at nominal, for the held rows.
8. **Order the reasons by count, descending,** ties broken by the first run in design order with that reason.
   The example becomes 27, 4, 3.
9. **P7:** "Every diagnostic result for a model version measured noisy in the model prediction it analyzes
   carries a note saying so."
10. **P3:** "…and has no other lookup for reuse".
11. **P4:** "when the user gives no seed, the seed is 0, and is recorded (P5; `designs.md`)".
12. **C49 adds** "…and stores no record of a run stopped partway" (`model_interface.md`, 0028). Its negative
    control stores the stopped run as failed.

## Alternatives considered

- **Keep every section,** an empty one saying "None: <reason>": a fixed layout, but more text that repeats the
  note.
- **"Too few usable runs"** for the no-usable-run case: no new note, but it doesn't say the runs were ok.
- **A named rank tolerance** (such as 10⁻¹²·σ_max), which would also refuse near-deficient fits. Not chosen: a
  near-deficient fit gets wide intervals, which say so.
- **Give the point run the constant note:** not chosen. One value is its ordinary answer for a deterministic
  model.
- **Leave the spawn condition as a stated condition:** not chosen. The rule and check are cheap.
- **Count any bit-for-bit equal point as containing the anchor,** and fix G12's counts and CL7's header to
  match. Not chosen: refusal keeps one simple rule (the center, n odd).
- **Group the reasons by kind:** not chosen; the counts by kind are already the note's first line.

## Consequences

- **`../design/diagnostics/shared.md`** (accepted): S1 (Decision 1); the notes (Decisions 2 and 8); S2's test
  (Decision 7); S5's test (Decision 4); random draws (Decision 5).
- **The diagnostic specs** (accepted): each degenerate-case section lists its figures (Decision 1).
- **`../design/uncertainty.md`**, **`linear_model.md`**, **`polynomial_model.md`** (accepted): Decision 3.
- **`../design/principles.md`** (accepted): P3, P4, P6, and P7 as Decisions 10, 11, 4, and 9.
- **`../design/designs.md`** (accepted): the shared anchor's paragraph and G12's test add Decision 6's
  refusal.
- **`../design/diagnostics/coordinate_lines.md`** (accepted): its precheck adds Decision 6's refusal.
- **`../design/contracts.md`** (accepted):
  - degenerate cases: "z missing in every run" (Decision 2); the anchor at a range's end expects a refusal for
    coordinate lines (Decision 6);
  - C8 (Decision 5);
  - C49 (Decision 12).
