"""The ``random`` sampler and the samplers' registry (designs.md, Samplers; G17; 0032, 0065)."""

from fractions import Fraction

import numpy as np
import pytest

from ema.designs import samplers
from ema.types.errors import RequestError
from tests.support.fakes import FAKE_NESTED, registered


@pytest.mark.parametrize(("seed", "d", "n"), [(0, 1, 10), (1, 3, 50), (20261001, 20, 7), (2**63, 4, 33)])
def test_random_is_numpys_generator_random_bit_for_bit(seed, d, n):
    """An independent construction: numpy's ``Generator.random`` today (designs.md, Samplers)."""
    expected = np.random.default_rng(seed).random((n, d))
    rows = samplers.get("random").unit_rows(seed, d, 0, n)
    assert rows.dtype == np.float64 and np.array_equal(rows, expected)


def test_random_reaches_row_i_without_the_rows_before():
    expected = np.random.default_rng(5).random((1000, 3))
    assert np.array_equal(samplers.get("random").unit_rows(5, 3, 997, 1000), expected[997:])


def test_random_declarations():
    r = samplers.get("random")
    assert (r.name, r.version, r.nested, r.balanced_sizes, r.rate) == ("random", "1", True, "any", Fraction(1, 2))


@pytest.mark.parametrize("bad", [-1, True, 1.5, None])
def test_random_refuses_a_bad_seed(bad):
    with pytest.raises(RequestError, match="seed"):
        samplers.get("random").unit_rows(bad, 2, 0, 3)


def test_registry():
    assert samplers.names() == ("random",)
    with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
        samplers.get("sobol")
    with pytest.raises(ValueError, match="random"):
        samplers.register(samplers.get("random"))
    with pytest.raises(ValueError, match="fake_nested"):
        samplers.unregister("fake_nested")
    with registered(FAKE_NESTED):
        assert samplers.names() == ("fake_nested", "random")
        assert samplers.get("fake_nested") is FAKE_NESTED
    assert samplers.names() == ("random",)
