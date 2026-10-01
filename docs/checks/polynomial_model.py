"""Step 11: an independent recomputation of `diagnostics/polynomial_model.md`'s numbers.

Checks, without EMA's or v1's code (numpy, scipy, and `refmodels.py` only):

1. **Expected answers** (the table): every row with a number.
   - The expected values: the degree-p L2 projection of each model under the uniform distribution in unit
     coordinates, by tensor Gauss-Legendre quadrature (60 points per model parameter; 40 and 80 shown to agree),
     and R2's Sobol indices analytically (Ishigami's closed form).
   - The tolerances: |mean over 100 designs (seeds 1-100) - expected| + 5 x the standard deviation over them,
     rounded up to 2 significant digits, each design the first 20,000 rows of the `random` sampler
     (`default_rng(s).random((20000, d))`, z = 2u - 1); the bias and SD parts printed apart.
   - The test itself: seed 0's estimate against the spec's expected value and tolerance.
   - R1 and R10 at p = 2: exact recovery at seed 0 (10^-12).
2. **The mock report** (line ~268, "step 11 checks them"): R3, p = 2, seed 3, n_min = 90, alpha = 0.7072,
   level 2 (90, 180, 360 runs), the bootstrap from SeedSequence(3, spawn_key=(2^32 + 3,)), 1000 resamples,
   0.5th-99.5th percentiles, LOO on each resample's distinct runs.
3. **The comparison under the mock** (line ~378): the degree-2 projection of R3 by quadrature (7 points per
   model parameter, 6 and 8 shown to agree).
4. **"limit 0.0029"** (Uncertainty, R2's x3 first-order at p = 4): the projection's value, and the plain and
   bias-corrected fitted values at 8P = 280 runs, mean over 30 designs.

Run from docs/checks/: OMP_NUM_THREADS=2 ../../../EMA-v1/.venv/bin/python polynomial_model.py
Writes polynomial_model.out beside this file.
"""

from __future__ import annotations

import itertools
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular

import refmodels as R

OUT_LINES: list[str] = []


def out(s: str = "") -> None:
    print(s)
    OUT_LINES.append(s)


# ---------------------------------------------------------------------------------------------------------
# The basis: orthonormal Legendre terms of total degree <= p, by total degree, then exponents largest first.


def multi_indices(d: int, p: int) -> list[tuple[int, ...]]:
    idx = []
    for k in range(p + 1):
        terms = [a for a in itertools.product(range(k, -1, -1), repeat=d) if sum(a) == k]
        idx.extend(sorted(terms, reverse=True))
    return idx


def legendre_1d(z: np.ndarray, p: int) -> np.ndarray:
    """psi_0 .. psi_p at z: orthonormal under the uniform measure on [-1, 1] (psi_k = sqrt(2k+1) P_k)."""
    P = np.empty((p + 1,) + z.shape)
    P[0] = 1.0
    if p >= 1:
        P[1] = z
    for k in range(1, p):
        P[k + 1] = ((2 * k + 1) * z * P[k] - k * P[k - 1]) / (k + 1)
    for k in range(p + 1):
        P[k] *= math.sqrt(2 * k + 1)
    return P


def design_matrix(z: np.ndarray, idx: list[tuple[int, ...]], p: int) -> np.ndarray:
    n, d = z.shape
    one_d = [legendre_1d(z[:, i], p) for i in range(d)]
    A = np.ones((n, len(idx)))
    for j, a in enumerate(idx):
        for i, ai in enumerate(a):
            if ai:
                A[:, j] *= one_d[i][ai]
    return A


# ---------------------------------------------------------------------------------------------------------
# The fit and its estimates (the spec's Computation section).


def fit(z, y, idx, p, A=None):
    A = design_matrix(z, idx, p) if A is None else A
    Q, Rm = np.linalg.qr(A)
    c = solve_triangular(Rm, Q.T @ y)
    r = y - A @ c
    h = np.einsum("ij,ij->i", Q, Q)
    dev = np.linalg.norm(y - y.mean())
    rel = np.linalg.norm(r) / dev
    r2 = 1 - np.linalg.norm(r) ** 2 / dev**2
    loo = math.sqrt(np.sum((r / (1 - h)) ** 2)) / dev
    return c, rel, r2, loo, A


