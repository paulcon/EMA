"""Step 11's independent check of docs/design/diagnostics/scatter.md, "Expected answers" (and its mock report).

What it checks, row by row:

- R1, R2, R10 (mean, standard deviation, rho, S): the estimate at n = 20,000 (KNOWN_ANSWER_N), seed 0, the
  `random` sampler (default_rng(seed).random((n, d))), against the expected value; and the tolerance,
  recomputed as 5 (KNOWN_ANSWER_SDS) x the estimate's standard deviation over 100 designs, seeds 1-100.
  The estimators are written from scatter.md, "Computation": ddof 1; Spearman with average ranks; the binned
  index with floor(sqrt(n_u)) bins from a stable sort, numpy's array_split, adjusted
  S = 1 - (1 - eta2)(n_u - 1)/(n_u - B).
- The expected values: analytic ones from the formulas in reference_models.md (variance contributions); the
  rank correlations by quasi-Monte Carlo (8 scrambled Sobol sets of 2**22 points, seeds 1000-1007), the spec's
  source since step 11, and by brute force (2,000,000 uniform points, seed 20261001; Spearman over all).
- R4b: the relative spread (max - min)/max|y| (shared.md, Observations) at n = 20,000, seed 0, against
  8e-13, within 1%; and that y is not constant (so estimates are present).
- R5, n = 200, seed 0: the runs not usable, by kind, for y and for z (by construction from the regions).
- R2, n = 200, seed 1: the mock report's estimates, observations, and bootstrap intervals (1000 resamples from
  Generator(PCG64(SeedSequence(1, spawn_key=(2**32 + 1,)))), percentiles 0.5 and 99.5, S on each
  resample's distinct runs in the design's order), to 4 significant digits.

Not checked here: "R5, every estimate equal to scatter on the usable runs alone" and R4a's note (properties of
EMA's code, by construction; nothing to compute without it).

Run from docs/checks: OMP_NUM_THREADS=2 ../../../EMA-v1/.venv/bin/python scatter.py
"""

from __future__ import annotations

import math
import sys
import time

import numpy as np
from scipy.stats import rankdata

import refmodels as R

N = 20_000
SEEDS = range(1, 101)
SDS = 5
BRUTE_N = 2_000_000
BRUTE_SEED = 20261001
BOOT_TAG = 2**32 + 1
QMC_REPS = 8
QMC_LOG2N = 22

lines_out: list[str] = []


def out(s: str = "") -> None:
    print(s)
    lines_out.append(s)


def design(model: str, n: int, seed: int) -> np.ndarray:
    d = len(R.SPACES[R.space_of(model)])
    return 2 * np.random.default_rng(seed).random((n, d)) - 1


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = rankdata(x), rankdata(y)
    rx -= rx.mean()
    ry -= ry.mean()
    return float(rx @ ry / math.sqrt((rx @ rx) * (ry @ ry)))


def binned(x: np.ndarray, y: np.ndarray) -> float:
    n = len(y)
    B = math.isqrt(n)
    order = np.argsort(x, kind="stable")
    ybar = y.mean()
    ss = float(((y - ybar) ** 2).sum())
    between = sum(len(g) * (g.mean() - ybar) ** 2 for g in np.array_split(y[order], B))
    eta2 = between / ss
    return 1 - (1 - eta2) * (n - 1) / (n - B)


def estimates(z: np.ndarray, y: np.ndarray) -> dict[str, float]:
    est = {"mean": float(y.mean()), "sd": float(y.std(ddof=1))}
    for j in range(z.shape[1]):
        est[f"rho{j}"] = spearman(z[:, j], y)
        est[f"S{j}"] = binned(z[:, j], y)
    return est


def row(label: str, qty: str, spec: float, got: float, tol: float | None, tol_got: float | None) -> None:
    ok = abs(got - spec) <= tol if tol is not None else None
    tol_s = f"{tol:.2g}" if tol is not None else "-"
    tg = f"{tol_got:.2g}" if tol_got is not None else "-"
    tol_ok = ""
    if tol is not None and tol_got is not None:
        # The spec gives tolerances to 2 significant digits (rounded up or to nearest): agree within 15%.
        tol_ok = "tol ok" if abs(tol_got - tol) <= 0.15 * tol + 1e-12 else "TOL DIFFERS"
    out(f"| {label} | {qty} | {spec:.6g} | {got:.6g} | {tol_s} | {tg} | {'yes' if ok else 'NO'} {tol_ok} |")


