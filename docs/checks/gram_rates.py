"""Step 11 check of the Gram spectra and decay rates: coordinate_lines.md and lines.md, "Expected answers".

Independent of EMA (no code yet) and of v1. Each line's points are built from designs.md ("Lines", "Unit
coordinates", "Random lines"); y comes from refmodels.py. The Gram coefficients are computed two ways:

1. **Exact:** in Python's ``fractions``, from the runs' doubles, with the monic three-term recurrence
   p_(k+1)(s) = s p_k(s) - beta_k p_(k-1)(s), beta_k = k^2 (n^2 - k^2) / ((n - 1)^2 (4k^2 - 1)), on
   s_j = -1 + 2j/(n - 1). c_k^2 = ((1/n) sum_j y_j p_k(s_j))^2 / ((1/n) sum_j p_k(s_j)^2), exactly; the tail
   T(k)^2 = var(y) - sum_(1 <= j < k) c_j^2 (Parseval, exact), so only degrees up to K are needed. Floor and
   k* compared exactly; the square root, log10, and the least-squares slope in doubles.
2. **Float:** Lanczos on diag(s) from the start vector of ones, with full reorthogonalization (the method
   coordinate_lines.md specifies), all n degrees; its signed c_k compared with the exact ones.

Rows checked:
- coordinate_lines.md, Expected answers: R7/R8 rates at n = 17 and 33; R7 along c at 33, 65, 129 against
  log10(phi); the rate ratios along a, b, c over n = 17 -> 33 -> 65 -> 129; R8 along f and g constant; R1 every
  line; R10 k*; R2 along x3 constant; R3 at n = 17 (exact, and by Lanczos and QR in doubles; one and two ulps in y); R4a, R4b; R5's z
  along b; R2 under y -> 2^-10 y + 3.
- coordinate_lines.md, text: the "What it gives" table (n = 9 ... 129, k*/K at 33; not R6a, R6b: one draw of
  their noise), the all-degrees rates of LINE_RATE_WINDOW's reason (0.246, 0.255, 0.223), the mock report's
  observations (R8, n = 17), the three-term recurrence's loss of orthonormality in doubles (10^-8 at n = 33,
  0.4 at n = 65), and Lanczos against exact (within 4e-16 of the range on R7's lines at n = 17, 65, 129).
- lines.md, Expected answers: R7 random lines (m = 5, n = 17, seed 0); R11 random lines (m = 10, seed 0) at
  n = 33, 65, 129 against log10 of the Bernstein ellipse parameter; R7's given (1, 1) line; R10's two given lines, (a, e) = (1, 1) and e (0058); R1 and
  R10 random
  lines; R4a; R5 random lines; R2 under the shift.
- lines.md, text: the mock report's ends, lengths, ranges, and observations; R11 lengths 2.00, 1.39, 0.70 with
  rates 0.209, 0.362, 0.743 at n = 33; R2's median rate over 20 lines (0.381 at n = 17, 0.620 at n = 33).
- reference_models.md: R7's features off the grids (n = 17, 33, 65); R8's coordinate lines at n = 17 have 97
  distinct points.

No seeds of its own: random lines use designs.md's streams, SeedSequence(seed, spawn_key=(j,)).
Run from docs/checks/: OMP_NUM_THREADS=2 ../../../EMA-v1/.venv/bin/python gram_rates.py
Output: gram_rates.out (this script's stdout).
"""

from __future__ import annotations

import math
import sys
import time
from fractions import Fraction
from functools import lru_cache

import numpy as np

import refmodels as R

FLOOR = Fraction(1, 10**10)  # LINE_RATE_FLOOR
MIN_DEG = 3  # LINE_RATE_MIN_DEGREES
PHI = (1 + math.sqrt(5)) / 2

ROWS: list[tuple] = []


def row(name, quantity, spec, got, tol, ok):
    ROWS.append((name, quantity, spec, got, tol, "yes" if ok else "NO"))
    print(f"{name} | {quantity} | {spec} | {got} | {tol} | {'yes' if ok else 'NO'}", flush=True)


# ---------------------------------------------------------------- the exact Gram basis


@lru_cache(maxsize=None)
def gram_basis(n: int, kmax: int):
    """Exact values p_k(s_j), k = 0 ... kmax, and the norms (1/n) sum p_k^2, for the monic Gram polynomials."""
    s = [Fraction(2 * j - (n - 1), n - 1) for j in range(n)]
    p = [[Fraction(1)] * n, list(s)]
    for k in range(1, kmax):
        beta = Fraction(k * k * (n * n - k * k), (n - 1) ** 2 * (4 * k * k - 1))
        p.append([s[j] * p[k][j] - beta * p[k - 1][j] for j in range(n)])
    p = p[: kmax + 1]
    norms = [sum(v * v for v in pk) / n for pk in p]
    return p, norms


