"""Given, coordinate, and random lines (designs.md, Lines; G10-G14, G18; 0012, 0047, 0051, 0062, 0065)."""

from typing import ClassVar

import numpy as np
import pytest

from ema.designs import generators
from ema.designs.lines import SHARED_ANCHOR_TOL, lines_through_anchor
from ema.types.errors import RequestError
from ema.types.model import Limits
from ema.types.space import ModelParameterSpace
from tests.support.designs import CONTRACT, CONTRACT_SPACE, make_spec
from tests.support.designs import identity as ident

GIVEN = generators.get("lines")
COORD = generators.get("coordinate_lines")
RANDOM = generators.get("random_lines")

#: Six model parameters with nominal values at their ranges' centers (geometric on log ranges), as U2's.
SIX = make_spec([("a", 1.0), ("b", 0.0), ("c", 1.0), ("d", 15.0), ("e", 10.0), ("f", 1.0)], name="six")
SIX_SPACE = {
    "a": [0, 2],
    "b": [-1, 1],
    "c": {"range": [1e-2, 1e2], "scale": "log"},
    "d": [10, 20],
    "e": {"range": [1, 100], "scale": "log"},
    "f": [-3, 5],
}


def distinct(points: np.ndarray) -> int:
    return len({row.tobytes() for row in points})


def unit(space_form, spec, points):
    return ModelParameterSpace.parse(space_form).to_unit(spec, points)


class TestG10EvenlySpacedEndToEnd:
    space: ClassVar[dict] = {"a": [0, 2], "c": {"range": [1e-2, 1e2], "scale": "log"}}

    def test_a_diagonal_line_through_a_log_range(self):
        design = GIVEN.build(
            ident(CONTRACT, "lines", self.space, n=9, lines=[{"anchor": {}, "direction": {"a": 1, "c": 1}}]), CONTRACT
        )
        Z = unit(self.space, CONTRACT, design.points)
        steps = np.diff(Z, axis=0)
        assert np.allclose(steps, steps[0], rtol=0, atol=1e-15), "unequal steps in unit coordinates"
        assert design.points[0, 0] == 0.0 and design.points[0, 2] == 1e-2
        assert design.points[-1, 0] == 2.0 and design.points[-1, 2] == 1e2
        # This range's computed top end, exp(ln lo + (ln hi - ln lo)), misses hi (0047): the end is hi exactly.
        assert np.exp(np.log(1e-2) + (np.log(1e2) - np.log(1e-2)) * 1.0) != 1e2

    def test_order_runs_along_the_direction(self):
        design = GIVEN.build(
            ident(CONTRACT, "lines", self.space, n=5, lines=[{"anchor": {}, "direction": {"a": -1}}]), CONTRACT
        )
        assert design.points[0, 0] == 2.0 and design.points[-1, 0] == 0.0
        coord = COORD.build(ident(CONTRACT, "coordinate_lines", self.space, n=5), CONTRACT)
        assert coord.points[0, 0] == 0.0 and coord.points[4, 0] == 2.0, "a coordinate line runs from lo to hi"

    def test_a_zero_direction_component_keeps_the_anchors_value(self):
        """0062 item 4: 0.3 on [-1, 1] stays 0.3 on every point, not mapped back and forth."""
        design = GIVEN.build(
            ident(
                CONTRACT,
                "lines",
                {"a": [0, 2], "b": [-1, 1]},
                n=17,
                lines=[{"anchor": {"b": 0.3}, "direction": {"a": 1}}],
            ),
            CONTRACT,
        )
        assert np.all(design.points[:, 1] == 0.3)
        assert design.lines[0].anchor[1] == 0.3

    def test_line_records(self):
        design = GIVEN.build(
            ident(
                CONTRACT,
                "lines",
                self.space,
                n=5,
                lines=[{"anchor": {"a": 0.5}, "direction": {"a": 1, "c": 1}}, {"anchor": {}, "direction": {"c": 2}}],
            ),
            CONTRACT,
        )
        first, second = design.lines
        assert first.rows == (0, 5) and second.rows == (5, 10)
        assert first.direction == (1.0, 1.0) and second.direction == (0.0, 2.0), "kept as given (0065)"
        assert first.anchor[0] == 0.5 and first.anchor[1] == 0.0 and first.anchor[3] == 0.5
        assert first.ends == (tuple(design.points[0]), tuple(design.points[4]))


