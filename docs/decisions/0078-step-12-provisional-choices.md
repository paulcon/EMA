# 0078. Step 12's provisional choices: the linear model

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 12 (`../plans/12-linear-model.md`) builds the linear model diagnostic (`ema/diagnostics/linear_model.py`)
on step 09's base (record 0075), without the owner's review (0066). `diagnostics/linear_model.md` (LM1–LM10, the
mock report, the expected answers) and `uncertainty.md` (the bootstrap) specify it; `architecture.md` §6 places it;
records 0068 (`ema.numerics.fitting`) and 0073 (the report's conventions) say how its numbers are computed and
written. The roadmap asks this step to settle the per-level table's coefficients and their units (the consistency
review's DIAG-10d). A few details are open in the specs; each choice below keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

1. **Read `sampler` as any sampler's name, and refuse one with no implementation when the design is built**, with
   `samplers.get`'s "sampler sobol comes in a later version" (designs.md, Samplers; G17's wording), not with a list
   of today's names at parsing. C14 parses each parameter's other value before it asks for a refusal, so the other
   value `"sobol"` must parse. The reader (`_fits.SamplerName`) accepts letters, digits, `_`, and `-`.
2. **The per-level table's coefficients are printed without units, and the table's title names them**
   ("Coefficients in m³/yr. Each level is fitted on the usable runs among its first points."), as the mock report
   does (DIAG-10d): a number in each of 9 × 3 cells with its units would crowd the table, and the title gives them
   once. With a dimensionless model prediction, the title has no units sentence. (Review round 1, item 14: the
   cells store their units; the report leaves them out.)
3. **With a constant model prediction, no per-level table:** its fits are of one value, so their coefficients are
   that value and rounding, and their relative residual, R², and LOO error undefined; the shared observations
   (which state the value) and the constant note stay. Below the minimum, the table stays, as the spec says
   ("none" where a level has too few usable runs).
4. **A fit of rank below d + 1 on level L's usable runs** (0051's rule) gives no estimates and a note, "The usable
   runs' unit coordinates have rank r with the constant, below the fit's d + 1: no fit." The spec has no such case
   (random points have full rank with probability 1); `uncertainty.md`'s Rank rule says the rule decides the fits'
   notes on the usable runs.
5. **An estimate whose value is undefined while the fit is defined** (the LOO error, when a usable run has leverage
   1) is left out, with a note ("The leave-one-out error is undefined: a usable run has leverage 1."), as
   `uncertainty.md`'s Rules say: where a value can't be computed there is no estimate, and a note says why. (Review
   round 1, item 15: the leverage is named only when a run has it.)
6. **Undefined resamples are counted per estimate, keyed by its label** (V4; record 0073 item 4): "Undefined
   resamples, dropped: Intercept 16, a 16." under the coefficients table. A rank-deficient resample drops every
   coefficient, so their counts are equal.
7. **The coefficients table's title names the log ranges:** "y ≈ intercept + Σ slope·u, u the unit coordinates in
   [-1, 1] (r through its logarithm)."; with several, "(r, k through their logarithms)"; with none, no parenthesis.
