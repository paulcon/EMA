"""Loading a model spec, a stored model, and saving a drafted spec (architecture.md §5, spec.py).

Loading reads the spec and checks it (``ModelSpec.from_json``), hashes its tracked files (``hash_files``), checks
the input deck templates' names (M10), and warns about unlisted local imports (M17) by parsing the function's file,
never importing it, so nothing of the model runs in EMA's process (trust.md, T4; 0057 item 8). ``resolve_program``
comes with the run phases (step 04).
"""

import ast
import os
import string
from dataclasses import dataclass

from ema.models.files import hash_files, leads_to_credentials, open_regular, same_file
from ema.types.errors import PathRefused, SpecError
from ema.types.identity import TrackedFile, version_hash
from ema.types.model import CommandLine, ModelSpec, PythonFunction, is_credentials_file


@dataclass(frozen=True)
class LoadedModel:
    """A model spec as loaded: its location, its tracked files' digests, and its model version.

    Attributes
    ----------
    spec : ModelSpec
        The spec, with the settings of its loading.
    spec_path : str
        The spec's path as given, made absolute (links not resolved, nothing normalized), for messages.
    model_dir : str
        The directory of the spec's file, its links resolved, which its paths are relative to.
    files : tuple of TrackedFile
        Hashed at loading, sorted by path.
    model_version_id : str
        ``version_hash(spec, files)``.
    warnings : tuple of str
        Unlisted local imports (M17); none for a stored model.
    """

    spec: ModelSpec
    spec_path: str
    model_dir: str
    files: tuple[TrackedFile, ...]
    model_version_id: str
    warnings: tuple[str, ...]


def _as_given(path: str) -> str:
    """Make a path absolute without normalizing it, so ``link/..`` isn't collapsed before the link is resolved."""
    return path if os.path.isabs(path) else os.path.join(os.getcwd(), path)


def _read_text(path: str, what: str) -> str:
    try:
        with open_regular(path) as f:
            return f.read().decode("utf-8")
    except FileNotFoundError:
        raise SpecError(f"{what}: {path} doesn't exist") from None
    except UnicodeDecodeError as e:
        raise SpecError(f"{what} isn't UTF-8 text: {e.reason} at byte {e.start}") from None
    except OSError as e:
        raise SpecError(f"{what}: {path} couldn't be read: {e.strerror}") from None


def _check_templates(spec: ModelSpec, model_dir: str) -> None:
    """M10: every ``$name`` and ``${name}`` names a model parameter; ``$$`` is a literal ``$``."""
    if not isinstance(spec.interface, CommandLine):
        return
    names = [p.name for p in spec.parameters]
    for i, deck in enumerate(spec.interface.input_decks):
        field = f"input_decks[{i}].template"
        text = _read_text(os.path.join(model_dir, *deck.template.split("/")), field)
        for m in string.Template.pattern.finditer(text):
            name = m.group("named") or m.group("braced")
            line = text.count("\n", 0, m.start()) + 1
            if m.group("invalid") is not None:
                raise SpecError(f"{field}: {deck.template} line {line}: a $ that isn't $name, ${{name}}, or $$")
            if name is not None and name not in names:
                known = ", ".join(names)
                raise SpecError(f"{field}: {deck.template} line {line}: ${name} is not a model parameter ({known})")


def _candidates(base: str, dotted: str) -> list[str]:
    """Return the files ``import a.b`` would run from ``base``: a.py, a/__init__.py, a/b.py, a/b/__init__.py."""
    parts = dotted.split(".")
    out = []
    for k in range(1, len(parts) + 1):
        stem = os.path.join(base, *parts[:k])
        out += [stem + ".py", os.path.join(stem, "__init__.py")]
    return out


def _imports(tree: ast.AST) -> list[ast.Import | ast.ImportFrom]:
    """Return the import statements in a parsed file, in source order."""
    nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    return sorted(nodes, key=lambda n: (n.lineno, n.col_offset))


def _unlisted_imports(spec: ModelSpec, model_dir: str, files: tuple[TrackedFile, ...]) -> tuple[str, ...]:
    """M17: each import in the function's file that resolves to an unlisted file in the model's directory.

    The file is parsed (``ast``), never imported (T4). Module names are resolved against the model's directory,
    the first entry of the child's ``sys.path`` (trust.md, Python function); a relative import against the
    file's directory, as when the file is imported as a module of its package.
    """
    if not isinstance(spec.interface, PythonFunction):
        return ()
    file = spec.interface.function.rpartition(":")[0]
    path = os.path.join(model_dir, *file.split("/"))
    source = _read_text(path, "function")
    try:
        tree = ast.parse(source, filename=file)
    except SyntaxError as e:
        raise SpecError(f"function: {file} doesn't parse: {e.msg} (line {e.lineno})") from None
    except (ValueError, MemoryError, RecursionError) as e:
        raise SpecError(f"function: {file} doesn't parse: {type(e).__name__}") from None
    tracked = [os.path.join(model_dir, *f.path.split("/")) for f in files]
    here = os.path.dirname(path)
    warnings: dict[str, str] = {}
    for node in _imports(tree):
        found: list[tuple[str, str]] = []
        if isinstance(node, ast.Import):
            found = [(alias.name, model_dir) for alias in node.names]
        else:
            places = [model_dir]
            if node.level:
                place = here
                for _ in range(node.level - 1):
                    place = os.path.dirname(place)
                places = [place]
            module = node.module or ""
            for base in places:
                found += [(module, base)] if module else []
                found += [(f"{module}.{a.name}".lstrip("."), base) for a in node.names if a.name != "*"]
        for name, base in found:
            for candidate in _candidates(base, name):
                rel = os.path.relpath(candidate, model_dir).replace(os.sep, "/")
                if rel.split("/")[0] == ".." or not os.path.isfile(candidate):
                    continue
                if not any(same_file(candidate, t) for t in tracked):
                    warnings.setdefault(
                        rel,
                        f"{file} imports {name}, which resolves to {rel}, a file in the model's directory not listed "
                        "in files; the model version doesn't cover it",
                    )
    return tuple(warnings.values())


