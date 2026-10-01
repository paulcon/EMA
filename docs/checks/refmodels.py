"""The reference models R1-R11, written from docs/design/reference_models.md alone, for the step 11 checks.

Independent of EMA's code (there is none yet) and of v1's. Each model takes a dict of model parameter
arrays in model parameter units and returns y (R5: y and z, with its failure regions as masks). Each SPACE
gives, in the model spec's order, (lo, hi, scale, nominal). Unit coordinates z are in [-1, 1] (designs.md,
0047): a linear range is x = lo + (hi - lo) * (z + 1) / 2, a log range is the same in ln x.

Run the checks with any Python >= 3.12 that has numpy and scipy, e.g. ../EMA-v1/.venv/bin/python.
"""

from __future__ import annotations

import math

import numpy as np

SPACES: dict[str, dict[str, tuple[float, float, str, float]]] = {
    "R1": {"a": (0, 2, "linear", 1), "b": (-1, 1, "linear", 0), "c": (10, 20, "linear", 15),
           "k": (1, 100, "log", 10)},
    "R2": {f"x{i}": (-math.pi, math.pi, "linear", 0.0) for i in (1, 2, 3)},
    "R3": {"rw": (0.05, 0.15, "linear", 0.1), "r": (100, 50000, "log", 2236.06797749979),
           "Tu": (63070, 115600, "linear", 89335), "Hu": (990, 1110, "linear", 1050),
           "Tl": (63.1, 116, "linear", 89.55), "Hl": (700, 820, "linear", 760),
           "L": (1120, 1680, "linear", 1400), "Kw": (9855, 12045, "linear", 10950)},
    "R4": {p: (-1, 1, "linear", 0) for p in "abc"},
    "R5": {p: (-1, 1, "linear", 0) for p in "ab"},
    "R7": {p: (-1, 1, "linear", 0) for p in "abce"},
    "R8": {p: (-1, 1, "linear", 0) for p in "abcefg"},
    "R10": {p: (-1, 1, "linear", 0) for p in "abce"},
    "R11": {p: (-1, 1, "linear", 0) for p in "ab"},
}
SPACES["R6"] = SPACES["R1"]


def to_physical(model: str, z: np.ndarray) -> dict[str, np.ndarray]:
    """Map unit coordinates z (rows of points, columns in the space's order) to model parameter values."""
    z = np.atleast_2d(np.asarray(z, dtype=float))
    out = {}
    for j, (name, (lo, hi, scale, _)) in enumerate(SPACES[model].items()):
        u = (z[:, j] + 1) / 2
        if scale == "log":
            x = np.clip(np.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * u), lo, hi)
        else:
            x = lo + (hi - lo) * u
        out[name] = x
    return out


def r1(p):
    return 5 + 3 * p["a"] - p["b"] + 0 * p["c"] + 2 * np.log10(p["k"])


def r2(p):
    x1, x2, x3 = p["x1"], p["x2"], p["x3"]
    return np.sin(x1) + 7 * np.sin(x2) ** 2 + 0.1 * x3**4 * np.sin(x1)


def r3(p):
    rw, r, Tu, Hu, Tl, Hl, L, Kw = (p[k] for k in ("rw", "r", "Tu", "Hu", "Tl", "Hl", "L", "Kw"))
    lnr = np.log(r / rw)
    return 2 * np.pi * Tu * (Hu - Hl) / (lnr * (1 + 2 * L * Tu / (lnr * rw**2 * Kw) + Tu / Tl))


def r4a(p):
    return np.full_like(np.asarray(p["a"], dtype=float), 2.5)


def r4b(p):
    return 2.5 + 1e-12 * np.sin(40 * (p["a"] + p["b"] + p["c"]))


def r5(p):
    """y, z (NaN where missing), and the masks of the error and timeout regions (failed runs)."""
    a, b = p["a"], p["b"]
    error = a + b > 1
    timeout = (a < -0.8) & (b < -0.8)
    y = a + b**2
    z = np.where(b > 0.8, np.nan, a - b)
    return y, z, error, timeout


def r6a(p, rng):
    return r1(p) + 0.05 * rng.standard_normal(np.shape(p["a"]))


def r6b(p, rng):
    return r1(p) * (1 + 1e-8 * rng.standard_normal(np.shape(p["a"])))


def r7(p):
    """Summed in the order listed in reference_models.md."""
    a, b, c, e = p["a"], p["b"], p["c"], p["e"]
    return np.maximum(0, a + e - 0.6) + (b > 0.2).astype(float) + 1 / (1 + 4 * c**2)


def r8(p):
    return r7(p) + 0 * p["f"] + 0 * p["g"]


def psi1(u):
    return math.sqrt(3) * u


def psi2(u):
    return math.sqrt(5) * (3 * u**2 - 1) / 2


def r10(p):
    a, b, c = p["a"], p["b"], p["c"]
    return 2 * psi1(a) + 0.5 * psi2(b) + 1.5 * psi1(a) * psi1(c)


def g11(u):
    return 1 / (1 + 4 * u**2)


def r11(p):
    return g11(p["a"]) * g11(p["b"])


MODELS = {"R1": r1, "R2": r2, "R3": r3, "R4a": r4a, "R4b": r4b, "R7": r7, "R8": r8, "R10": r10, "R11": r11}


def space_of(model: str) -> str:
    return {"R4a": "R4", "R4b": "R4", "R6a": "R6", "R6b": "R6"}.get(model, model)


def evaluate_unit(model: str, z: np.ndarray) -> np.ndarray:
    """y at points given in unit coordinates (the deterministic models only)."""
    return MODELS[model](to_physical(space_of(model), z))