8. **Keys** (C5): the estimates `intercept`, `slope` (each model parameter's), `relative_residual`, `r2`, `loo`;
   the per-level table `usable` ("18 of 18", text), then the same keys. A level below the minimum, and a value
   that is undefined, is "none". Transforms: the intercept a·v + b, the slopes times a, the rest unchanged.
9. **The slopes figure names the model parameters as its x tick labels**, set with matplotlib's `set_xticks` and
   escaped by `plotting.axis_label` (T10), labels turned 90° above 8 model parameters. `ema.plotting` has no
   categorical-axis helper; adding one would change step 08's module, which steps 10–13 share. The tick labels
   are set outside `ema.plotting`'s style context, so their size is set explicitly (8 pt).
10. **Each usable run's level is passed to the interval method** (uncertainty.md: "the usable runs, as indices in
    the design's order, with their levels when the design has them"), so subsampling the levels needs no change
    here; the bootstrap ignores it.
11. **The example request** for the diagnostic contract is the defaults with seed 0 (at d = 3: 8, 16, 32 runs; at
    d = 20: 42, 84, 168).
12. **The shared helpers are in a private module, `ema/diagnostics/_fits.py`:** the sampler reader, a fit's values
    as one array (`[coefficients..., relative residual, R², LOO]`, from `ema.numerics.fitting`), the bootstrap's
    two estimators (the fit as drawn; LOO on distinct runs), each row's level, the per-level table, and the
    residual histogram's ⌊√n⌋ bins. The polynomial model may adopt them at the merge; nothing requires it.
13. **The figures read the coefficients from the stored result** (P1, 0037) and the unit coordinates from the
    batch's design, so ŷ in the shadow and the residuals is β₀ + Σ βᵢuᵢ of the stored doubles. The residuals' data
    card holds the bin edges and counts, and each run's residual with its run id (S9).

**Review round 1** (the independent review's minors and nits; fixed on `demo-diagfix`, each with a test)

14. **The per-level coefficients' cells store their units** (amends item 2): the intercept's and the slopes' cells
    hold the model prediction's units, so a result read as JSON has them on each number (`shared.md`, Units); the
    report leaves a cell's units out where its table's title says "in <units>." (`ema.report.render`'s
    `_observation_cell`, a rule of three lines, no field on `ObservationTable`, so no change to the stored type).
    The golden report still matches the mock byte for byte, and every other golden report is unchanged. The
    polynomial model's per-level table gets the same with `_fits.per_level(..., units=...)` (an optional argument).
15. **The LOO note names leverage 1 only when a run has it** (amends item 5): "The leave-one-out error is undefined:
    a usable run has leverage 1." when the fit's leverages hold an exact 1 (PRESS divides by 1 - h = 0), else "The
    leave-one-out error is undefined on these runs." (an overflow). A leverage of 1 ± 2⁻⁵² gives a finite, huge
    LOO error; that is PRESS's (step 02's), not changed here.
16. **The rank-deficient note's rank is the fit's** (`fitting.least_squares(A, y).rank`, from R's singular
    values), the rank that left the fit undefined, not a second SVD of A that could disagree at the threshold.
17. **Tests of the two notes on crafted batches:** a at its midpoint in every run (u_a = 0): "rank 3 with the
    constant, below the fit's 4 coefficients: no fit.", no estimates, "none" in each level; c = 1 in every run but
    one, at a row whose leverage is exactly 1 in doubles (found by the test): the coefficients and fit tables, no
    LOO estimate, and the leverage note.
18. **The JSON schema's patterns are anchored** (`^...$`): `_fits`'s sampler name and `base`'s decimal text. A JSON
    schema's `pattern` matches anywhere in the text, so the unanchored ones accepted "x0.7072" and "random sampler"
    in a client's validation, which the readers then refused. The readers' `fullmatch` is unchanged.
19. **The contract's lean interval method** (record 0084, Review round 1): the linear model's share of the
    contract went from about 84 s to 19 s of test time.

## Deferrals

- **v1's numbers were not run** (CLAUDE.md, v1 as an independent source): v1's `linear_coeffs` fits on normalized
  inputs with scikit-learn and reports a k-fold cross-validated R², not PRESS, so only the coefficients (mapped to
  unit coordinates) and the in-sample R² compare. Effort: about 1–2 hours, a script in v1's environment fed v2's
  R3 design points and runs (seed 3, 72 runs), its coefficients mapped and compared to the mock's within 10⁻¹⁰.
  Seam: `tests/support/reference.py`'s batch and the golden fixture; the independent check today is
  `docs/checks/linear_model.py`.

## Alternatives considered

- **`sampler` read by `Name(samplers.names)`:** refuses "sobol" at parsing, with a message other than designs.md's,
  and C14's check can't parse its other value.
- **Units in every per-level cell:** follows `shared.md`'s Units rule to the letter, but the golden report (the
  mock) has them once, in the title; the mock is the accepted spec of this report.
- **A per-level table for a constant model prediction:** numbers that are rounding (slopes about 10⁻¹⁶) and
  "none"s, which say nothing the constant note doesn't.

## Consequences

- **Spec edits on acceptance:** `diagnostics/shared.md`, Units: "a number with units is followed by them, or, in
  a table whose title names its units, by none" (item 2); `linear_model.md`, Minimum runs and degenerate cases:
  "Constant: the note, the shared observations, no per-level table, no estimates" (item 3), and the rank-deficient
  and leverage-1 notes (items 4, 5).
- **Cost:** the bootstrap refits each resample twice (as drawn, and on its distinct runs), about 2,000 calls of
  `fitting.least_squares` per evaluation, 0.15–0.5 s on a loaded machine, whatever the runs' number at these
  sizes: the call overhead of numpy's and scipy's wrappers dominates. The diagnostic contract's 19 checks over the
  linear model take about 25 s of CPU (C7, with its 8 memory offsets, about 5 s alone). A leaner fit in
  `ema.numerics.fitting` (fewer wrapper calls per fit) would speed both fits; it is step 02's module, shared with
  the polynomial model, so it isn't changed here.
- **Size:** `linear_model.py` 294 code lines and `_fits.py` 59, 353 against the roadmap's 300 for the step: the
  formatter writes each parameter's 8 arguments a line each (34 lines). The polynomial model can reuse `_fits.py`'s
  59 lines rather than write its own.
- **Shared files changed:** `docs/index.md` (an API block), `tests/slow/test_wheel.py` (the two modules), and
  `tests/unit/diagnostics/test_base.py`, whose registry test expected "the diagnostics are point_run" alone.
- **Deferrals:** none of the spec's items; v1's numbers (Deferrals).
- **Shared files changed in review round 1:** `src/ema/report/render.py` (item 14), `src/ema/diagnostics/base.py`
  (item 18), `tests/unit/report/test_render.py`.
