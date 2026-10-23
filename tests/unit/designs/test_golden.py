"""Golden points (G1; designs.md, Determinism; 0061, 0062): fixed requests whose points are pinned, on every
machine the checks run on.

The ``random`` sampler's unit rows and a linear range's points are compared bit for bit; a log range's points,
random lines, and a line through a space with a log range, in unit coordinates by the map back, within
``GOLDEN_UNIT_TOL``. Each golden range has |ln lo|, |ln hi| <= 64 and ln hi - ln lo >= 1. The values were
recorded from the first build (2026-10-01, macOS on Intel, numpy 2.5.3), each checked first against an independent
construction: numpy's ``Generator.random``, lo + (hi - lo) u, the log map computed directly, and step 11's
``random_line`` and ``given_line`` (``docs/checks/gram_rates.py``). A change here is a loss of reuse to record,
never a test to update quietly.
"""

import numpy as np

from ema.designs import generators, samplers
from ema.designs.generators import GOLDEN_UNIT_TOL
from ema.types.space import ModelParameterSpace
from tests.support.designs import CONTRACT, identity, make_spec

RANDOM_ROWS = [
    [0.6409027267181323, 0.7933204843286321, 0.04643436037494142],
    [0.6358003493871048, 0.31781602269270726, 0.5439272987224618],
    [0.13844189706642585, 0.37399732617206893, 0.8714748716635244],
    [0.873811402076917, 0.39992975283026777, 0.4474991436235909],
]
LINEAR_POINTS = [
    [1.2818054534362646, 0.5866409686572642, 1.0, 0.5],
    [0.09286872074988284, 0.27160069877420967, 1.0, 0.5],
    [0.6356320453854145, 0.08785459744492363, 1.0, 0.5],
]
LOG_UNIT = [[0.250190933209334], [0.794427601939151], [0.551371380490387]]
RANDOM_LINES_UNIT = [
    [1.0, -0.4019671544341825, 0.3580589943974348, -0.6369617512548017],
    [0.2782085147838549, -0.7009835772170914, 0.27673189992517866, -0.3043641159945297],
    [-0.44358297043229, -1.0, 0.19540480545292227, 0.028233519265742135],
    [-0.8808701661505232, 1.0, 0.15020205143144771, 0.5404548073970623],
    [-0.2924943295892697, 0.4353571434418919, -0.31633548065402917, -0.22977259630146885],
    [0.2958815069719838, -0.12928571311621595, -0.7828730127395059, -1.0],
]
LOG_LINE_UNIT = [
    [-1.0, -1.0],
    [-0.5, -0.4999999999999999],
    [0.0, 9.643274665532862e-17],
    [0.5, 0.5000000000000001],
    [1.0, 1.0],
]


def within(z: np.ndarray, golden: list) -> bool:
    return z.shape == np.shape(golden) and bool(np.all(np.abs(z - np.array(golden)) <= GOLDEN_UNIT_TOL))


def test_the_random_samplers_unit_rows_bit_for_bit():
    assert np.array_equal(samplers.get("random").unit_rows(20261001, 3, 0, 4), np.array(RANDOM_ROWS))


def test_a_linear_range_bit_for_bit():
    space = {"a": [0, 2], "b": [-1, 1]}
    design = generators.get("uniform").build(identity(CONTRACT, "uniform", space, n=3, seed=20261001), CONTRACT)
    assert np.array_equal(design.points, np.array(LINEAR_POINTS))


def test_a_log_range_in_unit_coordinates():
    space = {"c": {"range": [1e-3, 1e3], "scale": "log"}}
    design = generators.get("uniform").build(identity(CONTRACT, "uniform", space, n=3, seed=7), CONTRACT)
    assert within(ModelParameterSpace.parse(space).to_unit(CONTRACT, design.points), LOG_UNIT)


def test_random_lines_in_unit_coordinates():
    spec = make_spec([(name, 0.0) for name in "abce"], name="r7")
    space = {name: [-1, 1] for name in "abce"}
    design = generators.get("random_lines").build(identity(spec, "random_lines", space, m=2, n=3, seed=1), spec)
    assert within(ModelParameterSpace.parse(space).to_unit(spec, design.points), RANDOM_LINES_UNIT)


def test_a_line_through_a_space_with_a_log_range_in_unit_coordinates():
    spec = make_spec([("a", 1.0), ("c", 1.0)], name="gold")
    space = {"a": [0, 2], "c": {"range": [1e-2, 1e2], "scale": "log"}}
    lines = [{"anchor": {}, "direction": {"a": 1, "c": 1}}]
    design = generators.get("lines").build(identity(spec, "lines", space, n=5, lines=lines), spec)
    assert within(ModelParameterSpace.parse(space).to_unit(spec, design.points), LOG_LINE_UNIT)
