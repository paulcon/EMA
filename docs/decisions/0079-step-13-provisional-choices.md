# 0079. Step 13's provisional choices: the polynomial model

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

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
    (see the plan's Notes for the measured runs). *Superseded by item 17.*

**Review round 1** (the independent review's major, minors, and nits; fixed on `demo-13fix`, each with a test)

17. **`D20_SECONDS` is 180 s, and C18's bound counts both refits** (amends item 16). One evaluation at d = 20 with
    the defaults, measured alone (`sd.evaluate`, figures off) at a load average of 5–9 on 8 cores: 62 s wall, 91 s
    of CPU (68 s user, 26 s system: Accelerate's threads); profiled, 2003 QR factorizations 42 s (21 ms each,
    `numpy.linalg.qr` forming Q), 2003 SVDs of R 11 s (5.6 ms each, the rank rule), the rest 3 s; the as-drawn
    refits 35 s and the LOO refits on distinct runs (about 1168 rows) 26 s. `contracts.md`'s 19 s counted the
    as-drawn refits only, on another day. No speed-up keeps the numbers bit for bit and brings it under 60 s: the
    time is LAPACK's, and the Python around it is 3 s; the row gather `A[i]` is 0.7 s; skipping Q, the
    semi-normal equations, or a cheaper rank test than R's singular values each change a resample's numbers or its
    rank at the threshold (item 14's alternatives). So the bound is set from the CPU time with a margin of 2: 180 s
    of wall-clock time, one constant (`tests/contracts/diagnostic.py`, imported by the polynomial model's slow test;
    the other diagnostics' C18 at d = 20 in the fast tier takes a few seconds under it). With the slow tier's
    `-n auto` (this step's slow tests and the diagnostic contract, 8 workers, the load average 6–8 when it began),
    the evaluation took 80 s. A load several times the cores' still fails it:
    its wall time grows with the load, as the old Notes' 134–268 s at loads of 36–150 show.
18. **`SPECTRUM_YMIN` has one home, `ema.diagnostics._lines`** (amends item 13): the polynomial model imports it and
    keeps `SPECTRUM_YMIN * values.max()` as its decay figure's limit.
19. **One reader for a registry's name, `ema.diagnostics.base.Name`** (amends item 2; records 0076 item 17, 0078
    item 20): `Registered`, scatter's `SamplerName`, and `_fits.SamplerName` are gone. It reads any well-formed name
    (`^[A-Za-z][A-Za-z0-9_-]*$`), refuses what isn't one naming the registered ones, and leaves an unregistered name
    to the registry's "X comes in a later version" when the design is built. **The schema** is the pattern with the
    registered names as `examples`, not an `enum`: an enum is a client's check before EMA, so "sobol" would be
    refused in other words than G17's and PM1's, and C14's second value couldn't be sent through a validating
    client.
20. **`basis`'s "Changes the design?" is the spec's plain "no"** (replaces item 3), and C14 is amended: a "no"
    parameter whose other value is refused with "comes in a later version" passes, its promise tested by the
    diagnostic's own C29 test (a second basis registered: the same design bit for bit, another reuse key). C14 also
    refuses a declaration other than "yes", "no", or "yes (…)": `lines`' seed ("yes (random lines)") and the
    polynomial model's degree ("yes (through n_min's default)") are the specs' qualified yeses and are now checked
    as yeses on the example request (before, any value but exactly "yes" or "no" went unchecked). A "no (…)"
    fails. Two broken toys show each refusal (a qualified "no"; a "no" refused in other words).
21. **V = 0 on real runs** (corrects item 11's "no QR on any design tried gave exact zeros"): R11's space, degree
    1, 8 runs at (±0.375, ±0.375) with y = 0 and at (±1, ±1) with y = 1: y varies, and the ψ₁ coefficients are
    exactly 0 on this Mac's LAPACK. The test asserts the note, no Sobol table, √E_1 = 0, and the fit and residual
    figures only; it skips, naming the coefficients, where a LAPACK doesn't give exact zeros. The wrapped-fit test
    stays beside it.
22. **The LOO-undefined note is tested** (item 10): 6 runs, d = 2, p = 1, five at a = 0.5 and one at a = −0.3 (its
    leverage is 1): the note, no Held out table, "none" in the per-level table's LOO row.
23. **R2 at p = 10 without intervals (item 15) is an exception to `contracts.md`'s Test tiers**, for the owner to
    accept or refuse: the tier says the expected answers run as users run them, and this one replaces the bootstrap
    with `NoIntervals`; the spec edit below names it.
24. **This step's fast-tier share** is in record 0084 (Review round 2).
25. **Nits.** `fitting.least_squares` raises `ValueError` for `dtrtrs`'s illegal-argument code (info < 0) and
    `LinAlgError` ("R is singular") only for info > 0. The fit figure's data card keeps every usable run in each
    panel, with its run id, x, y, ŷ (`fitted`), and ŷ₋ₖ (`held_out`); a held-out prediction that isn't finite (a
    leverage of 1) is null, and that run is not drawn in the right panel (PM9's card: "each point's run id, y, ŷ,
    and ŷ₋ₖ"). The Sobol figure's legend swatches are a dot with its bar, as the series are drawn
    (`ema.plotting.intervals(..., label=...)`, an empty error bar), not lines. R5's z is tested (Expected answers,
    "R5, y and z"): every estimate equals the polynomial model on z's usable runs alone, and each strip holds every
    run not usable for z.

## Deferrals

- **PM10's and PM11's store parts** (a rerun after an interrupt makes 0 new runs; degree 3 after degree 2 reuses
  the runs through the store): step 14, through the workspace. Seams kept: `AnalysisContext.on_progress`, the
  convergent design's nesting (tested on the designs). Effort later: two tests at step 14.
- **The progress throttle's timing** (about once a second) is not tested against a clock: the test checks the
  first and last refits and monotone counts. Effort later: a test with a patched clock, about 15 lines.

## Spec edits on acceptance

- **`diagnostics/polynomial_model.md`, Parameters:** `basis` stays "no" (item 20); Named constants: `POLY_NMIN` and
  `POLY_MIN_RUNS` as the factor 2 (item 5); Minimum runs: the too-few note's wording is the precheck's (item 5);
  the LOO error's note (item 10); Figures: the fit figure's card holds a held-out prediction that isn't finite as
  null, and the Sobol legend's swatches (item 25).
- **`diagnostics/polynomial_model.md`, Expected answers, Time:** R2's at p = 10 compute no intervals (item 15);
  the slow tier's polynomial model tests then take about as long as R11's bootstrap; the LOO refits on distinct
  runs double the bootstrap's time that the Time line and `contracts.md`'s 19 s at d = 20 assume (item 16).
- **`contracts.md`, Test tiers:** an explicit exception, the polynomial model's R2 known answer at p = 10 computes
  no intervals (items 15, 23); the C18 bullet: "1000 resamples, each a refit of a 1848 × 231 matrix as drawn and
  one on its distinct runs (about 1168 rows) for LOO: about 91 s of CPU, 62 s wall, measured 2026-10-02".
- **`contracts.md`, Named constants:** `D20_SECONDS` is 180 s, "twice the polynomial model's CPU time for one
  evaluation at d = 20 with the defaults, both refits counted" (item 17); C18's row: "within `D20_SECONDS`, which
  counts every refit the evaluation makes".
- **`contracts.md`, C14:** "a parameter whose spec says 'no' and whose other value is refused as 'comes in a later
  version' passes; its promise is tested by the diagnostic's own tests with the other value registered (the
  polynomial model's basis, C29). A declaration is 'yes', 'no', or 'yes (…)', checked as a yes on the example
  request" (item 20).
- **`architecture.md` §4, `fitting.py`:** `least_squares` solves R with LAPACK's `dtrtrs` (item 14); §6, `base.py`:
  `Name`, the one reader for a registry's name (item 19).

## Alternatives considered

- **A reader that refuses unknown samplers and bases** (`Name(choices)`): fails C14, which parses a second value
  before preparing it; refusing at the design keeps "refused before building".
- **Registering a second basis so C14 checks "no" literally:** a fake in the product; the unit test registers one.
- **C14 accepting only exactly "yes" or "no"** (Review round 1): would fail `lines`' seed and the polynomial
  model's degree, whose specs qualify their yes; "yes (…)" is checked as a yes, and a qualified "no" fails.
- **An `enum` in the name's schema, or the pattern alone** (item 19): the enum refuses the next version's names
  before EMA can; the pattern alone tells a client nothing of today's names.
- **`D20_SECONDS` measured as CPU time** (item 17): steadier under load, but C18 promises a user's wait, which is
  wall-clock time; the margin of 2 on the CPU time covers the slow tier's own parallel load.
- **A faster fit for the bootstrap only** (no Q for the as-drawn refits, semi-normal equations): the resamples'
  numbers would come from another computation than the estimates'; `least_squares` stays the one fit (0068).
- **Batched QR over the 1000 resamples:** the interval-method interface calls an estimator per resample.
- **R2's known answer with the bootstrap, and a slow-tier target of 20 minutes:** the intervals at 20,000 runs are
  not what that test checks.

## Consequences

- **Size:** `polynomial_model.py` is 453 code lines (no docstrings, comments, or blanks) against the roadmap's 400
  (452 before Review round 1); `fitting.py` grows by 5. Review round 1 removed 10 lines net across `src/ema`
  (the three readers became one).
- **Tests:** 38 in `tests/unit/diagnostics/test_polynomial_model.py` (32 fast, 6 slow), and the contract's 19 checks
  over the polynomial model.
- Steps 12 (the linear model) and 14 (the workspace) can reuse `base.Name` and the per-level and progress patterns.
