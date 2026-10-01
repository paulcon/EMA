"""Check the truths stated in docs/design/reference_models.md, "The models" (step 11).

Independent of EMA's code: numpy, scipy, the standard library, and refmodels.py only. What it checks:

- R1: exactly linear in unit coordinates, with coefficients 10; 3, -1, 0, 2; R1(nominal) = 10 in doubles.
- R2: first-order and total Sobol indices from the closed-form variances, and by Monte Carlo (Saltelli 2010
  first-order, Jansen total; N = 2**20, seed 20261001) as a cross-check.
- R3: each nominal value at the center of its range (r: within 1e-12 in unit coordinates).
- R4b: the relative spread (max - min) / max|y| (diagnostics/shared.md): analytic, and over scatter's
  n = 20,000 design at seed 0 (the `random` sampler: default_rng(0).random((n, d))).
- R5: the measures of the error and timeout regions, their overlap, and the share of z missing.
- R6: 1e-8 * R1(nominal) = 1e-7.
- R7: the given (1, 1) line crosses the kink at a = e = 0.3; the kink and the jump off the grids of
  coordinate lines and of the (1, 1) line, n = 17, 33, 65, 129. (The (1, -1) line along the kink was dropped
  by 0058: whether it is constant depends on how the anchor is converted.)
- R3, for polynomial_model.md's comparison under its mock report: the model's own total indices, by tensor
  Gauss-Legendre quadrature (7 and 8 points per model parameter).
- R8: 97 distinct points in its coordinate lines at n = 17.
- R10: the variance 6.5 and the Sobol indices.
- R11: c_0, c_2, c_4, c_6 by Gauss-Legendre quadrature (200 points), c_0 analytically (arctan(2)/2) and by
  scipy's adaptive quad; the ratios c_k / c_(k+2) at k = 2 and 18, and -phi^2; the Sobol indices of the full
  function (closed form from the 1-D moments) and of its degree-10 projection.

Run: ../../../EMA-v1/.venv/bin/python truths.py > truths.out (from docs/checks/).
"""

from __future__ import annotations

import math
import time
from fractions import Fraction

import numpy as np
from scipy import integrate

import refmodels as R

T0 = time.time()
ROWS: list[tuple[str, str, str, str]] = []


def row(model, quantity, stated, computed, ok):
    ROWS.append((model, quantity, stated, computed, "ok" if ok else "DIFFERS"))


def close(a, b, tol):
    return abs(a - b) <= tol


# ---- R1 ----
rng = np.random.default_rng(1)
z = rng.uniform(-1, 1, (1000, 4))
y = R.evaluate_unit("R1", z)
A = np.column_stack([np.ones(len(z)), z])
coef = np.linalg.lstsq(A, y, rcond=None)[0]
resid = np.max(np.abs(y - A @ coef))
row("R1", "unit-coordinate coefficients (1, a, b, c, k)", "10; 3, -1, 0, 2",
    ", ".join(f"{c:.15g}" for c in coef) + f" (max residual {resid:.1e})",
    np.allclose(coef, [10, 3, -1, 0, 2], atol=1e-12) and resid < 1e-12)
nom = R.r1({"a": 1.0, "b": 0.0, "c": 15.0, "k": 10.0})
row("R1", "R1(nominal) in doubles", "10 exactly", repr(float(nom)), nom == 10.0)
row("R1", "log10(10) in doubles", "1 exactly", repr(math.log10(10.0)), math.log10(10.0) == 1.0)

# ---- R2 ----
a, b = 7.0, 0.1
pi = math.pi
V1 = 0.5 * (1 + b * pi**4 / 5) ** 2
V2 = a**2 / 8
V13 = b**2 * pi**8 * (1 / 18 - 1 / 50)
V = V1 + V2 + V13
S = {"x1": (V1 / V, (V1 + V13) / V), "x2": (V2 / V, V2 / V), "x3": (0.0, V13 / V)}
stated2 = {"x1": (0.3139, 0.5576), "x2": (0.4424, 0.4424), "x3": (0.0, 0.2437)}
row("R2", "variance (closed form)", "13.84 (linear_model.md)", f"{V:.6f}", close(V, 13.84, 0.005))
for k in S:
    row("R2", f"{k} first-order; total (closed form)", f"{stated2[k][0]}; {stated2[k][1]}",
        f"{S[k][0]:.6f}; {S[k][1]:.6f}",
        close(S[k][0], stated2[k][0], 5e-5) and close(S[k][1], stated2[k][1], 5e-5))
