"""Step 11: recompute the linear model's expected answers (docs/design/diagnostics/linear_model.md).

Checks, independently of EMA's code and v1's:

- The expected values (the fit's limits as the runs grow: the L2 projection of y onto {1, z_1 .. z_d} under the
  uniform measure on [-1, 1]^d, so beta_0 = E[y], beta_i = 3 E[y z_i], and the relative residual
  sqrt(1 - sum(beta_i^2 / 3) / Var y)):
  - R1, R2, R10: analytic.
  - R7: exact piecewise Gauss-Legendre quadrature (the kink a + e = 0.6 split out; each piece polynomial).
  - R3: tensor Gauss-Legendre quadrature at 6, 8, and 10 points per model parameter (convergence shown), and
    brute force at 2,000,000 uniform points (seed 20261001), the spec's original source.
- The tolerances: 5 x the standard deviation of each estimate over 100 designs (seeds 1-100) of 20,000 runs
  (n_min = 5000, alpha = 0.5, level 1: the first 20,000 rows of the `random` sampler).
- The known-answer test itself: the estimate at seed 0 within the spec's tolerance of the expected value.
- "LOO error -> the relative residual's value": LOO by PRESS at seed 0, against the expected relative residual.
- The mock report's point estimates (R3, defaults, seed 3: 18, 36, 72 runs): per-level coefficients, relative
  residual, R^2, LOO; the observations. Not its bootstrap intervals.

Run from docs/checks/: OMP_NUM_THREADS=2 ../../../EMA-v1/.venv/bin/python linear_model.py
Output: linear_model.out.
"""

from __future__ import annotations

import io
import math
import sys
import time

import numpy as np

import refmodels as R

N = 20_000
SEEDS = range(1, 101)
SDS = 5
BRUTE_N = 2_000_000
BRUTE_SEED = 20261001

out = io.StringIO()


def say(*a):
    print(*a)
    print(*a, file=out)


# ---------------------------------------------------------------- the fit, as the spec defines it


def fit(z, y):
    """Coefficients, relative residual, R^2, LOO error (PRESS by QR leverages)."""
    A = np.column_stack([np.ones(len(y)), z])
    Q, Rm = np.linalg.qr(A)
    beta = np.linalg.solve(Rm, Q.T @ y)
    r = y - A @ beta
    dev = np.linalg.norm(y - y.mean())
    rel = np.linalg.norm(r) / dev
    h = np.sum(Q**2, axis=1)
    loo = np.sqrt(np.sum((r / (1 - h)) ** 2)) / dev
    return beta, rel, 1 - rel**2, loo


def design(seed, n, d):
    return 2 * np.random.default_rng(seed).random((n, d)) - 1


# ---------------------------------------------------------------- expected values


def limits_from_moments(Ey, Eyz, Ey2):
    beta = np.concatenate([[Ey], 3 * np.asarray(Eyz)])
    var = Ey2 - Ey**2
    expl = np.sum(beta[1:] ** 2) / 3
    rel = math.sqrt(1 - expl / var)
    return beta, rel, 1 - rel**2, var


def gl(m, lo=-1.0, hi=1.0):
    x, w = np.polynomial.legendre.leggauss(m)
    return lo + (hi - lo) * (x + 1) / 2, w * (hi - lo) / 2


def tensor_moments(model, d, m, chunk=1_000_000):
    """E[y], E[y z_i], E[y^2] under uniform on [-1,1]^d, by m-point Gauss-Legendre per dimension."""
    x, w = gl(m)
    w = w / 2  # uniform density 1/2 per dimension
    total = m**d
    s0 = 0.0
    s1 = np.zeros(d)
    s2 = 0.0
    for start in range(0, total, chunk):
        idx = np.arange(start, min(start + chunk, total))
        digits = np.empty((len(idx), d), dtype=np.int64)
        rem = idx.copy()
        for j in range(d - 1, -1, -1):
            digits[:, j] = rem % m
            rem //= m
        z = x[digits]
        wt = np.prod(w[digits], axis=1)
        y = R.evaluate_unit(model, z)
        s0 += wt @ y
        s1 += (wt * y) @ z
        s2 += wt @ (y * y)
    return s0, s1, s2


