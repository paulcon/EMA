# 0072. Step 06's provisional choices: the store

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Step 06 builds `ema.store` (`../plans/06-store.md`): `data_model.md` in full and `architecture.md` §5's
`ema.store`. The specs give the tables, the writes and reads with sketches of their signatures, the invariants,
the connection, the lock, and the migration policy; where they are silent, or name an argument list as "…", the
choices below keep P1–P7 and the specs' intent. Record 0070 (step T) fixed the types the store reads and writes,
and that it writes `Provenance.column()` and `DiagnosticResult.column()`. The coordinator ruled on one item during
the step (item 2). None of the choices changes an accepted spec's rule; the signatures are listed under "Spec
edits on acceptance".

## Decision

We will, provisionally:

**Writes (§7)**

1. **W5 is `record_result(result) -> DiagnosticResult`.** The result carries everything W5 writes: its provenance
   (the `provenance` column, the request, the design's identity, the approval), its run ids (one `result_runs` row
   per design row), and a point run's measured-noisy record (record 0070 made these fields), so §7's separate
   `provenance, run_ids, approval_id, noisy` would only repeat them. It returns the stored result: on a result id
   already stored, the stored one, with nothing written (I7, 0056).
2. **A result's own measured-noisy record has `made_at` None** (the coordinator's ruling on wave 2's review, m1).
   The diagnostic can't know the time and a result must be a function of its request and runs (P4), so inside a
   `DiagnosticResult` the record's `made_at` is always None: W5 refuses one that is set, writes the table's
   `made_at` (the result's own `made_at`, one transaction time), Q10 reads it with `made_at`, and Q6 returns the
   result's record with `made_at` None, so an evaluated result, stored and read back, is equal to itself and a
   replay compares equal.
3. **W5 checks, in its transaction, before writing:** the result id is the SHA-256 of its reuse key, recomputed from
   its provenance (C50's basis); its directory is in place (§6); every run exists (`NotFound` otherwise) and is of
   the result's model version; its approval, when it has one, said yes to a diagnostic evaluation of that model
   version; and its counted new runs are exactly the distinct runs made under that approval (I12).
4. **W3 is `record_approval(*, model_version_id, asked_for, request, design, price, question, answer, points)`**,
   `points` the new keys (`RunKey`s) priced, exactly `price.new` distinct points and replicates. It refuses no new
   runs (C50), points that aren't the price's, a repeated key, and a design given exactly when it isn't the test
   run (`ValueError`), and an unknown model version (`NotFound`). The number of approvals before it, for its id, is
   counted inside the same transaction as the insert.
5. **W4 is `record_call(runs, batch_call=None)`**, with `records.BatchCall`. A call with no batch call stores one
   run; a batch call's id is `batch_call_id` of its runs in call order, its size their number, and each run names
   it. A failed precondition (I2, I3, I4, I6) is `ValueError`, an error in EMA's code (record 0070 item 4), and
   nothing is stored. W4 doesn't look for the run's directory: writing it before W4 is the runner's part of I5.
6. **W1 refuses a relative spec path** (`ValueError`; §3.2's `path` is absolute). The model version's `spec` column
   is `versioned_json()`, so Q14's `ModelVersion.spec` has the default settings; the loading's are Q3's `Loading`.

**Reads (§8)**

7. **Q1 builds stored runs without running `Run`'s checks again**: W4 checked each run as `Run` does, and no row
   changes (I1). This halves Q1's time; a test checks that every stored run passes `Run`'s checks (rebuilt with
   `dataclasses.replace`). A chunk's points are parsed in one JSON call.
8. **Q7's and Q15's `RunColumns.values`** hold every model prediction of the runs' model versions' specs, so a batch
   whose runs all failed still has its model prediction (NaN), as `RunBatch.usable` needs; `host` and `program` are
   object arrays sharing one string per distinct value (a `U` array costs 4 bytes per character per row).
9. **Q8 returns `ResultSummary`s**, built from each `results` row and its `result` column's counts, without reading
   `result_runs`; `ResultSummary.make` is given a private object with the four fields it reads, so the summary's
   text keeps its one home. Ties in `made_at` are broken by insertion order, newest first (Q8, Q10), oldest first
   (Q12).
10. **Q9:** `get_run(run_id)` and `runs_at(result_id, point_hash)` return `Run`s; a directory is
    `Layout.run_dir(id)` (a run's or a batch call's), whose existence the caller reads from the file system
    (§5.6); and `batch_call(batch_call_id) -> BatchCall` reads Q9's batch call.
11. **Q11's kinds** are `model_version`, `approval`, `run`, `batch_call`, and `result` (`ID_KINDS`). A prefix is
    read in either case; one that isn't 4 to 64 hex digits is `RequestError`; none found, `NotFound`; several,
    `AmbiguousId`, listing up to 10 by their shortest unique prefixes. An id given to any read that isn't 64 hex
    digits is `NotFound`, since no row has it.
12. **Q12 adds `approval_points(approval_id)`**, an audit's detail and the only reader of `ApprovedPoint`, which
    §10 names.
13. **Q13's `Coverage`** is `(approval_id, model_version_id, answer, covered)`, `covered` one bool per key asked
    about, in order, and `complete` when all are.

**Storage**

14. **A model prediction's `value` column has no declared type**, with `CHECK (typeof(value) IN ('real',
    'null'))`: a `REAL` column stores an integral double as an integer and reads −0.0 back as 0.0 (measured with
    SQLite 3.53), which would break C17's "every double exact". The other `REAL` columns hold times, a standard
    deviation, and a timeout, all ≥ 0, where −0.0 reads back as 0.0. JSON columns keep −0.0 (§3.4).
15. **Checks beyond §5's,** in `schema.sql`: ids and hashes 32 bytes; `batch_size ≥ 1`; `timeout_s > 0`; times and
    `std` ≥ 0; `reused_failed ≤ reused`; an approval has a design exactly when it isn't the test run.

**Connection, lock, migrations, files**

16. **Busy:** a statement that waits past the busy timeout (60 s) raises `WorkspaceBusy` (retryable), naming the
    database; W4 retries its `BEGIN IMMEDIATE` and `COMMIT` until they succeed (architecture.md §5). `chunk_rows`
    (30,000) and `busy_timeout_s` (60) are class attributes, so a test subclass makes them small (no monkeypatching,
    0065).
17. **`Store.open(path, *, create=True)`** takes the workspace's directory; `create` makes it and `runs/`,
    `files/`, `results/`; with `create=False` and no `ema.db`, `NotFound`. A database with tables and no schema
    version is refused as not EMA's, and an older version with no migration from it, both `WorkspaceVersion`.
    `migrations.prepare(conn, db, *, latest, migrations)` takes the version and the migrations as arguments, so
    a test migrates a workspace through a migration of its own.
18. **The run lock** writes "process <pid> on <host>, since <time>" into `run.lock` while held (emptied on
    release), and `WorkspaceBusy` names it and the lock's path.
19. **The result directory's temporary directory** is `results/.<first 12 hex digits>-<random>`, on the same file
    system, so the rename is atomic; if another process renames an identical directory into place first, ours is
    discarded (S10: its report and data cards are byte-identical).

**Tests**

20. **The store contract's implementation is the `Store` class**, opened on a fresh workspace by each check; its
    broken toys are subclasses, some overriding a private check (`_check_keys`, `_check_approvals`,
    `_check_predictions`, `_check_result_runs`, `_result_rows`). There is one check per invariant I1–I12, as §9
    names them, and C46's `check_reuse`.

**Review round 1** (the independent review's findings; each fixed with a test)

21. **The result directory is safe for several processes at once** (M1). The directory in place is never deleted
    where it is: a rename that finds one there (`ENOTEMPTY`, `EEXIST`) is retried inside a `BEGIN IMMEDIATE`
    transaction, which W5 also holds while it looks for the directory. Under it, a stored row means ours is
    discarded; otherwise the one in place is renamed into a fresh `results/.<12 hex>-old-<random>/` and ours
    renamed in, and the moved copy is deleted after the commit. The temporary directory is removed in a `finally`,
    so none is left. Tested with 4 spawned processes meeting at a barrier, 12 trials (half with a leftover in
    place): the earlier code failed 6 of 48 writes there with `FileNotFoundError`.
22. **W5 enforces "an approval is used once" and I12 in full** (M2; §5.4, §5.9, I12, C49). A result's approval
    must have been asked for its request (the canonical requests equal); no other stored result may cite it; and
    its counted new runs, its distinct runs made under its approval, all of the approval's runs, and the
    approval's `new` must be one number. The last makes "every run the approval priced was made" W5's rule: an
    evaluation interrupted before then stores no result (C49), and its rerun asks, and cites, an approval of its
    own (0054). Broken toys `CountsOnly`, `AnyRequestsApproval`, and `ApprovalUsedTwice` back the new parts of
    `check_new_runs`.
23. **W5 refuses a measured-noisy record** (m2; I10) unless the result is the point run's (`diagnostic ==
    "point_run"`, `store.POINT_RUN`) and the record is its own: its result id, model version, and model
    prediction. Broken toy `NoiseFromAnyResult`.
24. **`Store.open` maps SQLite's errors** (m1): a lock held past the busy timeout while opening is
    `WorkspaceBusy`; a file that isn't a database (`sqlite3.DatabaseError`) is `WorkspaceVersion`, "not an EMA
    workspace's database", as a foreign database already was.
25. **Stored runs' model predictions are in their spec's order** (m3), as W4 was given them; the table returns
    them by name.
26. **Q1 has a key-only read, `current_keys(model_version_id, point_hashes) -> dict[(hash, replicate),
    CurrentKey]`** (m4), `records.CurrentKey(run_id, attempt, status)` a named tuple: what `resolve` and `price`
    need. Measured 0.66–0.79 s per 10⁵ stored runs against `current_runs`' 2.3–2.4 s (this Mac, 2026-10-02):
    about 7–8 s per 10⁶, inside §6's 10 s with the hashing's 1.2 s only just. `current_runs` stays, for callers
    that need whole runs.
27. **Small ones** (n1, n2, n4, n5, n7): a read given an id in upper case returns it as stored (lower case), and
    W6 finds its directory; `result_directory` refuses an id that isn't 64 lowercase hex digits (`ValueError`)
    before making anything; a chunk binds at most the connection's variable limit less one
    (`SQLITE_LIMIT_VARIABLE_NUMBER`); W1 stores the spec path resolved (`os.path.realpath`, §3.2's "resolved when
    written"); a busy statement inside W4's transaction (a spill waiting for readers) rolls it back and retries
    the whole call, as a busy `BEGIN` or `COMMIT` already was.
28. **The run lock's fork caveat is documented** (n3): a child made by a bare `fork` shares the lock's open file
    description and keeps it held; the descriptor is non-inheritable, so the runner starts model processes with
    `subprocess` or `multiprocessing`'s "spawn", never "fork".

**Review round 2** (a nit left on step 06; fixed with a test)

29. **W6 moves the result's directory aside inside its transaction**, as `_put_in_place` does under the same lock,
    and deletes the moved copy after the commit (a failed commit puts it back): a W5 of the same result that
    follows never has its new directory deleted.

## Deferrals

- **§6's timing test, pricing a 10⁶-point design against 10⁶ stored runs in under 10 s,** is step 07's: it
  prices through `resolve` and `price`. The store's part is item 26's key-only read, measured at about 7–8 s per
  10⁶ by extrapolation; full `current_runs` stays about 20–25 s per 10⁶ (2.4 s per 10⁵), and Q15 and Q7 about
  1.5 s per 10⁵. The slow tier checks the chunked reads' correctness, `current_keys` included, at 70,001 runs,
  across real chunk boundaries.
- **The version-1 workspace fixture** (`tests/fixtures/workspace_v1.sql`): §11 asks for it from version 2 on.
  The migration path is tested with a test migration from version 1 to 2.

## Spec edits on acceptance

- `data_model.md` §7: W3's, W4's, and W5's signatures as items 1, 4, and 5; W5's checks (item 3); the
  measured-noisy `made_at` rule (item 2), also in §5.11 and `architecture.md` §3's `MeasuredNoisy`.
- `data_model.md` §7: W5's approval rules (item 22) and measured-noisy rule (item 23); W1 resolves its path
  (item 27).
- `data_model.md` §8: Q1's `current_keys` (item 26); Q8 returns `ResultSummary`s (item 9); Q9's `batch_call` (item 10); Q12's
  `approval_points` (item 12); Q13's `Coverage` fields (item 13).
- `data_model.md` §5.8: `value` has no declared type (item 14).
- `architecture.md` §5: `Layout.of`, `run_dir`, `result_dir`; `Store.chunk_rows` and `busy_timeout_s`;
  `migrations.prepare`; `Store.current_keys` and `records.CurrentKey` (item 26); the run lock's fork caveat
  (item 28), also for the runner's sketch.

## Alternatives considered

- **W5 with §7's five arguments:** each would have to be checked against the result's own fields, or could
  disagree with them (item 1).
- **Setting `made_at` in the result as W5 stores it:** an evaluated result would differ from the stored one, and a
  replay (no W5) would report a difference (item 2).
- **A `REAL` prediction column:** −0.0 reads back as 0.0 (item 14).
- **Validating stored runs again in Q1:** twice the time, for rows that W4 checked and that never change (item 7).
- **Q8 loading each full result:** a result's provenance holds its run ids, up to 10⁷ of them; the listing needs
  only the counts (item 9).
- **`U` string arrays for hosts and programs:** 2.4 GB for 10⁷ rows of a 60-character path (item 8).

## Consequences

- **Size:** `ema.store` is 1,216 code lines after review round 1 (without docstrings, comments, or blank lines;
  1,990 physical): `store.py` 995, `records.py` 75, `migrations.py` 59, `lock.py` 33, `layout.py` 21, `__init__.py`
  33; and `schema.sql`'s 112 lines of SQL. Round 1 added about 113 (the result directory's swap, W5's approval
  and measured-noisy rules, `current_keys`). `architecture.md` §11's estimate is 715: about 500 over, much of it
  the formatter's one-argument-per-line inserts and the chunked readers. The budget record is the
  coordinator's.
- Steps 07 (`resolve`, `price`, `run_new`, `read_batch`, `replay_batch`, `ask_approval`) and 14 call these
  signatures; a later change to a table is a schema change (`data_model.md` §11).
