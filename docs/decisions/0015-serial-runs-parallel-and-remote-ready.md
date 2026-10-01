# 0015. Run one model run at a time in v2.0, ready for parallel and remote runs later

**Date:** 2026-09-29. **Status:** accepted; its run-at-a-time wording amended by 0025; its platform question by 0029; its shared files by 0030. **Resolves:** none (TODO step 3, scope).

## Context

A slow simulation code takes hours for one diagnostic evaluation run serially (U2: 96 runs of about 2 minutes,
about 3 h 12 min). Local parallel runs would shorten that on a multicore computer, and remote or cluster runs
may be needed one day.

v1 ran models with joblib behind an `Executor` interface, "the extension point" for remote runs, which never
came (`../../../EMA-v1/src/ema/core/scheduler.py`, 232 lines; `../notes/v1/lessons_learned_2026-09-27.md`
§9). Several of v1's bugs lived in its own execution code, including the sandbox after Ctrl-C (§9). The
architecture draft (`../design/architecture.md` §6) has an `Executor` protocol with `SerialExecutor` and
`ProcessExecutor`, and `Model.evaluate(X, replicate)` (§5) prepares, runs, and parses a run in one call.

Estimated effort, discussed on 2026-09-29:

- **Local parallel runs**, added later to a serial scheduler that keeps the rules below: one small build step,
  about 100–200 source lines and their tests. When every run already runs in a child process, the standard
  library's `concurrent.futures` is enough, without joblib.
- **Remote or cluster runs:** the executor itself is small (200–400 lines on a library such as `submitit` or
  Parsl), but the feature is several build steps, perhaps 1,000–2,000 source lines, with decisions in the model
  interface, data model, and trust specs: runs that outlive EMA's process, copying files to and from another
  machine, a binary built for another platform being a different model version (P3), credentials, run
  durations per machine, and new transient failures (0010).

## Decision

We will run one model run at a time in v2.0, and keep the design ready for local parallel runs and for remote
runs, without building either.

The later specs provide:

1. **Only the main process writes the store.** A child process runs the model and returns its record.
2. **Runs are counted against the approval when they start**, not when they finish, so the scheduler never
   starts more new runs than were approved (P3).
3. **Each run has its own run directory.**
4. **A diagnostic result doesn't depend on the order in which runs finish:** runs are read from the store in
   the design's order (P4).
5. **A run has three phases:** *prepare* builds a self-contained run directory (the input deck, the model's
   files, the command); *execute* runs it; *collect* reads the model predictions and returns the run's record.
   Only file-based, serializable data passes between the phases, so a later executor replaces *execute* alone
   (step 4, step 9).
6. **Each run records where it ran** (the host), for provenance and for run durations per machine later (step
   8).
7. **The model interface leaves open** whether one model on two machines (a binary built for each) is one
   model version (step 4).

v2.0 has no executor interface: the runner is a serial loop that calls *execute*. A diagnostic evaluation that
is stopped is finished by running the same request again, which reuses the stored runs (U2); a later
asynchronous executor can use the same pattern, with runs still in progress kept in their own table, apart
from the stored runs (which are written once, with their final status).

## Alternatives considered

- **Local parallel runs in v2.0:** faster slow simulators, but the price, interruption, and isolation must
  account for workers from the first build step, and the parallel and serial paths both need tests.
- **Serial, with no provision:** the least writing now, but a serial loop that writes, counts, and handles
  interruption in one place is the costly retrofit.
- **An executor interface now** (v1, and the architecture draft): an extension point for a feature that may
  not come, which v1's lessons warn against.

## Consequences

- **`../design/scope.md`:** "In v2.0" says runs are serial; "Not in v2.0" lists local parallel runs and remote
  or cluster runs, each as later; the rules above are listed for the later specs.
- **`../design/model_interface.md`** (step 4): a run's three phases, and the open platform question.
- **`../design/data_model.md`** (step 8): the host of each run.
- **`../design/architecture.md`** (step 9): §6 drops the `Executor` protocol, `SerialExecutor`, and
  `ProcessExecutor`; `Model.evaluate` is split into the three phases.
- **`../design/contracts.md`** (step 7): tests that the approval cap counts at start, that an interrupted
  evaluation keeps its finished runs, and that results don't depend on the order runs finish.
- Adding local parallel runs later is a decision with its own record, and one small build step.
