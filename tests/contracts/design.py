"""The design generator contract: C20-C27 (contracts.md), over every registered generator and the toy.

Each ``check_*`` takes a generator and reads its inputs from ``CASES``, the table keyed by generator name that
``designs.md`` and 0061 item 4 ask for: seeded or not, the nesting it claims, an example identity, one over the
cap, a grid of requests for G3, and the parameters G18 refuses. A generator is called only with a design's
identity (0061). Every check runs on the contract model (contracts.md), d = 3, with h held at its nominal value.

Negative controls (contracts.md): ``Toy`` keeps every promise and is not registered; each ``Broken*`` toy
differs from it in one way and must fail one check. ``test_every_check_fails_on_its_broken_toy`` is the
meta-test, so no check passes vacuously.
"""

from __future__ import annotations

import inspect
import math
import re
import sys
import tracemalloc
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.designs.generators import MAX_DESIGN_POINTS
from ema.types.design import Design, DesignIdentity
from ema.types.errors import DesignTooLarge, RequestError
from ema.types.model import ModelSpec
from ema.types.space import ModelParameterSpace
from ema.types.streams import spawned
from tests.support.designs import CONTRACT, CONTRACT_SPACE, identity, make_spec, with_identity

SPEC = CONTRACT
SPACE = CONTRACT_SPACE
#: The same model with another nominal value for h, which every design holds (0046).
SPEC_OTHER_NOMINAL = make_spec([(p.name, 0.75 if p.name == "h" else p.nominal, p.limits) for p in CONTRACT.parameters])
#: Spaces every check of C21 builds in: the contract space (c's computed top end, exp(ln lo + (ln hi - ln lo)),
#: is 100.00000000000013, above hi); c over 10^-6 to 10^6 (the degenerate case); b held at a value other than its
#: nominal.
WIDE_SPACE = {**SPACE, "c": {"range": [1e-6, 1e6], "scale": "log"}}
HELD_SPACE = {"a": [0, 2], "b": 0.25, "c": {"range": [1e-2, 1e2], "scale": "log"}}
NAN, INF = math.nan, math.inf

#: G15's malformed spaces, each with what the refusal must name (M6: the limit too).
BAD_SPACES: list[tuple[dict[str, Any], tuple[str, ...]]] = [
    ({**SPACE, "nope": [0, 1]}, ("nope",)),
    ({**SPACE, "a": [2, 0]}, ("model parameter a",)),
    ({**SPACE, "a": [1, 1]}, ("model parameter a",)),
    ({**SPACE, "b": {"range": [-1, 1], "scale": "log"}}, ("model parameter b",)),
    ({**SPACE, "c": [0, 10]}, ("model parameter c", "gt 0")),
    ({**SPACE, "c": -1.0}, ("model parameter c", "gt 0")),
    ({**SPACE, "a": [NAN, 2]}, ("model parameter a",)),
    ({**SPACE, "a": [0, INF]}, ("model parameter a",)),
    ({**SPACE, "a": [-INF, 2]}, ("model parameter a",)),
    ({**SPACE, "a": [True, 2]}, ("model parameter a",)),
    ({**SPACE, "a": ["0", 2]}, ("model parameter a",)),
    ({**SPACE, "b": NAN}, ("model parameter b",)),
    ({**SPACE, "b": INF}, ("model parameter b",)),
    ({**SPACE, "b": True}, ("model parameter b",)),
    ({**SPACE, "b": "1"}, ("model parameter b",)),
    ({**SPACE, "a": [0, 1, 2]}, ("model parameter a",)),
    ({**SPACE, "c": {"range": [1e-2, 1e2], "scale": "ln"}}, ("model parameter c",)),
    ({**SPACE, "c": {"range": [1e-2, 1e2], "scale": "log", "extra": 1}}, ("model parameter c",)),
    ({**SPACE, "a": {"scale": "linear"}}, ("model parameter a",)),
    ({**SPACE, "a": None}, ("model parameter a",)),
]


def varied_names(space: Mapping[str, Any]) -> list[str]:
    """The names a space form varies (anything that isn't a held number), in the form's order."""
    return [k for k, v in space.items() if not isinstance(v, (int, float))]


def inside_value(form: Any) -> Any:
    """A value inside a range's form (its low end), or the held value itself."""
    if isinstance(form, (list, tuple)):
        return form[0]
    if isinstance(form, Mapping) and "range" in form:
        return form["range"][0]
    return form


