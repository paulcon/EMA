"""Layer 3b: the runner, the serial loop of 0015 and the only code that runs a model (AR4, P3).

architecture.md §6 (``ema.runner``) and §7 (steps 4–7 of one diagnostic evaluation, and ``test_model``'s);
data_model.md Q1, Q2, Q13, Q15, W4, and §10's run lock; contracts.md C34, C37, C41, C46–C49, C56; records 0010,
0015, 0056, 0063, 0071, 0072, 0074.

``resolve`` finds each design row's stored run, or a new key; ``price`` counts and times the new runs; ``run_new``
makes them one call at a time, each call checked against its approval (Q13) and the model's files (M16) before it
starts and stored (W4) when it ends; ``read_batch`` and ``replay_batch`` give a diagnostic its runs in the design's
order (C56).
"""

import contextlib
from collections.abc import Callable

import numpy as np

from ema.models.collect import collect, keep_or_remove
from ema.models.execute import ExecutedCall, execute
from ema.models.files import check_files, remove_tree
from ema.models.prepare import PreparedCall, prepare
from ema.models.processes import ModelProcesses
from ema.models.spec import LoadedModel
from ema.store import BatchCall, CurrentKey, Store
from ema.types.design import Design
from ema.types.errors import NotFound
from ema.types.identity import ID_DTYPE, batch_call_id, id_array, model_version_label, point_hash, run_id
from ema.types.model import PythonFunction
from ema.types.requests import Progress
from ema.types.results import Provenance
from ema.types.runs import Price, Resolution, Run, RunBatch, RunKey, RunStatus

_NO_RUN = "00" * 32


def _runnable(key: RunKey, current: CurrentKey | None) -> bool:
    """W4's attempt precondition (I2, I4; 0010): no run at the key and attempt 0, or the next attempt after a failure."""
    if current is None:
        return key.attempt == 0
    return current.status is RunStatus.FAILED and key.attempt == current.attempt + 1


def resolve(design: Design, model: LoadedModel, store: Store, *, retry_failed: bool) -> Resolution:
    """Resolve a design against the store (Q1): each row's stored run, or a new key (C46, C47; 0010).

    A row's key is the model version, its exact point (every bit: -0.0 is not 0.0), and its replicate; a key repeated
    in the design is one new run. A stored run is reused, a failed one too, unless ``retry_failed``: then the failed
    key is new, as the next attempt, stored beside the run it replaces (C47).

    Parameters
    ----------
    design
        The design, each point complete in the spec's order.
    model
        The loaded model; its model version is the design's.
    store
        The workspace's store.
    retry_failed
        Make the design's failed keys new runs.

    Returns
    -------
    Resolution
        Each row's stored run or new key; the new keys in the design's order of first appearance (record 0074,
        item 7); how many of the reused runs failed.

    Raises
    ------
    ValueError
        For a design of another model version, or points of another width.
    """
    mv = model.model_version_id
    width = len(model.spec.parameters)
    if design.identity is not None and design.identity.model_version_id != mv:
        raise ValueError(f"the design is of model version {design.identity.model_version_id}, not {mv}")
    if design.points.shape[1] != width and len(design):
        raise ValueError(f"a point of model {model.spec.name} has {width} values, not {design.points.shape[1]}")
    points = np.ascontiguousarray(design.points, dtype="<f8")
    replicates = design.replicates.tolist()
    distinct: dict[tuple[bytes, int], int] = {}
    row_distinct = np.empty(len(design), dtype=np.int64)
    for row in range(len(design)):
        row_distinct[row] = distinct.setdefault((points[row].tobytes(), replicates[row]), len(distinct))
    hashes = {raw: point_hash(np.frombuffer(raw, dtype="<f8")) for raw, _ in distinct}
    current = store.current_keys(mv, list(hashes.values()))  # Q1, keys only: the one store read
    run_ids: list[str] = []
    key_rows: list[int] = []
    new_keys: list[RunKey] = []
    reused_failed = 0
    for raw, replicate in distinct:
        digest = hashes[raw]
        stored = current.get((digest, replicate))
        failed = stored is not None and stored.status is RunStatus.FAILED
        if stored is not None and not (retry_failed and failed):
            run_ids.append(stored.run_id)
            key_rows.append(-1)
            reused_failed += failed
            continue
        attempt = 0 if stored is None else stored.attempt + 1
        run_ids.append(_NO_RUN)
        key_rows.append(len(new_keys))
        point = tuple(np.frombuffer(raw, dtype="<f8").tolist())  # hashed once (record 0074, item 24)
        new_keys.append(RunKey(point, digest, replicate, attempt, run_id(mv, digest, replicate, attempt)))
    distinct_ids = id_array(run_ids) if run_ids else np.zeros(0, dtype=ID_DTYPE)
    distinct_keys = np.asarray(key_rows, dtype=np.int64)
    return Resolution(design, mv, distinct_ids[row_distinct], distinct_keys[row_distinct], tuple(new_keys),
                      reused_failed)  # fmt: skip


