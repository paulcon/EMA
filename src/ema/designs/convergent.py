"""The convergent design (designs.md, Convergent; G7, G8, G18; 0047)."""

import math
from fractions import Fraction
from typing import Any

import numpy as np

from ema.designs._common import check_identity, read_params, rows, sampler_of, space_of
from ema.designs.generators import MAX_DESIGN_POINTS, register
from ema.types._values import as_int
from ema.types.design import Design, DesignIdentity
from ema.types.errors import DesignTooLarge, RequestError
from ema.types.identity import decimal_fraction
from ema.types.model import ModelSpec


def _alpha(value: Any) -> Fraction:
    try:
        alpha = decimal_fraction(value)
    except (ValueError, TypeError, ZeroDivisionError):
        raise RequestError(f"convergent: alpha must be a decimal number in (0, 1), not {value!r}") from None
    if not 0 < alpha < 1:
        raise RequestError(f"convergent: alpha must be in (0, 1), not {value}")
    return alpha


class Convergent:
    """Levels 0 ... L, nested: level l is the first n_l points of one uniform design of n_L points.

    The levels share the seed, space, and sampler. Its parameters are ``n_min`` (an integer >= 1), ``alpha`` (the error factor, in
    (0, 1), read as the decimal it is written as: its decimal string, 0047), and ``level`` (L >= 0).

    The sizes are n_l = ceil(n_min alpha^(-l/r)), each from n_min, in exact rational arithmetic, rounded up with no
    tolerance; r is the sampler's rate, and 1/r must be an integer (0065). Refused: alpha outside (0, 1), sizes
    not strictly increasing, and a sampler that isn't nested (G8).
    """

    name: str = "convergent"
    version: str = "1"

    def levels(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[tuple[int, ...], int]:
        """Return the level sizes n_0 ... n_L, and n_L; the sizes stop at the first one over the cap."""
        check_identity(self.name, self.version, identity, uses_sampler=True)
        sampler = sampler_of(self.name, identity)
        space_of(self.name, identity, spec)
        params = read_params(self.name, identity.params, ("n_min", "alpha", "level"))
        n_min = as_int(params["n_min"], "n_min", 1)
        level = as_int(params["level"], "level", 0)
        alpha = _alpha(params["alpha"])
        if not sampler.nested:
            raise RequestError(f"convergent: sampler {sampler.name} isn't nested, so its levels can't share points")
        k = 1 / Fraction(sampler.rate)
        if k.denominator != 1:
            raise RequestError(
                f"convergent: sampler {sampler.name} has rate r = {sampler.rate}, and 1/r isn't an "
                "integer; its rounding rule comes with its record"
            )
        factor = (1 / alpha) ** int(k)
        # Sizes far over the cap are refused without exact arithmetic on huge numbers (logs of the integers).
        if math.log(n_min) + level * (math.log(factor.numerator) - math.log(factor.denominator)) > 62 * math.log(2):
            raise DesignTooLarge(f"the design has more than 2^62 points, over the cap of {MAX_DESIGN_POINTS:,}")
        sizes: list[int] = []
        scale = Fraction(1)
        for _ in range(level + 1):
            n_l = math.ceil(n_min * scale)
            if sizes and n_l <= sizes[-1]:
                raise RequestError(
                    f"convergent: the sizes {', '.join(map(str, [*sizes, n_l]))} aren't strictly "
                    f"increasing (n_min = {n_min}, alpha = {params['alpha']}); raise n_min or lower "
                    "alpha"
                )
            sizes.append(n_l)
            if n_l > MAX_DESIGN_POINTS:
                return tuple(sizes), math.ceil(n_min * factor**level)
            scale *= factor
        return tuple(sizes), sizes[-1]

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """n_L (G3)."""
        return self.levels(identity, spec)[1]

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop) of the uniform design of n_L points, with the level sizes (G7)."""
        sizes, n = self.levels(identity, spec)
        start, stop = rows(n, start, stop)
        space = space_of(self.name, identity, spec)
        unit = sampler_of(self.name, identity).unit_rows(identity.seed, len(space.varied(spec)), start, stop)
        return Design(
            identity=identity,
            points=space.from_cube(spec, unit),
            replicates=np.zeros(stop - start, dtype=np.int64),
            levels=sizes,
            lines=None,
        )


register(Convergent())
