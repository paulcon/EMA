"""Layer 4: the workspace, EMA's front door, which the guides, the CLI, and the MCP server call (AR3).

architecture.md §7: ``open_workspace`` and ``Workspace``'s 18 methods, with ``open_workspace`` the 19 public names of
scope.md's 20; use_cases.md U1-U9; export.md E1-E7; data_model.md Q11, §6, §9, §10; trust.md T5 (the root), T6;
records 0054, 0055, 0056, 0057, 0061 item 12, 0062, 0063, 0080. It computes nothing itself: it calls the lower layers
in the order the rules require (``_evaluate``), and every method returns a type that prints as EMA's text, so an
interface formats no number (P1; C54, C55).
"""

import functools
import json
import os
import threading
from collections.abc import Callable, Mapping
from types import TracebackType
from typing import Any, Concatenate, Self

import numpy as np

import ema.diagnostics  # noqa: F401  (registers every diagnostic: record 0075 item 1)
from ema.approval import ask, ask_confirmation, fenced
from ema.diagnostics import base
from ema.models.files import check_files, is_within, open_regular
from ema.models.processes import ModelProcesses
from ema.models.spec import load_spec, save_spec
from ema.report.pdf import to_pdf
from ema.store import Store
from ema.types.errors import EMAError, NotFound, PathRefused, RequestError, SpecError
from ema.types.identity import hex_ids, model_version_label, point_hash, reuse_key, sha256_hex
from ema.types.model import CommandLine, ModelSpec, PythonFunction, hidden_character, is_credentials_file
from ema.types.requests import Approver, Progress
from ema.types.results import DiagnosticResult, Provenance, Reproduction, ResultSummary
from ema.types.runs import Price, RunStatus
from ema.types.space import ModelParameterSpace
from ema.types.summaries import (
    DiagnosticSummary,
    LoadingSummary,
    ModelDescription,
    ModelSummary,
    Proposal,
    Report,
    RunInfo,
)
from ema.workspace import _evaluate, _export, _reproduce

#: ``ask``, the terminal approver, is re-exported for the CLI, which imports only ema.workspace and ema.types (AR3).
__all__ = ["ResultRef", "Workspace", "ask", "open_workspace"]

#: A result, or its id: any unique prefix of at least 4 hex digits (Q11).
ResultRef = DiagnosticResult | str