row("R2", "mean (closed form: 7/2)", "3.5", f"{a / 2}", a / 2 == 3.5)


def saltelli_jansen(model, d, n, seed):
    """Saltelli (2010) first-order and Jansen (1999) total indices under the uniform distribution on [-1, 1]^d."""
    g = np.random.default_rng(seed)
    zA = g.uniform(-1, 1, (n, d))
    zB = g.uniform(-1, 1, (n, d))
    fA, fB = R.evaluate_unit(model, zA), R.evaluate_unit(model, zB)
    var = np.var(np.concatenate([fA, fB]))
    first, total = [], []
    for i in range(d):
        zAB = zA.copy()
        zAB[:, i] = zB[:, i]
        fAB = R.evaluate_unit(model, zAB)
        first.append(np.mean(fB * (fAB - fA)) / var)
        total.append(0.5 * np.mean((fA - fAB) ** 2) / var)
    return np.array(first), np.array(total)


MC_N, MC_SEED = 2**20, 20261001
f_mc, t_mc = saltelli_jansen("R2", 3, MC_N, MC_SEED)
for i, k in enumerate(S):
    row("R2", f"{k} first-order; total (Monte Carlo, N = 2^20, seed {MC_SEED})",
        f"{stated2[k][0]}; {stated2[k][1]}", f"{f_mc[i]:.4f}; {t_mc[i]:.4f}",
        close(f_mc[i], S[k][0], 0.01) and close(t_mc[i], S[k][1], 0.01))

# ---- R3 ----
for name, (lo, hi, scale, nominal) in R.SPACES["R3"].items():
    if scale == "log":
        zc = 2 * (math.log(nominal) - math.log(lo)) / (math.log(hi) - math.log(lo)) - 1
        center = math.sqrt(lo * hi)
    else:
        zc = 2 * (nominal - lo) / (hi - lo) - 1
        center = (lo + hi) / 2
    row("R3", f"{name}: nominal at the {'geometric ' if scale == 'log' else ''}center",
        f"{nominal}", f"center {center!r}; unit coordinate {zc:.1e}", abs(zc) <= 1e-12)

# ---- R4b ----
spread_analytic = 2e-12 / (2.5 + 1e-12)
u = np.random.default_rng(0).random((20_000, 3))
p = R.to_physical("R4", 2 * u - 1)
y4 = R.r4b(p)
spread_design = (y4.max() - y4.min()) / np.max(np.abs(y4))
row("R4b", "relative spread (max - min)/max|y|, analytic", "about 8e-13", f"{spread_analytic:.4e}",
    close(spread_analytic, 8e-13, 1e-15))
row("R4b", "relative spread at n = 20,000, seed 0", "about 8e-13",
    f"{spread_design:.4e} ({len(np.unique(y4))} distinct doubles)", close(spread_design, 8e-13, 0.01 * 8e-13))
y4a = R.r4a(p)
row("R4a", "distinct values at n = 20,000", "1", f"{len(np.unique(y4a))}", len(np.unique(y4a)) == 1)

# ---- R5 (exact areas, in fractions of the area 4 of [-1, 1]^2) ----
err_area = Fraction(1, 2)  # the triangle (0, 1), (1, 0), (1, 1)
to_area = Fraction(2, 10) ** 2
miss_area = Fraction(2, 10) * 2 - Fraction(18, 100)  # the strip b > 0.8, less its part with a + b > 1
row("R5", "error region a + b > 1: share of the space", "1/8", f"{err_area / 4}", err_area / 4 == Fraction(1, 8))
row("R5", "timeout region a, b < -0.8: share", "1/100", f"{to_area / 4}", to_area / 4 == Fraction(1, 100))
g5 = np.random.default_rng(5)
zz = g5.uniform(-1, 1, (4_000_000, 2))
_, z5, er, to = R.r5({"a": zz[:, 0], "b": zz[:, 1]})
row("R5", "error and timeout regions overlap", "no (implied)", f"{int(np.sum(er & to))} of 4e6 points in both",
    not np.any(er & to))
miss = np.isnan(z5) & ~er & ~to
row("R5", "z missing (b > 0.8, not failed): share", "not stated",
    f"{miss_area / 4} = {float(miss_area / 4)}; Monte Carlo (4e6, seed 5) {miss.mean():.4f}",
    abs(miss.mean() - float(miss_area / 4)) < 0.001)