def price(resolution: Resolution, store: Store) -> Price:
    """Price a resolution's new runs (P3; Q2): its counts, and ``new`` times the stored runs' mean time.

    The stored runs are every run of the model version, any status (Q2); with none, the time is unknown. Reused
    runs are counted once each, as new keys are (record 0074, item 8).

    Parameters
    ----------
    resolution
        The resolved design.
    store
        The workspace's store.

    Returns
    -------
    Price
        "96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)" (U2).
    """
    stored = resolution.row_runs[resolution.row_keys < 0]
    reused = len(np.unique(stored)) if len(stored) else 0
    count, mean = store.run_times(resolution.model_version_id)
    new = len(resolution.new_keys)
    time_s = None if mean is None else new * mean
    return Price.make(new=new, reused=reused, reused_failed=resolution.reused_failed, time_s=time_s, from_runs=count)


class _Loop:
    """``run_new``'s serial loop, one call at a time (0015).

    A class only so that the contract's broken toys change one step each (tests/contracts/runner.py; no
    monkeypatching, 0065; record 0074, item 6).

    The steps: ``next_call`` (Q13, W4's attempt precondition, and the call's size), ``check`` (the files, M16),
    ``call`` (prepare, execute, collect, then ``record``, W4, and ``keep``; on any exception, ``stored`` tells
    whether W4 committed: if not, ``stopped``, else ``keep``).
    """

    def __init__(
        self,
        model: LoadedModel,
        resolution: Resolution,
        approval_id: str,
        store: Store,
        processes: ModelProcesses,
        on_progress: Callable[[Progress], None] | None,
    ) -> None:
        if resolution.model_version_id != model.model_version_id:
            raise ValueError(f"the resolution is of model version {resolution.model_version_id}, not the model's")
        self.model, self.resolution, self.approval_id = model, resolution, approval_id
        self.store, self.processes, self.on_progress = store, processes, on_progress
        interface = model.spec.interface
        self.batch = isinstance(interface, PythonFunction) and interface.batch
        everything = max(len(resolution.new_keys), 1)
        self.size = (model.spec.batch_size or everything) if self.batch else 1

    def run(self) -> int:
        keys = self.resolution.new_keys
        total = len(keys)
        if not total:
            return 0
        done = 0
        while done < total:
            call = self.next_call(keys[done:])
            self.check()
            if not done:  # "0/n runs" once the first call is allowed to start (record 0074, item 23)
                self.progress(0, total)
            self.call(call)
            done += len(call)
            self.progress(done, total)
        return done

    def progress(self, done: int, total: int) -> None:
        if self.on_progress is not None:
            self.on_progress(Progress.of_runs(done, total))

    def next_call(self, pending: tuple[RunKey, ...]) -> tuple[RunKey, ...]:
        """Cut the next ``size`` keys to the leading ones Q13 covers and W4 would store (C37, C46, C48; P3, I4).

        Q13 counts only this approval's runs; a key run since the resolution, under another approval, fails W4's
        attempt precondition and is cut here, before its call could run it again and ``prepare`` wipe the stored
        run's directory (M14; record 0074, item 21).
        """
        mv = self.model.model_version_id
        candidate = pending[: self.size]
        coverage = self.store.approval_coverage(self.approval_id, candidate)
        label = model_version_label(self.model.spec.name, mv)
        if coverage.model_version_id != mv:
            raise ValueError(f"approval {self.approval_id} is of another model version than {label} (P3)")
        if not coverage.answer:
            raise ValueError(f"approval {self.approval_id} was answered no: no run is made under it (P3)")
        covered = next((i for i, c in enumerate(coverage.covered) if not c), len(candidate))
        current = self.store.current_keys(mv, [k.point_hash for k in candidate[:covered]])
        runnable = next((i for i, k in enumerate(candidate[:covered])
                         if not _runnable(k, current.get((k.point_hash, k.replicate)))), covered)  # fmt: skip
        if runnable == 0:
            why = "its run is already made, or its attempt isn't the next" if covered else (  # I2, I4; C48
                "its point isn't approved, or its run is made")  # fmt: skip
            raise ValueError(f"approval {self.approval_id} can't make run {candidate[0].run_id} of {label}: {why}")
        return candidate[:runnable]

    def check(self) -> None:
        """M16, C34: the tracked files hashed again; ``ModelChanged`` names the file."""
        check_files(self.model)

    def call(self, keys: tuple[RunKey, ...]) -> tuple[Run, ...]:
        layout = self.store.layout
        prepared: PreparedCall | None = None
        runs: tuple[Run, ...] | None = None
        try:
            prepared = prepare(self.model, keys, layout.runs, layout.files, approval_id=self.approval_id)
            executed = execute(self.model, prepared, self.processes)
            runs = collect(self.model, executed)
            self.record(runs, executed)
        except BaseException:
            if not self.stored(keys):
                self.stopped(keys, prepared)
            elif prepared is not None and runs is not None:
                # Ctrl-C just after W4's COMMIT: the runs are stored, so ``keep`` applies (I5, M14); the exception
                # that stopped the call matters more than one from ``keep``
                with contextlib.suppress(Exception):
                    self.keep(prepared, runs)
            raise
        self.keep(prepared, runs)
        return runs

    def stored(self, keys: tuple[RunKey, ...]) -> bool:
        """Whether W4 stored the call (I5): an exception can arrive after its COMMIT, before ``record`` returns.

        ``next_call`` lets no key with a run at its id start, so a stored first key is this call's. A check that is
        itself interrupted counts as stored: keeping a stopped call's directory is safer than deleting a stored one's.
        """
        try:
            self.store.get_run(keys[0].run_id)
        except NotFound:
            return False
        except BaseException:  # noqa: BLE001  (the exception that stopped the call is the one raised)
            return True
        return True

    def record(self, runs: tuple[Run, ...], executed: ExecutedCall) -> None:
        """W4: the call's runs together, with its batch call (I5, C49)."""
        call = runs[0].batch_call_id
        self.store.record_call(runs, None if call is None else BatchCall(call, len(runs), executed.time_s))

    def stopped(self, keys: tuple[RunKey, ...], prepared: PreparedCall | None) -> None:
        """Delete a call's directories, found from its keys, when it ended before W4 (0028, M14, C41)."""
        layout = self.store.layout
        directories = [layout.run_dir(k.run_id) for k in keys]
        if self.batch:
            directories.append(layout.run_dir(batch_call_id([k.run_id for k in keys])))
        for directory in directories:
            try:
                remove_tree(directory)
            except OSError:  # the exception that stopped the call matters more
                pass

    def keep(self, prepared: PreparedCall, runs: tuple[Run, ...]) -> None:
        """M14: delete the run directories ``keep`` doesn't keep, after W4 (I5)."""
        keep_or_remove(self.model, prepared, runs)


