"""A model spec, one dataclass per part (model_interface.md; architecture.md §3, model.py).

Values in model parameter units are doubles wherever they are built (0061 item 6): an ``int`` becomes a
``float``, and a bool or anything that isn't a finite number is refused (0065), so a spec built in Python agrees
with one parsed from JSON. The JSON form (``from_json``, ``to_json``, ``versioned_json``) and its checks (names,
M18, M21, T7, T8, unknown keys) come with model loading (roadmap step 03).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Literal

from ema.types._values import as_double
from ema.types.errors import RequestError, SpecError


@dataclass(frozen=True)
class Limits:
    """A model parameter's limits, outside which the model isn't defined (0024); either may be left out.

    Attributes
    ----------
    lower : float or None
        The lower limit.
    lower_strict : bool
        "gt" when True, "ge" when False.
    upper : float or None
        The upper limit.
    upper_strict : bool
        "lt" when True, "le" when False.
    """

    lower: float | None = None
    lower_strict: bool = False
    upper: float | None = None
    upper_strict: bool = False

    def __post_init__(self) -> None:
        for name in ("lower", "upper"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, as_double(value, f"limit {name}", SpecError))

    def contains(self, x: float) -> bool:
        """Tell whether ``x`` satisfies both limits."""
        if self.lower is not None and (x <= self.lower if self.lower_strict else x < self.lower):
            return False
        return self.upper is None or (x < self.upper if self.upper_strict else x <= self.upper)


@dataclass(frozen=True)
class ModelParameter:
    """One of a model's variables whose value a design sets (0003, 0024).

    Attributes
    ----------
    name : str
        An identifier, unique in the spec.
    units : str
        "" when dimensionless.
    description : str
        What it is.
    nominal : float
        Its default or best-guess value, inside its limits.
    limits : Limits
        None by default.
    """

    name: str
    units: str
    description: str
    nominal: float
    limits: Limits = Limits()

    def __post_init__(self) -> None:
        object.__setattr__(self, "nominal", as_double(self.nominal, f"model parameter {self.name}: nominal", SpecError))


@dataclass(frozen=True)
class RegexParser:
    """Read a model prediction with a regular expression (0027).

    Attributes
    ----------
    file : str
        Relative to the run directory, or "stdout" or "stderr".
    pattern : str
        One group, or a group named "value".
    match : {"first", "last"}
        Which match to read.
    """

    file: str
    pattern: str
    match: Literal["first", "last"] = "last"


@dataclass(frozen=True)
class JsonParser:
    """Read a model prediction from a JSON file (0027).

    Attributes
    ----------
    file : str
        Relative to the run directory.
    key : str
        Dotted; integer parts index lists.
    """

    file: str
    key: str


@dataclass(frozen=True)
class CsvParser:
    """Read a model prediction from a CSV file (0027).

    Attributes
    ----------
    file : str
        Relative to the run directory.
    column : str or int
        A header name or an index.
    row : int
        -1, the last row, by default.
    delimiter : str
        "," by default.
    """

    file: str
    column: str | int
    row: int = -1
    delimiter: str = ","


ParserSpec = RegexParser | JsonParser | CsvParser


@dataclass(frozen=True)
class PredictionSpec:
    """A model prediction: a scalar with a name, units, and a description (0021, 0022).

    Attributes
    ----------
    name : str
        An identifier, unique in the spec.
    units : str
        Its units.
    description : str
        What it is.
    parser : RegexParser, JsonParser, CsvParser, or None
        Required for a command-line model, refused for a Python function.
    """

    name: str
    units: str
    description: str
    parser: ParserSpec | None = None


@dataclass(frozen=True)
class FileEntry:
    """A file every run needs, copied into each run directory, or linked when shared (0030).

    Attributes
    ----------
    path : str
        Relative to the spec's directory.
    shared : bool
        Stored once, read-only.
    """

    path: str
    shared: bool = False


@dataclass(frozen=True)
class PythonFunction:
    """A model that is a Python function (0014, 0025).

    Attributes
    ----------
    function : str
        "file.py:f".
    batch : bool
        Whether it takes a batch of points.
    """

    function: str
    batch: bool = False


@dataclass(frozen=True)
class InputDeck:
    """An input deck written from a template for each run (model_interface.md).

    Attributes
    ----------
    template : str
        The template's path.
    writes : str
        The file it writes, relative to the run directory, with no "..".
    """

    template: str
    writes: str


@dataclass(frozen=True)
class CommandLine:
    """A model that is a command-line program (0014).

    Attributes
    ----------
    command : tuple of str
        The program and its arguments.
    input_decks : tuple of InputDeck
        Written before each run.
    """

    command: tuple[str, ...]
    input_decks: tuple[InputDeck, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "command", tuple(self.command))
        object.__setattr__(self, "input_decks", tuple(self.input_decks))


class Keep(Enum):
    """Which run directories are kept (0020, 0028)."""

    ALL = "all"
    INCOMPLETE = "incomplete"
    NONE = "none"


@dataclass(frozen=True)
class ModelSpec:
    """The user's description of a model (model_interface.md; architecture.md §3).

    Attributes
    ----------
    name : str
        A lowercase model name.
    description : str
        What the model is.
    interface : PythonFunction or CommandLine
        How EMA runs it.
    parameters : tuple of ModelParameter
        At least one, in the spec's order, which every point's columns follow.
    predictions : tuple of PredictionSpec
        At least one.
    files : tuple of FileEntry
        Files every run needs.
    env : Mapping[str, str]
        Variables set in the model's environment (trust.md, 0057); read-only.
    pass_env : tuple of str
        Names passed from EMA's environment; their values are not in the model version.
    noisy : bool
        Only False in v2.0 (0021).
    keep : Keep
        A setting, not in the model version (0029).
    batch_size : int or None
        A setting: all of a design's new runs when None.
    timeout_s : float
        A setting: seconds per run.
    """

    name: str
    description: str
    interface: PythonFunction | CommandLine
    parameters: tuple[ModelParameter, ...]
    predictions: tuple[PredictionSpec, ...]
    files: tuple[FileEntry, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    pass_env: tuple[str, ...] = ()
    noisy: bool = False
    keep: Keep = Keep.ALL
    batch_size: int | None = None
    timeout_s: float = 3600.0

    def __post_init__(self) -> None:
        for name in ("parameters", "predictions", "files", "pass_env"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))

    def parameter(self, name: str) -> ModelParameter:
        """Return the model parameter named ``name``.

        Raises
        ------
        RequestError
            When the model has none by that name.
        """
        for p in self.parameters:
            if p.name == name:
                return p
        known = ", ".join(p.name for p in self.parameters)
        raise RequestError(f"{name} is not a model parameter of model {self.name} ({known})")

    def prediction(self, name: str | None) -> PredictionSpec:
        """Return the model prediction named ``name``; with None, the only one.

        Raises
        ------
        RequestError
            When the model has none by that name, or None is given and the model has several.
        """
        known = ", ".join(p.name for p in self.predictions)
        if name is None:
            if len(self.predictions) == 1:
                return self.predictions[0]
            raise RequestError(f"model {self.name} has several model predictions ({known}); name one")
        for p in self.predictions:
            if p.name == name:
                return p
        raise RequestError(f"{name} is not a model prediction of model {self.name} ({known})")