EXPECTED = {
    # model: (names, mean, sd, rho, S, tolerances: mean, sd, rho list, S list)
    "R1": ("a b c k".split(), 10, math.sqrt(14 / 3), [0.8073, -0.2525, 0, 0.5156], [9 / 14, 1 / 14, 0, 4 / 14],
           (0.089, 0.045, [0.012, 0.034, 0.036, 0.027], [0.017, 0.018, 0.004, 0.026])),
    "R2": ("x1 x2 x3".split(), 3.5, 3.721, [0.4374, 0, 0], [0.3139, 0.4424, 0],
           (0.12, 0.11, [0.026, 0.038, 0.043], [0.022, 0.027, 0.006])),
    "R10": ("a b c e".split(), 0, math.sqrt(6.5), [0.7980, 0, 0.000, 0], [0.6154, 0.0385, 0, 0],
            (0.094, 0.070, [0.017, 0.036, 0.040, 0.034], [0.021, 0.013, 0.006, 0.004])),
}


def analytic_truths() -> dict[str, tuple[float, float, list[float]]]:
    """Mean, standard deviation, and first-order indices from the formulas (uniform on the unit cube)."""
    # R1: 10 + 3u_a - u_b + 2u_k, Var(u) = 1/3.
    v1 = np.array([9, 1, 0, 4]) / 3
    # R2: Ishigami with a = 7, b = 0.1 (Ishigami and Homma 1990; Sobol' and Levitan 1999).
    a, b, pi = 7.0, 0.1, math.pi
    V1 = 0.5 * (1 + b * pi**4 / 5) ** 2
    V2 = a**2 / 8
    V13 = b**2 * pi**8 * (1 / 18 - 1 / 50)
    V2tot = V1 + V2 + V13
    # R10: 2 psi1(a) + 0.5 psi2(b) + 1.5 psi1(a) psi1(c), orthonormal terms.
    return {
        "R1": (10.0, math.sqrt(v1.sum()), list(v1 / v1.sum())),
        "R2": (a / 2, math.sqrt(V2tot), [V1 / V2tot, V2 / V2tot, 0.0]),
        "R10": (0.0, math.sqrt(6.5), [4 / 6.5, 0.25 / 6.5, 0.0, 0.0]),
    }


def brute_rho(model: str) -> list[float]:
    d = len(R.SPACES[model])
    z = 2 * np.random.default_rng(BRUTE_SEED).random((BRUTE_N, d)) - 1
    y = R.evaluate_unit(model, z)
    return [spearman(z[:, j], y) for j in range(d)]


def qmc_rho(model: str) -> tuple[np.ndarray, np.ndarray]:
    """Population rank correlations by scrambled Sobol points: QMC_REPS independent scramblings of 2**QMC_LOG2N
    points each (seeds 1000-1007); the mean and its standard error."""
    from scipy.stats import qmc

    d = len(R.SPACES[model])
    reps = []
    for rep in range(QMC_REPS):
        z = 2 * qmc.Sobol(d, scramble=True, seed=1000 + rep).random_base2(QMC_LOG2N) - 1
        y = R.evaluate_unit(model, z)
        reps.append([spearman(z[:, j], y) for j in range(d)])
    reps = np.array(reps)
    return reps.mean(0), reps.std(0, ddof=1) / math.sqrt(QMC_REPS)


def known_answers() -> None:
    truths = analytic_truths()
    out(f"## Known answers: n = {N}, seed 0; tolerance = {SDS} x SD over seeds 1-100 at n = {N}")
    out(f"Brute-force rank correlations: {BRUTE_N} points, seed {BRUTE_SEED} (its standard error is about "
        f"(1 - rho^2)/sqrt(n) = 7e-4, so it agrees within 3 x that); and by quasi-Monte Carlo: {QMC_REPS} "
        f"scrambled Sobol designs of 2^{QMC_LOG2N} points (seeds 1000-{999 + QMC_REPS}), which must round to the "
        f"spec's 4 digits.")
    out("")
    out("| Row | Quantity | Spec expected | Recomputed | Spec tol | Recomputed tol | Agrees? |")
    out("|---|---|---|---|---|---|---|")
    for model, (names, m, s, rho, S, tols) in EXPECTED.items():
        est0 = estimates(design(model, N, 0), R.evaluate_unit(model, design(model, N, 0)))
        reps = [estimates(z, R.evaluate_unit(model, z)) for z in (design(model, N, s) for s in SEEDS)]
        sd = {k: float(np.std([r[k] for r in reps], ddof=1)) for k in est0}
        tm, ts, s_true = truths[model]
        rb = brute_rho(model)
        rq, rq_se = qmc_rho(model)
        row(model, "mean: truth vs spec", m, tm, 1e-12, None)
        row(model, "sd: truth vs spec", s, ts, 5e-4, None)
        row(model, "mean at seed 0", m, est0["mean"], tols[0], SDS * sd["mean"])
        row(model, "sd at seed 0", s, est0["sd"], tols[1], SDS * sd["sd"])
        for j, nm in enumerate(names):
            row(model, f"rho {nm}: brute force vs spec", rho[j], rb[j], 3 * (1 - rho[j] ** 2) / math.sqrt(BRUTE_N),
                None)
            row(model, f"rho {nm}: QMC (to 4 digits) vs spec", rho[j], rq[j], 5e-5, None)
            row(model, f"rho {nm} at seed 0", rho[j], est0[f"rho{j}"], tols[2][j], SDS * sd[f"rho{j}"])
        for j, nm in enumerate(names):
            row(model, f"S {nm}: truth vs spec", S[j], s_true[j], 5e-4, None)
            row(model, f"S {nm} at seed 0", S[j], est0[f"S{j}"], tols[3][j], SDS * sd[f"S{j}"])
        out(f"| {model} | brute-force rho, all digits | | {', '.join(f'{v:.5f}' for v in rb)} | | | |")
        out(f"| {model} | QMC rho, all digits (standard error) | | "
            f"{', '.join(f'{v:.6f} ({e:.1g})' for v, e in zip(rq, rq_se))} | | | |")
    out("")


