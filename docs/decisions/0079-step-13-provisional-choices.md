# 0079. Step 13's provisional choices: the polynomial model

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 13 (`../plans/13-polynomial-model.md`) builds `ema/diagnostics/polynomial_model.py` on
`demo-13-polynomial`, without the owner's review (0066). `diagnostics/polynomial_model.md` (PM1–PM12) gives the
parameters, the computation, the uncertainty, the degenerate cases, the figures, the expected answers, and the mock
report; `uncertainty.md` the bootstrap; `contracts.md` C1–C19 and C29; records 0068 (the numerics), 0073 (the
report's conventions), and 0075 (the diagnostics' base) the interfaces it builds on. The report on R3 matches the
mock (record 0073 item 6's Provenance edit applied), and every number of the mock was already checked by
`docs/checks/polynomial_model.py`. Where the specs leave a detail open, or the shared contract can't be met as the
spec words a declaration, each choice below keeps P1–P7 and the spec's intent.

## Decision

We will, provisionally:

**The request (PM1; C14, C15, C29)**

1. **The example request** (the contract's) is degree 1, level 2, seed 3: 8, 16, 32 points at d = 3, enough for
   the contract's failure masks to leave 2P usable runs, and cheap (about 50 evaluations of 1000 refits each).
   The contract's C18 runs it at d = 20 in the fast tier; C18 at d = 20 **with the defaults** (P = 231, 1848 runs),
   which `contracts.md` puts in the slow tier, is this step's own slow test, against `D20_SECONDS`.
2. **`sampler` and `basis` are read as any non-empty name** (a reader, `Registered`, whose JSON schema lists the
   registered names as examples), and refused when the design is built, before any run, by the registry's own
   "sampler X comes in a later version" / "basis X comes in a later version" (PM1, 0032). C14 parses a parameter's
   second value before it prepares the request, so a reader that refused unknown names failed C14.
3. **`basis`'s "Changes the design?" is written "no (one basis in v2.0: another is refused)"**, not the spec's "no":
   with one basis registered, its second value is refused, which C14 reads as a broken "no". The promise itself is
   tested with C29's fake basis registered: the same design bit for bit, and another request, so another reuse key
   (C29's last clause, record 0068's deferral). `degree` is "yes (through n_min's default)", as the spec writes it.
4. **Nesting** claims `degree` and `level` (PM11): the same seed's uniform rows, so a larger degree's or level's
   design starts with the smaller one's points. U4's case (degree 3, level 1 after degree 2, level 2 on R3: 300 new
   runs) is tested on the designs; its reuse through the store is step 14's.

**The numbers (PM2–PM7)**

5. **`POLY_NMIN` and `POLY_MIN_RUNS` are 2**, the factor of "2P" the spec's table names; n_min's default is the
   rule 2·C(d + p, p) of the parsed degree. The too-few note is the precheck's: "68 usable runs; polynomial model
   needs at least 168 (twice its 84 coefficients at degree 3)."
6. **The result's tables and keys:** estimates `fit` (`rel_residual`, `r2`), `loo` (`loo`), `sobol`
   (`first:<name>`, `total:<name>`, two per row), `decay` (`energy:<k>`, label "k⇥terms", units y's); `extra`'s
   `coefficients` (key `c:<multi-index>`, label "ψ₁(rw)·ψ₁(Hu)", "ψ₀" for the constant; in the result and the fit
   figure's data card, not the report, 0041); observations `levels` (`usable` "90 of 90", `rel_residual`, `r2`,
   `loo`, `total:<name>`). C5's declarations: c₀ a·v + b; the other coefficients and √E_k times a; the rest
   unchanged.
7. **Undefined resamples** are counted per estimate (V4), keyed by a short name ("relative residual", "R²",
   "leave-one-out error", "rw first-order", "rw total", "√E_2"); the report prints those that aren't 0. The
   as-drawn estimates share one estimator (one refit per resample), and the LOO error is a second, on distinct
   runs, which skips the refit below P + 1 distinct runs.
8. **The per-level table** writes "none" for a level with fewer than 2P usable runs, with A of rank below P, or
   where a number is 0/0 (a constant model prediction); level L's column is the estimates' fit.
9. **Rank below P at level L:** "The 40 usable runs don't determine the degree-2 polynomial: A has rank 9 of 10.",
   no estimates, the observations; the Fit header row is written in every case, so the header has one shape.
10. **The LOO error undefined on the usable runs** (a run of leverage 1; the spec is silent): its table is left
    out, with a note, "The leave-one-out error is undefined: a usable run has leverage 1." (uncertainty.md's rule:
    where a value can't be computed there is no estimate, and a note says why).
11. **V = 0** (0049): no Sobol table and the spec's note; the decay table stays (every √E_k 0); the fit and
    residual figures only. No QR on any design tried gave exact zeros, so the test wraps the fit to zero the
    non-constant coefficients.

**Progress (PM10)**

12. **"A: n × P, size"** is reported first (`Progress("analysis", 0, 0, ...)`), the size to 2 significant digits in
    kB, MB, or GB ("A: 14161 × 1771, 200 MB"); then "bootstrap: k of 1000 refits, about t left" after the first
    refit, the last, and about once a second (`PROGRESS_SECONDS`) between. An exception from the callback stops the
    evaluation with no result (tested); a rerun on the same runs gives the same result.

**Figures (PM9)**

13. **The fit figure** has two panels, x "fitted y" and "held-out prediction of y", each with y = ŷ and a strip
    of the runs not usable at their ŷ (every run in both panels, C12); ŷ from the stored coefficients, the
    leverages from A's QR (architecture.md §6); a held-out prediction that isn't finite (a leverage of 1) is left
    out of the right panel. Its data card holds the coefficients, each with its multi-index, term, value, and
    interval (the spec's "a data card" for the coefficients). **The Sobol figure's** x axis is "model parameter",
    with the names as ticks, a legend for first-order and total. **The decay figure's** lower limit is
    `SPECTRUM_YMIN` = 10⁻¹⁷ of the largest √E_k; its card names the limit and the degrees drawn as open markers.
    `SPECTRUM_YMIN` is defined in this module too (coordinate lines', step 11, is built at the same time): one
    constant on merge.

**Speed and the slow tier**

14. **`ema.numerics.fitting.least_squares` calls LAPACK's `dtrtrs` directly** (`scipy.linalg.lapack`), the routine
    `scipy.linalg.solve_triangular` calls after about 80 µs of argument checks: the same numbers bit for bit (the
    determinism tests pass unchanged), and about a third less time per refit, for the linear model's bootstrap too.
    A singular R raises `LinAlgError`, as before (the rank rule refuses one first). A one-line change to step 02's
    module.
15. **R2's expected answers at p = 10 compute no intervals** (an interval method defined in the test, `NoIntervals`,
    through V7's seam: every interval "none", with its reason): the estimates don't depend on the interval method,
    and the bootstrap's 1000 refits of a 20,000 × 286 matrix, as drawn and on distinct runs, take about 0.9 s each on
    this Mac under load, about 15 minutes, over the slow tier's 10-minute target alone (even the C30 fake's 400
    resamples took 18 minutes under a load of 40–150). The test then takes about 2 s. The bootstrap's own known
    answers are the golden report's (R3, 1000 resamples, every interval to 4 digits) and PM5's; R1, R10, and R11
    at 20,000 runs run the bootstrap as users run it. This is the fix `contracts.md` (Test tiers) asks a step that
    misses the target to propose.
16. **C18 at d = 20 keeps `D20_SECONDS` = 60 s.** One evaluation with the defaults (1848 × 231, 2000 QR fits) took
    268 s with -n auto while the machine's load average was 40–150 (several agents' test runs); `contracts.md`'s
    19 s was measured idle and as drawn only. The assertion is kept as specified; its result depends on the load
    (see the plan's Notes for the measured runs).

## Deferrals

- **PM10's and PM11's store parts** (a rerun after an interrupt makes 0 new runs; degree 3 after degree 2 reuses
  the runs through the store): step 14, through the workspace. Seams kept: `AnalysisContext.on_progress`, the
  convergent design's nesting (tested on the designs). Effort later: two tests at step 14.
- **The progress throttle's timing** (about once a second) is not tested against a clock: the test checks the
  first and last refits and monotone counts. Effort later: a test with a patched clock, about 15 lines.

## Spec edits on acceptance

- **`diagnostics/polynomial_model.md`, Parameters:** `basis`'s "Changes the design?" could read "no (another is
  refused in v2.0)" (item 3); Named constants: `POLY_NMIN` and `POLY_MIN_RUNS` as the factor 2 (item 5); Minimum
  runs: the too-few note's wording is the precheck's (item 5); the LOO error's note (item 10).
- **`diagnostics/polynomial_model.md`, Expected answers, Time:** R2's at p = 10 compute no intervals (item 15);
  the slow tier's polynomial model tests then take about as long as R11's bootstrap; the LOO refits on distinct
  runs double the bootstrap's time that the Time line and `contracts.md`'s 19 s at d = 20 assume (item 16).
- **`contracts.md`, Test tiers:** the same exception for the polynomial model's R2 known answer (item 15).
- **`architecture.md` §4, `fitting.py`:** `least_squares` solves R with LAPACK's `dtrtrs` (item 14).

## Alternatives considered

- **A reader that refuses unknown samplers and bases** (`Name(choices)`): fails C14, which parses a second value
  before preparing it; refusing at the design keeps "refused before building".
- **Registering a second basis so C14 checks "no" literally:** a fake in the product; the unit test registers one.
- **A faster fit for the bootstrap only** (no Q for the as-drawn refits, semi-normal equations): the resamples'
  numbers would come from another computation than the estimates'; `least_squares` stays the one fit (0068).
- **Batched QR over the 1000 resamples:** the interval-method interface calls an estimator per resample.
- **R2's known answer with the bootstrap, and a slow-tier target of 20 minutes:** the intervals at 20,000 runs are
  not what that test checks.

## Consequences

- **Size:** `polynomial_model.py` is 452 code lines (no docstrings, comments, or blanks) against the roadmap's 400;
  `fitting.py` grows by 3.
- **Tests:** 35 in `tests/unit/diagnostics/test_polynomial_model.py` (29 fast, 6 slow), and the contract's 19 checks
  over the polynomial model.
- Steps 12 (the linear model) and 14 (the workspace) can reuse `Registered` and the per-level and progress patterns.