def exact_spectrum(y: np.ndarray):
    """c_k^2 (k = 1 ... K) exact, T(k)^2 exact (k = 1 ... K), the range, and the variance (ddof 0)."""
    n = len(y)
    K = (n - 1) // 2
    yf = [Fraction(float(v)) for v in y]
    p, norms = gram_basis(n, K)
    mean = sum(yf) / n
    var = sum((v - mean) ** 2 for v in yf) / n
    c2 = [None]
    signed = [mean]
    for k in range(1, K + 1):
        ip = sum(yv * pv for yv, pv in zip(yf, p[k])) / n
        c2.append(ip * ip / norms[k])
        signed.append(float(ip) / math.sqrt(float(norms[k])))
    T2 = [None, var]
    for k in range(2, K + 1):
        T2.append(T2[-1] - c2[k - 1])
    rng = max(yf) - min(yf)
    return c2, T2, rng, var, signed


def rate_from_T2(T2, rng, K):
    """(k*, rate or None, reason)."""
    if rng == 0:
        return 0, None, "constant"
    thr = (FLOOR * rng) ** 2
    kstar = 0
    for k in range(1, K + 1):
        if T2[k] > thr:
            kstar = k
        else:
            break
    if kstar < MIN_DEG:
        return kstar, None, f"k* = {kstar}"
    ks = np.arange(1, kstar + 1, dtype=float)
    logT = np.array([0.5 * math.log10(T2[k].numerator) - 0.5 * math.log10(T2[k].denominator)
                     for k in range(1, kstar + 1)])
    slope = np.polyfit(ks, logT, 1)[0]
    return kstar, -slope, ""


def exact_rate(y):
    n = len(y)
    K = (n - 1) // 2
    c2, T2, rng, var, signed = exact_spectrum(y)
    kstar, rate, why = rate_from_T2(T2, rng, K)
    return dict(kstar=kstar, K=K, rate=rate, why=why, range=float(rng), signed=signed)


def lanczos_rate(y):
    """The rate from the float Lanczos basis (what EMA computes, CL2): T(k)^2 = sum_(j >= k) c_j^2."""
    n = len(y)
    K = (n - 1) // 2
    c = lanczos_basis(n).T @ np.asarray(y, dtype=float) / n
    T2 = [None] + [Fraction(float(np.sum(c[k:] ** 2))) for k in range(1, K + 1)]
    rng = Fraction(float(np.max(y))) - Fraction(float(np.min(y)))
    kstar, rate, why = rate_from_T2(T2, rng, K)
    return dict(kstar=kstar, K=K, rate=rate, why=why)


def all_degree_rate(y):
    """The rate with the window K = n - 1 (LINE_RATE_WINDOW's reason), exact."""
    n = len(y)
    K = n - 1
    yf = [Fraction(float(v)) for v in y]
    p, norms = gram_basis(n, K)
    mean = sum(yf) / n
    var = sum((v - mean) ** 2 for v in yf) / n
    T2 = [None, var]
    for k in range(1, K):
        ip = sum(yv * pv for yv, pv in zip(yf, p[k])) / n
        T2.append(T2[-1] - ip * ip / norms[k])
    rng = max(yf) - min(yf)
    return rate_from_T2(T2, rng, K)


# ---------------------------------------------------------------- the float Lanczos basis


def lanczos_basis(n: int) -> np.ndarray:
    """Columns q_k, orthonormal under the average over n points ((1/n) Q^T Q = I)."""
    s = -1 + 2 * np.arange(n) / (n - 1)
    Q = np.zeros((n, n))
    q = np.ones(n) / math.sqrt(n)
    Q[:, 0] = q
    for k in range(1, n):
        w = s * Q[:, k - 1]
        for _ in range(2):
            w -= Q[:, :k] @ (Q[:, :k].T @ w)
        w /= np.linalg.norm(w)  # a positive multiple, so the leading coefficient stays positive
        Q[:, k] = w
    return Q * math.sqrt(n)


def recurrence_basis_float(n: int) -> np.ndarray:
    """Orthonormal Gram polynomials by their three-term recurrence in doubles (coordinate_lines.md: unstable)."""
    s = -1 + 2 * np.arange(n) / (n - 1)
    P = np.zeros((n, n))
    P[:, 0] = 1
    P[:, 1] = s
    for k in range(1, n - 1):
        beta = k * k * (n * n - k * k) / ((n - 1) ** 2 * (4 * k * k - 1))
        P[:, k + 1] = s * P[:, k] - beta * P[:, k - 1]
    P /= np.sqrt((P ** 2).mean(axis=0))
    return P


# ---------------------------------------------------------------- lines (designs.md)