def run_new(
    model: LoadedModel,
    resolution: Resolution,
    approval_id: str,
    store: Store,
    processes: ModelProcesses,
    *,
    on_progress: Callable[[Progress], None] | None = None,
) -> int:
    """Make a resolution's new runs under an approval, one call at a time (0015; P3).

    The caller holds ``store.run_lock()`` (architecture.md §7; data_model.md §10). Before each call: Q13 for its
    keys, refusing a key the approval doesn't cover, an approval answered no, or another model version, and
    ``check_files`` (M16, C34). A call holds at most ``batch_size`` keys, and never more than remain approved,
    counted when it starts (C37, C48); a model that isn't a batch function has calls of one run. Each call is
    prepared, executed, collected, stored (W4), and then ``keep`` applied (I5, M14). Ctrl-C, or any exception, during
    a call kills it, deletes its directories, and passes through, with every finished call's runs stored (C49); one
    that arrives after W4's COMMIT leaves the call stored, and ``keep`` applied. An exception from ``on_progress``
    passes through the same way. A key whose run was made since the resolution, under another approval, is refused
    before its call starts (I4).

    Parameters
    ----------
    model
        The loaded model, of the resolution's model version.
    resolution
        The resolved design.
    approval_id
        The approval the new runs are made under (W3).
    store
        The workspace's store.
    processes
        The workspace's children (0026).
    on_progress
        Called with "0/96 runs" before the first call and after each call (PM10).

    Returns
    -------
    int
        The runs made: every new key's, unless an exception stopped the loop.

    Raises
    ------
    ValueError
        For a call its approval can't cover, or a key whose run was made since the resolution (an error in EMA's
        code: the workspace approves the resolution it runs, under the run lock).
    NotFound
        For an unknown approval.
    ModelChanged
        When a tracked file changed since loading, naming it.
    """
    return _Loop(model, resolution, approval_id, store, processes, on_progress).run()


