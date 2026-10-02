"""The diagnostic interface, its parameters, the registry, and ``evaluate`` with the shared precheck.

architecture.md §6 (``ema.diagnostics``) and §7 (steps 2 and 8); diagnostics/shared.md (the precheck, the shared
observations and notes, random draws; S5-S9); contracts.md (C1-C19, the declarations each diagnostic makes);
uncertainty.md (the interval-method seam); P4-P7; records 0035, 0036, 0041, 0051, 0065, 0067 (one identity per
design), 0073 (plain Unicode text in results), 0075.

A diagnostic is one module that subclasses ``DiagnosticBase`` and ends with ``register(...)``; ``evaluate`` is the
only entry point (the workspace's step 8): the precheck, ``compute``, the result built and round-tripped through
its JSON (C17), then the figures from that copy (P1).
"""

import dataclasses
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from importlib import metadata
from types import MappingProxyType
from typing import Any, ClassVar, Protocol

import numpy as np

from ema.designs import generators, samplers
from ema.numerics.intervals import Interval, IntervalMethod
from ema.numerics.tolerance import is_constant
from ema.types._values import as_double, as_int, is_number
from ema.types.design import DesignIdentity, DesignStructure
from ema.types.errors import NotFound, RequestError
from ema.types.identity import hex_ids, model_version_label
from ema.types.model import ModelSpec, PredictionSpec
from ema.types.requests import Progress, Request
from ema.types.results import (
    Counts,
    DiagnosticResult,
    Estimate,
    EstimateTable,
    Figure,
    IntervalInfo,
    MeasuredNoisy,
    Note,
    Observation,
    ObservationTable,
    Provenance,
)
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace
from ema.types.streams import spawned
from ema.types.summaries import DiagnosticParameterInfo, DiagnosticSummary
from ema.types.text import fmt

#: The smallest spawn key a diagnostic's own draws use: above every design stream's key (shared.md).
SPAWN_TAG_BASE = 2**32
#: The most failure reasons a note lists verbatim; the rest are summed (shared.md, S7).
NOTE_MAX_REASONS = 5

# --------------------------------------------------------------------------------------------------------------
# Diagnostic parameters: readers, so one value has one canonical form (record 0067's hand-off; C55)


class Reader(Protocol):
    """Reads one diagnostic parameter's value into its canonical form, and describes it as a JSON schema."""

    def read(self, value: Any, what: str) -> Any:
        """Return the canonical value; raise ``RequestError`` naming ``what`` when it isn't valid."""
        ...

    def schema(self) -> Mapping[str, Any]:
        """Return the value's JSON schema (C55)."""
        ...


@dataclass(frozen=True)
class Integer:
    """An integer >= ``minimum``; an integral float (3.0) is read as 3, a bool refused (0061 item 6)."""

    minimum: int

    def read(self, value: Any, what: str) -> int:
        """Return the value as an ``int``."""
        return as_int(value, what, self.minimum)

    def schema(self) -> Mapping[str, Any]:
        """Return ``{"type": "integer", "minimum": ...}``."""
        return {"type": "integer", "minimum": self.minimum}


#: A decimal number's text (0047): digits, an optional point, an optional exponent; no spaces, no "1/3".
_DECIMAL = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


@dataclass(frozen=True)
class DecimalText:
    """A decimal in the open interval (lo, hi), kept as its shortest decimal text (0047; record 0067's hand-off).

    A float is read as the decimal its ``repr`` writes (0.7072 is "0.7072"); text as the decimal it writes, with
    trailing zeros and the exponent removed ("7.0720e-1" is "0.7072"); so a float and its text are one value.
    """

    lo: float
    hi: float

    def read(self, value: Any, what: str) -> str:
        """Return the canonical decimal text."""
        if isinstance(value, np.floating):
            value = float(value)
        if is_number(value) and math.isfinite(float(value)):
            text = repr(float(value)) if isinstance(value, float) else str(int(value))
        elif isinstance(value, str) and _DECIMAL.fullmatch(value):
            text = value
        else:
            raise RequestError(f"{what} must be a decimal number in ({self.lo:g}, {self.hi:g}), not {value!r}")
        try:
            number = Decimal(text)
        except InvalidOperation:  # pragma: no cover - the pattern admits only decimals
            raise RequestError(f"{what} must be a decimal number, not {value!r}") from None
        if not Decimal(repr(self.lo)) < number < Decimal(repr(self.hi)):
            raise RequestError(f"{what} must be in ({self.lo:g}, {self.hi:g}), not {value}")
        canonical = format(number.normalize(), "f")
        return canonical

    def schema(self) -> Mapping[str, Any]:
        """Return a number in (lo, hi), or its decimal text."""
        return {
            "anyOf": [
                {"type": "number", "exclusiveMinimum": self.lo, "exclusiveMaximum": self.hi},
                {"type": "string", "pattern": _DECIMAL.pattern},
            ]
        }


