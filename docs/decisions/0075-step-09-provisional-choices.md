# 0075. Step 09's provisional choices: the diagnostics' base, the diagnostic contract, the point run, the reference models

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 09 (`../plans/09-diagnostics-base-and-point-run.md`) builds `ema.diagnostics.base` (the interface, the
diagnostic parameters and their parsing, the registry, the shared precheck, `evaluate`), the diagnostic contract
(C1–C19 with its toy, broken toys, and meta-test), the point run, and the reference models R1–R11 but R9, on
`demo-09-diagnostics`, without the owner's review (0066). `architecture.md` §6 gives the names and signatures,
`diagnostics/shared.md` the precheck and the shared notes, `contracts.md` the promises and their negative
controls, `point_run.md` the point run, `reference_models.md` the models. Three hand-offs come from earlier steps:
one canonical identity per design (record 0067's Deferrals), each diagnostic's compute repeated at memory offsets
(record 0068 item 1), and the conventions for text in results (record 0073). Steps 10–13 build the other five
diagnostics in parallel on this base. Several details are open in the specs, or can't be built as worded; each
choice below keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

**Adding a diagnostic**

1. **Importing `ema.diagnostics` imports every module in the package but `base` and the private ones**
   (`pkgutil`), and each diagnostic module ends with `register(...)`: adding a diagnostic is one module, with no
   other file to edit, so steps 10–13 don't conflict in `__init__.py`. Registration refuses a taken name, and a
   spawn tag below 2³² or another diagnostic's (C8).
2. **`DiagnosticBase`** gives the defaults a diagnostic may keep (`observation_scope` "Of the n usable runs",
   `transform` from the shared observations' keys and a `TRANSFORMS` mapping, `strips` none, `example_request`);
   the `Diagnostic` protocol declares its attributes as read-only properties, so class attributes meet it.

**Diagnostic parameters (§6, §7 step 2; C55)**

3. **`DiagnosticParameter` gains `reader`** (and `info()`): a reader turns a value into its canonical form and
   describes it as a JSON schema. Readers: `Integer(minimum)`, `DecimalText(lo, hi)`, `Point` (names to
   doubles: `x`, an anchor, a direction), `Name(choices)` (a sampler, a basis), `GivenLines`. `parse` reads text
   as JSON when it is JSON and as a bare string otherwise (the CLI's `--param k=v`, §8), then the reader: one
   parsing for Python, the CLI, and MCP. `json_schema` is the reader's, with the meaning and the default text as
   its description, and the default when it is a value (a rule of d has none). `seed_parameter` gives every
   diagnostic's `seed` row.
4. **One identity per design** (record 0067's hand-off): the readers canonicalize (an integer as `int`, 3.0 and
   "3" as 3; values and directions as doubles; alpha as its shortest decimal text: 0.7072, "0.70720", and
   "7.072e-1" are "0.7072", by `Decimal.normalize`), the space goes through its canonical form, and every
   identity is built by `base.identity`, which refuses a value that isn't canonical JSON data (a numpy number) or
   a seed that isn't an `int` (`TypeError`). `decimal_fraction` is unchanged: `DecimalText` refuses "1/3" and
   padded text before it is reached.
5. **Shared helpers in `base`**, beyond §6's list, so the workspace (step 14) and steps 10–13 write them once:
   `make_request` (§7 step 2: the space parsed and validated, a missing or extra space refused, unknown
   parameters refused naming the known ones, defaults filled in order, the only model prediction), `request_space`,
   `identity`, `describe` (a `DiagnosticSummary`), `estimate` and `interval_info` (an `IntervalInfo` with the
   method's settings, `seed`, and `distinct`, record 0073 item 4), `make_provenance`, `library_versions`, and
   `AnalysisContext.seed`, `.prediction`, `.stream(tag)`, `.on_step(what)` (the bootstrap's progress, PM10).

**The precheck and `evaluate` (shared.md; P6)**

6. **`compute` is always called**, with no usable run too, so a diagnostic can add its own notes (the point run's
   "No repeats"); `evaluate` refuses (`ValueError`, naming P6) estimates or `extra` when `estimates_allowed` is
   False, and any observation with no usable run. C1 and C3 then hold for every diagnostic by construction.
7. **The shared observations** are `evaluate`'s: one table keyed `"shared"`, titled by `observation_scope`, with
   columns (title, prediction) and rows Minimum, Maximum, "(max - min) / max|y|" (keys `min`, `max`, `spread`;
   the spread 0 when max|y| is 0). A diagnostic's own table keyed `"shared"` puts its rows first in that table
   (the point run's mock is one table); its other tables follow.
8. **Counts are of distinct runs**, each counted at its first row in design order; a run is new when any of its
   rows is new. "Constant" needs at least two usable runs (one run isn't "the same in all"); below the minimum
   and constant, both notes are written.
9. **The shared notes, in order:** `not_usable` ("k of n runs is/are not usable for y: 3 failed (error), 2
   missing y.", "Most frequent reasons:", at most 5 lines `  count  reason`, failure and missing reasons alike, by
   count and then the first run in design order, then "  k  (m other reasons)", and "Estimates use the u usable
   runs." ("Observations use" for a diagnostic without estimates or below its minimum) with
   `` `ws.failed_runs("<12 hex digits>")` lists each one.``, 0055); `reused_failed` ("k of the r reused runs had
   failed before; `retry_failed=True` runs them again.", C47); then one of `all_failed` ("All n runs failed: no
   estimates or observations."), `no_usable` (shared.md's text), `too_few` (shared.md's); `constant`
   (shared.md's, the value by `fmt` with units); `measured_noisy`, one per record of this model version and model
   prediction, newest first ("name@12 was measured noisy in y by point run <12> (11 runs at the nominal point |
   the point a = 1, ...): standard deviation s units, f of the range of y in this diagnostic's runs (r units)."),
   with "so no fraction" when the range is 0, there is no usable run, or the standard deviation is none; then the
   diagnostic's own notes.
10. **The provenance** is checked, not built, by `evaluate`: its request must be the context's and its spawn
    tags the diagnostic's (P5, C8). The point run's `MeasuredNoisy` is returned with placeholder ids, and
    `evaluate` sets its result id, model version, and model prediction (C52).

**The point run (`point_run.md`)**

11. Its observations table is the shared one ("Of the 5 runs at the point"): Replicate 0 (key `replicate_0`, or
    `kind` with "failed (error)" or "missing"), Mean, "Standard deviation (ddof 1)" ("none" below 2 usable runs),
    Distinct values, then the shared rows. It varies exactly as PT3 says; its record's `runs` is the runs at the
    point and its `std` None when "none". Its example request has 9 repeats, so the contract's failure masks have
    rows to work on. The figure's y label uses "−" as the spec writes it, its caption "-" as the mock; the card
    holds each point's replicate, y, and deviation, and the value deviations are from.

**The diagnostic contract (`tests/contracts/diagnostic.py`)**

12. **Negative controls where `evaluate` now keeps the promise** (contracts.md's wording can't be built as a
    diagnostic's fault): C1's "NaN observations of no runs" fails at `Observation` (NaN refused); C3's
    "estimates below the minimum" fails at `evaluate`'s refusal; C10's spread is `evaluate`'s, so its broken toy
    labels the table with nothing of what it is of; C13's size is the generator's, so its broken toy names a test
    generator whose size is one more than its rows; C14's `prediction` can't reach a design (`design_identity`
    takes none), so its broken toy declares its seed "no" and seeds its design with it; C16's note is
    `evaluate`'s, so its broken toy adds a note of its own; C19 uses a counting fake, so a toy that calls the
    bootstrap directly fails though it names the fake. The meta-test pins each broken toy's exception and message.
13. **C2 also shifts the usable runs** (as C5 does): a toy that fills failed runs' y with 0 gives the same numbers
    whatever a failed run's kind or reason, and only a shift shows the zeros.
14. **C5's tolerance under y + b** has a floor of 16 units in the last place of |b| + max|y| for a number in
    y's units, the rounding the shift itself makes: the point run's fixture spans 2⁻²⁸ of its values, so
    UNITS_RTOL·range is below one ulp there; for every other fixture the floor is far below UNITS_RTOL·range.
15. **C6 is skipped when the offset merges the fixture's distinct usable values**: contracts.md's exemption of
    the point run, written as the rule it states.
16. **C7 repeats `compute` at 8 memory offsets** with the heap scrambled (record 0068 item 1): the batch's
    points, replicates, and values placed by `at_offset`, read-only through their bases (the types would
    otherwise copy them back to aligned memory).
17. **C8 changes a diagnostic's tags** by copying it and setting `spawn_tags`: a diagnostic reads its tags from
    itself. C18's 60 s is asserted for each evaluation (the polynomial model's step measures d = 20).
18. **The checks about numbers and notes run without figures** (`NoFigures`, a test double that leaves out
    `figures`); C1, C7, C11, and C12 draw them. A PNG costs about 0.1 s, and the fast tier has 30 s.

**The reference models (`reference_models.md`; §11)**

19. **Names:** `r1`, `ishigami` (0060), `r3`, `r4a`, `r4b`, `r5`, `r6a`, `r6b`, `r7`, `r8`, `r10`, `r11`. Each is a
    directory `src/ema/reference_models/<id>/` with `model.json`, its function file (R8: its program `r8.py`, its
    deck template, and the shared `table.dat`), and **`space.json`**, the space of its expected answers:
    `ema.reference_models.space(id)` beside `path(id)`. Ids are read in any case; R9 is refused as later.
20. **Model predictions' descriptions are empty** but R3's ("water flow through the borehole"), so the header row
    reads as the mocks do ("y"; "y: water flow through the borehole, m³/yr"). **Limits** only where the model
    needs them (k, r, rw: `gt 0`); the reference ranges are in `space.json`, not limits.
21. **R8's command** is `["python3", "r8.py", "x.in"]`: standard library only, R7's constants read from
    `table.dat`, the value written with `repr`; `timeout_s` 60. **R6a and R6b** draw from a module-level
    `numpy.random.default_rng()`, fresh entropy in each child. **R5** returns `{"y", "z"}` with z NaN where
    b > 0.8, raises `ValueError("no convergence")` where a + b > 1, and sleeps 5 s where a, b < −0.8
    (`timeout_s` 0.2).
22. **Ports:** R2 and R3 from v1's `src/ema/testfunctions/library.py` (`ishigami`, `borehole`), with numpy;
    bit-identical to v1 at 200 random points, run in v1's own environment. v1's `truth.py` is not ported: its
    numbers are Monte Carlo estimates, and the analytic truths are in `reference_models.md` and `docs/checks/`.

**Layers and tooling**

23. **AR1's layer 3b** is written `"(ema.runner) | (ema.approval) | ema.diagnostics"`: import-linter's optional
    layers, until step 07 merges (then the parentheses go). `ema.diagnostics` joins AR4's, AR5's, and the
    reference models' source modules. Ruff and mypy exclude `src/ema/reference_models/`.

## Deferrals

- **PT1's price and rerun, PT4's and PT5's store parts, C47's retry, C52's W5** need the runner and the store:
  tested end to end at step 14. Here: the design, replicate 0's run id equal to the test run's, the record, and
  the note from a record in the context. The seam is `AnalysisContext.measured_noisy` (Q10's records).
- **R8 through the runner** (step 11, as the roadmap says); here its program is run directly and equals R7.
- **The merge of `demo-08-reports`** (step 08's review fixes) into this branch was refused by the permission
  system; the coordinator merges. This step's code meets the changes the coordinator listed (figure names,
  `differences(..., skip=("Provenance",))`).

## Spec edits on acceptance

- **`architecture.md` §6:** `DiagnosticParameter.reader` and `info()`, the readers, `DiagnosticBase`, and the
  helpers of item 5; the protocol's read-only declarations; `compute` called with no usable run, and
  `evaluate`'s refusals (item 6); the `"shared"` table's merge (item 7).
- **`contracts.md`:** the negative controls of C1, C3, C10, C13, C14, C16, and C19 as built (item 12); C2's
  shift (item 13); C5's floor (item 14); C6's exemption as a rule (item 15).
- **`diagnostics/shared.md`, Notes:** the texts of item 9 (`all_failed`, `reused_failed`, the id in the
  `failed_runs` line as 12 hex digits); "constant" needs two usable runs (item 8).
- **`reference_models.md`:** the model names, `space.json` and `space(id)` (items 19–21).

## Alternatives considered

- **An explicit import per diagnostic in `ema/diagnostics/__init__.py`:** clearer, but four parallel steps would
  edit one line (Ruff merges the imports).
- **`evaluate` skipping `compute` with no usable run:** simpler for diagnostics, but the point run's "No repeats"
  note with its one run failed would need a special case, and C1's negative control would have nothing to break.
- **Canonicalizing the identity after the fact** (a function over `DesignIdentity`): it would need each
  generator's parameter types; the readers know them where the value enters.
- **Alpha's text kept as written:** "0.70720" and "0.7072" would be two designs.
- **Diagnostics computing the shared observations themselves:** C10 would then be every diagnostic's to keep.

## Consequences

- **Size:** `ema.diagnostics` 780 code lines (no docstrings, comments, or blanks): `base.py` 619 against §11's
  "base and precheck ~300", `point_run.py` 154 (§11: 150–400 each). The base's overrun is the readers (about 95,
  item 3), the read-only protocol (about 45), and the request, identity, description, and provenance helpers
  (about 110) that the workspace's estimate counted; step 14 shrinks by as much. The reference models: 82 code
  lines of Python and 187 lines of specs, spaces, template, and table, against their 1,000.
- **Tests:** the fast tier gains 166 tests (the contract's 58 over the point run and the toy, about 4 s; the base's
  59, the point run's 18, and the reference models' 31, about 2.5 s); the slow tier one (R5's timeout). A
  diagnostic adds about 2 s to the contract (19 checks), so steps 10–13 will need the fast tier's budget watched.
- Steps 10–13 follow the plan's "Adding a diagnostic"; step 14 calls `make_request`, `identity`,
  `make_provenance`, and `evaluate` in §7's order.