def unit_to_phys(model, z):
    """designs.md, Unit coordinates: u = (z + 1)/2, a linear range lo + (hi - lo) u, a log range through exp."""
    return R.to_physical(model, z)


def build_line(model, z0, z1, n):
    """n points from z0 to z1, t_j = j/(n - 1); a coordinate on a face of the space set exactly to lo or hi."""
    t = np.arange(n) / (n - 1)
    z = z0[None, :] + t[:, None] * (z1 - z0)[None, :]
    z[0] = z0
    z[-1] = z1
    x = unit_to_phys(model, z)
    for j, (name, (lo, hi, _, _)) in enumerate(R.SPACES[model].items()):
        x[name] = np.where(z[:, j] == -1, lo, np.where(z[:, j] == 1, hi, x[name]))
    return x, z


def clip(anchor_z, direction):
    """The two ends of the line through anchor_z in direction, in [-1, 1]^d; t = 0 against the direction."""
    lo_t, hi_t = -np.inf, np.inf
    lo_face = hi_face = None
    for i, (a, d) in enumerate(zip(anchor_z, direction)):
        if d != 0:
            t1, t2 = (-1 - a) / d, (1 - a) / d
            if min(t1, t2) > lo_t:
                lo_t, lo_face = min(t1, t2), (i, -1.0 if d > 0 else 1.0)
            if max(t1, t2) < hi_t:
                hi_t, hi_face = max(t1, t2), (i, 1.0 if d > 0 else -1.0)
    z0 = np.clip(anchor_z + lo_t * direction, -1, 1)
    z1 = np.clip(anchor_z + hi_t * direction, -1, 1)
    z0[lo_face[0]] = lo_face[1]  # an end on a face is exactly that face
    z1[hi_face[0]] = hi_face[1]
    return z0, z1


def coordinate_line(model, i, n):
    d = len(R.SPACES[model])
    z0 = np.zeros(d)
    z1 = np.zeros(d)
    z0[i], z1[i] = -1.0, 1.0
    x, z = build_line(model, z0, z1, n)
    names = list(R.SPACES[model])
    nominal = {k: v[3] for k, v in R.SPACES[model].items()}
    for k in names:
        if k != names[i]:
            x[k] = np.full(n, float(nominal[k]))
    if n % 2 == 1:  # the shared anchor: the middle point is exactly the nominal value
        x[names[i]][(n - 1) // 2] = float(nominal[names[i]])
    return x


def random_line(model, j, n, seed=0):
    d = len(R.SPACES[model])
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(j,))))
    anchor_z = 2 * rng.random(d) - 1
    direction = rng.standard_normal(d)
    direction /= np.linalg.norm(direction)
    z0, z1 = clip(anchor_z, direction)
    x, z = build_line(model, z0, z1, n)
    return x, z0, z1, anchor_z, direction


def given_line(model, anchor_x, direction, n):
    names = list(R.SPACES[model])
    sp = R.SPACES[model]
    az = []
    for k in names:
        lo, hi, scale, _ = sp[k]
        v = anchor_x.get(k, None)
        if v is None:
            az.append(0.0)
        else:
            az.append(2 * (v - lo) / (hi - lo) - 1)  # linear ranges only (R7)
    dvec = np.array([float(direction.get(k, 0)) for k in names])
    z0, z1 = clip(np.array(az), dvec)
    x, z = build_line(model, z0, z1, n)
    return x, z0, z1


def y_of(model, x):
    return R.MODELS[model](x)


def fmt(v, digits=4):
    if v is None:
        return "none"
    return f"{v:.{digits}g}"


# ---------------------------------------------------------------- the checks


