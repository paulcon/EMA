"""Helpers for ``ema.numerics``'s tests: the reference models' functions in unit coordinates, the exact Gram
spectrum, arrays placed at chosen memory offsets, and Gauss-Legendre quadrature.

The reference models are written from ``docs/design/reference_models.md`` (as ``docs/checks/refmodels.py``),
in unit coordinates on [-1, 1]^d, which is all the numerics see.
"""

from __future__ import annotations

import math
from fractions import Fraction
from functools import cache

import numpy as np


def psi1(u: np.ndarray) -> np.ndarray:
    return math.sqrt(3) * u


def psi2(u: np.ndarray) -> np.ndarray:
    return math.sqrt(5) * (3 * u**2 - 1) / 2


def r1_unit(z: np.ndarray) -> np.ndarray:
    """R1 in unit coordinates: 5 + 3a - b + 2 log10 k, with a in [0, 2], b in [-1, 1], k in [1, 100] (log)."""
    a = 1 + z[:, 0]
    b = z[:, 1]
    log10k = 1 + z[:, 3]
    return 5 + 3 * a - b + 2 * log10k


def r2_unit(z: np.ndarray) -> np.ndarray:
    """R2 (Ishigami) in unit coordinates: each x in [-pi, pi]."""
    x = -math.pi + 2 * math.pi * (z + 1) / 2
    return np.sin(x[:, 0]) + 7 * np.sin(x[:, 1]) ** 2 + 0.1 * x[:, 2] ** 4 * np.sin(x[:, 0])


def r7_unit(z: np.ndarray) -> np.ndarray:
    """R7: a kink, a jump, and a Runge-type term, summed in the order listed."""
    a, b, c, e = z[:, 0], z[:, 1], z[:, 2], z[:, 3]
    return np.maximum(0, a + e - 0.6) + (b > 0.2).astype(float) + 1 / (1 + 4 * c**2)


def r10_unit(z: np.ndarray) -> np.ndarray:
    """R10: 2 psi1(a) + 0.5 psi2(b) + 1.5 psi1(a) psi1(c); e has no effect."""
    a, b, c = z[:, 0], z[:, 1], z[:, 2]
    return 2 * psi1(a) + 0.5 * psi2(b) + 1.5 * psi1(a) * psi1(c)


def coordinate_line(f, d: int, i: int, n: int) -> np.ndarray:
    """y along model parameter i through the center, at s_j = -1 + 2j/(n - 1) (the middle point exactly 0)."""
    z = np.zeros((n, d))
    z[:, i] = -1 + 2 * np.arange(n) / (n - 1)
    if n % 2:
        z[(n - 1) // 2, i] = 0.0
    return f(z)


@cache
def _exact_gram(n: int, kmax: int) -> tuple[list[list[Fraction]], list[Fraction]]:
    """The monic Gram polynomials' values p_k(s_j), k = 0 ... kmax, and their norms (1/n) sum_j p_k(s_j)^2."""
    s = [Fraction(2 * j - (n - 1), n - 1) for j in range(n)]
    p = [[Fraction(1)] * n, list(s)]
    for k in range(1, kmax):
        beta = Fraction(k * k * (n * n - k * k), (n - 1) ** 2 * (4 * k * k - 1))
        p.append([s[j] * p[k][j] - beta * p[k - 1][j] for j in range(n)])
    p = p[: kmax + 1]
    return p, [sum(v * v for v in pk) / n for pk in p]


def exact_gram_coefficients(y: np.ndarray, kmax: int) -> np.ndarray:
    """c_0 ... c_kmax of y's doubles in exact rational arithmetic, rounded once (coordinate_lines.md, Tests it
    implies)."""
    n = len(y)
    p, norms = _exact_gram(n, kmax)
    yf = [Fraction(float(v)) for v in y]
    out = []
    for k in range(kmax + 1):
        ip = sum((a * b for a, b in zip(yf, p[k], strict=True)), Fraction(0)) / n
        out.append(float(ip) / math.sqrt(float(norms[k])))
    return np.array(out)


def at_offset(values: np.ndarray, offset: int, keep: list[bytearray]) -> np.ndarray:
    """A copy of ``values`` whose data starts ``offset`` bytes past a 64-byte boundary (the BLAS note)."""
    values = np.ascontiguousarray(values)
    buf = bytearray(values.nbytes + 128)
    keep.append(buf)
    raw = np.frombuffer(buf, dtype=np.uint8)
    start = (-raw.ctypes.data) % 64 + offset
    out = raw[start : start + values.nbytes].view(values.dtype).reshape(values.shape)
    out[...] = values
    assert (out.ctypes.data - offset) % 64 == 0
    return out


OFFSETS = tuple(range(0, 64, 8))


def gauss_legendre_grid(d: int, m: int) -> tuple[np.ndarray, np.ndarray]:
    """Tensor Gauss-Legendre nodes ``(m**d, d)`` on [-1, 1]^d and weights for the uniform measure (sum 1)."""
    x, w = np.polynomial.legendre.leggauss(m)
    nodes = np.array(np.meshgrid(*([x] * d), indexing="ij")).reshape(d, -1).T
    weights = np.prod(np.array(np.meshgrid(*([w / 2] * d), indexing="ij")).reshape(d, -1), axis=0)
    return nodes, weights