def summaries(c, idx, p, d):
    alpha = np.array(idx)
    nz = alpha.sum(axis=1) > 0
    V = np.sum(c[nz] ** 2)
    first, total = [], []
    for i in range(d):
        involves = alpha[:, i] > 0
        alone = involves & (alpha.sum(axis=1) == alpha[:, i])
        first.append(np.sum(c[alone] ** 2) / V)
        total.append(np.sum(c[involves] ** 2) / V)
    deg = alpha.sum(axis=1)
    rootE = [math.sqrt(np.sum(c[deg == k] ** 2)) for k in range(1, p + 1)]
    return np.array(first), np.array(total), np.array(rootE), V


# ---------------------------------------------------------------------------------------------------------
# Quadrature projection.


def project(f_unit, d, p, nq, chunk=100_000):
    """Coefficients of the degree-p projection, its variance V, and Var f, by tensor Gauss-Legendre."""
    x, w = np.polynomial.legendre.leggauss(nq)
    w = w / 2
    idx = multi_indices(d, p)
    c = np.zeros(len(idx))
    m1 = m2 = 0.0
    total = nq**d
    done = 0
    while done < total:
        k = min(chunk, total - done)
        ii = np.stack(np.unravel_index(np.arange(done, done + k), (nq,) * d), axis=1)
        z = x[ii]
        wt = np.prod(w[ii], axis=1)
        fz = f_unit(z)
        A = design_matrix(z, idx, p)
        c += A.T @ (wt * fz)
        m1 += np.sum(wt * fz)
        m2 += np.sum(wt * fz**2)
        done += k
    return c, idx, m2 - m1**2


def unit_rows(seed, n, d):
    return 2 * np.random.default_rng(seed).random((n, d)) - 1


def roundup2(x):
    if x == 0:
        return 0.0
    e = math.floor(math.log10(abs(x))) - 1
    return math.ceil(x / 10**e) * 10**e


def fmt(x):
    return "%.4g" % x


# ---------------------------------------------------------------------------------------------------------


def ishigami_analytic():
    a, b = 7.0, 0.1
    pi = math.pi
    V1 = 0.5 * (1 + b * pi**4 / 5) ** 2
    V2 = a**2 / 8
    V13 = b**2 * pi**8 * (1 / 18 - 1 / 50)
    V = V1 + V2 + V13
    return V, np.array([V1 / V, V2 / V, 0.0]), np.array([(V1 + V13) / V, V2 / V, V13 / V])


def table_row(model, qty, spec, val, spec_tol, tol, seed0):
    ok_val = abs(val - spec) <= (spec_tol * 0.05 if spec_tol else 5e-5 * max(1, abs(spec)))
    ok_test = abs(seed0 - spec) <= spec_tol
    out(f"{model:<5}| {qty:<16}| {fmt(spec):>10} | {val:>12.6g} | {fmt(spec_tol):>8} | {tol:>8.2g} | "
        f"{seed0:>12.6g} | {'yes' if ok_test else 'NO'}")
    return ok_test


