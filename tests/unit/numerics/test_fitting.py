"""Least-squares fits, the rank rule, R², the relative residual, and PRESS (linear_model.md, polynomial_model.md;
uncertainty.md, Rules: Rank; 0051; PM2, PM3)."""

import math

import numpy as np
import pytest

from ema.numerics.basis import TotalDegree
from ema.numerics.fitting import Fit, least_squares, press, r2, rank, relative_residual
from tests.support.numerics import r1_unit, r10_unit


def unit_points(seed: int, n: int, d: int) -> np.ndarray:
    return 2 * np.random.default_rng(seed).random((n, d)) - 1


def design_matrix(Z: np.ndarray, p: int) -> np.ndarray:
    b = TotalDegree()
    return b.evaluate(Z, b.terms(Z.shape[1], p))


def test_r10_recovered_exactly() -> None:
    """PM2 (polynomial_model.md, Expected answers): R10 at p = 2, the three coefficients within 1e-12, the rest
    below 1e-12; relative residual, R², LOO: 0, 1, 0 within 1e-12."""
    Z = unit_points(0, 120, 4)
    y = r10_unit(Z)
    A = design_matrix(Z, 2)
    fit = least_squares(A, y)
    terms = TotalDegree().terms(4, 2).tolist()
    want = np.zeros(len(terms))
    want[terms.index([1, 0, 0, 0])] = 2.0
    want[terms.index([0, 2, 0, 0])] = 0.5
    want[terms.index([1, 0, 1, 0])] = 1.5
    assert np.abs(fit.coefficients - want).max() <= 1e-12
    assert fit.rank == len(terms)
    assert relative_residual(y, fit) <= 1e-12
    assert r2(y, fit) == pytest.approx(1.0, abs=1e-12)
    assert press(A, y, fit) <= 1e-12


def test_r1_linear_coefficients() -> None:
    """linear_model.md: R1's slopes in unit coordinates are 10; 3, -1, 0, 2 (k on its log scale)."""
    Z = unit_points(1, 40, 4)
    A = np.column_stack([np.ones(40), Z])
    fit = least_squares(A, r1_unit(Z))
    assert np.abs(fit.coefficients - [10, 3, -1, 0, 2]).max() <= 1e-12


def test_leverages_and_residuals() -> None:
    """The leverages are the hat matrix's diagonal; the residuals y - A beta."""
    Z = unit_points(2, 30, 3)
    A = design_matrix(Z, 2)
    y = np.sin(3 * Z[:, 0]) + Z[:, 1] * Z[:, 2]
    fit = least_squares(A, y)
    H = A @ np.linalg.solve(A.T @ A, A.T)
    assert np.abs(fit.leverages - np.diag(H)).max() <= 1e-12
    assert np.abs(fit.residuals - (y - A @ np.linalg.lstsq(A, y, rcond=None)[0])).max() <= 1e-12
    assert math.fsum(fit.leverages) == pytest.approx(A.shape[1], rel=1e-12)


def test_press_against_explicit_refits() -> None:
    """PM3: a fixture of 12 runs in d = 2, p = 2: the LOO error equal to explicit refits within 1e-12."""
    Z = unit_points(3, 12, 2)
    y = np.exp(Z[:, 0]) * np.cos(2 * Z[:, 1])
    A = design_matrix(Z, 2)
    fit = least_squares(A, y)
    loo = []
    for k in range(12):
        keep = np.arange(12) != k
        beta = np.linalg.lstsq(A[keep], y[keep], rcond=None)[0]
        loo.append(y[k] - A[k] @ beta)
    brute = math.sqrt(math.fsum(np.square(loo))) / math.sqrt(math.fsum((y - y.mean()) ** 2))
    assert press(A, y, fit) == pytest.approx(brute, abs=1e-12)


def test_relative_residual_and_r2() -> None:
    """linear_model.md: ||r|| / ||y - ybar||, and R² = 1 - that squared."""
    Z = unit_points(4, 50, 2)
    y = Z[:, 0] + Z[:, 1] ** 2
    A = np.column_stack([np.ones(50), Z])
    fit = least_squares(A, y)
    rel = math.sqrt(math.fsum(fit.residuals**2) / math.fsum((y - y.mean()) ** 2))
    assert relative_residual(y, fit) == pytest.approx(rel, rel=1e-14)
    assert r2(y, fit) == pytest.approx(1 - rel**2, rel=1e-14)