def _workspace_holding(path: str) -> str | None:
    """Return the workspace that holds a path, resolved through its links: it or an ancestor with ``ema.db`` (T5)."""
    current = os.path.realpath(path)
    while True:
        if os.path.isfile(os.path.join(current, "ema.db")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _counts(spec: ModelSpec) -> str:
    """Count a spec's model parameters and predictions: "3 model parameters (x1, x2, x3), 1 model prediction (y)"."""
    parameters = ", ".join(p.name for p in spec.parameters)
    predictions = ", ".join(p.name for p in spec.predictions)
    return (f"{_plural(len(spec.parameters), 'model parameter')} ({parameters}), "
            f"{_plural(len(spec.predictions), 'model prediction')} ({predictions})")  # fmt: skip


def _named_files(spec: ModelSpec) -> list[str]:
    """Return the files a spec names, relative to its directory: the function's file, the templates, ``files``."""
    interface = spec.interface
    named = [interface.function.rsplit(":", 1)[0]] if isinstance(interface, PythonFunction) else []
    if isinstance(interface, CommandLine):
        named += [deck.template for deck in interface.input_decks]
    return named + [f.path for f in spec.files]


def _spec_of(spec: str | Mapping[str, Any]) -> ModelSpec:
    """Read a drafted spec, as JSON text or a mapping, with every check of loading that needs no file (SpecError)."""
    if isinstance(spec, str):
        return ModelSpec.from_json(spec)
    try:
        text = json.dumps(spec, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise SpecError(f"the model spec isn't JSON data: {error}") from None
    return ModelSpec.from_json(text)


#: The most bytes read of an existing file at a drafted spec's path: far above any model spec.
_SPEC_FILE_LIMIT = 1 << 22


def _same_spec_text(path: str, text: str) -> str:
    """Return the text of the file at ``path`` when it holds the same spec as ``text`` (record 0081, Review round 1).

    The same bytes, or a hand-formatted file whose ``ModelSpec.from_json(...).to_json()`` is ``text``: the file's own
    text, which ``save_model`` asks about ("already saved, unchanged: load it?") and loads, writing nothing (T6).

    Raises
    ------
    PathRefused
        For a file with another spec, or other text, or something at the path that isn't a regular file EMA can read.
    """
    try:  # a regular file only, never blocking on a FIFO or a device (T6)
        with open_regular(path) as f:
            data = f.read(_SPEC_FILE_LIMIT + 1)
    except OSError as error:
        raise PathRefused(
            f"{path} exists, and isn't a file EMA can read ({error.strerror}); EMA never overwrites a file"
        ) from None
    if data == text.encode("utf-8"):
        return text
    try:
        existing = data.decode("utf-8")
        if ModelSpec.from_json(existing).to_json() == text:
            return existing
    except (UnicodeDecodeError, SpecError):
        pass
    raise PathRefused(f"{path} exists, with another spec or other text; EMA never overwrites a file")


def _not_too_long(path: str, what: str) -> str:
    """Return a path, refusing one the file system can't name: a part or the whole too long (record 0080, n3)."""
    try:
        name_max, path_max = os.pathconf(os.sep, "PC_NAME_MAX"), os.pathconf(os.sep, "PC_PATH_MAX")
    except (OSError, ValueError):
        name_max, path_max = 255, 1024
    data = os.fsencode(path)
    if len(data) >= path_max or any(len(part) > name_max for part in data.split(os.fsencode(os.sep))):
        raise PathRefused(
            f"{what} is too long for the file system: at most {name_max} bytes a name, {path_max - 1} the whole path"
        )
    return path


def _limits(p: Any) -> str:
    limits = p.limits
    parts = []
    if limits.lower is not None:
        parts.append(f"{'>' if limits.lower_strict else '≥'} {limits.lower!r}")
    if limits.upper is not None:
        parts.append(f"{'<' if limits.upper_strict else '≤'} {limits.upper!r}")
    return f"; limits {' and '.join(parts)}" if parts else ""


def _on_its_thread[**P, R](
    method: Callable[Concatenate["Workspace", P], R],
) -> Callable[Concatenate["Workspace", P], R]:
    """Refuse a call from a thread other than the one that opened the workspace, as EMA's error (§5, Connections).

    The store's SQLite connection stays on its thread; without this check, such a call fails deep inside it with
    ``sqlite3.ProgrammingError``. Record 0080, Review round 1.
    """

    @functools.wraps(method)
    def checked(self: "Workspace", /, *args: P.args, **kwargs: P.kwargs) -> R:
        if threading.get_ident() != self._thread:
            raise EMAError(
                f"the workspace {self.path} was opened on another thread, and its database connection stays there: "
                "open a workspace on each thread that uses one"
            )
        return method(self, *args, **kwargs)

    return checked


def open_workspace(path: str | os.PathLike[str] = "ema_workspace", *, root: str | os.PathLike[str] | None = None
                   ) -> "Workspace":  # fmt: skip
    """Open the workspace at ``path``, creating it on first use (data_model.md §1, §11; U1).

    An older schema is migrated after copying ``ema.db``; a newer one is refused (``WorkspaceVersion``).

    Parameters
    ----------
    path
        The workspace's directory. With ``root``, a relative path is resolved against the root (trust.md, The MCP
        server's root).
    root
        The one directory path arguments may name (T5; the MCP server's ``--root``, 0057): every method that takes a
        path then refuses one outside the root, inside a workspace, with a hidden character, or naming a credentials
        file, and a drafted spec's file resolving outside the root.

    Returns
    -------
    Workspace
        Open; close it, or use it as a context manager.

    Raises
    ------
    PathRefused
        For a root that isn't an existing directory, or is a workspace or inside one (0061 item 12).
    WorkspaceVersion
        For a newer schema, or a file that isn't an EMA workspace's database.
    """
    top = None
    if root is not None:
        top = os.path.realpath(os.fspath(root))
        if not os.path.isdir(top):
            raise PathRefused(f"the root {os.fspath(root)} isn't an existing directory")
        holder = _workspace_holding(top)
        if holder is not None:
            raise PathRefused(
                f"the root {top} is inside the workspace {holder}, or is one; name a directory outside it"
            )
        path = os.path.join(top, os.fspath(path))
    return Workspace(Store.open(os.fspath(path)), top)


class Workspace:
    """An open workspace: its store and its model versions' children (architecture.md §7; OD-16).

    Not frozen; a context manager, whose exit closes it. Open one with ``open_workspace``. It is bound to the thread
    that opened it, as its SQLite connection is (architecture.md §5, Connections): a call from another thread is
    refused (``EMAError``); open a workspace on each thread that uses one (the MCP server holds two). ``approve`` and
    ``confirm`` have no default: they are called only when there are new runs, or a file to save (P3), and ``None``
    says nobody can be asked: new runs and saving are refused before any question (``CannotAsk``).

    Attributes
    ----------
    path : str
        The workspace's directory, absolute.
    """

    def __init__(self, store: Store, root: str | None = None) -> None:
        self._store = store
        self._processes = ModelProcesses()
        self._root = root
        self._thread = threading.get_ident()
        self.path = store.layout.root

    def __enter__(self) -> Self:
        return self

    def __exit__(self, kind: type[BaseException] | None, error: BaseException | None, tb: TracebackType | None) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Workspace({self.path!r})"

    @_on_its_thread
    def close(self) -> None:
        """Stop the model versions' children and close the store (0026)."""
        try:
            self._processes.close()
        finally:
            self._store.close()

    # -- paths under the root (trust.md, T5) -------------------------------------------------------------------

    def _path(self, path: str | os.PathLike[str], what: str, *, directory: bool = False) -> str:
        """Return a path argument, absolute; under a root, refused outside it or inside a workspace (T5).

        A credentials file is refused by the path's name, or, for a ``directory`` EMA writes into (an export), by
        the files it would hold: a new ``.ssh`` or ``.aws`` directory is refused too (T7).
        """
        text = os.fspath(path)
        if self._root is None:
            return _not_too_long(os.path.abspath(text), what)
        ch = hidden_character(text)
        if ch is not None:
            raise PathRefused(f"{what} has a hidden character, U+{ord(ch):04X}: refused under the root {self._root}")
        full = os.path.join(self._root, text)
        if not is_within(full, self._root):
            raise PathRefused(f"{what} {text} is outside the root {self._root}")
        holder = _workspace_holding(full)
        if holder is not None:
            raise PathRefused(f"{what} {text} is inside the workspace {holder}; name a path outside any workspace")
        below = os.path.relpath(os.path.realpath(full), self._root).replace(os.sep, "/")
        if is_credentials_file(below) or (directory and is_credentials_file(f"{below}/runs.csv")):
            raise PathRefused(f"{what} {text} names a credentials file, which EMA doesn't read or write")
        return _not_too_long(os.path.abspath(full), what)

    def _spec_files_inside(self, spec: ModelSpec, spec_path: str) -> tuple[str, ...]:
        """Under a root, refuse a spec's file resolving outside it (T5); return the files that don't exist yet.

        The files are named relative to the spec's directory resolved through its links, as ``load_spec`` reads them
        (C33): a spec that is a link names the files beside its target.
        """
        directory = os.path.dirname(os.path.realpath(spec_path))
        missing = []
        for relative in _named_files(spec):
            full = os.path.join(directory, *relative.split("/"))
            if not os.path.lexists(full):
                missing.append(relative)
            elif self._root is not None and not is_within(full, self._root):
                raise PathRefused(f"the spec's file {relative} resolves outside the root {self._root}: not read")
        return tuple(missing)

    # -- models ------------------------------------------------------------------------------------------------

    def _summary(self, name: str) -> ModelSummary:
        model, spec = _evaluate.loaded(self._store, name)
        label = model_version_label(name, model.model_version_id)
        return ModelSummary(
            name=name,
            model_version=label,
            parameters=tuple(p.name for p in spec.parameters),
            predictions=tuple(p.name for p in spec.predictions),
            spec_path=model.spec_path,
            text=f"{label}: {_counts(spec)}; spec {model.spec_path}",
        )

    @_on_its_thread
    def load_model(self, path: str | os.PathLike[str]) -> LoadingSummary:
        """Load a model spec: validate it, hash its files, and make the name mean it (W1; M3; U6; 0054).

        Loading asks nothing and runs nothing. Loading again after a file changed makes a new model version; the
        latest loading of a name wins, and the summary says what the name meant before.

        Raises
        ------
        SpecError
            For a spec that doesn't validate, naming the field.
        PathRefused
            Under a root, for a path refused, or a file the spec names resolving outside the root, before any is
            read or hashed (T5).
        """
        spec_path = self._path(path, "the model spec")
        if self._root is not None:  # before load_spec reads or hashes any file the spec names (T5)
            try:
                with open_regular(spec_path) as f:
                    drafted = ModelSpec.from_json(f.read().decode("utf-8"))
            except (OSError, UnicodeDecodeError, SpecError):
                drafted = None  # load_spec refuses it, saying why, before it reads a file the spec names
            if drafted is not None:
                self._spec_files_inside(drafted, spec_path)
        model = load_spec(spec_path)
        if self._root is not None:  # the spec as load_spec read it, had it changed meanwhile
            self._spec_files_inside(model.spec, spec_path)
        name, mv = model.spec.name, model.model_version_id
        store = self._store
        before = store.current_loading(name)
        try:
            store.model_version(mv)
            new_version = False
        except NotFound:
            new_version = True
        store.record_loading(model.spec, model.spec_path, model.files)
        label = model_version_label(name, mv)
        lines = [f"Loaded {label}: {_counts(model.spec)}"]
        replaced, changed = None, []
        if before is not None and (before.model_version_id != mv or before.spec_path != os.path.realpath(spec_path)):
            old = store.model_version(before.model_version_id)
            replaced = f"was {model_version_label(name, before.model_version_id)} at {before.spec_path}"
            if before.model_version_id != mv:
                was = {f.path: f.sha256 for f in old.files}
                now = {f.path: f.sha256 for f in model.files}
                changed = [f"{p} changed" if p in was and p in now else f"{p} {'added' if p in now else 'removed'}"
                           for p in sorted(set(was) | set(now)) if was.get(p) != now.get(p)]  # fmt: skip
                if old.spec.versioned_json() != model.spec.versioned_json():
                    changed.insert(0, "the model spec changed")
                lines.append(f"New model version {label} ({replaced}): {', '.join(changed) or 'changed'}")
            else:
                lines.append(f"The same model version, from another spec file ({replaced})")
        elif before is not None:
            lines.append("Already loaded: nothing changed")
        lines += [f"Warning: {w}" for w in model.warnings]
        return LoadingSummary(
            model=self._summary(name),
            new_version=new_version,
            replaced=replaced,
            changed_files=tuple(changed),
            warnings=model.warnings,
            text="\n".join(lines),
        )

    @_on_its_thread
    def list_models(self) -> list[ModelSummary]:
        """List the models loaded, each as its name means now (Q3; 0054)."""
        return [self._summary(name) for name in self._store.model_names()]

    @_on_its_thread
    def describe_model(self, name: str) -> ModelDescription:
        """Describe a model: its model parameters, units, nominal values, limits, and model predictions (U1).

        Raises
        ------
        NotFound
            For a model that isn't loaded, naming those that are.
        """
        summary = self._summary(name)
        model, _ = _evaluate.loaded(self._store, name)
        spec = model.spec  # the model version's spec with the current loading's settings, as runs use it (0081 item 32)
        lines = [summary.text]
        if spec.description:
            lines.append(spec.description)
        lines.append("Model parameters:")
        lines += [f"- {p.name}" + (f" [{p.units}]" if p.units else "") + f": nominal {p.nominal!r}{_limits(p)}"
                  + (f"; {p.description}" if p.description else "") for p in spec.parameters]  # fmt: skip
        lines.append("Model predictions:")
        lines += [f"- {q.name}" + (f" [{q.units}]" if q.units else "") + (f": {q.description}" if q.description else "")
                  for q in spec.predictions]  # fmt: skip
        calls = "one point per call"
        if isinstance(spec.interface, PythonFunction) and spec.interface.batch:
            calls = f"batches of up to {spec.batch_size} points per call" if spec.batch_size else "one batch per call"
        lines.append(f"Runs: a timeout of {spec.timeout_s:g} s per call; {calls}; run directories kept: "
                     f"{spec.keep.value}")  # fmt: skip
        return ModelDescription(model=summary, spec=spec, text="\n".join(lines))

    @_on_its_thread
    def propose_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike[str]) -> Proposal:
        """Validate and render a drafted model spec, and the path it would be saved at; save nothing (U9; T6).

        Raises
        ------
        SpecError
            For a spec that doesn't validate.
        PathRefused
            For a path not ending in ``.json``, a parent that doesn't exist, a file at the path holding another
            spec (or something at it that isn't a regular file), or, under a root, a path refused or a spec's file resolving outside it
            (T5), its files named beside the spec's target when the path is a link.
        """
        parsed = _spec_of(spec)
        given = self._path(path, "the model spec's path")
        if not given.casefold().endswith(".json"):
            raise PathRefused(f"{given}: a model spec's file name ends in .json")
        parent = os.path.dirname(given)
        if not os.path.isdir(parent):
            raise PathRefused(f"{given}: its directory {parent} doesn't exist")
        absolute = os.path.join(os.path.realpath(parent), os.path.basename(given))
        text = parsed.to_json()
        saved = os.path.lexists(absolute)
        if saved:  # the same spec, hand-formatted or not, is shown as the file holds it (0081, Review round 1)
            text = _same_spec_text(absolute, text)
        missing = self._spec_files_inside(parsed, absolute)
        where = (f"Already saved at {absolute}, the same spec: save_model loads it after the user's yes, writing "
                 "nothing." if saved else f"Would be saved at {absolute}; nothing saved yet.")  # fmt: skip
        lines = [f"Model spec {parsed.name}: {_counts(parsed)}", where]
        if missing:
            lines.append(f"Files it names that don't exist yet: {', '.join(missing)}")
        lines += ["Its full text:", fenced(text)]
        return Proposal(spec=parsed, path=absolute, spec_text=text, missing_files=missing, text="\n".join(lines))

    @_on_its_thread
    def save_model(self, spec: str | Mapping[str, Any], path: str | os.PathLike[str], *, confirm: Approver | None
                   ) -> LoadingSummary:  # fmt: skip
        """Save a drafted model spec after the user's yes, and load it (W2, W1; T6; 0049).

        Validated as ``propose_model`` does: an invalid spec, or a file at the path holding another spec, is refused
        before anything is asked. The confirmation shows the absolute path, what the name means now, and the full
        text; the file written has exactly those bytes, created exclusively. A file at the path holding the same spec
        (the same bytes, or hand-formatted) is asked as "already saved, unchanged: load it?", with its own text, and
        loaded after the yes, never rewritten (T6; record 0081, Review round 1).

        Raises
        ------
        CannotAsk
            With ``confirm=None``: nothing asked, recorded, or saved.
        ApprovalDeclined
            On a no: nothing saved.
        SpecError, PathRefused
            As ``propose_model``; or when a file appears at the path between the yes and the write.
        """
        proposal = self.propose_model(spec, path)
        ask_confirmation(store=self._store, spec_path=proposal.path, spec_text=proposal.spec_text, confirm=confirm)
        if proposal.spec_text == proposal.spec.to_json():
            save_spec(proposal.spec, proposal.path)  # the same bytes already there are left as they are
        elif _same_spec_text(proposal.path, proposal.spec.to_json()) != proposal.spec_text:
            raise PathRefused(f"{proposal.path} changed after the question; nothing was loaded")
        return self.load_model(proposal.path)

    @_on_its_thread
    def test_model(self, name: str, *, approve: Approver | None) -> RunInfo:
        """Run the model once at its nominal point, replicate 0, after the user's yes (0049; U1, U2).

        Priced and approved like any new run (P3); the test run already stored asks nothing.

        Raises
        ------
        NotFound
            For a model that isn't loaded.
        ModelChanged
            When a tracked file changed since loading.
        CannotAsk, ApprovalDeclined, WorkspaceBusy
            As ``run``.
        """
        model, spec = _evaluate.loaded(self._store, name)
        check_files(model)
        run = _evaluate.test_run(self._store, self._processes, model, approve=approve)
        return _evaluate.info_of(self._store, spec, run)

    # -- diagnostics -------------------------------------------------------------------------------------------

    @_on_its_thread
    def list_diagnostics(self) -> list[DiagnosticSummary]:
        """List the diagnostics, each with its parameters (U1; C55)."""
        return [base.describe(base.get(name)) for name in base.names()]

    @_on_its_thread
    def describe_diagnostic(self, name: str) -> DiagnosticSummary:
        """Describe a diagnostic: its summary and each diagnostic parameter's type, default, and meaning (C55).

        Raises
        ------
        NotFound
            Naming the diagnostics there are.
        """
        return base.describe(base.get(name))

    @_on_its_thread
    def price(
        self,
        model: str,
        diagnostic: str,
        space: Mapping[str, Any] | ModelParameterSpace | None = None,
        *,
        prediction: str | None = None,
        retry_failed: bool = False,
        **params: Any,
    ) -> Price:
        """Price a diagnostic evaluation without asking or running anything (P3; Q1, Q2).

        Raises
        ------
        NotFound, ModelChanged, RequestError, DesignTooLarge
            As ``run``, before anything is priced.
        """
        prepared = _evaluate.prepare(self._store, model, diagnostic, space, prediction, params)
        return _evaluate.price(self._store, prepared, retry_failed=retry_failed)

    @_on_its_thread
    def run(
        self,
        model: str,
        diagnostic: str,
        space: Mapping[str, Any] | ModelParameterSpace | None = None,
        *,
        prediction: str | None = None,
        retry_failed: bool = False,
        approve: Approver | None,
        on_progress: Callable[[Progress], None] | None = None,
        **params: Any,
    ) -> DiagnosticResult:
        """Run one diagnostic evaluation, in architecture.md §7's order, and return its result (U1-U7).

        A repeated request returns the stored result, asking nothing (C50). New runs are priced and asked for
        first (P3); Ctrl-C passes through as ``KeyboardInterrupt``, with every finished run stored (C49).

        Parameters
        ----------
        model
            The model's name.
        diagnostic
            The diagnostic's name: "scatter", "point_run", ...
        space
            The model parameter space (designs.md's JSON or Python form); none for the point run (U7).
        prediction
            The model prediction; None for the only one.
        retry_failed
            Run the design's failed points again (C47; 0010).
        approve
            Asked before new runs: ``ema.ask`` on a terminal; None when nobody can be asked.
        on_progress
            Called with the runs' and the analysis's progress (PM10). An exception it raises stops the evaluation:
            between two calls during the runs, every finished run kept, and no result stored (C49). It is the
            cancellation hook for a caller off the main thread (the MCP server), where Ctrl-C can't reach a call.
        **params
            The diagnostic parameters: ``n=200, seed=1``.

        Returns
        -------
        DiagnosticResult
            With ``shown``: its short id and EMA's text.

        Raises
        ------
        NotFound
            For a model or diagnostic that isn't there.
        ModelChanged
            When a tracked file changed since loading, or during the runs, naming it (U6, M16).
        RequestError
            For a space or a diagnostic parameter refused; ``DesignTooLarge`` over the cap (G5).
        CannotAsk
            With new runs and ``approve=None``: nothing asked or recorded.
        ApprovalDeclined
            On a no: "declined: no runs made".
        WorkspaceBusy
            When another process, or another workspace of this process, is making runs in the workspace.
        """
        prepared = _evaluate.prepare(self._store, model, diagnostic, space, prediction, params)
        result, reused = _evaluate.run(
            self._store, self._processes, prepared, retry_failed=retry_failed, approve=approve,
            on_progress=on_progress,
        )  # fmt: skip
        return _evaluate.shown(self._store, result, reused=reused)

    # -- results -----------------------------------------------------------------------------------------------

    def _result_id(self, result: ResultRef) -> str:
        if isinstance(result, DiagnosticResult):
            return result.result_id
        if not isinstance(result, str):
            raise RequestError(f"a diagnostic result is a result or its id, not {result!r}")
        return self._store.resolve("result", result)

    @_on_its_thread
    def get_result(self, result: ResultRef) -> DiagnosticResult:
        """Return a stored diagnostic result with its provenance (Q6), by any unique id prefix of 4 or more (Q11).

        Raises
        ------
        NotFound, AmbiguousId
            For a prefix that names none, or several (listed).
        """
        return _evaluate.shown(self._store, self._store.get_result(self._result_id(result)))

    @_on_its_thread
    def list_results(self, *, model: str | None = None, model_version: str | None = None,
                     diagnostic: str | None = None, prediction: str | None = None) -> list[ResultSummary]:  # fmt: skip
        """List the stored diagnostic results, newest first, each with its short id and model version (Q8; U6).

        ``model_version`` is a label ("beam@91c0a2b3c4d5") or an id prefix; a label's name must be its model's.

        Raises
        ------
        NotFound, AmbiguousId
            For a model version that isn't there, or a label whose name isn't its model's; a prefix naming several.
        """
        version = None
        if model_version is not None:
            name, at, prefix = model_version.rpartition("@")
            version = self._store.resolve("model_version", prefix)
            if at:
                actual = self._store.model_version(version).spec.name
                if actual != name:
                    raise NotFound(f"no model version {model_version}: {prefix} is a version of {actual!r}")
        return list(self._store.list_results(model, version, diagnostic, prediction))

    @_on_its_thread
    def report(self, result: ResultRef, *, pdf: bool = False) -> Report:
        """Return a result's report, rebuilding its directory from the store when missing (data_model.md §6).

        Parameters
        ----------
        result
            The result, or its id.
        pdf
            Also make the PDF, through pandoc and lualatex (0018).

        Raises
        ------
        PandocMissing, PdfFailed
            For a PDF that can't be made, saying what to install or LaTeX's error.
        """
        stored = self._store.get_result(self._result_id(result))
        directory = _evaluate.result_directory(self._store, stored)
        path = os.path.join(directory, "report.md")
        with open(path, encoding="utf-8", newline="") as f:
            markdown = f.read()
        return Report(stored.result_id, markdown, path, to_pdf(path) if pdf else None)

    @_on_its_thread
    def failed_runs(self, result: ResultRef) -> list[RunInfo]:
        """List each run not usable for the result's model prediction: failed, or missing it (U3; shared.md, S7).

        Each with its reason, and a failed run's stderr tail, quoted (trust.md; 0061); in design order, each run once.
        """
        stored = self._store.get_result(self._result_id(result))
        spec = self._store.model_version(stored.model_version_id).spec
        out = []
        seen: set[str] = set()
        runs = self._store.result_runs(stored.result_id)
        usable = (runs.status == RunStatus.OK.code) & ~np.isnan(runs.values[stored.prediction])
        for row, run_id in enumerate(hex_ids(runs.run_ids)):
            if usable[row] or run_id in seen:
                continue
            seen.add(run_id)
            out.append(_evaluate.info_of(self._store, spec, self._store.get_run(run_id), row, stored.prediction))
        return out

    @_on_its_thread
    def run_dirs(self, id: str, *, point: Mapping[str, float] | None = None) -> list[RunInfo]:
        """Return a run's directories by its id; or, with ``point``, a result's runs there, one per replicate (0020; Q9).

        Raises
        ------
        NotFound, AmbiguousId
            For an id prefix that names none, or several.
        RequestError
            For a point naming no model parameter of the result's model, or leaving out a varied one.
        """
        store = self._store
        if point is None:
            run = store.get_run(store.resolve("run", id))
            return [_evaluate.info_of(store, store.model_version(run.model_version_id).spec, run)]
        result = store.get_result(store.resolve("result", id))
        spec = store.model_version(result.model_version_id).spec
        space = base.request_space(result.provenance.request, spec)
        for name in point:
            spec.parameter(name)
        values = []
        for p in spec.parameters:
            if p.name in point:
                values.append(float(point[p.name]))
            elif p.name in space.ranges:
                raise RequestError(f"the point names no value for {p.name}, which the result's space varies")
            else:
                values.append(space.held.get(p.name, p.nominal))
        return [_evaluate.info_of(store, spec, run) for run in store.runs_at(result.result_id, point_hash(values))]

    @_on_its_thread
    def reproduce(self, result: ResultRef | Provenance) -> Reproduction:
        """Replay a result from its provenance and the stored runs, and compare it with the original (U8; 0055).

        Makes no run and writes nothing. ``result`` is a stored result or its id, a result read from an export's
        ``result.json`` (``DiagnosticResult.from_json``), or a bare ``Provenance``; with a provenance whose result is
        deleted, the replay is returned with nothing to compare.
        """
        if isinstance(result, Provenance):
            p = result
            versions = {"ema": p.ema, "numpy": p.numpy, "scipy": p.scipy, "matplotlib": p.matplotlib}
            original = self._store.find_result(
                sha256_hex(reuse_key(p.model_version_id, p.request, p.run_ids, versions))
            )
            return _reproduce.reproduce(self._store, original, p)
        if isinstance(result, str):
            result = self._store.get_result(self._result_id(result))
        return _reproduce.reproduce(self._store, result, result.provenance)

    @_on_its_thread
    def export(self, result: ResultRef, directory: str | os.PathLike[str], *, pdf: bool = False) -> str:
        """Export a result's runs, design, result, and report into a new or empty directory (E1-E7; U5).

        With ``pdf``, ``report/`` also holds the report's PDF, through pandoc and lualatex (0018; 0081 item 31).

        Returns
        -------
        str
            The export's directory, absolute.

        Raises
        ------
        PathRefused
            For a directory that isn't empty; under a root, a path refused (E7, T5). Nothing is written.
        PandocMissing, PdfFailed
            With ``pdf``, when the PDF can't be made. Nothing is written.
        """
        target = self._path(directory, "the export's directory", directory=True)
        stored = self._store.get_result(self._result_id(result))
        return _export.export(self._store, stored, target, pdf=pdf)
