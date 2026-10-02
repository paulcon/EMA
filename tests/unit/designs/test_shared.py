"""The rules every generator shares (designs.md, Shared rules and The model parameter space; G2, G5, G6, G15,
G16, G18; 0049, 0061, 0062, 0065)."""

import numpy as np
import pytest

from ema.designs import generators
from ema.designs.generators import GOLDEN_UNIT_TOL, MAX_DESIGN_POINTS
from ema.types.errors import DesignTooLarge, RequestError
from ema.types.space import ModelParameterSpace
from tests.contracts.design import CASES
from tests.support.designs import CONTRACT, CONTRACT_SPACE, D1, D1_SPACE, D20, D20_SPACE, identity, with_identity

KINDS = ("point", "uniform", "convergent", "lines", "coordinate_lines", "random_lines")


def test_the_six_generators_and_the_constants():
    assert generators.names() == tuple(sorted(KINDS))
    assert MAX_DESIGN_POINTS == 10_000_000 and GOLDEN_UNIT_TOL == 1e-12
    for kind in KINDS:
        assert generators.get(kind).name == kind and generators.get(kind).version == "1"


def test_the_registry():
    with pytest.raises(RequestError, match="design generator plane comes in a later version"):
        generators.get("plane")
    with pytest.raises(ValueError, match="uniform"):
        generators.register(generators.get("uniform"))
    with pytest.raises(ValueError, match="plane"):
        generators.unregister("plane")
    # A fixture replacing a registered generator (C51) unregisters it and restores it afterwards (0065 item 1).
    original = generators.get("uniform")
    generators.unregister("uniform")
    try:
        assert "uniform" not in generators.names()
    finally:
        generators.register(original)
    assert generators.get("uniform") is original


