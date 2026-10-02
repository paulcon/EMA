"""The store: one function per write (W1–W6) and read (Q1–Q15) of data_model.md §7 and §8, each citing its id.

Only this package opens the database (AR5), and only the main process writes it (0015). Every write is one
``BEGIN IMMEDIATE`` transaction, committed before it returns (§3.3); no row is ever updated, and only W6 deletes,
a diagnostic result's own rows (I1). Reads run in autocommit, so each statement holds SQLite's shared lock only
while it runs; Q7 and Q15 read in chunks of ``chunk_rows`` rows, one statement each, so a writer in another
connection waits at most one chunk (0056).
"""

import errno
import json
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType, TracebackType
from typing import Any, Self, cast

import numpy as np

from ema.store import migrations
from ema.store.layout import Layout
from ema.store.lock import run_lock
from ema.store.records import (
    Approval,
    ApprovedPoint,
    BatchCall,
    Confirmation,
    Coverage,
    CurrentKey,
    Loading,
    ModelVersion,
)
from ema.types.design import DesignIdentity
from ema.types.errors import AmbiguousId, NotFound, RequestError, WorkspaceBusy, WorkspaceVersion
from ema.types.identity import (
    ID_DTYPE,
    TrackedFile,
    approval_id,
    batch_call_id,
    canonical_json,
    id_array,
    model_version_label,
    point_hash,
    reuse_key,
    run_id,
    sha256_hex,
    version_hash,
)
from ema.types.model import Keep, ModelSpec
from ema.types.requests import Request, TestRunRequest
from ema.types.results import Counts, DiagnosticResult, MeasuredNoisy, Provenance, ResultSummary
from ema.types.runs import FailureKind, Price, Run, RunColumns, RunKey, RunStatus
from ema.types.text import parse_timestamp, timestamp_text

#: Seconds a statement waits for another connection's lock before it fails (data_model.md §10).
BUSY_TIMEOUT_S = 60.0
#: Rows per statement when reading many (§6, §8: Q1, Q7, Q15).
CHUNK_ROWS = 30_000
#: The point run's diagnostic name: the only result with a measured-noisy record (I10; point_run.md).
POINT_RUN = "point_run"

#: The id kinds Q11 resolves: each one's table, its id column, and its name in messages.
ID_KINDS: Mapping[str, tuple[str, str, str]] = {
    "model_version": ("model_versions", "model_version_id", "model version"),
    "approval": ("approvals", "approval_id", "approval"),
    "run": ("runs", "run_id", "run"),
    "batch_call": ("batch_calls", "batch_call_id", "batch call"),
    "result": ("results", "result_id", "diagnostic result"),
}

_RUN_COLUMNS = (
    "run_id, model_version_id, point, replicate, attempt, status, kind, reason, stderr_tail, exit_code, time_s, "
    "batch_call_id, host, program, approval_id"
)
_STATUS = {s.value: s for s in RunStatus}
_KIND = {k.value: k for k in FailureKind}
_STATUS_CODE = {s.value: s.code for s in RunStatus}
_KIND_CODE = {k.value: k.code for k in FailureKind}
_ZERO_ID = bytes(32)


def _blob(hex_id: str, what: str) -> bytes:
    """Return an id's 32 bytes; ``NotFound`` for anything that isn't 64 hex digits, since no row has it."""
    try:
        raw = bytes.fromhex(hex_id)
    except (TypeError, ValueError):
        raw = b""
    if len(raw) != 32:
        raise NotFound(f"no {what} {hex_id!r}")
    return raw


def _hex(raw: bytes | None) -> str | None:
    return None if raw is None else raw.hex()


def _now() -> str:
    """Every timestamp is written by the store (§3.3): now, in UTC, to the millisecond."""
    return timestamp_text(datetime.now(UTC))


