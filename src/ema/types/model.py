"""A model spec, one dataclass per part, and its JSON form (model_interface.md; architecture.md §3, model.py).

Values in model parameter units are doubles wherever they are built (0061 item 6): an ``int`` becomes a
``float``, and a bool or anything that isn't a finite number is refused (0065), so a spec built in Python agrees
with one parsed from JSON. ``ModelSpec.from_json`` makes every check that needs no file (names, ``noisy: true``, the
``ema_`` prefix, unknown keys, and the trust boundary's checks of a spec, whose lists live here; M18, M21; trust.md
T7, T8, and T2's spec checks); the checks that need files (an input deck's template names, a function file's
imports, a link to a credentials file; M10, M17) are ``ema.models``'s (trust.md, Where the rules live).
"""

import json
import keyword
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal, NoReturn

from ema.types._values import as_double, as_int, is_number
from ema.types.errors import RequestError, SpecError
from ema.types.identity import canonical_json

#: The parts of a variable name, split at "_" and case-folded, that make it look like a credential, refused in
#: ``env`` and ``pass_env`` (trust.md T8, 0057 item 2).
CREDENTIAL_WORDS = frozenset(
    {"key", "apikey", "token", "secret", "password", "passwd", "passphrase", "credential", "credentials", "auth"}
)

#: EMA's own files in a run directory, refused as a deck's ``writes`` or a listed file, in any case (trust.md T7).
EMA_FILE_NAMES = ("point.json", "run.json", "predictions.json", "stdout.txt", "stderr.txt")

# Credentials files (trust.md, Paths; 0057 item 4), rewritten from v1's lists, without its ".key" suffix (LS-DYNA
# keyword decks use it). Compared case-folded.
_SECRET_NAMES = frozenset(
    {
        # logins, tokens, and service configurations that hold them
        ".netrc", "_netrc", ".pgpass", ".pypirc", ".npmrc", ".yarnrc", ".htpasswd", ".vault-token", ".boto",
        ".s3cfg", ".dockercfg", "kubeconfig", ".my.cnf", ".envrc",
        # private SSH keys
        "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "id_ecdsa_sk", "id_ed25519_sk",
        # shell start-up files, which often export keys, and history files
        ".profile", ".bashrc", ".bash_profile", ".bash_login", ".bash_logout", ".zshrc", ".zshenv", ".zprofile",
        ".zlogin", ".cshrc", ".tcshrc", ".kshrc", ".bash_history", ".zsh_history", ".sh_history", ".histfile",
        ".python_history", ".psql_history", ".mysql_history", ".sqlite_history", ".node_repl_history",
    }
)  # fmt: skip
_SECRET_WORDS = frozenset({"credential", "credentials", "secret", "secrets"})
_SECRET_SUFFIXES = frozenset({".pem", ".p8", ".p12", ".pfx", ".ppk", ".jks", ".keystore", ".kdbx", ".gpg", ".tfvars"})
_SECRET_DIRECTORIES = (
    ".ssh", ".aws", ".azure", ".gnupg", ".docker", ".kube", ".password-store", ".config/gcloud", ".config/gh",
    ".config/op",
)  # fmt: skip
_ENV_TEMPLATES = frozenset({".env.example", ".env.sample", ".env.template"})
_HIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
_HIDDEN_ALLOWED = frozenset({"\t", "\u200c", "\u200d"})
_VARIABLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MODEL_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")  # a lowercase model name (0086 item 3)


def hidden_character(text: str) -> str | None:
    """Return the first hidden character in ``text``, or None (trust.md T7, 0057 item 4).

    Hidden: Unicode's Cc (but tab), Cf (but the joiners U+200C and U+200D), Cs, Zl, and Zp. A line feed is
    hidden, so a string with none is one line.

    Examples
    --------
    >>> hidden_character("T_max = 1"), hidden_character("a" + chr(0x202E) + "b") == chr(0x202E)
    (None, True)
    """
    for ch in text:
        if ch not in _HIDDEN_ALLOWED and unicodedata.category(ch) in _HIDDEN_CATEGORIES:
            return ch
    return None


