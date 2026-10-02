"""Requests and questions: what a diagnostic evaluation or the test run asks for, what EMA asks the user, progress.

architecture.md §3 (requests.py); data_model.md §3.4 (the canonical request); P3; trust.md (the questions'
fields); record 0070.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from ema.types._values import finite_doubles
from ema.types.design import _freeze, _thaw
from ema.types.identity import canonical_json
from ema.types.runs import Price
from ema.types.space import ModelParameterSpace


@dataclass(frozen=True)
class Request:
    """What one diagnostic evaluation is asked for (glossary), canonical, with defaults filled in (§3.4).

    The space is parsed and written in its canonical form (every range ``{"range": [lo, hi], "scale": ...}``,
    every value a double, 0061), so a space given in any of its forms makes the same request. The diagnostic
    parameters are as the diagnostic parsed them. A request whose canonical form isn't strict JSON is refused.

    Attributes
    ----------
    diagnostic : str
        The diagnostic's name.
    prediction : str
        The model prediction analyzed.
    space : Mapping[str, Any] or None
        The model parameter space, canonical; None for the point run (U7). Read-only.
    params : Mapping[str, Any]
        Every diagnostic parameter, the seed included. Read-only, nested values included.
    """

    diagnostic: str
    prediction: str
    space: Mapping[str, Any] | None
    params: Mapping[str, Any]

    def __post_init__(self) -> None:
        space = self.space
        if space is not None:
            parsed = space if isinstance(space, ModelParameterSpace) else ModelParameterSpace.parse(space)
            object.__setattr__(self, "space", _freeze(parsed.canonical()))
        if not all(isinstance(k, str) for k in self.params):
            raise ValueError(f"diagnostic parameters are named by text: {list(self.params)!r}")
        object.__setattr__(self, "params", _freeze(self.params))
        canonical_json(self.canonical())

    def canonical(self) -> Mapping[str, Any]:
        """Return ``{"diagnostic", "prediction", "space", "params"}`` as plain JSON data (§3.4; record 0070)."""
        return {
            "diagnostic": self.diagnostic,
            "prediction": self.prediction,
            "space": _thaw(self.space),
            "params": _thaw(self.params),
        }


@dataclass(frozen=True)
class TestRunRequest:
    """The test run's request (data_model.md §3.4; 0049): one run at the nominal point.

    Attributes
    ----------
    point : tuple of float
        The nominal point, every model parameter in the spec's order.
    """

    __test__ = False  # not a pytest test class, though its name starts with "Test"

    point: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", finite_doubles(self.point, "the test run's point"))

    def canonical(self) -> Mapping[str, Any]:
        """Return ``{"test_run": {"point": [...]}}``."""
        return {"test_run": {"point": list(self.point)}}


@dataclass(frozen=True)
class ApprovalRequest:
    """The question asked before new runs (P3; U2; trust.md): prints as its text, rendered by ``ema.approval``.

    Attributes
    ----------
    asked_for : str
        "diagnostic_evaluation" or "test_run".
    model_version : str
        The model version's label.
    price : Price
        The price.
    first_for_version : bool
        The model version's first approval: the details below are shown (U2).
    command : tuple of str or None
        A command-line model's command.
    program : str or None
        The resolved program path (0029).
    templates : Mapping[str, str]
        Each input deck template's name and text. Read-only.
    files : tuple of str
        The files copied or linked into each run directory.
    function : str or None
        A Python function's "file.py:f", shown in place of the command.
    env : Mapping[str, str]
        The spec's environment. Read-only.
    pass_env : Mapping[str, bool]
        Each name passed: whether it is set in EMA's environment; never its value. Read-only.
    text : str
        The whole question.
    """

    asked_for: Literal["diagnostic_evaluation", "test_run"]
    model_version: str
    price: Price
    first_for_version: bool
    command: tuple[str, ...] | None
    program: str | None
    templates: Mapping[str, str]
    files: tuple[str, ...]
    function: str | None
    env: Mapping[str, str]
    pass_env: Mapping[str, bool]
    text: str

    def __post_init__(self) -> None:
        if self.asked_for not in ("diagnostic_evaluation", "test_run"):
            raise ValueError(f"an approval is for a diagnostic evaluation or the test run, not {self.asked_for!r}")
        if self.command is not None:
            object.__setattr__(self, "command", tuple(self.command))
        object.__setattr__(self, "files", tuple(self.files))
        for name in ("templates", "env", "pass_env"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class ConfirmationRequest:
    """The question asked before saving a model spec an MCP client drafted (0049; T6): prints as its text.

    Attributes
    ----------
    spec_path : str
        Absolute, its parent resolved through its links (T6).
    replaces : str or None
        What the model's name means now, when it is loaded (0054).
    spec_text : str
        The file's exact text.
    text : str
        The whole question.
    """

    spec_path: str
    replaces: str | None
    spec_text: str
    text: str

    def __str__(self) -> str:
        return self.text


#: Answers a question: True for yes. An ``Exception`` it raises counts as no; ``KeyboardInterrupt`` passes through.
Approver = Callable[[ApprovalRequest | ConfirmationRequest], bool]


@dataclass(frozen=True)
class Progress:
    """How far a diagnostic evaluation has got: prints as its text.

    Attributes
    ----------
    phase : str
        "runs" or "analysis".
    done : int
        Steps done, 0 <= done <= total.
    total : int
        Steps in all.
    text : str
        "40/96 runs"; "bootstrap: 230 of 1000 refits, about 6 min left"; "A: 14161 × 1771, 200 MB" (PM10).
    """

    phase: Literal["runs", "analysis"]
    done: int
    total: int
    text: str

    def __post_init__(self) -> None:
        if self.phase not in ("runs", "analysis") or not 0 <= self.done <= self.total:
            raise ValueError(f"progress is in runs or analysis, with 0 <= done <= total: {self!r}")

    def __str__(self) -> str:
        return self.text

    @classmethod
    def of_runs(cls, done: int, total: int) -> "Progress":
        """Build the runs' progress line, "40/96 runs" (U2)."""
        return cls("runs", done, total, f"{done}/{total} runs")
