"""Fake samplers, registered in the tests through the samplers' own registry (designs.md, Samplers; G17, C28).

No monkeypatching: a fixture registers a fake with ``register`` and removes it with ``unregister`` (0065).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

import numpy as np

from ema.designs import samplers
from ema.types.streams import spawned


@dataclass(frozen=True)
class FakeSampler:
    """A sampler whose row i comes from its own stream (spawn key i), so it is nested and makes blocks alone.

    It declares ``nested`` as it is told: the non-nested fake makes the same rows, and only says it isn't
    nested, which is all convergent's refusal reads (G8, G17).
    """

    name: str
    nested: bool
    version: str = "1"
    balanced_sizes: Literal["any", "powers_of_2"] = "any"
    rate: Fraction = field(default=Fraction(1, 2))

    def unit_rows(self, seed: int, d: int, start: int, stop: int) -> np.ndarray:
        rows = [spawned(seed, 7, i).random(d) for i in range(start, stop)]
        return np.array(rows, dtype=np.float64).reshape(stop - start, d)


FAKE_NESTED = FakeSampler(name="fake_nested", nested=True)
FAKE_NOT_NESTED = FakeSampler(name="fake_not_nested", nested=False)
FAKE_RATE_TWO_THIRDS = FakeSampler(name="fake_two_thirds", nested=True, rate=Fraction(2, 3))


@contextmanager
def registered(sampler: FakeSampler) -> Iterator[FakeSampler]:
    """Register a fake sampler for the duration of a ``with`` block, then unregister it (0065 item 1)."""
    samplers.register(sampler)
    try:
        yield sampler
    finally:
        samplers.unregister(sampler.name)
