# Use cases

**Status:** accepted. **Updated:** 2026-09-29.

> Each use case is a short scenario from the analyst's side: who they are, what model they have, what they
> want to learn, what they type (in Python or the CLI), what EMA asks them, and the report they get. Write
> them before the workspace functions: they become the guides, and the workspace's contract tests.
>
> - **Open decisions.** Where a use case depends on a decision still open in `../../STATUS.md`, it assumes
>   the suggested option and marks the place with its OD-n. If the decision goes the other way, the use case
>   is revised.
> - **Length.** U1–U4 are written in full. U5–U8 are variations that start from an earlier use case: each
>   has only its steps, what EMA asks, and "Done when".
> - **Typed steps** are in Python, against `ema.workspace` as drafted in `architecture.md` §7, so they are
>   provisional until that spec is accepted. One use case is also shown as CLI commands.

| Id | Name | Principles and decisions it exercises |
|---|---|---|
| U1 | First look at a cheap Python model | P3, P5; OD-5, OD-6 |
| U2 | Is a slow simulator smooth along each model parameter? | P3; OD-5, OD-6, OD-12 |
| U3 | A simulator that fails in part of its model parameter space | P6 |
| U4 | Does a low-degree polynomial fit? | P4, P6; OD-5, OD-12 |
| U5 | A second diagnostic reuses stored runs | P3 |
| U6 | The model changes | P3, P5 |
| U7 | A noisy model | P7; scope |
| U8 | Reproduce a stored diagnostic result | P4, P5 |

## U1 First look at a cheap Python model

- **Analyst and model:** a domain scientist with their own Python function: milliseconds per run, a handful
  of model parameters, and one scalar model prediction (OD-9). In the example, a cantilever beam: Young's
  modulus `E`, length `L`, and load `P`; the model prediction is the tip deflection. The "Done when" test runs
  the same steps on reference model R2 (Ishigami), whose answers are known.
- **Question:** over this model parameter space, which model parameters does the model prediction change
  with, and how: trends, spread, anything odd? The answer is the analyst's to draw from the figures (P2).
- **Steps, as typed:** the price is shown in the approval question; `estimate` exists for an analyst who
  wants the price without being asked, but U1 doesn't need it.

  ```python
  import ema

  ws = ema.open_workspace("beam_study")
  ws.load_model("beam/model.json")   # registers the model version
  ws.describe_model("beam")          # model parameters, units, nominal values
  ws.test_model("beam", approve=ema.ask)   # one run at the nominal point; asks y/n

  space = {"E": (190e9, 210e9), "L": (1.0, 2.0), "P": (1e3, 5e3)}
  result = ws.run("beam", "scatter", space, n=200, seed=1,
                  approve=ema.ask)   # shows the price, asks y/n
  print(result.report())
  ```

- **What EMA asks, and when:** two approvals (P3). `test_model` asks for its one run: 1 new, 0 reused, time
  unknown (no stored run durations yet). `run` asks for the design's runs: 200 new, 0 reused, and about
  0.2 s, estimated from the test run's stored duration. Loading the model asks nothing (OD-11 may change
  that).
- **What they get:** a report (one per diagnostic evaluation, 0006):
  - a header: the model version, the model parameter space, the design (uniform, n = 200, seed 1), and the
    runs (200 new, 0 reused, 0 failed);
  - a figure with one panel per model parameter, the model prediction against it, each axis labeled
    "name [units]", and a histogram of the model prediction, each with its data card;
  - numbers: the mean of the model prediction with its variability interval (OD-12); the observed minimum and
    maximum of the runs, as observations, not estimates; and one estimate per model parameter with its
    variability interval (for example, a rank correlation; which one is for the scatter spec, step 6);
  - notes, if any, and the provenance (P5).
- **What they do next, outside EMA:**
  - choose which model parameters to carry into a later study, and which to hold at their nominal values;
    possibly run U2 or U4 on them next;
  - narrow or widen the model parameter space and run scatter again, as a separate diagnostic evaluation;
    comparing the two reports is the analyst's job, not EMA's, in v2.0 (0005, 0006);
  - share the report and its figures with colleagues, or in a paper's supplement;
  - if something looks wrong (an unphysical value, a jump), fix the model function; loading it again makes a
    new model version (U6).
