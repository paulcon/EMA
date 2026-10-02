# BLAS determinism on this Mac (2026-10-01)

> A measurement for roadmap step 02's first task (`STATUS.md`, Next; consistency review, D). A note, not a
> spec: what it recommends is decided by a record. Scratch scripts, not kept.

## What was measured

- **Setup:** Intel Core i7-1068NG7 (4 cores, AVX-512), macOS 14.8.7; Python 3.14.7, numpy 2.5.3, scipy 1.18.1
  (both report BLAS and LAPACK = Accelerate), threadpoolctl 3.7.0.
- **Polynomial model:** A of n_u × P Legendre terms at the default 8P runs: (d, p) = (20, 1) 168 × 21;
  (3, 2) 80 × 10; (8, 2) 360 × 45; (2, 10) 528 × 66; (8, 3), (3, 8) 1320 × 165; (20, 2) 1848 × 231; (8, 4)
  3960 × 495; (20, 3) 14168 × 1771. Operations: `np.linalg.qr`; the fit (qr, `Q.T @ y`,
  `scipy.linalg.solve_triangular`, leverages); `np.linalg.lstsq`; `svd` values; `scipy.linalg.qr`, `lstsq`;
  5 bootstrap refits; `Q.T @ y` and elementwise alternatives; a Householder QR without matmul.
- **Coordinate lines:** Lanczos with full reorthogonalization as `docs/checks/gram_rates.py` writes it (two
  passes of `w -= Q[:, :k] @ (Q[:, :k].T @ w)`, then `w /= np.linalg.norm(w)`), n = 9 … 257; `c = Q.T @ y / n`.
- **Repeats:** 50 calls per process (10 at 14168 × 1771), each on fresh copies at a new heap address; 5
  processes (3 at the largest); three modes: default, `threadpool_limits(1)`, and `VECLIB_MAXIMUM_THREADS=1
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` set before Python starts. Then an **address probe**: each operand
  placed at byte offsets 0, 8, …, 56 from a 64-byte boundary. Then the threaded fits under 8 busy processes.

## Results

Differences are max |x − x₀| / max |x₀| in eps = 2.2·10⁻¹⁶ (ulps mislead: entries near zero change sign).
Each row behaved the same in all three modes.

| Operation | 50 calls | 5 processes | 8 offsets |
|---|---|---|---|
| qr, fit, lstsq, svd, scipy qr/lstsq, bootstrap refits (all sizes) | identical | identical | identical |
| `Q.T @ y`, `np.dot(Q.T, y)` (2-D × 1-D, gemv) | identical | identical | identical |
| `einsum(optimize=False)`, `add.reduce(..., axis=0)`, `np.sum(x * x)` | identical | identical | identical |
| Lanczos as in `gram_rates.py`, n = 9–65 | **2–3 bases**, ≤ 8.3 eps | **2–4** | **2–4** |
| the same, n = 129, 257 | identical | identical | **4** (n = 129) |
| Lanczos with norm `math.sqrt(np.sum(w * w))`, n = 9–257 | identical | identical | identical |
| 1-D · 1-D: `x @ y`, `np.dot(x, x)`, `np.linalg.norm(x)`, `np.vecdot` | — | — | **2–4 values** |

- **The cause is the address, not threads.** Accelerate's vector-vector `ddot` result depends on its
  operands' addresses mod 64, and is repeatable at a fixed address. `np.linalg.norm` of a vector is
  `sqrt(dot(x, x))`. The reorthogonalization's matrix-vector products are address-invariant at every n and
  k tried, so STATUS's "matrix products" should read "the norm".
- **Single-threading doesn't help:** the env-var mode varies exactly as the default. `threadpoolctl` does not
  see Accelerate (`threadpool_info()` is empty); its limit is a no-op.
- **Threads change bits but not repeatability:** default and single-threaded results differ from each other
  (QR's Q by up to 18 eps at 14168 × 1771), but each repeats itself, across processes and under load (20 of 20
  calls at (8, 3), (8, 4), (20, 2); 3 of 3 at (20, 3)). P4's "same machine, same libraries" assumes BLAS's
  thread setting unchanged.
- **Times** (ms per call): fit at 3960 × 495, 141 (single-threaded 174); QR at 14168 × 1771, 3800 (6350);
  Householder QR without matmul, 2940 at 3960 × 495 (21×), 280 at 1848 × 231 (10×); Lanczos at n = 129, 2.1,
  with the pairwise norm 2.2, all elementwise 7.1.

## Recommendation for step 02

Keep the Lanczos process as `coordinate_lines.md` specifies (no conflict with it or C7), and give
`ema.numerics` one rule: **no vector-vector BLAS.** Inner products and norms of 1-D arrays go through two
helpers, `dot(x, y) = float(np.sum(x * y))` and `norm(x) = math.sqrt(dot(x, x))` (numpy's pairwise sum,
address-invariant above); matrix products, qr, lstsq, and `solve_triangular` stay on BLAS/LAPACK. The rule also
covers the fits' ‖r‖ and ‖y − ȳ‖ (relative residual, R², LOO).

- **Enforcement:** Ruff's banned-api (TID251) on `numpy.linalg.norm`, `numpy.dot`, `numpy.inner`,
  `numpy.vdot`, `numpy.vecdot` in `src/ema`. `x @ y` on two 1-D arrays can't be caught statically, so a
  fast-tier test runs the Lanczos basis, the fits, and the bootstrap on inputs at the 8 offsets and asserts
  identical bytes; it also guards OpenBLAS (the Linux checks) and Apple-silicon Accelerate, not measured here.
- **Cost:** ~10 lines and a ~40-line test; no dependency; Lanczos 4% slower; no fit slower.

| Not recommended | Fixes it? | Cost |
|---|---|---|
| `VECLIB_MAXIMUM_THREADS=1` before numpy loads | no | QR 1.2–1.7× slower (the d = 20, p = 3 bootstrap ~54 → ~90 min); code before `import numpy` (AR2, AR7) |
| `threadpoolctl` | no | a new dependency, a record |
| All-elementwise products and Householder QR | yes | QR 10–21× slower: that bootstrap takes many hours |
| Exact Gram basis | lines only | contradicts `coordinate_lines.md` |

A record is still needed: the roadmap asks for one when anything varies, and the banned-api list is Ruff
configuration that 0059 doesn't name.
