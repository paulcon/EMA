# 0020. Keep each run's model output in its run directory, for inspection outside EMA

**Date:** 2026-09-29. **Status:** accepted; its keep values amended by 0028. **Resolves:** none (TODO step 3, scope).

## Context

The glossary (0003) separates model output, "anything a run produces: a Python function's return value, or
the files, logs, and streams a command-line program writes", from the model predictions an output parser reads
from it. Record 0015 gives each run its own run directory. No spec says whether that directory is kept, where it
lives, or how the analyst finds it.

An analyst who reads a diagnostic result may want to look at the rest of a run's model output by hand: the
fields, logs, and files behind a surprising model prediction, or the solver's messages behind a failed run
(U3). v1 kept every run directory under the workspace at `runs/<run id>/`, with the rendered input deck, the
copied files, the captured streams, everything the program wrote, and a record of the run, "so a surprising
result can be traced back to exactly what the program saw" (`../../../EMA-v1/docs/guides/input_deck_model.md`).
v1's run directories were about 2 kB each for its test models; a real simulation code can write gigabytes per
run.

## Decision

We will keep each run's model output in its run directory, for the analyst to inspect outside EMA.

- **Every run has a run directory, and runs in it:** a command-line model's command runs there, and a Python
  function runs with it as its working directory. A Python function's model predictions still come from its
  return value.
- **Kept by default.** The model spec may limit what is kept: all run directories (the default), only those of
  failed runs, or none. This setting doesn't decide what a run does, so it is not part of the model version
  (P3).
- **One place:** `<workspace>/runs/<run id>/`. It holds what the run saw and wrote, and a record of the run (the
  point, the command, the exit status, and the timing).
- **Found by a lookup:** a workspace function and a CLI command give a run's directory, from a run id or from a
  diagnostic result and a point. `failed_runs` and the runs CSV export (U5) show each run's directory too.
- **EMA reads only model predictions from it,** through the output parser, and never changes a run directory
  after its run. The rest of the model output is the analyst's to read; numbers taken from it by hand are
  outside P1.
- **Deleting a run directory loses nothing EMA needs:** the store holds the model predictions, and a stored
  run is reused whether or not its directory is kept. A reused run points to the directory of the run that
  made it.
- **Exports leave run directories out** by default (U5); copying a workspace copies them (U8).

## Alternatives considered

- **Always keep all, with no setting (v1):** the simplest, but a simulation code writing large fields fills
  the disk, and the analyst's only remedy is deleting by hand.
- **Keep only failed runs' directories:** explains failures and saves disk, but the analyst can't look behind
  a successful run's model prediction.
- **Delete every run directory:** the least disk, but model output is lost, and failures can't be traced.
- **A fixed layout with no lookup:** no new public name, but the analyst must map a point in a report to a
  run id by hand.

## Consequences

- **`../design/scope.md`:** "In v2.0" lists kept model output and the lookup.
- **`../design/model_interface.md`** (step 4): the keep setting; what a run directory holds; a Python function
  runs in its run directory.
- **`../design/data_model.md`** (step 8): each run's directory path, and whether it is kept.
- **`../design/architecture.md`** (step 9): the lookup, in `ema.workspace` and the CLI, counted against the
  budgets of public names and CLI commands; `failed_runs` and `export` show the path.
- **`../design/trust.md`** (step 10): EMA never runs anything from a kept run directory.
- Deleting kept run directories to free disk (a clean-up command) is not in v2.0; the analyst deletes them by
  hand.
