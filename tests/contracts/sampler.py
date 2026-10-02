"""The sampler contract: C28 (contracts.md), over ``random``, a fake nested sampler, and a fake that isn't nested.

The fakes are registered by the fixture through the samplers' own ``register`` and removed with ``unregister``
(0065 item 1; no monkeypatching). Two broken toys, each failing ``check_sampler``: one declares nested and isn't,
and one leaves its version out of the hash. ``test_every_check_fails_on_its_broken_toy`` is the meta-test.
"""

from __future__ import annotations

import inspect
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import numpy as np
import pytest

from ema.designs import generators, samplers
from ema.types.errors import RequestError
from tests.support.designs import CONTRACT, CONTRACT_SPACE, identity, with_identity
from tests.support.fakes import FAKE_NESTED, FAKE_NOT_NESTED, FakeSampler, registered


def check_sampler(sampler: Any) -> None:
    """C28: rows in [0, 1)^d, the same for the same seed; a block made alone equals those rows of the whole; the
    declarations (name and version in the identity's hash, r, nested, balanced sizes); a nested sampler's n rows
    are the first n of any larger request. The sampler is registered (the fixture, or the meta-test)."""
    assert isinstance(sampler.name, str) and sampler.name
    assert isinstance(sampler.version, str) and sampler.version, "no version to hash with the request"
    assert isinstance(sampler.rate, Fraction) and sampler.rate > 0
    assert isinstance(sampler.nested, bool)
    assert sampler.balanced_sizes in ("any", "powers_of_2")

    # What EMA hashes: the design's identity, as the workspace builds it from the registry, holds the sampler's
    # name and version (0046), and a generator refuses an identity of another version, so changing either
    # changes the identity of every design built with it (0062).
    ident = identity(CONTRACT, "uniform", CONTRACT_SPACE, n=4, sampler=sampler.name)
    fields = ident.canonical()
    assert (fields["sampler"], fields["sampler_version"]) == (sampler.name, sampler.version), "not in the hash"
    uniform = generators.get("uniform")
    assert len(uniform.build(ident, CONTRACT)) == 4
    try:
        uniform.build(with_identity(ident, sampler_version=sampler.version + ".other"), CONTRACT)
    except RequestError as error:
        assert sampler.version + ".other" in str(error), "the refusal doesn't name the version"
    else:
        raise AssertionError("an identity of another sampler version was built")

    for seed, d in ((0, 1), (3, 4), (20261001, 20)):
        rows = sampler.unit_rows(seed, d, 0, 64)
        assert rows.shape == (64, d) and rows.dtype == np.float64
        assert np.all((rows >= 0.0) & (rows < 1.0)), "a row outside [0, 1)"
        assert np.array_equal(rows, sampler.unit_rows(seed, d, 0, 64)), "the same seed gave other rows"
        if sampler.nested:
            for n in (1, 10, 63):
                assert np.array_equal(sampler.unit_rows(seed, d, 0, n), rows[:n]), f"declares nested; n = {n} isn't"
        assert np.array_equal(sampler.unit_rows(seed, d, 17, 40), rows[17:40]), "a block differs from the whole"
        assert sampler.unit_rows(seed, d, 5, 5).shape == (0, d)
    assert not np.array_equal(sampler.unit_rows(1, 3, 0, 8), sampler.unit_rows(2, 3, 0, 8))


# --------------------------------------------------------------------------------------------------------------
# Broken toys


@dataclass(frozen=True)
class BrokenNotNested(FakeSampler):
    """Declares nested, and isn't: its rows depend on how many are asked for."""

    def unit_rows(self, seed: int, d: int, start: int, stop: int) -> np.ndarray:
        return super().unit_rows(seed + stop, d, start, stop)


@dataclass(frozen=True)
class BrokenNoVersion(FakeSampler):
    """Leaves its version out of the hash: it declares none."""

    version: str = ""


#: Each check's broken toys, each with the failure it must give (a regular expression).
BROKEN: dict[str, list[tuple[Any, str]]] = {
    "check_sampler": [
        (BrokenNotNested(name="broken_not_nested", nested=True), "declares nested"),
        (BrokenNoVersion(name="broken_no_version", nested=True), "no version to hash"),
    ],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=["random", "fake_nested", "fake_not_nested"])
def sampler(request: pytest.FixtureRequest) -> Iterator[Any]:
    fakes = {"fake_nested": FAKE_NESTED, "fake_not_nested": FAKE_NOT_NESTED}
    if request.param in fakes:
        with registered(fakes[request.param]) as fake:
            yield samplers.get(fake.name)
    else:
        yield samplers.get(request.param)


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken, failure in BROKEN[check]:
        with registered(broken), pytest.raises(AssertionError, match=failure):
            CHECKS[check](broken)


def test_the_fakes_are_unregistered_afterwards() -> None:
    assert samplers.names() == ("random",)
