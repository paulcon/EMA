# 0077. Step 11's provisional choices: coordinate lines and lines, their shared per-line computation, and the contract's shared runs

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 11 (`../plans/11-coordinate-lines-and-lines.md`) builds `ema/diagnostics/_lines.py`,
`coordinate_lines.py`, and `lines.py` on step 09's base (record 0075), and runs R8, a command-line program,
through `ema.runner` and `ema.approval`, on `demo-11-lines`, without the owner's review (0066).
`diagnostics/coordinate_lines.md` (CL1–CL10) and `diagnostics/lines.md` (LN1–LN9) give the computation, the
observations, the figures, and the mock reports; records 0038, 0048, and 0058 the spectrum, the rate tolerances,
and the expected answers; record 0068 the Gram numerics (`ema.numerics.gram`, the window and floor the caller's);
record 0073 the report's and the figures' conventions. The build roadmap asks step 11 to watch C5's and C6's rate
tolerances and the shared anchor's rows. Several details are open in the specs, or can't be built as worded; each
choice below keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

**The shared per-line computation (`_lines.py`)**

1. **One base, `LinesDiagnostic`,** holds what both diagnostics do (no interval method, no tag, no estimates, the
   minimum `COORD_MIN_RUNS` = 1, one observations row and one figure per line, a note per constant line), with
   hooks for what differs (a line's label and "along ..." words, its figure's name, title, caption, x positions
   and anchor mark, its data card's description, and lines' Length column and ends tables). The analysis of one
   line is `analyze(y, usable, all_constant=...)`, its figure's spectrum panel `draw_spectrum`. Lines are read
   from the batch's design structure (`Design.lines`), so a replay (0063) analyzes the stored lines.
2. **Each line's cells, in this precedence:** no usable run: range "none", degrees "none", rate "none: 17 runs not
   usable"; every usable run of the diagnostic one double (0035): "none: constant", degrees "0 of K" on a complete
   line ("none" otherwise), no per-line note; any run not usable on the line (CL5): degrees "none", rate "none: 2
   runs not usable" ("1 run" singular), range over its usable runs; a constant line among others (two or more
   usable runs, one double; CL6): "0 of K", "none: constant", and its note; otherwise the spectrum, with k* "k* of
   K" and the rate, or "none" when k* < 3 (k* says why, as the Expected answers write it). A constant line that
   also has runs not usable still gets its note ("all 15 usable runs along f"), and its rate says the runs not
   usable.
3. **Values in the result:** usable and degrees are text ("17 of 17", "8 of 8"), the range a double in the model
   prediction's units, the rate a double or its "none" text, lines' length a double; the ends cells are text
   "from → to", each end `fmt` of the recorded double (S3) in the model parameter's units. The ends' full doubles
   are in the provenance's design structure and in each line's data card (P1).
