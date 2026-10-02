"""R4b (reference_models.md): 2.5 + 1e-12 sin(40 (a + b + c)), not constant (0035)."""

import numpy as np


def f(a, b, c):
    return float(2.5 + 1e-12 * np.sin(40 * (a + b + c)))
