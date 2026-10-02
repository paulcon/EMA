"""P6's one tolerance function (principles.md, P6; diagnostics/shared.md, The precheck)."""

import numpy as np
import pytest

from ema.numerics.tolerance import tolerance


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