def check_coordinate_lines():
    print("\n# coordinate_lines.md, Expected answers\n")
    rates = {}
    for n in (17, 33, 65, 129):
        for i, name in enumerate("abce"):
            r = exact_rate(y_of("R7", coordinate_line("R7", i, n)))
            rates[(name, n)] = r
    spec17 = dict(a=0.1811111, b=0.06916461, c=0.1957442, e=0.1811111)
    spec33 = dict(a=0.1103366, b=0.03749946, c=0.2088262, e=0.1103366)
    for n, spec in ((17, spec17), (33, spec33)):
        for name, v in spec.items():
            got = rates[(name, n)]["rate"]
            row(f"R7, n = {n}", f"rate along {name}", v, f"{got:.7g}", "1e-6", abs(got - v) <= 1e-6)
    # R8 = R7 + 0 f + 0 g: the same lines along a, b, c, e
    for n in (17, 33):
        for i, name in enumerate("abce"):
            r8 = exact_rate(y_of("R8", coordinate_line("R8", i, n)))["rate"]
            row(f"R8, n = {n}", f"rate along {name} equals R7's", f"{rates[(name, n)]['rate']:.7g}", f"{r8:.7g}",
                "exact", r8 == rates[(name, n)]["rate"])
    for n in (33, 65, 129):
        got = rates[("c", n)]["rate"]
        row(f"R7 along c, n = {n}", "rate vs log10 phi = 0.2090", f"{math.log10(PHI):.4f}", f"{got:.4f}", "0.01",
            abs(got - math.log10(PHI)) <= 0.01)
    spec_comp = {33: 0.2088, 65: 0.2136, 129: 0.2112}
    for n, v in spec_comp.items():
        got = rates[("c", n)]["rate"]
        row(f"R7 along c, n = {n}", "the spec's 'computed' value", v, f"{got:.4f}", "4 digits",
            abs(got - v) < 0.6e-4)
    ratio_spec = dict(a=(0.61, 0.51, 0.55), b=(0.54, 0.52, 0.52), c=(1.07, 1.02, 0.99))
    for name, spec in ratio_spec.items():
        lo, hi = ((0.45, 0.65) if name != "c" else (0.95, 1.1))
        for (n1, n2), v in zip(((17, 33), (33, 65), (65, 129)), spec):
            got = rates[(name, n2)]["rate"] / rates[(name, n1)]["rate"]
            row(f"R7 along {name}, {n1} -> {n2}", "rate ratio", v, f"{got:.2f}", f"[{lo}, {hi}]",
                lo <= got <= hi and abs(got - v) < 0.0051)
    # R8 along f and g: constant
    for i, name in ((4, "f"), (5, "g")):
        y = y_of("R8", coordinate_line("R8", i, 17))
        r = exact_rate(y)
        row("R8, n = 17", f"along {name}", "constant, y = 1", f"{r['why']}, y = {set(y.tolist())}", "exact",
            r["why"] == "constant" and set(y.tolist()) == {1.0})
    # R8: 97 distinct points
    pts = set()
    for i in range(6):
        x = coordinate_line("R8", i, 17)
        for j in range(17):
            pts.add(tuple(float(x[k][j]) for k in "abcefg"))
    row("R8, n = 17", "distinct points", 97, len(pts), "exact", len(pts) == 97)
    # mock report's observations for R8 at n = 17
    allys = []
    ranges = {}
    for i, name in enumerate("abcefg"):
        y = y_of("R8", coordinate_line("R8", i, 17))
        allys.append(y)
        ranges[name] = y.max() - y.min()
        r = exact_rate(y)
    ally = np.concatenate(allys)
    row("R8 mock", "min; max; (max-min)/max|y|", "0.2; 2; 0.9",
        f"{fmt(ally.min())}; {fmt(ally.max())}; {fmt((ally.max()-ally.min())/abs(ally).max())}", "4 digits",
        (fmt(ally.min()), fmt(ally.max()), fmt((ally.max()-ally.min())/abs(ally).max())) == ("0.2", "2", "0.9"))
    row("R8 mock", "ranges a, b, c, e, f, g", "0.4, 1, 0.8, 0.4, 0, 0",
        ", ".join(fmt(ranges[k]) for k in "abcefg"), "4 digits",
        [fmt(ranges[k]) for k in "abcefg"] == ["0.4", "1", "0.8", "0.4", "0", "0"])
    row("R8 mock", "degrees a, b, c, e", "8 of 8 each",
        ", ".join(f"{rates[(k, 17)]['kstar']} of {rates[(k, 17)]['K']}" for k in "abce"), "exact",
        all(rates[(k, 17)]["kstar"] == 8 for k in "abce"))

    # R1: k* = 1 along a, b, k; c has no effect, so its line is constant
    for i, name in enumerate("abck"):
        r = exact_rate(y_of("R1", coordinate_line("R1", i, 17)))
        want = "0; none: constant" if name == "c" else "1; none"
        ok = r["why"] == "constant" if name == "c" else (r["kstar"] == 1 and r["rate"] is None)
        row("R1, n = 17", f"along {name}: k*; rate", want, f"{r['kstar']}; {fmt(r['rate'])} {r['why']}",
            "exact", ok)
    # R10
    spec = dict(a=1, b=2, c=0, e=0)
    for i, name in enumerate("abce"):
        r = exact_rate(y_of("R10", coordinate_line("R10", i, 17)))
        row("R10, n = 17", f"along {name}: k*", spec[name], f"{r['kstar']} {r['why']}", "exact",
            r["kstar"] == spec[name] and (spec[name] > 0 or r["why"] == "constant"))
    # R2 along x3
    y = y_of("R2", coordinate_line("R2", 2, 17))
    row("R2, n = 17", "along x3: constant, value", "constant, 0", f"{set(y.tolist())}", "exact",
        set(y.tolist()) == {0.0})
    # R3 at n = 17 and its k* (0058)
    spec_r3 = dict(rw=(1.642241, 7), r=(3.143281, 4), Tu=(0.8161252, 8), Hu=(None, 1), Tl=(0.8160101, 8),
                   Hl=(None, 1), L=(0.9904442, 8), Kw=(3.630201, 3))
    for i, name in enumerate(R.SPACES["R3"]):
        r = exact_rate(y_of("R3", coordinate_line("R3", i, 17)))
        v, k = spec_r3[name]
        ok = r["kstar"] == k and (r["rate"] is None if v is None else abs(r["rate"] - v) <= 2e-4)
        row("R3, n = 17", f"along {name}: rate; k* of K; range", f"{v}; {k}",
            f"{fmt(r['rate'], 7)}; {r['kstar']} of {r['K']}; {fmt(r['range'])}", "2e-4 (0058); k* exact", ok)
        lz = lanczos_rate(y_of("R3", coordinate_line("R3", i, 17)))
        diff = 0.0 if v is None else abs(lz["rate"] - r["rate"])
        row("R3, n = 17", f"along {name}: Lanczos rate - exact; k*", "within 2e-4; same k*",
            f"{diff:.1e}; {lz['kstar']}", "2e-4 (0058)", lz["kstar"] == r["kstar"] and diff <= 2e-4)
        # the deterministic bound of one ulp in each y: each point moved by one ulp alone, the effects summed
        # with their worst signs, then checked by a run with those signs (0058); and a QR basis's rate
        if v is not None:
            y0 = y_of("R3", coordinate_line("R3", i, 17))
            eff = []
            for jj in range(len(y0)):
                yp = y0.copy()
                yp[jj] = np.nextafter(y0[jj], np.inf)
                eff.append(exact_rate(yp)["rate"] - r["rate"])
            signs = np.sign(eff)
            bound = float(np.sum(np.abs(eff)))
            for ulps in (1, 2):
                yw = y0.copy()
                for _ in range(ulps):
                    yw = np.array([np.nextafter(t, t + sg * np.inf) if sg else t for t, sg in zip(yw, signs)])
                rw_ = exact_rate(yw)
                worst = abs(rw_["rate"] - r["rate"])
                row("R3, n = 17", f"along {name}: rate change, {ulps} ulp(s) in each y, worst signs",
                    "below 2e-4 with Lanczos's", f"{worst:.1e} (1-ulp sum of effects {bound:.1e})", "2e-4 (0058)",
                    worst + diff < 2e-4 and rw_["kstar"] == r["kstar"])
            q, _ = np.linalg.qr(np.vander(-1 + 2 * np.arange(17) / 16, 17, increasing=True))
            cq = (q * math.sqrt(17)).T @ y0 / 17
            K = 8
            T2q = [None] + [Fraction(float(np.sum(cq[k:] ** 2))) for k in range(1, K + 1)]
            rq = rate_from_T2(T2q, Fraction(float(np.max(y0))) - Fraction(float(np.min(y0))), K)
            row("R3, n = 17", f"along {name}: QR-basis rate - exact; k*", "for 0058's context",
                f"{abs(rq[1] - r['rate']):.1e}; {rq[0]}", "2e-4 (0058)", rq[0] == r["kstar"] and abs(rq[1] - r["rate"]) < 2e-4)
    # R4a, R4b
    for i, name in enumerate("abc"):
        ra = exact_rate(y_of("R4a", coordinate_line("R4", i, 17)))
        rb = exact_rate(y_of("R4b", coordinate_line("R4", i, 17)))
        row("R4a, n = 17", f"along {name}", "none: constant", ra["why"], "exact", ra["why"] == "constant")
        row("R4b, n = 17", f"along {name}: k*; rate", "k* >= 3; a rate", f"{rb['kstar']}; {fmt(rb['rate'])}",
            "exact", rb["kstar"] >= 3 and rb["rate"] is not None)
    # R5, z along b
    x = coordinate_line("R5", 1, 17)
    yv, zv, err, tmo = R.r5(x)
    usable = ~np.isnan(zv) & ~err & ~tmo
    missing_b = x["b"][np.isnan(zv)].tolist()
    row("R5, z, n = 17", "along b: usable; missing at b", "15 of 17; 0.875, 1",
        f"{usable.sum()} of 17; {missing_b}", "exact", usable.sum() == 15 and missing_b == [0.875, 1.0])
    # R2 under 2^-10 y + 3
    for i, name in enumerate(("x1", "x2", "x3")):
        for n in (17, 33, 65):
            y = y_of("R2", coordinate_line("R2", i, n))
            r0 = exact_rate(y)
            r1 = exact_rate(2.0 ** -10 * y + 3)
            d = None if r0["rate"] is None else abs(r0["rate"] - r1["rate"])
            ok = (r0["kstar"] == r1["kstar"] and r0["why"] == r1["why"]
                  and (d is None or d <= 1e-5)
                  and abs(r1["range"] - 2.0 ** -10 * r0["range"]) <= 1e-15 * max(1, r0["range"]))
            row(f"R2 shift, n = {n}", f"along {name}: rate change; k*",
                "<= 1e-5; same", f"{fmt(d, 2)}; {r0['kstar']} -> {r1['kstar']}", "RATE_SHIFT_TOL", ok)


