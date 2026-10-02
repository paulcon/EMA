"""R11 (reference_models.md): g(a)·g(b), g(u) = 1/(1 + 4u²): poles at ±i/2, a known geometric decay."""


def g(u):
    return 1 / (1 + 4 * u**2)


def f(a, b):
    return g(a) * g(b)
