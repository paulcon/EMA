"""Lines: given, coordinate, and random (designs.md, Lines; G10-G14, G18; 0012, 0047, 0051, 0062, 0065).

Shared by the three: a line is straight in unit coordinates, and meets the space in a segment; its n points are
at t_j = j/(n - 1) from one end to the other, both included, t = 0 being the end reached from the anchor against
the direction. An end on a face is exactly that range's end. A coordinate whose direction component is 0 keeps
the anchor's value, bit for bit (0062). Since t_j = j/(n - 1), a line of 2n - 1 points contains the line of n
points, bit for bit (G11). Each line is recorded with its anchor, direction, ends, and rows (0063).
"""

from collections.abc import Mapping
from typing import Any

import numpy as np

from ema.designs._common import check_identity, read_params, rows, space_of
from ema.designs.generators import register
from ema.types._values import as_double, as_int
from ema.types.design import Design, DesignIdentity, Line
from ema.types.errors import RequestError
from ema.types.model import ModelSpec
from ema.types.space import ModelParameterSpace
from ema.types.streams import spawned

#: An anchor whose unit coordinate along a coordinate line is within this of 0 is that line's middle point (G12).
SHARED_ANCHOR_TOL = 1e-12


class _Segment:
    """One line's segment in unit coordinates, and how to make its points."""

    def __init__(
        self,
        space: ModelParameterSpace,
        spec: ModelSpec,
        anchor_x: np.ndarray,
        anchor_z: np.ndarray,
        direction: np.ndarray,
        n: int,
    ) -> None:
        self.space, self.spec, self.anchor_x, self.direction, self.n = space, spec, anchor_x, direction, n
        t0, t1 = space.clip_line(spec, anchor_z, direction)
        if not t0 < t1:
            raise RequestError("the line meets the space at one point only")
        moving = direction != 0.0
        z0 = np.clip(anchor_z + t0 * direction, -1.0, 1.0)
        z1 = np.clip(anchor_z + t1 * direction, -1.0, 1.0)
        a, d = anchor_z[moving], direction[moving]
        t_minus, t_plus = (-1.0 - a) / d, (1.0 - a) / d
        idx = np.flatnonzero(moving)
        # An end on a face is exactly that face (0047): the coordinates whose bound is the segment's end.
        z0[idx[np.minimum(t_minus, t_plus) == t0]] = np.where(d > 0, -1.0, 1.0)[np.minimum(t_minus, t_plus) == t0]
        z1[idx[np.maximum(t_minus, t_plus) == t1]] = np.where(d > 0, 1.0, -1.0)[np.maximum(t_minus, t_plus) == t1]
        self.z0, self.z1, self.moving = z0, z1, moving
        names = [p.name for p in spec.parameters]
        self.fixed = [names.index(v) for v, m in zip(space.varied(spec), moving, strict=True) if not m]

    def points(self, lo: int, hi: int) -> np.ndarray:
        """Points j in [lo, hi) of the line's n."""
        j = np.arange(lo, hi)
        t = j / (self.n - 1)
        Z = self.z0 + t[:, None] * (self.z1 - self.z0)
        Z[j == 0] = self.z0
        Z[j == self.n - 1] = self.z1
        X = self.space.from_unit(self.spec, np.clip(Z, -1.0, 1.0))
        X[:, self.fixed] = self.anchor_x[self.fixed]
        return X

    def ends(self) -> tuple[np.ndarray, np.ndarray]:
        return self.points(0, 1)[0], self.points(self.n - 1, self.n)[0]


def _anchor(space: ModelParameterSpace, spec: ModelSpec, anchor: Any, base: np.ndarray, what: str) -> np.ndarray:
    """Return ``base`` with the anchor's values set: finite numbers, for model parameters, inside the space.

    Refused otherwise, naming the model parameter (G14, G18).
    """
    if not isinstance(anchor, Mapping):
        raise RequestError(f"{what}: an anchor maps model parameters to values, not {anchor!r}")
    names = [p.name for p in spec.parameters]
    x = base.copy()
    for name, value in anchor.items():
        spec.parameter(name)
        x[names.index(name)] = as_double(value, f"{what}: the anchor's model parameter {name}")
    for p, value in zip(spec.parameters, x.tolist(), strict=True):
        r = space.ranges.get(p.name)
        if r is not None and not r.lo <= value <= r.hi:
            raise RequestError(
                f"{what}: the anchor's model parameter {p.name} = {value!r} is outside its range [{r.lo!r}, {r.hi!r}]"
            )
        held = space.held.get(p.name, p.nominal)
        if r is None and value != held:
            raise RequestError(
                f"{what}: the anchor's model parameter {p.name} = {value!r} is outside the space, "
                f"which holds it at {held!r}"
            )
    return x


