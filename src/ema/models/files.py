"""A model's files: paths compared as files, and the tracked files' hashes (architecture.md §5, files.py).

Paths are compared as files, never as strings (trust.md T1; P3, C33): ``same_file`` and ``is_within``. The
tracked files are hashed at loading (``hash_files``, which also refuses a named file whose link leads to a
credentials file, T7) and before every call (``check_files``, M16). ``remove_tree`` comes with the run phases
(step 04).
"""

import errno
import hashlib
import os
import stat
import sys
import unicodedata
from typing import TYPE_CHECKING, BinaryIO

from ema.types.errors import ModelChanged, SpecError
from ema.types.identity import TrackedFile, model_version_label
from ema.types.model import CommandLine, ModelSpec, PythonFunction, is_credentials_file

if TYPE_CHECKING:
    from ema.models.spec import LoadedModel

_CHUNK = 1 << 20
#: ``pathconf``'s case-sensitivity name: in ``os.pathconf_names`` where Python lists it, else Darwin's number.
_PC_CASE_SENSITIVE = os.pathconf_names.get("PC_CASE_SENSITIVE", 11 if sys.platform == "darwin" else None)


def _nearest_existing(path: str) -> str:
    while not os.path.lexists(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path


def _pathconf_case_insensitive(directory: str) -> bool | None:
    """Ask the file system whether ``directory`` is case-insensitive (macOS's ``_PC_CASE_SENSITIVE``), or None."""
    if _PC_CASE_SENSITIVE is None:
        return None
    try:
        return os.pathconf(directory, _PC_CASE_SENSITIVE) == 0
    except (OSError, ValueError):
        return None


def _swaps_to_itself(path: str) -> bool | None:
    """Tell whether ``path`` with its name's case swapped names the same file; None when its name has no letters."""
    head, tail = os.path.split(path)
    if tail.swapcase() == tail:
        return None
    try:
        return os.path.samefile(path, os.path.join(head, tail.swapcase()))
    except OSError:
        return False


def _probe_case_insensitive(directory: str) -> bool:
    """Probe ``directory``'s file system: an entry in it whose name has letters, then its own name and its parents'.

    An entry inside it is on its file system even when it is a mount point, whose own name is on its parent's.
    """
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                found = _swaps_to_itself(entry.path)
                if found is not None:
                    return found
    except OSError:
        pass
    path = directory
    while True:
        found = _swaps_to_itself(path)
        if found is not None:
            return found
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent


def _case_insensitive(path: str) -> bool:
    """Tell whether names below ``path``'s nearest existing directory are compared without case (T1).

    The file system is asked where it can say (``pathconf``), else probed (``_probe_case_insensitive``).
    """
    directory = _nearest_existing(path)
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    answer = _pathconf_case_insensitive(directory)
    return _probe_case_insensitive(directory) if answer is None else answer


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


def leads_to_credentials(path: str, directory: str) -> str | None:
    """Return the target of ``path``'s links when it is a credentials file, else None (trust.md, Paths; T7).

    The target is matched below ``directory`` when it lies there, and whole when it doesn't. For ``hash_files``
    and ``load_spec``.

    Parameters
    ----------
    path
        The path, which may be a link.
    directory
        The model's directory.

    Returns
    -------
    str or None
        The resolved target, when it is a credentials file.
    """
    target = os.path.realpath(path)
    base = os.path.realpath(directory)
    below = os.path.relpath(target, base) if is_within(target, base) else ".."
    outside = below.split(os.sep)[0] == ".."
    return target if is_credentials_file(target if outside else below.replace(os.sep, "/")) else None


def open_regular(path: str) -> BinaryIO:
    """Open a regular file to read its bytes, never blocking on a FIFO or a device (0069 item 32).

    Parameters
    ----------
    path
        The file, through its links.

    Returns
    -------
    BinaryIO
        Open for reading.

    Raises
    ------
    OSError
        When it can't be opened, or isn't a regular file (``strerror`` "not a regular file").
    """
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "not a regular file", path)
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open_regular(path) as f:
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _same_entry(a: str, b: str) -> bool:
    """Tell whether two paths, of one file by ``lstat``, are one directory entry (two spellings of one name).

    One directory and one name, compared NFC and case-folded; two hard links, or a link beside its target, are
    two entries.
    """

    def name(p: str) -> str:
        return unicodedata.normalize("NFC", os.path.basename(p)).casefold()

    try:
        return name(a) == name(b) and os.path.samefile(os.path.dirname(a), os.path.dirname(b))
    except OSError:
        return False


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
    in the model's directory is followed (the user put it there), and its target's contents hashed; a link beside
    its target, or two hard links, are two entries. Only regular files are read.

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
        Naming the field, for a file that is missing or isn't a regular file, one whose link leads to a
        credentials file (T7), or two entries that are one directory entry (two spellings of one name).
    """
    files = []
    seen: dict[tuple[int, int], list[tuple[str, str]]] = {}
    for rel, (field, shared) in _tracked(spec).items():
        path = os.path.join(model_dir, *rel.split("/"))
        if not os.path.exists(path):
            raise SpecError(f"{field}: {rel} isn't in the model's directory {model_dir}")
        if not os.path.isfile(path):
            raise SpecError(f"{field}: {rel} is not a regular file")
        target = leads_to_credentials(path, model_dir)
        if target is not None:
            raise SpecError(f"{field}: {rel} leads to a credentials file, {target}")
        entry = os.lstat(path)
        for other_path, other in seen.get((entry.st_dev, entry.st_ino), []):
            if _same_entry(path, other_path):
                raise SpecError(f"{field}: {rel} is the same file as {other}")
        seen.setdefault((entry.st_dev, entry.st_ino), []).append((path, rel))
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
        except OSError as e:
            raise ModelChanged(
                f"{label}: {f.path} is gone or can't be read since loading ({e.strerror}); load the model again for "
                "a new model version"
            ) from None
        if changed:
            raise ModelChanged(f"{label}: {f.path} changed since loading; load the model again for a new model version")
