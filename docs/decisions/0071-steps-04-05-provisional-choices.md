# 0071. Steps 04 and 05's provisional choices: running a model, and the Python model's child

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build steps 04 and 05 (`../plans/04-running-a-model.md`) were built together on `demo-04-models` without the
owner's review (0066): `ema.models`' three phases (`prepare`, `execute`, `collect`), the output parsers, `remove_tree`,
`resolve_program`, `sandbox.py` (the environment and the isolated child), `_worker.py`, and `ModelProcesses`; the
model adapter contract's C31, C32, and C34–C45. The specs (`../design/model_interface.md`, `../design/trust.md`,
`../design/architecture.md` §5, `../design/data_model.md` §5.6–§5.8 and §6, `../design/contracts.md`) and records
0020, 0025, 0026, 0028, 0030, 0043, 0057, 0069 (item 34), and 0070 leave some details open. Each choice below keeps
P1–P7 and the specs' intent. v1's `core/models/_sandbox.py` and `_worker.py` were re-reviewed against trust.md and
ported (without v1's limits, watchdog, withheld variables, output-parser kind, and profiling); `cli.py`,
`parsers.py`, and `python_fn.py` were read.

## Decision

We will, provisionally:

**A command**

1. **Resolve the program as the model's environment would:** a name with `shutil.which` on the model's own `PATH`
   (`model_environment`'s, so empty and relative base entries are gone, T2); a path with a `/` against the run
   directory, where its listed copy is. The program runs by its resolved path (`Popen(executable=...)`), with
   `argv[0]` as written. Not found: the run fails, kind `error`, "couldn't start X: not found on the model's PATH",
   with no exit code and the program recorded as written. `sandbox.find_program` does this for both `execute` and
   `resolve_program`, since `spec.py` can't import `execute` (AR4).
2. **`resolve_program`** (before any run, for the first approval) shows a program given with a `/` at its place in
   the model's directory (each run starts its copy), and a Python function's program as `sys.executable` (0029).
3. **When a program exits, its process group is killed:** what it left running (a background job) can't write to
   its run directory after `collect`, which "EMA never changes a run directory after its run" (0020) relies on.
   M20 names only the timeout and Ctrl-C; this adds the normal exit.
4. **A program's exit is awaited on a pidfd (Linux) or kqueue (macOS),** each wakeup checked with `poll`, not
   with `Popen.wait`'s polling, whose sleeps (up to 50 ms) dominate a millisecond program's run.
5. **Reasons** (one line): "exited with code N"; "killed by signal SIGKILL"; "timeout after N s" (`timeout_s` as
   `:g`); "couldn't start X: …"; a function's "ZeroDivisionError: division by zero at model.py:19"; "the child
   exited with code 3", "the child was killed by signal …"; "couldn't load model.py:f: ModuleNotFoundError: …".

**The Python child** (`sandbox.Child`, `_worker.py`)

6. **`sys.path` over the pipe, before any import:** the worker, started by its path, first reads a length-prefixed
   block of NUL-separated absolute paths with `os` alone (no `json` yet, which a `PYTHONPATH` entry could
   shadow), and replaces its `sys.path` with EMA's (each entry made absolute, a notebook's `''` included); it
   imports its own modules, then puts the model's directory first, so a model's `json.py` can't shadow the
   worker's.
7. **The function file is imported as a module of the model's directory:** `sub/model.py` is `sub.model`, so
   relative imports work and agree with M17's check (0069 item 34). The file's own directory is not added.
8. **The model's own modules are compiled from source, never from a cached `.pyc`** (a path hook for the model's
   directory): a `.pyc` whose recorded time (to the second) and size match an edited source would run old code
   under the new model version (P3; v1's lesson).
9. **A new child may take `max(timeout_s, START_TIMEOUT_S)`, 60 s, to start and import the function:** the start
   is not the call, and isn't in its time; a short `timeout_s` mustn't fail every call of a model whose libraries
   import slowly.
10. **The child starts in the first call's directory** (module-level code reads the run's copies); an import
    failure fails that call, kind `error`, its traceback in the call's `stderr.txt` (so in the stderr tail); the
    next call tries a new child.
