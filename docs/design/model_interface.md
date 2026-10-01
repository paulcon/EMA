# Model interface

**Status:** accepted. **Updated:** 2026-09-30. **Depends on:** OD-3 (0003, 0005), OD-6 (0014), OD-9 (0022),
OD-10 (0023), OD-11 (0026), OD-20 (0027); records 0015, 0020, 0021, 0024, 0025, 0028, 0029, 0030, 0031.

> The hardest thing to change later. This spec says what a model is to EMA: what it takes, what it returns,
> how it fails, and what makes a new version. It was written from an interview on 2026-09-30 (TODO step 4).
> `architecture.md` §3 and §5 have stubs for `ModelParameter`, `ModelSpec`, `Model`, and the adapters, which
> step 9 brings in line with this spec.

## The model spec

- **A JSON file,** `model.json` by convention. Relative paths in it resolve against its own directory, the
  model's directory. EMA reads and writes it with the standard library (the MCP server's `save_model`, 0016).
- **Names:** a model's name is lowercase letters, digits, `_`, and `-`. Model parameter and model prediction
  names are Python identifiers, unique across both lists, so they work as keyword arguments and in templates.
- **The model version id** is `name@` and the first 12 hexadecimal digits of the version hash; the store keeps
  the full hash.
- **`noisy`** is allowed only as `false` (the default); `noisy: true` is refused at loading, with a message
  that models declared noisy come in a later version (0021).
- **No run-time field:** the price's time comes only from stored run durations, and is "unknown" without them
  (P3).

