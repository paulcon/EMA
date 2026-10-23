"""Known answers not from EMA's code (plan 01, task 3): numpy's own generator, the log map computed directly,
and step 11's line constructions (``docs/checks/gram_rates.py``, written from the specs with no EMA code),
compared in unit coordinates within ``GOLDEN_UNIT_TOL`` (G1, 0062)."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

from ema.designs import generators
from ema.designs.generators import GOLDEN_UNIT_TOL
from ema.types.model import ModelSpec
from ema.types.space import ModelParameterSpace
from tests.support.designs import CONTRACT, identity, make_spec

CHECKS = Path(__file__).resolve().parents[3] / "docs" / "checks"


@pytest.fixture(scope="module")
def step11():
    """``gram_rates`` and its ``refmodels``, imported from ``docs/checks/`` for this module only."""
    sys.path.insert(0, str(CHECKS))
    try:
        yield importlib.import_module("gram_rates")
    finally:
        sys.path.remove(str(CHECKS))
        sys.modules.pop("gram_rates", None)
        sys.modules.pop("refmodels", None)


def spec_and_space(step11, model: str) -> tuple[ModelSpec, dict]:
    spaces = step11.R.SPACES[model]
    spec = make_spec([(name, float(v[3])) for name, v in spaces.items()], name=model.lower())
    form = {
        name: ([lo, hi] if scale == "linear" else {"range": [lo, hi], "scale": "log"})
        for name, (lo, hi, scale, _) in spaces.items()
    }
    return spec, form


def as_unit(spec, form, x: dict) -> np.ndarray:
    X = np.column_stack([np.asarray(x[p.name], dtype=float) for p in spec.parameters])
    return ModelParameterSpace.parse(form).to_unit(spec, X)


def close(a, b) -> bool:
    return bool(np.all(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)) <= GOLDEN_UNIT_TOL))


def test_uniform_log_points_are_the_formula_computed_directly():
    form = {"c": {"range": [1e-2, 1e2], "scale": "log"}}
    design = generators.get("uniform").build(identity(CONTRACT, "uniform", form, n=200, seed=9), CONTRACT)
    u = np.random.default_rng(9).random((200, 1))[:, 0]
    lo, hi = 1e-2, 1e2
    expected = np.clip(np.exp(np.log(lo) + (np.log(hi) - np.log(lo)) * u), lo, hi)
    expected[u == 0.0] = lo
    assert np.array_equal(design.points[:, 2], expected)


@pytest.mark.parametrize("model", ["R7", "R1"])
def test_random_lines_match_step_11(step11, model):
    spec, form = spec_and_space(step11, model)
    n = 17
    design = generators.get("random_lines").build(identity(spec, "random_lines", form, m=5, n=n, seed=0), spec)
    for j, line in enumerate(design.lines):
        x, z0, z1, anchor_z, direction = step11.random_line(model, j, n, seed=0)
        assert close(line.direction, direction), f"line {j}: direction"
        assert close(
            as_unit(spec, form, {p.name: [v] for p, v in zip(spec.parameters, line.anchor, strict=True)}), [anchor_z]
        ), f"line {j}: anchor"
        ends = np.array(line.ends)
        assert close(as_unit(spec, form, {p.name: ends[:, i] for i, p in enumerate(spec.parameters)}), [z0, z1])
        ours = design.points[line.rows[0] : line.rows[1]]
        assert close(ModelParameterSpace.parse(form).to_unit(spec, ours), as_unit(spec, form, x)), f"line {j}"


@pytest.mark.parametrize(
    ("model", "directions"),
    [("R7", [{"a": 1, "e": 1}]), ("R10", [{"a": 1, "e": 1}, {"e": 1}])],
)
def test_given_lines_match_step_11(step11, model, directions):
    spec, form = spec_and_space(step11, model)
    n = 17
    lines = [{"anchor": {}, "direction": d} for d in directions]
    design = generators.get("lines").build(identity(spec, "lines", form, lines=lines, n=n), spec)
    for line, d in zip(design.lines, directions, strict=True):
        x, z0, z1 = step11.given_line(model, {}, d, n)
        ours = design.points[line.rows[0] : line.rows[1]]
        assert close(ModelParameterSpace.parse(form).to_unit(spec, ours), as_unit(spec, form, x))
        assert close(ModelParameterSpace.parse(form).to_unit(spec, np.array(line.ends)), [z0, z1])


@pytest.mark.parametrize("model", ["R1", "R3"])
def test_coordinate_lines_match_step_11(step11, model):
    spec, form = spec_and_space(step11, model)
    n = 17
    design = generators.get("coordinate_lines").build(identity(spec, "coordinate_lines", form, n=n), spec)
    assert len(design.lines) == len(spec.parameters)
    for i, line in enumerate(design.lines):
        x = step11.coordinate_line(model, i, n)
        ours = design.points[line.rows[0] : line.rows[1]]
        assert close(ModelParameterSpace.parse(form).to_unit(spec, ours), as_unit(spec, form, x)), f"line {i}"