row("R5", "error and timeout shares, Monte Carlo (4e6, seed 5)", "0.125; 0.01",
    f"{er.mean():.4f}; {to.mean():.4f}", abs(er.mean() - 0.125) < 0.001 and abs(to.mean() - 0.01) < 3e-4)

# ---- R6 ----
r6b_sd = 1e-8 * float(nom)
row("R6b", "standard deviation 1e-8 * R1(nominal)", "1e-7", repr(r6b_sd), close(r6b_sd, 1e-7, 1e-22))

# ---- R7 ----
order7 = ("a", "b", "c", "e")


def r7_at(zpts):
    return R.evaluate_unit("R7", zpts)


# the (1, 1) line through the nominal point: the kink where a + e = 0.6
t = 0.3
row("R7", "(1, 1) line through nominal crosses the kink at", "a = e = 0.3", f"a = e = {t} (a + e - 0.6 = {t + t - 0.6:.1e})",
    abs(2 * t - 0.6) < 1e-15)

# off the grids: coordinate lines' points z_j = -1 + 2 j / (n - 1); the (1, 1) line's a = e = the same
for n in (17, 33, 65, 129):
    zg = [Fraction(-1) + Fraction(2 * jj, n - 1) for jj in range(n)]
    hits = [f for f in (Fraction(3, 5), Fraction(1, 5), Fraction(3, 10)) if f in zg]
    row("R7", f"kink z = 0.6 (a, e), jump z = 0.2 (b), diagonal kink 0.3: on the grid at n = {n}", "none",
        "none" if not hits else ", ".join(map(str, hits)), not hits)

# ---- R3: total indices of the model itself (polynomial_model.md, the comparison under the mock) ----
# By tensor Gauss-Legendre quadrature: T_i = E_(~i)[Var_i f] / Var f, from f on one grid (7 and 8 points per
# model parameter, to show convergence).
stated3 = [0.8669, 0, 0, 0.0540, 0, 0.0540, 0.0522, 0.0128]
tq = {}
for nq in (7, 8):
    xg, wg = np.polynomial.legendre.leggauss(nq)
    wg = wg / 2
    grids = np.meshgrid(*([xg] * 8), indexing="ij")
    F = R.evaluate_unit("R3", np.stack([g.ravel() for g in grids], axis=1)).reshape((nq,) * 8)
    W = wg
    for _ in range(7):
        W = np.multiply.outer(W, wg)
    mean = np.sum(W * F)
    var = np.sum(W * F**2) - mean**2
    tot = []
    for i in range(8):
        wi = wg.reshape([nq if k == i else 1 for k in range(8)])
        m1 = np.sum(wi * F, axis=i, keepdims=True)
        vi = np.sum(wi * (F - m1) ** 2, axis=i)
        wrest = W.sum(axis=i)
        tot.append(np.sum(wrest * vi) / var)
    tq[nq] = np.array(tot)
for i, k in enumerate(R.SPACES["R3"]):
    row("R3", f"{k} total index (Gauss-Legendre, 7 and 8 points per model parameter)", f"{stated3[i]}",
        f"{tq[8][i]:.5f} ({abs(tq[8][i] - tq[7][i]):.0e} from 7 points)", close(tq[8][i], stated3[i], 1e-4))

# ---- R8 ----
n = 17
pts = set()
for i in range(6):
    for jj in range(n):
        zp = [0.0] * 6
        zp[i] = -1 + 2 * jj / (n - 1)
        if jj == (n - 1) // 2:
            zp[i] = 0.0
        pts.add(tuple(zp))
row("R8", "distinct points of its coordinate lines, n = 17", "97 (102 rows)", f"{len(pts)} ({6 * n} rows)",
    len(pts) == 97)

# ---- R10 ----
var10 = 2**2 + 0.5**2 + 1.5**2
S10 = {"a": (4 / var10, (4 + 2.25) / var10), "b": (0.25 / var10, 0.25 / var10), "c": (0, 2.25 / var10),
       "e": (0, 0)}
stated10 = {"a": (0.6154, 0.9615), "b": (0.0385, 0.0385), "c": (0, 0.3462), "e": (0, 0)}
row("R10", "variance", "6.5", f"{var10}", var10 == 6.5)
for k in S10:
    row("R10", f"{k} first-order; total", f"{stated10[k][0]}; {stated10[k][1]}",
        f"{S10[k][0]:.6f}; {S10[k][1]:.6f}",
        close(S10[k][0], stated10[k][0], 5e-5) and close(S10[k][1], stated10[k][1], 5e-5))
