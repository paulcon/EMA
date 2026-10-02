"""The checks every generator shares (designs.md, Shared rules; G5, G6, G15, G18; 0049, 0061, 0062, 0065)."""

from collections.abc import Mapping
from typing import Any

import numpy as np

from ema.designs import samplers
from ema.designs.generators import MAX_DESIGN_POINTS
from ema.types._values import as_int
from ema.types.design import DesignIdentity
from ema.types.errors import DesignTooLarge, RequestError
from ema.types.model import ModelSpec
from ema.types.space import ModelParameterSpace


def check_identity(name: str, version: str, identity: DesignIdentity, *, uses_sampler: bool) -> int:
    """Refuse another kind or generator version, a seed that isn't an integer >= 0, or an unused sampler.

    Return the seed as an ``int`` (an integral float, 3.0, is read as 3), for the generator to draw from.
    """
    if identity.kind != name:
        raise RequestError(f"the design's identity is of kind {identity.kind}, not {name}")
    if identity.generator_version != version:
        raise RequestError(
            f"the design's identity is of design generator {name} version "
            f"{identity.generator_version}, which is not this EMA's version {version}"
        )
    seed = as_int(identity.seed, "seed", 0)
    if not uses_sampler and (identity.sampler is not None or identity.sampler_version is not None):
        raise RequestError(f"design generator {name} uses no sampler; the identity names sampler {identity.sampler}")
    return seed


def sampler_of(name: str, identity: DesignIdentity) -> samplers.Sampler:
    """Return the identity's sampler; refuse none, one that comes later, or another version (0062)."""
    if identity.sampler is None:
        raise RequestError(f"design generator {name} needs a sampler; the identity names none")
    sampler = samplers.get(identity.sampler)
    if identity.sampler_version != sampler.version:
        raise RequestError(
            f"the design's identity is of sampler {sampler.name} version {identity.sampler_version}, "
            f"which is not this EMA's version {sampler.version}"
        )
    return sampler


def read_params(
    name: str, params: Mapping[str, Any], required: tuple[str, ...], optional: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the generator's diagnostic parameters, defaults filled in; refuse an unknown or missing one."""
    optional = optional or {}
    for key in params:
        if key in ("seed", "sampler", "sampler_version", "generator_version"):
            raise RequestError(
                f"design generator {name}: {key} is a field of the design's identity, not a diagnostic parameter"
            )
        if key not in required and key not in optional:
            raise RequestError(f"design generator {name}: unknown diagnostic parameter {key}")
    for key in required:
        if key not in params:
            raise RequestError(f"design generator {name}: diagnostic parameter {key} is required")
    return {**optional, **params}


def space_of(name: str, identity: DesignIdentity, spec: ModelSpec) -> ModelParameterSpace:
    """Return the identity's space, parsed and validated (G15, M6); refuse one that varies nothing (0049)."""
    space = ModelParameterSpace.parse(identity.canonical()["space"])
    space.validate(spec)
    if not space.varied(spec):
        raise RequestError(
            f"design generator {name}: the space varies no model parameter; a space that holds "
            "every model parameter is the point design's"
        )
    return space


def rows(size: int, start: int, stop: int | None) -> tuple[int, int]:
    """Refuse a design over the cap, before anything is built (G5), and a block outside the design (G6)."""
    if size > MAX_DESIGN_POINTS:
        raise DesignTooLarge(f"the design has {size:,} points, over the cap of {MAX_DESIGN_POINTS:,}")
    stop = size if stop is None else stop
    integers = all(isinstance(i, (int, np.integer)) and not isinstance(i, (bool, np.bool_)) for i in (start, stop))
    if not (integers and 0 <= start <= stop <= size):
        raise RequestError(f"rows [{start!r}, {stop!r}) are not rows of the design's {size}")
    return int(start), int(stop)