A command-line model (U2's heat solver):

```json
{
  "name": "heat",
  "description": "2-D steady heat conduction in a plate",
  "interface": "command_line",
  "command": ["./heat_solver", "plate.in"],
  "input_decks": [{"template": "plate.in.template", "writes": "plate.in"}],
  "files": ["heat_solver", "solver.cfg", {"path": "mesh.dat", "shared": true}],
  "env": {"OMP_NUM_THREADS": "4"},
  "parameters": [
    {"name": "k", "units": "W/(m K)", "nominal": 45.0, "description": "thermal conductivity",
     "limits": {"gt": 0}},
    {"name": "q", "units": "W/m^2", "nominal": 3e4, "description": "heat flux"}
  ],
  "predictions": [
    {"name": "T_max", "units": "K", "description": "peak temperature",
     "parser": {"kind": "regex", "file": "plate.out", "pattern": "T_max = (\\S+)"}}
  ],
  "timeout_s": 600,
  "keep": "incomplete"
}
```

A Python function model (U1's beam):

```json
{
  "name": "beam",
  "description": "tip deflection of a cantilever beam",
  "interface": "python_function",
  "function": "beam.py:deflection",
  "parameters": [
    {"name": "E", "units": "Pa", "nominal": 2e11, "description": "Young's modulus", "limits": {"gt": 0}},
    {"name": "L", "units": "m", "nominal": 1.5, "description": "length", "limits": {"gt": 0}},
    {"name": "P", "units": "N", "nominal": 3e3, "description": "tip load"}
  ],
  "predictions": [{"name": "delta", "units": "m", "description": "tip deflection"}]
}
```

## What a model takes

- **A model parameter** has a name, units, a description, a nominal value, and optional limits (0024). It
  has no scale: a design's model parameter space says which model parameters are spread in their logarithm.
- **Limits** (0024): a lower and an upper value outside which the model isn't defined; either may be left
  out, and each may be strict or not (`gt`, `ge`, `lt`, `le`). The nominal value is inside them. A space that
  crosses a limit is refused when its design is built, so no run is refused at its point.
- **Continuous only:** every model parameter takes real values (0024).
- **Held model parameters** (0023): a variable the analyst usually doesn't vary (a mesh size, a solver
  tolerance) is an ordinary model parameter, with its nominal value. A design whose model parameter space
  leaves it out holds it at its nominal value. The model spec has no separate list of fixed values or
  constants.
- **A point is complete:** it has a value for every model parameter, held ones included, and runs are keyed by
  the complete point (P3).
- **Non-numeric settings** (a solver's name, a scheme) stay literal in the model's files, which the model
  version covers.
- **Files** (0030): the files a run needs, listed in the spec, for both kinds of model. Each is copied into
  every run directory, keeping its relative path; a file marked `"shared": true` (a large mesh) is stored once,
  read-only, at `<workspace>/files/<sha256>/<name>`, and linked into every run directory instead. A stored
  copy never changes: editing the source makes a new model version and a new copy. A model that writes to a
  shared file fails with a permission error. All listed files are tracked (Versions).

## What a model returns

- **Model predictions** (0021, 0022): a model spec lists one or more, each a scalar with a name, units, and a
  description (and, for a command-line model, its output parser). One run produces all of them.
- **Per model prediction:** a run keeps the model predictions it read. One it couldn't read is NaN, with its
  own reason; a run with none read is a failed run.
- **One per diagnostic evaluation:** a diagnostic evaluation analyzes one model prediction, named by
  `prediction=` (optional when the model has one), and counts a run as not usable when that model prediction
  is missing (P6).

## Interfaces

### Python function

- **Found by** `"function": "file.py:f"`: a file relative to the model's directory, and a function in it
  (0014). The file is tracked. Code in an installed package is reached through a short wrapper file. The
  function's file and its local imports are imported from the model's directory; listed files are copied or
  linked into the run directory (0030).
- **Called** as `f(**x)`, with one keyword float per model parameter, held ones included (0023), and with the
  run directory as its working directory (0020).
- **Returns** a float when the model has one model prediction, or a mapping from model prediction names to
  floats when it has several. A name missing from the mapping, or a non-finite value, is a missing model
  prediction (0022); names the spec doesn't list are ignored.
- **Batch** (0025): with `"batch": true`, the function is called as `f(X)`, with `X` an (n, d) array whose
  columns follow the spec's order of model parameters, and returns an (n,) array, or a mapping of names to
  (n,) arrays. At most `batch_size` points per call (by default, all of a design's new runs; not part of the
  model version). Each run keeps its own run directory; the call runs in a batch directory beside them. A
  non-finite value at one point is a missing model prediction for that run; an exception, a timeout, or a
  wrong shape fails every run in the call. Each run records the call's time divided by its size, and the
  call's size and time. A call's runs are counted against the approval when it starts (0015).
- **Isolated** (0026): every Python model runs in a child process, one long-lived child per model version,
  with a scrubbed environment (`trust.md`), stdin from `/dev/null`, and a timeout on every call. What the
  child returns is JSON, or arrays in a format that runs no code; never pickle. On a timeout, a crash, or
  Ctrl-C, the child is killed, and the next call starts a new one. No in-process option, and no memory or CPU
  limits in v2.0. A function shouldn't keep state between calls; the add-a-model guide says so.

### Command line

- **Command:** a list of strings, run without a shell, with the run directory as its working directory. A
  shell is used only when the spec says so (`["sh", "-c", "…"]`). stdin is `/dev/null`; the program runs in
  its own process group, which EMA kills on a timeout or Ctrl-C.
- **Input decks:** one or more, each a template file and the name it is written to in the run directory
  (relative, with no `..`). Templates use Python's `string.Template`: `$k` or `${k}` for a model parameter,
  `$$` for a literal `$`. A name that isn't a model parameter is refused when the model is loaded.
- **Numbers** are written by one fixed rule: the shortest decimal that reads back as the same double
  (`0.1` → `0.1`), and a whole number with no decimal point (`64.0` → `64`). The program reads exactly the
  point's value. There is no number-format field.
- **Files:** as in "What a model takes": copied, or shared and linked (0030). The program itself may be one of
  them. A program found on `PATH` or given by an absolute path is neither copied nor tracked (Versions).
- **Environment:** the scrubbed environment (`trust.md`), plus the spec's `env` mapping, which is part of the
  model version. The program is told nothing else: no replicate number and no run id.
- **Output parsers** (0027): each model prediction has one, of three kinds, each returning one scalar:
  `regex` (`file`, `pattern` with one group or a group named `value`, `match` first or last, default last),
  `json` (`file`, a dotted `key` whose integer parts index lists), and `csv` (`file`, `column` by header or
  index, `row` default `-1`, optional `delimiter`). `file` is relative to the run directory, or `stdout` or
  `stderr`. A parser that finds no file, match, or key, or reads a value that isn't a finite number, makes
  that model prediction missing, with a reason. Anything else is read by a wrapper script that writes JSON.

## A run

- **Prepare** makes the run directory, `<workspace>/runs/<run id>/`, and writes into it everything the run
  needs: the point; for a command-line model, the input decks; for both kinds, the listed files, copied or
  linked to their stored copies (0030). The directory is self-contained, or linked to read-only copies in the
  workspace.
- **Execute** runs the model there: the command, or a call to the Python function in its child (0026). Its
  streams go to `stdout.txt` and `stderr.txt`. A Python function's returned model predictions are written to
  `predictions.json` (0028).
- **Collect** reads the model predictions from files only: the output parsers for a command-line model,
  `predictions.json` for a Python function. It returns the run's record: the point, the command and its
  program's resolved path, the exit status, the model predictions and their reasons, the timing, and the host
  (0015, 0029). The record is also written to the run directory as `run.json`.
- **A batch** (0025) is prepared, executed, and collected as one call, in a batch directory beside its runs'
  directories.
- **Kept** (0020, 0028): the model spec's `keep` setting is `all` (the default), `incomplete` (runs that failed
  or have any model prediction missing), or `none`. It is not part of the model version. A directory not kept
  is deleted after collect. EMA never changes a run directory after its run.
- **Stopped:** a run stopped partway (Ctrl-C) is not stored, and its directory is deleted (0028).

## Failures

- **Never raised.** A failure at a point is a run's record, never an exception out of the adapter (M1).
- **Status:** a run is `ok` when it read at least one model prediction (a missing one has its own reason,
  0022), or `failed`, with one of three kinds:
  - `error`: the Python function raised, or its child died; or the program exited with a nonzero code or a
    signal, or couldn't start. A nonzero exit is a failure even when the model predictions can be read.
  - `timeout`: the call ran past `timeout_s`.
  - `unread`: the call finished cleanly, but none of its model predictions could be read.
- **Timeout:** `timeout_s` in the model spec, 3600 s by default, for each call (a run, or a batch, 0025).
- **Reason:** one line (`exited with code 2`, `ZeroDivisionError: division by zero at beam.py:14`,
  `timeout after 600 s`, `plate.out: pattern not found`), plus the last 15 lines of stderr, or of the
  traceback. It is stored with the run, so a failure can be understood when its run directory isn't kept; the
  full streams are in the run directory when it is.
- **Reports** count failed runs by kind (U3); `failed_runs` gives each one's point, kind, and reason.
- **Reuse:** a failed run is stored, and reused unless the user asks to retry (0010).

## Versions

- **Covered** (0029): the whole model spec except its location and the settings `keep`, `batch_size`, and
  `timeout_s`, plus the contents of the tracked files: the Python function's file, the input deck templates,
  and the files the spec lists. Descriptions, units, nominal values, limits (0024), and `shared` marks (0030)
  are covered.
- **Warned:** at loading, an import in the function's file that resolves to an unlisted file in the model's
  directory.
- **Not covered:** modules found elsewhere, installed packages, and programs on `PATH` or given by an absolute
  path. Each run records its program's resolved path and its host (0015); the first approval for a model
  version shows the path.
- **Platforms** (0015's open question, for v2.0): a program copied as a model file is tracked, so another
  build is another model version; a program outside the model's files is the same version on every machine.
- **Checked before each call:** the tracked files are hashed in full before every call, about 1 s per GB; a
  call whose model version no longer matches is refused, naming the file (U6).
- **Not in the model:** the model parameter space and scales belong to the design (0005, 0024).
- **Settings** (`keep`, `batch_size`, `timeout_s`) are stored with the model; the latest loading's values
  apply.

## Requirements

> Numbered, so tests and code can cite them. The tests belong to the model adapter contract
> (`contracts.md`, step 7), run over both kinds of model and over a batch model where it applies.

| Id | Requirement | Test |
|---|---|---|
| M1 | A failure at a point is a run's record: status `failed`, a kind, a reason, and NaN model predictions; the adapter never raises for a point. | A function that raises, a program that exits 2, a child killed by a signal, and a timeout each give a record of the right kind. |
| M2 | Model code gets stdin from `/dev/null` and no variable from `.env`. | A model that reads stdin gets end of file; one that writes its environment lacks a variable set in `.env`. |
| M3 | Editing a tracked file, or a covered field of the spec, changes the model version; moving the model's directory, or changing `keep`, `batch_size`, or `timeout_s`, doesn't. | One byte changed in each kind of tracked file; each field changed in turn; the directory moved. |
| M4 | Each model prediction is read, or missing with its own reason; a run is failed only when none is read. | A command-line model with two parsers, one of which finds nothing: the run is `ok`, with one NaN and its reason. |
| M5 | A model receives a value for every model parameter, held ones included. | A space that names one of three model parameters: the function receives all three, two at nominal. |
| M6 | A space that crosses a limit is refused before any run, naming the model parameter and the limit. | `k` in (−1, 10) with `gt: 0`: refused, and no run made. |
| M7 | A Python function returns a float, or a mapping by name; a missing name or a non-finite value is a missing model prediction; extra names are ignored. | Returns of `1.0`, `{"a": 1.0}`, `{"a": nan}`, and `{"a": 1.0, "zz": 2.0}`. |
| M8 | A batch model gives the same model predictions as the same function called one point at a time; a non-finite row is missing for that run only; an exception, a timeout, or a wrong shape fails every run in the call; no call holds more than `batch_size` points, or more than remain approved. | A vectorized reference model, both ways; a batch with one NaN row; one that raises; `batch_size` 3 over 10 points. |
| M9 | Every Python model runs in its own child; a timeout, a crash, or Ctrl-C kills it, and the next call starts a new one; nothing is unpickled. | A function that sleeps past `timeout_s`; one that calls `os._exit`; Ctrl-C during a call leaves no child process. |
| M10 | A template name that isn't a model parameter is refused at loading; `$$` writes `$`; every value is written so that it reads back as the same double, and whole numbers have no decimal point. | Templates with `$nope` and `$$`; values 0.1, 1e-300, 64.0, and −2.5 read back with `float()`. |
| M11 | Each output parser kind reads its known answer, and makes the model prediction missing, with a reason, when it finds no file, no match, or no key, or a value that isn't a finite number. | One fixture file per kind, and one per way to fail. |
| M12 | A nonzero exit fails the run, even when the model predictions can be read. | A program that writes a good `plate.out` and exits 1. |
| M13 | Collect reads model predictions only from files: output parsers, or `predictions.json`. | A Python function's run directory holds `predictions.json` with the stored values. |
| M14 | `keep` keeps all, incomplete, or no run directories as stated; a stopped run leaves no run directory. | Each value, over a complete run, a run with one missing model prediction, and a failed run; Ctrl-C during a run. |
| M15 | A shared file is stored once, read-only, and linked into each run directory; a write to it fails the run; editing the source makes a new model version and a new stored copy, and older run directories still point to the old one. | Ten runs with a shared file: one stored copy; a model that writes to it; an edit between two evaluations. |
| M16 | The tracked files are hashed before every call; a call after a change is refused, naming the file. | Edit a tracked file between two calls of one evaluation: the second is refused; the first's run is kept. |
| M17 | Loading warns about an import in the function's file that resolves to an unlisted local file. | `beam.py` imports `helper.py`, not listed: one warning naming it. |
| M18 | `noisy: true` is refused at loading. | A spec with `noisy: true`. |
| M19 | Each run records its host and its program's resolved path. | A command found on `PATH`: the record holds its absolute path. |
| M20 | A command runs without a shell, in its own process group, which a timeout or Ctrl-C kills whole. | A command whose argument holds `;` is passed literally; a program that starts a child and sleeps: both are gone after the timeout. |


## What this spec asks of other documents

- **Use cases** (accepted): U2's model spec example follows this spec (updated 2026-09-30).
- **Designs (step 5):** a space may name a subset of the model parameters, with a scale for each; spaces that
  cross limits are refused; whether a zero-width range holds a model parameter at another value (0023, 0024;
  answered by 0033: a held value, not a zero-width range).
- **Contracts (step 7):** the model adapter contract, from M1–M20.
- **Data model (step 8):** model predictions keyed by run and name, each with a reason (0022); a run's failure
  kind, reason, host, program path, and batch (0025, 0029); settings stored with the model; stored shared
  copies (0030).
- **Architecture (step 9):** `ModelParameter` (limits, no scale), `PredictionSpec`, `ModelSpec` with one
  dataclass per interface, the three phases in place of `Model.evaluate`, and `RunStatus` without
  `INVALID_INPUT` or `TIMEOUT` as statuses (a failure kind instead).
- **Trust (step 10):** the scrubbed environment; the stored copies written read-only; never following a link
  out of a run directory when reading model output (0030).
- **Guides (step 13):** the add-a-model guide: the JSON wrapper for other model output, stateless functions,
  helper files to list, shared files.
