"""Sobol indices and root energy per degree of a fitted polynomial (polynomial_model.md; PM4)."""

import math

import numpy as np
import pytest

from ema.numerics.basis import TotalDegree
from ema.numerics.fitting import least_squares
from ema.numerics.sobol import degree_energy, sobol_indices
from tests.support.numerics import r1_unit, r10_unit


def fitted(f, d: int, p: int, n: int = 200, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    Z = 2 * np.random.default_rng(seed).random((n, d)) - 1
    b = TotalDegree()
    terms = b.terms(d, p)
    return least_squares(b.evaluate(Z, terms), f(Z)).coefficients, terms


def test_r10_at_p2() -> None:
    """polynomial_model.md, Expected answers: R10 first-order 4/6.5, 0.25/6.5, 0, 0; total 6.25/6.5, 0.25/6.5,
    2.25/6.5, 0; sqrt(E_1) = 2, sqrt(E_2) = sqrt(2.5); within 1e-12."""
    coef, terms = fitted(r10_unit, 4, 2)
    first, total = sobol_indices(coef, terms)
    assert np.abs(first - np.array([4, 0.25, 0, 0]) / 6.5).max() <= 1e-12
    assert np.abs(total - np.array([6.25, 0.25, 2.25, 0]) / 6.5).max() <= 1e-12
    assert np.abs(degree_energy(coef, terms) - [2, math.sqrt(2.5)]).max() <= 1e-12


def test_r1_at_p2() -> None:
    """R1: first-order = total = 9/14, 1/14, 0, 4/14; sqrt(E_1) = sqrt(14/3), sqrt(E_2) = 0."""
    coef, terms = fitted(r1_unit, 4, 2)
    first, total = sobol_indices(coef, terms)
    want = np.array([9, 1, 0, 4]) / 14
    assert np.abs(first - want).max() <= 1e-12 and np.abs(total - want).max() <= 1e-12
    energy = degree_energy(coef, terms)
    assert energy[0] == pytest.approx(math.sqrt(14 / 3), abs=1e-12) and energy[1] <= 1e-12


def test_coefficients_set_by_hand() -> None:
    """PM4: a fixture whose coefficients are set by hand."""
    terms = TotalDegree().terms(3, 2)  # 00 0, 100, 010, 001, 200, 110, 101, 020, 011, 002
    coef = np.array([9.0, 1, 0, 2, 0, 3, 0, 0, 0, 1])
    first, total = sobol_indices(coef, terms)
    V = 1 + 4 + 9 + 1
    assert first.tolist() == pytest.approx([1 / V, 0, (4 + 1) / V])
    assert total.tolist() == pytest.approx([(1 + 9) / V, 9 / V, (4 + 1) / V])
    assert degree_energy(coef, terms).tolist() == pytest.approx([math.sqrt(5), math.sqrt(10)])


def test_constant_fit_has_no_indices() -> None:
    """0049: V = 0, so the Sobol indices are undefined (NaN); the energy is 0."""
    terms = TotalDegree().terms(2, 2)
    coef = np.zeros(len(terms))
    coef[0] = 3.0
    first, total = sobol_indices(coef, terms)
    assert np.isnan(first).all() and np.isnan(total).all()
    assert degree_energy(coef, terms).tolist() == [0.0, 0.0]


def test_scaling_leaves_indices() -> None:
    """P6: y -> 2^-40 y scales sqrt(E_k) by 2^-40, and leaves the indices unchanged, exactly."""
    coef, terms = fitted(lambda Z: np.sin(2 * Z[:, 0]) * Z[:, 1], 2, 3)
    f1, t1 = sobol_indices(coef, terms)
    f2, t2 = sobol_indices(2.0**-40 * coef, terms)
    assert np.array_equal(f1, f2) and np.array_equal(t1, t2)
    assert np.array_equal(degree_energy(2.0**-40 * coef, terms), 2.0**-40 * degree_energy(coef, terms))