def load_spec(path: str) -> LoadedModel:
    """Load a model spec from its file: read, check, and hash it (model_interface.md; M10, M17, M18, M21; T7).

    Nothing of the model runs: the function's file is parsed, never imported (T4). The model's directory is the
    directory of the spec's file, its links resolved, so a link to the spec is the same model (C33).

    Parameters
    ----------
    path
        The spec's file, absolute or relative to the working directory.

    Returns
    -------
    LoadedModel
        With its tracked files' digests, its model version, and its warnings.

    Raises
    ------
    SpecError
        Starting with the spec's path, and naming the field: a spec that doesn't validate, a credentials file
        (the spec itself, or a file it names, through links), a tracked file missing, a template naming something
        that isn't a model parameter, or a function file that doesn't parse.
    """
    spec_path = _as_given(path)
    real = os.path.realpath(path)
    model_dir = os.path.dirname(real)
    try:
        named = os.path.dirname(os.path.abspath(path))
        if is_credentials_file(os.path.basename(spec_path)) or leads_to_credentials(path, named):
            raise SpecError("the model spec is a credentials file, which EMA doesn't read")
        spec = ModelSpec.from_json(_read_text(real, "the model spec"))
        files = hash_files(spec, model_dir)
        _check_templates(spec, model_dir)
        warnings = _unlisted_imports(spec, model_dir, files)
    except SpecError as e:
        raise SpecError(f"{spec_path}: {e}") from None
    return LoadedModel(spec, spec_path, model_dir, files, version_hash(spec, files), warnings)


def stored_model(spec: ModelSpec, files: tuple[TrackedFile, ...], spec_path: str) -> LoadedModel:
    """Build a loaded model from the store's plain values, reading no file (architecture.md §5; 0054).

    The workspace passes the stored spec (Q14) with its current loading's settings set on it (Q3), its tracked
    files, and that loading's spec path; ``check_files`` checks the files before each call (M16).

    Parameters
    ----------
    spec
        The stored spec, with the loading's ``keep``, ``batch_size``, and ``timeout_s``.
    files
        Its tracked files, as stored.
    spec_path
        The loading's spec path.

    Returns
    -------
    LoadedModel
        With no warnings; its model version is computed again from the spec and files.
    """
    model_dir = os.path.dirname(os.path.realpath(spec_path))
    ordered = tuple(sorted(files, key=lambda f: f.path))
    return LoadedModel(spec, _as_given(spec_path), model_dir, ordered, version_hash(spec, ordered), ())


def save_spec(spec: ModelSpec, path: str) -> None:
    """Write a spec's ``to_json`` to a new file, never overwriting one (trust.md T6; ``save_model``).

    With an exclusive create, so a file that appears meanwhile is kept. An existing file with the same bytes is
    left as it is. The text is read back with ``ModelSpec.from_json`` first, so a spec built in Python that
    loading would refuse is never written.

    Parameters
    ----------
    spec
        The spec.
    path
        A ``.json`` file (in any case) in an existing directory.

    Raises
    ------
    SpecError
        When ``from_json`` refuses the spec's text.
    PathRefused
        For a name not ending in ``.json``, a directory that doesn't exist, a link to nothing, an existing file
        with other bytes or that isn't a regular file, or a file (or a link) that appears at the path before the
        write.
    """
    text = spec.to_json()
    ModelSpec.from_json(text)
    data = text.encode("utf-8")
    if not path.casefold().endswith(".json"):
        raise PathRefused(f"{path}: a model spec's file name ends in .json")
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        raise PathRefused(f"{path}: its directory {parent} doesn't exist")
    if os.path.islink(path) and not os.path.exists(path):
        raise PathRefused(f"{path} is a link to nothing, {os.readlink(path)}; EMA never writes through a link")
    try:
        with open_regular(path) as f:
            existing: bytes | None = f.read()
    except FileNotFoundError:
        existing = None
    except OSError as e:
        raise PathRefused(f"{path} can't be read: {e.strerror}") from None
    if existing == data:
        return
    if existing is not None:
        raise PathRefused(f"{path} exists, with other text; EMA never overwrites a file")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise PathRefused(f"{path} appeared before it could be written; it is kept, and nothing was saved") from None
    with os.fdopen(fd, "wb") as f:
        f.write(data)