def r7_moments():
    """Exact: the terms in (a, e), b, c are independent, so means add and variances add."""
    # m(a, e) = max(0, a + e - 0.6), on [-1, 1]^2, density 1/4. For each e, a runs over [max(-1, 0.6 - e), 1];
    # the inner integrand is a polynomial in a, the outer piecewise polynomial in e with a break at e = -0.4.
    def inner(e, f):
        lo = max(-1.0, 0.6 - e)
        if lo >= 1:
            return 0.0
        a, w = gl(12, lo, 1.0)
        return w @ f(a, e)

    def outer(f):
        tot = 0.0
        for lo, hi in ((-1.0, -0.4), (-0.4, 1.0)):
            e, w = gl(12, lo, hi)
            tot += sum(wi * inner(ei, f) for ei, wi in zip(e, w))
        return tot / 4

    m1 = outer(lambda a, e: a + e - 0.6)
    ma = outer(lambda a, e: (a + e - 0.6) * a)
    me = outer(lambda a, e: (a + e - 0.6) * e)
    m2 = outer(lambda a, e: (a + e - 0.6) ** 2)
    # indicator b > 0.2
    ib, ibb = 0.4, (1 - 0.04) / 4
    # g(c) = 1/(1 + 4c^2): E g = arctan(2)/2; E g^2 by quadrature (analytic on [-1, 1]); E[g c] = 0
    c, w = gl(200)
    g1 = math.atan(2) / 2
    g2 = (w @ (1 / (1 + 4 * c**2)) ** 2) / 2
    Ey = m1 + ib + g1
    Eyz = [ma, ibb, 0.0, me]
    var = (m2 - m1**2) + (ib - ib**2) + (g2 - g1**2)
    return Ey, Eyz, var + Ey**2


def r2_moments():
    a, b = 7.0, 0.1
    pi = math.pi
    Ey = a / 2
    var = a**2 / 8 + b * pi**4 / 5 + b**2 * pi**8 / 18 + 0.5
    Eyz1 = (1 / pi) * (1 + b * pi**4 / 5)
    return Ey, [Eyz1, 0.0, 0.0], var + Ey**2


def r10_moments():
    return 0.0, [2 / math.sqrt(3), 0.0, 0.0, 0.0], 6.5


# ---------------------------------------------------------------- comparison helpers

rows = []


def check(row, qty, spec, got, tol=None, digits=None, note=""):
    """Agree when |spec - got| is within half a unit of the spec's last printed digit (or tol if given)."""
    if tol is None:
        tol = 0.5 * 10.0 ** (-digits) * 1.0001 if digits is not None else 0.0
    ok = abs(spec - got) <= tol
    rows.append((row, qty, spec, got, ok, note))


def table(title, rs):
    say(f"\n## {title}\n")
    say(f"{'row':10} | {'quantity':28} | {'spec':>11} | {'recomputed':>13} | agrees | note")
    for row, qty, spec, got, ok, note in rs:
        say(f"{row:10} | {qty:28} | {spec:>11.6g} | {got:>13.7g} | {'yes' if ok else 'NO':6} | {note}")


LINEAR_BOOT_TAG = 2**32 + 2
MOCK_INTERVALS = {  # linear_model.md's mock report, R3, seed 3, 72 runs
    "Intercept": (74.39, 82.02), "rw": (62.31, 77.66), "r": (-4.032, 9.424), "Tu": (-7.785, 7.972),
    "Hu": (1.944, 16.68), "Tl": (-6.665, 5.679), "Hl": (-23.51, -10.14), "L": (-18.83, -4.943),
    "Kw": (1.701, 14.31), "relative residual": (0.1631, 0.2641), "R2": (0.9302, 0.9734),
    "LOO": (0.2168, 0.336),
}


def mock_bootstrap(z, y, seed):
    """uncertainty.md, The bootstrap: 1000 resamples from SeedSequence(seed, spawn_key=(LINEAR_BOOT_TAG,));
    coefficients, relative residual, R^2 as drawn; LOO on each resample's distinct runs (linear_model.md);
    undefined: rank below d + 1 (matrix_rank), or fewer than d + 2 distinct runs for LOO; 0.5th-99.5th
    percentiles, linear interpolation."""
    n, d = z.shape
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(LINEAR_BOOT_TAG,))))
    idx = rng.integers(0, n, (1000, n))
    drawn, loos, und_fit, und_loo = [], [], 0, 0
    for ix in idx:
        A = np.column_stack([np.ones(n), z[ix]])
        if np.linalg.matrix_rank(A) < d + 1:
            und_fit += 1
        else:
            b, rel, r2, _ = fit(z[ix], y[ix])
            drawn.append(np.concatenate([b, [rel, r2]]))
        u = np.unique(ix)
        Au = np.column_stack([np.ones(len(u)), z[u]])
        if len(u) < d + 2 or np.linalg.matrix_rank(Au) < d + 1:
            und_loo += 1
        else:
            loos.append(fit(z[u], y[u])[3])
    drawn = np.array(drawn)
    lo = np.percentile(drawn, 0.5, axis=0)
    hi = np.percentile(drawn, 99.5, axis=0)
    llo, lhi = np.percentile(loos, [0.5, 99.5])
    say(f"\nBootstrap (tag 2^32 + 2, seed {seed}, 1000 resamples): undefined {und_fit} (fit), {und_loo} (LOO)")
    labels = ["Intercept"] + list(R.SPACES["R3"]) + ["relative residual", "R2"]
    got = {lab: (lo[i], hi[i]) for i, lab in enumerate(labels)}
    got["LOO"] = (llo, lhi)
    say(f"  {'estimate':18} | {'mock interval':>20} | {'recomputed (4 digits)':>22} | agrees")
    for lab, (slo, shi) in MOCK_INTERVALS.items():
        glo, ghi = got[lab]
        ok = f"{glo:.4g}" == f"{slo:.4g}" and f"{ghi:.4g}" == f"{shi:.4g}"
        say(f"  {lab:18} | [{slo:.4g}, {shi:.4g}]".ljust(44) + f" | [{glo:.4g}, {ghi:.4g}]".ljust(25)
            + f" | {'yes' if ok else 'NO'}")