# --------------------------------------------------------------------------------------------------------------
# The per-generator table (designs.md, Shared rules; 0061 item 4)


@dataclass(frozen=True)
class Case:
    """One generator's inputs to the checks."""

    seeded: bool
    takes_space: bool
    #: (spec, space) -> a small valid identity
    example: Callable[[ModelSpec, Mapping[str, Any]], DesignIdentity]
    #: (spec) -> identities of several sizes (G3)
    grid: Callable[[ModelSpec], list[DesignIdentity]]
    #: (spec) -> (smaller, larger, "first rows" or "every other point") (G4)
    nesting: Callable[[ModelSpec], list[tuple[DesignIdentity, DesignIdentity, str]]]
    #: (spec) -> an identity whose size is over MAX_DESIGN_POINTS (G5)
    over_cap: Callable[[ModelSpec], DesignIdentity]
    #: (spec) -> identities G18 refuses, each with what the refusal must name
    bad_params: Callable[[ModelSpec], list[tuple[DesignIdentity, tuple[str, ...]]]]


def _point(spec: ModelSpec, space: Mapping[str, Any], **kw: Any) -> DesignIdentity:
    x = kw.pop("x", {k: inside_value(v) for k, v in space.items()})
    return identity(spec, "point", x=x, **kw)


def _nominal_space(spec: ModelSpec) -> dict[str, Any]:
    return dict(ModelParameterSpace.at_point(spec, {}).canonical())


def _given(spec: ModelSpec, space: Mapping[str, Any], n: int = 5, **kw: Any) -> DesignIdentity:
    names = [k for k in ("a", "b", "c") if k in varied_names(space)] or ["a"]
    lines = kw.pop(
        "lines",
        [
            {"anchor": {}, "direction": dict.fromkeys(names[:2], 1)},
            {"anchor": {names[0]: inside_value(space.get(names[0], 0))}, "direction": {names[-1]: -0.5}},
        ],
    )
    return identity(spec, "lines", space, lines=lines, n=n, **kw)


