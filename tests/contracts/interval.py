"""The interval-method contract: C30 (contracts.md), over the bootstrap and a fake method.

What any method promises (uncertainty.md, the interface): the same runs, estimators, and stream give the same
intervals, bit for bit, and another stream other intervals (V1); an estimator marked "distinct runs" receives each
index set's distinct runs, once each, in the design's order (V3); undefined values are dropped and counted (V4);
each estimate gets an interval or "none" with its reason, and the method has a name and settings that
``canonical_json`` writes (P5). The fake (``tests.support.fakes.FakeIntervalMethod``) keeps every promise,
registered by the fixture with ``register`` and removed with ``unregister`` (0065 item 1); each of the four broken
toys differs from it in one way and fails one check (the meta-test).
"""

from __future__ import annotations

import inspect
import math
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from ema.numerics import intervals
from ema.numerics.intervals import Estimator
from ema.types.identity import canonical_json
from ema.types.streams import spawned
from tests.support.fakes import FakeIntervalMethod, registered_interval_method

#: The usable runs: indices in the design's order, not contiguous (runs 1, 4, 7, ... failed).
USABLE = np.array([i for i in range(45) if i % 3 != 1])
VALUES = np.sin(np.arange(45) * 1.7) + np.arange(45) / 45
TAG = 2**32 + 99


def stream(seed: int = 5) -> np.random.Generator:
    return spawned(seed, TAG)


def mean_estimator(name: str = "mean", distinct: bool = False) -> Estimator:
    return Estimator(name, ("mean",), lambda idx: np.array([np.mean(VALUES[idx])]), distinct)


def two_labels() -> Estimator:
    return Estimator(
        "spread", ("lo", "hi"), lambda idx: np.array([np.min(VALUES[idx]), np.max(VALUES[idx])]), distinct=False
    )


class Recorder:
    """An estimator's function that records the index sets it receives."""

    def __init__(self, fn: Callable[[np.ndarray], float] | None = None) -> None:
        self.seen: list[np.ndarray] = []
        self.outputs: list[float] = []
        self.fn = fn or (lambda idx: float(np.mean(VALUES[idx])))

    def __call__(self, idx: np.ndarray) -> np.ndarray:
        self.seen.append(np.array(idx, copy=True))
        value = self.fn(idx)
        self.outputs.append(value)
        return np.array([value])


def run(method: Any, estimators: Sequence[Estimator], seed: int = 5) -> dict[str, tuple[Any, ...]]:
    return method.intervals(USABLE, None, estimators, stream(seed))


