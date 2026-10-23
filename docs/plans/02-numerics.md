# 02. Numerics

**Status:** in progress (demo; record 0066). **Branch:** `demo-02-numerics` (merged into `demo` by the
coordinator). **Updated:** 2026-10-02.

## Goal

`ema.numerics` exists (layer 1, pure): the orthonormal Legendre basis and its registry, the Gram spectrum and
its decay rate, the least-squares fits with the rank rule, R², the relative residual and PRESS, the Sobol indices
and √E_k of a fitted polynomial, scatter's rank correlation and binned index, the interval-method interface and
the bootstrap, and P6's tolerance function; with the basis and interval-method contracts (C29, C30) and known
answers, and one rule that keeps them bit-for-bit repeatable on Accelerate (no vector-vector BLAS).

## Implements

- **`docs/design/architecture.md` §4:** `ema.numerics`'s seven modules and their public names (`basis.py`,
  `gram.py`, `fitting.py`, `sobol.py`, `stats.py`, `intervals.py`, `tolerance.py`); the two seams' registries
  (`register`, `get`, `names`, `unregister`; 0065 item 1); §10's contracts grown by `ema.numerics` (AR1 beside
  `ema.designs`, AR2, AR4, AR5, the reference models').
- **`docs/design/uncertainty.md`:** the bootstrap's steps 1–5, its three constants, the rank rule, "none" under
  201 defined resamples; the interface; V1–V6 (V7 needs the diagnostics: steps 10, 12, 13).
- **`docs/design/diagnostics/coordinate_lines.md`, `lines.md`:** the Gram coefficients by Lanczos with full
  reorthogonalization; the tail T(k), the floor's k*, the rate (CL2, CL3's numerics).
