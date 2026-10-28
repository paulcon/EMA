"""R2 (reference_models.md): the Ishigami function (Ishigami and Homma, 1990).

Ported from EMA v1 at v1-final: src/ema/testfunctions/library.py (ishigami), reviewed against the reference models'
spec (reference_models.md).
"""

import numpy as np

A, B = 7.0, 0.1


def f(x1, x2, x3):
    return float(np.sin(x1) + A * np.sin(x2) ** 2 + B * x3**4 * np.sin(x1))
