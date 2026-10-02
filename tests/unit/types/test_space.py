"""The model parameter space: its JSON form, validation, the unit maps and the map back, and line clipping
(designs.md, The model parameter space; G10, G15, G16; M6; 0047, 0061, 0065)."""

import math
from types import MappingProxyType

import numpy as np
import pytest

from ema.types.errors import RequestError
from ema.types.model import Limits
from ema.types.space import ModelParameterSpace, Range, Scale
from tests.support.designs import CONTRACT, CONTRACT_SPACE, HEAT, make_spec

NAN, INF = math.nan, math.inf


class TestParse:
    def test_forms(self):
        space = ModelParameterSpace.parse(
            {
                "k": [30, 60],
                "E": {"range": [1e9, 1e12], "scale": "log"},
                "h": 0.01,
                "t": (1, 2),
                "u": {"range": (1, 2)},
                "v": Range(0, 1),
                "w": {"range": [1, 2], "scale": Scale.LOG},
            }
        )
        assert space.ranges["k"] == Range(30.0, 60.0, Scale.LINEAR)
        assert space.ranges["E"] == Range(1e9, 1e12, Scale.LOG)
        assert space.ranges["t"] == Range(1.0, 2.0) and space.ranges["u"] == Range(1.0, 2.0)
        assert space.ranges["v"] == Range(0.0, 1.0) and space.ranges["w"].scale is Scale.LOG
        assert space.held == {"h": 0.01}

    def test_integers_read_as_doubles(self):
        space = ModelParameterSpace.parse({"k": [30, 60], "q": 3})
        assert type(space.ranges["k"].lo) is float and type(space.held["q"]) is float
        assert space.canonical() == ModelParameterSpace.parse({"k": [30.0, 60.0], "q": 3.0}).canonical()

    @pytest.mark.parametrize(
        "form",
        [
            [0, 1, 2],
            [0],
            "0, 1",
            None,
            [NAN, 1],
            [0, INF],
            [-INF, 0],
            [True, 2],
            ["0", 2],
            NAN,
            INF,
            True,
            "1",
            {"range": [0, 1], "scale": "ln"},
            {"range": [0, 1], "scale": "linear", "extra": 1},
            {"scale": "log"},
            {"range": [0, 1, 2]},
        ],
    )
    def test_malformed_refused_naming_the_model_parameter(self, form):
        with pytest.raises(RequestError, match="model parameter k"):
            ModelParameterSpace.parse({"k": form})

    def test_a_name_must_be_text(self):
        with pytest.raises(RequestError):
            ModelParameterSpace.parse({1: [0, 1]})

    def test_mappings_are_read_only(self):
        space = ModelParameterSpace.parse({"k": [30, 60], "q": 3})
        assert isinstance(space.ranges, MappingProxyType) and isinstance(space.held, MappingProxyType)
        with pytest.raises(TypeError):
            space.held["q"] = 4.0  # type: ignore[index]

    def test_range_refuses_what_isnt_a_finite_number(self):
        for bad in (NAN, INF, True, "1"):
            with pytest.raises(RequestError):
                Range(bad, 1.0)


class TestValidate:
    def test_accepts_the_contract_space(self):
        ModelParameterSpace.parse(CONTRACT_SPACE).validate(CONTRACT)

    @pytest.mark.parametrize(
        ("form", "named"),
        [
            ({"nope": [0, 1]}, "nope"),
            ({"k": [60, 30]}, "model parameter k"),
            ({"k": [30, 30]}, "model parameter k"),
            ({"q": {"range": [-1, 1], "scale": "log"}}, "model parameter q"),
            ({"q": {"range": [0, 1], "scale": "log"}}, "model parameter q"),
            ({"k": [0, 10]}, "gt 0"),
            ({"k": [-10, 10]}, "model parameter k"),
            ({"k": -1}, "gt 0"),
            ({"k": 0}, "model parameter k"),
        ],
    )
    def test_refused_naming_it(self, form, named):
        space = ModelParameterSpace.parse(form)
        with pytest.raises(RequestError, match=named):
            space.validate(HEAT)

    def test_a_strict_limit_accepts_a_range_just_inside(self):
        ModelParameterSpace.parse({"k": [1e-6, 10]}).validate(HEAT)

    def test_the_upper_limit(self):
        spec = make_spec([("p", 0.5, Limits(upper=1.0))])
        ModelParameterSpace.parse({"p": [0, 1]}).validate(spec)
        with pytest.raises(RequestError, match="le 1"):
            ModelParameterSpace.parse({"p": [0, 1.5]}).validate(spec)


class TestCanonical:
    def test_every_range_with_its_scale(self):
        space = ModelParameterSpace.parse({"k": [30, 60], "E": {"range": [1e9, 1e12], "scale": "log"}, "h": 1})
        assert space.canonical() == {
            "k": {"range": [30.0, 60.0], "scale": "linear"},
            "E": {"range": [1e9, 1e12], "scale": "log"},
            "h": 1.0,
        }

    def test_canonical_parses_to_the_same_space(self):
        space = ModelParameterSpace.parse(CONTRACT_SPACE)
        assert ModelParameterSpace.parse(space.canonical()) == space


