# 07. The runner and approval

**Status:** in progress (demo; record 0066); its choices are record 0074. **Branch:** `demo-07-runner`.
**Updated:** 2026-10-02.

## Goal

`ema.runner` and `ema.approval` exist: a design is resolved against the store, priced, approved (the question
rendered, asked, and recorded), and its new runs made one call at a time, each call checked against its approval
and the model's files before it starts and stored after it ends, so the workspace (14) can run a diagnostic
evaluation and the test run, and the diagnostics (09–13) receive their run batches in the design's order.

## Implements

- **`architecture.md` §6 (3b):** `ema.runner`'s `resolve`, `price`, `run_new`, `read_batch`, `replay_batch`;
  `ema.approval`'s `ask_approval`, `ask_confirmation`, `ask` (re-exported as `ema.ask`); §7's steps 4–7 of one
  evaluation, and `test_model`'s steps, as far as they are the runner's and approval's.
- **`data_model.md`:** Q1, Q2, Q13 (before each call), W3, W4 (after each call), §10's run lock (held by the
  caller); I4 and I5 from the runner's side.
- **`trust.md`:** T3 (every question asked recorded, none when nobody can be asked), T4 (asking), T7's and T8's
  question text (hidden characters as codes, strings EMA didn't write in code spans and fenced blocks, `pass_env`
  names with "set" or "not set"), What needs a yes (the first approval's details), T6's question text.
- **`contracts.md`:** the runner's parts of C46–C49 and C56 (`architecture.md` §9: the store contract "with the
  runner and millisecond models"); C34, C37, and C41 finished through `run_new` (record 0071's deferrals).
- **Records** 0010 (failed runs reused, retried as the next attempt), 0015 (the serial loop, runs counted when they
  start), 0049 (the test run approved like any new run; the confirmation), 0056 (Q13 per call), P3.

## Out of scope for this step

- The workspace's order of an evaluation (14): the lock taken and the design resolved again under it, the reuse
  key, W5; `Resolution`'s row run ids built for `read_batch` (the workspace builds them, §6).
- The CLI's and the MCP server's approvers (15, 16): `--yes`, elicitation, `ELICITATION_TIMEOUT_S`.
- The store's key-only read for `resolve` (record 0072's deferral): `resolve` uses Q1 as it is.

## Tasks

1. Plan and record 0074.
2. Tests first: `tests/contracts/runner.py` (the runner's parts of C34, C37, C41, C46–C49, C56, broken toys, the
   meta-test), `tests/unit/test_runner.py`, `tests/unit/test_approval.py`; `tests/support/runner.py`; the toys
   log the points they are called at when `TOY_CALLS` is set.
3. Code `src/ema/runner.py` and `src/ema/approval.py`; `ema.ask` re-exported.
4. Import contracts (AR1 layer 3b, AR4, AR5, the reference models' contract), `docs/index.md`, the wheel test's
   module list; every check in `CLAUDE.md`; measure the lines.

## Checks before reporting done

- `uv run pytest -q && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto` on this step's tests.
- Lines of `ema.runner` and `ema.approval` against `architecture.md` §11's 418 (the roadmap's 440).

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0074's, numbered as there, one line each.

1. `run_new` refuses a call its approval can't cover with `ValueError` (an error in EMA's code, 0070 item 4).
2. A call is the next `batch_size` keys cut to the leading ones Q13 covers; none covered is the refusal.
3. Q13, then `check_files`, before each call; `prepare` → `execute` → `collect` → W4 → `keep`.
4. Any exception before W4 returns (Ctrl-C included) deletes the call's directories, found from its keys.
5. Progress: "0/n runs" before the first call, then after each call's W4 and `keep`.
6. `run_new`'s loop is a private class, `ema.runner._Loop`, so the contract's broken toys change one step.
7. `resolve` keys rows by exact bytes and replicate, new keys in first appearance; one store read, `_current`.
8. `price`: new and reused once per key; `new` × Q2's mean over every stored run; "time unknown" with none.
9. `read_batch` refuses a row count that isn't the design's; `replay_batch` builds the design from stored points.
10. The run lock is the caller's; `run_new` doesn't check it.
11. The approval's text: the model version, what it is for, the price; the first approval adds what each run starts.
12. Strings EMA didn't write in code spans or fences longer than any backtick run; hidden characters as codes.
13. Only `True` is a yes; an exception is a no, recorded; Ctrl-C at the question is recorded as a no and passes.
14. `ask_approval` checks the price against the resolution, new runs, and `asked_for`; `CannotAsk` first.
15. `ask_confirmation`: the name's meaning from Q3; same bytes on disk ask "already saved, unchanged: load it?".
16. `ask`: question and prompt on stderr, one line from stdin; "y" or "yes" is yes; `ema.ask` re-exported.
17. The runner's contract checks are their own module, `tests/contracts/runner.py`.
18. The three toys log each point they are called at to `TOY_CALLS` when set.
19. Ctrl-C in the checks: 0.1 s after a progress count, from a timer started in the callback.
20. Fast tier: C46, C47, C56 (and their meta-test), C48, C49 over the Python toy; the rest slow.
21. Review round 1: a call is also cut at the first key W4 wouldn't store (`current_keys`); none runnable refuses.
22. An exception after W4's COMMIT leaves the call stored: directories deleted only when it isn't, else `keep`.
23. "0/n runs" once the first call has passed Q13 and `check_files`; a refused first call reports nothing.
24. `resolve` reads `Store.current_keys` and hashes each point once.
25. `ask_approval` checks the design against `asked_for`, the model version, the files (first approval), `reused`.
26. An approver's exception text is a code span; a backslash in a path shown in a question is doubled.

## Notes

- **Size:** `ema.runner` 189 code lines, `ema.approval` 211: 400 against §11's 418 (record 0074, Consequences);
  364 before review round 1.
- **Tests:** 33 fast (about 1 s), 51 with the slow tier (about 5 s with `-n auto`). The whole fast tier measured
  27.6 s to 30.5 s on this machine under other builds' load (27.9 s before this step); the full slow tier 23 s.
- **Review round 1** (`demo-07fix`; record 0074 items 21–26): both majors (a stale resolution's key run twice,
  M1; a stored call's directories deleted by Ctrl-C after W4's COMMIT, M2) and the minors fixed, each with a test;
  `check_run_once` added to the fast tier (its meta-test slow); now 40 fast tests, 62 with the slow tier (the
  whole fast tier 36.5 s with `-n auto` at a load average near 57); `resolve` at 10⁵ points 1.08 s (was 1.51 s). The
  deferrals (`Store.current_keys`, `tests/contracts/store.py`'s pointer) are closed.
- **Spec edits on acceptance** (record 0074): `architecture.md` §9's contract table names `tests/contracts/runner.py`;
  §6's `run_new` raises `ValueError` for an uncovered call; `trust.md`: Ctrl-C at the question is recorded as a no.