4. **C5's declarations:** range scales by a; usable, length, and the ends are unchanged; the rate and its k* are
   declared with the flag "computed through a logarithm" (the rate's fit at the floor), so C5 holds the rate to
   `UNITS_LOG_TOL` and `RATE_SHIFT_TOL` and k* exactly (text), and C6 leaves both out (contracts.md, C6: "the
   observations that a cutoff at a fraction of a line's range decides"). `RATE_SHIFT_TOL` = 10⁻⁵ is a named
   constant in `_lines.py`, for the tests.
5. **Figures:** two stacked panels per line. The top: one marker per usable run joined in order, the anchor's dotted
   line (coordinate lines: its value; a given line: its distance along the line, its projection on the segment;
   a random line: none), the × strip, the title (the model parameter's name, or "line j"). The bottom:
   `ema.plotting.spectrum` with |c_k| / range, `SPECTRUM_YMIN`, the floor 10⁻¹⁰, the window shaded, and the tail
   fit drawn from the fit of log₁₀ T(k) shifted by log₁₀ of the range; with no spectrum, the panel is kept with its
   axis labels and the reason. One caption for all of a result's figures, as the mocks write it, so the report
   prints them in one paragraph. The data card: `panels` (top: axes, points with run ids, `not_usable`, `anchor`;
   bottom: axes, the plotted |c_k| / range with no run id, or `text`), `line` (coordinate lines: the model
   parameter, anchor, ends; lines: anchor, direction, ends in model parameter units and unit coordinates, length),
   and `spectrum` (every signed c_k, every T(k), K, k*, the absolute floor and its fraction, the rate, and the
   intercept of log₁₀(T(k) / range)), or `{"reason"}`.
6. **CL9's "the data card's c_k equal the result's":** the result holds observations only, no c_k; the test checks
   that the card's c_k are the line's Gram coefficients from the same runs, and the card's rate the result's.
7. **Lengths and distances** come from the recorded ends mapped to unit coordinates (`to_unit`): the length is the
   distance between them, point j sits at j/(n − 1) of it.

**Requests and designs**

8. **`design_identity` asks the generator for the design's size,** so every refusal of CL1 and LN1 (no varied
   model parameter, G14's anchors and directions, 0051's anchor on another point of a line) comes when the
   identity is made, before anything is built or priced. n < 7 is refused by the parameter's reader
   (`Integer(7)`).
9. **The design identity's seed is the request's,** as the point run's (record 0075): coordinate lines' and given
   lines' generators draw nothing, and the request's seed is recorded (0061).
10. **Lines' two modes:** `m`'s default is a rule, none when `lines` is given and 5 otherwise, read by an optional
    integer reader (`null` in MCP's JSON is none); `m` and `lines` both given, or neither, is refused in `design_identity`. The
    canonical request then holds `m: null` with given lines, or `lines: null` with random ones.
11. **The Provenance line leaves out a request parameter whose value is none** (`ema.report.render`, one line):
    lines' mock writes "m = 5, n = 17, seed 0", not "lines = null"; with given lines, "lines = [...]" and no m.
12. **Example requests** (the contract's): coordinate lines n = 9 through the nominal point, seed 0; lines m = 2,
    n = 9, seed 0: small, with other values 17 (nested, 2·9 − 1), an anchor `{"a": 0.3}`, m = 3, and a given line
    `{"direction": {"a": 1}}`. The seed's "Changes the design?" keeps lines' spec wording, "yes (random lines)".
13. **The ends tables** are keyed `ends_0`, `ends_1`, ..., titled by their row heading (so nothing is printed under
    them); the rates table is keyed `line_rates`; the constant line's note is coded `constant_line`.

**The diagnostic contract's shared runs (the roadmap's "shared anchor's rows"; step 09's review, M2)**

14. **The contract's batch builder treats a run in several rows as one run** (`tests/support/diagnostics.py`): it
    is failed, or missing y, when any of its rows is masked, with one kind and reason, the i-th counted by its
    first row; for designs with no repeated run nothing changes. C2 counts kinds and z's missing runs over distinct
    runs, as the header does (record 0075 item 8). A self-test checks the shared anchor.
15. **C6 skips the numbers declared through a logarithm** (`assert_transformed(..., skip_log=True)`), item 4.
16. **Step 09's registry test** matched "the diagnostics are point_run"; it now matches any list that names the
    point run, since steps 10–13 register more.

**Tests**

17. **R8 runs through `ema.runner` and `ema.approval`** with a temporary store, in the slow tier (about 20 s): U2's
    first evaluation is stopped after 41 runs (an exception from `on_progress`, as Ctrl-C), its rerun reuses them and
    makes the other 56 under its own approval, `read_batch` gives the batch, and the report is the mock report
    (0044), every number within one unit in its 4th digit, the rates within 10⁻⁶. Every other known answer runs the
    reference model's function in the test's process (record 0075), R8's as R7's with f and g of no effect.
18. **The exact-rational rate** is a test helper (`exact_rate`, about 20 lines, on step 02's exact Gram basis):
    k* and the rate of the runs' doubles, against which EMA's rates agree within 10⁻⁹ on R7's lines.

**Review round 1** (the independent review's minor and nits; fixed on `demo-diagfix`, each with a test)

19. **Item 2's precedence is tested directly:** a parametrized unit test of `analyze(...).cells(...)` over four
    paths, a constant line with runs not usable ("none: 2 runs not usable", its note's value kept), a constant
    diagnostic with an incomplete line ("none: constant", degrees "none"), a line with no usable run (range "none",
    "none: 9 runs not usable"), and one run not usable (singular), with the range's units only on a number.
20. **C6's skip is limited to named diagnostics** (corrects item 15): the contract's `C6_LOG_SKIP` is
    `("coordinate_lines", "lines")`, and a number declared through a logarithm by any other diagnostic fails C6
    ("C6 skips a number through a logarithm of lines' only"); a broken toy that declares its standard deviation so
    is in the meta-test. A later diagnostic whose numbers a cutoff at a fraction of a line's range decides is added
    to the set, with a record.

## Deferrals

None of the spec's requirements. The PNGs' cost (about 0.1–0.4 s each, two panels) is step 08's: the contract draws
18 of them for these two diagnostics.

## Spec edits on acceptance

- **`diagnostics/coordinate_lines.md`, CL9's test:** "the data card's c_k are the line's Gram coefficients, and its
  k* and rate the result's" (item 6). Its Observations: "none" for the range of a line with no usable run, and the
  precedence of item 2.
- **`diagnostics/lines.md`, Parameters:** `m`'s default "5; none with `lines`" (item 10).
- **`diagnostics/shared.md`, The report, Provenance:** a request parameter that is none is left out (item 11).
- **`contracts.md`, C5:** a diagnostic declares the rate's k* with the rate's flag (item 4); the contract's fixture
  counts a run in several rows once (item 14). **C6:** the numbers left out as through a logarithm are lines' only,
  named (item 20).
- **`architecture.md` §6:** `_lines.py`'s names (`LinesDiagnostic`, `LineAnalysis`, `analyze`, `draw_spectrum`,
  `window`, the constants).

## Alternatives considered

- **A new `Transform` member for k*,** or a declared set the contract skips in C6: an edit to step 09's base for one
  case; the existing flag already marks the rate's fit.
- **k* as an integer with "of 8" as its units:** prints the mock's cell, but units that aren't units.
- **Storing each line's c_k in the result** (CL9 as worded): the result type has no field for arrays of numbers that
  aren't estimates or observations; adding one is a store schema change, and the data card already holds them.
- **Leaving None parameters out of the canonical request** (in `make_request`): C14 and the request's identity read
  every declared parameter; leaving it out of the printed line is enough.
- **A line with runs not usable getting "none: constant"** when its usable runs agree: hides that its spectrum is
  undefined for another reason; the note still says it is constant.

## Consequences

- **Size:** `_lines.py` 222, `coordinate_lines.py` 84, `lines.py` 148 code lines: 454 against the roadmap's 550.
- **Shared files changed:** `src/ema/report/render.py` (item 11, one line), `tests/contracts/diagnostic.py`
  (items 14, 15), `tests/support/diagnostics.py` (item 14), `tests/unit/diagnostics/test_base.py` (item 16),
  `docs/index.md` (a block of its own), `tests/slow/test_wheel.py` (the three modules).
- Steps 10, 12, 13 see their contract unchanged but for C2's counts over distinct runs, which equal the rows' where
  no run repeats.
