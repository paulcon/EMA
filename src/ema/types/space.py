"""The model parameter space: a hyperrectangle of ranges, and held values (designs.md; 0005, 0023, 0024, 0033).

Generators reach a space only through its membership test, its unit maps, sampling the unit cube, and line
clipping, so a later shape (the hyperellipsoid, 0005) is one new class with the same methods.

The maps (designs.md, Unit coordinates; 0047, 0061, 0062): z in [-1, 1] and u in [0, 1] are related by
z = 2u - 1; a linear range is x = lo + (hi - lo) u, a log range x = exp(ln lo + (ln hi - ln lo) u) clamped to
[lo, hi], with numpy's ``log`` and ``exp``; a point on a face has that coordinate set to lo or hi exactly. The
map back is z = (2x - (lo + hi)) / (hi - lo), the same in ln x on a log range, clamped to [-1, 1], with lo and
hi mapping exactly to -1 and 1.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.types._values import as_double, is_number
from ema.types.errors import RequestError
from ema.types.model import Limits, ModelSpec


class Scale(Enum):
    """How a range is spread: evenly, or evenly in the logarithm (0024)."""

    LINEAR = "linear"
    LOG = "log"


@dataclass(frozen=True)
class Range:
    """A varied model parameter's range.

    Attributes
    ----------
    lo : float
        Its low end, as a double (0061); ``validate`` requires lo < hi, and lo > 0 on a log range.
    hi : float
        Its high end, as a double.
    scale : Scale
        Linear by default.
    """

    lo: float
    hi: float
    scale: Scale = Scale.LINEAR

    def __post_init__(self) -> None:
        object.__setattr__(self, "lo", as_double(self.lo, "range end"))
        object.__setattr__(self, "hi", as_double(self.hi, "range end"))
        if not isinstance(self.scale, Scale):
            try:
                object.__setattr__(self, "scale", Scale(self.scale))
            except ValueError:
                raise RequestError(f"a range's scale is linear or log, not {self.scale!r}") from None

    def _from_u(self, u: np.ndarray) -> np.ndarray:
        if self.scale is Scale.LOG:
            x = np.exp(np.log(self.lo) + (np.log(self.hi) - np.log(self.lo)) * u)
        else:
            x = self.lo + (self.hi - self.lo) * u
        x = np.clip(x, self.lo, self.hi)
        return np.where(u <= 0.0, self.lo, np.where(u >= 1.0, self.hi, x))

    def _to_z(self, x: np.ndarray) -> np.ndarray:
        x = np.clip(x, self.lo, self.hi)
        if self.scale is Scale.LOG:
            ln_lo, ln_hi = np.log(self.lo), np.log(self.hi)
            z = (2.0 * np.log(x) - (ln_lo + ln_hi)) / (ln_hi - ln_lo)
        else:
            z = (2.0 * x - (self.lo + self.hi)) / (self.hi - self.lo)
        z = np.clip(z, -1.0, 1.0)
        return np.where(x == self.lo, -1.0, np.where(x == self.hi, 1.0, z))


def _crossed(limits: Limits, x: float) -> str | None:
    """Return the limit ``x`` fails, as the spec writes it ("gt 0.0"), or None."""
    if limits.lower is not None and not (x > limits.lower if limits.lower_strict else x >= limits.lower):
        return f"{'gt' if limits.lower_strict else 'ge'} {limits.lower!r}"
    if limits.upper is not None and not (x < limits.upper if limits.upper_strict else x <= limits.upper):
        return f"{'lt' if limits.upper_strict else 'le'} {limits.upper!r}"
    return None


def _parse_range(value: Any, scale: Any, what: str) -> Range:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise RequestError(f"{what}: a range is two numbers [lo, hi], not {value!r}")
    lo, hi = (as_double(v, f"{what}: range end") for v in value)
    if isinstance(scale, str):
        if scale not in ("linear", "log"):
            raise RequestError(f"{what}: a range's scale is linear or log, not {scale!r}")
        scale = Scale(scale)
    if not isinstance(scale, Scale):
        raise RequestError(f"{what}: a range's scale is linear or log, not {scale!r}")
    return Range(lo, hi, scale)


@dataclass(frozen=True)
class ModelParameterSpace:
    """The set of model parameter values a design may sample: a hyperrectangle, and held values (0005, 0023).

    Each model parameter it names is varied over a range, or held at a value it gives; each one it leaves out
    is held at its nominal value.

    Attributes
    ----------
    ranges : Mapping[str, Range]
        The varied model parameters; read-only.
    held : Mapping[str, float]
        The held values the space gives; read-only.
    """

    ranges: Mapping[str, Range]
    held: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, r in self.ranges.items():
            if not isinstance(r, Range):
                raise RequestError(f"model parameter {name}: {r!r} is not a range")
        held = {name: as_double(v, f"model parameter {name}: held value") for name, v in self.held.items()}
        both = sorted(set(self.ranges) & set(held))
        if both:
            raise RequestError(f"model parameter {both[0]} is both varied and held")
        object.__setattr__(self, "ranges", MappingProxyType(dict(self.ranges)))
        object.__setattr__(self, "held", MappingProxyType(held))

    @classmethod
    def parse(cls, form: Mapping[str, Any]) -> "ModelParameterSpace":
        """Read designs.md's JSON form, or its Python form.

        A two-element list (or tuple) is a linear range; ``{"range": [lo, hi], "scale": "linear" | "log"}`` a
        range with a scale; a number a held value. Integers are read as doubles (0061). A ``Range`` is accepted
        as itself.

        Parameters
        ----------
        form
            Names to ranges or held values.

        Returns
        -------
        ModelParameterSpace

        Raises
        ------
        RequestError
            For a malformed form, naming the model parameter (G15, 0065): a list that isn't two numbers, an end
            or held value that isn't a finite number (a bool included), a scale other than linear or log, or a
            range's object with a key other than ``range`` and ``scale``.
        """
        if not isinstance(form, Mapping):
            raise RequestError(f"a model parameter space maps names to ranges or held values, not {form!r}")
        ranges: dict[str, Range] = {}
        held: dict[str, float] = {}
        for name, value in form.items():
            if not isinstance(name, str):
                raise RequestError(f"a model parameter space's names are text, not {name!r}")
            what = f"model parameter {name}"
            if isinstance(value, Range):
                ranges[name] = value
            elif isinstance(value, (list, tuple)):
                ranges[name] = _parse_range(value, Scale.LINEAR, what)
            elif isinstance(value, Mapping):
                extra = sorted(str(k) for k in value if k not in ("range", "scale"))
                if extra:
                    raise RequestError(
                        f"{what}: unknown key {extra[0]!r}; a range is "
                        '{"range": [lo, hi], "scale": "linear" or "log"}'
                    )
                if "range" not in value:
                    raise RequestError(f"{what}: a range's object needs its range, [lo, hi]")
                ranges[name] = _parse_range(value["range"], value.get("scale", Scale.LINEAR), what)
            elif is_number(value):
                held[name] = as_double(value, f"{what}: held value")
            else:
                raise RequestError(f"{what}: {value!r} is not a range, a range with a scale, or a held number")
        return cls(ranges=ranges, held=held)

    @classmethod
    def at_point(cls, spec: ModelSpec, x: Mapping[str, Any]) -> "ModelParameterSpace":
        """Build the point design's space (0049): every model parameter held, at ``x``'s value or its nominal.

        Raises
        ------
        RequestError
            For a name that isn't a model parameter, or a value that isn't a finite number.
        """
        if not isinstance(x, Mapping):
            raise RequestError(f"x maps model parameters to values, not {x!r}")
        for name in x:
            spec.parameter(name)
        held = {
            p.name: as_double(x[p.name], f"model parameter {p.name}") if p.name in x else p.nominal
            for p in spec.parameters
        }
        return cls(ranges={}, held=held)

    def validate(self, spec: ModelSpec) -> None:
        """Refuse the space for this model, naming the model parameter, before any run (G15, M6).

        Raises
        ------
        RequestError
            For a name that isn't one of the model's model parameters, lo >= hi, a log range with lo <= 0, or a
            range end or held value outside the model parameter's limits (naming the limit).
        """
        for name in [*self.ranges, *self.held]:
            spec.parameter(name)
        for name, r in self.ranges.items():
            what = f"model parameter {name}: the range [{r.lo!r}, {r.hi!r}]"
            if not r.lo < r.hi:
                raise RequestError(f"{what} needs lo < hi")
            if r.scale is Scale.LOG and r.lo <= 0.0:
                raise RequestError(f"{what} is log, and needs lo > 0")
            for end in (r.lo, r.hi):
                limit = _crossed(spec.parameter(name).limits, end)
                if limit:
                    raise RequestError(f"{what} crosses its limit {limit}")
        for name, value in self.held.items():
            limit = _crossed(spec.parameter(name).limits, value)
            if limit:
                raise RequestError(f"model parameter {name}: the held value {value!r} crosses its limit {limit}")

    def varied(self, spec: ModelSpec) -> tuple[str, ...]:
        """Return the varied model parameters, in the model spec's order (G16)."""
        return tuple(p.name for p in spec.parameters if p.name in self.ranges)

    def _varied_ranges(self, spec: ModelSpec) -> list[Range]:
        return [self.ranges[name] for name in self.varied(spec)]

    def _columns(self, spec: ModelSpec, values: np.ndarray, what: str) -> np.ndarray:
        values = np.atleast_2d(np.asarray(values, dtype=np.float64))
        d = len(self.varied(spec))
        if values.ndim != 2 or values.shape[1] != d:
            raise ValueError(f"{what} has {values.shape[-1]} columns; the space varies {d}")
        return values

    def complete(self, spec: ModelSpec, Xv: np.ndarray) -> np.ndarray:
        """Complete ``(n, d_varied)`` values of the varied model parameters to ``(n, d_all)`` points.

        Held model parameters are filled in (the space's held values, else nominal values), in the spec's order.
        """
        Xv = self._columns(spec, Xv, "Xv")
        X = np.empty((Xv.shape[0], len(spec.parameters)), dtype=np.float64)
        k = 0
        for j, p in enumerate(spec.parameters):
            if p.name in self.ranges:
                X[:, j] = Xv[:, k]
                k += 1
            else:
                X[:, j] = self.held.get(p.name, p.nominal)
        return X

    def to_unit(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray:
        """Map complete ``(n, d_all)`` points back to ``(n, d_varied)`` unit coordinates z in [-1, 1] (0061).

        Clamped, with lo and hi exactly -1 and 1. Held model parameters have no unit coordinate.
        """
        X = np.atleast_2d(np.asarray(X, dtype=np.float64))
        names = [p.name for p in spec.parameters]
        Z = np.empty((X.shape[0], len(self.varied(spec))), dtype=np.float64)
        for k, name in enumerate(self.varied(spec)):
            Z[:, k] = self.ranges[name]._to_z(X[:, names.index(name)])
        return Z

    def from_unit(self, spec: ModelSpec, Z: np.ndarray) -> np.ndarray:
        """Map ``(n, d_varied)`` unit coordinates to complete points.

        z is clamped to [-1, 1], u = (z + 1)/2, each range's map applied, and a face (z = -1 or 1) is exactly lo
        or hi.
        """
        Z = np.clip(self._columns(spec, Z, "Z"), -1.0, 1.0)
        U = (Z + 1.0) / 2.0
        Xv = np.column_stack([r._from_u(U[:, k]) for k, r in enumerate(self._varied_ranges(spec))]) if U.size else U
        return self.complete(spec, Xv.reshape(U.shape))

    def from_cube(self, spec: ModelSpec, U: np.ndarray) -> np.ndarray:
        """Map a sampler's ``(n, d_varied)`` rows u in [0, 1) to complete points (sampling the unit cube).

        Each range's map is applied to u itself (lo + (hi - lo) u, bit for bit, on a linear range); u = 0 is
        exactly lo.
        """
        U = self._columns(spec, U, "U")
        Xv = np.column_stack([r._from_u(U[:, k]) for k, r in enumerate(self._varied_ranges(spec))]) if U.size else U
        return self.complete(spec, Xv.reshape(U.shape))

    def contains(self, spec: ModelSpec, X: np.ndarray) -> np.ndarray:
        """Tell whether each complete point is in the space: varied values in their closed ranges, held ones exact."""
        X = np.atleast_2d(np.asarray(X, dtype=np.float64))
        inside = np.ones(X.shape[0], dtype=bool)
        for j, p in enumerate(spec.parameters):
            if p.name in self.ranges:
                r = self.ranges[p.name]
                inside &= (X[:, j] >= r.lo) & (X[:, j] <= r.hi)
            else:
                inside &= X[:, j] == self.held.get(p.name, p.nominal)
        return inside

    def clip_line(self, spec: ModelSpec, anchor_z: np.ndarray, direction_z: np.ndarray) -> tuple[float, float]:
        """Clip the line ``anchor_z + t direction_z`` to the space, in unit coordinates.

        Parameters
        ----------
        anchor_z, direction_z
            ``(d_varied,)`` each; the anchor inside [-1, 1]^d.

        Returns
        -------
        tuple of float
            The segment's t range (t0, t1), t0 <= 0 <= t1.

        Raises
        ------
        RequestError
            For a zero direction.
        """
        a = np.asarray(anchor_z, dtype=np.float64)
        d = np.asarray(direction_z, dtype=np.float64)
        moving = d != 0.0
        if not moving.any():
            raise RequestError("a line's direction is zero")
        t_minus, t_plus = (-1.0 - a[moving]) / d[moving], (1.0 - a[moving]) / d[moving]
        return float(np.minimum(t_minus, t_plus).max()), float(np.maximum(t_minus, t_plus).min())

    def canonical(self) -> Mapping[str, Any]:
        """Return the canonical form (data_model.md §3.4), by name.

        Every range is ``{"range": [lo, hi], "scale": ...}``, and every held value a double.
        """
        out: dict[str, Any] = {name: {"range": [r.lo, r.hi], "scale": r.scale.value} for name, r in self.ranges.items()}
        out.update(self.held)
        return {name: out[name] for name in sorted(out)}