def check_coordinate_lines_text():
    print("\n# coordinate_lines.md, text: the 'What it gives' table\n")
    table = {
        ("R7", 2, "R7 along c"): (0.155, 0.196, 0.209, 0.214, 0.211, (16, 16)),
        ("R3", 6, "R3 along L"): (0.967, 0.990, 0.990, 0.990, 0.992, (10, 16)),
        ("R3", 1, "R3 along r"): (3.139, 3.143, 3.151, 3.153, 3.157, (4, 16)),
        ("R2", 0, "R2 along x1"): (0.277, 0.493, 0.700, 0.692, 0.693, (15, 16)),
        ("R7", 0, "R7 along a"): (0.264, 0.181, 0.110, 0.056, 0.031, (16, 16)),
        ("R7", 1, "R7 along b"): (0.134, 0.069, 0.037, 0.020, 0.010, (16, 16)),
        ("R1", 0, "R1 along a"): (None,) * 5 + ((1, 16),),
        ("R10", 1, "R10 along b"): (None,) * 5 + ((2, 16),),
    }
    for (model, i, label), spec in table.items():
        for n, v in zip((9, 17, 33, 65, 129), spec[:5]):
            r = exact_rate(y_of(model, coordinate_line(model, i, n)))
            got = r["rate"]
            if v is None:
                ok = got is None
            else:
                ok = got is not None and abs(got - v) <= 0.00051 * 1.0001 if v < 1 else abs(got - v) <= 0.00051
            extra = f" [{r['kstar']}/{r['K']}]" if n == 33 else ""
            row(label, f"rate, n = {n}", fmt(v, 3) if v is not None else "none",
                (f"{got:.4f}" if got is not None else "none") + extra, "3 decimals",
                ok and (n != 33 or (r["kstar"], r["K"]) == spec[5]))
    print("\n# LINE_RATE_WINDOW's reason: R7 along c with every degree (0.246, 0.255, 0.223)\n")
    for n in (17, 33, 65, 129):
        kstar, rate, why = all_degree_rate(y_of("R7", coordinate_line("R7", 2, n)))
        want = {17: 0.246, 33: 0.255, 65: 0.223}.get(n)
        row("R7 along c, all degrees", f"rate, n = {n} (k* {kstar})", want if want else "-",
            fmt(rate), "3 decimals", want is None or abs(rate - want) <= 0.0005)
    print("\n# the three-term recurrence in doubles; Lanczos against exact\n")
    for n in (17, 33, 65):
        P = recurrence_basis_float(n)
        err = np.abs(P.T @ P / n - np.eye(n)).max()
        row("recurrence in doubles", f"max |(1/n)G^T G - I|, n = {n}", {33: "1e-8", 65: "0.4"}.get(n, "-"),
            f"{err:.1e}", "order of magnitude", True)
    for n in (17, 33, 65, 129):
        Q = lanczos_basis(n)
        orth = np.abs(Q.T @ Q / n - np.eye(n)).max()
        K = (n - 1) // 2
        worst = {}
        for model, i in (("R7", 0), ("R7", 1), ("R7", 2), ("R3", 1), ("R2", 0)):
            y = y_of(model, coordinate_line(model, i, n))
            ex = exact_rate(y)
            c = Q.T @ y / n
            diff = np.abs(c[: K + 1] - np.array(ex["signed"]))
            worst[model] = max(worst.get(model, 0.0), diff[1:].max() / ex["range"], diff[0] / np.abs(y).max())
        row("Lanczos vs exact", f"max |c_k diff|, n = {n}: R7 / range (CL2); R3 r, R2 x1; c_0 / max|y|",
            "within 4e-16 on R7 (n = 17, 65, 129)", f"R7 {worst['R7']:.1e}; R3 {worst['R3']:.1e}; R2 {worst['R2']:.1e}; "
            f"orthonormality {orth:.1e}", "CL2: 1e-14 of the range (R7); I within 1e-13",
            worst["R7"] <= 1e-14 and orth <= 1e-13)
    print("\n# R7's features off the grids\n")
    for n in (17, 33, 65):
        grid = -1 + 2 * np.arange(n) / (n - 1)
        hits = [v for v in (0.6, 0.2) if np.any(np.isclose(grid, v, atol=1e-12))]
        row("R7 grid", f"coordinate line points at 0.6 or 0.2, n = {n}", "none", hits or "none", "exact", not hits)