- **Done when:** on R2, in a fresh workspace:
  - the steps run end to end;
  - EMA asks exactly twice, with prices of 1 new, 0 reused, time unknown, and then 200 new, 0 reused, a time
    estimate;
  - the header counts 200 new, 0 reused, 0 failed;
  - the figure has one panel per model parameter, labeled with its units;
  - every number in the report and the data cards is computed from the stored runs (P1);
  - running the same steps again asks nothing, makes no new runs, and gives a byte-identical report (P3,
    P4).

  Known answers for R2 belong to the scatter spec (step 6), not to this use case.

## U2 Is a slow simulator smooth along each model parameter?

- **Analyst and model:** an engineer with a command-line simulation code, a steady heat-conduction solver for
  a plate: about 2 minutes per run, an input deck written from a template, 6 model parameters, and one scalar
  model prediction, the peak temperature, read by an output parser (OD-6, OD-9, OD-20). U2 includes writing
  the model spec, so it doubles as the add-a-model guide's example. The "Done when" test uses a reference
  model wrapped as a small command-line program.
- **Question:** along each model parameter, through the nominal point, is the model prediction smooth, or are
  there kinks, jumps, oscillations, or solver noise?
- **Steps, as typed:** this use case is also shown in the CLI.
  1. Write the input deck template and the model spec by hand, from the documented example. The fields are
     provisional until `model_interface.md` (step 4) is accepted.

     ```text
     heat/plate.in.template
       conductivity = {k}
       heat_flux    = {q}
       ...
     ```

     ```json
     {
       "name": "heat",
       "description": "2-D steady heat conduction in a plate",
       "interface": "command_line",
       "command": ["./heat_solver", "plate.in"],
       "input_deck": {"template": "plate.in.template", "writes": "plate.in"},
       "files": ["heat_solver", "mesh.dat"],
       "parameters": [
         {"name": "k", "units": "W/(m K)", "nominal": 45.0, "description": "thermal conductivity"},
         ...
       ],
       "predictions": [
         {"name": "T_max", "units": "K", "description": "peak temperature",
          "parser": {"kind": "regex", "file": "plate.out", "pattern": "T_max = (\\S+)"}}
       ]
     }
     ```

  2. Load it, test it at the nominal point, and run coordinate lines with 17 points per line. Each line's
     points include the nominal point, which the six lines share (`designs.md`, step 5): 97 distinct points,
     one of them the test run, so 96 new runs, about 3.2 hours. The analyst stops after 40 runs, and runs the
     same command the next day. How the model parameter space is given on the command line is open
     (`architecture.md` §8).

     ```text
     $ ema model add heat/model.json
     $ ema model test heat
       Price: 1 new run, 0 reused, time unknown
       Approve? [y/N] y
     $ ema run heat coordinate_lines --space space.json --param n=17
       Price: 96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)
       Approve? [y/N] y
       40/96 runs ... ^C
       Stopped: 40 runs stored.

     # the next day
     $ ema run heat coordinate_lines --space space.json --param n=17
       Price: 56 new runs, 41 reused, about 1 h 52 min (from 41 stored runs)
       Approve? [y/N] y
       56/56 runs
       Diagnostic result 3f2a; report: ema report 3f2a
     $ ema report 3f2a
     ```

     The same in Python:

     ```python
     ws = ema.open_workspace("heat_study")
     ws.load_model("heat/model.json")
     ws.test_model("heat", approve=ema.ask)
     space = {"k": (30.0, 60.0), "q": (1e4, 5e4), ...}
     result = ws.run("heat", "coordinate_lines", space, n=17, approve=ema.ask)
     print(result.report())
     ```