def r4b() -> None:
    z = design("R4b", N, 0)
    y = R.evaluate_unit("R4b", z)
    spread = (y.max() - y.min()) / np.abs(y).max()
    out("## R4b, n = 20000, seed 0")
    out(f"distinct values: {len(np.unique(y))} (constant only if 1); relative spread {spread:.6g}; "
        f"spec about 8e-13, within 1%: {'yes' if abs(spread - 8e-13) <= 0.01 * 8e-13 else 'NO'}; "
        f"the limit 2e-12/2.5 = {2e-12 / 2.5:.6g}")
    out("")


def r5() -> None:
    z = design("R5", 200, 0)
    p = R.to_physical("R5", z)
    y, zz, error, timeout = R.r5(p)
    failed = error | timeout
    missing_z = np.isnan(zz) & ~failed
    out("## R5, n = 200, seed 0 (by construction)")
    out(f"failed (error, a + b > 1): {int(error.sum())}; failed (timeout, a, b < -0.8): {int(timeout.sum())}; "
        f"usable for y: {int((~failed).sum())}; missing z (b > 0.8, not failed): {int(missing_z.sum())}; "
        f"usable for z: {int((~failed & ~missing_z).sum())}")
    out("Expected over the space: error 1/8 (25 of 200), timeout 1/100 (2 of 200).")
    out("")


def mock_report() -> None:
    n, seed = 200, 1
    z = 2 * np.random.default_rng(seed).random((n, 3)) - 1
    y = R.evaluate_unit("R2", z)
    est = estimates(z, y)
    g = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(BOOT_TAG,))))
    idx = g.integers(0, n, (1000, n))
    boot = {k: [] for k in est}
    for i in idx:
        zb, yb = z[i], y[i]
        boot["mean"].append(yb.mean())
        boot["sd"].append(yb.std(ddof=1))
        u = np.unique(i)  # distinct runs, in the design's order
        for j in range(3):
            boot[f"rho{j}"].append(spearman(zb[:, j], yb))
            boot[f"S{j}"].append(binned(z[u, j], y[u]))
    mock = {"mean": (3.582, 2.906, 4.232), "sd": (3.826, 3.275, 4.299),
            "rho0": (0.4185, 0.2651, 0.5489), "rho1": (0.02173, -0.1663, 0.1955),
            "rho2": (-0.009447, -0.2193, 0.1803), "S0": (0.2944, 0.1888, 0.4248),
            "S1": (0.4068, 0.2816, 0.5257), "S2": (-0.004922, -0.07658, 0.103)}
    out("## Mock report: R2, n = 200, seed 1 (4 significant digits)")
    out("| Estimate | Mock | Recomputed | Agrees? |")
    out("|---|---|---|---|")
    f = lambda v: format(v, ".4g")  # noqa: E731
    for k, (e, lo, hi) in mock.items():
        lo2, hi2 = np.percentile(boot[k], [0.5, 99.5])
        got = (f(est[k]), f(lo2), f(hi2))
        want = (f(e), f(lo), f(hi))
        out(f"| {k} | {want} | {got} | {'yes' if got == want else 'NO'} |")
    obs = (f(y.min()), f(y.max()), f((y.max() - y.min()) / np.abs(y).max()))
    out(f"| observations min, max, spread | ('-9.094', '12.85', '1.708') | {obs} | "
        f"{'yes' if obs == ('-9.094', '12.85', '1.708') else 'NO'} |")
    out(f"| bins | 14 | {math.isqrt(n)} | |")
    out("")


def main() -> None:
    t0 = time.time()
    out("# scatter.py: step 11 check of diagnostics/scatter.md, Expected answers")
    out(f"numpy {np.__version__}, Python {sys.version.split()[0]}")
    out("")
    known_answers()
    r4b()
    r5()
    mock_report()
    out(f"Runtime: {time.time() - t0:.0f} s")
    with open("scatter.out", "w") as fh:
        fh.write("\n".join(lines_out) + "\n")


if __name__ == "__main__":
    main()
