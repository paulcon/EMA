"""v1 as a second source for reference_models.md's truths (step 11).

Run in v1's own environment, from docs/checks/:
    PYTHONPATH=../../../EMA-v1/src ../../../EMA-v1/.venv/bin/python truths_v1.py > truths_v1.out

What it checks, without changing v1:
- v1's functions of the same name (library.py at v1-final) against refmodels.py, at 10,000 random points:
  ishigami = R2, borehole = R3 (in model parameter units), linear = R1 without k, legendre_sparse = R10
  without the a*c term.
- v1's ranges and units for borehole against R3's table.
- v1's Sobol estimator (truth.sobol_indices: Saltelli 2010 first-order, Jansen total; N = 2**19, seed 0)
  run on our R1, R2, R10, and R11 in unit coordinates, against reference_models.md's analytic values.
- v1's stored truth.json for ishigami, linear, legendre_sparse, and borehole, with what differs from ours.
"""

from __future__ import annotations

import json
import math
import types
from pathlib import Path

import numpy as np
from ema.testfunctions import get, library, truth

import refmodels as R

rng = np.random.default_rng(11)


def maxdiff(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


print("## v1's functions against refmodels.py (10,000 points, seed 11)\n")
z = rng.uniform(-1, 1, (10_000, 8))
p3 = R.to_physical("R3", z)
print(f"- borehole vs R3: max |diff| = {maxdiff(library.borehole(**p3), R.r3(p3)):.1e}")
p2 = R.to_physical("R2", z[:, :3])
print(f"- ishigami vs R2: max |diff| = {maxdiff(library.ishigami(**p2), R.r2(p2)):.1e}")
p1 = R.to_physical("R1", z[:, :4])
print(f"- linear(a, b, c) vs R1 - 2 log10(k): max |diff| = "
      f"{maxdiff(library.linear(p1['a'], p1['b'], p1['c']), R.r1(p1) - 2 * np.log10(p1['k'])):.1e}")
p10 = R.to_physical("R10", z[:, :4])
print(f"- legendre_sparse vs R10 - 1.5 psi1(a) psi1(c): max |diff| = "
      f"{maxdiff(library.legendre_sparse(**p10), R.r10(p10) - 1.5 * R.psi1(p10['a']) * R.psi1(p10['c'])):.1e}")

bh = get("borehole")
print("\n## v1's borehole ranges and units against R3's table\n")
for name, (lo, hi, scale, nominal) in R.SPACES["R3"].items():
    vlo, vhi = bh.ranges[name]
    print(f"- {name}: v1 [{vlo}, {vhi}] {bh.units.get(name, '') if hasattr(bh, 'units') else ''}; "
          f"ours [{lo}, {hi}] {scale}; v1's nominal {bh.nominal[name]}, ours {nominal}"
          + ("" if (vlo, vhi) == (lo, hi) else "  DIFFERS"))

print("\n## v1's Sobol estimator (N = 2**19, seed 0) on our models, in unit coordinates\n")
analytic = {
    "R1": ({"a": 9 / 14, "b": 1 / 14, "c": 0, "k": 4 / 14},) * 2,
    "R2": ({"x1": 0.3139, "x2": 0.4424, "x3": 0.0}, {"x1": 0.5576, "x2": 0.4424, "x3": 0.2437}),
    "R10": ({"a": 0.6154, "b": 0.0385, "c": 0, "e": 0}, {"a": 0.9615, "b": 0.0385, "c": 0.3462, "e": 0}),
    "R11": ({"a": 0.4485, "b": 0.4485}, {"a": 0.5515, "b": 0.5515}),
}
for model, (first_a, total_a) in analytic.items():
    names = list(R.SPACES[model])
    tf = types.SimpleNamespace(func=None, ranges={n: (-1.0, 1.0) for n in names}, input_names=names,
                               evaluate=lambda X, m=model: R.evaluate_unit(m, X))
    first, total = truth.sobol_indices(tf, n=2**19, seed=0)
    worst = max(max(abs(first[n] - first_a[n]) for n in names), max(abs(total[n] - total_a[n]) for n in names))
    print(f"- {model}: first " + ", ".join(f"{n} {first[n]:.4f}" for n in names)
          + "; total " + ", ".join(f"{n} {total[n]:.4f}" for n in names)
          + f"; worst |v1 - analytic| = {worst:.4f}")

print("\n## v1's stored truth.json (v1-final)\n")
stored = json.loads((Path(truth.__file__).parent / "truth.json").read_text())
for name in ("ishigami", "linear", "legendre_sparse", "borehole"):
    s = stored[name]
    print(f"- {name}: first {s['first']}; total {s['total']}; linear R^2 {s['linear_r2']}")
print(f"\nanalytic for v1's linear (no k): first = total = a 9/10, b 1/10; legendre_sparse: a {4 / 4.25:.4f}, "
      f"b {0.25 / 4.25:.4f}; ishigami linear R^2 {(1 + 0.02 * math.pi**4) ** 2 / (math.pi**2 / 3) / 13.844588:.4f}")