def is_credentials_file(path: str) -> bool:
    """Tell whether a "/"-separated path names a credentials file (trust.md, Paths; T7; 0057 item 4).

    By its name: ``.env`` and ``*.env`` and ``.env.*`` (but ``.env.example``, ``.env.sample``, ``.env.template``);
    a login, key, shell start-up, or history file (``.netrc``, ``id_rsa``, ``.zshrc``); a name with
    ``credential(s)`` or ``secret(s)`` as a word part, split at ".", "_", and "-"; a key or certificate suffix
    (``.pem``, ``.p12``, but not ``.key``). Or by a directory in it: ``.ssh``, ``.aws``, ``.gnupg``,
    ``.config/gcloud``, …. Only the path given is matched: a spec's paths below the model's directory, or a link's
    whole target outside it (``ema.models.files``). Names are compared case-folded.

    Examples
    --------
    >>> [is_credentials_file(p) for p in (".ssh/id_rsa", "db-credentials.json", "secretion.py", "deck.key")]
    [True, True, False, False]
    """
    parts = [p.casefold() for p in path.split("/") if p not in ("", ".")]
    if not parts:
        return False
    name = parts[-1]
    if name.endswith(".env") or (name.startswith(".env.") and name not in _ENV_TEMPLATES):
        return True
    dot = name.rfind(".")
    if name in _SECRET_NAMES or _SECRET_WORDS & set(re.split(r"[._-]", name)):
        return True
    if dot > 0 and name[dot:] in _SECRET_SUFFIXES:
        return True
    directories = "/" + "/".join(parts[:-1]) + "/"
    return any(f"/{d}/" in directories for d in _SECRET_DIRECTORIES)


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

    @classmethod
    def from_json(cls, text: str) -> "ModelSpec":
        """Read a model spec from its JSON text, making every check that needs no file.

        The checks (model_interface.md, The model spec; architecture.md §3's field table): required fields, and
        every unknown key, or a key of the other interface, refused; names (a lowercase model name; model
        parameter and model prediction names ASCII Python identifiers, unique across both lists, none starting
        with ``ema_``; M21); ``noisy: true`` refused (M18); nominal values inside their limits; each parser's
        settings. The trust boundary's checks (trust.md): duplicate keys, and strings (keys included) with a hidden
        character (T7); paths relative, with no ``..``, normalized to "/"-separated parts; credentials files (every
        path, a parser's ``file`` and a deck's ``writes`` included), EMA's own file names as a deck's ``writes`` or
        a listed file, and two run-directory paths that collide, case-folded (T7); ``env`` and ``pass_env`` names,
        credential-like ones refused, and no name in both (T8); an ``env`` ``PATH``'s entries absolute (T2).

        Parameters
        ----------
        text
            The spec's JSON.

        Returns
        -------
        ModelSpec
            Values in model parameter units as doubles.

        Raises
        ------
        SpecError
            Naming the field, as a path such as ``parameters[0].limits.gt``.
        """
        try:
            data = json.loads(text, object_pairs_hook=_JsonObject.of, parse_constant=_Constant)
            _check_strings(data, "")
        except json.JSONDecodeError as e:
            raise SpecError(f"the model spec is not JSON: {e}") from None
        except RecursionError:
            raise SpecError("the model spec is nested too deeply to be a model spec") from None
        return _read_spec(data)

    def to_json(self) -> str:
        """Write the spec as JSON text: every field, each default filled in, paths with "/", indented 2 spaces.

        ``from_json`` reads it back equal. This is the text ``save_spec`` writes and a confirmation shows (T6).
        """
        return json.dumps(_spec_object(self, settings=True), indent=2, ensure_ascii=False, allow_nan=False) + "\n"

    def versioned_json(self) -> str:
        """Write the canonical JSON the model version covers (data_model.md §3.4, 0029, M3).

        ``to_json``'s object without ``keep``, ``batch_size``, and ``timeout_s``: ``files`` and ``pass_env`` in the
        spec's order, which the model version's hash sorts (``version_hash``; 0086 item 4).
        """
        return canonical_json(_spec_object(self, settings=False))

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