11. **The protocol** (v1's): one JSON line per message over two pipes of the child's own, each request with a
    sequence number its reply echoes; points as JSON doubles (exact, by `repr`); the reply holds each run's model
    predictions and reasons. A reply that isn't JSON, or is out of step, is the child's death. Nothing is pickled.
12. **A call's streams:** for the call, the worker points its file descriptors 1 and 2 at the call's
    `stdout.txt` and `stderr.txt` (created exclusively, without following a link); between calls, 1 is EMA's
    stderr, so nothing reaches EMA's stdout (T9).
13. **A function's exception:** the reason names the innermost frame in the model's directory, one line, the
    message at most 300 characters; the traceback goes to the call's `stderr.txt`. `SystemExit` fails the call and
    keeps the child.
14. **Returns (M7):** a number, when the model has one model prediction, or a mapping by name; a number for a
    model with several, or anything neither a number nor a mapping, fails the call ("returns a mapping"); a value
    that isn't a number (a string; a bool, though Python's bools are integers) is missing, naming its type; a
    non-finite one is missing, naming it ("the function returned nan"); a name not returned is missing ("the
    function didn't return it").
15. **A batch (M8)** returns an `(n,)` array, or a mapping of names to them; any other shape fails every run in the
    call, with one reason.
16. **At most `MAX_CHILDREN` = 4 children** (v1's), the least recently used stopped; `ModelProcesses.close`, and a
    finalizer at exit, stop them all.
17. **A child is keyed by model version, and takes its environment when it starts** (trust.md); a `pass_env`
    value changed later in EMA's environment reaches the next child only.

**Prepare and collect**

18. **`prepare(model, keys, runs_dir, shared_dir, *, approval_id)`:** §5's `PreparedCall` holds the approval id,
    which the stub's signature doesn't take.
19. **Every call of a batch model has a batch directory** (`runs/<batch call id>/`, a call of one point too), where
    the function runs, with the listed files and the call's streams; each run's directory holds `point.json`,
    then `predictions.json` and `run.json`. A command or a single function's call runs in its run directory.
20. **`point.json`** holds the point by name, in the spec's order; nothing else (the program is told no run id
    and no replicate).
21. **A shared file's stored copy** is written to a temporary file beside it, hashed while copied, refused with
    `ModelChanged` when its digest isn't the loading's (the source changed after `check_files`), made read-only,
    and renamed into place; the link in the run directory is absolute. A copy in place is never rewritten.
22. **Listed files are copied with their permissions** (a program listed as a file stays executable), a link in
    the model's directory followed.
23. **`predictions.json`** is `{"predictions": {...}, "missing": {...}}`, written by `execute`; `collect` reads it
    from inside the run directory, keeps only finite numbers, and fails a run whose file it can't read, kind
    `error` ("predictions.json: couldn't be read (...)").
24. **`ExecutedCall.run_errors`** (beyond §5's stub): per run, why EMA couldn't write its `predictions.json` (kind
    `error`, 0057), since a batch call's runs have one directory each.
25. **`ExecutedCall` is `execute.py`'s**, and `collect.py` names it under `TYPE_CHECKING` only, never importing
    `execute` at run time; AR4's contract lists every other module of `ema.models` as a source.
26. **An `unread` run's reason** lists each model prediction's: "no model prediction read (y: out.json: not found;
    w: stdout: pattern not found)". Every reason is one line of at most 500 characters.
27. **`run.json`** holds the run's record (`Run`'s fields, the point by name), with the command or the function,
    and the call's directory; written without following a link, and a run it can't be written for fails, kind
    `error`, "run.json: couldn't be written: …" (T9).
28. **The stderr tail** is the last 15 lines of the call's `stderr.txt` (its last 64 KiB read, inside the
    directory), for a failed run only; a batch's runs share their call's.
29. **`collect.py` also has `kept`, `keep_or_remove`, `discard`, and `stderr_tail`,** for the runner: the keep rule
    (`incomplete`: failed, or a model prediction missing); a batch directory deleted with the last of its runs'
    (`data_model.md` §5.7); a stopped call's directories deleted (0028).