@dataclass(frozen=True)
class Point:
    """A mapping of model parameter names to finite numbers, each read as a double (x, an anchor, a direction).

    The names are checked against the model spec when the design is built (G9, G15); here only the form.
    """

    def read(self, value: Any, what: str) -> dict[str, float]:
        """Return ``{name: double}`` in the order given (canonical JSON sorts the keys)."""
        if not isinstance(value, Mapping):
            raise RequestError(f"{what} maps model parameter names to numbers, not {value!r}")
        out: dict[str, float] = {}
        for name, v in value.items():
            if not isinstance(name, str):
                raise RequestError(f"{what}: a model parameter's name is text, not {name!r}")
            out[name] = as_double(v, f"{what}: model parameter {name}")
        return out

    def schema(self) -> Mapping[str, Any]:
        """Return an object of numbers."""
        return {"type": "object", "additionalProperties": {"type": "number"}}


@dataclass(frozen=True)
class Name:
    """One of the names a registry holds now (a sampler, a basis), or of a fixed list."""

    choices: Callable[[], Sequence[str]]

    def read(self, value: Any, what: str) -> str:
        """Return the name; refuse one that isn't a choice, naming the choices."""
        known = tuple(self.choices())
        if not isinstance(value, str) or value not in known:
            raise RequestError(f"{what} is one of {', '.join(known)}, not {value!r}")
        return value

    def schema(self) -> Mapping[str, Any]:
        """Return a string among the choices."""
        return {"type": "string", "enum": list(self.choices())}


@dataclass(frozen=True)
class GivenLines:
    """Given lines: a non-empty list of ``{"anchor": {...}, "direction": {...}}``, values as doubles, or None."""

    def read(self, value: Any, what: str) -> list[dict[str, dict[str, float]]] | None:
        """Return the lines with each anchor and direction read by ``Point``; None stays None."""
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or not value:
            raise RequestError(f'{what}: a non-empty list of lines, each {{"anchor": {{...}}, "direction": {{...}}}}')
        lines = []
        for k, line in enumerate(value):
            if not isinstance(line, Mapping) or not set(line) <= {"anchor", "direction"} or "direction" not in line:
                raise RequestError(f'{what}[{k}]: a line is {{"anchor": {{...}}, "direction": {{...}}}}, not {line!r}')
            read = {"direction": Point().read(line["direction"], f"{what}[{k}].direction")}
            if "anchor" in line:
                read["anchor"] = Point().read(line["anchor"], f"{what}[{k}].anchor")
            lines.append(read)
        return lines

    def schema(self) -> Mapping[str, Any]:
        """Return a list of lines, or null."""
        point = Point().schema()
        line = {"type": "object", "properties": {"anchor": point, "direction": point}, "required": ["direction"]}
        return {"anyOf": [{"type": "array", "items": line, "minItems": 1}, {"type": "null"}]}


@dataclass(frozen=True)
class DiagnosticParameter:
    """One row of a diagnostic spec's parameter table, but ``space`` and ``prediction`` (architecture.md §6).

    Attributes
    ----------
    name : str
        Its name, a keyword argument of ``run``.
    type : str
        The spec's Type column: "integer ≥ 0".
    default : Any or callable
        A value, or a rule ``default(d, others)`` of the number of varied model parameters and the other
        parameters, parsed (2P).
    default_text : str
        The spec's Default column: "4", "2(d + 1)".
    meaning : str
        The spec's Meaning column.
    changes_design : str
        The spec's "Changes the design?": "yes", "no", or its wording (C14).
    other_value : Any
        A second valid value, for C14's check.
    reader : Reader
        How a value is read and described.
    """

    name: str
    type: str
    default: Any
    default_text: str
    meaning: str
    changes_design: str
    other_value: Any
    reader: Reader

    def parse(self, value: Any) -> Any:
        r"""Read a value from Python, the CLI's text, or MCP's JSON into its canonical form (§7; C55).

        Text is read as JSON when it is JSON ("3", "{\\"a\\": 1}"), and as a bare string otherwise ("random"), as
        the CLI's ``--param k=v`` gives it; every form then goes through the reader.

        Raises
        ------
        RequestError
            Naming the diagnostic parameter, for a value that isn't valid.
        """
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        return self.reader.read(value, f"diagnostic parameter {self.name}")

    def json_schema(self) -> Mapping[str, Any]:
        """Return the value's JSON schema, with its meaning and default (C55)."""
        schema = dict(self.reader.schema())
        schema["description"] = f"{self.meaning} Default: {self.default_text}."
        if not callable(self.default):
            schema["default"] = self.default
        return schema

    def info(self) -> DiagnosticParameterInfo:
        """Return its description for ``describe_diagnostic`` (C55)."""
        return DiagnosticParameterInfo(
            name=self.name,
            type=self.type,
            default=None if callable(self.default) else self.default,
            default_text=self.default_text,
            meaning=self.meaning,
            changes_design=self.changes_design,
            json_schema=self.json_schema(),
        )


