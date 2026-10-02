# 0068. Step 02's provisional choices: no vector-vector BLAS, and the numerics' details

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 02 (`../plans/02-numerics.md`) builds `ema.numerics` on the `demo` branch without the owner's review
(0066). The roadmap's first task for it, measuring BLAS determinism, was done on 2026-10-01
(`../notes/blas_determinism_2026-10-01.md`): on this Mac's Accelerate, every matrix operation (qr, lstsq, svd,
`solve_triangular`, gemv `Q.T @ y`) repeats bit for bit across calls, processes, and memory offsets, but a
vector-vector product (`ddot`, behind `x @ y` of two 1-D arrays, `np.dot`, `np.vecdot`, and `np.linalg.norm` of a
vector) depends on its operands' addresses mod 64, which made the Lanczos basis of `docs/checks/gram_rates.py`
take 2–4 values at n = 9–129. The roadmap asks for a record when anything varies; the banned-api list is Ruff
configuration that 0059 doesn't name. Building the step met further places where the specs
(`../design/architecture.md` §4, `../design/uncertainty.md`, the diagnostic specs' Computation sections) leave a
detail open. Each choice keeps P1–P7 and the specs' intent, and none changes an accepted spec's rule.

## Decision

We will, provisionally:

**Determinism (P4)**

1. **No vector-vector BLAS in `ema`.** Inner products and norms of 1-D arrays go through two helpers in
   `ema/numerics/_vector.py`, `dot(x, y) = float(np.sum(x * y))` and `norm(x) = math.sqrt(dot(x, x))` (numpy's
   pairwise sum, address-invariant), and every matrix-vector product through a third, `matvec(M, x)`: `M @ x`
   (gemv), or `dot` when M has one row, since numpy sends a one-row matrix times a vector to `ddot` too (the
   Lanczos process's first step, a fit with one term). Matrix products with two rows or more, `qr`, `svd`, and
   `solve_triangular` stay on BLAS/LAPACK. Ruff's banned-api rule (TID251) refuses `numpy.linalg.norm`,
   `numpy.dot`, `numpy.inner`, `numpy.vdot`, `numpy.vecdot`, `numpy.linalg.vecdot`, `numpy.tensordot`,
   `numpy.linalg.tensordot`, `numpy.linalg.multi_dot`, `numpy.einsum`, `numpy.matmul`, and `numpy.linalg.matmul`
   in `src/ema` (not in `tests/`); an AST test refuses what Ruff can't see, `.dot(` method calls anywhere in
   `src/ema` and `@` outside `_vector.matvec` (review round 1). A fast-tier test
   (`tests/unit/numerics/test_determinism.py`) asserts identical bytes at 8 memory offsets for the helpers, the
   Lanczos basis and spectrum (n = 9–129), the fits (with R², the relative residual, PRESS, the tolerance, ρ, S)
   on 15 fixtures, and the bootstrap, with numpy's small-block cache emptied and malloc moved before each call,
   so a function's own temporaries move too; three negative controls put BLAS back (`np.dot`, `np.linalg.norm`)
   in the Lanczos process, the fits and scatter, and the bootstrap's refits, and show each test then fails. The
   measured `ddot` varies among 16-byte-aligned operands too (2 values at n = 9, 17, 80, and others), so no
   placement of numpy's temporaries makes it safe. Not chosen (the note's table): single-threaded BLAS (doesn't fix
   it; `threadpoolctl` doesn't see Accelerate), all-elementwise products with a Householder QR (10–21× slower
   QR), the exact Gram basis (contradicts `coordinate_lines.md`). No dependency added.
2. **Exact zeros for a constant vector, where rounding would decide a 0/0** (0035, the bootstrap's step 3):
   - `gram_coefficients` of a line whose values are all the same double returns exactly (y₀, 0, …, 0): Lanczos
     leaves c_k at about 10⁻¹⁷, and a constant line's floor (10⁻¹⁰ of a range of 0) is 0, so k* would be K and
     a rate would be fitted to rounding. With exact zeros, k* = 0 and there is no rate (CL6).
   - The fits' ‖y − ȳ‖ and scatter's binned index center a constant y to exact zeros (`_vector.centered`): the
     mean of 20 copies of 0.1 isn't 0.1, and the relative residual, R², LOO, and S would be an O(1) ratio of
     rounding instead of undefined.

**`gram.py`**

3. **`tail(c)` is indexed by degree,** k = 0 … n − 1, so `T[k]` is T(k); T(0), which includes c₀, is kept for
   the indexing and not used by the rate.
4. **The window and the floor stay coordinate lines' constants:** `degrees_above_floor(T, floor)` counts k = 1,
   2, … while T(k) > floor, over the T it is given, so the caller passes `tail(c)[: K + 1]` and the absolute floor
   `tolerance(y, LINE_RATE_FLOOR)`.
5. **`decay_rate`** fits log₁₀ T(k) against k in closed form with `np.sum` (not `polyfit`), and returns the rate
   and the fitted line's intercept, log₁₀ T at k = 0 (for the spectrum figure's tail fit).
6. **The Lanczos basis** (from ones, two passes of reorthogonalization, as `gram_rates.py`) is built once per n
   and cached (16 sizes), read-only.

**`fitting.py`**

7. **The rank in `least_squares`** is computed from R's singular values (A's in exact arithmetic; `svd` of the
   P × P factor, not of the n × P matrix) with 0051's tolerance max(n, P)·ε·σ_max and A's shape; `rank(A)`
   applies the same rule to A's own singular values. Both pass a comparison with `np.linalg.matrix_rank`, also on
   resamples that take only p distinct values along one model parameter (rank P − 1, a singular value near
   ε·σ_max). R's and A's computed singular values differ only by rounding, so the two ranks can differ only for a
   singular value within rounding of the tolerance. Cost: the P × P `svd` is about 20% of a fit's time (n = 360,
   P = 15: 0.04 of 0.19 ms), against about 100% for A's.
