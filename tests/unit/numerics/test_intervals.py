"""The bootstrap (uncertainty.md, The bootstrap and Rules; V1-V6) and the interval-method registry."""

import json
import math

import numpy as np
import pytest

from ema.numerics import intervals
from ema.numerics.intervals import (
    BOOTSTRAP_MIN_DEFINED,
    BOOTSTRAP_PERCENTILES,
    BOOTSTRAP_RESAMPLES,
    Bootstrap,
    Estimator,
    Interval,
)
from ema.numerics.stats import binned_index, rank_correlation
from ema.types.errors import RequestError
from ema.types.identity import canonical_json
from ema.types.streams import spawned
from tests.support.numerics import r2_unit

TAG = 2**32 + 1  # scatter's tag (scatter.md), for the mock report


class Recorder:
    def __init__(self, fn=None) -> None:
        self.seen: list[np.ndarray] = []
        self.fn = fn or (lambda idx, call: float(len(idx)))

    def __call__(self, idx: np.ndarray) -> np.ndarray:
        self.seen.append(np.array(idx, copy=True))
        return np.array([self.fn(idx, len(self.seen) - 1)])


def test_constants() -> None:
    """uncertainty.md, Named constants."""
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_PERCENTILES, BOOTSTRAP_MIN_DEFINED) == (1000, (0.5, 99.5), 201)
    b = Bootstrap()
    assert b.name == "bootstrap"
    assert b.settings == {"resamples": 1000, "percentiles": [0.5, 99.5], "min_defined": 201}


def test_settings_are_json_and_fresh() -> None:
    """P5; record 0068 item 15: the settings are written by canonical_json as they are, read back equal, and a
    caller's change to them doesn't reach the method."""
    b = Bootstrap()
    text = canonical_json(b.settings)
    assert text == '{"min_defined":201,"percentiles":[0.5,99.5],"resamples":1000}'
    assert json.loads(text) == b.settings
    b.settings["resamples"] = 5
    b.settings["percentiles"].append(1.0)
    assert b.settings == json.loads(text)


@pytest.mark.parametrize("n", [7, 10, 201])
def test_the_resamples_are_the_specs_draws(n: int) -> None:
    """Step 1: integers(0, n_u, (1000, n_u)) from the stream, positions into the usable runs, in order (the
    bootstrap draws a row at a time, record 0068 item 13: the same numbers)."""
    usable = np.arange(n) * 3 + 1
    rec = Recorder()
    Bootstrap().intervals(usable, None, [Estimator("e", ("v",), rec, False)], spawned(4, TAG))
    draws = spawned(4, TAG).integers(0, n, (1000, n))
    assert len(rec.seen) == 1000
    assert all(np.array_equal(got, usable[row]) for got, row in zip(rec.seen, draws, strict=True))


def test_v1_bit_for_bit_and_another_tag() -> None:
    """V1: the same runs and stream give the same intervals, bit for bit; another tag, other intervals."""
    y = np.sin(np.arange(30.0))
    est = [Estimator("mean", ("mean",), lambda idx: np.array([np.mean(y[idx])]), False)]
    usable = np.arange(30)
    a = Bootstrap().intervals(usable, None, est, spawned(0, TAG))
    b = Bootstrap().intervals(usable, None, est, spawned(0, TAG))
    c = Bootstrap().intervals(usable, None, est, spawned(0, TAG + 1))
    assert a == b and a["mean"][0].bounds is not None
    assert a != c


def test_v2_every_estimate_uses_the_same_resamples() -> None:
    """V2: a recording estimator: the index sets it receives are identical across estimates."""
    r1, r2 = Recorder(), Recorder()
    ests = [Estimator("a", ("v",), r1, False), Estimator("b", ("v",), r2, False)]
    Bootstrap().intervals(np.arange(12), None, ests, spawned(1, TAG))
    assert len(r1.seen) == 1000
    assert all(np.array_equal(p, q) for p, q in zip(r1.seen, r2.seen, strict=True))


def test_v3_distinct_runs_once_each_in_the_designs_order() -> None:
    """V3: a "distinct runs" estimator receives each resample's distinct indices, once each, in the design's order."""
    usable = np.array([1, 4, 6, 9, 10, 15])
    drawn, distinct = Recorder(), Recorder()
    ests = [Estimator("drawn", ("v",), drawn, False), Estimator("distinct", ("v",), distinct, True)]
    Bootstrap().intervals(usable, None, ests, spawned(2, TAG))
    assert any(len(np.unique(s)) < 6 for s in drawn.seen)
    for as_drawn, got in zip(drawn.seen, distinct.seen, strict=True):
        assert np.array_equal(got, np.unique(as_drawn))


def test_v4_undefined_dropped_and_counted_per_label() -> None:
    """V4: undefined resamples are dropped per estimate, and counted per label."""

    def fn(idx: np.ndarray) -> np.ndarray:
        return np.array([math.nan if 0 in idx else 1.0, 2.0])

    result = Bootstrap().intervals(np.arange(10), None, [Estimator("e", ("a", "b"), fn, False)], spawned(3, TAG))
    draws = spawned(3, TAG).integers(0, 10, (1000, 10))
    with_zero = int(sum(0 in row for row in draws))
    a, b = result["e"]
    assert a.undefined == with_zero and b.undefined == 0
    assert a.bounds == (1.0, 1.0) and b.bounds == (2.0, 2.0)


