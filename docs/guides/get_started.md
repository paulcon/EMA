# Get started

**Status:** outline. **Use cases:** U1, U5, U9. **Specs:** `../design/architecture.md` §7–§8,
`../design/reference_models.md` (R2), `../design/uncertainty.md`, `../design/trust.md`. **Tested:** its
Python blocks run as written on R2, from an installed EMA, in the slow tier (C53; record 0060).

> Outline now, full text once the code exists. Each step shows what the user types and what they see; `<…>`
> marks text to write then, and the numbers shown are placeholders until the test computes them. The guide is
> in Python: the CLI can't name a reference model (`ema.cli` doesn't import `ema.reference_models`,
> `architecture.md` §10), and the other guides show the CLI with the analyst's own files.

1. **Install EMA** with uv, on Python 3.13 or newer (0059). Read access to the repository is needed (a
   GitHub login, or a token).

   ```text
   $ uv init my_study && cd my_study          # a project, if you have none
   $ uv add "ema @ git+https://github.com/pauls-code-projects/EMA@v2.0"
   $ uv tool install "ema[mcp] @ git+https://github.com/pauls-code-projects/EMA@v2.0"
   $ ema --help                               # the ema command and the MCP server, on PATH
   ```

   - `uv add` is for Python and notebooks in the project; `uv tool install` puts `ema` on `PATH`. <…>
   - **Optional, for PDF reports** (0018, 0059): pandoc and a LaTeX with lualatex, in staged steps, each with
     its check. Without them everything works but a PDF (`pdf=True`, or `ema report --pdf`), which raises
     `PandocMissing` naming what to install.
     - macOS: `brew install pandoc`, then `pandoc --version`; `brew install --cask basictex`, then
       `lualatex --version`; the packages pandoc's template needs, `sudo tlmgr install …` (the list is the
       PDF build step's). <…>
     - Linux: `apt install pandoc texlive-luatex …` (the list is the PDF build step's). <…>
     - Check: `print(ws.report(result, pdf=True).pdf)` on step 6's result gives the PDF's path. <…>

2. **Open a workspace,** and see where it lives.

   ```python
   import ema
   import ema.reference_models               # not re-exported by `ema` (architecture.md §2)
   ws = ema.open_workspace("first_study")   # created on first use
   print(ws.path)                            # /…/my_study/first_study
   ```

   - The workspace holds the store, the run directories, and the reports (`data_model.md`); an export goes
     where you name it. Opening it again later finds everything. <…>

3. **Load a reference model** (R2, Ishigami), and look at its model parameters.

   ```python
   print(ws.load_model(ema.reference_models.path("R2")))
   #   Loaded ishigami@<12 hex>: 3 model parameters (x1, x2, x3), 1 model prediction (y)
   print(ws.describe_model("ishigami"))
   #   the model parameters with units, nominal values, and limits; the model prediction
   ```

   - Reference models ship with EMA, with answers known (`reference_models.md`). Loading asks nothing and
     runs nothing; it makes a model version (W1, M3; U1). <…>

4. **Test it at the nominal point:** the first run, which EMA asks about (P3).

   ```python
   print(ws.test_model("ishigami", approve=ema.ask))
   #   ishigami@<12 hex>: test run at the nominal point
   #   Price: 1 new run, 0 reused, time unknown
   #   (the first approval for a model version also shows the function, the child's interpreter, the files,
   #   and the environment: trust.md, What needs the analyst's yes)
   #   Approve? [y/N] y
   #   Run <short id>: ok; y = 0 (x1 = x2 = x3 = 0)
   ```

   - Why "time unknown": EMA estimates time only from stored runs (P3). <…>

5. **Price a diagnostic** before running it.

   ```python
   import math
   space = {"x1": (-math.pi, math.pi), "x2": (-math.pi, math.pi), "x3": (-math.pi, math.pi)}
   print(ws.price("ishigami", "scatter", space, n=200, seed=1))
   #   200 new runs, 0 reused, about <t> (from 1 stored run)
   ```

   - The model parameter space: a range per model parameter (`designs.md`, JSON form); the diagnostic
     parameters as keywords; `ws.describe_diagnostic("scatter")` lists them. <…>

6. **Run it,** approving the runs.

   ```python
   result = ws.run("ishigami", "scatter", space, n=200, seed=1, approve=ema.ask)
   #   ishigami@<12 hex>
   #   Price: 200 new runs, 0 reused, about <t> (from 1 stored run)
   #   Approve? [y/N] y
   print(result)
   #   Diagnostic result <id>: scatter on ishigami@<12 hex>, y; 200 runs: 200 new, 0 reused, 0 failed;
   #   report: ema report <id>
   ```

   - Progress: `on_progress=print` shows "40/200 runs" as they finish; the CLI shows it on stderr. <…>
   - Running the same request again asks nothing, makes no run, and returns the same diagnostic result
     (P3, P4). <…>

7. **Read the report.**

   ```python
   report = ws.report(result)
   print(report.path)   # /…/first_study/results/<result id>/report.md: open it in a Markdown viewer
   ```

   - The header: the model version, the model parameter space, the design, the runs. <…>
   - The figures, and each one's data card (the numbers it draws, beside it). <…>
   - The numbers: estimates with their variability intervals, and observations. What a variability interval
     is (how much the estimate moves when the runs are resampled), and why it is not a confidence interval
     (0004, 0042). <…>
   - The notes, and the provenance (P5). The report holds no interpretation: the reading is yours (P2). <…>

8. **Run a second diagnostic,** and see which runs were reused (U5).

   ```python
   r2 = ws.run("ishigami", "polynomial_model", space, degree=2, level=4, seed=1, approve=ema.ask)
   #   ishigami@<12 hex>
   #   Price: 120 new runs, 200 reused, about <t> (from 201 stored runs)
   #   Approve? [y/N] y
   print(r2)
   #   Diagnostic result <id>: polynomial model on ishigami@<12 hex>, y; 320 runs: 120 new, 200 reused,
   #   0 failed; report: ema report <id>
   ```

   - With the same space and seed, the convergent design starts with scatter's 200 points
     (OD-13): 20, 40, 80, 160, 320 points at levels 0 to 4 (G7, with n_min = 2P = 20 and alpha = 0.7072,
     `polynomial_model.md`). <…>

9. **Through an MCP client** (U9): the same workspace, from an agent.

   - The client's configuration, with absolute paths (a client started from the desktop doesn't see the
     shell's `PATH`; `which ema` gives the first):

     ```json
     {"mcpServers": {"ema": {"command": "/Users/you/.local/bin/ema",
                             "args": ["--workspace", "first_study", "mcp", "--root", "/Users/you/my_study"]}}}
     ```

   - `--root` is required: every path the agent names must be inside it (`trust.md`, T5). <…>
   - Ask the agent to list the models: ishigami, loaded in step 3, is there. Ask it to run scatter with
     n = 300: the client asks you to approve, by elicitation; the agent can't answer for you (P3). The report
     opens as a resource, `ema://results/{id}/report`. <…>
   - The agent quotes EMA's numbers and doesn't make its own (P1). <…>

10. **Where to go next:** `add_a_model.md` (your own model), `run_a_diagnostic.md` (the diagnostics,
    failures, reuse, reproducing), `add_a_diagnostic.md` (contributing one). <…>
