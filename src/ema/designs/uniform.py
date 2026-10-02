"""The uniform design (designs.md, Generators; G4, G17)."""

import numpy as np

from ema.designs._common import check_identity, read_params, rows, sampler_of, space_of
from ema.designs.generators import register
from ema.types._values import as_int
from ema.types.design import Design, DesignIdentity
from ema.types.model import ModelSpec


class Uniform:
    """n points of the identity's sampler, mapped to the space: its parameter is ``n``, an integer >= 1.

    Seeded; with a nested sampler, the first n rows of a larger design are the n-row design. Size: n.
    """

    name: str = "uniform"
    version: str = "1"

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return n (G3)."""
        check_identity(self.name, self.version, identity, uses_sampler=True)
        sampler_of(self.name, identity)
        space_of(self.name, identity, spec)
        return as_int(read_params(self.name, identity.params, ("n",))["n"], "n", 1)

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Build rows [start, stop): the sampler's rows, each mapped to the space (``from_cube``)."""
        n = self.size(identity, spec)
        start, stop = rows(n, start, stop)
        space = space_of(self.name, identity, spec)
        unit = sampler_of(self.name, identity).unit_rows(identity.seed, len(space.varied(spec)), start, stop)
        return Design(
            identity=identity,
            points=space.from_cube(spec, unit),
            replicates=np.zeros(stop - start, dtype=np.int64),
            levels=None,
            lines=None,
        )


register(Uniform())