@pytest.mark.parametrize("kind", ["lines", "coordinate_lines", "random_lines"])
def test_g11_a_line_of_2n_minus_1_points_contains_the_line_of_n(kind):
    extra = {"lines": [{"anchor": {"a": 0.3}, "direction": {"a": 1, "b": -0.4, "c": 0.7}}]} if kind == "lines" else {}
    extra |= {"m": 4} if kind == "random_lines" else {}
    gen = generators.get(kind)
    small = gen.build(ident(CONTRACT, kind, CONTRACT_SPACE, n=17, **extra), CONTRACT)
    large = gen.build(ident(CONTRACT, kind, CONTRACT_SPACE, n=33, **extra), CONTRACT)
    for s, g in zip(small.lines, large.lines, strict=True):
        assert np.array_equal(large.points[g.rows[0] : g.rows[1]][::2], small.points[s.rows[0] : s.rows[1]])


class TestG12SharedAnchor:
    def test_u2_102_rows_97_distinct(self):
        design = COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=17), SIX)
        assert len(design) == 102 and distinct(design.points) == 97
        anchor = np.array([1.0, 0.0, 1.0, 15.0, 10.0, 1.0])
        for line in design.lines:
            assert np.array_equal(design.points[line.rows[0] + 8], anchor)

    def test_off_center_in_one(self):
        design = COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=17, anchor={"a": 0.3}), SIX)
        assert distinct(design.points) == 98

    def test_off_center_in_all_six(self):
        anchor = {"a": 0.3, "b": 0.1, "c": 2.0, "d": 11.0, "e": 3.0, "f": 0.3}
        design = COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=17, anchor=anchor), SIX)
        assert distinct(design.points) == 102

    def test_n_even(self):
        design = COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=16), SIX)
        assert len(design) == 96 and distinct(design.points) == 96

    @pytest.mark.parametrize("anchor", [{"a": 0.0}, {"a": 2.0}, {"a": 0.5}, {"d": 10.0}, {"c": 1e2}])
    def test_an_anchor_on_a_grid_point_off_center_is_refused(self, anchor):
        (name,) = anchor
        with pytest.raises(RequestError, match=f"model parameter {name}"):
            COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=17, anchor=anchor), SIX)

    def test_a_nominal_value_at_a_ranges_end_is_refused(self):
        """The degenerate case (contracts.md): a's nominal moved to 0, a range's end (0051)."""
        spec = make_spec([("a", 0.0), ("b", 0.0)])
        with pytest.raises(RequestError, match="model parameter a"):
            COORD.build(ident(spec, "coordinate_lines", {"a": [0, 2], "b": [-1, 1]}, n=17), spec)

    def test_the_tolerance(self):
        assert SHARED_ANCHOR_TOL == 1e-12

    @pytest.mark.parametrize(
        ("space", "anchor", "n", "through"),
        [
            ({"a": 5.0, "b": [-1, 1], "c": [-1, 1]}, {}, 5, ("b", "c")),  # a held model parameter first
            ({"a": [-1, 1], "b": 5.0, "c": [-1, 1]}, {"c": 0.3}, 5, ("a",)),  # one between varied ones
            ({"a": [-1, 1], "b": 5.0, "c": [-1, 1]}, {"a": 0.3}, 5, ("c",)),
            ({"a": [-1, 1], "b": 5.0, "c": [-1, 1]}, {}, 4, ()),  # n even
        ],
    )
    def test_lines_through_anchor_names_the_lines_built_through_it(self, space, anchor, n, through):
        """G12 in one place (review round 1): the lines ``lines_through_anchor`` names are those whose middle point
        is the anchor, bit for bit, in the built design; the report's Design row reads it."""
        spec = make_spec([("a", 0.0), ("b", 0.0), ("c", 0.0)])
        identity = ident(spec, "coordinate_lines", space, n=n, anchor=anchor)
        design = COORD.build(identity, spec)
        varied = [k for k, v in space.items() if isinstance(v, list)]
        x = np.array([anchor.get(k, space[k] if k not in varied else 0.0) for k in "abc"])
        built = tuple(
            name
            for name, line in zip(varied, design.lines, strict=True)
            if n % 2 and np.array_equal(design.points[line.rows[0] + (n - 1) // 2], x)
        )
        assert lines_through_anchor(identity, spec) == built == through


class TestG13RandomLines:
    def test_first_m_of_m_plus_1_and_line_3_alone(self):
        five = RANDOM.build(ident(CONTRACT, "random_lines", CONTRACT_SPACE, m=5, n=7, seed=1), CONTRACT)
        six_id = ident(CONTRACT, "random_lines", CONTRACT_SPACE, m=6, n=7, seed=1)
        six = RANDOM.build(six_id, CONTRACT)
        assert np.array_equal(six.points[:35], five.points) and six.lines[:5] == five.lines
        alone = RANDOM.build(six_id, CONTRACT, 21, 28)
        assert np.array_equal(alone.points, six.points[21:28])

    def test_directions_are_normalized_and_seeds_differ(self):
        design = RANDOM.build(ident(CONTRACT, "random_lines", CONTRACT_SPACE, m=5, n=7, seed=1), CONTRACT)
        for line in design.lines:
            assert abs(np.sqrt(np.sum(np.square(line.direction))) - 1.0) < 1e-15
        other = RANDOM.build(ident(CONTRACT, "random_lines", CONTRACT_SPACE, m=5, n=7, seed=2), CONTRACT)
        assert not np.array_equal(design.points, other.points)


class TestG14Refusals:
    space: ClassVar[dict] = {"a": [0, 2], "b": [-1, 1]}

    @pytest.mark.parametrize(
        ("lines", "named"),
        [
            ([{"anchor": {"a": 3.0}, "direction": {"a": 1}}], "model parameter a"),
            ([{"anchor": {"nope": 1.0}, "direction": {"a": 1}}], "nope"),
            ([{"anchor": {"h": 0.6}, "direction": {"a": 1}}], "model parameter h"),
            ([{"anchor": {}, "direction": {"a": 0, "b": 0}}], "direction"),
            ([{"anchor": {}, "direction": {"h": 1}}], "model parameter h"),
            ([{"anchor": {}, "direction": {"c": 1}}], "model parameter c"),
            ([{"anchor": {}, "direction": {"nope": 1}}], "nope"),
            ([{"anchor": {}}], "direction"),
            ([{"anchor": {}, "direction": {"a": 1}, "extra": 1}], "extra"),
            ([], "lines"),
            ({"anchor": {}, "direction": {"a": 1}}, "lines"),
        ],
    )
    def test_given_lines(self, lines, named):
        with pytest.raises(RequestError, match=named):
            GIVEN.build(ident(CONTRACT, "lines", self.space, n=5, lines=lines), CONTRACT)

    def test_n_below_2(self):
        for gen, extra in (
            (GIVEN, {"lines": [{"anchor": {}, "direction": {"a": 1}}]}),
            (COORD, {}),
            (RANDOM, {"m": 2}),
        ):
            with pytest.raises(RequestError, match=r"\bn\b"):
                gen.build(ident(CONTRACT, gen.name, self.space, n=1, **extra), CONTRACT)

    def test_a_coordinate_lines_nominal_outside_its_range(self):
        with pytest.raises(RequestError, match="model parameter a"):
            COORD.build(ident(CONTRACT, "coordinate_lines", {"a": [1.5, 2], "b": [-1, 1]}, n=5), CONTRACT)

    def test_a_coordinate_lines_anchor_naming_an_unknown_name(self):
        with pytest.raises(RequestError, match="nope"):
            COORD.build(ident(CONTRACT, "coordinate_lines", self.space, n=5, anchor={"nope": 1.0}), CONTRACT)

    def test_a_line_meeting_the_space_at_one_point(self):
        with pytest.raises(RequestError, match=r"lines\[0\], the line, meets the space at one point only"):
            GIVEN.build(
                ident(
                    CONTRACT,
                    "lines",
                    self.space,
                    n=5,
                    lines=[{"anchor": {"a": 2.0, "b": 1.0}, "direction": {"a": 1, "b": -1}}],
                ),
                CONTRACT,
            )


def test_g18_an_unnamed_log_coordinate_is_at_the_geometric_center():
    """0065 item 4: the anchor's unnamed varied model parameter is at u = 1/2 of its range's map."""
    space = {"a": [0, 2], "c": {"range": [1e-6, 1e6], "scale": "log"}}
    design = GIVEN.build(ident(CONTRACT, "lines", space, n=5, lines=[{"anchor": {}, "direction": {"a": 1}}]), CONTRACT)
    center = ModelParameterSpace.parse(space).from_unit(CONTRACT, np.array([[0.0, 0.0]]))[0, 2]
    assert center == pytest.approx(1.0, rel=1e-14)
    assert np.all(design.points[:, 2] == center) and design.lines[0].anchor[2] == center
    diag = GIVEN.build(
        ident(CONTRACT, "lines", space, n=5, lines=[{"anchor": {}, "direction": {"a": 1, "c": 1}}]), CONTRACT
    )
    assert diag.lines[0].direction == (1.0, 1.0)


def test_limits_hold_on_every_line():
    spec = make_spec([("a", 1.0, Limits(lower=0.0, lower_strict=True)), ("b", 0.0)])
    for gen, extra in ((COORD, {}), (RANDOM, {"m": 3})):
        design = gen.build(ident(spec, gen.name, {"a": [1e-6, 2], "b": [-1, 1]}, n=9, **extra), spec)
        assert np.all(design.points[:, 0] > 0)


class TestG10EndsOnTheirFaces:
    """m3 (review round 1): each end's bounding coordinates are exactly lo or hi, by the far-end face rule and the
    t = 1 point set to the segment's far end (C21)."""

    @pytest.mark.parametrize("form", [CONTRACT_SPACE, {**CONTRACT_SPACE, "c": {"range": [1e-6, 1e6], "scale": "log"}}])
    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 7])
    def test_random_lines(self, form, seed):
        from tests.contracts.design import assert_ends_on_faces

        design = RANDOM.build(ident(CONTRACT, "random_lines", form, m=50, n=5, seed=seed), CONTRACT)
        assert_ends_on_faces(design, CONTRACT, ModelParameterSpace.parse(form))

    def test_random_lines_seed_0_line_8_far_end(self):
        design = RANDOM.build(ident(CONTRACT, "random_lines", CONTRACT_SPACE, m=10, n=5, seed=0), CONTRACT)
        assert design.lines[8].ends[1][2] == 0.01

    def test_a_given_line_whose_far_end_by_steps_misses_its_face(self):
        """The far end, computed as anchor + t1·direction, has a = -0.9999999999999998; the face rule sets it to
        -1 exactly."""
        from tests.contracts.design import assert_ends_on_faces

        form = {"a": [-1, 1], "b": [-1, 1]}
        a, b = 0.6120714150542472, 0.26063551088695647
        line = {"anchor": {"a": a, "b": b}, "direction": {"a": -1.5547311319959862, "b": 0.16863040701051427}}
        design = GIVEN.build(ident(CONTRACT, "lines", form, n=9, lines=[line]), CONTRACT)
        assert_ends_on_faces(design, CONTRACT, ModelParameterSpace.parse(form))
        assert design.points[0, 0] == 1.0 and design.points[-1, 0] == -1.0