def seed_parameter(meaning: str, changes_design: str) -> DiagnosticParameter:
    """Return the ``seed`` row every diagnostic has: an integer >= 0, default 0, recorded (shared.md; 0061)."""
    return DiagnosticParameter("seed", "integer ≥ 0", 0, "0", meaning, changes_design, 1, Integer(0))


# --------------------------------------------------------------------------------------------------------------
# The interface


class Transform(Enum):
    """How a number changes under y -> a·y + b (C5)."""

    UNCHANGED = "unchanged"
    SCALED = "times a"
    AFFINE = "a·v + b"
    SCALED_ONLY = "unchanged under a·y only"


@dataclass(frozen=True)
class AnalysisContext:
    """What a diagnostic's ``compute`` and ``figures`` read beside the run batch (architecture.md §6).

    Attributes
    ----------
    request : Request
        The canonical request.
    spec : ModelSpec
        The model version's spec.
    space : ModelParameterSpace
        The request's space; the point run's, every model parameter held at the point (0049).
    interval_method : IntervalMethod or None
        From the registry by the diagnostic's ``interval_method``, so a fake replaces it (C19).
    measured_noisy : tuple of MeasuredNoisy
        Q10's records, newest first, or a provenance's on a replay (C16, 0055).
    on_progress : callable or None
        Called with the analysis's ``Progress``; an exception from it stops the evaluation (C49).
    """

    request: Request
    spec: ModelSpec
    space: ModelParameterSpace
    interval_method: IntervalMethod | None
    measured_noisy: tuple[MeasuredNoisy, ...] = ()
    on_progress: Callable[[Progress], None] | None = None

    @property
    def seed(self) -> int:
        """Return the request's seed (0 by default; shared.md, Random draws)."""
        return int(self.request.params.get("seed", 0))

    @property
    def prediction(self) -> PredictionSpec:
        """Return the model prediction analyzed."""
        return self.spec.prediction(self.request.prediction)

    def stream(self, tag: int) -> np.random.Generator:
        """Return the diagnostic's own stream: ``SeedSequence(seed, spawn_key=(tag,))`` (S8; uncertainty.md)."""
        if tag < SPAWN_TAG_BASE:
            raise ValueError(f"a diagnostic's spawn tag is at least 2**32, not {tag}")
        return spawned(self.seed, tag)

    def on_step(self, what: str) -> Callable[[int, int], None] | None:
        """Return an ``on_step(done, total)`` for an interval method that reports "what: done of total"."""
        report = self.on_progress
        if report is None:
            return None

        def step(done: int, total: int) -> None:
            report(Progress("analysis", done, total, f"{what}: {done} of {total} resamples"))

        return step


@dataclass(frozen=True)
class Computation:
    """What a diagnostic's ``compute`` returns (architecture.md §6).

    Attributes
    ----------
    estimates : tuple of EstimateTable
        None below the minimum or with a constant model prediction (P6).
    observations : tuple of ObservationTable
        A table keyed ``"shared"`` adds its rows before the shared ones, in the shared table (the point run's);
        the others follow it. None with no usable run.
    notes : tuple of Note
        The diagnostic's own notes, after the shared ones.
    header_rows : tuple of (str, str)
        Its own header rows (S2): the polynomial model's Fit.
    extra : tuple of EstimateTable
        Kept out of the report (0041).
    measured_noisy : MeasuredNoisy or None
        The point run's record; ``evaluate`` sets its result id, model version, and model prediction.
    """

    estimates: tuple[EstimateTable, ...] = ()
    observations: tuple[ObservationTable, ...] = ()
    notes: tuple[Note, ...] = ()
    header_rows: tuple[tuple[str, str], ...] = ()
    extra: tuple[EstimateTable, ...] = ()
    measured_noisy: MeasuredNoisy | None = None


