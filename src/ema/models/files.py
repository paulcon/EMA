"""A model's files: paths compared as files, and the tracked files' hashes (architecture.md §5, files.py).

Paths are compared as files, never as strings (trust.md T1; P3, C33): ``same_file`` and ``is_within``. The
tracked files are hashed at loading (``hash_files``, which also refuses a named file whose link leads to a
credentials file, T7) and before every call (``check_files``, M16). ``remove_tree`` comes with the run phases
(step 04).
"""

import hashlib
import os
import unicodedata
from typing import TYPE_CHECKING

from ema.types.errors import ModelChanged, SpecError
from ema.types.identity import TrackedFile, model_version_label
from ema.types.model import CommandLine, ModelSpec, PythonFunction, is_credentials_file

if TYPE_CHECKING:
    from ema.models.spec import LoadedModel

_CHUNK = 1 << 20


def _nearest_existing(path: str) -> str:
    while not os.path.lexists(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path


def _case_insensitive(path: str) -> bool:
    """Probe the file system of ``path``'s nearest existing part: does its name with its case swapped name it."""
    path = _nearest_existing(path)
    while True:
        head, tail = os.path.split(path)
        if tail.swapcase() != tail:
            try:
                return os.path.samefile(path, os.path.join(head, tail.swapcase()))
            except OSError:
                return False
        if head == path:
            return False
        path = head


def _canonical(path: str) -> str:
    resolved = unicodedata.normalize("NFC", os.path.normpath(os.path.realpath(path)))
    return resolved.casefold() if _case_insensitive(resolved) else resolved


def same_file(a: str | os.PathLike[str], b: str | os.PathLike[str]) -> bool:
    """Tell whether two paths name the same file (trust.md T1; P3, C33).

    When both exist, the file system decides (``os.path.samefile``: links, hard links, and case). Otherwise the
    paths are resolved through their links and normalized (``normpath``, then Unicode NFC), and case-folded only
    where the file system of the nearest existing part is case-insensitive, found by probing it.

    Parameters
    ----------
    a, b
        The paths.

    Returns
    -------
    bool
        True when they name one file.
    """
    try:
        return os.path.samefile(a, b)
    except OSError:
        return _canonical(os.fspath(a)) == _canonical(os.fspath(b))


def is_within(path: str | os.PathLike[str], directory: str | os.PathLike[str]) -> bool:
    """Tell whether ``path``, resolved through its links, is ``directory`` or below it, as files (T1, T5).

    Each of the resolved path's ancestors, the nearest existing one included, is compared with the directory by
    ``same_file``; so ``ROOT/../x`` is outside the root, and the root itself is inside it.

    Parameters
    ----------
    path
        The path, which needn't exist.
    directory
        The directory.

    Returns
    -------
    bool
        True when it is the directory or lies below it.
    """
    current = os.path.realpath(path)
    while True:
        if same_file(current, directory):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


def _leads_to_credentials(path: str, directory: str) -> str | None:
    """Return the target of ``path``'s links when it is a credentials file (trust.md, Paths; T7).

    The target is matched below ``directory`` when it lies there, and whole when it doesn't.
    """
    target = os.path.realpath(path)
    base = os.path.realpath(directory)
    below = os.path.relpath(target, base) if is_within(target, base) else ".."
    checked = target if below.startswith("..") else below.replace(os.sep, "/")
    return target if is_credentials_file(checked) else None


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked(spec: ModelSpec) -> dict[str, tuple[str, bool]]:
    """Each tracked file's path, with the field that names it and its shared mark (model_interface.md, Versions)."""
    tracked: dict[str, tuple[str, bool]] = {}
    if isinstance(spec.interface, PythonFunction):
        tracked[spec.interface.function.rpartition(":")[0]] = ("function", False)
    if isinstance(spec.interface, CommandLine):
        for i, deck in enumerate(spec.interface.input_decks):
            tracked.setdefault(deck.template, (f"input_decks[{i}].template", False))
    for i, entry in enumerate(spec.files):
        tracked[entry.path] = (f"files[{i}]", entry.shared)
    return tracked


def hash_files(spec: ModelSpec, model_dir: str) -> tuple[TrackedFile, ...]:
    """Hash a spec's tracked files: the Python function's file, the input deck templates, and the listed files.

    A file named twice (a template also listed) is tracked once, with the listed entry's ``shared`` mark. A link
    in the model's directory is followed (the user put it there), and its target's contents hashed.

    Parameters
    ----------
    spec
        The model spec.
    model_dir
        The directory its paths are relative to.

    Returns
    -------
    tuple of TrackedFile
        Sorted by path.

    Raises
    ------
    SpecError
        Naming the field, for a file that is missing or isn't a file, one whose link leads to a credentials file
        (T7), or two entries that are one file.
    """
    files = []
    seen: dict[tuple[int, int], str] = {}
    for rel, (field, shared) in _tracked(spec).items():
        path = os.path.join(model_dir, *rel.split("/"))
        if not os.path.exists(path):
            raise SpecError(f"{field}: {rel} isn't in the model's directory {model_dir}")
        if not os.path.isfile(path):
            raise SpecError(f"{field}: {rel} is not a file")
        target = _leads_to_credentials(path, model_dir)
        if target is not None:
            raise SpecError(f"{field}: {rel} leads to a credentials file, {target}")
        stat = os.stat(path)
        if (stat.st_dev, stat.st_ino) in seen:
            raise SpecError(f"{field}: {rel} is the same file as {seen[stat.st_dev, stat.st_ino]}")
        seen[stat.st_dev, stat.st_ino] = rel
        try:
            files.append(TrackedFile(rel, _sha256(path), shared))
        except OSError as e:
            raise SpecError(f"{field}: {rel} couldn't be read: {e.strerror}") from None
    return tuple(sorted(files, key=lambda f: f.path))


def check_files(model: "LoadedModel") -> None:
    """Hash a loaded model's tracked files again, before a call (M16, C34; U6).

    Parameters
    ----------
    model
        The loaded model, with the digests from its loading.

    Raises
    ------
    ModelChanged
        Naming the first file that changed, or is gone, since loading.
    """
    label = model_version_label(model.spec.name, model.model_version_id)
    for f in model.files:
        try:
            changed = _sha256(os.path.join(model.model_dir, *f.path.split("/"))) != f.sha256
        except OSError:
            raise ModelChanged(f"{label}: {f.path} is gone or can't be read since loading") from None
        if changed:
            raise ModelChanged(f"{label}: {f.path} changed since loading; load the model again for a new model version")