# --------------------------------------------------------------------------------------------------------------
# The JSON form: reading (from_json) and writing (to_json, versioned_json)

_COMMON_KEYS = (
    "name", "description", "interface", "parameters", "predictions", "files", "env", "pass_env", "noisy", "keep",
    "batch_size", "timeout_s",
)  # fmt: skip
_INTERFACES = {
    "python_function": ("a Python function's model spec", ("function", "batch")),
    "command_line": ("a command-line model's spec", ("command", "input_decks")),
}
_OUTSIDE = (
    "paths in a model spec stay inside the model's directory: put a link to the file there, or move the spec up a "
    "directory"
)
_OUTSIDE_RUN = "paths in the run directory stay inside it"


class _JsonObject(dict[str, Any]):
    """A JSON object that remembers its first duplicate key (T7)."""

    duplicate: str | None = None

    @classmethod
    def of(cls, pairs: list[tuple[str, Any]]) -> "_JsonObject":
        obj = cls()
        for key, value in pairs:
            if key in obj and obj.duplicate is None:
                obj.duplicate = key
            obj[key] = value
        return obj


class _Constant:
    """``NaN``, ``Infinity``, or ``-Infinity`` in the text, kept until its field is known, then refused."""

    def __init__(self, name: str) -> None:
        self.name = name


def _fail(path: str, message: str) -> NoReturn:
    raise SpecError(f"{path or 'the model spec'}: {message}")