class TestOrderAndCompletion:
    def test_varied_in_the_spec_order(self):
        space = ModelParameterSpace.parse({"c": [1, 2], "a": [0, 1]})
        assert space.varied(CONTRACT) == ("a", "c")

    def test_complete_fills_held_and_nominal_values(self):
        space = ModelParameterSpace.parse({"c": {"range": [1e-2, 1e2], "scale": "log"}, "a": [0, 2], "b": 0.25})
        X = space.complete(CONTRACT, np.array([[0.5, 3.0], [1.5, 4.0]]))
        assert X.tolist() == [[0.5, 0.25, 3.0, 0.5], [1.5, 0.25, 4.0, 0.5]]

    def test_at_point(self):
        space = ModelParameterSpace.at_point(HEAT, {"k": 50})
        assert space.ranges == {} and space.held == {"k": 50.0, "q": 3e4}
        assert list(space.held) == ["k", "q"]
        with pytest.raises(RequestError, match="nope"):
            ModelParameterSpace.at_point(HEAT, {"nope": 1.0})
        with pytest.raises(RequestError, match="model parameter k"):
            ModelParameterSpace.at_point(HEAT, {"k": NAN})


class TestMaps:
    space = ModelParameterSpace.parse({"a": [0, 2], "c": {"range": [1e-2, 1e2], "scale": "log"}})

    def test_forward_linear_and_log(self):
        X = self.space.from_unit(CONTRACT, np.array([[0.0, 0.0], [-0.5, 0.5]]))
        assert X[0, 0] == 1.0 and X[0, 2] == pytest.approx(1.0, rel=1e-15)
        assert X[1, 0] == 0.0 + 2.0 * 0.25
        assert X[1, 2] == np.clip(np.exp(np.log(1e-2) + (np.log(1e2) - np.log(1e-2)) * 0.75), 1e-2, 1e2)

    def test_faces_exact(self):
        X = self.space.from_unit(CONTRACT, np.array([[-1.0, -1.0], [1.0, 1.0]]))
        assert X[0, 0] == 0.0 and X[0, 2] == 1e-2 and X[1, 0] == 2.0 and X[1, 2] == 1e2

    def test_clamped(self):
        X = self.space.from_unit(CONTRACT, np.array([[-1.5, 1.0 + 1e-15]]))
        assert X[0, 0] == 0.0 and X[0, 2] == 1e2

    def test_from_cube_is_the_formula(self):
        U = np.array([[0.0, 0.0], [0.25, 0.999], [0.5, 0.5]])
        X = self.space.from_cube(CONTRACT, U)
        assert X[0, 0] == 0.0 and X[0, 2] == 1e-2
        assert X[1, 0] == 0.0 + (2.0 - 0.0) * 0.25
        lo, hi = 1e-2, 1e2
        assert X[1, 2] == np.clip(np.exp(np.log(lo) + (np.log(hi) - np.log(lo)) * 0.999), lo, hi)
        assert X[:, 1].tolist() == [0.0, 0.0, 0.0] and X[:, 3].tolist() == [0.5, 0.5, 0.5]

    def test_map_back(self):
        X = self.space.from_unit(CONTRACT, np.array([[0.25, -0.75]]))
        Z = self.space.to_unit(CONTRACT, X)
        assert Z.shape == (1, 2)
        assert Z[0, 0] == (2 * X[0, 0] - 2.0) / 2.0
        assert abs(Z[0, 1] - -0.75) < 1e-15

    @pytest.mark.parametrize(
        ("form", "x", "z"),
        [
            ([0.1, 0.7], 0.1, -1.0),
            ([0.3, 1.1], 0.3, -1.0),
            ({"range": [1e-6, 10], "scale": "log"}, 10.0, 1.0),
            ({"range": [1e-6, 10], "scale": "log"}, 1e-6, -1.0),
            ([0.1, 0.7], 0.7, 1.0),
        ],
    )
    def test_map_back_known_answers(self, form, x, z):
        """G10's known answers (0061): lo and hi map exactly to -1 and 1."""
        spec = make_spec([("p", x)])
        assert ModelParameterSpace.parse({"p": form}).to_unit(spec, np.array([[x]]))[0, 0] == z

    def test_map_back_clamped(self):
        spec = make_spec([("p", 0.5)])
        assert ModelParameterSpace.parse({"p": [0, 1]}).to_unit(spec, np.array([[1.5], [-0.5]])).tolist() == [
            [1.0],
            [-1.0],
        ]

    def test_log_geometric_center_is_zero(self):
        spec = make_spec([("p", 1.0)])
        space = ModelParameterSpace.parse({"p": {"range": [1e-6, 1e6], "scale": "log"}})
        assert space.to_unit(spec, np.array([[1.0]]))[0, 0] == 0.0
        assert space.from_unit(spec, np.array([[0.0]]))[0, 0] == pytest.approx(1.0, rel=1e-14)

    def test_contains(self):
        X = np.array([[0.0, 0.0, 1e-2, 0.5], [2.0, 0.0, 1e2, 0.5], [2.1, 0.0, 1.0, 0.5], [1.0, 0.1, 1.0, 0.5]])
        assert self.space.contains(CONTRACT, X).tolist() == [True, True, False, False]


class TestClipLine:
    space = ModelParameterSpace.parse({"a": [0, 2], "b": [-1, 1]})

    def test_segment(self):
        t0, t1 = self.space.clip_line(CONTRACT, np.array([0.0, 0.0]), np.array([1.0, 1.0]))
        assert (t0, t1) == (-1.0, 1.0)
        t0, t1 = self.space.clip_line(CONTRACT, np.array([0.5, 0.0]), np.array([1.0, 0.0]))
        assert (t0, t1) == (-1.5, 0.5)
        t0, t1 = self.space.clip_line(CONTRACT, np.array([0.0, 0.5]), np.array([-2.0, 1.0]))
        assert (t0, t1) == (-0.5, 0.5)

    def test_zero_direction_refused(self):
        with pytest.raises(RequestError, match="direction"):
            self.space.clip_line(CONTRACT, np.array([0.0, 0.0]), np.array([0.0, 0.0]))
