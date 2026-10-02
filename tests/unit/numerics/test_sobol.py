"""Sobol indices and root energy per degree of a fitted polynomial (polynomial_model.md; PM4)."""

import math

import numpy as np
import pytest

from ema.numerics.basis import TotalDegree
from ema.numerics.fitting import least_squares
from ema.numerics.sobol import degree_energy, sobol_indices
from tests.support.numerics import r1_unit, r10_unit


def fitted(f, d: int, p: int, n: int = 200, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    Z = 2 * np.random.default_rng(seed).random((n, d)) - 1
    b = TotalDegree()
    terms = b.terms(d, p)
    y = f(Z)
    return least_squares(b.evaluate(Z, terms), y).coefficients, terms, y


def test_r10_at_p2() -> None:
    """polynomial_model.md, Expected answers: R10 first-order 4/6.5, 0.25/6.5, 0, 0; total 6.25/6.5, 0.25/6.5,
    2.25/6.5, 0; sqrt(E_1) = 2, sqrt(E_2) = sqrt(2.5); within 1e-12."""
    coef, terms, y = fitted(r10_unit, 4, 2)
    first, total = sobol_indices(coef, terms, y=y)
    assert np.abs(first - np.array([4, 0.25, 0, 0]) / 6.5).max() <= 1e-12
    assert np.abs(total - np.array([6.25, 0.25, 2.25, 0]) / 6.5).max() <= 1e-12
    assert np.abs(degree_energy(coef, terms) - [2, math.sqrt(2.5)]).max() <= 1e-12


def test_r1_at_p2() -> None:
    """R1: first-order = total = 9/14, 1/14, 0, 4/14; sqrt(E_1) = sqrt(14/3), sqrt(E_2) = 0."""
    coef, terms, y = fitted(r1_unit, 4, 2)
    first, total = sobol_indices(coef, terms, y=y)
    want = np.array([9, 1, 0, 4]) / 14
    assert np.abs(first - want).max() <= 1e-12 and np.abs(total - want).max() <= 1e-12
    energy = degree_energy(coef, terms)
    assert energy[0] == pytest.approx(math.sqrt(14 / 3), abs=1e-12) and energy[1] <= 1e-12


def test_coefficients_set_by_hand() -> None:
    """PM4: a fixture whose coefficients are set by hand."""
    terms = TotalDegree().terms(3, 2)  # 00 0, 100, 010, 001, 200, 110, 101, 020, 011, 002
    coef = np.array([9.0, 1, 0, 2, 0, 3, 0, 0, 0, 1])
    first, total = sobol_indices(coef, terms, y=np.arange(3.0))
    V = 1 + 4 + 9 + 1
    assert first.tolist() == pytest.approx([1 / V, 0, (4 + 1) / V])
    assert total.tolist() == pytest.approx([(1 + 9) / V, 9 / V, (4 + 1) / V])
    assert degree_energy(coef, terms).tolist() == pytest.approx([math.sqrt(5), math.sqrt(10)])


def test_constant_fit_has_no_indices() -> None:
    """0049: V = 0 though y varies (a contrived design), so the Sobol indices are undefined (NaN); the energy
    is 0."""
    terms = TotalDegree().terms(2, 2)
    coef = np.zeros(len(terms))
    coef[0] = 3.0
    first, total = sobol_indices(coef, terms, y=np.arange(3.0))
    assert np.isnan(first).all() and np.isnan(total).all()
    assert degree_energy(coef, terms).tolist() == [0.0, 0.0]


def test_scaling_leaves_indices() -> None:
    """P6: y -> 2^-40 y scales sqrt(E_k) by 2^-40, and leaves the indices unchanged, exactly."""
    coef, terms, y = fitted(lambda Z: np.sin(2 * Z[:, 0]) * Z[:, 1], 2, 3)
    f1, t1 = sobol_indices(coef, terms, y=y)
    f2, t2 = sobol_indices(2.0**-40 * coef, terms, y=2.0**-40 * y)
    assert np.array_equal(f1, f2) and np.array_equal(t1, t2)
    assert np.array_equal(degree_energy(2.0**-40 * coef, terms), 2.0**-40 * degree_energy(coef, terms))


def test_constant_y_has_no_indices() -> None:
    """polynomial_model.md, Uncertainty; 0035: a constant y makes the Sobol indices undefined (0/0), though the
    fit's coefficients are rounding, not zeros (V about 3e-34 on 40 runs of 0.1: without the check, indices of
    rounding near 0.17, 0.21, 0.30)."""
    for value in (0.1, 7.0, 1e6 + 0.3):
        coef, terms, y = fitted(lambda Z, value=value: np.full(len(Z), value), 3, 2, n=40)
        first, total = sobol_indices(coef, terms, y=y)
        assert np.isnan(first).all() and np.isnan(total).all()
    coef, terms, y = fitted(lambda Z: np.full(len(Z), 0.1), 3, 2, n=40)
    assert float(np.sum(coef[1:] ** 2)) > 0  # what V alone would miss


def test_r4b_wiggle_has_indices() -> None:
    """0035: R4b, 2.5 + 1e-12 sin(40 (a + b + c)), is not constant: finite indices, each in [0, 1]."""
    coef, terms, y = fitted(lambda Z: 2.5 + 1e-12 * np.sin(40 * Z.sum(axis=1)), 3, 2, n=60)
    first, total = sobol_indices(coef, terms, y=y)
    assert np.isfinite(first).all() and np.isfinite(total).all()
    assert (first >= 0).all() and (total <= 1).all() and (first <= total).all()