class TestSizeRefusesWhatBuildRefuses:
    """m8 (review round 1): size() makes build()'s cheap checks, so it never sizes a design build() refuses."""

    @pytest.mark.parametrize(
        "lines",
        [
            [{"anchor": {"a": 3.0}, "direction": {"a": 1}}],
            [{"anchor": {}, "direction": {"a": 0}}],
            [{"anchor": {}}],
            [{"anchor": {"a": 2.0, "b": 1.0}, "direction": {"a": 1, "b": -1}}],
        ],
    )
    def test_given_lines(self, lines):
        identity = ident(CONTRACT, "lines", {"a": [0, 2], "b": [-1, 1]}, n=5, lines=lines)
        for call in (GIVEN.size, GIVEN.build):
            with pytest.raises(RequestError):
                call(identity, CONTRACT)

    def test_coordinate_lines_anchor_on_its_line(self):
        identity = ident(SIX, "coordinate_lines", SIX_SPACE, n=17, anchor={"a": 0.5})
        for call in (COORD.size, COORD.build):
            with pytest.raises(RequestError, match="model parameter a"):
                call(identity, SIX)


@pytest.mark.parametrize("n", [2, 3, 16, 17, 41])
def test_0051_from_the_points_near_the_anchor_equals_from_the_whole_line(n):
    """m6 (review round 1): coordinate lines check 0051 on the few points near the anchor's place; every point
    of every line, as an anchor, is refused unless it is the shared middle, and the doubles beside it are not."""
    whole = COORD.build(ident(SIX, "coordinate_lines", SIX_SPACE, n=n), SIX)
    names = [p.name for p in SIX.parameters]
    for k, line in enumerate(whole.lines):
        name = names[k]
        column = whole.points[line.rows[0] : line.rows[1], k]
        for j, value in enumerate(column.tolist()):
            middle = n % 2 == 1 and j == (n - 1) // 2
            identity = ident(SIX, "coordinate_lines", SIX_SPACE, n=n, anchor={name: value})
            if middle:
                assert COORD.size(identity, SIX) == 6 * n
            else:
                with pytest.raises(RequestError, match=f"model parameter {name}"):
                    COORD.size(identity, SIX)
            for beside in (np.nextafter(value, -np.inf), np.nextafter(value, np.inf)):
                r = ModelParameterSpace.parse(SIX_SPACE).ranges[name]
                if r.lo <= beside <= r.hi and beside not in column:
                    assert (
                        COORD.size(ident(SIX, "coordinate_lines", SIX_SPACE, n=n, anchor={name: beside}), SIX) == 6 * n
                    )