def main():
    t0 = time.time()
    say("# Linear model: step 11 recomputation")
    say(f"numpy {np.__version__}, Python {sys.version.split()[0]}; N = {N}, tolerance designs: seeds 1-100")

    names = {
        "R1": ["intercept", "a", "b", "c", "k"],
        "R2": ["intercept", "x1", "x2", "x3"],
        "R3": ["intercept"] + list(R.SPACES["R3"]),
        "R7": ["intercept", "a", "b", "c", "e"],
        "R10": ["intercept", "a", "b", "c", "e"],
    }
    spec_val = {
        "R2": [3.5, 2.815, 0, 0],
        "R7": [1.068, 0.2230, 0.72, 0, 0.2230],
        "R10": [0, 3.464, 0, 0, 0],
        "R3": [77.76, 71.49, -0.16, 0.00, 16.09, 0.15, -16.09, -15.62, 7.73],
    }
    spec_digits = {"R2": [1, 3, 0, 0], "R7": [3, 4, 2, 0, 4], "R10": [0, 3, 0, 0, 0], "R3": [2] * 9}
    spec_rel = {"R2": (0.8995, 4), "R7": (0.6739, 4), "R10": (0.6202, 4), "R3": (0.2304, 4)}
    spec_r2 = {"R2": (0.1908, 4), "R7": (0.5458, 4), "R10": (0.6154, 4)}
    spec_tol = {
        "R2": [0.11, 0.18, 0.22, 0.24],
        "R7": [0.016, 0.024, 0.025, 0.024, 0.029],
        "R10": [0.060, 0.12, 0.098, 0.13, 0.10],
        "R3": [0.32, 0.91, 0.68, 0.64, 0.73, 0.69, 0.87, 0.70, 0.64],
    }
    spec_tol_rel = {"R2": 0.010, "R7": 0.014, "R10": 0.016, "R3": 0.0064}
    spec_tol_r2 = {"R2": 0.018, "R7": 0.019, "R10": 0.020}

    # ---- expected values
    limits = {}
    limits["R2"] = limits_from_moments(*r2_moments())
    limits["R7"] = limits_from_moments(*r7_moments())
    limits["R10"] = limits_from_moments(*r10_moments())

    say("\n## R3 by tensor Gauss-Legendre quadrature (points per model parameter: 6, 8, 10)\n")
    for m in (6, 8, 10):
        tq = time.time()
        Ey, Eyz, Ey2 = tensor_moments("R3", 8, m)
        lim = limits_from_moments(Ey, Eyz, Ey2)
        say(f"m = {m:2d}: intercept {lim[0][0]:.6f}; slopes " + ", ".join(f"{v:.5f}" for v in lim[0][1:])
            + f"; relative residual {lim[1]:.6f}; R2 {lim[2]:.6f} ({time.time() - tq:.0f} s)")
    limits["R3"] = lim
    zb = 2 * np.random.default_rng(BRUTE_SEED).random((BRUTE_N, 8)) - 1
    yb = R.evaluate_unit("R3", zb)
    bb, relb, r2b, loob = fit(zb, yb)
    say(f"brute force, {BRUTE_N} points, seed {BRUTE_SEED}: intercept {bb[0]:.4f}; slopes "
        + ", ".join(f"{v:.4f}" for v in bb[1:]) + f"; relative residual {relb:.5f}")
    sd_b = np.linalg.norm(yb - yb.mean()) / math.sqrt(BRUTE_N)
    say(f"  (brute force's own standard error on a slope ~ sqrt(3) x sd(residual)/sqrt(N) = "
        f"{math.sqrt(3) * relb * sd_b / math.sqrt(BRUTE_N):.3f})")
    say("Hu and Hl slopes, quadrature: "
        f"{limits['R3'][0][4]:.6f}, {limits['R3'][0][6]:.6f} (sum {limits['R3'][0][4] + limits['R3'][0][6]:.2e})")
    rw_lo, rw_hi = R.SPACES["R3"]["rw"][:2]
    tu_lo, tu_hi = R.SPACES["R3"]["Tu"][:2]
    say(f"slopes in model parameter units (mock's prose): rw {limits['R3'][0][1] / ((rw_hi - rw_lo) / 2):.1f}"
        f" m3/yr per m; Tu {limits['R3'][0][3] / ((tu_hi - tu_lo) / 2):.3g} per m2/yr")

    # ---- R1 exact at seed 0
    z = design(0, N, 4)
    beta, rel, r2, loo = fit(z, R.evaluate_unit("R1", z))
    for i, (s, b) in enumerate(zip([10, 3, -1, 0, 2], beta)):
        check("R1", names["R1"][i], s, b, tol=1e-12)
    check("R1", "relative residual", 0, rel, tol=1e-12)
    check("R1", "R2", 1, r2, tol=1e-12)
    check("R1", "LOO", 0, loo, tol=1e-12)

    # ---- expected values vs the spec
    for mdl in ("R2", "R7", "R10", "R3"):
        beta, rel, r2, var = limits[mdl]
        for i, (s, dg) in enumerate(zip(spec_val[mdl], spec_digits[mdl])):
            check(mdl, f"expected {names[mdl][i]}", s, beta[i], digits=dg)
        check(mdl, "expected relative residual", spec_rel[mdl][0], rel, digits=spec_rel[mdl][1])
        if mdl in spec_r2:
            check(mdl, "expected R2", spec_r2[mdl][0], r2, digits=spec_r2[mdl][1])
        if mdl == "R2":
            check("R2", "Var y (13.84)", 13.84, var, digits=2)
    table("Expected values (limits) against the spec", rows)
    rows.clear()

    # ---- tolerances over 100 designs, and the known-answer test at seed 0
    say("\n## Tolerances: 5 x standard deviation over 100 designs of 20,000 runs (spec | recomputed | ratio)\n")
    for mdl, d in (("R2", 3), ("R7", 4), ("R10", 4), ("R3", 8)):
        est = []
        for s in SEEDS:
            z = design(s, N, d)
            b, rel, r2, loo = fit(z, R.evaluate_unit(mdl, z))
            est.append(np.concatenate([b, [rel, r2, loo]]))
        est = np.array(est)
        tol = SDS * est.std(axis=0, ddof=1)
        mean = est.mean(axis=0)
        labels = names[mdl] + ["relative residual", "R2", "LOO"]
        spec_t = spec_tol[mdl] + [spec_tol_rel[mdl], spec_tol_r2.get(mdl, float("nan")), spec_tol_rel[mdl]]
        beta, rel, r2, _ = limits[mdl]
        expected = list(beta) + [rel, r2, rel]
        z0 = design(0, N, d)
        b0, rel0, r20, loo0 = fit(z0, R.evaluate_unit(mdl, z0))
        e0 = list(b0) + [rel0, r20, loo0]
        say(f"{mdl}:")
        say(f"  {'quantity':18} | {'spec tol':>8} | {'5 sd':>8} | {'ratio':>5} | {'expected':>10} | "
            f"{'mean-exp':>9} | {'seed 0':>10} | seed 0 within spec tol?")
        for i, lab in enumerate(labels):
            st = spec_t[i]
            ratio = tol[i] / st if st == st else float("nan")
            inside = abs(e0[i] - expected[i]) <= st if st == st else None
            say(f"  {lab:18} | {st:8.3g} | {tol[i]:8.3g} | {ratio:5.2f} | {expected[i]:10.5g} | "
                f"{mean[i] - expected[i]:9.2g} | {e0[i]:10.5g} | {inside}")
    say(f"\nRuntime {time.time() - t0:.0f} s")

    # ---- the mock report (point estimates only)
    say("\n## Mock report: R3, defaults, seed 3 (18, 36, 72 runs); point estimates\n")
    z = design(3, 72, 8)
    y = R.evaluate_unit("R3", z)
    say(f"observations: min {y.min():.4g}, max {y.max():.4g}, (max - min)/max|y| {(y.max() - y.min()) / np.abs(y).max():.4g}")
    for n in (18, 36, 72):
        b, rel, r2, loo = fit(z[:n], y[:n])
        say(f"n = {n:2d}: " + ", ".join(f"{v:.4g}" for v in b) + f"; rel {rel:.4g}; R2 {r2:.4g}; LOO {loo:.4g}")
    mock_bootstrap(z, y, seed=3)

    say(f"\nTotal runtime {time.time() - t0:.0f} s")
    with open("linear_model.out", "w") as fh:
        fh.write(out.getvalue())


if __name__ == "__main__":
    main()
