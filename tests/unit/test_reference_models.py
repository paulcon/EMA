"""The reference models (reference_models.md; architecture.md §11): each spec loads, its space fits it, and each
function gives the model's truths, checked against ``docs/checks/refmodels.py`` (written from the spec alone, an
independent source) at random points, and against the analytic values the spec states.
"""

from __future__ import annotations

import importlib.util
import math
import shutil
import string
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from ema import reference_models
from ema.models.spec import load_spec
from ema.types.space import ModelParameterSpace
from tests.support import reference

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("refmodels", ROOT / "docs" / "checks" / "refmodels.py")
assert _spec is not None and _spec.loader is not None
refmodels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(refmodels)

DETERMINISTIC = ["R1", "R2", "R3", "R4a", "R4b", "R7", "R10", "R11"]


@pytest.mark.parametrize("id", reference_models.IDS)
def test_each_spec_loads_and_its_space_fits(id):
    """Each reference model is a model spec with its files (M3, M17: no unlisted import), and its space validates."""
    loaded = load_spec(reference_models.path(id))
    assert not loaded.warnings and not loaded.spec.noisy
    space = ModelParameterSpace.parse(reference_models.space(id))
    space.validate(loaded.spec)
    assert space.varied(loaded.spec) == tuple(p.name for p in loaded.spec.parameters), "the space varies every one"
    nominal = np.array([[p.nominal for p in loaded.spec.parameters]])
    z = space.to_unit(loaded.spec, nominal)
    assert np.allclose(z, 0.0, atol=1e-12), "nominal values at the ranges' centers (geometric, on a log range)"


def test_names_and_ids():
    assert reference.model("R2").spec.name == "ishigami"  # 0060
    assert reference_models.path("r4a") == reference_models.path("R4a")
    with pytest.raises(ValueError, match="R9, a real simulator, comes later"):
        reference_models.path("R9")
    with pytest.raises(ValueError, match="no reference model 'R12'"):
        reference_models.path("R12")


@pytest.mark.parametrize("id", DETERMINISTIC)
def test_each_function_agrees_with_the_independent_models(id):
    """At 200 random points in unit coordinates, each function equals refmodels.py's, to rounding."""
    loaded = reference.model(id)
    fn = reference.function(id)
    space = ModelParameterSpace.parse(reference_models.space(id))
    z = np.random.default_rng(20261002).uniform(-1, 1, (200, len(loaded.spec.parameters)))
    points = space.from_unit(loaded.spec, z)
    names = [p.name for p in loaded.spec.parameters]
    ours = np.array([fn(**dict(zip(names, map(float, row), strict=True))) for row in points])
    theirs = refmodels.evaluate_unit(id, z)
    assert np.allclose(ours, theirs, rtol=1e-12, atol=1e-15), np.max(np.abs(ours - theirs))


def test_r1_is_linear_in_unit_coordinates_and_10_at_the_nominal_point():
    """R1: 10 + 3u_a - u_b + 0u_c + 2u_k exactly in unit coordinates, only with k's log scale; R1(nominal) = 10."""
    fn = reference.function("R1")
    assert fn(a=1.0, b=0.0, c=15.0, k=10.0) == 10.0
    loaded = reference.model("R1")
    space = ModelParameterSpace.parse(reference_models.space("R1"))
    z = np.random.default_rng(1).uniform(-1, 1, (50, 4))
    y = [fn(**dict(zip("abck", map(float, row), strict=True))) for row in space.from_unit(loaded.spec, z)]
    u = space.to_unit(loaded.spec, space.from_unit(loaded.spec, z))
    assert np.allclose(y, 10 + 3 * u[:, 0] - u[:, 1] + 2 * u[:, 3], rtol=0, atol=1e-13)


def test_r2_is_v1s_ishigami():
    """R2 is v1's ishigami, ported (EMA v1 at v1-final: src/ema/testfunctions/library.py)."""
    fn = reference.function("R2")
    assert fn(x1=0.0, x2=0.0, x3=0.0) == 0.0
    assert math.isclose(fn(x1=math.pi / 2, x2=math.pi / 2, x3=1.0), 1 + 7 + 0.1)


