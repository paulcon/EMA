"""R1 (reference_models.md): f = 5 + 3a - b + 0c + 2 log10 k; exactly 10 + 3u_a - u_b + 2u_k in unit coordinates."""

import math


def f(a, b, c, k):
    return 5.0 + 3.0 * a - b + 0.0 * c + 2.0 * math.log10(k)