8. **A fit of rank below P is undefined:** its coefficients, residuals, and leverages are NaN, with its rank, so
   every estimate from it is undefined (dropped and counted in a bootstrap).
9. **`relative_residual(y, fit)`, `r2(y, fit)`, `press(A, y, fit)`** (§4 names them without signatures) give NaN
   on a constant y, an undefined fit, a non-finite result, and, for PRESS, fewer than P + 1 runs or a run of
   leverage 1 (r_k/0, so its left-out residual is unknown); PRESS is the LOO *error* of the specs
   (√Σ(r_k/(1 − h_kk))² / ‖y − ȳ‖), not the raw sum of squares.

**`sobol.py`, `stats.py`, `tolerance.py`**

10. **`sobol_indices(coef, terms, *, y)` gives NaN arrays when y is constant or V = 0** (0035, 0049;
    `polynomial_model.md`, Uncertainty): a fit to a constant y has coefficients at rounding level (on 40 runs of
    0.1, V ≈ 3·10⁻³⁴, which gave indices 0.169, 0.205, 0.302), so V alone can't tell (review round 1). The test of
    "constant" is one public function, `ema.numerics.tolerance.is_constant(y)`: every value the same double, by
    `==`; an empty y isn't constant. `gram_coefficients` and `_vector.centered` use it too. **Step 13 must** pass
    each resample's y, as drawn, to `sobol_indices` (and the level's y at level L), and give the constant-y note
    from `is_constant` before fitting. **`degree_energy`** gives √E_k for k = 1 … the terms' largest total degree.
11. **`binned_index(x, y, bins)` returns the adjusted index S** (step 4), NaN on a constant y or n ≤ B; it refuses
    fewer than 1 bin or more bins than runs. **`rank_correlation`** uses `scipy.stats.rankdata` (average ranks)
    and Pearson's formula on the ranks, NaN when either is constant.
12. **`tolerance(values, rel)`** refuses no values, a non-finite value, and a negative or non-finite `rel`.

**`intervals.py`**

