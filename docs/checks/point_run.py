"""Step 11's independent check of docs/design/diagnostics/point_run.md, "Expected answers".

What it checks, row by row:

- R1, nominal, repeats 4: replicate 0, mean, standard deviation (ddof 1), distinct values, varies: computed
  from refmodels.r1 at the nominal point, 5 times (a deterministic model gives the same double each time).
- R4a, repeats 4: one distinct value.
- R6a and R6b, nominal, repeats 100 (replicates 0-100: 101 runs, so 100 degrees of freedom): the bounds
  [sqrt(chi2_100(p/2)/100), sqrt(chi2_100(1 - p/2)/100)] on s/sigma, with two-sided probability p = 1e-6,
  from scipy's chi2.ppf; then 20,000 simulated point runs of each (fresh entropy, as the models draw), and the
  fraction outside the bounds (expected about 1e-6, so 0 here). sigma: 0.05 for R6a, 1e-8 x R1(nominal) = 1e-7
  for R6b.
- R6a and R6b, repeats 4, varies: the fraction of 20,000 simulated point runs with two equal doubles (0).
- R5 at {a: 0.9, b: 0.9}: a + b > 1, so all 5 runs fail with an error; R5 at the nominal point: z is defined
  (b <= 0.8) and no region fails, so 5 runs are usable for z.

The notes ("no constant note", "none") are properties of EMA's report, not computed here.

Run from docs/checks: ../../../EMA-v1/.venv/bin/python point_run.py
"""

from __future__ import annotations

import math
import sys
import time

import numpy as np
from scipy.stats import chi2

import refmodels as R

P_TWO_SIDED = 1e-6
DF = 100
SIMS = 20_000

lines_out: list[str] = []


def out(s: str = "") -> None:
    print(s)
    lines_out.append(s)


def nominal(space: str) -> dict[str, np.ndarray]:
    return {k: np.full(5, v[3], dtype=float) for k, v in R.SPACES[space].items()}


def main() -> None:
    t0 = time.time()
    out("# point_run.py: step 11 check of diagnostics/point_run.md, Expected answers")
    out(f"numpy {np.__version__}, Python {sys.version.split()[0]}")
    out("")
    out("| Row | Quantity | Spec | Recomputed | Agrees? |")
    out("|---|---|---|---|---|")

    def row(label: str, qty: str, spec, got, ok: bool) -> None:
        out(f"| {label} | {qty} | {spec} | {got} | {'yes' if ok else 'NO'} |")

    y = R.r1(nominal("R1"))
    row("R1, nominal, repeats 4", "replicate 0; mean; sd; distinct", "10; 10; 0; 1",
        f"{float(y[0])!r}; {float(y.mean())!r}; {float(y.std(ddof=1))!r}; {len(np.unique(y))}",
        y[0] == 10 and y.mean() == 10 and y.std(ddof=1) == 0 and len(np.unique(y)) == 1)
    row("R1, nominal, repeats 4", "varies", "no", "yes" if len(np.unique(y)) > 1 else "no", len(np.unique(y)) == 1)
    out(f"(log10(10) == 1.0 in doubles: {math.log10(10.0) == 1.0}; np.log10: {np.log10(10.0) == 1.0})")

    y = R.r4a(nominal("R4"))
    row("R4a, repeats 4", "distinct values", "1", str(len(np.unique(y))), len(np.unique(y)) == 1)

    lo = math.sqrt(chi2.ppf(P_TWO_SIDED / 2, DF) / DF)
    hi = math.sqrt(chi2.ppf(1 - P_TWO_SIDED / 2, DF) / DF)
    row(f"R6a, R6b, repeats 100 ({DF + 1} runs)", "bounds on s/sigma, two-sided 1e-6, 100 df",
        "[0.6735, 1.360]", f"[{lo:.4f}, {hi:.4f}]", f"{lo:.4f}" == "0.6735" and f"{hi:.4g}" == "1.36")
    lo99 = math.sqrt(chi2.ppf(P_TWO_SIDED / 2, DF - 1) / (DF - 1))
    hi99 = math.sqrt(chi2.ppf(1 - P_TWO_SIDED / 2, DF - 1) / (DF - 1))
    out(f"(for comparison, 99 df, if repeats 100 meant 100 runs: [{lo99:.4f}, {hi99:.4f}])")

    rng = np.random.default_rng()  # fresh entropy, as the models draw
    p = {k: np.full((SIMS, DF + 1), v[3], dtype=float) for k, v in R.SPACES["R6"].items()}
    for name, model, sigma in (("R6a", R.r6a, 0.05), ("R6b", R.r6b, 1e-7)):
        ys = model(p, rng)
        ratio = ys.std(axis=1, ddof=1) / sigma
        outside = float(np.mean((ratio < lo) | (ratio > hi)))
        row(f"{name}, nominal, repeats 100", f"sd / {sigma:g} within the bounds, {SIMS} simulated point runs",
            "inside (fails with probability 1e-6)", f"outside in {outside:.2g}; s/sigma from {ratio.min():.3f} "
            f"to {ratio.max():.3f}", outside == 0)
        y5 = ys[:, :5]
        ties = float(np.mean([len(np.unique(r)) < 5 for r in y5]))
        row(f"{name}, nominal, repeats 4", f"varies (all 5 distinct), {SIMS} simulated", "yes",
            f"two equal doubles in {ties:.2g}", ties == 0 and (y5.std(axis=1) > 0).all())

    pa = {"a": np.full(5, 0.9), "b": np.full(5, 0.9)}
    _, _, error, timeout = R.r5(pa)
    row("R5, {a: 0.9, b: 0.9}, repeats 4", "runs", "5 failed (error)",
        f"{int(error.sum())} error, {int(timeout.sum())} timeout", bool(error.all() and not timeout.any()))
    _, z, error, timeout = R.r5(nominal("R5"))
    usable = int((~error & ~timeout & ~np.isnan(z)).sum())
    row("R5, nominal, prediction z, repeats 4", "runs usable for z", "5", str(usable), usable == 5)

    out("")
    out(f"Simulations: {SIMS} point runs of each, fresh entropy. Runtime: {time.time() - t0:.1f} s")
    with open("point_run.out", "w") as fh:
        fh.write("\n".join(lines_out) + "\n")


if __name__ == "__main__":
    main()