class Diagnostic(Protocol):
    """What every diagnostic declares and does (architecture.md §6; contracts.md, Declared by each diagnostic).

    The declarations are read-only here, so a class attribute (``nesting = ("n",)``) meets them.
    """

    @property
    def name(self) -> str:
        """Its name: "scatter"."""
        ...

    @property
    def title(self) -> str:
        """Its title, for the report's (S1): "Scatter"."""
        ...

    @property
    def summary(self) -> str:
        """One line on what it does, for ``describe_diagnostic``."""
        ...

    @property
    def takes_space(self) -> bool:
        """False for the point run (U7)."""
        ...

    @property
    def parameters(self) -> tuple[DiagnosticParameter, ...]:
        """Every row of its spec's parameter table but ``space`` and ``prediction``."""
        ...

    @property
    def interval_method(self) -> str | None:
        """Its interval method's name, "bootstrap", or None (uncertainty.md, Per diagnostic)."""
        ...

    @property
    def spawn_tags(self) -> tuple[int, ...]:
        """Its own streams' spawn keys, each >= 2**32 (C8)."""
        ...

    @property
    def has_estimates(self) -> bool:
        """Whether its spec promises estimates (C9, C11)."""
        ...

    @property
    def header_rows(self) -> tuple[str, ...]:
        """The labels of its own header rows (C11): ("Fit",) or ()."""
        ...

    @property
    def constant_note(self) -> bool:
        """False for the point run: one value is its answer (PT6, C4)."""
        ...

    @property
    def nesting(self) -> tuple[str, ...]:
        """The diagnostic parameters whose smaller requests nest in larger ones (C15)."""
        ...

    def observation_scope(self, n_usable: int, batch: RunBatch) -> str:
        """Return the shared observations' label (C10): "Of the 200 usable runs"."""
        ...

    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]:
        """Return a number's change under y -> a·y + b, and whether it is computed through a logarithm (C5)."""
        ...

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return (figure name, panel index) -> the ``(n,)`` mask of the rows whose runs the panel draws (C12)."""
        ...

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return small, valid diagnostic parameters for d varied model parameters."""
        ...

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return the fewest usable runs for estimates (or observations), and why (C3)."""
        ...

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the design's identity, from the parsed parameters (record 0067's hand-off)."""
        ...

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return the diagnostic's own numbers and notes."""
        ...

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw the figures from the runs and the stored result only (P1, 0037)."""
        ...


#: The shared observations' keys and how they change under y -> a·y + b (shared.md, Observations; C5).
SHARED_TRANSFORMS: Mapping[str, Transform] = {
    "min": Transform.AFFINE,
    "max": Transform.AFFINE,
    "spread": Transform.SCALED_ONLY,
}


class DiagnosticBase:
    """Defaults a diagnostic may keep: the declarations' common values and the C-checks' lookups.

    A subclass sets ``name``, ``title``, ``summary``, ``parameters``, and the declarations that differ, a
    ``TRANSFORMS`` mapping ``(table key, key) -> (Transform, through a logarithm)`` for its own numbers, and
    writes ``min_runs``, ``design_identity``, ``compute``, and ``figures``.
    """

    name: str = ""
    title: str = ""
    summary: str = ""
    takes_space: bool = True
    parameters: tuple[DiagnosticParameter, ...] = ()
    interval_method: str | None = None
    spawn_tags: tuple[int, ...] = ()
    has_estimates: bool = True
    header_rows: tuple[str, ...] = ()
    constant_note: bool = True
    nesting: tuple[str, ...] = ()
    TRANSFORMS: ClassVar[Mapping[tuple[str, str], tuple[Transform, bool]]] = MappingProxyType({})

    def observation_scope(self, n_usable: int, batch: RunBatch) -> str:
        """Return "Of the n usable runs" (C10)."""
        return f"Of the {n_usable} usable runs"

    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]:
        """Return the declared change: the shared observations', then ``TRANSFORMS``'s (C5).

        Raises
        ------
        KeyError
            For a number the diagnostic didn't declare.
        """
        if table_key == "shared" and key in SHARED_TRANSFORMS:
            return SHARED_TRANSFORMS[key], False
        return self.TRANSFORMS[(table_key, key)]

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return no strips; a diagnostic whose panels have strips overrides it (C12)."""
        return {}

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return every parameter's default, but a seed of 1 (any valid request will do)."""
        return {"seed": 1}


# --------------------------------------------------------------------------------------------------------------
# The registry (0065)

_REGISTRY: dict[str, Diagnostic] = {}


def register(d: Diagnostic) -> None:
    """Add a diagnostic to the registry.

    Raises
    ------
    ValueError
        When its name is taken, or a spawn tag is below 2**32 or another registered diagnostic's (C8).
    """
    if d.name in _REGISTRY:
        raise ValueError(f"diagnostic {d.name} is already registered")
    taken = {t for other in _REGISTRY.values() for t in other.spawn_tags}
    for tag in d.spawn_tags:
        if tag < SPAWN_TAG_BASE or tag in taken:
            raise ValueError(f"diagnostic {d.name}'s spawn tag {tag} is below 2**32 or already used (C8)")
    _REGISTRY[d.name] = d


def unregister(name: str) -> None:
    """Remove a diagnostic from the registry (0065 item 1): for the tests, and a later plugin mechanism.

    Raises
    ------
    ValueError
        When no diagnostic has that name.
    """
    if name not in _REGISTRY:
        raise ValueError(f"no diagnostic {name} is registered")
    del _REGISTRY[name]


def get(name: str) -> Diagnostic:
    """Return the diagnostic named ``name``.

    Raises
    ------
    NotFound
        Naming the diagnostics there are.
    """
    if name not in _REGISTRY:
        raise NotFound(f"no diagnostic {name!r}; the diagnostics are {', '.join(names())}")
    return _REGISTRY[name]


def names() -> tuple[str, ...]:
    """Return the registered diagnostics' names, sorted."""
    return tuple(sorted(_REGISTRY))


