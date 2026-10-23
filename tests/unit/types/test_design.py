"""A design's identity, its lines, the design, and its structure (architecture.md §3, design.py; 0046, 0063)."""

from types import MappingProxyType

import numpy as np
import pytest

from ema.types.design import Design, DesignIdentity, DesignStructure, Line
from ema.types.identity import canonical_json


def make_identity(**kw):
    fields = {
        "model_version_id": "ab" * 32,
        "kind": "lines",
        "space": {"a": {"range": [0.0, 1.0], "scale": "linear"}},
        "params": {"lines": [{"anchor": {"a": 0.5}, "direction": {"a": 1}}], "n": 5},
        "seed": 0,
        "sampler": None,
        "sampler_version": None,
        "generator_version": "1",
    }
    fields.update(kw)
    return DesignIdentity(**fields)


def test_identity_canonical_holds_every_field():
    ident = make_identity()
    assert ident.canonical() == {
        "model_version_id": "ab" * 32,
        "kind": "lines",
        "space": {"a": {"range": [0.0, 1.0], "scale": "linear"}},
        "params": {"lines": [{"anchor": {"a": 0.5}, "direction": {"a": 1}}], "n": 5},
        "seed": 0,
        "sampler": None,
        "sampler_version": None,
        "generator_version": "1",
    }
    assert canonical_json(ident.canonical()) == canonical_json(make_identity().canonical())


def test_identity_is_read_only_all_the_way_down():
    params = {"lines": [{"anchor": {"a": 0.5}, "direction": {"a": 1}}], "n": 5}
    ident = make_identity(params=params)
    params["n"] = 7
    params["lines"][0]["anchor"]["a"] = 0.9
    assert ident.params["n"] == 5 and ident.canonical()["params"]["lines"][0]["anchor"]["a"] == 0.5
    assert isinstance(ident.space, MappingProxyType) and isinstance(ident.params, MappingProxyType)
    with pytest.raises(TypeError):
        ident.params["n"] = 9  # type: ignore[index]
    with pytest.raises(TypeError):
        ident.params["lines"][0]["anchor"]["a"] = 0.1  # type: ignore[index]


def test_identities_compare_by_value():
    assert make_identity() == make_identity()
    assert make_identity(seed=1) != make_identity()


def test_line_holds_tuples_of_doubles():
    line = Line(anchor=[0, 1], direction=[1], ends=([0, 1], [2, 1]), rows=(0, 5))
    assert line.anchor == (0.0, 1.0) and type(line.anchor[0]) is float
    assert line.ends == ((0.0, 1.0), (2.0, 1.0)) and line.direction == (1.0,)
    assert line == Line(anchor=(0.0, 1.0), direction=(1.0,), ends=((0.0, 1.0), (2.0, 1.0)), rows=(0, 5))


def test_design_arrays_are_read_only_and_len_counts_rows():
    design = Design(
        identity=None, points=np.zeros((3, 2)), replicates=np.zeros(3, dtype=np.int64), levels=None, lines=None
    )
    assert len(design) == 3
    with pytest.raises(ValueError):
        design.points[0, 0] = 1.0
    with pytest.raises(ValueError):
        design.replicates[0] = 1


def test_design_refuses_mismatched_rows():
    with pytest.raises(ValueError):
        Design(identity=None, points=np.zeros((3, 2)), replicates=np.zeros(2, dtype=np.int64), levels=None, lines=None)


def test_design_structure():
    line = Line(anchor=(0.0,), direction=(1.0,), ends=((0.0,), (1.0,)), rows=(0, 3))
    s = DesignStructure(levels=(2, 4), lines=(line,))
    assert s.levels == (2, 4) and s.lines == (line,)
    assert DesignStructure(levels=None, lines=None) == DesignStructure(levels=None, lines=None)