30. **Parsers:** a reason names the file ("plate.out: pattern not found", "out.json: no key forces.lift", "h.csv: no
    column lift", "…: 'inf' is not a finite number", "…: outside the run directory", "…: not found"); JSON's
    booleans aren't numbers, and a JSON string holding a number is read (as v1); a regex group that matched
    nothing is missing; CSV headers are stripped; a file that isn't regular is never waited on.
31. **`remove_tree`** makes a directory the model made read-only writable to empty it, and removes a link at its
    path without following it; **`write_own`** opens the directory without following a link and creates the
    file exclusively there.
32. **`ModelProcesses.child`** refuses a command-line model with `TypeError`.
33. **The host** is `socket.gethostname()`; **a call's time** runs from the program's start, or the request's send,
    to its exit or the reply.

**Tests**

34. **The toys' `mode`** (a held model parameter, nominal 0) picks a behaviour (`tests/support/models.py`); the
    command toy also reads w with a regex from stdout. The bench runs the command toy with the project's
    interpreter first on its `PATH` (macOS's `/usr/bin/python3` is a shim that adds variables of its own).
35. **The slow tier** holds C31's, C38's, and C41's batch variants (the Python variant's child again, with timeouts
    and Ctrl-C) and C41 over the command-line model (its rule reads only statuses), for the fast tier's 30 s.

**Review round 1** (the independent review's findings, fixed; each has a test in `tests/unit/models/`)

36. **Ctrl-C is held while a process starts** (`sandbox.InterruptHeld`; M20, C39): from just before `Popen` (a
    command's program, or the child) until the process is bound inside the `try` whose handler kills it, a SIGINT
    only sets a flag; that `try` first restores the previous handler and, if a SIGINT came, delivers it again
    (`signal.raise_signal`), so the previous handler runs there (Python's raises `KeyboardInterrupt`, and the
    process is killed; one that ignores SIGINT lets the run go on). Signals are never blocked (a blocked mask is
    inherited by the program); outside the main thread nothing is held (Python runs no handler there). A child
    that never received its `sys.path` is killed, never kept. Killing a group (`kill_group`, `Child.close`) holds
    Ctrl-C too, so a second one can't leave it running.
37. **A process's exit is seen without reaping it** (`has_exited`: `waitid` with `WNOWAIT`), and its group is
    killed before it is reaped (`kill_group`), so the group id can't be a new process's (choice 3). A program's exit
    is awaited on a pidfd or kqueue; where neither can be had (`pidfd_open` refused with ENOSYS or EPERM: an old
    kernel, a seccomp filter), it is checked every 5 ms. Every wait polls (`select.poll`), so a descriptor
    numbered over 1,023 works.
38. **A crash is seen at once:** while a reply is awaited, the child is checked every 0.5 s, so a child that died
    while a process it started holds the replies pipe open fails the call then, not at the timeout.
39. **A reply line is at most `MAX_REPLY_BYTES` = 64 MiB;** a longer one is the child's death, read no further.
    Only each new chunk is searched for the line's end. A reply EMA can't parse (nested too deeply, an integer too
    long for Python) is the child's death; a `seq` that isn't an integer is out of step; a child's error that isn't
    text fails the call ("the child's error isn't text"), and one is kept to 1,000 characters.
40. **The reply is checked again in EMA** (M1): `execute` writes to `predictions.json` only finite numbers (not
    bools) and only text as a reason; a run whose reply holds no mapping of model predictions fails, kind `error`;
    a value that isn't a finite double is missing ("the child's reply holds no finite number for it").
41. **JSON integers are read as doubles** in the JSON parser and in `predictions.json` (`parse_int=float`): one
    beyond a double's range, or too long for Python's int, is infinite, so missing as not finite, never an
    exception. `predictions.json` that isn't EMA's (not a mapping of mappings, or nested too deeply) fails its run,
    "predictions.json: not EMA's model predictions"; a value in it that isn't a finite double is missing,
    "predictions.json: not a finite number".
42. **Text is a number in ASCII decimal syntax only:** an optional sign, digits with an optional point, or a point
    and digits, and an optional exponent (`+1.5E+03`, `.5`, `5.`), or a spelling of infinity or NaN (read, then
    missing as not finite). `1_000`, other scripts' digits, `0x10`, and Fortran's `1.5D+03` are "not a number".
    The review suggested JSON's syntax; it would refuse `+1.0e+00` (C's `%+e`) and `.5000E+00` (Fortran's `E`
    format), which solvers print.
43. **A call's time** (`Outcome.time_s`) runs from the call's request to its reply; a new child's start and import
    are never in it. When the call fails while the child starts, its time is the start's.
44. **The stderr tail reads only the file's last 64 KiB** (`read_inside(..., last=)`), once per call and only when
    a run failed.
45. **`remove_tree` empties a directory without read or search permission at any depth** (each failed entry
    retried once, recursively); it changes no directory above `path`.
46. **The worker restores its streams after every call:** file descriptors 1 and 2, and `sys.stdout` and
    `sys.stderr`, whatever the function made of them (replaced, closed); a failure's message goes to file
    descriptor 2 directly. A stream file it can't create closes the other.
47. **Only the model's own modules are compiled from source** (choice 8): a directory in the model's directory that
    is an entry of EMA's `sys.path` (a project's `.venv`, a library EMA imports from there), or a directory below
    the model's in a `site-packages` or `dist-packages`, is loaded as EMA loads it.
48. **M7's numbers, one rule:** a bool is not a number, numpy's (`np.bool_`) too; nor a complex; an integer beyond a
    double's range is missing ("the function returned an integer beyond a double's range"), returned alone or in
    a mapping, never a failed call; a batch's values are read one by one as a mapping's are, never converted
    (`["1.5"]` is missing, as `{"y": "1.5"}` is).
49. **A stream file `execute` can't create** fails the run, kind `error`: "couldn't start X: stderr.txt: File
    exists"; nothing is left open. The worker that can't be started fails the call ("couldn't start the child:
    ...").
50. **AR4 lists `ema.models.collect`,** with `exclude_type_checking_imports = true` (import-linter), so its
    `TYPE_CHECKING` import of `ExecutedCall` is left out and a run-time import of `execute` would break AR4.

**Review round 2** (the findings left on steps 04 and 05; each has a test in `tests/unit/models/`)

51. **A call's reply limit grows with the call** (M8, M1, G5; amends item 39's fixed 64 MiB): `sandbox.reply_limit`
    is 64 MiB plus, per run, 640 bytes for each model prediction and one more, with each name as JSON writes it, so
    a correct batch reply of 10^7 runs is never the child's death; past it, the reason names `batch_size`.
