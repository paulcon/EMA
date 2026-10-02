"""The Gram spectrum and its decay rate (coordinate_lines.md, Computation; lines.md; CL2, CL3, CL8)."""

import math

import numpy as np
import pytest

from ema.numerics import gram
from ema.numerics.gram import decay_rate, degrees_above_floor, gram_coefficients, tail
from ema.numerics.tolerance import tolerance
from tests.support.numerics import coordinate_line, exact_gram_coefficients, r1_unit, r7_unit, r10_unit

#: coordinate_lines.md's constants, which the diagnostic owns; repeated here to compute its rate.
FLOOR, MIN_DEGREES = 1e-10, 3


def line_rate(y: np.ndarray) -> tuple[int, tuple[float, float] | None]:
    """k* and the rate as coordinate lines computes them: the window K, the floor 1e-10 of the range."""
    K = (len(y) - 1) // 2
    T = tail(gram_coefficients(y))[: K + 1]
    k_star = degrees_above_floor(T, tolerance(y, FLOOR))
    return k_star, decay_rate(T, k_star, MIN_DEGREES)


def basis_matrix(n: int) -> np.ndarray:
    """G with G[j, k] = G_k(s_j), from the coefficients of the unit vectors: c(e_j) = G[j, :] / n."""
    return n * np.array([gram_coefficients(e) for e in np.eye(n)])


@pytest.mark.parametrize("n", [7, 17, 33, 65, 129])
def test_orthonormal(n: int) -> None:
    """CL2: (1/n) G^T G = I within 1e-13; G_0 = 1; leading coefficients positive (G_1 increasing)."""
    G = basis_matrix(n)
    assert np.abs(G.T @ G / n - np.eye(n)).max() <= 1e-13
    assert np.allclose(G[:, 0], 1.0, rtol=0, atol=1e-14)
    assert (np.diff(G[:, 1]) > 0).all()


@pytest.mark.parametrize("n", [17, 65, 129])
@pytest.mark.parametrize("i", [0, 1, 2, 3])
def test_against_exact_rational_arithmetic(n: int, i: int) -> None:
    """CL2: R7's lines, c_0 ... c_K within 1e-14 of the line's range of the exact coefficients; c_0 the mean;
    the sum of c_k^2 (k >= 1) the variance, ddof 0."""
    y = coordinate_line(r7_unit, 4, i, n)
    c = gram_coefficients(y)
    rng = float(np.max(y) - np.min(y))
    K = (n - 1) // 2
    exact = exact_gram_coefficients(y, K)
    assert np.abs(c[1 : K + 1] - exact[1:]).max() <= 1e-14 * rng
    assert c[0] == pytest.approx(np.mean(y), rel=1e-15, abs=1e-15)
    assert math.fsum(c[1:] ** 2) == pytest.approx(np.var(y), rel=1e-13)


def test_y_recovered() -> None:
    """CL2: y_j = sum_k c_k G_k(s_j)."""
    y = coordinate_line(r7_unit, 4, 0, 33)
    assert np.abs(basis_matrix(33) @ gram_coefficients(y) - y).max() <= 1e-14


def test_tail() -> None:
    """T(k) = sqrt(sum_(j >= k) c_j^2), indexed by degree; T(1) is the standard deviation (ddof 0)."""
    c = np.array([5.0, 3.0, 0.0, 4.0])
    assert tail(c).tolist() == [math.sqrt(50.0), 5.0, 4.0, 4.0]
    y = coordinate_line(r7_unit, 4, 2, 17)
    assert tail(gram_coefficients(y))[1] == pytest.approx(np.std(y), rel=1e-14)


def test_rate_one_on_a_constructed_spectrum() -> None:
    """CL3: y = sum_k 10^-k G_k at n = 33 has rate 1 within 1e-6 (0048)."""
    n = 33
    y = basis_matrix(n) @ (10.0 ** -np.arange(n))
    k_star, fitted = line_rate(y)
    assert fitted is not None
    assert k_star >= 3 and fitted[0] == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize(
    ("n", "expected"),
    [(17, (0.1811111, 0.06916461, 0.1957442, 0.1811111)), (33, (0.1103366, 0.03749946, 0.2088262, 0.1103366))],
)
def test_r7_expected_rates(n: int, expected: tuple[float, ...]) -> None:
    """coordinate_lines.md, Expected answers: R7 along a, b, c, e at n = 17 and 33, within 1e-6."""
    for i, want in enumerate(expected):
        _, fitted = line_rate(coordinate_line(r7_unit, 4, i, n))
        assert fitted is not None and fitted[0] == pytest.approx(want, abs=1e-6)


def test_polynomial_lines_have_no_rate() -> None:
    """CL3: R1 (linear) k* = 1, none; R10 along b (quadratic) k* = 2, none; along a, k* = 1."""
    for i in (0, 1, 3):
        assert line_rate(coordinate_line(r1_unit, 4, i, 17)) == (1, None)
    assert line_rate(coordinate_line(r10_unit, 4, 1, 17)) == (2, None)
    assert line_rate(coordinate_line(r10_unit, 4, 0, 17)) == (1, None)


def test_degrees_above_floor_counts_from_one() -> None:
    T = np.array([9.0, 1.0, 0.5, 1e-11, 1e-12])
    assert degrees_above_floor(T, 1e-10) == 2
    assert degrees_above_floor(T, 2.0) == 0
    assert degrees_above_floor(T[:3], 1e-10) == 2


def test_decay_rate_fit() -> None:
    """Minus the least-squares slope of log10 T(k) over k = 1 ... k*, and its intercept; none below the minimum."""
    T = np.array([1.0, 10.0**-1.0, 10.0**-3.0, 10.0**-5.0, 1.0])
    rate, intercept = decay_rate(T, 3, 3)  # type: ignore[misc]
    assert rate == pytest.approx(2.0, abs=1e-14) and intercept == pytest.approx(1.0, abs=1e-14)
    assert decay_rate(T, 2, 3) is None


def test_scaling_by_a_power_of_two() -> None:
    """CL8: y -> 2^-10 y leaves k* and the rate within 1e-12."""
    y = coordinate_line(r7_unit, 4, 2, 33)
    k1, r1 = line_rate(y)
    k2, r2 = line_rate(2.0**-10 * y)
    assert k1 == k2 and r1 is not None and r2 is not None and abs(r1[0] - r2[0]) <= 1e-12


def test_a_constant_line() -> None:
    """CL6: every value the same double: c = (y_0, 0, ..., 0) exactly, so 0 degrees above the floor (0) and no rate;
    without it, Lanczos's rounding (about 1e-17) would sit above a floor of 0 and give a rate."""
    y = np.full(17, 0.1)
    c = gram_coefficients(y)
    assert c[0] == 0.1 and not c[1:].any()
    assert line_rate(y) == (0, None)
    assert np.abs(gram._basis(17).T @ y / 17)[1:].max() > 0  # what the shortcut avoids


def test_refuses_fewer_than_two_points() -> None:
    with pytest.raises(ValueError):
        gram_coefficients(np.array([1.0]))