def _lines(
    segments: list[_Segment],
    records: list[tuple[np.ndarray, np.ndarray]],
    n: int,
    identity: DesignIdentity,
    start: int,
    stop: int | None,
    d: int,
) -> Design:
    start, stop = rows(len(segments) * n, start, stop)
    lines, blocks = [], []
    for k, (segment, (anchor, direction)) in enumerate(zip(segments, records, strict=True)):
        first, last = segment.ends()
        lines.append(
            Line(
                anchor=tuple(anchor.tolist()),
                direction=tuple(direction.tolist()),
                ends=(tuple(first.tolist()), tuple(last.tolist())),
                rows=(k * n, (k + 1) * n),
            )
        )
        lo, hi = max(start, k * n), min(stop, (k + 1) * n)
        if lo < hi:
            blocks.append(segment.points(lo - k * n, hi - k * n))
    points = np.concatenate(blocks) if blocks else np.empty((0, d))
    return Design(
        identity=identity,
        points=points,
        replicates=np.zeros(stop - start, dtype=np.int64),
        levels=None,
        lines=tuple(lines),
    )


class GivenLines:
    """Given lines (``lines``): each an anchor and a direction, with n points.

    Its parameters are ``lines``, a list of ``{"anchor": {...}, "direction": {...}}``, and ``n`` >= 2 points per
    line. Not seeded. Size: (number of lines)·n.

    The anchor is in model parameter units, a partial mapping: unnamed varied model parameters at the range's
    center in unit coordinates (z = 0; the geometric center on a log range), held ones at their held values; it
    must be inside the space. The direction is in unit coordinates, unnamed components 0; nonzero, naming only
    varied model parameters; recorded as given, not normalized (0065).
    """

    name: str = "lines"
    version: str = "1"

    def _read(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[list[_Segment], list[Any], int, int]:
        check_identity(self.name, self.version, identity, uses_sampler=False)
        space = space_of(self.name, identity, spec)
        params = read_params(self.name, identity.canonical()["params"], ("lines", "n"))
        n = as_int(params["n"], "n", 2)
        given = params["lines"]
        if not isinstance(given, list) or not given:
            raise RequestError('lines: at least one line, each {"anchor": {...}, "direction": {...}}')
        varied = space.varied(spec)
        center = space.from_unit(spec, np.zeros((1, len(varied))))[0]
        segments, records = [], []
        for k, line in enumerate(given):
            what = f"lines[{k}]"
            if not isinstance(line, Mapping):
                raise RequestError(f'{what}: a line is {{"anchor": {{...}}, "direction": {{...}}}}, not {line!r}')
            extra = sorted(str(key) for key in line if key not in ("anchor", "direction"))
            if extra:
                raise RequestError(f"{what}: unknown key {extra[0]}; a line has an anchor and a direction")
            if "direction" not in line:
                raise RequestError(f"{what}: a line needs a direction")
            anchor_x = _anchor(space, spec, line.get("anchor", {}), center, what)
            direction = self._direction(space, spec, line["direction"], what)
            anchor_z = space.to_unit(spec, anchor_x[None, :])[0]
            segments.append(_Segment(space, spec, anchor_x, anchor_z, direction, n))
            records.append((anchor_x, direction))
        return segments, records, n, len(spec.parameters)

    @staticmethod
    def _direction(space: ModelParameterSpace, spec: ModelSpec, direction: Any, what: str) -> np.ndarray:
        if not isinstance(direction, Mapping):
            raise RequestError(f"{what}: a direction maps varied model parameters to components, not {direction!r}")
        varied = space.varied(spec)
        vector = np.zeros(len(varied))
        for name, value in direction.items():
            spec.parameter(name)
            if name not in varied:
                raise RequestError(f"{what}: the direction names model parameter {name}, which the space holds")
            vector[varied.index(name)] = as_double(value, f"{what}: the direction's model parameter {name}")
        if not vector.any():
            raise RequestError(f"{what}: the direction is zero")
        return vector

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return (number of lines)·n (G3)."""
        check_identity(self.name, self.version, identity, uses_sampler=False)
        space_of(self.name, identity, spec)
        params = read_params(self.name, identity.canonical()["params"], ("lines", "n"))
        n = as_int(params["n"], "n", 2)
        if not isinstance(params["lines"], list) or not params["lines"]:
            raise RequestError('lines: at least one line, each {"anchor": {...}, "direction": {...}}')
        return len(params["lines"]) * n

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop): each line's n points in turn, lines in the order given."""
        rows(self.size(identity, spec), start, stop)
        segments, records, n, d = self._read(identity, spec)
        return _lines(segments, records, n, identity, start, stop, d)


class CoordinateLines:
    """Coordinate lines: one line per varied model parameter, each over its whole range.

    The lines are in the model spec's order, each from lo to hi, the others at the anchor's values. Its parameters are ``n`` >= 2 and ``anchor`` (a
    partial mapping; unnamed model parameters at their nominal values, held ones at their held values). Not
    seeded. Size: d·n, d varied.

    With n odd, a line along which the anchor's unit coordinate (by the map back) is within
    ``SHARED_ANCHOR_TOL`` of 0 has its middle point set exactly to the anchor, so such lines share the anchor's
    run (G12). An anchor that equals, bit for bit, a point of a line along which it is off center is refused,
    naming the model parameter (0051), as is an anchor outside the space (a nominal value outside its range).
    """

    name: str = "coordinate_lines"
    version: str = "1"

    def _read(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[ModelParameterSpace, np.ndarray, int]:
        check_identity(self.name, self.version, identity, uses_sampler=False)
        space = space_of(self.name, identity, spec)
        params = read_params(self.name, identity.canonical()["params"], ("n",), {"anchor": {}})
        n = as_int(params["n"], "n", 2)
        base = np.array([space.held.get(p.name, p.nominal) for p in spec.parameters])
        return space, _anchor(space, spec, params["anchor"], base, "coordinate_lines"), n

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return d·n (G3)."""
        space, _, n = self._read(identity, spec)
        return len(space.varied(spec)) * n

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop): each varied model parameter's line in turn, in the model spec's order."""
        space, anchor_x, n = self._read(identity, spec)
        varied = space.varied(spec)
        rows(len(varied) * n, start, stop)
        names = [p.name for p in spec.parameters]
        anchor_z = space.to_unit(spec, anchor_x[None, :])[0]
        segments, records = [], []
        for i, name in enumerate(varied):
            direction = np.zeros(len(varied))
            direction[i] = 1.0
            segment = _Segment(space, spec, anchor_x, anchor_z, direction, n)
            column = segment.points(0, n)[:, names.index(name)]
            value = anchor_x[names.index(name)]
            if n % 2 == 1 and abs(anchor_z[i]) <= SHARED_ANCHOR_TOL:
                segment = _SharedAnchor(segment, names.index(name), value)
            elif np.any(column == value):
                raise RequestError(
                    f"coordinate_lines: the anchor's model parameter {name} = {float(value)!r} is a point of "
                    "its coordinate line, off the range's center; give another anchor (0051)"
                )
            segments.append(segment)
            records.append((anchor_x, direction))
        return _lines(segments, records, n, identity, start, stop, len(names))


class _SharedAnchor(_Segment):
    """A coordinate line whose middle point is the anchor, exactly (G12)."""

    def __init__(self, segment: _Segment, column: int, value: float) -> None:
        self.__dict__.update(segment.__dict__)
        self.column, self.value = column, value

    def points(self, lo: int, hi: int) -> np.ndarray:
        X = super().points(lo, hi)
        middle = (self.n - 1) // 2
        if lo <= middle < hi:
            X[middle - lo, self.column] = self.value
        return X


class RandomLines:
    """Random lines: its parameters are ``m`` >= 1 lines and ``n`` >= 2 points per line; seeded. Size: m·n.

    Line j has its own stream, ``spawned(seed, j)`` (P4): its anchor is d draws from it, converted as the
    ``random`` sampler's are, so uniform in the space; its direction is d standard normals from the same stream,
    after the anchor's, divided by their norm (computed elementwise), so uniform on the sphere in unit
    coordinates. So m lines are the first m of m + 1, and line j can be made alone (G13).
    """

    name: str = "random_lines"
    version: str = "1"

    def _read(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[ModelParameterSpace, int, int]:
        check_identity(self.name, self.version, identity, uses_sampler=False)
        space = space_of(self.name, identity, spec)
        params = read_params(self.name, identity.params, ("m", "n"))
        return space, as_int(params["m"], "m", 1), as_int(params["n"], "n", 2)

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """Return m·n (G3)."""
        _, m, n = self._read(identity, spec)
        return m * n

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop): each line's n points in turn, lines j = 0 ... m - 1."""
        space, m, n = self._read(identity, spec)
        rows(m * n, start, stop)
        d = len(space.varied(spec))
        segments, records = [], []
        for j in range(m):
            stream = spawned(identity.seed, j)
            u = stream.random(d)
            v = stream.standard_normal(d)
            direction = v / np.sqrt(np.sum(v * v))
            anchor_x = space.from_cube(spec, u[None, :])[0]
            segments.append(_Segment(space, spec, anchor_x, 2.0 * u - 1.0, direction, n))
            records.append((anchor_x, direction))
        return _lines(segments, records, n, identity, start, stop, len(spec.parameters))


register(GivenLines())
register(CoordinateLines())
register(RandomLines())