def known_answer_block(name, f_unit, d, p, spec, nq=60, n=20_000, seeds=range(1, 101)):
    """spec: dict qty -> (list of expected, list of tolerance)."""
    t0 = time.time()
    c, idx, varf = project(f_unit, d, p, nq)
    c2, _, _ = project(f_unit, d, p, nq + 20)
    first, total, rootE, V = summaries(c, idx, p, d)
    rel = math.sqrt(max(0.0, 1 - V / varf))
    exp = {"first": first, "total": total, "rootE": rootE, "rel": [rel], "loo": [rel]}
    out(f"\n{name}, p = {p}: projection by {nq}-point Gauss-Legendre per model parameter; "
        f"max |c(nq={nq}) - c(nq={nq + 20})| = {np.max(np.abs(c - c2)):.1e}; Var f = {varf:.10g}; "
        f"V_p = {V:.10g}")
    A_est = {k: [] for k in exp}
    for s in list(seeds) + [0]:
        z = unit_rows(s, n, d)
        y = f_unit(z)
        cc, rr, _, ll, _ = fit(z, y, idx, p)
        f1, tt, ee, _ = summaries(cc, idx, p, d)
        for k, v in (("first", f1), ("total", tt), ("rootE", ee), ("rel", [rr]), ("loo", [ll])):
            A_est[k].append(np.asarray(v))
    out(f"  100 designs of {n} runs + seed 0: {time.time() - t0:.0f} s")
    out("model| quantity        |  spec exp. | projection   | spec tol |  recomp. tol (bias + 5 SD)       "
        "| seed 0       | seed 0 within spec tol?")
    allok = True
    for k, (spec_vals, spec_tols) in spec.items():
        est = np.array(A_est[k])
        reps, s0 = est[:-1], est[-1]
        mean, sd = reps.mean(axis=0), reps.std(axis=0, ddof=1)
        for j, (sv, st) in enumerate(zip(spec_vals, spec_tols)):
            if sv is None:
                continue
            bias = abs(mean[j] - exp[k][j])
            tol = roundup2(bias + 5 * sd[j])
            ok_test = abs(s0[j] - sv) <= st
            allok &= ok_test
            dval = abs(exp[k][j] - sv)
            out(f"{name:<5}| {k}[{j + 1}]".ljust(23) + f"| {fmt(sv):>10} | {exp[k][j]:>12.7g} | {st:>8.2g} | "
                f"{tol:>8.2g} (bias {bias:.1e} + {5 * sd[j]:.1e}) | {s0[j]:>12.7g} | "
                f"{'yes' if ok_test else 'NO'}{'   <- expected differs from projection by %.1e' % dval if dval > 0.6 * 10 ** (math.floor(math.log10(abs(sv))) - 3 if sv else -9) else ''}")
    return exp, allok


def exact_block(name, f_unit, d, p, coef_spec, first_spec, total_spec, rootE_spec):
    idx = multi_indices(d, p)
    z = unit_rows(0, 20_000, d)
    y = f_unit(z)
    c, rel, r2, loo, _ = fit(z, y, idx, p)
    f1, tt, ee, _ = summaries(c, idx, p, d)
    ce = np.zeros(len(idx))
    for a, v in coef_spec.items():
        ce[idx.index(a)] = v
    errs = {
        "coefficients": np.max(np.abs(c - ce)),
        "relative residual": abs(rel),
        "R2 - 1": abs(r2 - 1),
        "LOO": abs(loo),
        "first-order": np.max(np.abs(f1 - first_spec)),
        "total": np.max(np.abs(tt - total_spec)),
        "rootE": np.max(np.abs(ee - rootE_spec)),
    }
    out(f"\n{name}, p = {p}, seed 0, 20,000 runs: largest error against the spec's exact values (tolerance 1e-12)")
    for k, v in errs.items():
        out(f"  {k:<18} {v:.1e}  {'yes' if v <= 1e-12 else 'NO'}")
    return all(v <= 1e-12 for v in errs.values())


# ---------------------------------------------------------------------------------------------------------