def test_r3_at_its_nominal_point():
    fn = reference.function("R3")
    loaded = reference.model("R3")
    y = fn(**{p.name: p.nominal for p in loaded.spec.parameters})
    assert math.isclose(y, refmodels.evaluate_unit("R3", np.zeros((1, 8)))[0], rel_tol=1e-13) and 50 < y < 100


def test_r4_constants():
    assert reference.function("R4a")(a=0.3, b=-0.2, c=0.9) == 2.5
    r4b = reference.function("R4b")
    assert r4b(a=0.0, b=0.0, c=0.0) == 2.5 and r4b(a=0.01, b=0.0, c=0.0) != 2.5


def test_r5_fails_in_its_regions():
    """R5: an error where a + b > 1; z missing where b > 0.8; y and z elsewhere. (The timeout region sleeps 5 s, so
    it is tested where its runs are made: tests/support/reference.py stops it at the spec's 0.2 s.)"""
    fn = reference.function("R5")
    with pytest.raises(ValueError, match="no convergence"):
        fn(a=0.9, b=0.9)
    out = fn(a=-0.5, b=0.9)
    assert out["y"] == -0.5 + 0.81 and math.isnan(out["z"])
    assert fn(a=0.25, b=-0.5) == {"y": 0.5, "z": 0.75}
    assert reference.model("R5").spec.timeout_s == 0.2


@pytest.mark.slow
def test_r5_times_out_in_its_corner():
    case = reference.prepare(__import__("ema.diagnostics", fromlist=["base"]).base.get("point_run"), "R5",
                             params={"x": {"a": -0.9, "b": -0.9}, "repeats": 0}, prediction="y")  # fmt: skip
    made = reference.batch(case, "R5")
    assert made.runs.kind.tolist() == [1] and "timeout after 0.2 s" in made.runs.reasons.values()


@pytest.mark.parametrize(("id", "scale"), [("R6a", 0.05), ("R6b", 1e-7)])
def test_r6_draws_fresh_noise(id, scale):
    """R6a and R6b: R1 plus noise of the stated size, never repeating a draw."""
    fn = reference.function(id)
    draws = np.array([fn(a=1.0, b=0.0, c=15.0, k=10.0) for _ in range(400)])
    assert len(np.unique(draws)) == 400
    assert 0.8 * scale < np.std(draws - 10.0) < 1.2 * scale


def test_r7_features_at_their_places():
    fn = reference.function("R7")
    assert fn(a=0.6, b=0.0, c=0.0, e=0.0) == 1.0 and fn(a=0.7, b=0.0, c=0.0, e=0.0) > 1.0
    assert fn(a=0.0, b=0.2, c=0.0, e=0.0) == 1.0 and fn(a=0.0, b=0.2000001, c=0.0, e=0.0) == 2.0
    assert fn(a=0.0, b=0.0, c=0.5, e=0.0) == 0.5


def test_r10_and_r11_at_the_nominal_point():
    assert reference.function("R10")(a=0.0, b=0.0, c=0.0, e=0.0) == pytest.approx(-0.5 * math.sqrt(5) / 2)
    assert reference.function("R11")(a=0.0, b=0.0) == 1.0


def test_r8_is_r7_as_a_program(tmp_path):
    """R8: its input deck, shared file, and program give R7's value, written exactly (the runner runs it at step 11)."""
    loaded = reference.model("R8")
    source = Path(loaded.model_dir)
    for name in ("r8.py", "table.dat"):
        shutil.copy(source / name, tmp_path / name)
    r7 = reference.function("R7")
    rng = np.random.default_rng(8)
    for _ in range(3):
        x = dict(zip("abcefg", map(float, rng.uniform(-1, 1, 6)), strict=True))
        template = string.Template((source / "x.in.template").read_text())
        (tmp_path / "x.in").write_text(template.substitute({k: repr(v) for k, v in x.items()}))
        subprocess.run([sys.executable, "r8.py", "x.in"], cwd=tmp_path, check=True, timeout=30)
        text = (tmp_path / "out.txt").read_text()
        assert float(text.removeprefix("y = ")) == r7(a=x["a"], b=x["b"], c=x["c"], e=x["e"])
    assert loaded.spec.interface.command[0] == "python3"  # type: ignore[union-attr]
