"""Variability intervals: the interval-method interface and the bootstrap (uncertainty.md; 0004, 0040, 0041; C30).

The interval method is one of the four seams (architecture.md §4): a registry (``register``, ``get``, ``names``,
``unregister``; 0065), its v2.0 implementation ``bootstrap``, and a fake registered in the tests. A method takes
the usable runs (indices in the design's order, with their levels when the design has them), the estimators, and
the diagnostic's spawned stream; it doesn't read the store, make runs, or know which diagnostic calls it.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from ema.types.errors import RequestError

#: Resamples per bootstrap (uncertainty.md, Named constants).
BOOTSTRAP_RESAMPLES = 1000
#: The interval's ends: numpy's linear-interpolation percentiles.
BOOTSTRAP_PERCENTILES = (0.5, 99.5)
#: The fewest defined resamples an interval is made from; below it, "none" and the reason.
BOOTSTRAP_MIN_DEFINED = 201


@dataclass(frozen=True)
class Estimator:
    """One computation per resample, giving one or more estimates.

    A fit's coefficients, R², and residual come from one refit, not one refit per number.

    Attributes
    ----------
    name : str
        The key of its intervals in the method's result.
    labels : tuple of str
        The estimates it gives, in order.
    fn : callable
        Run indices -> ``(len(labels),)`` values; NaN (or any non-finite value) where undefined.
    distinct : bool
        "Distinct runs": it receives each index set's distinct runs, once each, in the design's order (V3).
    """

    name: str
    labels: tuple[str, ...]
    fn: Callable[[np.ndarray], np.ndarray]
    distinct: bool


@dataclass(frozen=True)
class Interval:
    """One estimate's variability interval, or "none" with the reason (0041).

    Attributes
    ----------
    bounds : tuple of float, or None
        (lo, hi), finite, lo <= hi; None for "none".
    reason : str or None
        Why there is no interval, when ``bounds`` is None ("3 of 1000 resamples defined, fewer than 201"); the
        report writes it after "none: ".
    undefined : int
        The resamples on which the estimate was undefined, dropped (V4).
    """

    bounds: tuple[float, float] | None
    reason: str | None
    undefined: int

    def __post_init__(self) -> None:
        if (self.bounds is None and not self.reason) or (self.bounds is not None and self.reason is not None):
            raise ValueError("an interval has bounds and no reason, or no bounds and a reason")
        if self.bounds is not None:
            lo, hi = self.bounds
            if not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
                raise ValueError(f"bounds must be finite with lo <= hi, not {self.bounds}")
        if self.undefined < 0:
            raise ValueError(f"a count of undefined resamples can't be negative: {self.undefined}")


class IntervalMethod(Protocol):
    """What a diagnostic reads from an interval method (uncertainty.md, The interval-method interface; C30).

    Attributes
    ----------
    name : str
        Named under each table and in the result.
    """

    name: str

    @property
    def settings(self) -> Mapping[str, Any]:
        """Return its settings, named under each table and in the result.

        JSON values, so that ``canonical_json(dict(method.settings))`` writes them (P5; record 0068 item 15).
        """
        ...

    def intervals(
        self,
        usable: np.ndarray,
        levels: np.ndarray | None,
        estimators: Sequence[Estimator],
        stream: np.random.Generator,
        on_step: Callable[[int, int], None] | None = None,
    ) -> dict[str, tuple[Interval, ...]]:
        """Return each estimator's intervals, one per label; ``on_step(done, total)`` reports progress."""
        ...


_REGISTRY: dict[str, IntervalMethod] = {}


def register(method: IntervalMethod) -> None:
    """Add an interval method to the registry.

    Raises
    ------
    ValueError
        When its name is taken.
    """
    if method.name in _REGISTRY:
        raise ValueError(f"interval method {method.name} is already registered")
    _REGISTRY[method.name] = method


def unregister(name: str) -> None:
    """Remove an interval method from the registry (0065 item 1): for the tests, and a later plugin mechanism.

    Raises
    ------
    ValueError
        When no interval method has that name.
    """
    if name not in _REGISTRY:
        raise ValueError(f"no interval method {name} is registered")
    del _REGISTRY[name]


def get(name: str) -> IntervalMethod:
    """Return the interval method named ``name``.

    Raises
    ------
    RequestError
        "interval method X comes in a later version", for a name with no implementation.
    """
    if name not in _REGISTRY:
        raise RequestError(f"interval method {name} comes in a later version")
    return _REGISTRY[name]


