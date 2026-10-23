# 06. The store

**Status:** in progress (demo; record 0066); its choices are record 0072. **Branch:** `demo-06-store`.
**Updated:** 2026-10-02.

## Goal

`ema.store` exists: the workspace's database (SQLite, from Python's standard library), its files' paths, the
run lock, and the result directory, with one function per write W1–W6 and read Q1–Q15 of `data_model.md`, so
the runner and approval (07), the diagnostics (09–13), and the workspace (14) can keep and read every record.

## Implements

- **`data_model.md`:** all of it: §3 (logical types, canonical JSON, ids), §4–§5 (every table, key, index, and
  check, in `schema.sql`, shipped as package data), §6 (run, shared, and result directories' paths; the result
  directory written to a temporary directory and renamed into place), §7 (W1–W6), §8 (Q1–Q15, Q7 and Q15 in
  chunks of 30,000 rows), §9 (I1–I12: enforced by the store's checks and keys), §10 (one `Store` per thread,
  busy timeout 60 s, rollback journal, `synchronous=FULL`, foreign keys on; the run lock), §11 (the schema
  version in `PRAGMA user_version`; migrations in one `BEGIN IMMEDIATE` after a copy; a newer workspace refused).
- **`architecture.md` §5's `ema.store`:** `Store` (`open`, `layout`, `run_lock`, `result_directory`, `close`),
  `layout.py`'s `Layout`, `lock.py`'s run lock (`fcntl.flock(LOCK_EX | LOCK_NB)` on a descriptor kept open),
  `records.py`'s `ModelVersion`, `Loading`, `Confirmation`, `Approval`, `ApprovedPoint`, `BatchCall`, `RunUsed`,
  `Coverage`; `migrations.py`. AR1 (`ema.models | ema.store` siblings) and AR5 (only `ema.store` imports
  `sqlite3`) in `pyproject.toml`'s import contracts.
- **`contracts.md`:** the store's parts of C46, C50, C51, C52, and C56, and C17's round trip of a result through
  the store, as `tests/contracts/store.py`'s checks of I1–I12 (`data_model.md` §9), each with a broken toy and the
  meta-test.
- **Record 0070** items 12, 13, 18: the store writes `Provenance.column()` and `DiagnosticResult.column()`,
  reads with `from_columns`, keeps run ids in `result_runs`, and writes times with `text.timestamp_text`.

## Out of scope for this step

- `ema.runner` (`resolve`, `price`, `run_new`, `read_batch`, `replay_batch`) and `ema.approval` (07): they call
  Q1, Q2, Q13, Q15, W3, and W4; C47–C49's runner parts.
- The workspace (14): the reuse key's versions, `open_workspace`, the loading's message, `reproduce`, export.
- A version-2 schema and its fixture `tests/fixtures/workspace_v1.sql` (§11: "from version 2 on").

## Tasks

1. Plan and record 0072.
2. Tests first: `tests/contracts/store.py` (I1–I12, broken toys, meta-test), `tests/unit/store/` (each W and Q,
   the layout, the lock, migrations, the result directory, chunking), a slow-tier timing test; the wheel test
   gains `schema.sql` and the store's modules.
3. Code `ema/store/`: `schema.sql`, `records.py`, `layout.py`, `lock.py`, `migrations.py`, `store.py`.
4. Import contracts (AR1, AR5), `docs/index.md`'s API list, every check in `CLAUDE.md`; measure the lines.

## Checks before reporting done

- `uv run pytest -q && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto`.
- Lines of `ema.store` against `architecture.md` §11's 715.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0072's, numbered as there, one line each.

1. W5 is `record_result(result) -> DiagnosticResult`: the result carries its provenance, run ids, approval, and
   measured-noisy record; it returns the stored result (the stored one on a repeated id, nothing written).
2. A result's own measured-noisy record has `made_at` None (the coordinator's ruling): W5 refuses one set, writes
   the table's `made_at`, Q10 reads it, Q6 returns None, so evaluated == stored == replayed.
3. W5 checks the result id against its reuse key, its directory, its runs (exist, its model version), its
   approval (yes, a diagnostic evaluation, its model version), and I12, in its transaction.
4. W3 is `record_approval(*, model_version_id, asked_for, request, design, price, question, answer, points)`,
   `points` the `price.new` distinct new `RunKey`s; `n_before` counted in the same transaction.
5. W4 is `record_call(runs, batch_call=None)`; one run without a batch call; a precondition failure is
   `ValueError`, nothing stored; the run directory's existence is the runner's part of I5.
6. W1 refuses a relative spec path; Q14's spec has default settings (the loading's are Q3's).
7. Q1 builds stored runs without re-running `Run`'s checks (W4 ran them; rows never change): twice as fast; tested.
8. Q7/Q15 `values` hold every model prediction of the specs; hosts and programs are shared-string object arrays.
9. Q8 returns `ResultSummary`s from the `results` rows alone (no `result_runs`); ties ordered by insertion.
10. Q9: `get_run`, `runs_at`, directories by `Layout.run_dir`, and `batch_call(id) -> BatchCall`.
11. Q11 kinds `model_version`, `approval`, `run`, `batch_call`, `result`; malformed prefix `RequestError`; several
    `AmbiguousId` listing up to 10; a malformed id given to a read is `NotFound`.