def mock_report():
    out("\nMock report: R3, p = 2, seed 3, levels 90, 180, 360 (n_min = 90, alpha = 0.7072)")
    a = Fraction("0.7072")
    sizes = [math.ceil(90 / a ** (2 * l)) for l in range(3)]
    out(f"  level sizes, exact: {sizes}")
    d, p = 8, 2
    idx = multi_indices(d, p)
    z = 2 * np.random.default_rng(3).random((360, d)) - 1
    y = R.evaluate_unit("R3", z)
    names = list(R.SPACES["R3"])
    levels = []
    for n in sizes:
        c, rel, r2, loo, _ = fit(z[:n], y[:n], idx, p)
        f1, tt, ee, _ = summaries(c, idx, p, d)
        levels.append((n, rel, r2, loo, tt))
    c, rel, r2, loo, A = fit(z, y, idx, p)
    f1, tt, ee, _ = summaries(c, idx, p, d)
    tag = 2**32 + 3
    draws = np.random.Generator(np.random.PCG64(np.random.SeedSequence(3, spawn_key=(tag,)))).integers(
        0, 360, (1000, 360))
    B = {"rel": [], "r2": [], "loo": [], "f1": [], "tt": [], "ee": []}
    undefined = loo_undefined = 0
    for row in draws:
        Ab, yb = A[row], y[row]
        if np.linalg.matrix_rank(Ab) < len(idx):
            undefined += 1
        else:
            cb, rb, r2b, _, _ = fit(None, yb, idx, p, A=Ab)
            f1b, ttb, eeb, _ = summaries(cb, idx, p, d)
            B["rel"].append(rb), B["r2"].append(r2b), B["f1"].append(f1b), B["tt"].append(ttb), B["ee"].append(eeb)
        u = np.unique(row)
        if len(u) < len(idx) + 1 or np.linalg.matrix_rank(A[u]) < len(idx):
            loo_undefined += 1
        else:
            _, _, _, lb, _ = fit(None, y[u], idx, p, A=A[u])
            B["loo"].append(lb)
    pct = lambda v: np.percentile(np.array(v), [0.5, 99.5], axis=0)  # noqa: E731
    out(f"  undefined resamples: fit {undefined}, LOO {loo_undefined}")
    spec = {
        "rel": (0.03526, 0.02607, 0.03786), "r2": (0.9988, 0.9986, 0.9993), "loo": (0.04192, 0.03645, 0.05058),
    }
    for k, val in (("rel", rel), ("r2", r2), ("loo", loo)):
        lo, hi = pct(B[k])
        s = spec[k]
        out(f"  {k:<4} spec {s[0]} [{s[1]}, {s[2]}]   recomputed {fmt(val)} [{fmt(lo)}, {fmt(hi)}]")
    spec_sobol = {
        "rw": (0.8304, 0.8248, 0.8361, 0.8673, 0.8625, 0.8721),
        "r": (5.622e-06, 1.007e-07, 6.983e-05, 4.257e-05, 1.703e-05, 0.0002161),
        "Tu": (3.38e-06, 1.725e-07, 8.413e-05, 4.465e-05, 1.64e-05, 0.0002891),
        "Hu": (0.04188, 0.03938, 0.04421, 0.05421, 0.05085, 0.05717),
        "Tl": (1.369e-06, 3.161e-08, 5.496e-05, 1.397e-05, 8.325e-06, 0.0002055),
        "Hl": (0.04149, 0.03906, 0.04369, 0.05415, 0.05143, 0.0564),
        "L": (0.03857, 0.03655, 0.04051, 0.05012, 0.04713, 0.05265),
        "Kw": (0.009238, 0.00811, 0.01044, 0.01251, 0.01103, 0.01412),
    }
    f1p, ttp = pct(B["f1"]), pct(B["tt"])
    mism = 0
    for i, nm in enumerate(names):
        got = (f1[i], f1p[0][i], f1p[1][i], tt[i], ttp[0][i], ttp[1][i])
        same = all(fmt(g) == fmt(s) for g, s in zip(got, spec_sobol[nm]))
        mism += not same
        out(f"  {nm:<3} spec {spec_sobol[nm]}\n      got  ({', '.join(fmt(g) for g in got)})  {'same' if same else 'DIFFERS'}")
    eep = pct(B["ee"])
    out(f"  rootE spec 44.67 [44.22, 45.08], 10.37 [9.843, 10.96]; got "
        f"{fmt(ee[0])} [{fmt(eep[0][0])}, {fmt(eep[1][0])}], {fmt(ee[1])} [{fmt(eep[0][1])}, {fmt(eep[1][1])}]")
    out(f"  observations: min {fmt(y.min())} (spec 10.24), max {fmt(y.max())} (spec 225.2), "
        f"(max - min)/max|y| {fmt((y.max() - y.min()) / np.abs(y).max())} (spec 0.9545)")
    spec_levels = [
        (0.02633, 0.9993, 0.05555, [0.8705, 0.0003875, 0.0008148, 0.04762, 0.0003035, 0.05415, 0.04878, 0.01158]),
        (0.03296, 0.9989, 0.04664, [0.8651, 0.0001167, 7.24e-05, 0.05401, 2.474e-05, 0.05433, 0.05239, 0.01201]),
        (0.03526, 0.9988, 0.04192, [0.8673, 4.257e-05, 4.465e-05, 0.05421, 1.397e-05, 0.05415, 0.05012, 0.01251]),
    ]
    for (n, rl, rr2, lo, tt_l), (srel, sr2, sloo, stt) in zip(levels, spec_levels):
        got = [rl, rr2, lo] + list(tt_l)
        want = [srel, sr2, sloo] + stt
        bad = [(fmt(g), w) for g, w in zip(got, want) if fmt(g) != fmt(w)]
        out(f"  level n = {n}: {'all 11 agree to 4 digits' if not bad else 'DIFFER: ' + str(bad)}")
    return mism