def test_v5_linear_interpolation_percentiles() -> None:
    """V5: resampled values 0, 1, ..., 999 give [4.995, 994.005], not recentered or clipped."""
    rec = Recorder(lambda idx, call: float(call))
    result = Bootstrap().intervals(np.arange(5), None, [Estimator("e", ("v",), rec, False)], spawned(0, TAG))
    lo, hi = result["e"][0].bounds  # type: ignore[misc]
    assert lo == pytest.approx(4.995, abs=1e-12) and hi == pytest.approx(994.005, abs=1e-12)


@pytest.mark.parametrize(("defined", "bounded"), [(0, False), (200, False), (201, True)])
def test_v6_none_under_201_defined(defined: int, bounded: bool) -> None:
    """V6: estimators defined on 0, 200, and 201 of the 1000 resamples: none, none, an interval."""
    rec = Recorder(lambda idx, call: float(call) if call < defined else math.nan)
    (iv,) = Bootstrap().intervals(np.arange(5), None, [Estimator("e", ("v",), rec, False)], spawned(0, TAG))["e"]
    assert iv.undefined == 1000 - defined
    if bounded:
        assert iv.bounds is not None and iv.reason is None
    else:
        assert iv.bounds is None
        assert iv.reason == f"{defined} of 1000 resamples defined, fewer than 201"


def test_infinite_values_are_undefined() -> None:
    rec = Recorder(lambda idx, call: math.inf if call % 2 else 1.0)
    (iv,) = Bootstrap().intervals(np.arange(5), None, [Estimator("e", ("v",), rec, False)], spawned(0, TAG))["e"]
    assert iv.undefined == 500 and iv.bounds == (1.0, 1.0)


def test_on_step_and_its_exception_stops() -> None:
    """architecture.md §4: on_step(done, total) for the analysis's progress (PM10); an exception stops it."""
    steps: list[tuple[int, int]] = []
    est = [Estimator("e", ("v",), lambda idx: np.array([1.0]), False)]
    Bootstrap().intervals(np.arange(5), None, est, spawned(0, TAG), on_step=lambda d, t: steps.append((d, t)))
    assert steps[0] == (1, 1000) and steps[-1] == (1000, 1000) and len(steps) == 1000

    class Stop(Exception):
        pass

    def stop(done: int, total: int) -> None:
        if done == 3:
            raise Stop

    with pytest.raises(Stop):
        Bootstrap().intervals(np.arange(5), None, est, spawned(0, TAG), on_step=stop)


def test_estimator_shape_is_checked() -> None:
    est = [Estimator("e", ("a", "b"), lambda idx: np.array([1.0]), False)]
    with pytest.raises(ValueError):
        Bootstrap().intervals(np.arange(5), None, est, spawned(0, TAG))


def test_no_usable_runs_is_refused_plainly() -> None:
    """Record 0068, review round 2: with no usable runs (the precheck's to refuse first), a clear ValueError, not
    1000 resamples of nothing."""
    est = [Estimator("e", ("a",), lambda idx: np.array([1.0]), False)]
    with pytest.raises(ValueError, match="no usable runs|there are none"):
        Bootstrap().intervals(np.arange(0), None, est, spawned(0, TAG))


def test_interval_refuses_inconsistent_fields() -> None:
    with pytest.raises(ValueError):
        Interval(None, None, 0)
    with pytest.raises(ValueError):
        Interval((1.0, 2.0), "a reason", 0)
    with pytest.raises(ValueError):
        Interval((2.0, 1.0), None, 0)
    with pytest.raises(ValueError):
        Interval((math.nan, 1.0), None, 0)
    with pytest.raises(ValueError):
        Interval((1.0, 2.0), None, -1)


def test_registry() -> None:
    """architecture.md §4 (0065): register, get, names, unregister; a later method is refused by name."""
    assert intervals.names() == ("bootstrap",)
    assert isinstance(intervals.get("bootstrap"), Bootstrap)
    with pytest.raises(RequestError, match="interval method subsampling comes in a later version"):
        intervals.get("subsampling")
    with pytest.raises(ValueError):
        intervals.register(Bootstrap())
    with pytest.raises(ValueError):
        intervals.unregister("subsampling")


def test_scatter_mock_report_intervals() -> None:
    """scatter.md, Mock report (R2, n = 200, seed 1): every interval to 4 significant digits, through the
    bootstrap, with the binned index on each resample's distinct runs (docs/checks/scatter.out)."""
    z = 2 * np.random.default_rng(1).random((200, 3)) - 1
    y = r2_unit(z)

    def drawn(idx: np.ndarray) -> np.ndarray:
        yb = y[idx]
        return np.array([np.mean(yb), np.std(yb, ddof=1)] + [rank_correlation(z[idx, j], yb) for j in range(3)])

    def binned(idx: np.ndarray) -> np.ndarray:
        B = math.isqrt(len(idx))
        return np.array([binned_index(z[idx, j], y[idx], B) for j in range(3)])

    ests = [
        Estimator("drawn", ("mean", "sd", "rho0", "rho1", "rho2"), drawn, False),
        Estimator("binned", ("S0", "S1", "S2"), binned, True),
    ]
    result = Bootstrap().intervals(np.arange(200), None, ests, spawned(1, TAG))
    got = [iv.bounds for iv in result["drawn"] + result["binned"]]
    want = [
        (2.906, 4.232),
        (3.275, 4.299),
        (0.2651, 0.5489),
        (-0.1663, 0.1955),
        (-0.2193, 0.1803),
        (0.1888, 0.4248),
        (0.2816, 0.5257),
        (-0.07658, 0.103),
    ]
    assert [(f"{lo:.4g}", f"{hi:.4g}") for lo, hi in got] == [(f"{lo:.4g}", f"{hi:.4g}") for lo, hi in want]
