# 0026. Run every Python model in an isolated child process

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** OD-11.

## Context

A Python model is arbitrary code. In EMA's own process it can read EMA's environment (the API keys in `.env`),
hang with no timeout, crash EMA, or change EMA's working directory; record 0020 has it run with its run
directory as the working directory. Record 0015 says only the main process writes the store, and a child
process runs the model and returns its record. A command-line model already runs as its own process.

v1 ran Python models in-process unless `execution.isolate` was set; models its agent saved were isolated by
default. Its isolated child (`../../../EMA-v1/src/ema/core/models/_sandbox.py`, `_worker.py`, 534 lines) is a
long-lived process per model version: a scrubbed environment, stdin from `/dev/null`, JSON lines over its own
pipes with a sequence number per message, never pickle, and the child killed on any exception during an
exchange, Ctrl-C included. Measured in v1 (`../../../EMA-v1/docs/guides/python_models.md`): about 0.1 s to
start the child, once per model version; one pipe round trip per call; 5,120 runs of Ishigami took 5.3 s
in-process and 6.5 s isolated. In-process, v1 needed workarounds to run new code after an edit (re-importing
changed modules, compiling from source rather than a stale `.pyc`).

v1's memory and CPU limits relied on a watchdog on macOS, which can't cap a process's address space.

In v2.0 the agent writes no model code (0016), so "isolate only what the agent writes" has nothing to cover.
Scope lists `_sandbox.py` and `_worker.py` as "port, after re-review", with OD-11 deciding how they are used.

## Decision

We will run every Python model in an isolated child process. There is no in-process option.

- **One long-lived child per model version**, started on the first call, and stopped when EMA is done with
  the model or the process exits. A new model version gets a new child.
- **Isolated:** the child gets a scrubbed environment (which variables, `trust.md`, step 10), stdin from
  `/dev/null`, and the run directory (or the batch directory, 0025) as its working directory for each call.
  What it returns is JSON, or arrays in a format that runs no code; never pickle.
- **A timeout on every call** (its default and whether it is part of the model version: items 9 and 10 of the
  step 4 interview). On a timeout, a crash, or Ctrl-C, the child is killed, and a new one is started for the
  next call.
- **No memory or CPU limits in v2.0.**
- **Functions shouldn't keep state between calls.** A function that does (a cache in a global) could make its
  model predictions depend on the order of runs. The add-a-model guide says so; the point run's repeats show
  such a dependence as measured variation (P7, 0011).

## Alternatives considered

- **Isolated by default, with an opt-out field:** in-process runs for a debugger or a profiler, but the
  opt-out has no timeout, reads EMA's environment, and can crash EMA; and there are two paths to test. The
  analyst can debug by calling the function directly, outside EMA.
- **In-process by default (v1):** the fastest start, but the common path has no timeout and sees EMA's
  secrets, and v1 needed re-import and `.pyc` workarounds.
- **Only models the agent writes:** the agent writes none in v2.0 (0016).
- **A fresh process per call:** no state carries between calls, and no child lifecycle to manage, but each
  call pays about 0.1–0.3 s to start Python and import NumPy: U1's 200 runs would take about 30 s instead of
  0.2 s, unless the model uses `batch` (0025).
- **Memory and CPU limits (v1's `memory_mb` and `cpu_s`):** catch accidents only, and on macOS only through a
  watchdog. Later: about 50 lines from v1's `_worker.py`, with no seam needed now.

## Consequences

- **`../design/model_interface.md`:** the Python function section says the function runs in the child, with
  its run directory as the working directory; no `isolate` field.
- **`../design/principles.md`** (accepted): the held candidate "User code runs isolated, without EMA's
  secrets" no longer waits on OD-11; it is decided with `trust.md` (step 10).
- **`../design/trust.md`** (step 10): the scrubbed environment; the rule that a child's output is never
  unpickled; `_sandbox.py` and `_worker.py` re-reviewed and ported (scope), without v1's limits.
- **`../design/contracts.md`** (step 7): the model adapter contract: a function that reads a variable from
  `.env` doesn't see it; a function that hangs is stopped at its timeout and recorded as failed; a function
  that kills its process (`os._exit`) fails only its run, and the next run starts a new child; Ctrl-C during a
  call leaves no child behind.
- **U1:** 200 runs of a millisecond function take a fraction of a second more than in-process.
- **`../../STATUS.md`:** OD-11 moves to "Decided", naming this record, when it is accepted (0001).