52. **No wait for a program's exit is longer than 60 s** (`execute._MAX_WAIT_S`; M1, M20): a `timeout_s` past
    about 24.8 days overflowed `poll`'s C int (and kqueue's timespec) and raised; each wakeup checks again.
53. **Nits:** a reply line is read no more than one byte past its limit and refused as soon as it passes it; an
    `OSError` during a call's exchange says "couldn't exchange the call with the child", not "couldn't start".

## Deferrals

- **C37's sizing** (no call over `batch_size`, or over what remains approved) and its negative control: the
  runner's, step 07, about 20 test lines; the seam is `prepare`, which takes any keys. This step's C37 broken toy
  fails only the first run of a failed batch call.
- **C34's refused call and C41's stopped run through `run_new`:** step 07; this step checks `check_files` raising
  after an edit, with the first run kept, and `discard`.
- **T9's protocol stream under a scripted MCP client:** step 15; this step checks EMA's stdout stays empty.

## Questions for the owner

- **Killing a finished program's process group** (item 3): a program that starts a daemon on purpose (a license
  server) loses it at its exit. Keep, or kill only on a timeout and Ctrl-C as M20 says? Kept after review round 1;
  the proposed amendment to M20 is under "Spec edits on acceptance". What it doesn't cover: a daemon that calls
  `setsid` (or `setpgid`) leaves the group and escapes, as from any process-group kill; and **a Python function's
  leftover process isn't killed when its call ends** (not made consistent): the child is its group's leader and
  lives across calls, so killing the group would kill it; such a process lives until the child is stopped (a
  timeout, a crash, Ctrl-C, the least recently used child stopped, `close`) and could write to a run directory
  after `collect`. To make it consistent later: the worker forks per call, the fork runs the function in a
  process group of its own and replies through a pipe, and the worker kills that group when the call ends; about
  40 lines in `_worker.py` (`_call` is the seam), a fork per call (milliseconds), and module state no longer
  carried from one call to the next.
