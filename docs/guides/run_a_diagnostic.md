# Run a diagnostic and read its report

**Status:** outline. **Updated:** 2026-10-02 (review round 1 of applying 0066–0085). **Use cases:** U1–U5, U7, U8. **Specs:** `../design/diagnostics/`,
`../design/designs.md`, `../design/uncertainty.md`, `../design/export.md`. **Tested:** through the use cases
(C53); its examples are the use cases' models.

> After the model is loaded and tested (`add_a_model.md`). Each step in Python and in the CLI. Outline now,
> full text once the code exists; `<…>` marks text to write then.

## Run one

1. **Choose a diagnostic:** the list, and each one's diagnostic parameters.

   ```python
   for d in ws.list_diagnostics():     # point run, scatter, coordinate lines, lines, linear model,
       print(d)                        # polynomial model
   print(ws.describe_diagnostic("coordinate_lines"))
   #   each diagnostic parameter: type, default, meaning, changes the design?
   ```

   ```text
   $ ema diagnostics
   $ ema diagnostics coordinate_lines
   ```

   - Which question each answers (`scope.md`, the diagnostic specs), in one line each. <…>

2. **Choose the model parameter space and the diagnostic parameters.**

   ```text
   {"k": [30, 60], "q": [1e4, 5e4], …}
   ```

   - U2's space, `space.json`: a range for each of its six model parameters (four elided here). A range is
     linear; `{"range": [1e9, 1e12], "scale": "log"}` gives a log scale (`designs.md`'s example; U2's q
     stays linear, its nominal value at the range's center); a number, such as `"h": 0.01`, holds
     the model parameter at that value (`designs.md`, JSON form; 0023, 0024). A space that crosses a model's
     limit is refused, naming it (M6). <…>
   - In Python, a dict: `{"k": (30, 60), …}`; in the CLI, a JSON file, `--space space.json`. <…>
   - Diagnostic parameters: keywords in Python (`n=17`), `--param n=17` in the CLI; the seed (0 when none is
     given, `designs.md`). <…>
   - A model with several model predictions: `prediction="T_max"`, `--prediction T_max` (one per diagnostic
     evaluation). <…>
   - The point run takes no space: it runs at the nominal point, or at `x` (U7). <…>

3. **Price it:** new runs, stored runs reused, and the time, from stored run durations (P3).

   ```text
   $ ema price heat coordinate_lines --space space.json --param n=17
     96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)
   ```

   - A design too large is refused before pricing (`DesignTooLarge`, G5). <…>

4. **Run it:** what you're asked to approve (P3).

   ```text
   $ ema run heat coordinate_lines --space space.json --param n=17
     New runs of the model version `heat@b204…`: coordinate_lines on `T_max`.
     Price: 96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)
     Approve? [y/N] y
     96/96 runs
     Diagnostic result 3f2a: coordinate_lines on heat@b204…, T_max; 97 runs: 96 new, 1 reused, 0 failed;
     report: ema report 3f2a
   ```

   - The question shows the model version and the price; the first approval for a model version also shows
     what will run (`add_a_model.md`). A no makes no run (`ApprovalDeclined`). <…>
   - Unattended (a scheduler, `nohup`): `--yes` approves the price in advance; it is still priced, shown, and
     recorded (W3). In Python, an approver that prints the question and says yes,
     `approve=lambda q: print(q) or True`; the question is rendered and recorded either way. With no
     terminal and no `--yes`, the answer is no. <…>
   - Another process making runs in the same workspace: `WorkspaceBusy`, naming it; reads and prices still
     work (`data_model.md` §10). <…>

## Read the report

5. **Open it.**

   ```text
   $ ema report 3f2a              # the Markdown on stdout; its path on stderr
   $ ema report 3f2a --pdf        # with pandoc and lualatex (get_started.md, step 1)
   ```

   - The header: the model version, the model parameter space, the design, run counts by status, failed runs
     by kind. <…>
   - Each number and its interval: an estimate with its variability interval and the method that made it, or
     an observation with none, or "none: <reason>" (`uncertainty.md`, 0041, 0042). What the interval means,
     once (`get_started.md`, step 7). <…>
   - The figures, and their data cards. <…>
   - The notes: constant model prediction, too few usable runs, failed runs, a model version measured noisy
     (`shared.md`). <…>
   - The provenance (P5). <…>

## When runs stop, fail, or vary

6. **Interrupted** (U2): Ctrl-C keeps every finished run. The same command later prices only what's left:

   ```text
   $ ema run heat coordinate_lines --space space.json --param n=17
     New runs of the model version `heat@b204…`: coordinate_lines on `T_max`.
     Price: 56 new runs, 41 reused, about 1 h 52 min (from 41 stored runs)
   ```

7. **Failed runs** (U3): the header and a note count them by kind; estimates use the usable runs only (P6).

   ```python
   wide = {"k": (5.0, 60.0), "q": (1e4, 2e5), ...}   # U3's wider space
   r1 = ws.run("heat", "scatter", wide, n=200, seed=2, approve=ema.ask)
   for run in ws.failed_runs(r1):  # each run not usable: its point, kind, and reason
       print(run)
   ```

   ```text
   $ ema failed-runs <r1's id>
   $ ema run-dirs <run id>        # its run directory, when kept
   ```

   - Too few usable runs: counts and a note, and no estimates (P6). <…>
   - A stored failed run is reused, like any stored run; `retry_failed=True` (`--retry-failed`) runs the
     failed ones again (0010). <…>

8. **A noisy model** (U7): the point run's repeats measure it.

   ```python
   ws.run("heat", "point_run", repeats=10, approve=ema.ask)
   ```

   - Repeats that vary make the model version measured noisy in that model prediction; every later diagnostic
     result for it, on that model prediction, carries a note (P7, C16). <…>

## Reuse, find, export, reproduce

9. **Reuse across diagnostics** (U5): a run is stored once and reused by any later design that has its point;
   the price counts it. Nested designs with the same space and seed share their first points (OD-13). <…>

10. **Find a result later.**

    ```python
    for r in ws.list_results(model="heat"):   # each with its id, diagnostic, model version, prediction
        print(r)
    print(ws.get_result("3f2a"))       # any unique prefix of 4 or more hex digits (Q11)
    ```

    ```text
    $ ema results --model heat
    $ ema results 3f2a
    ```

11. **Export its runs** (E1–E7).

    ```text
    $ ema export 3f2a heat_runs/                # prints the export's directory, absolute
      /…/heat_runs
    $ ema export 3f2a heat_runs_pdf/ --pdf      # also report/report.pdf, with pandoc and lualatex
      /…/heat_runs_pdf
    ```

    - `runs.csv` (a row per design row, so a repeated point appears again: the model parameter values, the
      model predictions, the status, the reason, the run time; EMA's columns start with `ema_`; E2),
      `result.json`, and `report/`: the report, its figures, and their data cards, and with `--pdf` (`pdf=True`)
      `report.pdf` (E1; 0081 item 31). <…>
    - **Open `runs.csv` as data,** not as a spreadsheet's formulas: a cell starting with `=`, `+`, `-`, or `@`
      may be read as a formula. Import it (pandas, or the spreadsheet's import as text) (`trust.md`,
      `export.md`). <…>

12. **Reproduce a result** (U8): from its provenance and the stored runs, with no new runs.

    ```text
    $ ema reproduce 3f2a
      Diagnostic result 3f2a: identical (estimates, intervals, notes, figures' data cards).
    ```

    - What "differs" names: the estimates, the provenance fields (versions) that differ, and any rows where the
      rebuilt design's points differ from the stored runs' (0062). <…>
    - In a copy of the workspace; or, in Python, from an export's `result.json`, its `result` key (`DiagnosticResult.from_json`,
      `architecture.md` §7). <…>
