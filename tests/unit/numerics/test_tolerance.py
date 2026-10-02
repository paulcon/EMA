"""P6's one tolerance function and its test of "constant" (principles.md, P6; diagnostics/shared.md, The
precheck; 0035)."""

import numpy as np
import pytest

from ema.numerics.tolerance import is_constant, tolerance


def test_relative_to_the_range() -> None:
    assert tolerance(np.array([3.0, -1.0, 7.0]), 1e-10) == pytest.approx(8e-10, rel=1e-15)
    assert tolerance(np.array([5.0]), 0.5) == 0.0


def test_units_change_no_note() -> None:
    """P6: y -> a y + b scales the tolerance by a."""
    y = np.array([0.1, 0.7, 0.3])
    assert tolerance(2.0**-20 * y + 3.0, 1e-3) == pytest.approx(2.0**-20 * tolerance(y, 1e-3), rel=1e-9)


def test_refusals() -> None:
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            tolerance(np.array([1.0, 2.0]), bad)
    with pytest.raises(ValueError):
        tolerance(np.array([]), 1e-10)
    with pytest.raises(ValueError):
        tolerance(np.array([1.0, np.nan]), 1e-10)


def test_constant_is_exact_equality() -> None:
    """0035: constant only when every value is the same double; no flatness tolerance. R4b's wiggle varies."""
    assert is_constant(np.full(20, 0.1)) and is_constant(np.array([2.5])) and is_constant(np.array([0.0, -0.0]))
    z = 2 * np.random.default_rng(0).random((40, 3)) - 1
    r4b = 2.5 + 1e-12 * np.sin(40 * z.sum(axis=1))
    assert not is_constant(r4b)
    assert not is_constant(np.array([1.0, np.nextafter(1.0, 2.0)]))
    assert not is_constant(np.array([]))  # too few runs decides that case
    assert not is_constant(np.array([np.nan, np.nan]))