- **`diagnostics/linear_model.md`, `polynomial_model.md`:** the fit by QR, the relative residual, R², the LOO
  error by PRESS with QR leverages, the rank rule (0051); the terms and their order, the Sobol indices of the
  fitted polynomial, √E_k (PM2's, PM3's, PM4's numerics).
- **`diagnostics/scatter.md`:** Spearman's ρ with average ranks; the binned first-order index, adjusted for its
  bias (SC's numerics).
- **P6** (`principles.md`; `diagnostics/shared.md`, The precheck): the one tolerance function.
- **`docs/design/contracts.md`:** C29 (`tests/contracts/basis.py`) and C30 (`tests/contracts/interval.py`),
  each with its toy or fake, its broken toys, and the meta-test.
- **`docs/notes/blas_determinism_2026-10-01.md`'s recommendation,** adopted as record 0068 item 1: `dot` and
  `norm` through `np.sum`; Ruff's banned-api (TID251) on the 1-D BLAS calls; a fast-tier test of identical
  bytes at 8 memory offsets.
- **v1:** `core/legendre.py`'s `total_degree_indices`, `n_terms`, `legendre_basis`, ported after re-review into
  `basis.py` ("Ported from EMA v1 at v1-final: src/ema/core/legendre.py"); `diagnostics/_uncertainty.py` read
  only.

## Out of scope for this step

- The diagnostics that call these functions (steps 09–13), and their constants (`LINE_RATE_FLOOR`,
  `SCATTER_BOOT_TAG`, ...): the diagnostics own them; numerics takes them as arguments.
- The basis name in a request's identity (C29's last clause): requests are step T's, the check step 13's.
- V7 (the fake method on the diagnostics) and V4's diagnostic fixtures: steps 10, 12, 13.

## Tasks

1. Write the record (0068), with the BLAS decision first; extend `pyproject.toml` (layers, AR2/AR4/AR5, the
   reference models' contract, TID251) and `docs/index.md`.
2. Tests first: C29, C30 with toys and broken toys; known answers per module (below); the 8-offset test.
3. Write `ema.numerics` until they pass; port v1's basis after re-review.
4. Run every check in `CLAUDE.md`; report lines against §11's 553.

Known answers (each test cites its id):

- Legendre: ψ₁, ψ₂ as `reference_models.md` writes them; orthonormality by Gauss–Legendre quadrature (C29);
  P = C(d + p, p) for d = 1 … 8, p = 1 … 4 (PM2); the stated order.
- Gram: (1/n)GᵀG = I within 10⁻¹³ (CL2); y recovered, c₀ the mean, Σc_k² the variance; agreement with exact
  rational arithmetic (a 30-line test helper, as `coordinate_lines.md`'s "Tests it implies") within 10⁻¹⁴ of the
  range on R7's lines at n = 17, 65, 129; y = Σ10⁻ᵏG_k at n = 33, rate 1 within 10⁻⁶ (CL3); R7 at n = 17 and 33
  along a, b, c, e (Expected answers, 10⁻⁶); R1's k* = 1; R10 along b, k* = 2; scaling by 2⁻¹⁰ exact to 10⁻¹².
- Fits: R10 at p = 2 recovered within 10⁻¹² with its Sobol indices and √E_k (PM2, PM4); R1's √E_1 = √(14/3);
  PRESS against explicit refits on 12 runs in d = 2, p = 2 within 10⁻¹² (PM3); the rank rule against
  `np.linalg.matrix_rank` (0051); a rank-deficient A's fit undefined.
- Scatter: the mock report's ρ and S at R2, n = 200, seed 1 (four digits), and its bootstrap intervals,
  end to end through `Bootstrap` (SC's mock, V1–V3).
- Bootstrap: V1 (bit for bit; another tag, other intervals), V2, V3, V5 ([4.995, 994.005]), V6 (0, 200, 201
  defined), the resamples equal to `spawned(seed, tag).integers(0, n_u, (1000, n_u))`.

## Checks before reporting done

- The fast tier in under 30 s; lint, mypy, import contracts, docs with `-W`; the package's lines against §11's 553.

## Stop condition

The checks pass; the report goes to the coordinator (0066), who has the step reviewed.

## Choices made here

Each is in record 0068, numbered as there, with its reason.

1. No vector-vector BLAS: `dot`/`norm` through `np.sum`, matrix-vector products through `matvec` (a one-row
   matrix through `dot`) (`ema/numerics/_vector.py`); TID251 on `numpy.linalg.norm`, `numpy.dot`, `numpy.inner`,
   `numpy.vdot`, `numpy.vecdot`, `numpy.linalg.vecdot`, `numpy.tensordot`, `numpy.linalg.tensordot`,
   `numpy.linalg.multi_dot`, `numpy.einsum`, `numpy.matmul`, `numpy.linalg.matmul`; an AST test of `.dot(` and
   `@` (only in `matvec`); an 8-offset byte-identity test with the heap scrambled, and negative controls.
2. A constant vector gets exact zeros where rounding would decide a 0/0: a constant line's Gram coefficients are
   (y₀, 0, …, 0) (else k* = K on a floor of 0); the fits and the binned index center a constant y to zeros.
3. `tail(c)` is indexed by degree, k = 0 … n − 1.
4. The window and floor are the caller's: `degrees_above_floor(tail(c)[: K + 1], tolerance(y, LINE_RATE_FLOOR))`.
5. `decay_rate` in closed form with `np.sum`; returns the rate and the line's intercept at k = 0.
6. The Lanczos basis is cached per n, read-only.
7. `least_squares`' rank from R's singular values with 0051's tolerance (about 20% of a fit's time); `rank(A)`
   from A's; they can differ only within rounding of the tolerance.
8. A fit of rank below P has NaN coefficients, residuals, and leverages.
9. `relative_residual(y, fit)`, `r2(y, fit)`, `press(A, y, fit)`: NaN when undefined (for `press`, also a run of
   leverage 1); `press` is the LOO error.
10. `sobol_indices(coef, terms, *, y)` NaN when y is constant (`tolerance.is_constant`, 0035) or V = 0;
    `degree_energy` for k = 1 … p.
11. `binned_index` returns the adjusted S; `rank_correlation` by `rankdata` and Pearson on the ranks.
12. `tolerance` refuses no values, non-finite values, and a negative or non-finite `rel`.
13. The bootstrap: every non-finite value undefined; estimators once per resample, in order; `on_step(b, 1000)`
    after each; the spec's draws taken a row at a time (the same numbers, tested; 160 KB instead of 160 MB).
14. The "none" reason "k of 1000 resamples defined, fewer than 201"; `Interval` checks its fields.
15. `Bootstrap.settings` a fresh plain dict of JSON values per call (`canonical_json` writes it); the levels
    unused.
16. Registry errors as step 01's (0067 item 19).
17. C29 over `total_degree` and a fake tensor basis; C30 over the bootstrap and a fake registered as `fake_range`
    (`tests/support/fakes.py`, for V7 in steps 10, 12, 13).
18. The scatter mock report's intervals reproduced through the numerics (an end-to-end known answer for V1–V3).

## Notes

- **Built** on `demo-02-numerics` (0066); no stop for review; the coordinator commits. Ported from EMA v1 at
  v1-final: `src/ema/core/legendre.py` (`total_degree_indices`, `n_terms`, `legendre_basis`, into
  `basis.py`'s `TotalDegree`), re-reviewed: the order and the normalization agree with `polynomial_model.md` and
  `reference_models.md`; the gradient, the hold-out split, and the term cap are left out (not in v2.0).
  `diagnostics/_uncertainty.py` read only (v2's bootstrap differs: a spawned stream, percentiles 0.5/99.5, distinct
  runs, "none").
- **The BLAS rule probed** (2026-10-02): with `np.linalg.norm` back in the Lanczos process, the 8-offset test fails
  at n = 17; with `np.dot` in `_vector.dot`, the helpers' and Lanczos tests fail. The first version's fits' and
  bootstrap's tests passed either way; the reason first given (16-byte-aligned temporaries, where `ddot` repeats)
  was wrong, since `ddot` varies among those too: numpy's small-block cache kept the temporaries in place, and the
  fixture happened not to show it. Review round 1 fixed both (record 0068, Review round 1).
- **Review round 1** (2026-10-02; record 0068, Review round 1): the banned list grown, `matvec`, and the AST test
  of `.dot(` and `@`; `scramble_heap` and three negative controls (Lanczos, fits, bootstrap) that put BLAS back
  and fail; `Bootstrap.settings` a fresh JSON dict, checked by C30 through `canonical_json`; `is_constant` and
  `sobol_indices(..., y=)`; `least_squares`' rank against `matrix_rank`, with p distinct values along one model
  parameter; R4b's wiggle in the fits, scatter, Sobol, and lines tests; CL2 against exact arithmetic at every
  degree; the C30 fake in `tests/support/fakes.py`.
- **Found while testing:** Lanczos's rounding on a constant line (c_k about 10⁻¹⁷ above a floor of 0) and a mean
  that rounds on a constant y (20 copies of 0.1) would each turn a 0/0 into a number; item 2 fixes both, with tests.
- **Tests:** 164 new (148, and 16 in review round 1) in `tests/unit/numerics/`, `tests/contracts/basis.py`,
  `tests/contracts/interval.py` (and 19 doctests in `ema.numerics`); the fast tier's whole run, the times, and the
  lines are in the report.
- **Deferred** (record 0068): C29's identity clause (step 13); V4's and V7's diagnostic fixtures (steps 10, 12,
  13). Step 13 passes each resample's y to `sobol_indices` (record 0068 item 10).
- **Source lines:** `ema.numerics` 357 code lines (1,009 physical) against §11's 553 (341 before review round 1).
