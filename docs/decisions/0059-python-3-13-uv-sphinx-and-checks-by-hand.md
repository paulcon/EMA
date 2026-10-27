# 0059. Support Python 3.13 and newer; build with uv and a lockfile, document with Sphinx, run the checks on GitHub Actions by hand, and make PDFs with lualatex

**Date:** 2026-10-01. **Status:** accepted; item 5's "not published" amended by 0088. **Resolves:** OD-17, OD-18; 0018's step-12 plan.

## Context

- **A Python model runs in EMA's own interpreter** (`../design/trust.md`: the worker is `sys.executable`), so a
  user's model function and its packages must import on the Python that EMA is installed with. A model whose
  packages lag can still run as a command-line model under its own Python.
- **Scientific Python's support window** (SPEC 0) lets numpy, scipy, and matplotlib drop a Python version three
  years after its release: 3.12 (October 2023) from about now. A floor of 3.12 would in time leave its users on
  frozen library versions.
- **This Mac** (Intel, macOS 14) has Python 3.14.0 from python.org and 3.11; v1 runs here on 3.14 with numpy
  2.5.3, scipy 1.18.1, and matplotlib 3.11.2. pandoc 3.5 and TeX Live 2022 are installed; uv 0.12.21, with its
  own Pythons 3.14.7 and 3.13.15, was installed for this step.