def _key(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _check_strings(value: Any, path: str) -> None:
    """Refuse duplicate keys, and hidden characters in every string, keys included (T7)."""
    if isinstance(value, dict):
        if isinstance(value, _JsonObject) and value.duplicate is not None:
            _fail(_key(path, value.duplicate), "the key appears twice in one object")
        for key, item in value.items():
            if hidden_character(key) is not None:
                _check_string(key, _key(path, ascii(key)))
            _check_strings(item, _key(path, key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_strings(item, f"{path}[{i}]")
    elif isinstance(value, str):
        _check_string(value, path)
    elif isinstance(value, _Constant):
        _fail(path, f"{value.name} is not a number a model spec may hold")


def _check_string(text: str, path: str) -> None:
    ch = hidden_character(text)
    if ch is not None:
        _fail(path, f"holds the hidden character U+{ord(ch):04X}; a spec's strings are one line, with none hidden")


def _object(value: Any, path: str, required: tuple[str, ...], optional: tuple[str, ...], what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "must be a JSON object")
    for key in value:
        if key not in required and key not in optional:
            _fail(_key(path, key), f"isn't a field of {what}")
    for key in required:
        if key not in value:
            _fail(_key(path, key), "is required")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        _fail(path, f"must be a string, not {value!r}")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, f"must be true or false, not {value!r}")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, f"must be a JSON list, not {value!r}")
    return value


def _relative(value: Any, path: str, outside: str) -> str:
    """Return a relative path's "/"-separated parts, with empty and "." parts dropped and no ".." (T7)."""
    text = _string(value, path)
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if text.startswith("/"):
        _fail(path, f"{text} is an absolute path; {outside}")
    if ".." in parts:
        _fail(path, f"{text} has a .. part; {outside}")
    if not parts:
        _fail(path, "is an empty path")
    return "/".join(parts)


def _model_path(value: Any, path: str) -> str:
    """Read a path relative to the model's directory, not a credentials file (T7)."""
    rel = _relative(value, path, _OUTSIDE)
    if is_credentials_file(rel):
        _fail(path, f"{rel} is a credentials file, which a model spec may not name")
    return rel


def _run_file(value: Any, path: str) -> str:
    """Read a file's path in the run directory: not a credentials file, nor one of EMA's own (T7).

    EMA's own files are at the top of the run directory, so a path whose first part is one of their names, in any
    case, is refused too.
    """
    rel = _relative(value, path, _OUTSIDE_RUN)
    if is_credentials_file(rel):
        _fail(path, f"{rel} is a credentials file, which a model spec may not name")
    if rel.split("/")[0].casefold() in EMA_FILE_NAMES:
        _fail(path, f"{rel} is the name of one of EMA's own files in a run directory")
    return rel


def _identifier(value: Any, path: str) -> str:
    """Read a model parameter's or a model prediction's name: an ASCII identifier, not a keyword (0069 item 26).

    ASCII, since Python reads a non-ASCII identifier in its NFKC form (``µ`` as ``μ``, ``ﬁ`` as ``fi``), so the
    name would fail as a keyword argument, and ``string.Template`` names are ASCII.
    """
    name = _string(value, path)
    if not _VARIABLE.fullmatch(name) or keyword.iskeyword(name):
        _fail(path, f"{name!r} must be an ASCII Python identifier ([A-Za-z_][A-Za-z0-9_]*), and not a keyword")
    if name.startswith("ema_"):
        _fail(path, f"{name} starts with ema_, the prefix of EMA's own columns in an export")
    return name


def _variable(value: Any, path: str) -> str:
    """Read an ``env`` or ``pass_env`` name: a variable name, not credential-like (T8)."""
    name = _string(value, path)
    if not _VARIABLE.fullmatch(name):
        _fail(path, f"{name!r} is not a variable name ([A-Za-z_][A-Za-z0-9_]*)")
    if CREDENTIAL_WORDS & {part.casefold() for part in name.split("_")}:
        _fail(path, f"{name} looks like a credential; a model reads its credentials from its tool's own file")
    return name


def _limits_text(limits: Limits) -> str:
    parts = []
    if limits.lower is not None:
        parts.append(f"{'gt' if limits.lower_strict else 'ge'} {limits.lower!r}")
    if limits.upper is not None:
        parts.append(f"{'lt' if limits.upper_strict else 'le'} {limits.upper!r}")
    return ", ".join(parts)


def _limits(value: Any, path: str) -> Limits:
    obj = _object(value, path, (), ("gt", "ge", "lt", "le"), "limits")
    if "gt" in obj and "ge" in obj or "lt" in obj and "le" in obj:
        _fail(path, "gives two lower or two upper limits")
    lower = next((k for k in ("gt", "ge") if k in obj), None)
    upper = next((k for k in ("lt", "le") if k in obj), None)
    return Limits(
        lower=None if lower is None else as_double(obj[lower], _key(path, lower), SpecError),
        lower_strict=lower == "gt",
        upper=None if upper is None else as_double(obj[upper], _key(path, upper), SpecError),
        upper_strict=upper == "lt",
    )


def _parameter(value: Any, path: str) -> ModelParameter:
    obj = _object(value, path, ("name", "units", "nominal", "description"), ("limits",), "a model parameter")
    limits = _limits(obj.get("limits", {}), _key(path, "limits"))
    nominal = as_double(obj["nominal"], _key(path, "nominal"), SpecError)
    if not limits.contains(nominal):
        _fail(_key(path, "nominal"), f"{nominal!r} is outside its limits ({_limits_text(limits)})")
    return ModelParameter(
        name=_identifier(obj["name"], _key(path, "name")),
        units=_string(obj["units"], _key(path, "units")),
        description=_string(obj["description"], _key(path, "description")),
        nominal=nominal,
        limits=limits,
    )


def _output_file(value: Any, path: str) -> str:
    """Read a parser's ``file``: ``stdout`` or ``stderr`` as written, or a file in the run directory (T7)."""
    text = _string(value, path)
    if text in ("stdout", "stderr"):
        return text
    rel = _relative(text, path, _OUTSIDE_RUN)
    if rel in ("stdout", "stderr"):
        _fail(path, f"{text!r} reads as the stream {rel}; write {rel} for the stream")
    if is_credentials_file(rel):
        _fail(path, f"{rel} is a credentials file, which a model spec may not name")
    return rel


def _parser(value: Any, path: str) -> ParserSpec:
    """Read an output parser's settings, checked as far as they can be without a run (0027)."""
    kind = value.get("kind") if isinstance(value, dict) else None
    if kind == "regex":
        obj = _object(value, path, ("kind", "file", "pattern"), ("match",), "a regex parser")
        pattern = _string(obj["pattern"], _key(path, "pattern"))
        try:
            groups = re.compile(pattern)
        except re.error as e:
            _fail(_key(path, "pattern"), f"isn't a regular expression: {e}")
        if groups.groups != 1 and "value" not in groups.groupindex:
            _fail(_key(path, "pattern"), "needs one group, or a group named value")
        match = obj.get("match", "last")
        if match not in ("first", "last"):
            _fail(_key(path, "match"), f"must be first or last, not {match!r}")
        return RegexParser(file=_output_file(obj["file"], _key(path, "file")), pattern=pattern, match=match)
    if kind == "json":
        obj = _object(value, path, ("kind", "file", "key"), (), "a json parser")
        key = _string(obj["key"], _key(path, "key"))
        if "" in key.split("."):
            _fail(_key(path, "key"), f"{key!r} has an empty part")
        return JsonParser(file=_output_file(obj["file"], _key(path, "file")), key=key)
    if kind == "csv":
        obj = _object(value, path, ("kind", "file", "column"), ("row", "delimiter"), "a csv parser")
        column = obj["column"]
        if not (isinstance(column, str) and column) and not is_number(column):
            _fail(_key(path, "column"), f"must be a header or an index, not {column!r}")
        if is_number(column):
            column = as_int(column, _key(path, "column"), -(2**63), SpecError)
        delimiter = _string(obj.get("delimiter", ","), _key(path, "delimiter"))
        if len(delimiter) != 1:
            _fail(_key(path, "delimiter"), f"must be one character, not {delimiter!r}")
        return CsvParser(
            file=_output_file(obj["file"], _key(path, "file")),
            column=column,
            row=as_int(obj.get("row", -1), _key(path, "row"), -(2**63), SpecError),
            delimiter=delimiter,
        )
    if not isinstance(value, dict):
        _fail(path, "must be a JSON object")
    _fail(_key(path, "kind"), f"must be regex, json, or csv, not {kind!r}")


def _prediction(value: Any, path: str, command_line: bool) -> PredictionSpec:
    required = ("name", "units", "description") + (("parser",) if command_line else ())
    what = "a command-line model's prediction" if command_line else "a Python function's model prediction"
    obj = _object(value, path, required, (), what)
    return PredictionSpec(
        name=_identifier(obj["name"], _key(path, "name")),
        units=_string(obj["units"], _key(path, "units")),
        description=_string(obj["description"], _key(path, "description")),
        parser=_parser(obj["parser"], _key(path, "parser")) if command_line else None,
    )


def _function(value: Any) -> str:
    text = _string(value, "function")
    file, _, name = text.rpartition(":")
    if not file or not name.isidentifier() or keyword.iskeyword(name):
        _fail("function", f"{text!r} must be file.py:f, with f a function's name")
    if unicodedata.normalize("NFKC", name) != name:
        _fail("function", f"{name!r} is read by Python as {unicodedata.normalize('NFKC', name)!r}; write that name")
    rel = _model_path(file, "function")
    if not rel.endswith(".py"):
        _fail("function", f"{file} is not a .py file")
    return f"{rel}:{name}"


def _interface(obj: dict[str, Any]) -> PythonFunction | CommandLine:
    if obj["interface"] == "python_function":
        return PythonFunction(function=_function(obj["function"]), batch=_bool(obj.get("batch", False), "batch"))
    command = _list(obj["command"], "command")
    if not command:
        _fail("command", "needs the program, then its arguments")
    words = tuple(_string(c, f"command[{i}]") for i, c in enumerate(command))
    if not words[0]:
        _fail("command[0]", "the program is empty")
    decks = []
    for i, deck in enumerate(_list(obj.get("input_decks", []), "input_decks")):
        path = f"input_decks[{i}]"
        d = _object(deck, path, ("template", "writes"), (), "an input deck")
        decks.append(
            InputDeck(_model_path(d["template"], f"{path}.template"), _run_file(d["writes"], f"{path}.writes"))
        )
    return CommandLine(command=words, input_decks=tuple(decks))


def _files(value: Any) -> tuple[FileEntry, ...]:
    entries: list[FileEntry] = []
    for i, item in enumerate(_list(value, "files")):
        path = f"files[{i}]"
        if isinstance(item, str):
            entry = FileEntry(_run_file(_model_path(item, path), path))
        else:
            obj = _object(item, path, ("path",), ("shared",), "a files entry")
            rel = _run_file(_model_path(obj["path"], f"{path}.path"), f"{path}.path")
            entry = FileEntry(rel, _bool(obj.get("shared", False), f"{path}.shared"))
        _check_overlap(entry.path, [e.path for e in entries], path, "listed")
        entries.append(entry)
    return tuple(entries)


def _check_overlap(rel: str, taken: list[str], path: str, what: str) -> None:
    """Refuse a run-directory path that is one already taken, or a directory of one, or below one (0069 item 31).

    Compared case-folded, as a case-insensitive file system would (T1).
    """
    folded = rel.casefold()
    for other in taken:
        theirs = other.casefold()
        if folded == theirs:
            _fail(path, f"{rel} is {other}, already {what}" if rel != other else f"{rel} is already {what}")
        if theirs.startswith(folded + "/") or folded.startswith(theirs + "/"):
            _fail(path, f"{rel} and {other}, already {what}, would be a file and a directory at once")


def _environment(obj: dict[str, Any]) -> tuple[dict[str, str], tuple[str, ...]]:
    """``env`` and ``pass_env`` (trust.md T2, T8; 0057 item 1)."""
    raw = obj.get("env", {})
    if not isinstance(raw, dict):
        _fail("env", "must be a JSON object of strings")
    env = {_variable(name, f"env.{name}"): _string(value, f"env.{name}") for name, value in raw.items()}
    for entry in env.get("PATH", "/").split(":"):
        if not entry.startswith("/"):
            _fail(
                "env.PATH",
                f"the entry {entry!r} is empty or relative; values are literal (no $PATH, no ~): each entry is an "
                "absolute directory",
            )
    names: list[str] = []
    for i, name in enumerate(_list(obj.get("pass_env", []), "pass_env")):
        name = _variable(name, f"pass_env[{i}]")
        if name in names:
            _fail(f"pass_env[{i}]", f"{name} is named twice")
        if name in env:
            _fail(f"pass_env[{i}]", f"{name} is in env too; a variable is set by the spec or passed, not both")
        names.append(name)
    return env, tuple(names)


def _read_spec(data: Any) -> "ModelSpec":
    """Read and check a parsed spec (ModelSpec.from_json)."""
    if not isinstance(data, dict):
        _fail("", "must be a JSON object")
    if "interface" not in data:
        _fail("interface", "is required")
    if not isinstance(data["interface"], str) or data["interface"] not in _INTERFACES:
        _fail("interface", f"must be python_function or command_line, not {data['interface']!r}")
    what, own = _INTERFACES[data["interface"]]
    required = ("name", "description", "interface", "parameters", "predictions", own[0])
    obj = _object(data, "", required, _COMMON_KEYS + own, what)

    name = _string(obj["name"], "name")
    if not _MODEL_NAME.fullmatch(name):
        _fail("name", f"{name!r} must start with a lowercase letter or digit, then lowercase letters, digits, _, or -")
    interface = _interface(obj)
    files = _files(obj.get("files", []))
    if isinstance(interface, CommandLine):
        taken = [f.path for f in files]
        for i, deck in enumerate(interface.input_decks):
            _check_overlap(deck.writes, taken, f"input_decks[{i}].writes", "listed in files or written by a deck")
            taken.append(deck.writes)
    env, pass_env = _environment(obj)

    params = [_parameter(p, f"parameters[{i}]") for i, p in enumerate(_list(obj["parameters"], "parameters"))]
    preds = [
        _prediction(p, f"predictions[{i}]", isinstance(interface, CommandLine))
        for i, p in enumerate(_list(obj["predictions"], "predictions"))
    ]
    if not params:
        _fail("parameters", "needs at least one model parameter")
    if not preds:
        _fail("predictions", "needs at least one model prediction")
    seen: dict[str, str] = {}
    for path, item in [(f"parameters[{i}]", p) for i, p in enumerate(params)] + [
        (f"predictions[{i}]", p) for i, p in enumerate(preds)
    ]:
        if item.name in seen:
            _fail(f"{path}.name", f"{item.name} is also {seen[item.name]}'s name; names are unique across both lists")
        seen[item.name] = path

    if _bool(obj.get("noisy", False), "noisy"):
        _fail("noisy", "true is refused: models declared noisy come in a later version")
    keep = _string(obj.get("keep", "all"), "keep")
    if keep not in {k.value for k in Keep}:
        _fail("keep", f"must be all, incomplete, or none, not {keep!r}")
    batch_size = obj.get("batch_size")
    if batch_size is not None:
        if not (isinstance(interface, PythonFunction) and interface.batch):
            _fail("batch_size", "is a setting of a batch Python function (batch: true) only")
        batch_size = as_int(batch_size, "batch_size", 1, SpecError)
    timeout_s = as_double(obj.get("timeout_s", 3600.0), "timeout_s", SpecError)
    if timeout_s <= 0:
        _fail("timeout_s", f"must be > 0, not {timeout_s!r}")
    return ModelSpec(
        name=name,
        description=_string(obj["description"], "description"),
        interface=interface,
        parameters=tuple(params),
        predictions=tuple(preds),
        files=files,
        env=env,
        pass_env=pass_env,
        keep=Keep(keep),
        batch_size=batch_size,
        timeout_s=timeout_s,
    )


def _parser_object(parser: ParserSpec) -> dict[str, Any]:
    if isinstance(parser, RegexParser):
        return {"kind": "regex", "file": parser.file, "pattern": parser.pattern, "match": parser.match}
    if isinstance(parser, JsonParser):
        return {"kind": "json", "file": parser.file, "key": parser.key}
    return {
        "kind": "csv",
        "file": parser.file,
        "column": parser.column,
        "row": parser.row,
        "delimiter": parser.delimiter,
    }


def _limits_object(limits: Limits) -> dict[str, float]:
    out = {}
    if limits.lower is not None:
        out["gt" if limits.lower_strict else "ge"] = limits.lower
    if limits.upper is not None:
        out["lt" if limits.upper_strict else "le"] = limits.upper
    return out


def _spec_object(spec: "ModelSpec", settings: bool) -> dict[str, Any]:
    """Return the spec as JSON data, each default filled in; the settings only when asked (0029)."""
    out: dict[str, Any] = {"name": spec.name, "description": spec.description}
    if isinstance(spec.interface, PythonFunction):
        out |= {"interface": "python_function", "function": spec.interface.function, "batch": spec.interface.batch}
    else:
        decks = [{"template": d.template, "writes": d.writes} for d in spec.interface.input_decks]
        out |= {"interface": "command_line", "command": list(spec.interface.command), "input_decks": decks}
    out["files"] = [{"path": f.path, "shared": f.shared} for f in spec.files]
    out["env"] = dict(spec.env)
    out["pass_env"] = list(spec.pass_env)
    out["parameters"] = [
        {
            "name": p.name,
            "units": p.units,
            "nominal": p.nominal,
            "description": p.description,
            "limits": _limits_object(p.limits),
        }
        for p in spec.parameters
    ]
    out["predictions"] = [
        {"name": p.name, "units": p.units, "description": p.description}
        | ({} if p.parser is None else {"parser": _parser_object(p.parser)})
        for p in spec.predictions
    ]
    out["noisy"] = spec.noisy
    if settings:
        out |= {"keep": spec.keep.value, "batch_size": spec.batch_size, "timeout_s": float(spec.timeout_s)}
    return out