@pytest.mark.parametrize("kind", KINDS)
def test_another_generator_version_is_refused_naming_both(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    with pytest.raises(RequestError, match=r"(?s)version 2\b.*version 1\b"):
        generators.get(kind).build(with_identity(ident, generator_version="2"), CONTRACT)
    with pytest.raises(RequestError, match="is not"):
        generators.get(kind).size(with_identity(ident, generator_version="2"), CONTRACT)


@pytest.mark.parametrize("kind", ["uniform", "convergent"])
def test_another_sampler_version_is_refused_naming_both(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    with pytest.raises(RequestError, match=r"(?s)sampler random version 0\.9.*version 1\b"):
        generators.get(kind).build(with_identity(ident, sampler_version="0.9"), CONTRACT)


@pytest.mark.parametrize("kind", ["point", "lines", "coordinate_lines", "random_lines"])
def test_a_sampler_where_none_is_used_is_refused(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    with pytest.raises(RequestError, match="sampler"):
        generators.get(kind).build(with_identity(ident, sampler="random", sampler_version="1"), CONTRACT)


@pytest.mark.parametrize("kind", KINDS)
def test_another_kind_is_refused(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    other = "uniform" if kind != "uniform" else "point"
    with pytest.raises(RequestError, match=kind):
        generators.get(other).build(ident, CONTRACT)


@pytest.mark.parametrize("kind", [k for k in KINDS if k != "point"])
def test_nothing_varied_is_refused_by_every_generator_but_point(kind):
    """designs.md, Nothing varied (0049)."""
    held = {"a": 1.0, "b": 0.0, "c": 1.0}
    ident = CASES[kind].example(CONTRACT, held)
    with pytest.raises(RequestError, match="varies no model parameter"):
        generators.get(kind).build(ident, CONTRACT)


@pytest.mark.parametrize("kind", KINDS)
def test_block_bounds(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    gen = generators.get(kind)
    n = gen.size(ident, CONTRACT)
    assert len(gen.build(ident, CONTRACT, n, n)) == 0
    for start, stop in ((-1, 2), (2, 1), (0, n + 1)):
        with pytest.raises(RequestError, match="rows"):
            gen.build(ident, CONTRACT, start, stop)


@pytest.mark.parametrize("kind", KINDS)
def test_unknown_parameters_and_reserved_names_are_refused(kind):
    ident = CASES[kind].example(CONTRACT, CONTRACT_SPACE)
    for key in ("bogus", "seed", "sampler"):
        bad = with_identity(ident, params={**ident.canonical()["params"], key: 1})
        with pytest.raises(RequestError, match=key):
            generators.get(kind).build(bad, CONTRACT)


def test_g5_over_the_cap_names_the_size_and_the_cap():
    ident = identity(CONTRACT, "uniform", CONTRACT_SPACE, n=MAX_DESIGN_POINTS + 1)
    with pytest.raises(DesignTooLarge, match=r"10,000,001.*10,000,000"):
        generators.get("uniform").build(ident, CONTRACT)
    assert generators.get("uniform").size(ident, CONTRACT) == MAX_DESIGN_POINTS + 1


def random_space(rng: np.random.Generator) -> dict:
    form: dict = {}
    for name in ("a", "b"):
        lo = float(rng.uniform(-5, 5))
        form[name] = [lo, lo + float(rng.uniform(1e-3, 10))]
    exps = sorted(rng.uniform(-8, 8, size=2))
    form["c"] = {"range": [float(10 ** exps[0]), float(10 ** (exps[1] + 0.5))], "scale": "log"}
    return form


@pytest.mark.parametrize("kind", KINDS)
def test_g2_random_requests_stay_inside(kind):
    rng = np.random.default_rng(12)
    for _ in range(20):
        form = random_space(rng)
        ident = CASES[kind].example(CONTRACT, form)
        if kind == "coordinate_lines":  # the nominal values are outside these ranges: anchor at the middles
            middles = {k: (v[0] + v[1]) / 2 for k, v in form.items() if isinstance(v, list)}
            middles["c"] = float(np.sqrt(form["c"]["range"][0] * form["c"]["range"][1]))
            ident = identity(CONTRACT, kind, form, n=5, anchor=middles)
        design = generators.get(kind).build(ident, CONTRACT)
        space = ModelParameterSpace.parse(ident.space)
        assert np.all(space.contains(CONTRACT, design.points))
        assert np.all(design.points[:, 3] == 0.5)


@pytest.mark.parametrize("spec_space", [(D1, D1_SPACE), (D20, D20_SPACE)], ids=["d1", "d20"])
@pytest.mark.parametrize("kind", KINDS)
def test_d1_and_d20(kind, spec_space):
    """The degenerate cases d = 1 and d = 20 (contracts.md)."""
    spec, space = spec_space
    params = {
        "point": {"repeats": 2},
        "uniform": {"n": 9},
        "convergent": {"n_min": 3, "alpha": "0.5", "level": 1},
        "lines": {"n": 5, "lines": [{"anchor": {}, "direction": {spec.parameters[0].name: 1}}]},
        "coordinate_lines": {"n": 5},
        "random_lines": {"m": 2, "n": 5},
    }[kind]
    gen = generators.get(kind)
    ident = identity(spec, kind, None if kind == "point" else space, **params)
    design = gen.build(ident, spec)
    assert design.points.shape == (gen.size(ident, spec), len(spec.parameters))
    if kind == "coordinate_lines":
        assert len(design) == 5 * len(spec.parameters)
    assert np.all(ModelParameterSpace.parse(ident.space).contains(spec, design.points))


@pytest.mark.parametrize("kind", [k for k in KINDS if k != "point"])
def test_a_log_range_over_twelve_decades(kind):
    """The degenerate case (contracts.md): c over 10^-6 to 10^6, inside, exact ends, and the map back."""
    form = {**CONTRACT_SPACE, "c": {"range": [1e-6, 1e6], "scale": "log"}}
    ident = CASES[kind].example(CONTRACT, form)
    design = generators.get(kind).build(ident, CONTRACT)
    space = ModelParameterSpace.parse(form)
    assert np.all(space.contains(CONTRACT, design.points))
    z = space.to_unit(CONTRACT, design.points)
    assert np.all(np.abs(z) <= 1.0)
    c = design.points[:, 2]
    assert np.array_equal(z[:, 2][c == 1e-6], -np.ones(np.sum(c == 1e-6)))
    assert np.array_equal(z[:, 2][c == 1e6], np.ones(np.sum(c == 1e6)))
    if kind == "coordinate_lines":
        line = design.lines[2]
        assert line.ends[0][2] == 1e-6 and line.ends[1][2] == 1e6
        assert design.points[line.rows[0] + 2, 2] == 1.0, "the shared anchor: the nominal value, exactly"
