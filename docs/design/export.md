# Export

**Status:** accepted. **Updated:** 2026-10-01, from an interview; the MCP root by 0057. **Depends on:** 0050, 0053, U5, P5,
C17; records 0015, 0020, 0022, 0025, 0029, 0046.

> What `export` writes, so an analyst can use a diagnostic result's runs in another tool, and how reading it
> back gives the same values bit for bit. Written before the data model (TODO step 8), which stores what an
> export reads (0050).

## What an export holds

- **One diagnostic result:** `export(result_id, directory)` (U5). It holds the runs that result used, its
  design, and the result with its provenance. There is no export of a model version's runs without a result:
  to get every run, export the result of the largest design.
- **Every run of the design,** in design order, failed and unusable runs included, each with its status, kind,
  and reason, so the export shows what the diagnostic saw (U3).
- **One row per design row.** A design that repeats a point (U2's coordinate lines: 102 rows, 97 runs) has
  102 rows; the rows of one run share its run id.
- **Every model parameter is a column,** held ones included with their value, so every row is a complete
  point (0023) that another tool can run again.

## Files and columns

- **The directory** holds `runs.csv` and `result.json` (U5) at the top, and `report/`: a copy of the result's
  report, its PNGs, and their data cards, laid out as in the workspace so the report's links work. It can be
  shared as it is.
- **`runs.csv`:** one row per design row, in design order. Columns, in this order:
  - EMA's, each named with the prefix `ema_`, so no model's name can collide with them (a model parameter or
    model prediction name may not start with `ema_`):
    - `ema_row`: the design row, from 0;
    - `ema_run_id`;
    - `ema_replicate`;
    - `ema_status`: `ok` or `failed`;
    - `ema_kind`: `error`, `timeout`, or `unread`, empty when ok;
    - `ema_reason`: the one-line reason, empty when ok;
    - `ema_new`: `true` when the result's own diagnostic evaluation made the run, `false` when it reused a
      stored one;
    - `ema_time_s`: the run's time (a batch call's share, 0025);
    - `ema_run_dir`: the kept run directory's path, empty when not kept (0020);
    - `ema_host` (0015);
    - `ema_program`: the resolved program path (0029).
  - Every model parameter, by name, in the model spec's order, in model parameter units (held ones included).
  - Every model prediction, by name, in the model spec's order (0022).
  - `ema_missing`: each model prediction missing from an `ok` run, with its reason, in the model spec's order
    (`z: plate.out: pattern not found`), joined by `; `, a `;` inside a reason written as `,`; empty when every
    model prediction was read, and for a failed run.
- **`result.json`** (strict JSON, C17):
  - `export_format`: 1;
  - the design: its request in `../designs.md`'s JSON form (kind, space, generator parameters, seed, sampler
    and its version) and its model version id (0046);
  - the model version's spec, as JSON, without its location;
  - a column dictionary: for each column of `runs.csv`, its kind (EMA, model parameter, model prediction),
    units, and description, and for a model parameter its scale and range in this design's space;
  - the diagnostic result with its provenance, as stored (P5, C17).
- **Numbers** are written as `%.17g`: 17 significant digits, which read back exactly (0.1 is
  `0.10000000000000001`). Measured on 300,000 doubles over 10^±300, both Python's `float()` and
  `numpy.loadtxt` give every value back bit for bit; 15 digits give 7%.
- **A missing value** (a failed run's model predictions, a model prediction not read) is an empty cell, which
  pandas, R, and spreadsheets read as missing.

## Reading it back

- **The format is the promise.** EMA has no reader for an export. Python's `csv` and `float()`, and `json`,
  read it back: the same model parameter values and model predictions bit for bit, and the same diagnostic
  result and provenance (U5). With pandas: `pd.read_csv(path, float_precision="round_trip")`; its default
  parser isn't guaranteed to read every double exactly.
- **An existing directory** that isn't empty is refused, naming it; an export never overwrites a file.
- **Text columns** (`ema_reason`, `ema_missing`) are not escaped for spreadsheets: a cell that starts with `=`,
  `+`, `-`, or `@` may be read as a formula there, and the run-a-diagnostic guide says to open `runs.csv` as
  data (`trust.md`).

## Interfaces

- **Python:** `ws.export(result_id, directory)` (U5).
- **CLI:** `ema export RESULT_ID DIR`.
- **MCP:** an export tool, one of the server's 10 (0016, 0053), writing only inside the directory the user named
  when starting the server, `ema mcp --root DIR`, and outside any workspace (`trust.md`, T5).

## Requirements

| Id | Requirement | Test |
|---|---|---|
| E1 | `export` writes `runs.csv`, `result.json`, and `report/` (the report, its PNGs, and their data cards) into a new or empty directory, and refuses one that isn't empty, naming it, without writing anything. | U5's `r2`, twice into one directory: the second is refused and the files are unchanged. |
| E2 | `runs.csv` has one row per design row, in design order, every run included, with the columns above in their order. | U2's coordinate lines: 102 rows, 97 run ids; U3's `r1`: 34 failed rows with their kinds and reasons. |
| E3 | Every number in `runs.csv` is `%.17g`, and a missing value is an empty cell; `csv` and `float()` read back every model parameter value and model prediction bit for bit. | U5's `r2` read back equals the stored doubles; a fixture of doubles over 10^±300, subnormals, and −0.0. |
| E4 | `ema_missing` lists each model prediction missing from an `ok` run, with its reason, in the model spec's order. | R5 with z: every run with b > 0.5 has `z: <reason>`; a reason containing `;` is written with `,`. |
| E5 | `result.json` is strict JSON holding the format version, the design, the model spec, the column dictionary, and the diagnostic result with its provenance, which loads back equal to the stored result (C17). | U5's `r2`: `json.load` gives the stored result and provenance; every `runs.csv` column has a dictionary entry. |
| E6 | `ema_new` is true exactly for the runs the result's own diagnostic evaluation made. | U5's `r2`: 120 true, 200 false. |
| E7 | The MCP export tool writes only inside the directory the user named when starting the server (`ema mcp --root`), and outside any workspace. | A path outside it, one with `..`, and one inside a workspace are refused. |

## What this spec asks of other documents

- **Data model (step 8):** what `runs.csv` reads: for each run its one-line reason apart from the stderr tail,
  its kind, time, host, program path, and run directory; for each result, which of its runs its own diagnostic
  evaluation made (`ema_new`); each missing model prediction's reason (0022).
- **Architecture (step 9):** `Workspace.export`, `ema export`, and the MCP export tool, the tenth (0016,
  0053).
- **Trust (step 10):** done (`trust.md`, 0057).
- **README:** the id prefix E.
