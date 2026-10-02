"""A design, its identity, its lines, and its structure (designs.md; data_model.md §3.4; 0046, 0063, 0065)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class DesignIdentity:
    """A design's identity (0046, data_model.md §3.4): stored with each result and approval.

    With the provenance's ``DesignStructure`` and the stored runs' points, a replay needs no generator; with
    today's generator at the identity's versions, the design can also be rebuilt (0063). A generator is called
    with an identity only (0061).

    Attributes
    ----------
    model_version_id : str
        The model version's id.
    kind : str
        "point", "uniform", "convergent", "lines", "coordinate_lines", or "random_lines".
    space : Mapping[str, Any]
        The model parameter space, in its canonical form; read-only.
    params : Mapping[str, Any]
        The generator's parameters that aren't fields here (no seed, sampler, or versions); alpha as its
        decimal string. Read-only, nested values included.
    seed : int
        The request's seed, for every kind; only seeded generators use it (0061).
    sampler : str or None
        For uniform and convergent designs.
    sampler_version : str or None
        The sampler's version.
    generator_version : str
        The generator's version.
    """

    model_version_id: str
    kind: str
    space: Mapping[str, Any]
    params: Mapping[str, Any]
    seed: int
    sampler: str | None
    sampler_version: str | None
    generator_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "space", _freeze(self.space))
        object.__setattr__(self, "params", _freeze(self.params))

    def canonical(self) -> Mapping[str, Any]:
        """Return every field as plain JSON data (dicts and lists), for ``canonical_json`` and hashing."""
        return {
            "model_version_id": self.model_version_id,
            "kind": self.kind,
            "space": _thaw(self.space),
            "params": _thaw(self.params),
            "seed": self.seed,
            "sampler": self.sampler,
            "sampler_version": self.sampler_version,
            "generator_version": self.generator_version,
        }


@dataclass(frozen=True)
class Line:
    """One line of a lines design, as recorded with it (designs.md, Lines; 0063).

    Attributes
    ----------
    anchor : tuple of float
        A complete point, in model parameter units and the spec's order.
    direction : tuple of float
        In unit coordinates, one component per varied model parameter in the spec's order: a given line's as
        the user gave it, a random line's normalized (0065).
    ends : tuple of two tuples of float
        The complete points at t = 0 and t = 1, the line's first and last rows.
    rows : tuple of int
        Its rows [start, stop) in the whole design.
    """

    anchor: tuple[float, ...]
    direction: tuple[float, ...]
    ends: tuple[tuple[float, ...], tuple[float, ...]]
    rows: tuple[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor", tuple(float(v) for v in self.anchor))
        object.__setattr__(self, "direction", tuple(float(v) for v in self.direction))
        start, stop = self.ends
        object.__setattr__(self, "ends", (tuple(float(v) for v in start), tuple(float(v) for v in stop)))
        object.__setattr__(self, "rows", (int(self.rows[0]), int(self.rows[1])))


@dataclass(frozen=True, eq=False)
class Design:
    """A design's points, as a generator builds them, or a block of its rows (G6).

    Its arrays are read-only. Compare two designs with ``np.array_equal``, field by field (C14, C20).

    Attributes
    ----------
    identity : DesignIdentity or None
        None only for the test run (data_model.md §5.4).
    points : numpy.ndarray
        ``(n, d)``: every model parameter, in the spec's order.
    replicates : numpy.ndarray
        ``(n,)`` integers.
    levels : tuple of int or None
        A convergent design's sizes n_0 ... n_L.
    lines : tuple of Line or None
        A lines design's lines, whose rows index the whole design.
    """

    identity: DesignIdentity | None
    points: np.ndarray
    replicates: np.ndarray
    levels: tuple[int, ...] | None
    lines: tuple[Line, ...] | None

    def __post_init__(self) -> None:
        points = np.asarray(self.points, dtype=np.float64).view()
        replicates = np.asarray(self.replicates, dtype=np.int64).view()
        if points.ndim != 2 or replicates.ndim != 1 or points.shape[0] != replicates.shape[0]:
            raise ValueError(f"points {points.shape} and replicates {replicates.shape} don't match")
        points.flags.writeable = False
        replicates.flags.writeable = False
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "replicates", replicates)

    def __len__(self) -> int:
        """Return the number of rows."""
        return int(self.points.shape[0])


@dataclass(frozen=True)
class DesignStructure:
    """What a diagnostic reads from a design beyond its points and replicates (0063).

    Kept in a result's provenance, so a replay builds its ``Design`` with no generator.

    Attributes
    ----------
    levels : tuple of int or None
        A convergent design's sizes n_0 ... n_L.
    lines : tuple of Line or None
        Each line's anchor, direction, ends, and rows.
    """

    levels: tuple[int, ...] | None
    lines: tuple[Line, ...] | None
