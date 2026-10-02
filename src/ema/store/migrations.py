"""The schema's version and its migrations (data_model.md §11; architecture.md §5).

The version is ``PRAGMA user_version``. A new database gets the schema (``schema.sql``) and the current version in
one transaction; an older one is copied to ``ema.db.v<N>`` and migrated one version at a time, in one
``BEGIN IMMEDIATE`` transaction that reads the version again first, so two processes can't both migrate and a
second opener never copies a half-migrated file; a newer one is refused, naming both versions.
"""

import shutil
import sqlite3
from collections.abc import Callable, Mapping
from importlib.resources import files

from ema.types.errors import WorkspaceVersion

#: The schema version this EMA writes (data_model.md §11's table).
SCHEMA_VERSION = 1

#: Each migration takes the schema from version N (the key) to N + 1, inside the caller's transaction. None yet:
#: version 1 is the first schema; from version 2 on, a stored version-1 workspace must open and migrate (§11).
MIGRATIONS: Mapping[int, Callable[[sqlite3.Connection], None]] = {}


def schema_statements() -> list[str]:
    """Return ``schema.sql``'s statements, one each, from the package's data."""
    text = files("ema.store").joinpath("schema.sql").read_text(encoding="utf-8")
    statements, pending = [], ""
    for line in text.splitlines(keepends=True):
        if not pending and line.lstrip().startswith("--"):
            continue
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending.strip())
            pending = ""
    return statements


def user_version(conn: sqlite3.Connection) -> int:
    """Return the database's schema version (0 for a new database)."""
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _newer(db: str, version: int, latest: int) -> WorkspaceVersion:
    return WorkspaceVersion(
        f"the workspace's database {db} has schema version {version}, newer than this EMA's {latest}: use a newer EMA"
    )


def prepare(
    conn: sqlite3.Connection,
    db: str,
    *,
    latest: int = SCHEMA_VERSION,
    migrations: Mapping[int, Callable[[sqlite3.Connection], None]] = MIGRATIONS,
) -> int:
    """Bring the database to schema version ``latest``: create it, migrate it, or refuse it (data_model.md §11).

    Parameters
    ----------
    conn
        A connection in autocommit mode (``isolation_level=None``), outside any transaction.
    db
        The database's path, for the copy taken before a migration (``<db>.v<N>``) and for messages.
    latest, migrations
        The version to reach and the migrations, from N to N + 1 (this module's, unless a test gives its own).

    Returns
    -------
    int
        The version the database had when opened (0 for a new one).

    Raises
    ------
    WorkspaceVersion
        For a newer schema, naming both versions; a database with tables but no version, which isn't EMA's; or an
        older version with no migration from it.
    """
    found = user_version(conn)
    if found > latest:
        raise _newer(db, found, latest)
    if found == latest:
        return found
    conn.execute("BEGIN IMMEDIATE")
    try:
        found = user_version(conn)  # again, under the write lock: another process may have done it meanwhile
        if found > latest:
            raise _newer(db, found, latest)
        if found == 0:
            if conn.execute("SELECT 1 FROM sqlite_schema LIMIT 1").fetchone():
                raise WorkspaceVersion(f"{db} is not an EMA workspace's database: it has tables but no schema version")
            for statement in schema_statements():
                conn.execute(statement)
        elif found < latest:
            missing = [n for n in range(found, latest) if n not in migrations]
            if missing:
                raise WorkspaceVersion(f"{db} has schema version {found}, and this EMA can't migrate it to {latest}")
            shutil.copyfile(db, f"{db}.v{found}")
            for n in range(found, latest):
                migrations[n](conn)
        conn.execute(f"PRAGMA user_version = {int(latest)}")
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return found
