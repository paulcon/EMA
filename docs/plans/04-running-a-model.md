# 04. Running a model: the command-line model, and the Python model's child (steps 04 and 05)

**Status:** in progress (demo; record 0066); its choices are record 0071. **Branch:** `demo-04-models`.
**Updated:** 2026-10-02.

## Goal

A loaded model can be run, one call at a time, through the three phases of `architecture.md` §5: `prepare` writes
a call's run directories, `execute` runs a command (no shell, its own process group, stdin from `/dev/null`, the
model's environment) or a Python function, or a batch of points, in its model version's isolated child, and
`collect` reads the model predictions from files only and returns each run's record, never raising for a point.
Steps 04 and 05 are built together (the roadmap's rows), so the model adapter contract runs whole over a Python
function, a batch, and a command-line model.

## Implements

- **`docs/design/architecture.md` §5, `ema.models`:** `prepare.py` (`PreparedCall`, `prepare`), `execute.py`
  (`ExecutedCall`, `execute`; imported in `ema` by `ema.runner` only, AR4), `collect.py` (`collect`), `parsers.py`
  (`OutputParser`, `register`, `get`, `names`, `unregister`; regex, JSON, CSV), `files.py`'s `remove_tree`,
  `spec.py`'s `resolve_program`, `sandbox.py` (`BASE_ENV`, `model_environment`, the child), `_worker.py`,
  `processes.py` (`ModelProcesses`); §10's AST check on `ema/models/__init__.py` kept (it re-exports no execute).
- **`docs/design/model_interface.md`:** M1, M2, M4, M5, M7–M16 (M16: the hash check before a call exists from step
  03; the call's refusal is the runner's), M19, M20; the Python function's interface (float or mapping; batch);
  Isolated; Command line (command, input decks, numbers, files, environment, parsers); A run; Failures.
- **`docs/design/trust.md`:** T2 (the environment, both kinds), T4 (nothing runs in EMA's process), T9 (output read
  inside the run directory; EMA's files written, and directories deleted, without following links; streams off
  EMA's stdout); Running a model.
- **Records:** 0020, 0025, 0026, 0028, 0030, 0031, 0043; 0069 item 34 (the child's `sys.path`, a function file in a
  subdirectory as a dotted module); 0070's `Run`, `RunKey`, `RunStatus`, `FailureKind`.
- **`docs/design/contracts.md`:** C31, C32, C34–C45 in `tests/contracts/model.py` (beside step 03's C33), each with
  its broken toys, over the kinds its "Run over" column names.
- **v1:** `core/models/_sandbox.py` and `_worker.py` ported after re-review (named below); `cli.py`, `parsers.py`,
  and `python_fn.py` read.

## Out of scope for this step

- The runner (step 07): `run_new`'s refusal of a call after `check_files` fails (C34's call), its call sizes
  (`batch_size`, and what remains approved: C37's sizing), its Ctrl-C handling (C41's and C49's stopped call
  through `run_new`), and storing runs (W4). `execute` is written for it, and tests call it directly.
- The first approval's text (step 07) — `resolve_program` gives it the program.
- Under a scripted MCP client, the protocol stream with a printing function (T9's last test; step 15).

## Tasks

1. Extend the toys in `tests/models/` with a `mode` model parameter that picks a behaviour (failures, a hang with a
   child process, an inspection of the environment, a write to the shared file, non-finite and missing model
   predictions, prints, a wrong return) and the command toy with a second, regex-parsed model prediction.
2. Tests first: the contract checks C31, C32, C34–C45 and their broken toys in `tests/contracts/model.py`;
   unit tests in `tests/unit/models/` (`test_sandbox.py`, `test_prepare.py`, `test_execute.py`,
   `test_parsers.py`, and additions to `test_files.py` and `test_spec.py`).
3. The code: `sandbox.py`, `_worker.py` (ported), `processes.py`, `prepare.py`, `execute.py`, `collect.py`,
   `parsers.py`, `files.py`'s `remove_tree` and `write_own`, `spec.py`'s `resolve_program`.
4. The import contracts (AR4's source modules), the API reference, the package's re-exports.
5. The checks in `CLAUDE.md`; the slow tier for this package.

## Checks before reporting done

- Fast tier with the import contracts, lint, mypy, docs with `-W`; the slow tier for `tests/contracts/model.py`
  and `tests/unit/models`.
- `ema.models`' lines against §11's 1,323.

## Stop condition

All checks pass; report to the coordinator (record 0066), and wait for the review.

## Choices made here

Each is in record 0071, with why; the numbers match.

1. A command's program: a name found on the model's own `PATH`, a path with `/` in the run directory; run by its
   resolved path with `argv[0]` as written; `find_program` shared by `execute` and `resolve_program`.
2. `resolve_program` shows a program given with `/` at its place in the model's directory; a Python function's is
   `sys.executable`.
3. When a program exits, its process group is killed, so nothing it left running writes to its run directory.
4. A program's exit is awaited on a pidfd or kqueue, not `Popen.wait`'s polling.
5. Failure reasons: "exited with code N", "killed by signal SIGKILL", "timeout after N s", "couldn't start X: …",
   "Type: message at file.py:line", "the child exited with code N", "couldn't load file.py:f: …".
6. The child receives `sys.path` as a length-prefixed block of NUL-separated paths, read with `os` alone, before any
   import; the model's directory is put first after the worker's own imports.
7. The function file is imported as a dotted module of the model's directory (0069 item 34).
8. The model's own modules are compiled from source, never from a cached `.pyc` (P3).
9. A new child may take `max(timeout_s, 60 s)` to start and import; the start is not the call, and is not timed.
10. The child starts in the first call's directory; an import failure fails the call, its traceback in the call's
    `stderr.txt`.
11. The protocol: one JSON line per message with a sequence number; points as JSON doubles (exact); per-run replies;
    a malformed reply is the child's death.
12. A call's streams: the worker points its file descriptors 1 and 2 at the call's files for the call; between
    calls, 1 is EMA's stderr.
13. A function's exception: the reason names the innermost frame in the model's directory; one line, 300
    characters at most; the traceback to the call's stderr; `SystemExit` fails the call and keeps the child.
14. Returns (M7): a number for a model with several model predictions, or something neither a number nor a
    mapping, fails the call; a value that isn't a number (a string, a bool) is missing, with its type.
15. A batch returns an `(n,)` array or a mapping of them; any other shape fails the call.
16. At most four children (v1's `MAX_CHILDREN`), least recently used stopped; all stopped at `close` and at exit.
17. The child takes its environment when it starts; it is keyed by model version.
18. `prepare` takes the call's `approval_id` as a keyword (the stub's `PreparedCall` holds it).
19. Every batch model's call has a batch directory (a call of one point too); its listed files and streams are
    there; each run's directory holds `point.json`, `predictions.json`, and `run.json`.
20. `point.json` holds the point by name only (no run id or replicate: the program is told nothing else).
21. A shared copy is written to a temporary file, hashed while copied, refused (`ModelChanged`) when its digest
    isn't the loading's, made read-only, and renamed into place; the link is absolute.
22. Listed files are copied with their permissions (a program listed as a file stays executable).
23. `predictions.json` holds `{"predictions", "missing"}`; one collect can't read fails its run, kind `error`.
24. `ExecutedCall.run_errors`: per run, why EMA couldn't write its `predictions.json` (kind `error`, 0057).
25. `ExecutedCall` is `execute.py`'s; `collect.py` names it under `TYPE_CHECKING` only, and AR4's contract lists
    every other module of `ema.models` as a source.
26. An `unread` run's reason: "no model prediction read (y: …; z: …)"; reasons one line, 500 characters at most.
27. `run.json`: the run's record, with the command or the function, and the call's directory.
28. The stderr tail: the last 15 lines of the call's `stderr.txt` (its last 64 KiB read), for a failed run only.
29. `collect.py` adds `kept`, `keep_or_remove`, `discard`, and `stderr_tail` for the runner.
30. Parsers: reasons name the file ("plate.out: pattern not found"); JSON's booleans aren't numbers, a JSON string
    holding a number is read; a regex group that matched nothing is missing; CSV headers are stripped.
31. `remove_tree` makes read-only directories writable to empty them; `write_own` opens the directory without
    following a link and creates the file exclusively in it.
32. `ModelProcesses.child` refuses a command-line model (`TypeError`).
33. The host is `socket.gethostname()`; a call's time runs from the program's start, or the request, to its exit or
    reply.
34. The toys' `mode`; the bench runs the command toy with the project's interpreter first on its `PATH`.
35. The slow tier holds C31's, C38's, and C41's batch variants and C41 over the command-line model.

Review round 1 (record 0071, items 36–50):

36. Ctrl-C is held while a process starts (`InterruptHeld`) and delivered inside the `try` that kills it.
37. A process's exit is seen without reaping it (`waitid` `WNOWAIT`); its group is killed, then it is reaped; a
    refused pidfd falls back to a 5 ms check; waits use `poll`.
38. The child is checked every 0.5 s while a reply is awaited, so a crash is seen at once.
39. A reply line is at most 64 MiB; a reply EMA can't parse, or out of step, is the child's death.
40. `execute` checks the reply again: only finite numbers and text reasons reach `predictions.json`.
41. JSON integers are read as doubles (the JSON parser, `predictions.json`): one too large is not finite.
42. Text is a number in ASCII decimal syntax only (sign, point, exponent; `inf` and `nan` read and refused).
43. A call's time is its request's to its reply; a new child's start is never in it.
44. The stderr tail reads the last 64 KiB, once per call, for a failed run only.
45. `remove_tree` empties unreadable directories at any depth, changing nothing above its path.
46. The worker restores file descriptors 1 and 2 and `sys.stdout` and `sys.stderr` after every call.
47. Only the model's own modules are compiled from source: not EMA's `sys.path` entries in its directory, nor a
    `site-packages` below it.
48. M7: `np.bool_` and complex aren't numbers; an integer beyond a double is missing; a batch's values are read as
    a mapping's.
49. A stream file `execute` can't create fails the run, kind `error`; a worker that can't start fails the call.
50. AR4 lists `ema.models.collect`, with `exclude_type_checking_imports = true`.

## Notes

- **Built:** `src/ema/models/{sandbox,_worker,processes,prepare,execute,collect,parsers}.py`; `files.py`
  (`remove_tree`, `write_own`), `spec.py` (`resolve_program`), `__init__.py` (re-exports `ModelProcesses`,
  `remove_tree`, `resolve_program`). Tests: `tests/contracts/model.py` (C31, C32, C34–C45, 15 broken toys beside
  C33's), `tests/unit/models/test_{sandbox,prepare,execute,parsers}.py`, additions to `test_files.py` and
  `test_spec.py`; the toys in `tests/models/{python,batch,command_line}` and `tests/support/models.py` (the bench).
  Shared files: `pyproject.toml` (AR4's sources), `docs/index.md` (a block of its own).
- **Ported from EMA v1 at v1-final:** `src/ema/core/models/_sandbox.py` (into `sandbox.py`'s `Child`: the two
  pipes, sequence numbers, the `select` loop, the process-group kill) and `src/ema/core/models/_worker.py` (into
  `_worker.py`: the protocol loop). Re-reviewed against trust.md: v1's memory and CPU limits, its watchdog, its
  withheld variables, its output-parser kind, and its profiling dropped; the environment is trust.md's allowlist;
  `sys.path` over the pipe; streams to the call's files. `cli.py`, `parsers.py`, and `python_fn.py` read, not
  ported.
- **Size** (code lines without docstrings, comments, or blanks): `ema.models` 1,210 against §11's 1,323; this
  step's part about 908 (`sandbox` 178, `_worker` 164, `collect` 150, `parsers` 123, `execute` 122, `prepare` 94,
  `processes` 33, `files` +33, `spec` +7) against the roadmap's 1,160 (640 + 520).
- **Times:** the fast tier went from about 12.5 s to about 22–24 s on this machine, measured while other agents
  were building (it is shared); about 7 s of it is the model contract, whose runs start processes (about 45 ms
  each for a program here), time out (0.25 s), and press Ctrl-C (0.2 s). The slow tier for this package takes
  about 5 s with `-n auto`.
- **Deferrals:**
  - C37's negative control "fills the last batch past the approved count" and its check (calls of at most
    `batch_size` points, never more than remain approved) are the runner's: step 07, about 20 test lines; the seam
    is `prepare`, which takes any keys. This step's C37 broken toy fails only the first run of a failed batch.
  - C34's refusal of the next call, and C41's stopped run, through `run_new`: step 07 (this step checks
    `check_files` raising and `discard`).
  - T9's protocol stream under a scripted MCP client: step 15 (this step checks that EMA's stdout stays empty).
- **Review round 1** (fixed on this branch; record 0071, items 36–50): Ctrl-C while a program or the child
  starts no longer leaks it (21 of 40 probe calls did); a refused pidfd no longer fails every command; the four M1
  gaps (an over-long JSON integer, a deeply nested reply, a reply whose model predictions aren't a mapping, a
  400-digit integer in `predictions.json`) fail or miss a run, never raise; a crash with a descendant holding the
  pipe is seen in 0.5 s, not at the timeout; a first call's time leaves out the child's start; the stderr tail
  reads 64 KiB; `remove_tree` handles nested unreadable directories; AR4 covers `collect`. Nits: the reply is
  read in linear time and capped at 64 MiB; the wait's deadline is computed once; a finished program's group is
  killed before it is reaped; the worker's stream restore and two descriptor leaks; the source-only hook's reach;
  M7's consistency; `finite`'s syntax; `poll` for `select`. Tests: `tests/unit/models/test_{execute,sandbox,
  parsers,files}.py` (one or more per finding, each failing before the fix). Signatures step 07 uses are
  unchanged; `Outcome` gained `time_s` (with a default), `read_inside` a `last` keyword, and `sandbox.py` the
  public `InterruptHeld`, `has_exited`, `kill_group`, `readable`, `MAX_REPLY_BYTES`.
- **Size after review round 1:** `ema.models` about 1,341 code lines, over §11's 1,323 by about 18; proposed in
  record 0071 (Questions), not settled here. Fast tier about 26.5 s on this machine (shared).
- **Reviewer, look hardest at:** the child's lifecycle under Ctrl-C and timeouts (`sandbox.Child._exchange`,
  `close`); `_worker.py`'s file-descriptor juggling around a call; choice 3 (killing a finished program's process
  group), which goes beyond M20's wording; and that `collect` can't raise for a point.
