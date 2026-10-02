-- The store's schema, version 1 (data_model.md §5; §11). Every table is append-only (§3.3): no row is updated, and
-- only delete_result (W6) deletes, a diagnostic result's own rows. Ids and hashes are 32-byte BLOBs (§3.2); a
-- timestamp is ISO 8601 text in UTC, to the millisecond; a JSON column is canonical strict JSON (§3.4) and is never
-- in a WHERE clause. A model prediction's value has no declared type, so SQLite keeps it a double, -0.0 included: a
-- REAL column stores an integral double as an integer and reads -0.0 back as 0.0 (record 0072).

CREATE TABLE model_versions (
    model_version_id BLOB PRIMARY KEY CHECK (length(model_version_id) = 32),
    name TEXT NOT NULL,
    spec TEXT NOT NULL,
    files TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX model_versions_name ON model_versions (name);

CREATE TABLE loadings (
    loading INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    model_version_id BLOB NOT NULL REFERENCES model_versions,
    spec_path TEXT NOT NULL,
    keep TEXT NOT NULL CHECK (keep IN ('all', 'incomplete', 'none')),
    batch_size INTEGER CHECK (batch_size IS NULL OR batch_size >= 1),
    timeout_s REAL NOT NULL CHECK (timeout_s > 0),
    loaded_at TEXT NOT NULL
);
CREATE INDEX loadings_name ON loadings (name, loading);

CREATE TABLE confirmations (
    confirmation INTEGER PRIMARY KEY,
    spec_path TEXT NOT NULL,
    spec_sha256 BLOB NOT NULL CHECK (length(spec_sha256) = 32),
    question TEXT NOT NULL,
    answer INTEGER NOT NULL CHECK (answer IN (0, 1)),
    asked_at TEXT NOT NULL
);

CREATE TABLE approvals (
    approval_id BLOB PRIMARY KEY CHECK (length(approval_id) = 32),
    model_version_id BLOB NOT NULL REFERENCES model_versions,
    asked_for TEXT NOT NULL CHECK (asked_for IN ('diagnostic_evaluation', 'test_run')),
    request TEXT NOT NULL,
    design TEXT,
    new INTEGER NOT NULL CHECK (new >= 1),
    reused INTEGER NOT NULL CHECK (reused >= 0),
    reused_failed INTEGER NOT NULL CHECK (reused_failed >= 0 AND reused_failed <= reused),
    time_s REAL CHECK (time_s IS NULL OR time_s >= 0),
    question TEXT NOT NULL,
    answer INTEGER NOT NULL CHECK (answer IN (0, 1)),
    asked_at TEXT NOT NULL,
    CHECK ((asked_for = 'test_run') = (design IS NULL))
);
CREATE INDEX approvals_answer ON approvals (model_version_id, answer);

CREATE TABLE approval_points (
    approval_id BLOB NOT NULL REFERENCES approvals,
    point_hash BLOB NOT NULL CHECK (length(point_hash) = 32),
    replicate INTEGER NOT NULL CHECK (replicate >= 0),
    PRIMARY KEY (approval_id, point_hash, replicate)
) WITHOUT ROWID;

CREATE TABLE batch_calls (
    batch_call_id BLOB PRIMARY KEY CHECK (length(batch_call_id) = 32),
    size INTEGER NOT NULL CHECK (size >= 1),
    time_s REAL NOT NULL CHECK (time_s >= 0)
);

CREATE TABLE runs (
    run_id BLOB PRIMARY KEY CHECK (length(run_id) = 32),
    model_version_id BLOB NOT NULL REFERENCES model_versions,
    point_hash BLOB NOT NULL CHECK (length(point_hash) = 32),
    replicate INTEGER NOT NULL CHECK (replicate >= 0),
    attempt INTEGER NOT NULL CHECK (attempt >= 0),
    point TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'failed')),
    kind TEXT CHECK (kind IN ('error', 'timeout', 'unread')),
    reason TEXT,
    stderr_tail TEXT,
    exit_code INTEGER,
    time_s REAL NOT NULL CHECK (time_s >= 0),
    batch_call_id BLOB REFERENCES batch_calls,
    host TEXT NOT NULL,
    program TEXT NOT NULL,
    approval_id BLOB NOT NULL REFERENCES approvals,
    UNIQUE (model_version_id, point_hash, replicate, attempt),
    CHECK ((status = 'ok') = (kind IS NULL) AND (status = 'ok') = (reason IS NULL))
);
CREATE INDEX runs_time ON runs (model_version_id, time_s);

CREATE TABLE predictions (
    run_id BLOB NOT NULL REFERENCES runs,
    name TEXT NOT NULL,
    value CHECK (typeof(value) IN ('real', 'null')),
    reason TEXT,
    PRIMARY KEY (run_id, name),
    CHECK ((value IS NULL) <> (reason IS NULL))
) WITHOUT ROWID;

CREATE TABLE results (
    result_id BLOB PRIMARY KEY CHECK (length(result_id) = 32),
    model_version_id BLOB NOT NULL REFERENCES model_versions,
    diagnostic TEXT NOT NULL,
    prediction TEXT NOT NULL,
    request TEXT NOT NULL,
    design TEXT NOT NULL,
    approval_id BLOB REFERENCES approvals,
    result TEXT NOT NULL,
    provenance TEXT NOT NULL,
    made_at TEXT NOT NULL
);
CREATE INDEX results_made ON results (model_version_id, made_at);

CREATE TABLE result_runs (
    result_id BLOB NOT NULL REFERENCES results,
    "row" INTEGER NOT NULL CHECK ("row" >= 0),
    run_id BLOB NOT NULL REFERENCES runs,
    PRIMARY KEY (result_id, "row")
) WITHOUT ROWID;

CREATE TABLE measured_noisy (
    result_id BLOB PRIMARY KEY REFERENCES results,
    model_version_id BLOB NOT NULL REFERENCES model_versions,
    prediction TEXT NOT NULL,
    point TEXT NOT NULL,
    runs INTEGER NOT NULL CHECK (runs >= 0),
    std REAL CHECK (std IS NULL OR std >= 0),
    made_at TEXT NOT NULL
);
CREATE INDEX measured_noisy_read ON measured_noisy (model_version_id, prediction, made_at);
