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

from ema.designs import samplers
from ema.types.identity import canonical_json, sha256_hex
from tests.support.designs import CONTRACT, CONTRACT_SPACE, identity
from tests.support.fakes import FAKE_NESTED, FAKE_NOT_NESTED, FakeSampler, registered


def identity_hash(sampler: Any) -> str:
    """The hash of a uniform design's identity that uses this sampler (0046): its name and version are in it."""
    ident = identity(CONTRACT, "uniform", CONTRACT_SPACE, n=4, sampler=None, sampler_version=None)
    fields = dict(ident.canonical())
    fields["sampler"], fields["sampler_version"] = sampler.name, sampler.version
    return sha256_hex(canonical_json(fields))


def check_sampler(sampler: Any) -> None:
    """C28: rows in [0, 1)^d, the same for the same seed; a block made alone equals those rows of the whole; the
    declarations (name and version in the identity's hash, r, nested, balanced sizes); a nested sampler's n rows
    are the first n of any larger request."""
    assert isinstance(sampler.name, str) and sampler.name
    assert isinstance(sampler.version, str) and sampler.version, "no version to hash with the request"
    assert isinstance(sampler.rate, Fraction) and sampler.rate > 0
    assert isinstance(sampler.nested, bool)
    assert sampler.balanced_sizes in ("any", "powers_of_2")

    renamed = FakeSampler(name=sampler.name + "_other", nested=sampler.nested, version=sampler.version)
    reversioned = FakeSampler(name=sampler.name, nested=sampler.nested, version=sampler.version + ".1")
    assert len({identity_hash(sampler), identity_hash(renamed), identity_hash(reversioned)}) == 3

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


BROKEN: dict[str, list[Any]] = {
    "check_sampler": [
        BrokenNotNested(name="broken_not_nested", nested=True),
        BrokenNoVersion(name="broken_no_version", nested=True),
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
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)


def test_the_fakes_are_unregistered_afterwards() -> None:
    assert samplers.names() == ("random",)
