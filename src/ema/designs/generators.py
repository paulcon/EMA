"""Design generators: the interface, the registry, and the cap (designs.md, Shared rules; C20-C27).

A generator is stateless (0061): ``size(identity, spec)`` and ``build(identity, spec, start, stop)``, and
everything it needs is in the design's identity. An identity of another generator or sampler version is refused,
naming both (``RequestError``; 0061, 0062). The six generators register themselves when ``ema.designs`` is
imported.
"""

from typing import Protocol

from ema.types.design import Design, DesignIdentity
from ema.types.errors import RequestError
from ema.types.model import ModelSpec

#: The largest design built: more points are refused before building (G5).
MAX_DESIGN_POINTS = 10_000_000
#: Golden points across machines are compared in unit coordinates within this, absolute (G1, 0062).
GOLDEN_UNIT_TOL = 1e-12


class DesignGenerator(Protocol):
    """What every design generator does (designs.md, Generators; C20-C27).

    Attributes
    ----------
    name : str
        Its kind: the identity's ``kind``.
    version : str
        Its version: the identity's ``generator_version``.
    """

    name: str
    version: str

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return the design's number of rows, in closed form, from the identity alone (G3)."""
        ...

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop) of the design, refused over the cap before anything is built (G5, G6)."""
        ...


_REGISTRY: dict[str, DesignGenerator] = {}


def register(generator: DesignGenerator) -> None:
    """Add a design generator to the registry.

    Raises
    ------
    ValueError
        When its name is taken.
    """
    if generator.name in _REGISTRY:
        raise ValueError(f"design generator {generator.name} is already registered")
    _REGISTRY[generator.name] = generator


def unregister(name: str) -> None:
    """Remove a design generator from the registry (0065 item 1): for the tests, and a later plugin mechanism.

    Raises
    ------
    ValueError
        When no generator has that name.
    """
    if name not in _REGISTRY:
        raise ValueError(f"no design generator {name} is registered")
    del _REGISTRY[name]


def get(name: str) -> DesignGenerator:
    """Return the design generator of kind ``name``.

    Raises
    ------
    RequestError
        "design generator X comes in a later version", for a kind with no implementation.
    """
    if name not in _REGISTRY:
        raise RequestError(f"design generator {name} comes in a later version")
    return _REGISTRY[name]


def names() -> tuple[str, ...]:
    """Return the registered generators' names, sorted."""
    return tuple(sorted(_REGISTRY))