def mock_comparison():
    out("\nUnder the mock (line ~378): the degree-2 projection of R3 by quadrature")
    f = lambda z: R.evaluate_unit("R3", z)  # noqa: E731
    res = {}
    for nq in (6, 7, 8):
        c, idx, varf = project(f, 8, 2, nq)
        f1, tt, ee, V = summaries(c, idx, 2, 8)
        res[nq] = (math.sqrt(1 - V / varf), tt, ee)
    rel, tt, ee = res[7]
    out(f"  relative residual {rel:.4f} (spec 0.0341); nq 6/8: {res[6][0]:.6f}, {res[8][0]:.6f}")
    out(f"  totals {', '.join('%.4f' % t for t in tt)}")
    out("  spec   0.8668, 0, 0, 0.0537, 0, 0.0537, 0.0516, 0.0126")
    out(f"  sqrt(E_1), sqrt(E_2) of the projection: {ee[0]:.4f}, {ee[1]:.4f}")
    c3, idx3, varf = project(f, 8, 3, 8)
    _, _, ee3, _ = summaries(c3, idx3, 3, 8)
    out(f"  degree-3 projection's sqrt(E_1..3): {', '.join('%.4f' % e for e in ee3)} "
        f"(spec line ~128: 44.47, 10.41, 1.549, means of fits)")


def x3_limit():
    out("\n'limit 0.0029' (Uncertainty): R2's x3 first-order at p = 4")
    f = lambda z: R.evaluate_unit("R2", z)  # noqa: E731
    c, idx, varf = project(f, 3, 4, 60)
    f1, tt, _, V = summaries(c, idx, 4, 3)
    out(f"  degree-4 projection: first-order x3 = {f1[2]:.2e}, total x3 = {tt[2]:.4f}")
    plain, corr, corr_raw = [], [], []
    P = len(idx)
    for s in range(1, 31):
        z = unit_rows(s, 280, 3)
        y = f(z)
        cc, _, _, _, A = fit(z, y, idx, 4)
        r = y - A @ cc
        s2 = r @ r / (len(y) - P)
        diag = np.diag(np.linalg.inv(A.T @ A))
        f1p, _, _, Vp = summaries(cc, idx, 4, 3)
        plain.append(f1p[2])
        cc2 = np.maximum(cc**2 - s2 * diag, 0)
        alpha = np.array(idx)
        alone = (alpha[:, 2] > 0) & (alpha.sum(axis=1) == alpha[:, 2])
        nz = alpha.sum(axis=1) > 0
        corr.append(np.sum(cc2[alone]) / np.sum(cc2[nz]))
        cc3 = cc**2 - s2 * diag
        corr_raw.append(np.sum(cc3[alone]) / np.sum(cc3[nz]))
    out(f"  fitted at 280 runs (8P), mean over seeds 1-30: plain {np.mean(plain):.4f} (spec 0.0091), "
        f"bias-corrected, clipped at 0 {np.mean(corr):.4f}, unclipped {np.mean(corr_raw):.4f} (spec 0.0042)")