def describe(d: Diagnostic) -> DiagnosticSummary:
    """Return a diagnostic's description, each parameter with its JSON schema (U1; C55)."""
    lines = [f"{d.name}: {d.summary}"]
    if d.takes_space:
        lines.append("  space: model parameter space, required")
    lines.append("  prediction: model prediction name, default the only one")
    for p in d.parameters:
        lines.append(f"  {p.name}: {p.type}, default {p.default_text}; {p.meaning}")
    return DiagnosticSummary(
        name=d.name,
        summary=d.summary,
        takes_space=d.takes_space,
        parameters=tuple(p.info() for p in d.parameters),
        text="\n".join(lines),
    )


# --------------------------------------------------------------------------------------------------------------
# The request (architecture.md §7, step 2) and the design's identity


def make_request(
    diagnostic: Diagnostic,
    spec: ModelSpec,
    space: Mapping[str, Any] | ModelParameterSpace | None = None,
    prediction: str | None = None,
    params: Mapping[str, Any] | None = None,
) -> Request:
    """Return the canonical request: the space parsed and checked, every parameter parsed, defaults filled in.

    Parameters
    ----------
    diagnostic
        The diagnostic.
    spec
        The model version's spec.
    space
        ``designs.md``'s JSON or Python form, or a space; None for the point run (U7).
    prediction
        The model prediction; None for the only one.
    params
        The diagnostic parameters given, as keyword arguments, the CLI's text, or MCP's JSON.

    Raises
    ------
    RequestError
        For a missing or extra space, an unknown model prediction or diagnostic parameter (naming the known
        ones), or a value that isn't valid (G15, M6).
    """
    given = dict(params or {})
    if diagnostic.takes_space and space is None:
        raise RequestError(f"{diagnostic.name.replace('_', ' ')} needs a model parameter space")
    if not diagnostic.takes_space and space is not None:
        raise RequestError(f"{diagnostic.name.replace('_', ' ')} takes no model parameter space")
    parsed_space = None
    if space is not None:
        parsed_space = space if isinstance(space, ModelParameterSpace) else ModelParameterSpace.parse(space)
        parsed_space.validate(spec)
    known = {p.name: p for p in diagnostic.parameters}
    unknown = sorted(set(given) - set(known))
    if unknown:
        raise RequestError(
            f"{diagnostic.name.replace('_', ' ')} has no diagnostic parameter {unknown[0]} "
            f"(its parameters: {', '.join(known) or 'none'})"
        )
    d = len(parsed_space.varied(spec)) if parsed_space is not None else 0
    out: dict[str, Any] = {name: known[name].parse(value) for name, value in given.items()}
    for p in diagnostic.parameters:
        if p.name not in out:
            default = p.default(d, dict(out)) if callable(p.default) else p.default
            out[p.name] = p.parse(default) if default is not None else None
    name = spec.prediction(prediction).name
    canonical = None if parsed_space is None else parsed_space.canonical()
    return Request(diagnostic=diagnostic.name, prediction=name, space=canonical, params=out)


def request_space(request: Request, spec: ModelSpec) -> ModelParameterSpace:
    """Return the request's space, or the point run's: every model parameter held at ``x`` (0049)."""
    if request.space is not None:
        return ModelParameterSpace.parse(request.space)
    return ModelParameterSpace.at_point(spec, request.params.get("x", {}))


def identity(
    kind: str,
    space: ModelParameterSpace,
    params: Mapping[str, Any],
    spec: ModelSpec,
    model_version_id: str,
    *,
    seed: int,
    sampler: str | None = None,
) -> DesignIdentity:
    """Return a design's identity in its one canonical form (0046, 0061; record 0067's hand-off).

    The space in its canonical form; the generator's parameters as parsed (integers as integers, alpha as its
    decimal text, values and directions as doubles); the seed as an integer; the sampler's and the generator's
    versions from their registries. A value of another type is refused, so two identities of one design can't
    differ in a type.

    Raises
    ------
    RequestError
        For a generator or sampler with no implementation.
    TypeError
        For a value that isn't canonical JSON data (a numpy number), or a seed that isn't an ``int``.
    """
    _check_canonical(params, "the design's parameters")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"a design's seed is an int, not {seed!r}")
    return DesignIdentity(
        model_version_id=model_version_id,
        kind=kind,
        space=dict(space.canonical()),
        params=dict(params),
        seed=seed,
        sampler=sampler,
        sampler_version=None if sampler is None else samplers.get(sampler).version,
        generator_version=generators.get(kind).version,
    )