def _chunks(items: Sequence[Any], size: int) -> Iterator[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _marks(n: int) -> str:
    return ",".join("?" * n)


def _busy(error: sqlite3.OperationalError) -> bool:
    text = str(error).lower()
    return "locked" in text or "busy" in text


def _request_from(text: str) -> Request | TestRunRequest:
    data = json.loads(text)
    if "test_run" in data:
        return TestRunRequest(tuple(data["test_run"]["point"]))
    return Request(**data)


@dataclass(frozen=True)
class _Listed:
    """What ``ResultSummary.make`` reads of a result, from a ``results`` row without its runs (Q8)."""

    result_id: str
    diagnostic: str
    prediction: str
    counts: Counts


class _Columns:
    """Rows of ``runs`` (in ``_RUN_COLUMNS``' order) and their model predictions, gathered into columns (Q7, Q15)."""

    def __init__(self, names: Sequence[str], *, points: bool, tails: bool) -> None:
        self.names, self.want_points, self.want_tails = tuple(names), points, tails
        self.ids: list[bytes] = []
        self.points: list[list[float]] = []
        self.replicates: list[int] = []
        self.status: list[int] = []
        self.kind: list[int] = []
        self.time_s: list[float] = []
        self.host: list[str] = []
        self.program: list[str] = []
        self.batch: list[bytes] = []
        self.approval: list[bytes] = []
        self.values: dict[str, list[float]] = {n: [] for n in names}
        self.reasons: dict[str, str] = {}
        self.tails: dict[str, str] = {}
        self.missing: dict[str, dict[str, str]] = {}
        self._texts: dict[str, str] = {}

    def _shared(self, text: str) -> str:
        return self._texts.setdefault(text, text)  # few distinct hosts and programs: one string each

    def add(self, rows: Sequence[tuple[Any, ...]], predictions: Mapping[bytes, list[tuple[str, Any, Any]]]) -> None:
        nan = float("nan")
        if self.want_points:
            self.points.extend(json.loads("[" + ",".join(row[2] for row in rows) + "]"))
        for row in rows:
            raw = row[0]
            self.ids.append(raw)
            self.replicates.append(row[3])
            self.status.append(_STATUS_CODE[row[5]])
            self.kind.append(-1 if row[6] is None else _KIND_CODE[row[6]])
            if row[7] is not None:
                self.reasons[raw.hex()] = row[7]
                if self.want_tails and row[8] is not None:
                    self.tails[raw.hex()] = row[8]
            self.time_s.append(row[10])
            self.batch.append(row[11] or _ZERO_ID)
            self.host.append(self._shared(row[12]))
            self.program.append(self._shared(row[13]))
            self.approval.append(row[14])
            read = {name: value for name, value, _ in predictions.get(raw, ())}
            for name, column in self.values.items():
                value = read.get(name)
                column.append(nan if value is None else value)
            for name, _, reason in predictions.get(raw, ()):
                if reason is not None:
                    self.missing.setdefault(name, {})[raw.hex()] = reason

    def build(self, order: np.ndarray | None = None) -> RunColumns:
        def arr(values: list[Any], dtype: Any) -> np.ndarray:
            out = np.array(values, dtype=dtype)
            return out if order is None else out[order]

        def ids(raws: list[bytes]) -> np.ndarray:
            out = np.frombuffer(b"".join(raws), dtype=ID_DTYPE).copy()
            return out if order is None else out[order]

        n = len(self.ids)
        points = None
        if self.want_points:
            width = len(self.points[0]) if self.points else 0
            points = arr(self.points, np.float64).reshape(-1 if n else 0, width)
        return RunColumns(
            run_ids=ids(self.ids),
            points=points,
            replicates=arr(self.replicates, np.int64),
            status=arr(self.status, np.int64),
            kind=arr(self.kind, np.int64),
            values={name: arr(v, np.float64) for name, v in self.values.items()},
            reasons=self.reasons,
            stderr_tails=self.tails,
            missing=self.missing,
            time_s=arr(self.time_s, np.float64),
            host=arr(self.host, object),
            program=arr(self.program, object),
            batch_call_ids=ids(self.batch),
            approval_ids=ids(self.approval),
        )


class Store:
    """A workspace's store: its database, paths, run lock, and result directories (data_model.md; architecture.md §5).

    Not frozen: it holds the connection. One per thread that uses it, as a SQLite connection stays on its thread
    (§10, 0056); a context manager, closing on exit. Open one with ``Store.open``.

    Attributes
    ----------
    layout : Layout
        The workspace's paths.
    """

    #: Rows per statement for the chunked reads; a class attribute so a test can make it small.
    chunk_rows: int = CHUNK_ROWS
    #: The busy timeout, in seconds; a class attribute so a test can make it short.
    busy_timeout_s: float = BUSY_TIMEOUT_S

    def __init__(self, conn: sqlite3.Connection, layout: Layout) -> None:
        self._conn = conn
        self.layout = layout
        self._prediction_names: dict[bytes, tuple[str, ...]] = {}
        # Rows per chunk: chunk_rows, but never more bound variables than this SQLite allows (one is the model
        # version's, in Q1).
        self._chunk = max(1, min(self.chunk_rows, conn.getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER) - 1))

    # -- opening and closing ------------------------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | os.PathLike[str], *, create: bool = True) -> "Store":
        """Open the store of the workspace at ``path``: create it, migrate it, or refuse it (data_model.md §10, §11).

        Parameters
        ----------
        path
            The workspace's directory.
        create
            Create the workspace (its directory, ``ema.db``, ``runs/``, ``files/``, ``results/``) when missing.

        Returns
        -------
        Store
            Connected with the rollback journal, ``synchronous=FULL``, foreign keys on, and a busy timeout of
            ``busy_timeout_s`` (60 s), so a read in one connection delays a write in another instead of failing it.

        Raises
        ------
        NotFound
            With ``create=False``, when there is no workspace at ``path``.
        WorkspaceVersion
            For a newer schema, naming both versions (an older one is migrated after copying ``ema.db``); a file
            that isn't an EMA workspace's database.
        WorkspaceBusy
            When another connection holds the database's lock past the busy timeout.
        """
        layout = Layout.of(path)
        if create:
            for directory in (layout.root, layout.runs, layout.files, layout.results):
                os.makedirs(directory, exist_ok=True)
        elif not os.path.isfile(layout.db):
            raise NotFound(f"no workspace at {layout.root}: it has no ema.db")
        conn = sqlite3.connect(layout.db, timeout=cls.busy_timeout_s, isolation_level=None)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = FULL")
            migrations.prepare(conn, layout.db)
        except sqlite3.OperationalError as error:
            conn.close()
            if _busy(error):
                raise WorkspaceBusy(
                    f"the workspace's database {layout.db} stayed locked by another connection for "
                    f"{cls.busy_timeout_s:g} s"
                ) from error
            raise
        except sqlite3.DatabaseError as error:  # "file is not a database", or a damaged one
            conn.close()
            raise WorkspaceVersion(f"{layout.db} is not an EMA workspace's database: {error}") from error
        except BaseException:
            conn.close()
            raise
        return cls(conn, layout)

    def close(self) -> None:
        """Close the connection."""
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, kind: type[BaseException] | None, error: BaseException | None, tb: TracebackType | None) -> None:
        self.close()

    def run_lock(self) -> AbstractContextManager[None]:
        """Hold the workspace's run lock for a ``with`` block: one process at a time makes runs (§10).

        Raises
        ------
        WorkspaceBusy
            When another holder has it, naming the holder and the lock.
        """
        return run_lock(self.layout.lock)

    @contextmanager
    def result_directory(self, result_id: str) -> Iterator[str]:
        """Yield a temporary directory for a result's files, renamed into ``results/<result id>/`` on exit (§6).

        If the result's directory exists already: with a stored result (Q5), the temporary directory is discarded,
        and the stored result is the answer (W5 then writes nothing, 0056); with no stored result, it is a
        leftover (or another process's identical directory, S10) and is replaced. On an exception, the temporary
        directory is removed and nothing is put in place.

        Safe for several processes at once (review round 1, M1): the directory in place is never deleted where it
        is. A first rename that finds it there is retried under the database's write lock, which W5 also holds
        while it looks for the directory: the one in place is moved aside atomically, ours renamed in, and the
        moved copy deleted afterwards, so W5 never sees the directory missing.

        Raises
        ------
        ValueError
            For a result id that isn't 64 lowercase hex digits.
        """
        if len(result_id) != 64 or any(ch not in "0123456789abcdef" for ch in result_id):
            raise ValueError(f"a result id is 64 lowercase hex digits, not {result_id!r}")
        final = self.layout.result_dir(result_id)
        os.makedirs(self.layout.results, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix=f".{result_id[:12]}-", dir=self.layout.results)
        try:
            yield tmp
            self._put_in_place(tmp, final, result_id)
        finally:
            if os.path.lexists(tmp):
                shutil.rmtree(tmp, ignore_errors=True)

    def _put_in_place(self, tmp: str, final: str, result_id: str) -> None:
        """Rename ``tmp`` to ``final``; if a directory is there, keep it with a stored result, else replace it (§6)."""
        try:
            os.rename(tmp, final)
            return
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                raise
        asides: list[str] = []
        try:
            with self._write() as c:
                while not c.execute(
                    "SELECT 1 FROM results WHERE result_id = ?", (bytes.fromhex(result_id),)
                ).fetchone():
                    aside = tempfile.mkdtemp(prefix=f".{result_id[:12]}-old-", dir=self.layout.results)
                    asides.append(aside)
                    try:
                        os.rename(final, os.path.join(aside, "old"))
                    except FileNotFoundError:
                        pass  # gone meanwhile (a rename outside the lock): nothing to move aside
                    try:
                        os.rename(tmp, final)
                        return
                    except OSError as error:
                        if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                            raise
                # stored meanwhile, with its directory in place: ours is discarded (0056)
        finally:
            for aside in asides:
                shutil.rmtree(aside, ignore_errors=True)

    # -- transactions -------------------------------------------------------------------------------------------

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> list[Any]:
        """Run one read statement to its end; a lock held past the busy timeout is ``WorkspaceBusy``."""
        try:
            return self._conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as error:
            if _busy(error):
                raise self._busy_error() from error
            raise

    def _busy_error(self) -> WorkspaceBusy:
        return WorkspaceBusy(
            f"the workspace's database {self.layout.db} stayed locked by another connection for "
            f"{self.busy_timeout_s:g} s"
        )

    def _step(self, sql: str, persist: bool) -> None:
        """Run BEGIN or COMMIT; with ``persist``, wait past the busy timeout until it succeeds (W4, C49)."""
        while True:
            try:
                self._conn.execute(sql)
                return
            except sqlite3.OperationalError as error:
                if not _busy(error):
                    raise
                if not persist:
                    raise self._busy_error() from error

    @contextmanager
    def _write(self, *, persist: bool = False) -> Iterator[sqlite3.Connection]:
        """One write transaction (§3.3, §7): ``BEGIN IMMEDIATE``, committed on exit, rolled back on any exception."""
        self._step("BEGIN IMMEDIATE", persist)
        try:
            yield self._conn
            if self._conn.in_transaction:  # W5 rolls back itself when it finds its result stored
                self._step("COMMIT", persist)
        except BaseException:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
            raise

    # -- W1, Q3, Q14: model versions and loadings ---------------------------------------------------------------

    def record_loading(self, spec: ModelSpec, spec_path: str, files: Sequence[TrackedFile]) -> str:
        """W1: record a ``load_model``: the model version if new, and a loading (§5.1, §5.2; 0029, 0054).

        Parameters
        ----------
        spec
            The validated spec, with its settings (``keep``, ``batch_size``, ``timeout_s``).
        spec_path
            The spec file, absolute; stored resolved (§3.2: symbolic links and ``..`` resolved).
        files
            Its tracked files, hashed.

        Returns
        -------
        str
            The model version id. A repeated loading adds a loading row only; the name now means this version,
            path, and settings.
        """
        if not os.path.isabs(spec_path):
            raise ValueError(f"a loading's spec path is absolute, not {spec_path!r}")
        spec_path = os.path.realpath(spec_path)
        tracked = tuple(sorted(files, key=lambda f: f.path))
        mv = version_hash(spec, tracked)
        now = _now()
        with self._write() as c:
            if (
                c.execute("SELECT 1 FROM model_versions WHERE model_version_id = ?", (bytes.fromhex(mv),)).fetchone()
                is None
            ):
                listed = canonical_json([[f.path, f.sha256, f.shared] for f in tracked])
                c.execute(
                    "INSERT INTO model_versions VALUES (?, ?, ?, ?, ?)",
                    (bytes.fromhex(mv), spec.name, spec.versioned_json(), listed, now),
                )
            c.execute(
                "INSERT INTO loadings (name, model_version_id, spec_path, keep, batch_size, timeout_s, loaded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (spec.name, bytes.fromhex(mv), spec_path, spec.keep.value, spec.batch_size, float(spec.timeout_s), now),
            )
        return mv

    def current_loading(self, name: str) -> Loading | None:
        """Q3: what a model name means now: its latest loading's model version, spec file, and settings (0054)."""
        rows = self._execute(
            "SELECT loading, name, model_version_id, spec_path, keep, batch_size, timeout_s, loaded_at FROM loadings "
            "WHERE name = ? ORDER BY loading DESC LIMIT 1",
            (name,),
        )
        if not rows:
            return None
        n, name, mv, path, keep, batch, timeout, at = rows[0]
        return Loading(n, name, mv.hex(), path, Keep(keep), batch, timeout, parse_timestamp(at))

    def model_names(self) -> tuple[str, ...]:
        """Q3, every name: the model names loaded, sorted, for ``list_models`` (record 0080 item 3)."""
        return tuple(row[0] for row in self._execute("SELECT DISTINCT name FROM loadings ORDER BY name"))

    def model_version(self, model_version_id: str) -> ModelVersion:
        """Q14: a model version's spec and tracked files, by its id (0056).

        Raises
        ------
        NotFound
            For an unknown id.
        """
        raw = _blob(model_version_id, "model version")
        rows = self._execute(
            "SELECT name, spec, files, created_at FROM model_versions WHERE model_version_id = ?", (raw,)
        )
        if not rows:
            raise NotFound(f"no model version {model_version_id}")
        name, spec, listed, at = rows[0]
        files = tuple(TrackedFile(path, digest, shared) for path, digest, shared in json.loads(listed))
        return ModelVersion(raw.hex(), name, ModelSpec.from_json(spec), files, parse_timestamp(at))

    def _predictions_of(self, mv: bytes) -> tuple[str, ...]:
        """Return the model predictions of a model version's spec (I6), in order; cached, as rows never change."""
        if mv not in self._prediction_names:
            rows = self._execute("SELECT spec FROM model_versions WHERE model_version_id = ?", (mv,))
            if not rows:
                raise NotFound(f"no model version {mv.hex()}")
            self._prediction_names[mv] = tuple(p["name"] for p in json.loads(rows[0][0])["predictions"])
        return self._prediction_names[mv]

    # -- W2, W3, Q4, Q12, Q13: confirmations and approvals ------------------------------------------------------

    def record_confirmation(self, spec_path: str, spec_sha256: str, question: str, answer: bool) -> None:
        """W2: record a confirmation to save a drafted model spec, and its answer (§5.3; 0049, T3)."""
        with self._write() as c:
            c.execute(
                "INSERT INTO confirmations (spec_path, spec_sha256, question, answer, asked_at) VALUES (?, ?, ?, ?, ?)",
                (spec_path, bytes.fromhex(spec_sha256), question, int(bool(answer)), _now()),
            )

    def record_approval(
        self,
        *,
        model_version_id: str,
        asked_for: str,
        request: Request | TestRunRequest,
        design: DesignIdentity | None,
        price: Price,
        question: str,
        answer: bool,
        points: Sequence[RunKey],
    ) -> str:
        """W3: record a price shown and its answer, and on a yes the points and replicates it covers (§5.4, §5.5).

        Every answer is stored, yes or no (T3). The id hashes the number of approvals stored before it (§3.4).

        Parameters
        ----------
        model_version_id
            The model version priced.
        asked_for
            "diagnostic_evaluation" with a ``Request`` and its design's identity, or "test_run" with a
            ``TestRunRequest`` and no design (0049).
        request, design
            What was priced.
        price
            The price shown (Q1, Q2): its new, reused, and reused-failed counts and its time.
        question
            The text shown, in full.
        answer
            Yes or no.
        points
            The new keys priced, one per new run: ``price.new`` distinct points and replicates (P3).

        Returns
        -------
        str
            The approval id.

        Raises
        ------
        ValueError
            For no new runs (C50), points that aren't the price's new runs, or a design that doesn't match
            ``asked_for``.
        NotFound
            For an unknown model version.
        """
        keys = {(k.point_hash, k.replicate) for k in points}
        if price.new < 1:
            raise ValueError("no approval is asked for no new runs (C50)")
        if len(points) != price.new:
            raise ValueError(f"an approval's points are its price's {price.new} new runs, not {len(points)}")
        if len(keys) != len(points):
            raise ValueError("an approval covers each point and replicate once: one is given twice")
        if (design is None) != (asked_for == "test_run"):
            raise ValueError("an approval has a design exactly when it is for a diagnostic evaluation (0049)")
        mv = _blob(model_version_id, "model version")
        with self._write() as c:
            if c.execute("SELECT 1 FROM model_versions WHERE model_version_id = ?", (mv,)).fetchone() is None:
                raise NotFound(f"no model version {model_version_id}")
            n_before = c.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
            aid = approval_id(mv.hex(), asked_for, request, price.new, price.reused, n_before)
            c.execute(
                "INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    bytes.fromhex(aid),
                    mv,
                    asked_for,
                    canonical_json(request.canonical()),
                    None if design is None else canonical_json(design.canonical()),
                    price.new,
                    price.reused,
                    price.reused_failed,
                    price.time_s,
                    question,
                    int(bool(answer)),
                    _now(),
                ),
            )
            if answer:
                c.executemany(
                    "INSERT INTO approval_points VALUES (?, ?, ?)",
                    ((bytes.fromhex(aid), bytes.fromhex(h), r) for h, r in sorted(keys)),
                )
        return aid

    def has_approval(self, model_version_id: str) -> bool:
        """Q4: whether this model version has had an approval answered yes (U2's first approval shows more)."""
        return bool(
            self._execute(
                "SELECT 1 FROM approvals WHERE model_version_id = ? AND answer = 1 LIMIT 1",
                (_blob(model_version_id, "model version"),),
            )
        )

    def approvals(self) -> tuple[Approval, ...]:
        """Q12: every approval, with its question and answer, in order (T3)."""
        rows = self._execute(
            "SELECT approval_id, model_version_id, asked_for, request, design, new, reused, reused_failed, time_s, "
            "question, answer, asked_at FROM approvals ORDER BY asked_at, rowid"
        )
        return tuple(
            Approval(
                aid.hex(),
                mv.hex(),
                asked_for,
                _request_from(request),
                None if design is None else DesignIdentity(**json.loads(design)),
                new,
                reused,
                reused_failed,
                time_s,
                question,
                bool(answer),
                parse_timestamp(at),
            )
            for aid, mv, asked_for, request, design, new, reused, reused_failed, time_s, question, answer, at in rows
        )

    def approval_points(self, approval_id: str) -> tuple[ApprovedPoint, ...]:
        """Q12 (an audit's detail): the points and replicates an approval covers, by point hash (P3)."""
        aid = _blob(approval_id, "approval")
        rows = self._execute(
            "SELECT point_hash, replicate FROM approval_points WHERE approval_id = ? ORDER BY point_hash, replicate",
            (aid,),
        )
        return tuple(ApprovedPoint(aid.hex(), h.hex(), r) for h, r in rows)

    def confirmations(self) -> tuple[Confirmation, ...]:
        """Q12: every confirmation, with its question and answer, in order (T3)."""
        rows = self._execute(
            "SELECT confirmation, spec_path, spec_sha256, question, answer, asked_at FROM confirmations "
            "ORDER BY asked_at, confirmation"
        )
        return tuple(Confirmation(n, p, h.hex(), q, bool(a), parse_timestamp(t)) for n, p, h, q, a, t in rows)

    def approval_coverage(self, approval_id: str, keys: Sequence[RunKey]) -> Coverage:
        """Q13: which of one call's keys an approval covers and has no run for yet, and its model version (0056).

        The runner asks before each call and refuses a key not covered, or another model version (P3).

        Raises
        ------
        NotFound
            For an unknown approval.
        """
        aid = _blob(approval_id, "approval")
        rows = self._execute("SELECT model_version_id, answer FROM approvals WHERE approval_id = ?", (aid,))
        if not rows:
            raise NotFound(f"no approval {approval_id}")
        mv, answer = rows[0]
        covered = []
        for key in keys:
            ph = bytes.fromhex(key.point_hash)
            approved = self._execute(
                "SELECT 1 FROM approval_points WHERE approval_id = ? AND point_hash = ? AND replicate = ?",
                (aid, ph, key.replicate),
            )
            made = self._execute(
                "SELECT 1 FROM runs WHERE model_version_id = ? AND point_hash = ? AND replicate = ? AND approval_id = ?",
                (mv, ph, key.replicate, aid),
            )
            covered.append(bool(approved) and not made)
        return Coverage(aid.hex(), mv.hex(), bool(answer), tuple(covered))

    # -- W4, Q1, Q2, Q9: runs ------------------------------------------------------------------------------------

    def record_call(self, runs: Sequence[Run], batch_call: BatchCall | None = None) -> None:
        """W4: store one finished call's runs and their model predictions, together or not at all (§5.6–§5.8; C49).

        Checked first, in the same transaction: each run's id is its key's hash (I3); its approval said yes for its
        model version, covers its point and replicate, and has no run there yet (I4, P3); its attempt is one more
        than the key's current run, which failed, or 0 (I2, C47); an ok run has every model prediction of its spec
        (I6). A lock held by another connection is waited for past the busy timeout, since the call has finished
        and its runs must be stored: a busy ``BEGIN`` or ``COMMIT`` is tried again, and a busy statement inside the
        transaction (a large call's spill to the database file, which waits for readers) rolls it back and tries
        the whole transaction again.

        Parameters
        ----------
        runs
            One run, or a batch call's runs in call order (0025).
        batch_call
            The batch call, for a batch Python function's call; its id is its runs' (``batch_call_id``), and each
            run names it.

        Raises
        ------
        ValueError
            When a check fails; nothing is stored.
        """
        runs = tuple(runs)
        hashes = self._check_keys(runs, batch_call)
        while True:
            try:
                self._insert_call(runs, hashes, batch_call)
                return
            except sqlite3.OperationalError as error:
                if not _busy(error):
                    raise

    def _insert_call(self, runs: Sequence[Run], hashes: Sequence[str], batch_call: BatchCall | None) -> None:
        """W4's transaction: its checks, then the call's rows."""
        with self._write(persist=True) as c:
            self._check_approvals(c, runs, hashes)
            self._check_attempts(c, runs, hashes)
            self._check_predictions(c, runs)
            if batch_call is not None:
                c.execute(
                    "INSERT INTO batch_calls VALUES (?, ?, ?)",
                    (bytes.fromhex(batch_call.batch_call_id), batch_call.size, float(batch_call.time_s)),
                )
            c.executemany(
                f"INSERT INTO runs ({_RUN_COLUMNS}, point_hash) VALUES ({_marks(16)})",
                (
                    (
                        bytes.fromhex(r.run_id),
                        bytes.fromhex(r.model_version_id),
                        canonical_json(list(r.point)),
                        r.replicate,
                        r.attempt,
                        r.status.value,
                        None if r.kind is None else r.kind.value,
                        r.reason,
                        r.stderr_tail,
                        r.exit_code,
                        float(r.time_s),
                        None if r.batch_call_id is None else bytes.fromhex(r.batch_call_id),
                        r.host,
                        r.program,
                        bytes.fromhex(r.approval_id),
                        bytes.fromhex(h),
                    )
                    for r, h in zip(runs, hashes, strict=True)
                ),
            )
            c.executemany(
                "INSERT INTO predictions VALUES (?, ?, ?, ?)",
                (
                    (bytes.fromhex(r.run_id), name, value, r.missing.get(name) if value is None else None)
                    for r in runs
                    for name, value in r.predictions.items()
                ),
            )

    def _check_keys(self, runs: Sequence[Run], batch_call: BatchCall | None) -> list[str]:
        """Check the call's shape and I3: each run's point hash is its point's, and its id its key's hash."""
        if not runs:
            raise ValueError("a call stores at least one run")
        if batch_call is None:
            if len(runs) != 1 or runs[0].batch_call_id is not None:
                raise ValueError("a call that isn't a batch call stores one run, with no batch call")
        elif (
            batch_call.batch_call_id != batch_call_id([r.run_id for r in runs])
            or batch_call.size != len(runs)
            or any(r.batch_call_id != batch_call.batch_call_id for r in runs)
            or not batch_call.time_s >= 0
        ):
            raise ValueError("a batch call's id is its runs' ids', its size their number, and each run names it")
        hashes = [point_hash(r.point) for r in runs]
        for r, h in zip(runs, hashes, strict=True):
            if r.run_id != run_id(r.model_version_id, h, r.replicate, r.attempt):
                raise ValueError(f"run {r.run_id}: its id is not its key's hash (I3)")
        if len({(r.model_version_id, h, r.replicate) for r, h in zip(runs, hashes, strict=True)}) != len(runs):
            raise ValueError("a call makes each key once: a point and replicate is given twice")
        return hashes

    def _check_approvals(self, c: sqlite3.Connection, runs: Sequence[Run], hashes: Sequence[str]) -> None:
        """I4 (P3, C48): an approval answered yes for the run's model version, covering its key, with no run there."""
        seen: dict[str, tuple[bytes, int] | None] = {}
        for r, h in zip(runs, hashes, strict=True):
            aid = bytes.fromhex(r.approval_id)
            if r.approval_id not in seen:
                row = c.execute(
                    "SELECT model_version_id, answer FROM approvals WHERE approval_id = ?", (aid,)
                ).fetchone()
                seen[r.approval_id] = row
            row = seen[r.approval_id]
            if row is None or not row[1] or row[0].hex() != r.model_version_id:
                raise ValueError(f"run {r.run_id}: its approval did not say yes for its model version (P3)")
            ph = bytes.fromhex(h)
            if (
                c.execute(
                    "SELECT 1 FROM approval_points WHERE approval_id = ? AND point_hash = ? AND replicate = ?",
                    (aid, ph, r.replicate),
                ).fetchone()
                is None
            ):
                raise ValueError(f"run {r.run_id}: its approval doesn't cover its point and replicate (P3)")
            if c.execute(
                "SELECT 1 FROM runs WHERE model_version_id = ? AND point_hash = ? AND replicate = ? AND approval_id = ?",
                (row[0], ph, r.replicate, aid),
            ).fetchone():
                raise ValueError(f"run {r.run_id}: its approval already has a run at its key (I4)")

    def _check_attempts(self, c: sqlite3.Connection, runs: Sequence[Run], hashes: Sequence[str]) -> None:
        """I2 (C47): the attempt is one more than the key's current run, which failed, or 0 when there is none."""
        for r, h in zip(runs, hashes, strict=True):
            row = c.execute(
                "SELECT attempt, status FROM runs WHERE model_version_id = ? AND point_hash = ? AND replicate = ? "
                "ORDER BY attempt DESC LIMIT 1",
                (bytes.fromhex(r.model_version_id), bytes.fromhex(h), r.replicate),
            ).fetchone()
            expected = 0 if row is None else row[0] + 1
            if row is not None and row[1] != RunStatus.FAILED.value:
                raise ValueError(f"run {r.run_id}: only a failed run is retried (0010)")
            if r.attempt != expected:
                raise ValueError(f"run {r.run_id}: attempt {r.attempt}, but the key's next is {expected} (I2)")

    def _check_predictions(self, c: sqlite3.Connection, runs: Sequence[Run]) -> None:
        """I6 (0022, 0043): an ok run has exactly its spec's model predictions, each a value or a reason."""
        for r in runs:
            if r.status is RunStatus.OK:
                names = self._predictions_of(bytes.fromhex(r.model_version_id))
                if set(r.predictions) != set(names):
                    raise ValueError(f"run {r.run_id}: an ok run has every model prediction of its spec: {names}")

    def current_runs(self, model_version_id: str, point_hashes: Sequence[str]) -> dict[tuple[str, int], Run]:
        """Q1: the current run (the highest attempt) at each stored key of these points, for pricing and running.

        Parameters
        ----------
        model_version_id
            The model version.
        point_hashes
            The design's point hashes (repeats are read once).

        Returns
        -------
        dict
            ``(point hash, replicate)`` to its current run, for the keys with a stored run (C46, C47).
        """
        mv = _blob(model_version_id, "model version")
        distinct = list(dict.fromkeys(point_hashes))
        out: dict[tuple[str, int], Run] = {}
        for chunk in _chunks(distinct, self._chunk):
            rows = self._execute(
                f"SELECT {_RUN_COLUMNS}, point_hash FROM runs WHERE model_version_id = ? AND point_hash IN "
                f"({_marks(len(chunk))})",
                (mv, *(bytes.fromhex(h) for h in chunk)),
            )
            current: dict[tuple[bytes, int], tuple[Any, ...]] = {}
            for row in rows:
                key = (row[15], row[3])
                if key not in current or current[key][4] < row[4]:
                    current[key] = row
            kept = list(current.values())
            for row, run in zip(kept, self._runs(kept, self._read_predictions([row[0] for row in kept])), strict=True):
                out[(row[15].hex(), row[3])] = run
        return out

    def current_keys(self, model_version_id: str, point_hashes: Sequence[str]) -> dict[tuple[str, int], CurrentKey]:
        """Q1, keys only: the current run's id, attempt, and status at each stored key of these points.

        What the runner's ``resolve`` and ``price`` need (C46, C47), without points, model predictions, or other
        columns, so it is several times faster than ``current_runs`` (record 0072, review round 1).

        Parameters
        ----------
        model_version_id
            The model version.
        point_hashes
            The design's point hashes (repeats are read once).

        Returns
        -------
        dict
            ``(point hash, replicate)`` to its current run's ``CurrentKey``, for the keys with a stored run.
        """
        mv = _blob(model_version_id, "model version")
        distinct = list(dict.fromkeys(point_hashes))
        out: dict[tuple[str, int], CurrentKey] = {}
        attempts: dict[tuple[bytes, int], int] = {}
        for chunk in _chunks(distinct, self._chunk):
            rows = self._execute(
                "SELECT point_hash, replicate, attempt, run_id, status FROM runs WHERE model_version_id = ? AND "
                f"point_hash IN ({_marks(len(chunk))})",
                (mv, *(bytes.fromhex(h) for h in chunk)),
            )
            for ph, replicate, attempt, raw, status in rows:
                if attempts.get((ph, replicate), -1) < attempt:
                    attempts[(ph, replicate)] = attempt
                    out[(ph.hex(), replicate)] = CurrentKey(raw.hex(), attempt, _STATUS[status])
        return out

    def _read_predictions(self, raws: Sequence[bytes]) -> dict[bytes, list[tuple[str, Any, Any]]]:
        out: dict[bytes, list[tuple[str, Any, Any]]] = {}
        for chunk in _chunks(raws, self._chunk):
            for raw, name, value, reason in self._execute(
                f"SELECT run_id, name, value, reason FROM predictions WHERE run_id IN ({_marks(len(chunk))})", chunk
            ):
                out.setdefault(raw, []).append((name, value, reason))
        return out

    def _runs(
        self, rows: Sequence[Sequence[Any]], predictions: Mapping[bytes, list[tuple[str, Any, Any]]]
    ) -> list[Run]:
        """Build stored runs from ``runs`` rows and their model predictions, in their spec's order.

        W4 checked each run as ``Run`` does, and no row changes (I1), so a stored run is built without checking it
        again: Q1 builds one per design point (record 0072). Points are parsed one chunk at a time.
        """
        points = json.loads("[" + ",".join(row[2] for row in rows) + "]")
        out = []
        for row, point in zip(rows, points, strict=True):
            read = predictions.get(row[0], [])
            if read:  # the table returns them by name: put them in the spec's order (I6)
                by_name = {item[0]: item for item in read}
                read = [by_name[name] for name in self._predictions_of(row[1]) if name in by_name]
            run = object.__new__(Run)
            vars(run).update(
                run_id=row[0].hex(),
                model_version_id=row[1].hex(),
                point=tuple(point),
                replicate=row[3],
                attempt=row[4],
                status=_STATUS[row[5]],
                kind=None if row[6] is None else _KIND[row[6]],
                reason=row[7],
                stderr_tail=row[8],
                exit_code=row[9],
                predictions=MappingProxyType({name: value for name, value, _ in read}),
                missing=MappingProxyType({name: reason for name, _, reason in read if reason is not None}),
                time_s=row[10],
                batch_call_id=_hex(row[11]),
                host=row[12],
                program=row[13],
                approval_id=row[14].hex(),
            )
            out.append(run)
        return out

    def run_times(self, model_version_id: str) -> tuple[int, float | None]:
        """Q2: the number of stored runs of this model version, any status, and their mean time; None with none.

        The price's "about 1 h 52 min (from 41 stored runs)" (P3, U2), from the ``(model_version_id, time_s)`` index.
        """
        ((n, mean),) = self._execute(
            "SELECT COUNT(*), AVG(time_s) FROM runs WHERE model_version_id = ?",
            (_blob(model_version_id, "model version"),),
        )
        return int(n), (None if n == 0 else float(mean))

    def get_run(self, run_id: str) -> Run:
        """Q9: a run, by its id, with its model predictions.

        Raises
        ------
        NotFound
            For an unknown id.
        """
        raw = _blob(run_id, "run")
        rows = self._execute(f"SELECT {_RUN_COLUMNS} FROM runs WHERE run_id = ?", (raw,))
        if not rows:
            raise NotFound(f"no run {run_id}")
        return self._runs(rows, self._read_predictions([raw]))[0]

    def runs_at(self, result_id: str, point_hash: str) -> tuple[Run, ...]:
        """Q9: a diagnostic result's runs at a point, one per replicate, in replicate order (0020).

        Raises
        ------
        NotFound
            For an unknown result.
        """
        rid = self._require_result(result_id)
        rows = self._execute(
            f"SELECT DISTINCT {', '.join('r.' + c for c in _RUN_COLUMNS.split(', '))} FROM result_runs AS u "
            "JOIN runs AS r ON r.run_id = u.run_id WHERE u.result_id = ? AND r.point_hash = ? ORDER BY r.replicate",
            (rid, _blob(point_hash, "point")),
        )
        return tuple(self._runs(rows, self._read_predictions([row[0] for row in rows])))

    def batch_call(self, batch_call_id: str) -> BatchCall:
        """Q9: a batch call, by its id (its directory is ``layout.run_dir(batch_call_id)``; 0025).

        Raises
        ------
        NotFound
            For an unknown id.
        """
        raw = _blob(batch_call_id, "batch call")
        rows = self._execute("SELECT size, time_s FROM batch_calls WHERE batch_call_id = ?", (raw,))
        if not rows:
            raise NotFound(f"no batch call {batch_call_id}")
        return BatchCall(raw.hex(), rows[0][0], rows[0][1])

    # -- Q7, Q15: runs as columns ------------------------------------------------------------------------------

    def _names(self, mvs: Iterable[bytes]) -> list[str]:
        names: dict[str, None] = {}
        for mv in mvs:
            names.update(dict.fromkeys(self._predictions_of(mv)))
        return list(names)

    def result_runs(self, result_id: str) -> RunColumns:
        """Q7: each design row's run, in design order, with its point, model predictions, and stderr tail (0061).

        For export (E2) and ``failed_runs`` (U3); read in chunks of ``chunk_rows`` rows.

        Raises
        ------
        NotFound
            For an unknown result.
        """
        rid = self._require_result(result_id)
        (mv,) = self._execute("SELECT model_version_id FROM results WHERE result_id = ?", (rid,))[0]
        columns = _Columns(self._predictions_of(mv), points=True, tails=True)
        start = 0
        select = ", ".join("r." + c for c in _RUN_COLUMNS.split(", "))
        while True:
            rows = self._execute(
                f"SELECT {select} FROM result_runs AS u JOIN runs AS r ON r.run_id = u.run_id WHERE u.result_id = ? "
                f'AND u."row" >= ? AND u."row" < ? ORDER BY u."row"',
                (rid, start, start + self._chunk),
            )
            columns.add(rows, self._read_predictions(list(dict.fromkeys(row[0] for row in rows))))
            if len(rows) < self._chunk:
                break
            start += self._chunk
        return columns.build()

    def runs_by_id(self, run_ids: np.ndarray | Sequence[str], *, points: bool = False) -> RunColumns:
        """Q15: these runs, in the order given, a repeated id repeated (rows share runs; C56, 0056).

        Parameters
        ----------
        run_ids
            Ids in any form ``ema.types.id_array`` reads.
        points
            Also read each run's point (a replay, 0062).

        Returns
        -------
        RunColumns
            One row per id given, with its model predictions; stderr tails left empty (0061).

        Raises
        ------
        NotFound
            For an id with no stored run, counting them.
        """
        given = run_ids if isinstance(run_ids, np.ndarray) and run_ids.dtype == ID_DTYPE else id_array(run_ids)
        unique, inverse = np.unique(given, return_inverse=True)
        raws = [bytes(u) for u in unique.tolist()] if len(unique) else []
        found: dict[bytes, tuple[Any, ...]] = {}
        for chunk in _chunks(raws, self._chunk):
            for row in self._execute(f"SELECT {_RUN_COLUMNS} FROM runs WHERE run_id IN ({_marks(len(chunk))})", chunk):
                found[row[0]] = row
        if len(found) != len(raws):
            absent = next(r for r in raws if r not in found)
            raise NotFound(f"{len(raws) - len(found)} of {len(raws)} runs are not stored, such as run {absent.hex()}")
        rows = [found[r] for r in raws]
        columns = _Columns(self._names(dict.fromkeys(row[1] for row in rows)), points=points, tails=False)
        columns.add(rows, self._read_predictions(raws))
        return columns.build(order=inverse.reshape(-1))

    # -- W5, W6, Q5, Q6, Q8, Q10: diagnostic results ------------------------------------------------------------

    def _has_result(self, result_id: str) -> bool:
        return bool(
            self._execute("SELECT 1 FROM results WHERE result_id = ?", (_blob(result_id, "diagnostic result"),))
        )

    def _require_result(self, result_id: str) -> bytes:
        rid = _blob(result_id, "diagnostic result")
        if not self._execute("SELECT 1 FROM results WHERE result_id = ?", (rid,)):
            raise NotFound(f"no diagnostic result {result_id}")
        return rid

    def record_result(self, result: DiagnosticResult) -> DiagnosticResult:
        """W5: store a diagnostic result, its provenance, its runs, and a point run's record, in one transaction.

        The result carries what W5 writes (record 0072): its provenance (``Provenance.column()``, the request, the
        design's identity, and its approval, §5.9), its run ids (one ``result_runs`` row per design row, §5.10),
        and a point run's measured-noisy record (§5.11), whose ``made_at`` W5 sets.

        Checked first: the result id is its reuse key's hash (§3.4, C50); its directory is in place (§6); every run
        exists and is of its model version; its approval said yes to a diagnostic evaluation of its model version,
        and its new runs are exactly the runs made under that approval (I12); its measured-noisy record has no
        ``made_at``.

        Returns
        -------
        DiagnosticResult
            The stored result: on a result id already stored (two identical requests at once), the stored one,
            with nothing written (I7, 0056).

        Raises
        ------
        ValueError
            When a check fails; nothing is written.
        NotFound
            For a run that isn't stored.
        """
        p = result.provenance
        versions = {"ema": p.ema, "numpy": p.numpy, "scipy": p.scipy, "matplotlib": p.matplotlib}
        if result.result_id != sha256_hex(reuse_key(p.model_version_id, p.request, p.run_ids, versions)):
            raise ValueError(f"result {result.result_id}: its id is not its reuse key's hash (§3.4)")
        noisy = result.measured_noisy
        self._check_noisy(result)
        rid = bytes.fromhex(result.result_id)
        now = _now()
        with self._write() as c:
            if c.execute("SELECT 1 FROM results WHERE result_id = ?", (rid,)).fetchone():
                c.execute("ROLLBACK")
                return self.get_result(result.result_id)
            if not os.path.isdir(self.layout.result_dir(result.result_id)):
                raise ValueError(f"result {result.result_id}: its directory is not in place (§6)")
            self._check_result_runs(c, result)
            c.execute(
                "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rid,
                    bytes.fromhex(result.model_version_id),
                    result.diagnostic,
                    result.prediction,
                    canonical_json(p.request.canonical()),
                    canonical_json(p.design.canonical()),
                    None if p.approval_id is None else bytes.fromhex(p.approval_id),
                    result.column(),
                    p.column(),
                    now,
                ),
            )
            c.executemany(
                "INSERT INTO result_runs VALUES (?, ?, ?)", ((rid, row, raw) for row, raw in self._result_rows(result))
            )
            if noisy is not None:
                c.execute(
                    "INSERT INTO measured_noisy VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        rid,
                        bytes.fromhex(noisy.model_version_id),
                        noisy.prediction,
                        canonical_json(list(noisy.point)),
                        noisy.runs,
                        noisy.std,
                        now,
                    ),
                )
        return result

    def _check_noisy(self, result: DiagnosticResult) -> None:
        """I10: a measured-noisy record comes only with a point run's result, as its own, with no ``made_at`` yet."""
        noisy = result.measured_noisy
        if noisy is None:
            return
        if noisy.made_at is not None:
            raise ValueError("a result's own measured-noisy record has no made_at: W5 sets it (record 0072)")
        if result.diagnostic != POINT_RUN:
            raise ValueError(f"only a point run's result has a measured-noisy record, not {result.diagnostic}'s (I10)")
        if (noisy.result_id, noisy.model_version_id, noisy.prediction) != (
            result.result_id,
            result.model_version_id,
            result.prediction,
        ):
            raise ValueError("a measured-noisy record is its own result's: its id, model version, and prediction (I10)")

    def _result_rows(self, result: DiagnosticResult) -> Iterator[tuple[int, bytes]]:
        """One ``result_runs`` row per design row: its number and its run's id (§5.10)."""
        raw = result.provenance.run_ids.tobytes()
        for row in range(len(raw) // 32):
            yield row, raw[32 * row : 32 * row + 32]

    def _check_result_runs(self, c: sqlite3.Connection, result: DiagnosticResult) -> None:
        """W5's preconditions on runs and approval: every run exists, of the model version; its approval; I12."""
        p = result.provenance
        mv = bytes.fromhex(result.model_version_id)
        own = None if p.approval_id is None else bytes.fromhex(p.approval_id)
        priced = None
        if own is not None:
            row = c.execute(
                "SELECT model_version_id, asked_for, answer, request, new FROM approvals WHERE approval_id = ?", (own,)
            ).fetchone()
            if row is None or row[0] != mv or row[1] != "diagnostic_evaluation" or not row[2]:
                raise ValueError(
                    f"result {result.result_id}: its approval said yes to no evaluation of its model version"
                )
            self._check_approval_request(result, row[3])
            self._check_approval_unused(c, result, own)
            priced = row[4]
        raws = [bytes(u) for u in np.unique(p.run_ids).tolist()]
        found = new = 0
        for chunk in _chunks(raws, self._chunk):
            for run_mv, run_approval in c.execute(
                f"SELECT model_version_id, approval_id FROM runs WHERE run_id IN ({_marks(len(chunk))})", chunk
            ).fetchall():
                found += 1
                if run_mv != mv:
                    raise ValueError(f"result {result.result_id}: a run of another model version")
                new += run_approval == own
        if found != len(raws):
            raise NotFound(f"result {result.result_id}: {len(raws) - found} of its {len(raws)} runs are not stored")
        self._check_new_runs(c, result, own, priced, new)

    def _check_approval_request(self, result: DiagnosticResult, request: str) -> None:
        """Check that the approval was asked for this result's request: it is used by the evaluation that asked (§5.4)."""
        if request != canonical_json(result.provenance.request.canonical()):
            raise ValueError(f"result {result.result_id}: its approval was asked for another request (§5.4)")

    def _check_approval_unused(self, c: sqlite3.Connection, result: DiagnosticResult, own: bytes) -> None:
        """Check that no other stored result cites the approval: an approval is used once (§5.4)."""
        if c.execute("SELECT 1 FROM results WHERE approval_id = ? LIMIT 1", (own,)).fetchone():
            raise ValueError(f"result {result.result_id}: its approval is another result's (an approval is used once)")

    def _check_new_runs(
        self, c: sqlite3.Connection, result: DiagnosticResult, own: bytes | None, priced: int | None, new: int
    ) -> None:
        """I12 (E6): the result's new runs (its runs made under its approval) are exactly the approval's runs.

        ``new`` counts the result's distinct runs whose approval is its own; ``priced`` is its approval's ``new``
        (None without one). Every run the approval priced was made and is the result's: an evaluation interrupted
        before all were made stores no result (C49), and its rerun's counts and approval are the rerun's (0054).
        """
        if new != result.counts.new:
            raise ValueError(
                f"result {result.result_id}: {result.counts.new} new runs counted, but {new} made under its approval (I12)"
            )
        if own is None or priced is None:
            return
        (made,) = c.execute(
            "SELECT COUNT(*) FROM approval_points AS a JOIN runs AS r ON r.model_version_id = ? "
            "AND r.point_hash = a.point_hash AND r.replicate = a.replicate AND r.approval_id = a.approval_id "
            "WHERE a.approval_id = ?",
            (bytes.fromhex(result.model_version_id), own),
        ).fetchone()
        if not new == made == priced:
            raise ValueError(
                f"result {result.result_id}: its approval priced {priced} new runs and {made} were made, but the "
                f"result has {new} of them (I12, C49)"
            )

    def find_result(self, reuse_key_hash: str) -> DiagnosticResult | None:
        """Q5: the diagnostic result stored for this reuse key (its hash, the result id), if any (C50, 0054)."""
        return self.get_result(reuse_key_hash) if self._has_result(reuse_key_hash) else None

    def get_result(self, result_id: str) -> DiagnosticResult:
        """Q6: a diagnostic result with its full provenance, the run ids in design order included (§5.9).

        Its own measured-noisy record has ``made_at`` None, as the diagnostic made it; the table's ``made_at`` is
        Q10's (record 0072).

        Raises
        ------
        NotFound
            For an unknown result.
        """
        rid = _blob(result_id, "diagnostic result")
        rows = self._execute(
            "SELECT model_version_id, diagnostic, prediction, request, design, approval_id, result, provenance "
            "FROM results WHERE result_id = ?",
            (rid,),
        )
        if not rows:
            raise NotFound(f"no diagnostic result {result_id}")
        mv, diagnostic, prediction, request, design, approval, column, provenance = rows[0]
        parts: list[bytes] = []
        start = 0
        while True:
            chunk = self._execute(
                'SELECT run_id FROM result_runs WHERE result_id = ? AND "row" >= ? AND "row" < ? ORDER BY "row"',
                (rid, start, start + self._chunk),
            )
            parts.extend(r[0] for r in chunk)
            if len(chunk) < self._chunk:
                break
            start += self._chunk
        run_ids = np.frombuffer(b"".join(parts), dtype=ID_DTYPE).copy()
        noisy = self._noisy(
            self._execute(f"SELECT {_NOISY_COLUMNS} FROM measured_noisy WHERE result_id = ?", (rid,)), made_at=False
        )
        return DiagnosticResult.from_columns(
            result_id=rid.hex(),
            model_version_id=mv.hex(),
            diagnostic=diagnostic,
            prediction=prediction,
            result=column,
            measured_noisy=noisy[0] if noisy else None,
            provenance=Provenance.from_columns(
                provenance,
                model_version_id=mv.hex(),
                request=request,
                design=design,
                approval_id=_hex(approval),
                run_ids=run_ids,
            ),
        )

    @staticmethod
    def _noisy(rows: Sequence[Sequence[Any]], *, made_at: bool = True) -> tuple[MeasuredNoisy, ...]:
        return tuple(
            MeasuredNoisy(
                rid.hex(),
                mv.hex(),
                prediction,
                tuple(json.loads(point)),
                runs,
                std,
                parse_timestamp(at) if made_at else None,
            )
            for rid, mv, prediction, point, runs, std, at in rows
        )

    def measured_noisy(self, model_version_id: str, prediction: str) -> tuple[MeasuredNoisy, ...]:
        """Q10: the point runs that measured this model version noisy in this model prediction, newest first (PT4).

        Each with its ``made_at``; a later result copies the records it reads into its provenance (I10, C52).
        """
        return self._noisy(
            self._execute(
                f"SELECT {_NOISY_COLUMNS} FROM measured_noisy WHERE model_version_id = ? AND prediction = ? "
                "ORDER BY made_at DESC, rowid DESC",
                (_blob(model_version_id, "model version"), prediction),
            )
        )

    def list_results(
        self,
        name: str | None = None,
        model_version_id: str | None = None,
        diagnostic: str | None = None,
        prediction: str | None = None,
    ) -> tuple[ResultSummary, ...]:
        """Q8: the diagnostic results, by model name, model version, diagnostic, or model prediction, newest first.

        Each as its summary (``ResultSummary``): its shortest unique id prefix (Q11), its model version's label, its
        counts, and when it was stored.
        """
        where, params = [], []
        for column, value in (
            ("v.name", name),
            ("r.model_version_id", None if model_version_id is None else _blob(model_version_id, "model version")),
            ("r.diagnostic", diagnostic),
            ("r.prediction", prediction),
        ):
            if value is not None:
                where.append(f"{column} = ?")
                params.append(value)
        rows = self._execute(
            "SELECT r.result_id, r.model_version_id, v.name, r.diagnostic, r.prediction, r.result, r.made_at "
            "FROM results AS r JOIN model_versions AS v ON v.model_version_id = r.model_version_id "
            + (f"WHERE {' AND '.join(where)} " if where else "")
            + "ORDER BY r.made_at DESC, r.rowid DESC",
            params,
        )
        shortest = _shortest_prefixes(
            [r[0].hex() for r in self._execute("SELECT result_id FROM results ORDER BY result_id")]
        )
        out = []
        for rid, mv, model, diag, pred, column, at in rows:
            c = json.loads(column)["counts"]
            counts = Counts(**{**c, "failed": {FailureKind(k): v for k, v in c["failed"].items()}})
            listed = cast(DiagnosticResult, _Listed(rid.hex(), diag, pred, counts))
            label = model_version_label(model, mv.hex())
            out.append(
                ResultSummary.make(
                    listed, short_id=shortest[rid.hex()], model_version=label, made_at=parse_timestamp(at)
                )
            )
        return tuple(out)

    def delete_result(self, result_id: str) -> None:
        """W6: delete a diagnostic result's measured-noisy, ``result_runs``, and ``results`` rows, then its directory.

        Runs and approvals are kept, so the result replays from its provenance (C51, U8). Tests only: no public
        name in v2.0 (0056).

        Raises
        ------
        NotFound
            For an unknown result.
        """
        with self._write() as c:
            rid = self._require_result(result_id)
            for table in ("measured_noisy", "result_runs", "results"):
                c.execute(f"DELETE FROM {table} WHERE result_id = ?", (rid,))
        directory = self.layout.result_dir(rid.hex())
        if os.path.isdir(directory):
            shutil.rmtree(directory)

    # -- Q11: ids ------------------------------------------------------------------------------------------------

    def resolve(self, kind: str, prefix: str) -> str:
        """Q11: the id of this kind that a prefix of at least 4 hex digits names (§3.4, Shown).

        Parameters
        ----------
        kind
            "model_version", "approval", "run", "batch_call", or "result".
        prefix
            4 to 64 hex digits, in either case.

        Raises
        ------
        RequestError
            For a prefix that isn't 4 to 64 hex digits.
        NotFound
            When it names none.
        AmbiguousId
            When it names several, listing them (their shortest unique prefixes, up to 10).
        """
        table, column, word = self._kind(kind)
        text = prefix.strip().lower() if isinstance(prefix, str) else ""
        if not 4 <= len(text) <= 64 or any(ch not in "0123456789abcdef" for ch in text):
            raise RequestError(f"{prefix!r} is not a {word} id: give 4 to 64 hex digits")
        lo, hi = bytes.fromhex(text.ljust(64, "0")), bytes.fromhex(text.ljust(64, "f"))
        rows = self._execute(
            f"SELECT {column} FROM {table} WHERE {column} BETWEEN ? AND ? ORDER BY {column} LIMIT 11", (lo, hi)
        )
        if not rows:
            raise NotFound(f"no {word} {text}")
        if len(rows) == 1:
            return str(rows[0][0].hex())
        shown = ", ".join(self.short(kind, r[0].hex()) for r in rows[:10])
        more = ", and more" if len(rows) > 10 else ""
        raise AmbiguousId(f"{text} names several {word}s: {shown}{more}")

    def short(self, kind: str, id: str) -> str:
        """Q11: an id's shortest prefix, of at least 4 hex digits, unique among ids of its kind (as git shows commits).

        Raises
        ------
        NotFound
            For an id of this kind that isn't stored.
        """
        table, column, word = self._kind(kind)
        raw = _blob(id, word)
        id = raw.hex()
        if not self._execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (raw,)):
            raise NotFound(f"no {word} {id}")
        neighbors = self._execute(
            f"SELECT {column} FROM {table} WHERE {column} < ? ORDER BY {column} DESC LIMIT 1", (raw,)
        ) + self._execute(f"SELECT {column} FROM {table} WHERE {column} > ? ORDER BY {column} LIMIT 1", (raw,))
        common = max((len(os.path.commonprefix([id, n[0].hex()])) for n in neighbors), default=0)
        return id[: max(4, common + 1)]

    @staticmethod
    def _kind(kind: str) -> tuple[str, str, str]:
        if kind not in ID_KINDS:
            raise ValueError(f"no id kind {kind!r}: one of {', '.join(ID_KINDS)}")
        return ID_KINDS[kind]


_NOISY_COLUMNS = "result_id, model_version_id, prediction, point, runs, std, made_at"


def _shortest_prefixes(ordered: Sequence[str]) -> dict[str, str]:
    """Each sorted id's shortest unique prefix, of at least 4 hex digits (Q11), from its neighbors."""
    out = {}
    for i, hex_id in enumerate(ordered):
        common = 0
        for j in (i - 1, i + 1):
            if 0 <= j < len(ordered):
                common = max(common, len(os.path.commonprefix([hex_id, ordered[j]])))
        out[hex_id] = hex_id[: max(4, common + 1)]
    return out