f10, t10 = saltelli_jansen("R10", 4, MC_N, MC_SEED)
row("R10", f"first-order; total, Monte Carlo (N = 2^20, seed {MC_SEED})", "as above",
    "; ".join(f"{x:.4f}" for x in f10) + " | " + "; ".join(f"{x:.4f}" for x in t10),
    np.allclose(f10, [S10[k][0] for k in S10], atol=0.01) and np.allclose(t10, [S10[k][1] for k in S10], atol=0.01))

# ---- R11 ----
xg, wg = np.polynomial.legendre.leggauss(200)
wg = wg / 2  # the uniform measure on [-1, 1]
g = R.g11(xg)


def psi(k, x):
    return math.sqrt(2 * k + 1) * np.polynomial.legendre.Legendre.basis(k)(x)


c = np.array([np.sum(wg * g * psi(k, xg)) for k in range(41)])
stated11 = {0: 0.5536, 2: -0.2446, 4: 0.09474, 6: -0.03637}
for k, v in stated11.items():
    q = integrate.quad(lambda x: 0.5 * R.g11(x) * psi(k, x), -1, 1, epsabs=1e-14, epsrel=1e-13)[0]
    row("R11", f"c_{k} (Gauss-Legendre, 200 points; scipy quad)", f"{v}", f"{c[k]:.7f}; {q:.7f}",
        close(c[k], v, 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 3)) and close(c[k], q, 1e-12))
row("R11", "c_0 analytic, arctan(2)/2", "0.5536", f"{math.atan(2) / 2:.10f}", close(c[0], math.atan(2) / 2, 1e-14))
row("R11", "odd coefficients", "zero", f"max |c_odd| = {np.max(np.abs(c[1::2])):.1e}", np.max(np.abs(c[1::2])) < 1e-15)
phi = (1 + math.sqrt(5)) / 2
for k, v in ((2, -2.58), (18, -2.617)):
    ratio = c[k] / c[k + 2]
    row("R11", f"c_{k} / c_{k + 2}", f"{v}", f"{ratio:.5f}", close(ratio, v, 0.5 * 10 ** -(len(str(v).split('.')[1]))))
row("R11", "limit of c_k / c_(k+2)", f"-phi^2 = {-phi**2:.5f}", f"c_38/c_40 = {c[38] / c[40]:.5f}",
    close(c[38] / c[40], -phi**2, 0.005))
# full function: E[g] = c_0, E[g^2] = sum c_k^2; f = g(a) g(b)
Eg2 = integrate.quad(lambda x: 0.5 * R.g11(x) ** 2, -1, 1, epsabs=1e-15)[0]
s2 = Eg2 - c[0] ** 2
V11 = (c[0] ** 2 + s2) ** 2 - c[0] ** 4
first11 = c[0] ** 2 * s2 / V11
row("R11", "first-order; total (a, b), the full function (for the record)",
    "not stated (polynomial_model.md's 0.4486 is the degree-10 projection's)",
    f"{first11:.6f}; {1 - first11:.6f}", close(first11, 0.4485, 5e-5))
# the degree-10 projection: c_j c_k with j + k <= 10
cc = np.outer(c[:11], c[:11])
mask = np.add.outer(np.arange(11), np.arange(11)) <= 10
cc = np.where(mask, cc, 0.0)
Vp = np.sum(cc**2) - cc[0, 0] ** 2
fp = np.sum(cc[1:, 0] ** 2) / Vp
row("R11", "first-order; total (a, b), the degree-10 projection", "0.448617; 0.551383 (polynomial_model.md)",
    f"{fp:.6f}; {1 - fp:.6f}", close(fp, 0.448617, 5e-7))

# ---- print ----
w = [max(len(r[i]) for r in ROWS) for i in range(5)]
w = [min(x, 70) for x in w]
print("| Model | Quantity | Stated | Computed | |")
print("|---|---|---|---|---|")
for r in ROWS:
    print("| " + " | ".join(r) + " |")
print(f"\n{sum(r[4] == 'ok' for r in ROWS)} ok, {sum(r[4] != 'ok' for r in ROWS)} differ; "
      f"numpy {np.__version__}; {time.time() - T0:.1f} s")