def test_scaling_by_a_power_of_two_is_exact() -> None:
    """LM/PM's changes of units (P6): y -> 2^40 y scales the coefficients, and leaves the relative residual, R²,
    and LOO unchanged, exactly."""
    Z = unit_points(5, 40, 3)
    y = np.sin(2 * Z[:, 0]) + Z[:, 2]
    A = design_matrix(Z, 2)
    f1, f2 = least_squares(A, y), least_squares(A, 2.0**40 * y)
    assert np.array_equal(f2.coefficients, 2.0**40 * f1.coefficients)
    assert relative_residual(y, f1) == relative_residual(2.0**40 * y, f2)
    assert r2(y, f1) == r2(2.0**40 * y, f2)
    assert press(A, y, f1) == press(A, 2.0**40 * y, f2)


def test_rank_is_numpys_matrix_rank_rule() -> None:
    """uncertainty.md, Rank (0051): singular values above max(n, P) eps sigma_max."""
    rng = np.random.default_rng(6)
    full = rng.standard_normal((20, 6))
    deficient = np.column_stack([full[:, :5], full[:, 0] + full[:, 1]])
    tiny = np.column_stack([full[:, :5], 1e-15 * full[:, 5] + full[:, 0]])
    for A in (full, deficient, tiny, full[:4]):
        assert rank(A) == np.linalg.matrix_rank(A)
    assert rank(deficient) == 5


def test_a_rank_deficient_fit_is_undefined() -> None:
    """uncertainty.md: a fit of rank below its terms is undefined: its numbers are NaN, and its rank is given."""
    Z = np.repeat(unit_points(7, 3, 2), 4, axis=0)  # 3 distinct points, 6 terms at p = 2
    A = design_matrix(Z, 2)
    y = Z[:, 0]
    fit = least_squares(A, y)
    assert fit.rank == 3
    assert np.isnan(fit.coefficients).all() and np.isnan(fit.residuals).all() and np.isnan(fit.leverages).all()
    assert math.isnan(relative_residual(y, fit)) and math.isnan(r2(y, fit)) and math.isnan(press(A, y, fit))


def test_fewer_runs_than_terms() -> None:
    A = design_matrix(unit_points(8, 4, 2), 2)
    fit = least_squares(A, np.arange(4.0))
    assert fit.rank == 4 and np.isnan(fit.coefficients).all()


def test_undefined_on_constant_y() -> None:
    """uncertainty.md, step 3: R², the relative residual, and LOO are 0/0 on a constant y: undefined."""
    Z = unit_points(9, 20, 2)
    A = np.column_stack([np.ones(20), Z])
    for value in (7.0, 0.1, 1e6 + 0.3):  # 0.1 and 1e6 + 0.3: the mean of 20 copies rounds away from the value
        y = np.full(20, value)
        fit = least_squares(A, y)
        assert np.allclose(fit.coefficients, [value, 0, 0], rtol=1e-14, atol=1e-9)
        assert math.isnan(relative_residual(y, fit)) and math.isnan(r2(y, fit)) and math.isnan(press(A, y, fit))


def test_press_needs_more_runs_than_terms() -> None:
    """uncertainty.md: LOO undefined with fewer than P + 1 runs (every leverage 1)."""
    Z = unit_points(10, 3, 2)
    A = np.column_stack([np.ones(3), Z])
    y = Z[:, 0] + 2 * Z[:, 1]
    assert math.isnan(press(A, y, least_squares(A, y)))


def test_fit_type() -> None:
    fit = least_squares(np.eye(3), np.arange(3.0))
    assert isinstance(fit, Fit) and fit.coefficients.tolist() == [0.0, 1.0, 2.0]
    assert not fit.coefficients.flags.writeable
    with pytest.raises(ValueError):
        least_squares(np.eye(3), np.arange(4.0))
