"""R6a (reference_models.md): R1 + 0.05·ε, ε standard normal from fresh entropy, like a real noisy model."""

import math

import numpy as np

_NOISE = np.random.default_rng()  # fresh entropy in each child: replicates never repeat a draw


def f(a, b, c, k):
    return 5.0 + 3.0 * a - b + 0.0 * c + 2.0 * math.log10(k) + 0.05 * float(_NOISE.standard_normal())
