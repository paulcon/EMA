"""Model specs and design identities for the design tests (contracts.md, The contract model; designs.md).

Built in Python, with no files: the contract model's d = 3, d = 1, and d = 20 model parameters, the heat model
of G9, and a helper that builds a design's identity the way the workspace will (0046, 0061 item 4).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from ema.designs import generators, samplers
from ema.types.design import DesignIdentity
from ema.types.identity import sha256_hex
from ema.types.model import Limits, ModelParameter, ModelSpec, PredictionSpec, PythonFunction
from ema.types.space import ModelParameterSpace


def make_spec(
    parameters: list[tuple[str, float, Limits]] | list[tuple[str, float]],
    name: str = "contract",
) -> ModelSpec:
    """A Python-function model spec with these (name, nominal[, limits]) model parameters."""
    params = []
    for p in parameters:
        limits = p[2] if len(p) > 2 else Limits()  # type: ignore[misc]
        params.append(
            ModelParameter(name=p[0], units="", description=f"model parameter {p[0]}", nominal=p[1], limits=limits)
        )
    return ModelSpec(
        name=name,
        description="a model built in the tests",
        interface=PythonFunction(function="model.py:f"),
        parameters=tuple(params),
        predictions=(
            PredictionSpec(name="y", units="", description="f"),
            PredictionSpec(name="z", units="", description="f + 1"),
        ),
    )


#: The contract model, d = 3 (contracts.md): a in [0, 2], b in [-1, 1], c in [1e-2, 1e2] log, each with its
#: nominal value at its range's center, and h held at its nominal value. c has the limit gt 0, so M6 is tested.
CONTRACT = make_spec([("a", 1.0), ("b", 0.0), ("c", 1.0, Limits(lower=0.0, lower_strict=True)), ("h", 0.5)])
CONTRACT_SPACE: dict[str, Any] = {"a": [0, 2], "b": [-1, 1], "c": {"range": [1e-2, 1e2], "scale": "log"}}

#: d = 1: a only.
D1 = make_spec([("a", 1.0)], name="contract_d1")
D1_SPACE: dict[str, Any] = {"a": [0, 2]}

#: d = 20: x1 ... x20 in [-1, 1], nominal 0.
D20 = make_spec([(f"x{i}", 0.0) for i in range(1, 21)], name="contract_d20")
D20_SPACE: dict[str, Any] = {f"x{i}": [-1, 1] for i in range(1, 21)}

#: G9's heat model (model_interface.md): k with gt 0, q.
HEAT = make_spec([("k", 45.0, Limits(lower=0.0, lower_strict=True)), ("q", 3e4)], name="heat")


def model_version_id(spec: ModelSpec) -> str:
    """A stand-in model version id: the hash of the spec's model parameters (the real one is step 03's)."""
    return sha256_hex(repr([(p.name, p.nominal) for p in spec.parameters]))


def identity(
    spec: ModelSpec,
    kind: str,
    space: Mapping[str, Any] | None = None,
    *,
    seed: int = 0,
    sampler: str | None = None,
    sampler_version: str | None = None,
    generator_version: str | None = None,
    **params: Any,
) -> DesignIdentity:
    """A design's identity, as the workspace builds one from a request (0046, 0061 item 4).

    The space is passed as given (so malformed forms reach the generator); the point design's is built from
    ``x`` when not given (0049). Uniform and convergent designs get the ``random`` sampler unless one is named.
    """
    if kind == "point" and space is None:
        space = ModelParameterSpace.at_point(spec, params.get("x", {})).canonical()
    if kind in ("uniform", "convergent") and sampler is None:
        sampler = "random"
    if sampler is not None and sampler_version is None:
        sampler_version = samplers.get(sampler).version
    if generator_version is None:
        generator_version = generators.get(kind).version
    return DesignIdentity(
        model_version_id=model_version_id(spec),
        kind=kind,
        space=dict(space or {}),
        params=params,
        seed=seed,
        sampler=sampler,
        sampler_version=sampler_version,
        generator_version=generator_version,
    )


def unit(spec: ModelSpec, space: Mapping[str, Any], points: np.ndarray) -> np.ndarray:
    """The points' unit coordinates, by the map back (designs.md, 0061)."""
    return ModelParameterSpace.parse(space).to_unit(spec, points)


def with_identity(ident: DesignIdentity, **changes: Any) -> DesignIdentity:
    """The same identity with some fields changed."""
    fields = dict(ident.canonical())
    fields.update(changes)
    return DesignIdentity(**fields)
