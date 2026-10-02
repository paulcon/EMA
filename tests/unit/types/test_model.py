"""The model spec's dataclasses, built in Python (architecture.md §3, model.py; 0061 item 6; 0065)."""

import math
from types import MappingProxyType

import pytest

from ema.types.errors import RequestError, SpecError
from ema.types.model import (
    CommandLine,
    CsvParser,
    FileEntry,
    InputDeck,
    JsonParser,
    Keep,
    Limits,
    ModelParameter,
    ModelSpec,
    PredictionSpec,
    PythonFunction,
    RegexParser,
)
from tests.support.designs import CONTRACT, HEAT


class TestLimits:
    def test_contains(self):
        gt0 = Limits(lower=0.0, lower_strict=True)
        assert not gt0.contains(0.0) and gt0.contains(1e-300)
        ge0_le1 = Limits(lower=0.0, upper=1.0)
        assert ge0_le1.contains(0.0) and ge0_le1.contains(1.0) and not ge0_le1.contains(1.0000000000000002)
        lt1 = Limits(upper=1.0, upper_strict=True)
        assert not lt1.contains(1.0) and lt1.contains(-1e300)
        assert Limits().contains(-1e308)

    def test_integers_become_doubles(self):
        lim = Limits(lower=0, upper=10)
        assert type(lim.lower) is float and type(lim.upper) is float

    @pytest.mark.parametrize("bad", [True, "1", math.nan, math.inf])
    def test_refused(self, bad):
        with pytest.raises(SpecError):
            Limits(lower=bad)


class TestModelParameter:
    def test_nominal_becomes_a_double(self):
        p = ModelParameter(name="k", units="", description="", nominal=45)
        assert type(p.nominal) is float and p.nominal == 45.0

    @pytest.mark.parametrize("bad", [True, "45", math.nan, -math.inf, None])
    def test_nominal_refused(self, bad):
        with pytest.raises(SpecError, match="k"):
            ModelParameter(name="k", units="", description="", nominal=bad)


def test_model_spec_lookups():
    assert HEAT.parameter("k").nominal == 45.0
    with pytest.raises(RequestError, match="nope"):
        HEAT.parameter("nope")
    single = ModelSpec(
        name="one",
        description="",
        interface=PythonFunction(function="m.py:f"),
        parameters=HEAT.parameters,
        predictions=(PredictionSpec(name="y", units="", description=""),),
    )
    assert single.prediction(None).name == "y"
    assert CONTRACT.prediction("z").name == "z"
    with pytest.raises(RequestError, match="y, z"):
        CONTRACT.prediction(None)
    with pytest.raises(RequestError, match="nope"):
        CONTRACT.prediction("nope")


def test_model_spec_holds_tuples_and_read_only_mappings():
    spec = ModelSpec(
        name="heat",
        description="",
        interface=CommandLine(command=["./heat", "plate.in"], input_decks=[InputDeck("t.in", "plate.in")]),
        parameters=list(HEAT.parameters),
        predictions=[PredictionSpec("T_max", "K", "", RegexParser("plate.out", r"T_max = (\S+)"))],
        files=[FileEntry("mesh.dat", shared=True)],
        env={"OMP_NUM_THREADS": "4"},
        pass_env=["HOME"],
    )
    assert isinstance(spec.parameters, tuple) and isinstance(spec.predictions, tuple)
    assert isinstance(spec.files, tuple) and isinstance(spec.pass_env, tuple)
    assert isinstance(spec.interface, CommandLine) and spec.interface.command == ("./heat", "plate.in")
    assert isinstance(spec.env, MappingProxyType)
    with pytest.raises(TypeError):
        spec.env["X"] = "1"  # type: ignore[index]
    assert spec.keep is Keep.ALL and spec.timeout_s == 3600.0 and not spec.noisy


def test_parser_defaults():
    assert RegexParser("stdout", "(.*)").match == "last"
    assert CsvParser("out.csv", "y").row == -1 and CsvParser("out.csv", 0).delimiter == ","
    assert JsonParser("out.json", "a.b.0").key == "a.b.0"
