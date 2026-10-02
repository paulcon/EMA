# Add a model

**Status:** outline. **Use cases:** U1, U2, U6. **Specs:** `../design/model_interface.md` (M1–M21),
`../design/trust.md` (T2–T4, T7, T8, T10). **Tested:** through the use cases (C53); its examples are U1's
beam and U2's heat solver, which the use cases run on reference models.

> Two paths: a Python function, and a command-line program with an input deck. Both end at the same place: a
> model spec (JSON) that `load_model` (`ema model add`) reads. Outline now, full text once the code exists;
> `<…>` marks text to write then.

## A Python function

1. **Write the function** (U1's beam, δ = PL³/(3EI)).

   ```python
   # beam/beam.py
   def deflection(E, L, P, I=8.33e-6):
       return P * L**3 / (3 * E * I)
   ```

   - Called as `f(**x)`: one keyword float per model parameter; returns a float, or a mapping of model
     prediction names to floats (M7). <…>
   - Its working directory is the run directory; relative paths in it read the files the spec lists. <…>
   - **Stateless:** each call stands alone. A module-level cache or counter makes model predictions depend on
     the order of runs (0026); the point run's repeats would show it. <…>
   - Code in an installed package: a short wrapper file that imports it. <…>
   - Many points per call (`"batch": true`, 0025): `f(X)` with an (n, d) array. <…>

2. **Describe it in a model spec:** name, description, `"interface": "python_function"`, `"function":
   "beam.py:deflection"`, and each model parameter and model prediction (`model_interface.md`'s beam).

   - Each model parameter: name, units, description, nominal value, limits (`gt`, `ge`, `lt`, `le`). Ranges
     and log scales belong to the model parameter space, given per diagnostic, not to the model (0024). <…>
   - Each model prediction: name, units, description. <…>
   - Units as plain text or Unicode (`W/m²`, `W/(m K)`), not mathtext: a spec's names and units print
     literally (`trust.md`, T10). <…>
   - Files the function reads (`"files"`), and large read-only ones as `{"path": …, "shared": true}`, stored
     once and linked into each run directory (0030). <…>
   - **Helper modules** the function imports: list them in `"files"`, and they are tracked. An import that
     resolves to an unlisted file in the model's directory is a warning at loading (M17); modules elsewhere,
     and installed packages, are not tracked (0029). <…>

3. **Load it, and see its model version.**

   ```python
   print(ws.load_model("beam/model.json"))
   #   Loaded beam@91c0…: 3 model parameters (E, L, P), 1 model prediction (delta)
   ```

   ```text
   $ ema model add beam/model.json
   ```

   - What loading checks, and what an error names (the field: `SpecError`). Loading imports nothing and runs
     nothing (T4). <…>
   - The model version: a hash of everything that decides a run (M3, 0029). <…>

4. **Test it at the nominal point.**

   ```python
   print(ws.test_model("beam", approve=ema.ask))
   #   beam@91c0…: test run at the nominal point
   #   Price: 1 new run, 0 reused, time unknown
   #   (the first approval for a model version: the function, the child's interpreter, the files, the
   #   environment)
   #   Approve? [y/N] y
   #   Run 5d02: ok; delta = 0.002026
   ```

   ```text
   $ ema model test beam
   ```

5. **Time a few runs, and check that repeats agree:** the point run with 3 repeats, then a price.

   ```python
   print(ws.run("beam", "point_run", repeats=3, approve=ema.ask))   # at the nominal point
   space = {"E": (190e9, 210e9), "L": (1.0, 2.0), "P": (1e3, 5e3)}
   print(ws.price("beam", "scatter", space, n=200, seed=1))   # a time from 4 stored runs
   ```

   - Repeats that differ make the model version measured noisy in that model prediction, and every later
     diagnostic result for it, on that model prediction, carries a note (U7, P7, C16). <…>

6. **When a run fails,** and how to see why.

   ```python
   # after an edit to beam.py and loading it again: a new model version, beam@a417…
   info = ws.test_model("beam", approve=ema.ask)
   #   beam@a417…: test run at the nominal point
   #   Price: 1 new run, 0 reused, time unknown
   #   (the first approval for this model version: the function, the child's interpreter, the files, the
   #   environment)
   #   Approve? [y/N] y
   print(info)
   #   Run 9b3e: failed (error): ZeroDivisionError: division by zero at beam.py:3; run directory: …/runs/9b3e…/
   print(ws.run_dirs(info.run_id)[0].run_dir)   # then list it: point.json, run.json, stdout.txt,
                                                # stderr.txt, and the files copied into it
   ```

   ```text
   $ ema run-dirs 9b3e
   ```

   - The three failure kinds (`error`, `timeout`, `unread`), each with a one-line reason and the last lines
     of stderr, and a missing model prediction (M1, M4, 0022). <…>
   - What a run directory holds, and the `keep` setting (`all`, `incomplete`, `none`; 0020, 0028). <…>
   - A timeout: `timeout_s` in the spec, 3600 s by default, per call. <…>

## A command-line program

1. **The input-deck template** (U2's heat solver): `string.Template`, `$k` or `${k}` per model parameter, `$$`
   for a literal `$`. Numbers are written as the shortest decimal that reads back as the same double; there is
   no format field. <…>

   ```text
   # heat/plate.in.template
   conductivity = $k
   heat_flux    = $q
   ```

2. **The command, the run directory, and the files copied into it.**

   - `"command": ["./heat_solver", "plate.in"]`: a list, run without a shell, in the run directory. A shell
     only when the spec says so (`["sh", "-c", …]`); a program such as `/bin/sh` is not tracked, so the
     model version doesn't cover it (0029, `trust.md`). <…>
   - `"input_decks"`, `"files"`, shared files (0030). A program on `PATH` or given by an absolute path is
     neither copied nor tracked; one listed in `"files"` is (0029). <…>
   - A file outside the model's directory: a link to it inside the directory (`trust.md`). <…>
   - A command of more than one line, or a scheduler's or module system's many variables: a wrapper script,
     listed in `"files"`. <…>

3. **Reading the model predictions** from the model output: an output parser per model prediction, `regex`,
   `json`, or `csv` (0027), on a file in the run directory, or `stdout` or `stderr`.

   ```json
   "parser": {"kind": "regex", "file": "plate.out", "pattern": "T_max = (\\S+)"}
   ```

   - What makes a model prediction missing, with its reason. <…>
   - Any other output: a wrapper script that reads it and writes JSON, read by the `json` parser (0027). <…>

4. **What you approve, and why.** The first approval for a model version shows the command and the
   program's resolved path, the input deck templates, the files, and the environment the spec sets (U2,
   `trust.md`, What needs the user's yes; 0029, 0057); later ones show only the model version and the
   price. Every question and answer is recorded (T3). <…>

   ```text
   $ ema model add heat/model.json
   $ ema model test heat
     heat@b204…: test run at the nominal point
     Price: 1 new run, 0 reused, time unknown
     Command: ./heat_solver plate.in (/…/heat/heat_solver)
     Input deck plate.in.template → plate.in:
       conductivity = $k
       heat_flux    = $q
     Files: heat_solver, solver.cfg, mesh.dat (shared)
     Environment: OMP_NUM_THREADS=4
     Approve? [y/N] y
   ```

5. **Test it at the nominal point; time a few runs:** as the Python function's steps 4–6, with `ema model test`
   and `ema run heat point_run --param repeats=3`. <…>

## The environment and files (`../design/trust.md`)

- **What a model sees:** the base variables (`BASE_ENV`: `PATH`, `HOME`, the locale, …), the names in
  `pass_env` with their values from EMA's environment, and `env`, whose values win. Nothing else (T2). <…>
- **`pass_env`, with an example:** a license server, `"pass_env": ["LM_LICENSE_FILE"]`; the first approval
  says whether each name is set, never its value. <…>
- **No secret in `env`:** `env` is stored, hashed, and shown in the approval. A credential-like name
  (`*_API_KEY`, `*_TOKEN`, …) is refused in either field (T8). <…>
- **macOS:** `DYLD_*` variables are dropped when a protected program, such as `/bin/sh`, starts; a wrapper
  script sets them itself before it starts the model's program. <…>
- **Units** as plain text or Unicode, not mathtext (above). <…>
- **A file outside the model's directory:** a link inside it (above). <…>

## When a model changes (U6)

- **What makes a new model version:** a changed tracked file (the function's file, the templates, and the
  listed files, helper modules and a program included when listed), or a changed field that decides a run
  (M3, 0029). What doesn't: `keep`, `batch_size`, `timeout_s`, a program on `PATH`. <…>
- **A changed file before loading again:** a run is refused, naming the file (`ModelChanged`, M16).

  ```text
  $ ema model add heat/model.json
    New model version heat@7c1e (was heat@b204): solver.cfg changed
  ```

- **Stored runs:** kept, with their model version; a new model version reuses none of them, and its first
  price says "time unknown" (P3). Old diagnostic results and their reports don't change (P5). <…>
