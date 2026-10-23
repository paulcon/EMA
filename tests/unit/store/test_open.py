"""Opening a workspace's store: its layout, connection settings, schema version, migrations, and the run lock
(data_model.md §1, §10, §11; architecture.md §5)."""

import os
import sqlite3
import threading

import pytest

from ema.store import BUSY_TIMEOUT_S, Layout, Store, migrations
from ema.types.errors import NotFound, WorkspaceBusy, WorkspaceVersion
from ema.types.identity import point_hash
from tests.support import store as world


def test_the_layout_names_every_path(tmp_path):
    layout = Layout.of(tmp_path / "ws")
    root = str(tmp_path / "ws")
    assert layout.root == root
    assert (layout.db, layout.lock) == (f"{root}/ema.db", f"{root}/run.lock")
    assert (layout.runs, layout.files, layout.results) == (f"{root}/runs", f"{root}/files", f"{root}/results")
    assert layout.run_dir("ab" * 32) == f"{root}/runs/{'ab' * 32}"
    assert layout.result_dir("cd" * 32) == f"{root}/results/{'cd' * 32}"


def test_a_relative_path_is_made_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Layout.of("ws").root == os.path.join(str(tmp_path), "ws")


def test_open_creates_the_workspace_and_its_directories(tmp_path):
    with Store.open(str(tmp_path / "ws")) as store:
        for path in (store.layout.runs, store.layout.files, store.layout.results):
            assert os.path.isdir(path)
        assert os.path.isfile(store.layout.db)
    conn = sqlite3.connect(tmp_path / "ws" / "ema.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == migrations.SCHEMA_VERSION == 1
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")}
    assert tables == {
        "model_versions", "loadings", "confirmations", "approvals", "approval_points", "runs", "batch_calls",
        "predictions", "results", "result_runs", "measured_noisy",
    }  # fmt: skip


def test_open_without_create_refuses_a_missing_workspace(tmp_path):
    with pytest.raises(NotFound, match="no workspace"):
        Store.open(str(tmp_path / "nothing"), create=False)
    assert not (tmp_path / "nothing").exists()


def test_open_again_keeps_what_is_stored(tmp_path):
    with Store.open(str(tmp_path)) as store:
        mv = world.load(store)
    with Store.open(str(tmp_path), create=False) as store:
        assert store.model_version(mv).name == "toy"


def test_the_connection_settings(tmp_path):
    """§10: foreign keys on, rollback journal, synchronous FULL, a busy timeout of 60 s."""
    assert BUSY_TIMEOUT_S == 60.0
    with Store.open(str(tmp_path)) as store:
        conn = store._conn
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2


def test_a_store_stays_on_its_thread(tmp_path):
    """§10: one Store per thread, as a SQLite connection stays on its thread."""
    errors = []
    with Store.open(str(tmp_path)) as store:

        def read():
            try:
                store.run_times("ab" * 32)
            except sqlite3.ProgrammingError as e:
                errors.append(e)

        thread = threading.Thread(target=read)
        thread.start()
        thread.join()
    assert errors


def test_a_newer_workspace_is_refused_naming_both_versions(tmp_path):
    Store.open(str(tmp_path)).close()
    conn = sqlite3.connect(tmp_path / "ema.db")
    conn.execute("PRAGMA user_version = 7")
    conn.close()
    with pytest.raises(WorkspaceVersion, match=r"schema version 7, newer than this EMA's 1"):
        Store.open(str(tmp_path))


def test_a_database_that_is_not_emas_is_refused(tmp_path):
    os.makedirs(tmp_path / "ws")
    conn = sqlite3.connect(tmp_path / "ws" / "ema.db")
    conn.execute("CREATE TABLE other (x)")
    conn.close()
    with pytest.raises(WorkspaceVersion, match="not an EMA workspace"):
        Store.open(str(tmp_path / "ws"))


def _connect(path):
    return sqlite3.connect(path, isolation_level=None, check_same_thread=False)


def test_an_older_schema_is_copied_then_migrated(tmp_path):
    """§11: copied to ema.db.v<N> first, then migrated N → N + 1 in one transaction."""
    Store.open(str(tmp_path)).close()
    db = str(tmp_path / "ema.db")

    def add_column(conn):
        conn.execute("ALTER TABLE confirmations ADD COLUMN note TEXT")

    conn = _connect(db)
    assert migrations.prepare(conn, db, latest=2, migrations={1: add_column}) == 1
    assert migrations.user_version(conn) == 2
    assert "note" in {r[1] for r in conn.execute("PRAGMA table_info(confirmations)")}
    copy = _connect(f"{db}.v1")
    assert migrations.user_version(copy) == 1
    assert "note" not in {r[1] for r in copy.execute("PRAGMA table_info(confirmations)")}
    assert migrations.prepare(conn, db, latest=2, migrations={1: add_column}) == 2  # already done: nothing


def test_a_failed_migration_leaves_the_version(tmp_path):
    Store.open(str(tmp_path)).close()
    db = str(tmp_path / "ema.db")

    def broken(conn):
        conn.execute("ALTER TABLE confirmations ADD COLUMN note TEXT")
        raise RuntimeError("half done")

    conn = _connect(db)
    with pytest.raises(RuntimeError):
        migrations.prepare(conn, db, latest=2, migrations={1: broken})
    assert migrations.user_version(conn) == 1
    assert "note" not in {r[1] for r in conn.execute("PRAGMA table_info(confirmations)")}


def test_an_older_schema_with_no_migration_is_refused(tmp_path):
    Store.open(str(tmp_path)).close()
    db = str(tmp_path / "ema.db")
    with pytest.raises(WorkspaceVersion, match="can't migrate"):
        migrations.prepare(_connect(db), db, latest=3, migrations={1: lambda c: None})


def test_the_schema_is_package_data():
    statements = migrations.schema_statements()
    assert len(statements) == 17  # 11 tables, 6 indexes
    assert all(s.startswith("CREATE") for s in statements)


def test_the_run_lock_excludes_a_second_holder(tmp_path):
    """§10 and architecture.md §5: a second holder, in this process too, is refused naming the holder."""
    with Store.open(str(tmp_path)) as store, Store.open(str(tmp_path)) as other:
        with store.run_lock():
            with pytest.raises(WorkspaceBusy, match=rf"process {os.getpid()} on .*run\.lock"), other.run_lock():
                pass
            with pytest.raises(WorkspaceBusy), store.run_lock():
                pass
        with other.run_lock():  # released
            pass
    assert WorkspaceBusy.retryable


def test_the_run_lock_is_released_on_an_exception(tmp_path):
    with Store.open(str(tmp_path)) as store:
        with pytest.raises(KeyboardInterrupt), store.run_lock():
            raise KeyboardInterrupt
        with store.run_lock():
            pass


def test_a_long_write_lock_elsewhere_is_workspace_busy(tmp_path):
    """A write that waits past the busy timeout is refused as busy, retryable (architecture.md §5)."""

    class Impatient(Store):
        busy_timeout_s = 0.05

    with Impatient.open(str(tmp_path)) as store:
        blocker = _connect(store.layout.db)
        blocker.execute("BEGIN EXCLUSIVE")
        try:
            with pytest.raises(WorkspaceBusy, match="locked"):
                world.load(store)
        finally:
            blocker.execute("ROLLBACK")
        world.load(store)


def test_w4_waits_past_the_busy_timeout_until_it_commits(tmp_path):
    """W4 retries past the timeout: its call has finished and its runs must be stored (C49)."""

    class Impatient(Store):
        busy_timeout_s = 0.05

    with Impatient.open(str(tmp_path)) as store:
        mv = world.load(store)
        (k,) = world.keys(mv, [(1.0, 0.0, 0.5)])
        approval = world.approve(store, mv, [k])
        blocker = _connect(store.layout.db)
        blocker.execute("BEGIN EXCLUSIVE")
        timer = threading.Timer(0.3, lambda: blocker.execute("ROLLBACK"))
        timer.start()
        store.record_call([world.ok_run(k, mv, approval)])
        timer.join()
        assert store.run_times(mv)[0] == 1


def test_a_file_that_is_not_a_database_is_refused(tmp_path):
    """Review round 1, m1: a damaged or foreign ema.db is WorkspaceVersion, not sqlite3's own error."""
    (tmp_path / "ema.db").write_bytes(b"not a database at all" * 100)
    with pytest.raises(WorkspaceVersion, match="not an EMA workspace"):
        Store.open(str(tmp_path))


def test_opening_a_locked_workspace_is_workspace_busy(tmp_path):
    """Review round 1, m1: a database locked past the busy timeout while opening is WorkspaceBusy, retryable."""

    class Impatient(Store):
        busy_timeout_s = 0.05

    Store.open(str(tmp_path)).close()
    blocker = _connect(str(tmp_path / "ema.db"))
    blocker.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(WorkspaceBusy, match="locked") as error:
            Impatient.open(str(tmp_path))
        assert error.value.retryable
    finally:
        blocker.execute("ROLLBACK")
    Impatient.open(str(tmp_path)).close()


def test_w4_retries_a_busy_statement_inside_its_transaction(tmp_path):
    """Review round 1, n7: a busy statement inside W4's transaction (a spill that waits for readers) rolls it back and
    tries the whole call again."""

    class SpillsOnce(Store):
        spilled = False

        def _check_predictions(self, c, runs):
            if not self.spilled:
                self.spilled = True
                c.execute("INSERT INTO batch_calls VALUES (?, 1, 1.0)", (b"\x01" * 32,))  # written, then rolled back
                raise sqlite3.OperationalError("database is locked")
            super()._check_predictions(c, runs)

    with SpillsOnce.open(str(tmp_path)) as store:
        mv = world.load(store)
        (k,) = world.keys(mv, [(1.0, 0.0, 0.5)])
        approval = world.approve(store, mv, [k])
        store.record_call([world.ok_run(k, mv, approval)])
        assert store.spilled and store.run_times(mv)[0] == 1
        with pytest.raises(NotFound):
            store.batch_call("01" * 32)


def test_chunks_fit_sqlites_variable_limit(tmp_path):
    """Review round 1, n4: a chunk never binds more variables than the connection allows."""
    with Store.open(str(tmp_path)) as store:
        store._conn.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 17)  # W4's insert binds 16
        small = Store(store._conn, store.layout)
        assert small._chunk == 16
        mv = world.load(small)
        points = [(float(i), 0.0, 0.5) for i in range(40)]
        _, runs = world.made(small, mv, points)
        hashes = [point_hash(p) for p in points]
        assert len(small.current_runs(mv, hashes)) == len(small.current_keys(mv, hashes)) == 40
        assert len(small.runs_by_id(world.ids(runs))) == 40