CASES: dict[str, Case] = {
    "point": Case(
        seeded=False,
        takes_space=False,
        example=lambda spec, space: _point(spec, space, repeats=3),
        grid=lambda spec: [_point(spec, SPACE, repeats=r) for r in (0, 1, 5)],
        nesting=lambda spec: [(_point(spec, SPACE, repeats=2), _point(spec, SPACE, repeats=5), "first rows")],
        over_cap=lambda spec: _point(spec, SPACE, repeats=MAX_DESIGN_POINTS),
        bad_params=lambda spec: [
            (identity(spec, "point", _nominal_space(spec), repeats=-1), ("repeats",)),
            (identity(spec, "point", _nominal_space(spec), repeats=True), ("repeats",)),
            (identity(spec, "point", _nominal_space(spec), repeats=2.5), ("repeats",)),
            (identity(spec, "point", _nominal_space(spec), x={"a": NAN}), ("model parameter a",)),
            (identity(spec, "point", _nominal_space(spec), x={"a": "1"}), ("model parameter a",)),
            (identity(spec, "point", _nominal_space(spec), x={"nope": 1.0}), ("nope",)),
            (identity(spec, "point", _nominal_space(spec), x={"c": -1.0}), ("model parameter c", "gt 0")),
            (identity(spec, "point", _nominal_space(spec), seed=-1), ("seed",)),
            (identity(spec, "point", _nominal_space(spec), other=1), ("other",)),
        ],
    ),
    "uniform": Case(
        seeded=True,
        takes_space=True,
        example=lambda spec, space: identity(spec, "uniform", space, n=7),
        grid=lambda spec: [identity(spec, "uniform", SPACE, n=n) for n in (1, 2, 9)],
        nesting=lambda spec: [
            (identity(spec, "uniform", SPACE, n=5), identity(spec, "uniform", SPACE, n=12), "first rows")
        ],
        over_cap=lambda spec: identity(spec, "uniform", SPACE, n=MAX_DESIGN_POINTS + 1),
        bad_params=lambda spec: [
            (identity(spec, "uniform", SPACE, n=0), ("n",)),
            (identity(spec, "uniform", SPACE, n=True), ("n",)),
            (identity(spec, "uniform", SPACE, n=2.5), ("n",)),
            (identity(spec, "uniform", SPACE), ("n",)),
            (identity(spec, "uniform", SPACE, n=5, seed=-1), ("seed",)),
            (identity(spec, "uniform", SPACE, n=5, seed=True), ("seed",)),
        ],
    ),
    "convergent": Case(
        seeded=True,
        takes_space=True,
        example=lambda spec, space: identity(spec, "convergent", space, n_min=2, alpha="0.7072", level=2),
        grid=lambda spec: (
            [identity(spec, "convergent", SPACE, n_min=2, alpha="0.7072", level=lv) for lv in (0, 1, 3)]
            + [identity(spec, "convergent", SPACE, n_min=3, alpha="0.5", level=2)]
        ),
        nesting=lambda spec: [
            (
                identity(spec, "convergent", SPACE, n_min=2, alpha="0.5", level=1),
                identity(spec, "convergent", SPACE, n_min=2, alpha="0.5", level=2),
                "first rows",
            ),
        ],
        over_cap=lambda spec: identity(spec, "convergent", SPACE, n_min=10, alpha="0.5", level=12),
        bad_params=lambda spec: [
            (identity(spec, "convergent", SPACE, n_min=2, alpha="1", level=1), ("alpha",)),
            (identity(spec, "convergent", SPACE, n_min=2, alpha="0", level=1), ("alpha",)),
            (identity(spec, "convergent", SPACE, n_min=2, alpha="0.95", level=2), ("alpha",)),
            (identity(spec, "convergent", SPACE, n_min=0, alpha="0.5", level=1), ("n_min",)),
            (identity(spec, "convergent", SPACE, n_min=2, alpha="0.5", level=-1), ("level",)),
            (identity(spec, "convergent", SPACE, n_min=2, alpha="0.5", level=True), ("level",)),
            (identity(spec, "convergent", SPACE, n_min=2, alpha="0.5", level=1, seed=-1), ("seed",)),
        ],
    ),
    "lines": Case(
        seeded=False,
        takes_space=True,
        example=lambda spec, space: _given(spec, space),
        grid=lambda spec: [
            _given(spec, SPACE, n=2),
            _given(spec, SPACE, n=5),
            _given(spec, SPACE, n=3, lines=[{"anchor": {}, "direction": {"c": 1}}]),
        ],
        nesting=lambda spec: [(_given(spec, SPACE, n=5), _given(spec, SPACE, n=9), "every other point")],
        over_cap=lambda spec: _given(
            spec, SPACE, n=MAX_DESIGN_POINTS + 1, lines=[{"anchor": {}, "direction": {"a": 1}}]
        ),
        bad_params=lambda spec: [
            (_given(spec, SPACE, n=1), ("n",)),
            (_given(spec, SPACE, n=True), ("n",)),
            (_given(spec, SPACE, lines=[]), ("lines",)),
            (_given(spec, SPACE, lines=[{"anchor": {"nope": 1.0}, "direction": {"a": 1}}]), ("nope",)),
            (_given(spec, SPACE, lines=[{"anchor": {"a": NAN}, "direction": {"a": 1}}]), ("model parameter a",)),
            (_given(spec, SPACE, lines=[{"anchor": {"a": 5.0}, "direction": {"a": 1}}]), ("model parameter a",)),
            (_given(spec, SPACE, lines=[{"anchor": {}, "direction": {}}]), ("direction",)),
            (_given(spec, SPACE, lines=[{"anchor": {}, "direction": {"a": 0}}]), ("direction",)),
            (_given(spec, SPACE, lines=[{"anchor": {}, "direction": {"h": 1}}]), ("model parameter h",)),
            (_given(spec, SPACE, lines=[{"anchor": {}, "direction": {"nope": 1}}]), ("nope",)),
            (_given(spec, SPACE, lines=[{"anchor": {}, "direction": {"a": INF}}]), ("model parameter a",)),
            (_given(spec, SPACE, seed=-1), ("seed",)),
        ],
    ),
    "coordinate_lines": Case(
        seeded=False,
        takes_space=True,
        example=lambda spec, space: identity(spec, "coordinate_lines", space, n=5),
        grid=lambda spec: [identity(spec, "coordinate_lines", SPACE, n=n) for n in (2, 4, 5)],
        nesting=lambda spec: [
            (
                identity(spec, "coordinate_lines", SPACE, n=5),
                identity(spec, "coordinate_lines", SPACE, n=9),
                "every other point",
            )
        ],
        over_cap=lambda spec: identity(spec, "coordinate_lines", SPACE, n=MAX_DESIGN_POINTS // 3 + 1),
        bad_params=lambda spec: [
            (identity(spec, "coordinate_lines", SPACE, n=1), ("n",)),
            (identity(spec, "coordinate_lines", SPACE, n=2.5), ("n",)),
            (identity(spec, "coordinate_lines", SPACE, n=5, anchor={"nope": 1.0}), ("nope",)),
            (identity(spec, "coordinate_lines", SPACE, n=5, anchor={"a": INF}), ("model parameter a",)),
            (identity(spec, "coordinate_lines", SPACE, n=5, anchor={"a": 5.0}), ("model parameter a",)),
            (identity(spec, "coordinate_lines", SPACE, n=5, seed=-1), ("seed",)),
        ],
    ),
    "random_lines": Case(
        seeded=True,
        takes_space=True,
        example=lambda spec, space: identity(spec, "random_lines", space, m=3, n=5),
        grid=lambda spec: [identity(spec, "random_lines", SPACE, m=m, n=n) for m, n in ((1, 2), (2, 5), (3, 3))],
        nesting=lambda spec: [
            (
                identity(spec, "random_lines", SPACE, m=2, n=5),
                identity(spec, "random_lines", SPACE, m=3, n=5),
                "first rows",
            ),
            (
                identity(spec, "random_lines", SPACE, m=2, n=5),
                identity(spec, "random_lines", SPACE, m=2, n=9),
                "every other point",
            ),
        ],
        over_cap=lambda spec: identity(spec, "random_lines", SPACE, m=1, n=MAX_DESIGN_POINTS + 1),
        bad_params=lambda spec: [
            (identity(spec, "random_lines", SPACE, m=0, n=5), ("m",)),
            (identity(spec, "random_lines", SPACE, m=True, n=5), ("m",)),
            (identity(spec, "random_lines", SPACE, m=2, n=1), ("n",)),
            (identity(spec, "random_lines", SPACE, m=2, n=5, seed=-1), ("seed",)),
        ],
    ),
}


# --------------------------------------------------------------------------------------------------------------
# The toy and its broken toys (contracts.md, Negative controls)


def toy_identity(spec: ModelSpec, space: Mapping[str, Any], n: int = 7, **kw: Any) -> DesignIdentity:
    seed = kw.pop("seed", 0)
    return DesignIdentity(
        model_version_id="0" * 64,
        kind="toy",
        space=dict(space),
        params={"n": n, **kw},
        seed=seed,
        sampler=None,
        sampler_version=None,
        generator_version="1",
    )


@dataclass(frozen=True)
class Toy:
    """A generator that keeps every promise: row 0 is the space's top corner, row i > 0 a draw from stream i."""

    name: str = "toy"
    version: str = "1"

    def check(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[ModelParameterSpace, int]:
        if identity.kind != self.name or identity.generator_version != self.version:
            raise RequestError(
                f"design generator {identity.kind} version {identity.generator_version} is not "
                f"design generator {self.name} version {self.version}"
            )
        unknown = set(identity.params) - {"n"}
        if unknown:
            raise RequestError(f"toy: unknown parameter {min(unknown)}")
        for key, value, low in (("n", identity.params.get("n"), 1), ("seed", identity.seed, 0)):
            if not isinstance(value, int) or isinstance(value, bool) or value < low:
                raise RequestError(f"toy: {key} must be an integer >= {low}")
        space = ModelParameterSpace.parse(identity.space)
        space.validate(spec)
        if not space.varied(spec):
            raise RequestError("toy: the space varies no model parameter")
        return space, identity.params["n"]

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        return self.check(identity, spec)[1]

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        space, n = self.check(identity, spec)
        if n > MAX_DESIGN_POINTS:
            raise DesignTooLarge(f"the design has {n:,} points, over the cap of {MAX_DESIGN_POINTS:,}")
        stop = n if stop is None else stop
        points = np.array([self.row(identity, spec, space, i) for i in range(start, stop)])
        points = points.reshape(stop - start, len(spec.parameters))
        return Design(
            identity=identity, points=points, replicates=np.zeros(stop - start, dtype=np.int64), levels=None, lines=None
        )

    def seed_for(self, identity: DesignIdentity, i: int) -> int:
        return identity.seed

    def row(self, identity: DesignIdentity, spec: ModelSpec, space: ModelParameterSpace, i: int) -> np.ndarray:
        d = len(space.varied(spec))
        if i == 0:
            return space.from_unit(spec, np.ones((1, d)))[0]
        return space.from_cube(spec, spawned(self.seed_for(identity, i), i).random(d)[None, :])[0]


class BrokenGlobalDraws(Toy):
    """C20's negative control: draws from numpy's global generator."""

    def row(self, identity: DesignIdentity, spec: ModelSpec, space: ModelParameterSpace, i: int) -> np.ndarray:
        d = len(space.varied(spec))
        return space.from_cube(spec, np.random.random((1, d)))[0]  # noqa: NPY002


class BrokenUnclamped(Toy):
    """C21's negative control: maps a log range by exp(ln lo + (ln hi - ln lo) u), without the clamp or the end."""

    def row(self, identity: DesignIdentity, spec: ModelSpec, space: ModelParameterSpace, i: int) -> np.ndarray:
        if i != 0:
            return super().row(identity, spec, space, i)
        x = space.complete(spec, np.zeros((1, len(space.varied(spec)))))[0]
        names = [p.name for p in spec.parameters]
        for name, r in space.ranges.items():
            lo, hi = r.lo, r.hi
            u = 1.0
            x[names.index(name)] = (
                np.exp(np.log(lo) + (np.log(hi) - np.log(lo)) * u) if r.scale.value == "log" else lo + (hi - lo) * u
            )
        return x


class BrokenSizeOffByOne(Toy):
    """C22's negative control: a size off by one."""

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        return super().size(identity, spec) + 1


class BrokenReseedsWithN(Toy):
    """C23's negative control: reseeds when n changes."""

    def seed_for(self, identity: DesignIdentity, i: int) -> int:
        return identity.seed + identity.params["n"]


class BrokenAllocatesFirst(Toy):
    """C24's negative control: allocates, then checks."""

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        n = identity.params["n"]
        scratch = np.empty((n, len(spec.parameters)))
        scratch[:1] = 0.0
        return super().build(identity, spec, start, stop)


class BrokenReseedsBlocks(Toy):
    """C25's negative control: reseeds each block."""

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        object.__setattr__(self, "_start", start)
        return super().build(identity, spec, start, stop)

    def seed_for(self, identity: DesignIdentity, i: int) -> int:
        return identity.seed + getattr(self, "_start", 0)


class BrokenSpaceOrder(Toy):
    """C26's negative control: columns in the space's order, not the model spec's."""

    def row(self, identity: DesignIdentity, spec: ModelSpec, space: ModelParameterSpace, i: int) -> np.ndarray:
        x = super().row(identity, spec, space, i)
        in_space = [n for n in space.ranges]  # the space's order
        in_spec = list(space.varied(spec))
        names = [p.name for p in spec.parameters]
        out = x.copy()
        for a, b in zip(in_space, in_spec, strict=True):
            out[names.index(a)] = x[names.index(b)]
        return out


class BrokenBuildsFirst(Toy):
    """C27's negative control: builds from the raw space before validating it."""

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        names = [p.name for p in spec.parameters]
        for name, form in identity.space.items():
            names.index(name)
            lo, hi = (
                form["range"]
                if isinstance(form, Mapping)
                else (form if isinstance(form, (list, tuple)) else (form, form))
            )
            _ = lo + (hi - lo) * 0.5
        return super().build(identity, spec, start, stop)


BROKEN: dict[str, list[Toy]] = {
    "check_deterministic": [BrokenGlobalDraws()],
    "check_inside": [BrokenUnclamped()],
    "check_size": [BrokenSizeOffByOne()],
    "check_nesting": [BrokenReseedsWithN()],
    "check_too_large": [BrokenAllocatesFirst()],
    "check_blocks": [BrokenReseedsBlocks()],
    "check_column_order": [BrokenSpaceOrder()],
    "check_bad_space": [BrokenBuildsFirst()],
}

CASES["toy"] = Case(
    seeded=True,
    takes_space=True,
    example=lambda spec, space: toy_identity(spec, space),
    grid=lambda spec: [toy_identity(spec, SPACE, n=n) for n in (1, 2, 9)],
    nesting=lambda spec: [(toy_identity(spec, SPACE, n=5), toy_identity(spec, SPACE, n=12), "first rows")],
    over_cap=lambda spec: toy_identity(spec, SPACE, n=MAX_DESIGN_POINTS + 1),
    bad_params=lambda spec: [(toy_identity(spec, SPACE, n=0), ("n",)), (toy_identity(spec, SPACE, seed=-1), ("seed",))],
)


# --------------------------------------------------------------------------------------------------------------
# Helpers


def same(d1: Design, d2: Design) -> bool:
    """Two designs' arrays, levels, and lines are equal, bit for bit (C14, C20)."""
    return (
        d1.points.shape == d2.points.shape
        and np.array_equal(d1.points, d2.points)
        and np.array_equal(d1.replicates, d2.replicates)
        and d1.levels == d2.levels
        and d1.lines == d2.lines
    )


def refused(fn: Callable[[], Any], *names: str) -> None:
    """``fn`` raises RequestError whose message names each of ``names`` (as a word)."""
    with pytest.raises(RequestError) as info:
        fn()
    message = str(info.value)
    for name in names:
        assert re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", message), f"{name!r} not named in {message!r}"


# --------------------------------------------------------------------------------------------------------------
# The checks


def check_deterministic(generator: Any) -> None:
    """C20: G1 on one machine; another seed only where the generator takes one; the version refusals (0061,
    0062); and two model versions that differ in a held model parameter's nominal value give other points (0046).
    """
    case = CASES[generator.name]
    ident = case.example(SPEC, SPACE)
    first, second = generator.build(ident, SPEC), generator.build(ident, SPEC)
    assert same(first, second), "the same request gave other points"

    one = generator.build(with_identity(ident, seed=1), SPEC)
    two = generator.build(with_identity(ident, seed=2), SPEC)
    if case.seeded:
        assert not np.array_equal(one.points, two.points), "seeds 1 and 2 gave the same points"
    else:
        assert same(one, two), "an unseeded generator's points changed with the seed"

    refused(lambda: generator.build(with_identity(ident, generator_version="999"), SPEC), "999", generator.version)
    if ident.sampler is not None:
        refused(
            lambda: generator.build(with_identity(ident, sampler_version="999"), SPEC),
            "999",
            str(ident.sampler_version),
        )

    other = generator.build(case.example(SPEC_OTHER_NOMINAL, SPACE), SPEC_OTHER_NOMINAL)
    h = [p.name for p in SPEC.parameters].index("h")
    assert np.all(first.points[:, h] == 0.5) and np.all(other.points[:, h] == 0.75)


def check_inside(generator: Any) -> None:
    """C21: every point inside the space's closed ranges and every limit; held values exact; a line's ends on a
    face exactly, log ranges included (G2, G10, 0047)."""
    case = CASES[generator.name]
    names = [p.name for p in SPEC.parameters]
    for form in (SPACE, WIDE_SPACE, HELD_SPACE):
        ident = case.example(SPEC, form)
        design = generator.build(ident, SPEC)
        space = ModelParameterSpace.parse(ident.space)
        X = design.points
        for j, p in enumerate(SPEC.parameters):
            assert all(p.limits.contains(float(v)) for v in X[:, j]), f"{p.name} outside its limits"
            if p.name in space.ranges:
                r = space.ranges[p.name]
                assert np.all((X[:, j] >= r.lo) & (X[:, j] <= r.hi)), f"{p.name} outside [{r.lo}, {r.hi}]"
            else:
                held = space.held.get(p.name, p.nominal)
                assert np.all(X[:, j] == held), f"{p.name} not held exactly at {held}"
        for line in design.lines or ():
            for end in line.ends:
                on_face = [end[names.index(k)] in (r.lo, r.hi) for k, r in space.ranges.items()]
                assert any(on_face), f"a line's end {end} is on no face exactly"
            first, last = line.rows
            assert tuple(X[first]) == line.ends[0] and tuple(X[last - 1]) == line.ends[1]


def check_size(generator: Any) -> None:
    """C22: the size computed before building equals the number of rows built (G3)."""
    for ident in CASES[generator.name].grid(SPEC):
        size = generator.size(ident, SPEC)
        design = generator.build(ident, SPEC)
        assert size == len(design) == design.points.shape[0] == design.replicates.shape[0], (size, len(design))
        assert design.points.shape[1] == len(SPEC.parameters)


def check_nesting(generator: Any) -> None:
    """C23: where nesting is claimed, the smaller design's points are the larger's, bit for bit (G4)."""
    for small_id, large_id, how in CASES[generator.name].nesting(SPEC):
        small, large = generator.build(small_id, SPEC), generator.build(large_id, SPEC)
        if how == "first rows":
            k = len(small)
            assert np.array_equal(large.points[:k], small.points), "not the first rows"
            assert np.array_equal(large.replicates[:k], small.replicates)
        else:
            assert small.lines is not None and large.lines is not None
            for s, g in zip(small.lines, large.lines, strict=True):
                refined = large.points[g.rows[0] : g.rows[1]][::2]
                assert np.array_equal(refined, small.points[s.rows[0] : s.rows[1]]), "not every other point"


def check_too_large(generator: Any) -> None:
    """C24: a design over MAX_DESIGN_POINTS is refused before it is built, and no array is allocated (G5)."""
    ident = CASES[generator.name].over_cap(SPEC)
    size = generator.size(ident, SPEC)
    assert size > MAX_DESIGN_POINTS
    tracemalloc.start()
    try:
        with pytest.raises(DesignTooLarge) as info:
            generator.build(ident, SPEC)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 16 * 2**20, f"{peak:,} bytes allocated before the refusal"
    assert f"{size:,}" in str(info.value) and f"{MAX_DESIGN_POINTS:,}" in str(info.value)


def check_blocks(generator: Any) -> None:
    """C25: rows [a, b) made alone equal those rows of the whole design (G6)."""
    for ident in [*CASES[generator.name].grid(SPEC), CASES[generator.name].example(SPEC, SPACE)]:
        whole = generator.build(ident, SPEC)
        n = len(whole)
        if n < 3:
            continue
        a, b = n // 3, max(n // 3 + 1, 2 * n // 3)
        block = generator.build(ident, SPEC, a, b)
        assert np.array_equal(block.points, whole.points[a:b]), f"rows [{a}, {b}) differ"
        assert np.array_equal(block.replicates, whole.replicates[a:b])
        assert block.levels == whole.levels and block.lines == whole.lines


def check_column_order(generator: Any) -> None:
    """C26: a design's columns follow the model spec's order, whatever order the space names them in (G16)."""
    case = CASES[generator.name]
    reversed_space = dict(reversed(list(SPACE.items())))
    assert list(reversed_space) != list(SPACE)
    one = generator.build(case.example(SPEC, SPACE), SPEC)
    two = generator.build(case.example(SPEC, reversed_space), SPEC)
    assert np.array_equal(one.points, two.points), "the space's order changed the points"


def check_bad_space(generator: Any) -> None:
    """C27: G15, for a generator that takes a space, and G18: refused before building, with RequestError naming
    the model parameter or the generator's parameter, and, for a limit, the limit (M6)."""
    case = CASES[generator.name]
    if case.takes_space:
        for form, names in BAD_SPACES:
            ident = case.example(SPEC, form)
            refused(lambda ident=ident: generator.build(ident, SPEC), *names)
            refused(lambda ident=ident: generator.size(ident, SPEC), *names)
    for ident, names in case.bad_params(SPEC):
        refused(lambda ident=ident: generator.build(ident, SPEC), *names)


# --------------------------------------------------------------------------------------------------------------
# Parametrization, and the meta-test


CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


def implementations() -> list[Any]:
    return [generators.get(name) for name in generators.names()] + [Toy()]


@pytest.fixture(params=implementations(), ids=lambda g: g.name)
def generator(request: pytest.FixtureRequest) -> Any:
    return request.param


def test_every_generator_has_a_case() -> None:
    """The table covers every registered generator (0061 item 4)."""
    assert set(generators.names()) <= set(CASES)


def test_the_toy_is_not_registered() -> None:
    assert "toy" not in generators.names()


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls): every check has a broken toy, and fails on each."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        # A failed assertion, pytest.raises' "did not raise", or an error the check lets through all fail it.
        with pytest.raises((AssertionError, pytest.fail.Exception, Exception)):  # type: ignore[arg-type]
            CHECKS[check](broken)
