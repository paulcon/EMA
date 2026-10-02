"""Prepare a call: its run directories, written with everything the run needs (model_interface.md, A run; 0015).

Each run's directory is ``<runs_dir>/<run id>/``, made afresh (a leftover from a call that never finished is
deleted without following links, 0061), and holds ``point.json``. The call's directory (the run directory, or for
a batch model the batch directory ``<runs_dir>/<batch call id>/`` beside its runs', 0025) holds what the model
reads: the input decks, written from their templates with M10's number rule, and the listed files, copied keeping
their relative paths, or, when shared, linked to a stored copy at ``<shared_dir>/<sha256>/<name>``, written once
and read-only (0030, M15). Only plain data passes on: ``PreparedCall``.
"""

import hashlib
import json
import os
import shutil
import string
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ema.models.files import open_regular, remove_tree
from ema.models.sandbox import model_environment
from ema.models.spec import LoadedModel
from ema.types.errors import ModelChanged
from ema.types.identity import TrackedFile, batch_call_id, model_version_label
from ema.types.model import CommandLine, PythonFunction
from ema.types.runs import RunKey


@dataclass(frozen=True)
class PreparedCall:
    """A call ready to execute: plain, serializable data (architecture.md §5).

    Attributes
    ----------
    keys : tuple of RunKey
        One, or a batch call's (0025).
    approval_id : str
        Recorded with each run (C48).
    run_dirs : tuple of str
        Each key's run directory, absolute.
    call_dir : str
        The run directory, or the batch directory beside them.
    command : tuple of str or None
        A command-line model's command; None for a Python function.
    env : Mapping[str, str]
        The whole environment the model gets (``model_environment``; trust.md).
    timeout_s : float
        The call's timeout.
    """

    keys: tuple[RunKey, ...]
    approval_id: str
    run_dirs: tuple[str, ...]
    call_dir: str
    command: tuple[str, ...] | None
    env: Mapping[str, str]
    timeout_s: float


def number_text(x: float) -> str:
    """Write a value for an input deck by M10's one rule.

    The shortest decimal that reads back as the same double, and a whole number with no decimal point.

    Examples
    --------
    >>> [number_text(v) for v in (0.1, 64.0, -2.5, 1e-300, 1e22, -0.0)]
    ['0.1', '64', '-2.5', '1e-300', '1e+22', '-0']
    """
    text = repr(float(x))
    return text.removesuffix(".0")


def _fresh_dir(path: str) -> str:
    remove_tree(path)
    os.makedirs(path)
    return path


def _in(directory: str, relative: str) -> str:
    path = os.path.join(directory, *relative.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _stored_copy(model: LoadedModel, tracked: TrackedFile, shared_dir: str) -> str:
    """Return the read-only stored copy of a shared file, written once (0030, M15).

    ``ModelChanged`` when the source no longer has the digest of its model version.
    """
    target = os.path.join(shared_dir, tracked.sha256, os.path.basename(tracked.path))
    if os.path.isfile(target):
        return target
    os.makedirs(os.path.dirname(target), exist_ok=True)
    digest = hashlib.sha256()
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".copy-")
    try:
        with open_regular(os.path.join(model.model_dir, *tracked.path.split("/"))) as source, os.fdopen(fd, "wb") as f:
            while chunk := source.read(1 << 20):
                digest.update(chunk)
                f.write(chunk)
        if digest.hexdigest() != tracked.sha256:
            label = model_version_label(model.spec.name, model.model_version_id)
            raise ModelChanged(f"{label}: {tracked.path} changed since loading; load the model again")
        os.chmod(temporary, 0o444)
        os.replace(temporary, target)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)
    return target


def prepare(
    model: LoadedModel, keys: Sequence[RunKey], runs_dir: str, shared_dir: str, *, approval_id: str
) -> PreparedCall:
    """Make a call's run directories and write into them everything the run needs (model_interface.md, A run).

    Parameters
    ----------
    model
        The loaded model; the runner has checked its files (``check_files``, M16).
    keys
        One key, or a batch call's keys (a batch model only); each point complete, in the spec's order (M5).
    runs_dir
        The workspace's ``runs/``.
    shared_dir
        The workspace's ``files/``, where shared files are stored once (0030).
    approval_id
        The approval the call's runs are made under (C48).

    Returns
    -------
    PreparedCall
        The call, ready for ``execute``.

    Raises
    ------
    ValueError
        For no keys, several keys for a model that isn't a batch function, or a point of the wrong length.
    ModelChanged
        When a shared file's source no longer has its model version's digest.
    """
    spec, keys = model.spec, tuple(keys)
    batch = isinstance(spec.interface, PythonFunction) and spec.interface.batch
    if not keys or (len(keys) > 1 and not batch):
        raise ValueError(f"a call of model {spec.name} holds one run, or a batch model's runs; got {len(keys)}")
    names = [p.name for p in spec.parameters]
    run_dirs = []
    for key in keys:
        if len(key.point) != len(names):
            raise ValueError(f"a point of model {spec.name} has {len(names)} values, not {len(key.point)} (M5)")
        run_dir = _fresh_dir(os.path.join(os.path.abspath(runs_dir), key.run_id))
        point = dict(zip(names, key.point, strict=True))
        with open(os.path.join(run_dir, "point.json"), "x") as f:
            f.write(json.dumps(point, indent=2) + "\n")
        run_dirs.append(run_dir)
    if batch:
        call_dir = _fresh_dir(os.path.join(os.path.abspath(runs_dir), batch_call_id([k.run_id for k in keys])))
    else:
        call_dir = run_dirs[0]
    if isinstance(spec.interface, CommandLine):
        values = {n: number_text(v) for n, v in zip(names, keys[0].point, strict=True)}
        for deck in spec.interface.input_decks:
            with open_regular(os.path.join(model.model_dir, *deck.template.split("/"))) as source:
                template = string.Template(source.read().decode("utf-8"))
            with open(_in(call_dir, deck.writes), "x", encoding="utf-8") as written:
                written.write(template.substitute(values))
    tracked = {f.path: f for f in model.files}
    for entry in spec.files:
        target = _in(call_dir, entry.path)
        if entry.shared:
            os.symlink(_stored_copy(model, tracked[entry.path], os.path.abspath(shared_dir)), target)
        else:
            shutil.copy(os.path.join(model.model_dir, *entry.path.split("/")), target)
    command = tuple(spec.interface.command) if isinstance(spec.interface, CommandLine) else None
    env = model_environment(spec)
    return PreparedCall(keys, approval_id, tuple(run_dirs), call_dir, command, env, spec.timeout_s)
