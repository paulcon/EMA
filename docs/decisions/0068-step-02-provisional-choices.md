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
   pairwise sum, address-invariant); matrix products, `qr`, `svd`, and `solve_triangular` stay on BLAS/LAPACK.
   Ruff's banned-api rule (TID251) refuses `numpy.linalg.norm`, `numpy.dot`, `numpy.inner`, `numpy.vdot`, and
   `numpy.vecdot` in `src/ema` (not in `tests/`). A fast-tier test (`tests/unit/numerics/test_determinism.py`)
   asserts identical bytes at 8 memory offsets for the helpers, the Lanczos basis and spectrum (n = 9–129), the
   fits (with R², the relative residual, PRESS, the tolerance, ρ, S), and the bootstrap. Probed: with `np.dot`
   put back in `dot`, the helpers' and Lanczos tests fail; the fits' and bootstrap's still pass, since the vectors
   they reduce are numpy's own 16-byte-aligned temporaries, where the measured `ddot` repeats; those two guard
   their inputs' placement. Not chosen (the note's table): single-threaded BLAS (doesn't fix it; `threadpoolctl`
   doesn't see Accelerate), all-elementwise products with a Householder QR (10–21× slower QR), the exact Gram
   basis (contradicts `coordinate_lines.md`). No dependency added.
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
   applies the same rule to A's own singular values. Both pass a comparison with `np.linalg.matrix_rank`.
8. **A fit of rank below P is undefined:** its coefficients, residuals, and leverages are NaN, with its rank, so
   every estimate from it is undefined (dropped and counted in a bootstrap).
9. **`relative_residual(y, fit)`, `r2(y, fit)`, `press(A, y, fit)`** (§4 names them without signatures) give NaN
   on a constant y, an undefined fit, a non-finite result, and, for PRESS, fewer than P + 1 runs; PRESS is the LOO
   *error* of the specs (√Σ(r_k/(1 − h_kk))² / ‖y − ȳ‖), not the raw sum of squares.

**`sobol.py`, `stats.py`, `tolerance.py`**

10. **`sobol_indices` gives NaN arrays when V = 0** (0049); a fit to a constant y has coefficients at rounding
    level, so the diagnostic's estimator treats a constant y as undefined itself. **`degree_energy`** gives √E_k
    for k = 1 … the terms' largest total degree.
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
15. **`Bootstrap.settings`** is `{"resamples": 1000, "percentiles": (0.5, 99.5), "min_defined": 201}`, read-only.
    The levels are not used by the bootstrap (the caller passes level L's usable runs).
16. **Registries** as step 01's (0067 item 19): `register` of a taken name and `unregister` of a missing one
    raise `ValueError`; `get` raises `RequestError`, "basis X comes in a later version" and "interval method X
    comes in a later version".

**Tests**

17. **C29's contract** runs over `total_degree` and a fake tensor-product basis (the same Legendre functions, a
    different index set), with Gauss–Legendre grids of p + 2 points per model parameter; its broken toy has
    unnormalized terms. **C30's** runs over the bootstrap and a toy (400 resamples, the range of the defined
    values, "none" under 10), registered as `fake_range`; its four broken toys are the contract's.
18. **The scatter mock report's intervals** (R2, n = 200, seed 1) are reproduced through `Bootstrap`,
    `rank_correlation`, and `binned_index` to 4 digits: an end-to-end known answer for V1–V3 before the
    diagnostic exists.

## Deferrals

- **C29's last clause** (the basis name in a request's identity): requests are step T's, and the check is the
  polynomial model's (step 13). Effort later: one assertion in step 13's identity test.
- **V4's and V7's diagnostic fixtures** (scatter's two-valued fixture, the linear model at 2(d + 1); the fake
  method on three diagnostics): steps 10, 12, 13, whose diagnostics they need. The numerics side (counting,
  "none", the fake through the registry) is tested here.
- **The exact-rational comparison at every degree:** CL2's test compares c_0 … c_K, as `gram_rates.py` does; the
  top half of the spectrum is checked by orthonormality and by recovering y.
- **`STATUS.md`** and `docs/decisions/README.md`: the coordinator's (0066).

## Spec edits on acceptance

None is required. Clarifications that would help: `architecture.md` §4, the signatures of `r2`,
`relative_residual` (`(y, fit)`), and that `press` returns the LOO error; `tail`'s indexing and that the window is
the caller's (items 3–4); `uncertainty.md`, that non-finite values are undefined (item 13); `contracts.md` or
`architecture.md` §1, the TID251 rule beside AR2 (item 1).

## Alternatives considered

- **`degrees_above_floor` taking n and applying the window itself:** puts `LINE_RATE_WINDOW`, a diagnostic
  constant, in layer 1.
- **A flatness tolerance for "constant"** instead of exact equality: 0035 and `shared.md` say there is none.
- **Rank from A's singular values in every refit:** an n × P SVD per resample, about as costly again as the QR;
  R's are the same singular values.
- **Drawing the bootstrap's resamples in one call,** as the spec writes it: the same numbers (item 13), and up
  to 160 MB held for the whole analysis.
- **An `Interval` with no checks** (the stub's): a "none" with no reason would reach the report.

## Consequences

- `pyproject.toml`: `TID251` selected, the banned-api table, `tests/**` exempt; `ema.numerics` beside
  `ema.designs` in AR1's layers, and in AR2's, AR4's, AR5's, and the reference models' source modules.
- **Size:** `ema.numerics` is 341 code lines (no docstrings, comments, or blank lines; 940 physical), against
  §11's 553.
- Every later diagnostic computes norms of vectors with `ema.numerics._vector` (a private module imported across
  packages: a later record may make it public, `ema.numerics.vector`).