def main():
    t0 = time.time()
    out(f"polynomial_model.py: numpy {np.__version__}, Python {sys.version.split()[0]}")
    ok = True
    # R1 and R10: exact.
    r3_ = math.sqrt(3)
    ok &= exact_block("R1", lambda z: R.evaluate_unit("R1", z), 4, 2,
                      {(0, 0, 0, 0): 10, (1, 0, 0, 0): r3_, (0, 1, 0, 0): -1 / r3_, (0, 0, 0, 1): 2 / r3_},
                      np.array([9, 1, 0, 4]) / 14, np.array([9, 1, 0, 4]) / 14, np.array([math.sqrt(14 / 3), 0]))
    ok &= exact_block("R10", lambda z: R.evaluate_unit("R10", z), 4, 2,
                      {(1, 0, 0, 0): 2, (0, 2, 0, 0): 0.5, (1, 0, 1, 0): 1.5},
                      np.array([4, 0.25, 0, 0]) / 6.5, np.array([6.25, 0.25, 2.25, 0]) / 6.5,
                      np.array([2, math.sqrt(2.5)]))
    # R2, analytic Sobol.
    V, S, T = ishigami_analytic()
    out(f"\nR2 analytic: V = {V:.6f}; first {S.round(6)}; total {T.round(6)}")
    out("  spec (polynomial_model.md): first 0.313905, 0.442411, 0; total 0.557589, 0.442411, 0.243684")
    out("\nKnown answers at 20,000 runs. 'projection' is the limit; a value 'expected differs' when the "
        "spec's differs from it beyond 4 digits.")
    exp2, ok2 = known_answer_block(
        "R2", lambda z: R.evaluate_unit("R2", z), 3, 10, {
            "first": ([0.313905, 0.442411, 0], [4.1e-5, 5.1e-5, 1e-5]),
            "total": ([0.557589, 0.442411, 0.243684], [5.1e-5, 5.1e-5, 4.1e-5]),
            "rootE": ([1.62542, 0.594723, 1.88396, 1.95229, 1.18024, 1.35741, 0.364431, 0.339391, 0.0502251, 0.0459147],
                      [x * 1e-4 for x in (1.9, 2.4, 2.2, 2.4, 2.2, 2.6, 3.2, 2.7, 3.2, 3.2)]),
            "rel": ([0.00137138], [7.5e-5]), "loo": ([0.00137138], [7.5e-5])})
    out(f"  R2 degree-10 projection vs analytic: first-order differs by "
        f"{np.max(np.abs(exp2['first'] - S)):.1e}, total by {np.max(np.abs(exp2['total'] - T)):.1e}")
    exp11, ok11 = known_answer_block(
        "R11", lambda z: R.evaluate_unit("R11", z), 2, 10, {
            "first": ([0.448617, 0.448617], [2.9e-4, 3.3e-4]),
            "total": ([0.551383, 0.551383], [3.3e-4, 2.9e-4]),
            "rootE": ([0, 0.191472, 0, 0.0952851, 0, 0.0434089, 0, 0.0189107, 0, 0.00802035],
                      [x * 1e-4 for x in (1.1, 2.1, 1.7, 3.2, 2.7, 4.1, 3.2, 4.6, 3.9, 5.3)]),
            "rel": ([0.0167170], [9.6e-4]), "loo": ([0.0167170], [9.6e-4])})  # 0058
    # R11 from its 1-D coefficients (reference_models.md: c_0 = 0.5536, c_2 = -0.2446, c_4, c_6).
    x, w = np.polynomial.legendre.leggauss(200)
    ck = (legendre_1d(x, 10) * (w / 2)) @ R.g11(x)
    out(f"\nR11 1-D coefficients c_0..c_6 (even): {', '.join('%.5g' % ck[k] for k in (0, 2, 4, 6))} "
        f"(spec 0.5536, -0.2446, 0.09474, -0.03637); c_0 = arctan(2)/2 = {math.atan(2) / 2:.6f}")
    E = [math.sqrt(sum((ck[j] * ck[k - j]) ** 2 for j in range(k + 1) if not (j == 0 and k - j == 0)))
         for k in range(1, 11)]
    out(f"  sqrt(E_k) from c_j c_k: {', '.join('%.4g' % e for e in E)}")
    ok &= ok2 and ok11
    mism = mock_report()
    mock_comparison()
    x3_limit()
    out(f"\nseed-0 tests within the spec's tolerances, and R1/R10 exact: {'all' if ok else 'NOT all'}; "
        f"mock Sobol rows differing: {mism}. Total {time.time() - t0:.0f} s.")
    Path(__file__).with_suffix(".out").write_text("\n".join(OUT_LINES) + "\n")


if __name__ == "__main__":
    main()