def _check_canonical(value: Any, what: str) -> None:
    """Refuse what would make one design two identities: numpy numbers, bools as numbers, integral floats kept."""
    if isinstance(value, Mapping):
        for k, v in value.items():
            _check_canonical(v, f"{what}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check_canonical(v, f"{what}[{i}]")
    elif not (value is None or isinstance(value, (bool, str)) or type(value) in (int, float)):
        raise TypeError(f"{what} is {value!r}, of type {type(value).__name__}: not canonical JSON data")


# --------------------------------------------------------------------------------------------------------------
# Helpers the diagnostics share


def estimate(key: str, label: str, value: float, interval: Interval) -> Estimate:
    """Return an estimate with its variability interval, or "none" and the reason (0041)."""
    return Estimate(key=key, label=label, value=value, interval=interval.bounds, reason=interval.reason)


def interval_info(
    ctx: AnalysisContext, n_usable: int, *, distinct: str | None = None, undefined: Mapping[str, int] | None = None
) -> IntervalInfo:
    """Return the line under an estimates table: the method's name and settings, the seed, and ``distinct``.

    ``distinct`` names what is recomputed on the distinct runs of each resample ("the index"; record 0073 item 4).

    Raises
    ------
    ValueError
        With no interval method in the context.
    """
    method = ctx.interval_method
    if method is None:
        raise ValueError("this diagnostic evaluation has no interval method")
    settings: dict[str, Any] = {**dict(method.settings), "seed": ctx.seed}
    if distinct is not None:
        settings["distinct"] = distinct
    counts = {k: n for k, n in (undefined or {}).items() if n}
    return IntervalInfo(method=method.name, settings=settings, n_usable=n_usable, undefined=counts)


def library_versions() -> dict[str, str]:
    """Return the versions a result's reuse key and provenance hold: EMA, numpy, scipy, matplotlib (0062)."""
    return {name: metadata.version(name) for name in ("ema", "numpy", "scipy", "matplotlib")}


def make_provenance(
    batch: RunBatch,
    ctx: AnalysisContext,
    diagnostic: Diagnostic,
    model_version_id: str,
    *,
    approval_id: str | None,
    versions: Mapping[str, str],
) -> Provenance:
    """Return the provenance of a diagnostic evaluation on this batch (P5; data_model.md §5.9; 0063).

    The measured-noisy records read are the context's for this model version and model prediction; the design
    structure is the batch design's levels and lines.
    """
    design = batch.design
    if design.identity is None:
        raise ValueError("a diagnostic evaluation's design has an identity (the test run's has none)")
    return Provenance(
        ema=versions["ema"],
        numpy=versions["numpy"],
        scipy=versions["scipy"],
        matplotlib=versions["matplotlib"],
        model_version_id=model_version_id,
        request=ctx.request,
        design=design.identity,
        run_ids=batch.runs.run_ids,
        approval_id=approval_id,
        spawn_tags=tuple(diagnostic.spawn_tags),
        measured_noisy_read=_noisy_records(ctx, model_version_id),
        design_structure=DesignStructure(levels=design.levels, lines=design.lines),
    )


def _noisy_records(ctx: AnalysisContext, model_version_id: str) -> tuple[MeasuredNoisy, ...]:
    return tuple(
        m
        for m in ctx.measured_noisy
        if m.model_version_id == model_version_id and m.prediction == ctx.request.prediction
    )


# --------------------------------------------------------------------------------------------------------------
# The precheck (shared.md, The precheck; P6)


@dataclass(frozen=True, eq=False)
class Precheck:
    """What the shared precheck found, before ``compute`` (shared.md; S5-S7).

    Attributes
    ----------
    counts : Counts
        The header's runs, over distinct runs.
    usable : numpy.ndarray
        ``(n,)`` bools: the design rows whose run is usable.
    n_usable : int
        Distinct usable runs.
    minimum : int
        The diagnostic's minimum, and ``why``.
    why : str
        Why that minimum.
    constant : bool
        Every usable run gives the same double, with at least two (0035).
    estimates_allowed : bool
        At least the minimum, at least one usable run, and not constant where the diagnostic notes it.
    notes : tuple of Note
        The shared notes, but the measured-noisy ones.
    """

    counts: Counts
    usable: np.ndarray
    n_usable: int
    minimum: int
    why: str
    constant: bool
    estimates_allowed: bool
    notes: tuple[Note, ...] = field(default=())


def _with_units(text: str, units: str) -> str:
    return f"{text} {units}" if units else text


def _reasons(batch: RunBatch, prediction: str, firsts: np.ndarray, not_usable: np.ndarray) -> list[str]:
    """Return the note's lines of reasons: at most 5, by count, ties by the first run in design order (S7, 0051)."""
    runs = batch.runs
    ids = hex_ids(runs.run_ids[firsts[not_usable]])
    missing = runs.missing.get(prediction, {})
    counted: dict[str, int] = {}
    for run in ids:  # in design order, so dict order breaks ties
        reason = runs.reasons.get(run) or missing.get(run) or f"{prediction} not read"
        counted[reason] = counted.get(reason, 0) + 1
    ranked = sorted(counted.items(), key=lambda item: -item[1])
    shown, rest = ranked[:NOTE_MAX_REASONS], ranked[NOTE_MAX_REASONS:]
    width = len(str(max(n for _, n in ranked)))
    lines = [f"  {n:>{width}}  {reason}" for reason, n in shown]
    if rest:
        others = sum(n for _, n in rest)
        lines.append(f"  {others:>{width}}  ({len(rest)} other reasons)")
    return lines


def precheck(
    diagnostic: Diagnostic, batch: RunBatch, ctx: AnalysisContext, result_id: str
) -> tuple[Precheck, np.ndarray]:
    """Run the shared precheck: count the runs, decide the minimum and "constant", and write the shared notes.

    Returns the precheck and the usable runs' values, one per usable design row.
    """
    p = ctx.request.prediction
    units = ctx.prediction.units
    runs = batch.runs
    _, firsts = np.unique(runs.run_ids, return_index=True)
    firsts = np.sort(firsts)  # each distinct run's first row, in design order
    usable_rows = batch.usable(p)
    ok = runs.status[firsts] == RunStatus.OK.code
    usable = usable_rows[firsts]
    is_new = np.isin(runs.run_ids[firsts], runs.run_ids[batch.new])  # a run is new when any of its rows is
    new_runs = int(is_new.sum())
    kinds = runs.kind[firsts]
    failed = {kind: int((kinds == kind.code).sum()) for kind in FailureKind}
    n_runs, n_usable = len(firsts), int(usable.sum())
    counts = Counts(
        rows=len(batch.design),
        runs=n_runs,
        new=new_runs,
        reused=n_runs - new_runs,
        failed=failed,
        missing=int((ok & ~usable).sum()),
        usable=n_usable,
    )
    y = runs.values[p][usable_rows]
    d = len(ctx.space.varied(ctx.spec))
    minimum, why = diagnostic.min_runs(d, ctx.request.params)
    constant = n_usable >= 2 and is_constant(y)
    estimates_allowed = n_usable >= max(minimum, 1) and not (constant and diagnostic.constant_note)

    notes: list[Note] = []
    not_usable = ~usable
    if not_usable.any():
        parts = [f"{failed[k]} failed ({k.value})" for k in FailureKind if failed[k]]
        if counts.missing:
            parts.append(f"{counts.missing} missing {p}")
        k = int(not_usable.sum())
        lines = [f"{k} of {n_runs} runs {'is' if k == 1 else 'are'} not usable for {p}: {', '.join(parts)}."]
        lines += ["Most frequent reasons:", *_reasons(batch, p, firsts, not_usable)]
        listed = f'`ws.failed_runs("{result_id[:12]}")` lists each one.'
        if n_usable:
            what = "Estimates" if diagnostic.has_estimates and estimates_allowed else "Observations"
            listed = f"{what} use the {n_usable} usable runs. {listed}"
        lines.append(listed)
        notes.append(Note("not_usable", "\n".join(lines)))
    reused_failed = int((~is_new & ~ok).sum())
    if reused_failed:
        notes.append(
            Note(
                "reused_failed",
                f"{reused_failed} of the {counts.reused} reused runs had failed before; "
                "`retry_failed=True` runs them again.",
            )
        )
    name = diagnostic.name.replace("_", " ")
    if n_usable == 0 and not ok.any():
        nothing = "estimates or observations" if diagnostic.has_estimates else "observations"
        notes.append(Note("all_failed", f"All {n_runs} runs failed: no {nothing}."))
    elif n_usable == 0:
        notes.append(
            Note("no_usable", f"No run is usable for {p}: {sum(failed.values())} failed, {counts.missing} missing {p}.")
        )
    elif n_usable < minimum:
        notes.append(Note("too_few", f"{n_usable} usable runs; {name} needs at least {minimum} ({why})."))
    if constant and diagnostic.constant_note:
        value = _with_units(fmt(float(y[0])), units)
        notes.append(Note("constant", f"{p} is the same in all {n_usable} usable runs: {value}."))
    found = Precheck(counts, usable_rows, n_usable, minimum, why, constant, estimates_allowed, tuple(notes))
    return found, y


def _noisy_notes(ctx: AnalysisContext, model_version_id: str, y: np.ndarray) -> list[Note]:
    """One note per point run that measured this model version noisy in this model prediction (P7; point_run.md)."""
    p, units = ctx.request.prediction, ctx.prediction.units
    label = model_version_label(ctx.spec.name, model_version_id)
    nominal = tuple(q.nominal for q in ctx.spec.parameters)
    notes = []
    for m in _noisy_records(ctx, model_version_id):
        if m.point == nominal:
            where = "the nominal point"
        else:
            where = "the point " + ", ".join(
                f"{q.name} = {fmt(v)}" for q, v in zip(ctx.spec.parameters, m.point, strict=True)
            )
        text = f"{label} was measured noisy in {p} by point run {m.result_id[:12]} ({m.runs} runs at {where}): "
        if m.std is None:
            text += "standard deviation none (one usable run; the failures vary), so no fraction of the range."
        elif not len(y):
            text += f"standard deviation {_with_units(fmt(m.std), units)}; no usable run here, so no fraction."
        else:
            spread = float(np.max(y) - np.min(y))
            std = _with_units(fmt(m.std), units)
            if spread == 0.0:
                text += f"standard deviation {std}; the range of {p} in this diagnostic's runs is 0, so no fraction."
            else:
                text += (
                    f"standard deviation {std}, {fmt(m.std / spread)} of the range of {p} in this diagnostic's runs "
                    f"({_with_units(fmt(spread), units)})."
                )
        notes.append(Note("measured_noisy", text))
    return notes


def _shared_rows(y: np.ndarray, units: str) -> tuple[tuple[Observation, ...], ...]:
    lo, hi = float(np.min(y)), float(np.max(y))
    top = float(np.max(np.abs(y)))
    spread = (hi - lo) / top if top > 0.0 else 0.0
    return (
        (Observation("min", "Minimum", lo, units),),
        (Observation("max", "Maximum", hi, units),),
        (Observation("spread", "(max - min) / max|y|", spread, ""),),
    )


# --------------------------------------------------------------------------------------------------------------
# evaluate (architecture.md §6, §7 step 8)


def evaluate(
    diagnostic: Diagnostic,
    batch: RunBatch,
    ctx: AnalysisContext,
    provenance: Provenance,
    result_id: str,
    out_dir: str,
) -> DiagnosticResult:
    """Run one diagnostic evaluation's analysis: the precheck, ``compute``, the result, then its figures.

    The only entry point (architecture.md §6). The shared precheck counts the runs (S2, over distinct runs),
    decides the minimum and "constant" (P6, 0035), and writes the shared notes (S7) and observations (C10);
    ``compute`` gets ``estimates_allowed`` False below the minimum or with a constant model prediction (C3, C4),
    and is refused estimates then, and any estimate or observation with no usable run (C1). The result is
    round-tripped through its JSON (C17), and the figures are drawn from that copy into ``out_dir`` (P1).

    Parameters
    ----------
    diagnostic
        The diagnostic, from the registry.
    batch
        The runs, one per design row, in design order (C56).
    ctx
        The request, the spec, the space, the interval method, the measured-noisy records, the progress callback.
    provenance
        The provenance the workspace built (``make_provenance``); its request and spawn tags are checked.
    result_id
        The SHA-256 of the reuse key (data_model.md §3.4).
    out_dir
        Where the figures are written.

    Raises
    ------
    ValueError
        For a provenance of another request or other spawn tags, or a computation that breaks P6.
    """
    if diagnostic.name != ctx.request.diagnostic:
        raise ValueError(f"the request is for {ctx.request.diagnostic}, not {diagnostic.name}")
    if provenance.request != ctx.request or tuple(provenance.spawn_tags) != tuple(diagnostic.spawn_tags):
        raise ValueError("the provenance is of another request, or records other spawn tags (P5, C8)")
    pre, y = precheck(diagnostic, batch, ctx, result_id)
    computed = diagnostic.compute(batch, ctx, estimates_allowed=pre.estimates_allowed)
    if (computed.estimates or computed.extra) and not pre.estimates_allowed:
        raise ValueError(
            f"{diagnostic.name} made estimates with {pre.n_usable} usable runs, below its minimum of "
            f"{pre.minimum} or of a constant model prediction (P6)"
        )
    if pre.n_usable == 0 and computed.observations:
        raise ValueError(f"{diagnostic.name} made observations of no usable run (P6)")
    observations: list[ObservationTable] = []
    if pre.n_usable:
        own = [t for t in computed.observations if t.key == "shared"]
        title = diagnostic.observation_scope(pre.n_usable, batch)
        rows = tuple(row for t in own for row in t.rows) + _shared_rows(y, ctx.prediction.units)
        observations.append(ObservationTable("shared", title, (title, ctx.request.prediction), rows))
        observations += [t for t in computed.observations if t.key != "shared"]
    measured = computed.measured_noisy
    if measured is not None:
        measured = dataclasses.replace(
            measured,
            result_id=result_id,
            model_version_id=provenance.model_version_id,
            prediction=ctx.request.prediction,
        )
    notes = (*pre.notes, *_noisy_notes(ctx, provenance.model_version_id, y), *computed.notes)
    result = DiagnosticResult(
        result_id=result_id,
        diagnostic=diagnostic.name,
        title=diagnostic.title,
        model_version_id=provenance.model_version_id,
        prediction=ctx.request.prediction,
        counts=pre.counts,
        header_rows=computed.header_rows,
        notes=notes,
        estimates=computed.estimates,
        observations=tuple(observations),
        figures=(),
        extra=computed.extra,
        measured_noisy=measured,
        provenance=provenance,
    )
    stored = DiagnosticResult.from_json(result.to_json())
    figures = tuple(diagnostic.figures(batch, stored, ctx, out_dir))
    return dataclasses.replace(stored, figures=figures)