- **What EMA asks, and when:** every approval shows the price and the model version (P3). The first approval
  for a model version (here, the test run's) also shows what will run: the command, the input deck template,
  and the files copied into the run directory. Later approvals for that model version show only the price.
  After the interruption, the rerun asks again, for the 56 new runs only.
- **What they get:** a report:
  - a header: the model version, the model parameter space, the design (coordinate lines, 17 points each,
    through the nominal point), and the runs (97: 56 new, 41 reused, 0 failed);
  - figures: the model prediction along each line, one panel per model parameter; the spectrum of each line;
  - numbers: one estimate per line with its variability interval (for example, the spectrum's decay rate;
    which one is for the coordinate lines spec, step 6);
  - notes, if any, and the provenance.
- **What they do next, outside EMA:**
  - choose a method: smooth along every line, a polynomial surrogate or a spectral method (and perhaps U4);
    kinks or jumps, local or piecewise methods;
  - look closer at a kink: run a finer line through it, in a narrower model parameter space, as a new
    diagnostic evaluation (which diagnostic runs a single line is for OD-5);
  - if a line looks noisy, tighten the solver tolerance or refine the mesh; that changes the model's files,
    so it makes a new model version (U6);
  - share the report and its figures.
- **Done when:** on the command-line reference model, in a fresh workspace:
  - the model spec loads;
  - the test run asks once: 1 new, 0 reused, time unknown;
  - the first approval shows the command, the template, and the files, and later approvals for the same
    model version don't;
  - a diagnostic evaluation interrupted after k runs leaves k stored runs;
  - the rerun's price is 96 − k new and k + 1 reused, and exactly 96 − k runs are made (P3);
  - the report has one panel per model parameter and one spectrum per line;
  - running the same command again asks nothing and makes no new runs.

  Known answers belong to the coordinate lines spec (step 6).

## U3 A simulator that fails in part of its model parameter space

- **Analyst and model:** the engineer and heat solver from U2, over a wider model parameter space. At low
  conductivity and high heat flux, the solver doesn't converge and exits with an error; a few runs time out.
  The "Done when" test uses a reference model that fails in a known region, in both ways.
- **Question:** where in the model parameter space does the model fail, why, and what do the runs that
  worked still show?
- **Steps, as typed:**

  ```python
  wide = {"k": (5.0, 60.0), "q": (1e4, 2e5), ...}
  r1 = ws.run("heat", "scatter", wide, n=200, seed=2, approve=ema.ask)
  print(r1.report())                   # 34 of 200 runs failed: 30 errors, 4 timeouts
  ws.failed_runs(r1.result_id)         # each failed run: its point and its reason

  # a polynomial model with too few usable runs (U4's diagnostic), in a space where most runs fail
  wider = {"k": (1.0, 60.0), "q": (1e4, 5e5), ...}
  r2 = ws.run("heat", "polynomial_model", wider, degree=3, level=0, approve=ema.ask)

  # the same space, more points: the first 200 are the same points (OD-13)
  r3 = ws.run("heat", "scatter", wide, n=300, seed=2, approve=ema.ask)
  r4 = ws.run("heat", "scatter", wide, n=300, seed=2, retry_failed=True, approve=ema.ask)

  # a narrower space that avoids the failures: a new design, all new runs
  narrow = {"k": (20.0, 60.0), "q": (1e4, 1e5), ...}
  r5 = ws.run("heat", "scatter", narrow, n=200, seed=2, approve=ema.ask)
  ```

  - `r2`: in 6 model parameters, a cubic has 84 coefficients, and at U4's illustrative sizes its level-0
    design has 168 points. In the wider space 100 of them fail, which leaves 68 usable runs, fewer than the
    84 coefficients (the polynomial model's spec sets the minimum, step 6).
  - `r3` and `r4`: a stored failed run is reused, like any stored run, unless the analyst asks to retry
    (record 0010).
  - `r5`: a uniform design in a different model parameter space shares almost no points with the first, so
    nothing is reused.
- **What EMA asks, and when:** each `run` asks once, with its price (P3):
  - `r1`: 200 new, 0 reused;
  - `r2`: 168 new, 0 reused;
  - `r3`: 100 new, 200 reused, of which 34 failed;
  - `r4`: 34 new (the failed points, run again), 266 reused;
  - `r5`: 200 new, 0 reused.
- **What they get:**
  - `r1`: the header counts 200 runs: 34 failed (30 errors, 4 timeouts), 166 usable. Each panel marks the
    failed runs at their model parameter values (a marker along the bottom axis). A failure map shows failed
    and usable runs in each pair of model parameters, for a failure region that depends on two at once. A
    note counts the failed runs by reason. Estimates come from the usable runs only.
  - `r2`: counts and a note ("68 usable runs; a degree-3 polynomial model in 6 model parameters needs at
    least 84"), and no estimates (P6).
  - `r3`: as `r1`, with a note that 34 of the reused runs had failed before, and that `retry_failed` runs
    them again.
  - `ws.failed_runs`: each failed run's point and reason: the solver's own message, or "timeout after 600 s".
- **What they do next, outside EMA:**
  - choose a model parameter space inside the region where the model runs, for the next diagnostics;
  - change the solver's settings (tolerance, iterations, time step) so it converges; that changes the
    model's files: a new model version (U6);
  - send the failure reasons, and where they occur, to the simulation code's developers;
  - record the failure region as the model's range of validity, in their own study or paper.
- **Done when:** on the failing reference model:
  - exactly the points in the known region fail, each stored with its reason;
  - the header and the note count the failed runs by reason;
  - the estimates equal those computed from the usable runs alone;
  - the polynomial model gives counts and a note, and no estimates (P6);
  - a design that includes a failed point reuses it, and the price counts it as reused and failed; no new
    run is made at a failed point;
  - with `retry_failed`, exactly the failed points are priced as new, and run.

## U4 Does a low-degree polynomial fit?

- **Analyst and model:** an analyst planning an uncertainty study, who wants to know whether a cheap
  polynomial surrogate is worth building first. The model is a Python function of about 5 seconds per run:
  the focal shift of a lens assembly under thermal load, with 8 model parameters (material properties,
  temperatures, mount stiffness) and one scalar model prediction (OD-9). The "Done when" test uses reference
  models with known answers: a polynomial, and R2 (Ishigami).
- **Question:** how well does a low-degree polynomial fit the model prediction over this model parameter
  space, and how is its variation split among the model parameters and their interactions (Sobol indices)?
- **Steps, as typed:** a linear model, then polynomial models of degree 2 and 3, on convergent designs with
  the same seed. Convergent designs with the same seed and model parameter space are nested, so each larger
  design reuses the runs of the smaller ones (OD-13). The analyst gives the degree-3 run a budget of one hour
  (OD-15).

  ```python
  space = {...}   # 8 model parameters
  r1 = ws.run("lens", "linear_model", space, level=2, seed=3, approve=ema.ask)
  r2 = ws.run("lens", "polynomial_model", space, degree=2, level=2, seed=3, approve=ema.ask)
  r3 = ws.run("lens", "polynomial_model", space, degree=3, level=2, seed=3,
              budget=ema.Budget(max_seconds=3600), approve=ema.ask)
  #   refused: 960 new runs, about 80 min, over the budget of 60 min
  r3 = ws.run("lens", "polynomial_model", space, degree=3, level=1, seed=3,
              budget=ema.Budget(max_seconds=3600), approve=ema.ask)
  ```

- **What EMA asks, and when:** each run asks once, with its price, unless it is refused first. The numbers
  are illustrative: design sizes follow `designs.md` (step 5); here, a convergent design has
  2 × (number of coefficients) points at level 0, doubling at each level.
  - `r1`: 72 new, 0 reused, about 6 min;
  - `r2`: 288 new, 72 reused, about 24 min;
  - `r3` at level 2: refused before asking, since 960 new runs, about 80 min, is over the budget;
  - `r3` at level 1: 300 new, 360 reused, about 25 min.
- **What they get:** three reports. The polynomial model's numbers and figures are settled in its spec
  (step 6); the lean set is:
  - numbers: the fit's residual and cross-validated error, and the Sobol first-order and total indices, each
    with its variability interval (for example, convergence over the design's levels, OD-12);
  - figures: a 1-D shadow (the model prediction against the fitted polynomial), the Sobol indices with their
    intervals, and a histogram of the residuals.

  The linear model's report has its coefficients with intervals, the 1-D shadow, the residual histogram, and
  the residual norm. The active subspace, a 2-D shadow, and the decay of the coefficients are not in this
  lean set; whether they are in v2.0 is for scope (step 3) and the polynomial model's spec (step 6).
- **What they do next, outside EMA:**
  - build a polynomial surrogate of the chosen degree in a UQ tool, and use it for the uncertainty study;
  - export the stored runs, and fit the surrogate in their own tool (U5);
  - hold at their nominal values, in the uncertainty study, the model parameters with small total Sobol
    indices (the analyst's judgment, P2);
  - if no degree fits, look at lines (U2) or failures (U3) to see why, and choose another method.
- **Done when:** on the polynomial reference model and on R2:
  - each price counts as reused exactly the points shared with the earlier designs;
  - the budget refuses the level-2 run before asking, and makes no run;
  - running the same steps again gives identical diagnostic results, intervals included (P4);
  - y → a·y + b leaves every note and the Sobol indices unchanged (P6).

  Known answers (exact recovery of a polynomial, Ishigami's Sobol indices) belong to the polynomial model's
  spec (step 6).

## U5 A second diagnostic reuses stored runs

- **Steps, as typed:** after U1, the analyst runs a degree-2 polynomial model in the same model parameter
  space, with the same seed. The convergent design starts from the same seeded uniform stream as scatter's
  design (OD-13), so scatter's 200 points are its first 200. At U4's illustrative sizes, 3 model parameters,
  degree 2, and level 4 make 320 points. Then the analyst runs the same request again, and exports the runs.

  ```python
  # after U1
  r2 = ws.run("beam", "polynomial_model", space, degree=2, level=4, seed=1, approve=ema.ask)
  r3 = ws.run("beam", "polynomial_model", space, degree=2, level=4, seed=1, approve=ema.ask)
  ws.export(r2.result_id, "beam_runs/")
  ```

  The export holds the runs that diagnostic result used, with its design, and the diagnostic result with its
  provenance: a CSV of runs (one row per run: the model parameter values, the model predictions, the status,
  the reason for a failure, and the run time) and a JSON file for the rest. Model predictions that are arrays
  (OD-9) will need another format.
- **What EMA asks, and when:** `r2` asks once: 120 new, 200 reused, and a time estimated from the stored run
  durations. `r3` has no new runs, so it asks nothing (P3).
- **Done when:**
  - `r2`'s price counts exactly the 200 shared points as reused, and exactly the 120 others are run;
  - `r3` asks nothing and makes no run;
  - the export holds exactly `r2`'s runs; reading it back gives the same model parameter values and model
    predictions, bit for bit, and the same provenance.

## U6 The model changes

- **Steps, as typed:**
  1. After U1, the analyst fixes a bug in `beam.py`, and runs scatter again before loading the model again.
     EMA re-hashes the model's files before every run, and refuses. The analyst loads the model again, which
     makes a new model version, and runs scatter.

     ```python
     # beam.py edited
     ws.run("beam", "scatter", space, n=200, seed=1, approve=ema.ask)
     #   refused: beam.py changed since the model was loaded; load it again to make a new model version
     ws.load_model("beam/model.json")   # new model version beam@3f2a (was beam@91c0): beam.py changed
     r = ws.run("beam", "scatter", space, n=200, seed=1, approve=ema.ask)
     ws.list_results(model="beam")      # U1's diagnostic result and this one, each with its model version
     ```

  2. After U2, the engineer tightens the solver's tolerance in `solver.cfg`, a file the model spec lists and
     EMA copies into each run directory. Loading the model again makes a new model version, and coordinate
     lines run again.

     ```text
     $ ema model add heat/model.json
       New model version heat@7c1e (was heat@b204): solver.cfg changed
     $ ema run heat coordinate_lines --space space.json --param n=17
     ```

- **What EMA asks, and when:** a new model version has no stored runs, and no stored run durations:
  - `r` asks for 200 new, 0 reused, time unknown (P3);
  - the heat model's run asks for 97 new, 0 reused, time unknown, and, as the first approval for the new
    model version, shows the command, the input deck template, and the files again (U2).
- **Done when:**
  - changing one byte in a model file makes a new model version, and no stored run is reused (P3);
  - a run whose model files changed since the model was loaded is refused, with the name of the file;
  - a change between an approval and its runs is refused, and the runs made before it are kept (P3);
  - the old diagnostic result's report is unchanged, and its provenance names the old model version (P5);
  - listing results shows both, each with its model version.

## U7 A noisy model

Whether models declared noisy are in v2.0 is for scope (P7, "Open"). U7 needs only the point run and the
note, whatever scope decides.

- **Steps, as typed:** the heat solver from U2 is declared deterministic, but its iterative tolerance makes
  the peak temperature vary slightly between runs at the same point. After U2, the engineer runs the point
  run at the nominal point with 10 repeats. The repeats are replicates 1 to 10 of a deterministic model
  (record 0011).

  ```python
  p = ws.run("heat", "point_run", repeats=10, approve=ema.ask)   # at the nominal point
  print(p.report())
  r = ws.run("heat", "scatter", space, n=200, seed=4, approve=ema.ask)
  print(r.report())   # carries the note
  ```

  The point run needs no model parameter space; `run`'s signature in `architecture.md` §7 must allow that.
- **What EMA asks, and when:** the point run asks for 10 new runs (replicates 1 to 10), 1 reused (the test
  run at nominal, replicate 0), about 20 min. Scatter asks as usual.
- **What they get:** the point run's report gives the model prediction at the point, and its measured
  variation across the 11 runs (which numbers, and the tolerance for "varies", relative to what, are for the
  point run's spec, step 6). The model version is recorded as measured noisy. Every later diagnostic result
  for that model version carries a note: the model version was measured noisy, by which point run, and by how
  much (P7).
- **Done when:**
  - on a noisy reference model declared deterministic, the point run's repeats are stored as replicates 1 to
    k, and its report gives the measured variation;
  - every later diagnostic result for that model version carries the note;
  - on a deterministic reference model, the repeats measure no variation, and no note is added;
  - running the same point run again makes no new runs.

## U8 Reproduce a stored diagnostic result

- **Steps, as typed:** a colleague reviewing the analyst's paper gets a copy of the workspace directory from
  U1, and checks the scatter result. `reproduce` recomputes the diagnostic result from its provenance and the
  stored runs, with no new runs, and compares.

  ```python
  ws = ema.open_workspace("copy_of_beam_study")
  ws.list_results()
  check = ws.reproduce("3f2a")
  print(check)
  #   Diagnostic result 3f2a: identical (estimates, intervals, notes, figures' data cards).
  # or:
  #   Differs: 2 estimates. Provenance differs in numpy (2.3.1 here, 2.4.0 there).
  ```

- **What EMA asks, and when:** nothing: reproducing makes no runs.
- **Done when:**
  - in a copy of the workspace, with the same EMA and library versions, reproducing gives an identical
    diagnostic result, intervals included, and a byte-identical report (P1, P4), and makes no run;
  - a deleted diagnostic result is recomputed identical from its provenance and the stored runs (P5);
  - with one library version changed, the check names exactly that provenance field.

## What the use cases ask of other specs

> Collected for the steps that settle them. None of these is decided here.

- **Scope (step 3):** the use cases use five diagnostics: point run, scatter, coordinate lines, linear model,
  and polynomial model (OD-5 suggests 3–4). U4's report leaves out the active subspace, a 2-D shadow, and
  the decay of the coefficients. U7 works whether or not models declared noisy are in v2.0.
- **Model interface (step 4):** U2's model spec fields (`command`, `input_deck`, `files`, `parameters`,
  `predictions` with a regex parser, OD-20) are provisional. U6 needs the files a model copies into its run
  directory (such as `solver.cfg`) to be part of its model version.
- **Designs (step 5):** uniform designs with the same seed and model parameter space are nested: the first n
  points of a larger design are the smaller design (U3, U4). A convergent design starts from the same seeded
  stream as a uniform design with the same seed, so a polynomial model reuses a scatter's runs (U5).
  Coordinate lines through the nominal point include it, and share it (U2). U4's design sizes are
  illustrative.
- **Diagnostic specs (step 6):** the "Decide:" lines on step 6 in `../../TODO.md` (U1, U2, U7).
- **Contracts (step 7):** U3's failure map ("Decide:" line on step 7); failed runs reused unless retried
  (record 0010); the point run's repeats of a deterministic model (record 0011).
- **Data model (step 8):** a retried run stored beside the failed run it replaces (0010); a model version
  recorded as measured noisy, with the point run that measured it (U7).
- **Architecture (step 9), `ema.workspace`:**
  - `test_model` takes `approve`, since its run is a new run (U1);
  - `run` for the point run needs no model parameter space (U7);
  - new names: `failed_runs` (U3), `reproduce` (U8), and `retry_failed` on `run` and `estimate` (0010);
    with `ema.ask` and `ema.Budget`, the public names are near the budget of 15 (scope);
  - `run` re-hashes the model's files first, and refuses if they changed since the model was loaded (U6);
  - the first approval for a model version shows the command, the input deck template, and the files (U2);
  - `export` writes a CSV of runs and a JSON file, not `.npz` (U5);
  - the CLI takes a model parameter space as `--space FILE` in U2; how is still open (§8).
