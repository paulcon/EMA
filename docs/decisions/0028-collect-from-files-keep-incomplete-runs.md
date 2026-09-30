# 0028. Collect every run from files, and keep the run directories of incomplete runs

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 4; details of 0015 and 0020).

## Context

Record 0015 splits a run into three phases (prepare, execute, collect), with only file-based, serializable
data between them, so a later executor can replace *execute* alone. Record 0020 keeps each run's directory,
and lets the model spec limit what is kept to "only those of failed runs", or none.

Since then, record 0022 has let a run read some of its model predictions and not others; a failed run is now
one that read none. Record 0026 runs every Python model in a long-lived child process, whose reply could go to
*collect* in memory. Neither record says what happens to the directory of a run stopped partway (Ctrl-C),
which 0015 doesn't store.

## Decision

- **Collect from files, for both kinds of model.** A Python function's *execute* writes the model predictions
  it returned to `predictions.json` in the run directory; *collect* reads that file, as it reads a
  command-line model's model output through its output parsers.
- **Streams per run.** A Python function's stdout and stderr go to `stdout.txt` and `stderr.txt` in its run
  directory for the length of its call, as a command-line program's do.
- **The keep setting's middle value is `incomplete`:** a run directory is kept when the run failed, or when any
  of its model predictions is missing (0022). The setting's values are `all` (the default), `incomplete`, and
  `none`.
- **A stopped run's directory is deleted.** A run stopped partway is not stored (0015), so its directory is
  removed; the rerun makes a new run, with a new id and directory.

## Alternatives considered

- **A Python function's result in memory:** one file fewer per run, but two ways to collect, and a later
  remote executor would add the file anyway.
- **One log per child:** simpler for the child, but a run's messages mixed with the others'.
- **Keep only failed runs' directories (0020's words, under 0022's definition):** a run with one model
  prediction missing would lose the model output that explains why.
- **Keep a stopped run's directory, marked stopped:** shows what a hanging program wrote, but it is a directory
  the store doesn't know. A hang is seen through the timeout instead, whose run is stored as failed, with its
  directory kept.

## Consequences

- **Record 0020** (accepted) is refined, not superseded: its setting "only those of failed runs" is named
  `incomplete`, and covers runs with any model prediction missing.
- **`../design/model_interface.md`:** "A run" section: the three phases, the files of a run directory, the keep
  setting's values.
- **`../design/contracts.md`** (step 7): each keep value, with a failed run, a run with one model prediction
  missing, and a complete run; a stopped run leaves no directory; `predictions.json` is the only way a Python
  function's model predictions reach the store.