- **v1** built with setuptools and documented with Sphinx, MyST, and furo
  (`../notes/v1/lessons_learned_2026-09-27.md` §9, which also gives its lesson: lower bounds in
  `pyproject.toml`, and a lockfile, uv, for development). Its workflows ran on GitHub Actions by hand only
  (`workflow_dispatch`, v1's `.github/workflows/ci.yml`), testing 3.11 and 3.14.
- **PDFs (0018):** the linear model's mock report, read with `trust.md`'s options
  (`-f markdown-raw_tex-raw_html-raw_attribute`), fails under pdflatex on "≈" (Unicode); xelatex and
  lualatex make it, but Latin Modern has no "≈". lualatex with DejaVu Serif makes it with no font warning,
  from TeX Live's copy by name, or from the four files matplotlib ships in `mpl-data/fonts/ttf/` (regular,
  bold, italic, bold italic) when each is named; with the regular file alone, headings lose their bold. BasicTeX
  and small Linux TeX installs lack DejaVu Serif. Code otherwise prints in LM Mono, which lacks "α" and "≈"
  (missing glyphs, with exit 0); matplotlib also ships DejaVu Sans Mono's four files. The math uses Latin Modern
  Math, from TeX. A font path holding `%`, `#`, or `~` breaks lualatex; a font `Path=./` resolves against
  pandoc's working directory. A figure pandoc can't find is replaced by its description, with a warning and
  exit 0. A missing package or font stops lualatex with a line that names it ("File `x.sty' not found", "The
  font "X" cannot be found"). One PDF takes about 4 s.
- **The repository is private on GitHub,** whose free plan gives 2,000 Actions minutes a month; macOS minutes
  count ten times. GitHub Pages for a private repository needs a paid plan. A `workflow_dispatch` workflow can
  be started only once its file is on the default branch. The Ubuntu runners have Pythons 3.13 and 3.14, and
  no pandoc or LaTeX.
- **uv's lowest resolution** (`--resolution lowest-direct`) lowers every direct dependency, the dependency
  group's tools included, and rewrites `uv.lock`. Passed as flags (`--python 3.13 --resolution
  lowest-direct`) to `uv sync` alone, they are undone by the next plain `uv run`, which re-resolves on
  `.python-version`'s Python; set as `UV_PYTHON` and `UV_RESOLUTION`, they hold for every uv command in the
  job (numpy 2.1.0, scipy 1.14.1, matplotlib 3.9.2 on 3.13.15, in a scratch project). uv accepts the project's
  own extra (`ema[mcp]`) in a dependency group.
- **MkDocs's Material theme** is in maintenance mode; Sphinx is v1's, and stable.
- **`../design/architecture.md` §10** leaves to setup whether import-linter sees standard-library imports
  (AR2, AR5). It does: import-linter 2.15 with `include_external_packages = true` reports `ema.types -> os` and
  `ema.types -> sqlite3` for an AR2-style forbidden contract, in a scratch project. It refuses a layer or a
  source module that doesn't exist, but accepts a forbidden module that doesn't. `lint-imports` took about
  1.1 s.

## Decision

We will:

1. **Support Python 3.13 and newer** (`requires-python = ">=3.13"`), and develop on 3.14
   (`.python-version`). Raising the floor is a new record.
2. **Manage the environment with uv,** with `uv.lock` committed. `pyproject.toml` gives every runtime
   dependency a lower bound: numpy, scipy, and matplotlib at their first releases with wheels for Python 3.13.
   The build backend is `uv_build`, the package in `src/ema/`; the wheel holds the package's data files
   (`ema/reference_models/`, `ema/store/schema.sql`, `ema/mcp/tools.md`), and the slow tier's wheel-build test
   checks them.
3. **Keep the development tools in a uv dependency group** (`dev`, installed by `uv sync`, not shipped), each
   with a lower bound at its release when first locked: pytest and pytest-xdist; Ruff; mypy; import-linter;
   Sphinx, MyST, and furo. A tool is not a runtime dependency, so `../design/scope.md`'s budget is unchanged.
   **The build step that adds `ema.mcp`** adds the `mcp` extra, with its lower bound at its first release with
   elicitation, and `ema[mcp]` to the `dev` group, so the MCP code is installed for tests, mypy, and the docs.
4. **Configure each tool's scope** in `pyproject.toml` and the root `conftest.py`:
   - **Ruff:** line length 120; Ruff's defaults with B905, NPY (NPY002, as `../design/principles.md` names), I
     (import order), and D with the NumPy convention (its missing-docstring rules apply only to public names;
     not in `tests/` or `conftest.py`); `docs/checks/` excluded, as scripts with their own style. `ruff format`
     formats.
   - **mypy:** `files = ["src"]`, not strict, with scipy's missing types ignored.
   - **pytest:** `testpaths = ["tests", "src"]` and `--doctest-modules`; the root `conftest.py` adds the
     `--slow` option, and keeps `src/ema/reference_models/` out of collection (`collect_ignore`: its models
     are programs and data, and share file names).
   - **import-linter:** `architecture.md` §10's contracts, from the first build step. Each lists only the
     layers and source modules that exist, and grows as build steps add packages; a forbidden module may be
     named before it exists.
5. **Build a documentation site with Sphinx,** locally, not published: the guides (`docs/guides/`, read by
   MyST) and an API reference of `architecture.md`'s public names, generated from the docstrings (autodoc,
   autosummary, napoleon), with warnings as errors. `docs/conf.py` excludes `design/`, `decisions/`,
   `notes/`, `plans/`, and `checks/`, and sets napoleon and autodoc so a dataclass's fields are described
   once.
6. **Use these commands** (CLAUDE.md):

   | Command | What | When |
   |---|---|---|
   | `uv sync` | install | |
   | `uv run pytest -q && uv run lint-imports` | the fast tier (`../design/contracts.md`), with the import contracts | after every edit |
   | `uv run pytest -q --slow -n auto` | both tiers' tests | before a step is reported done |
   | `uv run ruff check && uv run ruff format --check && uv run mypy` | lint | before a step is reported done |
   | `uv run sphinx-build -W --keep-going docs docs/_build/html` | the docs | before a step is reported done |

7. **Run the checks on GitHub Actions, started by hand** (`.github/workflows/checks.yml`, `workflow_dispatch`
   only), on Linux: lint, the import contracts, and the docs on 3.14 (the site kept as the run's artifact);
   both tiers on 3.14 with `uv sync --locked`; and both tiers on 3.13 at the lowest versions the lower bounds
   allow, with `UV_PYTHON=3.13` and `UV_RESOLUTION=lowest-direct` set for the whole job, which tests the
   runtime lower bounds. macOS is tested on the owner's Mac. Estimated at 30–35 minutes a run, measured on the
   first run, which the owner starts after merging and pushing the first build step.
8. **Make PDFs with lualatex** (`ema.report.to_pdf`), the text in DejaVu Serif and code in DejaVu Sans Mono,
   each from matplotlib's four files, each file named, so no TeX text font is needed. The PDF holds every
   figure of the report. How `to_pdf` places the fonts and finds the figures is the build step's plan (the
   Context's pitfalls: the working directory, characters in a path, figures dropped with exit 0).
   - **`PandocMissing`** is raised when pandoc or lualatex isn't found, or when lualatex stops on a missing
     package or font; it names what to install.
   - **`PdfFailed`** (an `EMAError`, not retryable) is raised when lualatex stops for any other reason, with
     LaTeX's error line, or when a figure is missing from the PDF.
   - **The PDF tests** (0018's, and T10's) are in the slow tier, skipped when `to_pdf` raises `PandocMissing`,
     as on the workflow's runners; they check the numbers and the figures.
   - **Nothing to install on the owner's Mac.** The get-started guide gives pandoc and a LaTeX with lualatex as
     an optional install, in staged steps (step 13).
9. **Take import-linter's view of standard-library imports** as §10 needs it (checked at step 12, above), with
   no AST test for AR2's and AR5's lists; the first build step's AR2 contract confirms it on EMA's own code.

## Alternatives considered

- **Python 3.14 only:** one version to test, but a model package without 3.14 wheels couldn't be a Python
  function.
- **Python 3.12 and newer:** the widest, but on library versions that stop being released, and three versions
  to test.
- **No documentation site in v2.0:** guides read on GitHub, Sphinx added later in about half a day; the owner
  chose the API reference now.
- **MkDocs:** its Material theme is in maintenance mode.
- **A separate source directory for the site** (`docs/site/`): no exclusions, but the guides would have to be
  included from outside it.
- **Checks on every push:** about 30 minutes per push; the full local tests already gate a step.
- **No continuous integration:** Linux and Python 3.13 untested.
- **setuptools or hatchling as the build backend:** both work; `uv_build` needs no configuration for a
  `src/` layout, and includes the package's data files.
- **pdflatex:** fails on the reports' Unicode. **TeX Live's DejaVu Serif:** missing from BasicTeX.
- **All of §10's contracts from the first build step, with missing layers marked optional:** one edit fewer
  later, but a contract that checks nothing yet reads as if it did.

## Consequences

- **`../../CLAUDE.md`:** the commands, as item 6 (Layers joins the fast tier; Docs filled in).
- **`../design/architecture.md`:** §3's `PandocMissing` row, and a new `PdfFailed` row (errors don't count
  against the budget of public names); §6's `to_pdf` comment (item 8); §10's `pyproject.toml` block (each
  contract grows with its packages, item 4), its standard-library bullet (seen, checked at step 12; no AST
  test for them), and its last bullet (the fast tier's command, not a Layers command); the last section's
  setup line (done, by this record).
- **`../design/contracts.md`:** the slow tier's "Contains" adds the PDF tests, skipped when `to_pdf` raises
  `PandocMissing`.
- **`../design/trust.md`:** T10's test, "(when pandoc is installed)" becomes "(when `to_pdf` doesn't raise
  `PandocMissing`)".
- **`../design/scope.md`:** the Reports row and the dependencies row: "pandoc and lualatex".
- **0018's status:** "accepted; its step-12 plan amended by 0059".
- **`../../TODO.md`:** step 12 done, its pandoc and LaTeX plan moved to step 13's get-started guide; the first
  plan includes the repository's scaffolding.
- **`../../STATUS.md`:** OD-17 and OD-18 decided (0059); step 12 done.
- **The first build step** writes `.python-version`, `pyproject.toml`, `uv.lock`, `conftest.py`,
  `docs/conf.py` and `docs/index.md`, and `.github/workflows/checks.yml`, with the import contracts its
  packages need, and reports the tiers' times.
- **Step 13:** the get-started guide's first step installs EMA with uv on Python 3.13 or newer, and gives
  pandoc and LaTeX as an optional install.
- **The owner's Mac** has uv and its own Pythons 3.14 and 3.13 (installed in staged steps for this step).
- Every new docstring must build without a Sphinx warning, so a broken docstring fails the docs command.