13. **The bootstrap counts every non-finite value as undefined** (NaN and ±inf: x/0 gives inf), calls each
    estimator once per resample in the estimators' order, and calls `on_step(b, 1000)` after each resample (the
    diagnostic throttles its progress to about once a second). It draws the spec's
    `integers(0, n_u, (1000, n_u))` one row per resample: numpy 2.5 gives the same numbers (a test compares
    them with the single call at n_u = 7, 10, 201), and the draws take 160 KB rather than 160 MB at the
    known-answer size (20,000 runs). If a numpy release changed that, the test fails, and the single call returns.
14. **The "none" reason** is "k of 1000 resamples defined, fewer than 201"; the report writes "none: " before it
    (`uncertainty.md`'s line). **`Interval`** refuses bounds with a reason, no bounds without one, non-finite or
    reversed bounds, and a negative count.
15. **`Bootstrap.settings`** is a property that returns a fresh plain dict of JSON values on each call,
    `{"resamples": 1000, "percentiles": [0.5, 99.5], "min_defined": 201}`: a caller's change to it can't reach the
    method, `ema.types.identity.canonical_json` writes it as it is, and a stored copy reads back equal (a
    `MappingProxyType`, the first choice, made `canonical_json` raise `TypeError`; review round 1).
    `IntervalMethod.settings` is a read-only property in the protocol, and C30 checks that
    `canonical_json(dict(method.settings))` writes any method's. The levels are not used by the bootstrap (the
    caller passes level L's usable runs).
16. **Registries** as step 01's (0067 item 19): `register` of a taken name and `unregister` of a missing one
    raise `ValueError`; `get` raises `RequestError`, "basis X comes in a later version" and "interval method X
    comes in a later version".

**Tests**

17. **C29's contract** runs over `total_degree` and a fake tensor-product basis (the same Legendre functions, a
    different index set), with Gauss–Legendre grids of p + 2 points per model parameter; its broken toy has
    unnormalized terms. **C30's** runs over the bootstrap and a toy (400 resamples, the range of the defined
    values, "none" under 10, `on_step` after each resample), registered as `fake_range`; its four broken toys are
    the contract's. The fake is `tests.support.fakes.FakeIntervalMethod`, with `registered_interval_method()`, for
    V7's fixtures in steps 10, 12, and 13.
18. **The scatter mock report's intervals** (R2, n = 200, seed 1) are reproduced through `Bootstrap`,
    `rank_correlation`, and `binned_index` to 4 digits: an end-to-end known answer for V1–V3 before the
    diagnostic exists.

## Deferrals

- **C29's last clause** (the basis name in a request's identity): requests are step T's, and the check is the
  polynomial model's (step 13). Effort later: one assertion in step 13's identity test.
- **V4's and V7's diagnostic fixtures** (scatter's two-valued fixture, the linear model at 2(d + 1); the fake
  method on three diagnostics): steps 10, 12, 13, whose diagnostics they need. The numerics side (counting,
  "none", the fake through the registry) is tested here.
- **`STATUS.md`** and `docs/decisions/README.md`: the coordinator's (0066).

## Spec edits on acceptance

None is required. Clarifications that would help: `architecture.md` §4, the signatures of `r2`,
`relative_residual` (`(y, fit)`), and that `press` returns the LOO error; `sobol_indices(coef, terms, *, y)`
(item 10); `tolerance.py`'s second public name, `is_constant(y)` (item 10); `IntervalMethod.settings` as a
read-only property of JSON values (item 15); `tail`'s indexing and that the window is the caller's (items 3–4);
`uncertainty.md`, that non-finite values are undefined (item 13); `contracts.md` or `architecture.md` §1, the
TID251 rule and the AST test beside AR2 (item 1), and `_vector.matvec` for every matrix-vector product.

## Review round 1

The independent review (2026-10-02) found no blockers or majors, and every number verified. Fixed:

- **The BLAS rule's gaps** (item 1): `np.linalg.vecdot`, `x.dot(y)`, `np.tensordot(x, y, 1)`, `x @ y`, and a
  one-row matrix product each gave 2–4 values at 8 offsets, and the record's reason for the fits' and the
  bootstrap's tests passing (16-byte-aligned temporaries repeat) was false: `ddot` gives 2 values among them at
  n = 9, 65, 100, 129, 200, 1000. Now: the longer banned list; `matvec` for every matrix-vector product (the
  Lanczos process's first projection was a one-row product); the AST test of `.dot(` and `@`; the heap scrambled
  between calls (numpy's small-block cache kept the temporaries in place), and negative controls that put BLAS
  back and fail. Banned beyond the review's two because each reduces to `ddot` and was measured varying
  (`multi_dot`, `einsum` with `optimize`) or is `@` by another name (`matmul`); `scipy.linalg.norm` and
  `np.linalg.vector_norm` were measured not varying and are not banned.
- **`Bootstrap.settings`** (item 15): a fresh dict of JSON values, not a `MappingProxyType`.
- **Sobol indices on a constant y** (item 10): `is_constant`, and `sobol_indices` takes y.
- **The rank rule's tests** (item 7): `least_squares`' rank checked against `matrix_rank` too, and on resamples
  with p distinct values along one model parameter.
- **0035's second half**: R4b's 10⁻¹² wiggle gives finite fit numbers, ρ, S, Sobol indices, and lines with
  k* ≥ 3, each tested.
- **Nits:** record item numbers in docstrings; CL2's comparison with exact rational arithmetic at every degree
  (within 2.3·10⁻¹⁶ of the range; the deferral is gone); PRESS's NaN at leverage 1 (item 9); the cost of `svd(R)`
  (item 7); the C30 fake moved to `tests/support/fakes.py` (item 17).

## Review round 2

The minor findings left from wave 2 (m3 and a nit). Fixed:

- **The banned list, longer** (item 1; P4): `numpy.cov`, `numpy.corrcoef`, `scipy.stats.pearsonr`,
  `scipy.stats.linregress`, and `operator.matmul` (`@` by another name); the AST test also refuses
  `__matmul__`, `__rmatmul__`, and `__imatmul__`, as attributes or strings. Neither sees a library's internals:
  step 09's diagnostic contract checks each whole compute for identical bytes at memory offsets (said in
  `pyproject.toml`). Nothing in `src` used a newly banned name.
- **The bootstrap with no usable runs** (item 15): a `ValueError` naming it, not 1,000 resamples of nothing (the
  precheck refuses first; this is the method's own guard).

## Alternatives considered

- **`degrees_above_floor` taking n and applying the window itself:** puts `LINE_RATE_WINDOW`, a diagnostic
  constant, in layer 1.
- **A flatness tolerance for "constant"** instead of exact equality: 0035 and `shared.md` say there is none.
- **Rank from A's singular values in every refit:** an n × P SVD per resample, about as costly again as the QR;
  R's are the same singular values.
- **An allowlist of reviewed `@` uses** instead of `matvec` (review round 1): each use would have to be argued to
  have two rows or more for every input; `matvec` makes one-row inputs safe by construction, and the AST test
  stays one line.
- **`settings` as a `MappingProxyType`, documented as `dict(...)` first:** every caller would need to know it; a
  fresh dict costs nothing at one call per diagnostic.
- **`sobol_indices` without y, the caller checking:** a caller that forgets gets indices of rounding (v1's G1).
- **Drawing the bootstrap's resamples in one call,** as the spec writes it: the same numbers (item 13), and up
  to 160 MB held for the whole analysis.
- **An `Interval` with no checks** (the stub's): a "none" with no reason would reach the report.

## Consequences

- `pyproject.toml`: `TID251` selected, the banned-api table, `tests/**` exempt; `ema.numerics` beside
  `ema.designs` in AR1's layers, and in AR2's, AR4's, AR5's, and the reference models' source modules.
- **Size:** `ema.numerics` is 357 code lines (no docstrings, comments, or blank lines; 1,009 physical), against
  §11's 553.
- Every later diagnostic computes inner products, norms, and matrix-vector products with `ema.numerics._vector`
  (a private module imported across packages: a later record may make it public, `ema.numerics.vector`); a new
  `@` anywhere in `src/ema` fails the AST test until it goes through `matvec` or is reviewed and listed in
  `MATMUL_ALLOWED`.
- The fits' rank costs a P × P `svd` per fit, about 20% of a fit's time (item 7).
