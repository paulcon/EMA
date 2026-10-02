"""R7 (reference_models.md): max(0, a + e - 0.6) + 1[b > 0.2] + 1/(1 + 4c²), summed in the order listed."""


def f(a, b, c, e):
    return max(0.0, a + e - 0.6) + (1.0 if b > 0.2 else 0.0) + 1.0 / (1.0 + 4.0 * (c * c))