def _new_rows(runs_approval_ids: np.ndarray, approval_id: str | None) -> np.ndarray:
    if approval_id is None:
        return np.zeros(len(runs_approval_ids), dtype=bool)
    return np.asarray(runs_approval_ids == id_array([approval_id])[0], dtype=bool)


def read_batch(design: Design, run_ids: np.ndarray, store: Store, *, new_approval: str | None) -> RunBatch:
    """Read the given run for each design row, in design order (C56; Q15).

    The ids are the ones the workspace builds: the resolution's ``row_runs``, each new row's ``RunKey.run_id`` filled
    in through ``row_keys``. Never "the current run now", so another process's retry can't slip in.

    Parameters
    ----------
    design
        The design.
    run_ids
        One run id per design row, in any form ``id_array`` reads.
    store
        The workspace's store.
    new_approval
        This evaluation's approval: a row is new when its run was made under it (E6); None with no new runs.

    Returns
    -------
    RunBatch
        The design, its runs, and which rows are new.

    Raises
    ------
    ValueError
        For a number of ids that isn't the design's rows.
    NotFound
        For an id with no stored run.
    """
    ids = run_ids if isinstance(run_ids, np.ndarray) and run_ids.dtype == ID_DTYPE else id_array(run_ids)
    if len(ids) != len(design):
        raise ValueError(f"a run batch has one run id per design row: {len(ids)} ids, {len(design)} rows")
    runs = store.runs_by_id(ids)
    return RunBatch(design, runs, _new_rows(runs.approval_ids, new_approval))


def replay_batch(provenance: Provenance, store: Store) -> RunBatch:
    """Read a replay's batch (U8; 0062, 0063): the provenance's runs, and a design built from their stored points.

    The design has the provenance's identity, the stored runs' points and replicates, and its design structure's
    levels and lines, with no generator; a row is new when its run's approval is the provenance's.

    Parameters
    ----------
    provenance
        The provenance replayed.
    store
        The workspace's store.

    Returns
    -------
    RunBatch
        In the provenance's order.

    Raises
    ------
    NotFound
        For a run that isn't stored.
    """
    runs = store.runs_by_id(provenance.run_ids, points=True)
    assert runs.points is not None
    structure = provenance.design_structure
    design = Design(provenance.design, runs.points, runs.replicates, structure.levels, structure.lines)
    return RunBatch(design, runs, _new_rows(runs.approval_ids, provenance.approval_id))
