"""R6b (reference_models.md): R1·(1 + 10⁻⁸·ε), ε standard normal from fresh entropy: noise at a solver tolerance."""

import math

import numpy as np

_NOISE = np.random.default_rng()  # fresh entropy in each child: replicates never repeat a draw


def f(a, b, c, k):
    r1 = 5.0 + 3.0 * a - b + 0.0 * c + 2.0 * math.log10(k)
    return r1 * (1.0 + 1e-8 * float(_NOISE.standard_normal()))