12. Q12 adds `approval_points(approval_id)` (the only reader of `ApprovedPoint`).
13. Q13's `Coverage` is `(approval_id, model_version_id, answer, covered)`, with `complete`.
14. `predictions.value` has no declared type: a `REAL` column reads −0.0 back as 0.0 (measured).
15. Extra `CHECK`s: id lengths, `batch_size ≥ 1`, `timeout_s > 0`, times and std ≥ 0, `reused_failed ≤ reused`,
    a design exactly when not the test run.
16. Past the 60 s busy timeout, `WorkspaceBusy`; W4 retries until it commits; `chunk_rows`, `busy_timeout_s` are
    class attributes for tests.
17. `Store.open(path, *, create=True)`: the workspace's directory; `NotFound` without `create`; a non-EMA database
    or an unmigratable version is `WorkspaceVersion`; `migrations.prepare` takes `latest` and `migrations`.
18. The run lock writes its holder ("process <pid> on <host>, since <time>"), named by `WorkspaceBusy`.
19. The temporary result directory is `results/.<12 hex>-<random>` (atomic rename); a raced identical one wins.
20. The store contract runs over the `Store` class; broken toys are subclasses, some overriding private checks.
21. (Review round 1) The result directory swaps a directory in place under the write lock W5 holds; none deleted in place.
22. (Review round 1) W5: the approval asked for the result's request, cited by no other result, all its runs made and used.
23. (Review round 1) W5 takes a measured-noisy record only with a point run's result, as its own.
24. (Review round 1) `Store.open`: locked is `WorkspaceBusy`; not a database is `WorkspaceVersion`.
25. (Review round 1) Stored runs' model predictions in their spec's order.
26. (Review round 1) Q1's key-only read `current_keys -> dict[(hash, replicate), CurrentKey]` for `resolve`.
27. (Review round 1) Upper-case ids read back as stored; `result_directory` checks its id; chunks fit SQLite's
    variable limit; W1 resolves its path; W4 retries a busy statement inside its transaction.
28. (Review round 1) The run lock's fork caveat: the runner starts processes with `subprocess` or "spawn".
29. (Review round 2) W6 moves the result's directory aside inside its transaction, deleted after the commit.

## Notes

- **Built** on `demo-06-store` (record 0066), tests first: the contract module (`tests/contracts/store.py`, a
  check per invariant I1–I12 and C46's, 13 broken toys, the meta-test) and the unit tests were written before
  `store.py`; each toy fails its check on the assertion meant for it (checked one by one).
- **Tests:** 1,172 in the fast tier (2 slow skipped), 96 of them new: `tests/unit/store/` 55,
  `tests/contracts/store.py` 41 collected (13 checks, the meta-test over 13 toys, and the invariant list; the
  contract conftest collects each `test_*` twice, as it does for `model.py`); the slow tier adds
  `tests/slow/test_store_scale.py` (70,001 runs across real 30,000-row chunks) and the wheel test's store modules
  and `schema.sql`. All 1,174 pass with `--slow -n auto`.
- **Times** (this Mac, 2026-10-02, other builds running): the fast tier 14.5 s serially (the store's tests 1.4 s
  and 0.8 s); both tiers 25 s with `-n auto`; the scale test about 11 s. At 10⁵ stored runs: W4 about 0.11–0.16 ms
  per run in batch calls of 10⁴; Q1 2.4 s; Q15 1.5 s (1.6 s with points); Q7 1.5 s; W5 1.3 s; Q6 0.1 s; Q2
  0.01 s.
- **Source lines** (code lines, as plan 01 counts them): `ema.store` 1,103 [1,801 physical]: `store.py` 890,
  `records.py` 69, `migrations.py` 59, `lock.py` 33, `__init__.py` 31, `layout.py` 21; and `schema.sql` 112 lines of
  SQL. Against §11's 715: about 390 over (record 0072, Consequences); the budget record is the coordinator's.
- **Shared files, edited additively:** `pyproject.toml` (AR1's layer `ema.models | ema.store`; `ema.store` added to
  AR4's and the reference models' sources; AR5 already excludes it), `docs/index.md` (a block of its own for the
  store's five modules), `tests/slow/test_wheel.py` (a `MODULES +=` list of its own).
- **Deferred** (0072): §6's timing test, pricing at 10⁶, is step 07's (`current_keys` measured about 7–8 s per 10⁶
  extrapolated); the version-1 workspace fixture (from schema version 2 on).
- **Review round 1** (0072 items 21–28): every major, minor, and cheap nit fixed, each with a test; the fast tier
  is 1,183 tests (2 slow skipped), 11 of them new, and the contract's meta-test covers 17 toys (4 new). New:
  `tests/unit/store/test_concurrency.py` (4 spawned processes, 12 trials, about 1 s). Not changed: `RunUsed` stays
  exported (`architecture.md` §5 and `data_model.md` §10 name it); the `_Listed` cast stays, since a typed
  alternative needs `ResultSummary.make` in `ema.types` to take a protocol (step T's module). `ema.store` is now
  1,216 code lines (`store.py` 995).
- **For step 07:** `resolve` and `price` read Q1's key-only `current_keys` (each key's run id, attempt, status);
  `run_new` calls Q13 before each call and W4 after it, with `BatchCall` for a batch call; `ask_approval` calls W3
  with the `Price` and the new keys; `read_batch` and `replay_batch` read Q15 (`runs_by_id`, `points=True` for a
  replay); model processes start with `subprocess` or "spawn" (the run lock's fork caveat). For step 14: W5 takes
  the result whole, after `result_directory` puts its files in place, and refuses (`ValueError`) a result whose
  approval was asked for another request, is cited by another result, or has a priced run not made and used; a
  measured-noisy record only with a point run's result.