def names() -> tuple[str, ...]:
    """Return the registered interval methods' names, sorted."""
    return tuple(sorted(_REGISTRY))


class Bootstrap:
    """The bootstrap over the usable runs (uncertainty.md, The bootstrap, steps 1-5; V1-V6).

    1. ``stream.integers(0, n_u, (1000, n_u))``, drawn a row at a time: each row is a resample's positions among
       the usable runs; every estimator gets the same resamples (V2).
    2. An estimator is called on each resample as drawn, duplicates included, or, when it is marked "distinct
       runs", on the resample's distinct runs, once each, in the design's order (V3).
    3. A non-finite value is undefined: dropped for that estimate, and counted (V4).
    4. The interval is numpy's linear-interpolation percentiles (0.5, 99.5) of the defined values (V5); "none"
       with fewer than 201 defined (V6).
    5. Reported as computed: not recentered, shifted, or clipped.

    The levels are not used: the bootstrap resamples level L's usable runs, which the caller passes.
    """

    name: str = "bootstrap"

    @property
    def settings(self) -> dict[str, Any]:
        """Return the constants named under each table: resamples, percentiles, and the fewest defined.

        A fresh plain dict of JSON values on each call (the percentiles a list), so a caller can't change the
        method's, ``ema.types.identity.canonical_json`` writes it as it is, and a stored copy reads back equal
        (record 0068 item 15).

        Examples
        --------
        >>> Bootstrap().settings
        {'resamples': 1000, 'percentiles': [0.5, 99.5], 'min_defined': 201}
        """
        return {
            "resamples": BOOTSTRAP_RESAMPLES,
            "percentiles": list(BOOTSTRAP_PERCENTILES),
            "min_defined": BOOTSTRAP_MIN_DEFINED,
        }

    def intervals(
        self,
        usable: np.ndarray,
        levels: np.ndarray | None,
        estimators: Sequence[Estimator],
        stream: np.random.Generator,
        on_step: Callable[[int, int], None] | None = None,
    ) -> dict[str, tuple[Interval, ...]]:
        """Return each estimator's intervals, one per label, from 1000 resamples of the usable runs.

        Parameters
        ----------
        usable
            The usable runs' indices, in the design's order.
        levels
            Each usable run's level, or None; not used by the bootstrap.
        estimators
            The estimators; their names must differ.
        stream
            The diagnostic's spawned stream (``spawned(seed, tag)``).
        on_step
            Called as ``on_step(done, 1000)`` after each resample; an exception from it stops the method.

        Raises
        ------
        ValueError
            When an estimator gives a number of values other than its labels', or two share a name.
        """
        usable = np.asarray(usable)
        if len({e.name for e in estimators}) != len(estimators):
            raise ValueError("two estimators share a name")
        values = {e.name: np.empty((BOOTSTRAP_RESAMPLES, len(e.labels))) for e in estimators}
        for b in range(BOOTSTRAP_RESAMPLES):
            # Row b of integers(0, n_u, (1000, n_u)), drawn alone: the same numbers (a test checks), 1/1000 the memory.
            positions = stream.integers(0, len(usable), len(usable))
            drawn = usable[positions]
            distinct = usable[np.unique(positions)] if any(e.distinct for e in estimators) else drawn
            for e in estimators:
                out = np.asarray(e.fn(distinct if e.distinct else drawn), dtype=np.float64)
                if out.shape != (len(e.labels),):
                    raise ValueError(f"estimator {e.name} gave shape {out.shape}, not ({len(e.labels)},)")
                values[e.name][b] = out
            if on_step is not None:
                on_step(b + 1, BOOTSTRAP_RESAMPLES)
        return {e.name: tuple(_interval(values[e.name][:, j]) for j in range(len(e.labels))) for e in estimators}


def _interval(values: np.ndarray) -> Interval:
    """Apply steps 3-5 and the "none" rule to one estimate's resampled values."""
    defined = values[np.isfinite(values)]
    undefined = len(values) - len(defined)
    if len(defined) < BOOTSTRAP_MIN_DEFINED:
        reason = f"{len(defined)} of {len(values)} resamples defined, fewer than {BOOTSTRAP_MIN_DEFINED}"
        return Interval(None, reason, undefined)
    lo, hi = np.percentile(defined, BOOTSTRAP_PERCENTILES)
    return Interval((float(lo), float(hi)), None, undefined)


register(Bootstrap())
