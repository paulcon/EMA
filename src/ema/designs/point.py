"""The point design (designs.md, Point; G9; 0011, 0049)."""

import numpy as np

from ema.designs._common import check_identity, read_params, rows
from ema.designs.generators import register
from ema.types._values import as_int
from ema.types.design import Design, DesignIdentity
from ema.types.errors import RequestError
from ema.types.identity import canonical_json
from ema.types.model import ModelSpec
from ema.types.space import ModelParameterSpace


class Point:
    """One point, as replicates 0 ... repeats (0011): its parameters are ``x`` and ``repeats``.

    ``x`` maps some model parameters to values (the rest at their nominal values; no ``x`` is the nominal point),
    each inside its limits. The identity's space holds every model parameter at the point (0049). Nested in
    repeats; not seeded. Size: repeats + 1.
    """

    name: str = "point"
    version: str = "1"

    def _read(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[np.ndarray, int]:
        check_identity(self.name, self.version, identity, uses_sampler=False)
        params = read_params(self.name, identity.params, (), {"x": {}, "repeats": 0})
        repeats = as_int(params["repeats"], "repeats", 0)
        space = ModelParameterSpace.at_point(spec, params["x"])
        space.validate(spec)
        given = ModelParameterSpace.parse(identity.canonical()["space"])
        if canonical_json(given.canonical()) != canonical_json(space.canonical()):
            raise RequestError(
                "the point design's space must hold every model parameter at the point: "
                f"{canonical_json(space.canonical())}"
            )
        return space.complete(spec, np.empty((1, 0)))[0], repeats

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return repeats + 1 (G3)."""
        return self._read(identity, spec)[1] + 1

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Build the point, complete, in rows [start, stop), with replicates start ... stop - 1 (G9)."""
        point, repeats = self._read(identity, spec)
        start, stop = rows(repeats + 1, start, stop)
        return Design(
            identity=identity,
            points=np.tile(point, (stop - start, 1)),
            replicates=np.arange(start, stop, dtype=np.int64),
            levels=None,
            lines=None,
        )


register(Point())
