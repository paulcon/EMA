"""Samplers: points in the unit cube [0, 1)^d for the uniform and convergent designs.

v2.0 plans for several and builds one, ``random`` (designs.md, Samplers; OD-13, 0032, 0033; C28). Generators reach
a sampler only through this interface and its registry; a fake is registered in the tests through the same
``register``, and removed with ``unregister`` (0065).
"""

from fractions import Fraction
from typing import Literal, Protocol

import numpy as np

from ema.types._values import as_int
from ema.types.errors import RequestError


class Sampler(Protocol):
    """What a generator reads from a sampler (designs.md, the sampler interface).

    Attributes
    ----------
    name : str
        Hashed with the request, in the design's identity.
    version : str
        Hashed with the request, in the design's identity.
    nested : bool
        Whether the first n rows of a larger request are the n-row request.
    balanced_sizes : {"any", "powers_of_2"}
        The sizes at which it is balanced.
    rate : fractions.Fraction
        r: an estimate's error from n points is assumed to decrease like n^(-r); the convergent design's sizes
        use it.
    """

    name: str
    version: str
    nested: bool
    balanced_sizes: Literal["any", "powers_of_2"]
    rate: Fraction

    def unit_rows(self, seed: int, d: int, start: int, stop: int) -> np.ndarray:
        """Return rows [start, stop) of the sampler's sequence for this seed, ``(stop - start, d)`` in [0, 1)."""
        ...


_REGISTRY: dict[str, Sampler] = {}


def register(sampler: Sampler) -> None:
    """Add a sampler to the registry.

    Raises
    ------
    ValueError
        When its name is taken.
    """
    if sampler.name in _REGISTRY:
        raise ValueError(f"sampler {sampler.name} is already registered")
    _REGISTRY[sampler.name] = sampler


def unregister(name: str) -> None:
    """Remove a sampler from the registry (0065 item 1): for the tests, and a later plugin mechanism.

    Raises
    ------
    ValueError
        When no sampler has that name.
    """
    if name not in _REGISTRY:
        raise ValueError(f"no sampler {name} is registered")
    del _REGISTRY[name]


def get(name: str) -> Sampler:
    """Return the sampler named ``name``.

    Raises
    ------
    RequestError
        "sampler X comes in a later version", for a name with no implementation (G17).
    """
    if name not in _REGISTRY:
        raise RequestError(f"sampler {name} comes in a later version")
    return _REGISTRY[name]


def names() -> tuple[str, ...]:
    """Return the registered samplers' names, sorted."""
    return tuple(sorted(_REGISTRY))


class Random:
    """The ``random`` sampler (designs.md, Samplers): PCG64 seeded from the request.

    Row i is the raw 64-bit draws i·d to i·d + d - 1, each converted to (x >> 11)·2^-53, the same as numpy's
    ``Generator.random`` today; row i is reached with ``advance(i·d)``, so a block needs no rows before it.
    Nested for every n, balanced at any size, rate 1/2. Its doubles are built from PCG64's raw output, which
    numpy keeps stable (NEP 19), so its rows are the same on every machine (G1, 0062).
    """

    name: str = "random"
    version: str = "1"
    nested: bool = True
    balanced_sizes: Literal["any", "powers_of_2"] = "any"
    rate: Fraction = Fraction(1, 2)

    def unit_rows(self, seed: int, d: int, start: int, stop: int) -> np.ndarray:
        """Return rows [start, stop) for ``seed``, ``(stop - start, d)`` doubles in [0, 1).

        Raises
        ------
        RequestError
            For a seed that isn't an integer >= 0 (G18).
        """
        seed = as_int(seed, "seed", 0)
        bits = np.random.PCG64(seed)
        bits.advance(start * d)
        raw = bits.random_raw((stop - start) * d)
        return ((raw >> np.uint64(11)).astype(np.float64) * 2.0**-53).reshape(stop - start, d)


register(Random())
