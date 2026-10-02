"""The point design (designs.md, Point; G9, G4 in repeats, G18; 0011, 0049)."""

import numpy as np
import pytest

from ema.designs import generators
from ema.types.errors import RequestError
from ema.types.space import ModelParameterSpace
from tests.support.designs import HEAT, identity

POINT = generators.get("point")


def test_g9_the_point_complete_with_replicates():
    design = POINT.build(identity(HEAT, "point", x={"k": 50}, repeats=3), HEAT)
    assert design.points.tolist() == [[50.0, 3e4]] * 4
    assert design.replicates.tolist() == [0, 1, 2, 3]
    assert design.levels is None and design.lines is None


def test_g9_a_value_outside_its_limits_is_refused():
    ident = identity(HEAT, "point", ModelParameterSpace.at_point(HEAT, {}).canonical(), x={"k": -1})
    with pytest.raises(RequestError, match=r"model parameter k.*gt 0"):
        POINT.build(ident, HEAT)


def test_no_x_is_the_nominal_point_and_repeats_default_to_0():
    design = POINT.build(identity(HEAT, "point"), HEAT)
    assert design.points.tolist() == [[45.0, 3e4]] and design.replicates.tolist() == [0]


def test_integers_and_doubles_give_the_same_point():
    one = POINT.build(identity(HEAT, "point", x={"k": 50}, repeats=1), HEAT)
    two = POINT.build(identity(HEAT, "point", x={"k": 50.0}, repeats=1), HEAT)
    assert np.array_equal(one.points, two.points) and one.points.dtype == np.float64


def test_an_unknown_name_is_refused():
    ident = identity(HEAT, "point", ModelParameterSpace.at_point(HEAT, {}).canonical(), x={"nope": 1.0})
    with pytest.raises(RequestError, match="nope"):
        POINT.build(ident, HEAT)


def test_the_space_must_be_the_points():
    """0049: the point design's space holds every model parameter at the point."""
    ident = identity(HEAT, "point", {"k": 50.0, "q": 3e4}, x={"k": 45.0})
    with pytest.raises(RequestError, match="space"):
        POINT.build(ident, HEAT)
    with pytest.raises(RequestError, match="space"):
        POINT.build(identity(HEAT, "point", {"k": [40, 50]}), HEAT)


def test_g4_nested_in_repeats():
    small = POINT.build(identity(HEAT, "point", x={"k": 50}, repeats=1), HEAT)
    large = POINT.build(identity(HEAT, "point", x={"k": 50}, repeats=4), HEAT)
    assert np.array_equal(large.points[:2], small.points) and np.array_equal(large.replicates[:2], small.replicates)