def key(result: Mapping[str, tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    return [(name, i.bounds, i.reason, i.undefined) for name, ivs in sorted(result.items()) for i in ivs]


def check_same_stream_same_intervals(method: Any) -> None:
    """C30, V1: the same runs, estimators, and stream give the same intervals, bit for bit; another stream gives
    other intervals."""
    ests = [mean_estimator(), two_labels(), mean_estimator("mean_distinct", distinct=True)]
    first, again = run(method, ests), run(method, ests)
    assert key(first) == key(again), "the same stream gave other intervals"
    other = run(method, ests, seed=6)
    assert key(first) != key(other), "another stream gave the same intervals"


def check_distinct_runs(method: Any) -> None:
    """C30, V3: a "distinct runs" estimator receives each index set's distinct runs, once each, in the design's
    order."""
    drawn, distinct = Recorder(), Recorder()
    run(method, [Estimator("drawn", ("v",), drawn, False), Estimator("distinct", ("v",), distinct, True)])
    assert drawn.seen and len(drawn.seen) == len(distinct.seen)
    assert any(len(np.unique(s)) < len(s) for s in drawn.seen), "the method drew no duplicates to remove"
    for as_drawn, got in zip(drawn.seen, distinct.seen, strict=True):
        assert np.array_equal(got, np.unique(as_drawn)), "not the index set's distinct runs, once each, in order"
        assert np.isin(got, USABLE).all()


def check_undefined_dropped_and_counted(method: Any) -> None:
    """C30, V4: undefined (NaN) values are dropped, and counted per estimate."""
    sometimes = Recorder(lambda idx: math.nan if USABLE[0] in idx else float(np.mean(VALUES[idx])))
    never = Recorder(lambda idx: math.nan)
    result = run(method, [Estimator("sometimes", ("v",), sometimes, False), Estimator("never", ("v",), never, False)])
    nans = sum(math.isnan(v) for v in sometimes.outputs)
    assert 0 < nans < len(sometimes.outputs), "the fixture should be undefined on some index sets only"
    (iv,) = result["sometimes"]
    assert iv.undefined == nans, f"counted {iv.undefined} undefined, {nans} were"
    defined = [v for v in sometimes.outputs if not math.isnan(v)]
    if iv.bounds is not None:
        lo, hi = iv.bounds
        assert math.isfinite(lo) and math.isfinite(hi), "an undefined value was kept"
        assert min(defined) <= lo <= hi <= max(defined)
    (none,) = result["never"]
    assert none.bounds is None and none.undefined == len(never.outputs)


def check_interval_or_none_with_reason(method: Any) -> None:
    """C30: each estimate gets an interval or "none" with its reason; the method has a name and settings."""
    assert isinstance(method.name, str) and method.name
    assert isinstance(method.settings, Mapping) and method.settings
    canonical_json(dict(method.settings))  # JSON values, for the result's provenance (P5; record 0068 item 15)
    never = Estimator("never", ("v",), lambda idx: np.array([math.nan]), False)
    ests = [mean_estimator(), two_labels(), never]
    result = run(method, ests)
    assert set(result) == {e.name for e in ests}
    for e in ests:
        assert len(result[e.name]) == len(e.labels)
        for iv in result[e.name]:
            if iv.bounds is None:
                assert isinstance(iv.reason, str) and iv.reason, "none with no reason"
            else:
                lo, hi = iv.bounds
                assert math.isfinite(lo) and math.isfinite(hi) and lo <= hi and iv.reason is None
            assert isinstance(iv.undefined, int) and iv.undefined >= 0
    assert result["never"][0].bounds is None


# --------------------------------------------------------------------------------------------------------------
# The broken toys: the fake (tests/support/fakes.py), each with one promise broken


class BrokenFixedSeed(FakeIntervalMethod):
    """Ignores the stream it is given, and draws from a fixed seed."""

    def draws(self, stream: np.random.Generator, n: int) -> np.ndarray:
        return spawned(0).integers(0, n, (400, n))


class BrokenDuplicates(FakeIntervalMethod):
    """Passes duplicates to a "distinct runs" estimator."""

    def distinct(self, sample: np.ndarray) -> np.ndarray:
        return sample


@dataclass(frozen=True)
class LooseInterval:
    bounds: tuple[float, float] | None
    reason: str | None
    undefined: int


class BrokenKeepsNaN(FakeIntervalMethod):
    """Keeps NaN values: its range is NaN wherever any resample was undefined, and it counts none."""

    def summarize(self, values: np.ndarray) -> Any:
        return LooseInterval((float(np.min(values)), float(np.max(values))), None, 0)


class BrokenNoReason(FakeIntervalMethod):
    """Gives "none" with no reason."""

    def summarize(self, values: np.ndarray) -> Any:
        iv = super().summarize(values)
        return LooseInterval(iv.bounds, None, iv.undefined) if iv.bounds is None else iv


BROKEN: dict[str, list[Any]] = {
    "check_same_stream_same_intervals": [BrokenFixedSeed()],
    "check_distinct_runs": [BrokenDuplicates()],
    "check_undefined_dropped_and_counted": [BrokenKeepsNaN()],
    "check_interval_or_none_with_reason": [BrokenNoReason()],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=["bootstrap", "fake_range"])
def method(request: pytest.FixtureRequest) -> Iterator[Any]:
    if request.param == "fake_range":
        with registered_interval_method() as fake:
            yield fake
    else:
        yield intervals.get(request.param)


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)


def test_the_toy_keeps_every_promise() -> None:
    for check in CHECKS.values():
        check(FakeIntervalMethod())


def test_the_fake_is_unregistered_afterwards() -> None:
    assert intervals.names() == ("bootstrap",)
