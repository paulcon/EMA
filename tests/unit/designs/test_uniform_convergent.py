"""Uniform and convergent designs (designs.md, Generators, Convergent, Samplers; G1, G7, G8, G17, G18)."""

import numpy as np
import pytest

from ema.designs import generators
from ema.types.errors import RequestError
from tests.support.designs import CONTRACT, CONTRACT_SPACE, D20, D20_SPACE, identity, with_identity
from tests.support.fakes import FAKE_NESTED, FAKE_NOT_NESTED, FAKE_RATE_TWO_THIRDS, registered

UNIFORM = generators.get("uniform")
CONVERGENT = generators.get("convergent")
LINEAR = {"a": [0, 2], "b": [-1, 1]}


def test_g1_uniform_same_request_same_points_and_seeds_differ():
    ident = identity(CONTRACT, "uniform", CONTRACT_SPACE, n=20, seed=1)
    assert np.array_equal(UNIFORM.build(ident, CONTRACT).points, UNIFORM.build(ident, CONTRACT).points)
    other = UNIFORM.build(identity(CONTRACT, "uniform", CONTRACT_SPACE, n=20, seed=2), CONTRACT)
    assert not np.array_equal(UNIFORM.build(ident, CONTRACT).points, other.points)


def test_uniform_linear_points_are_lo_plus_width_times_u():
    """designs.md, Determinism: points in linear ranges are lo + (hi - lo) u, bit for bit."""
    design = UNIFORM.build(identity(CONTRACT, "uniform", LINEAR, n=30, seed=4), CONTRACT)
    u = np.random.default_rng(4).random((30, 2))
    assert np.array_equal(design.points[:, 0], 0.0 + (2.0 - 0.0) * u[:, 0])
    assert np.array_equal(design.points[:, 1], -1.0 + (1.0 - -1.0) * u[:, 1])
    assert np.all(design.points[:, 2] == 1.0) and np.all(design.points[:, 3] == 0.5)
    assert design.replicates.tolist() == [0] * 30


@pytest.mark.parametrize(
    ("n_min", "alpha", "level", "sizes"),
    [
        (18, "0.7072", 3, (18, 36, 72, 144)),
        (18, 0.7072, 3, (18, 36, 72, 144)),
        (18, "0.7072", 6, (18, 36, 72, 144, 288, 576, 1151)),
        (18, "0.7071", 3, (18, 37, 73, 145)),
        (18, "0.70710678", 3, (18, 37, 73, 145)),
        (18, "0.5", 2, (18, 72, 288)),
        (18, "0.9", 0, (18,)),
    ],
)
def test_g7_sizes_in_exact_arithmetic_and_the_points_are_uniforms(n_min, alpha, level, sizes):
    ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=n_min, alpha=alpha, level=level, seed=3)
    design = CONVERGENT.build(ident, CONTRACT)
    assert design.levels == sizes and len(design) == sizes[-1] == CONVERGENT.size(ident, CONTRACT)
    whole = UNIFORM.build(identity(CONTRACT, "uniform", CONTRACT_SPACE, n=sizes[-1], seed=3), CONTRACT)
    assert np.array_equal(design.points, whole.points)


@pytest.mark.parametrize(
    ("params", "named"),
    [
        ({"n_min": 18, "alpha": "1", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "0", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "1.5", "level": 2}, "alpha"),
        ({"n_min": 2, "alpha": "0.95", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": "abc", "level": 2}, "alpha"),
        ({"n_min": 18, "alpha": True, "level": 2}, "alpha"),
        ({"n_min": 0, "alpha": "0.5", "level": 2}, "n_min"),
        ({"n_min": 18, "alpha": "0.5", "level": -1}, "level"),
        ({"n_min": 18, "alpha": "0.5"}, "level"),
    ],
)
def test_g8_g18_convergent_refusals(params, named):
    with pytest.raises(RequestError, match=named):
        CONVERGENT.build(identity(CONTRACT, "convergent", CONTRACT_SPACE, **params), CONTRACT)


def test_g17_a_sampler_other_than_random_comes_later():
    for gen, params in ((UNIFORM, {"n": 5}), (CONVERGENT, {"n_min": 2, "alpha": "0.5", "level": 1})):
        ident = identity(CONTRACT, gen.name, CONTRACT_SPACE, sampler="sobol", sampler_version="1", **params)
        with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
            gen.build(ident, CONTRACT)


def test_g17_a_registered_sampler_works_with_uniform_and_convergent_refuses_one_not_nested():
    with registered(FAKE_NESTED), registered(FAKE_NOT_NESTED):
        for fake in (FAKE_NESTED, FAKE_NOT_NESTED):
            ident = identity(CONTRACT, "uniform", LINEAR, n=6, sampler=fake.name, seed=2)
            u = fake.unit_rows(2, 2, 0, 6)
            assert np.array_equal(UNIFORM.build(ident, CONTRACT).points[:, 0], 0.0 + 2.0 * u[:, 0])
        nested = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_nested")
        assert CONVERGENT.build(nested, CONTRACT).levels == (2, 8)
        not_nested = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_not_nested")
        with pytest.raises(RequestError, match="fake_not_nested"):
            CONVERGENT.build(not_nested, CONTRACT)


def test_g18_a_sampler_whose_one_over_r_isnt_an_integer():
    with registered(FAKE_RATE_TWO_THIRDS):
        ident = identity(CONTRACT, "convergent", LINEAR, n_min=2, alpha="0.5", level=1, sampler="fake_two_thirds")
        with pytest.raises(RequestError, match="fake_two_thirds"):
            CONVERGENT.build(ident, CONTRACT)


def test_uniform_and_convergent_need_a_sampler():
    ident = identity(CONTRACT, "uniform", LINEAR, n=3)
    with pytest.raises(RequestError, match="sampler"):
        UNIFORM.build(with_identity(ident, sampler=None, sampler_version=None), CONTRACT)


def test_d20():
    design = UNIFORM.build(identity(D20, "uniform", D20_SPACE, n=100), D20)
    assert design.points.shape == (100, 20) and np.all(np.abs(design.points) <= 1.0)


def test_g5_convergent_far_over_the_cap_is_refused_quickly():
    from ema.types.errors import DesignTooLarge

    for alpha, level in (("1e-300", 3), ("0.5", 10**9)):
        ident = identity(CONTRACT, "convergent", CONTRACT_SPACE, n_min=2, alpha=alpha, level=level)
        with pytest.raises(DesignTooLarge):
            CONVERGENT.build(ident, CONTRACT)
