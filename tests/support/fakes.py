"""Fakes for the seams, registered in the tests through their own registries: samplers (designs.md, Samplers;
G17, C28) and an interval method (uncertainty.md, the interface; C30, V7).

No monkeypatching: a fixture registers a fake with ``register`` and removes it with ``unregister`` (0065).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Literal

import numpy as np

from ema.designs import samplers
from ema.numerics import intervals
from ema.numerics.intervals import Estimator, Interval
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


class FakeIntervalMethod:
    """An interval method that keeps every promise of C30, registered as ``fake_range`` (V7; record 0068 item 17).

    ``resamples`` (400) resamples with replacement from the stream it is given, the interval the range of the defined
    values, "none" under ``min_defined`` (10) defined; ``on_step(done, resamples)`` after each resample. Its settings
    are a fresh plain dict of JSON values, as the bootstrap's (record 0068 item 15). C30's broken toys subclass it,
    each overriding one step.
    """

    name = "fake_range"
    resamples = 400
    min_defined = 10

    @property
    def settings(self) -> dict[str, Any]:
        return {"resamples": self.resamples, "min_defined": self.min_defined}

    def draws(self, stream: np.random.Generator, n: int) -> np.ndarray:
        return stream.integers(0, n, (self.resamples, n))

    def distinct(self, sample: np.ndarray) -> np.ndarray:
        return np.unique(sample)

    def summarize(self, values: np.ndarray) -> Any:
        defined = values[np.isfinite(values)]
        undefined = len(values) - len(defined)
        if len(defined) < self.min_defined:
            reason = f"{len(defined)} of {self.resamples} resamples defined, fewer than {self.min_defined}"
            return Interval(None, reason, undefined)
        return Interval((float(defined.min()), float(defined.max())), None, undefined)

    def intervals(
        self,
        usable: np.ndarray,
        levels: np.ndarray | None,
        estimators: Sequence[Estimator],
        stream: np.random.Generator,
        on_step: Callable[[int, int], None] | None = None,
    ) -> dict[str, tuple[Any, ...]]:
        draws = self.draws(stream, len(usable))
        values = {e.name: np.empty((len(draws), len(e.labels))) for e in estimators}
        for b, positions in enumerate(draws):
            for e in estimators:
                idx = usable[self.distinct(positions)] if e.distinct else usable[positions]
                values[e.name][b] = e.fn(idx)
            if on_step is not None:
                on_step(b + 1, len(draws))
        return {e.name: tuple(self.summarize(values[e.name][:, j]) for j in range(len(e.labels))) for e in estimators}


class LeanIntervalMethod(FakeIntervalMethod):
    """The fake with 25 resamples and "none" under 5 defined: for the diagnostic contract's checks that don't test
    the intervals themselves (record 0084, Review round 1).

    It still calls the diagnostic's own estimators on resamples drawn from the stream it is given, so the checks of
    a transform (an interval's ends are the min and max of estimates, exact under a·y with a a power of 2), of
    determinism at memory offsets, and of the failures' independence keep their force, at about 1/40 of the
    bootstrap's fits.
    """

    name = "fake_lean"
    resamples = 25
    min_defined = 5


@contextmanager
def registered_interval_method(method: Any = None) -> Iterator[Any]:
    """Register an interval method (the fake by default) for a ``with`` block, then unregister it (0065 item 1)."""
    method = FakeIntervalMethod() if method is None else method
    intervals.register(method)
    try:
        yield intervals.get(method.name)
    finally:
        intervals.unregister(method.name)