- **Size** (review round 1): the fixes take `ema.models` to about 1,341 code lines, over §11's 1,323 by about 18
  (the interrupt hold, exits seen without reaping, the reply checked again in EMA, the worker's stream restore).
  Accept a budget of 1,360, or have them trimmed?
- **A JSON string holding a number** (item 30) is read as the number, as v1 did; should only JSON numbers be read?

## Spec edits on acceptance

- **`architecture.md` §5:** `prepare`'s `approval_id` keyword; `ExecutedCall.run_errors`; `collect.py`'s `kept`,
  `keep_or_remove`, `discard`, `stderr_tail`; `sandbox.py`'s `find_program`, `Child`, `START_TIMEOUT_S`;
  `processes.py`'s `child` and `MAX_CHILDREN`; `parsers.py`'s `read` and `read_inside`; `files.py`'s `write_own`.
- **`architecture.md` §5 (review round 1):** `sandbox.py`'s `InterruptHeld`, `has_exited`, `kill_group`,
  `readable`, `MAX_REPLY_BYTES`, and `Outcome.time_s`; `read_inside`'s `last`; AR4's sources with `collect` and
  `exclude_type_checking_imports`.
- **`architecture.md` §5 (review round 2):** `sandbox.py`'s `reply_limit`.
- **`model_interface.md`:** A run: a batch call's listed files are in its batch directory; Command line: a
  program's process group is killed at its exit (if item 3 is kept). **M20, proposed:** "A command runs without
  a shell, in its own process group, which a timeout, Ctrl-C (also while the program starts), or the program's
  exit kills whole; a process that leaves the group (`setsid`) is not EMA's to kill. A Python function's child is
  killed with its group on a timeout, a crash, or Ctrl-C; a process the function leaves running lives until its
  child is stopped." Test: as now, and a program that leaves a background job: it is gone after the run.

## Alternatives considered

- **The child's start counted in the call's timeout:** one number, but a short `timeout_s` would fail every call of
  a model that imports a large library.
- **Importing the function file by its path (v1's `_load_file`):** works without packages, but relative imports
  fail at run time, against M17's check (0069 item 34).
- **`json` for the child's first message:** simpler, but `json` would be imported before `sys.path` is replaced.
- **Listed files in each run directory of a batch:** each run directory self-contained, but the function runs in
  the batch directory and reads its files there; copying them into every run directory too costs a copy per run.
- **`ExecutedCall` in a module of its own:** `collect` could import it at run time, but architecture §5 places it
  in `execute.py`, and a type-only import keeps AR4's contract exact.

## Consequences

- **Size:** `ema.models` is 1,210 code lines (without docstrings, comments, and blanks) against §11's 1,323; this
  step's part about 908 against the roadmap's 1,160 (640 + 520). After review round 1, about 1,341 (over by about
  18: a question above); this step's part about 1,040, within the roadmap's 1,160.
- **Tests:** the fast tier gains about 10 s on this machine (the model contract about 7 s: process starts,
  timeouts, Ctrl-C); the coordinator should measure the merged fast tier against the 30 s budget. Review round 1
  adds about 3 s (the branch's fast tier about 26.5 s here, on a machine other agents share).
- **For step 07:** `run_new` calls `check_files`, `prepare(..., approval_id=)`, `execute`, `collect`, stores the
  runs, then `keep_or_remove`; on Ctrl-C, `discard` and re-raise. `ModelProcesses` is the workspace's.