def check_lines():
    print("\n# lines.md, Expected answers and mock report\n")
    spec_rates = (0.8166077, 0.6447274, 0.2184303, 0.07051713, 0.1891380)
    spec_len = (0.6417, 2.665, 2.367, 2.17, 2.275)
    spec_range = (0.4261, 0.3665, 1.274, 1.132, 1.102)
    spec_ends = {
        "a": ("0.6198 → 1", "-1 → 1", "1 → -1", "-1 → 1", "0.2123 → 0.783"),
        "b": ("-0.4175 → -0.3458", "-0.1497 → -0.6877", "-0.9938 → 0.003045", "-0.1718 → 0.3618",
              "-0.2506 → -0.8688"),
        "c": ("0.1892 → 0.5543", "-0.1069 → 0.381", "0.1505 → 0.6742", "-0.1998 → 0.1157", "-1 → 1"),
        "e": ("-1 → -0.6411", "0.9332 → -0.672", "0.3123 → 0.8897", "-0.3275 → -0.8983", "0.0431 → 0.7265"),
    }
    allys = []
    for j in range(5):
        x, z0, z1, _, _ = random_line("R7", j, 17)
        y = y_of("R7", x)
        allys.append(y)
        r = exact_rate(y)
        length = float(np.linalg.norm(z1 - z0))
        row(f"R7 random line {j}", "rate", spec_rates[j], f"{r['rate']:.7g}", "1e-6",
            abs(r["rate"] - spec_rates[j]) <= 1e-6)
        row(f"R7 random line {j}", "length; range; k*", f"{spec_len[j]}; {spec_range[j]}; 8 of 8",
            f"{fmt(length)}; {fmt(r['range'])}; {r['kstar']} of {r['K']}", "4 digits",
            fmt(length) == fmt(spec_len[j]) and fmt(r["range"]) == fmt(spec_range[j]) and r["kstar"] == 8)
        for k in "abce":
            got = f"{fmt(float(x[k][0]))} → {fmt(float(x[k][-1]))}"
            row(f"R7 random line {j}", f"ends of {k}", spec_ends[k][j], got, "4 digits", got == spec_ends[k][j])
    ally = np.concatenate(allys)
    got = f"{fmt(ally.min())}; {fmt(ally.max())}; {fmt((ally.max() - ally.min()) / abs(ally).max())}"
    row("R7 random mock", "min; max; (max-min)/max|y|", "0.2; 1.995; 0.8997", got, "4 digits",
        got == "0.2; 1.995; 0.8997")

    # R7 given lines
    spec_given = {17: 0.2025713, 33: 0.1082395, 65: 0.05902797}
    for n, v in spec_given.items():
        x, z0, z1 = given_line("R7", {}, {"a": 1, "e": 1}, n)
        r = exact_rate(y_of("R7", x))
        length = float(np.linalg.norm(z1 - z0))
        row(f"R7 given diagonal, n = {n}", "length; rate", f"2.828; {v}", f"{length:.6f}; {r['rate']:.7g}",
            "exact; 1e-6", abs(length - 2 * math.sqrt(2)) < 1e-15 and abs(r["rate"] - v) <= 1e-6)
    # R10's two given lines through the nominal point (0058, LN5): line 0, (a, e) = (1, 1), varies (k* = 1);
    # line 1, along e (no effect), is constant at -sqrt(5)/4, so only line 1 has a note
    x0, _, _ = given_line("R10", {}, {"a": 1, "e": 1}, 17)
    x1, _, _ = given_line("R10", {}, {"e": 1}, 17)
    r0, r1_ = exact_rate(y_of("R10", x0)), exact_rate(y_of("R10", x1))
    y1 = y_of("R10", x1)
    row("R10 given lines, n = 17", "line 0: k*; rate", "1; none", f"{r0['kstar']}; {fmt(r0['rate'])}", "exact",
        r0["kstar"] == 1 and r0["rate"] is None)
    row("R10 given lines, n = 17", "line 1: constant; value", "constant, -0.559",
        f"{r1_['why'] or 'NOT constant'}, {sorted(set(format(v, '.4g') for v in y1.tolist()))}", "exact",
        r1_["why"] == "constant" and len(set(y1.tolist())) == 1 and format(y1[0], ".4g") == "-0.559")

    # R11 random lines, m = 10, seed 0, n = 33, 65, 129, against the Bernstein ellipse of the nearest pole
    spec_r11 = {0: 0.2090, 1: 0.2090, 3: 0.2090, 4: 0.2090, 5: 0.2090, 6: 0.2090, 9: 0.2090, 2: 0.7532,
                7: 0.2555, 8: 0.3568}
    for j in range(10):
        _, z0, z1, _, _ = random_line("R11", j, 33)
        mid, half = (z0 + z1) / 2, (z1 - z0) / 2
        best = np.inf
        for i in range(2):
            if half[i] == 0:
                continue
            for pole in (0.5j, -0.5j):
                w = (pole - mid[i]) / half[i]
                root = np.sqrt(w * w - 1)
                rho = max(abs(w + root), abs(w - root))
                best = min(best, rho)
        analytic = math.log10(best)
        length = float(np.linalg.norm(z1 - z0))
        devs = []
        for n in (33, 65, 129):
            x, _, _, _, _ = random_line("R11", j, n)
            devs.append(exact_rate(y_of("R11", x))["rate"] - analytic)
        ok = abs(analytic - spec_r11[j]) < 0.6e-4 and all(abs(d) <= 0.02 for d in devs)
        row(f"R11 random line {j} (length {length:.3f})", "log10 rho; rate - log10 rho at n = 33, 65, 129",
            f"{spec_r11[j]}; within 0.02", f"{analytic:.4f}; " + ", ".join(f"{d:+.4f}" for d in devs), "0.02", ok)

    # R1 and R10 random lines
    for model, k in (("R1", 1), ("R10", 2)):
        for j in range(5):
            x, *_ = random_line(model, j, 17)
            r = exact_rate(y_of(model, x))
            row(f"{model} random line {j}", "k*; rate", f"{k}; none", f"{r['kstar']}; {fmt(r['rate'])}", "exact",
                r["kstar"] == k and r["rate"] is None)
    # R4a
    for j in range(5):
        x, *_ = random_line("R4", j, 17)
        r = exact_rate(y_of("R4a", x))
        row(f"R4a random line {j}", "rate", "none: constant", r["why"], "exact", r["why"] == "constant")
    # R5 random lines
    for j in range(5):
        x, *_ = random_line("R5", j, 17)
        yv, zv, err, tmo = R.r5(x)
        missing = np.isnan(zv) & ~err & ~tmo
        row(f"R5 random line {j}", "error; timeout; z missing (of 17)", "by region",
            f"{err.sum()}; {tmo.sum()}; {missing.sum()}", "by construction", True)
    # R2 shift on random lines
    for j in range(5):
        for n in (17, 33, 65):
            x, *_ = random_line("R2", j, n)
            y = y_of("R2", x)
            r0, r1 = exact_rate(y), exact_rate(2.0 ** -10 * y + 3)
            d = None if r0["rate"] is None else abs(r0["rate"] - r1["rate"])
            row(f"R2 shift, random line {j}, n = {n}", "rate change; k*", "<= 1e-5; same",
                f"{fmt(d, 2)}; {r0['kstar']} -> {r1['kstar']}", "RATE_SHIFT_TOL",
                r0["kstar"] == r1["kstar"] and (d is None or d <= 1e-5))

    print("\n# lines.md, text\n")
    # R11: lengths 2.00, 1.39, 0.70 with rates 0.209, 0.362, 0.743 at n = 33
    found = []
    for j in range(10):
        x, z0, z1, _, _ = random_line("R11", j, 33)
        found.append((float(np.linalg.norm(z1 - z0)), exact_rate(y_of("R11", x))["rate"]))
    row("R11, n = 33", "lengths 2.00, 1.39, 0.70: rates 0.209, 0.362, 0.743", "as stated",
        "; ".join(f"{L:.2f}: {r:.3f}" for L, r in found), "find them", True)
    # R2 median over 20 lines
    for n, v in ((17, 0.381), (33, 0.620)):
        rs = []
        for j in range(20):
            x, *_ = random_line("R2", j, n)
            rr = exact_rate(y_of("R2", x))["rate"]
            if rr is not None:
                rs.append(rr)
        med = float(np.median(rs))
        row("R2, 20 random lines, seed 0", f"median rate, n = {n}", v, f"{med:.3f} ({len(rs)} rates)",
            "3 decimals", abs(med - v) < 0.0006)


def main():
    t0 = time.time()
    print(f"gram_rates.py; Python {sys.version.split()[0]}, numpy {np.__version__}")
    print("row | quantity | spec value | recomputed | tolerance | agrees?")
    check_coordinate_lines()
    check_coordinate_lines_text()
    check_lines()
    bad = [r for r in ROWS if r[5] == "NO"]
    print(f"\n{len(ROWS)} rows, {len(bad)} disagree; {time.time() - t0:.0f} s")
    for r in bad:
        print("DISAGREES:", " | ".join(str(v) for v in r))


if __name__ == "__main__":
    main()
