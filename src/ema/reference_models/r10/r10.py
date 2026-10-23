"""R10 (reference_models.md): 2ψ₁(a) + 0.5ψ₂(b) + 1.5ψ₁(a)ψ₁(c), with the orthonormal Legendre polynomials."""

import math


def psi1(u):
    return math.sqrt(3) * u


def psi2(u):
    return math.sqrt(5) * (3 * u**2 - 1) / 2


def f(a, b, c, e):
    return 2 * psi1(a) + 0.5 * psi2(b) + 1.5 * psi1(a) * psi1(c)
