# Onboarding open-source PDE and computational-science packages into EMA: installation and examples

**Contents.** 1 Purpose and use · 2 How an example becomes an EMA model · 3 Platform notes · 4 The packages (4.1 Python finite elements and volumes: FEniCSx, Firedrake, NGSolve, scikit-fem, FiPy · 4.2 C++ finite elements: deal.II, MFEM, DUNE, MOOSE, Elmer · 4.3 CFD and hyperbolic: OpenFOAM, SU2, PyClaw, Dedalus · 4.4 PETSc and others: PETSc, Devito, py-pde, SfePy, FreeFEM, and the ones left out · 4.5 more finite elements and solvers: libMesh, hIPPYlib, Trilinos, SLEPc, DifferentialEquations.jl · 4.6 CFD, AMR, plasma, multiphase, subsurface: Nek5000, AMReX, SAMRAI, WarpX, MFiX, PFLOTRAN · 4.7 engineering systems: OpenFAST, EnergyPlus, OpenSees, PyChrono, Meep, GTSAM · 4.8 weather and climate: climlab, WRF, CESM, E3SM, ICON · 4.9 machine-learned emulators: ACE, NeuralGCM, ClimaX · 4.10 chemistry and molecular dynamics: PySCF, RDKit, OpenMM, LAMMPS, NAMD, VMD · 4.11 biology and biomechanics: PhysiCell, COBRApy, CellBender, Scanpy, OpenSim, SimVascular · 4.12 visualization: PyVista, VisIt) · 5 Comparison and a suggested order.

**Status: desk research, 2026-09-24. No step in this document has been run.** Every install command comes from the project's own documentation, with its source cited, and is unverified on our machines. Anything marked **(unconfirmed)** could not be checked even in the documentation. Commands and versions change, so re-check the cited page before running a step.

**Sections 4.5–4.12 were added later the same day** from the list in `more-cse-software.md`, by the same method (desk research, sources cited, nothing run). Packages from that list that this document already covered (FEniCS, deal.II, MFEM, DUNE, FiPy, MOOSE, Dedalus, OpenFOAM, SU2, PETSc) keep their sections; SLEPc is added next to PETSc; Cantera and MODFLOW/FloPy are left out because they are already EMA applications (`docs/applications.md`).

**Spot checks after assembly (2026-09-24).** Five claims were re-read at their sources and hold:
- Firedrake's install page: "Intel Macs are no longer supported".
- Homebrew 7.0.0 moves Intel to Tier 3, with no new bottles and removal on 2027-09-01.
- conda-forge's `openfoam` is 2412, built for linux_64 only.
- MFEM's latest release is v4.10.
- EMA's `string.Template` expands `-v $EMA_WORKDIR:/work` inside one argument, which answers the question several sections below leave open. They also ask Claude Code to check it, which is now unnecessary but harmless.

The rest are as the researchers left them.

## 1. Purpose and how to use this document

EMA has three real applications, SWMM, MODFLOW 6 and Cantera (`docs/applications.md`). All three are small command-line models. This document plans the next tier: the big open-source PDE frameworks and their example collections (4.1–4.4), and then a wider set of computational-science codes: solvers, CFD and plasma, engineering systems, weather and climate, machine-learned emulators, chemistry and molecular dynamics, biology, and two visualization tools (4.5–4.12). Several of the later ones are not PDE solvers, and a few are poor fits for EMA; their sections say so and pick the smallest configuration that does fit. For each package it says:
- how to install it on the two target platforms, an **Intel Mac** and **AWS EC2** (Ubuntu 24.04);
- which 2–3 of its own examples to turn into EMA models, which inputs to vary over which ranges, which scalar output to read, and what structure EMA should find;
- a **staged set of Claude Code prompts** that do the install and the preparation later, one stage at a time, each ending at a stop condition.

Nothing here is code. The prompts ask Claude Code to write the drivers, templates and `model.json` files when the time comes, following the existing examples.

### Using the prompts

- **Open Claude Code in the EMA repo.** The prompts assume that EMA's `docs/`, `examples/` and `tests/` are readable.
- **One package at a time, one prompt per turn.** Don't paste the next stage until the current one reports success. Each prompt ends with "stop and report".
- **Give each package its own branch.** For example, `apps-<pkg>`, branched from `main`. Commit only when you've reviewed the work.
- **Isolate installs.** Put each package in its own conda env (`ema-<pkg>`) or in a pinned Docker image, and never in EMA's `.venv/`. Claude Code must never read `.env`. The prompts say so, but watch for it.
- **Ask before large or system-wide steps.** The prompts ask first before `sudo`, Homebrew changes, and downloads over 1 GB. Approve them one by one.
- **Use plan mode for the "prepare example" stage** (shift+tab). There Claude Code proposes the files it will write before writing them.
- **Keep track of spending.** The "first campaign" stage names its run count, and `ema run` asks before it runs anything. Don't use `--yes` until a model has been profiled.
- **AWS.** You launch the instance and connect with ssh yourself. Then run Claude Code on the instance in a clone of the EMA repo, and paste the "AWS" variants of the prompts.

## 2. How a package's example becomes an EMA model

These are the constraints each example has to fit. They come from `src/ema/core/models/cli.py`, `parsers.py`, `_sandbox.py` and the design rules in `CLAUDE.md`.

- **The command-line model is the default.**
  - EMA renders the input files from `string.Template` templates and copies the static files. It then runs the command in a fresh run directory, with no shell and with stdin from `/dev/null`, and reads **one scalar** with a `regex`, `json`, `csv` or isolated `python` parser.
  - **One output per `model.json`.** Several outputs of the same example need several `model.json` files, which can share their templates, as `examples/beam/`'s variants do.
- **`$` in templates.** Placeholders are `$name` or `${name}`, and a literal dollar sign must be written as `$$`. OpenFOAM dictionaries (`$internalField`, `#include`), MOOSE `.i` files (`${...}` brace expressions) and some `.prm` files use `$`. Every such template needs its literal `$` escaped, or the substitution fails. A common alternative is a small driver that reads a `key = value` deck and edits the package's own file, as Cantera's `ignite.py` does.
- **Python packages still run as command-line models.** FEniCSx, Firedrake, NGSolve, FiPy, PyClaw and Dedalus live in their own conda env, not EMA's venv. So the pattern is a command whose first element is **the absolute path of that env's `python`**, running a short driver in the model directory. The version hash covers the driver, but not the interpreter or the installed package, a limitation CLAUDE.md already lists. The `model.json` description should therefore record the package version, and the driver should print it into `stdout.txt`.
- **Static files are copied flat, by file name** (`cli.py`), while `input_files` destinations may include subdirectories (`system/controlDict`). A case directory (OpenFOAM's `0/`, `constant/`, `system/`) therefore has to be all templates (with no placeholders if need be, but every `$` escaped), or a static archive that a driver unpacks.
- **Command arguments are templated too.** `"-grashof", "$grashof"` puts an input straight onto the command line, which suits PETSc, MFEM and FreeFEM (`getARGV`) with no deck at all. A relative argument naming a file next to `model.json` is passed as its absolute host path, unless the run directory holds a copy, so **a driver run inside Docker must be a static file** (the container can't see the host path).
- **Compiled codes** (deal.II, MFEM, DUNE, MOOSE, SU2, PETSc, OpenFOAM, Elmer, Nektar++) take a parameter file or command-line options. A `.prm`, `.cfg`, `.i`, `.sif` or OpenFOAM dictionary becomes a template, and command-line options can carry `$placeholders` directly in the command.
  - Compiled example binaries given by absolute path are not hashed.
  - A binary built inside the model directory, or a wrapper script there, is hashed.
- **Environment.**
  - Variables from `.env` are withheld from every model program. `PATH` and the rest of the environment pass through.
  - A spec's `env` can set `OMP_NUM_THREADS=1` (recommended: EMA already runs runs in parallel with `-j N`) and MPI variables.
  - An MPI launcher (`mpirun -n 2 …`) can be the command, but serial runs are the default: parallelism belongs to EMA's scheduler.
- **Docker as the command.**
  - `["docker", "run", "--rm", "-v", "$EMA_WORKDIR:/work", "-w", "/work", "<image>@sha256:<digest>", …]` works today as an ordinary command (`$EMA_WORKDIR` is substituted like an input). The analyst approves the command, but EMA doesn't hash the image, so pin it by digest.
  - Run the container as your own user (`--user 501:20`, your numeric ids), so the files it writes into the run directory stay readable. There's no shell, so `$(id -u)` won't expand, and a literal `$` would need `$$` anyway; a wrapper script in the model directory can compute it instead, and the hash covers the wrapper.
  - Container start-up adds about 0.5–2 s per run **(unconfirmed; measure with `ema profile`)**.
- **Speed.** Aim for a laptop-size configuration under about 10 s per run. For a sense of scale, a Sobol analysis with `n_base` 256 and 4 inputs is 1,536 runs, about 4 hours of serial CPU time at 10 s per run, or 1 hour with `-j 4`.
- **Noise and determinism.** EMA assumes a deterministic model unless `repeat` shows otherwise.
  - Iterative-solver tolerances make the output a slightly rough function of its inputs. Tighten the tolerances (relative 1e-10 or so) so that this roughness stays below what the diagnostics resolve, or measure it with `repeat` and pass `output_noise`.
  - Adaptive mesh refinement, remeshing with geometric inputs, and time-step control make outputs **piecewise smooth**. The kinks and jumps `nonsmooth` and `curve1d` report are then real features of the discretization, not bugs. The example tables mark where to expect them.
  - Parallel reductions (MPI, threaded assembly) can change the last digits from one run to the next. Run serially.
- **Read binary output in the driver, not in a `python` output parser.** EMA's `python` parser runs in a child of EMA's own interpreter (`sys.executable` in `_sandbox.py`), so it can import only what EMA's `.venv` has. netCDF (WRF, CESM, E3SM, ICON), VTK (PyVista), HDF5 and similar formats are therefore read by the driver or a wrapper script in the model's own environment, which prints one line (`EMA_OUTPUT <value>`) for a `regex` parser. Sections 4.8 and 4.12 rely on this.
- **Failures are data.** A run that diverges or times out is recorded as failed (NaN), and every diagnostic tolerates that. Set `timeout_s` to a few times the profiled run time.

## 3. Platform notes

### Intel Mac (macOS x86_64)

Intel support is being withdrawn across the ecosystem. **Homebrew 7.0.0 (2026-09-13) moved Intel Macs to Tier 3:** no CI, no new bottles, and support ends in September 2027. GCC and gfortran already lost their Intel bottles, so **this document never uses Homebrew on the Intel Mac.** conda-forge still builds `osx-64` (it needs macOS ≥ 11) and has announced no end date; Anaconda's *defaults* channel is phasing Intel out, so use Miniforge only. Several projects now publish Apple-Silicon-only binaries (the deal.II `.dmg`, OpenFOAM.app after v2506, MFEM bottles, PyMFEM and Clawpack wheels, FreeFEM after 4.15, numba after 0.62). Each package section says which route still works. Where none does, the route is **Docker Desktop**, which on an Intel Mac runs `linux/amd64` images natively, with no emulation penalty, though in a Linux VM with its own memory limit (raise it to 8 GB or more in Settings → Resources). Install Miniforge (`https://github.com/conda-forge/miniforge`) as the conda for every conda route; use `mamba`/`conda` from it, never EMA's `.venv`.

### AWS EC2 (Ubuntu 24.04 LTS, x86_64)

- **Instance type.** A compute-optimized instance, such as `c7i.2xlarge` (8 vCPU, 16 GB), is enough for every laptop-size example here. Use `c7i.8xlarge` for OpenFOAM or MOOSE campaigns with `-j 16` or more. Check the current prices on the AWS pricing page **(unconfirmed; prices vary by region)**.
- **Storage.** Use a gp3 EBS volume of at least 100 GB, since the Docker images and Spack builds are large. Keep the EMA workspace on EBS, not on EFS or NFS: SQLite's write-ahead log is unsupported on network filesystems, and the fallback journal is slower (the `EMA_SQLITE_WAL` note in CLAUDE.md).
- **Install routes, in order of preference:**
  1. apt packages, where they are current (deal.II and OpenFOAM have PPAs or repositories);
  2. conda-forge (Miniforge);
  3. Docker (`docker.io` from apt);
  4. Spack, for C++ stacks that need a specific build (`https://spack.readthedocs.io`).
- **EMA itself.** Clone the repo, create the Python 3.14 venv, and install it following `CLAUDE.md`'s Commands section.
- **Getting results back.** `ema export <id>` writes a `.npz`. Copy the workspace, or its `report.md` and figures, back with `scp` or `rsync`.
- **Cost.** A campaign of about 2,000 runs at 10 s per run, with `-j 8`, takes about 45 minutes of instance time. Stop the instance when it's idle.

## 4. The packages

Each package follows the same template: what it is, installation on the Intel Mac and on AWS, preparing 2–3 of its examples for EMA, the staged Claude Code prompts, and gotchas with sources. Each group opens with the notes its researcher found common to the group.


### 4.1 Python finite-element and finite-volume packages

Desk research, checked 2026-09-24. Nothing here was installed or run. Estimated run times are estimates from the examples' sizes, not measurements: every one is marked *(estimate)* and must be confirmed with `ema profile`. Cross-cutting facts used below:

- **Homebrew on Intel Macs**: Homebrew 7.0.0 (13 Sep 2026) moved macOS Intel x86_64 to Tier 3: no CI and no new bottles. Support ends entirely in September 2027. So any route that needs `brew install` of compiled libraries on an Intel Mac may mean building from source. Sources: https://brew.sh/2026/09/13/homebrew-7.0.0/, https://docs.brew.sh/Support-Tiers
- **conda-forge on Intel Macs**: conda-forge still builds osx-64 (Miniforge ships a macOS x86_64 installer), and has required macOS ≥ 11.0 since February 2026. It has announced no osx-64 end date (its news feed through 31 Aug 2026 has none). Anaconda's *defaults* channel stopped new osx-64 builds in mid-2025, so use conda-forge/Miniforge only. Sources: https://github.com/conda-forge/miniforge, https://conda-forge.org/news/2026/02/06/macOS-11/, https://conda-forge.org/news/, https://www.anaconda.com/blog/intel-mac-package-support-deprecation
- **Docker Desktop** supports Intel Macs (4 GB RAM minimum) on the current and two previous major macOS releases. Source: https://docs.docker.com/desktop/setup/install/mac-install/
- **EMA wiring**: these packages are installed in their own conda env, venv, or Docker image, never EMA's `.venv`. EMA's `$EMA_PYTHON` is EMA's own interpreter, so it is **not** the right command here. The command is the env's absolute `python` path (or `docker run ...`) followed by a driver script next to `model.json`. That makes the interpreter path the one machine-specific line in each `model.json` (see `docs/guides/input_deck_model.md`, "The command").
- **AWS instance**: every example below is small and serial. A `c7i.xlarge` (4 vCPU, 8 GB) is enough for `-j 4`, and a `c7i.2xlarge` for `-j 8`. Add 30 GB gp3 disk if you use Docker images. Set `OMP_NUM_THREADS=1` (and for PETSc-based codes, run one MPI rank per run) so EMA's parallel runs don't oversubscribe cores.

---

#### FEniCSx (DOLFINx)

**What it is.** FEniCSx is a general finite-element framework. You write the weak form in UFL (Python), and FFCx compiles it just-in-time to C. DOLFINx is the C++/Python core (it uses PETSc). License: LGPL-3.0-or-later. Current release **DOLFINx 0.11.0** (0.11.0.post0 is the same code with a docs fix). There are two example collections: 26 official demos at https://docs.fenicsproject.org/dolfinx/main/python/demos.html (source in `python/demo/` of https://github.com/FEniCS/dolfinx), and the **FEniCSx tutorial** by J. S. Dokken (about 35 notebooks, which target 0.11.0.post0) at https://jsdokken.com/dolfinx-tutorial/ (source https://github.com/jorgensd/dolfinx-tutorial, as `.py` and `.ipynb`).
*Legacy FEniCS* (DOLFIN 2019.1.0, April 2019) is effectively frozen: "Updates are now very rarely made to the legacy FEniCS library", and the project recommends FEniCSx (https://fenicsproject.org/download/). Don't onboard it. Its old tutorials (the FEniCS book, `ft01_poisson.py`, ...) have direct equivalents in Dokken's tutorial.

**Install on an Intel Mac.** conda-forge builds `fenics-dolfinx` 0.11.0 for osx-64 (Python 3.12 builds with the stable ABI), so no Docker is needed.
1. Install Miniforge (osx-64 installer; needs macOS ≥ 11) if there's no conda/mamba:
   ```bash
   curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
   bash Miniforge3-MacOSX-x86_64.sh -b -p "$HOME/miniforge3"
   ```
2. Create a dedicated env with a pinned version:
   ```bash
   ~/miniforge3/bin/mamba create -n fenicsx-0.11 -c conda-forge python=3.12 fenics-dolfinx=0.11.0 mpich
   ```
   (`pyvista` from the official command is only for plotting. Leave it out.)
3. Check:
   ```bash
   ~/miniforge3/envs/fenicsx-0.11/bin/python -c "import dolfinx, sys; print(dolfinx.__version__, sys.platform)"
   ```
Known problems: FFCx compiles forms with a C compiler at first use. If the env has none, the first solve fails with a compiler error. Then add `c-compiler` from conda-forge or install the Xcode Command Line Tools *(unconfirmed which one the feedstock expects)*. The JIT cache sits in `~/.cache/fenics`, so the first run of each new form takes seconds longer.
Sources: https://fenicsproject.org/download/, https://github.com/FEniCS/dolfinx#installation, https://github.com/conda-forge/fenics-dolfinx-feedstock (osx_64 in the build matrix), https://prefix.dev/channels/conda-forge/packages/fenics-dolfinx (0.11.0 osx-64 builds), recipe skip rules at https://raw.githubusercontent.com/conda-forge/fenics-dolfinx-feedstock/main/recipe/recipe.yaml.

**Install on AWS (Ubuntu 24.04 EC2).**
1. PPA (native, system Python 3.12). The PPA publishes `fenics-dolfinx 1:0.11.0.post0-2~ppa1~noble1` for noble (uploaded 2026-09-04):
   ```bash
   sudo add-apt-repository ppa:fenics-packages/fenics
   sudo apt update
   sudo apt install fenicsx
   /usr/bin/python3 -c "import dolfinx; print(dolfinx.__version__)"
   ```
2. Alternatively, use conda exactly as on the Mac, with the `Miniforge3-Linux-x86_64.sh` installer (keeps the version identical across machines. Recommended.)
3. Docker fallback: `dolfinx/dolfinx:v0.11.0` (amd64 and arm64, pushed 2026-06-11; `stable` currently points to the same release). Pin the digest:
   ```bash
   docker pull dolfinx/dolfinx:v0.11.0
   docker buildx imagetools inspect dolfinx/dolfinx:v0.11.0   # copy the sha256 digest
   docker run --rm -v "$PWD":/work -w /work dolfinx/dolfinx@sha256:<digest> python3 -c "import dolfinx; print(dolfinx.__version__)"
   ```
Sources: https://launchpad.net/~fenics-packages/+archive/ubuntu/fenics, https://fenicsproject.org/download/, https://hub.docker.com/r/dolfinx/dolfinx/tags, https://github.com/FEniCS/dolfinx#docker-images.

**Preparing the examples for EMA.** The parameters are Python variables or `fem.Constant`s at the top of each tutorial script. The recipe:
- Turn the script into a driver `run.py` that reads a small key = value deck (rendered from a `string.Template`, like `examples/cantera/ignition.template`).
- Remove the plotting (`pyvista`, `matplotlib`) and the file output (`XDMFFile`, `VTXWriter`).
- Compute one scalar with `fem.assemble_scalar(fem.form(...))`, reduced over ranks with `mesh.comm.allreduce`, and print it as `output = <value:.12e>`.
- Run serially (no `mpirun`).
- Shrink the mesh through `create_unit_square(..., n, n)` / `create_box` counts or gmsh's `CharacteristicLengthMax`.
- Keep the mesh fixed: a geometric input that changes element counts or re-meshes makes jumps in the output.
- Prefer integrals over maxima of nodal values: a max jumps between nodes as the peak moves.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Deflection of a membrane, `chapter1/membrane_code.py` (https://jsdokken.com/dolfinx-tutorial/chapter1/membrane_code.html) | Poisson on a unit disk (gmsh mesh), Gaussian pressure load `p = A exp(-β²(x² + (y−R0)²))`. The tutorial uses A = 4, β = 12, R0 = 0.3, h = 0.05 | `A` 4 [1, 8]; `beta` 12 [4, 20]; `R0` 0.3 [0, 0.6] (all in the Python constants, which the deck feeds); mesh fixed at h = 0.1 | total deflection ∫w dx | exactly linear in `A` (w ∝ A), so under `log_output` A has exponent 1; decreasing in `beta` (narrower load) and in `R0` (load nearer the clamped edge); A multiplies the others, so sobol shows interactions that vanish on a log output | 1–3 s after the JIT cache is warm; 5–20 s for the first run *(estimate)* | cli (env python + `run.py`) | regex on stdout |
| Linear elasticity of a clamped beam, `chapter2/linearelasticity_code.py` (https://jsdokken.com/dolfinx-tutorial/chapter2/linearelasticity_code.html) | 3D cantilever under gravity, hex box mesh [20, 6, 6], LU. Tutorial: L = 1, W = 0.2, μ = 1, λ = 1.25, ρ = 1, g = 0.4(W/L)² | `mu` 1 [0.5, 2]; `lambda_` 1.25 [0.5, 5]; `g` 0.016 [0.005, 0.05]; `W` 0.2 [0.1, 0.3] (element counts fixed, so W moves nodes only) | tip deflection: mean of −u_z over the end face x = L | exactly linear in `g`; roughly homogeneous of degree −1 in (μ, λ), with λ weak (Poisson effect), so λ is near-negligible; strong decrease with `W` (beam theory ≈ W⁻²): `linear_coeffs(log_output=True)` should find a near power law | 1–2 s *(estimate)* | cli | regex |
| Robin, Neumann and Dirichlet conditions, `chapter3/robin_neumann_dirichlet.py` (https://jsdokken.com/dolfinx-tutorial/chapter3/robin_neumann_dirichlet.html) | steady heat conduction on a 10×10 unit square with mixed boundary conditions. Tutorial: κ = 1, r = 1000, manufactured data | `kappa` 1 [0.1, 10] (log); `r` (Robin transfer coefficient) 100 [1, 10⁴] (log); `s` (ambient temperature, replacing the manufactured `s`) 1 [0, 2]; `f` (constant source replacing the manufactured one) 1 [0, 10] | mean temperature ∫u dx | affine in `s` and `f`; monotone and **saturating** in `r` (a plateau as the Robin boundary approaches Dirichlet), with the transition set by the Biot-like ratio r/κ: interaction between κ and r | < 1 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard FEniCSx (DOLFINx 0.11.0) examples into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, Homebrew version, Docker (docker version, whether the daemon runs), C compilers (cc --version), any MPI (mpiexec --version), and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, conda-forge env `fenicsx-0.11` (osx-64 builds of 0.11.0 exist). On Ubuntu 24.04, the same conda env, with the fenics-packages PPA or the pinned docker image dolfinx/dolfinx:v0.11.0 as fallbacks. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install FEniCSx on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel) and create a named env: `mamba create -n fenicsx-0.11 -c conda-forge python=3.12 fenics-dolfinx=0.11.0 mpich`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Then check with `<env>/bin/python -c "import dolfinx; print(dolfinx.__version__)"` and report the env's absolute python path. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install FEniCSx on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64 installer) and a named env `fenicsx-0.11` with `python=3.12 fenics-dolfinx=0.11.0 mpich` from conda-forge, the same as on my Mac. Never use EMA's .venv, and never read .env. Ask before any sudo, and before downloads over 1 GB. If conda fails, report and propose (don't run) either `ppa:fenics-packages/fenics` + `apt install fenicsx` (0.11.0 for noble) or docker `dolfinx/dolfinx:v0.11.0` pinned by digest. Check with `import dolfinx; print(dolfinx.__version__)` and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — FEniCSx smoke test. In a scratch directory outside the EMA repo, download the Poisson demo of DOLFINx 0.11.0 (python/demo/demo_poisson.py from the v0.11.0 tag of github.com/FEniCS/dolfinx), and run it with the fenicsx-0.11 env's python, serially, with plotting disabled if it needs pyvista. Time it twice, so the second run shows the time with a warm JIT cache (~/.cache/fenics). Report the printed output, both wall times, and where the JIT cache is. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the FEniCSx membrane example for EMA. Enter plan mode first and show me the plan. Source: chapter1/membrane_code.py of github.com/jorgensd/dolfinx-tutorial (for DOLFINx 0.11). Copy it into examples/fenicsx/membrane/ as a driver run.py that reads a key = value deck rendered from membrane.template (inputs A = 4 [1, 8], beta = 12 [4, 20], R0 = 0.3 [0, 0.6]), builds the gmsh disk with a fixed CharacteristicLength of 0.1, runs serially, has no plotting or file output, and prints `total deflection = <∫w dx, %.12e>`. Follow docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/ (deck + driver + regex on stdout). The command is the fenicsx-0.11 env's absolute python path (not $EMA_PYTHON) and run.py. Set OMP_NUM_THREADS=1 in env and timeout_s 300. Check by hand that A = 4, beta = 12, R0 = 0.3 matches the tutorial, and that doubling A doubles the output. Then run `ema profile examples/fenicsx/membrane/model.json -n 5` and report time per run (first and warm). Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the FEniCSx clamped-beam example. Plan mode first. Source: chapter2/linearelasticity_code.py of the DOLFINx tutorial (0.11). Put it in examples/fenicsx/beam/. Inputs through a deck: mu = 1 [0.5, 2], lambda_ = 1.25 [0.5, 5], g = 0.016 [0.005, 0.05], W = 0.2 [0.1, 0.3]. Keep the [20, 6, 6] hex mesh counts fixed (W only moves the nodes) and the LU solver. Output: the mean of -u_z over the face x = L, printed as `tip deflection = %.12e`. Remove XDMF and pyvista output. Command-line model with the fenicsx-0.11 env's absolute python path, like examples/cantera. Check that doubling g doubles the output. Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the FEniCSx Robin example. Plan mode first. Source: chapter3/robin_neumann_dirichlet.py of the DOLFINx tutorial (0.11). Put it in examples/fenicsx/robin/. Keep its boundary layout and 10×10 mesh, but replace the manufactured data with constants: kappa = 1 [0.1, 10] (scale log), r = 100 [1, 1e4] (scale log), ambient s = 1 [0, 2], source f = 1 [0, 10]. Keep any Dirichlet and Neumann data as fixed constants you choose and state them. Output: the mean temperature ∫u dx (the unit square has area 1), printed as `mean temperature = %.12e`. Command-line model as in examples/cantera. Then `ema profile ... -n 5`, and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 5 — first FEniCSx campaign. For examples/fenicsx/beam/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on W (n 9), and morris (n_traj 6). Use `ema estimate` to report the run count and estimated time, and ask me before running `ema run`. After it runs, report: whether repeats are identical, whether g is linear, whether lambda_ is (possibly) negligible, and what morris ranks first. Then suggest (don't run) linear_coeffs with log_output. Stop and report.
```

```text
Stage 6 — FEniCSx troubleshooting. An EMA FEniCSx model (examples/fenicsx/<example>) fails or is slow. Diagnose read-only first: run the driver by hand in a copied run directory with the fenicsx-0.11 env's python. Check for FFCx/cffi JIT compiler errors (no C compiler in the env), a JIT cache that isn't writable or is rebuilt each run (~/.cache/fenics; the time of the first run vs later ones), PETSc/MPI start-up errors (mpich vs openmpi in the env; don't launch with mpirun), gmsh import errors, threads oversubscribed (OMP_NUM_THREADS), a regex that doesn't match the printed line, and `could not start` (a wrong interpreter path in model.json). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License LGPL-3.0: fine for use as an external program.
- JIT: the first run of each new form compiles C code (several seconds). The cache is in `~/.cache/fenics`. Inputs passed as `fem.Constant` don't change the form, so later runs reuse it. Inputs baked into the UFL as Python floats may recompile each run. Under Docker with `--rm`, mount a persistent cache volume or every run recompiles.
- MPI: run serially. Parallel reductions and partitioning change the rounding, so results would depend on the rank count.
- Determinism: direct LU is deterministic. With iterative solvers (CG/AMG demos), the output jitters at the level of the tolerance: tighten `ksp_rtol` or declare `output_noise`.
- gmsh meshes: a geometric input re-meshes the domain, which makes `nonsmooth` jumps. Keep geometry fixed, or move nodes with a fixed topology.
- API churn: DOLFINx changes its Python API between minor releases (0.10 → 0.11 had "significant Python API changes"). Pin 0.11.0 and use the tutorial version that matches it.
- Legacy FEniCS 2019.1: unmaintained, so don't use it.
- Sources: https://fenicsproject.org/download/, https://github.com/FEniCS/dolfinx, https://github.com/FEniCS/dolfinx/releases, https://docs.fenicsproject.org/dolfinx/main/python/demos.html, https://jsdokken.com/dolfinx-tutorial/, https://github.com/jorgensd/dolfinx-tutorial, https://github.com/conda-forge/fenics-dolfinx-feedstock, https://prefix.dev/channels/conda-forge/packages/fenics-dolfinx, https://launchpad.net/~fenics-packages/+archive/ubuntu/fenics, https://hub.docker.com/r/dolfinx/dolfinx/tags

---

#### Firedrake

**What it is.** Firedrake is an automated finite-element system: UFL weak forms, code generated through TSFC/PyOP2, and PETSc solvers. Its demos are unusually rich for geoscience and fluid dynamics. License: LGPL-3.0-or-later, with PyOP2 under BSD-3 (https://github.com/firedrakeproject/firedrake/blob/main/LICENSE). Current release **2026.4.2** (docs show 2026.4.3.dev0). There are 40 demos (8 introductory, 32 advanced), listed at https://www.firedrakeproject.org/documentation.html, each at `https://www.firedrakeproject.org/demos/<name>.py.html` with a downloadable `.py`. **Why it qualifies:** it's the closest comparable package to FEniCSx with a rich collection of examples (Burgers, shallow water, Rayleigh–Bénard, Navier–Stokes, ...), but **no Intel-Mac support** (see below). It is still worth onboarding through Docker on the Mac and natively on AWS.

**Install on an Intel Mac.** The install page says "Intel Macs are no longer supported" (https://www.firedrakeproject.org/install.html), and the native route needs Homebrew, which is now Tier 3 on Intel. **Route: Docker Desktop.**
1. Install Docker Desktop for Mac (Intel chip) from https://docs.docker.com/desktop/setup/install/mac-install/.
2. Pull the pinned release image (amd64 available) and record its digest:
   ```bash
   docker pull firedrakeproject/firedrake-vanilla-default:2026.4.2
   docker buildx imagetools inspect firedrakeproject/firedrake-vanilla-default:2026.4.2
   ```
3. Check:
   ```bash
   docker run --rm firedrakeproject/firedrake-vanilla-default@sha256:<digest> python3 -c "import firedrake; print(firedrake.__version__)"
   ```
   (`firedrake-vanilla-default` is the plain real-mode build. `firedrakeproject/firedrake` adds extra packages.) The image is likely more than 1 GB *(size unconfirmed)*. The Python interpreter's path inside the image is also unconfirmed: it may be a venv, not `/usr/bin/python3`. Check with `docker run ... which python3`.
Known problems: Docker Desktop's file sharing must include the EMA workspace path. Each `docker run` adds container start-up time (about 1 s *(estimate)*) plus Firedrake's import and kernel compilation, unless the cache is mounted (see Gotchas).
Sources: https://www.firedrakeproject.org/install.html, https://hub.docker.com/r/firedrakeproject/firedrake-vanilla-default/tags

**Install on AWS (Ubuntu 24.04 EC2).** Ubuntu is officially supported. Native install (it builds PETSc, which takes a long time: roughly 30–60 min on 4 vCPUs *(estimate)*):
1. ```bash
   curl -O https://raw.githubusercontent.com/firedrakeproject/firedrake/release/scripts/firedrake-configure
   sudo apt install $(python3 firedrake-configure --show-system-packages)
   git clone --branch $(python3 firedrake-configure --show-petsc-version) https://gitlab.com/petsc/petsc.git
   cd petsc && python3 ../firedrake-configure --show-petsc-configure-options | xargs -L1 ./configure
   make PETSC_DIR=$PWD PETSC_ARCH=arch-firedrake-default all && cd ..
   python3 -m venv ~/venv-firedrake && . ~/venv-firedrake/bin/activate
   pip cache purge
   export $(python3 firedrake-configure --show-env)
   pip install --no-binary h5py 'firedrake[check]==2026.4.2'
   ```
   (Pinning `==2026.4.2` must match the PETSc version that `firedrake-configure` from the `release` branch asks for. If it doesn't, drop the pin and record the version *(unconfirmed)*.)
2. Check: `~/venv-firedrake/bin/python -c "import firedrake"`, and `firedrake-check` (from the `[check]` extra).
3. Docker fallback (recommended if the build fails): the same pinned `firedrakeproject/firedrake-vanilla-default:2026.4.2` image (amd64), as on the Mac. Instance: `c7i.2xlarge` to build PETSc faster, and it can then run `-j 8`.
Sources: https://www.firedrakeproject.org/install.html, https://hub.docker.com/r/firedrakeproject/firedrake-vanilla-default/tags

**Preparing the examples for EMA.** Parameters are Python variables or `Constant`s in the demo script. The recipe:
- Make a driver `run.py` that reads a key = value deck, drops the `VTKFile(...).write` and plotting calls, computes one scalar with `assemble(...)`, and prints it.
- Shrink `UnitSquareMesh(n, n)`, and keep the **number of time steps fixed** (dt = T/steps), so no input changes the step count (that would make jumps).
- With Docker, the command is `docker run --rm -v <run dir>:/work -w /work -v <cache volume>:/root/.cache <image@digest> python3 run.py deck.txt`. How EMA passes the run directory to a Docker command (`$EMA_WORKDIR` in the argument list) must be checked against `docs/guides/input_deck_model.md`. The driver script must be in the run directory or mounted too.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Burgers equation, `burgers.py` (https://www.firedrakeproject.org/demos/burgers.py.html) | 2D viscous Burgers on a unit square, P2 vector field, backward Euler. Demo: n = 30, ν = 1e-4, dt = 1/n, end = 0.5, initial u = (sin πx, 0) | `nu` 0.01 [1e-3, 0.1] (log); `U0` (initial amplitude) 1 [0.5, 2]; `T` (end time) 0.5 [0.2, 0.8]; fixed n = 30 and 20 steps | kinetic energy ½∫\|u\|² dx at T | decreasing in `nu` and `T`, increasing in `U0`. By Burgers' scaling (u = U0·v(x, U0 t; ν/U0)), energy/U0² depends only on U0·T and ν/U0, so `active_subspace` on log inputs should find about **2 directions among 3**. At small ν a steep front forms (smooth but sharp), so curvature is large near ν = 1e-3 | 5–15 s including import *(estimate)* | cli (docker on Mac, venv python on AWS) | regex |
| Rayleigh–Bénard convection, `rayleigh-benard.py` (https://www.firedrakeproject.org/demos/rayleigh-benard.py.html) | steady Boussinesq in a differentially heated square cavity: T = 1 on the left wall (id 1), T = 0 on the right (id 2), no-slip. Taylor–Hood + P1, Newton. Demo: Ra = 200, Pr = 6.8, N = 128 | `Ra` 200 [20, 2000] (log); `Pr` 6.8 [0.7, 20] (log); N reduced to 32 | Nusselt number on the hot wall, −∫ ∂T/∂x ds over id 1 | monotone increasing in `Ra`, with Nu ≈ 1 (conduction) at low Ra and curving upward; `Pr` expected to have a smaller effect *(to be confirmed by the run)*; watch for Newton failures at the top of the Ra range (NaN runs) | 5–20 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only) for Firedrake 2026.4.2. Report: OS/version, uname -m, Docker (version, daemon running, file-sharing settings if visible, free space in Docker's disk image), conda/mamba, Homebrew, compilers, MPI, and free disk space. Don't install anything, and don't read .env. Recommend a route: an Intel Mac is not supported natively by Firedrake, so Docker with firedrakeproject/firedrake-vanilla-default:2026.4.2 pinned by digest. On Ubuntu 24.04, the native firedrake-configure + pip install in ~/venv-firedrake, or the same Docker image as a fallback. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install Firedrake on this Intel Mac via Docker. Docker Desktop must already run (if not, stop and tell me; don't install it yourself). Tell me the image size, and ask me before pulling if it is over 1 GB. Then `docker pull firedrakeproject/firedrake-vanilla-default:2026.4.2`, get its sha256 digest with `docker buildx imagetools inspect`, and verify with `docker run --rm <image>@sha256:<digest> python3 -c "import firedrake; print(firedrake.__version__)"`. Also report `which python3` inside the image. Never touch EMA's .venv, and never read .env. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install Firedrake on this AWS EC2 instance (Ubuntu 24.04 x86_64), natively, following https://www.firedrakeproject.org/install.html: firedrake-configure from the release branch, the apt system packages (ask me before sudo), clone and build PETSc at the version firedrake-configure names, create ~/venv-firedrake, export firedrake-configure --show-env, and `pip install --no-binary h5py 'firedrake[check]'` (pin 2026.4.2 if it matches the PETSc version; report what you pinned). Never use EMA's .venv, and never read .env. Run long builds in the background and report progress. Verify with `firedrake-check`. Stop at the first error and report it; propose (don't run) the Docker fallback firedrakeproject/firedrake-vanilla-default:2026.4.2 pinned by digest. Don't continue to the next stage.
```

```text
Stage 3 — Firedrake smoke test. Download the helmholtz.py demo for Firedrake 2026.4.2 (www.firedrakeproject.org/demos/helmholtz.py) to a scratch directory outside the EMA repo, and run it with the installed route (docker run --rm -v "$PWD":/work -w /work <image@digest> python3 helmholtz.py on the Mac, ~/venv-firedrake/bin/python on AWS). Run it twice: once with no cache, and once with a named Docker volume mounted at the image's cache directory (find where PyOP2/TSFC cache kernels, e.g. ~/.cache). Report the output and both wall times, split into container start, import, and solve if you can. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the Firedrake Burgers example for EMA. Plan mode first. Source: demos burgers.py (Firedrake 2026.4.2). Copy it to examples/firedrake/burgers/ as run.py, which reads a key = value deck rendered from burgers.template with inputs nu = 0.01 [1e-3, 0.1] (scale log), U0 = 1 [0.5, 2] (initial condition U0*sin(pi x)), T = 0.5 [0.2, 0.8]. Fix n = 30 and exactly 20 backward-Euler steps (dt = T/20). Remove the VTK output, and print `energy = <0.5*assemble(inner(u,u)*dx), %.12e>`. Set it up as an EMA command-line model following docs/applications.md, docs/guides/input_deck_model.md and examples/cantera. On the Mac the command is docker run --rm with the run directory mounted at /work, a persistent cache volume, and the image pinned by digest (check how EMA passes the run directory and whether run.py must be a static file); on AWS it is ~/venv-firedrake/bin/python. Set OMP_NUM_THREADS=1 and timeout_s 600. Then `ema profile examples/firedrake/burgers/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the Firedrake Rayleigh–Bénard example. Plan mode first. Source: the rayleigh-benard.py demo (2026.4.2). Put it in examples/firedrake/rayleigh_benard/. Inputs through a deck: Ra = 200 [20, 2000] (scale log), Pr = 6.8 [0.7, 20] (scale log). Mesh N = 32, and keep the demo's boundary conditions (hot wall id 1, cold wall id 2) and solver. Output: the Nusselt number on the hot wall, -assemble(grad(T)[0]*ds(1)), printed as `Nu = %.12e`. If Newton fails, the driver must exit non-zero (so EMA records a failed run) rather than print a number. Same command pattern as the Burgers model. Check Nu at Ra = 20 is close to 1. Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 5 — first Firedrake campaign. For examples/firedrake/burgers/model.json, write a campaign with repeat (n_points 2, replicates 2), curve1d on nu (n 9), and morris (n_traj 5). Report `ema estimate` (runs and time), and ask me before `ema run -j <cores/2>`. Afterwards report: repeatability, monotonicity in nu, the morris ranking, and any kinks or jumps. Suggest (don't run) active_subspace on the log inputs to test the expected 2-direction structure. Stop and report.
```

```text
Stage 6 — Firedrake troubleshooting. An EMA Firedrake model fails, times out, or is slow. Diagnose read-only: rerun the driver by hand in a copy of a failed run directory with the same command. Check: Docker file sharing and mounts (the run directory visible at /work? run.py present?), the kernel cache not persisted (each run recompiles; compare times with and without the cache volume), PETSc/MPI errors, threads oversubscribed (OMP_NUM_THREADS, too many -j for the Docker VM's CPUs and memory), Newton divergence at extreme inputs, a regex mismatch, or the image digest changed. Report the cause and a proposed fix. Ask before editing model.json or pulling images.
```

**Gotchas and sources.**
- No Intel-Mac native install. On AWS the native build compiles PETSc (long), so Docker is the pragmatic route on both machines.
- Code generation: Firedrake compiles kernels at first use and caches them in the user's cache directory. Under `docker run --rm` the cache is lost, so mount a named volume. Import time alone is several seconds *(estimate)*, which dominates small runs.
- EMA's `-j N` with Docker: each run is a container, and Docker Desktop's VM CPU and memory limits cap the real parallelism.
- Determinism: serial direct solves are repeatable. Newton with iterative inner solves jitters at the level of the tolerance.
- Keep the time-step count fixed; don't use adaptive time stepping.
- Sources: https://www.firedrakeproject.org/install.html, https://www.firedrakeproject.org/documentation.html, https://www.firedrakeproject.org/demos/burgers.py.html, https://www.firedrakeproject.org/demos/rayleigh-benard.py.html, https://hub.docker.com/r/firedrakeproject/firedrake-vanilla-default/tags

---

#### NGSolve

**What it is.** Netgen/NGSolve is a high-order finite-element library (C++ with a Python interface) with the Netgen mesher and OpenCascade geometry. It is used for solid mechanics, fluids, and electromagnetics. License: LGPL-2.1 (https://pypi.org/project/ngsolve/, https://github.com/NGSolve/ngsolve). Current release **6.2.2607** (9 Sep 2026). Its examples are the **i-tutorials**: about 67 Jupyter notebooks in 11 units (Poisson, coefficients, subdomains, adaptivity, parabolic, Navier–Stokes, unfitted methods, BEM, ...) at https://docu.ngsolve.org/latest/i-tutorials/index.html (source `docs/i-tutorials/` in the GitHub repo). **Why it qualifies:** it's a comparable package with a rich collection of examples, and it installs with **pip wheels on Intel Macs** (universal2), making it the lowest-friction compiled FE package here.

**Install on an Intel Mac.**
1. Create a dedicated venv with Python 3.12 (from Miniforge or python.org, not EMA's `.venv`):
   ```bash
   ~/miniforge3/bin/mamba create -n ngsolve-2607 -c conda-forge python=3.12
   ~/miniforge3/envs/ngsolve-2607/bin/python -m pip install "ngsolve==6.2.2607"
   ```
   PyPI has `ngsolve-6.2.2607-cp312-cp312-macosx_10_15_universal2.whl`. It pulls `netgen-mesher==6.2.2607` and `netgen-occt==7.8.1`, which has a `macosx_10_15_x86_64` wheel. On macOS it doesn't use `ngsolve-openblas`. I couldn't confirm which Python versions `netgen-mesher` 6.2.2607 has macOS wheels for, so use 3.12, which the listing shows *(unconfirmed for 3.13/3.14)*.
2. Check:
   ```bash
   ~/miniforge3/envs/ngsolve-2607/bin/python -c "import ngsolve, netgen; print(ngsolve.__version__)"
   ```
Known problems: pip may fall back to building from source if no wheel matches, which needs Xcode and CMake. Stop if pip starts compiling.
Sources: https://ngsolve.org/installation.html, https://pypi.org/project/ngsolve/#files, https://pypi.org/pypi/ngsolve/6.2.2607/json, https://pypi.org/pypi/netgen-occt/7.8.1/json

**Install on AWS (Ubuntu 24.04 EC2).**
1. pip, as on the Mac (the `manylinux_2_28_x86_64` wheels, which also pull `ngsolve-openblas==0.3.33`):
   ```bash
   python3 -m venv ~/venv-ngsolve      # needs: sudo apt install python3-venv (ask first)
   ~/venv-ngsolve/bin/pip install "ngsolve==6.2.2607"
   ~/venv-ngsolve/bin/python -c "import ngsolve; print(ngsolve.__version__)"
   ```
2. Alternative: the NGSolve PPA publishes `6.2.2607-0~ubuntu24.04.1` for noble (`sudo add-apt-repository ppa:ngsolve/ngsolve && sudo apt install ngsolve`; the package name is *unconfirmed*).
3. Docker fallback: there is **no official NGSolve image** (only community images such as `pymor/ngsolve`). If needed, build a two-line image `FROM python:3.12-slim` + `pip install ngsolve==6.2.2607`, and pin the base image by digest.
Sources: https://pypi.org/project/ngsolve/#files, https://launchpad.net/~ngsolve/+archive/ubuntu/ngsolve, https://hub.docker.com/r/pymor/ngsolve

**Preparing the examples for EMA.** The i-tutorials are notebooks. The recipe:
- Export the needed cells to a driver `run.py` (or rewrite it: a few dozen lines).
- Parameters are Python values: `mesh.MaterialCF({...})` coefficients, `CoefficientFunction`s, `maxh`, `order`, `dt`, `tend`.
- Remove `Draw(...)` (webgui).
- Compute the output with `Integrate(cf, mesh)` or a point evaluation `gfu(mesh(x, y))`, and print it.
- Shrink with a larger `maxh` or a lower `order`.
- Keep `maxh` and the geometry fixed across runs. Don't use the adaptivity loop (unit 1.6) as a model: adaptive refinement makes the output nonsmooth in every input.
- Set `ngsolve.SetNumThreads(1)` or leave task-manager threads off, so parallel EMA runs don't compete for cores.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Subdomains, `unit-1.5-subdomains/subdomains.ipynb` (https://docu.ngsolve.org/latest/i-tutorials/unit-1.5-subdomains/subdomains.html) | steady diffusion on a 2×2 square with a 0.3×0.5 rectangular inclusion, piecewise conductivity (`{'inner': 3.7, 'outer': 1}`), order 3, maxh 0.2, Dirichlet data x on the bottom and 2−y on the right | `lam_inner` 3.7 [0.1, 100] (log); `lam_outer` 1 [0.5, 2]; `f` (uniform source, added) 1 [0, 5] | ∫u dx | affine in `f`; saturating in `lam_inner` at both ends of its log range (plateaus: the inclusion acts as an insulator or a perfect conductor); an interaction between `lam_outer` and `f` (u_source ∝ f/λ) | < 1 s *(estimate)* | cli (env python + `run.py`) | regex |
| Parabolic model problem, `unit-3.1-parabolic/parabolic.ipynb` (https://docu.ngsolve.org/latest/i-tutorials/unit-3.1-parabolic/parabolic.html) | unsteady convection–diffusion on (−1, 1)², rotating wind b = (2y(1−x²), −2x(1−y²)), diffusion 0.01, source of two Gaussians of opposite sign, order 3, maxh 0.25, dt 0.001, tend 2 | `eps` (diffusion) 0.01 [1e-3, 0.1] (log); `w` (wind amplitude) 1 [0, 2]; `q` (source amplitude) 1 [0, 2]; laptop config: dt 0.01, tend 1 (100 implicit steps) | ∫u² dx at tend (**not** ∫u dx: the wind, source and initial condition are all odd under (x, y) → (−x, −y), so ∫u dx is 0 by symmetry, a useful sanity check) | decreasing in `eps`; quadratic in `q` with an interaction with eps and w; smooth in all three | 1–5 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only) for NGSolve 6.2.2607. Report: OS/version, uname -m, the available Python 3.12 interpreters (Miniforge, python.org, Homebrew), conda/mamba, Docker, Xcode Command Line Tools (xcode-select -p), compilers, and free disk space. Don't install anything, and don't read .env. Recommend a route: pip wheels (universal2 on macOS, manylinux x86_64 on Linux) into a dedicated Python 3.12 env named ngsolve-2607. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install NGSolve on this Intel Mac. Create a dedicated env (conda-forge Miniforge: `mamba create -n ngsolve-2607 -c conda-forge python=3.12`; ask me before installing Miniforge), then `<env>/bin/python -m pip install "ngsolve==6.2.2607"` using binary wheels only (add --only-binary=:all:; if pip wants to build from source, stop and report). Never use EMA's .venv, and never read .env. Ask before any sudo or Homebrew change, and before downloads over 1 GB. Verify with `import ngsolve, netgen; print(ngsolve.__version__)` and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install NGSolve on this AWS EC2 instance (Ubuntu 24.04 x86_64). Create ~/venv-ngsolve with Python 3.12 (ask before `sudo apt install python3-venv` if needed), then `pip install --only-binary=:all: "ngsolve==6.2.2607"`. Never use EMA's .venv, and never read .env. Verify the import and version, and report the absolute python path. If pip fails, stop and report; propose (don't run) the ppa:ngsolve/ngsolve route (6.2.2607 for noble) or a small Docker image FROM python:3.12-slim pinned by digest. Don't continue to the next stage.
```

```text
Stage 3 — NGSolve smoke test. In a scratch directory outside the EMA repo, write the Poisson example of i-tutorial unit-1.1 (docu.ngsolve.org/latest/i-tutorials/unit-1.1-poisson) as a script without Draw calls, printing ndof and Integrate(gfu, mesh). Run it with the ngsolve-2607 env's python and report the output and wall time (import time separately). Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the NGSolve subdomains example for EMA. Plan mode first. Source: i-tutorial unit-1.5-subdomains (NGSolve 6.2.2607). Create examples/ngsolve/subdomains/ with run.py, which reads a key = value deck from subdomains.template: lam_inner = 3.7 [0.1, 100] (scale log), lam_outer = 1 [0.5, 2], f = 1 [0, 5] (a uniform source added to the tutorial's problem). Keep the geometry, maxh 0.2, order 3 and the tutorial's Dirichlet data fixed, and print `mean u = <Integrate(gfu, mesh), %.12e>`. Set threads to 1. EMA command-line model like examples/cantera, with the env's absolute python path. Check that the output is affine in f (three values of f). Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the NGSolve parabolic example. Plan mode first. Source: i-tutorial unit-3.1-parabolic. Create examples/ngsolve/parabolic/: inputs eps = 0.01 [1e-3, 0.1] (scale log), w = 1 [0, 2] (multiplies the wind b), q = 1 [0, 2] (multiplies the Gaussian source); maxh 0.25, order 3, implicit Euler with dt 0.01 and exactly 100 steps (tend 1); initial condition as in the tutorial. Print both `int_u = ...` and `energy = <Integrate(gfu*gfu, mesh), %.12e>` but make the model's output the energy; report int_u for 3 inputs as a symmetry check (it should be ~0). Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 5 — first NGSolve campaign. For examples/ngsolve/subdomains/model.json, write a campaign with repeat (n_points 2, replicates 2), curve1d on lam_inner (n 13), and morris (n_traj 8). Report the run count and time from `ema estimate`, and ask me before `ema run`. Afterwards report: repeatability, whether f is linear, the plateaus in lam_inner, and the morris ranking. Stop and report.
```

```text
Stage 6 — NGSolve troubleshooting. An EMA NGSolve model fails or is slow. Diagnose read-only: rerun run.py by hand in a copy of a run directory with the env's python. Check: the wheel's architecture (file on the .so files; x86_64 slice present), netgen-occt import errors, threads (SetNumThreads, OMP_NUM_THREADS) oversubscribed with -j, a leftover Draw/webgui import that needs a display or ipywidgets, meshes that differ between runs (geometry or maxh changed by an input), a regex mismatch, or a wrong interpreter path. Report the cause and a proposed fix. Ask before changing anything.
```

**Gotchas and sources.**
- LGPL-2.1: fine as an external program.
- High order plus a coarse `maxh` is fast, but change neither between runs. The Netgen mesher is deterministic for fixed geometry and `maxh` *(unconfirmed across thread counts)*.
- Task-manager parallelism can change the summation order, so outputs may jitter at the rounding level when threads are on. Use one thread per run.
- The notebooks use `Draw` from `ngsolve.webgui`. Strip it.
- No official Docker image.
- Sources: https://ngsolve.org/installation.html, https://pypi.org/project/ngsolve/, https://docu.ngsolve.org/latest/i-tutorials/index.html, https://github.com/NGSolve/ngsolve, https://launchpad.net/~ngsolve/+archive/ubuntu/ngsolve

---

#### scikit-fem

**What it is.** scikit-fem is a pure-Python finite-element assembly library (depends only on NumPy and SciPy) with 1D, triangle, quad, tet, and hex elements, and many special elements. License: BSD-3-Clause. Current release **12.0.2** (5 Jun 2026), Python ≥ 3.10. There are 56 numbered examples (`ex01`–`ex56`: heat, elasticity, Stokes, conjugate heat transfer, hyperelasticity, contact, ...), listed at https://scikit-fem.readthedocs.io/en/latest/listofexamples.html, with source in `docs/examples/exNN.py` of https://github.com/kinnala/scikit-fem. Many compare against an exact solution. **Why it qualifies:** it's a comparable package with a rich collection of examples, it has no compiled code (trivial to install on an Intel Mac and on AWS), and its runs take well under a second. That makes it ideal for testing EMA's diagnostics against known analytic structure.

**Install on an Intel Mac.**
1. ```bash
   ~/miniforge3/bin/mamba create -n skfem-12 -c conda-forge python=3.12 numpy scipy
   ~/miniforge3/envs/skfem-12/bin/python -m pip install "scikit-fem==12.0.2" meshio
   ```
   (`meshio` is needed by the examples that load `.msh` files, such as ex28. A plain `python3 -m venv` works equally well.)
2. Check: `~/miniforge3/envs/skfem-12/bin/python -c "import skfem; print(skfem.__version__)"`
Known problems: none expected (pure Python). Examples that load meshes need the repo's `docs/examples/meshes/` files.
Sources: https://pypi.org/project/scikit-fem/, https://github.com/kinnala/scikit-fem

**Install on AWS (Ubuntu 24.04 EC2).**
1. ```bash
   python3 -m venv ~/venv-skfem      # ask before: sudo apt install python3-venv
   ~/venv-skfem/bin/pip install "scikit-fem==12.0.2" meshio
   ~/venv-skfem/bin/python -c "import skfem; print(skfem.__version__)"
   ```
2. Docker fallback (rarely needed): `python:3.12-slim` pinned by digest, plus the same pip line.
Sources: https://pypi.org/project/scikit-fem/

**Preparing the examples for EMA.** Each `exNN.py` is a short script. Parameters are module-level Python variables (`thermal_conductivity`, `joule_heating`, `peclet`, ...). The recipe:
- Copy the script and the mesh file it loads (as a static file).
- Replace the parameter assignments with values read from a deck, keep the example's own exact-solution comparison as a check, remove the `matplotlib` plotting at the bottom, and print the scalar.
- These examples are already laptop-sized.
- Because scikit-fem needs only NumPy and SciPy, a Python-function model is also possible. The brief's pattern (a separate env and a command-line model) is still recommended, to keep EMA's venv clean.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| ex17, insulated wire (`docs/examples/ex17.py`) | steady heat conduction in a wire (core radius 2, annulus to radius 3; mesh `meshes/disk.json`), Joule heating, Robin cooling. Example: k_core = 101, k_annulus = 11, q = 5, h = 7 | `k_core` 101 [50, 400]; `k_annulus` 11 [2, 50] (log); `q` (Joule heating) 5 [1, 20]; `h` 7 [1, 50] (log) | centre temperature T(0) (the example computes `basis.probes` at the origin and an exact value) | exactly linear in `q`. The textbook cylinder solution T0 = q a²[1/(4k_c) + ln(b/a)/(2k_a) + 1/(2bh)] (to check against ex17's own exact expression) is a sum of reciprocals: at the nominal point, core ≈ 0.05, annulus ≈ 0.37, surface ≈ 0.48, so `k_core` should come out **negligible or possibly negligible**; additive in 1/k_a and 1/h, times q | < 1 s (mostly import) *(estimate)* | cli (env python + `run.py`) | regex |
| ex28, conjugate heat transfer (`docs/examples/ex28.py`) | channel flow (Poiseuille) over a heated solid wall; mesh `meshes/ex28.msh`. Example: Pe = 357, kratio = 80/(4.181/7.14) ≈ 137 | `peclet` 357 [50, 2000] (log); `kratio` 137 [10, 500] (log) | exit interface temperature (the example prints the numerical and exact fully developed values) | monotone in both; smooth; nearly a power law in log inputs *(to be confirmed)*. The example's longitudinal gradient is tied to Pe (3/(4 Pe)), which should be kept as written | < 1 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only) for scikit-fem 12.0.2. Report: OS/version, uname -m, the Python 3.12 interpreters available, conda/mamba, and free disk space. Don't install anything, and don't read .env. Recommend a route: a dedicated env skfem-12 (conda-forge python=3.12 numpy scipy, then pip scikit-fem==12.0.2 meshio) on both the Intel Mac and Ubuntu 24.04. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install scikit-fem on this Intel Mac: `mamba create -n skfem-12 -c conda-forge python=3.12 numpy scipy`, then `<env>/bin/python -m pip install scikit-fem==12.0.2 meshio`. Never use EMA's .venv, and never read .env. Ask before installing Miniforge or changing Homebrew. Verify `import skfem; print(skfem.__version__)`, and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install scikit-fem on this AWS EC2 instance (Ubuntu 24.04 x86_64): create ~/venv-skfem (ask before any sudo apt), then `pip install scikit-fem==12.0.2 meshio`. Never use EMA's .venv, and never read .env. Verify the import and version, and report the python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — scikit-fem smoke test. In a scratch directory outside the EMA repo, fetch docs/examples/ex01.py from the v12.0.2 tag of github.com/kinnala/scikit-fem, run it with the skfem-12 env's python (a non-interactive matplotlib backend, MPLBACKEND=Agg), and report its output and wall time. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare scikit-fem ex17 (insulated wire) for EMA. Plan mode first. Source: docs/examples/ex17.py and docs/examples/meshes/disk.json at tag v12.0.2 of github.com/kinnala/scikit-fem. Create examples/skfem/wire/ with run.py (reads a key = value deck from wire.template), disk.json as a static file, and inputs k_core = 101 [50, 400], k_annulus = 11 [2, 50] (scale log), q = 5 [1, 20], h = 7 [1, 50] (scale log). Print `T0 = <centre temperature, %.12e>`, and also the example's exact value on a second line for checking. Remove the plotting. EMA command-line model like examples/cantera, with the env's absolute python path. Check that the numerical and exact T0 agree at nominal and at two other points. Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare scikit-fem ex28 (conjugate heat transfer) for EMA. Plan mode first. Source: docs/examples/ex28.py and meshes/ex28.msh at v12.0.2. Create examples/skfem/conjugate/ with inputs peclet = 357 [50, 2000] (scale log) and kratio = 137 [10, 500] (scale log); keep the example's heat-flux rule longitudinal_gradient = 3/4/peclet. Output: the numerical exit interface temperature, printed as `T_exit = %.12e` (plus the exact value on its own line). Static file ex28.msh, and meshio in the env. Then `ema profile ... -n 5` and report. Stop and report; don't run a campaign.
```

```text
Stage 5 — first scikit-fem campaign. For examples/skfem/wire/model.json, write a campaign with repeat (n_points 2, replicates 2), morris (n_traj 10) and linear_coeffs (log_output true). Report the run count from `ema estimate`, and ask me before `ema run`. Afterwards compare with the analytic expectation: q linear with exponent 1, k_core negligible or possibly negligible, the ranking of k_annulus vs h. Stop and report.
```

```text
Stage 6 — scikit-fem troubleshooting. An EMA scikit-fem model fails. Diagnose read-only: rerun run.py in a copy of a run directory. Check: the mesh file isn't in the run directory (not listed in static_files), meshio missing, matplotlib trying to open a window (set MPLBACKEND=Agg in env), an API change in 12.x vs the example's tag (use the example from the same tag as the installed version), a regex mismatch, or a wrong interpreter path. Report the cause and a proposed fix; ask before changing anything.
```

**Gotchas and sources.**
- BSD-3: no licensing concerns.
- Deterministic: direct sparse solves (SciPy SuperLU/UMFPACK), serial.
- Examples change between releases. Always take `exNN.py` from the tag matching the installed version.
- Import of SciPy/Matplotlib dominates run time. Skip importing matplotlib.
- Sources: https://pypi.org/project/scikit-fem/, https://scikit-fem.readthedocs.io/en/latest/listofexamples.html, https://github.com/kinnala/scikit-fem, https://raw.githubusercontent.com/kinnala/scikit-fem/master/docs/examples/ex17.py, https://raw.githubusercontent.com/kinnala/scikit-fem/master/docs/examples/ex28.py

---

#### FiPy

**What it is.** FiPy is NIST's finite-volume PDE solver in Python (diffusion, convection, phase field, level set, Cahn–Hilliard). License: NIST software, public domain in the US (17 U.S.C. § 105), with permission to use, copy, and modify (https://github.com/usnistgov/fipy/blob/master/LICENSE.rst). Current release **4.0.3** (18 Jun 2026). There are 31 example modules (diffusion 7, convection 4, phase field 9, level set 4, Cahn–Hilliard 2, flow 1, reactive wetting 1, updating 3) at https://pages.nist.gov/fipy/en/latest/EXAMPLES.html (source `examples/` in https://github.com/usnistgov/fipy). They run as `python -m examples.<module>`-style scripts with doctest-checked results.

**Install on an Intel Mac.** `fipy` is `noarch` on conda-forge, so osx-64 is covered as long as its dependencies (NumPy, SciPy, and optionally petsc4py) have osx-64 builds.
1. ```bash
   ~/miniforge3/bin/mamba create -n fipy-4 -c conda-forge python=3.12 fipy=4.0.3 scipy
   ```
   Use the SciPy solver suite: it needs no MPI and is deterministic. The PETSc suite (`petsc4py`, `mpi4py`) is optional. Trilinos needs Python < 3.9, so don't use it.
2. Check:
   ```bash
   FIPY_SOLVERS=scipy ~/miniforge3/envs/fipy-4/bin/python -c "import fipy; print(fipy.__version__); print(fipy.solvers.solver_suite)"
   ```
   (`solver_suite` is the attribute name I remember *(unconfirmed)*. Otherwise the check is that `import fipy` succeeds with `FIPY_SOLVERS=scipy`.)
Sources: https://pages.nist.gov/fipy/en/latest/INSTALLATION.html, https://pages.nist.gov/fipy/en/latest/SOLVERS.html, https://prefix.dev/channels/conda-forge/packages/fipy

**Install on AWS (Ubuntu 24.04 EC2).**
1. The same conda env (Linux Miniforge), or pip: `python3 -m venv ~/venv-fipy && ~/venv-fipy/bin/pip install "fipy==4.0.3"` (it pulls numpy, scipy, matplotlib, typer).
2. Check with `FIPY_SOLVERS=scipy` as above.
3. Docker fallback: `python:3.12-slim` pinned by digest + `pip install fipy==4.0.3` (no official image found *(unconfirmed)*).
Sources: https://pypi.org/project/fipy/, https://pages.nist.gov/fipy/en/latest/INSTALLATION.html

**Preparing the examples for EMA.** The examples are Python scripts with the parameters as module-level variables (`diffCoeff`, `convCoeff`, `L`, `nx`, `D`, `timeStepDuration`, `steps`, `kappa1`, ...) inside the docstring-style code. The recipe:
- Copy the code into a driver that reads a deck, removes the `Viewer` calls (and `input()` pauses), and prints one scalar: a cell value, `var.cellVolumeAverage`, or a sum.
- Set `FIPY_SOLVERS=scipy` in the model's `env`.
- Shrink `nx`, `ny`, and the number of steps. Keep the step count fixed (dt = t_end/steps).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples.convection.exponential1D.mesh1D` (https://pages.nist.gov/fipy/en/latest/generated/examples.convection.exponential1D.mesh1D.html) | steady 1D convection–diffusion, φ(0) = 0, φ(L) = 1, exponential scheme. Example: D = 1, u = 10, L = 10, nx = 10, and the solution matches the analytic one | `D` 1 [0.1, 10] (log); `u` 1 [0.1, 10] (log); `L` 10 [2, 20] (log); nx = 51 (odd, so a cell centre sits at L/2) | φ at x = L/2 | analytic: φ(L/2) = 1/(1 + e^(−Pe/2)) with Pe = uL/D, a logistic function of one combination. In log inputs, `active_subspace` should find **one direction ∝ (−1, +1, +1)** for (D, u, L), with plateaus at 0.5 (Pe → 0) and 1 (large Pe) | < 1 s *(estimate)* | cli (env python + `run.py`) | regex |
| `examples.diffusion.mesh1D` (https://pages.nist.gov/fipy/en/latest/generated/examples.diffusion.mesh1D.html), the implicit transient case | 1D transient diffusion, nx = 50, dx = 1, φ(0) = 1, φ(L) = 0, implicit steps | `D` 1 [0.1, 10] (log); `t_end` 100 [10, 1000] (log); 100 implicit steps with dt = t_end/100 | φ at the cell nearest x = 10 | the implicit scheme depends only on D·dt/dx², so the output is **exactly a function of D·t_end**: one direction (1, 1) in log inputs; monotone increasing in both, saturating toward the linear steady profile at large D·t | < 1 s *(estimate)* | cli | regex |
| `examples.phase.anisotropy` (https://pages.nist.gov/fipy/en/latest/generated/examples.phase.anisotropy.html) | dendritic solidification: phase field + heat equation. Example: dx = 0.025, nx = 500, dt = 5e-4, 10,000 steps; N = 6, θ = π/8, κ1 = 0.9, κ2 = 20, D_T = 2.25; its test mode is 20×20 with 10 steps | `kappa1` 0.9 [0.6, 1.2]; `kappa2` 20 [10, 30]; `DT` 2.25 [1, 4]; `alpha` 0.015 [0.01, 0.02]; laptop config nx = ny = 60, 300 steps | solid fraction (cell-volume average of φ) at the end | growth rate increasing in `kappa1` (undercooling drive), `alpha` affecting the tip; likely smooth but steep. A realistic, costlier model: a use for `morris` rather than `sobol` | 10–60 s *(estimate; may exceed the 10 s target)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only) for FiPy 4.0.3. Report: OS/version, uname -m, conda/mamba (Miniforge), the available Python 3.12, and free disk space. Don't install anything, and don't read .env. Recommend a route: a dedicated conda-forge env fipy-4 (python=3.12 fipy=4.0.3 scipy) with the SciPy solver suite (FIPY_SOLVERS=scipy) on both the Intel Mac and Ubuntu 24.04. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install FiPy on this Intel Mac: `mamba create -n fipy-4 -c conda-forge python=3.12 fipy=4.0.3 scipy` (conda-forge only; ask before installing Miniforge). Don't install PETSc or Trilinos. Never use EMA's .venv, and never read .env. Verify with `FIPY_SOLVERS=scipy <env>/bin/python -c "import fipy; print(fipy.__version__)"`, and report which solver suite FiPy picked and the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install FiPy on this AWS EC2 instance (Ubuntu 24.04 x86_64): the same conda-forge env fipy-4 (Linux Miniforge, python=3.12 fipy=4.0.3 scipy), or, if I prefer no conda, ~/venv-fipy with `pip install fipy==4.0.3` (ask before any sudo apt). Never use EMA's .venv, and never read .env. Verify with FIPY_SOLVERS=scipy, and report the python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — FiPy smoke test. In a scratch directory outside the EMA repo, take examples/diffusion/mesh1D.py from the 4.0.3 tag of github.com/usnistgov/fipy (or the installed package's examples if present), and run it with FIPY_SOLVERS=scipy and MPLBACKEND=Agg using the fipy-4 env's python, non-interactively (if it waits for input, feed /dev/null). Report its output and wall time. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare FiPy exponential1D for EMA. Plan mode first. Source: examples/convection/exponential1D/mesh1D.py of FiPy 4.0.3. Create examples/fipy/exponential1d/ with run.py (reads a key = value deck): D = 1 [0.1, 10], u = 1 [0.1, 10], L = 10 [2, 20], all scale log; nx = 51; φ(0) = 0, φ(L) = 1; the exponential convection term as in the example. Print `phi_mid = <φ at the centre cell x = L/2, %.12e>`, and the analytic value 1/(1+exp(-u*L/(2*D))) on a second line. Env: FIPY_SOLVERS=scipy, MPLBACKEND=Agg, OMP_NUM_THREADS=1. EMA command-line model like examples/cantera, with the env's absolute python path. Check numerical vs analytic at three points. Then `ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare FiPy transient diffusion. Plan mode first. Source: examples/diffusion/mesh1D.py (the implicit transient case) of FiPy 4.0.3. Create examples/fipy/diffusion1d/: nx = 50, dx = 1, φ(0) = 1, φ(50) = 0, initial 0; inputs D = 1 [0.1, 10] and t_end = 100 [10, 1000], both scale log; exactly 100 implicit steps with dt = t_end/100. Print `phi_10 = <φ at the cell centre nearest x = 10, %.12e>`. Check by hand that (D, t_end) = (1, 100) and (10, 10) give the same output to rounding. Then `ema profile ... -n 5` and report. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare FiPy dendrite (phase.anisotropy). Plan mode first. Source: examples/phase/anisotropy.py of FiPy 4.0.3. Create examples/fipy/dendrite/ with inputs kappa1 = 0.9 [0.6, 1.2], kappa2 = 20 [10, 30], DT = 2.25 [1, 4], alpha = 0.015 [0.01, 0.02]; keep N = 6, θ = π/8, dx = 0.025, dt = 5e-4; start with nx = ny = 60 and 300 steps. Remove the viewer, and print `solid_fraction = <phase.cellVolumeAverage, %.12e>`. Measure one run's time by hand first; if it's over 30 s, propose a smaller configuration and ask me. Then `ema profile ... -n 3` and report. Stop and report; don't run a campaign.
```

```text
Stage 5 — first FiPy campaign. For examples/fipy/exponential1d/model.json, write a campaign with repeat (n_points 2, replicates 2), curve1d on u (n 11), morris (n_traj 10), and active_subspace with small settings from `ema diagnostics`. Report the run count from `ema estimate`, and ask me before `ema run`. Afterwards report whether EMA found one dominant direction ∝ (-1, +1, +1) in (D, u, L) log coordinates, and the plateaus in curve1d. Stop and report.
```

```text
Stage 6 — FiPy troubleshooting. An EMA FiPy model fails or is slow. Diagnose read-only: rerun run.py in a copy of a run directory with the same env. Check: FIPY_SOLVERS not set (FiPy picks PETSc first if installed, which pulls in MPI), a Viewer or matplotlib window, the example waiting on input(), a solver that didn't converge (sweeps for nonlinear terms; residual printed), a regex mismatch, a step count that depends on an input, or a wrong interpreter path. Report the cause and a proposed fix; ask before changing anything.
```

**Gotchas and sources.**
- License: US public domain (NIST), so no concerns.
- Solver choice: without `FIPY_SOLVERS`, FiPy prefers PETSc, then Trilinos, then SciPy. Set `scipy` explicitly for serial, deterministic runs.
- Iterative solvers (FiPy's default for many terms) leave tolerance-level jitter. For the phase-field example, `repeat` should confirm it is zero, or measure `output_noise`.
- The phase-field example is the only one likely to exceed 10 s per run.
- Examples are docstring-heavy scripts. Copy them from the matching 4.0.3 tag.
- Sources: https://pages.nist.gov/fipy/en/latest/INSTALLATION.html, https://pages.nist.gov/fipy/en/latest/SOLVERS.html, https://pages.nist.gov/fipy/en/latest/EXAMPLES.html, https://pypi.org/project/fipy/, https://github.com/usnistgov/fipy, https://prefix.dev/channels/conda-forge/packages/fipy


### 4.2 C++ finite-element packages: deal.II, MFEM, DUNE, MOOSE, Elmer

Desk research only. Nothing was installed or run. All versions, tags, and platform facts were checked on 2026-09-24 from the URLs cited; anything not confirmed from an official page is marked **(unconfirmed)**. Run times marked "est." are estimates, not measurements.

**Shared platform context (applies to every package below)**

- **Homebrew on Intel macOS moved to Tier 3 in September 2026**: no CI and no new Intel bottles. Homebrew still runs on Intel until September 2027. Updated formulae may need source builds ([Homebrew 7.0.0, 2026-09-13](https://brew.sh/2026/09/13/homebrew-7.0.0/); [scivision summary](https://www.scivision.dev/homebrew-eol-intel-cpu/)). GCC, and with it `gfortran`, lost its Intel bottles on 2026-09-03 ([wazuh issue #38893](https://github.com/wazuh/wazuh/issues/38893), citing [Homebrew commit d69ac4a](https://github.com/Homebrew/homebrew-core/commit/d69ac4a9489769a6918361de3304ea46a27271e3)). **Rule for this document: don't use Homebrew for anything new on the Intel Mac.**
- **conda-forge osx-64** is still built. conda-forge raised its minimum macOS to 11.0 in February 2026 and has announced no end date for osx-64 ([conda-forge news](https://conda-forge.org/news/)). Anaconda's *defaults* channel is phasing out Intel Mac packages ([Anaconda blog](https://www.anaconda.com/blog/intel-mac-package-support-deprecation)). Use Miniforge (conda-forge) only.
- **Docker Desktop** ships an Intel build. It supports the current macOS release and the two before it ([Docker docs](https://docs.docker.com/desktop/setup/install/mac-install/)). An `amd64` image runs natively on an Intel Mac, with no emulation. Each `docker run --rm` adds per-run startup overhead, probably 0.5–2 s **(unconfirmed estimate)**. `-j N` in EMA starts N containers at once, so the Docker Desktop VM needs at least N CPUs.
- **AWS**: Ubuntu 24.04 on `c7i.xlarge` (4 vCPU, 8 GiB) is enough to run the models. Use `c7i.2xlarge` (8 vCPU, 16 GiB) for the source builds (DUNE pip, Elmer, MOOSE modules) ([c7i](https://aws.amazon.com/ec2/instance-types/c7i/)). Give it a 60 GB gp3 root volume, because each Docker image is 2–3 GB. Docker Engine on Ubuntu: [docs.docker.com/engine/install/ubuntu](https://docs.docker.com/engine/install/ubuntu/).
- **EMA hooks used below** (from `docs/guides/input_deck_model.md` in the EMA repo):
  - The `command` is a list, run with no shell.
  - `$EMA_WORKDIR` is the run directory and `$EMA_BASE_DIR` is the model directory.
  - Inputs can go into templates or into command arguments.
  - A literal `$` in a template is written `$$`.
  - Binaries and scripts next to `model.json` that the command names, and static files, are covered by the version hash. A program given by absolute path is not.
  - Whether `$EMA_WORKDIR` is expanded *inside* a longer argument such as `-v $EMA_WORKDIR:/work` is **(unconfirmed)**. Each Docker prompt below tells Claude Code to check this and to fall back to a small wrapper script.

---

#### deal.II

**What it is.** A C++ finite-element library with adaptive meshes, hp methods, and MPI. It is dual-licensed: Apache-2.0 with the LLVM exception, or LGPL-2.1-or-later ([LICENSE.md](https://raw.githubusercontent.com/dealii/dealii/master/LICENSE.md)). The current release is **9.8.0 (2026-08-09)** ([dealii.org](https://www.dealii.org/)).
- The tutorials are the `examples/step-N/` directories of the source tree, documented at [Tutorial.html](https://www.dealii.org/current/doxygen/deal.II/Tutorial.html). They are numbered up to step-97, about 90 programs in all, plus a separate code gallery.
- About 16 tutorials read `.prm` parameter files through `ParameterHandler`, for example step-28, 29, 32, 33, and 34.

**Install on an Intel Mac.** Use Docker Desktop with the official `amd64` image. There is no native Intel route that is current:
- Release `.dmg` files are Apple Silicon only (9.7.1: `sequoia-arm64`, `tahoe-arm64`; 9.8.0 has no `.dmg`) ([GitHub releases API](https://api.github.com/repos/dealii/dealii/releases?per_page=4)).
- conda-forge `dealii` stops at **9.3.2** (linux-64, osx-64) ([anaconda API](https://api.anaconda.org/package/conda-forge/dealii); [feedstock](https://github.com/conda-forge/dealii-feedstock)).
- A Homebrew formula was not found **(unconfirmed)**, and Homebrew is Tier 3 on Intel anyway.
- The wiki's Mac advice is the `.dmg`, or a source build via candi or Spack, which takes hours ([wiki: Getting deal.II](https://github.com/dealii/dealii/wiki/Getting-deal.II)).

1. Install Docker Desktop for Mac (Intel chip) ([docs](https://docs.docker.com/desktop/setup/install/mac-install/)).
2. Pull the newest tagged image. As of 2026-09-24 there is no `v9.8.0-*` tag on Docker Hub yet ([tags API](https://hub.docker.com/v2/repositories/dealii/dealii/tags?page_size=40)). The image is about 2.65 GB for amd64:
   ```bash
   docker pull dealii/dealii:v9.7.1-noble
   docker inspect --format '{{index .RepoDigests 0}}' dealii/dealii:v9.7.1-noble
   # index digest read from Docker Hub on 2026-09-24 (verify): sha256:28a40c95e76879c717a96ea3f5c87cc00ec1d7a4ce9d250ab936fb723eab6995
   ```
3. Get the tutorial sources for the *same* version:
   ```bash
   mkdir -p ~/pde/dealii && cd ~/pde/dealii
   curl -L -o dealii-9.7.1.tar.gz https://github.com/dealii/dealii/archive/refs/tags/v9.7.1.tar.gz
   tar xzf dealii-9.7.1.tar.gz dealii-9.7.1/examples
   ```
4. Build and run step-1 inside the container. This is the check:
   ```bash
   cp -r dealii-9.7.1/examples/step-1 . && cd step-1
   docker run --rm -v "$PWD":/work -w /work dealii/dealii:v9.7.1-noble \
       bash -lc 'cmake . && make release && make && ./step-1'
   ls *.svg   # grid-1.svg, grid-2.svg
   ```
   - Known problem: the user inside the image may not be root **(unconfirmed)**, so files it writes to a bind mount can have the wrong owner. On Docker Desktop this is usually harmless. On Linux, add `--user $(id -u):$(id -g)`.
   - Known problem: step-29 needs UMFPACK. The images are built from the Ubuntu packages, which include SuiteSparse **(unconfirmed for this tag)**.

**Install on AWS (Ubuntu 24.04 EC2).** Install natively from apt, using the maintainer's backports PPA.
- Noble's own `libdeal.ii-dev` is **9.5.1** ([packages.ubuntu.com](https://packages.ubuntu.com/noble/libdeal.ii-dev)).
- The PPA `ppa:ginggs/deal.ii-9.6.0-backports` has **9.6.0** for noble ([Launchpad](https://launchpad.net/~ginggs/+archive/ubuntu/deal.ii-9.6.0-backports); commands from the [wiki](https://github.com/dealii/dealii/wiki/Getting-deal.II)).
- No 9.7 or 9.8 PPA was found.

1. Install from the PPA:
   ```bash
   sudo apt-get update && sudo apt-get install -y software-properties-common
   sudo add-apt-repository -y ppa:ginggs/deal.ii-9.6.0-backports
   sudo apt-get update && sudo apt-get install -y libdeal.ii-dev cmake g++ make
   ```
2. Get the tutorials from tag `v9.6.0`, the same way as Mac step 3 but with `v9.6.0`.
3. Check: `cd step-1 && cmake . && make release && make && ./step-1`.
4. Docker fallback: install Docker Engine ([docs](https://docs.docker.com/engine/install/ubuntu/)) and use the same `dealii/dealii:v9.7.1-noble` image, pinned by digest, exactly as on the Mac. Using the image on both machines gives identical binaries.

**Preparing the examples for EMA.**
- **Where the inputs go.** step-29 already reads `step-29.prm` (sections `Mesh & geometry parameters`, `Physical constants`, `Output parameters`), so that file becomes the template. Other steps hard-code their coefficients. For those, add about 15 lines of `ParameterHandler` code that read a small `.prm`. That is plain C++; see step-29 for the pattern.
- **Shrinking to laptop size.** Fix the global refinement count and replace adaptive refinement cycles with one solve. Adaptive meshes make outputs jump as the refinement pattern changes. Turn off the VTU and gnuplot output.
- **Scalar output.** Add one line at the end of the program:
  - `std::cout << "EMA_OUTPUT " << std::setprecision(17) << value << '\n';`
  - Compute the value with `VectorTools::point_value` or `VectorTools::compute_mean_value`, and parse it with a regex on stdout.
- **Building and running.** Compile the modified step once, inside the pinned image on the Mac or natively on AWS. Keep the binary next to `model.json` so the version hash covers it.
  - Mac command: `docker run --rm -v <run dir>:/work -w /work <image@digest> ./step-29 step-29.prm`, with the binary as a static file.
  - AWS native command: `$EMA_BASE_DIR/step-29 step-29.prm`.
- **Determinism.** Run serially with a direct solver (UMFPACK in step-29, or `SparseDirectUMFPACK` in the others), so the output does not jitter.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/step-29` ([doc](https://www.dealii.org/current/doxygen/deal.II/step_29.html)) | Helmholtz ultrasound focusing, complex field split into real and imaginary parts, absorbing boundary | `omega` 3.0e7 [2.0e7, 4.0e7] rad/s (log); `c` 1.5e5 [1.2e5, 1.8e5] (log); `Focal distance` 0.3 [0.2, 0.4]. Refinements fixed at the default 5 (25,600 cells) | intensity \|u\| at the geometric focus (0.5, focal distance), via `point_value`. The lens is an arc centred at (0.5, d); confirm in `make_grid` | **One-dimensional ridge.** The PDE is −ω²u − c²Δu = 0 with BC c ∂u/∂n ∓ ωu = 0. Dividing by c² leaves only k = ω/c, so ln ω and ln c act along the direction (1, −1): active_subspace dimension 1, and equal-and-opposite exponents in `linear_coeffs(log_output)`. Likely non-monotone in k (interference). Smooth in focal distance, which moves vertices continuously | ≈0.7 s native (docs: 0.7 s at 5 refinements, release build) plus Docker start on the Mac | cli (Docker on Mac, native on AWS) | regex on stdout |
| `examples/step-8` ([doc](https://www.dealii.org/current/doxygen/deal.II/step_8.html)), patched to read `.prm`, global refinement only | 2-D linear elasticity on [−1,1]², body force in three discs of radius 0.2 | `lambda` 1 [0.5, 2] (log); `mu` 1 [0.5, 2] (log); `force` 1 [0.5, 2] (log), scaling both force components | max \|u\| over vertices, or \|u\| at (0.5, 0) | **Exact power law.** Linear in `force` (exponent +1). Homogeneous of degree −1 in (λ, μ), so their exponents sum to −1. Expect `linear_coeffs(log_output)` → `power_law`, with μ dominant | est. < 0.5 s at 5–6 global refinements | cli | regex on stdout |
| `examples/step-6` ([doc](https://www.dealii.org/current/doxygen/deal.II/step_6.html)), patched to read `.prm` | −∇·(a∇u) = 1 on a disc, with a = contrast inside radius r and 1 outside | `contrast` 20 [2, 100] (log); `radius` 0.5 [0.3, 0.7] | mean of u (`compute_mean_value`) | Monotone decreasing in both inputs; saturates in contrast. **Nonsmooth in radius at mesh resolution:** the coefficient is sampled at quadrature points, so small steps appear as the interface crosses them. With the tutorial's 8 adaptive cycles the steps get larger, because the mesh changes with r. A deliberate test for `nonsmooth` and `curve1d` | est. < 0.5 s at 5 global refinements | cli | regex on stdout |

**Claude Code prompts.**

```text
Stage 1 — deal.II: check this machine (read-only).
Package: deal.II. Target: 9.7.1 via the Docker image dealii/dealii:v9.7.1-noble on an Intel Mac, or 9.6.0 from ppa:ginggs/deal.ii-9.6.0-backports on Ubuntu 24.04. Don't install or change anything, and don't read .env.
Report: OS and version, `uname -m`, CPU count, RAM, free disk space; whether Docker is installed and running (`docker info`) and its CPU/memory allocation; conda/mamba and Homebrew presence (just note them — Homebrew must not be used on Intel macOS); compilers (`cc --version`, `c++ --version`, `cmake --version`); MPI (`mpirun --version`); on Linux, `apt-cache policy libdeal.ii-dev`.
Then recommend a route: Docker on the Intel Mac, and native PPA 9.6.0 (Docker fallback) on Ubuntu 24.04.
Stop and report the table and the recommendation; don't continue to the next stage.
```

```text
Stage 2a — deal.II: install on the Intel Mac (Docker route).
Package: deal.II 9.7.1 through the Docker image dealii/dealii:v9.7.1-noble (amd64, about 2.65 GB). Don't use EMA's .venv, don't read .env, don't use Homebrew.
1. Confirm Docker Desktop is running. The image is over 1 GB: ask me before pulling it.
2. `docker pull dealii/dealii:v9.7.1-noble`, then record the digest with `docker inspect --format '{{index .RepoDigests 0}}' dealii/dealii:v9.7.1-noble`. Docker Hub showed sha256:28a40c95e76879c717a96ea3f5c87cc00ec1d7a4ce9d250ab936fb723eab6995 on 2026-09-24; say whether it matches.
3. Download the matching tutorial sources into ~/pde/dealii: https://github.com/dealii/dealii/archive/refs/tags/v9.7.1.tar.gz, extracting only dealii-9.7.1/examples.
Stop at the first error and report it verbatim; don't improvise workarounds. When done, report the digest and the examples path; don't continue to the next stage.
```

```text
Stage 2b — deal.II: install on AWS EC2 Ubuntu 24.04 x86_64 (runs on the instance).
Package: deal.II 9.6.0 from ppa:ginggs/deal.ii-9.6.0-backports (noble's own libdeal.ii-dev is 9.5.1). Don't read .env and don't use EMA's .venv.
1. Show me the exact sudo commands and ask before running them: apt-get update; install software-properties-common; add-apt-repository -y ppa:ginggs/deal.ii-9.6.0-backports; apt-get install -y libdeal.ii-dev cmake g++ make.
2. Report `dpkg -s libdeal.ii-dev | grep Version`.
3. Download the tutorial sources for tag v9.6.0 into ~/pde/dealii (examples/ only).
If the PPA fails, stop and ask whether to use the Docker fallback: install Docker Engine per docs.docker.com/engine/install/ubuntu (ask before sudo) and pull dealii/dealii:v9.7.1-noble, pinned by digest.
Stop at the first error and report it; don't continue to the next stage.
```

```text
Stage 3 — deal.II: smoke test with tutorial step-1.
Use the route installed in stage 2: Docker image dealii/dealii:v9.7.1-noble pinned by digest on the Mac, or the native 9.6.0 PPA on AWS.
Copy examples/step-1 to ~/pde/dealii/step-1. Run `cmake . && make release && make && ./step-1`, inside `docker run --rm -v "$PWD":/work -w /work <image@digest> bash -lc '...'` on the Mac.
Report: whether grid-1.svg and grid-2.svg were written; the wall time of the build and of the run, separately; and, on Docker, the time of `docker run --rm <image> true` alone, which is the per-run container overhead.
Stop and report; don't continue.
```

```text
Stage 4.1 — deal.II: prepare step-29 (Helmholtz ultrasound) as an EMA command-line model.
Start in plan mode and show me the plan before editing anything.
Context: deal.II (9.7.1 Docker image pinned by digest on the Intel Mac, or 9.6.0 native on AWS). Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/, and examples/modflow/ first, and follow their layout.
1. Copy the tutorial's examples/step-29 into examples/dealii/step29/.
2. Laptop configuration: keep "Number of refinements" = 5. Disable the VTU output, or make it optional, so a run writes nothing large.
3. Add a few lines of C++ that print `EMA_OUTPUT <value>` with 17 significant digits. The value is the intensity sqrt(v^2+w^2) at the geometric focus (0.5, focal distance), from VectorTools::point_value. First confirm in make_grid() that the SphericalManifold centre is (0.5, focal_distance).
4. Make step-29.prm a template with placeholders $omega, $c and $focal_distance (a literal $ must be $$). Inputs, as log-scale where marked: omega 3.0e7 [2.0e7, 4.0e7] (log), c 1.5e5 [1.2e5, 1.8e5] (log), focal_distance 0.3 [0.2, 0.4].
5. Build the binary once, in the same environment it will run in, and keep it next to model.json so the version hash covers it.
6. Write model.json:
   - Command on the Mac: docker run --rm with the run directory mounted at /work, the image pinned by digest, and ./step-29 step-29.prm. Check whether EMA expands $EMA_WORKDIR inside a longer argument such as "$EMA_WORKDIR:/work"; if not, use a small wrapper script in the model directory.
   - Command on AWS: the binary directly.
   - Output: a regex on stdout. timeout_s: 120.
7. Run `ema profile examples/dealii/step29/model.json -n 3` and report the time per run and the three outputs.
Stop and report; don't start a campaign.
```

```text
Stage 4.2 — deal.II: prepare step-8 (linear elasticity) as an EMA command-line model.
Start in plan mode first.
Context: deal.II, same route as stage 3 (Docker image pinned by digest on the Intel Mac, native 9.6.0 on AWS). Follow docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/, and examples/modflow/.
1. Copy examples/step-8 into examples/dealii/step8/.
2. Replace the 8 adaptive cycles with one solve after 5 global refinements, so results do not jump with the mesh.
3. Add a ParameterHandler that reads step-8.prm, with entries lambda, mu, and force (force multiplies both components of the right-hand side). Follow step-29's pattern.
4. Print `EMA_OUTPUT <max |u| over vertices>` with 17 digits. Turn off VTK output.
5. Make step-8.prm a template. Inputs, all log-scale: lambda 1 [0.5, 2], mu 1 [0.5, 2], force 1 [0.5, 2].
6. Build once, write model.json (the same command pattern as step-29), and run `ema profile ... -n 3`.
Also check the physics by hand: doubling force must double the output, and doubling both lambda and mu must halve it, both to about 1e-10 relative. Report those two ratios and the time per run.
Stop and report; don't start a campaign.
```

```text
Stage 4.3 — deal.II: prepare step-6 (Poisson with a discontinuous coefficient) as an EMA command-line model.
Start in plan mode first.
Context: deal.II, same route as before. Follow the EMA docs and the examples/cantera and examples/modflow layout.
1. Copy examples/step-6 into examples/dealii/step6/.
2. Add a ParameterHandler with contrast (the coefficient inside the disc, 20 in the tutorial), radius (0.5 in the tutorial), and a switch "adaptive" (default false). When adaptive is false, use 5 global refinements and one solve; when true, keep the tutorial's 8 cycles.
3. Print `EMA_OUTPUT <mean of u>` from VectorTools::compute_mean_value. Turn off the gnuplot and VTU output.
4. Inputs: contrast 20 [2, 100] (log), radius 0.5 [0.3, 0.7]. Save two model.json files, model_global.json and model_adaptive.json, that differ only in the switch.
5. Run `ema profile` on both and report the time per run.
Stop and report; don't start a campaign.
```

```text
Stage 5 — deal.II: first campaigns (cheap).
Package deal.II, with the models from stage 4 in examples/dealii/.
Propose campaign JSON files, but don't run them yet:
(a) step29: morris with 6 trajectories on omega, c, and focal_distance (6 × (3+1) = 24 runs), then active_subspace with its smallest example size.
(b) step8: linear_coeffs with log_output true, n about 30.
(c) step6: curve1d in radius with 21 points, once for model_global and once for model_adaptive (42 runs).
Use `ema estimate` to give the total run count and the estimated time for each campaign. Ask me before any `ema run`.
After I approve and the runs finish, report whether EMA found:
- step29: one active direction proportional to (1, −1) in (ln omega, ln c);
- step8: power_law, with exponent +1 for force and lambda and mu summing to −1;
- step6: jumps or kinks in radius, more of them in the adaptive model.
Then stop.
```

```text
Stage 6 — deal.II: troubleshooting.
Package deal.II, Docker image dealii/dealii:v9.7.1-noble on the Intel Mac or the 9.6.0 PPA on Ubuntu 24.04. For the failing model in examples/dealii/, check these in order and report what you find before changing anything:
(1) "Could not find a package configuration file provided by deal.II": deal.II_DIR is not set. In the image, look for deal.IIConfig.cmake under /usr and pass -DDEAL_II_DIR.
(2) An UMFPACK assertion in step-29: the library was built without UMFPACK. Report `grep UMFPACK` in deal.IIConfig.cmake.
(3) "Permission denied" writing to /work: the container user's uid doesn't match; add --user $(id -u):$(id -g).
(4) Tutorial and library versions differ: compile errors about removed functions. The tutorial tag must match the library version.
(5) Runs are slow on the Mac: measure `docker run --rm <image> true`, and check the Docker Desktop CPU count against EMA's -j.
(6) A mixed-up binary: a Linux ELF can't run natively on macOS, so the Docker command is required there.
(7) Outputs with small jumps: adaptive refinement is on, or a Krylov solver has a loose tolerance.
Don't reinstall anything without asking. Stop and report.
```

**Gotchas and sources.**
- License: Apache-2.0 with the LLVM exception, or LGPL-2.1+. Fine to wrap and redistribute modified tutorials with attribution.
- Version pitfall: the tutorial code must come from the same tag as the library, and the three routes give three versions: 9.5.1 (noble), 9.6.0 (PPA), and 9.7.1 (Docker). 9.8.0 is released but has no Docker tag or PPA yet.
- A binary built in the Linux image runs only inside that image. On the Mac, every run is a `docker run`. Pin the image by digest, or a re-tag silently changes the model.
- MPI tutorials (step-40 and later, `-mpi` examples) make reductions depend on the rank count. Stay serial.
- Adaptive refinement (step-6 and step-8 by default) makes outputs piecewise constant or jumpy in geometric and coefficient inputs. Use global refinement unless the jumps are what you want to study.
- step-29's own documentation reports 0.7 s at the default settings in a release build. Debug builds (the default `make` in some setups) are about 10× slower **(unconfirmed factor)**, so always `make release`.
- Sources: https://www.dealii.org/ ; https://www.dealii.org/current/doxygen/deal.II/Tutorial.html ; https://www.dealii.org/current/doxygen/deal.II/step_29.html ; https://www.dealii.org/current/doxygen/deal.II/step_8.html ; https://www.dealii.org/current/doxygen/deal.II/step_6.html ; https://github.com/dealii/dealii/wiki/Getting-deal.II ; https://hub.docker.com/r/dealii/dealii/tags ; https://github.com/dealii/dealii/wiki/Docker-Images ; https://launchpad.net/~ginggs/+archive/ubuntu/deal.ii-9.6.0-backports ; https://packages.ubuntu.com/noble/libdeal.ii-dev ; https://api.anaconda.org/package/conda-forge/dealii ; https://api.github.com/repos/dealii/dealii/releases

---

#### MFEM

**What it is.** A lightweight, scalable C++ finite-element library from LLNL, licensed BSD-3-Clause. The current release is **v4.10 (September 2026)** ([mfem.org/download](https://mfem.org/download/)).
- There are **41 example codes** in `examples/` (`exN.cpp`, plus parallel `exNp.cpp`) and several miniapps: electromagnetics (Volta, Tesla, Joule), Navier, meshing, and more ([mfem.org/examples](https://mfem.org/examples/)). Each example takes command-line options through `OptionsParser`.
- The Python bindings **PyMFEM 4.10.0** (2026-09-21) ship 42 serial `ex*.py` ports ([PyPI](https://pypi.org/project/mfem/); [PyMFEM examples](https://github.com/mfem/PyMFEM/tree/master/examples)).

**Install on an Intel Mac.** Build serial MFEM from source with the Xcode Command Line Tools. Serial MFEM has no required dependencies, so this is short and uses no package manager ([building](https://mfem.org/building/)). Alternatives were checked and rejected:
- Homebrew's `mfem` 4.10 has bottles for Apple Silicon and Linux only, not Intel ([formulae.brew.sh](https://formulae.brew.sh/formula/mfem)).
- PyMFEM has wheels for manylinux x86_64 and macOS arm64 only ([PyPI](https://pypi.org/project/mfem/)).
- conda-forge `mfem` **4.8** does have osx-64 ([anaconda API](https://api.anaconda.org/package/conda-forge/mfem)), but that is older.

1. Install the compilers if they are missing: `xcode-select --install`, then check with `c++ --version` and `make --version`.
2. Build:
   ```bash
   mkdir -p ~/pde/mfem && cd ~/pde/mfem
   git clone --depth 1 --branch v4.10 https://github.com/mfem/mfem.git mfem-4.10
   cd mfem-4.10 && make serial -j 4
   cd examples && make ex1 ex2 ex16
   ```
3. Check: `./ex1 -m ../data/star.mesh -no-vis`. It should print the problem size and write `refined.mesh` and `sol.gf`.
4. Fallback: `conda create -n mfem -c conda-forge mfem=4.8 cxx-compiler make`, then build the examples against it. Whether the examples' makefile finds a conda-installed MFEM is **(unconfirmed)**; you may need `make MFEM_DIR=$CONDA_PREFIX` or CMake.
5. Docker fallback: `ghcr.io/mfem/containers/cpu:latest`, which has OpenMPI and hypre; pin it by digest. It is published only as `latest`, and the MFEM version inside it and whether it is amd64 are **(unconfirmed)** ([containers README](https://github.com/mfem/containers/blob/main/README.md)).

Known problem: `-vis` is on by default in most examples and tries to connect to a GLVis socket. Always pass `-no-vis`.

**Install on AWS (Ubuntu 24.04 EC2).**
1. `sudo apt-get update && sudo apt-get install -y build-essential git`
2. Build as on the Mac (steps 2–3 above). Check: `./ex1 -m ../data/star.mesh -no-vis`.
3. Optional Python route, which suits drivers written in Python:
   ```bash
   sudo apt-get install -y python3-venv
   python3 -m venv ~/pde/pymfem-env && ~/pde/pymfem-env/bin/pip install mfem==4.10.0
   ~/pde/pymfem-env/bin/python -c "import mfem.ser as mfem; print(mfem.__file__)"
   ```
   These are manylinux x86_64 wheels for CPython 3.11–3.14; Ubuntu 24.04 ships Python 3.12.
4. Docker fallback: `ghcr.io/mfem/containers/cpu:latest`, pinned by digest ([github.com/mfem/containers](https://github.com/mfem/containers)).

**Preparing the examples for EMA.**
- **Where the inputs go.** On the command line. For example, `ex16 -k 0.5 -a 0.01 -tf 0.5 -dt 0.01 -r 2 -o 2 -m star.mesh -no-vis`, and EMA can put inputs directly into arguments. Coefficients that are hard-coded (ex2's λ and μ, its pull force) need one `args.AddOption(...)` line each.
- **Static files.** The mesh files come from `mfem/data/` (`star.mesh`, `beam-tri.mesh`). Copy them into the model directory as static files, and name them with `-m`.
- **Shrinking to laptop size.** Use `-r` (refinement levels) and `-o` (order); for time-dependent examples, also `-tf` and `-dt`.
- **Scalar output.** Add one print at the end, `std::cout << "EMA_OUTPUT " << std::setprecision(17) << value << std::endl;`, and parse it with a regex on stdout.
- **Model type.** Build the serial library, which has no MPI reductions and is deterministic. Keep the executables in the model directory so the version hash covers them. The command is the binary with arguments, native on both platforms.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/ex16.cpp` ([source](https://github.com/mfem/mfem/blob/master/examples/ex16.cpp)) | nonlinear heat conduction du/dt = ∇·((κ + αu)∇u), insulated boundary, initial hot disc (u = 2 inside r = 0.5, 1 outside), star mesh | `-k` κ 0.5 [0.1, 1.0] (log); `-a` α 0.01 [0.0, 0.05]; `-tf` t_f 0.5 [0.1, 1.0]. `-dt` 0.01, `-r 2 -o 2` fixed | max nodal temperature at t_f (`u.Max()`). The mean is conserved, so don't use it | Monotone decreasing in all three. With α small, the output is close to a function of κ·t_f alone: near one active direction in (ln κ, ln t_f). **Planted staircase:** the time loop ends on a multiple of dt, so the output steps in t_f with width dt; `curve1d` and `nonsmooth` should report jumps at that resolution | est. 0.2–1 s | cli, inputs as arguments | regex on stdout |
| `examples/ex2.cpp` ([source](https://github.com/mfem/mfem/blob/master/examples/ex2.cpp)), with 5 added options | linear elasticity, two-material cantilever (`beam-tri.mesh`); material 1 is 50× stiffer; pull force −1e−2 on boundary attribute 2 | `lambda1` 50 [25, 100] (log); `mu1` 50 [25, 100] (log); `lambda2` 1 [0.5, 2] (log); `mu2` 1 [0.5, 2] (log); `force` 0.01 [0.005, 0.02] (log) | tip deflection = −(min y-displacement), positive | **Exact power law.** Linear in force (exponent +1), and the four moduli's exponents sum to −1. μ dominates bending; the λ's are likely possibly negligible. Additive in ln-space | est. < 0.5 s | cli, inputs as arguments | regex on stdout |

**Claude Code prompts.**

```text
Stage 1 — MFEM: check this machine (read-only).
Package: MFEM v4.10, built serial from source (tag v4.10) on an Intel Mac and on Ubuntu 24.04. PyMFEM 4.10.0 wheels are optional, Linux only. Don't install anything, and don't read .env.
Report: OS and version, `uname -m`, CPUs, RAM, free disk; `xcode-select -p` or build-essential; `c++ --version`, `make --version`, `git --version`; conda/mamba, Homebrew, and Docker presence (Homebrew is not to be used on Intel macOS); MPI (not needed for the serial build); python3 version.
Recommend: a native serial source build on both machines, with Docker ghcr.io/mfem/containers/cpu as the fallback.
Stop and report; don't continue.
```

```text
Stage 2a — MFEM: install on the Intel Mac.
Package: MFEM v4.10, serial, from source with the Xcode Command Line Tools. No Homebrew, no conda, and not EMA's .venv; don't read .env.
1. If the Xcode Command Line Tools are missing, ask me before running `xcode-select --install`.
2. mkdir -p ~/pde/mfem; git clone --depth 1 --branch v4.10 https://github.com/mfem/mfem.git ~/pde/mfem/mfem-4.10
3. cd there; `make serial -j 4`; then in examples/, `make ex1 ex2 ex16`.
Report the build wall time and `ls -l examples/ex1 examples/ex2 examples/ex16`.
Stop at the first error and report it verbatim; don't try Homebrew or other workarounds. Don't continue to the next stage.
```

```text
Stage 2b — MFEM: install on AWS EC2 Ubuntu 24.04 x86_64 (on the instance).
Package: MFEM v4.10, serial, from source; optionally PyMFEM 4.10.0 in its own venv. Don't read .env and don't touch EMA's .venv.
1. Ask before running: sudo apt-get update && sudo apt-get install -y build-essential git python3-venv
2. Clone tag v4.10 into ~/pde/mfem/mfem-4.10; `make serial -j $(nproc)`; in examples/, `make ex1 ex2 ex16`.
3. Optional (ask first): python3 -m venv ~/pde/pymfem-env && ~/pde/pymfem-env/bin/pip install mfem==4.10.0, then import mfem.ser.
Stop at the first error and report; don't continue.
```

```text
Stage 3 — MFEM: smoke test with ex1.
Package: MFEM v4.10 serial in ~/pde/mfem/mfem-4.10.
cd examples; time `./ex1 -m ../data/star.mesh -no-vis`, and then time `./ex16 -no-vis`.
Report stdout (sizes, iterations), the files written, and the wall time of each.
Stop and report; don't continue.
```

```text
Stage 4.1 — MFEM: prepare ex16 (nonlinear heat) as an EMA command-line model.
Start in plan mode and show me the plan first.
Package: MFEM v4.10 serial, in ~/pde/mfem/mfem-4.10. Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/, and examples/modflow/.
1. Create examples/mfem/ex16/. Copy ex16.cpp there, plus a small Makefile or build script that compiles it against ~/pde/mfem/mfem-4.10 (record that path in a README line). Copy data/star.mesh as a static file.
2. Patch ex16.cpp to print `EMA_OUTPUT <u.Max()>` with 17 digits after the time loop. Leave visualization off.
3. Build the binary into the model directory, so the version hash covers it.
4. Write model.json with the inputs as command arguments: -k kappa 0.5 [0.1, 1.0] (log), -a alpha 0.01 [0.0, 0.05], -tf t_final 0.5 [0.1, 1.0]. Fixed arguments: -dt 0.01 -r 2 -o 2 -m star.mesh -no-vis. Output: a regex on stdout. timeout_s: 60.
5. Run `ema profile examples/mfem/ex16/model.json -n 3` and report the time per run and the outputs.
Stop and report; no campaign yet.
```

```text
Stage 4.2 — MFEM: prepare ex2 (two-material cantilever) as an EMA command-line model.
Start in plan mode first.
Package: MFEM v4.10 serial. Follow the same EMA docs and examples as before.
1. Create examples/mfem/ex2/ with ex2.cpp and data/beam-tri.mesh as a static file.
2. Add OptionsParser options -l1, -m1, -l2, and -m2 (material 1 and 2 Lamé parameters; the defaults 50, 50, 1, 1 reproduce the tutorial) and -f (pull force magnitude, default 1e-2).
3. Print `EMA_OUTPUT <tip deflection>`, where tip deflection = −(minimum y-component of the displacement GridFunction), as a positive number. Keep -no-vis, and don't write the mesh and solution files.
4. Build the binary into the model directory. Inputs, all log-scale: lambda1 50 [25, 100], mu1 50 [25, 100], lambda2 1 [0.5, 2], mu2 1 [0.5, 2], force 0.01 [0.005, 0.02].
5. Verify by hand: doubling force doubles the output, and doubling all four moduli halves it. Report both ratios.
6. Run `ema profile ... -n 3` and report the time per run.
Stop and report.
```

```text
Stage 5 — MFEM: first campaigns.
Models: examples/mfem/ex16 and examples/mfem/ex2.
Propose, but don't run:
(a) ex16: morris with 8 trajectories (32 runs), plus curve1d in t_final with 41 points, so the dt-wide staircase shows (41 runs).
(b) ex2: linear_coeffs with log_output true (about 40 runs) and morris with 6 trajectories (36 runs).
Give the total run count and `ema estimate` for each, and ask me before `ema run`.
Afterwards report:
- ex16: monotone effects, and jumps in t_final at about the 0.01 spacing;
- ex2: power_law, with the force exponent about +1, the moduli exponents summing to about −1, and whether the lambdas are flagged possibly negligible.
Stop.
```

```text
Stage 6 — MFEM: troubleshooting.
Package: MFEM v4.10, serial build. For a failing model in examples/mfem/, check these and report before changing anything:
(1) The run hangs or fails "Unable to connect to GLVis": -no-vis is missing.
(2) "Can not open mesh file": the mesh is not listed as a static file, or -m names the path from the tutorial (../data/...).
(3) Link errors when building outside examples/: MFEM_DIR or config.mk paths. Use the library's config/config.mk.
(4) Every output is identical: the new option was added after args.Parse(), or not wired to the coefficient.
(5) ex16 fails at large alpha or dt: the time integrator diverged. Report t, and consider a smaller dt.
(6) Timeouts: the refinement level (-r) or order is too high.
Don't rebuild the library without asking. Stop and report.
```

**Gotchas and sources.**
- License: BSD-3, so redistribution of patched examples is unrestricted. Keep the notice.
- Serial builds have no MPI. Parallel `exNp` examples need hypre and METIS, and their reductions can vary with the rank count.
- Every example opens a GLVis socket unless given `-no-vis`. Examples write files like `refined.mesh` and `sol.gf` into the working directory, which is fine inside an EMA run directory.
- ex16 conserves the mean temperature (insulated boundary), so a "mean temperature" output would be constant. EMA should then report `constant_output`, which is a useful sanity check.
- ex16's final time is a whole number of steps, so t_f is effectively quantised to dt.
- PyMFEM has no Intel macOS wheel. A source build (`pip install ./ -C"with-parallel=No"`) is possible but untested here **(unconfirmed on Intel macOS 2026)**.
- Sources: https://mfem.org/download/ ; https://mfem.org/examples/ ; https://mfem.org/building/ ; https://github.com/mfem/mfem ; https://formulae.brew.sh/formula/mfem ; https://api.anaconda.org/package/conda-forge/mfem ; https://pypi.org/project/mfem/ ; https://github.com/mfem/PyMFEM ; https://github.com/mfem/containers ; https://mfem.org/tutorial/docker/

---

#### DUNE

**What it is.** DUNE is a modular C++ framework:
- The core modules are dune-common, dune-geometry, dune-grid, dune-istl, and dune-localfunctions.
- The discretization modules are PDELab and dune-fem.
- Licenses: the core modules are GPL-2 with a runtime exception ([license](https://www.dune-project.org/about/license/)); dune-fem is GPL-2+ ([PyPI](https://pypi.org/project/dune-fem/)).

The practical way in is **dune-fem's Python bindings**, which JIT-compile the C++ behind the scenes. `dune-fem` **2.12.0.2** was released on PyPI on 2026-06-03, as an sdist only ([PyPI JSON](https://pypi.org/pypi/dune-fem/json)). The dune-fem tutorial has Getting Started, Next Steps, and **13 example problems**: DG, elasticity, spiral wave, wave equation, Stokes, Navier–Stokes, mixed Poisson, eigenvalues, biharmonic, crystal growth, mean-curvature flow, DWR, and two-phase flow ([tutorial](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/)). The scripts are obtained with `python -m dune.fem` ([installation](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/installation.html)). PDELab's C++ tutorials are a separate collection that is not used here **(count unconfirmed)**.

**Install on an Intel Mac.** Use a dedicated environment: Python 3.12 and build tools from Miniforge (osx-64), the compilers from the Xcode Command Line Tools, then `pip install dune-fem`.
- DUNE says the pip route is tested on "a number of Linux distributions and on MacOS" ([pip install page](https://www.dune-project.org/installation/installation-pip/)). Intel macOS specifically is **(unconfirmed)**.
- Its macOS notes use Homebrew for dependencies. Avoid Homebrew on Intel (Tier 3) and take the same tools from conda-forge instead.

1. Install Miniforge for x86_64, if it is absent ([Miniforge](https://github.com/conda-forge/miniforge)):
   ```bash
   curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
   bash Miniforge3-MacOSX-x86_64.sh -b -p ~/miniforge
   ```
2. Create the environment and install dune-fem. The C++ build takes tens of minutes and needs about 8 GB RAM **(unconfirmed)**:
   ```bash
   ~/miniforge/bin/conda create -y -n dune -c conda-forge python=3.12 cmake pkg-config openmpi mpi4py suitesparse numpy scipy matplotlib
   ~/miniforge/envs/dune/bin/pip install dune-fem==2.12.0.2
   ```
3. Check, and fetch the tutorial scripts:
   ```bash
   cd ~/pde/dune && ~/miniforge/envs/dune/bin/python -m dune.fem   # creates fem_tutorial/
   cd fem_tutorial && ~/miniforge/envs/dune/bin/python concepts.py
   ```
   The first run JIT-compiles for minutes; the second should be near-instant ([installation](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/installation.html)).
4. Docker fallback: build your own image, since no official versioned dune-fem image was confirmed. Pin it by the image ID it gets ([container images](https://www.dune-project.org/dev/container-images/) point to CI images; `registry.dune-project.org/dune-fem/dune-fempy` exists **(tags unconfirmed)**). The Dockerfile is five lines:
   - `FROM python:3.12-slim-bookworm`
   - apt-install `build-essential cmake pkg-config libopenmpi-dev libsuitesparse-dev git`
   - `pip install dune-fem==2.12.0.2 mpi4py`
   - set `ENV DUNE_PY_DIR=/dune-py`, mounted from the host so the JIT cache persists.

Known problems:
- A `CMAKE_PREFIX_PATH` that finds libraries outside the environment can break later shared-library loading ([pip page](https://www.dune-project.org/installation/installation-pip/)). Keep the conda environment clean.
- Mixing conda's `openmpi` with the Xcode clang is the most likely failure **(unconfirmed)**. If it happens, drop `openmpi mpi4py` and try again with a serial build.

**Install on AWS (Ubuntu 24.04 EC2).** Install natively with pip in a dedicated venv.
- Noble has only the core C++ packages, at 2.9.0 (`libdune-grid-dev` 2.9.0; [packages.ubuntu.com](https://packages.ubuntu.com/noble/libdune-grid-dev); [deb page](https://www.dune-project.org/installation/installation-deb/)). It has no dune-fem Python bindings **(unconfirmed)**, so use pip.

1. Install the build dependencies and dune-fem:
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential cmake pkg-config git \
        libopenmpi-dev openmpi-bin libsuitesparse-dev python3-dev python3-venv
   python3 -m venv ~/pde/dune-env && ~/pde/dune-env/bin/pip install dune-fem==2.12.0.2 mpi4py
   ```
2. Check: `~/pde/dune-env/bin/python -m dune.fem && cd fem_tutorial && ~/pde/dune-env/bin/python concepts.py`.
3. Instance: `c7i.2xlarge` for the build; the parallel compile needs RAM.
4. Docker fallback: the Dockerfile above.

**Preparing the examples for EMA.**
- **Where the inputs go.** In the tutorials the parameters are Python variables (`lamb`, `mu`, `rho`, `g` in elasticity; `spiral_a`, `spiral_b`, `spiral_eps`, `spiral_D`, `dt` in the spiral). Turn each script into a small driver that reads a deck, a `key = value` text template, and prints one number.
- **Constants, not floats.** Put every input into the UFL form as a `dune.ufl.Constant` and never as a literal Python float. A literal float is baked into the generated C++, so every new value triggers a new JIT compile (tens of seconds) and fills the cache. With `Constant`, the compiled module is reused ([tutorial intro](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/dune-fempy_nb.html)).
- **The JIT cache.** Set `DUNE_PY_DIR` to a fixed absolute path in the spec's `env`, never the run directory, so every run reuses one cache ([python bindings](https://www.dune-project.org/installation/installation-pythonbindings/)). Warm the cache with one serial run before any parallel campaign. Several workers compiling the same module at once is a likely failure **(unconfirmed)**.
- **Shrinking and output.** Shrink with the structured grid's cell counts and `endTime`. Compute the scalar output with `dune.fem.integrate` over the domain, and drop plotting and VTK output.
- **Model type.** A command-line model whose command is the environment's absolute Python path running `driver.py` from the model directory. It is not a Python-function model, because dune-fem lives in its own environment, not EMA's `.venv`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `fem_tutorial` elasticity ([page](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/elasticity_nb.html)) | linear elasticity: beam [0,1]×[0,0.15], 100×15 cells, clamped left end, gravity load, CG + ILU | `lamb` 0.1 [0.05, 0.2] (log); `mu` 1 [0.5, 2] (log); `rho` 1e-3 [5e-4, 2e-3] (log); `g` = 9.8 fixed | mean vertical deflection −∫u_y dx / \|Ω\| (positive), via `integrate` | **Exact power law:** exponent +1 in ρ, and the λ and μ exponents sum to −1 (the problem is homogeneous in the moduli). μ dominates and λ is small, possibly negligible. A check that the iterative solver's tolerance doesn't show up as noise | est. 0.5–2 s after JIT; the first run takes minutes | cli (env python + driver) | regex on stdout |
| `fem_tutorial` spiral wave, Barkley model ([page](https://www.dune-project.org/sphinx/content/sphinx/dune-fem/spiral_nb.html)) | excitable reaction–diffusion on [0, 2.5]², 30×30 grid, dt 0.25 | `spiral_a` 0.75 [0.6, 0.9]; `spiral_b` 0.02 [0.005, 0.05] (log); `spiral_eps` 0.02 [0.01, 0.05] (log). `D` = 0.01 fixed; endTime shortened to about 25 (100 steps) | excited-area fraction ∫(u > 0.5) dx / \|Ω\| at endTime | **Threshold behaviour:** the wave survives or dies, so expect plateaus and jumps (`nonsmooth`, `curve1d`) and strong interactions (`sobol` `interacting`). An area fraction from a threshold is itself piecewise constant at mesh resolution, so there are small steps | est. 1–5 s after JIT | cli (env python + driver) | regex on stdout |

**Claude Code prompts.**

```text
Stage 1 — DUNE: check this machine (read-only).
Package: dune-fem 2.12.0.2 from PyPI (sdist; it compiles C++ at install and JIT-compiles at run time), in a dedicated conda env "dune" (Intel Mac) or venv ~/pde/dune-env (Ubuntu 24.04). Don't install anything, and don't read .env.
Report: OS, `uname -m`, CPUs, RAM (the build needs about 8 GB), free disk (needs about 5 GB); c++ and cmake versions; pkg-config; conda/mamba (Miniforge?) and Homebrew (don't use it on Intel macOS); Docker; MPI; python3 version.
Recommend: Miniforge env + pip on the Mac, a venv + apt build tools on AWS, and a self-built Docker image as the fallback.
Stop and report; don't continue.
```

```text
Stage 2a — DUNE: install dune-fem 2.12.0.2 on the Intel Mac.
Use a new conda env "dune" from Miniforge (osx-64), not EMA's .venv. No Homebrew; don't read .env.
1. If Miniforge is absent, ask before downloading Miniforge3-MacOSX-x86_64.sh from github.com/conda-forge/miniforge and installing it to ~/miniforge.
2. conda create -y -n dune -c conda-forge python=3.12 cmake pkg-config openmpi mpi4py suitesparse numpy scipy matplotlib
3. ~/miniforge/envs/dune/bin/pip install dune-fem==2.12.0.2 — run it in the background, log to ~/pde/dune/install.log, and report its wall time.
Stop at the first error, show the last 40 lines of the log, and don't try other channels or Homebrew. Don't continue.
```

```text
Stage 2b — DUNE: install dune-fem 2.12.0.2 on AWS EC2 Ubuntu 24.04 (on the instance).
Use the venv ~/pde/dune-env, not EMA's .venv; don't read .env.
1. Ask before running: sudo apt-get update && sudo apt-get install -y build-essential cmake pkg-config git libopenmpi-dev openmpi-bin libsuitesparse-dev python3-dev python3-venv
2. python3 -m venv ~/pde/dune-env && ~/pde/dune-env/bin/pip install dune-fem==2.12.0.2 mpi4py — log it to ~/pde/dune/install.log and report the wall time.
Stop at the first error with the log tail; don't continue.
```

```text
Stage 3 — DUNE: smoke test.
Package: dune-fem 2.12.0.2 in the env from stage 2 (Mac ~/miniforge/envs/dune/bin/python; AWS ~/pde/dune-env/bin/python).
In ~/pde/dune: set DUNE_PY_DIR=~/pde/dune/dune-py, run `python -m dune.fem` to get fem_tutorial/, then run `python concepts.py` twice.
Report both wall times (the first includes JIT; the second should be much shorter), the size of ~/pde/dune/dune-py, and any warnings.
Stop and report; don't continue.
```

```text
Stage 4.1 — DUNE: prepare the elasticity tutorial as an EMA command-line model.
Start in plan mode first.
Package: dune-fem 2.12.0.2 in its own env. Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/ (a Python driver reading a small deck: the closest pattern), and examples/modflow/.
1. Create examples/dune/elasticity/ with driver.py, adapted from fem_tutorial's elasticity script. The driver:
   - reads deck.txt (lamb, mu, rho);
   - puts them in the form as dune.ufl.Constant, never as Python floats;
   - keeps the 100×15 grid;
   - prints `EMA_OUTPUT <value>` with 17 digits, where value = −(integral of u_y)/area;
   - does no plotting.
2. deck.template has $lamb, $mu and $rho.
3. model.json:
   - command: [<absolute path of the env's python>, "driver.py"];
   - env: DUNE_PY_DIR=<absolute path ~/pde/dune/dune-py>;
   - inputs: lamb 0.1 [0.05, 0.2], mu 1 [0.5, 2], rho 1e-3 [5e-4, 2e-3], all log-scale;
   - output: a regex on stdout; timeout_s: 900, for the first JIT.
4. Warm the JIT cache with one serial run, then run `ema profile ... -n 3` and confirm that no run recompiles. Report the times.
5. Check by hand: doubling rho doubles the output; doubling lamb and mu halves it.
Stop and report.
```

```text
Stage 4.2 — DUNE: prepare the spiral-wave (Barkley) tutorial as an EMA command-line model.
Start in plan mode first.
Package: dune-fem 2.12.0.2, same env and DUNE_PY_DIR as stage 4.1.
1. Create examples/dune/spiral/driver.py from fem_tutorial's spiral script, using the linear parameter set. The driver:
   - reads spiral_a, spiral_b and spiral_eps from a deck, as dune.ufl.Constant;
   - keeps D = 0.01, the 30×30 grid, and dt = 0.25, with endTime 25;
   - prints `EMA_OUTPUT <fraction of the domain where u > 0.5 at endTime>`;
   - has no animation.
2. Inputs: spiral_a 0.75 [0.6, 0.9], spiral_b 0.02 [0.005, 0.05] (log), spiral_eps 0.02 [0.01, 0.05] (log).
3. Warm the JIT cache, then run `ema profile -n 3`. Report the time per run. If it is over 10 s, propose a shorter endTime.
Stop and report.
```

```text
Stage 5 — DUNE: first campaigns.
Models: examples/dune/elasticity and examples/dune/spiral. The JIT cache must already be warm.
Propose, but don't run:
(a) elasticity: linear_coeffs with log_output true, n about 30.
(b) spiral: morris with 6 trajectories (24 runs), then curve1d in spiral_b with 21 points.
Give the run counts and `ema estimate`, and ask before `ema run`. Use -j 2 at most for the first campaign.
Afterwards report:
- elasticity: power_law, with the rho exponent about +1 and lamb + mu about −1;
- spiral: interactions, and any jumps or plateaus in spiral_b.
Stop.
```

```text
Stage 6 — DUNE: troubleshooting.
Package: dune-fem 2.12.0.2. For a failing DUNE model in examples/dune/, check and report before changing anything:
(1) Every run takes minutes: an input entered the form as a float, not a Constant, so each value compiles a new module. Grep the driver, and look at the growth of DUNE_PY_DIR.
(2) Errors in parallel runs only: a JIT race. Warm the cache serially, and use -j 1 until it's warm.
(3) An ImportError or missing .so at run time: the env's python is not the one in the command, or a CMAKE_PREFIX_PATH or LD_LIBRARY_PATH problem (see the DUNE pip page).
(4) MPI init errors when run from EMA: mpi4py/openmpi in a non-MPI launch. Try OMPI_MCA settings in env, or remove the explicit mpi4py import.
(5) The pip build is killed: out of memory. Use a larger instance, or MAKEFLAGS=-j2.
(6) After a dependency change: delete the dune-py cache (the docs say it must be rebuilt).
Stop and report.
```

**Gotchas and sources.**
- License: GPL-2 with a runtime exception (core), and GPL-2+ for dune-fem. Patched tutorial drivers that are shipped in EMA's repo should keep the GPL notice.
- **JIT compile cost dominates.** The first use of each new form compiles C++ for minutes. Parameters must be `Constant`s, the cache (`DUNE_PY_DIR`) must be shared and warm, and `ema profile` must be run after warming.
- The PyPI release is an sdist only, so every install compiles, on both machines.
- Ubuntu's 2.9.0 packages are core C++ only. Don't mix them with the pip install.
- Iterative solvers (CG + ILU) give tolerance-level jitter. Tighten the tolerance, or finite differences will see noise.
- Sources: https://www.dune-project.org/sphinx/content/sphinx/dune-fem/ ; https://www.dune-project.org/sphinx/content/sphinx/dune-fem/installation.html ; https://www.dune-project.org/installation/installation-pip/ ; https://www.dune-project.org/installation/installation-deb/ ; https://www.dune-project.org/installation/installation-pythonbindings/ ; https://www.dune-project.org/dev/container-images/ ; https://pypi.org/project/dune-fem/ ; https://packages.ubuntu.com/noble/libdune-grid-dev ; https://www.dune-project.org/about/license/ ; https://www.dune-project.org/sphinx/content/sphinx/dune-fem/elasticity_nb.html ; https://www.dune-project.org/sphinx/content/sphinx/dune-fem/spiral_nb.html

---

#### MOOSE

**What it is.** INL's multiphysics framework in C++, built on libMesh and PETSc and licensed LGPL-2.1 ([LICENSE](https://raw.githubusercontent.com/idaholab/moose/master/LICENSE)). Inputs are hierarchical `.i` files (HIT). The collection:
- 21 framework examples, `examples/ex01_inputfile` to `ex21_debugging` ([GitHub](https://github.com/idaholab/moose/tree/master/examples)).
- Tutorials: `tutorials/darcy_thermo_mech`, which needs its own compiled app.
- Module tutorials, for example `modules/heat_transfer/tutorials/introduction/therm_step01–03.i`, `modules/solid_mechanics/tutorials/introduction/mech_step01–…i`, and `modules/porous_flow/examples/tutorial/01.i…`.
- Thousands of module test inputs **(count unconfirmed)**.
- The prebuilt executable (`moose`/`moose-opt`, with all modules) can copy the module inputs out with `--copy-inputs <module>` ([Docker docs](https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/docker.md)).

**Install on an Intel Mac.** Use Docker with `idaholab/moose`, which is amd64 only, so it runs natively on Intel. It is about 1.9 GB, with all modules compiled into `/opt/moose` and `moose-opt` on the PATH.
- The INL conda channel's osx-64 folder has `moose-dev` 2026.08.23 (the build environment) but **no prebuilt `moose` package** ([conda.software.inl.gov/public/osx-64](https://conda.software.inl.gov/public/osx-64/)).
- MOOSE maintainers say Intel Mac support ends in line with Apple's timeline ([discussion #32539](https://github.com/idaholab/moose/discussions/32539)).
- Building the modules natively from `moose-dev` is possible but takes a long time **(unconfirmed duration: likely an hour or more)**.

1. Install Docker Desktop for Mac (Intel) ([docs](https://docs.docker.com/desktop/setup/install/mac-install/)).
2. Pull a dated tag and record its digest ([tags](https://hub.docker.com/r/idaholab/moose/tags)):
   ```bash
   docker pull idaholab/moose:2026.08.12-167ee97
   docker inspect --format '{{index .RepoDigests 0}}' idaholab/moose:2026.08.12-167ee97
   # Docker Hub on 2026-09-24 (verify): sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452
   ```
3. Copy the inputs out and check:
   ```bash
   mkdir -p ~/pde/moose && cd ~/pde/moose
   docker run --rm -v "$PWD":/projects -w /projects idaholab/moose:2026.08.12-167ee97 \
       bash -lc 'moose-opt --copy-inputs heat_transfer && moose-opt --copy-inputs solid_mechanics && moose-opt --copy-inputs porous_flow'
   docker run --rm -v "$PWD":/projects -w /projects/moose/heat_transfer/tutorials/introduction idaholab/moose:2026.08.12-167ee97 \
       moose-opt -i therm_step01.i
   ```
   - The exact directory layout that `--copy-inputs` creates is **(unconfirmed)**; the docs show `moose/<module>`.
   - Known problem: the images are Rocky Linux with MPICH, and `/environment` may need sourcing in `moose-dev` images ([docker docs](https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/docker.md)).
   - Alternative: `conda create -n moose-dev moose-dev=2026.08.23` from the INL channel, then clone MOOSE at the matching commit and build `modules/heat_transfer` and `modules/solid_mechanics` with `make -j4`. A maintainer confirmed that `moose-dev=2025.06.20` worked on an Intel Mac ([#32539](https://github.com/idaholab/moose/discussions/32539)).

**Install on AWS (Ubuntu 24.04 EC2).** Install natively with the prebuilt conda package `moose` from INL's channel. It is linux-64, **2026.09.13**, about 387 MB, with mpich and openmpi builds ([linux-64 listing](https://conda.software.inl.gov/public/linux-64/); [prebuilt docs](https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/moose_conda_binary.md); [Miniforge steps](https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/install_miniconda.md)).

1. Install Miniforge and create the environment:
   ```bash
   curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   bash Miniforge3-Linux-x86_64.sh -b -p ~/miniforge
   ~/miniforge/bin/conda config --add channels https://conda.software.inl.gov/public
   ~/miniforge/bin/conda create -y -n moose moose=2026.09.13
   ```
2. Check: `~/miniforge/envs/moose/bin/moose --help`. The docs use `moose --help` for the conda package and `moose-opt` in Docker; which names the conda package installs is **(unconfirmed)**, so check with `ls ~/miniforge/envs/moose/bin | grep -i moose`.
3. Copy the inputs: `moose --copy-inputs heat_transfer` (likewise `solid_mechanics`, `porous_flow`).
4. Docker fallback: the same `idaholab/moose:2026.08.12-167ee97` image, pinned by digest.

**Preparing the examples for EMA.**
- **Where the inputs go.** In the `.i` file: `Materials/thermal/thermal_conductivity`, `BCs/.../function`, and so on. There are two ways to vary them:
  - Make the `.i` a template with `$k` placeholders.
  - Pass MOOSE command-line overrides as arguments, `moose-opt -i therm.i Materials/thermal/thermal_conductivity=45`. EMA can put inputs into arguments.
- **Escaping `$` in templates.** HIT uses `${var}` and `${fparse ...}` substitution, so every existing `${` in a template must be written `$${` for EMA.
- **Shrinking.** Use `Mesh/.../nx, ny`, `Executioner/end_time, dt`, and `Outputs/exodus=false`.
- **Scalar output.** Add a `[Postprocessors]` block (`PointValue`, `SideAverageValue`, `ElementExtremeValue`) and `[Outputs] csv = true`. MOOSE then writes `<input>_out.csv` with a `time` column and one column per postprocessor, and EMA's csv parser takes that column at row −1.
- **Determinism.** Run one process (no `mpiexec`), set `--n-threads=1` and `OMP_NUM_THREADS=1`, and use LU (`-pc_type lu`, as mech_step02 does) or tight tolerances.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `modules/heat_transfer/tutorials/introduction/therm_step03.i` ([raw](https://raw.githubusercontent.com/idaholab/moose/master/modules/heat_transfer/tutorials/introduction/therm_step03.i)) | transient conduction on a 2×1 block (10×10), T = 300 on the left, right boundary ramped at 300 + r·t, 5 steps | `thermal_conductivity` 45 [10, 100] (log); `specific_heat` 0.5 [0.25, 1] (log); `density` 8000 [4000, 16000] (log); ramp `r` 5 [1, 10] K/s (log), written into `function = '300+$r*t'` | T − 300 at (1, 0.5) at t = 5 (`PointValue` postprocessor on T, minus 300 in a `ParsedPostprocessor`) | **Exactly linear in r.** ρ and c_p enter only as their product, and with k only through the diffusivity k/(ρc_p). So there are 2 active directions in ln-space: the ρ and c_p exponents are equal, and the k exponent is opposite. Monotone and smooth | est. 1–3 s (app start-up dominates) + Docker start on the Mac | cli | csv (`_out.csv`, column of the postprocessor, row −1) |
| `modules/solid_mechanics/tutorials/introduction/mech_step02.i` ([raw](https://raw.githubusercontent.com/idaholab/moose/master/modules/solid_mechanics/tutorials/introduction/mech_step02.i)) | small-strain plane elasticity, bottom fixed, pressure 1e7·t on the top, LU | `youngs_modulus` 1e9 [5e8, 2e9] (log); `poissons_ratio` 0.3 [0.2, 0.45]; pressure rate `p` 1e7 [5e6, 2e7] (log) | −(top-surface average disp_y) at t = 5 (`SideAverageValue`) | **Power law:** exponent +1 in p and −1 in E (exact for linear elasticity). Smooth and nonlinear in ν | est. 1–3 s | cli | csv |
| `modules/porous_flow/examples/tutorial/01.i` ([raw](https://raw.githubusercontent.com/idaholab/moose/master/modules/porous_flow/examples/tutorial/01.i)) | single-phase Darcy injection into an aquifer, annular 3-D mesh, porepressure fixed at 1e6 Pa on the injection area, end_time 1e6 s | aquifer `permeability` 1e-14 [1e-15, 1e-13] m² (log, all three diagonal entries from one placeholder); injection `porepressure` 1e6 [5e5, 2e6] Pa (log) | porepressure at a point in the aquifer at r ≈ 5 m, z = 0, at end_time (`PointValue`) | Near-linear in injection pressure (exactly linear if fluid properties are constant; check the tutorial's fluid). **Sigmoid in ln(permeability):** the diffusion front reaches the point or not, so expect a plateau and saturation in `curve1d`. Low dimension | est. 2–5 s | cli | csv |

**Claude Code prompts.**

```text
Stage 1 — MOOSE: check this machine (read-only).
Package: MOOSE. On the Intel Mac: Docker image idaholab/moose:2026.08.12-167ee97 (amd64, about 1.9 GB, moose-opt with all modules), because the INL conda channel has no prebuilt osx-64 moose. On Ubuntu 24.04: the conda package moose=2026.09.13 from https://conda.software.inl.gov/public. Don't install anything; don't read .env.
Report: OS, `uname -m`, CPUs, RAM, free disk (needs 5+ GB); Docker (running? CPU/memory allocation); conda/Miniforge; Homebrew (don't use it on Intel); MPI; compilers.
Recommend: the route above for this machine.
Stop and report; don't continue.
```

```text
Stage 2a — MOOSE: install on the Intel Mac (Docker).
Package: MOOSE via idaholab/moose:2026.08.12-167ee97. Not EMA's .venv; don't read .env.
1. The image is about 1.9 GB: ask me before pulling. Then record `docker inspect --format '{{index .RepoDigests 0}}' idaholab/moose:2026.08.12-167ee97`; Docker Hub showed sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452 on 2026-09-24, so say whether it matches.
2. In ~/pde/moose, run moose-opt --copy-inputs for heat_transfer, solid_mechanics, and porous_flow inside the container, with ~/pde/moose mounted at /projects. Report the directory tree two levels deep.
Stop at the first error and report; don't try to build MOOSE from source. Don't continue.
```

```text
Stage 2b — MOOSE: install on AWS EC2 Ubuntu 24.04 (on the instance).
Package: prebuilt MOOSE conda package moose=2026.09.13, in env "moose" from the INL channel https://conda.software.inl.gov/public. Not EMA's .venv; don't read .env; no sudo needed.
1. If Miniforge is absent, ask, then install Miniforge3-Linux-x86_64.sh to ~/miniforge.
2. conda config --add channels https://conda.software.inl.gov/public; conda create -y -n moose moose=2026.09.13 (about 400 MB).
3. Report which moose executables are in ~/miniforge/envs/moose/bin and the output of `<exe> --help | head`.
4. Copy the inputs for heat_transfer, solid_mechanics, and porous_flow into ~/pde/moose.
If conda can't solve the environment, stop and ask about the Docker fallback (idaholab/moose:2026.08.12-167ee97, pinned by digest; Docker Engine install needs sudo, so ask). Don't continue.
```

```text
Stage 3 — MOOSE: smoke test.
Package: MOOSE (the Docker image pinned by digest on the Mac, or conda moose=2026.09.13 on AWS).
Run heat_transfer/tutorials/introduction/therm_step01.i with --n-threads=1 in a scratch copy under ~/pde/moose/smoke.
Report the files written, the final lines of the console output, and the wall time. On the Mac, also report the time of `docker run --rm <image> true`, the per-run overhead.
Stop and report; don't continue.
```

```text
Stage 4.1 — MOOSE: prepare therm_step03 (transient conduction) as an EMA command-line model.
Start in plan mode first.
Package: MOOSE (Docker idaholab/moose pinned by digest on the Intel Mac; conda moose=2026.09.13 on AWS). Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/, and examples/modflow/.
1. Copy therm_step03.i to examples/moose/therm/therm.template.
2. Set exodus = false. Add a PointValue postprocessor for T at (1, 0.5, 0), and a ParsedPostprocessor for dT = T − 300. Set [Outputs] csv = true (the file base is fixed, e.g. out).
3. Placeholders: $k (thermal_conductivity), $cp (specific_heat), $rho (density) and $r (ramp, in function = '300+$r*t'). Escape any existing ${ ... } as $${ ... }.
4. Inputs, all log-scale: k 45 [10, 100], cp 0.5 [0.25, 1], rho 8000 [4000, 16000], r 5 [1, 10].
5. model.json:
   - command: moose-opt (Docker on the Mac, with the run directory mounted; check whether EMA expands $EMA_WORKDIR inside a longer argument, or use a wrapper script) or the conda executable's absolute path on AWS, with -i therm.i --n-threads=1;
   - env: OMP_NUM_THREADS=1;
   - output: the csv parser on out.csv, column dT, row −1.
6. Check by hand: doubling r doubles dT, and doubling k, rho, and cp together leaves dT unchanged. Report both, plus `ema profile -n 3` times.
Stop and report.
```

```text
Stage 4.2 — MOOSE: prepare mech_step02 (elastic block under pressure) as an EMA command-line model.
Start in plan mode first.
Package: MOOSE, same route as 4.1. Follow the same EMA docs and examples.
1. Copy mech_step02.i to examples/moose/mech/mech.template.
2. Placeholders: $E (youngs_modulus), $nu (poissons_ratio), $p (the 1e7 in function = 1e7*t, becoming $p*t).
3. Add a SideAverageValue on disp_y over boundary top, and a ParsedPostprocessor defl = −(that average). Set csv = true and exodus = false.
4. Inputs: E 1e9 [5e8, 2e9] (log), nu 0.3 [0.2, 0.45], p 1e7 [5e6, 2e7] (log). The output parser takes column defl, row −1.
5. Check by hand that defl ∝ p/E (doubling both leaves it unchanged, to 1e-8 relative). Run `ema profile -n 3` and report.
Stop and report.
```

```text
Stage 4.3 — MOOSE: prepare porous_flow tutorial 01 (Darcy injection) as an EMA command-line model.
Start in plan mode first.
Package: MOOSE, same route. Follow the same EMA docs and examples.
1. Copy porous_flow/examples/tutorial/01.i to examples/moose/injection/injection.template.
2. Placeholders: $perm (all three diagonal entries of permeability_aquifer) and $p_inj (the injection DirichletBC value).
3. Add a PointValue of porepressure at (5, 0.5, 0), after checking that this point lies in the aquifer block (z in [−2, 2]) and inside the annulus. Set csv = true and exodus = false.
4. Inputs: perm 1e-14 [1e-15, 1e-13] (log), p_inj 1e6 [5e5, 2e6] (log).
5. Report which fluid-properties object the tutorial uses: if its properties are constant, the output should be linear in p_inj.
6. Run `ema profile -n 3`. If a run exceeds 10 s, propose a coarser mesh (nr) or fewer time steps.
Stop and report.
```

```text
Stage 5 — MOOSE: first campaigns.
Models: examples/moose/therm, mech, and injection.
Propose, but don't run:
(a) therm: linear_coeffs with log_output (about 30 runs) and active_subspace at its smallest example size.
(b) mech: linear_coeffs with log_output (about 30 runs).
(c) injection: curve1d in perm with 21 points, and morris with 4 trajectories (12 runs).
Give the run counts and `ema estimate`, and ask me before `ema run`. On the Mac, set -j no higher than the Docker Desktop CPU count.
Afterwards report:
- therm: the rho and cp exponents are equal, the k exponent is opposite, and r is linear;
- mech: power_law with exponents +1 (p) and −1 (E);
- injection: a plateau or saturation in perm.
Stop.
```

```text
Stage 6 — MOOSE: troubleshooting.
Package: MOOSE (Docker idaholab/moose pinned by digest, or conda moose=2026.09.13). For a failing model in examples/moose/, check these and report before changing anything:
(1) EMA reports "invalid $ syntax": a HIT ${...} or $ in the template must be written $$.
(2) "did not converge": print the nonlinear residuals, relax nl_rel_tol, or reduce dt. EMA records the run as failed, which is fine for a few points.
(3) Missing out.csv: file_base or csv = true is missing, or the postprocessor's execute_on is wrong.
(4) An unknown object type (e.g. PackedColumn or DarcyPressure): the tutorial needs its own app and is not in moose-opt. Use module inputs only.
(5) Slow runs: app start-up. Measure `moose-opt --version` alone. On the Mac, add the docker run overhead.
(6) Different results between -j 1 and -j 4: threads or MPI got in. Enforce --n-threads=1 and OMP_NUM_THREADS=1, and don't use mpiexec.
(7) Conda solve errors: channel priority. Keep the INL channel and conda-forge only.
Stop and report.
```

**Gotchas and sources.**
- License: LGPL-2.1. The `idaholab/moose` image bundles PETSc and libMesh, whose licenses differ; don't redistribute the image.
- **Intel Mac: no prebuilt conda package.** Docker is the realistic route, and MOOSE is ending Intel Mac support.
- `idaholab/moose` publishes dated tags about every two weeks, and `latest` moves. Pin by digest.
- HIT `${...}` substitution collides with EMA's `string.Template` syntax.
- Each run pays the start-up of a large multiphysics executable, likely about 1 s **(unconfirmed)**, even for a 10×10 mesh. Laptop runs of about 1–3 s are realistic.
- Transient problems with adaptive time stepping (`IterationAdaptiveDT`) or mesh adaptivity produce outputs that jump. Keep a fixed dt and a fixed mesh for smooth-structure studies.
- The darcy_thermo_mech tutorial needs its own compiled app, so it is excluded here.
- Sources: https://github.com/idaholab/moose ; https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/docker.md ; https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/moose_conda_binary.md ; https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/install_miniconda.md ; https://raw.githubusercontent.com/idaholab/moose/master/modules/doc/content/getting_started/installation/install_conda_moose.md ; https://conda.software.inl.gov/public/linux-64/ ; https://conda.software.inl.gov/public/osx-64/ ; https://hub.docker.com/r/idaholab/moose/tags ; https://github.com/idaholab/moose/discussions/32539 ; https://mooseframework.inl.gov/getting_started/installation/index.html (returned 403 to the fetcher, so the GitHub sources above were used instead)

---

#### Elmer

**What it is.** Elmer FEM, from CSC Finland: multiphysics finite elements (heat, elasticity, Navier–Stokes, electromagnetics, acoustics). It is written in Fortran and C++. The solver is GPL-2 and the libraries LGPL-2.1, per the [license policy](https://github.com/ElmerCSC/elmerfem/blob/devel/license_texts/ElmerLicensePolicy.md). The latest release is **26.2.1 (2026-04-29)**, under a calendar versioning scheme since 26.1 ([releases API](https://api.github.com/repos/ElmerCSC/elmerfem/releases?per_page=3)). The examples are:
- the manuals and tutorials, about 900 pages ([README](https://github.com/ElmerCSC/elmerfem));
- several hundred regression tests in `fem/tests/`, each a plain-text `.sif` deck plus a mesh **(exact count unconfirmed)**.

**Why it's included.** It is a comparable package with a rich collection of examples, and its `.sif` decks are the most template-friendly inputs of this group. `docs/applications.md` already lists it as a candidate.

**Install on an Intel Mac.** Use Docker with an image you build locally from the official recipe. The recipe is `docker/elmer.dockerfile`: `FROM ubuntu:latest`, with MPI, MUMPS, ElmerIce and Lua ([dockerfile](https://raw.githubusercontent.com/ElmerCSC/elmerfem/devel/docker/elmer.dockerfile)). No official published image was found: the older [elmerfem-docker](https://github.com/ElmerCSC/elmerfem-docker) repository has only local-build recipes, and the third-party Docker Hub images are unmaintained. Homebrew is not an option: the Elmer tap builds from source with GCC's `gfortran` ([Packages wiki](https://github.com/ElmerCSC/elmerfem/wiki/Packages)), and GCC lost its Intel bottles on 2026-09-03, so it would compile GCC first. conda-forge `elmerfem` was not found **(unconfirmed)**.

1. Install Docker Desktop (Intel).
2. Write a pinned copy of the official recipe: `FROM ubuntu:24.04`, then `git clone --branch release-26.2.1 --depth 1 https://github.com/ElmerCSC/elmerfem.git`. Use the recipe's apt list (`build-essential cmake git libblas-dev liblapack-dev libmumps-dev libparmetis-dev mpich`) plus `gfortran`. Configure with `-DWITH_MPI=FALSE -DWITH_ELMERGUI=FALSE -DCMAKE_INSTALL_PREFIX=/usr/local/elmer`, then run `make -j4 install`.
3. Build it and record the image ID. The build takes tens of minutes **(unconfirmed)**:
   ```bash
   docker build -t ema/elmer:26.2.1 -f elmer.Dockerfile .
   docker inspect --format '{{.Id}}' ema/elmer:26.2.1
   ```
4. Check: `docker run --rm ema/elmer:26.2.1 /usr/local/elmer/bin/ElmerSolver -v`. The `-v` flag is **(unconfirmed)**; running with no arguments also prints the version banner.

**Install on AWS (Ubuntu 24.04 EC2).** Build natively from source, following [compilation_instructions/Ubuntu.md](https://github.com/ElmerCSC/elmerfem/blob/devel/compilation_instructions/Ubuntu.md), which targets 24.04.

1. Build and install:
   ```bash
   sudo apt-get update && sudo apt-get install -y git cmake build-essential gfortran libopenmpi-dev libblas-dev liblapack-dev
   git clone --branch release-26.2.1 --depth 1 https://github.com/ElmerCSC/elmerfem.git ~/pde/elmer/src
   mkdir -p ~/pde/elmer/build && cd ~/pde/elmer/build
   cmake -DWITH_ELMERGUI:BOOL=FALSE -DWITH_MPI:BOOL=FALSE -DCMAKE_INSTALL_PREFIX=$HOME/pde/elmer/install ../src
   make -j$(nproc) install
   ```
2. Alternative: the PPA, `sudo add-apt-repository ppa:elmer-csc-ubuntu/elmer-csc-ppa && sudo apt-get install elmerfem-csc`. On 2026-09-24 Launchpad listed noble builds labelled 9.0 ([PPA packages](https://launchpad.net/~elmer-csc-ubuntu/+archive/ubuntu/elmer-csc-ppa/+packages)). How that label maps to release 26.x is **(unconfirmed)**, and an earlier issue said noble was missing ([#642](https://github.com/ElmerCSC/elmerfem/issues/642), now closed).
3. Check: `~/pde/elmer/install/bin/ElmerSolver` prints its banner, and `ctest -R CavityLid` in the build directory passes. That the tests are registered with `ctest` follows from the `runtest.cmake` files **(unconfirmed exact invocation)**.
4. Docker fallback: the same Dockerfile as on the Mac.

**Preparing the examples for EMA.**
- **Where the inputs go.** In the `.sif` deck, as keywords: `Material 1 / Density`, `Viscosity`, `Youngs Modulus`, `Poisson Ratio`, `Boundary Condition n / Velocity 1`, `Normal Force` or `Surface Traction`, and so on. The deck becomes the template.
- **Escaping `$` in templates.** Elmer's MATC expressions use `$` (for example `$ pi*...`), so any `$` in a deck must be written `$$`.
- **Meshes.** Some tests generate the mesh at test time with `ElmerGrid 1 2 square` from a `.grd` file. Do that once, and ship the resulting mesh directory as static files: `mesh.header`, `mesh.nodes`, `mesh.elements`, `mesh.boundary`. The version hash then covers the mesh.
- **Shrinking.** Use the `.grd` element counts and, for nonlinear or steady problems, `Steady State Max Iterations`.
- **Scalar output.** Append a `SaveScalars` solver:
  - `Equation = SaveScalars`, `Procedure = "SaveData" "SaveScalars"`, `Filename = scalars.dat`
  - `Variable 1 = Velocity 2`, `Operator 1 = max abs`, or `Save Points` / `Save Coordinates` for a point value
  - Parse `scalars.dat` with a regex. Its companion `scalars.dat.names` lists the columns.
- **Model type.** A command-line model: `ElmerSolver case.sif`, native on AWS and `docker run` on the Mac. Run serially, with a direct solver or tight linear tolerances.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `fem/tests/CavityLid/` (`case.sif`, `square.grd`) ([dir](https://github.com/ElmerCSC/elmerfem/tree/devel/fem/tests/CavityLid)) | steady lid-driven cavity Navier–Stokes, Re = 100 (density 1, viscosity 0.01, lid velocity 1), stabilized FEM | `Density` 1 [0.5, 2] (log); `Viscosity` 0.01 [0.005, 0.02] (log); lid `Velocity 1` 1 [0.5, 2] (log) → Re from 25 to 800 | max \|Velocity 2\| in the cavity (SaveScalars) | Dimensional output = U·f(Re), with Re = ρUL/μ. So there are 2 active directions in ln-space (ln U, ln ρ − ln μ): the density and viscosity exponents are equal and opposite. Smooth and monotone over the steady range. At the high-Re corner, check nonlinear convergence; failed runs are possible | est. 1–5 s | cli | regex on `scalars.dat` |
| `fem/tests/CooksMembrane/` (`cooksmembrane.sif`, `body/` mesh) ([dir](https://github.com/ElmerCSC/elmerfem/tree/devel/fem/tests/CooksMembrane)) | large-deformation neo-Hookean plane strain, mixed formulation, direct solver; reference UY = 6.1468 at (48, 60) | `Youngs Modulus` 200 [100, 400] (log); `Poisson Ratio` 0.35 [0.25, 0.45]; applied traction 4 [1, 8] (log) | UY at the corner (48, 60) (SaveScalars with a point, or `Save Points`) | Stress scales with E, so the output depends only on traction/E and ν: the traction and E exponents are equal and opposite, an exact ridge. The output is nonlinear (concave) in traction/E, so `power_law` is not expected. Newton may fail at the largest loads, which gives a failure region | est. 1–5 s | cli | regex on `scalars.dat` |

**Claude Code prompts.**

```text
Stage 1 — Elmer: check this machine (read-only).
Package: Elmer FEM release 26.2.1. On the Intel Mac: a locally built Docker image from the official docker/elmer.dockerfile, pinned to ubuntu:24.04 and tag release-26.2.1. On Ubuntu 24.04: a native source build (compilation_instructions/Ubuntu.md). Don't install anything; don't read .env.
Report: OS, `uname -m`, CPUs, RAM, free disk (about 5 GB); Docker; gfortran, cmake, and c++ versions; BLAS/LAPACK (Linux: dpkg -l | grep -E 'libblas|liblapack'); conda; Homebrew (don't use it; gfortran has no Intel bottles since 2026-09-03).
Recommend: the route above.
Stop and report; don't continue.
```

```text
Stage 2a — Elmer: install on the Intel Mac (Docker, locally built image).
Package: Elmer FEM release-26.2.1. Not EMA's .venv; don't read .env; no Homebrew.
1. Write ~/pde/elmer/elmer.Dockerfile. It is based on https://raw.githubusercontent.com/ElmerCSC/elmerfem/devel/docker/elmer.dockerfile, with these changes:
   - FROM ubuntu:24.04;
   - apt install build-essential cmake git gfortran libblas-dev liblapack-dev libmumps-dev libparmetis-dev;
   - git clone --branch release-26.2.1 --depth 1;
   - cmake -DWITH_MPI=FALSE -DWITH_ELMERGUI=FALSE -DCMAKE_INSTALL_PREFIX=/usr/local/elmer;
   - make -j4 install.
   Show me the file.
2. Ask before building: it downloads over 1 GB of packages. Build it as ema/elmer:26.2.1 and record `docker inspect --format '{{.Id}}'`.
3. Check: `docker run --rm ema/elmer:26.2.1 /usr/local/elmer/bin/ElmerSolver` prints the banner.
Stop at the first error with the log tail; don't continue.
```

```text
Stage 2b — Elmer: install on AWS EC2 Ubuntu 24.04 (on the instance).
Package: Elmer FEM release-26.2.1, a native serial build into ~/pde/elmer/install. Don't read .env.
1. Ask before running: sudo apt-get update && sudo apt-get install -y git cmake build-essential gfortran libopenmpi-dev libblas-dev liblapack-dev
2. Clone tag release-26.2.1 to ~/pde/elmer/src. In ~/pde/elmer/build, run cmake -DWITH_ELMERGUI:BOOL=FALSE -DWITH_MPI:BOOL=FALSE -DCMAKE_INSTALL_PREFIX=$HOME/pde/elmer/install ../src, then make -j$(nproc) install. Log to build.log and report the wall time.
If the build fails, stop and ask whether to try the PPA (ppa:elmer-csc-ubuntu/elmer-csc-ppa, elmerfem-csc; sudo) or the Docker recipe. Don't continue.
```

```text
Stage 3 — Elmer: smoke test with the CavityLid regression test.
Package: Elmer 26.2.1 (the Docker image ema/elmer:26.2.1 on the Mac, or ~/pde/elmer/install on AWS).
Copy fem/tests/CavityLid from the release-26.2.1 sources to ~/pde/elmer/smoke. Run `ElmerGrid 1 2 square`, then `ElmerSolver case.sif` (inside docker run with the directory mounted on the Mac).
Report the final lines (the solver norm, and whether it matches the test's reference norm in case.sif or CMakeLists), the mesh size, and the wall time.
Stop and report.
```

```text
Stage 4.1 — Elmer: prepare CavityLid as an EMA command-line model.
Start in plan mode first.
Package: Elmer 26.2.1 (Docker image ema/elmer:26.2.1 by ID on the Mac, native on AWS). Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/, and examples/modflow/.
1. Create examples/elmer/cavity/. Generate the mesh once with ElmerGrid 1 2 square, and list the square/ mesh files as static files.
2. Make case.sif a template. Placeholders: $rho (Density), $mu (Viscosity), $U (lid Velocity 1). Escape any $ as $$.
3. Append a SaveScalars solver writing scalars.dat with max abs of Velocity 2, and tighten the steady and nonlinear tolerances if needed, so outputs don't jitter.
4. Inputs, all log-scale: rho 1 [0.5, 2], mu 0.01 [0.005, 0.02], U 1 [0.5, 2].
5. Command: ElmerSolver case.sif (docker run on the Mac, checking the $EMA_WORKDIR mount as before; the binary's absolute path on AWS). Output: a regex on scalars.dat.
6. Check by hand: scaling rho and U by 2 and mu by 4 keeps Re fixed, so the output should scale by exactly 2. Report it, plus `ema profile -n 3` times.
Stop and report.
```

```text
Stage 4.2 — Elmer: prepare CooksMembrane as an EMA command-line model.
Start in plan mode first.
Package: Elmer 26.2.1, same route. Follow the same EMA docs and examples.
1. Create examples/elmer/cook/ with the body/ mesh files as static files, and cooksmembrane.sif as a template.
2. Placeholders: $E (Youngs Modulus), $nu (Poisson Ratio), $t (the applied traction, 4.0 in the test). Escape any $.
3. Add SaveScalars (or Save Points) writing the Y displacement at the node nearest (48, 60) to scalars.dat. First confirm the nominal run reproduces UY ≈ 6.1468.
4. Inputs: E 200 [100, 400] (log), nu 0.35 [0.25, 0.45], t 4 [1, 8] (log).
5. Check by hand that doubling E and t together leaves UY unchanged. Run `ema profile -n 3` at the nominal point and at t = 8, E = 100, the hardest corner, and report the convergence and times.
Stop and report.
```

```text
Stage 5 — Elmer: first campaigns.
Models: examples/elmer/cavity and examples/elmer/cook.
Propose, but don't run:
(a) cavity: linear_coeffs with log_output (about 30 runs), plus curve1d in mu with 21 points.
(b) cook: morris with 6 trajectories (24 runs), plus curve1d in t with 21 points.
Give the run counts and `ema estimate`, and ask before `ema run`.
Afterwards report:
- cavity: equal and opposite rho and mu exponents, and smoothness;
- cook: equal and opposite t and E effects, concavity in t, and any failed runs at high t/E.
Stop.
```

```text
Stage 6 — Elmer: troubleshooting.
Package: Elmer 26.2.1. For a failing model in examples/elmer/, check and report before changing anything:
(1) "Invalid placeholder": a MATC $ in the deck must be written $$.
(2) Mesh not found: the "Header / Mesh DB" path versus the static-file layout in the run directory.
(3) Missing scalars.dat: the SaveScalars solver has no Exec Solver = After All, or the Filename path is wrong.
(4) Nonlinear divergence at high Re or high load: raise Nonlinear System Max Iterations, add relaxation, or narrow the range. Failed runs are recorded, not fatal.
(5) Outputs that differ slightly between identical runs: iterative linear tolerances. Tighten them, or use Linear System Solver = Direct.
(6) On the Mac, slow runs: measure the docker run overhead and the Docker Desktop CPU count against -j.
Stop and report.
```

**Gotchas and sources.**
- License: the solver is GPL-2 and the libraries LGPL-2.1. Test decks copied into EMA should keep attribution.
- There is no maintained binary for Intel macOS and no published official Docker image, so the image is built locally from source (about 70 MB of source). Build it once and pin it by ID.
- The PPA's noble status and version labelling (9.0 versus 26.x) are ambiguous. Prefer the source build at a release tag on AWS.
- `$` in MATC expressions collides with EMA templates. Steady Navier–Stokes may stop converging near the top of the Re range.
- Sources: https://github.com/ElmerCSC/elmerfem ; https://api.github.com/repos/ElmerCSC/elmerfem/releases ; https://github.com/ElmerCSC/elmerfem/blob/devel/compilation_instructions/Ubuntu.md ; https://raw.githubusercontent.com/ElmerCSC/elmerfem/devel/docker/elmer.dockerfile ; https://github.com/ElmerCSC/elmerfem-docker ; https://github.com/ElmerCSC/elmerfem/wiki/Packages ; https://launchpad.net/~elmer-csc-ubuntu/+archive/ubuntu/elmer-csc-ppa/+packages ; https://github.com/ElmerCSC/elmerfem/issues/642 ; https://raw.githubusercontent.com/ElmerCSC/elmerfem/devel/fem/tests/CavityLid/case.sif ; https://raw.githubusercontent.com/ElmerCSC/elmerfem/devel/fem/tests/CooksMembrane/cooksmembrane.sif


### 4.3 CFD and hyperbolic solvers: OpenFOAM, SU2, PyClaw, Dedalus

Desk research only; nothing was installed or run. Checked 2026-09-24. Times per run are estimates to be measured with `ema profile`, not measurements.

Additions judged:
- **Dedalus: included.** A comparable package with a rich collection of examples. It adds spectral methods (the others are finite-volume codes), installs from conda-forge on osx-64, and has examples that run in seconds.
- **Nektar++: dropped for now.** Its session-XML `<PARAMETERS>` block would suit templates well, and it has Ubuntu 24.04 apt packages ([doc.nektar.info](https://doc.nektar.info/userguide/5.7.0/user-guidese1.html)). But its incompressible-flow examples overlap OpenFOAM's, and the only macOS route documented is a 2016 Homebrew tap ([nektar.info](https://www.nektar.info/installing-nektar-on-os-x-through-macports-or-homebrew/)), so the Intel Mac would need Docker anyway. It is the next candidate if FE/spectral-element CFD is wanted.
- **Basilisk: dropped.** Examples set their parameters as constants in C source, so every input change is a code change that has to be approved and compiled per run. Adaptive octree remeshing makes outputs nonsmooth in every input. There are no releases, only darcs head or a tarball ([basilisk.fr/src/INSTALL](http://basilisk.fr/src/INSTALL)).

A fact about EMA shapes all four recipes (from `src/ema/core/models/cli.py`): `input_files` destinations may contain subdirectories (`0/U`, `system/controlDict` are created with their parents), but `static_files` are copied **flat**, by basename, into the run directory. A case directory such as OpenFOAM's `0/ constant/ system/` therefore needs either every file as a template (a template without placeholders is allowed, but every `$` must be written `$$`), or a static archive (`case.tar`) that a driver script unpacks. A driver script named relative to `model.json` is passed to the command as an absolute *host* path. When the command is `docker run`, the driver must therefore be a static file, whose run-directory copy is left as a relative name that the container can see.

---

#### OpenFOAM

**What it is.** Finite-volume CFD (incompressible and compressible flow, turbulence, multiphase, heat transfer, combustion). GPL-3.0, C++. There are two independent lines that are **not** interchangeable:

- **openfoam.com (OpenCFD/ESI), "vYYMM"**: current **v2606**, released 2026-06-26 ([news](https://www.openfoam.com/news/main-news/openfoam-v2606), [current release](https://www.openfoam.com/current-release)). Its tutorials are in `$FOAM_TUTORIALS`, which is `tutorials/` in [gitlab.com/openfoam/core/openfoam](https://gitlab.com/openfoam/core/openfoam), arranged by solver: `tutorials/incompressible/icoFoam/cavity/cavity`, `tutorials/incompressible/simpleFoam/pitzDaily`, `tutorials/incompressible/simpleFoam/airFoil2D` (all three confirmed by raw file fetches). There are several hundred cases **(exact count unconfirmed)**.
- **openfoam.org (OpenFOAM Foundation), integer versions**: current **14**, released 2026-07-14; 13 was released 2025-07-08 ([v14 Ubuntu page](https://openfoam.org/download/14-ubuntu/), [GitHub OpenFOAM-14](https://github.com/OpenFOAM/OpenFOAM-14)). Solvers are modules run by `foamRun -solver <module>`. Tutorials are arranged by module: [tutorials/incompressibleFluid](https://github.com/OpenFOAM/OpenFOAM-14/tree/master/tutorials/incompressibleFluid) has 54 cases, including `cavity`, `pitzDaily`, `pitzDailySteady`, and `airFoil2D`. Viscosity is in `constant/physicalProperties` (`viscosityModel constant; nu 1e-05;`, confirmed for pitzDailySteady); the ESI line uses `constant/transportProperties`.

**Recommendation: use ESI v2606 for EMA.** It has an official apt repository, multi-arch Docker images, and the `#eval{...}` expression directive. `#eval` lets a template compute velocity components from an angle-of-attack input without compiling code; the Foundation equivalent, `#calc`, compiles C++ in every fresh run directory. The Foundation v14 paths are given as an alternative.

**Install on an Intel Mac.** Neither line runs natively on current Intel macOS. OpenFOAM.app (the Homebrew tap `gerlero/openfoam`) has **dropped Intel**: its last Intel release is 2.1.2, with up to v2506, for macOS 13 ([openfoam-app README](https://github.com/gerlero/openfoam-app)). The conda-forge `openfoam` package is ESI v2412 and is built for **linux_64 only** ([feedstock](https://github.com/conda-forge/openfoam-feedstock), [anaconda.org](https://anaconda.org/conda-forge/openfoam)). The Foundation's macOS route is a Multipass Ubuntu VM ([openfoam.org/download/macos](https://openfoam.org/download/macos/)). **The route is Docker Desktop**, which still ships Intel builds in 2026 ([docker.com](https://www.docker.com/products/docker-desktop/); Apple's Intel support ends after macOS 27, [Der Flounder](https://derflounder.wordpress.com/2026/09/15/intel-apps-and-macos-golden-gate/)).

1. Install Docker Desktop for Mac (Intel) and give it at least 4 CPUs and 8 GB of memory.
2. Pull an image with v2606. The official `opencfd/openfoam-default` has tags up to **2512** (amd64 and arm64; no 2606 tag as of this check, [Docker Hub tags](https://hub.docker.com/r/opencfd/openfoam-default/tags)). The community images `microfluidica/openfoam` have `2606` and `14` (amd64 and arm64), plus `-slim` tags without tutorials ([gerlero/docker-openfoam](https://github.com/gerlero/docker-openfoam)):
   ```bash
   docker pull microfluidica/openfoam:2606          # ESI v2606 with tutorials; or opencfd/openfoam-default:2512
   docker image inspect --format '{{index .RepoDigests 0}}' microfluidica/openfoam:2606   # record the digest to pin
   ```
3. Optional: OpenCFD's `openfoam-docker` wrapper script ([gitlab packaging/containers](https://gitlab.com/openfoam/packaging/containers/-/raw/main/openfoam-docker); usage `openfoam-docker -c './Allrun'`, per the [docker wiki](https://gitlab.com/openfoam/core/openfoam/-/wikis/precompiled/docker.md)). EMA should call `docker run` directly.
4. Check:
   ```bash
   docker run --rm microfluidica/openfoam:2606 bash -lc 'echo $WM_PROJECT_VERSION; simpleFoam -help | head -3'
   ```
Known problems: it is not documented whether the image's entrypoint sets up the OpenFOAM environment for non-interactive `docker run image cmd` **(unconfirmed)**, so drivers should source `etc/bashrc` explicitly. Docker Desktop's bind-mount I/O on macOS is slow, so keep `writeInterval` large. Each `docker run` adds roughly 0.5 to 1 s of start-up **(estimate)**.

**Install on AWS (Ubuntu 24.04 EC2).** Instance: c7i.xlarge (4 vCPU) for serial runs with `ema run -j 4`; c7i.4xlarge for `-j 16`.

1. ESI v2606 from the official apt repository ([debian wiki](https://gitlab.com/openfoam/core/openfoam/-/wikis/precompiled/debian.md); the package name `openfoam2606-default` follows the documented pattern `openfoam<ver>-default`):
   ```bash
   curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
   sudo apt-get update
   apt-cache policy openfoam2606-default       # confirm it exists for noble before installing
   sudo apt-get install -y openfoam2606-default
   openfoam2606 -c 'simpleFoam -help | head -3' # the wrapper starts the environment (the -c form is unconfirmed; plain 'openfoam2606' opens a shell)
   ```
   Whether v2606 is built for 24.04 as well as 26.04 is **(unconfirmed)**; the wiki says the repository targets "the newest Ubuntu LTS versions" with a transition period.
2. Alternative, Foundation v14 ([openfoam.org/download/14-ubuntu](https://openfoam.org/download/14-ubuntu/), which supports 22.04, 24.04, and 26.04):
   ```bash
   sudo sh -c "wget -O - https://dl.openfoam.org/gpg.key > /etc/apt/trusted.gpg.d/openfoam.asc"
   sudo add-apt-repository "http://dl.openfoam.org/ubuntu main dev"
   sudo apt update && sudo apt -y install openfoam14
   bash -c '. /opt/openfoam14/etc/bashrc && foamRun -help | head -3'
   ```
3. Docker fallback: install `docker.io`, then use the same image and digest as on the Mac. On Linux, pass `--user <uid>:<gid>` as literal numbers (EMA runs no shell, so `$(id -u)` isn't expanded); otherwise run directories fill with root-owned files.

**Preparing the examples for EMA.** An OpenFOAM case is a directory. Parameters live in dictionaries:
- viscosity in `constant/transportProperties` (ESI) or `constant/physicalProperties` (Foundation);
- inlet and freestream values in `0/U`, `0/k`, `0/epsilon`, and `0/nuTilda` (the ESI `airFoil2D` keeps them in `0.orig/`);
- mesh resolution in `system/blockMeshDict` (the cell counts in `blocks`);
- iterations and end time in `system/controlDict`;
- tolerances and `residualControl` in `system/fvSolution`.

Recipe:
- Copy the tutorial into `examples/openfoam/<case>/`. Turn every case file into a template (escape every OpenFOAM `$`, as in `$internalField`, `$FOAM_CASE`, and `#eval{ $x }`, as `$$`), or keep the fixed files in a static `case.tar`.
- Add a small static driver `run_case.sh` that sources the OpenFOAM `etc/bashrc`, runs `blockMesh` and the solver **serially**, and prints one line `EMA_OUTPUT <value>` read from a function object's `postProcessing/.../*.dat` file.
- Parse it with EMA's regex parser on stdout.
- For the scalar output, add function objects in `controlDict`: `surfaceFieldValue` (patch `areaAverage` of `p`), `volFieldValue`, `probes`, or `forceCoeffs`. Set `writePrecision 12` in the function object, because the case default of 6 digits quantizes the output.
- For speed, halve the `blocks` cell counts, set `writeInterval` to the end time, and remove the `streamlines` function.
- For smooth outputs in steady cases, replace `residualControl` stopping with a fixed iteration count. Stopping on residuals makes the iteration count, and hence the output, jump by small steps as inputs vary.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| ESI `tutorials/incompressible/icoFoam/cavity/cavity` (Foundation 14: `incompressibleFluid/cavity`) | transient laminar lid-driven cavity, L = 0.1 m, 20×20 cells | lid speed `U_lid` 1 m/s [0.5, 2] (log) in `0/U` (`movingWall` value); `nu` 0.01 m²/s [0.002, 0.02] (log) in `constant/transportProperties`. Raise `endTime` to 2 s (about 2 diffusion times at the lowest nu) with `deltaT` 0.002 (Courant ≤ 0.8 at U = 2) | Ux at the cavity centre divided by `U_lid` (a `probes` function object; the driver divides) | Depends only on Re = U_lid·L/nu once steady, so it has **one active direction** in (ln U_lid, ln nu) with weights about (+1, −1). Smooth and monotone in Re for Re 2.5 to 100 | 1–3 s native; +1 s in Docker **(estimate)** | cli | regex on stdout |
| ESI `tutorials/incompressible/simpleFoam/pitzDaily` (Foundation 14: `incompressibleFluid/pitzDailySteady`) | steady RANS (k-ε) backward-facing step | inlet speed `U_in` 10 m/s [5, 15] (log) in `0/U`; `nu` 1e-5 [5e-6, 2e-5] (log) in `transportProperties`/`physicalProperties`; inlet turbulence intensity `I` 0.05 [0.01, 0.1] via `0/k` (`turbulentIntensityKineticEnergyInlet`). Halve the `blocks` counts (about 3,000 cells), fixed 400 iterations | kinematic pressure drop, the `areaAverage` of p on `inlet` (the outlet is p = 0) | Close to a **power law** Δp ∝ U_in^≈2 (log-output `linear_coeffs`: exponent near 2 for U_in, small for nu). `I` is small or possibly negligible. Smooth if the iteration count is fixed; small **steps** if `residualControl` stops the run | 5–10 s coarse; about 30–60 s at the tutorial's 12,225 cells **(estimate)** | cli | regex on stdout |
| ESI `tutorials/incompressible/simpleFoam/airFoil2D` (Spalart–Allmaras; a mesh in `constant/polyMesh.orig`; `Allrun` defaults to `parallel=true`) | steady RANS 2-D airfoil | angle of attack `alpha` 8° [−4, 12] and freestream speed `U_inf` 26 m/s [15, 35], entering `0.orig/U` as `internalField uniform (#eval{ $U_inf*cos(degToRad($alpha)) } #eval{ $U_inf*sin(degToRad($alpha)) } 0)`, with EMA's placeholders substituted before OpenFOAM reads the file (a template must write `$$internalField` for OpenFOAM's own references; `#eval` inside a vector entry is **unconfirmed**) | lift coefficient Cl from `forceCoeffs`, with `liftDir`/`dragDir` rotated by `alpha` via `#eval` (a second model.json for Cd) | Cl **nearly linear** in alpha (slope ≈ 0.1/deg) with curvature toward the top of the range. `U_inf` is close to negligible for Cl (a weak Reynolds effect). Cd is **non-monotone** in alpha (a minimum near 0°) | 15–40 s serial, 500 iterations; cutting to 250 halves it **(estimate; over the 10 s target)** | cli | regex on stdout |

The mesh for `airFoil2D` is several files in `constant/polyMesh.orig`, so ship it as a static `polyMesh.tar` that the driver unpacks into `constant/polyMesh`. The `forceCoeffs` output file name (`coefficient.dat` in recent ESI versions, `forceCoeffs.dat` in older ones) is **(unconfirmed for v2606)**, so the driver should locate the file itself.

**Claude Code prompts.**

```text
Stage 1 (OpenFOAM, read-only machine check). In the EMA repo, check this machine without changing anything: OS and version (sw_vers or /etc/os-release), CPU architecture (uname -m), free disk space (df -h .), whether Docker is installed and running (docker version, docker info | head), Homebrew (brew --version), conda/mamba, compilers (cc --version), MPI (mpirun --version), and whether any OpenFOAM is already installed (which simpleFoam foamRun openfoam2606; ls /usr/lib/openfoam /opt/openfoam* 2>/dev/null). Do not read .env. Then recommend a route from these rules: on an Intel Mac, Docker Desktop with the image microfluidica/openfoam:2606 (ESI v2606), because OpenFOAM.app dropped Intel and conda-forge's openfoam is linux-64 only; on Ubuntu 24.04 x86_64, the ESI apt package openfoam2606-default, with the Docker image as fallback. Stop and report the findings and the recommended route; don't install anything or continue to the next stage.
```

```text
Stage 2a (OpenFOAM on the Intel Mac, Docker route). Install nothing with Homebrew and use no sudo; do not touch EMA's .venv or read .env. Docker Desktop must already be running (if it isn't, stop and tell me). Tell me the image size before pulling it, and ask me first if it is over 1 GB. Then: docker pull microfluidica/openfoam:2606; record the pinned reference with docker image inspect --format '{{index .RepoDigests 0}}' microfluidica/openfoam:2606 and write it into examples/openfoam/IMAGE.txt with the date. Check that the OpenFOAM environment works non-interactively: docker run --rm <image@digest> bash -lc 'echo $WM_PROJECT_DIR $WM_PROJECT_VERSION; which simpleFoam icoFoam blockMesh'. If the variables are empty, find the bashrc inside the image (ls /usr/lib/openfoam /openfoam* 2>/dev/null) and report its path. Stop at the first error and report it verbatim; don't improvise workarounds. Stop and report the digest, the bashrc path, and the version string; don't continue to the next stage.
```

```text
Stage 2b (OpenFOAM on AWS Ubuntu 24.04 x86_64, native ESI v2606). I have launched and ssh'd into the instance, and this Claude Code runs there in a clone of the EMA repo. Don't touch EMA's .venv or read .env. Ask me before every sudo command. Steps: curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash; sudo apt-get update; apt-cache policy openfoam2606-default (if there is no candidate for noble, stop and report; the fallback is Docker with microfluidica/openfoam:2606 pinned by digest, or the Foundation's openfoam14 from dl.openfoam.org, but ask me which). Tell me the download size apt reports and ask if it is over 1 GB, then sudo apt-get install -y openfoam2606-default. Check: openfoam2606 -c 'echo $WM_PROJECT_DIR; simpleFoam -help | head -3' (if -c is not supported, find the bashrc under /usr/lib/openfoam/openfoam2606/etc/ and use bash -c '. <bashrc> && simpleFoam -help'). Stop at the first error and report it verbatim. Stop and report the installed version and the bashrc path; don't continue to the next stage.
```

```text
Stage 3 (OpenFOAM smoke test, ESI v2606; route: Docker on the Intel Mac or native on Ubuntu, as installed in stage 2). In a scratch directory outside the repo, copy the tutorial $FOAM_TUTORIALS/incompressible/icoFoam/cavity/cavity (inside the container on the Mac: docker run --rm -v <scratch>:/work -w /work <image@digest> bash -lc '. <bashrc> && cp -r $FOAM_TUTORIALS/incompressible/icoFoam/cavity/cavity . && cd cavity && blockMesh && icoFoam'). Time the whole command with /usr/bin/time (and separately a docker run that only runs 'true', to measure container start-up). Report: the last "Time =" line, the final Courant number, the wall time, and the start-up overhead. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (OpenFOAM: prepare the lid-driven cavity for EMA). Use plan mode first and show me the plan before writing files. Package: OpenFOAM ESI v2606, route as installed (Docker image pinned by digest on the Intel Mac; the openfoam2606 apt package on Ubuntu). Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/ and examples/modflow/ first. Create examples/openfoam/cavity/ from tutorials/incompressible/icoFoam/cavity/cavity:
- Every case file becomes a template at its subdirectory path in input_files (0/U, 0/p, constant/transportProperties, system/controlDict, system/blockMeshDict, system/fvSchemes, system/fvSolution). Escape every OpenFOAM $ as $$.
- Inputs: U_lid (nominal 1, range [0.5, 2] m/s, scale log) in 0/U's movingWall value, and nu (nominal 0.01, [0.002, 0.02] m^2/s, scale log) in transportProperties.
- Set endTime 2, deltaT 0.002, and writeInterval equal to endTime.
- Add a probes function object at (0.05 0.05 0.005) for U, with writePrecision 12.
- A static driver run_case.sh sources the OpenFOAM bashrc, runs blockMesh and icoFoam serially, reads the last probe value of Ux, and prints "EMA_OUTPUT <Ux/U_lid>" (awk is fine; the driver must not need Python inside the container).
- The command is either ["docker","run","--rm","-v","$EMA_WORKDIR:/work","-w","/work","<image@digest>","bash","run_case.sh"] (Mac) or ["bash","run_case.sh"] with the native bashrc (Ubuntu). Because the driver is a static file, it stays relative inside the container.
- The output is a regex parser on stdout for EMA_OUTPUT. Set timeout_s to 120.
Then run `ema profile examples/openfoam/cavity/model.json -n 3` and report the time per run, the phase breakdown, and the output at the nominal point. Stop and report; don't start a campaign.
```

```text
Stage 4.2 (OpenFOAM: prepare pitzDaily for EMA). Use plan mode first. Package: OpenFOAM ESI v2606 (route as installed). Follow docs/guides/input_deck_model.md and the pattern of examples/openfoam/cavity/. Create examples/openfoam/pitzdaily/ from tutorials/incompressible/simpleFoam/pitzDaily:
- Inputs: U_in (10, [5, 15] m/s, log) in 0/U's inlet value; nu (1e-5, [5e-6, 2e-5] m^2/s, log) in constant/transportProperties; I (0.05, [0.01, 0.1]) as the intensity of a turbulentIntensityKineticEnergyInlet on 0/k.
- Halve every block's cell counts in blockMeshDict. Remove residualControl from fvSolution and use a fixed endTime of 400 iterations. Remove the streamlines function.
- Add a surfaceFieldValue function object computing the areaAverage of p on patch inlet, with writePrecision 12. The driver prints "EMA_OUTPUT <value>" from the last line of its .dat file.
- Check convergence at the four corners of the input box: report the final initial residuals of p and U, and whether 400 iterations suffice. If they don't, raise the count and say so.
Then run `ema profile examples/openfoam/pitzdaily/model.json -n 3` and report the time per run. If it exceeds 15 s, stop and propose coarser options rather than proceeding. Stop and report; don't start a campaign.
```

```text
Stage 4.3 (OpenFOAM: prepare airFoil2D for EMA; ESI v2606 only, because it uses #eval). Use plan mode first. Create examples/openfoam/airfoil2d/ from tutorials/incompressible/simpleFoam/airFoil2D, following docs/guides/input_deck_model.md and examples/openfoam/cavity/:
- Ship the mesh constant/polyMesh.orig as a static polyMesh.tar that the static driver unpacks into constant/polyMesh. Run serially (no decomposePar).
- Inputs: alpha (8, [-4, 12] degrees) and U_inf (26, [15, 35] m/s). In the 0/U template, write internalField as uniform (#eval{ $U_inf*cos(degToRad($alpha)) } #eval{ $U_inf*sin(degToRad($alpha)) } 0), with OpenFOAM's own $internalField references escaped as $$internalField. First verify in the container that #eval works inside a vector entry (render one case and run foamDictionary 0/U -entry internalField); if it doesn't, stop and report.
- Add a forceCoeffs function object on patch walls with magUInf $U_inf, lRef 1, Aref 1, and liftDir and dragDir rotated by alpha via #eval. The driver finds the coefficient file under postProcessing/ (its name varies by version) and prints "EMA_OUTPUT <Cl>" from the last row.
- Make a second model_cd.json for Cd, sharing the templates.
- Cut the iterations to 250 if Cl changes by less than 1e-4 over the last 50.
Then `ema profile` both model files and report the times per run and Cl and Cd at the nominal point. Stop and report; don't start a campaign.
```

```text
Stage 5 (OpenFOAM first campaign). Using examples/openfoam/cavity/model.json (ESI v2606, route as installed), write examples/openfoam/cavity/campaign.json with a small budget: morris with 6 trajectories (6 x 3 = 18 runs) and curve1d on nu with 9 points, so about 27 runs. Run `ema estimate` on it and show me the run count and the estimated time, then ask me before running. After I approve, run `ema run examples/openfoam/cavity/campaign.json --yes -j 4` and report whether both inputs matter, whether the effects are monotone, and whether the result is consistent with dependence on Re = U_lid*L/nu only (the Morris mu* of ln U_lid and ln nu similar in size and opposite in sign). Stop and report; don't run further diagnostics.
```

```text
Stage 6 (OpenFOAM troubleshooting). An EMA run of an OpenFOAM model in examples/openfoam/ failed or gave odd values (ESI v2606, Docker on the Intel Mac or native on Ubuntu 24.04). Diagnose without changing the model first. Read the run directory's ema_run.json, stderr.txt and stdout, and log files. Check these in order:
(1) a template error from an unescaped $ (EMA says "invalid $ syntax"; escape it as $$);
(2) the OpenFOAM environment missing inside docker run (empty WM_PROJECT_DIR: source the bashrc in the driver);
(3) "cannot find file" for a case file that was listed as a static file (static files are copied flat; case files must be input_files templates or come from a tarball);
(4) a Courant number above 1 or divergence at the edge of the input box (reduce deltaT or narrow the range);
(5) outputs that step between nearby inputs (residualControl stopping or writePrecision 6: use fixed iterations and writePrecision 12);
(6) root-owned files on Linux (add --user uid:gid);
(7) a timeout (raise timeout_s or coarsen the mesh);
(8) the forceCoeffs or probes file not found (the name differs between versions).
Report the cause with evidence and a proposed fix. Stop and ask before editing anything.
```

**Gotchas and sources.**
- ESI and Foundation cases are **not interchangeable**: they differ in solver names (`simpleFoam` vs `foamRun -solver incompressibleFluid`), viscosity files, and the tutorial tree. Pin one line per model.json and say which in its description.
- The Intel Mac has no native route: OpenFOAM.app dropped Intel after v2506, and conda-forge is linux-64 only. Docker on the Intel Mac is still available but depends on Apple's Intel support after macOS 27.
- Every `$` in an OpenFOAM dictionary (`$internalField`, `#include "$FOAM_CASE/..."`, comments) must be `$$` in an EMA template.
- Run each case serially. `decomposePar` with parallel reductions changes the last digits, and EMA's `-j` gives parallelism across runs instead.
- Stopping on `residualControl` and 6-digit `writePrecision` both put small steps into outputs. EMA's `nonsmooth` and `finite_diff` would flag them as features of the model.
- Changing the mesh (block counts) with an input would make outputs nonsmooth; keep geometry fixed.
- The official `opencfd/*` images have no 2606 tag yet (latest 2512); `microfluidica/openfoam` is a community image (pin by digest).
- Licence: GPL-3.0. Running it as an external program is fine.
- Sources: https://www.openfoam.com/news/main-news/openfoam-v2606 · https://www.openfoam.com/current-release · https://gitlab.com/openfoam/core/openfoam/-/wikis/precompiled/debian.md · https://gitlab.com/openfoam/core/openfoam/-/wikis/precompiled/docker.md · https://hub.docker.com/r/opencfd/openfoam-default/tags · https://github.com/gerlero/docker-openfoam · https://github.com/gerlero/openfoam-app · https://github.com/conda-forge/openfoam-feedstock · https://openfoam.org/download/14-ubuntu/ · https://openfoam.org/download/macos/ · https://github.com/OpenFOAM/OpenFOAM-14/tree/master/tutorials/incompressibleFluid · https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/pitzDaily/system/controlDict · https://gitlab.com/openfoam/core/openfoam/-/raw/master/tutorials/incompressible/simpleFoam/airFoil2D/Allrun

---

#### SU2

**What it is.** A finite-volume (and FEM) suite for compressible and incompressible CFD, adjoint shape design, heat transfer, and FSI. LGPL-2.1, C++ with Python scripts ([download page](https://su2code.github.io/docs_v7/Download/)). Current **v8.5.0 "Harrier"**, published 2026-04-27 ([GitHub releases API](https://api.github.com/repos/su2code/SU2/releases/latest)). The tutorials are in [github.com/su2code/Tutorials](https://github.com/su2code/Tutorials) and are described at [su2code.github.io/tutorials/home](https://su2code.github.io/tutorials/home/). There are about 46, in categories: about 14 compressible, about 11 incompressible, 4 structural, 8 multiphysics, 7 design, and 2 others. Each tutorial is one `.cfg` (flat `KEY= value` lines, `%` comments, no `$`) plus a `.su2` mesh file.

**Install on an Intel Mac.** Two routes, both native:

1. **conda-forge (recommended):** `su2` 8.5.0 is listed for linux-64, **osx-64**, and osx-arm64 ([anaconda.org/conda-forge/su2](https://anaconda.org/conda-forge/su2)). Whether the 8.5.0 build itself exists for osx-64 is **(unconfirmed)**, so check with `conda search`:
   ```bash
   # miniforge assumed (https://conda-forge.org/download/)
   conda search -c conda-forge "su2=8.5.0"          # confirm an osx-64 build
   conda create -n ema-su2 -c conda-forge su2=8.5.0
   conda run -n ema-su2 SU2_CFD --help | head -5    # check
   ```
2. **Official binaries:** the release assets include `SU2-v8.5.0-macos64.zip` and `SU2-v8.5.0-macos64-mpi.zip`. Whether "macos64" is x86_64 or arm64 is **(unconfirmed)**, so check with `file bin/SU2_CFD`. Setup per the [Linux/macOS page](https://su2code.github.io/docs_v7/SU2-Linux-MacOS/): unzip, then `export SU2_RUN=<dir>/bin; export PATH=$SU2_RUN:$PATH; export PYTHONPATH=$SU2_RUN:$PYTHONPATH`. The MPI build needs MPICH. Gatekeeper may quarantine downloaded binaries (`xattr -d com.apple.quarantine`) **(unconfirmed)**.

Check: `SU2_CFD inv_NACA0012.cfg` in the QuickStart folder. Known problems: the download page itself says "for best performance and compatibility you should always consider building SU2 from source" ([download.html](https://su2code.github.io/download.html)).

**Install on AWS (Ubuntu 24.04 EC2).** Instance: c7i.xlarge (serial runs, `-j 4`).

1. conda-forge, as on the Mac: `conda create -n ema-su2 -c conda-forge su2=8.5.0`.
2. Or the release binary `SU2-v8.5.0-linux64.zip` (or `-linux64-omp`/`-linux64-mpi`) from [releases](https://github.com/su2code/SU2/releases), with the `SU2_RUN`/`PATH` exports above.
3. There is no apt package from the project **(none found)**.
4. Docker fallback: SU2 publishes **only build and test containers** (`ghcr.io/su2code/su2/build-su2`), which contain no binaries ([Container-Development](https://su2code.github.io/docs_v7/Container-Development/), [Docker-Builds](https://github.com/su2code/Docker-Builds)). Instead, use `condaforge/miniforge3` pinned by digest and `mamba install su2=8.5.0` in a derived image.

Check: `SU2_CFD --help` and the QuickStart case.

**Preparing the examples for EMA.** Everything is in the `.cfg`:
- flow conditions: `MACH_NUMBER`, `AOA`, `FREESTREAM_PRESSURE`, `FREESTREAM_TEMPERATURE`, `REYNOLDS_NUMBER`; for incompressible cases `INC_VELOCITY_INIT`, `INC_DENSITY_INIT`, `MU_CONSTANT`, `MARKER_ISOTHERMAL`;
- boundary markers;
- iteration control: `ITER`, `CONV_FIELD`, `CONV_RESIDUAL_MINVAL`, `CFL_NUMBER`, `MGLEVEL`;
- output: `HISTORY_OUTPUT`, `OUTPUT_FILES`, `TABULAR_FORMAT`, `CONV_FILENAME`.

Recipe:
- Make the `.cfg` a template (a flat file, no escaping needed unless it contains `$`), and ship the `.su2` mesh as a static file (flat is fine).
- The command is the env's absolute `SU2_CFD` path plus the `.cfg` name, run serially with `OMP_NUM_THREADS=1` in `env`.
- The output is the last row of `history.csv`. Its header entries are quoted and padded (`"       CD       "`) **(unconfirmed exact format)**, so an isolated Python parser that strips quotes and spaces is safer than EMA's `csv` parser matching a column name.
- For speed, set `OUTPUT_FILES= (RESTART)` or the minimum (the VTU and surface files cost I/O), keep multigrid, and use a looser `CONV_RESIDUAL_MINVAL` (for example −8).
- For smooth outputs, prefer a fixed `ITER` with a tolerance that isn't reached, or a very tight one. Stopping on the residual changes the iteration count between neighbouring inputs.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| QuickStart NACA 0012: `Tutorials/compressible_flow/QuickStart` (also `SU2/QuickStart`), `inv_NACA0012.cfg` + `mesh_NACA0012_inv.su2` (10,216 triangles) ([Quick Start](https://su2code.github.io/docs_v7/Quick-Start/)) | 2-D inviscid transonic Euler | `MACH` 0.8 [0.5, 0.85]; `AOA` 1.25° [−2, 4] | CD (model 1); CL (model 2) from `history.csv` | **Kink/steep rise in CD** at drag divergence (shock onset near M ≈ 0.7): `curve1d`/`nonsmooth` in Mach. CL nearly linear and odd in AOA at low Mach (a symmetric airfoil, so CL(0) = 0); strong **Mach×AOA interaction** transonically | 5–15 s serial to residual −8 **(estimate)** | cli | python (history.csv last row) |
| Incompressible laminar flat plate with heat transfer: [Inc_Laminar_Flat_Plate](https://su2code.github.io/tutorials/Inc_Laminar_Flat_Plate/), `lam_flatplate.cfg` + `mesh_flatplate_65x65.su2` (Tutorials path `incompressible_flow/Inc_Laminar_Flat_Plate` **(unconfirmed)**) | laminar boundary layer, `INC_NAVIER_STOKES` with energy | inlet speed 69.17 m/s [30, 100] (log) in `INC_VELOCITY_INIT`; viscosity 1.835e-5 Pa·s [1e-5, 4e-5] (log) in `MU_CONSTANT`; wall temperature 148.8 K [120, 280] in `MARKER_ISOTHERMAL` | drag coefficient CD (model 1); total wall heat flux `TOTAL_HEATFLUX` (model 2) | CD follows Blasius, **a power law in Re**: log-output `linear_coeffs` finds exponents ≈ −0.5 on speed, +0.5 on viscosity, with wall T negligible for CD if property variation is off. Heat flux is **linear in (T_wall − T_inlet)** and a power law in speed | 10–20 s serial **(estimate)** | cli | python |
| Inviscid bump in a channel: [Inviscid_Bump](https://su2code.github.io/tutorials/Inviscid_Bump/), `inv_channel.cfg` + `mesh_channel_256x128.su2` | internal subsonic/transonic Euler | outlet static pressure 101300 Pa [80000, 101000] (`MARKER_OUTLET`); inlet total temperature 288.6 K [250, 330] (`MARKER_INLET`); total pressure fixed at 102010 Pa | mass-averaged total-pressure ratio at the outlet (a `MARKER_ANALYZE` surface output; field name **unconfirmed**) | Near-constant loss while subsonic, then a **kink** where a shock forms on the bump as back pressure drops. **Inlet total temperature should be exactly negligible** for a pressure ratio (a false-positive check) | 30–90 s at 32,768 cells **(estimate; over target)**; use fewer `ITER` and `MGLEVEL= 3` | cli | python |

**Claude Code prompts.**

```text
Stage 1 (SU2, read-only machine check). In the EMA repo, without changing anything, report: OS and version, CPU architecture (uname -m), free disk space, conda/mamba/miniforge (which conda mamba; conda info | head -20), Homebrew, Docker, compilers, MPI (mpirun --version), and whether SU2 is already installed (which SU2_CFD). Do not read .env. Recommend a route: a conda env named ema-su2 with conda-forge su2=8.5.0 on both the Intel Mac and Ubuntu 24.04, with the official v8.5.0 release zip as fallback (on the Mac, check that it is x86_64). Stop and report; don't install anything or continue to the next stage.
```

```text
Stage 2a (SU2 on the Intel Mac). Create a conda env; never use EMA's .venv, never read .env, and use no sudo or Homebrew. Run: conda search -c conda-forge "su2=8.5.0" and confirm there is an osx-64 build (if not, stop and report the newest osx-64 version available). Then conda create -y -n ema-su2 -c conda-forge su2=8.5.0, and ask me first if the download is over 1 GB. Check: conda run -n ema-su2 which SU2_CFD; file on that binary (must be x86_64); conda run -n ema-su2 SU2_CFD --help | head. Record the absolute SU2_CFD path in examples/su2/SU2_PATH.txt. Stop at the first error and report it verbatim. Stop and report the path and version; don't continue to the next stage.
```

```text
Stage 2b (SU2 on AWS Ubuntu 24.04 x86_64). I launched the instance and ssh'd in, and this Claude Code runs there in a clone of the EMA repo. Never use EMA's .venv or read .env; ask before any sudo. If conda is missing, ask me before installing miniforge in $HOME (no sudo). Then conda create -y -n ema-su2 -c conda-forge su2=8.5.0 (ask if the download is over 1 GB). Check: conda run -n ema-su2 SU2_CFD --help | head. Fallback if conda fails: the release asset SU2-v8.5.0-linux64.zip from https://github.com/su2code/SU2/releases, unzipped under $HOME/opt/su2-8.5.0; but ask me before switching. Record the absolute SU2_CFD path in examples/su2/SU2_PATH.txt. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 (SU2 smoke test, v8.5.0, conda env ema-su2). In a scratch directory outside the repo, download (git clone --depth 1 https://github.com/su2code/Tutorials, or fetch just the two files) the QuickStart case: inv_NACA0012.cfg and mesh_NACA0012_inv.su2. Run it serially with OMP_NUM_THREADS=1 and the env's SU2_CFD, timed with /usr/bin/time. Report: the iteration count, the final density residual, the final CL and CD from history.csv, the wall time, and the first 3 lines of history.csv verbatim (so we see the header format). Stop and report; don't continue.
```

```text
Stage 4.1 (SU2: prepare QuickStart NACA 0012 for EMA). Use plan mode first. Package: SU2 8.5.0 in conda env ema-su2 (absolute SU2_CFD path from examples/su2/SU2_PATH.txt). Read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/ and examples/modflow/. Create examples/su2/naca0012/:
- inv_NACA0012.cfg becomes a template with $mach (nominal 0.8, [0.5, 0.85]) in MACH_NUMBER and $aoa (1.25, [-2, 4] degrees) in AOA. The mesh is a static file.
- Minimal output files, TABULAR_FORMAT= CSV, HISTORY_OUTPUT including AERO_COEFF, and a fixed iteration budget chosen so the density residual reaches about -10 at the hardest corner (Mach 0.85, AOA 4). Measure it and tell me.
- The command is [<absolute SU2_CFD>, "inv_NACA0012.cfg"], with env OMP_NUM_THREADS=1.
- An isolated Python output parser parse_history.py reads the last row of history.csv, stripping quotes and spaces from header names. Make two model files: model_cd.json (CD) and model_cl.json (CL).
Run `ema profile` on each (-n 3) and report the time per run and CL and CD at the nominal point. Stop and report; don't start a campaign.
```

```text
Stage 4.2 (SU2: prepare the incompressible laminar flat plate with heat transfer). Use plan mode first. Package: SU2 8.5.0 (conda env ema-su2). Create examples/su2/flatplate/ from the Tutorials repo's Inc_Laminar_Flat_Plate case (lam_flatplate.cfg, mesh_flatplate_65x65.su2):
- Inputs: u_in (69.17, [30, 100] m/s, scale log) as the x-component of INC_VELOCITY_INIT (and the inlet marker, if it sets the speed separately); mu (1.835e-5, [1e-5, 4e-5] Pa s, log) in MU_CONSTANT; t_wall (148.8, [120, 280] K) in MARKER_ISOTHERMAL.
- Outputs: model_cd.json (drag coefficient) and model_q.json (total wall heat flux), read from history.csv by the same isolated Python parser as examples/su2/naca0012/.
- Use a fixed iteration count that converges at the lowest viscosity and highest speed. Check it and report.
Then `ema profile` each and report the times per run. If a run exceeds 20 s, propose options (a looser tolerance, CFL) before continuing. Stop and report; don't start a campaign.
```

```text
Stage 4.3 (SU2: prepare the inviscid bump). Use plan mode first. Package: SU2 8.5.0 (conda env ema-su2). Create examples/su2/bump/ from Inviscid_Bump (inv_channel.cfg, mesh_channel_256x128.su2):
- Inputs: p_out (101300, [80000, 101000] Pa) in MARKER_OUTLET; t0_in (288.6, [250, 330] K) in MARKER_INLET, with the total pressure fixed at 102010.
- Output: add MARKER_ANALYZE on the outlet and put the surface total-pressure field in HISTORY_OUTPUT. Check the exact field names in SU2_CFD's history output for 8.5.0 and report them. The output is outlet mass-averaged total pressure / 102010.
- Measure the run time at the nominal point first. If it exceeds 60 s, stop and report options (fewer ITER, a looser tolerance), because this case is over the 10 s target.
Then `ema profile` and report. Stop and report; don't start a campaign.
```

```text
Stage 5 (SU2 first campaign). Using examples/su2/naca0012/model_cd.json (SU2 8.5.0, conda env ema-su2), write a campaign with curve1d on mach (15 points at nominal AOA) and morris with 5 trajectories (15 runs): about 30 runs. Run `ema estimate` and show me the run count and the time, then ask before running. After I approve, run it with `ema run ... --yes -j 4` and report: whether curve1d finds a kink or steep rise in CD with Mach (and where), whether morris ranks Mach above AOA for CD, and any failed runs. Stop and report; don't run further diagnostics.
```

```text
Stage 6 (SU2 troubleshooting). An EMA run of an SU2 8.5.0 model in examples/su2/ failed or gave odd values. Diagnose before changing anything. Read the run directory's ema_run.json, stdout, and history.csv. Check in order:
(1) SU2_CFD not found (the command must use the env's absolute path; conda activation doesn't happen under EMA);
(2) a config error ("option not recognized": an option renamed between SU2 7 and 8);
(3) divergence (NaN residuals) at the corners of the input box (lower CFL_NUMBER or narrow the range);
(4) the parser failing on history.csv's quoted and padded header;
(5) outputs that step between nearby inputs (the residual stopping rule: use fixed ITER);
(6) the mesh file missing (static files are copied flat; MESH_FILENAME must be the bare name);
(7) slow runs from writing VTU/surface files every iteration (OUTPUT_WRT_FREQ, OUTPUT_FILES);
(8) OMP/MPI thread oversubscription with ema -j (set OMP_NUM_THREADS=1).
Report the cause with evidence and the proposed fix. Ask before editing.
```

**Gotchas and sources.**
- Licence: LGPL-2.1, fine as an external program.
- The official Docker images are build and test environments only, with no runtime image.
- The architecture of the `macos64` zip is unconfirmed; prefer conda-forge osx-64.
- MPI partitioning and OpenMP builds can change the last digits. Run serially with `OMP_NUM_THREADS=1`.
- Option names change between major versions (v7 → v8), so tutorials in the Tutorials repo track `develop` and may run ahead of 8.5.0. Pin the Tutorials commit and check that the cfg parses.
- Stopping on convergence produces step-like noise, and transonic cases can limit-cycle (the residual stalls), which gives non-repeatable-looking outputs near shock onset. Run `repeat` at one transonic point to confirm determinism.
- Sources: https://api.github.com/repos/su2code/SU2/releases/latest · https://github.com/su2code/SU2/releases · https://anaconda.org/conda-forge/su2 · https://su2code.github.io/download.html · https://su2code.github.io/docs_v7/SU2-Linux-MacOS/ · https://su2code.github.io/docs_v7/Quick-Start/ · https://su2code.github.io/tutorials/home/ · https://su2code.github.io/tutorials/Inviscid_Bump/ · https://su2code.github.io/tutorials/Inc_Laminar_Flat_Plate/ · https://su2code.github.io/docs_v7/Container-Development/ · https://github.com/su2code/Docker-Builds

---

#### PyClaw (Clawpack)

**What it is.** Finite-volume wave-propagation methods for hyperbolic conservation laws (Clawpack), with PyClaw as its Python front end, which calls Fortran Riemann solvers. BSD-3, Python + Fortran. Current Clawpack **v5.14.0**, released 2026-01-27; 5.13.1 was released 2025-09-12 ([GitHub releases](https://api.github.com/repos/clawpack/clawpack/releases?per_page=3)). The examples are in [pyclaw/examples](https://github.com/clawpack/pyclaw/tree/master/examples): 26 directories, including `acoustics_1d_homogeneous`, `advection_1d`, `burgers_1d`, `euler_1d` (Sod shock tube), `shallow_1d` (dam break), `traffic`, `euler_2d`, and `shallow_sphere`. They are importable as `clawpack.pyclaw.examples` ([docs](https://www.clawpack.org/pyclaw/examples.html)). Each example is a Python `setup(...)` whose physical parameters are local variables, not arguments: `shocktube.py` has `setup(use_petsc=False, outdir='./_output', solver_type='classic', kernel_language='Python', disable_output=False)` with `gamma=1.4`, `rho_l=1, p_l=1, rho_r=0.125, p_r=0.1`, 800 cells, and `tfinal=0.4`.

**GeoClaw and AMRClaw:** these are Fortran codes run by `make .output` with `setrun.py` writing `.data` files and the `CLAW` and `FC` environment variables set. They fit EMA as command-line models (`setrun.py` parameters become a template), but adaptive mesh refinement makes outputs nonsmooth in most inputs, and GeoClaw tsunami examples download topography and take minutes. They are not recommended for the first pass.

**Install on an Intel Mac.** PyPI `clawpack` 5.14.0 ships a wheel only for cp313 macOS **arm64**, plus an sdist ([pypi JSON](https://pypi.org/pypi/clawpack/json)). On Intel it builds from source with meson-python and gfortran (`pyproject.toml` requires `meson-python` and `numpy`; its classifiers list Python up to 3.12; [pyproject](https://raw.githubusercontent.com/clawpack/clawpack/v5.14.0/pyproject.toml), [prereqs](https://www.clawpack.org/prereqs.html)). conda-forge has `clawpack` **5.9.0** for linux-64, osx-64, and osx-arm64 ([anaconda.org](https://anaconda.org/conda-forge/clawpack)).

1. Route A (current version, built in a conda env; the compiler comes from conda-forge, not Homebrew):
   ```bash
   conda create -n ema-clawpack -c conda-forge python=3.12 numpy scipy matplotlib meson meson-python ninja gfortran pip
   conda run -n ema-clawpack pip install --no-build-isolation clawpack==5.14.0
   ```
   (`pip install clawpack` is the documented PyClaw-only command, [installing_pip](https://www.clawpack.org/installing_pip.html); `--no-build-isolation` so the env's gfortran and numpy are used. The build on osx-64 is **unconfirmed**.)
2. Route B (binary, older): `conda create -n ema-clawpack -c conda-forge clawpack=5.9.0 python=3.11`. Whether the py3.11 build exists is **(unconfirmed)**; check with `conda search`.
3. Check:
   ```bash
   conda run -n ema-clawpack python -c "import clawpack, clawpack.pyclaw, clawpack.riemann; print(clawpack.__version__)"
   conda run -n ema-clawpack python -c "from clawpack.riemann import euler_with_efix_1D; print('Fortran Riemann solvers ok')"
   ```
   Find the example directory with `python -c "import clawpack.pyclaw.examples as e, os; print(os.path.dirname(e.__file__))"`. Whether the examples ship in the installed package is **(unconfirmed)**; if not, `git clone --branch v5.14.0 https://github.com/clawpack/pyclaw`.
Known problems: f2py/meson builds fail without a matching Fortran compiler. The Docker image `clawpack/v5.9.0_dockerimage:release` is 5.9.0 and Jupyter-oriented, with its architecture undocumented ([docker_image](https://www.clawpack.org/docker_image.html)).

**Install on AWS (Ubuntu 24.04 EC2).** Instance: c7i.large is enough (runs are sub-second to a few seconds). `-j 2`.

1. `sudo apt-get install -y gfortran` (ask first), or use conda-forge's `gfortran` as on the Mac.
2. The same conda env as Route A; on Linux the sdist builds with the system or conda gfortran.
3. Docker fallback: `condaforge/miniforge3` (pinned digest) with `mamba install clawpack=5.9.0`, or `clawpack/v5.9.0_dockerimage:release` pinned by digest.
4. Check: the same import command.

**Preparing the examples for EMA.** Parameters are Python variables inside each example's `setup()`, set before the initial condition, or in `state.problem_data` (for example `problem_data['gamma']`, `['grav']`, `['rho']`, `['bulk']`).

Recipe:
- Copy the example `.py` into `examples/pyclaw/<name>/` and edit it once (with approval) so its `setup()` reads the physical parameters from a small `params.json` deck. The deck is the EMA template, so the code stays fixed and only the deck varies, as in `examples/cantera/`.
- Call `setup(..., disable_output=True, kernel_language='Fortran')` (Fortran Riemann solvers are much faster; shocktube defaults to the Python kernel), run `claw.run()`, compute the scalar from `claw.frames[-1]` or `claw.solution.q`, and write it to `output.json`.
- The command is the conda env's absolute python plus the driver. Set `OMP_NUM_THREADS=1`.
- For speed, use 200 to 400 cells and `num_output_times=1`.
- Outputs: use integrals (the mass right of x = 0, the total energy) for smooth structure, and point probes for jumps. A probe that a shock or contact crosses is **discontinuous** in the inputs, which is exactly what `nonsmooth` should find.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| [`euler_1d/shocktube.py`](https://github.com/clawpack/pyclaw/tree/master/examples/euler_1d) (Sod) | 1-D Euler Riemann problem, x ∈ [−1, 1], t = 0.4 | `p_l` 1.0 [0.5, 2.0]; `rho_r` 0.125 [0.05, 0.5]; `p_r` 0.1 [0.05, 0.3]; `gamma` 1.4 [1.2, 1.67] (all in `params.json`, used where `setup` sets the left and right states and `problem_data['gamma']`) | (1) the mass in x > 0 at t = 0.4 (model 1); (2) the density at a probe x = 0.5 (model 2) | (1) **Smooth, monotone** (increasing in `p_l`, decreasing in `p_r`), nearly additive. (2) **Jumps** where the shock or contact crosses x = 0.5, so `nonsmooth`/`curve1d` find them at this resolution. `gamma` matters less than the pressures | 0.3–1.5 s (import-dominated) at 400 cells, Fortran kernel **(estimate)** | cli (env python + driver) | json |
| [`shallow_1d/dam_break.py`](https://github.com/clawpack/pyclaw/tree/master/examples/shallow_1d) | 1-D shallow water dam break, `num_cells` 500, t = 2 | `h_l` 3.0 [1.5, 5.0]; `h_r` 1.0 [0.2, 1.4]; `grav` 1.0 [0.5, 9.81] (log) in `problem_data['grav']` | (1) the bore position at t = 2 (the location of the largest depth jump; model 1); (2) the depth at a gauge x = 1.0 (model 2) | (1) **A power law in g**: position ∝ √g at fixed depths (log-output exponent ≈ 0.5), smooth in h_l and h_r, with an h_l×h_r interaction. (2) **A jump** when the bore reaches the gauge | 0.3–1 s **(estimate)** | cli | json |
| [`acoustics_1d_homogeneous/acoustics_1d.py`](https://github.com/clawpack/pyclaw/tree/master/examples/acoustics_1d_homogeneous) | 1-D linear acoustics, periodic on [0, 1], Gaussian pulse, t = 1 | `rho` 1.0 [0.5, 2] (log); `bulk` 1.0 [0.5, 4] (log); pulse `beta` 200 [100, 400] | pressure at x = 0.5 at t = 1 | Depends on c = √(bulk/rho), so there is **one active direction** in (ln rho, ln bulk) with weights about (−1, +1). **Non-monotone and oscillatory** as the split pulses wrap round the periodic domain. The output is linear in pulse amplitude (not an input) | 0.2–1 s **(estimate)** | cli | json |

**Claude Code prompts.**

```text
Stage 1 (PyClaw/Clawpack, read-only machine check). In the EMA repo, without changing anything, report: OS and version, architecture (uname -m), disk space, conda/mamba (conda info), Python versions available, Fortran compilers (which gfortran; gfortran --version), Homebrew, Docker, and whether clawpack is importable in any existing conda env (conda env list). Do not read .env or touch EMA's .venv. Recommend a route: a conda env ema-clawpack with python=3.12 and conda-forge gfortran, meson, and meson-python, then pip install --no-build-isolation clawpack==5.14.0 (PyPI has no Intel-mac wheel); fallback conda-forge clawpack=5.9.0. Stop and report; don't install or continue.
```

```text
Stage 2a (PyClaw on the Intel Mac). Create the conda env ema-clawpack; never use EMA's .venv, never read .env, and make no Homebrew changes or sudo. Run: conda create -y -n ema-clawpack -c conda-forge python=3.12 numpy scipy matplotlib meson meson-python ninja gfortran pip; then conda run -n ema-clawpack pip install --no-build-isolation clawpack==5.14.0. If the build fails, stop and report the last 40 lines of the error. Don't improvise; the fallback (conda install -c conda-forge clawpack=5.9.0 in a fresh env) needs my approval. Check: conda run -n ema-clawpack python -c "import clawpack, clawpack.riemann; print(clawpack.__version__)". Then find the examples directory (python -c "import clawpack.pyclaw.examples as e, os; print(os.path.dirname(e.__file__))") and list it. Record the env's absolute python path in examples/pyclaw/PYTHON_PATH.txt. Stop and report; don't continue.
```

```text
Stage 2b (PyClaw on AWS Ubuntu 24.04 x86_64). I launched and ssh'd into the instance, and Claude Code runs there in a clone of the EMA repo. Never use EMA's .venv or read .env; ask before sudo. If conda is absent, ask before installing miniforge in $HOME. Then do the same as the Mac: conda create -y -n ema-clawpack -c conda-forge python=3.12 numpy scipy matplotlib meson meson-python ninja gfortran pip; conda run -n ema-clawpack pip install --no-build-isolation clawpack==5.14.0. Run the same check, and record the python path in examples/pyclaw/PYTHON_PATH.txt. Stop at the first error and report; don't continue.
```

```text
Stage 3 (PyClaw smoke test, clawpack 5.14.0 in env ema-clawpack). In a scratch directory outside the repo, run the Sod shock tube: copy euler_1d/shocktube.py from the installed examples (or from git clone --branch v5.14.0 https://github.com/clawpack/pyclaw), then run it with the env's python: python shocktube.py iplot=0 kernel_language=Fortran. Time it with /usr/bin/time. Also time python -c "import clawpack.pyclaw" alone, to separate import time. Report the wall times, the number of output frames, and the min and max density at the final frame (read with clawpack.pyclaw.Solution(frame, path='_output')). Stop and report; don't continue.
```

```text
Stage 4.1 (PyClaw: prepare the Sod shock tube for EMA). Use plan mode first. Package: clawpack 5.14.0 in conda env ema-clawpack (absolute python in examples/pyclaw/PYTHON_PATH.txt). Read docs/applications.md, docs/guides/input_deck_model.md, and examples/cantera/ (the driver-plus-deck pattern). Create examples/pyclaw/shocktube/:
- A driver shocktube_ema.py based on euler_1d/shocktube.py reads params.json (the template: p_l nominal 1.0 [0.5, 2.0]; rho_r 0.125 [0.05, 0.5]; p_r 0.1 [0.05, 0.3]; gamma 1.4 [1.2, 1.67]), keeping rho_l = 1.
- It runs 400 cells with the Fortran kernel, disable_output=True, and tfinal 0.4, and writes output.json with mass_right (the integral of density over x > 0) and rho_probe (the density in the cell containing x = 0.5).
- Two model files, model_mass.json and model_probe.json. Each uses the json parser on its key. The command is [<absolute env python>, "shocktube_ema.py"], with env OMP_NUM_THREADS=1.
Then `ema profile` each with -n 3 and report the time per run and the outputs at the nominal point. Stop and report; don't start a campaign.
```

```text
Stage 4.2 (PyClaw: prepare the dam break). Use plan mode first. Package: clawpack 5.14.0 (env ema-clawpack). Following examples/pyclaw/shocktube/, create examples/pyclaw/dambreak/ from shallow_1d/dam_break.py:
- Inputs in params.json: h_l 3.0 [1.5, 5.0]; h_r 1.0 [0.2, 1.4]; grav 1.0 [0.5, 9.81], scale log.
- Use the Fortran kernel with the Roe solver, 400 cells, and tfinal 2.
- Outputs: bore_x (the x of the largest downward depth jump right of the dam) and h_gauge (the depth at x = 1.0), as model_bore.json and model_gauge.json.
- Confirm the domain is wide enough that the bore stays inside it at grav 9.81 and h_l 5. If not, widen the domain or shorten tfinal and tell me.
Then `ema profile` each and report. Stop and report; don't start a campaign.
```

```text
Stage 4.3 (PyClaw: prepare 1-D acoustics). Use plan mode first. Package: clawpack 5.14.0 (env ema-clawpack). Following examples/pyclaw/shocktube/, create examples/pyclaw/acoustics/ from acoustics_1d_homogeneous/acoustics_1d.py:
- Inputs: rho 1.0 [0.5, 2] (log); bulk 1.0 [0.5, 4] (log); beta 200 [100, 400].
- Use the Fortran kernel, 200 cells, and tfinal 1. The output is the pressure at x = 0.5 at t = 1, in output.json, read by the json parser.
Then `ema profile` and report the time per run and the value at nominal (it should be close to the initial peak, since c = 1 wraps each half-pulse once round the unit periodic domain). Stop and report; don't start a campaign.
```

```text
Stage 5 (PyClaw first campaign). Using examples/pyclaw/shocktube/model_mass.json and model_probe.json (clawpack 5.14.0), write one campaign per model: for model_mass, morris with 8 trajectories (8 x 5 = 40 runs); for model_probe, curve1d on p_r with 25 points and nonsmooth on p_l (use its example parameters, and show me its cost). Run `ema estimate` on each and show me the run counts and times, then ask before running. After approval, run with -j 4 and report: whether mass_right is monotone and smooth, the Morris ranking, and whether curve1d/nonsmooth find jumps in rho_probe and where. Stop and report; don't run more.
```

```text
Stage 6 (PyClaw troubleshooting). An EMA run of a PyClaw model in examples/pyclaw/ (clawpack 5.14.0, conda env ema-clawpack) failed or looks wrong. Diagnose before editing. Read ema_run.json and stderr.txt in the run directory. Check in order:
(1) ImportError for clawpack.riemann (Fortran extensions not built; rebuild in the env, and don't switch Pythons);
(2) the command using the wrong python (it must be the env's absolute path; EMA doesn't activate conda);
(3) a CFL violation or NaN at the corners of the input box (the fixed dt/CFL settings; negative depth in the dam break when h_r is small);
(4) the Python kernel being used by mistake (slow runs);
(5) a probe output that jumps (expected: a wave crossed the probe; don't smooth it away);
(6) import time dominating the run time (report it);
(7) waves leaving a non-periodic domain (widen the domain).
Report the cause and the proposed fix; ask before editing.
```

**Gotchas and sources.**
- There is no Intel-mac wheel for 5.14.0: it is a source build needing gfortran and meson. conda-forge's binary package is 5.9.0.
- A plain `pip install` into EMA's `.venv` would work technically but pulls in a Fortran build; keep it in its own env as the brief requires.
- Runs are deterministic (serial, fixed CFL-driven stepping). PETSc parallel runs (`use_petsc`) aren't needed.
- Point probes and "location of a jump" outputs are piecewise constant or discontinuous at grid resolution. EMA should report them as jumps "at this resolution"; use integrals for smooth structure.
- GeoClaw and AMRClaw: AMR regridding causes nonsmoothness, `make` builds per model, and topography downloads make them heavy.
- Licence: BSD-3.
- Sources: https://api.github.com/repos/clawpack/clawpack/releases?per_page=3 · https://pypi.org/pypi/clawpack/json · https://raw.githubusercontent.com/clawpack/clawpack/v5.14.0/pyproject.toml · https://www.clawpack.org/installing_pip.html · https://www.clawpack.org/prereqs.html · https://www.clawpack.org/docker_image.html · https://anaconda.org/conda-forge/clawpack · https://www.clawpack.org/pyclaw/examples.html · https://github.com/clawpack/pyclaw/tree/master/examples · https://raw.githubusercontent.com/clawpack/pyclaw/master/examples/euler_1d/shocktube.py · https://raw.githubusercontent.com/clawpack/pyclaw/master/examples/shallow_1d/dam_break.py · https://raw.githubusercontent.com/clawpack/pyclaw/master/examples/acoustics_1d_homogeneous/acoustics_1d.py

---

#### Dedalus

**What it is.** Spectral methods (Fourier, Chebyshev, and curvilinear bases) for PDEs written symbolically in Python: initial-value, boundary-value, and eigenvalue problems. GPL-3.0, Python with Cython and FFTW and MPI. Current **v3.0.5**, released 2026-01-21 ([GitHub releases](https://api.github.com/repos/DedalusProject/dedalus/releases?per_page=2)). The examples are in [dedalus/examples](https://github.com/DedalusProject/dedalus/tree/master/examples): 16 scripts, including `ivp_1d_kdv_burgers`, `ivp_2d_rayleigh_benard`, `ivp_2d_shear_flow`, `evp_1d_rayleigh_benard`, `lbvp_2d_poisson`, and `ivp_sphere_shallow_water`. It qualifies as a comparable package with a rich collection of examples, and its spectral methods complement the finite-volume codes above. The 1-D examples run in seconds, and parameters are plain Python variables at the top of each script.

**Install on an Intel Mac.** conda-forge `dedalus` 3.0.5 is built for linux-64, **osx-64**, and osx-arm64 ([anaconda.org](https://anaconda.org/conda-forge/dedalus)). This is the project's recommended full-stack route ([installation](https://dedalus-project.readthedocs.io/en/latest/pages/installation.html)).

1. Create the env:
   ```bash
   conda create -n ema-dedalus -c conda-forge dedalus=3.0.5
   conda env config vars set -n ema-dedalus OMP_NUM_THREADS=1 NUMEXPR_MAX_THREADS=1
   ```
2. Check: `conda run -n ema-dedalus python -m dedalus test`. That runs the whole test suite (minutes), so a lighter check is `python -c "import dedalus.public as d3; print(d3.__name__)"`.

Known problems: the docs' Apple Silicon note (use osx-64 under Rosetta) does not apply to Intel. MPI (mpi4py) is initialised on import, and a macOS firewall prompt on first run is possible **(unconfirmed)**.

**Install on AWS (Ubuntu 24.04 EC2).** Instance: c7i.large (1-D examples), c7i.2xlarge for 2-D.

1. Install miniforge in `$HOME` if absent.
2. `conda create -n ema-dedalus -c conda-forge dedalus=3.0.5`, then set `OMP_NUM_THREADS=1` as above.
3. Docker fallback: `condaforge/miniforge3` pinned by digest, with `mamba install dedalus=3.0.5`.
4. Check: the same import check.

The pip route needs `FFTW_PATH`, `MPI_PATH`, and `CC=mpicc` ([installation](https://dedalus-project.readthedocs.io/en/latest/pages/installation.html)), so avoid it.

**Preparing the examples for EMA.** Each example script has a "Parameters" block of module variables. For example, `kdv_burgers.py` has `Lx = 10, Nx = 1024, a = 1e-4, b = 2e-4, dealias = 3/2, stop_sim_time = 10, timestepper = d3.SBDF2, timestep = 2e-3`, with an initial condition steepened by `n = 20`, and "should take just a few seconds to run".

Recipe:
- Copy the script into `examples/dedalus/<name>/` and change the Parameters block once, so it reads `params.json` (the template).
- Remove the HDF5 snapshot handlers (I/O) and compute the scalar at the end from the field's grid data, then write it to `output.json`. The command is the env's absolute python plus the script, with `OMP_NUM_THREADS=1`, and the json parser.
- To shrink, lower `Nx`/`Nz` and `stop_sim_time`. Keep the time step fixed (the 2-D examples use an adaptive CFL time step, which makes outputs slightly nonsmooth in the inputs). Keep seeded noise seeded (`fill_random(..., seed=42)`).
- The eigenvalue examples are the cheapest and fully deterministic.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| [`evp_1d_rayleigh_benard`](https://github.com/DedalusProject/dedalus/tree/master/examples/evp_1d_rayleigh_benard) | linear stability of no-slip Rayleigh–Bénard convection (`Nz = 64`, `Rayleigh = 1710`, `Prandtl = 1`, kx ∈ [3.0, 3.25]) | `Rayleigh` 1710 [1200, 2500]; `Prandtl` 1 [0.1, 10] (log); `kx` 3.117 [2.5, 3.7] | (1) the growth rate at the given kx (model 1); (2) the maximum growth rate over a 20-point kx grid (model 2) | (1) **Smooth, monotone in Rayleigh**, crossing 0 near Ra_c ≈ 1708 at kx ≈ 3.117; the zero crossing is **independent of Prandtl** (Pr changes the magnitude, so there is a Ra×Pr interaction). (2) **Kinks** where the argmax over the kx grid switches: nonsmooth by construction, at this resolution | 1–3 s at Nz = 32 (import about 1–2 s) **(estimate)** | cli | json |
| [`ivp_1d_kdv_burgers`](https://github.com/DedalusProject/dedalus/tree/master/examples/ivp_1d_kdv_burgers) | KdV–Burgers: dispersive, dissipative waves from a steep pulse | diffusivity `a` 1e-4 [5e-5, 5e-4] (log); dispersion `b` 2e-4 [1e-4, 1e-3] (log); steepness `n` 20 [10, 30]. Nx 256, `stop_sim_time` 5, fixed dt 2e-3 | the energy ∫u² dx at t = 5 | **Monotone decreasing in `a`**, and smooth. An interaction of `b` with `n` (dispersion vs. steepening). If `a` and `b` are both at their minimum, Nx = 256 under-resolves: Gibbs ripples and possible blow-up (NaN), which EMA records as failed runs | 2–5 s **(estimate)** | cli | json |
| [`lbvp_2d_poisson`](https://github.com/DedalusProject/dedalus/tree/master/examples/lbvp_2d_poisson) | Poisson equation, Fourier(x)×Chebyshev(y); Dirichlet `u(y=0) = g = 0.025·sin(8x)`, Neumann at the top; seeded filtered random forcing f | boundary amplitude `A` 0.025 [0, 0.05]; forcing scale `s` 1 [0, 2] (multiplying f); boundary wavenumber `k` 8 [2, 12] (integer-valued: treat as a discrete setting, or as a known step) | u at a fixed interior point | **Exactly linear in A and in s, and additive** (a linear BVP): a known-answer check for `linear_coeffs` (R² = 1) and `sobol` (no interactions between A and s). `k` interacts with A (u ∝ A·e^(−k·y)-like decay) | 1–2 s at 128×64 **(estimate)** | cli | json |

**Claude Code prompts.**

```text
Stage 1 (Dedalus, read-only machine check). In the EMA repo, without changing anything, report: OS and version, architecture (uname -m), disk space, conda/mamba (conda info), existing envs (conda env list), MPI (which mpirun), Docker, and whether dedalus is importable anywhere. Do not read .env or touch EMA's .venv. Recommend: a conda env ema-dedalus with conda-forge dedalus=3.0.5 and OMP_NUM_THREADS=1 (the same on the Intel Mac and Ubuntu 24.04); Docker (condaforge/miniforge3 pinned) only as fallback. Stop and report; don't install or continue.
```

```text
Stage 2a (Dedalus on the Intel Mac). Never use EMA's .venv or read .env; no Homebrew or sudo. Run conda create -y -n ema-dedalus -c conda-forge dedalus=3.0.5 (ask first if the download is over 1 GB), then conda env config vars set -n ema-dedalus OMP_NUM_THREADS=1 NUMEXPR_MAX_THREADS=1. Check: conda run -n ema-dedalus python -c "import dedalus, dedalus.public as d3; print(dedalus.__version__)". Record the env's absolute python in examples/dedalus/PYTHON_PATH.txt. Stop at the first error and report verbatim; don't continue.
```

```text
Stage 2b (Dedalus on AWS Ubuntu 24.04 x86_64). I launched and ssh'd into the instance, and Claude Code runs there in a clone of the EMA repo. Never use EMA's .venv or read .env; ask before sudo, and ask before installing miniforge in $HOME if conda is missing. Then conda create -y -n ema-dedalus -c conda-forge dedalus=3.0.5 and set OMP_NUM_THREADS=1 and NUMEXPR_MAX_THREADS=1 as env vars. Run the same import check, and record the python path in examples/dedalus/PYTHON_PATH.txt. Stop at the first error and report; don't continue.
```

```text
Stage 3 (Dedalus smoke test, 3.0.5 in env ema-dedalus). In a scratch directory outside the repo, fetch examples/ivp_1d_kdv_burgers/kdv_burgers.py from https://github.com/DedalusProject/dedalus at tag v3.0.5 and run it with the env's python and OMP_NUM_THREADS=1 (if it opens a plot window, set MPLBACKEND=Agg), timed with /usr/bin/time. Also time python -c "import dedalus.public" alone. Report both wall times, the final sim time and iteration count it logs, and any warnings. Stop and report; don't continue.
```

```text
Stage 4.1 (Dedalus: prepare the Rayleigh-Benard eigenvalue example). Use plan mode first. Package: Dedalus 3.0.5 in env ema-dedalus (absolute python in examples/dedalus/PYTHON_PATH.txt). Read docs/applications.md, docs/guides/input_deck_model.md, and examples/cantera/. Create examples/dedalus/rb_evp/ from examples/evp_1d_rayleigh_benard/rayleigh_benard_evp.py (tag v3.0.5):
- The script reads params.json (template: rayleigh 1710 [1200, 2500]; prandtl 1 [0.1, 10], scale log; kx 3.117 [2.5, 3.7]), uses Nz = 32 (check that the growth rate at nominal agrees with Nz = 64 to 1e-6 and report the difference), has no plotting, and writes output.json with growth_at_kx, plus growth_max over a fixed 20-point kx grid on [2.5, 3.7].
- Two model files, model_growth.json and model_growth_max.json, with the json parser and env OMP_NUM_THREADS=1.
Then `ema profile` each and report the time per run and the values at the nominal point (the growth rate should be slightly positive at Ra 1710). Stop and report; don't start a campaign.
```

```text
Stage 4.2 (Dedalus: prepare KdV-Burgers). Use plan mode first. Package: Dedalus 3.0.5 (env ema-dedalus). Create examples/dedalus/kdv_burgers/ from ivp_1d_kdv_burgers/kdv_burgers.py:
- Inputs in params.json: a 1e-4 [5e-5, 5e-4] (log); b 2e-4 [1e-4, 1e-3] (log); n 20 [10, 30].
- Nx 256, stop_sim_time 5, fixed timestep 2e-3, no file handlers or plots. Write output.json with energy (the integral of u^2 at the final time, computed with d3.Integrate or a grid sum).
- Check the four corners of (a, b) at n = 30 for NaN or blow-up and report. If any fails, propose narrower ranges or a larger Nx rather than changing them silently.
Then `ema profile` and report. Stop and report; don't start a campaign.
```

```text
Stage 4.3 (Dedalus: prepare the 2-D Poisson known-answer model). Use plan mode first. Package: Dedalus 3.0.5 (env ema-dedalus). Create examples/dedalus/poisson/ from lbvp_2d_poisson/poisson.py:
- Inputs in params.json: A 0.025 [0, 0.05] (the boundary amplitude replacing the 0.025 in g); s 1.0 [0, 2] (multiplying the seeded forcing f; keep its seed); k 8 [2, 12] (the boundary wavenumber, rounded to an integer in the script, and documented as such in model.json).
- Nx, Ny = 128, 64. The output is u at (x, y) = (1.0, 1.0), in output.json. No plots.
- Verify linearity by hand at 3 points before profiling: u(2A) - 2u(A) at s = 0 should be about 0.
Then `ema profile` and report. Stop and report; don't start a campaign.
```

```text
Stage 5 (Dedalus first campaign). Using examples/dedalus/rb_evp/model_growth.json (Dedalus 3.0.5), write a campaign with curve1d on rayleigh (15 points) and morris with 8 trajectories (32 runs): about 47 runs. Also, for examples/dedalus/poisson/model.json, write a campaign with linear_coeffs (small n, e.g. 20). Run `ema estimate` on both and show me the run counts and times, then ask before running. After approval, run with -j 4 and report: where the growth rate crosses zero (it should be near Ra 1708 for kx 3.117), whether prandtl changes that crossing, and whether linear_coeffs on the Poisson model reports R^2 about 1 with A and s linear. Stop and report; don't run more.
```

```text
Stage 6 (Dedalus troubleshooting). An EMA run of a Dedalus 3.0.5 model in examples/dedalus/ failed or looks wrong. Diagnose before editing. Read ema_run.json and stderr.txt. Check in order:
(1) the wrong python or a missing env (the command must be the env's absolute python);
(2) oversubscription or slow runs (OMP_NUM_THREADS=1 in the model's env; ema -j times threads must not exceed cores);
(3) MPI initialisation errors or hangs on macOS (try env MPICH/OpenMPI variables, and report);
(4) NaN or blow-up in the IVP at extreme inputs (under-resolution: Nx, dt);
(5) the eigenvalue solver returning a spurious mode (filter infinite or huge eigenvalues, as the example does);
(6) a matplotlib backend error (MPLBACKEND=Agg);
(7) import time dominating (report it).
Report the cause with evidence and a proposed fix; ask before editing.
```

**Gotchas and sources.**
- Licence: GPL-3.0; it runs as a separate program.
- Always set `OMP_NUM_THREADS=1` (the project says so); with `ema -j`, threads multiply.
- Import cost of about 1–2 s dominates the 1-D examples **(estimate)**. A persistent isolated Python model can't be used, because the package lives in its own env, not in EMA's venv.
- The 2-D IVP examples (`rayleigh_benard.py`: "about 5 cpu-minutes") are far over the time budget, and their adaptive CFL time stepping plus random initial noise make outputs sensitive. Use the 1-D, EVP, and LBVP examples.
- A maximum over a discrete kx grid is nonsmooth by construction. Label such outputs so EMA's kinks aren't mistaken for physics.
- Sources: https://api.github.com/repos/DedalusProject/dedalus/releases?per_page=2 · https://anaconda.org/conda-forge/dedalus · https://dedalus-project.readthedocs.io/en/latest/pages/installation.html · https://github.com/DedalusProject/dedalus/tree/master/examples · https://raw.githubusercontent.com/DedalusProject/dedalus/master/examples/ivp_1d_kdv_burgers/kdv_burgers.py · https://raw.githubusercontent.com/DedalusProject/dedalus/master/examples/evp_1d_rayleigh_benard/rayleigh_benard_evp.py · https://raw.githubusercontent.com/DedalusProject/dedalus/master/examples/lbvp_2d_poisson/poisson.py · https://raw.githubusercontent.com/DedalusProject/dedalus/master/examples/ivp_2d_rayleigh_benard/rayleigh_benard.py


### 4.4 PETSc, Devito, and other packages with example collections (desk research, checked 2026-09-24)

Everything below is desk research: nothing was installed or run. Versions and platform claims were checked on 2026-09-24 against the URLs cited. **(unconfirmed)** marks what I could not verify from official pages.

Two EMA facts shape every recipe below (from `docs/guides/input_deck_model.md` and `examples/beam/model_args.json`):
- Inputs can be **command-line arguments** (`"command": ["./ex19", "-grashof", "$grashof", ...]`) as well as template placeholders. PETSc options and FreeFEM `getARGV` fit that directly, with no template and no `$$` problem.
- A file next to `model.json` that the command names (a compiled binary, a driver script) is passed as an absolute path and covered by the version hash, so keep the compiled tutorial binary or driver in the model directory. Programs given by absolute path (a conda env's `python`) are not hashed.

---

#### PETSc

**What it is.** Portable, Extensible Toolkit for Scientific Computation (Argonne): parallel linear/nonlinear solvers (KSP, SNES), time steppers (TS), structured-grid (DMDA) and unstructured (DMPlex) support. C with Fortran and Python (`petsc4py`) bindings. BSD-2-Clause. Current release **3.25.5** (install page, checked 2026-09-24). Examples live in the source tree as `src/<package>/tutorials/exNN.c`, each with a `/*TEST ... TEST*/` block of test command lines at the bottom; they are browsable at `https://petsc.org/release/src/snes/tutorials/index.html`, `https://petsc.org/release/src/ts/tutorials/index.html`, `.../src/ksp/tutorials/`, `.../src/tao/tutorials/`, `.../src/dm/tutorials/`. There are several hundred tutorials across packages (SNES and TS alone have dozens each; exact count **(unconfirmed)**). Every tutorial is configured by the **options database**: command-line options such as `-da_grid_x 32 -da_grid_y 32 -par 5.0 -snes_monitor -pc_type lu`, also readable from a file (`-options_file`) or the `PETSC_OPTIONS` environment variable. `petsc4py` has only one documented demo (`poisson2d`), so the C tutorials are the collection to use.

**Install on an Intel Mac.** conda-forge builds `petsc` and `petsc4py` 3.25.5 for **osx-64** (prefix.dev lists linux-64, linux-aarch64, osx-64, osx-arm64). Homebrew's `petsc` 3.25.5 has bottles only for Apple Silicon macOS and Linux, so on an Intel Mac `brew install petsc` would build PETSc and its dependencies (gcc, open-mpi, hdf5-mpi, ...) from source: slow, and not recommended. The conda packages do not include the tutorials, so download the matching source tarball for them.

1. Install Miniforge if there is no conda or mamba (https://github.com/conda-forge/miniforge).
2. Create a dedicated environment with the same version as the tutorials, a C compiler, make, and pkg-config:
   ```bash
   mamba create -n ema-petsc -c conda-forge python=3.12 petsc=3.25.5 petsc4py=3.25.5 mpich compilers make pkg-config
   ```
3. Get the tutorials from the matching tarball (source only, not the with-docs one):
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -LO https://web.cels.anl.gov/projects/petsc/download/release-snapshots/petsc-3.25.5.tar.gz
   tar xf petsc-3.25.5.tar.gz
   ```
4. Compile one tutorial against the conda PETSc (PETSc's recommended user makefile is `$PETSC_DIR/share/petsc/Makefile.user`, which uses pkg-config; with conda `PETSC_DIR=$CONDA_PREFIX`):
   ```bash
   conda activate ema-petsc
   cd ~/src/petsc-3.25.5/src/snes/tutorials
   mpicc ex19.c -o ex19 $(pkg-config --cflags --libs petsc)
   ```
   If `pkg-config` finds no `petsc`, try `PETSc` (the `.pc` file name) or `cp $CONDA_PREFIX/share/petsc/Makefile.user makefile && make ex19` **(unconfirmed that the conda package ships `Makefile.user` and which `.pc` name it uses)**.
5. Check:
   ```bash
   ./ex19 -da_grid_x 16 -da_grid_y 16 -snes_monitor_short -snes_converged_reason
   python -c "from petsc4py import PETSc; print(PETSc.Sys.getVersion())"
   ```
   Expect `(3, 25, 5)` and a converged SNES.

Known problems: the conda `compilers` clang on osx-64 needs the Xcode Command Line Tools SDK (`xcode-select --install`); MPICH may print warnings about the network interface on a laptop without a network (set `MPIR_CVAR_CH3_INTERFACE_HOSTNAME=localhost` if so **(unconfirmed)**); serial runs (`./ex19` without `mpiexec`) avoid MPI launch overhead entirely.

Sources: https://petsc.org/release/install/ ; https://prefix.dev/channels/conda-forge/packages/petsc ; https://prefix.dev/channels/conda-forge/packages/petsc4py ; https://formulae.brew.sh/formula/petsc ; https://petsc.org/release/install/download/ ; https://petsc.org/release/manual/getting_started/

**Install on AWS (Ubuntu 24.04 EC2).** Three native routes: conda-forge (same 3.25.5 as the Mac; recommended, so both machines run identical code), apt (`petsc-dev` in noble/universe is **3.19.6**, too old to share tutorials with 3.25), or Spack (`spack install petsc`, a long source build). There is no official PETSc Docker image **(unconfirmed; none found)**; the fallback is a conda environment inside a pinned `condaforge/miniforge3` image. A `c7i.xlarge` (4 vCPU, 8 GiB) is plenty for serial laptop-size runs with `-j 4` in EMA.

1. `sudo apt-get update && sudo apt-get install -y build-essential curl` (only for curl/make; the compiler comes from conda).
2. Install Miniforge, then the same environment as on the Mac:
   ```bash
   mamba create -n ema-petsc -c conda-forge python=3.12 petsc=3.25.5 petsc4py=3.25.5 mpich compilers make pkg-config
   ```
3. Download and unpack `petsc-3.25.5.tar.gz` as on the Mac; compile with `mpicc ... $(pkg-config --cflags --libs petsc)`.
4. Docker fallback (pin by digest after the first pull):
   ```bash
   docker pull condaforge/miniforge3:latest
   docker inspect --format '{{index .RepoDigests 0}}' condaforge/miniforge3:latest
   ```
   and build a small image that runs step 2 and compiles the chosen tutorials.
5. Check: same as the Mac.

apt route, if chosen anyway: `sudo apt-get install -y petsc-dev` then use tutorials from `petsc-3.19.6.tar.gz` (older options may differ).

Sources: https://packages.ubuntu.com/noble/petsc-dev ; https://petsc.org/release/install/ ; https://prefix.dev/channels/conda-forge/packages/petsc

**Preparing the examples for EMA.** Every physical parameter of a tutorial is an option read with `PetscOptionsGetReal`/`PetscOptionsReal`, so EMA passes inputs as command arguments: `["./ex19", "-grashof", "$grashof", ...]`, with fixed settings (grid, solver, tolerances) either as literal arguments or in a static options file passed with `-options_file petsc.opts`. Shrink with `-da_grid_x/-da_grid_y` (or `-da_refine k` from the tiny default grid) and use a direct solver (`-pc_type lu`) in serial to remove Krylov-tolerance jitter; tighten `-snes_rtol 1e-10 -snes_atol 1e-12`. Add `-snes_error_if_not_converged` (documented option) so a diverged Newton solve exits non-zero and EMA records a failed run instead of a wrong number. Most tutorials print only iteration counts, so the copied tutorial needs a two-line edit after `SNESSolve`/`TSSolve`: compute a scalar (`VecMax`, `VecNorm`, or `VecStrideNorm` for one field) and `PetscPrintf(PETSC_COMM_WORLD, "EMA_OUTPUT %.12e\n", value)`; parse it with a regex on stdout. (A `-snes_view_solution` viewer option that would avoid editing the C file is **(unconfirmed)**; I could not find it in the 3.25 docs.) Recompile inside the `ema-petsc` env and keep the binary in the model directory, so the version hash covers it.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `src/snes/tutorials/ex19.c` (https://petsc.org/release/src/snes/tutorials/ex19.c.html), grid 32×32, `-pc_type lu` | 2-D driven cavity with buoyancy, velocity–vorticity–temperature | `-lidvelocity` 1 [0.1, 10]; `-grashof` 100 [1, 1e4] (log); `-prandtl` 1 [0.1, 10] (log) | added print of `VecStrideNorm(x, 0, NORM_2)` (norm of the u velocity field); second model: temperature field norm (field 3) | smooth; lid velocity dominant when Grashof small; Grashof × Prandtl interaction (buoyancy-driven regime); possible Newton failures at high Grashof and low lid speed (a failure region) | < 1 s (serial, 32×32, LU) **(estimate)** | command-line (binary in model dir, options as args) | regex `EMA_OUTPUT (\S+)` on stdout |
| `src/snes/tutorials/ex15.c` (https://petsc.org/release/src/snes/tutorials/ex15.c.html), grid 33×33, `-blocks 2,2` | p-Laplacian Bratu with piecewise diffusivity | `-p` 2 [1.3, 3]; `-lambda` 0.5 [0, 3]; `-source` 0.1 [0.01, 1] (log); `-kappa` 1e-3 [1e-4, 1] (log) | added print of `VecMax(u)` | strong p × lambda interaction; fold of the Bratu branch in lambda → failed runs above a curve (nonsmooth/failure-region map); kappa's effect on a log scale | ~1 s **(estimate)** | command-line | regex |
| `src/ts/tutorials/ex20.c` (https://petsc.org/release/src/ts/tutorials/ex20.c.html) | van der Pol oscillator (stiff ODE, TS with adaptive steps) | `-mu` 10 [1, 1000] (log); `-ts_max_time` 0.5 [0.1, 3] | first component y(T) of the final solution the program already prints (`VecView` after `TSSolve`) | smooth in T for small mu; relaxation oscillation for large mu gives steep, near-jump changes in y(T) (curve1d/nonsmooth); adaptive-step jitter unless `-ts_rtol 1e-10 -ts_atol 1e-12` | < 0.2 s | command-line | python parser (read the first number after the `Vec Object` header) or regex |

**Claude Code prompts.**

```text
Stage 1 (PETSc, read-only check). In the EMA repo, check this machine for running PETSc 3.25.5 tutorials as EMA command-line models. Read-only: report OS and version, CPU architecture (uname -m), whether conda/mamba/Miniforge exist and their versions, Homebrew (brew --version, and whether brew lists petsc), Docker (docker version), a C compiler (cc --version, xcode-select -p on macOS), any MPI (mpicc/mpiexec on PATH), free disk space in $HOME, and any existing conda env named ema-petsc. Do not install or change anything, and do not read .env. Recommend a route: conda-forge env "ema-petsc" with petsc=3.25.5 (osx-64 and linux-64 are built); Homebrew only as a last resort on Intel (no Intel bottle); apt petsc-dev only if conda is impossible (it is 3.19.6). Stop and report; don't continue to the next stage.
```

```text
Stage 2a (PETSc, install on the Intel Mac). Install PETSc 3.25.5 for EMA on this Intel Mac (osx-64) via conda-forge, never into EMA's .venv, and never read .env. Steps: (1) if no conda/mamba, ask me before installing Miniforge; (2) mamba create -n ema-petsc -c conda-forge python=3.12 petsc=3.25.5 petsc4py=3.25.5 mpich compilers make pkg-config; (3) ask me, then download https://web.cels.anl.gov/projects/petsc/download/release-snapshots/petsc-3.25.5.tar.gz to ~/src and unpack it (tutorials only; do not configure or build PETSc from it); (4) in the env, compile src/snes/tutorials/ex19.c with mpicc and pkg-config (try the pc names petsc and PETSc; else $CONDA_PREFIX/share/petsc/Makefile.user); (5) check: python -c "from petsc4py import PETSc; print(PETSc.Sys.getVersion())" and ./ex19 -da_grid_x 16 -da_grid_y 16 -snes_converged_reason. Ask before any sudo, Homebrew change, or download over 1 GB. Stop at the first error and report the exact command and output instead of improvising. Stop and report the versions and the check output; don't continue to the next stage.
```

```text
Stage 2b (PETSc, install on AWS Ubuntu 24.04 x86_64; I am ssh'd into the instance). Install PETSc 3.25.5 for EMA via conda-forge in an env named ema-petsc (not apt: noble's petsc-dev is 3.19.6), never into EMA's .venv, and never read .env. Ask me before any sudo (apt-get install build-essential curl only if missing). Then: Miniforge (ask first), mamba create -n ema-petsc -c conda-forge python=3.12 petsc=3.25.5 petsc4py=3.25.5 mpich compilers make pkg-config; download and unpack petsc-3.25.5.tar.gz from https://web.cels.anl.gov/projects/petsc/download/release-snapshots/ into ~/src; compile src/snes/tutorials/ex19.c with the env's mpicc and pkg-config. If conda fails, propose (do not run) a Docker fallback: a Dockerfile FROM condaforge/miniforge3 pinned by digest that does the same. Check with petsc4py's getVersion and ./ex19 -da_grid_x 16 -da_grid_y 16 -snes_converged_reason. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (PETSc smoke test). In the ema-petsc conda env (PETSc 3.25.5), from ~/src/petsc-3.25.5/src/snes/tutorials, compile ex5.c and ex19.c if not already compiled, then run and time: ./ex5 -da_grid_x 17 -da_grid_y 17 -snes_monitor -snes_converged_reason; ./ex19 -da_refine 3 -snes_monitor_short -pc_type lu -snes_converged_reason; and one TS tutorial: compile src/ts/tutorials/ex20.c and run ./ex20 -mu 10. Use /usr/bin/time (or time) for wall time. Report each command's final lines and wall time. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (PETSc, prepare SNES ex19 as an EMA model). Use plan mode first and show me the plan before writing anything. Package: PETSc 3.25.5 from the ema-petsc conda env; tutorial src/snes/tutorials/ex19.c (driven cavity). Copy ex19.c into examples/petsc/ex19_cavity/, add after SNESSolve a VecStrideNorm(x, 0, NORM_2, &nrm) and PetscPrintf "EMA_OUTPUT %.12e\n" (nothing else changed; note the edit in a comment), and a small build script that compiles it with the env's mpicc into ex19 in that directory. Write model.json as a command-line model (read docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/model.json, examples/modflow/model.json, examples/beam/model_args.json): command ["ex19", "-lidvelocity", "$lidvelocity", "-grashof", "$grashof", "-prandtl", "$prandtl", "-options_file", "petsc.opts"], static file petsc.opts with -da_grid_x 32 -da_grid_y 32 -pc_type lu -snes_rtol 1e-10 -snes_error_if_not_converged; inputs lidvelocity 1 [0.1, 10], grashof 100 [1, 1e4] with scale log, prandtl 1 [0.1, 10] with scale log; output regex "EMA_OUTPUT (\S+)" on stdout; number_format ".10g"; timeout_s 60. If the binary needs the env's shared libraries at run time, set them through the spec's env (not a shell). Then run `.venv/bin/ema profile examples/petsc/ex19_cavity/model.json -n 5` and report time per run and the output at nominal. Stop and report; don't continue to the next stage.
```

```text
Stage 4.2 (PETSc, prepare SNES ex15 p-Bratu). Plan mode first. PETSc 3.25.5, ema-petsc env; tutorial src/snes/tutorials/ex15.c. Copy into examples/petsc/ex15_pbratu/, add after SNESSolve a VecMax of the solution printed as "EMA_OUTPUT %.12e\n", build the binary in that directory with the env's mpicc. Command-line model like examples/beam/model_args.json: ["ex15", "-p", "$p", "-lambda", "$lam", "-source", "$source", "-kappa", "$kappa", "-options_file", "petsc.opts"], with petsc.opts holding -da_grid_x 33 -da_grid_y 33 -blocks 2,2 -jtype NEWTON -pc_type lu -snes_rtol 1e-10 -snes_error_if_not_converged (and -o pointing at a file inside the run directory, or disable the VTS write if the code allows). Inputs: p 2 [1.3, 3], lam 0.5 [0, 3], source 0.1 [0.01, 1] (log), kappa 1e-3 [1e-4, 1] (log). Output regex on stdout. Then `.venv/bin/ema profile examples/petsc/ex15_pbratu/model.json -n 5`; also try lam = 3 once by hand and report whether SNES diverges (expected: a failure region). Stop and report; don't continue to the next stage.
```

```text
Stage 4.3 (PETSc, prepare TS ex20 van der Pol). Plan mode first. PETSc 3.25.5, ema-petsc env; tutorial src/ts/tutorials/ex20.c, unmodified. Build the binary into examples/petsc/ex20_vdp/. Command-line model: ["ex20", "-mu", "$mu", "-ts_max_time", "$T", "-ts_rtol", "1e-10", "-ts_atol", "1e-12"]; first check by hand that -ts_max_time overrides the tutorial's 0.5 (it is set before TSSetFromOptions, verify in the source). Output: the first component of the final solution the program prints with VecView; use a small python output parser (parse.py, isolated) that reads stdout.txt and returns the first number after the "Vec Object" header, or a regex if the format is stable. Inputs: mu 10 [1, 1000] scale log, T 0.5 [0.1, 3]. Then `.venv/bin/ema profile examples/petsc/ex20_vdp/model.json -n 5`. Stop and report; don't continue to the next stage.
```

```text
Stage 5 (PETSc, first campaign). For examples/petsc/ex19_cavity/model.json (PETSc 3.25.5 ex19), write examples/petsc/ex19_cavity/campaign.json with: repeat (2 points × 3 replicates, to confirm determinism), morris with 8 trajectories, and curve1d on grashof with 15 points. Compute the run count with `.venv/bin/ema estimate` and show it to me; ask before running. Then `.venv/bin/ema run ... -j 4` and report: repeatability, morris ranking and monotone flags, any failed runs and where they are, curve1d features. Expected: smooth, lidvelocity dominant, grashof x prandtl interaction, possible failures at high grashof. Stop and report; don't continue.
```

```text
Stage 6 (PETSc troubleshooting). An EMA command-line model built from a PETSc 3.25.5 tutorial fails. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt and ema_run.json: (a) "dyld: Library not loaded"/"cannot open shared object file": the binary can't find the conda env's libpetsc; fix by an rpath at compile time (-Wl,-rpath,$CONDA_PREFIX/lib) rather than DYLD_LIBRARY_PATH (macOS strips DYLD_* from child processes of protected binaries); (b) "WARNING! There are options you set that were not used": misspelled option or option read under a prefix; run once with -options_left; (c) SNES DIVERGED_* with -snes_error_if_not_converged: expected in a failure region; check it is reproducible and not a too-loose linear solve (use -pc_type lu); (d) MPI init hangs or network warnings from MPICH: run serial without mpiexec; (e) output jitter between replicates: tighten -snes_rtol/-ts_rtol, use LU, run serial; (f) pkg-config can't find petsc: check $CONDA_PREFIX/lib/pkgconfig. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License BSD-2-Clause; the conda MPICH/Open MPI builds bring their own licenses (permissive).
- MPI: run serially (no `mpiexec`) for laptop configs; EMA's `-j N` gives the parallelism. If you do use `mpiexec -n k`, parallel reductions can change the last digits: set `number_format` and expect `repeat` to show tiny noise.
- Determinism: iterative Krylov solves stop at a tolerance, so outputs move with the input by tolerance-sized steps; use `-pc_type lu` or tight `-ksp_rtol` for small grids. Adaptive TS steps behave the same way.
- Run time: the default grids are tiny (ex5, ex19 start at 4×4); `-da_refine 3`–`4` (~33–65 points per side) is the laptop regime.
- Version pitfalls: tutorials must match the library version (options and APIs change between minor releases); apt's 3.19.6 differs from conda's 3.25.5. `-da_grid_x` must be set before `DMSetUp` (the tutorials call `DMSetFromOptions`, so the command line is fine).
- Homebrew on Intel macOS: no bottle; source build. conda-forge still builds osx-64 (checked 2026-09-24), but many conda-forge dependencies are dropping osx-64; pin the env with `conda env export > ema-petsc.yml`.
- Sources: https://petsc.org/release/install/ ; https://petsc.org/release/install/download/ ; https://petsc.org/release/manual/getting_started/ ; https://petsc.org/release/manual/other/ (options database) ; https://petsc.org/release/manualpages/SNES/SNESSetErrorIfNotConverged/ ; https://petsc.org/release/manualpages/SNES/SNESSetFromOptions/ ; https://petsc.org/release/src/snes/tutorials/ex19.c.html ; https://petsc.org/release/src/snes/tutorials/ex15.c.html ; https://petsc.org/release/src/snes/tutorials/ex5.c.html ; https://petsc.org/release/src/ts/tutorials/ex20.c.html ; https://petsc.org/release/petsc4py/demo/demo.html ; https://prefix.dev/channels/conda-forge/packages/petsc ; https://prefix.dev/channels/conda-forge/packages/petsc4py ; https://formulae.brew.sh/formula/petsc ; https://packages.ubuntu.com/noble/petsc-dev

---

#### Devito

**What it is.** A Python DSL and just-in-time compiler for finite-difference stencil codes (seismic imaging, wave propagation, simple CFD). MIT license; Python that generates and compiles C (OpenMP/MPI/GPU optional). Latest **4.8.23** on PyPI (2026-08-07), pure-Python wheel, Python 3.10–3.14. Examples: `examples/seismic/` (acoustic, elastic, tti, viscoacoustic, viscoelastic, self_adjoint, abc_methods, inversion, tutorials), `examples/cfd/` (11 notebooks: convection, diffusion, Burgers, Laplace, Poisson, cavity flow, shallow water, Darcy flow), and `examples/userapi/` notebooks; https://github.com/devitocodes/devito/tree/main/examples. Why it qualifies (one line): a comparable open-source PDE framework with a rich example collection, pip-installable and fast per run, covering wave propagation, which no other package here does.

**Install on an Intel Mac.** Devito needs only Python and a C compiler; Apple clang from the Xcode Command Line Tools works (`DEVITO_ARCH=clang` or `osx`); Apple clang lacks OpenMP, so keep the default single-threaded C backend (EMA parallelizes across runs anyway). Its dependencies (numpy, sympy, cgen, codepy, psutil) have osx-64 wheels or are pure Python **(unconfirmed per dependency; numpy's last osx-64 wheels depend on the numpy version)**.

1. `xcode-select --install` (if `xcode-select -p` fails).
2. Create an env of its own (conda gives an osx-64 numpy regardless of PyPI wheel policy):
   ```bash
   mamba create -n ema-devito -c conda-forge python=3.12 numpy scipy matplotlib pip
   conda activate ema-devito
   python -m pip install "devito==4.8.23"
   git clone --depth 1 --branch v4.8.23 https://github.com/devitocodes/devito.git ~/src/devito   # examples; tag name (unconfirmed)
   ```
3. Check:
   ```bash
   DEVITO_ARCH=clang python -c "import devito; print(devito.__version__)"
   cd ~/src/devito && DEVITO_ARCH=clang python examples/seismic/acoustic/acoustic_example.py -d 101 101 --tn 500   # CLI flags per seismic_args (unconfirmed spelling)
   ```
Known problems: the examples are imported as the `examples` package from the repo root (`from examples.seismic import demo_model, ...`), so the driver must put the clone on `sys.path` or run from it; the JIT cache lives under the temp dir (`TMPDIR`), per the FAQ.

Sources: https://pypi.org/project/devito/ ; https://www.devitoproject.org/download.html ; https://github.com/devitocodes/devito/blob/main/FAQ.md ; https://github.com/devitocodes/devito

**Install on AWS (Ubuntu 24.04 EC2).**
1. `sudo apt-get install -y build-essential git` (gcc for the JIT).
2. Same env as the Mac (or a plain `python3 -m venv ~/venvs/ema-devito` with `pip install devito==4.8.23`), plus the clone for the examples. Use `DEVITO_ARCH=gcc`; `DEVITO_LANGUAGE=openmp` is optional (leave it off and let EMA's `-j` parallelize).
3. Docker fallback: `devitocodes/devito` images on Docker Hub (`latest`, `cpu-dev`, `gcc-dev`; linux/amd64 and arm64). Pin by digest: `docker pull devitocodes/devito:gcc-dev && docker inspect --format '{{index .RepoDigests 0}}' devitocodes/devito:gcc-dev`. Docker Desktop on the Intel Mac can use the same image.
4. Check: as on the Mac. Instance: `c7i.xlarge` or `c7i.2xlarge`.

Sources: https://www.devitoproject.org/download.html ; https://hub.docker.com/r/devitocodes/devito/tags

**Preparing the examples for EMA.** Devito examples are Python scripts and notebooks whose parameters are Python variables or keyword arguments (`demo_model('layers-isotropic', vp_top=1.5, vp_bottom=3.5, nlayers=3, shape=(101, 101), spacing=(10., 10.), nbl=10)` in `examples/seismic/preset_models.py`; `tn`, source frequency `f0`, `space_order`). The pattern is a short driver script in the model directory, run by the env's absolute `python` path, that reads a small deck (or `argparse` options), builds the model and solver from the example's own functions, runs one forward simulation, and prints one scalar. Keep the grid shape, spacing, space order, and `tn` fixed across runs: then the generated C is identical and Devito's on-disk JIT cache means only the first run pays the compile (a few seconds); whether a fresh process reuses the cached shared object is **(unconfirmed)**, measure it with `ema profile`. Physical parameters are data, not code, so they never trigger recompilation. Set `DEVITO_LOGGING=ERROR` to keep stdout clean. Float32 is the default (`dtype=np.float32`): outputs carry ~1e-7 relative noise-like rounding, so tell EMA through `repeat` or use `dtype=np.float64`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/seismic/acoustic/acoustic_example.py` + `preset_models.py` 'layers-isotropic', 101×101, tn 1000 ms | 2-D acoustic wave propagation in a layered medium, Ricker source, receiver line | `vp_top` 1.5 km/s [1.2, 2.0]; `vp_bottom` 3.5 km/s [2.5, 4.5]; source peak frequency `f0` 0.010 kHz [0.005, 0.02]; (fixed `nlayers` 3) | (a) L2 norm of the receiver traces; (b) first-arrival time at the farthest receiver (threshold crossing) | (a) smooth, vp_top dominant; (b) piecewise constant in steps of dt (jumps at time-step resolution) and a kink where the refracted head wave overtakes the direct wave, a good nonsmooth test | ~1 s after the first compile **(estimate)** | command-line (env python + driver) | regex on stdout |
| `examples/cfd/04_burgers.ipynb` (converted to a driver) | 2-D viscous Burgers, explicit time stepping | viscosity `nu` 0.01 [0.001, 0.1] (log); initial hat amplitude 2 [1, 3]; number of steps fixed | max of u at the final time | smooth in nu; steepening at low nu; explicit-scheme instability (NaN/blow-up) at the high end of nu when dt is fixed → failure region | < 1 s **(estimate)** | command-line | regex |

**Claude Code prompts.**

```text
Stage 1 (Devito, read-only check). Check this machine for running Devito 4.8.23 examples as EMA command-line models. Read-only: OS, uname -m, conda/mamba, a C compiler (cc --version; xcode-select -p on macOS; gcc on Linux), Docker, free disk, existing env ema-devito, and whether ~/src/devito exists. Don't install anything; don't read .env. Recommend: conda env ema-devito (python 3.12) + pip devito==4.8.23 + a clone of the matching tag for examples; Docker devitocodes/devito pinned by digest only as fallback. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (Devito, install on the Intel Mac). Install Devito 4.8.23 in a conda env named ema-devito (conda-forge python=3.12 numpy scipy matplotlib pip, then pip install devito==4.8.23), never EMA's .venv, never read .env. Ask before installing Miniforge or the Xcode Command Line Tools. Shallow-clone https://github.com/devitocodes/devito at the tag for 4.8.23 into ~/src/devito (check the tag name with git ls-remote --tags first). Check: DEVITO_ARCH=clang python -c "import devito; print(devito.__version__)". Stop at the first error and report it. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (Devito, install on AWS Ubuntu 24.04; I am on the instance). Ask before sudo apt-get install -y build-essential git. Create conda env ema-devito (python=3.12) or a venv at ~/venvs/ema-devito, pip install devito==4.8.23, clone the matching tag into ~/src/devito. Use DEVITO_ARCH=gcc. If pip fails, propose (don't run) the Docker fallback devitocodes/devito:gcc-dev pinned by digest. Check the import and version. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (Devito smoke test). In ema-devito, from ~/src/devito, run the acoustic example with a small grid (python examples/seismic/acoustic/acoustic_example.py --help first, then a 101x101, tn 500 run), twice, timing each with time. Report the output, the first and second wall times (the second shows the JIT cache), and where the JIT cache directory is. Don't touch EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (Devito, prepare the layered acoustic example). Plan mode first. Devito 4.8.23 in env ema-devito. Create examples/devito/acoustic_layers/ with a driver acoustic.py that adds ~/src/devito to sys.path (path passed via the spec's env, e.g. DEVITO_EXAMPLES), reads deck.txt (vp_top, vp_bottom, f0), builds demo_model('layers-isotropic', vp_top=..., vp_bottom=..., nlayers=3, shape=(101,101), spacing=(10.,10.), nbl=10, space_order=4, dtype=np.float64), a Ricker source at the top centre and a receiver line, runs AcousticWaveSolver forward to tn=1000 ms, and prints "EMA_OUTPUT <L2 norm of rec.data>". Template deck.template with $vp_top $vp_bottom $f0. Command: [<absolute path of ema-devito's python>, "acoustic.py", "deck.txt"]; env DEVITO_ARCH (clang on Mac, gcc on Linux), DEVITO_LOGGING=ERROR. Follow docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/. Inputs: vp_top 1.5 [1.2, 2.0], vp_bottom 3.5 [2.5, 4.5], f0 0.010 [0.005, 0.02]. Then `.venv/bin/ema profile examples/devito/acoustic_layers/model.json -n 5` and report time per run (first vs later). Also add a second model.json (model_arrival.json) printing the first-arrival time at the farthest receiver (first sample above 1% of the trace max). Stop and report; don't continue.
```

```text
Stage 4.2 (Devito, prepare Burgers). Plan mode first. Devito 4.8.23, env ema-devito. Convert examples/cfd/04_burgers.ipynb (Devito part only) into examples/devito/burgers/burgers.py driven by deck.txt with nu and the hat amplitude; keep grid, dt and step count as in the notebook; print "EMA_OUTPUT <max u at final time>"; exit non-zero if the field has NaN/Inf. Command-line model as in stage 4.1. Inputs nu 0.01 [0.001, 0.1] scale log, amp 2 [1, 3]. Profile with `.venv/bin/ema profile ... -n 5`; also run nu=0.1 once and report whether it blows up. Stop and report; don't continue.
```

```text
Stage 5 (Devito, first campaign). For examples/devito/acoustic_layers/model.json write a campaign: repeat (2 points x 3), morris (8 trajectories), and curve1d on vp_top (15 points) for model_arrival.json. Show the run count from `.venv/bin/ema estimate` and ask before running with -j 4. Report repeatability, ranking, and curve1d jumps/kinks (expected: steps at dt resolution in the arrival time; smooth norm). Stop and report.
```

```text
Stage 6 (Devito troubleshooting). A Devito 4.8.23 EMA model fails or is slow. Check read-only: stderr for "CompilationError" (compiler missing, or DEVITO_ARCH wrong for the platform); "ModuleNotFoundError: examples" (sys.path to the clone); every run recompiling (the grid/space_order/tn changed, or the JIT cache dir isn't writable/persistent: check TMPDIR in the spec's env); NaN outputs (CFL: dt too large for the highest velocity; Devito's critical_dt); replicate differences (float32; use float64, and don't set DEVITO_LANGUAGE=openmp with nondeterministic reductions). Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- MIT license. No MPI needed at laptop size; leave `DEVITO_MPI` off.
- The first run per grid configuration compiles C (seconds); keep geometry fixed across a campaign. Geometric inputs (layer depth, domain size) change the grid or the source/receiver positions → interpolation effects and possible recompiles.
- CFL: `critical_dt` depends on the maximum velocity; if the driver lets Devito pick dt from the model, dt changes with `vp_bottom`, adding small discretization-driven wiggles; fix dt from the upper end of the range.
- Examples are research-grade: the `examples` package APIs change between releases; pin the tag.
- Sources: https://github.com/devitocodes/devito ; https://pypi.org/project/devito/ ; https://www.devitoproject.org/download.html ; https://github.com/devitocodes/devito/blob/main/FAQ.md ; https://raw.githubusercontent.com/devitocodes/devito/main/examples/seismic/preset_models.py ; https://raw.githubusercontent.com/devitocodes/devito/main/examples/seismic/acoustic/acoustic_example.py ; https://github.com/devitocodes/devito/tree/main/examples/cfd ; https://hub.docker.com/r/devitocodes/devito/tags

---

#### py-pde

**What it is.** A Python package for solving PDEs by finite differences on regular grids (Cartesian, polar, spherical, cylindrical), with PDEs given as expression strings and compiled with numba. MIT. Latest **0.59.0** on conda-forge (noarch; Python >=3.11,<3.14; numba >=0.59). Examples: `examples/simple_pdes/` (15 scripts, e.g. `pde_brusselator_expression.py`, `pde_heterogeneous_diffusion.py`, `boundary_conditions.py`, `klein_gordon.py`, `pde_schroedinger.py`), `examples/advanced_pdes/`, `examples/fields/`, `examples/output/`, `examples/jupyter/`; the gallery has 42 examples (https://py-pde.readthedocs.io/en/latest/gallery.html). Why it qualifies: comparable open-source PDE package with a rich, small, fast example gallery (reaction–diffusion, pattern formation, stochastic PDEs), each a one-file Python script whose parameters are plain variables.

**Install on an Intel Mac.** The catch is numba: numba 0.63 (2025-12-08) dropped osx-64 binaries, and 0.62.x is the last release for Intel Macs; conda-forge's current numba (0.67.0) has no osx-64 build. So pin numba 0.62 and Python 3.13 or lower (0.62 does not support 3.14 **(unconfirmed)**).

1. ```bash
   mamba create -n ema-pypde -c conda-forge python=3.12 "numba=0.62" "py-pde=0.59.0" h5py
   ```
   If the solver can't find an osx-64 numba 0.62 on conda-forge **(unconfirmed that one exists)**, use `pip install "numba==0.62.*" "py-pde==0.59.0"` in a conda Python 3.12 env (0.62 shipped macOS x86_64 wheels **(unconfirmed)**).
2. `git clone --depth 1 https://github.com/zwicker-group/py-pde ~/src/py-pde` (for the examples; check out the tag matching 0.59.0).
3. Check: `python -c "import pde, numba; print(pde.__version__, numba.__version__)"` and `MPLBACKEND=Agg python ~/src/py-pde/examples/simple_pdes/simple.py`.

Known problems: examples call `PlotTracker` or `plot()`; run them with `MPLBACKEND=Agg` or strip plotting in the driver.

Sources: https://prefix.dev/channels/conda-forge/packages/py-pde ; https://prefix.dev/channels/conda-forge/packages/numba ; https://github.com/numba/numba/issues/10187 ; https://numba.readthedocs.io/en/stable/release/0.63.0-notes.html ; https://github.com/zwicker-group/py-pde

**Install on AWS (Ubuntu 24.04 EC2).**
1. Miniforge, then `mamba create -n ema-pypde -c conda-forge python=3.12 "py-pde=0.59.0" h5py` (latest numba is fine on linux-64; pin it to the version the Mac uses, 0.62, for identical numerics).
2. Or plain pip in a venv: `python3 -m venv ~/venvs/ema-pypde && ~/venvs/ema-pypde/bin/pip install "py-pde==0.59.0" "numba==0.62.*"`.
3. Docker fallback: no official image **(unconfirmed)**; use `condaforge/miniforge3` pinned by digest with step 1.
4. Check: as on the Mac. Instance: `c7i.xlarge`.

**Preparing the examples for EMA.** Parameters are Python variables at the top of each script (`a, b = 1, 3` and `d0, d1 = 1, 0.1` in the Brusselator); some are baked into expression strings with f-strings, which makes numba recompile for each new value. The driver should instead pass them through the `PDE(..., consts={...})` argument (documented in the advanced-usage manual) so the expression, and hence the compiled code, stays fixed. Remove the `PlotTracker`, shrink the grid (64×64 → 32×32) and `t_range`, fix `dt` (or use the adaptive solver with a tight tolerance), and seed the random initial condition (the examples use `ScalarField.random_normal`/`random_uniform`; seeding via an `rng` argument is **(unconfirmed)**, else `np.random.seed`). Print one scalar: a spatial average, a norm, or the standard deviation of a field (pattern amplitude). numba compile time dominates a short run (seconds per process); EMA starts a fresh process per run, so expect ~3–10 s/run **(estimate)** unless the driver uses `backend="numpy"` for tiny grids (whether `solve` accepts it is **(unconfirmed)**).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/simple_pdes/pde_brusselator_expression.py` (32×32, t_range 20) | Brusselator reaction–diffusion (Turing/Hopf patterns) | `a` 1 [0.5, 2]; `b` 3 [1.5, 4.5]; `d0` 1 [0.5, 2]; `d1` 0.1 [0.05, 0.5] (log) | spatial std of u at t_end (pattern amplitude) | a threshold: near zero below the instability boundary (Hopf at b = 1 + a² for the homogeneous state) and growing above it → kink/nonsmooth along a curve in (a, b); strong a×b interaction; d1 matters only through the Turing ratio | ~5 s (compile-dominated) **(estimate)** | command-line (env python + driver) | regex |
| `examples/simple_pdes/pde_heterogeneous_diffusion.py` | 1-D diffusion with diffusivity D0 + A·tanh(x), Dirichlet 0 | offset `D0` 1.01 → use [1.1, 3]; amplitude `A` 1 [0, 1]; final time `T` 100 → [10, 100] | remaining mass ∫c dx at T | smooth, monotone decreasing in D0 and T; A a weaker effect (mostly redistributes); near-additive on log scales | ~3 s **(estimate)** | command-line | regex |
| `examples/simple_pdes/boundary_conditions.py` | 2-D diffusion with Neumann flux on one side, Dirichlet sin(y/2) on the other, periodic in y | left flux 0.1 [0, 0.5]; right-boundary amplitude 1 [0, 2]; diffusivity 1 [0.5, 2] | mean of c at t = 10 | output exactly linear in the two boundary inputs (linear PDE) → `linear_coeffs` should find linear structure and zero interaction between them; diffusivity enters nonlinearly | ~3 s **(estimate)** | command-line | regex |

**Claude Code prompts.**

```text
Stage 1 (py-pde, read-only check). Check this machine for running py-pde 0.59.0 examples as EMA command-line models. Read-only: OS, uname -m, conda/mamba, python versions available, Docker, disk, existing env ema-pypde, ~/src/py-pde. On an Intel Mac, note that numba >= 0.63 has no osx-64 build, so the env must pin numba 0.62 and python <= 3.12. Don't install anything; don't read .env. Stop and report the recommended route; don't continue to the next stage.
```

```text
Stage 2a (py-pde, install on the Intel Mac). Create conda env ema-pypde: mamba create -n ema-pypde -c conda-forge python=3.12 "numba=0.62" "py-pde=0.59.0" h5py; if no osx-64 numba 0.62 resolves, stop and ask before trying pip wheels (numba==0.62.*) in that env. Never EMA's .venv, never read .env; ask before installing Miniforge. Shallow-clone https://github.com/zwicker-group/py-pde into ~/src/py-pde at the tag for 0.59.0. Check: python -c "import pde, numba; print(pde.__version__, numba.__version__)". Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 2b (py-pde, install on AWS Ubuntu 24.04; I'm on the instance). Create conda env ema-pypde (conda-forge python=3.12 "numba=0.62" "py-pde=0.59.0" h5py), matching the Mac's numba; ask before Miniforge or any sudo. Clone the examples at the 0.59.0 tag into ~/src/py-pde. Check the versions. If conda fails, propose (don't run) a condaforge/miniforge3 image pinned by digest. Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 3 (py-pde smoke test). In ema-pypde with MPLBACKEND=Agg, run ~/src/py-pde/examples/simple_pdes/simple.py and pde_brusselator_expression.py (temporarily with t_range=2 via a copy in the scratchpad, not editing the clone), timing each twice. Report wall times, how much is numba compilation (first vs second run in a fresh process), and any warnings. Stop and report; don't continue.
```

```text
Stage 4.1 (py-pde, prepare the Brusselator). Plan mode first. py-pde 0.59.0 in env ema-pypde. Create examples/pypde/brusselator/brusselator.py from examples/simple_pdes/pde_brusselator_expression.py: read a, b, d0, d1 from deck.txt, pass them through PDE(..., consts=...) so the expressions don't change between runs, UnitGrid([32, 32]), seeded random initial v (fixed seed), no PlotTracker, t_range 20, fixed dt 1e-3 (check stability), print "EMA_OUTPUT <std of u at t_end>". Template deck.template with $a $b $d0 $d1. Command [<absolute path of ema-pypde python>, "brusselator.py", "deck.txt"], env MPLBACKEND=Agg (and NUMBA_CACHE_DIR inside the model's run directory if needed). Follow docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/. Inputs: a 1 [0.5, 2], b 3 [1.5, 4.5], d0 1 [0.5, 2], d1 0.1 [0.05, 0.5] scale log. Then `.venv/bin/ema profile examples/pypde/brusselator/model.json -n 5`; report time per run and the split between import/compile and solve. Stop and report; don't continue.
```

```text
Stage 4.2 (py-pde, heterogeneous diffusion). Plan mode first. As stage 4.1, from examples/simple_pdes/pde_heterogeneous_diffusion.py: inputs D0 1.5 [1.1, 3], A 1 [0, 1], T 50 [10, 100]; diffusivity "D0 + A*tanh(x)" with D0 and A as consts; no storage/kymograph; print "EMA_OUTPUT <integral of c at T>" (field.integral). examples/pypde/hetero_diffusion/. Profile with -n 5 and report. Stop and report; don't continue.
```

```text
Stage 4.3 (py-pde, boundary conditions). Plan mode first. As stage 4.1, from examples/simple_pdes/boundary_conditions.py: inputs flux 0.1 [0, 0.5], amp 1 [0, 2], diffusivity 1 [0.5, 2]; bc x-left {"derivative": flux}, x-right {"value": "amp*sin(y/2)"} (check how py-pde accepts a parameter inside a BC expression; if it can't, format the value into the string and accept recompiles), y periodic; seeded initial field; t_range 10; print "EMA_OUTPUT <mean of c>". examples/pypde/boundary_conditions/. Profile with -n 5 and report. Stop and report; don't continue.
```

```text
Stage 5 (py-pde, first campaign). For examples/pypde/boundary_conditions/model.json write a campaign with repeat (2 x 3), linear_coeffs (small n), and morris (6 trajectories). Show the run count from `.venv/bin/ema estimate` and the estimated wall time; ask before running with -j 4. Expected: exactly linear in flux and amp, no interaction between them; diffusivity nonlinear. Then, if I agree, the same for the Brusselator with morris and a surface2d on (a, b) to see the instability boundary. Report. Stop and report.
```

```text
Stage 6 (py-pde troubleshooting). A py-pde 0.59.0 EMA model fails or is slow. Check read-only: numba import/LLVM errors on Intel Mac (numba > 0.62 installed; recreate with numba 0.62); every run recompiling (expressions contain the input values; move them to consts; set NUMBA_CACHE_DIR to a persistent writable directory in the spec's env); "matplotlib" or display errors (MPLBACKEND=Agg, remove trackers); NaN/Inf (explicit dt too large for the largest diffusivity; reduce dt or use the adaptive solver); replicate differences (unseeded random initial condition; numba parallel reductions: disable parallel). Report cause and fix; change nothing without my OK.
```

**Gotchas and sources.**
- MIT license; single-process by default (MPI optional via `py-pde[mpi]`; not needed).
- Intel Mac: numba is the constraint (0.62 last; Python ≤ 3.13); the conda-forge py-pde requires numba ≥ 0.59, so 0.62 satisfies it. Future py-pde releases may raise the numba floor above 0.62; pin py-pde 0.59.0.
- Randomness: several examples start from random fields and some are stochastic PDEs (`stochastic_simulation.py`, `multiplicative_noise.py`); fix the seed per run, or treat them as noisy models with EMA's `repeat` and `EMA_REPLICATE` as the seed.
- Explicit steppers go unstable when an input raises the diffusivity past the fixed-dt limit: a failure region that is an artifact of the solver setting, not the physics.
- Sources: https://github.com/zwicker-group/py-pde ; https://py-pde.readthedocs.io/en/latest/gallery.html ; https://py-pde.readthedocs.io/en/latest/manual/advanced_usage.html ; https://py-pde.readthedocs.io/en/latest/examples_gallery/simple_pdes/pde_brusselator_expression.html ; https://github.com/zwicker-group/py-pde/tree/master/examples/simple_pdes ; https://prefix.dev/channels/conda-forge/packages/py-pde ; https://prefix.dev/channels/conda-forge/packages/numba ; https://github.com/numba/numba/issues/10187

---

#### SfePy

**What it is.** Simple Finite Elements in Python: FE (and IGA) for coupled PDEs in 1-D/2-D/3-D, declarative problem-description files that are ordinary Python modules, run by `sfepy-run`. BSD-3-Clause. Latest **2026.2** (conda-forge; PyPI has 2026.2 as an sdist only, no wheels). Examples ship inside the package (`sfepy/examples/`) and are listed at https://sfepy.org/doc-devel/examples/gallery.html: about 100 examples in 11 sections (diffusion ~30, linear elasticity ~31, large deformation ~11, multi-physics ~7, Navier–Stokes 6, acoustics, homogenization, quantum, phononic, dg, misc). Why it qualifies: a comparable open-source FE package with one of the largest runnable example galleries, where each example is a small Python file with its material parameters as module variables, and many take `define()` arguments from the command line.

**Install on an Intel Mac.** The SfePy docs say it "is known to work on various flavors of recent Linux, Intel-based MacOS and Windows". Because PyPI has no wheels, use conda-forge (which lists macOS 64-bit builds; that 2026.2 is built for osx-64 is **(unconfirmed: check with `conda search -c conda-forge sfepy --platform osx-64`)**).

1. ```bash
   mamba create -n ema-sfepy -c conda-forge python=3.12 "sfepy=2026.2"
   ```
2. Check:
   ```bash
   conda activate ema-sfepy
   python -c "import sfepy; print(sfepy.__version__)"
   python -c "import sfepy, os; print(os.path.dirname(sfepy.__file__))"   # examples at <that>/examples
   sfepy-run $(python -c "import sfepy,os;print(os.path.dirname(sfepy.__file__))")/examples/diffusion/poisson_short_syntax.py -o /tmp/p
   ```
   `sfepy-test` runs the full test suite (slow; optional).

Known problems: whether the conda package includes the example meshes (`meshes/2d/its2D.mesh` etc.) under `sfepy/meshes` is **(unconfirmed)**; if not, clone https://github.com/sfepy/sfepy at the release tag for the data.

Sources: https://sfepy.org/doc-devel/installation.html ; https://prefix.dev/channels/conda-forge/packages/sfepy ; https://pypi.org/simple/sfepy/

**Install on AWS (Ubuntu 24.04 EC2).** No `python3-sfepy` package in noble (packages.ubuntu.com: "not available in this suite"), although later Ubuntu releases have a `sfepy-run` man page.
1. Miniforge, then the same `mamba create -n ema-sfepy -c conda-forge python=3.12 "sfepy=2026.2"`.
2. Docker fallback: the docs name `sfepy/sfepy-desktop` images (desktop-oriented; tags and architectures **(unconfirmed)**); a `condaforge/miniforge3` image pinned by digest with step 1 is simpler.
3. Check: as on the Mac. Instance: `c7i.xlarge`.

**Preparing the examples for EMA.** A problem-description file sets materials, regions, fields, BCs and solvers as module-level variables; some wrap everything in `def define(...)` whose arguments `sfepy-run -d "key : value, ..."` sets, and `-c "key : value"` overrides top-level items. Two workable patterns: (1) a template copy of the example file with `$young`-style placeholders (SfePy files contain no `$`, so no escaping) run by `sfepy-run`; (2) better, a driver script, run by the env's python, that calls `sfepy.applications.solve_pde(conf, define_args=...)` and then evaluates one scalar with `pb.evaluate('ev_...')` or reads a value at a vertex, printing `EMA_OUTPUT <value>`. Pattern 2 also keeps VTK writing out of the run (or send it into the run directory with `-o`). Mesh size is fixed by the mesh file, or by `refinement_level` where an example offers it (its2D_1 does); keep it at 0–1 for sub-second runs. Linear problems with a direct solver are deterministic to rounding.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `sfepy/examples/linear_elasticity/its2D_1.py` (and `its2D_2.py` for stresses) https://sfepy.org/doc-devel/examples/linear_elasticity-its2D_2.html | diametrically point-loaded disk (Brazilian test), linear elasticity | Young's modulus 2000 MPa [1000, 4000] (log); Poisson's ratio 0.4 [0.1, 0.45]; point load 1000 N [500, 2000] (log) | vertical displacement of the loaded top vertex (second model: horizontal stress at the centre) | exact power law: displacement ∝ load / E (exponents +1, −1 with `linear_coeffs(log_output=True)`); Poisson's ratio a weak smooth effect; centre stress independent of E | < 1 s **(estimate)** | command-line (env python + driver) | regex |
| `sfepy/examples/diffusion/poisson_parametric_study.py` | steady Poisson with Dirichlet ±2 and a source in a circular subdomain | subdomain diameter 0.25 [0.1, 0.6]; source strength 10 [1, 20]; conductivity c 1 [0.2, 5] (log) | mean temperature over the domain | linear in the source strength, ∝ 1/c for the source part; the diameter selects mesh cells, so the output moves in small steps as the circle crosses element boundaries → jumps "at this resolution" for nonsmooth/curve1d (a genuine test of the jump detector) | < 1 s **(estimate)** | command-line | regex |
| `sfepy/examples/diffusion/time_heat_equation_multi_material.py` | transient heat conduction in two materials | conductivity ratio [0.1, 10] (log); convection/boundary coefficient; final time | temperature at a probe point at the end | smooth, monotone; interaction between conductivity ratio and time; parameter names to be read from the file **(unconfirmed)** | ~1–3 s **(estimate)** | command-line | regex |

**Claude Code prompts.**

```text
Stage 1 (SfePy, read-only check). Check this machine for running SfePy 2026.2 examples as EMA command-line models. Read-only: OS, uname -m, conda/mamba, whether conda-forge has sfepy 2026.2 for this platform (conda search -c conda-forge sfepy --platform osx-64 or linux-64; read-only), Docker, disk, existing env ema-sfepy. Don't install; don't read .env. Recommend conda env ema-sfepy. Stop and report; don't continue.
```

```text
Stage 2a (SfePy, install on the Intel Mac). mamba create -n ema-sfepy -c conda-forge python=3.12 "sfepy=2026.2" (never EMA's .venv; never read .env; ask before installing Miniforge). Check: python -c "import sfepy; print(sfepy.__version__)", find the installed examples directory and whether meshes/2d/its2D.mesh exists; if the meshes are missing, ask before shallow-cloning https://github.com/sfepy/sfepy at the 2026.2 tag into ~/src/sfepy. Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 2b (SfePy, install on AWS Ubuntu 24.04; I'm on the instance). Noble has no python3-sfepy, so use conda: mamba create -n ema-sfepy -c conda-forge python=3.12 "sfepy=2026.2"; ask before Miniforge or sudo. Same checks as on the Mac. If conda fails, propose (don't run) a condaforge/miniforge3 Docker image pinned by digest. Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 3 (SfePy smoke test). In ema-sfepy, run sfepy-run on the installed examples/diffusion/poisson_short_syntax.py and examples/linear_elasticity/its2D_2.py with -o pointing into a scratch directory, timing each. Report wall times, output files, and the solver's log lines. Don't touch EMA. Stop and report; don't continue.
```

```text
Stage 4.1 (SfePy, prepare its2D). Plan mode first. SfePy 2026.2 in env ema-sfepy. Create examples/sfepy/its2d/ with a driver its2d.py that loads the installed examples/linear_elasticity/its2D_1.py as a ProblemConf (or copies it next to the driver as a template if overriding young/poisson/load isn't possible otherwise), sets young, poisson and the point load from deck.txt, solves with solve_pde, and prints "EMA_OUTPUT <vertical displacement of the top loaded vertex>"; no VTK output outside the run directory. Command [<absolute path of ema-sfepy python>, "its2d.py", "deck.txt"]; static file: the mesh if it isn't found from the package. Inputs: young 2000 [1000, 4000] scale log, poisson 0.4 [0.1, 0.45], load 1000 [500, 2000] scale log. Follow docs/applications.md, docs/guides/input_deck_model.md, examples/cantera/. Then `.venv/bin/ema profile examples/sfepy/its2d/model.json -n 5`. Stop and report; don't continue.
```

```text
Stage 4.2 (SfePy, prepare the Poisson subdomain study). Plan mode first. From examples/diffusion/poisson_parametric_study.py, make examples/sfepy/poisson_subdomain/ with a driver that sets the subdomain diameter, source value and conductivity from deck.txt (without the parametric hook: one problem per run), solves, and prints "EMA_OUTPUT <mean of t over Omega>" (use an ev_integrate term divided by the domain volume). Inputs: diameter 0.25 [0.1, 0.6], source 10 [1, 20], c 1 [0.2, 5] scale log. Profile with -n 5 and report. Stop and report; don't continue.
```

```text
Stage 4.3 (SfePy, prepare the multi-material heat example). Plan mode first. Read examples/diffusion/time_heat_equation_multi_material.py and propose 2-4 physical inputs (conductivities, boundary coefficient, final time) with ranges; after my OK, build examples/sfepy/heat_multi/ as in stage 4.1 with a probe temperature at the final time as "EMA_OUTPUT". Profile with -n 5. Stop and report; don't continue.
```

```text
Stage 5 (SfePy, first campaign). For examples/sfepy/its2d/model.json write a campaign: repeat (2 x 3), linear_coeffs with log_output true, and morris (6 trajectories). Show the run count from `.venv/bin/ema estimate` and ask before running with -j 4. Expected: power_law with exponents +1 (load) and -1 (young), poisson small. For poisson_subdomain, propose a curve1d on diameter (31 points) and ask. Report. Stop and report.
```

```text
Stage 6 (SfePy troubleshooting). An SfePy 2026.2 EMA model fails. Check read-only: mesh file not found (paths in the example are relative to the sfepy data dir; copy the mesh as a static file); output VTK written outside the run directory (set output_dir/-o to the run dir); override not applied (the variable is read at import time: patch the conf object, not the module, before solve_pde); solver "linear system not converged" (use ls.scipy_direct); tiny jumps in a geometric input (element membership of a region: expected, report as at this mesh resolution). Report cause and fix; change nothing without my OK.
```

**Gotchas and sources.**
- BSD-3-Clause. Serial by default (a PETSc-based parallel mode exists; not needed).
- Geometry-selecting inputs (region radius, subdomain size) act through element membership: piecewise-constant jumps at mesh resolution.
- Versions are calendar-based (2026.2); example file names and material keys can change between releases; pin the version.
- Sources: https://sfepy.org/doc-devel/installation.html ; https://sfepy.org/doc-devel/examples/gallery.html ; https://sfepy.org/doc-devel/users_guide.html ; https://manpages.ubuntu.com/manpages/resolute/man1/sfepy-run.1.html ; https://sfepy.org/doc-devel/src/sfepy/applications/pde_solver_app.html ; https://raw.githubusercontent.com/sfepy/sfepy/master/sfepy/examples/linear_elasticity/its2D_1.py ; https://raw.githubusercontent.com/sfepy/sfepy/master/sfepy/examples/diffusion/poisson_parametric_study.py ; https://prefix.dev/channels/conda-forge/packages/sfepy ; https://packages.ubuntu.com/noble/python3-sfepy

---

#### FreeFEM

**What it is.** A finite-element PDE solver with its own C++-like scripting language (`.edp` files), automatic mesh generation and adaptation, 2-D/3-D. LGPL-3.0. Latest release **v4.17** on GitHub (assets: Ubuntu 22.04/24.04/26.04 `.deb`, Windows, Docker tarballs for amd64/arm64; no macOS asset; release date shown as 2024-07-13 on the page, which looks inconsistent with a 26.04 `.deb` **(unconfirmed)**). Examples ship in the source tree: `examples/tutorial/` (80 `.edp` files), plus `examples/examples`, `3d`, `eigen`, `mpi`, `ffddm`, `hpddm`, `bem`, ... (hundreds of scripts), and 20 documented tutorials at https://doc.freefem.org/tutorials/index.html (heat exchanger, thermal conduction, elasticity, Stokes, Navier–Stokes, acoustics, fan blade, ...). Why it qualifies: a comparable open-source FE package with one of the largest example collections; a script takes command-line values through `getARGV` and prints scalars with `cout`, a natural fit for EMA's command-argument inputs.

**Install on an Intel Mac.** Three routes: (1) conda-forge `freefem` **4.13** (osx-64 and linux-64; last published about 2 years ago); (2) the official **4.15** Intel `.dmg` (`FreeFEM-v4.15-Intel-O.dmg`), the last release with an Intel macOS binary; (3) Docker Desktop with the official `freefem/freefem:v4.17-docker` (linux/amd64). Recommended: conda-forge 4.13 on both machines, since noble's apt package is also 4.13 and the tutorials used here are stable across 4.x.

1. ```bash
   mamba create -n ema-freefem -c conda-forge "freefem=4.13"
   conda activate ema-freefem
   which FreeFem++ FreeFem++-nw    # the -nw binary name in the conda build is (unconfirmed)
   ```
   Alternative (.dmg): download `FreeFEM-v4.15-Intel-O.dmg` from https://github.com/FreeFem/FreeFem-sources/releases/tag/v4.15, move `FreeFem++.app` to `/Applications`, clear quarantine if Gatekeeper blocks it, and call the `FreeFem++` executable inside the app bundle by absolute path (path inside the bundle **(unconfirmed)**).
2. Get the examples: `git clone --depth 1 --branch v4.13 https://github.com/FreeFem/FreeFem-sources ~/src/FreeFem-sources` (tag name **(unconfirmed)**; the examples are plain files, only `examples/tutorial` is needed).
3. Check: `FreeFem++ -nw -v 0 ~/src/FreeFem-sources/examples/tutorial/beam.edp` prints the maximum displacement without opening a window.

Sources: https://prefix.dev/channels/conda-forge/packages/freefem ; https://github.com/FreeFem/FreeFem-sources/releases/expanded_assets/v4.15 ; https://github.com/FreeFem/FreeFem-sources/releases/expanded_assets/v4.17 ; https://raw.githubusercontent.com/FreeFem/FreeFem-doc/master/source/introduction/installation.rst ; https://hub.docker.com/r/freefem/freefem/tags

**Install on AWS (Ubuntu 24.04 EC2).**
1. apt (4.13): `sudo apt-get install -y freefem++` (noble/universe `4.13+dfsg-1build5`, amd64). Or conda as on the Mac (same 4.13).
2. Newest (4.17): `curl -LO https://github.com/FreeFem/FreeFem-sources/releases/download/v4.17/FreeFEM-4.17-amd64-ubuntu24.04.deb` then `sudo apt-get install -y ./FreeFEM-4.17-amd64-ubuntu24.04.deb` (the docs' older wording is `dpkg -i` after `apt-get install libgsl-dev libhdf5-dev liblapack-dev libopenmpi-dev freeglut3-dev`).
3. Docker fallback: `docker pull freefem/freefem:v4.17-docker` (amd64 790 MB; arm64) and pin by digest.
4. Check: `FreeFem++ -nw -v 0 beam.edp`. Instance: `c7i.xlarge`.

Sources: https://packages.ubuntu.com/noble/freefem++ ; https://github.com/FreeFem/FreeFem-sources/releases/expanded_assets/v4.17 ; https://hub.docker.com/r/freefem/freefem/tags

**Preparing the examples for EMA.** Copy the `.edp` into the model directory and replace each physical constant with `getARGV`: `include "getARGV.idp"` then `real E = getARGV("-E", 21.5);`, so EMA passes inputs as command arguments (`["FreeFem++", "-nw", "-v", "0", "beam.edp", "-E", "$E", ...]`) and the `.edp` itself stays static (no `$` templating needed; FreeFEM code rarely contains `$`, but a template would need `$$` for any). Remove or guard `plot(...)` calls (with `-nw` they are ignored), and add one `cout << "EMA_OUTPUT " << value << endl;` at the end (e.g. `u[].max`, an `int2d(Th)(u)/area`, or a point value `u(x0, y0)`). Shrink meshes via the `square(nx, ny)`/`buildmesh(... (n))` counts; avoid `adaptmesh` in campaigns unless nonsmooth behaviour in inputs is wanted (adaptation makes the mesh depend on the inputs). Direct solvers (`solver=UMFPACK` or the default sparse LU) are deterministic.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/tutorial/beam.edp` https://github.com/FreeFem/FreeFem-sources/blob/master/examples/tutorial/beam.edp | 2-D linear elasticity, cantilever under self-weight (10×2, 20×5 mesh) | Young's modulus `E` 21.5 [10, 40] (log); Poisson's ratio `sigma` 0.29 [0.1, 0.45]; gravity `gravity` 0.05 [0.01, 0.1] (log) | maximum displacement magnitude (the script already computes it) | exact power law: ∝ gravity/E; sigma a small smooth effect; `linear_coeffs(log_output=True)` → exponents +1 and −1 | < 0.5 s | command-line | regex |
| `examples/tutorial/thermic-fast.edp` | transient heat conduction in two materials with a convective (Robin) boundary | high-conductivity value 1.8 → `k1` [0.5, 5] (log); base 0.2 → `k0` [0.05, 1] (log); `alpha` 0.25 [0.05, 1]; final time `T` 5 [1, 10] | mean temperature over the domain at T (or the temperature at a fixed point) | smooth, monotone in alpha and T (cooling), k interactions with alpha (Biot number), near-additive in logs | ~1 s | command-line | regex |
| `examples/tutorial/NS-BackwardStep.edp` | steady Navier–Stokes over a backward-facing step, Newton + Reynolds continuation + `adaptmesh` | final Reynolds number `Re` 150 [50, 500]; step height ratio (mesh heights [1.5, 1] → h/H) [0.3, 0.6] | reattachment length (the script computes it) | monotone increasing in Re; mesh adaptation depends on the inputs → small jumps (nonsmooth at mesh resolution); Newton failures at the high end possible | ~10–60 s per run with adaptation **(unconfirmed)**; drop adaptation for < 10 s | command-line | regex |

**Claude Code prompts.**

```text
Stage 1 (FreeFEM, read-only check). Check this machine for running FreeFEM tutorials (.edp) as EMA command-line models. Read-only: OS, uname -m, conda/mamba, whether FreeFem++ is already on PATH (and its version from FreeFem++ -h or -v), Homebrew, Docker, disk, env ema-freefem. Recommend: conda-forge freefem=4.13 in env ema-freefem (osx-64 and linux-64); alternatives: official 4.15 Intel .dmg (Mac), apt freefem++ 4.13 or the 4.17 ubuntu24.04 .deb (AWS), Docker freefem/freefem:v4.17-docker. Don't install; don't read .env. Stop and report; don't continue.
```

```text
Stage 2a (FreeFEM, install on the Intel Mac). mamba create -n ema-freefem -c conda-forge "freefem=4.13" (not EMA's .venv; never read .env; ask before Miniforge). Report the binaries it installed (FreeFem++, FreeFem++-nw, ...) and the path to getARGV.idp. Shallow-clone https://github.com/FreeFem/FreeFem-sources at the v4.13 tag into ~/src/FreeFem-sources (ask first; check the tag with git ls-remote). Check: FreeFem++ -nw -v 0 ~/src/FreeFem-sources/examples/tutorial/beam.edp. If conda fails, stop and ask before trying the 4.15 Intel .dmg. Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 2b (FreeFEM, install on AWS Ubuntu 24.04; I'm on the instance). Prefer the same version as the Mac: conda env ema-freefem with freefem=4.13; alternatively ask me before sudo apt-get install -y freefem++ (noble has 4.13). Clone the examples at v4.13 into ~/src/FreeFem-sources. Check beam.edp with -nw -v 0. If both fail, propose (don't run) docker pull freefem/freefem:v4.17-docker pinned by digest. Stop at the first error and report. Stop and report; don't continue.
```

```text
Stage 3 (FreeFEM smoke test). In ema-freefem, run FreeFem++ -nw -v 0 on examples/tutorial/beam.edp, thermic-fast.edp and Laplace.edp from ~/src/FreeFem-sources (in a scratch copy, since some write files), timing each. Report wall times, the printed scalars, and any files written. Don't touch EMA. Stop and report; don't continue.
```

```text
Stage 4.1 (FreeFEM, prepare beam.edp). Plan mode first. FreeFEM 4.13 in env ema-freefem. Copy examples/tutorial/beam.edp into examples/freefem/beam/; replace E, sigma and gravity with getARGV (include "getARGV.idp"; check it is found from the conda install, else copy it as a static file), keep the mesh, remove plots, and print "EMA_OUTPUT <max displacement>" once. model.json as a command-line model with inputs as command arguments (see examples/beam/model_args.json, docs/applications.md, docs/guides/input_deck_model.md): [<absolute path of the env's FreeFem++>, "-nw", "-v", "0", "beam.edp", "-E", "$E", "-sigma", "$sigma", "-gravity", "$gravity"]. Inputs: E 21.5 [10, 40] scale log, sigma 0.29 [0.1, 0.45], gravity 0.05 [0.01, 0.1] scale log. Regex "EMA_OUTPUT (\S+)" on stdout. Then `.venv/bin/ema profile examples/freefem/beam/model.json -n 5`. Stop and report; don't continue.
```

```text
Stage 4.2 (FreeFEM, prepare thermic-fast.edp). Plan mode first. As 4.1 from examples/tutorial/thermic-fast.edp in examples/freefem/thermic/: getARGV for k1 (1.8), k0 (0.2), alpha (0.25), T (5); keep dt 0.1; no plots or file writes outside the run dir; print "EMA_OUTPUT <int2d(Th)(u)/area at T>". Inputs k1 1.8 [0.5, 5] log, k0 0.2 [0.05, 1] log, alpha 0.25 [0.05, 1], T 5 [1, 10]. Profile -n 5 and report. Stop and report; don't continue.
```

```text
Stage 4.3 (FreeFEM, prepare NS-BackwardStep.edp). Plan mode first, and first time one unmodified run. From examples/tutorial/NS-BackwardStep.edp in examples/freefem/backstep/: getARGV for the final Reynolds number (continuation list truncated at it) and the step height ratio; print "EMA_OUTPUT <reattachment length>" (one of the four variants the script computes; tell me which). Make two model files: model_adapt.json (with adaptmesh, as published) and model_fixed.json (fixed mesh, no adaptation) so a campaign can compare their smoothness. Inputs Re 150 [50, 500], ratio [0.3, 0.6]. Profile each with -n 3; if a run takes over 60 s, stop and propose a coarser mesh. Stop and report; don't continue.
```

```text
Stage 5 (FreeFEM, first campaign). For examples/freefem/beam/model.json: repeat (2 x 3), linear_coeffs with log_output true, morris (6 trajectories). Show the run count from `.venv/bin/ema estimate` and ask before running with -j 4. Expected: power_law, exponents about -1 for E and +1 for gravity, sigma small. If I agree, then curve1d on Re (15 points) for both backstep models, to compare adaptive vs fixed meshes (expect small jumps with adaptmesh). Report. Stop and report.
```

```text
Stage 6 (FreeFEM troubleshooting). A FreeFEM EMA model fails. Check read-only in the run directory: "include file not found getARGV.idp" (copy it as a static file or add the idp path with -I **check the flag**); a window or X11 error (missing -nw, or use FreeFem++-nw); no EMA_OUTPUT line (verbosity or an early exit(); grep stdout.txt); getARGV not taking the value (name mismatch; options are read as strings then converted); Newton divergence in NS-BackwardStep (lower Re step in the continuation); run-to-run differences (adaptmesh or iterative solver; use a fixed mesh and direct solver); macOS Gatekeeper blocking a .dmg binary. Report cause and fix; change nothing without my OK.
```

**Gotchas and sources.**
- LGPL-3.0 (the scripts you write are yours). The conda and apt builds are serial `FreeFem++`; `ff-mpirun` (MPI) isn't needed at laptop size.
- Intel Mac: no 4.16/4.17 macOS assets; 4.15 is the last Intel `.dmg`; conda-forge's 4.13 is two years old but runs the tutorials.
- `adaptmesh` makes the mesh depend on the inputs: nonsmooth outputs at mesh resolution, and non-repeatable results if metrics tie. Use fixed meshes unless that is the point.
- `-v 0` quiets FreeFEM; `-nw` avoids graphics (from the docs' option list; `-ne` to suppress echo of the script is **(unconfirmed)**).
- Sources: https://github.com/FreeFem/FreeFem-sources/releases ; https://github.com/FreeFem/FreeFem-sources/tree/master/examples ; https://github.com/FreeFem/FreeFem-sources/tree/master/examples/tutorial ; https://github.com/FreeFem/FreeFem-sources/blob/master/idp/getARGV.idp ; https://doc.freefem.org/tutorials/index.html ; https://doc.freefem.org/introduction/installation.html ; https://raw.githubusercontent.com/FreeFem/FreeFem-doc/master/source/introduction/installation.rst ; https://prefix.dev/channels/conda-forge/packages/freefem ; https://packages.ubuntu.com/noble/freefem++ ; https://hub.docker.com/r/freefem/freefem/tags

---

#### Considered, not included

(From my knowledge of these projects, not verified today unless a URL is given; all reasons are **(unconfirmed)** beyond what is stated above.)
- **preCICE tutorials**: coupling library; every tutorial needs two or more solvers (OpenFOAM, CalculiX, FEniCS...) and a coupled run is minutes, not seconds.
- **CalculiX**: good input-deck fit (`.inp`, `ccx` in apt, fast) but few curated examples of its own (test suite rather than tutorials); a strong later candidate for structures.
- **Code_Aster**: large, test-case collection is rich but installation (Salome-Meca, containers) is heavy and runs are slow; French-language docs.
- **PyLith**: crustal deformation, good examples, but binary distribution is Linux/macOS tarballs with a narrow focus and multi-minute runs.
- **ExaHyPE**: hyperbolic PDE engine for HPC; code generation and source builds, not laptop-scale.
- **lethe**: CFD/DEM on deal.II; needs deal.II built with Trilinos/p4est, runs are heavy.
- **Oasis**: FEniCS-legacy Navier–Stokes solver; depends on legacy FEniCS (dolfin), whose conda-forge support is fading; FEniCSx is covered.
- **GetFEM**: FE library with Python interface and examples, but conda-forge/macOS availability is uncertain and SfePy/FreeFEM cover the same ground more easily.
- **porepy**: porous-media and fractured-media simulations in Python; examples are fewer and run times longer; install by pip from source; a candidate for a later round.
- **Chaste**: cardiac/cancer modelling; Docker-based or source builds, long runs, C++ test-driven "user projects".
- **PETSc's TAO / DMPlex examples**: covered inside the PETSc section (same install).
- **libMesh and Trilinos** were listed here at first; both now have sections in 4.5 (libMesh through INL's prebuilt conda package, Trilinos through conda-forge 16.2.0).


### 4.5 More finite-element libraries, solvers, and differential equations: libMesh, hIPPYlib, Trilinos, SLEPc, DifferentialEquations.jl

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions and platform claims come from the URLs cited, most of them read today through the GitHub, anaconda.org and Docker Hub APIs. **(unconfirmed)** marks what I could not verify. Every run time is an *(estimate)* from the example's size and must be measured with `ema profile`.

Notes common to the group:
- **Two of the five build on the PETSc section (4.4).** SLEPc goes into the same `ema-petsc` conda env, and the source build of libMesh (the fallback route) links against that env's PETSc. Do 4.4's PETSc stages first.
- **conda-forge on osx-64, as of today.** `slepc`/`slepc4py` 3.25.2 (osx-64 builds uploaded 2026-09-23, requiring `petsc >=3.25.5,<3.26`); `trilinos` and `pytrilinos` 16.2.0 (osx-64 builds 2026-09-03); legacy `fenics` 2019.1.0 (osx-64 builds rebuilt 2026-09-09 for Python 3.11–3.14); `julia` 1.13.0. There is no `libmesh` package on conda-forge, but INL's MOOSE channel has `moose-libmesh` for osx-64 (it needs macOS ≥ 13.3).
- **Upstream is ahead of conda-forge for Trilinos.** Trilinos 17.2.1 (2026-08-31) is current, but conda-forge still ships 16.2.0, the last line with the legacy Epetra-based `PyTrilinos`. Trilinos 17 keeps only `PyTrilinos2`.
- **Julia is a new kind of command-line model for EMA.** Each run starts a Julia process, and loading and compiling DifferentialEquations.jl costs seconds per run. The DifferentialEquations.jl section says how to keep that down (a pinned project, a sysimage), and what a persistent process would cost EMA.
- **AWS instance.** Every example is serial and small, so a `c7i.xlarge` (4 vCPU, 8 GB) is enough for `-j 4`, and a `c7i.2xlarge` for `-j 8`. The libMesh source build and a Julia sysimage each need about 8 GB of RAM while they build *(estimate)*. Add 40 GB of gp3 for the conda envs, the Julia depot, and the source trees.
- **Threads.** Set `OMP_NUM_THREADS=1` in every spec's `env`. Julia models also need `JULIA_NUM_THREADS=1` and `OPENBLAS_NUM_THREADS=1`. Let EMA's `-j N` provide the parallelism.

---

#### libMesh

**What it is.** A C++ finite-element library (University of Texas / INL; the mesh and assembly layer under MOOSE), with adaptive mesh refinement, reduced-basis methods, adjoint-based error estimation, and PETSc/SLEPc solvers. License LGPL-2.1. Current stable release **v1.8.4 (2025-10-06)**. v1.7.9 (2026-02-06) is a maintenance release of the 1.7 line, adding support for newer PETSc, and v1.9.0-rc2 (2025-10-06) is a pre-release. The examples are in `examples/` of https://github.com/libMesh/libmesh, with pages at https://libmesh.github.io/examples.html: **75 examples** in 15 groups at the v1.8.4 tag (introduction, adaptivity, adjoints, eigenproblems, fem_system, miscellaneous, optimization, reduced_basis, subdomains, systems_of_equations, transient, vector_fe, and others). Most read a GetPot `.in` file, and `infile.parse_command_line(argc, argv)` lets `key=value` arguments on the command line override it, so EMA can pass inputs as command arguments with no template.
Fit: good once built. The examples are C++ programs that you compile against an installed libMesh. The `reduced_basis` examples are unusual for EMA: an offline stage builds a reduced-basis model once, and each online run then evaluates it in milliseconds with a rigorous error bound. It is a surrogate the package certifies itself, and EMA can check it independently (see the table).

**Install on an Intel Mac.** There is no conda-forge `libmesh`, and Homebrew is Tier 3 on Intel. Two routes:
- **Route A (recommended): INL's prebuilt `moose-libmesh`.** The MOOSE conda channel has `moose-libmesh 2026.08.18_0772c3d` for osx-64 (mpich build, about 34 MB). It depends on `moose-petsc 3.25.4` and needs `__osx >=13.3`, so macOS 13.3 or later. The version names MOOSE commit `0772c3d` (2026-08-18), whose `libmesh` submodule is libMesh commit `ab36c007` (2026-06-05). That is a master snapshot, not a release, so take the examples from that commit.
- **Route B (fallback): build v1.8.4 from source** against the `ema-petsc` env from section 4.4, with the conda compilers. It is a long autotools build, about 30–60 minutes with `-j4` *(estimate)*. Whether 1.8.4 (October 2025) builds against PETSc 3.25.5 is **(unconfirmed)**. v1.7.9's release note mentions compatibility with newer PETSc versions for 1.7.x, so 1.8.x may need its next patch release.

1. Route A: install Miniforge (see 4.1), then create the env from INL's channel:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-libmesh -c https://conda.software.inl.gov/public -c conda-forge \
       "moose-libmesh=2026.08.18_0772c3d" "moose-petsc=3.25.4"
   ```
2. Get the examples from the matching libMesh commit:
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone https://github.com/libMesh/libmesh.git libmesh-src
   cd libmesh-src && git checkout ab36c007ae608290e097bdfbc2766a46d8192b70
   ```
   (The examples don't need the submodules. Don't run `git submodule update`.)
3. Find `libmesh-config`. The package installs libMesh under the env, and MOOSE's activation scripts set `LIBMESH_DIR` **(unconfirmed where; try `$CONDA_PREFIX/libmesh/bin/libmesh-config` and `find $CONDA_PREFIX -name libmesh-config`)**.
4. Compile one example outside the libMesh build system:
   ```bash
   conda activate ema-libmesh
   LMC=$(find "$CONDA_PREFIX" -name libmesh-config -type f | head -1)
   cd ~/src/libmesh-src/examples/introduction/introduction_ex4
   $($LMC --cxx) -o ex4 introduction_ex4.C $($LMC --cppflags --cxxflags --include) $($LMC --ldflags --libs)
   ```
   (`libmesh-config` supports `--cxx`, `--cppflags`, `--cxxflags`, `--include` and `--libs`; `--ldflags` is **(unconfirmed)**. If it fails, drop it.)
5. Check: `./ex4 -d 2 -n 15` should solve a 2-D Poisson problem and print the mesh and system info.

Route B, in outline (**unconfirmed** against PETSc 3.25):
```bash
conda activate ema-petsc     # from section 4.4; add: mamba install -n ema-petsc -c conda-forge make autoconf automake
curl -LO https://github.com/libMesh/libmesh/releases/download/v1.8.4/libmesh-1.8.4.tar.gz
tar xf libmesh-1.8.4.tar.gz && mkdir libmesh-1.8.4/build && cd libmesh-1.8.4/build
../configure --prefix=$HOME/opt/libmesh-1.8.4 --with-methods=opt PETSC_DIR=$CONDA_PREFIX SLEPC_DIR=$CONDA_PREFIX CC=mpicc CXX=mpicxx
make -j4 && make install
```
Use the release tarball (`libmesh-1.8.4.tar.gz`), not GitHub's "Source code" archive, which the release note says not to use. With Route B the examples come from the same tarball.

Known problems: Route A's `__osx >=13.3` refuses older macOS. MOOSE maintainers say Intel Mac support ends on Apple's timeline, so the osx-64 builds may stop (MOOSE discussion #32539, cited in 4.2). The conda clang needs the Xcode Command Line Tools SDK.
Sources: https://github.com/libMesh/libmesh/releases, https://libmesh.github.io/installation.html, https://libmesh.github.io/examples.html, https://conda.software.inl.gov/public/osx-64/, https://conda.software.inl.gov/public/linux-64/, https://github.com/idaholab/moose/commit/0772c3d45eac8019a76f6dcdb8683231fe354c57, https://api.anaconda.org/package/conda-forge/libmesh (not found), https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/libmesh/package.py

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same `moose-libmesh` from INL's channel. linux-64 has `2026.08.18_0772c3d` in mpich and openmpi builds, so choose mpich to match the Mac. Then use the same commands as on the Mac.
2. Fallback: Spack, `spack install libmesh@1.8.4 +petsc +slepc ~mpi` (Spack lists 1.8.4, and `petsc` and `slepc` are variants), or Route B against the `ema-petsc` env.
3. Docker fallback: `idaholab/moose` (see 4.2) contains a libMesh build for MOOSE **(unconfirmed where `libmesh-config` is in the image)**. Pin it by digest, and compile the examples inside the container into the model directory.
4. apt: Ubuntu 24.04 has no `libmesh-dev` package (packages.ubuntu.com has none for noble).
5. Check: compile and run `introduction_ex4` as on the Mac.
Sources: https://conda.software.inl.gov/public/linux-64/, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/libmesh/package.py, https://packages.ubuntu.com/noble/libmesh-dev

**Preparing the examples for EMA.** The recipe:
- Compile each example into its model directory with `libmesh-config`, so the version hash covers the binary. Copy the example's `.in` file there as a static file.
- Pass inputs as GetPot overrides on the command line, `"online_x_vel=$xvel"`. `parse_command_line` gives command-line values priority over the `.in` file (from the examples' source). A value like `Reynolds=$Re` fits in one argument, since EMA's templates substitute inside an argument.
- Most examples print only diagnostics, so add one `libMesh::out << "EMA_OUTPUT " << std::setprecision(12) << value << std::endl;` after the solve, and parse it with a regex.
- Run serially (no `mpiexec`). Use a direct solver where the example allows (`-pc_type lu`, which libMesh passes to PETSc), and turn off file output (`output_gmv = false` etc.).
- Adaptive examples (`adjoints`, `adaptivity`) make outputs piecewise constant in any input that changes which elements get refined. That is a real feature, and EMA should see it as jumps.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/reduced_basis/reduced_basis_ex1` (https://github.com/libMesh/libmesh/tree/v1.8.4/examples/reduced_basis/reduced_basis_ex1) | steady 2-D convection–diffusion on a 50×50 truth mesh. A reduced basis (Nmax 20, greedy on 100 training points) is built offline once, and each online run evaluates it | `online_x_vel` −2 [−2, 2]; `online_y_vel` 0.79 [−2, 2] (the training box is [−2, 2]², so stay inside it); `online_N` fixed at 20 | `output 1, value = ...` (the average of the solution over a subregion). A second model reads `bound = ...`, the certified error bound | smooth (the parameters enter the operator affinely, so the output is a smooth rational-like function): `surface2d` should show no kinks, and `fourier` should fit well. The bound should be tiny and flat inside the training box. Outside it EMA isn't asked to go. A `surrogate_check` of EMA's own is a cross-check on the certified bound | < 0.5 s online; the offline stage runs once, about 1–5 min *(estimate)* | command-line (a wrapper script in the model dir links the offline data, then runs the binary) | regex `output 1, value = (\S+),` on stdout |
| `examples/adjoints/adjoints_ex1` (https://github.com/libMesh/libmesh/tree/v1.8.4/examples/adjoints/adjoints_ex1) | Laplace on an L-shaped domain, second-order Lagrange elements, adjoint-residual error indicator, `max_adaptivesteps` 6 of adaptive refinement, two QoIs with exact values in `l-shaped.in` | numerical settings, not physics: `refine_fraction` 0.05 [0.02, 0.3]; `coarserefinements` 3 fixed; `max_adaptivesteps` 6 fixed (lower it to 4 for speed); `relative_residual_tolerance` 1e-7 [1e-10, 1e-5] (log) | the relative error in QoI 0 (the program prints `The relative error in QoI 0 is ...`) | piecewise constant in `refine_fraction` (element counts change in steps), so `nonsmooth` and `curve1d` should report jumps "at this resolution". Decreasing overall, and the tolerance input is negligible below about 1e-8. This is a study of the method, not the physics | 5–30 s *(estimate)* | command-line | regex `relative error in QoI 0 is (\S+)` |
| `examples/fem_system/fem_system_ex1` (https://github.com/libMesh/libmesh/tree/v1.8.4/examples/fem_system/fem_system_ex1) | incompressible Navier–Stokes, lid-driven cavity (`application = 0`), `coarsegridsize` 20, 15 transient steps of 0.005 | `Reynolds` (in `navier.in`) 1 [0.1, 100] (log); `deltat` 0.005 fixed; set `transient = false`, `n_timesteps = 1` for the steady problem (the example's own `run.sh` uses that combination) | kinetic energy or velocity L2 norm, printed by an added line after the solve (`system.calculate_norm(...)`) | smooth and monotone in `Reynolds` at low Re; Newton failures possible at the top of the range (failed runs); the discontinuous lid corner makes the output mesh-sensitive, so keep the mesh fixed | 5–20 s *(estimate)* | command-line; `navier.in` is a second GetPot file, so render it from a template (`Reynolds = $Re`) instead of the command line (**unconfirmed** whether `navier.in` reads command-line overrides) | regex `EMA_OUTPUT (\S+)` |

For `reduced_basis_ex1`: run the offline stage once by hand (`./reduced_basis_ex1 -online_mode 0`) in the model directory. The online stage reads `rb_eval.bin` and a legacy `offline_data` directory from the working directory (`legacy_read_offline_data_from_files()`). EMA copies static files flat and can't copy a directory, so a small wrapper script in the model directory symlinks `$EMA_BASE_DIR/offline_data` into the run directory and then runs the binary with `-online_mode 1`. The version hash covers the wrapper but not the offline data, so record the offline settings in the description.

**Claude Code prompts.**

```text
Stage 1 (libMesh, read-only check). I want to onboard libMesh examples into EMA as command-line models. Read-only: report OS and version (sw_vers; route A needs macOS >= 13.3), uname -m, conda/mamba (Miniforge) and its version, any env named ema-libmesh or ema-petsc (section 4.4 of docs/brainstorms/pde_packages_onboarding.md), whether the INL channel https://conda.software.inl.gov/public is reachable (curl -sI), Homebrew (note only, don't use it on Intel), Docker, compilers (cc --version, xcode-select -p), git, and free disk space. Don't install anything, and don't read .env. Recommend a route: A = INL's moose-libmesh=2026.08.18_0772c3d (osx-64 and linux-64) in a new env ema-libmesh, with examples from libMesh commit ab36c007; B = build libMesh 1.8.4 from the release tarball against the ema-petsc env (compatibility with PETSc 3.25 unconfirmed). Stop and report; don't continue to the next stage.
```

```text
Stage 2a (libMesh, install on the Intel Mac). Route A. Never install into EMA's .venv, and never read .env. Ask before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Steps: (1) mamba create -n ema-libmesh -c https://conda.software.inl.gov/public -c conda-forge "moose-libmesh=2026.08.18_0772c3d" "moose-petsc=3.25.4"; (2) git clone https://github.com/libMesh/libmesh.git ~/src/libmesh-src and git checkout ab36c007ae608290e097bdfbc2766a46d8192b70 (no submodules); (3) find libmesh-config inside the env and report its path and `libmesh-config --version`; (4) compile examples/introduction/introduction_ex4/introduction_ex4.C with `$(libmesh-config --cxx)` and the flags from `--cppflags --cxxflags --include --libs` (add --ldflags if it exists); (5) run ./ex4 -d 2 -n 15 and report the last lines. If step 1 fails on the macOS version, stop and report; don't try route B without asking me. Stop at the first error and report the command and its output. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (libMesh, install on AWS Ubuntu 24.04 x86_64; I'm ssh'd in). Route A as on the Mac: Miniforge (ask first), then mamba create -n ema-libmesh -c https://conda.software.inl.gov/public -c conda-forge "moose-libmesh=2026.08.18_0772c3d" "moose-petsc=3.25.4" (choose the mpich build). Clone libMesh at ab36c007ae608290e097bdfbc2766a46d8192b70 into ~/src/libmesh-src. Compile and run introduction_ex4 as a check. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. If conda fails, propose (don't run) spack install libmesh@1.8.4 +petsc +slepc, or the idaholab/moose Docker image pinned by digest. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (libMesh smoke test). In the ema-libmesh env, compile examples/reduced_basis/reduced_basis_ex1 and examples/adjoints/adjoints_ex1 from ~/src/libmesh-src into a scratch directory outside the EMA repo (copy each example's .in, .xda and .h/.C files there). Run reduced_basis_ex1 -online_mode 0 (offline; time it), then -online_mode 1 (online; time it) and report the four "output N, value = ..., bound = ..." lines. Run adjoints_ex1 with output_gmv=false on the command line, and report the QoI error lines and the wall time. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (libMesh, prepare reduced_basis_ex1 for EMA). Plan mode first; show me the plan before writing anything. Read docs/applications.md, docs/guides/input_deck_model.md, examples/beam/model_args.json and examples/cantera/. Create examples/libmesh/rb_convdiff/: compile reduced_basis_ex1 there with libmesh-config (ema-libmesh env); copy reduced_basis_ex1.in as a static file; run the offline stage once there (-online_mode 0) so rb_eval.bin and offline_data/ exist; write a small wrapper script (run_online.py or a shell script, run by an absolute interpreter path) that symlinks $EMA_BASE_DIR/offline_data and rb_eval.bin into the run directory and execs the binary with -online_mode 1 and the rest of its arguments. model.json: command-line model, command [<wrapper>, "online_x_vel=$xvel", "online_y_vel=$yvel"], inputs xvel -2 [-2, 2], yvel 0.79 [-2, 2], output regex "output 1, value = (\S+)," on stdout, env OMP_NUM_THREADS=1, timeout_s 60. Put the offline settings (n_elem 50, Nmax 20, 100 training points) and the libMesh commit in the description. Check by hand that (-2, 0.79) reproduces stage 3's output 1. Write a second model_bound.json that reads "bound = (\S+)" for output 1. Then run `.venv/bin/ema profile examples/libmesh/rb_convdiff/model.json -n 5` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (libMesh, prepare adjoints_ex1). Plan mode first. Create examples/libmesh/adjoints_lshape/: compile adjoints_ex1 there (all its .C files) with libmesh-config; static files general.in, l-shaped.in, lshaped.xda. Command-line model: command ["adjoints_ex1", "refine_fraction=$refine_fraction", "relative_residual_tolerance=$rtol", "max_adaptivesteps=4", "output_gmv=false"]; inputs refine_fraction 0.05 [0.02, 0.3], rtol 1e-7 [1e-10, 1e-5] with scale log. Output: regex "relative error in QoI 0 is (\S+)" on stdout (check the exact printed text in the source first, and match the last occurrence if it prints once per adaptive step; if a regex can't pick the last one, use an isolated python parser). env OMP_NUM_THREADS=1, timeout_s 180. Check by hand that the nominal run prints a small relative error. Then `.venv/bin/ema profile examples/libmesh/adjoints_lshape/model.json -n 5` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.3 (libMesh, prepare fem_system_ex1 lid-driven cavity). Plan mode first. Create examples/libmesh/cavity/: copy fem_system_ex1's sources, add one line after the solve that prints "EMA_OUTPUT %.12e" of the velocity L2 norm (system.calculate_norm on the u and v variables, or the kinetic energy; say which), and note the edit in a comment. Compile with libmesh-config. fem_system_ex1.in is a static file with transient = false, n_timesteps = 1, and every output format off; navier.in becomes the template navier.template with "Reynolds = $Re" (check it for literal $ and escape it as $$). Inputs: Re 1 [0.1, 100] with scale log. Output regex "EMA_OUTPUT (\S+)". env OMP_NUM_THREADS=1, timeout_s 120. Check that Re = 1 converges and report the value; try Re = 100 once and report whether Newton converges. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 (libMesh, first campaign). For examples/libmesh/rb_convdiff/model.json, write campaign.json with repeat (n_points 2, replicates 2), surface2d on xvel and yvel (a 15 x 15 grid), sobol (n_base 256), and surrogate_check (kind auto). Run `.venv/bin/ema estimate` and show me the run count and the time; ask me before `ema run`. Then report: whether repeats are identical; any kinks or jumps from surface2d (expected: none, the output is smooth); the Sobol indices and the interaction share; whether surrogate_check meets its target. Compare the spread of the output with the RB error bound from model_bound.json at a few points. Suggest (don't run) a nonsmooth campaign on examples/libmesh/adjoints_lshape (expected: jumps in refine_fraction). Stop and report.
```

```text
Stage 6 (libMesh troubleshooting). An EMA libMesh model in examples/libmesh/<example> fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt and ema_run.json, and by running the binary by hand in a copy of the run directory: (a) "Library not loaded" / "cannot open shared object file": the binary can't find the env's libmesh or libpetsc; propose an rpath at link time, not DYLD_LIBRARY_PATH; (b) "ERROR: Could not open ... .in" or a missing mesh (.xda): a static file is missing from model.json; (c) the RB online stage can't find offline_data or rb_eval.bin: the wrapper didn't link them; (d) PETSc "unused option" warnings or GetPot values that don't take effect: a misspelled key, or a key read from a second .in file; (e) Newton divergence in fem_system_ex1 at high Reynolds: expected, a failed run; (f) jumps in adaptive examples: expected, not a bug; (g) MPI start-up hangs: run without mpiexec. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License LGPL-2.1: fine for use as an external program. INL's conda packages carry their own licenses (LGPL for MOOSE).
- Parallelism: run serially, with `OMP_NUM_THREADS=1`. The `moose-libmesh` build uses `llvm-openmp`, so set the variable in every spec's `env`.
- Determinism: direct solves are repeatable. Iterative solves and adaptive refinement make outputs rough or piecewise constant, so treat adaptivity inputs as numerical settings and expect jumps. Set `-pc_type lu` and tight tolerances where the example uses Krylov solvers.
- The RB example is itself a surrogate. EMA analyses the reduced model, so a claim about the truth finite-element model needs the error bound (the second model) or a few truth solves for comparison.
- Version pitfalls: Route A tracks libMesh master (commit `ab36c007`), not a release, so use the examples from that commit. The API changes between releases, and examples from v1.8.4 may not compile against it. Route A needs macOS ≥ 13.3.
- Run time: set by the mesh (`n_elem`, `coarsegridsize`, `coarserefinements`) and the number of adaptive steps. Keep them fixed and small.
- Sources: https://github.com/libMesh/libmesh, https://github.com/libMesh/libmesh/releases, https://github.com/libMesh/libmesh/releases/tag/v1.8.4, https://libmesh.github.io/examples.html, https://libmesh.github.io/installation.html, https://github.com/libMesh/libmesh/tree/v1.8.4/examples/reduced_basis/reduced_basis_ex1, https://github.com/libMesh/libmesh/tree/v1.8.4/examples/adjoints/adjoints_ex1, https://github.com/libMesh/libmesh/tree/v1.8.4/examples/fem_system/fem_system_ex1, https://conda.software.inl.gov/public/osx-64/, https://conda.software.inl.gov/public/linux-64/, https://github.com/idaholab/moose/commit/0772c3d45eac8019a76f6dcdb8683231fe354c57, https://github.com/idaholab/moose/discussions/32539, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/libmesh/package.py, https://packages.ubuntu.com/noble/libmesh-dev

---

#### hIPPYlib

**What it is.** Inverse Problem PYthon library: deterministic and Bayesian inverse problems governed by PDEs, with inexact Newton–CG for the MAP point, low-rank Laplace approximations of the posterior (randomized double-pass eigensolvers), prior samples from BiLaplacian priors, and MCMC. Pure Python on top of **legacy FEniCS (DOLFIN) 2019.1**. License GPL-2.0 (the `COPYRIGHT` file at the 3.2.0 tag: "GNU General Public License ... version 2.0 dated June 1991"). Current release **3.2.0 (GitHub 2025-12-12, PyPI 2025-12-18)**. The INSTALL file at the tag still says "hIPPYlib depends on FEniCS version 2019.1". Examples: `applications/` in https://github.com/hippylib/hippylib (`poisson/` with `model_subsurf.py`, `model_subsurf_multNoise.py` and `model_continuous_obs.py`; `ad_diff/model_ad_diff.py`; `forward_uq/`; `mcmc/`; `time_dependent/`), plus 7 tutorial notebooks in `tutorial/` (`1_FEniCS101` … `7_GaussianPriors`). About a dozen in all.
**The FEniCSx port.** `hippylib/hippylibx` (https://github.com/hippylib/hippylibx) is "the next version of hIPPYlib powered by dolfinx", but its README says it targets DOLFINx 0.8.0, three minor versions behind today's 0.11.0 (section 4.1). It has no GitHub release and no PyPI package, and its last push was 2026-05-15. Don't onboard it yet.
**What still works on an Intel Mac.** Legacy FEniCS is frozen upstream, but conda-forge still rebuilds it: `fenics-dolfin 2019.1.0` has osx-64 builds uploaded 2026-09-09 for Python 3.11–3.14 (build 66, mpich, with `petsc4py`, `slepc4py` and a clang C++ compiler for the JIT among its dependencies). So a native conda env works today. The risk is that these rebuilds stop, so pin the env and export it.
Fit: good, and unusual. The EMA inputs are the analyst's modelling choices (prior hyperparameters, noise level), and the outputs are summaries of the inverse problem: the misfit at the MAP point, the KL distance from prior to posterior, the posterior variance trace, and the number of data-informed directions. The truth and its synthetic data must be held fixed across runs, which needs a small edit (below).

**Install on an Intel Mac.** Route: conda-forge legacy FEniCS plus `pip install hippylib==3.2.0` in the same env (not EMA's `.venv`).
1. Install Miniforge if needed (see 4.1).
2. Create the env with the versions pinned:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-hippylib -c conda-forge python=3.12 fenics=2019.1.0 mpich matplotlib scipy
   ~/miniforge3/envs/ema-hippylib/bin/python -m pip install "hippylib==3.2.0"
   ```
   (`hippylib` 3.2.0 on PyPI requires only `mpi4py`, `numpy`, `matplotlib` and `scipy`. It doesn't pin FEniCS, which comes from conda.)
3. Get the applications from the tag (the pip package doesn't include them):
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -L -o hippylib-3.2.0.tar.gz https://github.com/hippylib/hippylib/archive/refs/tags/3.2.0.tar.gz
   tar xf hippylib-3.2.0.tar.gz
   ```
4. Check:
   ```bash
   ~/miniforge3/envs/ema-hippylib/bin/python -c "import dolfin, hippylib, importlib.metadata as m; print(dolfin.__version__, m.version('hippylib'))"
   ```
   Expect `2019.1.0 3.2.0`.
5. Freeze the env: `mamba env export -n ema-hippylib > ema-hippylib.yml`.

Known problems: DOLFIN compiles expressions and forms with its JIT (dijitso/FFC) on first use and caches them in `~/.cache/dijitso` **(unconfirmed path)**, so the first run takes much longer. `model_subsurf.py` uses `dl.CompiledExpression` for the anisotropic tensor, which needs the JIT's C++ compiler (the package depends on `clangxx_osx-64`). The Docker image `hippylib/fenics:latest` is from 2019-05-31 (amd64 only), so use it only as a last resort.
Sources: https://github.com/hippylib/hippylib/releases/tag/3.2.0, https://raw.githubusercontent.com/hippylib/hippylib/master/INSTALL.md, https://pypi.org/project/hippylib/, https://api.anaconda.org/package/conda-forge/fenics-dolfin, https://prefix.dev/channels/conda-forge/packages/fenics-dolfin, https://github.com/hippylib/hippylibx, https://hub.docker.com/r/hippylib/fenics/tags, https://fenicsproject.org/download/

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same conda env (`Miniforge3-Linux-x86_64.sh`, then the same `mamba create` and `pip install`), so both machines run identical code. conda-forge has linux-64 builds of `fenics` 2019.1.0.
2. apt: the FEniCS PPA now publishes FEniCSx. Ubuntu's archive has had `python3-dolfin` (legacy) **(unconfirmed for noble; check packages.ubuntu.com/noble/python3-dolfin)**, but its PETSc (3.19) differs from conda's, so prefer conda.
3. Docker fallback: `hippylib/fenics:latest` (2019, amd64), pinned by digest. It is old, so check that `pip install hippylib==3.2.0` works inside it before relying on it **(unconfirmed)**.
4. Check: as on the Mac.
Sources: https://api.anaconda.org/package/conda-forge/fenics, https://hub.docker.com/r/hippylib/fenics/tags, https://packages.ubuntu.com/

**Preparing the examples for EMA.** The recipe:
- Copy the application script into a driver `run.py` next to `model.json`, and have it read a `key = value` deck rendered from a template, as `examples/cantera/ignite.py` does. The command is the `ema-hippylib` env's absolute `python`.
- **Keep the truth and the data fixed.** `model_subsurf.py` draws the true parameter as a sample of the *same* prior whose `gamma` and `delta` you would vary. Changing the prior would then change the truth. In the driver, build the truth from a reference prior with the tutorial's values (γ = 0.1, δ = 0.5), generate the data once per run from that truth with the fixed seed, and use the deck's `gamma`, `delta` and `rel_noise` only for the inversion prior and the noise model.
- Randomness is seeded: `parRandom = Random(..., seed=1)` in `hippylib/utils/random.py`, and the scripts call `np.random.seed(1)`. So runs are repeatable on one machine, and `repeat` should show zero noise. The randomized estimators (the double-pass eigensolver, `posterior.trace(method="Randomized", r=200)`) are deterministic given the seed, but their error is a smooth function of the inputs only up to the estimator's variance. Prefer exact outputs (the MAP cost, KL, eigenvalue counts) over randomized traces.
- Remove the XDMF output, `modelVerify` (a finite-difference derivative check that costs extra solves), and the sampling loop (set `nsamples` to 0).
- Print one line `EMA_OUTPUT <value:.12e>` and parse it with a regex.
- Coarsen: `--nx 32 --ny 32` instead of 64 for the Poisson case, and `ad_20.xml` (the coarse mesh) instead of `ad_10k.xml` for advection–diffusion.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `applications/poisson/model_subsurf.py` (https://github.com/hippylib/hippylib/blob/3.2.0/applications/poisson/model_subsurf.py) | nonlinear inverse problem: log-permeability `m` in −∇·(e^m ∇u) = 0 on a unit square, 50 pointwise observations in the lower half, anisotropic BiLaplacian prior; MAP by inexact Newton–CG, then a low-rank Laplace approximation (k = 50) | `gamma` 0.1 [0.02, 0.5] (log); `delta` 0.5 [0.1, 2.5] (log); `rel_noise` 0.01 [0.002, 0.05] (log); truth and data fixed (see the recipe); mesh 32×32 | KL distance from prior to posterior (`posterior.klDistanceFromPrior()`); second model: the misfit part of the cost at the MAP point | KL decreases steadily as `rel_noise` grows (less information), close to linear in log(rel_noise) *(expected)*; the prior's correlation length ∝ sqrt(γ/δ) makes `gamma` × `delta` interact, so sobol should show an interaction that `linear_coeffs(log_output=True)` explains through a ratio. The misfit at the MAP point scales like the number of observations when the noise model is right (a flat plateau); the discrepancy principle shows up as a trend in `rel_noise` | 10–60 s after the JIT cache is warm *(estimate)* | command-line (env python + `run.py`) | regex `EMA_OUTPUT (\S+)` |
| `applications/ad_diff/model_ad_diff.py` (https://github.com/hippylib/hippylib/blob/3.2.0/applications/ad_diff/model_ad_diff.py) | linear Bayesian inverse problem: initial condition of a time-dependent advection–diffusion (SUPG, κ = 0.001, t ∈ [0, 4], dt 0.1) from sparse observations in time; BiLaplacian prior γ = 1, δ = 8; k = 80 eigenpairs | `kappa` 0.001 [3e-4, 1e-2] (log); `gamma` 1 [0.3, 3] (log); `delta` 8 [2, 32] (log); `rel_noise` 0.01 [0.002, 0.05] (log); mesh `ad_20.xml`; k reduced to 30 | the number of generalized eigenvalues of the prior-preconditioned misfit Hessian above 1 (the data-informed dimension); second model: the largest eigenvalue | the count is an integer, so a staircase: `nonsmooth` reports jumps everywhere, and it isn't suited to sobol (use `morris` and `curve1d`). It falls with `rel_noise` and with `kappa` (diffusion destroys information). The largest eigenvalue is smooth, close to a power law in `rel_noise` (∝ rel_noise⁻², since the misfit Hessian scales with 1/σ²; an *(expected)* exact exponent of −2 for a linear problem), a good known-answer check for `linear_coeffs(log_output=True)` | 30–120 s (80+ time-dependent forward/adjoint pairs) *(estimate)* | command-line | regex |
| `tutorial/5_HessianSpectrum.ipynb` (https://github.com/hippylib/hippylib/blob/3.2.0/tutorial/5_HessianSpectrum.ipynb) | spectrum of the data-misfit Hessian for a 2-D inverse problem as the noise level, the number of observations and the prior change (the tutorial's own experiment) | noise level and prior hyperparameters as in the notebook (read its first cells for the nominal values; I didn't extract them **(unconfirmed)**) | an eigenvalue at a fixed index (smooth) | power law in the noise level; decay of the spectrum governed by the prior's smoothing | 10–60 s *(estimate)* | command-line (notebook converted to `run.py` with `jupyter nbconvert --to script`) | regex |

**Claude Code prompts.**

```text
Stage 1 (hIPPYlib, read-only check). I want to onboard hIPPYlib 3.2.0 applications into EMA as command-line models. hIPPYlib needs legacy FEniCS 2019.1 (DOLFIN), which conda-forge still builds for osx-64 and linux-64. Read-only: report OS and version, uname -m, conda/mamba (Miniforge) and its version, any existing env named ema-hippylib, C/C++ compilers (cc --version, xcode-select -p), Docker, and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge env ema-hippylib (python=3.12 fenics=2019.1.0 mpich) plus pip install hippylib==3.2.0 in that env; the Docker image hippylib/fenics (2019) only as a last resort; not hippylibx (it targets DOLFINx 0.8). Stop and report; don't continue to the next stage.
```

```text
Stage 2a (hIPPYlib, install on the Intel Mac). Never install into EMA's .venv, and never read .env. Ask before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Steps: (1) mamba create -n ema-hippylib -c conda-forge python=3.12 fenics=2019.1.0 mpich matplotlib scipy; (2) <env>/bin/python -m pip install "hippylib==3.2.0"; (3) download https://github.com/hippylib/hippylib/archive/refs/tags/3.2.0.tar.gz to ~/src and unpack it (for applications/ and tutorial/); (4) check: <env>/bin/python -c "import dolfin, hippylib, importlib.metadata as m; print(dolfin.__version__, m.version('hippylib'))" (expect 2019.1.0 3.2.0); (5) mamba env export -n ema-hippylib > ~/src/ema-hippylib.yml. Report the env's absolute python path. Stop at the first error and report the command and its output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (hIPPYlib, install on AWS Ubuntu 24.04 x86_64; I'm ssh'd in). The same conda env as on my Mac: Miniforge (Linux x86_64 installer; ask first), mamba create -n ema-hippylib -c conda-forge python=3.12 fenics=2019.1.0 mpich matplotlib scipy, then pip install hippylib==3.2.0 into it, and unpack the 3.2.0 source tarball into ~/src. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. If conda can't solve the env, report and propose (don't run) the Docker image hippylib/fenics:latest pinned by digest. Check as on the Mac. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (hIPPYlib smoke test). In a scratch directory outside the EMA repo, with the ema-hippylib env's python, run applications/poisson/model_subsurf.py from ~/src/hippylib-3.2.0 with --nx 32 --ny 32 --nsamples 0, serially. Time it twice (the second run shows the time with a warm JIT cache). Report "Converged in ... iterations", "Final cost", the posterior/prior trace line, "KL-Distance from prior", both wall times, and where the JIT cache is. If --nsamples 0 fails, report it rather than editing the script. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (hIPPYlib, prepare the Poisson subsurface example). Plan mode first; show me the plan before writing anything. Source: applications/poisson/model_subsurf.py of hippylib 3.2.0. Create examples/hippylib/subsurf/ with a driver run.py that reads a key = value deck rendered from subsurf.template (follow examples/cantera/ignite.py and ignition.template, docs/applications.md, docs/guides/input_deck_model.md). Inputs: gamma 0.1 [0.02, 0.5] scale log, delta 0.5 [0.1, 2.5] scale log, rel_noise 0.01 [0.002, 0.05] scale log. Important: build the true parameter and the synthetic data from a fixed reference prior (gamma 0.1, delta 0.5, the script's anisotropy, the fixed seeds), and use the deck's gamma and delta only for the inversion prior and rel_noise only for the noise; say in a comment why. Mesh 32 x 32. Remove modelVerify, the XDMF output, and the sampling. Print "EMA_OUTPUT %.12e" of posterior.klDistanceFromPrior(). Command: the ema-hippylib env's absolute python path (not $EMA_PYTHON) and run.py. env OMP_NUM_THREADS=1; timeout_s 600. Write model_misfit.json too, printing the misfit part of the cost at the MAP point from a second driver flag. Check by hand that the nominal deck converges and that doubling rel_noise lowers KL. Then `.venv/bin/ema profile examples/hippylib/subsurf/model.json -n 5` and report first and warm times. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (hIPPYlib, prepare the advection-diffusion example). Plan mode first. Source: applications/ad_diff/model_ad_diff.py (with ad_20.xml and targets.txt as static files). Create examples/hippylib/ad_diff/ with a deck-driven run.py: inputs kappa 0.001 [3e-4, 1e-2], gamma 1 [0.3, 3], delta 8 [2, 32], rel_noise 0.01 [0.002, 0.05], all scale log. Keep the true initial condition and the observation times fixed; reduce k from 80 to 30; drop modelVerify and file output. Output model.json: the largest generalized eigenvalue d[0] ("EMA_OUTPUT %.12e"); model_rank.json: the number of eigenvalues above 1. Command-line model as in stage 4.1, timeout_s 900. Check by hand that halving rel_noise multiplies d[0] by about 4 (the misfit Hessian scales as 1/sigma^2). Then `.venv/bin/ema profile ... -n 3` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 5 (hIPPYlib, first campaign). For examples/hippylib/subsurf/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 6), and linear_coeffs with log_output true. Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run` (runs take tens of seconds each). Then report: whether repeats are identical (they should be: the seeds are fixed); the morris ranking and monotone flags; the exponents from linear_coeffs and its CV R^2; whether gamma and delta interact. Expected: KL falls with rel_noise; gamma and delta act partly through their ratio. Suggest (don't run) a curve1d on rel_noise for model_misfit.json. Stop and report.
```

```text
Stage 6 (hIPPYlib troubleshooting). An EMA hIPPYlib model in examples/hippylib/<example> fails or is slow. Diagnose read-only first by running the driver by hand in a copy of the run directory with the ema-hippylib env's python: (a) JIT errors from dijitso/FFC ("Unable to compile C++ code"): the env's clang or SDK; check xcode-select -p and the env's compiler package; (b) every run slow: the JIT cache isn't reused (check ~/.cache for dijitso and whether HOME differs for EMA's runs); (c) "Not Converged" from ReducedSpaceNewtonCG: at extreme gamma/delta/rel_noise this is a real failure, recorded as a failed run; (d) outputs that change between repeats: a random draw that isn't seeded, or the truth depending on the deck's prior (see stage 4.1); (e) PETSc/MPI start-up errors: run without mpirun; (f) numpy 2 or Python 3.12 incompatibilities in hippylib 3.2.0: report the traceback. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License: GPL-2.0 for hIPPYlib (`COPYRIGHT` at the tag), LGPL-3 for FEniCS 2019.1. Both are fine for use as external programs.
- Legacy FEniCS is frozen upstream. conda-forge rebuilds it for new Python and PETSc versions (build 66, September 2026), but that can stop. Export the env (`mamba env export`) and keep the file.
- Parallelism: run serially, with `OMP_NUM_THREADS=1`. The scripts are MPI-aware (`rank == 0` prints), but EMA's `-j N` is the parallelism.
- Determinism: seeds are fixed (`parRandom` seed 1, `np.random.seed(1)`), so `repeat` should show zero noise on one machine. Randomized trace estimators are repeatable, but their sampling error makes the output slightly rough in the inputs. Prefer exact summaries.
- The truth must not move with the inputs (the stage 4.1 edit). Otherwise EMA measures how the synthetic truth changes, not how the inference does.
- Run time: tens of seconds to minutes. Morris and curve1d campaigns are affordable, and a Sobol campaign on 4 inputs (1,536 runs at `n_base` 256) is AWS work.
- Sources: https://hippylib.github.io, https://github.com/hippylib/hippylib, https://github.com/hippylib/hippylib/releases/tag/3.2.0, https://raw.githubusercontent.com/hippylib/hippylib/master/INSTALL.md, https://pypi.org/project/hippylib/, https://github.com/hippylib/hippylib/blob/3.2.0/applications/poisson/model_subsurf.py, https://github.com/hippylib/hippylib/blob/3.2.0/applications/ad_diff/model_ad_diff.py, https://github.com/hippylib/hippylib/tree/3.2.0/tutorial, https://github.com/hippylib/hippylib/blob/3.2.0/hippylib/utils/random.py, https://github.com/hippylib/hippylib/blob/3.2.0/COPYRIGHT, https://github.com/hippylib/hippylibx, https://api.anaconda.org/package/conda-forge/fenics-dolfin, https://api.anaconda.org/package/conda-forge/fenics, https://hub.docker.com/r/hippylib/fenics/tags, https://fenicsproject.org/download/

---

#### Trilinos

**What it is.** Sandia's collection of more than 50 C++ packages for large-scale solvers: linear algebra (Tpetra, and Epetra in the 16.x line), Krylov solvers (Belos, AztecOO), preconditioners (MueLu, ML, Ifpack2), eigensolvers (Anasazi), nonlinear solvers and continuation (NOX, LOCA), optimization (ROL), time integration (Tempus), and Python bindings (PyTrilinos in ≤ 16, PyTrilinos2 in 17). License: BSD-3-Clause for most packages (the conda-forge recipe declares BSD-3-Clause; a few packages are LGPL). Current release **17.2.1 (2026-08-31)**. The 16.2 line is also maintained (16.2.2, 2026-08-17). Examples are spread across packages as `packages/<pkg>/example/`: e.g. 32 ROL example directories in `packages/rol/example/`, and 40 PyTrilinos scripts in `packages/PyTrilinos/example/` at 16.2.0 (https://github.com/trilinos/Trilinos).
Fit: medium. Trilinos is a solver toolkit, not an application, so its examples are demonstrations of an algorithm, with physics parameters as command-line options (PyTrilinos) or hard-coded constants (ROL, which need a small edit). Two examples fit EMA well: a PyTrilinos NOX nonlinear boundary-value problem that runs without a compiler, and a ROL optimal-control problem whose optimum depends on physical and regularization inputs.

**Install on an Intel Mac.** conda-forge builds `trilinos` and `pytrilinos` **16.2.0 for osx-64** (build 2, 2026-09-03, Python 3.11–3.14, with openmpi). It is built with Epetra, NOX/LOCA, ROL, Belos, Anasazi, MueLu, Tempus-era Rythmos, and Stokhos enabled, and with examples and tests off. Trilinos 17 is not on conda-forge yet. Homebrew is Tier 3 on Intel. So: conda-forge 16.2.0.
1. Install Miniforge if needed (see 4.1).
2. Create the env with the versions pinned:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-trilinos -c conda-forge python=3.12 trilinos=16.2.0 pytrilinos=16.2.0 openmpi compilers cmake make
   ```
3. Get the examples from the matching tag (the package ships no examples):
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -L -o trilinos-16.2.0.tar.gz https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-16-2-0.tar.gz
   tar xf trilinos-16.2.0.tar.gz
   ```
   (The tarball is a few hundred MB **(unconfirmed size)**, so ask before downloading. A sparse `git clone --filter=blob:none --sparse` of `packages/PyTrilinos/example` and `packages/rol/example` is smaller.)
4. Check:
   ```bash
   ~/miniforge3/envs/ema-trilinos/bin/python -c "from PyTrilinos import Epetra, NOX, Teuchos; print(Teuchos.Teuchos_Version())"
   ```
   The recipe's own tests import `PyTrilinos.Teuchos`, `Epetra`, `NOX`, `NOX.Epetra` and `LOCA`. The exact version function is **(unconfirmed)**, so if it doesn't exist, `import PyTrilinos` and print `PyTrilinos.__file__`.

Known problems: the `.py.in` example files are CMake templates. They import `testutil.fromPyTrilinosImport`, so a copied example needs its imports rewritten as `from PyTrilinos import Epetra, NOX, ...`. The conda build uses openmpi, so an MPI program may warn about the network on a laptop. Run serially without `mpiexec`.
Sources: https://github.com/trilinos/Trilinos/releases, https://api.anaconda.org/package/conda-forge/trilinos, https://api.anaconda.org/package/conda-forge/pytrilinos, https://prefix.dev/channels/conda-forge/packages/trilinos, https://github.com/conda-forge/trilinos-feedstock (recipe/recipe.yaml, recipe/build.sh), https://trilinos.github.io

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same conda env (linux-64 has `trilinos`/`pytrilinos` 16.2.0), so both machines match.
2. For Trilinos 17 (PyTrilinos2 and Tpetra only): Spack, `spack install trilinos@17.2.1 +python +nox +rol` (Spack lists 17.2.1, and `+python` builds PyTrilinos2 for versions ≥ 15). It is a long build, one to several hours on 8 cores *(estimate)*.
3. apt: noble's `trilinos-all-dev` is **13.2.0**, too old to match the 16.2 examples.
4. Docker: no official Trilinos image found **(unconfirmed)**. The fallback is a `condaforge/miniforge3` image pinned by digest, with step 1 inside it.
5. Check: as on the Mac.
Sources: https://packages.ubuntu.com/noble/trilinos-all-dev, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/trilinos/package.py, https://api.anaconda.org/package/conda-forge/trilinos

**Preparing the examples for EMA.** The recipe:
- **PyTrilinos examples** (Python): copy the `.py.in` file into the model directory as `run.py`, replace the `testutil` imports with `from PyTrilinos import ...`, and keep its `optparse` options. EMA then passes inputs as command arguments (`"-k", "$k", "--bc0", "$bc0"`), as `examples/beam/model_args.json` does. The command is the env's absolute `python`. Add one `print("EMA_OUTPUT %.12e" % value)` after the solve. Exit non-zero if NOX didn't converge (the script already counts failures in `status`), so EMA records a failed run.
- **ROL examples** (C++): the physics and regularization constants are hard-coded in `example_01.cpp`/`.hpp`. Edit them to read `argv` (or a Teuchos XML file rendered from a template; the XML has no `$`). Compile against the conda env with a three-line `CMakeLists.txt` (`find_package(ROL)` or `find_package(Trilinos COMPONENTS ROL)`; the exact package name is **(unconfirmed)**), and keep the binary in the model directory. Replace `rand()` initial guesses with a fixed vector or `srand(0)`.
- Run serially, with `OMP_NUM_THREADS=1` (the conda build has OpenMP enabled).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `packages/PyTrilinos/example/exNOX_1Dfdm.py.in` (https://github.com/trilinos/Trilinos/blob/trilinos-release-16-2-0/packages/PyTrilinos/example/exNOX_1Dfdm.py.in) | 1-D nonlinear BVP u'' = k u² on [0, 1], u(0) = bc0, u(1) = bc1, centered finite differences on `numelem` points, NOX Newton with a matrix-free Jacobian and a finite-difference-coloring preconditioner | `-k` 1000 [10, 1e5] (log); `--bc0` 1 [0.5, 2]; `--bc1` 2 [0.5, 3]; `-n` 100 fixed (more for large k) | ∫u dx (trapezoid over the solution vector, serial) printed by the added line | decreasing in `k`, close to a power law at large k (boundary layers of width ∝ k^(−1/2) *(expected)*), so `linear_coeffs(log_output=True)` should find a negative exponent for `k`; increasing in `bc0` and `bc1`, with a bc × k interaction (the layers scale with the boundary values). At large k the linear initial guess may fail to converge: failed runs, a failure region at the top of the `k` range | 1–3 s, mostly Python and PyTrilinos import *(estimate)* | command-line (env python + `run.py`, options as arguments) | regex `EMA_OUTPUT (\S+)` |
| `packages/rol/example/burgers-control/example_01.cpp` + `example_01.hpp` (https://github.com/trilinos/Trilinos/tree/trilinos-release-16-2-0/packages/rol/example/burgers-control) | optimal distributed control of steady 1-D viscous Burgers, with bound constraints 0 ≤ z ≤ 1 on the control, solved by primal-dual active set and by a trust-region (Lin–Moré) method; the state is solved by Newton inside the objective | `alpha` (control penalty, hard-coded 1e-3) 1e-3 [1e-5, 1e-1] (log); `nu` (viscosity, 10^(param[0]−2) = 0.01 in the code) 0.01 [1e-3, 0.1] (log); `f` (forcing, param[1]/100 = 0) 0 [−0.5, 0.5]; `u0` (left boundary value, 1 + param[2]/1000) 1 [0.5, 1.5]; `nx` 1028 reduced to 128 | the optimal objective J(z*) from the trust-region run, printed by an added line (`obj.value(y, tol)`) | increasing and smooth in `alpha` on a log scale; the active set of the bound changes with `alpha` and `nu`, so the optimal control changes in steps and J(z*) has kinks in its derivative (`nonsmooth` "kinks at this resolution" at small alpha) *(expected)*; small `nu` makes the state solve harder, a possible failure region | < 1 s at nx 128 *(estimate)* | command-line (compiled binary in model dir, inputs as arguments after the edit) | regex |

**Claude Code prompts.**

```text
Stage 1 (Trilinos, read-only check). I want to onboard two Trilinos 16.2.0 examples into EMA (a PyTrilinos NOX script and a ROL C++ example). Read-only: report OS and version, uname -m, conda/mamba (Miniforge) and its version, any env named ema-trilinos, compilers (cc --version, c++ --version, xcode-select -p), cmake, MPI on PATH, Docker, git, and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge env ema-trilinos with trilinos=16.2.0 pytrilinos=16.2.0 (osx-64 and linux-64 builds exist; Trilinos 17.2.1 isn't on conda-forge yet, and 17 dropped the legacy PyTrilinos); Spack for 17.2.1 only if needed; not apt (noble has 13.2.0). Stop and report; don't continue to the next stage.
```

```text
Stage 2a (Trilinos, install on the Intel Mac). Never install into EMA's .venv, and never read .env. Ask before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Steps: (1) mamba create -n ema-trilinos -c conda-forge python=3.12 trilinos=16.2.0 pytrilinos=16.2.0 openmpi compilers cmake make; (2) get the example sources for tag trilinos-release-16-2-0: prefer a sparse clone of https://github.com/trilinos/Trilinos (git clone --filter=blob:none --sparse --branch trilinos-release-16-2-0, then git sparse-checkout set packages/PyTrilinos/example packages/rol/example) into ~/src/trilinos-16.2.0; tell me the size before a full tarball download; (3) check: <env>/bin/python -c "from PyTrilinos import Teuchos, Epetra, NOX, LOCA; print('ok')" and report the env's absolute python path. Stop at the first error and report the command and its output. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (Trilinos, install on AWS Ubuntu 24.04 x86_64; I'm ssh'd in). The same conda env as on the Mac: Miniforge (ask first), mamba create -n ema-trilinos -c conda-forge python=3.12 trilinos=16.2.0 pytrilinos=16.2.0 openmpi compilers cmake make, and the same sparse clone of the 16.2.0 examples. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. If conda fails, propose (don't run) spack install trilinos@17.2.1 +python +nox +rol (a long build; PyTrilinos2 differs from PyTrilinos) or a Dockerfile FROM condaforge/miniforge3 pinned by digest. Check as on the Mac. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (Trilinos smoke test). In a scratch directory outside the EMA repo, with the ema-trilinos env: (1) copy packages/PyTrilinos/example/exNOX_1Dfdm.py.in to ex_nox.py, replace the testutil imports with from PyTrilinos import Teuchos, Epetra, EpetraExt, NOX, run it serially with -k 1000 --bc0 1 --bc1 2 -v 1, and report the last lines and the wall time; (2) build packages/rol/example/burgers-control/example_01.cpp against the env with a minimal CMakeLists.txt (find_package for ROL or Trilinos; report which worked), run it with input.xml next to it, and report "End Result" and the wall time. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (Trilinos, prepare the PyTrilinos NOX example for EMA). Plan mode first; show me the plan before writing anything. Read docs/applications.md, docs/guides/input_deck_model.md and examples/beam/model_args.json. Create examples/trilinos/nox_1dfdm/run.py from exNOX_1Dfdm.py.in (Trilinos 16.2.0): imports from PyTrilinos, plotting and the parameter-list printout removed, and after the solve print "EMA_OUTPUT %.12e" of the trapezoid integral of the solution (serial), and exit 1 if NOX didn't converge. Keep the script's options. model.json: command-line model, command [<ema-trilinos env's absolute python>, "run.py", "-k", "$k", "--bc0", "$bc0", "--bc1", "$bc1", "-n", "200", "-v", "0"]; inputs k 1000 [10, 1e5] scale log, bc0 1 [0.5, 2], bc1 2 [0.5, 3]; output regex "EMA_OUTPUT (\S+)"; env OMP_NUM_THREADS=1; timeout_s 60. Check by hand that the nominal run converges and that k = 1e5 either converges or fails cleanly with exit 1. Then `.venv/bin/ema profile examples/trilinos/nox_1dfdm/model.json -n 5` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (Trilinos, prepare ROL burgers-control). Plan mode first. Copy packages/rol/example/burgers-control/example_01.cpp, example_01.hpp and input.xml (Trilinos 16.2.0) to examples/trilinos/rol_burgers/. Edit, with a comment at each change: read alpha, nu, f, u0 and nx from argv (keep nx 128 as the default); replace the local param vectors in value/gradient/hessVec with a member set from nu, f, u0 (the code maps nu = 10^(param[0]-2), f = param[1]/100, u0 = 1 + param[2]/1000, so invert those or set the physical values directly); drop checkGradient/checkHessVec and the control_*.txt output; seed rand() with 0; after the Lin-More solve print "EMA_OUTPUT %.12e" of obj.value(y, tol). Build it in that directory with the env's compilers (a CMakeLists.txt and a build script). model.json: command ["rol_burgers", "$alpha", "$nu", "$f", "$u0"], static file input.xml; inputs alpha 1e-3 [1e-5, 1e-1] scale log, nu 0.01 [1e-3, 0.1] scale log, f 0 [-0.5, 0.5], u0 1 [0.5, 1.5]; regex output; timeout_s 60. Check by hand that the nominal inputs reproduce the unedited example's objective. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 (Trilinos, first campaign). For examples/trilinos/rol_burgers/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), curve1d on alpha (n 21), and nonsmooth on alpha. Report the run count from `.venv/bin/ema estimate` and ask me before `ema run`. Then report: repeatability; the morris ranking and monotone flags; curve1d and nonsmooth features in alpha (expected: monotone increasing, possibly kinks where the active set changes, reported "at this resolution"); failed runs and where they are (expected: small nu). Suggest (don't run) linear_coeffs with log_output on examples/trilinos/nox_1dfdm (expected: a negative exponent for k). Stop and report.
```

```text
Stage 6 (Trilinos troubleshooting). An EMA Trilinos model in examples/trilinos/<example> fails. Diagnose read-only first, from the run directory's stdout.txt and stderr.txt, and by running the command by hand in a copy of the run directory: (a) ImportError for PyTrilinos modules: the wrong python (it must be the ema-trilinos env's) or a module not built in the conda package (check the recipe's list: Teuchos, Epetra, EpetraExt, NOX, LOCA, Anasazi, ...); (b) "Library not loaded" for the ROL binary: link with an rpath to the env's lib; (c) NOX "failed to converge" at large k: expected, a failed run; (d) Open MPI warnings or hangs at start-up: run without mpiexec, and set OMPI_MCA_* variables in the spec's env only if needed (tell me which); (e) outputs that vary between repeats: rand() initial guesses, OpenMP threads (OMP_NUM_THREADS=1), or loose Krylov tolerances in input.xml; (f) CMake can't find ROL: report the files under $CONDA_PREFIX/lib/cmake. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License: BSD-3-Clause for most packages, a few LGPL. Both are fine for external use.
- Version split: upstream is 17.2.1 (Tpetra-only, PyTrilinos2), conda-forge is 16.2.0 (Epetra, legacy PyTrilinos). The examples above use 16.2.0 APIs (Epetra, NOX.Epetra) and won't run on Trilinos 17. Pin 16.2.0 and take the examples from the `trilinos-release-16-2-0` tag.
- Parallelism: the conda build has OpenMP and MPI (openmpi) on. Set `OMP_NUM_THREADS=1` and run serially. Epetra's `PyComm` works without `mpiexec`.
- Determinism: Newton and trust-region solves are deterministic given their initial guess. The ROL example's `rand()` guesses must be fixed. Iterative linear solves with loose tolerances (the Krylov relative tolerance 1e-2 in `input.xml`) make the optimum slightly rough, so tighten them for EMA.
- Run time: seconds. PyTrilinos' import dominates the Python example.
- Sources: https://trilinos.github.io, https://github.com/trilinos/Trilinos, https://github.com/trilinos/Trilinos/releases, https://github.com/trilinos/Trilinos/tree/trilinos-release-16-2-0/packages/PyTrilinos/example, https://github.com/trilinos/Trilinos/blob/trilinos-release-16-2-0/packages/PyTrilinos/example/exNOX_1Dfdm.py.in, https://github.com/trilinos/Trilinos/tree/trilinos-release-16-2-0/packages/rol/example/burgers-control, https://github.com/conda-forge/trilinos-feedstock, https://api.anaconda.org/package/conda-forge/trilinos, https://api.anaconda.org/package/conda-forge/pytrilinos, https://prefix.dev/channels/conda-forge/packages/trilinos, https://packages.ubuntu.com/noble/trilinos-all-dev, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/trilinos/package.py

---

#### SLEPc

**What it is.** Scalable Library for Eigenvalue Problem Computations (Universitat Politècnica de València), built on PETSc: linear eigenproblems (EPS: Krylov–Schur, Davidson, LOBPCG, ...), SVD, polynomial (PEP) and nonlinear (NEP) eigenproblems, and matrix functions (MFN). C, with Fortran and Python (`slepc4py`) bindings. License BSD-2-Clause. Current release **3.25.2** (the tarball on slepc.upv.es is dated 2026-09-18; the 3.25 series started in March 2026). SLEPc's release branch follows PETSc's, so 3.25.x goes with PETSc 3.25.x. Tutorials: `src/eps/tutorials/` has **34** (`ex1.c` … `ex58.c`, three in Fortran), browsable at https://slepc.upv.es/release/src/eps/tutorials/index.html, and there are more in `src/svd`, `src/pep`, `src/nep` and `src/mfn`. Like PETSc's tutorials, they read physical parameters as options (`PetscOptionsGetScalar`) and SLEPc settings as `-eps_*` options.
Fit: good, and it complements PETSc. An eigenvalue as a function of operator parameters is smooth where it's simple, and has **kinks where eigenvalues cross** (when the output is "the k-th smallest" or "the rightmost"). That is exactly what `nonsmooth` and `curve1d` look for, and one of the examples below has the kink at a known place.

**Install on an Intel Mac.** Build on 4.4's `ema-petsc` env (PETSc 3.25.5). conda-forge has `slepc` and `slepc4py` **3.25.2 for osx-64** (uploaded 2026-09-23), requiring `petsc >=3.25.5,<3.26`, so they match the env. Choose the `real` build, to match the env's PETSc.
1. Install into the existing env:
   ```bash
   ~/miniforge3/bin/mamba install -n ema-petsc -c conda-forge "slepc=3.25.2=real_*" "slepc4py=3.25.2"
   ```
   (If the solver wants to change `petsc`, stop: the build string or the MPI variant doesn't match. Check `mamba list -n ema-petsc petsc`.)
2. Get the tutorials from the matching tarball (about 1.9 MB):
   ```bash
   cd ~/src && curl -LO https://slepc.upv.es/download/distrib/slepc-3.25.2.tar.gz && tar xf slepc-3.25.2.tar.gz
   ```
3. Compile a tutorial against the env (with conda, `SLEPC_DIR=PETSC_DIR=$CONDA_PREFIX`):
   ```bash
   conda activate ema-petsc
   cd ~/src/slepc-3.25.2/src/eps/tutorials
   mpicc ex9.c -o ex9 $(pkg-config --cflags --libs slepc petsc) -Wl,-rpath,$CONDA_PREFIX/lib
   ```
   (The `.pc` name, `slepc` or `SLEPc`, is **(unconfirmed)**. Otherwise add `-I$CONDA_PREFIX/include -L$CONDA_PREFIX/lib -lslepc -lpetsc` by hand.)
4. Check:
   ```bash
   ./ex9 -eps_nev 4 -terse
   python -c "from slepc4py import SLEPc; print(SLEPc.Sys.getVersion())"
   ```
   Expect `(3, 25, 2)` and four eigenvalues.

Known problems: as for PETSc (4.4). Link with an rpath rather than relying on `DYLD_LIBRARY_PATH`. The `complex` builds exist too, so don't mix them.
Sources: https://slepc.upv.es/download/, https://slepc.upv.es/release/installation/ **(unconfirmed path)**, https://api.anaconda.org/package/conda-forge/slepc, https://prefix.dev/channels/conda-forge/packages/slepc, https://api.anaconda.org/package/conda-forge/slepc4py

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same step into the `ema-petsc` env (linux-64 has 3.25.2), then the same tarball and compile.
2. apt: noble's `slepc-dev` is **3.19.2** and `python3-slepc4py` 3.19.2, matching apt's PETSc 3.19.6 but not the conda env. Use it only if you took PETSc from apt too.
3. Spack: `spack install slepc@3.25.2` (it brings PETSc).
4. Docker: no official SLEPc image found **(unconfirmed)**. Use the same `condaforge/miniforge3` fallback as PETSc.
5. Check: as on the Mac.
Sources: https://packages.ubuntu.com/noble/slepc-dev, https://packages.ubuntu.com/noble/python3-slepc4py, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/slepc/package.py

**Preparing the examples for EMA.** The same recipe as PETSc (4.4):
- Inputs go on the command line (`"-beta", "$beta"`), and fixed settings go in a static options file passed with `-options_file slepc.opts`.
- Keep the compiled binary in the model directory, so the hash covers it.
- The tutorials print eigenvalues through `EPSErrorView` with only about 5 decimals. So add after `EPSSolve` a loop that prints the wanted eigenvalue with `EPSGetEigenpair` as `EMA_OUTPUT %.12e`, and parse it with a regex. The `-eps_view_values` viewer is an alternative that needs no edit, but its precision is **(unconfirmed)**.
- Tighten the solver with `-eps_tol 1e-12` and fix `-eps_ncv`, so the tolerance doesn't add roughness.
- Add a check that the number converged (`EPSGetConverged`) is at least the index printed, and exit non-zero otherwise, so EMA records a failed run.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `src/eps/tutorials/ex9.c` (https://slepc.upv.es/release/src/eps/tutorials/ex9.c.html) | Brusselator wave model: the linearized reaction–diffusion operator on a 1-D grid of `-n` 30 points (matrix size 60), non-symmetric, via a shell matrix; `EPSSetWhichEigenpairs(EPS_LARGEST_REAL)` | `-L` 0.51302 [0.3, 0.8]; `-alpha` 2 [1.5, 2.5]; `-beta` 5.45 [4.5, 6.5]; `-delta1` 0.008 [0.004, 0.016] (log); `-delta2` 0.004 fixed (all defaults from the source) | real part of the rightmost eigenvalue (added print) | the default L = 0.51302 sits at the Hopf point (real part ≈ 0), so the output changes sign inside the input box: stability boundary. It increases with `beta`. **Kinks** where the rightmost eigenvalue switches from one mode to another (`nonsmooth`, `curve1d` on `L` and `beta`), smooth between them. The imaginary part (a second model) jumps where a complex pair and a real eigenvalue exchange the lead | < 0.2 s *(estimate)* | command-line (binary in model dir, options as args) | regex `EMA_OUTPUT (\S+)` |
| `src/eps/tutorials/ex2.c` (https://slepc.upv.es/release/src/eps/tutorials/ex2.c.html), edited to an anisotropic Laplacian | 5-point Laplacian on an n × m grid (options `-n`, `-m`); the edit scales the x-couplings by `-ax` and the y-couplings by `-ay` (three lines in the assembly loop) | `-ax` 1 [0.5, 2]; `-ay` 1 [0.5, 2]; `-n` = `-m` = 30 fixed; `-eps_smallest_real -eps_nev 2` | the second-smallest eigenvalue (added print) | **known answer**: the eigenvalues are ax(2 − 2cos(iπ/(n+1))) + ay(2 − 2cos(jπ/(m+1))), so the second-smallest is min over the (2,1) and (1,2) modes. It is piecewise linear, with a kink exactly on the diagonal ax = ay (n = m). `nonsmooth` must find it there, `linear_coeffs` fits each side exactly, and `surface2d` shows a ridge along the diagonal. A clean test of EMA's kink detection | < 0.5 s *(estimate)* | command-line | regex |

**Claude Code prompts.**

```text
Stage 1 (SLEPc, read-only check). I want to add SLEPc 3.25.2 to the existing ema-petsc conda env (PETSc 3.25.5, section 4.4 of docs/brainstorms/pde_packages_onboarding.md) and run its EPS tutorials as EMA command-line models. Read-only: report OS and version, uname -m, conda/mamba, whether ema-petsc exists and `mamba list -n ema-petsc` for petsc, petsc4py, mpich and slepc (build strings, real or complex), whether ~/src/petsc-3.25.5 exists, a C compiler, and free disk space. Don't install anything, and don't read .env. Recommend: mamba install -n ema-petsc -c conda-forge "slepc=3.25.2=real_*" slepc4py=3.25.2 (osx-64 and linux-64 builds require petsc >=3.25.5,<3.26), tutorials from slepc-3.25.2.tar.gz. If ema-petsc doesn't exist, say to do the PETSc stages first. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (SLEPc, install on the Intel Mac). Never install into EMA's .venv, and never read .env. Ask before any sudo or Homebrew change and before downloads over 1 GB. Steps: (1) mamba install -n ema-petsc -c conda-forge "slepc=3.25.2=real_*" "slepc4py=3.25.2" and show me the transaction first; if it wants to change or remove petsc, stop and report instead; (2) download https://slepc.upv.es/download/distrib/slepc-3.25.2.tar.gz to ~/src and unpack it (tutorials only; don't configure or build SLEPc); (3) in the env, compile src/eps/tutorials/ex9.c with mpicc and pkg-config (try slepc, then SLEPc; else explicit -lslepc -lpetsc), with -Wl,-rpath,$CONDA_PREFIX/lib; (4) check: ./ex9 -eps_nev 4 -terse, and python -c "from slepc4py import SLEPc; print(SLEPc.Sys.getVersion())". Stop at the first error and report the command and its output. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (SLEPc, install on AWS Ubuntu 24.04 x86_64; I'm ssh'd in). The same as the Mac, into the ema-petsc env created in the PETSc stage 2b: mamba install -n ema-petsc -c conda-forge "slepc=3.25.2=real_*" "slepc4py=3.25.2" (show me the transaction; stop if it changes petsc), download and unpack slepc-3.25.2.tar.gz into ~/src, compile ex9.c, and check. Don't use apt's slepc-dev (3.19.2). Never use EMA's .venv, and never read .env. Ask before any sudo. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (SLEPc smoke test). In the ema-petsc env, from ~/src/slepc-3.25.2/src/eps/tutorials, compile ex1.c, ex2.c and ex9.c if not already compiled, then run and time: ./ex1 -n 100 -eps_nev 4 -terse; ./ex2 -n 30 -m 30 -eps_smallest_real -eps_nev 4 -terse; ./ex9 -eps_nev 4 -terse; ./ex9 -L 0.6 -eps_nev 4 -terse. Report each output and wall time, and check ex2's smallest eigenvalue against 2(2 - 2cos(pi/31)) by hand. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (SLEPc, prepare ex9 Brusselator for EMA). Plan mode first; show me the plan before writing anything. Read docs/applications.md, docs/guides/input_deck_model.md, examples/beam/model_args.json, and section 4.4's PETSc stage 4.1 in docs/brainstorms/pde_packages_onboarding.md. Copy ex9.c (SLEPc 3.25.2) into examples/slepc/ex9_brusselator/, and after EPSSolve add: get the number converged; exit with an error if it is 0; otherwise EPSGetEigenpair(eps, 0, &kr, &ki, NULL, NULL) and PetscPrintf "EMA_OUTPUT %.12e\n" of the real part and "EMA_IMAG %.12e\n" of the imaginary part (a comment notes the edit). Build it there with the env's mpicc and an rpath (a small build script). model.json: command ["ex9", "-L", "$L", "-alpha", "$alpha", "-beta", "$beta", "-delta1", "$delta1", "-options_file", "slepc.opts"], static slepc.opts with -n 30 -eps_nev 4 -eps_tol 1e-12 -eps_ncv 24; inputs L 0.51302 [0.3, 0.8], alpha 2 [1.5, 2.5], beta 5.45 [4.5, 6.5], delta1 0.008 [0.004, 0.016] scale log; output regex "EMA_OUTPUT (\S+)"; number_format ".10g"; timeout_s 30. model_imag.json reads EMA_IMAG. Check by hand that the nominal real part is close to 0 (the default L is the Hopf point). Then `.venv/bin/ema profile examples/slepc/ex9_brusselator/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (SLEPc, prepare an anisotropic ex2 with a known kink). Plan mode first. Copy ex2.c (SLEPc 3.25.2) into examples/slepc/ex2_aniso/. Edit: read -ax and -ay (default 1) with PetscOptionsGetReal, scale the diagonal to 2*ax + 2*ay and the x- and y-neighbour couplings to -ax and -ay, and after EPSSolve print the second-smallest eigenvalue as "EMA_OUTPUT %.12e" (with -eps_smallest_real -eps_nev 2; sort the two converged values yourself); exit with an error if fewer than 2 converged. Build with the env's mpicc. model.json: command ["ex2", "-n", "30", "-m", "30", "-ax", "$ax", "-ay", "$ay", "-eps_smallest_real", "-eps_nev", "2", "-eps_tol", "1e-12"]; inputs ax 1 [0.5, 2], ay 1 [0.5, 2]; regex output. Check by hand against the closed form min(ax*c2 + ay*c1, ax*c1 + ay*c2) with ck = 2 - 2cos(k*pi/31) at (1, 1), (0.5, 2) and (2, 0.5), and report the differences. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 (SLEPc, first campaign). For examples/slepc/ex2_aniso/model.json, write campaign.json with repeat (n_points 2, replicates 2), surface2d on ax and ay (21 x 21), nonsmooth, and curve1d on ax (n 41) at ay = 1. Report the run count from `.venv/bin/ema estimate` and ask me before `ema run`. Then report: repeatability; where surface2d and nonsmooth put kinks (expected: exactly on the diagonal ax = ay, "at this resolution"); curve1d's kink location (expected: ax = 1). Then suggest (don't run) the same diagnostics plus morris for examples/slepc/ex9_brusselator (expected: a sign change of the real part near the nominal L, kinks where the rightmost mode changes). Stop and report.
```

```text
Stage 6 (SLEPc troubleshooting). An EMA SLEPc model in examples/slepc/<example> fails. Diagnose read-only first, from stdout.txt, stderr.txt and ema_run.json in the run directory: (a) "Library not loaded" / "cannot open shared object file": rebuild with -Wl,-rpath,$CONDA_PREFIX/lib; (b) "Number of converged eigenpairs 0" or the added error exit: raise -eps_ncv or -eps_max_it, or the target is wrong (EPS_LARGEST_REAL vs -eps_smallest_real); (c) the output jumps between two values on repeats: a near-degenerate eigenvalue with a loose -eps_tol, so tighten it and fix -eps_ncv; (d) a slepc/petsc mismatch at start-up ("SLEPc version ... requires PETSc ..."): check mamba list for both; (e) unused-option warnings: a misspelled option; run once with -options_left; (f) kinks EMA reports away from eigenvalue crossings: check whether the printed index changed because fewer pairs converged. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License BSD-2-Clause, the same as PETSc.
- Version lock: SLEPc 3.25.x needs PETSc 3.25.x. The conda-forge 3.25.2 builds require `petsc >=3.25.5`, so the `ema-petsc` env fits exactly. Don't mix real and complex builds.
- Parallelism: run serially, one process per run, with `OMP_NUM_THREADS=1`.
- Determinism: Krylov–Schur starts from a fixed initial vector unless you set one, so runs are repeatable. Loose `-eps_tol` and near-degenerate eigenvalues can make the reported value switch between neighbours, so use 1e-12 and a fixed `-eps_ncv`.
- Crossings are features, not bugs: "the k-th eigenvalue" is continuous but only piecewise smooth. If a smooth output is wanted, track one eigenvector (not planned here).
- Sources: https://slepc.upv.es, https://slepc.upv.es/download/, https://slepc.upv.es/download/distrib/slepc-3.25.2.tar.gz, https://slepc.upv.es/release/src/eps/tutorials/index.html, https://slepc.upv.es/release/src/eps/tutorials/ex9.c.html, https://slepc.upv.es/release/src/eps/tutorials/ex2.c.html, https://gitlab.com/slepc/slepc, https://api.anaconda.org/package/conda-forge/slepc, https://api.anaconda.org/package/conda-forge/slepc4py, https://prefix.dev/channels/conda-forge/packages/slepc, https://packages.ubuntu.com/noble/slepc-dev, https://packages.ubuntu.com/noble/python3-slepc4py, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/slepc/package.py

---

#### DifferentialEquations.jl

**What it is.** The SciML suite's umbrella package for solving ODEs, SDEs, DDEs, DAEs and more in Julia, with hundreds of solvers (explicit RK, Rosenbrock, BDF, IMEX, symplectic, and wrappers for Sundials and others). License MIT. Current release **v8.1.1 (2026-08-27)**. v8.0.0 (2026-04-27) had "many breaking changes": the umbrella now depends only on `OrdinaryDiffEq` (v7), `SciMLBase` and a few helpers, so SDE, DDE and other solvers are separate packages, and the docs import sub-packages (`import OrdinaryDiffEqRosenbrock as ODERosenbrock`). It requires Julia ≥ 1.10. Examples: the docs at https://docs.sciml.ai/DiffEqDocs/stable/ have about 10 tutorials (getting started, stiff equations, SDEs, DDEs, DAEs, BVPs, ...) and about 8 worked examples (classical physics, conditional dosing, Kepler, outer solar system, maxima and minima of solutions, spiking neurons, Beeler–Reuter, heat equation). PDEs through MethodOfLines.jl (v0.11.13, 2026-06-25) have their own tutorials (e.g. https://docs.sciml.ai/MethodOfLines/stable/tutorials/brusselator/).
Fit: good numerically (smooth, fast, adaptive and deterministic), but awkward operationally. **Julia's start-up and compile latency is paid by every run**, because EMA's command-line model starts one process per run. See the recipe for how to keep it down.

**Install on an Intel Mac.** Julia still ships official macOS x86_64 binaries: 1.13.0 (released 2026-09-09) has a `mac/x64` tarball and DMG, and the support page lists macOS x86-64 as Tier 1 **(the page may lag behind the 1.13 release; unconfirmed for later versions)**. juliaup v1.22.7 (2026-09-11) has an `x86_64-apple-darwin` build. conda-forge also has `julia` 1.13.0 for osx-64, but juliaup is the official route. Pin **Julia 1.12.7** rather than 1.13.0, since the SciML docs were last built with 1.12.6. Moving to 1.13 is a later, deliberate step.
1. Install juliaup without changing shell start-up files, with 1.12.7 as the default channel:
   ```bash
   curl -fsSL https://install.julialang.org | sh -s -- --yes --add-to-path=no --default-channel 1.12.7
   ~/.juliaup/bin/juliaup status
   ```
2. Find the real binary, to use by absolute path in `model.json`:
   ```bash
   ~/.juliaup/bin/julia +1.12.7 -e 'println(joinpath(Sys.BINDIR, "julia")); println(VERSION)'
   ```
3. Create a pinned project for the EMA models (a `Project.toml` and `Manifest.toml` that you keep):
   ```bash
   mkdir -p ~/pde/ema-diffeq && cd ~/pde/ema-diffeq
   ~/.juliaup/bin/julia +1.12.7 --project=. -e 'using Pkg; Pkg.add([
       Pkg.PackageSpec(name="DifferentialEquations", version="8.1.1"),
       Pkg.PackageSpec(name="OrdinaryDiffEqTsit5"),
       Pkg.PackageSpec(name="OrdinaryDiffEqRosenbrock")]); Pkg.precompile()'
   ```
   The sub-package names come from the v8 docs, and the exact set each example needs is **(unconfirmed until the tutorial code is run)**. Precompiling takes several minutes, and the depot (`~/.julia`) grows by 1–3 GB *(estimate)*.
4. Check:
   ```bash
   ~/.juliaup/bin/julia +1.12.7 --project=$HOME/pde/ema-diffeq -e 'import OrdinaryDiffEqTsit5 as T; f(u,p,t)=1.01u; s=T.solve(T.ODEProblem(f,0.5,(0.0,1.0)),T.Tsit5(); reltol=1e-8); println(s.u[end])'
   ```
   Expect about `1.3728` (0.5·e^1.01), and time it: the first run shows the latency.

Known problems: juliaup's `julia` is a launcher that picks the version from `+channel`, from a directory override, or from the project's `Manifest.toml` (`julia_version`). For EMA, use the real binary's absolute path so nothing implicit changes the version. Homebrew isn't needed.
Sources: https://julialang.org/downloads/, https://julialang.org/downloads/manual-downloads/, https://julialang.org/downloads/support/, https://github.com/JuliaLang/juliaup (README: installer flags, `+channel`, manifest-based version selection), https://github.com/JuliaLang/juliaup/releases, https://julialang-s3.julialang.org/bin/versions.json, https://github.com/SciML/DifferentialEquations.jl/releases, https://api.anaconda.org/package/conda-forge/julia

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: juliaup, the same commands (the installer has an x86_64 Linux build), with Julia 1.12.7 and the same project. Copy `Project.toml` and `Manifest.toml` from the Mac and run `Pkg.instantiate()`, so both machines resolve the same package versions.
2. Docker fallback: the official image `julia:1.12.7` (Docker Hub library image; pin by digest). Mount a named volume for the depot, or each container recompiles. Container start-up adds to Julia's own latency, so prefer native.
3. conda-forge `julia` (1.13.0 linux-64) is a third option, but it isn't the official build.
4. Check: as on the Mac.
Sources: https://github.com/JuliaLang/juliaup, https://hub.docker.com/_/julia, https://api.anaconda.org/package/conda-forge/julia

**Preparing the examples for EMA.** The recipe:
- **A driver `run.jl`** next to `model.json` reads a `key = value` deck rendered from a template (like `examples/cantera/ignition.template`), builds the tutorial's problem with those parameters, solves it with tight tolerances (`reltol = 1e-10, abstol = 1e-12`), and prints `EMA_OUTPUT <value>` with `@printf("%.12e")` (or `println(repr(x))`). It exits non-zero unless `SciMLBase.successful_retcode(sol)`, so a solver failure is a failed run.
- **The command** is `[<absolute julia 1.12.7 binary>, "--startup-file=no", "--project=$EMA_BASE_DIR", "run.jl", "deck.txt"]`. EMA expands `$EMA_BASE_DIR` inside an argument. List `Project.toml` and `Manifest.toml` as static files, so the version hash covers the package versions.
- **env**: `JULIA_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`. Leave `JULIA_DEPOT_PATH` at its default so runs share the compiled cache.
- **Latency is the main cost.** Each run pays process start plus package loading (about 1–3 s for OrdinaryDiffEq sub-packages with Julia's package images) plus compiling `solve` for this problem type (from well under a second for Tsit5 on a small ODE to tens of seconds for a stiff PDE with sparse Jacobians) *(all estimates; measure with `ema profile`)*. Three remedies:
  1. **Import only the sub-packages you need** (`OrdinaryDiffEqTsit5`, `OrdinaryDiffEqRosenbrock`), not the whole umbrella.
  2. **A sysimage** built with PackageCompiler.jl v2.4.3 (2026-09-18), with `run.jl` as the precompile workload: `create_sysimage(["OrdinaryDiffEqRosenbrock"]; sysimage_path="ema_diffeq.so", precompile_execution_file="run.jl")`, then add `"--sysimage=ema_diffeq.so"` (a relative name next to `model.json`) to the command. That removes almost all per-run compile time. The sysimage is a few hundred MB *(estimate)*, and because the command names it, EMA hashes it. That makes a new model version whenever it is rebuilt, which is correct, but the hash costs a little time.
  3. **A persistent Julia process** (e.g. DaemonMode.jl) would remove start-up, but it breaks EMA's model: one fresh process per run in its own directory, a scrubbed environment, and a timeout that kills the run. A crash or leaked state would affect later runs. Don't use it for EMA. If latency still dominates after a sysimage, it is a reason for a future EMA feature (a persistent-worker command-line model), not for a workaround.
- Chaotic systems (Lorenz) are deterministic on one machine and one Julia/package version, but a long-time output is a very rough function of the inputs. EMA should see that as roughness, not noise (`repeat` shows zero).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Lorenz system, "Getting Started" (https://docs.sciml.ai/DiffEqDocs/stable/getting_started/) | the parameterized Lorenz example: p = [σ, ρ, β] = [10, 28, 8/3], u₀ = [1, 0, 0]; the tutorial uses tspan (0, 100) and (0, 1); here tspan (0, 150) with Tsit5 | `sigma` 10 [8, 12]; `rho` 28 [20, 35]; `beta` 2.6667 [2, 3] | time average of z over t ∈ [50, 150] (saveat 0.01) | `rho` dominant and increasing: z̄ = ρ − 1 exactly where the orbit settles on a fixed point, and close to it in the chaotic regime. A change of regime near ρ ≈ 24.74 (the subcritical Hopf point), where `curve1d` on `rho` should show a kink or jump. In the chaotic regime the output is rough on fine scales (finite-time averages of a chaotic orbit), so `finite_diff` gradients are meaningless there and `fourier`'s fit is imperfect, while `repeat` shows zero noise: a deliberate test of EMA's roughness-versus-noise distinction | 2–5 s, almost all start-up; < 1 s with a sysimage *(estimate)* | command-line (julia binary + `run.jl` + deck) | regex `EMA_OUTPUT (\S+)` |
| Robertson (ROBER) stiff kinetics, "Differential Algebraic Equations" tutorial (https://docs.sciml.ai/DiffEqDocs/stable/tutorials/dae_example/) | mass-matrix DAE form of the Robertson equations, p = (k₁, k₂, k₃) = (0.04, 3e7, 1e4), u₀ = [1, 0, 0], tspan (0, 1e5), `Rodas5` with reltol = abstol = 1e-8 | `k1` 0.04 [0.01, 0.16] (log); `k2` 3e7 [3e6, 3e8] (log); `k3` 1e4 [1e3, 1e5] (log) | peak of y₂ over t (saveat on a log-spaced grid from 1e-6 to 1e5) | **a near power law** with a known answer: early on y₁ ≈ 1 and y₂ reaches a quasi-steady state with k₂y₂² ≈ k₁, so y₂,max ≈ sqrt(k₁/k₂) (3.65e-5 at the nominal values, which matches the classic peak). `linear_coeffs(log_output=True)` should find exponents close to +0.5 for k1 and −0.5 for k2, k3 near 0 (`negligible` or `possibly_negligible`), and `power_law` set | 3–10 s without a sysimage (Rodas5 and mass-matrix compile), about 1 s with *(estimate)* | command-line | regex |
| 2-D Brusselator PDE, "Solving Large Stiff Equations" (https://docs.sciml.ai/DiffEqDocs/stable/tutorials/advanced_ode_example/) | method-of-lines Brusselator on a periodic 32 × 32 grid (2,048 ODEs), forcing switched on at t = 1.1, tspan (0, 11.5); the tutorial's parameters A = 3.4, B = 1, α = 10; `KenCarp47` with a sparse (KLU) Jacobian | `A` 3.4 [3.0, 4.0]; `B` 1.0 [0.5, 1.5]; `alpha` 10 [2, 20] (log); grid fixed at N = 32 | spatial mean of U at t = 11.5 | the reaction terms put the system beyond its Hopf point, so U oscillates in time, and its value at a fixed final time depends on the phase: a non-monotone, wavy response in `A` and `B`, which `curve1d` should show as oscillation and `fourier` as slow spectral decay. `alpha` smooths spatial structure and matters less for the mean *(expected)* | 20–90 s without a sysimage (sparsity detection and KLU compile), 3–10 s with *(estimate)* | command-line (use a sysimage) | regex |

**Claude Code prompts.**

```text
Stage 1 (DifferentialEquations.jl, read-only check). I want to run DifferentialEquations.jl (v8.1.1) examples as EMA command-line models with Julia 1.12.7 via juliaup. Read-only: report OS and version, uname -m, whether juliaup or julia exist (which julia; juliaup status; julia --version), the size of ~/.julia if it exists, conda/mamba (note only), Docker, and free disk space. Don't install anything, and don't read .env. Recommend: juliaup (official, with an x86_64-apple-darwin build) installed with --add-to-path=no and default channel 1.12.7, a pinned project in ~/pde/ema-diffeq; conda-forge julia or the Docker image julia:1.12.7 only as fallbacks. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (DifferentialEquations.jl, install on the Intel Mac). Never install into EMA's .venv, never read .env, and don't edit my shell start-up files. Ask before running the juliaup installer (it downloads Julia, about 200-300 MB), before any sudo or Homebrew change, and before downloads over 1 GB. Steps: (1) curl -fsSL https://install.julialang.org | sh -s -- --yes --add-to-path=no --default-channel 1.12.7; (2) report the real binary path: ~/.juliaup/bin/julia +1.12.7 -e 'println(joinpath(Sys.BINDIR, "julia"))'; (3) in ~/pde/ema-diffeq, with --project=., Pkg.add DifferentialEquations at version 8.1.1 plus OrdinaryDiffEqTsit5 and OrdinaryDiffEqRosenbrock, then Pkg.precompile(); report the time and the resolved versions (Pkg.status()); (4) check: solve du/dt = 1.01u, u(0) = 0.5 on (0, 1) with Tsit5 and print u(1) (expect about 1.3728), and time a cold run. Stop at the first error and report the command and its output. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (DifferentialEquations.jl, install on AWS Ubuntu 24.04 x86_64; I'm ssh'd in). The same as the Mac: juliaup with --yes --add-to-path=no --default-channel 1.12.7 (ask first), then create ~/pde/ema-diffeq from the Project.toml and Manifest.toml I copy from my Mac (ask me for them; if I have none, Pkg.add as on the Mac) and run Pkg.instantiate() and Pkg.precompile(). Never use EMA's .venv, and never read .env. Ask before any sudo. If juliaup fails, propose (don't run) the Docker image julia:1.12.7 pinned by digest with a named volume for the depot. Check as on the Mac. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (DifferentialEquations.jl smoke test and latency). In a scratch directory outside the EMA repo, write a 20-line script (a scratch file, not in the repo) that solves the Robertson DAE from https://docs.sciml.ai/DiffEqDocs/stable/tutorials/dae_example/ (mass-matrix form, p = (0.04, 3e7, 1e4), tspan (0, 1e5), Rodas5, reltol = abstol = 1e-8) and prints the maximum of y2 over a log-spaced saveat grid. Run it three times as separate processes with the absolute julia 1.12.7 binary, --startup-file=no and --project=~/pde/ema-diffeq, and report each wall time and the printed value (expect about 3.6e-5). Then report how the time splits: time julia -e 'import OrdinaryDiffEqRosenbrock' alone vs the full script. Don't build a sysimage yet. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (DifferentialEquations.jl, prepare ROBER for EMA). Plan mode first; show me the plan before writing anything. Read docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/ (deck + driver + regex). Create examples/diffeq/rober/: run.jl reads a key = value deck (rober.template: k1 = $k1, ...), solves the tutorial's mass-matrix Robertson problem with Rodas5 (reltol 1e-10, abstol 1e-12), prints "EMA_OUTPUT %.12e" of max y2 over a log-spaced saveat grid from 1e-6 to 1e5, prints the Julia and package versions to stdout, and exits 1 unless the retcode is successful. Copy Project.toml and Manifest.toml from ~/pde/ema-diffeq into the model directory and list them as static files. model.json: command [<absolute julia 1.12.7 binary>, "--startup-file=no", "--project=$EMA_BASE_DIR", "run.jl", "rober.deck"]; inputs k1 0.04 [0.01, 0.16], k2 3e7 [3e6, 3e8], k3 1e4 [1e3, 1e5], all scale log; env JULIA_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1; timeout_s 300. Check by hand that the nominal value is close to sqrt(0.04/3e7) = 3.65e-5. Then `.venv/bin/ema profile examples/diffeq/rober/model.json -n 5` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (DifferentialEquations.jl, prepare Lorenz). Plan mode first. Create examples/diffeq/lorenz/ like examples/diffeq/rober/: run.jl builds the parameterized Lorenz problem from https://docs.sciml.ai/DiffEqDocs/stable/getting_started/ (u0 [1, 0, 0]) with sigma, rho, beta from the deck, tspan (0, 150), Tsit5 with reltol 1e-10 and abstol 1e-12, saveat 0.01, and prints "EMA_OUTPUT %.12e" of the mean of z over t in [50, 150]. Inputs sigma 10 [8, 12], rho 28 [20, 35], beta 2.6667 [2, 3]. Same command, static files, env and timeout as stage 4.1. Check by hand that rho = 20 gives about 19 (the fixed point z = rho - 1) and report the nominal value. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 (DifferentialEquations.jl, prepare the 2-D Brusselator PDE, with a sysimage). Plan mode first. Create examples/diffeq/brusselator/: run.jl reproduces the problem of https://docs.sciml.ai/DiffEqDocs/stable/tutorials/advanced_ode_example/ (N = 32, periodic, forcing from t = 1.1, tspan (0, 11.5)) with A, B, alpha from the deck, solved with KenCarp47 and the sparse-Jacobian setup the tutorial uses (add whatever sub-packages it imports to a separate project in ~/pde/ema-diffeq-pde, and report them). Output: "EMA_OUTPUT %.12e" of the spatial mean of U at t = 11.5. First profile without a sysimage (`ema profile ... -n 3`). Then ask me before building a sysimage with PackageCompiler (it takes minutes and several hundred MB): create_sysimage with run.jl as the precompile workload, saved as ema_diffeq_pde.so in the model directory and passed as "--sysimage=ema_diffeq_pde.so". Profile again and report both times. Inputs A 3.4 [3.0, 4.0], B 1.0 [0.5, 1.5], alpha 10 [2, 20] scale log; timeout_s 600. Stop and report; don't run a campaign.
```

```text
Stage 5 (DifferentialEquations.jl, first campaign). For examples/diffeq/rober/model.json, write campaign.json with repeat (n_points 2, replicates 2), linear_coeffs with log_output true (n 64), and morris (n_traj 6). Report the run count and time from `.venv/bin/ema estimate` (the time is mostly Julia start-up), and ask me before `ema run`. Then report: repeatability; the exponents and their intervals, the CV R^2 and whether power_law is set; which inputs are negligible. Expected: exponents about +0.5 for k1 and -0.5 for k2, k3 negligible or possibly negligible. Suggest (don't run) curve1d on rho for examples/diffeq/lorenz (expected: a change of regime near rho = 24.74, rough above it). Stop and report.
```

```text
Stage 6 (DifferentialEquations.jl troubleshooting). An EMA Julia model in examples/diffeq/<example> fails or is slow. Diagnose read-only first, from stdout.txt, stderr.txt and ema_run.json in the run directory, and by running the command by hand: (a) "could not start": the julia path in model.json is the juliaup launcher or wrong; use the real binary; (b) "Package X not found in current path" or precompiling on every run: the --project path, missing static Project.toml/Manifest.toml, or a JULIA_DEPOT_PATH that differs for EMA's runs; (c) every run slow: measure start-up vs load vs compile (time julia -e 'import ...'); propose a sysimage; (d) timeouts on the first runs only: precompilation after a package change; run Pkg.precompile() once by hand; (e) retcode Unstable/MaxIters: a real solver failure at extreme inputs (a failed run), or tolerances too tight for the step limit; (f) repeats that differ: threads (JULIA_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1) or a changed Manifest; (g) a sysimage error after a Julia or package update: rebuild it. Report the cause and propose a fix; change nothing without my OK. Stop and report.
```

**Gotchas and sources.**
- License: MIT for DifferentialEquations.jl, OrdinaryDiffEq.jl and MethodOfLines.jl. Julia itself is MIT.
- Parallelism: set `JULIA_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. Sparse and stiff solvers otherwise use BLAS threads, and runs would compete with EMA's `-j N`.
- Determinism: adaptive solvers are deterministic for a fixed Julia, package set and CPU. Pin the `Manifest.toml`, keep it among the model's static files so the hash covers it, and print the versions in every run. Chaotic outputs differ between machines (and after package updates) at long times, even though `repeat` shows none of it on one machine. Stochastic problems (SDEs, separate packages in v8) would need a seed: EMA passes `EMA_REPLICATE`, which `run.jl` can read with `ENV["EMA_REPLICATE"]` to seed each run.
- Run time: dominated by per-process start-up and compilation, not by the solve. Measure with `ema profile`, and use a sysimage for anything stiff or large. A Sobol campaign of 1,536 runs at 3 s each is about 1.3 hours serial, and a sysimage can halve that or better *(estimate)*.
- Version pitfalls: v8 split the umbrella. Tutorial code written for v7 (`using DifferentialEquations` giving every solver) may need sub-package imports. Julia 1.13 is new, so stay on 1.12.7 until SciML's docs build with 1.13.
- Sources: https://docs.sciml.ai/DiffEqDocs/stable/, https://docs.sciml.ai/DiffEqDocs/stable/getting_started/, https://docs.sciml.ai/DiffEqDocs/stable/tutorials/dae_example/, https://docs.sciml.ai/DiffEqDocs/stable/tutorials/advanced_ode_example/, https://docs.sciml.ai/MethodOfLines/stable/tutorials/brusselator/, https://github.com/SciML/DifferentialEquations.jl/releases, https://github.com/SciML/DifferentialEquations.jl/blob/master/Project.toml, https://github.com/SciML/OrdinaryDiffEq.jl, https://github.com/SciML/MethodOfLines.jl/releases, https://github.com/JuliaLang/PackageCompiler.jl/releases, https://github.com/JuliaLang/juliaup, https://github.com/JuliaLang/juliaup/releases, https://julialang.org/downloads/, https://julialang.org/downloads/manual-downloads/, https://julialang.org/downloads/support/, https://julialang-s3.julialang.org/bin/versions.json, https://hub.docker.com/_/julia, https://api.anaconda.org/package/conda-forge/julia

---

### 4.6 CFD, adaptive mesh refinement, plasma, multiphase, and subsurface codes: Nek5000/NekRS, AMReX, SAMRAI, WarpX, MFiX, PFLOTRAN

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions and platform claims were read on 2026-09-24 from the GitHub release APIs, the anaconda.org file lists for conda-forge, Bitbucket, Docker Hub, the Spack package recipes, and each project's documentation. **(unconfirmed)** marks what I could not check; every run time is an *(estimate)* to confirm with `ema profile`. Facts common to the group:

- **These are big HPC codes.** All six are built for MPI clusters, and four of them (NekRS, AMReX, WarpX, SAMRAI) also target GPUs. Each still has a small serial case that fits EMA on a laptop: 2-D or 1-D, a coarse mesh, a few hundred steps, no plot files. The example tables say what that costs. MFiX is the exception: its useful cases take minutes to tens of minutes per run, so plan it for AWS.
- **Compiled per case.** Nek5000 compiles each case into its own `nek5000` binary (`makenek`), MFiX builds a `mfixsolver` per project (`build_mfixsolver --batch`), and AMReX and SAMRAI tutorials are compiled programs. Keep the binary, or a wrapper script, in the model directory so the version hash covers it (section 2).
- **ParmParse on the command line.** AMReX and WarpX read `key = value` inputs files through AMReX's ParmParse, and any argument after the inputs file overrides a key (`main3d.gnu.ex inputs hydro.cfl=0.9`). So EMA passes inputs as arguments such as `"adv.cfl=$cfl"`, with no template and no `$$` escaping. Source: https://amrex-codes.github.io/amrex/docs_html/Basics.html ("Overriding Parameters with Command-Line Arguments").
- **Adaptive mesh refinement makes outputs piecewise smooth.** Regridding decisions (tag thresholds, blocking factors) change discretely with the inputs, so AMR outputs have small jumps that `nonsmooth` and `curve1d` will find. Two examples below use the AMR cell count as an output on purpose: it is piecewise constant.
- **Particle and bubbling-bed codes are chaotic, not random.** A WarpX run with a fixed seed, or an MFiX run, repeats bit for bit in serial *(unconfirmed for MFiX)*, so `repeat` alone reports no noise. But a tiny change of input moves the trajectory, and the output then behaves like noise across the input box. Seed each replicate from `EMA_REPLICATE` where the code has a seed (WarpX `warpx.random_seed`), average over long windows, and pass `output_noise` measured by `repeat` to the shape diagnostics.
- **`EMA_REPLICATE` is an environment variable, not a template name.** Templates and arguments see only the inputs, `$EMA_PYTHON`, `$EMA_BASE_DIR` and `$EMA_WORKDIR` (`src/ema/core/models/cli.py`). A code that takes its seed as an argument needs a small wrapper script in the model directory that reads `EMA_REPLICATE` and adds the argument.
- **AWS instance.** A `c7i.2xlarge` (8 vCPU, 16 GB) runs every laptop-size example below with `-j 8`. Use a `c7i.4xlarge` or larger for MFiX and the WarpX capacitive discharge, where one run takes minutes. Add 50 GB of gp3 disk for the PETSc and SAMRAI source builds.
- **Homebrew is not used on the Intel Mac** (section 3). Every Intel-Mac route below uses Miniforge (conda-forge only) for compilers, MPI and libraries, or Docker Desktop.

---

#### Nek5000 (and NekRS)

**What it is.** Nek5000 is Argonne's spectral-element solver for incompressible and low-Mach flow, heat transfer and scalar transport. It is written in Fortran 77 with some C, and licensed under a BSD-style license (the `LICENSE` file: "Redistribution and use in source and binary forms, with or without modification..."). The last tagged release is **v19.0 (2019-12-28)**, but the project now says: "We now recommend using the latest master branch from github rather than the V19 release" (the master branch was last pushed 2026-09-15; `makenek` reports version 19.0.1). Examples live in the separate **NekExamples** repository (https://github.com/Nek5000/NekExamples, about 40 cases: `eddy_uv`, `kovasznay`, `rayleigh`, `turbChannel`, `blasius`, `lowMach_test`, ...), and the documentation has six tutorials (https://nek5000.github.io/NekDoc/tutorials.html: fully developed laminar flow, periodic hill, conjugate heat transfer, ...). A case is a `.par` (or older `.rea`) parameter file, a `.re2` mesh, a `.ma2` partition, a `SIZE` file and a `.usr` Fortran file of user routines, compiled together by `makenek <case>`.
**NekRS** (https://github.com/Nek5000/nekRS, BSD-3-Clause, **v26.0, 2026-01-27**) is its GPU successor (C++, OCCA backends CUDA, HIP, DPC++ and SERIAL). Its release notes say "Code is not fully optimized on CPUs", and every case JIT-compiles OCCA kernels at start-up. **Onboard Nek5000, not NekRS.** Nek5000 runs serially on a laptop CPU (`MPI=0`), reads `.par` values at run time without recompiling, and uses the same case layout and `.usr` concepts. NekRS makes sense only on an AWS GPU instance (for example g5/g6 with CUDA), and only once the Nek5000 models work. That is not planned here.
The fit is unusual in one way: the case, including the `.usr` file, is compiled once into a binary, and the inputs must reach it at run time. Put them in the `.par` file (physical properties, `dt`, `numSteps`, and `userParam01`–`userParam20`, which the `.usr` reads as `uparam(i)`), or in the `.rea` parameter lines for the older examples. A change to `.usr` or `SIZE` needs a rebuild.

**Install on an Intel Mac.** Nek5000 needs a C compiler, gfortran and GNU make; MPI is optional (`MPI=0` builds a serial binary with a dummy MPI). There is no conda-forge or Homebrew package of Nek5000 (anaconda.org has no `nek5000`), so it is built from source with compilers from conda-forge. conda-forge builds `gfortran` for osx-64 (16.2.0, uploaded 2026-09-24).
1. Install Miniforge (osx-64) if there is no conda (section 3).
2. Create a compiler env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-nek -c conda-forge c-compiler fortran-compiler make cmake
   ```
3. Get the source at a pinned master commit, and the examples:
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone https://github.com/Nek5000/Nek5000.git && git -C Nek5000 rev-parse HEAD   # record the commit
   git clone https://github.com/Nek5000/NekExamples.git && git -C NekExamples rev-parse HEAD
   ```
4. Build the mesh tools once (genbox and genmap need no X11):
   ```bash
   conda activate ema-nek
   cd ~/src/Nek5000/tools && ./maketools genbox && ./maketools genmap
   ```
5. Check with a serial build of `eddy_uv` in a scratch copy:
   ```bash
   export PATH=$HOME/src/Nek5000/bin:$PATH
   cp -r ~/src/NekExamples/eddy_uv ~/scratch/eddy_uv && cd ~/scratch/eddy_uv
   genmap          # answer: eddy_uv, then the default tolerance
   FC=gfortran CC=clang MPI=0 NEK_SOURCE_ROOT=$HOME/src/Nek5000 makenek eddy_uv
   echo "eddy_uv" > SESSION.NAME && echo "$PWD/" >> SESSION.NAME && ./nek5000 > logfile 2>&1; tail logfile
   ```
Known problems: `makenek` reads `FC`, `CC` and `MPI` from the environment or from its own edited copy. The first build may fetch third-party code such as gslib into `3rd_party/` **(unconfirmed)**, so run it with network access once. Recent gfortran versions reject some argument mismatches in old Fortran; if the build fails on "Type mismatch", add `FFLAGS="-fallow-argument-mismatch"` **(unconfirmed whether master already sets it)**. `eddy_uv` ships only a `.rea` and `.map`, and the quickstart runs `genmap` first; the `.rea` format still works on master **(unconfirmed for every example)**.
Sources: https://nek5000.github.io/NekDoc/quickstart.html, https://github.com/Nek5000/Nek5000/blob/master/bin/makenek, https://github.com/Nek5000/Nek5000/blob/master/core/makefile.template (the `MPI=0` dummy), https://anaconda.org/conda-forge/gfortran.

**Install on AWS (Ubuntu 24.04 EC2).**
1. apt compilers (the route the quickstart documents; Ubuntu 24.04 has gfortran 13):
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential gfortran cmake git
   ```
2. Clone Nek5000 and NekExamples at the same commits as on the Mac, build genbox and genmap, and build `eddy_uv` with `FC=gfortran CC=gcc MPI=0` as in steps 3–5 above.
3. Fallback: the same conda env as on the Mac (Linux installer), if the apt gfortran shows the argument-mismatch problem.
4. Spack has `nek5000` 17.0, 19.0 and develop, but it adds nothing over a source clone here.
Sources: https://nek5000.github.io/NekDoc/quickstart.html, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/nek5000/package.py.

**Preparing the examples for EMA.** The recipe for each case:
- Copy the case into `examples/nek5000/<case>/`.
- Add to `userchk` in the `.usr` one scalar, computed at the last step (`istep.eq.nsteps`) with Nek's global reductions (`glmax`, `glsc2`, `surface_int`), and printed by `nid.eq.0` as `EMA_OUTPUT <value>`.
- Build the binary once with `MPI=0` inside the model directory, so the version hash covers it.
- Make the `.par` (or `.rea`) file a template: the inputs replace property values or `userParamNN` lines. Neither format uses `$`, but check the `.usr` comments you template, if any.
- `SESSION.NAME` becomes a two-line template, `<case>` and `$EMA_WORKDIR/`.
- The `.re2`, `.ma2` (or `.map`) and `SIZE` files are static files.
- The command is `["nek5000"]`, run serially, parsed with a regex on stdout.
- Set `writeInterval` large (or `IOSTEP` 0 in a `.rea`), so no field files are written.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Fully developed laminar flow, tutorial `fdlf` (https://nek5000.github.io/NekDoc/tutorials/fdlf.html; the `.box`, `.par` and `userbc`/`useric` are in the page) | 2-D channel half (symmetry at y = 0, heated wall at y = 0.005 m), 50 × 5 elements from genbox; inlet profile and temperature from the analytic solution | `userParam02` mean velocity U_m 0.5 [0.1, 1.0] m/s; `userParam03` wall heat flux q'' 300 [50, 1000] (log) W/m²; `userParam04` inlet temperature T_in 10 [0, 40] °C; `conductivity` λ 0.025 [0.015, 0.05] W/m·K (`userParam01` H fixed at 0.01, since it must match the mesh) | wall temperature at the outlet, x = 0.2 m (added to `userchk`) | exactly affine in T_in and linear in q'' (analytic: T_w − T_b = q''H/(2λ)·(1 − 39/280) and T_b(x) = T_in + 2q''x/(U_m ρc_p H)), so `linear_coeffs` fits T_in and q'' exactly; ∝ 1/U_m in the bulk term and ∝ 1/λ in the wall term, with a q'' × U_m and q'' × λ interaction; no failures | 20 s–2 min with `numSteps` cut to 5000 (the flow crosses the 0.2 m channel in 0.4 s) *(estimate)* | cli (binary in model dir) | regex `EMA_OUTPUT (\S+)` on stdout |
| Walsh eddies, `eddy_uv` (https://github.com/Nek5000/NekExamples/tree/master/eddy_uv) | 2-D doubly periodic Navier–Stokes with an exact decaying-vortex solution plus a translation (u0, v0); `userchk` already prints the error against the exact solution | `p12` time step DT 1e-4 [2e-5, 1e-3] (log); `p02` viscosity (as −Re) Re 20 [5, 200] (log); `p96` u0 0.5 [0, 2]; `p97` v0 0.3 [0, 2] (the case's own values of u0 and v0 are **(unconfirmed)**; read them from the `.rea`) | max x-velocity error at the last step (the third number on the `X err` line) | a power law in DT: `linear_coeffs(log_output=True)` should find the exponent equal to the time-integration order (2 or 3, **(unconfirmed)** which is the default) until spatial error floors it (a kink in `curve1d`); a CFL failure region at large DT × (u0, v0); v0 and u0 nearly symmetric | 10–60 s for the 1000 steps *(estimate)* | cli | regex `(?m)^\s*\d+\s+\S+\s+(\S+).*X err` on stdout |
| Rayleigh–Bénard, `rayleigh/ray1` (https://github.com/Nek5000/NekExamples/tree/master/rayleigh) | 2-D convection in a 9 × 1 box, 10 elements in x, Ra = Rc(1 + ε) with Rc = p76 and ε = p75 | `p75` ε 0.2 [−0.2, 1.0]; `p02` Prandtl number 1 [0.5, 7] (log); keep Rc = 1707.762 | max vertical velocity at the last step (the case already prints `umax`, `vmax`) | a bifurcation at ε = 0: zero below onset, growing like √ε above (a kink that `nonsmooth` and `curve1d` should find); near onset the growth is slow, so at a fixed end time the kink is smeared and runs near ε = 0 are far from steady; Pr weak at steady state | 1–5 min with `NSTEPS` cut from 75000 to about 5000 *(estimate)* | cli | regex on the `vmax` column of the last `userchk` line |

**Claude Code prompts.**

```text
Stage 1 — check the machine for Nek5000 (read-only). I want to onboard Nek5000 (master branch; NOT NekRS) examples into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, Homebrew version (don't use it), gfortran and cc on PATH and their versions, make --version, any MPI (mpif77, mpicc), git, free disk space, and whether ~/src/Nek5000 or ~/src/NekExamples already exist. Don't install anything, and don't read .env. Recommend a route: on the Intel Mac, a conda-forge env `ema-nek` with c-compiler, fortran-compiler, make and cmake, and a source clone of Nek5000 master built serially (MPI=0); on Ubuntu 24.04, apt build-essential and gfortran. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install Nek5000 on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-nek -c conda-forge c-compiler fortran-compiler make cmake`. Never install into EMA's .venv, never use Homebrew, and never read .env. Ask me before installing Miniforge, before any sudo, and before any download over 1 GB. Then clone https://github.com/Nek5000/Nek5000 and https://github.com/Nek5000/NekExamples into ~/src and report both commit hashes. In the env, build genbox and genmap with `./maketools genbox` and `./maketools genmap` in ~/src/Nek5000/tools. Check that ~/src/Nek5000/bin/genbox, genmap and makenek exist and that gfortran --version runs from the env. Stop at the first error and report the command and its output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install Nek5000 on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before `sudo apt-get install -y build-essential gfortran cmake git`. Then clone Nek5000 and NekExamples into ~/src at the commits I give you (from the Mac; ask me for them), and build genbox and genmap with maketools. Never install into EMA's .venv, and never read .env. If the apt gfortran fails to build, report and propose (don't run) the conda env `ema-nek` from the Mac instructions. Check: genbox, genmap and makenek exist, and gfortran --version. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — Nek5000 smoke test. In a scratch directory outside the EMA repo, copy ~/src/NekExamples/eddy_uv, run genmap (case eddy_uv, default tolerance), build it serially with `FC=gfortran CC=<the env's C compiler> MPI=0 NEK_SOURCE_ROOT=$HOME/src/Nek5000 makenek eddy_uv` (with the ema-nek env active on the Mac), write SESSION.NAME (line 1 `eddy_uv`, line 2 the directory's absolute path with a trailing slash), and run ./nek5000 > logfile. Time the run. Report: build success or the first error in build.log, the wall time, the last three "X err" lines of the logfile, and how many field files it wrote. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the Nek5000 fully developed laminar flow tutorial for EMA. Enter plan mode first and show me the plan. Source: https://nek5000.github.io/NekDoc/tutorials/fdlf.html (fdlf.box, fdlf.par, and the userbc/useric in the page; SIZE from core/SIZE.template with ldim=2 and the lelg the tutorial gives). In examples/nek5000/fdlf/: generate fdlf.re2 with genbox and fdlf.ma2 with genmap once; write fdlf.usr with the tutorial's routines plus a userchk that, at istep.eq.nsteps, computes the wall temperature at the outlet corner (x = 0.2, y = 0.005) and prints `EMA_OUTPUT <value, es22.14>` from nid 0; build the serial binary nek5000 in that directory with MPI=0 (a build.sh there that records the Nek5000 commit). Templates: fdlf.par with inputs um = 0.5 [0.1, 1.0] (userParam02), qpp = 300 [50, 1000] (userParam03, scale log), tin = 10 [0, 40] (userParam04), lam = 0.025 [0.015, 0.05] (conductivity); keep userParam01 = 0.01, numSteps 5000, dt 1e-4, and writeInterval larger than numSteps; SESSION.NAME with `fdlf` and `$EMA_WORKDIR/`. Static files: fdlf.re2, fdlf.ma2. Command ["nek5000"], output regex "EMA_OUTPUT (\S+)" on stdout, env OMP_NUM_THREADS=1, timeout_s 600. Follow docs/guides/input_deck_model.md, examples/beam/model_csv.json (static files) and examples/cantera/. Check by hand that the output at nominal matches the tutorial's analytic T_b(0.2) + q''H/(2λ)(1 − 39/280) to a few digits, and that doubling qpp doubles (output − tin). Then run `.venv/bin/ema profile examples/nek5000/fdlf/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the Nek5000 eddy_uv example. Plan mode first. Source: ~/src/NekExamples/eddy_uv (eddy_uv.rea, .usr, .map, SIZE). In examples/nek5000/eddy_uv/, build the serial binary once (MPI=0). Make eddy_uv.rea a template with inputs dt = 1e-4 [2e-5, 1e-3] (scale log) on the p12 line (keep its sign convention: read what a negative DT means in the NekDoc .rea reference and tell me), re = 20 [5, 200] (scale log) on the p02 line written as -$re, u0 on the p96 line and v0 on the p97 line (ranges [0, 2]; report the case's own values first). Set IOSTEP (p15) so no field files are written, and remove or keep the outpost call at the last step (tell me which). SESSION.NAME template as in 4.1; eddy_uv.map static. Output: regex on stdout for the third number of the last line ending in "X err". timeout_s 300. Check by hand that halving dt lowers the error by roughly 4x or 8x (report the ratio). Then `.venv/bin/ema profile examples/nek5000/eddy_uv/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the Nek5000 Rayleigh–Bénard example. Plan mode first. Source: ~/src/NekExamples/rayleigh (ray1.rea, ray0.usr or the .usr the README names for ray1, ray1.map, SIZE with lx1 = 12). In examples/nek5000/rayleigh/, build serially. Template the .rea: eps = 0.2 [-0.2, 1.0] on p75, pr = 1 [0.5, 7] (scale log) on p02; keep Rc = 1707.762 on p76, DT -0.02; cut NSTEPS (p11) from 75000 to 5000 and IOSTEP to 0 or above NSTEPS. The case's userchk prints istep, time, umax, vmax; parse vmax from the last such line with a regex. timeout_s 1200. Check by hand at eps = -0.1 (vmax should decay toward 0) and eps = 0.5 (vmax should grow and level off); report both final values and the wall time. Then `.venv/bin/ema profile examples/nek5000/rayleigh/model.json -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first Nek5000 campaign. For examples/nek5000/eddy_uv/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on dt (n 9), and linear_coeffs with log_output true. Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run` (suggest -j 4). After it runs, report: whether repeats are bit-identical (expected: yes, serial), the exponent of dt from linear_coeffs with its interval (expected: the scheme's order, 2 or 3), whether curve1d shows a kink where spatial error takes over, and any failed runs at large dt with large u0 or v0 (a CFL failure region). Suggest (don't run) morris with n_traj 6 next. Stop and report.
```

```text
Stage 6 — Nek5000 troubleshooting. An EMA Nek5000 model (examples/nek5000/<case>) fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt, SESSION.NAME and logfile, and the model directory's build.log: (a) "could not open SESSION.NAME" or a wrong case path: check the rendered SESSION.NAME has the case name and the run directory with a trailing slash; (b) missing .re2/.ma2/.map: static files not listed; (c) array-bound errors (lelg, lx1): SIZE doesn't fit the mesh, rebuild; (d) the run diverges or stops with a CFL message: expected at large dt, a failure region, check it is reproducible; (e) the regex doesn't match: print format (Fortran E vs ES) or nid; (f) slow runs: field files still being written (writeInterval/IOSTEP), or MPI=1 binary launched serially; (g) a change to .usr not taking effect: the binary wasn't rebuilt. Report the cause and a proposed fix. Ask before changing the env, the build, or model.json.
```

**Gotchas and sources.**
- License: Nek5000 BSD-style (Argonne), NekRS BSD-3-Clause. Fine as external programs.
- Parallelism: build with `MPI=0` and run one process per run; EMA's `-j N` gives the parallelism. Set `OMP_NUM_THREADS=1` anyway.
- Determinism: serial runs are deterministic. The pressure and velocity solves stop at tolerances (`[PRESSURE] residualTol`, `[VELOCITY] residualTol` in `.par`), so outputs move in tolerance-sized steps; tighten them to 1e-10 for `finite_diff`, or measure the roughness with a fine `curve1d`. Nek5000 has no random numbers in these cases, so `EMA_REPLICATE` changes nothing.
- Run time: the time step is limited by CFL; cutting `numSteps` is the main lever, but an output at a fixed end time must not depend on the step count (keep `dt × numSteps` fixed, or make the end time an input).
- Compile per case: any `.usr` or `SIZE` change needs `makenek` again, and a binary built with a different `lelg` fails on larger meshes. Keep `build.sh` in the model directory and record the Nek5000 commit in `model.json`'s description.
- Version: use master, pinned by commit; v19.0 is from 2019 and the docs say RANS and newer features are not well supported there.
- NekRS: GPU-first, "not fully optimized on CPUs", and JIT-compiles kernels at start-up (seconds to minutes per new case). Not recommended for EMA on a laptop.
- Sources: https://github.com/Nek5000/Nek5000, https://github.com/Nek5000/Nek5000/releases, https://github.com/Nek5000/Nek5000/blob/master/LICENSE, https://github.com/Nek5000/NekExamples, https://nek5000.github.io/NekDoc/quickstart.html, https://nek5000.github.io/NekDoc/tutorials.html, https://nek5000.github.io/NekDoc/tutorials/fdlf.html, https://nek5000.github.io/NekDoc/problem_setup/case_files.html, https://github.com/Nek5000/NekExamples/blob/master/eddy_uv/README.md, https://github.com/Nek5000/NekExamples/blob/master/rayleigh/README.md, https://github.com/Nek5000/nekRS, https://github.com/Nek5000/nekRS/releases, https://github.com/Nek5000/nekRS/tree/v26.0/examples, https://anaconda.org/conda-forge/gfortran, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/nek5000/package.py

---

#### AMReX

**What it is.** AMReX is a C++ framework (with Fortran interfaces) for block-structured adaptive mesh refinement on CPUs and GPUs, from LBNL, NREL and Argonne; WarpX, MFIX-Exa, Nyx and Pele are built on it. License: BSD-3-Clause-LBNL. Current release **26.09 (2026-09-01)**; AMReX releases monthly as YY.MM. It is a framework, not a solver, so the examples to onboard are the programs in the **amrex-tutorials** repository (https://github.com/AMReX-Codes/amrex-tutorials, no releases; last pushed 2026-07-08), which has about 80 `inputs` files across `ExampleCodes/` (Basic heat equation, AMR advection, EB compressible flow, linear solvers, particles, SUNDIALS, UQ) and `GuidedTutorials/`. Each tutorial reads an `inputs` file through ParmParse (`key = value`), and any key can be overridden on the command line. One tutorial, `ExampleCodes/UQ/HeatEquation`, was written for uncertainty quantification: its inputs file says "these are what we vary for UQ", and it ships a PyTUQ workflow. That makes AMReX a close fit.
Python bindings exist (**pyAMReX 26.09**, conda-forge), but the tutorials are C++ programs, so pyAMReX isn't needed.

**Install on an Intel Mac.** conda-forge builds `amrex` 26.09 and `pyamrex` 26.09 for osx-64 (anaconda.org, uploaded 2026-09-02/03). The conda `amrex` is an installed CMake library, while the tutorials' documented build is GNU make against an AMReX **source tree** (`AMREX_HOME`), and `ExampleCodes/UQ/HeatEquation` has only a `GNUmakefile`. So the recipe takes the compilers and make from conda-forge and the AMReX source from GitHub at tag 26.09.
1. Install Miniforge if there is no conda.
2. Create a compiler env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-amrex -c conda-forge cxx-compiler c-compiler fortran-compiler make cmake python=3.12
   ```
3. Get the sources:
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone --branch 26.09 --depth 1 https://github.com/AMReX-Codes/amrex.git
   git clone https://github.com/AMReX-Codes/amrex-tutorials.git && git -C amrex-tutorials rev-parse HEAD   # record the commit
   ```
4. Build the UQ heat equation, serial, no MPI, no OpenMP:
   ```bash
   conda activate ema-amrex
   cd ~/src/amrex-tutorials/ExampleCodes/UQ/HeatEquation
   make -j4 AMREX_HOME=$HOME/src/amrex COMP=llvm USE_MPI=FALSE USE_OMP=FALSE DIM=3
   ```
5. Check:
   ```bash
   ./main3d.llvm.ex inputs && tail -2 datalog.txt
   ```
Known problems: `COMP=llvm` selects clang (the AMReX build docs list `gnu, cray, ibm, intel, intel-llvm, intel-classic, llvm, pgi`); the executable name follows `main<DIM>d.<COMP>[.MPI].ex` **(unconfirmed exact suffix; use whatever `ls *.ex` shows)**. The AMReX docs' macOS section assumes Homebrew GCC; don't follow it on Intel. If `make` from macOS (3.81) is picked up instead of the env's, the build may fail; the env's `make` comes first on `PATH` when the env is active.
Sources: https://amrex-codes.github.io/amrex/docs_html/BuildingAMReX.html, https://github.com/AMReX-Codes/amrex/releases, https://anaconda.org/conda-forge/amrex, https://anaconda.org/conda-forge/pyamrex, https://github.com/AMReX-Codes/amrex-tutorials/tree/main/ExampleCodes/UQ/HeatEquation.

**Install on AWS (Ubuntu 24.04 EC2).**
1. apt compilers (no AMReX package in apt is needed):
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential gfortran git
   ```
2. Clone `amrex` at tag 26.09 and `amrex-tutorials` at the Mac's commit, then build with `COMP=gnu USE_MPI=FALSE USE_OMP=FALSE` (executables `main3d.gnu.ex`, `main2d.gnu.ex`).
3. Fallback: the same conda env as on the Mac. Spack also has `amrex` 26.09 (`spack install amrex@26.09 dimensions=3 ~mpi`), useful only for CMake-built tutorials.
Sources: https://amrex-codes.github.io/amrex/docs_html/BuildingAMReX.html, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/amrex/package.py.

**Preparing the examples for EMA.** No template is needed: copy the tutorial's `inputs` into the model directory as a static file and pass each EMA input as a ParmParse override after it, `["main3d.gnu.ex", "inputs", "diffusion_coeff=$D", ...]`. Keep the compiled executable in the model directory (so it is hashed), with a `build.sh` recording the AMReX tag and tutorials commit. Turn plot files off (`plot_int=-1`, `amr.plot_int=-1`), run serially (`USE_MPI=FALSE`, `USE_OMP=FALSE`), and read the output from `datalog.txt` or stdout with a regex.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `ExampleCodes/UQ/HeatEquation` (https://github.com/AMReX-Codes/amrex-tutorials/tree/main/ExampleCodes/UQ/HeatEquation), 3-D, 32³ cells, 100 steps of dt 5e-8 | explicit heat equation on a periodic unit cube from a Gaussian hot spot T = 1 + A exp(−r²/(2v)); writes max, mean, std and one cell's temperature to `datalog.txt` at the last step | `diffusion_coeff` D 400 [100, 700] (the tutorial's UQ workflow uses mean 400, s.d. 100); `init_amplitude` A 1 [0.5, 1.5]; `init_variance` v 0.01 [0.005, 0.015] | model 1: `max_temp`; model 2: `mean_temp` (same run, a second `model.json`) | `mean_temp` is conserved on a periodic box: exactly independent of D (negligible), affine in A, and ≈ 1 + A(2πv)^{3/2}; `max_temp` falls with D·t/v, so D × v interact and A enters linearly; smooth, no failures (explicit stability limit dt < dx²/(6D) ≈ 1.6e-4/D is far from dt = 5e-8 for D ≤ 700) | < 2 s *(estimate)* | cli (binary in model dir, overrides as args) | regex `(?m)^\s*(?P<value>\S+)\s+\S+\s+\S+\s+\S+\s*$` on `datalog.txt` (column 1 for max; shift the group for mean) |
| `ExampleCodes/Amr/Advection_AmrCore` (https://github.com/AMReX-Codes/amrex-tutorials/tree/main/ExampleCodes/Amr/Advection_AmrCore), `Exec/inputs`, built with DIM=2 (its GNUmakefile default) | scalar advection of a blob in a single-vortex velocity field, 64 × 64 base grid, 2 levels of refinement, subcycling and refluxing; tags cells where φ exceeds `adv.phierr` | `adv.phierr` level-0 threshold 1.01 [1.001, 1.2] (passed as `adv.phierr=$e0 1.1 1.5`); `adv.cfl` 0.7 [0.3, 0.9]; `stop_time` 0.5 [0.25, 1.0] (the tutorial's 2.0 is cut for speed) | number of cells advanced on level 2 at the last step (printed as `[Level 2 step N] Advanced M cells` with `amr.v = 1`) | piecewise constant in `phierr` (regridding decisions) with many small jumps: `nonsmooth` and `curve1d` should find them, and `repeat` shows none; a threshold above the blob's maximum removes level 2 entirely (a plateau at 0, or a missing line, which fails the parse); `cfl` changes the step count and the regrid times, so the output is rough in it | 5–30 s *(estimate)* | cli | regex `\[Level 2 step \d+\] Advanced (\d+) cells` on stdout (last match) |

**Claude Code prompts.**

```text
Stage 1 — check the machine for AMReX (read-only). I want to onboard AMReX 26.09 tutorials (amrex-tutorials: ExampleCodes/UQ/HeatEquation and ExampleCodes/Amr/Advection_AmrCore) into EMA as command-line models, built serially with GNU make. Run only read-only commands and report: OS and version, CPU architecture (uname -m), conda/mamba (Miniforge) and where, Homebrew version (don't use it), C++ and Fortran compilers on PATH, `make --version` (GNU make version), git, any MPI, free disk space, and whether ~/src/amrex or ~/src/amrex-tutorials exist. Don't install anything, and don't read .env. Recommend a route: Intel Mac, conda-forge env `ema-amrex` with cxx-compiler, c-compiler, fortran-compiler, make, cmake, and the AMReX source at tag 26.09; Ubuntu 24.04, apt build-essential and gfortran with the same sources. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install AMReX build tools on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-amrex -c conda-forge cxx-compiler c-compiler fortran-compiler make cmake python=3.12`. Never install into EMA's .venv, never use Homebrew, never read .env. Ask me before installing Miniforge, before any sudo, and before downloads over 1 GB. Clone https://github.com/AMReX-Codes/amrex at tag 26.09 (depth 1) and https://github.com/AMReX-Codes/amrex-tutorials into ~/src; report the tutorials commit. Check: in the env, `make --version` reports GNU make 4.x and `clang++ --version` runs. Stop at the first error and report the command and output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install AMReX build tools on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before `sudo apt-get install -y build-essential gfortran git`. Clone amrex at tag 26.09 and amrex-tutorials at the commit I give you (from the Mac) into ~/src. Never install into EMA's .venv, never read .env. If apt is not allowed, propose (don't run) the conda env from the Mac instructions. Check g++ --version and make --version. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — AMReX smoke test. In ~/src/amrex-tutorials/ExampleCodes/UQ/HeatEquation (Mac: with ema-amrex active, COMP=llvm; AWS: COMP=gnu), build with `make -j4 AMREX_HOME=$HOME/src/amrex USE_MPI=FALSE USE_OMP=FALSE DIM=3`. Run `./<the .ex file> inputs` and time it; then run it again with `diffusion_coeff=700` appended and confirm the command-line override took effect (the max_temp in datalog.txt changes). Report the executable name, both wall times, and the last line of datalog.txt from each run. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the AMReX UQ heat equation for EMA. Enter plan mode first and show me the plan. In examples/amrex/uq_heat/: a build.sh that builds ExampleCodes/UQ/HeatEquation from ~/src/amrex-tutorials against ~/src/amrex (tag 26.09) serially (USE_MPI=FALSE USE_OMP=FALSE DIM=3) and copies the .ex into this directory, recording the AMReX tag and tutorials commit; the tutorial's inputs copied as a static file with plot_int = -1. Two model.json files sharing the binary: model_max.json and model_mean.json. Command [<the .ex>, "inputs", "diffusion_coeff=$D", "init_amplitude=$A", "init_variance=$v"]; inputs D = 400 [100, 700], A = 1 [0.5, 1.5], v = 0.01 [0.005, 0.015]; output regex on datalog.txt matching the last data row (four numbers) and taking column 1 (max_temp) or column 2 (mean_temp); number_format ".10g"; env OMP_NUM_THREADS=1; timeout_s 60. Follow docs/guides/input_deck_model.md and examples/beam/model_args.json. Check by hand that mean_temp doesn't change when D goes from 100 to 700, and that max_temp does. Then `.venv/bin/ema profile examples/amrex/uq_heat/model_max.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the AMReX AMR advection tutorial. Plan mode first. Source: ExampleCodes/Amr/Advection_AmrCore (build in Exec/ with DIM=2, USE_MPI=FALSE, USE_OMP=FALSE; copy the .ex into examples/amrex/adv_amr/ with a build.sh). Static file: Exec/inputs with amr.plot_int = -1 and amr.chk_int = -1. Command [<the .ex>, "inputs", "adv.phierr=$e0 1.1 1.5", "adv.cfl=$cfl", "stop_time=$tstop"] (check in a scratch run that the space-separated value inside one argument is read as three numbers); inputs e0 = 1.01 [1.001, 1.2], cfl = 0.7 [0.3, 0.9], tstop = 0.5 [0.25, 1.0]. Output: regex `\[Level 2 step \d+\] Advanced (\d+) cells` on stdout, last match. timeout_s 300. Check by hand that e0 = 1.2 still produces level-2 lines (if not, tell me the largest e0 that does, and I'll narrow the range). Then `.venv/bin/ema profile examples/amrex/adv_amr/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first AMReX campaign. For examples/amrex/uq_heat/model_mean.json and model_max.json, write campaign_mean.json and campaign_max.json, each with repeat (n_points 2, replicates 2), morris (n_traj 8) and sobol (n_base 64). Use `.venv/bin/ema estimate` for both and report run counts and times (runs are shared through the cache: the second campaign should cost little); ask me before `ema run -j 4`. Report: repeats identical (expected), D flagged negligible for mean_temp (expected, with an interval), A's effect linear, and for max_temp the D × v interaction share from sobol. Suggest (don't run) linear_coeffs with log_output for mean_temp - 1 if I add that output. Stop and report.
```

```text
Stage 6 — AMReX troubleshooting. An EMA AMReX model (examples/amrex/<example>) fails or looks wrong. Diagnose read-only from the run directory (stdout.txt, stderr.txt, datalog.txt) and the model directory: (a) "ParmParse: unknown/unused" or the override ignored: misspelled key or a prefix (adv., amr.) missing; AMReX prints unused parameters at the end with amrex.v=1; (b) an override value with spaces split into several arguments: it must be one argument; (c) the binary not found or built with MPI (name contains .MPI.): rebuild with USE_MPI=FALSE; (d) FPE traps (amrex.fpe_trap_invalid): a real NaN, record it as a failure; (e) datalog.txt missing: nsteps 0 or a crash before the last step; (f) the level-2 regex doesn't match because no level 2 exists at that input: that is a real feature, but decide with me whether to report 0 instead (a python parser); (g) threads: OMP_NUM_THREADS. Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- License BSD-3-Clause-LBNL.
- Parallelism: build with `USE_MPI=FALSE USE_OMP=FALSE`. An MPI build run without `mpiexec` still works, but reductions (`sum`, `norm2`) would depend on the rank count.
- Determinism: these tutorials use no random numbers, and serial runs repeat exactly. AMR outputs are piecewise constant in the tag thresholds and CFL, so expect `nonsmooth` flags that are real.
- Run time: `nsteps`, `n_cell` and `max_level` are the levers. Don't make `n_cell` or `max_grid_size` an input: they change the discretization in jumps.
- Version: the tutorials track AMReX `development`; build against the matching monthly tag (26.09) and pin the tutorials commit. The tutorials' `CMakeLists.txt` route could use the conda-forge `amrex` library instead **(unconfirmed)**; the GNU make route is the documented one.
- Sources: https://github.com/AMReX-Codes/amrex, https://github.com/AMReX-Codes/amrex/releases, https://amrex-codes.github.io/amrex/docs_html/BuildingAMReX.html, https://amrex-codes.github.io/amrex/docs_html/Basics.html, https://github.com/AMReX-Codes/amrex-tutorials, https://github.com/AMReX-Codes/amrex-tutorials/tree/main/ExampleCodes/UQ/HeatEquation, https://github.com/AMReX-Codes/amrex-tutorials/tree/main/ExampleCodes/Amr/Advection_AmrCore, https://anaconda.org/conda-forge/amrex, https://anaconda.org/conda-forge/pyamrex, https://github.com/AMReX-Codes/pyamrex/releases, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/amrex/package.py

---

#### SAMRAI

**What it is.** SAMRAI (Structured Adaptive Mesh Refinement Application Infrastructure) is LLNL's C++ library for block-structured AMR applications, with Fortran kernels (generated with m4) in its examples and optional GPU support through RAJA and Umpire. License: LGPL-2.1. Current release **v4.6.0 (2026-09-08)**, tag `v-4-6-0` (the README still says "The current release is SAMRAI v. 4.0.1", which is stale). It is a library for building AMR codes, not a solver, so the fit with EMA is the weakest in this group: its only runnable programs are the test applications in `source/test/applications/` (`LinAdv`, `Euler`, `ConvDiff`, `Simple`, and `Stencil` with RAJA), each with a few `example_inputs/*.input` files and `test_inputs/` for the regression tests. There are 5 applications and about a dozen example inputs. They qualify because `LinAdv` and `Euler` are complete AMR hyperbolic solvers driven by one input file; what is awkward is the build (CMake with BLT, Fortran, m4, MPI and optional HDF5), and that none prints a scalar result, so the driver needs a small source edit.

**Install on an Intel Mac.** There is no conda-forge package (anaconda.org has no `samrai`) and no Homebrew route, and Spack's `samrai` stops at 4.5.0. Build from source with a conda-forge toolchain.
1. Install Miniforge if there is no conda.
2. Create the env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-samrai -c conda-forge cxx-compiler c-compiler fortran-compiler cmake make m4 mpich
   ```
3. Clone with the BLT submodule at the release tag:
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone --recursive --branch v-4-6-0 https://github.com/LLNL/SAMRAI.git samrai-4.6.0
   ```
4. Configure without HDF5 (it is only for VisIt output, and requires MPI), with the test applications, optimized:
   ```bash
   conda activate ema-samrai
   cmake -S ~/src/samrai-4.6.0 -B ~/src/samrai-build -DCMAKE_BUILD_TYPE=Release \
     -DENABLE_HDF5=OFF -DENABLE_SAMRAI_TESTS=ON -DENABLE_CHECK_ASSERTIONS=OFF -DENABLE_OPENMP=OFF \
     -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_Fortran_COMPILER=mpifort
   cmake --build ~/src/samrai-build -j4 --target linadv
   ```
5. Check (the executable's location in the build tree is **(unconfirmed)**; find it with `find ~/src/samrai-build -name linadv -type f`):
   ```bash
   cd "$(dirname "$(find ~/src/samrai-build -name linadv -type f | head -1)")" && ./linadv ~/src/samrai-4.6.0/source/test/applications/LinAdv/example_inputs/sphere.2d.input | tail -3
   ```
   With HDF5 off, set `viz_dump_interval = 0` in the input first.
Known problems: `ENABLE_MPI` is on by default, and turning it off is **(unconfirmed)** to work, so use MPICH and run the binary without `mpiexec` (MPICH allows a singleton run). The m4 step needs `m4` on `PATH`. The full library build takes 20–40 min on a laptop *(estimate)*.
Sources: https://github.com/LLNL/SAMRAI, https://github.com/LLNL/SAMRAI/releases, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/CMakeLists.txt (options), https://github.com/LLNL/SAMRAI/blob/v-4-6-0/cmake/thirdparty/SetupSAMRAIThirdParty.cmake (HDF5 requires MPI), https://github.com/LLNL/SAMRAI/blob/v-4-6-0/source/test/applications/LinAdv/CMakeLists.txt.

**Install on AWS (Ubuntu 24.04 EC2).**
1. apt toolchain:
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential gfortran cmake m4 git libopenmpi-dev openmpi-bin
   ```
2. Clone and configure as on the Mac (with `mpicc`/`mpicxx`/`mpifort` from Open MPI), and build the `linadv` and `euler` targets.
3. Fallback: Spack `samrai@4.5.0` (one release behind), or the conda env from the Mac.
Sources: https://github.com/LLNL/SAMRAI, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/samrai/package.py.

**Preparing the examples for EMA.** SAMRAI reads one input file (`./linadv <input>`) in its own nested `Name { key = value }` format, with `//` comments and no `$`. So:
- Copy the example input into a template and replace the values to vary with placeholders.
- Set `viz_dump_interval = 0` and `restart_interval = 0`.
- Copy the application's `main.cpp` into the model directory's build and add, after the time loop, a print of one scalar: the number of cells on the finest level (sum the boxes of `patch_hierarchy->getPatchLevel(finest)`; the method that counts cells, for example `getBoxLevel()->getGlobalNumberOfCells()`, is **(unconfirmed)**), or an integral of the solution. Print it as `EMA_OUTPUT <value>`.
- Build that copy against the SAMRAI build tree, and keep the binary in the model directory.
- Parse stdout with a regex. SAMRAI writes `pout` to stdout and `plog` to a log file named from `base_name`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `LinAdv`, `example_inputs/sphere.2d.input` (https://github.com/LLNL/SAMRAI/tree/v-4-6-0/source/test/applications/LinAdv) | 2-D linear advection of a disc (u = 80 inside, 5 outside), 30 × 20 base grid, up to 3 levels with ratio 4, 25 steps, gradient and shock tagging | `advection_velocity` x-component 2.0 [0.5, 4.0]; `grad_tol` 10 [2, 40] (log); `radius` 2.9 [1.5, 5.0]; `uval_inside` 80 [20, 160] | model 1: cells on the finest level at the end (added print); model 2: total ∫u dx (conserved up to boundary outflow) | cell count: piecewise constant, jumps in `grad_tol` and `radius` (regridding), `uval_inside` matters only through the tags (ratio to `grad_tol`: an interaction); ∫u: ≈ linear in `uval_inside` and ∝ radius², nearly independent of velocity until the disc leaves the domain | 1–5 s *(estimate)* | cli (rebuilt binary in model dir) | regex `EMA_OUTPUT (\S+)` on stdout |
| `Euler`, `example_inputs/step.2d.input` (https://github.com/LLNL/SAMRAI/tree/v-4-6-0/source/test/applications/Euler) | 2-D Euler "STEP" problem (inflow at Mach ≈ 3 over a step, γ = 1.4), 4th-order Godunov, approximate Riemann solver, pressure-gradient and shock tagging | `gamma` 1.4 [1.2, 1.67]; inflow `velocity` x-component 3.0 [1.5, 4.0] (both intervals); `grad_tol` 20 [5, 80] (log) | total cells on the finest level at the end, or the maximum density (added print) | shock position and strength vary smoothly with Mach number and γ, but the refined-cell count jumps (regridding); a regime change near Mach 1 if the range reaches it (no shock); possible failures (negative pressure) at the extremes | 30 s–5 min; cut `max_integrator_steps` and the base grid *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine for SAMRAI (read-only). I want to onboard SAMRAI v4.6.0 test applications (LinAdv, Euler) into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture, conda/mamba (Miniforge) and where, Homebrew version (don't use it), C/C++/Fortran compilers, cmake --version, m4 --version, any MPI (mpicc, mpicxx, mpifort, mpiexec --version), git, free disk space, and whether ~/src/samrai-4.6.0 exists. Don't install anything, and don't read .env. Recommend a route: Intel Mac, conda-forge env `ema-samrai` (cxx-compiler, c-compiler, fortran-compiler, cmake, make, m4, mpich) and a source build of tag v-4-6-0 with HDF5 off; Ubuntu 24.04, apt build-essential, gfortran, cmake, m4, libopenmpi-dev. Say plainly that SAMRAI is a library and its examples need a small source edit to print a scalar. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — build SAMRAI on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-samrai -c conda-forge cxx-compiler c-compiler fortran-compiler cmake make m4 mpich`. Never install into EMA's .venv, never use Homebrew, never read .env. Ask me before installing Miniforge, before any sudo, and before downloads over 1 GB. Clone https://github.com/LLNL/SAMRAI with --recursive at tag v-4-6-0 into ~/src/samrai-4.6.0. Configure in ~/src/samrai-build with CMAKE_BUILD_TYPE=Release, ENABLE_HDF5=OFF, ENABLE_SAMRAI_TESTS=ON, ENABLE_CHECK_ASSERTIONS=OFF, ENABLE_OPENMP=OFF and the env's mpicc/mpicxx/mpifort; build only the targets linadv and euler with -j4 (tell me the elapsed time). Check that both executables exist and report their paths. Stop at the first error and report the command and the last 40 lines of output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — build SAMRAI on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before `sudo apt-get install -y build-essential gfortran cmake m4 git libopenmpi-dev openmpi-bin`. Clone tag v-4-6-0 with --recursive into ~/src/samrai-4.6.0, configure as on the Mac (Release, HDF5 off, tests on, assertions off, OpenMP off, MPI compiler wrappers), and build the linadv and euler targets with -j8. Never install into EMA's .venv, never read .env. If the build fails, report and propose (don't run) the conda env from the Mac instructions or Spack samrai@4.5.0. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — SAMRAI smoke test. In a scratch directory, copy source/test/applications/LinAdv/example_inputs/sphere.2d.input, set viz_dump_interval = 0, and run the built linadv on it serially (no mpiexec), timed. Then do the same for Euler's example_inputs/step.2d.input with viz_dump_interval = 0 (if it runs longer than 10 minutes, stop it and report). Report the wall times, the last 10 lines of stdout, and which log files were written (plog, named from base_name). Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare SAMRAI LinAdv for EMA. Enter plan mode first and show me the plan. In examples/samrai/linadv/: copy LinAdv's main.cpp and add, after the time loop and before the hierarchy is freed, code that prints from rank 0 `EMA_OUTPUT <number of cells on the finest level, as an integer>` and `EMA_INTEGRAL <sum over the finest-covering cells of uval * cell volume, %.12e>` (find the right SAMRAI API calls in the v4.6.0 headers and tell me which you used); a CMakeLists.txt or build.sh that builds this copy with the other LinAdv sources against ~/src/samrai-build and puts the binary here; sphere.template from example_inputs/sphere.2d.input with viz_dump_interval = 0 and placeholders vx = 2.0 [0.5, 4.0] (first advection_velocity component), grad_tol = 10 [2, 40] (scale log), radius = 2.9 [1.5, 5.0], uin = 80 [20, 160]. Two model.json files: model_cells.json (regex "EMA_OUTPUT (\S+)") and model_integral.json (regex "EMA_INTEGRAL (\S+)"). Command [<binary>, "sphere.input"], env OMP_NUM_THREADS=1, timeout_s 120. Follow docs/guides/input_deck_model.md and examples/beam/. Check by hand that doubling uin roughly doubles the integral. Then `.venv/bin/ema profile examples/samrai/linadv/model_cells.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare SAMRAI Euler (2-D step). Plan mode first. As in 4.1, copy Euler's main.cpp into examples/samrai/euler_step/, add the finest-level cell-count print and a maximum-density print (EMA_OUTPUT and EMA_RHOMAX), and build it. Template from example_inputs/step.2d.input with viz_dump_interval = 0, and max_integrator_steps reduced so one run takes under a minute (tell me the value and the simulated end time). Inputs: gamma = 1.4 [1.2, 1.67], ux = 3.0 [1.5, 4.0] (both velocity entries of interval_0 and interval_1), grad_tol = 20 [5, 80] (scale log). Two model.json files (cells, rhomax), regex on stdout, timeout_s 600. Check by hand at ux = 1.5 and 4.0 and report both outputs and times. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first SAMRAI campaign. For examples/samrai/linadv/model_cells.json and model_integral.json, write campaign.json files with repeat (n_points 2, replicates 2), curve1d on grad_tol (n 15) and morris (n_traj 6); they share runs through the cache. Report `.venv/bin/ema estimate` run counts and times, and ask me before `ema run -j 4`. Report: repeats identical (expected), the jumps curve1d and nonsmooth find in the cell count (expected, at this resolution), whether the integral is smooth and nearly linear in uin, and morris's ranking for each output. Stop and report.
```

```text
Stage 6 — SAMRAI troubleshooting. An EMA SAMRAI model fails. Diagnose read-only from the run directory (stdout.txt, stderr.txt, the plog file named from base_name): (a) input parse errors (SAMRAI reports the line; a missing comma in a vector like advection_velocity, or a placeholder rendered in the wrong place); (b) VisIt/HDF5 errors: viz_dump_interval not 0 with HDF5 off; (c) MPI init failures when run without mpiexec: try MPICH's singleton mode, or check which MPI the binary links (otool -L / ldd); (d) "dyld: Library not loaded" for libsamrai or libmpi: rpath from the build tree, fix at link time, not with DYLD_LIBRARY_PATH; (e) assertion failures (if assertions were left on): a real invalid state, record as failure; (f) negative density or pressure in Euler at extreme inputs: expected failure region; (g) the regex finds nothing: the print is inside a TESTING or rank guard that didn't run. Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- License LGPL-2.1: fine for running the examples as external programs.
- Parallelism: MPI is on by default; run one rank per run (no `mpiexec`) and keep `ENABLE_OPENMP=OFF`.
- Determinism: no random numbers; serial runs repeat exactly. Regridding makes cell counts piecewise constant, and Godunov limiters make shock quantities piecewise smooth.
- Run time: the library build is the big cost (20–40 min, once). Per run, the 2-D examples with few steps are seconds; the Euler step problem needs its step count cut.
- Version: v4.6.0's release notes list a RefineSchedule fix that "may change numerical results", so pin the tag and don't mix builds. Spack lags at 4.5.0.
- Fit: SAMRAI is a library; every model needs an edited copy of the example's `main.cpp`. If time is short, onboard AMReX instead, which covers the same AMR structure with less work.
- Sources: https://github.com/LLNL/SAMRAI, https://github.com/LLNL/SAMRAI/releases, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/README.md, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/RELEASE-NOTES, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/LICENSE, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/CMakeLists.txt, https://github.com/LLNL/SAMRAI/tree/v-4-6-0/source/test/applications, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/source/test/applications/LinAdv/example_inputs/sphere.2d.input, https://github.com/LLNL/SAMRAI/blob/v-4-6-0/source/test/applications/Euler/example_inputs/step.2d.input, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/samrai/package.py

---

#### WarpX

**What it is.** WarpX is an electromagnetic and electrostatic particle-in-cell (PIC) code on AMReX, for laser–plasma acceleration, beams, plasma devices and fusion. C++17 with a Python interface (`pywarpx`, PICMI). License: BSD-3-Clause-LBNL. The repository is now **https://github.com/BLAST-WarpX/warpx** (formerly ECP-WarpX), docs at https://warpx.readthedocs.io. Current release **26.09 (2026-09-03)**; releases are monthly. Examples: `Examples/` holds about 800 files, the physics cases in `Examples/Physics_applications/` (laser acceleration, plasma acceleration, capacitive discharge, uniform plasma, laser–ion, ...) and many tests in `Examples/Tests/` (Langmuir waves in 1-D, 2-D, 3-D and RZ, ...), each an `inputs_*` ParmParse file or a `*_picmi.py` script. The fit is good in 1-D: WarpX builds 1-D, 2-D, RZ and 3-D executables, and 1-D cases run in seconds. The noise is the unusual part (see Gotchas).

**Install on an Intel Mac.** conda-forge builds `warpx` 26.09 for **osx-64** (anaconda.org, uploaded 2026-09-04; macOS ≥ 11). The package installs the executables `warpx.1d.NOMPI.OMP.DP.PDP.OPMD.FFT.EB.QED`, `warpx.2d...`, `warpx.rz...`, `warpx.3d...` (and `rcylinder`, `rsphere`) plus `pywarpx` (from the feedstock's package-contents test). It is built without MPI, with OpenMP. The osx-64 and linux-64 builds require an **x86-64-v3 CPU** (AVX2, the `_x86_64-microarch-level >=3` dependency), which Intel Macs from about 2013 (Haswell) on have.
1. Install Miniforge if there is no conda.
2. Check the CPU has AVX2:
   ```bash
   sysctl -n machdep.cpu.leaf7_features | tr ' ' '\n' | grep -x AVX2
   ```
3. Create the env with a pinned version:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-warpx -c conda-forge warpx=26.09 python=3.12
   ```
4. Check:
   ```bash
   ls ~/miniforge3/envs/ema-warpx/bin/warpx.*
   ~/miniforge3/envs/ema-warpx/bin/python -c "import pywarpx; print(pywarpx.__version__)"
   ```
Known problems: the executables' names encode the build options; use the `1d` one for 1-D inputs files. The docs' macOS tip warns about MPI or HDF5 left in `/usr/local` by Homebrew interfering with other package managers; check `/usr/local/bin` for `mpicc` and friends. `pywarpx.__version__` may not exist **(unconfirmed)**; `import pywarpx` succeeding is the check.
Sources: https://warpx.readthedocs.io/en/latest/install/users.html, https://anaconda.org/conda-forge/warpx (files list), https://github.com/conda-forge/warpx-feedstock/blob/main/recipe/recipe.yaml, https://github.com/conda-forge/warpx-feedstock/blob/main/recipe/build.sh, https://github.com/BLAST-WarpX/warpx/releases.

**Install on AWS (Ubuntu 24.04 EC2).**
1. conda-forge, same as the Mac (recommended, identical version): Miniforge Linux installer, then `mamba create -n ema-warpx -c conda-forge warpx=26.09 python=3.12`. c7i instances are x86-64-v3 or later.
2. Fallback: Spack `spack install warpx@26.09` (the Spack package has 26.09; a long source build).
3. There is no official Docker image in the install docs **(unconfirmed; none listed)**.
Sources: https://warpx.readthedocs.io/en/latest/install/users.html, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/warpx/package.py.

**Preparing the examples for EMA.** WarpX reads a ParmParse inputs file, so the tutorial's `inputs_*` file is a static file and each EMA input is an override argument after it: `["<env>/bin/warpx.1d.NOMPI.OMP.DP.PDP.OPMD.FFT.EB.QED", "inputs", "my_constants.n0=$n0", ...]`. For the output, add a **reduced diagnostic** to the inputs, which writes a text table to `diags/reducedfiles/<name>.txt` with step and time in the first two columns: `FieldEnergy` (total field energy per level), `ParticleEnergy`, or `FieldMaximum`. Set `<name>.separator = ,` and read the last row with EMA's csv parser by column index. Remove the full diagnostics (`diagnostics.diags_names = none`, or drop the `diag1` and `openpmd` blocks) so each run doesn't write plot files. Set `amrex.omp_threads = 1` (the default, `nosmt`, uses one thread per physical core). For stochastic cases, a wrapper script in the model directory reads `EMA_REPLICATE` and adds `warpx.random_seed=<EMA_REPLICATE + 1>` (the seed must be a positive integer; 1 is the default seed).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Langmuir wave, `Examples/Tests/langmuir/inputs_test_1d_langmuir_multi` (https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Tests/langmuir/inputs_test_1d_langmuir_multi) | 1-D electron–positron plasma oscillation, 128 cells, 80 steps, particles loaded 2 per cell with `NUniformPerCell` (no random numbers) and a sinusoidal momentum perturbation of size ε | `my_constants.epsilon` ε 0.01 [0.001, 0.05] (log); `my_constants.n0` 2e24 [5e23, 8e24] (log) m⁻³; `max_step` fixed at 80 | total field energy at the last step (added `FieldEnergy` reduced diagnostic, column 3) | a power law in ε with exponent 2 in the linear regime (`linear_coeffs(log_output=True)`), bending above it at large ε; oscillatory in n0 (the plasma period ∝ n0^−1/2 against a fixed end time), so non-monotone in n0 and `fourier` finds it; deterministic: `repeat` identical | < 2 s *(estimate)* | cli (conda binary, overrides as args) | csv on `diags/reducedfiles/FE.txt`, `delimiter` ",", column 2, row −1 (check the header line parses) |
| Laser wakefield, `Examples/Physics_applications/laser_acceleration/inputs_base_1d` (https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Physics_applications/laser_acceleration/inputs_base_1d) | 1-D laser-driven plasma wake with a moving window, 256 cells, Gaussian pulse, electrons 10 per cell, uniform density, at rest | `laser1.e_max` 16e12 [4e12, 32e12] V/m (log); `electrons.density` 2e23 [5e22, 8e23] m⁻³ (log); `laser1.profile_duration` 15e-15 [5e-15, 30e-15] s; `max_step` fixed at 1000 (the base file's 100 barely enters the plasma) | peak longitudinal field behind the pulse (added `FieldMaximum` reduced diagnostic, the max E_z column) or the electron kinetic energy (`ParticleEnergy`) | wake amplitude ∝ e_max² while the laser is weak (exponent 2 under `log_output`), saturating at large e_max; a resonance: the wake is largest when the pulse length is near half a plasma wavelength, so an optimum in duration that moves with density (a duration × density interaction and a ridge that `active_subspace` in log inputs should find); deterministic with `NUniformPerCell`, but wave-breaking at high e_max makes the output rough | 5–30 s *(estimate)* | cli | csv on the reduced-diagnostics file, last row |
| Capacitive discharge (Turner et al. 2013 benchmark case 1), `Examples/Physics_applications/capacitive_discharge/inputs_base_1d_picmi.py` in its `--test` mode (https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Physics_applications/capacitive_discharge/inputs_base_1d_picmi.py) | 1-D helium RF discharge at 13.56 MHz with Monte Carlo collisions; test mode: 32 cells, 256 particles per cell, dt doubled, 320 RF cycles; saves the time-averaged ion density profile | RF voltage amplitude 450 [300, 600] V; gas density 9.64e20 [5e20, 2e21] m⁻³ (log) (both hard-coded in the class, so the driver copy takes them as arguments) | peak (or mid-gap) time-averaged ion density, printed by the driver from the saved array | **stochastic**: MCC collisions and thermal loading use random numbers, so `repeat` with seeds from `EMA_REPLICATE` measures a real noise level; density rises with voltage and with gas density over this range (monotone, a power law is plausible); pass the measured noise to `curve1d` as `output_noise` | 2–15 min *(estimate)*: plan for AWS with `-j 8` | cli (env python + driver copy) | regex on stdout |

**Claude Code prompts.**

```text
Stage 1 — check the machine for WarpX (read-only). I want to onboard WarpX 26.09 examples (1-D Langmuir wave, 1-D laser wakefield, 1-D capacitive discharge PICMI) into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture, whether the CPU has AVX2 (macOS: sysctl -n machdep.cpu.leaf7_features; Linux: grep avx2 /proc/cpuinfo) because the conda-forge warpx builds need x86-64-v3, conda/mamba (Miniforge) and where, Homebrew version (don't use it), anything MPI- or HDF5-like in /usr/local/bin and /usr/local/lib, Docker, free disk space, and any existing env named ema-warpx. Don't install anything, and don't read .env. Recommend a route: conda-forge env `ema-warpx` with warpx=26.09 (osx-64 and linux-64 builds exist, no MPI, OpenMP); Spack warpx@26.09 only as a fallback. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install WarpX on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-warpx -c conda-forge warpx=26.09 python=3.12`. Never install into EMA's .venv, never use Homebrew, never read .env. Ask me before installing Miniforge, before any sudo, and before any download over 1 GB. Check: list <env>/bin/warpx.* and report the exact executable names; `<env>/bin/python -c "import pywarpx"`; and `<env>/bin/warpx.1d.<suffix> --help` or a run with no arguments (report what it prints). Stop at the first error (in particular a solver message about `__archspec` or microarch level: the CPU lacks AVX2) and report; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install WarpX on this AWS EC2 instance (Ubuntu 24.04, x86_64). Install Miniforge (ask first) and create `ema-warpx` with `mamba create -n ema-warpx -c conda-forge warpx=26.09 python=3.12`. Never install into EMA's .venv, never read .env, ask before any sudo. If conda fails, report and propose (don't run) `spack install warpx@26.09`. Check as on the Mac: list the warpx.* executables and import pywarpx. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — WarpX smoke test. In a scratch directory, download Examples/Tests/langmuir/inputs_test_1d_langmuir_multi from the 26.09 tag of github.com/BLAST-WarpX/warpx. Run the env's warpx.1d.* executable on it twice, timed, with `amrex.omp_threads=1` appended, then a third time with `diagnostics.diags_names=none` and a reduced diagnostic appended (`warpx.reduced_diags_names=FE FE.type=FieldEnergy FE.intervals=80 FE.separator=,` as separate arguments). Report the wall times, the last lines of stdout, the files under diags/ (and whether the third run wrote only diags/reducedfiles/FE.txt), and the contents of FE.txt. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the WarpX 1-D Langmuir wave for EMA. Enter plan mode first and show me the plan. In examples/warpx/langmuir_1d/: the tutorial's inputs_test_1d_langmuir_multi as a static file named inputs, edited only to replace the full diagnostics with `diagnostics.diags_names = none` and to add `warpx.reduced_diags_names = FE`, `FE.type = FieldEnergy`, `FE.intervals = 80`, `FE.separator = ,`, and `amrex.omp_threads = 1`. Command [<ema-warpx env>/bin/warpx.1d.<suffix>, "inputs", "my_constants.epsilon=$eps", "my_constants.n0=$n0"]; inputs eps = 0.01 [0.001, 0.05] (scale log), n0 = 2e24 [5e23, 8e24] (scale log); output csv on diags/reducedfiles/FE.txt, delimiter ",", column index 2 (total field energy, level 0), row -1 (check how the header line looks and whether EMA's csv parser needs it skipped; tell me); number_format ".10g"; env OMP_NUM_THREADS=1; timeout_s 120. Record the WarpX version in the description. Follow docs/guides/input_deck_model.md and examples/beam/model_csv.json. Check by hand that doubling eps multiplies the output by about 4. Then `.venv/bin/ema profile examples/warpx/langmuir_1d/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the WarpX 1-D laser wakefield. Plan mode first. Source: Examples/Physics_applications/laser_acceleration/inputs_base_1d (26.09). In examples/warpx/lwfa_1d/: inputs (static) with the full diagnostics and the FieldProbe removed, max_step = 1000, amrex.omp_threads = 1, and a FieldMaximum reduced diagnostic FM (intervals = max_step, separator ","). Before choosing the output column, run once and show me FM.txt's header, and tell me which column is max |Ez|. Command: the warpx.1d executable, "inputs", "laser1.e_max=$emax", "electrons.density=$ne", "laser1.profile_duration=$tau"; inputs emax = 16e12 [4e12, 32e12] (scale log), ne = 2e23 [5e22, 8e23] (scale log), tau = 15e-15 [5e-15, 30e-15]. csv parser, last row. timeout_s 300. Check by hand that halving emax reduces the output by about 4 at nominal density. Then `.venv/bin/ema profile examples/warpx/lwfa_1d/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the WarpX capacitive discharge (stochastic). Plan mode first. Source: Examples/Physics_applications/capacitive_discharge/inputs_base_1d_picmi.py (26.09), test mode (-t, case 1). In examples/warpx/ccp_1d/, write a driver copy run_ccp.py that takes --voltage and --gas-density, uses them in place of case 1's hard-coded 450 V and 9.64e20, keeps the test-mode resolution, sets the WarpX random seed to int(os.environ.get("EMA_REPLICATE", "0")) + 1 (find how PICMI passes warpx.random_seed in 26.09 and tell me; also seed the script's own numpy rng the same way), and at the end prints `EMA_OUTPUT <max of the time-averaged ion density>`; no plots, no .npy left behind if avoidable. Command [<ema-warpx env>/bin/python, "run_ccp.py", "--voltage", "$V", "--gas-density", "$ng"]; inputs V = 450 [300, 600], ng = 9.64e20 [5e20, 2e21] (scale log); regex on stdout; env OMP_NUM_THREADS=1; timeout_s 3600. Time one run by hand first and tell me before profiling if it exceeds 10 minutes. Then `.venv/bin/ema profile examples/warpx/ccp_1d/model.json -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first WarpX campaign. For examples/warpx/langmuir_1d/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on n0 (n 21), and linear_coeffs with log_output true. Report `.venv/bin/ema estimate`, and ask me before `ema run -j 4`. Report: repeats identical (expected: the loading is deterministic), the exponent of eps from linear_coeffs (expected about 2, with its interval), whether curve1d on n0 is oscillatory (expected) and what fourier would add, and any failed runs. Then propose (don't run) a repeat with replicates 5 on examples/warpx/ccp_1d/model.json to measure its noise, with its estimated cost. Stop and report.
```

```text
Stage 6 — WarpX troubleshooting. An EMA WarpX model fails or looks noisy. Diagnose read-only from the run directory (stdout.txt, stderr.txt, diags/): (a) "ParmParse: unused" or an override with no effect: a wrong key or a my_constants name; (b) the reduced-diagnostics file missing: intervals larger than max_step, or the file name/path differs; (c) the csv parser fails on the header: the header row format (check what EMA's parse_csv does with it); (d) CFL or particle-shape errors at extreme densities (resolution of the plasma wavelength): an expected failure region or a range to narrow; (e) threads: amrex.omp_threads and OMP_NUM_THREADS (runs slow or oversubscribed with -j); (f) results that differ between identical runs: the seed isn't fixed or threads > 1 (atomic current deposition order); (g) an "illegal instruction": the CPU lacks AVX2 for the x86-64-v3 build. Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- License BSD-3-Clause-LBNL.
- Parallelism: the conda build has no MPI and uses OpenMP; set `amrex.omp_threads = 1` (an integer set there overrides `OMP_NUM_THREADS`) and `OMP_NUM_THREADS=1`, and let EMA run runs in parallel.
- Noise: PIC has shot noise. Cases that load particles with `NUniformPerCell` and no thermal spread (the Langmuir and wakefield examples) use no random numbers and repeat exactly in serial, but their outputs are still rough in the inputs. Random loading, thermal momenta and Monte Carlo collisions use the seed: `warpx.random_seed = n` sets the seed per rank to `(rank + 1) × n`, `random` draws a new one each run, and "when GPU threading is used, one should not expect to obtain the same random numbers". Seed each replicate from `EMA_REPLICATE` through a wrapper, and use `repeat` to size `output_noise`.
- Run time: 1-D is seconds; 2-D and 3-D examples are minutes to hours on a laptop. Keep `max_step` fixed across a campaign (it is a discretization choice, not an input).
- Version: releases are monthly and not backward-compatible (`run_exports: warpx ==26.09` in the feedstock); pin the conda version and use the example files from the same tag.
- CPU: the conda-forge builds need x86-64-v3 (AVX2).
- Sources: https://github.com/BLAST-WarpX/warpx, https://github.com/BLAST-WarpX/warpx/releases, https://warpx.readthedocs.io/en/latest/install/users.html, https://github.com/BLAST-WarpX/warpx/blob/26.09/Docs/source/usage/parameters.rst (`warpx.random_seed`, `amrex.omp_threads`, reduced diagnostics, `reduced_diags.separator`), https://github.com/BLAST-WarpX/warpx/tree/26.09/Examples, https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Tests/langmuir/inputs_test_1d_langmuir_multi, https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Physics_applications/laser_acceleration/inputs_base_1d, https://github.com/BLAST-WarpX/warpx/blob/26.09/Examples/Physics_applications/capacitive_discharge/inputs_base_1d_picmi.py, https://anaconda.org/conda-forge/warpx, https://github.com/conda-forge/warpx-feedstock, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/warpx/package.py, https://amrex-codes.github.io/amrex/docs_html/Basics.html

---

#### MFiX

**What it is.** MFiX (Multiphase Flow with Interphase eXchanges) is NETL's multiphase CFD code: two-fluid (TFM), discrete element (DEM, with coarse-grained, superquadric and glued-sphere particles), particle-in-cell (PIC) and hybrid models, for fluidized beds, gasifiers, hoppers and reactors. Fortran solver with a Python/Qt GUI. The site calls it "open-source" and "free to download"; the license text was not reachable without logging in **(unconfirmed which license)**. Current release **MFiX 26.1.2 (announced 2026-07-09)**; NETL says "There is no planned date yet for a 26.2 release". **Downloads require a free registration that NETL moderates by hand** ("typically within one or two days"; forum users report waiting several business days). After approval, the download page gives a personal `conda create` command with a private, expiring channel URL on `mfix.netl.doe.gov/s3/...`. There is no conda-forge package and no public source repository. Tutorials are GUI walkthroughs in the 26.1 manual (https://mfix.netl.doe.gov/doc/mfix/26.1/html/tutorials/index.html: 2-D TFM fluidized bed, 2-D DEM fluidized bed, 3-D fluidized bed, 3-D DEM hopper, DEM chutes, cyclone, CHEMKIN batch reactor, ...), and the GUI's New Project menu has templates for them. A project is one `<name>.mfx` keyword file.
The fit is poor for a laptop. The batch solver (`mfixsolver -f project.mfx`) works as a command-line model, but TFM and DEM cases take minutes to hours, and bubbling beds are chaotic. Plan MFiX for AWS, with coarse 2-D cases and long time averages. (MFIX-Exa, the AMReX-based successor, is a separate code and not covered here.)

**Install on an Intel Mac.** The 26.1 manual says: "We provide installable packages for both Intel and M1-based Macs", tested on macOS 14.5. Whether the 26.1.2 channel still has osx-64 builds is behind the login **(unconfirmed)**.
1. Register at https://mfix.netl.doe.gov (Register), and wait for approval.
2. Install Miniforge (osx-64) if there is no conda.
3. Log in, open Products → MFiX → Download, and copy the `conda create -n mfix-26.1.2 ...` command. It includes a private token; don't share it or commit it, and don't paste it into files in the repo.
4. Run it (the command installs `mfix`, `mfix-solver`, the GUI and its dependencies from conda-forge and NETL's channel).
5. Build a batch solver for a project and check:
   ```bash
   conda activate mfix-26.1.2
   mkdir -p ~/mfix-scratch/fb2d && cd ~/mfix-scratch/fb2d     # a project saved from the GUI's TFM template
   build_mfixsolver --batch -j 4
   ./mfixsolver -f <project>.mfx
   ```
Known problems: the environment name is whatever the download command sets (`mfix-26.1.2` assumed). The GUI has had start-up errors on recent macOS (a forum report for 25.3 on macOS 26.1); the batch solver doesn't need the GUI. The download token expires, so the install must happen soon after copying the command. `build_mfixsolver` compiles with the Fortran compiler in the env **(unconfirmed that the env ships one)**.
Sources: https://mfix.netl.doe.gov/doc/mfix/26.1/html/getting_started/install-macos.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/solver/build-batch.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/solver/run-batch.html, https://mfix.netl.doe.gov/forum/t/mfix-26-1-2-is-available-for-download/6735, https://mfix.netl.doe.gov/forum/t/mfix-26-1-1-is-available-for-download/6689.

**Install on AWS (Ubuntu 24.04 EC2).** The same route: Miniforge (Linux x86_64), then the download page's command. The manual lists Ubuntu 24.10 and CentOS 8 as tested; 24.04 is "likely to work" **(unconfirmed)**. There is no Docker image, apt package or Spack package. Build the batch solver per project with `build_mfixsolver --batch -j 8` (add `--smp` only if you want threads inside one run; don't). Use a `c7i.4xlarge` or larger: runs take minutes each.
Sources: https://mfix.netl.doe.gov/doc/mfix/26.1/html/getting_started/install-linux.html, https://mfix.netl.doe.gov/forum/t/mfix-26-1-is-available-for-download/6647 (glibc discussion).

**Preparing the examples for EMA.** The recipe:
- Create the tutorial project in the GUI (or from its template), then save it.
- Build a batch solver in the project directory, and copy `mfixsolver` into the model directory (hashed).
- Make the `.mfx` file a template: it is `KEYWORD = value` lines (`BC_V_G(1) = 0.25`, `D_P0(1) = 200.0e-6`, `TSTOP = ...`). Check it for `$` (the GUI section at the end may contain JSON) and escape any with `$$`.
- Keep `RES_DT` and the VTK output intervals large so each run writes little.
- For the output, define a **monitor** in the GUI before saving: a region average or sum written to `<filename base>.csv` at a fixed simulated-time interval.
- The output is a time average over the second half of the run, so it needs a small isolated `python` parser that reads the monitor CSV and averages the rows after a start time.
- The batch solver also takes keyword overrides on the command line (the manual's `./mfixsolver -f DES_FB1.mfx NODESI=2 NODESJ=2`). Whether every keyword can be overridden that way is **(unconfirmed)**, so use the template.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| 2-D TFM fluidized bed, tutorial 3.2 (https://mfix.netl.doe.gov/doc/mfix/26.1/html/tutorials/tutorial_tfm.html): 10 cm × 30 cm, 20 × 60 cells, 200 µm particles of density 2500 kg/m³, gas 0.25 m/s | bubbling gas–solid bed, Eulerian–Eulerian | gas inlet velocity 0.25 [0.02, 0.5] m/s; particle diameter 200e-6 [100e-6, 400e-6] m (log); particle density 2500 [1500, 3500] kg/m³ | time-averaged pressure drop across the bed over the second half of a run (monitor of pressure at the inlet and outlet regions) | a **kink at minimum fluidization**: ΔP rises about linearly with velocity (Ergun) until u_mf and then plateaus at the bed weight per area (∝ solids density; `curve1d` and `nonsmooth` should find it, at this resolution); u_mf ∝ d²(ρ_s − ρ_g) at small Reynolds numbers, so the kink moves with diameter and density (interaction); above u_mf the bubbling makes the average noisy in the inputs even though `repeat` may show none | 5–30 min for 5–10 s of simulated time *(estimate)*; AWS | cli (per-project batch solver) | python (average of the monitor CSV after t₀) |
| 3-D DEM hopper, tutorial 3.6 (https://mfix.netl.doe.gov/doc/mfix/26.1/html/tutorials/tutorial_hopper.html): 5 cm diameter hopper, 10 × 25 × 10 mesh, 3 mm particles, pure granular flow | granular discharge through an orifice | orifice diameter (the tutorial's value **(unconfirmed)**) [3, 6] particle diameters; particle–wall friction 0.3 [0.1, 0.6]; restitution coefficient 0.8 [0.5, 0.95] | discharge mass flow rate over a window after start-up (a monitor of solids mass leaving, or of mass remaining) | Beverloo law: rate ∝ (D − k d)^{5/2}, a power law in the orifice size above a jamming threshold, with **no flow** (a failure region, or zero) near D ≈ 3–4 d; weak dependence on restitution; friction lowers the rate; chaotic granular flow gives run-to-run roughness | 20 min–2 h *(estimate)*; AWS only | cli | python |

**Claude Code prompts.**

```text
Stage 1 — check the machine for MFiX (read-only). I want to onboard MFiX 26.1.2 (NETL) tutorials into EMA as command-line models using the batch solver. Run only read-only commands and report: OS and version, CPU architecture, conda/mamba (Miniforge) and where, any existing conda env whose name starts with mfix, free disk space, CPU count and memory. Don't install anything, don't read .env, and don't look for or print any MFiX download token. Tell me plainly: MFiX downloads need a registration that NETL approves by hand, the install command comes from the download page after login, and a laptop run takes minutes; recommend AWS (c7i.4xlarge or larger) for campaigns and the Mac only for setting up projects. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install MFiX on this Intel Mac. I have registered and will paste the conda command from the MFiX download page into my own terminal myself; you must not handle the token. Before that: if there is no Miniforge, ask me before installing it (osx-64 installer). After I tell you the install finished, check read-only: `conda env list` shows the mfix env (report its name), `conda run -n <env> which build_mfixsolver mfix`, and the Fortran compiler build_mfixsolver will use (`conda run -n <env> build_mfixsolver --help`). Never install into EMA's .venv, never use Homebrew, never read .env, and ask before any sudo or download over 1 GB. Stop at the first error and report it; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install MFiX on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before installing Miniforge (Linux x86_64). I will paste the MFiX download command myself; don't handle the token. Then check read-only as on the Mac: the env name, build_mfixsolver on PATH in the env, and `build_mfixsolver --help`. Never install into EMA's .venv, never read .env, ask before any sudo. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — MFiX smoke test. I will create the 2-D TFM fluidized-bed tutorial project (manual section 3.2) in the GUI and save it to a scratch directory outside the EMA repo, and tell you its path. There, with the mfix env, run `build_mfixsolver --batch -j 4` (time it), then run `./mfixsolver -f <project>.mfx` with TSTOP temporarily set to 0.5 s in a copy of the .mfx, timed. Report the build time, the run time, the files written (sizes), and whether the run finished normally. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the MFiX 2-D TFM fluidized bed for EMA. Enter plan mode first and show me the plan. In examples/mfix/tfm_bed2d/: the saved project's .mfx as a template (grep it for `$` first and escape each as `$$`; show me the lines you template), the batch mfixsolver copied here with a build.sh recording the MFiX version, and the monitor CSV the project defines (I'll add a monitor in the GUI for the pressure at the inlet and outlet regions if the tutorial has none: tell me what it needs). Inputs: ug = 0.25 [0.02, 0.5] (the inlet BC gas velocity keyword), dp = 200e-6 [100e-6, 400e-6] (scale log), rhos = 2500 [1500, 3500]; TSTOP fixed at the shortest value where the bed has settled into bubbling (propose it from the smoke test). Output: an isolated python parser (parse.py) that reads the monitor CSV and returns the mean pressure difference over the second half of the run. Command ["mfixsolver", "-f", "<project>.mfx"], env OMP_NUM_THREADS=1, timeout_s 3600. Follow docs/guides/input_deck_model.md and examples/beam/model_parser.json. Check by hand at ug = 0.02 (below minimum fluidization: ΔP below bed weight) and 0.4 (ΔP near bed weight per area); report both and the wall times. Then `.venv/bin/ema profile examples/mfix/tfm_bed2d/model.json -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the MFiX 3-D DEM hopper (AWS only). Plan mode first. I will create the hopper tutorial project (manual section 3.6) in the GUI with a monitor of the solids mass in the domain (or leaving the outlet) and give you its path. In examples/mfix/dem_hopper/: the .mfx template (escape `$`), the batch solver, build.sh. Inputs: the orifice diameter (tell me which keyword or geometry parameter sets it, and its tutorial value, before choosing the range; target [3, 6] particle diameters), wall friction 0.3 [0.1, 0.6], restitution 0.8 [0.5, 0.95]. Output: an isolated python parser returning the discharge rate from the slope of mass versus time over a window after start-up (and a clear error if nothing flowed). timeout_s 14400. Time one run first and tell me before profiling. Then `.venv/bin/ema profile ... -n 2`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first MFiX campaign (on AWS). For examples/mfix/tfm_bed2d/model.json, write campaign.json with repeat (n_points 2, replicates 2) and curve1d on ug (n 11); nothing else yet. Report `.venv/bin/ema estimate` (runs and hours), and ask me before `ema run -j 16` (or my chosen -j). Report: whether repeats are identical (they may be, since MFiX has no seed; say so), the kink curve1d and nonsmooth find near minimum fluidization and its location (at this resolution), the plateau level versus the bed weight per area, and how rough the curve is above the kink. Suggest (don't run) a surface2d on (ug, dp) with its cost. Stop and report.
```

```text
Stage 6 — MFiX troubleshooting. An EMA MFiX model fails or is slow. Diagnose read-only from the run directory (stdout.txt, stderr.txt, <RUN_NAME>.LOG, the monitor CSV): (a) the template failed: a `$` left unescaped in the .mfx (EMA's error says which line); (b) keyword errors reported in the LOG: a misspelled or deprecated keyword, or an index like BC_V_G(1) pointing at the wrong boundary; (c) the solver diverges (NaN, "DT < DT_MIN"): a physical failure at extreme inputs, check it is reproducible; (d) the monitor CSV missing or short: the monitor interval versus TSTOP, or a region name; (e) runs much slower than profiled: VTK or restart output too frequent, or SMP threads (OMP_NUM_THREADS); (f) the batch solver out of date after editing UDFs: rebuild. Never print or copy the download token. Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- License and access: "open-source ... free to download", but only after a registration NETL approves by hand, with private, expiring conda channel tokens. Keep tokens out of the repo and out of Claude Code's context. The exact license text needs a login **(unconfirmed)**.
- Parallelism: build the batch solver without `--dmp` and `--smp`, and run serially; EMA's `-j N` does the rest.
- Determinism and noise: MFiX has no seed input for EMA to vary. Bubbling beds and granular flows are chaotic, so outputs are rough in the inputs even if `repeat` shows identical runs; use long averaging windows, and estimate `output_noise` from the scatter of a fine `curve1d`. DEM initial particle seeding may use random numbers **(unconfirmed)**.
- Run time: minutes to hours per run. Budget with `ema estimate` before anything else, and use AWS.
- Version pitfalls: 26.1 moved the GUI to Qt6; batch solvers are built per version and per project. Pin the env name and record the version in `model.json`.
- Sources: https://mfix.netl.doe.gov/products/mfix/, https://mfix.netl.doe.gov/products/mfix/download/ (registration), https://mfix.netl.doe.gov/doc/mfix/26.1/html/index.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/about.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/getting_started/install-macos.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/getting_started/install-linux.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/solver/build-batch.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/solver/run-batch.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/model_setup/monitor.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/tutorials/tutorial_tfm.html, https://mfix.netl.doe.gov/doc/mfix/26.1/html/tutorials/tutorial_hopper.html, https://mfix.netl.doe.gov/forum/t/mfix-26-1-is-available-for-download/6647, https://mfix.netl.doe.gov/forum/t/mfix-26-1-1-is-available-for-download/6689, https://mfix.netl.doe.gov/forum/t/mfix-26-1-2-is-available-for-download/6735, https://mfix.netl.doe.gov/forum/t/error-installing-mfix-on-windows/6750

---

#### PFLOTRAN

**What it is.** PFLOTRAN is a massively parallel subsurface flow and reactive transport code (Richards, multiphase, thermal–hydrologic, geochemistry with kinetic and equilibrium reactions), written in object-oriented Fortran 2003/2008 on PETSc. License: GNU LGPL, version 2.1 or later (pflotran.org). The source lives at **https://bitbucket.org/pflotran/pflotran** (the GitHub mirror `petsc/pflotran` stopped in 2017). Current release **v7.0.0 (tagged 2025-09-08)**; master is active (last commit 2026-09-22). The documentation site still labels itself "v6.0 documentation". Examples: the `shortcourse/exercises/` directory of the source (about 24 exercises: `1D_sorption_decay`, `1D_variably_saturated_flow`, `1D_Calcite`, `5-spot`, `heater`, `co2`, ...) and the much larger `regression_tests/`. An input deck is one `.in` file of keyword blocks, with no `$` in its syntax, so it is a natural template.
**PETSc version.** PFLOTRAN needs one specific PETSc release. Its install page says `git checkout v3.24.5`, and its "Previous PETSc Releases" page says v3.24.x since 2025-09-08 (v3.21.x before). But the v7.0.0 tag's own CI file (`.gitlab/petsc-git-version.txt`) still names **v3.21.4**, while master's names v3.24.3. So pair **PFLOTRAN master (pinned by commit) with PETSc 3.24.5**, as the install page does; if you need the v7.0.0 tag itself, use PETSc 3.21.4. Both are older than the 3.25.5 in this document's `ema-petsc` env (section 4.4), so **don't reuse `ema-petsc`**: build a separate PETSc.

**Install on an Intel Mac.** There is no conda-forge or Homebrew package of PFLOTRAN, and the documentation has no macOS page (Linux, WSL, Visual Studio and VM only). Two routes:
1. **Source build (recommended).** Compilers from conda-forge, PETSc 3.24.5 built from git with the options PFLOTRAN documents (they download MPICH, HDF5 with Fortran bindings, BLAS/LAPACK, METIS and ParMETIS):
   ```bash
   ~/miniforge3/bin/mamba create -n ema-pflotran -c conda-forge c-compiler cxx-compiler fortran-compiler make cmake python=3.12 git
   conda activate ema-pflotran
   mkdir -p ~/src && cd ~/src
   git clone https://gitlab.com/petsc/petsc petsc-pflotran && cd petsc-pflotran && git checkout v3.24.5
   ./configure PETSC_ARCH=arch-pflotran --COPTFLAGS='-O3' --CXXOPTFLAGS='-O3' --FOPTFLAGS='-O3 -Wno-unused-function' \
     --with-debugging=no --download-mpich=yes --download-hdf5=yes --download-hdf5-fortran-bindings=yes \
     --download-fblaslapack=yes --download-metis=yes --download-parmetis=yes
   make PETSC_DIR=$HOME/src/petsc-pflotran PETSC_ARCH=arch-pflotran all
   cd ~/src && git clone https://bitbucket.org/pflotran/pflotran && git -C pflotran rev-parse HEAD   # record the commit
   cd pflotran/src/pflotran && make PETSC_DIR=$HOME/src/petsc-pflotran PETSC_ARCH=arch-pflotran pflotran
   ```
   Check: `./pflotran -input_prefix <deck>` on the sorption exercise (Stage 3).
2. **Docker (fallback).** PFLOTRAN's CI publishes PETSc images on Docker Hub, `pflotran/petsc:v3.24.3` (amd64, pushed 2026-01-07), which Docker Desktop runs natively on an Intel Mac. Build PFLOTRAN inside a small image `FROM pflotran/petsc:v3.24.3@sha256:<digest>`, following `.gitlab/build-pflotran.sh`, and run each model through `docker run` (section 2).
A third route, conda-forge's `petsc=3.24.5` (osx-64 builds exist, with Fortran bindings and HDF5), is **(unconfirmed)**: it may lack HDF5's Fortran modules or ParMETIS that PFLOTRAN needs.
Known problems: the PETSc build takes 30–60 min *(estimate)*; the Xcode Command Line Tools may be needed for the macOS SDK; `--download-*` fetches sources from the internet during configure.
Sources: https://www.pflotran.org/documentation/user_guide/how_to/installation/installation.html, https://www.pflotran.org/documentation/user_guide/how_to/installation/linux.html, https://www.pflotran.org/documentation/user_guide/how_to/installation/previous_petsc_releases.html, https://bitbucket.org/pflotran/pflotran/src/v7.0.0/.gitlab/petsc-git-version.txt, https://bitbucket.org/pflotran/pflotran/src/master/.gitlab/petsc-git-version.txt, https://hub.docker.com/r/pflotran/petsc/tags, https://anaconda.org/conda-forge/petsc.

**Install on AWS (Ubuntu 24.04 EC2).**
1. apt compilers, then the same PETSc 3.24.5 source build and PFLOTRAN build as on the Mac (the Linux install page's route):
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential gfortran git python3 cmake
   ```
2. Docker fallback: `pflotran/petsc:v3.24.3` pinned by digest, with PFLOTRAN built in a derived image.
3. Spack's `pflotran` has 5.0.0 (with `petsc@3.20:3.21`) and `develop` (with `petsc@main`), neither of which matches 3.24.x; don't use it.
Sources: https://www.pflotran.org/documentation/user_guide/how_to/installation/linux.html, https://hub.docker.com/r/pflotran/petsc/tags, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/pflotran/package.py.

**Preparing the examples for EMA.** The recipe:
- Copy the exercise's `.in` file to a template and replace values with placeholders.
- Change `DATABASE ../../../database/<file>` to the bare file name, and list that database file (from the source's `database/`) as a static file.
- Add an `OBSERVATION` region where the output is read, and in `OUTPUT` keep `PERIODIC_OBSERVATION TIMESTEP 1`. Drop `FORMAT TECPLOT` and `TIMES` so no snapshot files are written.
- Run `["pflotran", "-input_prefix", "<deck name>"]` with the binary copied into the model directory (it is statically linked against PETSc in the CI build; a shared build needs its rpath).
- Read the last row of the observation file, `<prefix>-obs-0.pft` **(unconfirmed name for a serial run)**. Its header names contain spaces inside quotes, so use a small isolated `python` parser that picks the column by header name.
- The exercises already use `SOLVER DIRECT`, so linear-solver jitter is not an issue; Newton tolerances remain.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `shortcourse/exercises/1D_sorption_decay/transport_sorption_decay.in` (https://bitbucket.org/pflotran/pflotran/src/v7.0.0/shortcourse/exercises/1D_sorption_decay/) | 1-D advection–dispersion over 100 m (100 cells, 25 y) of six tracers: conservative, linearly sorbing (Kd), decaying (half-life), and sorbing + decaying | Darcy velocity 1 [0.2, 5] m/y (log); Kd of Eaq 1.25786e-4 [1e-5, 1e-3] m³/kg (log); half-life of Eaq 10 [1, 100] y (log); porosity 0.25 [0.15, 0.4] | total Eaq at the `middle` observation point (x = 50 m) at 25 y | breakthrough is a steep front: concentration vs velocity is sigmoidal with a near-plateau at the inlet value (a plateau and a steep rise that `curve1d` resolves), shifted by retardation R = 1 + ρ_b Kd/φ, so velocity × Kd × porosity interact through v/R; decay adds an exponential factor exp(−λ x R/v), log-linear in the half-life; deterministic | < 2 s *(estimate)* | cli (binary + database static) | python (last row, column by name) |
| `shortcourse/exercises/1D_variably_saturated_flow/vsat_flow.in` (https://bitbucket.org/pflotran/pflotran/src/v7.0.0/shortcourse/exercises/1D_variably_saturated_flow/) | 1-D Richards equation in a 10 m column (100 cells, 10 y), van Genuchten/Mualem soil, recharge at the top, hydrostatic bottom | recharge flux 10 [1, 100] cm/y (log); permeability 1e-12 [1e-14, 1e-11] m² (log); van Genuchten α 1e-4 [1e-5, 1e-3] 1/Pa (log); m 0.5 [0.3, 0.7] | liquid saturation at an added observation point near the top (z = 9.95 m) at 10 y | at steady state k_r(S) = q/K_sat, so the output depends on flux and permeability only through their ratio: a ridge along ln q − ln k (`active_subspace` in log inputs should find one direction; `linear_coeffs(log_output=True)` equal and opposite exponents); a plateau at full saturation when q approaches K_sat (low permeability, high flux); α and m shape the curve (interactions) | 1–3 s *(estimate)* | cli | python |
| `shortcourse/exercises/1D_Calcite/calcite_tran_only.in` (https://bitbucket.org/pflotran/pflotran/src/v7.0.0/shortcourse/exercises/1D_Calcite/) | 1-D reactive transport over 100 cells for 25 y: acidic inflow dissolving calcite with a kinetic rate law, `hanford.dat` database | calcite rate constant 1e-6 [1e-8, 1e-4] mol/m²/s (log); calcite specific surface area 1 [0.1, 10] m²/m³ (log); Darcy velocity 1 [0.2, 5] m/y (log); initial calcite volume fraction 1e-5 [1e-6, 1e-3] (log) | pH at an added observation point (x = 50 m) at 25 y | the rate enters only as rate constant × surface area, so their exponents are equal (an exact ridge in log inputs); a plateau at the equilibrium limit when kinetics are fast; a **kink** where calcite is exhausted (small volume fractions), which `nonsmooth` should find; velocity sets a Damköhler number with the rate (interaction) | 2–10 s *(estimate)* | cli | python |

**Claude Code prompts.**

```text
Stage 1 — check the machine for PFLOTRAN (read-only). I want to onboard PFLOTRAN (bitbucket.org/pflotran/pflotran, master pinned by commit, with PETSc 3.24.5) short-course exercises into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture, conda/mamba (Miniforge) and where, Homebrew version (don't use it), C/C++/Fortran compilers, make, git, any MPI or HDF5 on PATH, Docker (and whether the daemon runs), free disk space (PETSc's build needs several GB), and whether ~/src/petsc-pflotran, ~/src/pflotran, or the conda env ema-petsc exist (ema-petsc has PETSc 3.25.5, which is too new for PFLOTRAN; don't reuse it). Don't install anything, and don't read .env. Recommend a route: a source build of PETSc v3.24.5 with PFLOTRAN's documented configure options, compilers from a conda-forge env `ema-pflotran`; Docker image pflotran/petsc:v3.24.3 as the fallback. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install PFLOTRAN on this Intel Mac. Create a conda-forge env (never defaults): `mamba create -n ema-pflotran -c conda-forge c-compiler cxx-compiler fortran-compiler make cmake python=3.12 git`. Never install into EMA's .venv, never use Homebrew, never read .env. Ask me before installing Miniforge, before any sudo, and before downloads over 1 GB. Then: clone https://gitlab.com/petsc/petsc into ~/src/petsc-pflotran and check out v3.24.5; configure with PETSC_ARCH=arch-pflotran and exactly the options from https://www.pflotran.org/documentation/user_guide/how_to/installation/linux.html (--with-debugging=no, --download-mpich, --download-hdf5, --download-hdf5-fortran-bindings, --download-fblaslapack, --download-metis, --download-parmetis, -O3 flags); build it (tell me the time); clone https://bitbucket.org/pflotran/pflotran into ~/src/pflotran and report the commit; `make pflotran` in src/pflotran with PETSC_DIR and PETSC_ARCH set. Stop at the first error and report the command and the tail of configure.log or the make output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install PFLOTRAN on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before `sudo apt-get install -y build-essential gfortran git python3 cmake`. Then build PETSc v3.24.5 from git with PFLOTRAN's documented configure options (PETSC_ARCH=arch-pflotran) in ~/src/petsc-pflotran, clone PFLOTRAN at the commit I give you (from the Mac), and `make pflotran`. Never install into EMA's .venv, never read .env. If the build fails, report and propose (don't run) a Dockerfile FROM pflotran/petsc:v3.24.3 pinned by digest that builds PFLOTRAN following .gitlab/build-pflotran.sh. Stop at the first error and report. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — PFLOTRAN smoke test. In a scratch directory outside the EMA repo, copy shortcourse/exercises/1D_sorption_decay/transport_sorption_decay.in and database/simple_rxn_database.dat from ~/src/pflotran, change the DATABASE line to the bare file name, and run `<path>/pflotran -input_prefix transport_sorption_decay`, timed. Report the wall time, the last 15 lines of stdout, the files written (names and sizes), and the header line and last row of the observation file (tell me its exact name). Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the PFLOTRAN sorption and decay exercise for EMA. Enter plan mode first and show me the plan. In examples/pflotran/sorption_decay/: copy the pflotran binary (and a build.sh recording the PFLOTRAN commit and PETSc 3.24.5), the database simple_rxn_database.dat as a static file, and a template transport.template from transport_sorption_decay.in with DATABASE set to the bare name, FORMAT TECPLOT and TIMES removed, PERIODIC_OBSERVATION TIMESTEP 1 kept, and placeholders v = 1 [0.2, 5] m/y (scale log; the SPECIFIED_VELOCITY dataset), kd = 1.25786e-4 [1e-5, 1e-3] (scale log; Eaq's DISTRIBUTION_COEFFICIENT only), thalf = 10 [1, 100] y (scale log; Eaq -> Faq HALF_LIFE), phi = 0.25 [0.15, 0.4] (POROSITY). Input file destination transport.in; command ["pflotran", "-input_prefix", "transport"]. Output: an isolated python parser (parse.py) that reads the observation file, finds the column whose header contains "Total Eaq" and "middle", and returns the last row's value. number_format ".10g", env OMP_NUM_THREADS=1, timeout_s 120. Follow docs/guides/input_deck_model.md and examples/beam/model_parser.json. Check by hand that the nominal output matches the exercise's run in Stage 3, and that a larger kd lowers it. Then `.venv/bin/ema profile examples/pflotran/sorption_decay/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the PFLOTRAN variably saturated flow exercise. Plan mode first. Source: shortcourse/exercises/1D_variably_saturated_flow/vsat_flow.in. In examples/pflotran/vsat_flow/: template with an added REGION top_obs (COORDINATE 0.5 0.5 9.95) and OBSERVATION on it, an OUTPUT block with PERIODIC_OBSERVATION TIMESTEP 1 and no snapshot files, and placeholders q = 10 [1, 100] cm/y (scale log; LIQUID_FLUX of the recharge condition), k = 1e-12 [1e-14, 1e-11] (scale log; PERM_ISO), alpha = 1e-4 [1e-5, 1e-3] (scale log), m = 0.5 [0.3, 0.7] (both M entries, saturation and permeability functions, from the same placeholder). Output: python parser returning the liquid saturation column for top_obs, last row. timeout_s 120. Check by hand that multiplying q and k by 10 together leaves the output nearly unchanged (steady state), and report both values. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the PFLOTRAN 1-D calcite exercise. Plan mode first. Source: shortcourse/exercises/1D_Calcite/calcite_tran_only.in, database hanford.dat (static; tell me its size). In examples/pflotran/calcite/: template with an observation region at x = 50 m, output restricted to the observation file, and placeholders krate = 1e-6 [1e-8, 1e-4] (scale log; Calcite RATE_CONSTANT), area = 1 [0.1, 10] (scale log; the calcite specific surface area in the initial constraint's MINERALS line), v = 1 [0.2, 5] (scale log), vf = 1e-5 [1e-6, 1e-3] (scale log; calcite volume fraction). Output: python parser for pH at the observation point, last row (check the pH column name). timeout_s 300. Check by hand that krate x 10 with area / 10 gives the same pH to many digits. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first PFLOTRAN campaign. For examples/pflotran/vsat_flow/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), linear_coeffs with log_output true, and active_subspace with a small size (look up its parameters with the describe tool or docs/diagnostics/active_subspace.md and pick the example size). Report `.venv/bin/ema estimate` and ask me before `ema run -j 4`. Report: repeats identical (expected), the exponents of q and k (expected about equal and opposite), whether active_subspace finds one dominant direction along ln q − ln k, any plateau at full saturation, and failed runs (Newton failures at extreme alpha or m). Stop and report.
```

```text
Stage 6 — PFLOTRAN troubleshooting. An EMA PFLOTRAN model fails. Diagnose read-only from the run directory (stdout.txt, stderr.txt, <prefix>.out, the observation file): (a) "ERROR: ... keyword not recognized": an input keyword that changed between PFLOTRAN versions, or a placeholder rendered into the wrong line; (b) database not found: the DATABASE path or the static file; (c) "time step cut" repeated until the minimum step and stop: a real convergence failure at extreme inputs, check it reproduces; (d) dyld or shared-library errors for libpetsc, libhdf5_fortran or libmpi: rpath, fix at link time; (e) PETSc version mismatch errors at build time: the PETSc checkout isn't v3.24.x; (f) the parser can't find the column: header names include units and region names in quotes, print the header; (g) MPI warnings: run without mpirun. Report the cause and a proposed fix; change nothing without my OK.
```

**Gotchas and sources.**
- License LGPL-2.1-or-later.
- PETSc version: PFLOTRAN tracks one PETSc release series at a time (3.24.x now); the doc's `ema-petsc` env (3.25.5) is too new. Keep a separate PETSc build, and record both commits in `model.json`'s description.
- Parallelism: run one process, without `mpirun`, and let EMA's `-j N` run runs in parallel.
- Determinism: the exercises use a direct linear solver; Newton and time-step control make outputs slightly rough in the inputs at the tolerance level (time-step cuts change the path). Tighten Newton tolerances, or measure with a fine `curve1d`. No random numbers.
- Run time: the 1-D exercises are seconds; 3-D exercises and regression tests with unstructured meshes take much longer.
- Units: many inputs carry units in the deck (`m/yr`, `cm/y`, `y`); keep each placeholder's unit fixed and state it in the input's description.
- Sources: https://www.pflotran.org/, https://www.pflotran.org/documentation/index.html, https://www.pflotran.org/documentation/user_guide/how_to/installation/installation.html, https://www.pflotran.org/documentation/user_guide/how_to/installation/linux.html, https://www.pflotran.org/documentation/user_guide/how_to/installation/previous_petsc_releases.html, https://bitbucket.org/pflotran/pflotran, https://bitbucket.org/pflotran/pflotran/src/v7.0.0/shortcourse/exercises/, https://bitbucket.org/pflotran/pflotran/src/v7.0.0/.gitlab/, https://bitbucket.org/pflotran/pflotran/src/master/.gitlab/petsc-git-version.txt, https://github.com/petsc/pflotran (stale mirror), https://hub.docker.com/r/pflotran/petsc/tags, https://anaconda.org/conda-forge/petsc, https://github.com/spack/spack-packages/blob/develop/repos/spack_repo/builtin/packages/pflotran/package.py

---

### 4.7 Engineering systems: wind turbines, buildings, structures, multibody dynamics, photonics, and robotics

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions and platform builds were read today from GitHub releases (through `gh api`), the anaconda.org package API (the same file lists prefix.dev shows), PyPI's JSON API, and Docker Hub. Every run time is an *(estimate)* from the example's size and must be confirmed with `ema profile`. **(unconfirmed)** marks what I could not check in the official sources.

Cross-cutting facts for this group:
- **Six very different kinds of program.** OpenFAST and EnergyPlus are compiled command-line codes that read their own text input files, so they fit EMA the way SWMM and MODFLOW do. OpenSeesPy, PyChrono, Meep and GTSAM are Python libraries, so each example becomes a short driver run by the package env's own `python`, like `examples/cantera/ignite.py`. None of the six needs Docker on an Intel Mac today.
- **Intel Mac routes checked today.** conda-forge builds osx-64 for `openfast` 5.0.0, `pychrono` 10.0.0, `pymeep` 1.34.0 (Python 3.10–3.13 only), `gtsam` 4.3.0 and `opensees` 3.8.0. The `projectchrono` channel's `pychrono` 10.0.0 and PyPI's `openseespymac` 3.8.0.0 are **Apple Silicon only**, so the Intel Mac must use conda-forge for those two. EnergyPlus 26.1.0 ships an official macOS x86_64 tarball. GTSAM's PyPI wheels are `universal2`, so they include x86_64.
- **The NREL GitHub organization has moved.** `github.com/NREL/EnergyPlus` and `NREL/OpenStudio` now redirect to `github.com/NatLabRockies/...`; release assets download from the new path. Old links still redirect.
- **Noise.** OpenFAST with TurbSim turbulence is the only example that is stochastic by design. There the driver seeds TurbSim from `EMA_REPLICATE`. Contact dynamics (PyChrono) and nonlinear structural solvers (OpenSees) are deterministic in serial, but they iterate to a tolerance, so their outputs can be slightly rough. `repeat` and a fine `curve1d` show how rough.
- **AWS instance.** A `c7i.xlarge` (4 vCPU, 8 GB) covers everything with `-j 4`. For OpenFAST turbulent-wind campaigns (about 30–90 s per run *(estimate)*), use a `c7i.4xlarge` (16 vCPU) with `-j 16`. Add 20 GB of gp3 disk for the r-test cases and the EnergyPlus install. Set `OMP_NUM_THREADS=1` in every spec's `env` (OpenFAST, PyChrono, OpenSees and GTSAM's TBB build can all start threads).

---

#### OpenFAST

**What it is.** NREL's whole-turbine aero-hydro-servo-elastic simulator: ElastoDyn/BeamDyn structures, AeroDyn aerodynamics, InflowWind, ServoDyn control, HydroDyn, and so on, joined by a glue code. It includes TurbSim, which generates turbulent inflow. Written in Fortran, with C++ and Python bindings. Apache-2.0. Current release **v5.0.0 (2026-03-12)**, a major glue-code update with a tight-coupling solver; v4.2.1 (2026-03-10) is the last 4.x. The examples are the regression-test cases in the separate repository https://github.com/OpenFAST/r-test (tag `v5.0.0`, same date): `glue-codes/openfast/` holds about 90 cases (5 MW land-based, offshore platforms, AWT-27, AOC, UAE, MHK, linearization cases), listed in `glue-codes/openfast/CaseList.md`. Docs: https://openfast.readthedocs.io. The inputs are `.fst` plus one text file per module (`*_ElastoDyn.dat`, `*_InflowWind.dat`, ...), in a "value  Name  - comment" format with no `$`, so they template cleanly. Outputs are time series (`.out` text or `.outb` binary). The scalar EMA reads is a statistic of one channel.

**Install on an Intel Mac.** conda-forge's `openfast` 5.0.0 has osx-64 builds (the anaconda.org file list shows linux-64, linux-aarch64, osx-64, osx-arm64 and win-64; the osx-64 5.0.0 build was re-uploaded 2026-09-19). GitHub releases carry Windows binaries only.
1. Install Miniforge (osx-64) if there is no conda.
2. Create the env. It needs a Fortran compiler and CMake as well, to build the 5 MW baseline controller `DISCON`:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-openfast -c conda-forge openfast=5.0.0 fortran-compiler cmake make
   ```
3. Get only the needed r-test cases. The whole repository is about 3.7 GB (GitHub's reported size), so clone sparsely:
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone --depth 1 --branch v5.0.0 --filter=blob:none --sparse https://github.com/OpenFAST/r-test.git
   cd r-test && git sparse-checkout set glue-codes/openfast/5MW_Land_DLL_WTurb glue-codes/openfast/5MW_Baseline
   ```
4. Build the controller the 5 MW cases load (`ServoData/DISCON/CMakeLists.txt` builds `DISCON.dll`, keeping the `.dll` suffix on every OS, and installs it into `ServoData/`):
   ```bash
   conda activate ema-openfast
   cd ~/src/r-test/glue-codes/openfast/5MW_Baseline/ServoData/DISCON
   cmake -S . -B build && cmake --build build && cmake --install build
   ```
5. Check:
   ```bash
   ~/miniforge3/envs/ema-openfast/bin/openfast -h
   ~/miniforge3/envs/ema-openfast/bin/turbsim -h
   ```
Known problems: the feedstock's own tests run `openfast -h` and `turbsim -h`, but not every module driver (`beamdyn_driver` and `inflowwind_driver` tests are commented out). A controller built with a different gfortran than OpenFAST's is usually fine through the Bladed C interface **(unconfirmed)**. The `5MW_Baseline` directory includes airfoil, hydro and wind data, and its size is **(unconfirmed)**, probably a few hundred MB.
Sources: https://openfast.readthedocs.io/en/main/source/install/index.html, https://github.com/conda-forge/openfast-feedstock (recipe.yaml), https://anaconda.org/conda-forge/openfast/files, https://github.com/OpenFAST/openfast/releases, https://github.com/OpenFAST/r-test.

**Install on AWS (Ubuntu 24.04 EC2).**
1. Use the same conda env with the Linux x86_64 Miniforge installer (the linux-64 5.0.0 build exists), so both machines run the same binary.
2. Do the same sparse r-test clone and DISCON build. On Linux, `cmake --install` also writes `DISCON.dll` (a shared object despite the name).
3. Fallback: build from source with CMake and gfortran (`sudo apt install gfortran cmake libblas-dev liblapack-dev`, then follow the docs' CMake instructions). There is no official Docker image (`openfast/openfast` doesn't exist on Docker Hub today).
4. Check: `openfast -h`, `turbsim -h`.
Sources: https://openfast.readthedocs.io/en/main/source/install/index.html, https://anaconda.org/conda-forge/openfast/files.

**Preparing the examples for EMA.** The 5 MW case refers to `../5MW_Baseline/...` (airfoils, controller, wind), and EMA copies static files flat. So:
- Pack a trimmed case into a static `case.tar.gz` in the model directory: the case directory plus the `5MW_Baseline` files it names, with `../5MW_Baseline/` rewritten to `5MW_Baseline/`.
- A driver `run.py`, run by the env's `python`, unpacks the archive into the run directory and edits a handful of keyed lines from a key = value deck. Each OpenFAST line is `value  Name  - comment`, so it replaces the value on the line whose second token is the name. The driver then runs `openfast` and writes a JSON of statistics.
- Set `OutFileFmt 1` (text `.out`) and `TMax` long enough to pass the start-up transient. Compute statistics over the last 30 s only.
- One output per `model.json`: mean `GenPwr` and max |`TwrBsMyt`| share the archive and driver, with different `json` keys.
- Keep `DT` fixed: changing it changes the solution.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `glue-codes/openfast/5MW_Land_DLL_WTurb` (https://github.com/OpenFAST/r-test/tree/v5.0.0/glue-codes/openfast/5MW_Land_DLL_WTurb), switched to **steady wind**: `WindType 1` in the InflowWind file (as in `5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady8mps.dat`), `TMax` 90 s | NREL 5 MW onshore turbine, ElastoDyn + AeroDyn + DISCON variable-speed/pitch controller | `HWindSpeed` 8 [4, 20] m/s; `PLExp` (shear) 0.2 [0, 0.4]; `AirDens` 1.225 [1.1, 1.3] | mean `GenPwr` over the last 30 s (second model: max \|`TwrBsMyt`\|) | power **kinks** at rated wind (about 11.4 m/s) and plateaus above it (region 3): `curve1d`/`nonsmooth` find the kink. Below rated, power ∝ ρ (so `AirDens` matters only below rated, an interaction with wind speed). Shear near-negligible for power. Tower-base moment is **non-monotone**, peaking near rated where thrust peaks | 20–60 s for 90 s simulated at DT 0.00625 *(estimate)* | cli (env python + `run.py` + static archive) | `json` (driver writes `stats.json`) |
| same case with its **turbulent** inflow: TurbSim input `5MW_Baseline/Wind/90m_12mps_twr.inp` (31×31 grid, `IECKAI`, `RandSeed1` 13428), regenerated per run | same turbine in IEC Kaimal turbulence | `URef` 12 [6, 20] m/s; `IECturbc` (turbulence intensity, %) 14 [5, 25]; seed = 13428 + `EMA_REPLICATE` | max \|`TwrBsMyt`\| over the usable 60 s | **noise**: `repeat` measures the seed-to-seed spread, which grows with `IECturbc`. The max load increases with `IECturbc` and has a maximum near rated wind. Pass `output_noise` to later diagnostics. A good test of how EMA works with a genuinely stochastic model | 30–90 s (TurbSim plus OpenFAST) *(estimate)* | cli (driver runs `turbsim` then `openfast`) | `json` |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard OpenFAST 5.0.0 r-test cases into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, whether Miniforge conda/mamba exists and where, any env named ema-openfast, Homebrew version (don't use it), Docker, git version (sparse checkout needs ≥ 2.25), a Fortran compiler (gfortran --version), cmake, and free disk space in $HOME. Don't install anything, and don't read .env. Recommend a route: a conda-forge env `ema-openfast` with openfast=5.0.0 (osx-64 and linux-64 builds exist) plus fortran-compiler, cmake and make for the DISCON controller, and a sparse clone of github.com/OpenFAST/r-test at tag v5.0.0 (the full repository is about 3.7 GB, so never clone it whole). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install OpenFAST on this Intel Mac. Use Miniforge only (conda-forge, never defaults): `mamba create -n ema-openfast -c conda-forge openfast=5.0.0 fortran-compiler cmake make`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Then sparse-clone r-test into ~/src: `git clone --depth 1 --branch v5.0.0 --filter=blob:none --sparse https://github.com/OpenFAST/r-test.git`, then `git sparse-checkout set glue-codes/openfast/5MW_Land_DLL_WTurb glue-codes/openfast/5MW_Baseline`, and report the size on disk. Build the controller in 5MW_Baseline/ServoData/DISCON with the env's cmake (`cmake -S . -B build && cmake --build build && cmake --install build`), and confirm that ServoData/DISCON.dll exists. Check `openfast -h` and `turbsim -h` with the env's absolute paths, and report them. Stop at the first error and report the command and its output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install OpenFAST on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64) and the same env `ema-openfast` (openfast=5.0.0 fortran-compiler cmake make from conda-forge), then the same sparse r-test clone at v5.0.0 and the DISCON build as on my Mac. Never use EMA's .venv, and never read .env. Ask before any sudo, and before downloads over 1 GB. If conda fails, report and propose (don't run) a source build with apt gfortran and cmake, following openfast.readthedocs.io. Check `openfast -h` and `turbsim -h`, and report the absolute paths. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — OpenFAST smoke test. In a scratch copy outside the EMA repo (cp -r the two sparse-checked-out directories into /tmp/of_smoke/, keeping their relative layout), run `openfast 5MW_Land_DLL_WTurb.fst` from the 5MW_Land_DLL_WTurb directory with the ema-openfast env's binary and OMP_NUM_THREADS=1. Time it. Report the last lines of the screen output, the wall time, the simulated TMax, which output files appeared (.outb, .sum, .ech), and whether DISCON.dll loaded. Then make a second copy with OutFileFmt set to 1, run it again, and report the header line of the .out file (channel names) and whether GenPwr and TwrBsMyt are among them. Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the OpenFAST 5 MW steady-wind example for EMA. Enter plan mode first and show me the plan. Source: r-test v5.0.0 glue-codes/openfast/5MW_Land_DLL_WTurb plus the 5MW_Baseline files it names (AeroDyn blade and airfoils, the ElastoDyn tower and blade files, ServoData/DISCON.dll and DISCON.IN, the InflowWind file). Put in examples/openfast/5mw_steady/: (1) a static case.tar.gz holding a trimmed, self-contained copy, with every "../5MW_Baseline/" rewritten to "5MW_Baseline/", the InflowWind file set to WindType 1 (steady), TMax 90 and OutFileFmt 1; (2) run.py, which reads a key = value deck rendered from case.template (HWindSpeed = 8 [4, 20], PLExp = 0.2 [0, 0.4], AirDens = 1.225 [1.1, 1.3]), unpacks the archive into the run directory, replaces the value on each keyed line (format "value  Name  - comment"), runs the env's openfast by absolute path, and writes stats.json with the mean GenPwr and the max |TwrBsMyt| over t ≥ 60 s, and the OpenFAST version; (3) model.json (mean power) and model_tower.json (tower moment), which share the files, like examples/beam/'s variants. Follow docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/. The command is the ema-openfast env's absolute python path and run.py; env OMP_NUM_THREADS=1; timeout_s 600; json parser. Check by hand: at 8 m/s, power is below 5 MW and roughly matches the r-test steady 8 m/s results if available; at 16 m/s it is near 5 MW. Then run `.venv/bin/ema profile examples/openfast/5mw_steady/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the OpenFAST 5 MW turbulent-wind example. Plan mode first. Reuse the 4.1 archive with InflowWind's WindType 3, and add 5MW_Baseline/Wind/90m_12mps_twr.inp as a TurbSim template. Put in examples/openfast/5mw_turb/. Deck inputs: URef = 12 [6, 20], IECturbc = 14 [5, 25] (a turbulence intensity in percent, which TurbSim accepts in place of "A"/"B"/"C"). run.py sets RandSeed1 = 13428 + int(os.environ.get("EMA_REPLICATE", "0")), runs the env's turbsim, points InflowWind at the new .bts, runs openfast, and writes stats.json with the max |TwrBsMyt| over the usable time. Keep NumGrid 31×31 and UsableTime 60 unless the profile is too slow; if so, propose smaller values and don't change them yourself. Output via a json parser; timeout_s 900; OMP_NUM_THREADS=1. Check by hand that replicate 0 twice gives identical output, and that EMA_REPLICATE=1 gives a different one. Then `.venv/bin/ema profile examples/openfast/5mw_turb/model.json -n 3`, and report the TurbSim and OpenFAST times separately. Stop and report; don't run a campaign.
```

```text
Stage 5 — first OpenFAST campaign. For examples/openfast/5mw_steady/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on HWindSpeed (n 17), and morris (n_traj 6). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run` (suggest -j 4). After it runs, report: whether repeats are identical, where curve1d puts the kink (expected near 11.4 m/s, "at this resolution"), whether power is flat above it, the morris ranking, and whether PLExp is (possibly) negligible. Expected: wind speed dominant, AirDens important only below rated. Suggest (don't run) a surface2d on (HWindSpeed, AirDens) and, for 5mw_turb, a repeat with 5 replicates at 3 points before any other diagnostic. Stop and report.
```

```text
Stage 6 — OpenFAST troubleshooting. An EMA OpenFAST model (examples/openfast/<example>) fails, is slow, or gives odd values. Diagnose read-only first from the run directory (stdout.txt, stderr.txt, ema_run.json, the .sum and .ech files). Check for: a file OpenFAST can't open (a path still starting "../" inside the archive), the DISCON.dll that won't load (wrong architecture, missing libgfortran: check with `otool -L` or `ldd`), "FATAL" messages from AbortLevel (instability at extreme inputs: a failed run is expected there, so report the inputs), the solver's convergence warnings with the v5 tight coupling, a TurbSim grid that doesn't cover the rotor at a given URef/RefHt, a stats window that starts before the transient ends (compare with TMax), OMP threads oversubscribed, and a wrong interpreter path in model.json. Report the cause and a proposed fix. Ask before changing the env, the archive or model.json.
```

**Gotchas and sources.**
- License Apache-2.0. The 5 MW DISCON source in r-test is Apache-2.0 too.
- Threads: the conda build links OpenMP (`llvm-openmp` on macOS, `libgomp` on Linux). Set `OMP_NUM_THREADS=1` and let EMA's `-j` parallelize.
- Determinism: steady-wind runs are deterministic. With turbulence, the output depends on TurbSim's seed. The driver must seed from `EMA_REPLICATE` (never the clock), so `repeat` measures seed-to-seed noise and reruns reproduce.
- Transients: the start-up (initial rotor speed 12.1 rpm in ElastoDyn) takes tens of seconds to settle. A short `TMax` makes the statistics depend on the transient, which looks like noise in the inputs.
- Kinks are physics: the controller switches regions at rated wind, so the kink in power and the peak in thrust are real features, not solver artefacts.
- Version pitfalls: v5.0.0 changed the glue code and some input files (the `.fst` has `NRotors`, `MirrorRotor`, `CompSoil`). r-test inputs must come from the same tag as the binary.
- Run time: 60–100 s of simulated time per run makes campaigns hours long on a laptop. Use AWS with `-j 16` for anything beyond Morris.
- Sources: https://github.com/OpenFAST/openfast, https://github.com/OpenFAST/openfast/releases, https://openfast.readthedocs.io, https://openfast.readthedocs.io/en/main/source/install/index.html, https://github.com/OpenFAST/r-test, https://github.com/OpenFAST/r-test/tree/v5.0.0/glue-codes/openfast/5MW_Land_DLL_WTurb, https://github.com/OpenFAST/r-test/blob/v5.0.0/glue-codes/openfast/CaseList.md, https://github.com/OpenFAST/r-test/tree/v5.0.0/glue-codes/openfast/5MW_Baseline/ServoData/DISCON, https://github.com/conda-forge/openfast-feedstock, https://anaconda.org/conda-forge/openfast/files

---

#### EnergyPlus (and why not OpenStudio)

**What it is.** The US DOE's whole-building energy simulator: heat balance, HVAC, plant, and daylighting over a year of weather. It's a C++ command-line program that reads an `.idf` (or `.epJSON`) and an `.epw` weather file, and writes CSV, HTML/CSV tables and SQLite. It also ships a Python API (`pyenergyplus`) inside the install. License: a BSD-3-Clause-style license with extra naming conditions (`LICENSE.txt`). Current release **26.1.0 (2026-03-31)**. **26.2.0 is at RC2 (2026-09-22)**, and its final release is due any day (releases come in March and September), so re-check before installing. The repository has moved to https://github.com/NatLabRockies/EnergyPlus. The examples are `testfiles/` in the repository (about 810 `.idf` files), shipped as `ExampleFiles/` in the install, plus weather files in `weather/` (shipped as `WeatherData/`). Docs: https://energyplus.net/documentation and https://bigladdersoftware.com/epx/docs/26-1/.
**OpenStudio is not needed.** OpenStudio 3.11.0 (2026-01-15, with 4.0.0-alpha on 2026-09-01) is an SDK and GUI that writes `.idf` files and runs EnergyPlus. EMA only needs an `.idf` template and the `energyplus` binary. `eppy` 0.6.7 (PyPI, 2026-08-26) can edit IDFs but isn't needed either: plain `$placeholders` in the IDF work, since the example IDFs contain no `$` (checked for the three below).

**Install on an Intel Mac.** Official x86_64 builds exist for 26.1.0 (`Darwin-macOS12.1-x86_64`, `.dmg` 168 MB or `.tar.gz` 215 MB). There's no conda-forge package. The tarball needs no installer and no sudo.
1. Download and unpack into your home directory:
   ```bash
   mkdir -p ~/opt && cd ~/opt
   curl -LO https://github.com/NatLabRockies/EnergyPlus/releases/download/v26.1.0/EnergyPlus-26.1.0-6f2e40d102-Darwin-macOS12.1-x86_64.tar.gz
   tar xf EnergyPlus-26.1.0-6f2e40d102-Darwin-macOS12.1-x86_64.tar.gz
   ```
2. Check (the unpacked directory name is **(unconfirmed)**; list it first):
   ```bash
   ls ~/opt/EnergyPlus-26.1.0-*/
   ~/opt/EnergyPlus-26.1.0-*/energyplus --version
   ```
3. Clear the quarantine attribute if Gatekeeper blocks the unsigned binary: `xattr -dr com.apple.quarantine ~/opt/EnergyPlus-26.1.0-*` **(unconfirmed that it's needed)**.
Known problems: the `.dmg` installs into `/Applications/EnergyPlus-26-1-0` and asks for an admin password, so prefer the tarball. That the tarball contains `ExampleFiles/` and `WeatherData/` is **(unconfirmed)**. Otherwise take the IDF and EPW files from the tagged repository (`testfiles/`, `weather/`).
Sources: https://github.com/NatLabRockies/EnergyPlus/releases/tag/v26.1.0, https://energyplus.net/downloads.

**Install on AWS (Ubuntu 24.04 EC2).**
1. Official tarball for Ubuntu 24.04 x86_64 (240 MB), with no sudo:
   ```bash
   mkdir -p ~/opt && cd ~/opt
   curl -LO https://github.com/NatLabRockies/EnergyPlus/releases/download/v26.1.0/EnergyPlus-26.1.0-6f2e40d102-Linux-Ubuntu24.04-x86_64.tar.gz
   tar xf EnergyPlus-26.1.0-6f2e40d102-Linux-Ubuntu24.04-x86_64.tar.gz
   ~/opt/EnergyPlus-26.1.0-*/energyplus --version
   ```
2. Alternative: the `.sh` installer (installs into `/usr/local`, so it needs sudo).
3. Docker fallback: `nrel/energyplus` stops at **25.1.0** (amd64, 2025-04-02), so it lags. Use it only if pinned by digest and the IDFs are converted to 25.1.
Sources: https://github.com/NatLabRockies/EnergyPlus/releases/tag/v26.1.0, https://hub.docker.com/r/nrel/energyplus/tags.

**Preparing the examples for EMA.**
- Copy the example `.idf` into the model directory as a template (`in.idf.template`). Replace the chosen field values with `$name`. The IDFs contain no `$`, but check again after editing.
- Add `Output:SQLite, SimpleAndTabular;` so a Python parser can read the result with `sqlite3`. Use `TabularDataWithStrings` for annual totals (for example `AnnualBuildingUtilityPerformanceSummary` / `Site and Source Energy` / `Total Site Energy`), or `ReportData` for an output variable.
- The command is `[<abs>/energyplus, "-w", "weather.epw", "-d", ".", "in.idf"]`, with the `.epw` as a static file. `-r` (ReadVarsESO) is only needed for `eplusout.csv`. The options are from the official command-line page.
- One output per `model.json`.
- Keep the run period and time step fixed. Autosized HVAC resizes with the inputs: that is part of the model, but it adds small steps.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `testfiles/1ZoneUncontrolled.idf` (https://github.com/NatLabRockies/EnergyPlus/blob/v26.1.0/testfiles/1ZoneUncontrolled.idf), annual, weather `weather/USA_CO_Golden-NREL.724666_TMY3.epw` (the file's header names Denver/Golden) | one unconditioned zone, heat balance only | wall `R13LAYER` resistance 2.29 [1, 6] m²K/W (log); roof `R31LAYER` resistance 5.46 [2, 10] (log); concrete floor conductivity 1.73 [0.8, 2.5]; wall solar absorptance 0.75 [0.3, 0.9] | annual mean `Zone Mean Air Temperature` (hourly, from the SQL `ReportData`) | smooth and monotone; resistances act through 1/R, so effects **saturate** at high R (curvature in log R); solar absorptance raises the mean nearly linearly; near-additive; possibly one negligible input (the floor) | 2–5 s *(estimate)* | cli (energyplus + template) | python (sqlite3) |
| `testfiles/5Zone_IdealLoadsAirSystems_ReturnPlenum.idf` (https://github.com/NatLabRockies/EnergyPlus/blob/v26.1.0/testfiles/5Zone_IdealLoadsAirSystems_ReturnPlenum.idf), run period extended from 14 Jan to the full year, Chicago weather (`USA_IL_Chicago-OHare_TMY2.epw`, as its header says) | five zones plus a plenum, with ideal loads air systems (no equipment sizing) | heating setpoint 21 [18, 23] °C; cooling setpoint 24 [23, 28] °C; infiltration design flow per zone 0.032 [0.01, 0.1] m³/s (all five objects together); insulation `IN46` conductivity 0.023 [0.015, 0.05] (log) | annual ideal-loads heating energy (sum of `Zone Ideal Loads Supply Air Total Heating Energy`, or the district-heating meter **(unconfirmed which)**); a second model for cooling | heating is nearly linear in the heating setpoint and the infiltration flow, with an interaction between them; the cooling setpoint is **negligible** for heating (the deadband never closes in these ranges); conductivity enters as a power law (`linear_coeffs` with `log_output`) | 20–60 s annual *(estimate)* | cli | python (sqlite3) |
| `testfiles/ASHRAE901_OfficeSmall_STD2019_Denver.idf` (https://github.com/NatLabRockies/EnergyPlus/blob/v26.1.0/testfiles/ASHRAE901_OfficeSmall_STD2019_Denver.idf), with its shipped run period (January only), Denver weather `USA_CO_Denver-Aurora-Buckley.AFB.724695_TMY3.epw` **(unconfirmed which Denver file the test suite uses)** | DOE prototype small office: packaged rooftop units, autosized | window `SimpleGlazingSystem` U-factor 2.04 [1.0, 3.5] W/m²K; SHGC 0.38 [0.2, 0.6]; infiltration multiplier 1 [0.5, 2] on the six `ZoneInfiltration:DesignFlowRate` objects; heating setpoint (occupied) at its schedule value ±2 °C | total site energy for the run period (tabular) | mostly linear; the SHGC effect has one sign in a January run (it offsets heating) and would flip in an annual run (a sign change EMA can show with `curve1d` on SHGC over a year); small **steps** from autosizing and staged DX equipment, which `nonsmooth` may report (at this resolution) | 10–30 s for one month, 1–3 min annual *(estimate)* | cli | python (sqlite3) |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard EnergyPlus 26.1.0 examples into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, any existing EnergyPlus install (ls /Applications | grep -i energyplus; ls ~/opt; `which energyplus`), Docker, free disk space in $HOME, and whether python3's sqlite3 module works in EMA's .venv (`.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"`, read-only). Don't install anything, and don't read .env. Recommend a route: the official 26.1.0 tarball (macOS 12.1 x86_64 on the Mac, Ubuntu 24.04 x86_64 on AWS) unpacked into ~/opt, with no sudo. Note that 26.2.0 is at RC2 (2026-09-22); don't use a release candidate. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install EnergyPlus on this Intel Mac. Ask me first, then download https://github.com/NatLabRockies/EnergyPlus/releases/download/v26.1.0/EnergyPlus-26.1.0-6f2e40d102-Darwin-macOS12.1-x86_64.tar.gz (215 MB) into ~/opt and unpack it. Don't use the .dmg, sudo, or Homebrew. Never install anything into EMA's .venv, and never read .env. Report the unpacked directory's name and whether it contains energyplus, Energy+.idd, ExampleFiles/ and WeatherData/. Run `<dir>/energyplus --version`. If macOS blocks the binary, report the exact message and ask me before removing the quarantine attribute. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install EnergyPlus on this AWS EC2 instance (Ubuntu 24.04 x86_64). Ask me first, then download https://github.com/NatLabRockies/EnergyPlus/releases/download/v26.1.0/EnergyPlus-26.1.0-6f2e40d102-Linux-Ubuntu24.04-x86_64.tar.gz (240 MB) into ~/opt and unpack it. No sudo: the .sh installer needs it, so propose it only if the tarball fails. Never use EMA's .venv, and never read .env. Check `<dir>/energyplus --version`. If a shared library is missing, report the ldd output and ask before installing anything with apt. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — EnergyPlus smoke test. In a scratch directory outside the EMA repo, copy 1ZoneUncontrolled.idf from the install's ExampleFiles (or testfiles/ of the v26.1.0 tag) and USA_CO_Golden-NREL.724666_TMY3.epw from WeatherData (or weather/), then run `<dir>/energyplus -w USA_CO_Golden-NREL.724666_TMY3.epw -d out 1ZoneUncontrolled.idf` and time it. Report the wall time, the last lines of out/eplusout.err (warnings and severe errors), and the files in out/. Then add `Output:SQLite, SimpleAndTabular;` to a copy, run it again, and report the list of tables in eplusout.sql and three rows of TabularDataWithStrings for 'Total Site Energy'. Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the EnergyPlus single-zone example for EMA. Enter plan mode first and show me the plan. Source: 1ZoneUncontrolled.idf of EnergyPlus 26.1.0. Put in examples/energyplus/onezone/: in.idf.template (a copy with $r_wall in R13LAYER's Thermal Resistance, $r_roof in R31LAYER's, $k_floor in 'C5 - 4 IN HW CONCRETE' Conductivity, $alpha_wall in R13LAYER's Solar Absorptance, plus `Output:SQLite, SimpleAndTabular;`; grep for any other '$' and escape it as '$$'), the static file USA_CO_Golden-NREL.724666_TMY3.epw, parse_eplus.py (an isolated python parser that opens eplusout.sql with sqlite3 and returns the annual mean of the hourly 'Zone Mean Air Temperature' for ZONE ONE), and model.json. Inputs: r_wall 2.29 [1, 6] scale log, r_roof 5.456 [2, 10] scale log, k_floor 1.73 [0.8, 2.5], alpha_wall 0.75 [0.3, 0.9]. The command is the absolute energyplus path, "-w", "USA_CO_Golden-NREL.724666_TMY3.epw", "-d", ".", "in.idf"; env OMP_NUM_THREADS=1; timeout_s 120. Follow docs/guides/input_deck_model.md, examples/swmm/ and examples/beam/model_parser.json. Check by hand that the nominal run matches an untouched run of the original IDF to printed precision. Then `.venv/bin/ema profile examples/energyplus/onezone/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the EnergyPlus five-zone ideal-loads example. Plan mode first. Source: testfiles/5Zone_IdealLoadsAirSystems_ReturnPlenum.idf (26.1.0). Put in examples/energyplus/fivezone_ideal/: a template with the RunPeriod changed to 1 Jan–31 Dec (show me which run period you change, since the file has two), the heating and cooling setpoint schedules' values replaced by $t_heat and $t_cool (find the schedules the DualSetPoint objects use and show me them first), all five ZoneInfiltration:DesignFlowRate 'Design Flow Rate' fields replaced by $infil, IN46's Conductivity by $k_ins, and Output:SQLite added. Weather: USA_IL_Chicago-OHare_TMY2.epw as a static file. Inputs: t_heat 21 [18, 23], t_cool 24 [23, 28], infil 0.032 [0.01, 0.1], k_ins 0.023 [0.015, 0.05] scale log. Output (model.json): annual heating energy summed over the zones' ideal loads systems. Tell me which report variable or meter you use and why; model_cooling.json does the same for cooling. Check by hand that raising t_heat by 1 °C raises heating. Then `.venv/bin/ema profile ... -n 3` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the EnergyPlus small-office prototype. Plan mode first. Source: testfiles/ASHRAE901_OfficeSmall_STD2019_Denver.idf (26.1.0), keeping its January run period. Put in examples/energyplus/small_office/: a template with WindowMaterial:SimpleGlazingSystem 'Glazing Layer' U-Factor → $u_win and SHGC → $shgc, a multiplier $infil_mult applied to the six ZoneInfiltration:DesignFlowRate objects (list their current values, and write each as value*multiplier in the driver or template, whichever you propose), and Output:SQLite. Weather: find which Denver EPW the file expects (its header comments) and use that one from weather/. Inputs: u_win 2.04 [1.0, 3.5], shgc 0.38 [0.2, 0.6], infil_mult 1 [0.5, 2]. Output: 'Total Site Energy' (GJ) from the tabular data. Check by hand that the nominal run matches the untouched IDF. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first EnergyPlus campaign. For examples/energyplus/onezone/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), and curve1d on r_wall (n 11). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run` (suggest -j 4). After it runs, report: whether repeats are identical (expected: yes), the morris ranking and monotone flags, whether k_floor is (possibly) negligible, and the curvature curve1d shows in r_wall (saturation expected). Suggest (don't run) sobol with n_base 128 and linear_coeffs with log_output. Stop and report.
```

```text
Stage 6 — EnergyPlus troubleshooting. An EMA EnergyPlus model (examples/energyplus/<example>) fails or gives odd values. Diagnose read-only first from the run directory: eplusout.err (Severe/Fatal lines), eplusout.end, stdout.txt, ema_run.json. Check for: a template substitution error (a literal '$' in the IDF, or a placeholder EMA didn't fill), an IDD version mismatch ('Version' object ≠ 26.1), a missing or wrong weather file (-w path, or the design days' location vs the EPW), Energy+.idd not found (the binary moved out of its install directory), sizing failures at extreme inputs (a failed run in a region is data: report the inputs), a parser that reads the wrong table or units (GJ vs kWh), and threads (-j or OMP_NUM_THREADS). Report the cause and a proposed fix. Ask before changing the template or model.json.
```

**Gotchas and sources.**
- License: BSD-3-Clause-style with an extra clause on the "EnergyPlus" name. Weather files carry their own terms.
- Threads: EnergyPlus can use several threads for some calculations (`-j`). Leave `-j` unset (1) and set `OMP_NUM_THREADS=1`.
- Determinism: deterministic, but HVAC and zone iterations converge to tolerances, and autosizing jumps between sizes, so outputs can show small steps. `nonsmooth` reports them "at this resolution".
- Run time: an annual run with real HVAC takes about a minute. Shorten the run period (as the prototype's test file already does) for exploration.
- Version pitfalls: an IDF must match the binary's version (`Version,26.1;`). IDFs from other versions need the `IDFVersionUpdater` in the install. 26.2.0 is imminent: pin 26.1.0 and record the version in each `model.json` description.
- Repository moved to `NatLabRockies`. Release URLs under `NREL/` still redirect **(for now)**.
- Sources: https://energyplus.net, https://energyplus.net/downloads, https://github.com/NatLabRockies/EnergyPlus, https://github.com/NatLabRockies/EnergyPlus/releases/tag/v26.1.0, https://github.com/NatLabRockies/EnergyPlus/blob/develop/doc/running-energyplus-from-command-line.md, https://github.com/NatLabRockies/EnergyPlus/tree/v26.1.0/testfiles, https://github.com/NatLabRockies/EnergyPlus/tree/v26.1.0/weather, https://bigladdersoftware.com/epx/docs/26-1/getting-started/what-is-energyplus.html, https://github.com/NatLabRockies/OpenStudio/releases, https://pypi.org/project/eppy/, https://hub.docker.com/r/nrel/energyplus/tags

---

#### OpenSees / OpenSeesPy

**What it is.** The Open System for Earthquake Engineering Simulation (UC Berkeley, PEER): nonlinear finite elements for structural and geotechnical systems, with fiber sections, hysteretic materials, pushover and time-history analysis. It's C++, with a Tcl interpreter (`OpenSees`) and a Python module (OpenSeesPy). **License: not open source in the OSI sense.** The UC Regents' `COPYRIGHT` allows use by educational, research and non-profit entities for noncommercial purposes, and internal use by others. Commercial distribution needs a license from UC. Current release **OpenSees v3.8.0 (2026-02-18)**; PyPI `openseespy` **3.8.0.0 (2026-03-18)**. Examples: the OpenSeesPy docs list structural examples at https://openseespydoc.readthedocs.io/en/latest/src/structure.html (elastic truss, nonlinear truss, portal frame, moment curvature, RC frame gravity, RC frame pushover, three-story steel building, FRP-confined column), plus earthquake examples such as the RC frame under El Centro (https://openseespydoc.readthedocs.io/en/latest/src/RCFrameEarthquake.html). About 20 in all **(unconfirmed count)**, each a downloadable `.py`.

**Install on an Intel Mac.** **The PyPI route fails on Intel.** `openseespy` 3.8.0.0 is a meta-package that pulls `openseespymac` on macOS, and `openseespymac` 3.8.0.0 has only a `macosx_13_0_arm64` wheel (the last pure `py3-none-any` Mac upload was 3.4.0.2 in 2022, too old to use). conda-forge's `opensees` 3.8.0 **does** build osx-64 (Python 3.10–3.14, uploaded 2026-03-24), with the Tcl `OpenSees` binary and a Python module whose recipe test is `import opensees`.
1. Create the env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-opensees -c conda-forge python=3.12 opensees=3.8.0 numpy
   ```
2. Check:
   ```bash
   ~/miniforge3/envs/ema-opensees/bin/python -c "import opensees as ops; ops.wipe(); ops.model('basic','-ndm',2,'-ndf',3); print('ok')"
   ```
Known problems: the documented import is `import openseespy.opensees as ops`. The conda module is imported as `opensees`, and that it has the same functions is **(unconfirmed)**. Write drivers as `try: import openseespy.opensees as ops` / `except ImportError: import opensees as ops`. The conda build links Open MPI and MUMPS; serial use shouldn't start MPI **(unconfirmed)**.
Sources: https://pypi.org/project/openseespy/3.8.0.0/, https://pypi.org/project/openseespymac/#files, https://anaconda.org/conda-forge/opensees/files, https://github.com/conda-forge/opensees-feedstock (meta.yaml), https://github.com/OpenSees/OpenSees/releases/tag/v3.8.0.

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred, for identical code on both machines: the same conda env (the linux-64 `opensees` 3.8.0 exists).
2. Alternative: PyPI into a separate venv. `openseespylinux` 3.8.0.0 requires Python ≥ 3.12, and Ubuntu 24.04's `python3` is 3.12:
   ```bash
   python3 -m venv ~/venvs/ema-opensees
   ~/venvs/ema-opensees/bin/pip install openseespy==3.8.0.0
   ~/venvs/ema-opensees/bin/python -c "import openseespy.opensees as ops; print('ok')"
   ```
3. There's no official Docker image **(unconfirmed; none found)**.
Sources: https://pypi.org/project/openseespylinux/, https://openseespydoc.readthedocs.io, https://anaconda.org/conda-forge/opensees/files.

**Preparing the examples for EMA.**
- Download the example `.py` (and its helpers: `RCFrameGravity.py`, `ReadRecord.py`, `elCentro.at2`) into the model directory. Turn it into `run.py`, which reads a key = value deck rendered from a template (as `examples/cantera/`), or `argparse` options (as `examples/beam/model_args.json`).
- Delete the plotting and the `PASSED/FAILED` file writes. Print one line: `EMA_OUTPUT = <value:.12e>`.
- When an analysis step fails to converge (`ops.analyze` returns non-zero), print nothing and exit non-zero. EMA then records a failed run, and the failure region becomes data. Don't retry with other algorithms: that would hide the boundary.
- Helper files the driver imports (`RCFrameGravity.py`) must be in the model directory. The command names only `run.py`, so the version hash doesn't cover the helpers (CLAUDE.md's Known limitations: only the scripts the command names are hashed, not the modules they import). Merge them into `run.py` if possible.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Nonlinear truss, `NonlinearTruss.py` (https://openseespydoc.readthedocs.io/en/latest/src/nonlinearTruss.html) | three truss bars to an apex, `Hardening` material, load control in 1000 steps | load `Px` 160 [50, 300] kip; yield stress `sY` 36 [24, 60] ksi; hardening `alpha` 0.05 [0.01, 0.1]; `E` 29000 [25000, 33000] ksi | horizontal displacement of node 4 at full load | linear in `Px` and ∝ 1/E while elastic; a **kink** where the bars yield (on a line Px ∝ sY in the (Px, sY) plane: `surface2d` and `nonsmooth`); after yielding, `alpha` dominates and `E` becomes nearly negligible, a strong interaction | < 1 s *(estimate)* | cli (env python + `run.py`) | regex on stdout |
| RC frame pushover, `RCFrameGravity.py` + `RCFramePushOver.py` (https://openseespydoc.readthedocs.io/en/latest/src/RCFramePushOver.html) | 2D one-bay RC portal frame, fiber sections (Concrete01 core/cover, Steel01), gravity P = 180, then displacement-controlled pushover (dU 0.1 in, maxU 15 in) | core `fpc` 6 [4, 8] ksi (cover scaled with it); steel `fy` 60 [40, 80] ksi; axial load `P` 180 [0, 500] kip; target drift `maxU` 15 → fixed | base shear at a roof displacement of 5 in (or the peak base shear) | `fy` dominant and monotone; P-Δ softening with `P`, an interaction with `fy`; **failure region**: non-convergence at high P and low fpc (concrete crushing), which the analysis reports as a failed run | 2–5 s *(estimate)* | cli | regex |
| RC frame earthquake, `RCFrameEarthquake.py` with `elCentro.at2` (https://openseespydoc.readthedocs.io/en/latest/src/RCFrameEarthquake.html) | the same frame under the El Centro record, Newmark (γ 0.5, β 0.25), Rayleigh damping, dt 0.01 s | ground-motion scale factor 1 [0.25, 3] (log); `fy` 60 [40, 80]; damping factor 0.000625 [0.0002, 0.002] (log) | peak roof drift | nearly linear in the scale factor while elastic, then steeper with **kinks** as members yield (`curve1d` on the scale factor); rougher than the pushover (hysteresis makes the peak drift sensitive), so check with `repeat` that serial runs are identical; convergence failures at large scale factors | 10–40 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard OpenSeesPy 3.8 examples into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, Miniforge conda/mamba and any env named ema-opensees, python3 versions on PATH, Homebrew version (don't use it), and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, conda-forge `opensees=3.8.0` in env ema-opensees (PyPI's openseespymac 3.8.0.0 is arm64-only, so `pip install openseespy` fails on Intel); on Ubuntu 24.04, the same conda env, or `pip install openseespy==3.8.0.0` in a separate venv (Python ≥ 3.12). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install OpenSees on this Intel Mac. Use Miniforge (conda-forge only): `mamba create -n ema-opensees -c conda-forge python=3.12 opensees=3.8.0 numpy`. Don't use pip for openseespy here, and never install into EMA's .venv or read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Check: `<env>/bin/python -c "import opensees as ops; ops.wipe(); ops.model('basic','-ndm',2,'-ndf',3); print('ok')"`, and also try `import openseespy.opensees` and report which import works. Report the env's absolute python path and whether the `OpenSees` Tcl binary is in <env>/bin. Stop at the first error and report the output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install OpenSees on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge and the same env ema-opensees (python=3.12 opensees=3.8.0 numpy from conda-forge). If conda fails, propose (don't run) a venv at ~/venvs/ema-opensees with `pip install openseespy==3.8.0.0`. Never use EMA's .venv, and never read .env. Ask before any sudo, and before downloads over 1 GB. Check with the same two-line model as on the Mac, and report the import that works and the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — OpenSees smoke test. In a scratch directory outside the EMA repo, download Truss.py (the elastic truss example; find its link on https://openseespydoc.readthedocs.io/en/latest/src/truss.html) and NonlinearTruss.py (https://openseespydoc.readthedocs.io/en/latest/src/nonlinearTruss.html). Change the import line to the one that worked in Stage 2, remove the plotting, and run both with the ema-opensees env's python and OMP_NUM_THREADS=1. Time them. Report the printed results, whether the elastic truss prints its "Passed" check, and the wall times. Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the OpenSees nonlinear truss for EMA. Enter plan mode first and show me the plan. Source: NonlinearTruss.py from the OpenSeesPy docs (v3.8). Put in examples/opensees/nonlinear_truss/: run.py (inputs from a key = value deck rendered from truss.template, or argparse options like examples/beam/model_args.json, whichever you propose), with Px = 160 [50, 300], sY = 36 [24, 60], alpha = 0.05 [0.01, 0.1], E = 29000 [25000, 33000], the example's geometry, A = 4 and 1000 load steps, no plotting, printing `EMA_OUTPUT = <node 4 x-displacement, %.12e>`; if ops.analyze returns non-zero, exit with status 1 and print nothing. model.json: the ema-opensees env's absolute python path and run.py; env OMP_NUM_THREADS=1; timeout_s 60; regex "EMA_OUTPUT = (\S+)". Check by hand: with Px small enough to stay elastic, halving E doubles the displacement. Then `.venv/bin/ema profile examples/opensees/nonlinear_truss/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the OpenSees RC frame pushover. Plan mode first. Sources: RCFrameGravity.py and RCFramePushOver.py from the OpenSeesPy docs. Put in examples/opensees/rc_pushover/ a single run.py that merges both (so the version hash covers all the code; show me the merge), with inputs fpc = 6 [4, 8] (core; scale the cover's f'c by the same ratio, and say so), fy = 60 [40, 80], P = 180 [0, 500]. Keep the fiber section, dU = 0.1 and maxU = 15, and print `EMA_OUTPUT = <base shear at roof displacement 5.0 in, %.12e>` (sum the column base reactions after ops.reactions()). Non-convergence before 5 in means exit 1 and no output. Command-line model as in 4.1, timeout_s 120. Check by hand that the nominal run completes and that fy = 80 gives a larger base shear than fy = 40. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the OpenSees RC frame under El Centro. Plan mode first. Sources: RCFrameEarthquake.py, ReadRecord.py and elCentro.at2 from the OpenSeesPy docs. Put in examples/opensees/rc_elcentro/: run.py with the gravity model merged in, and ReadRecord's function merged in too; elCentro.at2 as a static file. Inputs: scale = 1 [0.25, 3] (scale log), fy = 60 [40, 80], damp = 0.000625 [0.0002, 0.002] (scale log; the Rayleigh stiffness factor the example uses). Output: `EMA_OUTPUT = <peak |roof displacement| over the record, %.12e>`. Keep the example's fallback algorithm loop only if it is part of the published example, and tell me what it does; otherwise a failed step means exit 1. timeout_s 300. Check by hand that repeating the nominal run gives identical output. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first OpenSees campaign. For examples/opensees/nonlinear_truss/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on Px (n 21), surface2d on (Px, sY) (n 15 per side), and morris (n_traj 8). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run`. After it runs, report: repeatability, where curve1d finds the kink in Px (at this resolution), whether surface2d shows the yield line Px ∝ sY, the morris ranking, and whether E is (possibly) negligible (expected: important below yield, weak above, so not negligible over the whole box). Suggest (don't run) nonsmooth and the same campaign for rc_pushover. Stop and report.
```

```text
Stage 6 — OpenSees troubleshooting. An EMA OpenSees model (examples/opensees/<example>) fails or gives odd values. Diagnose read-only first from the run directory (stdout.txt, stderr.txt, ema_run.json). Check for: an import error (openseespy.opensees vs opensees; the wrong env's python in model.json), MPI or MUMPS start-up messages from the conda build, "analyze failed" / "Newton failed to converge" (expected at extreme inputs; confirm it's reproducible and report the inputs), a leftover model when the driver doesn't call ops.wipe(), outputs read at the wrong step (a pushover stopping before 5 in), a ground-motion file path the driver can't find (it must be a static file in the run directory), and threads (OMP_NUM_THREADS). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License: the UC Regents' noncommercial/internal-use terms, not an OSI license. Fine for research use. Check with UC before commercial work or redistributing binaries.
- Threads and MPI: the conda build links Open MPI, MUMPS and OpenMP. Run serially with `OMP_NUM_THREADS=1`, and never under `mpirun`.
- Determinism: serial static and dynamic analyses are deterministic. Newton iterations stop at a tolerance (`test NormDispIncr` in the examples), so outputs can be rough at the tolerance's level. Tighten it if `curve1d` shows jitter.
- Failures are data: convergence failures mark real limit states (crushing, instability) or numerical trouble. Report them as a failure region, and don't retry them away.
- Intel Mac: PyPI has no Intel wheel for 3.8, so conda-forge is the only current route. The docs' import line differs from the conda module's.
- Sources: https://opensees.berkeley.edu, https://github.com/OpenSees/OpenSees, https://github.com/OpenSees/OpenSees/releases/tag/v3.8.0, https://github.com/OpenSees/OpenSees/blob/master/COPYRIGHT, https://openseespydoc.readthedocs.io, https://openseespydoc.readthedocs.io/en/latest/src/structure.html, https://openseespydoc.readthedocs.io/en/latest/src/nonlinearTruss.html, https://openseespydoc.readthedocs.io/en/latest/src/RCFrameGravity.html, https://openseespydoc.readthedocs.io/en/latest/src/RCFramePushOver.html, https://openseespydoc.readthedocs.io/en/latest/src/RCFrameEarthquake.html, https://opensees.github.io/OpenSeesDocumentation/user/pythonInstall.html, https://pypi.org/project/openseespy/, https://pypi.org/project/openseespymac/, https://pypi.org/project/openseespylinux/, https://anaconda.org/conda-forge/opensees/files, https://github.com/conda-forge/opensees-feedstock

---

#### Project Chrono / PyChrono

**What it is.** A multiphysics dynamics engine: rigid and flexible multibody systems, frictional contact (NSC complementarity or SMC penalty), vehicles, granular media, FEA. It's C++, with the Python bindings PyChrono. BSD-3-Clause. Current release **10.0.0 (2026-04-07)**. Python demos are in `src/demos/python/` of https://github.com/projectchrono/chrono (109 `.py` files at tag 10.0.0; `mbs/` alone has 25, such as `demo_MBS_spring.py`, `demo_MBS_crank_plot.py`, `demo_MBS_friction.py` and `demo_MBS_collisionSMC.py`). Docs: https://api.projectchrono.org. Nearly every demo opens an Irrlicht window, so each needs its visualization loop replaced by a plain time loop.

**Install on an Intel Mac.** The official instruction is `conda install projectchrono::pychrono -c conda-forge`, but the **`projectchrono` channel has no osx-64 build since 8.0.0** (10.0.0 is linux-64, linux-aarch64, osx-arm64 and win-64). **conda-forge's `pychrono` 10.0.0 does build osx-64** (Python 3.10–3.14, 2026-04-02). Its build turns Irrlicht, vehicle, postprocess and Cascade **off** (`build_pychrono.sh`), so only the core modules are there, which is enough for the MBS demos without graphics. (PyPI's `pychrono` 1.1.0 is not Project Chrono's package; don't use it.)
1. Create the env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-chrono -c conda-forge python=3.12 pychrono=10.0.0 numpy
   ```
2. Check:
   ```bash
   ~/miniforge3/envs/ema-chrono/bin/python -c "import pychrono as chrono; s = chrono.ChSystemNSC(); print(chrono.__file__)"
   ```
Known problems: demos that `import pychrono.irrlicht` fail with this build, so the driver must not import it. Whether the version is exposed as `pychrono.__version__` is **(unconfirmed)**, so take it from `conda list pychrono`.
Sources: https://api.projectchrono.org/pychrono_installation.html, https://anaconda.org/projectchrono/pychrono/files, https://anaconda.org/conda-forge/pychrono/files, https://github.com/conda-forge/pychrono-feedstock (recipe/build_pychrono.sh).

**Install on AWS (Ubuntu 24.04 EC2).**
1. The same conda-forge env (the linux-64 10.0.0 build exists), so both machines match.
2. Alternative: `mamba create -n ema-chrono -c conda-forge -c projectchrono python=3.12 projectchrono::pychrono=10.0.0` (the official channel, linux-64, which includes Irrlicht and the vehicle module) **(unconfirmed which modules the projectchrono build enables)**.
3. Source build with CMake (https://api.projectchrono.org/tutorial_install_chrono.html) only if a module is missing.
Sources: https://anaconda.org/conda-forge/pychrono/files, https://anaconda.org/projectchrono/pychrono/files, https://api.projectchrono.org/pychrono_installation.html.

**Preparing the examples for EMA.**
- Copy the demo into `examples/chrono/<example>/run.py`. Delete every `pychrono.irrlicht` / `vis.` line and `matplotlib`, and replace `while vis.Run():` with `while sys.GetChTime() < T_END: sys.DoStepDynamics(dt)`.
- Read the inputs from a key = value deck (as `examples/cantera/`) or from `argparse` options.
- Print one line, `EMA_OUTPUT = <value:.12e>`.
- Fix the step size and the solver settings. Set Chrono's thread counts to 1 (`sys.SetNumThreads(1, 1, 1)` in recent versions **(unconfirmed signature for 10.0)**) as well as `OMP_NUM_THREADS=1`: collision detection and the solver can use threads, and threaded contact solves can change the last digits.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `src/demos/python/mbs/demo_MBS_spring.py` (https://github.com/projectchrono/chrono/blob/10.0.0/src/demos/python/mbs/demo_MBS_spring.py): body 1 on a `ChLinkTSDA`, no gravity, dt 1e-3 | damped spring-mass, 1 DOF in effect (mass 1, start 3 m below the anchor) | `spring_coef` 50 [10, 200] (log); `damping_coef` 1 [0.1, 10] (log); `rest_length` 1.5 [1, 2] | spring length at t = 5 s | known answer: a damped oscillator. **Affine in `rest_length`** (equilibrium shifts); **oscillatory in `spring_coef`** (the phase √k·t sweeps several periods, so `fourier` needs high degree and `curve1d` shows many turning points); decay in `damping_coef` gives an interaction. A good check that EMA doesn't read oscillation as noise | < 1 s (5000 steps) *(estimate)* | cli (env python + `run.py`) | regex |
| `src/demos/python/mbs/demo_MBS_crank_plot.py` (https://github.com/projectchrono/chrono/blob/10.0.0/src/demos/python/mbs/demo_MBS_crank_plot.py) | slider-crank driven at constant angular speed (motor), gravity | `crank_rad` 0.4 [0.2, 0.6]; `rod_length` 1.5 [1, 3]; angular speed π [1, 10] rad/s (log) | max piston speed over the second revolution | kinematic, so a nearly closed form: speed ≈ ω r (1 + r/(2L)) to first order. **Exactly linear in ω** (`linear_coeffs` with `log_output`: exponent 1); `crank_rad` dominant; `rod_length` weak (near-negligible for long rods); smooth; deterministic | < 1 s *(estimate)* | cli | regex |
| `src/demos/python/mbs/demo_MBS_friction.py` (https://github.com/projectchrono/chrono/blob/10.0.0/src/demos/python/mbs/demo_MBS_friction.py), reduced to **one** rolling sphere on the floor, walls moved out of reach | NSC frictional contact with rolling friction (Bullet collision) | rolling friction 0.02 [0.001, 0.05] (log); sliding friction 0.4 [0.1, 0.8]; initial angular speed 10 [2, 20] rad/s | distance travelled at t = 5 s | **nonsmooth**: the sphere either stops before 5 s (distance plateaus: a power law ≈ v₀²/μ_r) or is still rolling (distance grows with t); the boundary between them is a kink curve in (μ_r, v₀) for `surface2d`/`nonsmooth`; sliding friction is near-negligible when the sphere starts rolling without slip (initial linear speed = ω r in the demo); iterative-solver roughness: check with `repeat` and a fine `curve1d` | 1–3 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard PyChrono 10.0.0 demos into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, Miniforge conda/mamba and any env named ema-chrono, Homebrew version (don't use it), and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge `pychrono=10.0.0` in env ema-chrono (conda-forge builds osx-64 and linux-64; the projectchrono channel has no osx-64 build since 8.0.0, and conda-forge's build has no Irrlicht). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install PyChrono on this Intel Mac. Use Miniforge (conda-forge only, not the projectchrono channel, which has no osx-64 10.0.0): `mamba create -n ema-chrono -c conda-forge python=3.12 pychrono=10.0.0 numpy`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Check: `<env>/bin/python -c "import pychrono as chrono; s = chrono.ChSystemNSC(); print('ok')"`, and report `conda list -n ema-chrono pychrono` and whether `import pychrono.irrlicht` fails (expected). Report the env's absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install PyChrono on this AWS EC2 instance (Ubuntu 24.04 x86_64). Preferred: Miniforge and the same env ema-chrono (python=3.12 pychrono=10.0.0 numpy from conda-forge). Never use EMA's .venv, and never read .env. Ask before any sudo, and before downloads over 1 GB. If conda-forge fails, propose (don't run) the projectchrono channel's linux-64 build. Check as on the Mac, and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — PyChrono smoke test. In a scratch directory outside the EMA repo, download src/demos/python/mbs/demo_MBS_spring.py from the 10.0.0 tag of github.com/projectchrono/chrono. Make a headless copy: remove the pychrono.irrlicht import and every vis. line, and replace the render loop with a loop to t = 5 s at dt 1e-3 that prints spring_1.GetLength() at the end. Run it with the ema-chrono env's python and OMP_NUM_THREADS=1, twice, and time it. Report the output of both runs (they should be identical) and the wall time. Also report which thread-count setter ChSystemNSC has in this version (look at dir(chrono.ChSystemNSC) for SetNumThreads and report its signature). Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the PyChrono spring example for EMA. Enter plan mode first and show me the plan. Source: demo_MBS_spring.py (Chrono 10.0.0). Put in examples/chrono/spring/: run.py (headless, as in Stage 3, keeping only body_1 and spring_1), reading spring_coef = 50 [10, 200] (scale log), damping_coef = 1 [0.1, 10] (scale log), rest_length = 1.5 [1, 2] from a key = value deck rendered from spring.template (as examples/cantera/), setting Chrono's threads to 1, stepping at 1e-3 to t = 5, and printing `EMA_OUTPUT = <spring_1.GetLength(), %.12e>`. model.json: the ema-chrono env's absolute python path and run.py; env OMP_NUM_THREADS=1; timeout_s 60; regex. Check by hand against the closed-form damped oscillator for body_1 (mass 1, starting length from the demo's positions, zero initial velocity): report both numbers at the nominal inputs. Then `.venv/bin/ema profile examples/chrono/spring/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the PyChrono slider-crank. Plan mode first. Source: demo_MBS_crank_plot.py (Chrono 10.0.0). Put in examples/chrono/crank/: headless run.py without matplotlib or irrlicht, with inputs crank_rad = 0.4 [0.2, 0.6], rod_length = 1.5 [1, 3], omega = 3.14159 [1, 10] (scale log; replace the ChFunctionConst(CH_PI) with it), running for two revolutions (t_end = 4π/omega, dt 1e-3) and printing `EMA_OUTPUT = <max |piston x-speed| over the second revolution, %.12e>`. Keep the floor large enough for the longest rod and say so. Command-line model as in 4.1. Check by hand against the slider-crank formula v ≈ ω r (sin θ + r sin 2θ / (2L)) at the nominal inputs. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the PyChrono rolling-friction example. Plan mode first. Source: demo_MBS_friction.py (Chrono 10.0.0). Put in examples/chrono/rolling/: a headless run.py with one sphere (radius 0.5, density 1000) on the demo's floor box, the walls removed or moved beyond reach (tell me which), NSC contact with Bullet as in the demo, inputs mu_roll = 0.02 [0.001, 0.05] (scale log), mu_slide = 0.4 [0.1, 0.8] and omega0 = 10 [2, 20], initial linear speed omega0*radius as in the demo, dt 1e-3 to t = 5, printing `EMA_OUTPUT = <x displacement of the sphere, %.12e>`. Set Chrono's threads to 1 and OMP_NUM_THREADS=1. Check by hand: run the nominal point 3 times and report whether the outputs are bit-identical. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first PyChrono campaign. For examples/chrono/rolling/model.json, write campaign.json with repeat (n_points 3, replicates 3), curve1d on mu_roll (n 21), surface2d on (mu_roll, omega0) (n 15 per side), and morris (n_traj 8). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run`. After it runs, report: whether repeats are identical (if not, the measured noise), the plateau and kink curve1d and surface2d find (the sphere stopping before 5 s), the morris ranking, and whether mu_slide is (possibly) negligible. Suggest (don't run) linear_coeffs with log_output on examples/chrono/crank (expected exponent 1 in omega). Stop and report.
```

```text
Stage 6 — PyChrono troubleshooting. An EMA PyChrono model (examples/chrono/<example>) fails or gives odd values. Diagnose read-only first from the run directory. Check for: an ImportError for pychrono.irrlicht or pychrono.vehicle (not in the conda-forge build: remove it from the driver), a changed API between Chrono versions (method names in demos from another tag), bodies passing through each other (a time step or collision envelope too large for the inputs), outputs that differ between replicates (threads: OMP_NUM_THREADS and Chrono's own thread setters; the solver's iteration count), a simulation that stops early (an exception in the loop), and a wrong interpreter path in model.json. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License BSD-3-Clause.
- Threads: the conda-forge build enables OpenMP. Set `OMP_NUM_THREADS=1` and Chrono's thread counts to 1, or contact results may differ between replicates.
- Determinism and noise: NSC contact solves a complementarity problem by iteration to a fixed iteration count or tolerance. Outputs that depend on contact (stopping distance) can be rough at the solver's precision. `repeat` checks run-to-run determinism, and a fine `curve1d` shows the roughness in an input.
- Nonsmooth by nature: stick-slip, impacts and stopping produce kinks and plateaus. That's what `nonsmooth` should find.
- Visualization: nearly every demo uses Irrlicht, which conda-forge's build lacks. Budget time to make each demo headless.
- API churn: Chrono renamed much of its API in 9.0 (`ChVectorD` → `ChVector3d`, `SetBodyFixed` → `SetFixed`). Use demos from the same tag as the installed version.
- Sources: https://projectchrono.org, https://github.com/projectchrono/chrono, https://github.com/projectchrono/chrono/releases/tag/10.0.0, https://github.com/projectchrono/chrono/tree/10.0.0/src/demos/python/mbs, https://api.projectchrono.org/pychrono_installation.html, https://api.projectchrono.org/tutorial_install_chrono.html, https://anaconda.org/conda-forge/pychrono/files, https://anaconda.org/projectchrono/pychrono/files, https://github.com/conda-forge/pychrono-feedstock

---

#### Meep

**What it is.** MIT's finite-difference time-domain (FDTD) electromagnetics solver: waveguides, resonators, gratings, flux spectra, and resonant modes through Harminv. C++ core with a Python interface (PyMeep). GPL-2.0-or-later. Current release **v1.34.0 (2026-07-09)**. The examples are about 110 scripts in `python/examples/` of https://github.com/NanoComp/meep, many with notebooks, and the tutorials at https://meep.readthedocs.io/en/master/Python_Tutorials/Basics/ explain them (`straight-waveguide.py`, `bend-flux.py`, `ring.py`, `holey-wvg-cavity.py`, ...). 2D examples at resolution 10–20 run in seconds, so Meep fits EMA well.

**Install on an Intel Mac.** conda-forge `pymeep` 1.34.0 has osx-64 builds, both serial (`nompi`) and MPICH, for **Python 3.10–3.13** (no 3.14 build yet). The Meep docs say binary packages exist for "Linux and macOS (x86 and ARM)".
1. Create a serial env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-meep -c conda-forge python=3.12 "pymeep=1.34.0=nompi_*" numpy
   ```
2. Check:
   ```bash
   ~/miniforge3/envs/ema-meep/bin/python -c "import meep as mp; print(mp.__version__)"
   ```
Known problems: an unpinned `pymeep` may resolve to an MPI build, which then needs `mpirun` for parallel runs and prints MPI start-up messages. Pin `nompi`. The tutorials also need `matplotlib` and `h5utils`, but the drivers below use neither.
Sources: https://meep.readthedocs.io/en/master/Installation/, https://anaconda.org/conda-forge/pymeep/files, https://github.com/NanoComp/meep/releases/tag/v1.34.0.

**Install on AWS (Ubuntu 24.04 EC2).**
1. The same conda env with the Linux Miniforge installer (the linux-64 1.34.0 `nompi` builds exist).
2. Fallbacks: Ubuntu's `python3-meep` package (noble's version is older than 1.34 **(unconfirmed which)**), or a source build per the docs. Neither is recommended.
3. Check as on the Mac.
Sources: https://meep.readthedocs.io/en/master/Installation/, https://anaconda.org/conda-forge/pymeep/files.

**Preparing the examples for EMA.**
- Copy the example into `run.py`. Turn its hard-coded parameters (`n`, `w`, `r` in `ring.py`, for example) into `argparse` options passed on the command line (as `examples/beam/model_args.json`), or a deck.
- Remove the field output (`output_epsilon`, `output_efield_z`, the h5 files) and the plotting.
- Print one line, `EMA_OUTPUT = <value:.12e>`.
- Keep `resolution` fixed: it is the discretization, not an input.
- For Harminv outputs, the driver must pick one mode deterministically, for example the mode with the largest Q in a fixed frequency window. Otherwise the output jumps when a different mode is chosen, and `nonsmooth` reports a jump that comes from the driver.
- Geometric inputs are smooth thanks to Meep's subpixel averaging, but pixel-scale wiggles remain **(expected; measure with a fine `curve1d`)**.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `python/examples/ring.py` (https://github.com/NanoComp/meep/blob/v1.34.0/python/examples/ring.py), resolution 10 | 2D dielectric ring resonator, Gaussian pulse, Harminv at a point in the ring (the tutorial finds modes at 0.118, 0.147 and 0.175 with Q ≈ 81, 316 and 1677) | `n` 3.4 [2.5, 3.6]; `w` 1 [0.8, 1.2]; `r` 1 [0.8, 1.5] | frequency of the mode in the window [0.14, 0.16] (second model: that mode's Q) | frequency decreases smoothly with `n`, `w` and `r` (∝ 1/(n·size) roughly: a power law for `linear_coeffs` with `log_output`); Q grows steeply (roughly exponentially) with `n` and `r`, so use `log_output` or a log-scale Q; **jumps** if the window catches a different mode at the edges of the box, which marks the box as too wide | 2–10 s *(estimate)* | cli (env python + `run.py`) | regex |
| `python/examples/bend-flux.py` (https://github.com/NanoComp/meep/blob/v1.34.0/python/examples/bend-flux.py), resolution 10 | 90° waveguide bend, transmission normalized by a straight-waveguide run (two simulations per run) | `eps` 12 [6, 13] (the waveguide's ε); `w` 1 [0.6, 1.4]; `fcen` 0.15 [0.1, 0.2] | band-averaged bend transmittance (transmitted flux divided by the straight guide's) over the 100 frequencies | bounded in [0, 1]; strong `eps` × `w` interaction (confinement); non-monotone in `fcen` (resonant radiation losses give ripples, so `fourier` needs several degrees); smooth but possibly pixel-wiggly in `w` | 10–30 s *(estimate)* | cli | regex |
| `python/examples/holey-wvg-cavity.py` (https://github.com/NanoComp/meep/blob/v1.34.0/python/examples/holey-wvg-cavity.py) in its `-r` (resonant modes) mode, resolution 20 | photonic-crystal waveguide cavity (holes of radius r, defect spacing d), Harminv | `r` 0.36 [0.25, 0.45] (edit the constant into an option); `d` 1.4 [1.2, 1.6]; `N` (holes per side) 3, fixed | Q of the defect mode in a fixed frequency window | Q depends steeply on `r` and `d` (a mirror strength: `log_output` helps); a **jump** if the mode leaves the band gap; an integer `N` would make steps, so it is fixed. The example already takes `-N`, `-sy`, `-fcen` and `-df` options | 10–40 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard Meep 1.34.0 examples into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, Miniforge conda/mamba and any env named ema-meep, any MPI on PATH (mpirun --version), Homebrew version (don't use it), and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge `pymeep=1.34.0=nompi_*` with python=3.12 in env ema-meep (osx-64 and linux-64 builds exist for Python 3.10–3.13; none for 3.14). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install Meep on this Intel Mac. Use Miniforge (conda-forge only): `mamba create -n ema-meep -c conda-forge python=3.12 "pymeep=1.34.0=nompi_*" numpy`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before downloads over 1 GB. Check: `<env>/bin/python -c "import meep as mp; print(mp.__version__)"`, and report the build string from `conda list -n ema-meep pymeep` (it must contain nompi) and the env's absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install Meep on this AWS EC2 instance (Ubuntu 24.04 x86_64). Preferred: Miniforge and the same env ema-meep (python=3.12, pymeep=1.34.0=nompi_*, numpy from conda-forge). Never use EMA's .venv, and never read .env. Ask before any sudo, and before downloads over 1 GB. Don't use apt's python3-meep. Check as on the Mac, and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — Meep smoke test. In a scratch directory outside the EMA repo, download python/examples/ring.py from the v1.34.0 tag of github.com/NanoComp/meep. Remove the output_epsilon and output_efield_z calls and the second sim.run, run it with the ema-meep env's python and OMP_NUM_THREADS=1, and time it. Report the harminv0: lines (frequency, imag. freq., Q, |amp|, amplitude, error) and compare them with the tutorial's modes at 0.118, 0.147 and 0.175 (Q ≈ 81, 316, 1677). Report the wall time. Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the Meep ring resonator for EMA. Enter plan mode first and show me the plan. Source: python/examples/ring.py (Meep 1.34.0). Put in examples/meep/ring/: run.py taking --n, --w and --r as options (the command-line style of examples/beam/model_args.json), with resolution 10, no field output, the same source and Harminv call, collecting the modes from the Harminv object's modes list (not by parsing stdout), choosing the mode with 0.14 ≤ freq ≤ 0.16 and the largest Q (exit 1 if there is none), and printing `EMA_OUTPUT_FREQ = %.12e` and `EMA_OUTPUT_Q = %.12e`. model.json reads the frequency and model_q.json reads Q; they share run.py. Inputs: n = 3.4 [2.5, 3.6], w = 1 [0.8, 1.2], r = 1 [0.8, 1.5]. The command is the ema-meep env's absolute python path and run.py; env OMP_NUM_THREADS=1; timeout_s 300. Check by hand that the nominal run gives about 0.147 and Q about 316. Then `.venv/bin/ema profile examples/meep/ring/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the Meep bend-flux example. Plan mode first. Source: python/examples/bend-flux.py (Meep 1.34.0). Put in examples/meep/bend/: run.py with options --eps (replacing epsilon=12 in both geometries), --w and --fcen, keeping resolution 10, df 0.1 and nfreq 100, and the straight-guide normalization run followed by the bend run (with the reflected-flux subtraction as in the example), no plotting, printing `EMA_OUTPUT = <mean of bend transmitted flux / straight transmitted flux over the frequencies, %.12e>`. Inputs: eps = 12 [6, 13], w = 1 [0.6, 1.4], fcen = 0.15 [0.1, 0.2]. Command-line model as in 4.1, timeout_s 600. Check by hand that the nominal value is between 0 and 1 and consistent with the tutorial's transmission plot. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the Meep holey-waveguide cavity. Plan mode first. Source: python/examples/holey-wvg-cavity.py (Meep 1.34.0), run with -r (resonant modes). Put in examples/meep/holey_cavity/: run.py with new options --hole_r (replacing r = 0.36) and --d (replacing 1.4), keeping N = 3, sy = 6, fcen = 0.25, df = 0.2 and resolution 20, no field output, choosing the Harminv mode with the largest Q in a fixed window (propose the window from a nominal run and show me the modes first), and printing `EMA_OUTPUT = <Q, %.12e>`. Inputs: hole_r = 0.36 [0.25, 0.45], d = 1.4 [1.2, 1.6]. timeout_s 600. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first Meep campaign. For examples/meep/ring/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on r (n 21, to show the pixel-scale wiggle), and morris (n_traj 8). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run` (suggest -j 4). After it runs, report: repeatability, any failed runs (no mode in the window) and where they are, the curve1d shape (smooth decrease expected, with or without small wiggles), the morris ranking, and whether any input is (possibly) negligible. Suggest (don't run) linear_coeffs with log_output on the frequency and on model_q.json. Stop and report.
```

```text
Stage 6 — Meep troubleshooting. An EMA Meep model (examples/meep/<example>) fails or gives odd values. Diagnose read-only first from the run directory. Check for: an MPI build instead of nompi (MPI start-up messages; conda list pymeep), Harminv finding no mode or a different one in the window (print all modes for that run by hand), fields that never decay (stop_when_fields_decayed and a run that times out), h5 output files filling the run directory (remove the output_* calls), jumps in the output caused by mode selection, pixel-scale wiggles in geometric inputs (compare resolution 10 and 20 at two points), threads (OMP_NUM_THREADS), and a wrong interpreter path. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License GPL-2.0-or-later. Running Meep as an external program is fine, but don't copy Meep's code into EMA.
- Parallelism: use the serial `nompi` build. EMA's `-j` runs several at once. MPI Meep would need `mpirun` as the command.
- Determinism: serial FDTD is deterministic. Harminv's fit is deterministic but chooses among modes, so the driver's mode selection must be a fixed rule.
- Resolution: outputs depend on `resolution`. Keep it fixed per model, and record it in the description.
- Python version: 1.34.0 has no Python 3.14 build on conda-forge. Use 3.12 (the env is separate from EMA's 3.14 venv anyway).
- Sources: https://meep.readthedocs.io, https://meep.readthedocs.io/en/master/Installation/, https://meep.readthedocs.io/en/master/Python_Tutorials/Basics/, https://github.com/NanoComp/meep, https://github.com/NanoComp/meep/releases/tag/v1.34.0, https://github.com/NanoComp/meep/tree/v1.34.0/python/examples, https://anaconda.org/conda-forge/pymeep/files

---

#### GTSAM

**What it is.** Georgia Tech's library for smoothing and mapping with factor graphs: nonlinear least-squares estimation for SLAM, visual odometry, IMU preintegration and structure from motion. **It is an estimator, not a simulator**: it computes the most likely states given measurements and noise models. It's C++, with Python bindings. BSD-2-Clause ("Simplified BSD" on PyPI; GitHub reports it as NOASSERTION). Current release **4.3.0 (2026-09-18)**, with 4.2.2 (2026-06-30) the previous. Python examples are in `python/gtsam/examples/` of https://github.com/borglab/gtsam (about 25 `.py` scripts plus notebooks in `slam/`, `nonlinear/` and other subdirectories, such as `slam/Pose2SLAMExample.ipynb`, `slam/OdometryExample.ipynb`, `slam/Pose2SLAMStressTest.ipynb` and `Pose2SLAMExample_g2o.py`). Datasets are in `examples/Data/` (`noisyToyGraph.txt`, `w100.graph`, `Klaus3.g2o`, ...). Docs: https://gtsam.org and https://borglab.github.io/gtsam/.
**Why it qualifies, and what is awkward.** A driver that builds a small pose graph from a few scalar inputs (noise sigmas, a loop-closure error, the number of poses) and returns an estimation error or a marginal standard deviation is a deterministic, millisecond-fast model with exactly known structure. It is a good test of EMA itself: scale invariance, power laws, a kink at zero error. It is not a physical model, and the "examples" are tutorials whose measurements are fixed, so every model here is a driver adapted from an example, not the example itself.

**Install on an Intel Mac.** PyPI's `gtsam` 4.3.0 has `macosx_10_15_universal2` wheels for CPython 3.11–3.14, which include x86_64. conda-forge also builds osx-64 (4.3.0, Python 3.11–3.14). Use a separate venv; pip is enough here.
1. Create a venv outside EMA's (any Python 3.11–3.14; python.org's or a conda one):
   ```bash
   python3.12 -m venv ~/venvs/ema-gtsam
   ~/venvs/ema-gtsam/bin/pip install gtsam==4.3.0 numpy
   ```
   (conda alternative: `mamba create -n ema-gtsam -c conda-forge python=3.12 gtsam=4.3.0`.)
2. Check:
   ```bash
   ~/venvs/ema-gtsam/bin/python -c "import gtsam; print(gtsam.__version__ if hasattr(gtsam,'__version__') else 'ok'); print(gtsam.Pose2(1,2,0.3))"
   ```
Known problems: `gtsam.__version__` may not exist **(unconfirmed)**, so record the version from `pip show gtsam`. The notebooks import `graphviz` and `matplotlib`, which the drivers don't need. Docker Hub's `borglab/gtsam` images (latest, 2026-06-16, amd64) predate 4.3.0.
Sources: https://pypi.org/project/gtsam/4.3.0/#files, https://anaconda.org/conda-forge/gtsam/files, https://github.com/borglab/gtsam/releases/tag/4.3.0.

**Install on AWS (Ubuntu 24.04 EC2).**
1. The same pip route, which has manylinux x86_64 wheels for 3.11–3.14:
   ```bash
   sudo apt install python3.12-venv    # ask first; only if venv is missing
   python3 -m venv ~/venvs/ema-gtsam && ~/venvs/ema-gtsam/bin/pip install gtsam==4.3.0 numpy
   ```
2. Fallback: the conda-forge env as above.
3. Check as on the Mac.
Sources: https://pypi.org/project/gtsam/4.3.0/#files.

**Preparing the examples for EMA.** Each model is a driver `run.py` in the model directory, run by the venv's `python` with `argparse` options (as `examples/beam/model_args.json`):
- The driver builds the graph from the example's structure and optimizes with the example's optimizer.
- It prints `EMA_OUTPUT = <value:.12e>`, a scalar computed against a ground truth it constructs itself.
- Any random draws are seeded by a fixed seed plus `EMA_REPLICATE`, so the model is deterministic per replicate.
- Set tight optimizer tolerances (`setRelativeErrorTol(1e-12)`, `setAbsoluteErrorTol(1e-12)`), so that iteration counts don't make the output rough.
- A run takes milliseconds after importing `gtsam` (about 0.5 s *(estimate)*), so campaigns of 10,000 runs are cheap.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `python/gtsam/examples/slam/Pose2SLAMExample.ipynb` (https://github.com/borglab/gtsam/blob/4.3.0/python/gtsam/examples/slam/Pose2SLAMExample.ipynb): 5 poses on a 2 m square, prior on pose 1, 4 odometry factors, 1 loop closure 5→2, Gauss-Newton | 2D pose-graph SLAM (estimation) | odometry σ_xy 0.2 [0.02, 1] (log); odometry σ_θ 0.1 [0.01, 0.5] (log); loop-closure σ_xy 0.2 [0.02, 1] (log); loop-closure error `e` (an added x offset in the 5→2 measurement) 0.5 [0, 2] m | (a) position error of pose 5 vs. the true square; (b) second model: √(trace of pose 5's 2×2 position marginal covariance) at `e` = 0 | (a) is **invariant to scaling all σ together** (only ratios matter: `active_subspace` in the log σ's finds a direction with a zero eigenvalue) and nearly **linear in `e`** (a kink at `e` = 0 if the range crossed zero); (b) is **homogeneous of degree 1** in the σ's: `linear_coeffs(log_output=True)` gives exponents summing to 1 and `power_law`; `e` is **negligible** for (b) | ≈ 0.5 s, dominated by the import *(estimate)* | cli (venv python + `run.py`) | regex |
| `python/gtsam/examples/slam/Pose2SLAMStressTest.ipynb` (https://github.com/borglab/gtsam/blob/4.3.0/python/gtsam/examples/slam/Pose2SLAMStressTest.ipynb), adapted: a chain of N poses with odometry noise drawn with seed 42 + `EMA_REPLICATE`, plus a loop closure every K poses, Levenberg-Marquardt | long-trajectory pose-graph SLAM with drift | odometry noise σ 0.05 [0.01, 0.2] (log); number of poses N 500 [100, 2000] (log; rounded to an integer by the driver); loop-closure σ 0.1 [0.01, 1] (log); closure interval K 50, fixed | RMS position error of the optimized trajectory vs. truth | with a fixed seed, RMSE is **exactly proportional to the odometry σ** when the loop σ scales with it (a power law; otherwise it depends on the ratio); it grows with N like a random walk (exponent ≈ 0.5 *(expected, not verified)*); integer N gives small **steps**; **noise** across replicates, which `repeat` measures | 0.5–2 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard GTSAM 4.3.0 pose-graph examples into EMA as command-line models. Run only read-only commands and report: OS and version, uname -m, which python3.11–3.14 interpreters exist outside EMA's .venv (python.org, conda envs) and their paths, Miniforge conda/mamba, any ~/venvs/ema-gtsam, and free disk space. Don't install anything, and don't read .env. Recommend a route: a separate venv ~/venvs/ema-gtsam with `pip install gtsam==4.3.0 numpy` (universal2 macOS wheels include x86_64; manylinux x86_64 on Ubuntu), or a conda-forge env ema-gtsam with gtsam=4.3.0 (osx-64 and linux-64 builds exist). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install GTSAM on this Intel Mac. Create a venv outside EMA's .venv, at ~/venvs/ema-gtsam, with a Python 3.11–3.13 interpreter that isn't EMA's (tell me which you use), and `pip install gtsam==4.3.0 numpy`. Never install into EMA's .venv, and never read .env. Ask me before installing any interpreter, before any sudo or Homebrew change, and before downloads over 1 GB. If pip can't find a wheel, stop and propose (don't run) the conda-forge env `mamba create -n ema-gtsam -c conda-forge python=3.12 gtsam=4.3.0`. Check: `<venv>/bin/python -c "import gtsam; print(gtsam.Pose2(1,2,0.3))"`, report `pip show gtsam`, and confirm that `file` on the gtsam extension module shows x86_64. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — install GTSAM on this AWS EC2 instance (Ubuntu 24.04 x86_64). Create ~/venvs/ema-gtsam with the system python3 (ask me before `sudo apt install python3.12-venv` if venv is missing) and `pip install gtsam==4.3.0 numpy`. Never use EMA's .venv, and never read .env. Check as on the Mac, and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — GTSAM smoke test. In a scratch directory outside the EMA repo, write (don't download: the example is a notebook) a short script with the code cells of python/gtsam/examples/slam/Pose2SLAMExample.ipynb at tag 4.3.0, without the graphviz, display and plotting cells. Run it with the ema-gtsam python and OMP_NUM_THREADS=1, and time it with the import and without (time the optimize call separately). Report the final poses, the marginal covariance of pose 5, and the times. Change nothing in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the GTSAM Pose2 SLAM example for EMA. Enter plan mode first and show me the plan. Source: slam/Pose2SLAMExample.ipynb (GTSAM 4.3.0). Put in examples/gtsam/pose2_loop/: run.py with options --sig_odo_xy, --sig_odo_th, --sig_loop_xy (the loop closure's θ sigma tied to --sig_odo_th, and say so) and --loop_err (added to the x of the 5→2 measurement). It keeps the notebook's prior, measurements and initial estimate, uses Gauss-Newton with relative and absolute error tolerances of 1e-12 and 100 iterations, and prints `EMA_OUTPUT_ERR = <|position of pose 5 − (true position)|, %.12e>` and `EMA_OUTPUT_SD = <sqrt(trace of pose 5's 2x2 position marginal covariance), %.12e>`. model.json reads ERR and model_sd.json reads SD. Inputs: sig_odo_xy 0.2 [0.02, 1] scale log, sig_odo_th 0.1 [0.01, 0.5] scale log, sig_loop_xy 0.2 [0.02, 1] scale log, loop_err 0.5 [0, 2]. The command is the venv's absolute python path and run.py, as in examples/beam/model_args.json; env OMP_NUM_THREADS=1; timeout_s 30; regex. Check by hand: with loop_err 0 the error is ~0; multiplying all three sigmas by 10 leaves ERR unchanged and multiplies SD by 10. Then `.venv/bin/ema profile examples/gtsam/pose2_loop/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the GTSAM long-chain example. Plan mode first. Source: the structure of slam/Pose2SLAMStressTest.ipynb (GTSAM 4.3.0), adapted to Pose2 with ground truth: N poses one unit apart on a gently curving path you choose and state, odometry measurements = truth + Gaussian noise with sigma sig_odo drawn from numpy's default_rng(42 + int(os.environ.get("EMA_REPLICATE", "0"))), a loop-closure factor to pose 0 every K = 50 poses with noise sig_loop, the initial estimate from dead reckoning, and Levenberg-Marquardt with tolerances of 1e-12. Put it in examples/gtsam/chain/. Options: --sig_odo 0.05 [0.01, 0.2] scale log, --n_poses 500 [100, 2000] scale log (rounded to an int in the driver, and say that this makes steps), --sig_loop 0.1 [0.01, 1] scale log. Print `EMA_OUTPUT = <RMS position error vs. truth, %.12e>`. Check by hand that replicate 0 twice gives identical output and EMA_REPLICATE=1 a different one. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first GTSAM campaign. For examples/gtsam/pose2_loop/model_sd.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 10), linear_coeffs with log_output (n 64), and active_subspace (default size). Use `.venv/bin/ema estimate` to report the run count and time, and ask me before `ema run`. After it runs, report: repeatability, whether loop_err is flagged negligible (expected), the exponents and whether power_law is set (expected: exponents summing to 1), and the active subspace's dimension and direction. Suggest (don't run) the same on model.json (ERR), where the expected structure is invariance to the sigmas' common scale and near-linearity in loop_err. Stop and report.
```

```text
Stage 6 — GTSAM troubleshooting. An EMA GTSAM model (examples/gtsam/<example>) fails or gives odd values. Diagnose read-only first from the run directory. Check for: an import error (the wrong interpreter in model.json, or an arm64-only wheel: run `file` on the extension module), an optimizer that stops early (the tolerances and iteration limit; print the iteration count), an indeterminant linear system (a graph without a prior, or sigmas so small the system is ill-conditioned at the edges of the box), outputs that differ between replicate-0 runs (unseeded randomness, or TBB threads: set OMP_NUM_THREADS=1, and check whether the wheel uses TBB), and steps from integer rounding of n_poses. Report the cause and a proposed fix. Ask before changing the venv or model.json.
```

**Gotchas and sources.**
- License BSD-2-Clause (the `LICENSE` file; PyPI says "Simplified BSD"). Some third-party code in the repository has its own licenses (`LICENSE.BSD`, `gtsam/3rdparty`).
- Fit: an estimation library, not a physical simulator. The models are small drivers whose structure is known in closed form, which makes them tests of EMA's diagnostics rather than new science.
- Threads: GTSAM can be built with TBB (the `latest-tbb` Docker tag). Whether the PyPI wheel uses TBB is **(unconfirmed)**. Set `OMP_NUM_THREADS=1`, and check with `repeat`.
- Determinism: deterministic given the seed. Seed from `EMA_REPLICATE`, never from the clock. Optimizer tolerances make outputs rough at their own level, so tighten them.
- Run time: the import dominates (about 0.5 s *(estimate)*), and the optimization itself takes milliseconds.
- Version pitfalls: the notebooks install `gtsam-develop` in Colab. Use the pinned release, since the Python API changes between 4.2 and 4.3 **(unconfirmed which calls)**.
- Sources: https://gtsam.org, https://borglab.github.io/gtsam/, https://github.com/borglab/gtsam, https://github.com/borglab/gtsam/releases/tag/4.3.0, https://github.com/borglab/gtsam/tree/4.3.0/python/gtsam/examples, https://github.com/borglab/gtsam/blob/4.3.0/python/gtsam/examples/slam/Pose2SLAMExample.ipynb, https://github.com/borglab/gtsam/blob/4.3.0/python/gtsam/examples/slam/Pose2SLAMStressTest.ipynb, https://github.com/borglab/gtsam/blob/4.3.0/python/gtsam/examples/Pose2SLAMExample_g2o.py, https://github.com/borglab/gtsam/tree/4.3.0/examples/Data, https://pypi.org/project/gtsam/4.3.0/#files, https://anaconda.org/conda-forge/gtsam/files, https://hub.docker.com/r/borglab/gtsam/tags

---

### 4.8 Weather, climate, and Earth-system models: climlab, WRF, CESM, E3SM, ICON

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions and dates come from GitHub releases (read with the GitHub API), prefix.dev, Docker Hub and the projects' own pages. Estimated run times are marked *(estimate)*, and anything I couldn't check is marked **(unconfirmed)**. Cross-cutting facts:

- **The size spread is enormous, so be honest about fit.** climlab is a laptop Python package whose runs take seconds. WRF has idealized cases that need no data and run in seconds to minutes. CESM, E3SM and ICON are Earth-system models built for supercomputers. For them, only **single-column** configurations (CESM's SCAM, E3SM's SCM) and ICON's **small torus "bubble"** case fit EMA's "seconds to a minute per run" budget. A global configuration, even at the coarsest resolution, costs hours per run and gigabytes of input data, so it is out of scope for EMA campaigns. Each section says so.
- **The Intel Mac can host the small configurations, but only through Docker for the big three.** None of WRF, CESM, E3SM or ICON is on conda-forge (conda-forge has only `wrf-python`, WRF's post-processing library, not the model). Homebrew isn't used here (Tier 3 on Intel). So the Mac route for WRF, CESM, E3SM and ICON is Docker Desktop with a `linux/amd64` image, which runs natively on Intel. Give Docker 8 GB of memory or more and 100 GB of disk.
- **One pattern for all four compiled models: build once, then run the executable directly in each EMA run directory.** Their own workflows (WRF's `test/em_*` directory, CIME's `case.submit`, ICON's generated run scripts) write outside the run directory and take seconds to minutes of set-up. The EMA model is therefore a **driver script next to `model.json`** that:
  1. writes the namelist from the inputs;
  2. links or copies the fixed files (tables, grids, initial files) into the run directory;
  3. runs the prebuilt executable serially;
  4. reads the netCDF output and prints one line, `EMA_OUTPUT <value>`, which a `regex` parser reads.
  Under Docker the driver must be a **static file** (the container can't see host paths), and the command is `docker run --rm --user <uid>:<gid> -v $EMA_WORKDIR:/work -w /work <image>@sha256:<digest> python3 <driver> deck.txt`.
- **Read netCDF in the driver, not in an EMA `python` output parser.** EMA's `python` parser runs in a child started with `sys.executable` (`src/ema/core/models/_sandbox.py`), which is EMA's own `.venv` interpreter. It could only `import netCDF4` or `xarray` if they were installed into EMA's `.venv`, which these prompts forbid. The driver runs in the model's own environment (the container's `python3`, or a conda env), so it can read the file.
- **Determinism.** All five models are deterministic when run serially with stochastic physics off (the default in every configuration below). Moist convection is chaotic, though: WRF's supercell, ICON's bubble and the single-column models' convection make the output a **rough** function of the inputs, even though `repeat` will show identical replicates. Expect `nonsmooth` to find many small jumps. Treat them as a property of the model, not noise, and prefer time- or domain-averaged outputs.
- **AWS instance.** climlab, the WRF 2-D and single-column cases, and the single-column CESM, E3SM and ICON bubble runs: `c7i.2xlarge` (8 vCPU, 16 GB) with a 100 GB gp3 volume. That is enough for the Docker images (1–25 GB each), the builds, and CESM or E3SM input data. For WRF's 3-D supercell or ICON's aquaplanet with `-j 16` or more, use a `c7i.8xlarge` (32 vCPU, 64 GB). Check prices for your region **(unconfirmed; prices vary)**. A global CESM or E3SM configuration would need an HPC instance (for example `hpc7a`) and 500 GB+ of input data. It isn't planned here.

---

#### climlab

**What it is.** climlab is a Python package for process-oriented climate modelling: energy-balance models (EBMs), radiative-convective column models, and radiation schemes (RRTMG, CAM3) wrapped from Fortran. License: MIT. Current release **0.9.2 (2026-03-18)**, a maintenance release for pandas 3.0 compatibility. Before it came 0.9.0 (2025-02-28), which added moist physics and "supports Python 3.12/3.13 and Numpy 2". The core is pure Python (`noarch` on conda-forge). The Fortran pieces live in companion packages: `climlab-rrtmg` 0.4.2, `climlab-cam3-radiation` 0.3.2 and `climlab-emanuel-convection` 0.3.1, all built for osx-64, osx-arm64 and linux-64. PyPI has only an sdist, so use conda-forge. There are 11 tutorial notebooks at https://climlab.readthedocs.io/en/latest/ (source in `docs/source/courseware/` of https://github.com/climlab/climlab **(unconfirmed path)**), and many more examples in Brian Rose's *Climate Laboratory* book (https://brian-rose.github.io/ClimateLaboratoryBook/). climlab is the easiest package in this group: seconds per run, no data downloads for the EBMs, and a real bifurcation (the ice-albedo feedback) that gives `nonsmooth` genuine jumps and hysteresis to find.

**Install on an Intel Mac.** conda-forge, osx-64. `climlab` itself is `noarch`, and its three Fortran dependencies have osx-64 builds for Python 3.10–3.14.
1. Install Miniforge (osx-64) if there is no conda/mamba:
   ```bash
   curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
   bash Miniforge3-MacOSX-x86_64.sh -b -p "$HOME/miniforge3"
   ```
2. Create a pinned env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-climlab -c conda-forge python=3.12 climlab=0.9.2
   ```
3. Check that it imports and that the RRTMG extension loads:
   ```bash
   ~/miniforge3/envs/ema-climlab/bin/python -c "import climlab, climlab.radiation; print(climlab.__version__); m = climlab.EBM_annual(num_points=90); m.integrate_years(1, verbose=False); print(float(m.global_mean_temperature()))"
   ```
Known problems: `climlab-cam3-radiation` depends on `pooch` and fetches its data files on first use, so it needs the network once. The EBM and RRTMG examples below don't use CAM3 radiation. Windows isn't supported, which doesn't matter here.
Sources: https://climlab.readthedocs.io/en/latest/installation.html, https://prefix.dev/channels/conda-forge/packages/climlab, https://prefix.dev/channels/conda-forge/packages/climlab-rrtmg, https://prefix.dev/channels/conda-forge/packages/climlab-cam3-radiation, https://prefix.dev/channels/conda-forge/packages/climlab-emanuel-convection, https://github.com/climlab/climlab/releases

**Install on AWS (Ubuntu 24.04 EC2).** Use the same conda-forge env with the Linux installer (`Miniforge3-Linux-x86_64.sh`), so both machines run identical code:
```bash
curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p "$HOME/miniforge3"
~/miniforge3/bin/mamba create -n ema-climlab -c conda-forge python=3.12 climlab=0.9.2
```
Check as on the Mac. There's no apt package or official Docker image, and none is needed. A `c7i.xlarge` (4 vCPU) is enough: runs take seconds.
Sources: https://github.com/conda-forge/miniforge, https://climlab.readthedocs.io/en/latest/installation.html

**Preparing the examples for EMA.** climlab is a Python package, but it lives in its own conda env, not EMA's `.venv`. So each example is a **command-line model**: the command is the `ema-climlab` env's absolute `python` path followed by `run.py deck.txt`. `run.py` is a driver next to `model.json` (hashed), and `deck.txt` is rendered from a `key = value` template, as in `examples/cantera/`. The driver:
- builds the model from the notebook's code;
- integrates for a fixed number of years;
- **checks convergence**: it compares the last two years' global means, and exits non-zero if they differ by more than a tolerance, so EMA records a failed run instead of a transient value;
- prints `EMA_OUTPUT <value:.12e>` and `climlab <version>`.

A Python-function model (`model_type: python`) doesn't fit, because it would import climlab into EMA's interpreter.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Ice-albedo feedback and runaway glaciation (https://climlab.readthedocs.io/en/latest/courseware/Snowball_Earth_in_the_EBM.html) | 1-D annual-mean diffusive EBM with an ice line (`climlab.EBM_annual(num_points=180, a0=0.3, a2=0.078, ai=0.62)`), started from climlab's default warm state | `S0` 1365 [1200, 1450] (the tutorial sweeps 1400→1200 through `model.subprocess['insolation'].S0`); `D` (diffusivity) 0.555 [0.3, 0.9]; `ai` 0.62 [0.5, 0.7]; `A` (OLR intercept) 210 [200, 220]. The driver prints `model.param` so the defaults can be checked **(unconfirmed that climlab's defaults are D = 0.555, A = 210)** | northern ice-edge latitude `model.icelat[1]` (a second model: `global_mean_temperature()`) | **plateaus and jumps**: 90° (ice-free) and 0° (snowball) plateaus, a jump at the small-ice-cap instability and at the snowball threshold, so `nonsmooth` and `curve1d` on `S0` should find them. The result depends on the initial state (hysteresis), so fix it. Convergence failures cluster near the jumps (critical slowing down), giving a failure region. `D` and `ai` interact with `S0` near the thresholds | 1–3 s (20 model years) *(estimate)* | cli (env python + `run.py`) | regex `EMA_OUTPUT (\S+)` |
| Radiative-convective equilibrium with RRTMG (API example at https://climlab.readthedocs.io/en/latest/api/climlab.radiation.RRTMG.html; spectral RRTMG notebook https://climlab.readthedocs.io/en/latest/courseware/Spectral_OLR_with_RRTMG.html) | single column: `climlab.column_state(num_lev=30)`, `ManabeWaterVapor` (fixed relative humidity), `RRTMG(albedo=...)`, `ConvectiveAdjustment(adj_lapse_rate=6.5)`, coupled with `climlab.couple` | `co2_ppmv` 280 [180, 1120] (log), passed as `absorber_vmr={'CO2': co2/1e6}`; `albedo` 0.25 [0.15, 0.35]; `adj_lapse_rate` 6.5 [5, 9.8] | equilibrium surface temperature `Ts` (K) | smooth; **nearly linear in ln CO2**, so with CO2 on a log scale `linear_coeffs` should report a linear structure. Strongly decreasing in albedo; increasing in lapse rate. Small interactions (the water-vapour feedback amplifies each). An albedo that is too high or too low can fail to converge in the fixed time: failed runs at the edges | 5–20 s (3–5 years at a 1-day step) *(estimate)* | cli | regex |
| Seasonal cycle and heat capacity (https://climlab.readthedocs.io/en/latest/courseware/Seasonal_cycle_and_heat_capacity.html) | seasonal diffusive EBM `climlab.EBM_seasonal(water_depth=..., orb={...})`, stepped through the last year with `step_forward()` | `water_depth` 10 [2, 50] m (log); `obliquity` 23.45 [22, 24.5]; `ecc` 0.017 [0, 0.06]; `long_peri` 281 [0, 360] | seasonal amplitude (max − min of `Ts`) at the grid latitude nearest 60°N, over the last year | amplitude decreasing in `water_depth`, close to a power law at large depths (`linear_coeffs(log_output=True)`, exponent near −1 **(unconfirmed)**); increasing in obliquity; `ecc` × `long_peri` interaction (the product e·sin ϖ matters), and `long_peri` is periodic, so non-monotone. If `EBM_seasonal` has an ice line (check `model.subprocess`), kinks appear too | 2–5 s (5 years) *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — climlab, check the machine (read-only). I want to onboard climlab 0.9.2 examples into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, any existing env named ema-climlab, Homebrew version (just report it), and free disk space. Don't install anything, and don't read .env. Recommend a route: a conda-forge env `ema-climlab` with python=3.12 climlab=0.9.2 (climlab is noarch, and climlab-rrtmg, climlab-cam3-radiation and climlab-emanuel-convection have osx-64 and linux-64 builds). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install climlab on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-climlab -c conda-forge python=3.12 climlab=0.9.2`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import climlab, climlab.radiation; print(climlab.__version__)"`, and report the env's absolute python path and the versions of climlab-rrtmg and numpy in the env (`mamba list -n ema-climlab`). Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install climlab on this AWS EC2 instance (Ubuntu 24.04, x86_64). Install Miniforge (Linux x86_64 installer; ask first) and create the same env as on my Mac: `mamba create -n ema-climlab -c conda-forge python=3.12 climlab=0.9.2`. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. Check as on the Mac and report the absolute python path and `mamba list -n ema-climlab climlab`. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — climlab smoke test. In a scratch directory outside the EMA repo, write a 10-line script that builds climlab.EBM_annual(num_points=180, a0=0.3, a2=0.078, ai=0.62), prints model.param, integrates 20 years (verbose=False), and prints model.icelat and model.global_mean_temperature(); then a second script that builds the RRTMG radiative-convective column from the RRTMG API example (column_state(num_lev=30), ManabeWaterVapor, RRTMG with albedo 0.25, ConvectiveAdjustment adj_lapse_rate 6.5, climlab.couple) and integrates 3 years, printing Ts each year. Run both with the ema-climlab env's python, time them, and report the printed values, whether Ts has stopped changing, and the wall times. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the climlab snowball-Earth EBM for EMA. Enter plan mode first and show me the plan. Source: the "Ice-albedo feedback and runaway glaciation" notebook (climlab.readthedocs.io/en/latest/courseware/Snowball_Earth_in_the_EBM.html). In examples/climlab/snowball/ write run.py, a driver that reads a key = value deck rendered from snowball.template, like examples/cantera/ignite.py and ignition.template. Inputs: S0 = 1365 [1200, 1450] (set through model.subprocess['insolation'].S0), D = climlab's default [0.3, 0.9], ai = 0.62 [0.5, 0.7], A = climlab's default [200, 220]; print model.param once by hand to get the defaults, and use them as the nominals. Always start from the same default initial state. Integrate 20 years, then 1 more; if the global mean changed by more than 1e-4 K in the last year, exit with status 2 (not converged). Print `climlab <version>` and `EMA_OUTPUT <icelat[1], %.12e>`. model.json: command [<ema-climlab absolute python>, "run.py", "deck.txt"] (not $EMA_PYTHON), regex "EMA_OUTPUT (\S+)" on stdout, env OMP_NUM_THREADS=1, timeout_s 120, and a description that records climlab 0.9.2. Write a second model_gmt.json that shares the driver and outputs the global mean temperature (the driver takes the output name from the deck or an argument). Check by hand: the nominal gives a partial ice cap, S0 = 1200 gives a snowball (icelat 0), and S0 = 1450 is ice-free (90). Then run `.venv/bin/ema profile examples/climlab/snowball/model.json -n 5` and report the time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the climlab RRTMG radiative-convective column. Plan mode first. Source: the RRTMG API example (climlab.readthedocs.io/en/latest/api/climlab.radiation.RRTMG.html). Put it in examples/climlab/rce/, with the same driver pattern as examples/climlab/snowball/. Inputs: co2_ppmv = 280 [180, 1120] with scale log (absorber_vmr CO2 = co2_ppmv/1e6; keep the other absorbers at the RRTMG defaults and state them), albedo = 0.25 [0.15, 0.35], adj_lapse_rate = 6.5 [5, 9.8]. Use a fixed timestep and a fixed number of years (choose it from Stage 3 so that Ts has converged at the nominal), with the same convergence check (exit 2 if the last year's change is above 1e-3 K). Output: `EMA_OUTPUT <Ts, %.12e>`. timeout_s 300. Check by hand that doubling CO2 from 280 to 560 warms Ts by a few kelvin, and report the number. Then `.venv/bin/ema profile examples/climlab/rce/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the climlab seasonal EBM. Plan mode first. Source: the "Seasonal cycle and heat capacity" notebook (climlab.readthedocs.io/en/latest/courseware/Seasonal_cycle_and_heat_capacity.html). Put it in examples/climlab/seasonal/. Inputs: water_depth = 10 [2, 50] (scale log), obliquity = 23.45 [22, 24.5], ecc = 0.017 [0, 0.06], long_peri = 281 [0, 360] (passed in orb={'ecc':..., 'obliquity':..., 'long_peri':...}; check the key names in climlab's orbital module first). Integrate 5 years, then step through one more year with step_forward(), recording Ts at the grid latitude nearest 60N. Output: `EMA_OUTPUT <max - min over that year, %.12e>`. Report whether EBM_seasonal has an ice-line albedo (list model.subprocess). Then `.venv/bin/ema profile examples/climlab/seasonal/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first climlab campaign. For examples/climlab/snowball/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on S0 (n 41), nonsmooth, and morris (n_traj 10). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before running `.venv/bin/ema run ... -j 4`. After it runs, report: whether the repeats are identical, where curve1d finds jumps and plateaus in S0 (expected: the snowball threshold and the small-ice-cap jump, with plateaus at 0 and 90), how many runs failed to converge and where, and morris's ranking. Then suggest (don't run) surface2d on (S0, D), and linear_coeffs with S0 on the RCE model's CO2. Stop and report.
```

```text
Stage 6 — climlab troubleshooting. An EMA climlab model (examples/climlab/<example>) fails or is slow. Diagnose read-only first: run the driver by hand in a copy of a failed run directory with the ema-climlab env's python. Check for: an ImportError from climlab_rrtmg or libgfortran (a broken env; compare `mamba list`), a pooch download attempted at run time (no network, or a cache that isn't writable), runs that exit 2 (not converged: are they clustered near a threshold? then they are real features, not bugs), NumPy 2 or pandas warnings that turn into errors, threads oversubscribed (OMP_NUM_THREADS), a regex that doesn't match, and `could not start` (a wrong interpreter path in model.json). Report the cause and a proposed fix. Ask before changing the env, the driver or model.json.
```

**Gotchas and sources.**
- License MIT (the RRTMG and CAM3 Fortran are redistributed under the wrappers' licenses, which are also permissive).
- Threads: the Fortran extensions are serial, but NumPy's BLAS may start threads. Set `OMP_NUM_THREADS=1` and let EMA's `-j` supply the parallelism.
- Determinism: fully deterministic. The only "noise" is **incomplete convergence**: an output read after a fixed time depends on how close to equilibrium it got. Use the driver's convergence check, not a longer blind run. Near a bifurcation, convergence slows sharply, so failed runs there are real.
- Hysteresis: the equilibrium depends on the initial state. Always start from the same state. A second model started from a snowball state would map the other branch, and the difference between the two is the hysteresis EMA can show.
- Run time: seconds. Python start-up and imports (about 1–2 s *(estimate)*) may dominate the EBMs.
- Versions: 0.9.x needs Python ≥ 3.10 and supports NumPy 2. Pin climlab 0.9.2 in the env, and record it in the description.
- Sources: https://climlab.readthedocs.io/en/latest/, https://climlab.readthedocs.io/en/latest/installation.html, https://climlab.readthedocs.io/en/latest/courseware/Snowball_Earth_in_the_EBM.html, https://climlab.readthedocs.io/en/latest/courseware/Seasonal_cycle_and_heat_capacity.html, https://climlab.readthedocs.io/en/latest/courseware/Spectral_OLR_with_RRTMG.html, https://climlab.readthedocs.io/en/latest/courseware/Soundings_from_Observations_and_RCE_Models.html, https://climlab.readthedocs.io/en/latest/api/climlab.radiation.RRTMG.html, https://github.com/climlab/climlab, https://github.com/climlab/climlab/releases, https://prefix.dev/channels/conda-forge/packages/climlab, https://prefix.dev/channels/conda-forge/packages/climlab-rrtmg, https://prefix.dev/channels/conda-forge/packages/climlab-cam3-radiation, https://prefix.dev/channels/conda-forge/packages/climlab-emanuel-convection, https://brian-rose.github.io/ClimateLaboratoryBook/

---

#### WRF (Weather Research and Forecasting model, ARW core)

**What it is.** WRF is a regional numerical weather prediction and atmospheric research model. It is written in Fortran (with C and csh/perl build scripts) and uses MPI and OpenMP. License: **public domain** ("NCAR and UCAR ... consider WRF to be in the public domain for use by any person or entity for any purpose without any fee or charge", `LICENSE.txt`). Current release **v4.8.0 (2026-06-08)**. It adds an optional CMake build for `em_real` and `em_ideal`, alongside the traditional `./configure && ./compile`. Download `v4.8.0.tar.gz` from the release assets: GitHub's "Source code" archives omit the mandatory submodules. Real-data forecasts need WPS and gigabytes of geographic and meteorological data, so they are out of scope. The **idealized cases** in `test/em_*` need no external data: `em_b_wave`, `em_convrad`, `em_fire`, `em_grav2d_x`, `em_heldsuarez`, `em_hill2d_x`, `em_les`, `em_quarter_ss`, `em_scm_xy`, `em_seabreeze2d_x`, `em_squall2d_x`, `em_squall2d_y` and `em_tropical_cyclone` (13, per the Users' Guide's "Idealized Case Initialization"). Each is run as `./ideal.exe` then `./wrf.exe`, from a `namelist.input` and a text `input_sounding`. Fit with EMA: the 1-D and 2-D cases run in seconds to tens of seconds on one core. The 3-D supercell takes minutes. Moist convection makes outputs rough. Some physical parameters (hill height, bubble amplitude) are hard-coded in `dyn_em/module_initialize_ideal.F`, so they can't be inputs without recompiling. Use the sounding and the namelist instead.

**Install on an Intel Mac.** There is no conda-forge WRF (only `wrf-python`), no current official Docker image (NCAR's `bigwxwrf/ncar-wrf` was last updated in 2017; `NCAR/WRF_DOCKER` is a Dockerfile repository for `em_real` tutorials and regression tests), and no Homebrew route (Tier 3). A native macOS build with conda-forge `gfortran` and `netcdf-fortran` is possible in principle (WRF's `configure` has Darwin/gfortran options), but it is fiddly and **(unconfirmed)**. **Recommended: build your own `linux/amd64` image with Docker Desktop.**
1. Install Docker Desktop (Intel chip), and raise memory to 8 GB in Settings → Resources.
2. Write a small Dockerfile (Claude Code writes it in Stage 2a) based on `ubuntu:24.04`, pinned by digest. It installs `gfortran gcc g++ make m4 perl tcsh curl file libnetcdf-dev libnetcdff-dev netcdf-bin python3 python3-numpy python3-netcdf4` from apt, downloads `https://github.com/wrf-model/WRF/releases/download/v4.8.0/v4.8.0.tar.gz` **(unconfirmed exact asset URL; the asset name `v4.8.0.tar.gz` is confirmed)**, and builds three ideal cases:
   ```bash
   docker pull ubuntu:24.04
   docker buildx imagetools inspect ubuntu:24.04          # copy the linux/amd64 digest into FROM
   docker build --platform linux/amd64 -t ema-wrf:4.8.0 .  # ~30–60 min per case *(estimate)*
   docker image inspect --format '{{.Id}}' ema-wrf:4.8.0  # use this sha256 id in model.json
   ```
   Inside the build: `export NETCDF=/usr`, then `./configure` and pick the **GNU (gfortran/gcc) serial** option (32 on Linux x86_64 in WRF 4.x **(unconfirmed; read the menu)**) with **no nesting** ("All 2-D and 1-D ideal cases MUST be compiled with serial computing and a 'no nest' option"). Then `./compile em_hill2d_x >& log.compile`. Copy `main/ideal.exe` to `/opt/wrf/bin/ideal_hill2d_x.exe` and `main/wrf.exe` to `wrf_hill2d_x.exe`. Repeat for `em_scm_xy` and `em_quarter_ss` (`./clean -a` and reconfigure between cases, since each case compiles its own `ideal.exe`). Keep the `run/` tables (`*.TBL`, `RRTM_DATA`, ...) and `test/em_*/` directories in the image.
3. Check:
   ```bash
   docker run --rm ema-wrf:4.8.0 bash -c 'cd /opt/wrf/WRF/test/em_hill2d_x && /opt/wrf/bin/ideal_hill2d_x.exe && /opt/wrf/bin/wrf_hill2d_x.exe 2>&1 | tail -2'
   ```
   Expect `wrf: SUCCESS COMPLETE WRF`.
Known problems: WRF looks for netCDF under `$NETCDF/include` and `$NETCDF/lib`, with the C and Fortran libraries together. Ubuntu keeps its libraries in `/usr/lib/x86_64-linux-gnu`, so configure may not find them. The usual fix is a directory of symlinks (`/opt/netcdf/{include,lib}`) and `NETCDF=/opt/netcdf` **(unconfirmed which is needed with 4.8)**. The build scripts need `csh` (the `tcsh` package). With gfortran ≥ 10 you may need `-fallow-argument-mismatch` (WRF 4.2+ adds it itself **(unconfirmed)**). 3-D runs may need an unlimited stack: set it in the driver (`resource.setrlimit(resource.RLIMIT_STACK, ...)`) or with `docker run --ulimit stack=-1`.
Sources: https://github.com/wrf-model/WRF/releases/tag/v4.8.0, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compilation_tutorial.php, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/Compile/ideal_compile.php, https://www2.mmm.ucar.edu/wrf/wrf_tutorial/compile_ideal.html, https://www2.mmm.ucar.edu/wrf/users/wrf_users_guide/build/html/idealized.html, https://github.com/NCAR/WRF_DOCKER, https://hub.docker.com/r/bigwxwrf/ncar-wrf/, https://prefix.dev/channels/conda-forge/packages/wrf-python, https://docs.docker.com/desktop/setup/install/mac-install/

**Install on AWS (Ubuntu 24.04 EC2).** Preferred: build natively with apt's compilers and netCDF (no Docker overhead per run). Use the same steps as the Dockerfile:
```bash
sudo apt-get update
sudo apt-get install -y gfortran gcc g++ make m4 perl tcsh curl file libnetcdf-dev libnetcdff-dev netcdf-bin python3 python3-numpy python3-netcdf4
mkdir -p ~/wrf && cd ~/wrf
curl -LO https://github.com/wrf-model/WRF/releases/download/v4.8.0/v4.8.0.tar.gz
tar xf v4.8.0.tar.gz && cd WRF*      # the top directory name is (unconfirmed)
export NETCDF=/usr                    # or a symlink directory, see the Mac notes
./configure                           # GNU serial, no nesting
./compile em_hill2d_x >& log.compile
ls -l main/ideal.exe main/wrf.exe
```
Fallback: the same Dockerfile as on the Mac (`sudo apt-get install -y docker.io`). A `c7i.2xlarge` suffices for the 1-D and 2-D cases, and a `c7i.8xlarge` for supercell campaigns with `-j 16` or more. Check: `cd test/em_hill2d_x && ./ideal.exe && ./wrf.exe` ends with `SUCCESS COMPLETE WRF`.
Sources: https://packages.ubuntu.com/noble/libnetcdff-dev, https://packages.ubuntu.com/noble/python3-netcdf4, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compilation_tutorial.php, https://github.com/wrf-model/WRF/releases/tag/v4.8.0

**Preparing the examples for EMA.** Each example directory holds:
- `run_wrf.py`, a static driver copied into the run directory (it must be a copy, not a host path, for Docker);
- `namelist.template`, a `string.Template` of the case's `namelist.input`. Fortran namelists contain no `$`, but check;
- the deck.

The driver:
1. writes `input_sounding` from the inputs (first line: surface pressure hPa, θ K, q_v g/kg; then height, θ, q_v, u, v per level);
2. links the physics tables from WRF's `run/` directory;
3. runs `ideal.exe` then `wrf.exe`, and exits non-zero unless `SUCCESS COMPLETE WRF` appears;
4. reads `wrfout_d01_*` with `netCDF4`;
5. prints `EMA_OUTPUT <value>`.

Set `nocolons = .true.` in `&time_control` so the output file names have no colons. Keep the grid and time step fixed, and run serially. WRF's stochastic schemes (SKEBS and the like) are off by default. Command on the Mac: `docker run --rm --user <uid>:<gid> -v $EMA_WORKDIR:/work -w /work <image id> python3 run_wrf.py deck.txt`. On AWS: the absolute path of `/usr/bin/python3`, then `run_wrf.py deck.txt`, with the executables' absolute paths in the deck or in `env`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `test/em_scm_xy` (https://github.com/wrf-model/WRF/tree/master/test/em_scm_xy), GABLS II–based single column: 3×3 doubly periodic points, 60 levels, `dx` 4 km, `time_step` 60 s, 59 h, full physics (`mp_physics` 2, RRTM/Dudhia radiation, `sf_sfclay_physics` 1, Noah LSM `sf_surface_physics` 2, YSU `bl_pbl_physics` 1) | diurnal cycle of the boundary layer over land (37.6°N, −96.7°) | `scm_vegfra` 50 [10, 90] (namelist); `scm_lat` 37.6 [25, 55] (namelist; changes insolation); `dtheta` 0 [−3, 3] K (the driver adds it to the sounding's θ below 1 km **(my addition)**); `run_hours` fixed at 36 to save time | mean 2-m temperature `T2` over the last 24 h (a second model: maximum `PBLH` over the last day) | monotone: `T2` decreasing in `scm_lat` and increasing in `dtheta`; `scm_vegfra` shifts the Bowen ratio, so a monotone effect on `PBLH`; mild interactions. `PBLH` from YSU may show small steps (level-by-level diagnosis), which `nonsmooth` would flag *(expected, unconfirmed)* | 10–40 s *(estimate)* | cli (docker or python3 + `run_wrf.py`) | regex |
| `test/em_hill2d_x` (https://github.com/wrf-model/WRF/tree/master/test/em_hill2d_x): 2-D flow over a bell-shaped hill 100 m high, 10 km half-width; `e_we` 202, 41 levels, `dx` 2 km, `ztop` 30 km, `time_step` 20 s, 10 h, no physics | linear hydrostatic mountain waves (dry), absorbing upper layer (`damp_opt` 3, `dampcoef` 0.1) | `U` 10 [2, 20] m/s (uniform wind in the sounding); `N` 0.01 [0.005, 0.02] s⁻¹ (θ(z) = θ₀ exp(N²z/g) in the sounding); `dampcoef` 0.1 [0.02, 0.3] (namelist). The hill itself is hard-coded (`module_initialize_ideal.F`) | maximum \|w\| over the domain at the last history time | near-linear in `U` while Nh/U is small (linear theory; *(expected, unconfirmed)*); weak dependence on `N` in the hydrostatic regime; **a regime change** (steepening, possible wave breaking) as Nh/U approaches about 1 (low `U`, high `N`), a kink or jump for `nonsmooth`; `dampcoef` near-**negligible** if the sponge works | 5–20 s *(estimate)* | cli | regex |
| `test/em_quarter_ss` (https://github.com/wrf-model/WRF/tree/master/test/em_quarter_ss): 3-D quarter-circle-shear supercell, 42×42×41 points (`e_we`, `e_sn` 42; `e_vert` 41), `dx` 2 km, `time_step` 12 s, 60 min, Kessler microphysics (`mp_physics` 1), `khdif` = `kvdif` = 500 | deep moist convection from a warm bubble in a Weisman–Klemp-type sounding | `shear_scale` 1 [0.5, 1.5] (the driver scales the sounding's u, v); `qv_scale` 1 [0.85, 1.1] (scales the sounding's low-level moisture); `khdif` 500 [250, 1000] (namelist, with `kvdif` = `khdif`) | domain-total accumulated grid-scale rain `RAINNC` at 60 min (second model: maximum `W` over the run's history times) | **thresholds**: below a moisture threshold no storm forms (a zero-rain plateau and a jump); strong `qv_scale` × `shear_scale` interaction; chaotic sensitivity makes the output **rough** (many small jumps) though `repeat` is exact; `khdif` smooths, a smaller effect | 2–6 min serial *(estimate)*: AWS for campaigns | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — WRF, check the machine (read-only). I want to onboard idealized WRF v4.8.0 cases (em_scm_xy, em_hill2d_x, em_quarter_ss) into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), Docker (docker version, whether the daemon runs, the memory and disk limits Docker Desktop reports in `docker info`), any gfortran, conda/mamba, netCDF (nc-config --all, nf-config --all), csh/tcsh, and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, a self-built linux/amd64 Docker image `ema-wrf:4.8.0` from ubuntu:24.04 pinned by digest (no conda-forge WRF, no current official image, no Homebrew); on Ubuntu 24.04, a native build with apt's gfortran and libnetcdff-dev. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — build WRF v4.8.0 in Docker on this Intel Mac. Write docker/wrf/Dockerfile in a scratch directory outside the EMA repo (show it to me before building): FROM ubuntu:24.04@sha256:<amd64 digest you look up with `docker buildx imagetools inspect ubuntu:24.04`>; apt-get install gfortran gcc g++ make m4 perl tcsh curl file libnetcdf-dev libnetcdff-dev netcdf-bin python3 python3-numpy python3-netcdf4; download the v4.8.0.tar.gz release asset from github.com/wrf-model/WRF/releases (not the "Source code" archive, which lacks submodules); configure the GNU serial option with no nesting (read the menu, don't guess the number; if netCDF isn't found, make /opt/netcdf/{include,lib} symlinks and set NETCDF=/opt/netcdf); compile em_hill2d_x, em_scm_xy and em_quarter_ss one after another (./clean -a and reconfigure between cases), copying each case's ideal.exe and wrf.exe to /opt/wrf/bin/<name>_<case>.exe; keep run/ and test/. Never install into EMA's .venv, and never read .env. Ask me before the build (it downloads about 1 GB of layers and takes an hour or more), before any sudo or Homebrew change, and before changing Docker Desktop's settings. Check: run ideal and wrf for em_hill2d_x inside the container and grep for "SUCCESS COMPLETE WRF". Report the image id (sha256) and the build log's last lines. Stop at the first error and report the command and output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — build WRF v4.8.0 on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask before sudo, then `sudo apt-get install -y gfortran gcc g++ make m4 perl tcsh curl file libnetcdf-dev libnetcdff-dev netcdf-bin python3 python3-numpy python3-netcdf4`. Download the v4.8.0.tar.gz release asset into ~/wrf, unpack, export NETCDF=/usr (or a symlink directory if configure can't find netCDF), run ./configure and choose GNU serial with no nesting (read the menu), and compile em_hill2d_x, em_scm_xy and em_quarter_ss in turn (./clean -a between cases), copying each ideal.exe and wrf.exe to ~/wrf/bin/<name>_<case>.exe. Never use EMA's .venv, and never read .env. Ask before downloads over 1 GB. If the native build fails, report and propose (don't run) the Dockerfile route from my Mac. Check each case with ideal.exe then wrf.exe in a copy of its test directory, grepping for "SUCCESS COMPLETE WRF". Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — WRF smoke test. For each of em_hill2d_x and em_scm_xy: copy the case's test directory (with its namelist.input, input_sounding and, for scm, input_soil and force_ideal.nc) to a scratch directory, link the physics tables from WRF's run/ directory that the case needs, run the case's ideal.exe and wrf.exe serially (inside the ema-wrf image on the Mac, natively on AWS), and time each. Then list the wrfout file's variables with ncdump -h and report the dimensions, the history times, and the ranges of W (hill2d) and T2 and PBLH (scm). Don't run em_quarter_ss yet, and don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the WRF single-column case (em_scm_xy) for EMA. Enter plan mode first and show me the plan. Put it in examples/wrf/scm/. Files: run_wrf.py (a static driver copied into the run directory), namelist.template (the case's namelist.input with $scm_vegfra, $scm_lat and nocolons = .true.; run_hours 36; check it has no other `$`, and escape any as `$$`), input_sounding.base, input_soil and force_ideal.nc as static files, and deck.template. The driver reads the deck, adds dtheta to the sounding's theta below 1 km, links the WRF run/ tables the case needs (or copies them in the image), runs ideal.exe and wrf.exe, exits 3 unless stdout contains "SUCCESS COMPLETE WRF", reads wrfout_d01_* with netCDF4, and prints `WRF 4.8.0` and `EMA_OUTPUT <mean T2 over the last 24 h at the centre point, %.12e>`. Inputs: scm_vegfra = 50 [10, 90], scm_lat = 37.6 [25, 55], dtheta = 0 [-3, 3]. Follow docs/guides/input_deck_model.md, examples/cantera/ and examples/beam/. Mac command: ["docker", "run", "--rm", "--user", "<my uid>:<gid>", "-v", "$EMA_WORKDIR:/work", "-w", "/work", "<image sha256 id>", "python3", "run_wrf.py", "deck.txt"]; AWS: [<absolute /usr/bin/python3>, "run_wrf.py", "deck.txt"] in a separate model_aws.json. env OMP_NUM_THREADS=1, timeout_s 600, regex "EMA_OUTPUT (\S+)". Write model_pblh.json too (max PBLH over the last day, same driver). Check by hand that the nominal matches Stage 3 and that scm_lat = 55 is cooler than 25. Then `.venv/bin/ema profile examples/wrf/scm/model.json -n 5` and report the time per run and the Docker start-up share. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the WRF 2-D hill case (em_hill2d_x). Plan mode first. Put it in examples/wrf/hill2d/, with the same driver pattern as examples/wrf/scm/. The driver writes input_sounding from U and N: a first line of surface pressure 1000 hPa, theta0 = 288 K (or the case's own value; read test/em_hill2d_x/input_sounding), and qv 0; then levels every 250 m to 30 km with theta = theta0*exp(N^2 z / 9.81), qv 0, u = U, v 0. Namelist template: the case's namelist.input with $dampcoef and nocolons = .true. Inputs: U = 10 [2, 20], N = 0.01 [0.005, 0.02], dampcoef = 0.1 [0.02, 0.3]. Output: `EMA_OUTPUT <max |W| over the domain at the last history time, %.12e>`. timeout_s 300. Check by hand that the nominal sounding reproduces the case's own result (compare with Stage 3), and that doubling U roughly doubles the output. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the WRF supercell case (em_quarter_ss). Plan mode first; this one is slow, so profile it before anything else. Put it in examples/wrf/supercell/, with the same driver pattern. The driver scales the case's own input_sounding: u and v by shear_scale, and qv below 3 km by qv_scale. Namelist template: the case's namelist with $khdif for both khdif and kvdif, run_minutes 60, history_interval 10, and nocolons = .true. Inputs: shear_scale = 1 [0.5, 1.5], qv_scale = 1 [0.85, 1.1], khdif = 500 [250, 1000]. Output: `EMA_OUTPUT <sum of RAINNC over the domain at 60 min, %.12e>`; also write model_wmax.json for the maximum W over the history times. Set the stack to unlimited in the driver (resource.setrlimit) or with docker's --ulimit stack=-1. timeout_s 1800. Check by hand that qv_scale = 0.85 gives much less rain than 1.0. Then `.venv/bin/ema profile ... -n 3` and tell me the time per run and what a 200-run campaign would cost on this machine and on a c7i.8xlarge with -j 16. Stop and report; don't run a campaign.
```

```text
Stage 5 — first WRF campaign. For examples/wrf/hill2d/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), curve1d on U (n 15), and surface2d on (U, N) (n 9 per side). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before running `.venv/bin/ema run ... -j 4`. After it runs, report: whether repeats are identical (expected: exactly), morris's ranking (expected: U first, dampcoef possibly negligible), curve1d's shape in U (near-linear at high U), and where surface2d finds a kink or jump (expected near N*100 m/U ≈ 1, low U and high N). Suggest (don't run) linear_coeffs with log_output. Stop and report.
```

```text
Stage 6 — WRF troubleshooting. An EMA WRF model (examples/wrf/<case>) fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt and ema_run.json, then by running the driver by hand in a copy of the run directory. Check for: ideal.exe or wrf.exe missing or built for another case (each case has its own ideal.exe), missing physics tables (LANDUSE.TBL, VEGPARM.TBL, SOILPARM.TBL, GENPARM.TBL, RRTM_DATA), "SUCCESS COMPLETE WRF" absent (CFL violations: the time step is too long for a high wind or a strong updraft, so a failure region, not a bug), a segfault in 3-D (stack size), a namelist read error (a template substitution produced a bad value; check number_format), files owned by root (docker --user), colons in output file names, netCDF4 missing from the driver's python, and oversubscribed threads (OMP_NUM_THREADS=1). Report the cause and a proposed fix. Ask before changing the image, the driver or model.json.
```

**Gotchas and sources.**
- License: public domain (with a warranty disclaimer).
- Parallelism: build **serial** (1-D and 2-D cases *must* be serial with no nesting). EMA's `-j` gives the parallelism. A dmpar build run under MPI gives the same answers only up to rounding, and writes `rsl.*` files instead of stdout.
- Determinism: serial WRF with no stochastic schemes is bit-reproducible (`repeat` should show zero spread). Convection makes outputs rough in the inputs. Prefer domain totals or time means to point maxima. CFL-violation crashes at strong winds are failed runs, and they form a failure region.
- Inputs: namelist values and the sounding are easy. Terrain, bubble and domain geometry are compiled into `ideal.exe` (`module_initialize_ideal.F`), so changing them means recompiling: don't make them inputs.
- Run time: seconds (`em_hill2d_x`, `em_scm_xy`) to minutes (`em_quarter_ss`). Docker start-up adds about 0.5–2 s per run **(unconfirmed; measure)**.
- Versions: record `WRF 4.8.0` in the description. The image isn't hashed, so pin it by its sha256 id. `configure` option numbers differ between versions and platforms: read the menu.
- Sources: https://github.com/wrf-model/WRF, https://github.com/wrf-model/WRF/releases, https://github.com/wrf-model/WRF/releases/tag/v4.8.0, https://github.com/wrf-model/WRF/blob/master/LICENSE.txt, https://www2.mmm.ucar.edu/wrf/users/, https://www2.mmm.ucar.edu/wrf/users/wrf_users_guide/build/html/idealized.html, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/CASES/Ideal/index.php, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compilation_tutorial.php, https://www2.mmm.ucar.edu/wrf/OnLineTutorial/Compile/ideal_compile.php, https://www2.mmm.ucar.edu/wrf/wrf_tutorial/compile_ideal.html, https://raw.githubusercontent.com/wrf-model/WRF/master/test/em_hill2d_x/namelist.input, https://raw.githubusercontent.com/wrf-model/WRF/master/test/em_quarter_ss/namelist.input, https://raw.githubusercontent.com/wrf-model/WRF/master/test/em_scm_xy/namelist.input, https://github.com/wrf-model/WRF/tree/master/test/em_scm_xy, https://github.com/NCAR/WRF_DOCKER, https://github.com/NCAR/container-wrf, https://hub.docker.com/r/bigwxwrf/ncar-wrf/, https://anaconda.org/conda-forge/wrf-python, https://packages.ubuntu.com/noble/libnetcdff-dev

---

#### CESM (Community Earth System Model), single-column CAM (SCAM)

**What it is.** CESM is NCAR's coupled climate model: atmosphere CAM, land CLM/CTSM, ocean POP/MOM6, sea ice CICE, and others. It is Fortran with MPI, driven by the Python/XML case system **CIME** (`create_newcase`, `case.setup`, `case.build`, `case.submit`). License: the CESM2 terms of use (a BSD-style copyright notice and disclaimer from UCAR, `LICENSE.txt`). Some components carry their own licenses. Releases:
- **CESM 2.1.5** (GitHub release `release-cesm2.1.5`, 2025-06-25): the "current supported CESM production release".
- **CESM 2.2.2** (tag `release-cesm2.2.2`, commit dated 2023-12-22): the "current supported CESM development release", which the site says "is not a scientifically supported version".
- **CESM 3.0** is still in beta (`cesm3_0_beta10` on GitHub, dated 2026-09-24; NCAR targeted a spring-2026 release, and the CESM3 page still says "More information coming soon" **(unconfirmed whether 3.0.0 is out)**).

**Honest fit:** a global CESM run, even F-compset atmosphere-only at 2°, takes hours per simulated year on many cores and tens of GB of input data. It **does not fit EMA**. The configuration that does fit is **SCAM**, the single-column CAM (compset `FSCAM`, res `T42_T42`). It uses the full CAM6 physics in one column, forced by an observed Intensive Observation Period (IOP). The IOP cases ship as CAM "usermods" directories: `scam_arm95`, `scam_arm97`, `scam_atex`, `scam_bomex`, `scam_cgilsS6/S11/S12`, `scam_dycomsRF01/RF02`, `scam_gateIII`, `scam_mpace`, `scam_rico`, `scam_sparticus`, `scam_togaII`, `scam_twp06`, `scam_SAS` (in `components/cam/cime_config/usermods_dirs/` of CESM 2.2). The SCAM page is https://www.cesm.ucar.edu/models/simpler-models/scam/index.html. SCAM's physics parameters (CLUBB, Zhang–McFarlane convection, MG microphysics) are exactly the kind of inputs that perturbed-parameter studies vary. CIME can't make a case per EMA run cheaply, so build one case, then run `cesm.exe` directly in each run directory with an edited `atm_in`. That is fiddly, and marked below.

**Install on an Intel Mac.** Docker only. There's no conda package, and a native CIME port to macOS would need Homebrew-built compilers and libraries (CIME's `homebrew` machine), which is ruled out on Intel.
1. Docker Desktop (Intel), with memory raised to 8 GB or more.
2. Pull NCAR's container `escomp/cesm-2.2`. Facts about it:
   - It is **CESM 2.2.0** on CentOS 8 with MPICH, netCDF and PnetCDF, amd64 only, 0.97 GB compressed, **last pushed 2020-11-02**.
   - It sets `CIME_MACHINE=container` and keeps input data in `$CESMDATAROOT/inputdata` (the home directory, `/home/user`).
   - It patches SCAM for GNU and `mpi-serial`.
   ```bash
   docker pull escomp/cesm-2.2:latest
   docker buildx imagetools inspect escomp/cesm-2.2:latest     # record the digest
   mkdir -p ~/cesm-container
   docker run -it --rm -v ~/cesm-container:/home/user escomp/cesm-2.2@sha256:<digest>
   ```
3. Inside the container, create and build a SCAM case (the command is from the SCAM page, with the case name and paths yours):
   ```bash
   create_newcase --case ~/cases/scam_bomex --compset FSCAM --res T42_T42 \
     --user-mods-dir $CESMROOT/components/cam/cime_config/usermods_dirs/scam_bomex --run-unsupported
   cd ~/cases/scam_bomex && ./case.setup && ./case.build && ./check_input_data --download && ./case.submit
   ```
   The first `case.submit` fetches the input data: the IOP file, initial conditions, and aerosol and ozone climatologies. The size is **(unconfirmed)**; expect hundreds of MB to a few GB.
4. Check: the case's `CaseStatus` ends with `case.run success`, and `run/` holds `*.cam.h0.*.nc`.
Known problems: the container is **six years old**, and its CentOS 8 base is end-of-life. Its `config_inputdata.xml` points at UCAR FTP and GridFTP servers from 2020 (`ftp.cgd.ucar.edu`, `gridanon.cgd.ucar.edu`), which may no longer serve data **(unconfirmed; test in Stage 3)**. If they don't, point `DIN_LOC_ROOT` at data fetched from the current CESM input data server.
Sources: https://github.com/ESCOMP/ESCOMP-Containers (`CESM/2.2/Dockerfile`, `Files/config_machines.xml`, `Files/config_inputdata.xml`), https://hub.docker.com/r/escomp/cesm-2.2, https://bb.cgd.ucar.edu/cesm/threads/containerized-cesm-for-laptops-workstations-windows-mac-linux.5684/, https://www.cesm.ucar.edu/models/simpler-models/scam/index.html

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred for a first try: the **same container**, which avoids porting CIME (`sudo apt-get install -y docker.io`, then as on the Mac). Use a `c7i.2xlarge` with 100 GB of gp3.
2. Native port of the supported release (CESM 2.1.5, or 2.2.2 to match the container's SCAM):
   ```bash
   sudo apt-get install -y gfortran gcc g++ make cmake perl libxml-libxml-perl python3 subversion git \
     libopenmpi-dev openmpi-bin libnetcdf-dev libnetcdff-dev libpnetcdf-dev liblapack-dev libblas-dev
   git clone -b release-cesm2.2.2 https://github.com/ESCOMP/CESM.git ~/cesm2.2.2
   cd ~/cesm2.2.2 && ./manage_externals/checkout_externals
   ```
   Then write `~/.cime/config_machines.xml` (and `config_compilers.xml`) for this machine, following CIME's porting guide and the `centos7-linux` entry. The pieces are:
   - `OS` LINUX, `COMPILERS` gnu, `MPILIBS` openmpi and mpi-serial;
   - `DIN_LOC_ROOT` on the EBS volume, and `BATCH_SYSTEM` none;
   - `NETCDF_PATH` /usr.

   Create the SCAM case with `--machine <yours>`. Porting takes a day or more, and every detail is **(unconfirmed)** until Stage 2b tries it.
3. Global configurations (for example `F2000climo` at `f19_g17`) are **not planned**. They need hours per simulated year on many cores and tens of GB of input data: an `hpc7a` or `c7i.24xlarge`-class instance and 500 GB+ of disk.
Sources: https://github.com/ESCOMP/CESM/releases, https://www.cesm.ucar.edu/models, https://esmci.github.io/cime/versions/master/html/users_guide/porting-cime.html, https://github.com/ESCOMP/CAM/tree/cam_cesm2_2_rel/cime_config/usermods_dirs

**Preparing the examples for EMA.** Build the SCAM case once, run it once with CIME, and treat its `run/` directory as the model's fixed files. It contains the namelists `atm_in`, `drv_in`, `drv_flds_in`, `lnd_in`, the data-model stream files, `*_modelio.nml` and `seq_maps.rc`, and the build directory holds `cesm.exe`. The EMA driver `run_scam.py` (static, run inside the container on the Mac):
1. copies those files into the EMA run directory;
2. rewrites the chosen `atm_in` variables from the deck;
3. rewrites the `diro`/`logfile` entries of the `*_modelio.nml` files to `.` (they hold the case's absolute run path **(unconfirmed that this suffices)**);
4. runs `cesm.exe` serially (the container's SCAM uses `mpi-serial`);
5. reads `*.cam.h0.*.nc` with netCDF4 (install `python3-netCDF4` into the image if it has none **(unconfirmed)**) and prints `EMA_OUTPUT`.

Input data stay at their absolute paths in the mounted data directory. Take the **nominal values from the built case's `atm_in`**. The CAM6 defaults in CESM 2.2's `namelist_defaults_cam.xml` are `clubb_c14` 2.2, `clubb_gamma_coef` 0.308 (0.270 for the SE dycore), `micro_mg_dcs` 500e-6 (MG2), `zmconv_c0_ocn` 0.0300 and `zmconv_c0_lnd` 0.0075 (MG2 with CLUBB), but SCAM's own values may differ.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| SCAM BOMEX, usermods `scam_bomex` (https://github.com/ESCOMP/CAM/tree/cam_cesm2_2_rel/cime_config/usermods_dirs/scam_bomex): IOP `BOMEX_5day_4scam.nc`, 15°N 300°E, start 1969-06-25, `STOP_N` 5 days | trade-wind shallow cumulus over ocean, CAM6 (CLUBB + MG2 + ZM) | `clubb_c14` from `atm_in` [0.5×, 2×]; `clubb_gamma_coef` from `atm_in` [0.22, 0.34]; `micro_mg_dcs` from `atm_in` [100e-6, 600e-6] (log) | time-mean low-cloud fraction `CLDLOW` over days 2–5 (second model: time-mean liquid water path `TGCLDLWP`) | CLUBB parameters dominate (`clubb_gamma_coef` is a known sensitive knob); `micro_mg_dcs` near-**negligible** for warm shallow cloud *(expected)*; interactions between the CLUBB parameters; some roughness from cloud-fraction switches (`nonsmooth` may flag small jumps) | 20–60 s after the build *(estimate)* | cli (docker + `run_scam.py`) | regex |
| SCAM ARM95, usermods `scam_arm95`: 36.6°N 262.5°E, start 1995-07-18, 1259 time steps (the default length) | continental deep convection at the ARM Southern Great Plains site | `zmconv_c0_lnd` from `atm_in` [0.002, 0.02] (log); `zmconv_ke` from `atm_in` [0.5×, 5×] (log); `clubb_c14` from `atm_in` [0.5×, 2×] | time-mean total precipitation `PRECT` (mm/day) | largely constrained by the IOP forcing (the moisture budget is prescribed), so precipitation is only moderately sensitive; `zmconv_c0_lnd` and `zmconv_ke` dominate the partition between convective and large-scale rain (a second model on `PRECC` would show it); roughness from convective triggering | 1–3 min *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — CESM, check the machine (read-only). I want to onboard CESM's single-column atmosphere model (SCAM, compset FSCAM) into EMA. Run only read-only commands and report: OS and version, CPU architecture, total RAM, free disk space (at least 60 GB needed), Docker (docker version, daemon running, Docker Desktop's memory and disk limits from `docker info`), any existing escomp/cesm images, and on Linux: gfortran, MPI, nc-config/nf-config, perl XML::LibXML, svn. Don't install anything, and don't read .env. Recommend a route: the escomp/cesm-2.2 container (CESM 2.2.0, CIME machine "container") on both the Intel Mac and AWS; a native CIME port of CESM 2.2.2 on Ubuntu only as a later option. Say plainly that global CESM configurations are out of scope. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install the CESM 2.2 container on this Intel Mac. Ask me before pulling escomp/cesm-2.2 (about 1 GB compressed, more on disk). Pull it, record its digest (`docker buildx imagetools inspect escomp/cesm-2.2:latest`), create ~/cesm-container for /home/user, and start it once with `docker run -it --rm -v ~/cesm-container:/home/user escomp/cesm-2.2@sha256:<digest>` just to run `echo $CIME_MACHINE $CESMROOT; ls $CESMROOT; gfortran --version; python3 -c "import netCDF4"` (report whether netCDF4 is importable). Never install into EMA's .venv, and never read .env. Ask before any sudo, Homebrew change, Docker Desktop settings change, or download over 1 GB. Stop at the first error and report the command and output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install the CESM 2.2 container on this AWS EC2 instance (Ubuntu 24.04). Ask before sudo, then install docker.io if missing and add me to the docker group (ask). Pull escomp/cesm-2.2 (ask first; about 1 GB), record the digest, create ~/cesm-container on the EBS volume, and run the same check as on my Mac. Never use EMA's .venv, and never read .env. Don't attempt a native CIME port now; if the container fails, report and propose (don't run) the native route: CESM release-cesm2.2.2 with manage_externals, apt gfortran/openmpi/netCDF/PnetCDF/LAPACK/libxml-libxml-perl/subversion, and a ~/.cime/config_machines.xml modelled on the centos7-linux entry. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — CESM SCAM smoke test. Inside the container (with ~/cesm-container mounted as /home/user), create the BOMEX case: `create_newcase --case ~/cases/scam_bomex --compset FSCAM --res T42_T42 --user-mods-dir $CESMROOT/components/cam/cime_config/usermods_dirs/scam_bomex --run-unsupported`, then case.setup and case.build. Before `./check_input_data --download`, run `./check_input_data` (no download) and tell me what is missing and roughly how large it is; ask me before downloading if it's over 1 GB. If the container's FTP input-data servers fail, stop and report (don't hunt for mirrors). Then `./case.submit`, time it, and report CaseStatus, the run directory's file list, the h0 history file's name and variables (ncdump -h if available), and the time-mean CLDLOW and TGCLDLWP. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare CESM SCAM BOMEX for EMA. Enter plan mode first and show me the plan; this is the fiddly part. Goal: each EMA run executes the already-built cesm.exe in its own run directory with an edited atm_in, without CIME. Put it in examples/cesm/scam_bomex/. Steps: (1) in the container, list what cesm.exe reads from the case's run directory (all *_in files, *_modelio.nml, seq_maps.rc, stream files) and which absolute paths they contain; (2) snapshot those files into a directory under ~/cesm-container (not the EMA repo), and record it; (3) write run_scam.py, a static driver copied into the run directory, that copies the snapshot in, sets clubb_c14, clubb_gamma_coef and micro_mg_dcs in atm_in from deck.txt (use f90nml only if the container has it; otherwise a careful regex on `name = value` lines), rewrites diro/logfile in *_modelio.nml to ".", runs cesm.exe (absolute path in the container), exits non-zero unless the cpl log says SUCCESSFUL TERMINATION, reads *.cam.h0.*.nc, and prints `CESM 2.2.0 SCAM` and `EMA_OUTPUT <time-mean CLDLOW over days 2-5, %.12e>`. Nominals: read them from the case's atm_in. Ranges: clubb_c14 [0.5x, 2x nominal], clubb_gamma_coef [0.22, 0.34], micro_mg_dcs [100e-6, 600e-6] with scale log. Command: docker run --rm --user <uid>:<gid> -v $EMA_WORKDIR:/work -v ~/cesm-container:/home/user -w /work <image>@sha256:<digest> python3 run_scam.py deck.txt (follow docs/guides/input_deck_model.md; a static driver, not a host path). timeout_s 600, env OMP_NUM_THREADS=1. Write model_lwp.json for TGCLDLWP too. Check by hand that the nominal reproduces Stage 3's CLDLOW. Then `.venv/bin/ema profile examples/cesm/scam_bomex/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare CESM SCAM ARM95. Plan mode first. Create and build the ARM95 case in the container like Stage 3 (usermods scam_arm95; ask before input-data downloads over 1 GB), run it once with CIME, snapshot its run directory, and reuse run_scam.py in examples/cesm/scam_arm95/. Inputs: zmconv_c0_lnd (nominal from atm_in, range [0.002, 0.02], scale log), zmconv_ke (nominal from atm_in, [0.5x, 5x], scale log), clubb_c14 ([0.5x, 2x]). Output: `EMA_OUTPUT <time-mean PRECT in mm/day, %.12e>`; also model_precc.json for PRECC. timeout_s 900. Check by hand that the nominal matches the CIME run. Then `.venv/bin/ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first CESM campaign. For examples/cesm/scam_bomex/model.json, write campaign.json with repeat (n_points 2, replicates 2) and morris (n_traj 6). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before running `.venv/bin/ema run ... -j 4` (each run uses one core; check Docker's CPU and memory limits first). After it runs, report: whether repeats are bit-identical, morris's ranking and any possibly-negligible input (expected: micro_mg_dcs), how many runs failed and with what error, and whether mu*/sigma suggest interactions. Suggest (don't run) a sobol with n_base 64 and its cost. Stop and report.
```

```text
Stage 6 — CESM SCAM troubleshooting. An EMA SCAM model (examples/cesm/<case>) fails. Diagnose read-only first: read the run directory's stdout.txt, stderr.txt, atm.log*, cesm.log* and cpl.log* (they're in the EMA run directory if modelio was rewritten; otherwise in the snapshot's path, which means the rewrite failed). Check for: a namelist read error in atm_in (a substituted value in a bad format; check number_format and Fortran real syntax), a missing input file (an absolute path to inputdata that isn't mounted), files the run writes outside the run directory, a CLUBB or MG failure at extreme parameters (a failure region, not a bug), cesm.exe not found (the build directory isn't on the mounted volume), root-owned files (docker --user), and netCDF4 missing in the container's python. Report the cause and a proposed fix. Ask before changing the container, the snapshot, the driver or model.json.
```

**Gotchas and sources.**
- License: CESM2 terms of use (BSD-style, UCAR). Components have their own notices.
- Parallelism: SCAM runs one column in one task (`mpi-serial` in the container). Don't use `mpirun`. EMA's `-j` supplies the parallelism, within Docker Desktop's CPU limit.
- Determinism: serial CAM is bit-reproducible on one machine and build. Changing compiler flags or the image changes the numbers. Moist physics makes outputs rough in the parameters.
- Run time: after a build of 20–40 min *(estimate)* and the input-data download, a 5-day BOMEX run takes tens of seconds *(estimate)*, which fits EMA. Anything global doesn't.
- Version pitfalls: the container is CESM 2.2.0 from 2020, while the supported releases are 2.1.5 and 2.2.2, and CESM3 is in beta. Its input-data server list may be stale. Namelist variable names differ between CAM versions (for example `clubb_gamma_coef`): check `namelist_definition.xml` for the version you run. CIME writes absolute paths into the run directory's namelists, so running outside CIME needs the modelio rewrite and is **(unconfirmed)** until Stage 4.1 proves it.
- Sources: https://www.cesm.ucar.edu, https://www.cesm.ucar.edu/models, https://www.cesm.ucar.edu/models/cesm3, https://www.cesm.ucar.edu/news/community-earth-system-model-3-cesm3-plans-progress-timelines, https://github.com/ESCOMP/CESM, https://github.com/ESCOMP/CESM/releases, https://github.com/ESCOMP/CESM/blob/release-cesm2.2.2/LICENSE.txt, https://www.cesm.ucar.edu/models/simpler-models/scam/index.html, https://github.com/ESCOMP/CAM/tree/cam_cesm2_2_rel/cime_config/usermods_dirs, https://github.com/ESCOMP/CAM/blob/cam_cesm2_2_rel/bld/namelist_files/namelist_defaults_cam.xml, https://github.com/ESCOMP/CAM/blob/cam_cesm2_2_rel/bld/namelist_files/namelist_definition.xml, https://github.com/ESCOMP/ESCOMP-Containers, https://hub.docker.com/r/escomp/cesm-2.2, https://bb.cgd.ucar.edu/cesm/threads/containerized-cesm-for-laptops-workstations-windows-mac-linux.5684/, https://esmci.github.io/cime/versions/master/html/users_guide/porting-cime.html

---

#### E3SM (Energy Exascale Earth System Model), single-column EAM (SCM)

**What it is.** E3SM is the US Department of Energy's Earth-system model: atmosphere EAM (and the newer C++ EAMxx/SCREAM), land ELM, ocean and sea ice MPAS. It is Fortran and C++ with MPI, driven by CIME like CESM. License: **3-Clause BSD**, except for separable pieces listed in `LICENSE`. Current release **v3.0.2 (2024-12-17)**. Newer tags exist but aren't releases: `v3.1.0-beta.2` and `v3.2.0-alpha`. **Honest fit:** global E3SM is built for DOE supercomputers and doesn't fit EMA. The fitting configuration is the **E3SM Single Column Model** (compset `FSCM`, grid `ne4_ne4`, serial with `mpi-serial`), run from the case library in https://github.com/E3SM-Project/scmlib. It has 36 scripts in `E3SM_SCM_scripts/` (`run_e3sm_scm_BOMEX.csh`, `..._DYCOMSrf01.csh`, `..._ARM97.csh`, `..._RICO.csh`, `..._GATEIII.csh`, ..., plus `run_e3sm_scm_TEMPLATE.csh`). For v3, the scripts say to set `e3sm_version master`, which "will work with official release v3 codes". E3SM v3.0.2's CIME includes a **`linux-generic`** machine ("Linux workstation or laptop", gnu, openmpi/mpich, no batch system, input data in `~/projects/acme/cesm-inputdata`), as well as `mac` and `singularity` machines. The E3SM wiki says the SCM can be built and run "in a useful fashion on the mac". The only container documented, `lukaszlacinski/e3sm:2021.03.19`, is an individual's image from 2021, and the page was last updated in January 2022. The `e3sm` Docker Hub organisation has no model images (the last update was in 2019).

**Install on an Intel Mac.** There's no current container and no conda package, and a native macOS build needs Homebrew or MacPorts compilers (ruled out on Intel). The possible route is **a self-built Ubuntu 24.04 `linux/amd64` Docker image** that uses the `linux-generic` machine: the same steps as AWS below, inside Docker Desktop. It is **(unconfirmed)**, since nobody documents it, and it is hard. **Recommendation: do E3SM on AWS only**, and use the Mac just to read results. If you try the Mac anyway, reuse the AWS commands in a Dockerfile, and give Docker 8 GB of memory and 100 GB of disk.
Sources: https://e3sm.atlassian.net/wiki/spaces/DOC/pages/2488401938, https://github.com/E3SM-Project/scmlib/wiki/Running-the-E3SM-Single-Column-Model, https://hub.docker.com/u/e3sm

**Install on AWS (Ubuntu 24.04 EC2).** Native, with the `linux-generic` machine and `mpi-serial`. `c7i.2xlarge`, 100 GB gp3.
```bash
sudo apt-get update
sudo apt-get install -y gfortran gcc g++ make cmake git perl libxml-libxml-perl python3 csh wget \
  libnetcdf-dev libnetcdff-dev libpnetcdf-dev libopenmpi-dev openmpi-bin liblapack-dev libblas-dev
git clone -b v3.0.2 --recursive https://github.com/E3SM-Project/E3SM.git ~/E3SM_code/v3.0.2
git clone https://github.com/E3SM-Project/scmlib.git ~/scmlib
mkdir -p ~/projects/acme/cesm-inputdata ~/projects/acme/scratch
```
Then, in `~/scmlib/E3SM_SCM_scripts/run_e3sm_scm_BOMEX.csh`, set the "USER DEFINED SETTINGS":
- `machine linux-generic`;
- `code_dir ~/E3SM_code`, `code_tag v3.0.2`;
- `e3sm_version master`, `dycore SE`;
- `casedirectory ~/SCM_runs` (it defaults to `$PSCRATCH`).

Run the script with `csh`. `linux-generic` may still need netCDF and PnetCDF paths through environment variables (`NETCDF_PATH`, `PNETCDF_PATH`) or a `~/.cime` override **(unconfirmed)**. Input data are downloaded at `case.submit` from E3SM's public input-data server **(unconfirmed URL and size)**. The BOMEX script uses the prescribed-aerosol file `mam5_0.9x1.2_L80_F2010_c013024.nc` for `master`. Check: the case's `CaseStatus` shows `case.run success`, and the run directory holds `*.eam.h0.*.nc`.
Sources: https://github.com/E3SM-Project/E3SM/releases, https://github.com/E3SM-Project/E3SM/blob/v3.0.2/cime_config/machines/config_machines.xml (the `linux-generic` entry), https://github.com/E3SM-Project/scmlib, https://raw.githubusercontent.com/E3SM-Project/scmlib/master/E3SM_SCM_scripts/run_e3sm_scm_BOMEX.csh, https://docs.e3sm.org/E3SM/EAM/user-guide/

**Preparing the examples for EMA.** Same pattern as CESM SCAM: build and run the case once with the scmlib script, snapshot its run directory (`atm_in`, `drv_in`, `*_modelio.nml`, streams, ...), and run `e3sm.exe` directly per EMA run from a driver `run_scm.py`. The driver edits `atm_in`, rewrites the modelio paths, runs, and reads `*.eam.h0.*.nc` with netCDF4 from a conda env (`mamba create -n ema-nc -c conda-forge python=3.12 netcdf4`) or apt's `python3-netcdf4`. On AWS the command is that python's absolute path and `run_scm.py deck.txt`. Take nominal values from the built case's `atm_in`: the scripts' `user_nl_eam` sets some tuning values per version, and v3's defaults come from EAM's namelist defaults.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| BOMEX, `E3SM_SCM_scripts/run_e3sm_scm_BOMEX.csh` (https://github.com/E3SM-Project/scmlib): 15°N 300°E, start 1969-06-25, `stop_n` 1 day, SW and LW radiation off | trade-wind shallow cumulus, EAMv3 physics (CLUBB, P3 microphysics, ZM) | `clubb_c14` from `atm_in` [0.5×, 2×]; `clubb_gamma_coef` from `atm_in` [0.2, 0.4]; `clubb_c1` from `atm_in` [0.5×, 2×] **(check the names in EAM's namelist_definition for v3)** | time-mean liquid water path `TGCLDLWP` over hours 6–24 (second model: `CLDLOW`) | CLUBB parameters interact strongly; `clubb_gamma_coef` likely first; smooth to moderately rough; possible failures (CLUBB instabilities) at range extremes | 10–60 s after the build *(estimate)* | cli (python + `run_scm.py`) | regex |
| DYCOMS-II RF01, `run_e3sm_scm_DYCOMSrf01.csh` | nocturnal marine stratocumulus | same three CLUBB inputs, plus `clubb_c8` or its v3 equivalent **(unconfirmed name)** | time-mean `TGCLDLWP` | **regime changes**: the stratocumulus can thin or break up at some parameter values, giving jumps or steep regions for `nonsmooth`; strong interactions | 10–60 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — E3SM, check the machine (read-only). I want to onboard E3SM's single-column model (FSCM, scmlib case library) into EMA. Run only read-only commands and report: OS and version, CPU architecture, RAM, free disk space (at least 60 GB needed), gfortran/gcc/cmake versions, MPI, nc-config/nf-config/pnetcdf-config, perl with XML::LibXML (perl -MXML::LibXML -e1), csh, python3, and Docker. Don't install anything, and don't read .env. Recommend a route: on this Intel Mac, none that is supported (say so; a self-built Ubuntu Docker image with CIME's linux-generic machine is possible but unproven, and I prefer AWS); on Ubuntu 24.04, a native build of E3SM v3.0.2 with the linux-generic machine and mpi-serial. Say plainly that global E3SM configurations are out of scope. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — E3SM on this Intel Mac: plan only. Don't build anything. Write (to a scratch directory outside the EMA repo) a proposed Dockerfile FROM ubuntu:24.04 pinned by digest that installs the same apt packages as the AWS route (gfortran gcc g++ make cmake git perl libxml-libxml-perl python3 csh wget libnetcdf-dev libnetcdff-dev libpnetcdf-dev libopenmpi-dev openmpi-bin liblapack-dev libblas-dev) and clones E3SM v3.0.2 with --recursive and scmlib, and estimate the image size and build time. Show it to me and stop. Never install into EMA's .venv, and never read .env. Ask before any sudo, Homebrew change, or download over 1 GB. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install E3SM v3.0.2 on this AWS EC2 instance (Ubuntu 24.04). Ask before sudo, then apt-get install gfortran gcc g++ make cmake git perl libxml-libxml-perl python3 csh wget libnetcdf-dev libnetcdff-dev libpnetcdf-dev libopenmpi-dev openmpi-bin liblapack-dev libblas-dev. Clone E3SM with `git clone -b v3.0.2 --recursive https://github.com/E3SM-Project/E3SM.git ~/E3SM_code/v3.0.2` (ask first; with submodules it's over 1 GB) and `git clone https://github.com/E3SM-Project/scmlib.git ~/scmlib`. Create ~/projects/acme/cesm-inputdata and ~/projects/acme/scratch on the EBS volume. Check that `~/E3SM_code/v3.0.2/cime/scripts/query_config --machines` lists linux-generic. Never use EMA's .venv, and never read .env. Stop at the first error and report the command and output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 3 — E3SM SCM smoke test (BOMEX). Copy ~/scmlib/E3SM_SCM_scripts/run_e3sm_scm_BOMEX.csh to ~/SCM_runs/, and edit only its USER DEFINED SETTINGS: casedirectory ~/SCM_runs, code_dir ~/E3SM_code, code_tag v3.0.2, machine linux-generic, e3sm_version master, dycore SE. Show me the diff, then run it with csh. If create_newcase or the build can't find netCDF or PnetCDF, stop and report the error with a proposed fix (environment variables or a ~/.cime/config_machines.xml override) and don't apply it without my OK. Before any input-data download over 1 GB, ask. Report the build time, the run time, CaseStatus, the run directory's contents, and the h0 file's TGCLDLWP and CLDLOW time means. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare E3SM SCM BOMEX for EMA. Enter plan mode first and show me the plan. Goal: each EMA run executes the built e3sm.exe in its own run directory, without CIME. In examples/e3sm/scm_bomex/: (1) list the files e3sm.exe reads from the case run directory and the absolute paths in them; (2) snapshot them into ~/e3sm_snapshots/bomex (outside the repo); (3) write run_scm.py, which copies the snapshot in, sets clubb_c14, clubb_gamma_coef and clubb_c1 in atm_in from deck.txt (first confirm the names in EAM's namelist_definition.xml for v3.0.2 and their values in the snapshot's atm_in), rewrites diro/logfile in *_modelio.nml to ".", runs e3sm.exe (absolute path), exits non-zero unless the coupler log reports a successful end, reads *.eam.h0.*.nc with netCDF4, and prints `E3SM v3.0.2 SCM` and `EMA_OUTPUT <mean TGCLDLWP over hours 6-24, %.12e>`. Python: a conda env ema-nc (python=3.12 netcdf4 from conda-forge; ask before creating it) or /usr/bin/python3 with python3-netcdf4; its absolute path is the first element of the command. Ranges: clubb_c14 [0.5x, 2x nominal], clubb_gamma_coef [0.2, 0.4], clubb_c1 [0.5x, 2x]. timeout_s 600, env OMP_NUM_THREADS=1. Write model_cldlow.json for CLDLOW too. Check by hand that the nominal reproduces Stage 3. Then `.venv/bin/ema profile examples/e3sm/scm_bomex/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare E3SM SCM DYCOMS-RF01. Plan mode first. Run run_e3sm_scm_DYCOMSrf01.csh once with the same settings as Stage 3 (show me the diff; ask before large downloads), snapshot its run directory to ~/e3sm_snapshots/dycoms, and reuse run_scm.py in examples/e3sm/scm_dycoms/. Inputs: the same three CLUBB parameters plus one more you find in atm_in that controls CLUBB's buoyancy or dissipation (propose it, with a range of 0.5x to 2x, and tell me why). Output: mean TGCLDLWP over the last 6 hours. Check by hand that the nominal reproduces the CIME run. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first E3SM campaign. For examples/e3sm/scm_bomex/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), and curve1d on clubb_gamma_coef (n 11). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before running `.venv/bin/ema run ... -j 6`. After it runs, report: bit-identical repeats or not, morris's ranking, failed runs and where, and curve1d's shape (smooth, kinks, jumps). Suggest (don't run) the same on the DYCOMS model, where regime changes are expected. Stop and report.
```

```text
Stage 6 — E3SM SCM troubleshooting. An EMA E3SM SCM model fails. Diagnose read-only first: stdout.txt, stderr.txt, atm.log*, e3sm.log*, cpl.log* in the run directory (or in the snapshot path, which means the modelio rewrite failed). Check for: a namelist read error in atm_in (value format, a variable name that doesn't exist in v3), missing input files (absolute paths into ~/projects/acme/cesm-inputdata), a build made with MPI instead of mpi-serial, a CLUBB failure at extreme parameters (a failure region), the netCDF python missing, and oversubscribed threads. Report the cause and a proposed fix. Ask before changing the build, the snapshot, the driver or model.json.
```

**Gotchas and sources.**
- License: 3-Clause BSD (with separately licensed pieces listed in `LICENSE`).
- Parallelism: the SCM scripts force `mpi-serial`, a single task, and a single thread. Keep it so.
- Determinism: bit-reproducible serially on one build. The output is rough in parameters where cloud regimes change.
- Run time: build 20–60 min *(estimate)*, then tens of seconds per 1-day SCM run *(estimate)*. BOMEX turns radiation off, which is cheaper.
- Version pitfalls: scmlib's scripts follow E3SM `master`, and claim to work with v3 releases. Namelist names and defaults (for example P3 microphysics instead of MG2 in v3) differ from CESM's CAM, so don't copy CAM parameter names blindly. The input-data server and download size are **(unconfirmed)**.
- Sources: https://e3sm.org, https://github.com/E3SM-Project/E3SM, https://github.com/E3SM-Project/E3SM/releases, https://github.com/E3SM-Project/E3SM/blob/master/LICENSE, https://github.com/E3SM-Project/E3SM/blob/v3.0.2/cime_config/machines/config_machines.xml, https://github.com/E3SM-Project/scmlib, https://github.com/E3SM-Project/scmlib/tree/master/E3SM_SCM_scripts, https://github.com/E3SM-Project/scmlib/wiki/Running-the-E3SM-Single-Column-Model, https://raw.githubusercontent.com/E3SM-Project/scmlib/master/E3SM_SCM_scripts/run_e3sm_scm_BOMEX.csh, https://gmd.copernicus.org/articles/13/4443/2020/, https://docs.e3sm.org/E3SM/EAM/user-guide/, https://e3sm.atlassian.net/wiki/spaces/DOC/pages/2488401938, https://hub.docker.com/u/e3sm

---

#### ICON (ICOsahedral Nonhydrostatic model)

**What it is.** ICON is the weather and climate model of DWD, MPI-M, DKRZ, KIT and C2SM, on icosahedral (or planar torus) grids. It is Fortran with MPI, OpenMP and GPU support. It has been open source since January 2024 under the **BSD-3-Clause** license. Current release **ICON 2026.04 (April 2026)**, preceded by 2025.10-2. Releases come twice a year, in April and October. Get it with `git clone --recursive https://gitlab.dkrz.de/icon/icon-model.git`: the docs warn that "downloading the tarball ... will result in an error during configuration". The release tag name is **(unconfirmed)**, since the GitLab server refused connections during this research. Build with a configure wrapper (`config/generic/gcc` on generic Linux) and `make`. Experiments are either `run/exp.*` templates turned into scripts by `./make_runscripts <name>` (the documented test is `atm_tracer_Hadley`), or `.config` files for `mkexp` (for example `run/examples/bubble.config`). Grids come from http://icon-downloads.mpimet.mpg.de/. **Honest fit:** global ICON doesn't fit EMA. DKRZ's easy.gems page documents a small **bubble** case on a doubly periodic torus: two stratified layers, a Gaussian warm and moist perturbation, 70 levels, about 20 km deep, AES physics. The page says "a 2hr simulation takes 11s on a mac". That fits. An aquaplanet at R02B04 (about 160 km) is a possible second example for AWS.

**Install on an Intel Mac.** ICON documents macOS builds with MacPorts or Homebrew, tested on "macOS Sequoia 15.3" (Intel or Apple Silicon isn't stated). Homebrew is ruled out on Intel, and MacPorts is outside this document's routes. **Recommended: the official development container `iconmodel/icon-dev`**. It holds the compilers and libraries, not ICON itself. Tags are `gcc-ubuntu-24.04`, `gcc` and `latest`, **amd64 only**, updated 2026-09-20 (so native on an Intel Mac). Build ICON inside it from a mounted source tree:
```bash
docker pull iconmodel/icon-dev:gcc-ubuntu-24.04
docker buildx imagetools inspect iconmodel/icon-dev:gcc-ubuntu-24.04     # record the digest
git clone --recursive https://gitlab.dkrz.de/icon/icon-model.git ~/icon/icon   # then check out the 2026.04 release tag
docker run -it --rm -v ~/icon/icon:/home/icon/icon -v ~/icon/pool:/home/icon/pool iconmodel/icon-dev@sha256:<digest>
# inside:
cd ~/icon && ./config/generic/gcc && make -j4       # 30–60 min *(estimate)*
./make_runscripts atm_tracer_Hadley && cd run && ./exp.atm_tracer_Hadley.run   # smoke test
```
The run commands are from ICON's "Supported environments" page, and the `./config/generic/gcc` wrapper is from its Docker example. Whether `atm_tracer_Hadley` needs a grid from the pool is **(unconfirmed)**.
Sources: https://docs.icon-model.org/documentation/buildrun/buildrun_environments.html, https://hub.docker.com/r/iconmodel/icon-dev, https://docs.icon-model.org/getting_started/getting_started.html, https://docs.icon-model.org/release/release.html

**Install on AWS (Ubuntu 24.04 EC2).** Native, following ICON's own Ubuntu 24.04 instructions (tested on "Ubuntu Noble Numbat 24.04.2 LTS"):
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake python3 gcc gfortran libopenmpi-dev libhdf5-dev libnetcdf-dev \
  libnetcdff-dev libeccodes-dev libblas-dev liblapack-dev libfyaml-dev libxml2-dev git
sudo update-alternatives --set mpi /usr/bin/mpicc.openmpi
sudo update-alternatives --set mpirun /usr/bin/mpirun.openmpi
git clone --recursive https://gitlab.dkrz.de/icon/icon-model.git ~/icon && cd ~/icon   # check out the 2026.04 tag
./config/generic/gcc && make -j8
./make_runscripts atm_tracer_Hadley && (cd run && ./exp.atm_tracer_Hadley.run)
```
Fallback: the `iconmodel/icon-dev` container, as on the Mac. `c7i.2xlarge` for the bubble, and `c7i.8xlarge` for an aquaplanet campaign. For the `mkexp` route, install `python3-six python3-jinja2`, which `mkexp` needs.
Sources: https://docs.icon-model.org/documentation/buildrun/buildrun_environments.html, https://docs.icon-model.org/documentation/buildrun/buildrun_running.html, https://www.icon-model.org/

**Preparing the examples for EMA.** Run the experiment once through its generated script, then keep what it produced:
- the namelists (`icon_master.namelist` and `NAMELIST_<exp>_atm`);
- the list of linked files: grid, external parameters, and data such as radiation tables.

The EMA model is:
- `namelist.template`, a `string.Template` of `NAMELIST_<exp>_atm` with the inputs as `$name`. Check the namelist for literal `$`; ICON's output name patterns use `<...>`, not `$`;
- `icon_master.namelist` as a static file;
- a driver `run_icon.py`, which links the grid and data by absolute path, runs the `icon` binary with one MPI rank (`mpirun -n 1` or directly **(unconfirmed which works)**), reads the output netCDF (`*_atm_2d_ml_*.nc`) with netCDF4, and prints `EMA_OUTPUT`.

On the Mac, the driver runs inside `iconmodel/icon-dev`, which needs `python3-netcdf4` **(unconfirmed that the image has it; else add a thin image on top)**.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Bubble on a torus, `run/examples/bubble.config` via `mkexp` (described at https://easy.gems.dkrz.de/simulations/ICON/bubble.html) | moist warm bubble in two stratified layers, AES physics (microphysics, vertical diffusion, radiation; each can be turned off with a void `dt`), 70 levels, 2 h | `ape_sst_val` (surface temperature, `nh_testcase_nml`) nominal from the config [nominal − 4, nominal + 4] K; `aes_bubble_config%t0` (lower-layer temperature, `aes_bubble_nml`) nominal from the config [± 4 K]; the constant relative humidity (namelist name **(unconfirmed)**) nominal [0.5, 0.95] | domain-mean accumulated precipitation after 2 h (from `pr` in `atm_2d_ml` **(unconfirmed name)**; second model: domain-max vertical velocity `wa`) | **threshold**: below some humidity or surface-temperature excess the bubble doesn't rain (a zero plateau and a jump); strong humidity × SST interaction; roughness from convection; deterministic serially | about 11 s "on a mac" per easy.gems; 10–30 s with EMA overhead *(estimate)* | cli (docker or env python + `run_icon.py`) | regex |
| Aquaplanet at R02B04 (the name of the experiment template in `run/` is **(unconfirmed)**; the `exclaim_ape_R02B04` experiments are cited by icon4py) | global aquaplanet with NWP physics, about 160 km grid | `tune_entrorg` (entrainment, `nwp_tuning_nml`) nominal from the namelist [0.5×, 1.5×]; `tune_zceff_min` nominal [0.5×, 1.5×]; the aquaplanet SST case or a uniform SST offset **(unconfirmed parameter names)** | global-mean precipitation or OLR over days 2–5 | global means that are nearly smooth; entrainment dominant; runs are deterministic, but chaotic weather makes short-average outputs rough in the inputs, so average over as many days as the budget allows | 5–20 min per 5 days on 8 cores *(estimate)*: AWS only | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — ICON, check the machine (read-only). I want to onboard ICON 2026.04's small torus "bubble" experiment into EMA. Run only read-only commands and report: OS and version, CPU architecture, RAM, free disk space (at least 40 GB), Docker (docker version, daemon running, Docker Desktop's memory and disk limits), any iconmodel images, git, and on Linux: gfortran, MPI, nc-config/nf-config, eccodes. Also check that https://gitlab.dkrz.de is reachable (git ls-remote --tags https://gitlab.dkrz.de/icon/icon-model.git | tail) and report the 2026.04 tag name. Don't install anything, and don't read .env. Recommend a route: on the Intel Mac, build ICON inside iconmodel/icon-dev:gcc-ubuntu-24.04 (amd64) pinned by digest; on Ubuntu 24.04, a native build with ICON's documented apt packages and ./config/generic/gcc. Say plainly that global ICON runs are out of scope for EMA on a laptop. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — build ICON 2026.04 inside Docker on this Intel Mac. Ask me before pulling iconmodel/icon-dev:gcc-ubuntu-24.04 (check its size first; the repository holds about 22 GB across tags) and before cloning ICON (with submodules, possibly over 1 GB). Clone with `git clone --recursive https://gitlab.dkrz.de/icon/icon-model.git ~/icon/icon` and check out the 2026.04 release tag (not a tarball). Record the image digest. In the container (docker run -it --rm -v ~/icon/icon:/home/icon/icon -v ~/icon/pool:/home/icon/pool iconmodel/icon-dev@sha256:<digest>), run ./config/generic/gcc and make -j4, and report the bin/icon path and the build time. Never install into EMA's .venv, and never read .env. Ask before any sudo, Homebrew change, or Docker settings change. Stop at the first error and report the command and output; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — build ICON 2026.04 on this AWS EC2 instance (Ubuntu 24.04). Ask before sudo, then install ICON's documented packages: build-essential cmake python3 gcc gfortran libopenmpi-dev libhdf5-dev libnetcdf-dev libnetcdff-dev libeccodes-dev libblas-dev liblapack-dev libfyaml-dev libxml2-dev, plus python3-six python3-jinja2 python3-netcdf4, and set the mpi and mpirun alternatives to openmpi (ask). Clone ICON with --recursive into ~/icon (ask first if over 1 GB), check out the 2026.04 tag, run ./config/generic/gcc and make -j8. Never use EMA's .venv, and never read .env. If configure fails, report and propose (don't run) the iconmodel/icon-dev container route. Report the bin/icon path and build time. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — ICON smoke test. First the documented test: `./make_runscripts atm_tracer_Hadley` and run run/exp.atm_tracer_Hadley.run (in the container on the Mac, natively on AWS); if it needs a grid or data it can't find, stop and report what and where from (don't download over 1 GB without asking). Then the bubble: copy run/examples/bubble.config, generate the experiment with utils/mkexp/mkexp (it needs six and jinja2), and run it without a batch system. Time both. Report: the experiment directory's files, the namelist files and the linked grid/data files (absolute paths), the output netCDF names and variables (ncdump -h), and the wall time of the 2-hour bubble. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the ICON bubble for EMA. Enter plan mode first and show me the plan. Put it in examples/icon/bubble/. From Stage 3's experiment: namelist.template = the atmosphere namelist with $ape_sst_val, $bubble_t0 (aes_bubble_config%t0) and the constant relative humidity (find its namelist name and tell me) substituted; check for any literal `$` and escape it as `$$`. icon_master.namelist as a static file. run_icon.py, a static driver, links the grid and data files by absolute path, runs the icon binary with one rank (try without mpirun first, then `mpirun -n 1`), exits non-zero unless the log reports a normal end, reads the atm_2d_ml output with netCDF4, and prints `ICON 2026.04` and `EMA_OUTPUT <domain-mean accumulated precipitation at 2 h, %.12e>` (find the precipitation variable's name and units). Inputs: nominals from the config, ranges ±4 K for the two temperatures and [0.5, 0.95] for humidity. Mac command: docker run --rm --user <uid>:<gid> -v $EMA_WORKDIR:/work -v ~/icon:/home/icon -w /work iconmodel/icon-dev@sha256:<digest> python3 run_icon.py deck.txt (check python3 and netCDF4 exist in the image; if not, propose a two-line Dockerfile on top and ask). AWS: /usr/bin/python3 and run_icon.py in model_aws.json. env OMP_NUM_THREADS=1, timeout_s 300. Write model_wmax.json too. Check by hand that the nominal reproduces Stage 3. Then `.venv/bin/ema profile examples/icon/bubble/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — ICON aquaplanet, feasibility only (AWS). Plan mode first; don't build a model yet. List the aquaplanet experiment templates in run/ (names containing ape or aquaplanet) and in run/examples, and what grids and data each needs (and their sizes). Run the smallest (R02B04 if available) for one simulated day with 8 MPI ranks and report the wall time and the namelist names of tune_entrorg, tune_zceff_min and the SST setting. Estimate the cost of a 100-run campaign on a c7i.8xlarge. Stop and report; don't prepare an EMA model until I decide.
```

```text
Stage 5 — first ICON campaign. For examples/icon/bubble/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on the relative humidity (n 15), and morris (n_traj 8). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before running `.venv/bin/ema run ... -j 4`. After it runs, report: whether repeats are bit-identical, where curve1d finds the onset of precipitation (a plateau at zero and then a jump or kink), morris's ranking and interaction signal, and failed runs. Suggest (don't run) surface2d on (humidity, SST). Stop and report.
```

```text
Stage 6 — ICON troubleshooting. An EMA ICON model fails. Diagnose read-only first: stdout.txt, stderr.txt and ICON's log in the run directory. Check for: a namelist read error (a substituted value's format, or a variable in the wrong group), a grid or data file not found (absolute links; the pool not mounted in Docker), MPI start-up problems (running without mpirun vs `mpirun -n 1`; Open MPI refusing to run as root in Docker, so use --user), an output file with a different name pattern than the driver expects, CFL or negative-mass aborts at extreme inputs (a failure region), root-owned files, and OMP_NUM_THREADS unset (an OpenMP build then uses every core). Report the cause and a proposed fix. Ask before changing the image, the build, the driver or model.json.
```

**Gotchas and sources.**
- License: BSD-3-Clause since 2024. Some external libraries bundled as submodules have their own licenses.
- Parallelism: build with OpenMP if you like, but run with `OMP_NUM_THREADS=1` and one MPI rank per EMA run. Results with a different rank count differ in the last digits.
- Determinism: the same binary, rank count and inputs give identical output. Convection makes the bubble's precipitation rough, with a threshold.
- Run time: the bubble takes seconds (11 s for 2 h "on a mac", per DKRZ). An aquaplanet takes minutes to hours: AWS only, and probably not an EMA campaign.
- Versions: clone, don't download the tarball. Record `ICON 2026.04` in the description, and pin the container by digest. The generated run scripts assume HPC paths: run them without a batch system on a workstation, as the docs describe.
- Sources: https://www.icon-model.org/, https://www.icon-model.org/icon_model/getting_started, https://docs.icon-model.org/, https://docs.icon-model.org/getting_started/getting_started.html, https://docs.icon-model.org/release/release.html, https://docs.icon-model.org/documentation/buildrun/buildrun_overview.html, https://docs.icon-model.org/documentation/buildrun/buildrun_environments.html, https://docs.icon-model.org/documentation/buildrun/buildrun_running.html, https://gitlab.dkrz.de/icon/icon-model, https://hub.docker.com/r/iconmodel/icon-dev, https://easy.gems.dkrz.de/simulations/ICON/bubble.html, https://icon.gitlab-pages.dkrz.de/icon-nwp/documentation/tools/tools_mkexp.html, https://wiki.mpimet.mpg.de/doku.php?id=models%3Apot-pourri%3Aspec_configs%3Arce_icon_lem_torus, http://icon-downloads.mpimet.mpg.de/

---

### 4.9 Machine-learned weather and climate emulators: ACE, NeuralGCM, ClimaX

Desk research, checked 2026-09-24. Nothing here was installed or run. Every time per run is an *(estimate)* for `ema profile` to measure. Facts common to the group:

- **These are neural networks, not PDE solvers.** Each one is already a smooth surrogate of a physics model or of reanalysis data. EMA has a different job here: probe the emulator's structure and compare it with the physics it claims to learn. Examples: does global-mean surface temperature rise monotonically and nearly linearly with a uniform SST offset? Is the response to a small SST patch linear in its amplitude, as Green's-function studies assume? Does the emulator break down (jumps, NaN, runaway values, which EMA records as failed runs) when an input leaves the training distribution, such as a large CO2 increase for ACE2-ERA5? `linear_coeffs`, `curve1d`, `nonsmooth` and `surrogate_check` answer these directly.
- **Inputs are perturbations, not physical parameters.** The weights are fixed. What EMA can vary is what the emulator is fed: forcing offsets (SST, CO2), initial-condition perturbations, the choice of start date, and the rollout length. Rollout length is an integer number of steps, so as an input it makes a staircase. Vary it only with `curve1d`, or keep it fixed.
- **Intel Mac: pip wheels are gone, conda-forge still works.** PyTorch's last macOS x86_64 wheel on PyPI is 2.2.2 (March 2024). JAX's last macOS x86_64 `jaxlib` wheel on PyPI is 0.4.38 (December 2024). conda-forge still builds both for `osx-64`: `pytorch` 2.13.0 (CPU builds) and `jaxlib` 0.10.2 (checked on anaconda.org, 2026-09-24). Every Intel-Mac route below is therefore Miniforge plus conda-forge, with pip used only for pure-Python packages that have no conda-forge build (`--no-deps`).
- **CPU versus GPU.** All three are built for GPUs. ACE's docs say that "while inference can be performed without a GPU, it may be very slow". NeuralGCM's demo recommends a GPU or TPU runtime. A laptop CPU can do a *short* rollout at the coarsest resolution in minutes, not seconds. That is enough for `repeat`, `curve1d` and a small `morris`, but not for `sobol`. A GPU instance is needed for anything longer.
- **AWS instance.** For CPU work (NeuralGCM at 2.8°, short ACE rollouts), use a `c7i.4xlarge` (16 vCPU, 32 GB), because model weights and a 1° state need memory. For GPU work, use a `g6.xlarge` (1 NVIDIA L4 with 24 GB, 4 vCPU, 16 GB RAM) or a `g5.xlarge` (1 NVIDIA A10G with 24 GB). The ACE workshop notebooks run on Colab's free T4 (16 GB), so 24 GB should be ample for inference *(estimate)*. Start from the AWS **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)**, which ships the NVIDIA driver and CUDA. Check GPU prices on the AWS pricing page **(unconfirmed; prices vary by region, and GPU instances cost several times a `c7i` of similar size)**. Run EMA with `-j 1` on a single-GPU instance: parallel runs would compete for one GPU's memory.
- **Per-run start-up cost.** An EMA command-line run is a fresh process, so every run loads the weights again: 1.8 GB for ACE2, 45–130 MB for NeuralGCM. It also recompiles JAX functions for NeuralGCM. That overhead can exceed the rollout itself. A persistent isolated Python model would avoid it, but EMA's isolated children run EMA's own interpreter, and these packages must not be installed into EMA's `.venv`. So the command-line route is the only one today. Measure the overhead with `ema profile` (the phase breakdown), and see "What EMA would need" in section 5.
- **Data sizes.** The weights are small to moderate. Initial-condition and forcing data are large, and the full training archives are terabytes on requester-pays or public cloud buckets. The prompts below download only one initial condition and one year of forcing, and they ask before any download over 1 GB.
- **EMA wiring.** Each package gets its own conda env (`ema-ace`, `ema-neuralgcm`, `ema-climax`), never EMA's `.venv`. The command is the env's absolute `python` followed by a driver `run.py` in the model directory. The driver reads a key = value deck (as in `examples/cantera/`), writes the package's config, runs the rollout, reduces the output to a cos(latitude)-weighted global mean, and prints one line. The model files (checkpoint, initial conditions, forcing) live outside the repo, in `~/ema-data/<pkg>/`, and are named by absolute path in the deck or env. They are therefore **not** in EMA's version hash, so the `model.json` description must record the checkpoint name and its SHA-256.

---

#### ACE (Ai2 Climate Emulator, package `fme`)

**What it is.** ACE is a family of autoregressive neural emulators of the global atmosphere from Ai2, based on a spherical Fourier neural operator (via `torch-harmonics`). It steps every 6 hours on a 1° grid and can run from days to centuries. Language: Python (PyTorch). License: Apache-2.0 (code and the ACE2 weights on Hugging Face). The package is `fme` ("full model emulation"): the current PyPI release is **fme 2026.5.1 (2026-05-11)**. GitHub already has a later tag, **v2026.8.0 (2026-08-10)**, which is not on PyPI **(unconfirmed why; pin 2026.5.1)**. `fme` requires Python ≥ 3.11 and `torch>=2.4.0`, and pins `torch-harmonics==0.8.0` (sdist only on PyPI).
Checkpoints are in the Hugging Face collection `allenai/ace`. They include `allenai/ACE2-ERA5` (trained on ERA5), `allenai/ACE2-SOM` (ACE2 coupled to a slab ocean, trained at 1×, 2× and 4× CO2), `ACE-climSST`, `ACE2-EAMv3`, `ACE2-SHiELD`, `HiRO-ACE` and others.
Examples: the quickstart at https://ai2-climate-emulator.readthedocs.io/en/latest/quickstart.html, and five workshop notebooks at https://ai2cm.github.io/ace/: ACE2-ERA5 basic, ACE2-ERA5 advanced ("modified conditions and custom diagnostics"), ACE2-SOM, SamudrACE, and HiRO-ACE. They are Colab notebooks built for a T4 GPU. The HF model repos each ship an `inference_config.yaml`, which is the template for EMA.
**Fit.** An EMA run is one rollout from one initial condition. The inputs are perturbations that `fme` supports natively: `forcing_loader.perturbations.sst` offers a uniform `constant` SST offset over ocean, and `greens_function` sinusoidal SST patches with `amplitude`, `lat_center`, `lon_center`, `lat_width` and `lon_width` (source: `fme/ace/data_loading/perturbation.py`). The output is a global mean read from `autoregressive_predictions.nc`. The awkward parts:
- The data are large: the checkpoint is 1.8 GB, one initial condition 118 MB, and one year of forcing 555 MB.
- CPU inference is slow.
- The ACE2-ERA5 model card itself warns that "the individual sensitivities to changing sea surface temperature and CO2 are not entirely realistic" and that the model is "not expected to generalize accurately for large perturbations of certain inputs (e.g. doubling of CO2)". That is exactly what EMA can map.

**Install on an Intel Mac.** `pip install fme` fails on an Intel Mac, because PyPI has no macOS x86_64 torch ≥ 2.3. Install torch and the compiled dependencies from conda-forge, then `fme` itself with `--no-deps`.
1. Install Miniforge if there's no conda (osx-64 installer, needs macOS ≥ 11):
   ```bash
   curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
   bash Miniforge3-MacOSX-x86_64.sh -b -p "$HOME/miniforge3"
   ```
2. Create the env from conda-forge. `pytorch` 2.13.0 has `cpu_generic` osx-64 builds for Python 3.10–3.13, and `torch-harmonics` 0.8.0 has an osx-64 build. The rest are noarch or have osx-64 builds:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-ace -c conda-forge python=3.12 "pytorch>=2.4" torch-harmonics=0.8.0 \
       cartopy dacite "einops>=0.8.1" gcsfs h5netcdf h5py imageio matplotlib moviepy netcdf4 numpy \
       "omegaconf>=2.1.0" pandas plotly s3fs tensorly tensorly-torch wandb xarray "zarr>=3" huggingface_hub
   ~/miniforge3/envs/ema-ace/bin/python -m pip install --no-deps fme==2026.5.1
   ```
   Whether conda-forge's `torch-harmonics` 0.8.0 build solves together with a recent `pytorch` is **(unconfirmed)**. If the solve fails, let the solver choose the pytorch version (drop `>=2.4`) and report which one it picked. `fme` needs ≥ 2.4.
3. Download ACE2-ERA5 weights and data (about 1.8 GB + 118 MB + 555 MB; ask first):
   ```bash
   mkdir -p ~/ema-data/ace2-era5 && cd ~/ema-data/ace2-era5
   ~/miniforge3/envs/ema-ace/bin/hf download allenai/ACE2-ERA5 ace2_era5_ckpt.tar inference_config.yaml \
       initial_conditions/ic_2020.nc forcing_data/forcing_2020.nc --local-dir .
   shasum -a 256 ace2_era5_ckpt.tar
   ```
   The CLI command name (`hf` or `huggingface-cli`) depends on the `huggingface_hub` version **(unconfirmed which the env gets)**.
4. Check:
   ```bash
   ~/miniforge3/envs/ema-ace/bin/python -c "import torch, fme, torch_harmonics; print(torch.__version__, fme.__version__, torch.cuda.is_available())"
   ```
   `fme.__version__` may not exist **(unconfirmed)**. `pip show fme` works either way.

Known problems:
- Apple's MPS backend (`FME_USE_MPS=1`) is for Apple GPUs and doesn't apply on an Intel Mac. Leave it unset.
- `wandb` is imported but not used when `log_to_wandb: false`.
- The DataLoader's `num_data_workers: 4` from the HF config spawns processes. Set it to 0 under EMA, which runs runs in parallel itself.

Sources: https://pypi.org/project/fme/ (2026.5.1, requires_dist), https://pypi.org/project/torch/#files (no macOS x86_64 wheel after 2.2.2), https://anaconda.org/conda-forge/pytorch, https://anaconda.org/conda-forge/torch-harmonics, https://huggingface.co/allenai/ACE2-ERA5, https://ai2-climate-emulator.readthedocs.io/en/latest/quickstart.html

**Install on AWS (Ubuntu 24.04 EC2).** Use a `g6.xlarge` or `g5.xlarge` with the Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04), and 200 GB of gp3 for the data. On Linux the PyPI torch wheels include CUDA, so pip works:
1. Check the GPU: `nvidia-smi`.
2. Install Miniforge (Linux x86_64 installer), then:
   ```bash
   mamba create -n ema-ace -c conda-forge python=3.12 pip
   ~/miniforge3/envs/ema-ace/bin/python -m pip install fme==2026.5.1
   ~/miniforge3/envs/ema-ace/bin/python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
   ```
   Expect `True`. If the torch wheel's CUDA is newer than the AMI's driver, install the torch build matching the driver's CUDA from https://pytorch.org/get-started/locally/ **(unconfirmed which CUDA the default wheel of the resolved torch uses)**.
3. Download data as on the Mac, plus `initial_conditions/1xCO2/ic.nc`, one `forcing_data/1xCO2/forcing_2032.nc` (945 MB) and `ace2_som_ckpt.tar` from `allenai/ACE2-SOM` for the third example.
4. CPU-only fallback: the same env on a `c7i.4xlarge`. Expect CPU speeds like the laptop's, times the core ratio.

There is no official ACE Docker image **(unconfirmed; none found)**.
Sources: https://github.com/ai2cm/ace, https://huggingface.co/allenai/ACE2-SOM, https://docs.aws.amazon.com/dlami/latest/devguide/aws-deep-learning-x86-base-gpu-ami-ubuntu-24-04.html

**Preparing the examples for EMA.** Use a driver plus a key = value deck, as in `examples/cantera/`. `run.py`:
- reads `ace.deck`;
- loads the HF `inference_config.yaml` from the model directory (a static file) and sets its fields: `experiment_dir: "."`, `checkpoint_path` and the data paths (absolute, under `~/ema-data/`, from the deck or an env variable), `n_forward_steps` (the deck value rounded to an integer), `forward_steps_in_memory` (≤ `n_forward_steps`), `forcing_loader.num_data_workers: 0`, `logging.log_to_wandb: false`, `data_writer.names: ["TMP2m", "PRATEsfc"]`, and `forcing_loader.perturbations: {sst: [{type: constant, config: {amplitude: <sst_offset>}}]}` (or a `greens_function` entry);
- runs `python -m fme.ace.inference config.yaml` as a subprocess with the same interpreter (`sys.executable`);
- opens `autoregressive_predictions.nc` with xarray, averages the last K days of the chosen variable with cos(latitude) weights, and prints `EMA_OUTPUT <value:.12e>` together with the `fme` version and the checkpoint's SHA-256.

YAML has no `$`, but since the driver writes it, there are no templates to escape. For CO2 (ACE2-SOM), the driver copies the forcing year file into the run directory and multiplies its `global_mean_co2` variable (ppm) by the input factor with xarray. That copy is 945 MB per run, so write it to the run directory and delete it at the end, or use a zarr view **(to design in Stage 4.3)**.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| ACE2-ERA5, HF `inference_config.yaml` with `initial_conditions/ic_2020.nc` (start 2020-01-01T00) and `forcing_data/forcing_2020.nc` (https://huggingface.co/allenai/ACE2-ERA5) | emulated global atmosphere, 1°, 6-h steps, prescribed SST and sea ice | `sst_offset` 0 K [−2, 2] (uniform `constant` SST perturbation over ocean); `days` 10 [5, 30] (rollout length; `n_forward_steps` = 4·days, an integer) | global-mean `TMP2m` averaged over the last 5 days of the rollout | monotone increasing and close to linear in `sst_offset`: the land-inclusive global mean rises by a bit less than the ocean offset *(expected, not checked)*. `days` gives a staircase plus weather noise from the start date. Deterministic, so `repeat` should agree to round-off, or show tiny CPU-thread jitter | CPU: 2–10 s per 6-h step, so 1–5 min for 10 days, plus 10–30 s to load the checkpoint *(estimate)*. GPU (L4): 5–20 s per run *(estimate)* | cli (env python + `run.py`) | regex on stdout |
| ACE2-ERA5 Green's-function patch: `forcing_loader.perturbations.sst: [{type: greens_function, ...}]` (fields from `fme/ace/data_loading/perturbation.py`; method as in https://arxiv.org/abs/2505.08742) | same, with a sinusoidal SST patch | `amplitude` 1 K [−3, 3]; `lat_center` 0° [−30, 30]; `lon_center` 180° [120, 280]; widths fixed at 20° × 40°; 30-day rollout | global-mean `TMP2m` (or `PRATEsfc`) over days 16–30 | nearly linear in `amplitude` for small patches (the Green's-function assumption; `linear_coeffs` R² tests it), with sign symmetry breaking at large amplitude. Strong dependence on location (the warm-pool "pattern effect"), so amplitude × location interaction in `sobol` (response ≈ amplitude × G(lat, lon)). `lon_center` near the dateline versus the east Pacific should matter most | CPU: 4–20 min *(estimate)*: marginal on a laptop. GPU: 20–60 s *(estimate)* | cli | regex |
| ACE2-SOM with CO2 scaled: HF `allenai/ACE2-SOM`, `initial_conditions/1xCO2/ic.nc`, `forcing_data/1xCO2/forcing_2032.nc` × a factor on `global_mean_co2` | ACE2 coupled to a slab ocean, trained at 1×, 2× and 4× CO2 | `co2_factor` 1 [1, 4] (log); rollout fixed at 2 years (`n_repeats` on the forcing if needed) | global-mean `TMP2m` over the last year | close to linear in ln(CO2) (the logarithmic forcing law), so with `scale: log` `linear_coeffs` should find a good linear fit. Too-fast adjustment (the model card says so). Possible **jumps** from the model card's "abrupt regime shifts in stratospheric temperature and moisture", for `nonsmooth` and `curve1d` to find | **AWS GPU only**: 2 years = 2,920 steps, 5–30 min per run on an L4 *(estimate)*, hours on CPU | cli | regex |

**Claude Code prompts.**

```text
Stage 1 (ACE, read-only check). I want to run the Ai2 Climate Emulator (fme 2026.5.1, ACE2-ERA5 weights) as an EMA command-line model. Read-only: report OS and version, CPU architecture (uname -m), RAM (sysctl hw.memsize or free -g), free disk in $HOME, whether Miniforge/conda/mamba exist and where, any existing env named ema-ace, whether an NVIDIA GPU exists (nvidia-smi), Docker, and Homebrew's version. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, a conda-forge env (pytorch CPU build + torch-harmonics=0.8.0 from conda-forge, then pip install --no-deps fme==2026.5.1), because PyPI has no Intel-Mac torch newer than 2.2.2. On Ubuntu with a GPU, a conda env with pip install fme==2026.5.1. Say whether this machine has the memory (≥ 16 GB) and the disk (≥ 5 GB) for ACE2-ERA5 inference. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (ACE, install on the Intel Mac). Create a conda env ema-ace from conda-forge only (Miniforge; never the defaults channel, never EMA's .venv, and never read .env): mamba create -n ema-ace -c conda-forge python=3.12 "pytorch>=2.4" torch-harmonics=0.8.0 cartopy dacite "einops>=0.8.1" gcsfs h5netcdf h5py imageio matplotlib moviepy netcdf4 numpy "omegaconf>=2.1.0" pandas plotly s3fs tensorly tensorly-torch wandb xarray "zarr>=3" huggingface_hub. Then <env>/bin/python -m pip install --no-deps fme==2026.5.1. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. If the solve fails, show me the conflict and propose one change; don't improvise. Check: import torch, torch_harmonics, fme; print torch's version and pip show fme. Then, after asking me (it's about 2.5 GB), download from Hugging Face allenai/ACE2-ERA5 into ~/ema-data/ace2-era5/: ace2_era5_ckpt.tar, inference_config.yaml, initial_conditions/ic_2020.nc, forcing_data/forcing_2020.nc. Record the checkpoint's SHA-256 in ~/ema-data/ace2-era5/SHA256. Report the env's absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b (ACE, install on AWS; Ubuntu 24.04, g6.xlarge or g5.xlarge with the Deep Learning Base OSS Nvidia Driver AMI; I'm ssh'd in). Check nvidia-smi first; if there's no GPU, stop and tell me. Install Miniforge (ask first), create env ema-ace (python=3.12 pip) from conda-forge, and pip install fme==2026.5.1 into it (never into EMA's .venv, and never read .env). Check torch.cuda.is_available() is True. If False, report torch's CUDA version and the driver's (nvidia-smi) and propose, without running it, the matching torch install from pytorch.org. Ask before any sudo and before any download over 1 GB. Then download the same ACE2-ERA5 files as on the Mac into ~/ema-data/ace2-era5/, and, after asking me (about 2.8 GB), allenai/ACE2-SOM's ace2_som_ckpt.tar, inference_config.yaml, initial_conditions/1xCO2/ic.nc and forcing_data/1xCO2/forcing_2032.nc into ~/ema-data/ace2-som/. Record SHA-256s. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 (ACE smoke test). In a scratch directory outside the EMA repo, copy ~/ema-data/ace2-era5/inference_config.yaml and edit the copy: experiment_dir ./out, checkpoint_path, initial_condition.path and forcing_loader.dataset.data_path to the absolute paths under ~/ema-data/ace2-era5/, n_forward_steps 8 (2 days), forward_steps_in_memory 8, num_data_workers 0, log_to_wandb false. Run `<ema-ace python> -m fme.ace.inference config.yaml` with OMP_NUM_THREADS unset, and time it. Then run it again with n_forward_steps 40. Report: both wall times, the time per step (the difference divided by 32), the time to load the checkpoint, peak memory (/usr/bin/time -l on macOS, -v on Linux), the files written to ./out, and the variables and dimensions of autoregressive_predictions.nc (ncdump -h or xarray). Don't touch EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (ACE, prepare the uniform-SST example). Plan mode first; show me the plan. Create examples/ace/sst_offset/ following docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/ (deck + driver + regex on stdout). Files: ace.template (key = value deck: sst_offset = $sst_offset, days = $days), a static base.yaml copied from the HF inference_config.yaml, and run.py, which: reads the deck; writes config.yaml into the run directory with experiment_dir ".", n_forward_steps = 4*round(days), forward_steps_in_memory = min(40, that), num_data_workers 0, log_to_wandb false, data_writer.names ["TMP2m"], and forcing_loader.perturbations = {sst: [{type: constant, config: {amplitude: sst_offset}}]}; takes the data paths from the env variable ACE_DATA (absolute, ~/ema-data/ace2-era5); runs sys.executable -m fme.ace.inference config.yaml; computes the cos(lat)-weighted global mean of TMP2m over the last 20 steps; prints "EMA_OUTPUT %.12e"; also prints the fme version and the checkpoint's SHA-256; and deletes autoregressive_predictions.nc afterwards if it's over 100 MB. Inputs: sst_offset 0 [-2, 2], days 10 [5, 30]. model.json: command = [the ema-ace env's absolute python, "run.py"]; env OMP_NUM_THREADS=4 on the Mac (say why), ACE_DATA; timeout_s = 4 × the Stage 3 estimate for 30 days. Hand check: sst_offset 0 vs +1 at days 10; the second must be warmer. Then `ema profile examples/ace/sst_offset/model.json -n 3` and report time per run and its phase breakdown. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (ACE, prepare the Green's-function patch example). Plan mode first. Create examples/ace/sst_patch/ by the pattern of examples/ace/sst_offset/, sharing its run.py logic (copy it; EMA hashes files in the model directory). Perturbation: forcing_loader.perturbations = {sst: [{type: greens_function, config: {amplitude, lat_center, lon_center, lat_width: 20, lon_width: 40}}]}. Before writing, read fme/ace/data_loading/perturbation.py in the ema-ace env to confirm these field names and that lon is in [0, 360). Inputs: amplitude 1 [-3, 3], lat_center 0 [-30, 30], lon_center 180 [120, 280]; rollout fixed at 30 days; output: global-mean TMP2m over days 16–30, printed as EMA_OUTPUT. Hand check: amplitude +1 and -1 at the nominal point should give outputs on opposite sides of amplitude 0. If ema profile shows more than 5 min per run on this machine, stop and say so: this example is then for AWS. Otherwise `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 (ACE, prepare ACE2-SOM with CO2; AWS GPU only). Plan mode first. Create examples/ace/som_co2/. run.py copies forcing_2032.nc from ACE_DATA (~/ema-data/ace2-som/forcing_data/1xCO2) into the run directory, multiplies its global_mean_co2 variable by co2_factor (check the variable name and units with xarray first, and report them), points forcing_loader.dataset.data_path at the run directory, sets n_forward_steps to 2920 (2 years; use forcing_loader.dataset.n_repeats if one year of forcing isn't enough, and check how the HF config uses it), runs inference, prints the cos(lat)-weighted global-mean TMP2m over the last 1460 steps as EMA_OUTPUT, and deletes the copied forcing and the predictions file. Input: co2_factor 1 [1, 4], scale log. timeout_s 3 × the measured time. Then `ema profile ... -n 2` on the GPU. Stop and report; don't run a campaign.
```

```text
Stage 5 (ACE, first campaign). For examples/ace/sst_offset/model.json, write campaign.json with: repeat (n_points 2, replicates 2: is ACE deterministic on this hardware?), curve1d on sst_offset (n 9, days fixed at 10), and linear_coeffs (n 16). Run `ema estimate` and show me the run count and the estimated time; ask me before `ema run`. Use -j 1 on a GPU machine and at most -j 2 on the Mac (memory). Report: whether repeats agree and to how many digits, the curve1d shape (monotone? kinks?), the linear_coeffs R² and the slope in K of TMP2m per K of SST, and any failed runs. Expected: monotone and close to linear in sst_offset, with a slope below 1. Then suggest, without running it, a morris over sst_offset and days, and, on AWS, the sst_patch campaign (sobol, n_base 32). Stop and report.
```

```text
Stage 6 (ACE troubleshooting). An EMA run of examples/ace/<example> fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt and ema_run.json, then by running run.py by hand in a copied run directory with the ema-ace python. Check: torch or torch_harmonics import errors (conda build mismatch; show conda list for pytorch and torch-harmonics); "CUDA not available" or a driver/CUDA mismatch on AWS; out of memory (forward_steps_in_memory too large; peak RSS); DataLoader worker errors (num_data_workers must be 0); dacite/config errors after an fme upgrade (field names changed; we pin 2026.5.1); missing or misnamed variables in the forcing or IC file for the chosen start time; NaN or runaway values in the predictions (the emulator left its training distribution: that's data, not a bug, so report the inputs); per-run time dominated by the checkpoint load; OMP oversubscription when EMA runs -j > 1. Report the cause and a proposed fix. Ask before changing the env, the data, or model.json.
```

**Gotchas and sources.**
- License: code Apache-2.0, ACE2 weights Apache-2.0 (HF model cards). The ERA5-derived data carry the Copernicus attribution notice quoted on the model card.
- Threads: PyTorch uses every core by default. With EMA `-j N`, set `OMP_NUM_THREADS` (and `torch.set_num_threads` in `run.py`) to cores/N.
- Determinism: ACE2-ERA5 and ACE2-SOM are deterministic networks (ACE2S variants are stochastic **(unconfirmed which are)**). Float reductions on CPU threads or on a GPU can still change the last digits, and in an autoregressive rollout those differences grow with time (chaos). Run `repeat` first. If repeats differ, declare the measured spread as `output_noise`, or average the output over a longer window. `n_ensemble_per_ic` exists in `InferenceConfig` for ensembles. For a seeded IC perturbation, seed from `EMA_REPLICATE`.
- Out-of-distribution inputs are the interesting part, but they fail in ways EMA records as NaN (failed runs) or as runaway values. Neither is a bug. Say so in `record_findings`.
- Version pitfalls: config field names change between `fme` releases, and checkpoints are tied to the `fme` version they were saved with **(unconfirmed range)**. Pin `fme==2026.5.1`, and record the checkpoint's SHA-256 in the model description (EMA doesn't hash files named by absolute path).
- Data costs: the full ERA5 training archive (`gs://ai2cm-public-requester-pays/...`) is requester-pays. Never point a driver at it.
- Sources: https://github.com/ai2cm/ace, https://github.com/ai2cm/ace/releases, https://pypi.org/project/fme/, https://ai2-climate-emulator.readthedocs.io/en/latest/quickstart.html, https://ai2-climate-emulator.readthedocs.io/en/latest/api.html, https://ai2cm.github.io/ace/, https://huggingface.co/collections/allenai/ace-67327d822f0f0d8e0e5e6ca4, https://huggingface.co/allenai/ACE2-ERA5, https://huggingface.co/allenai/ACE2-SOM, https://www.nature.com/articles/s41612-025-01090-0, https://arxiv.org/abs/2412.04418, https://arxiv.org/abs/2505.08742, https://pypi.org/project/torch/#files, https://anaconda.org/conda-forge/pytorch, https://anaconda.org/conda-forge/torch-harmonics, https://docs.aws.amazon.com/dlami/latest/devguide/aws-deep-learning-x86-base-gpu-ami-ubuntu-24-04.html

---

#### NeuralGCM

**What it is.** NeuralGCM is a hybrid model from Google Research: a differentiable spectral dynamical core (the `dinosaur` package) plus learned physics. It runs global weather and climate simulations from ERA5 initial conditions. Language: Python on JAX (with `dm-haiku`). License: code Apache-2.0; **trained weights CC BY-SA 4.0**. Current release **neuralgcm 1.2.2 (2025-07-31)** on PyPI and GitHub. The repo is active (last push 2026-09-24) and not archived. It requires Python ≥ 3.10, `dinosaur>=1.3.3`, `dm-haiku`, `jax` and `jaxlib`.
Checkpoints are on the public bucket `gs://neuralgcm/models/`:

| checkpoint | size |
|---|---|
| `v1/deterministic_0_7_deg.pkl` | 127 MB |
| `v1/deterministic_1_4_deg.pkl` | 74 MB |
| `v1/deterministic_2_8_deg.pkl` | 58 MB |
| `v1/stochastic_1_4_deg.pkl` | 47 MB |
| `v1_precip/stochastic_precip_2_8_deg.pkl` | 45 MB |
| `v1_precip/stochastic_evap_2_8_deg.pkl` | 45 MB |

Examples: the docs at https://neuralgcm.readthedocs.io have a forecasting quick start (`docs/inference_demo.ipynb`: regrid a slice of ARCO-ERA5, `model.encode`, `model.unroll`, compare with ERA5), plus pages on checkpoints, trained models and data preparation. There are about half a dozen notebooks **(unconfirmed count)**.
Initial conditions come from ARCO-ERA5 (`gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3`, public, anonymous). You stream only the variables and times you need, then regrid them conservatively to the model grid.
**Fit.** The 2.8° deterministic model is the laptop configuration. Its weights are small, and its state is 128 × 64 × 32 levels **(unconfirmed grid size)**. Inputs are perturbations of the SST forcing and of the initial state. A stochastic checkpoint takes an `rng_key`, which the driver seeds from `EMA_REPLICATE`, so `repeat` measures the noise.
Awkward parts:
- JAX compiles `encode`/`unroll` on first call in every new process: tens of seconds to minutes on CPU *(estimate)*. JAX's persistent compilation cache can amortize it.
- Intel-Mac JAX is conda-forge only.

**Install on an Intel Mac.** PyPI's `jaxlib` has no macOS x86_64 wheel after 0.4.38 (December 2024). conda-forge has `jaxlib` 0.10.2 for osx-64 (Python 3.11–3.14 CPU builds), `neuralgcm` 1.2.2 (noarch, depending on `dinosaur-dycore`, `dm-haiku`, `jax`, `jaxlib`, `optax`, `tensorflow-probability`, `xarray`, ...), `dinosaur-dycore` 1.4.0, `dm-haiku` 0.0.17 and `tensorstore` 0.1.85 (osx-64).
1. Install Miniforge (as in the ACE section).
2. Create the env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-neuralgcm -c conda-forge python=3.12 neuralgcm=1.2.2 gcsfs xarray-tensorstore
   ```
   Compatibility risk: PyPI's `dm-haiku` 0.0.17 declares `jax>=0.11` in its `jax` extra, while conda-forge's newest `jaxlib` is 0.10.2. conda-forge's `dm-haiku` 0.0.17 doesn't pin jax, so the solve may succeed with a combination that fails at import. Whether neuralgcm 1.2.2 + dm-haiku 0.0.17 + jax 0.10.2 work together is **(unconfirmed)**. The smoke test decides. If they don't, pin `dm-haiku=0.0.16` or an older jax/jaxlib pair from conda-forge, and report which.
3. Check:
   ```bash
   ~/miniforge3/envs/ema-neuralgcm/bin/python -c "import jax, neuralgcm, dinosaur; print(jax.__version__, jax.devices(), neuralgcm.__version__)"
   ```
   Expect `[CpuDevice(id=0)]`.
4. Fetch the weights once (58 MB) and one regridded initial condition (see Preparing). Keep them in `~/ema-data/neuralgcm/`.

Known problems:
- The ARCO-ERA5 slice for one time step (7 or so 3-D variables × 37 levels at 0.25°) is about 1 GB streamed *(estimate)*. Do it once and save the regridded result (a few MB at 2.8°).
- `gcsfs` needs `token='anon'`.

Sources: https://pypi.org/project/jaxlib/#files, https://anaconda.org/conda-forge/jaxlib, https://anaconda.org/conda-forge/neuralgcm, https://anaconda.org/conda-forge/dm-haiku, https://pypi.org/project/dm-haiku/, https://neuralgcm.readthedocs.io/en/latest/inference_demo.html

**Install on AWS (Ubuntu 24.04 EC2).** The 2.8° model is light enough for CPU. A `c7i.4xlarge` with a pip venv works, and PyPI has Linux wheels for `jaxlib` 0.11.2:
```bash
mamba create -n ema-neuralgcm -c conda-forge python=3.12 pip
~/miniforge3/envs/ema-neuralgcm/bin/python -m pip install neuralgcm==1.2.2 dinosaur gcsfs
~/miniforge3/envs/ema-neuralgcm/bin/python -c "import jax; print(jax.devices())"
```
For GPU (`g6.xlarge`, 1.4° or 0.7° models), add `pip install "jax[cuda12]"` (JAX also offers `cuda13` extras; match the AMI's driver) and check that `jax.devices()` lists a `CudaDevice`. There's no official Docker image **(unconfirmed; none found)**.
Sources: https://pypi.org/project/jax/ (extras `cuda12`, `cuda13`), https://pypi.org/project/neuralgcm/, https://github.com/neuralgcm/neuralgcm

**Preparing the examples for EMA.**
- **One-time preparation** (not an EMA run): `prep_ic.py` streams one ERA5 time (for example 2020-02-14T00, as in the demo) of `model.input_variables + model.forcing_variables` from ARCO-ERA5. It regrids them with `ConservativeRegridder` and `fill_nan_with_nearest`, as the demo does, and saves `ic_2020-02-14_2p8.nc` next to a copy of the checkpoint in `~/ema-data/neuralgcm/`.
- **Per run**, the driver `run.py`:
  - reads a key = value deck;
  - loads the checkpoint and the IC file;
  - adds `sst_offset` to `sea_surface_temperature` **only where the unfilled SST was defined (ocean)**, so save a land-sea mask in the prep step, because `fill_nan_with_nearest` fills land;
  - optionally adds `t_ic_offset` to the initial `temperature`;
  - runs `model.encode(inputs, forcings, jax.random.key(seed))` and `model.unroll(...)` with persistence forcing, as the demo does;
  - prints `EMA_OUTPUT` of the cos(latitude)-weighted global mean of 850 hPa temperature (or precipitation) at the final lead time.
  - The seed is `EMA_REPLICATE` (0 for ordinary runs).
  - Set `JAX_COMPILATION_CACHE_DIR` (or `jax.config.update("jax_compilation_cache_dir", ...)`) to a persistent directory outside the run directory, so compilation is paid once per machine. Whether the cache hits across processes for `unroll` is **(unconfirmed)**; measure it with `ema profile`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Forecasting quick start, `docs/inference_demo.ipynb` (https://neuralgcm.readthedocs.io/en/latest/inference_demo.html), `v1/deterministic_2_8_deg.pkl`, IC 2020-02-14 | hybrid dynamical core + learned physics, 2.8°, persisted SST and sea ice | `sst_offset` 0 K [−2, 2]; `t_ic_offset` 0 K [−1, 1] (uniform, added to initial temperature at all levels); lead fixed at 5 days | global-mean T at 850 hPa at day 5 | monotone increasing in both. The `t_ic_offset` signal decays with lead time while `sst_offset`'s grows, so both matter at day 5 and are close to additive. Deterministic, so `repeat` should agree (XLA CPU is deterministic for a fixed build **(unconfirmed)**). A uniform IC offset breaks hydrostatic balance slightly, so expect a transient | CPU: 30 s–3 min per run including compilation; 5–30 s with a warm compilation cache *(estimate)* | cli (env python + `run.py`) | regex |
| Same, `v1/stochastic_1_4_deg.pkl` (checkpoints page, https://neuralgcm.readthedocs.io/en/latest/checkpoints.html) | stochastic physics, 1.4° | as above, plus `EMA_REPLICATE` → `rng_key` | global-mean T850 at day 5 | measurable run-to-run noise. `repeat` gives its size, and `morris`/`curve1d` with `output_noise` then decide whether `t_ic_offset` is resolvable above the noise | CPU: 1–5 min *(estimate)*; GPU: 10–30 s | cli | regex |
| Same, `v1_precip/stochastic_precip_2_8_deg.pkl` | 2.8°, stochastic, predicts precipitation | `sst_offset` 0 K [−2, 2]; lead fixed at 10 days | global-mean precipitation rate averaged over days 6–10 (variable name **(unconfirmed)**; list `model.output_variables` first) | increasing with `sst_offset` at a few percent per K (hydrological sensitivity; magnitude **(unconfirmed)**), with stochastic noise comparable to the signal at small offsets: a test of `repeat` + `output_noise` | CPU: 1–4 min *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 (NeuralGCM, read-only check). I want to run NeuralGCM 1.2.2 (JAX) pretrained models as EMA command-line models. Read-only: report OS and version, uname -m, RAM, free disk, Miniforge/conda/mamba and their versions, any env named ema-neuralgcm, NVIDIA GPU (nvidia-smi), and whether this machine can reach storage.googleapis.com (a HEAD request to https://storage.googleapis.com/neuralgcm/models/v1/deterministic_2_8_deg.pkl only; no download). Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, conda-forge (jaxlib 0.10.2 osx-64 and neuralgcm 1.2.2 noarch), because PyPI has no Intel-Mac jaxlib after 0.4.38. On Ubuntu, pip in a conda env (Linux wheels), CPU for 2.8° and a GPU for 1.4°/0.7°. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (NeuralGCM, install on the Intel Mac). Create env ema-neuralgcm from conda-forge only (never defaults, never EMA's .venv, and never read .env): mamba create -n ema-neuralgcm -c conda-forge python=3.12 neuralgcm=1.2.2 gcsfs xarray-tensorstore. Ask before installing Miniforge, before sudo or Homebrew changes, and before downloads over 1 GB. Check: import jax, neuralgcm, dinosaur, haiku; print versions and jax.devices(). If an import fails because dm-haiku and jax disagree, report the versions (conda list jax jaxlib dm-haiku) and propose one pin (for example dm-haiku=0.0.16, or an older jax/jaxlib pair); don't try several. Then download gs://neuralgcm/models/v1/deterministic_2_8_deg.pkl (58 MB) with gcsfs token='anon' into ~/ema-data/neuralgcm/ and record its SHA-256. Report the env's absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b (NeuralGCM, install on AWS Ubuntu 24.04; I'm ssh'd in). Install Miniforge (ask first) and an env ema-neuralgcm (python=3.12 pip), then pip install neuralgcm==1.2.2 dinosaur gcsfs (never EMA's .venv, and never read .env). If nvidia-smi shows a GPU, also pip install "jax[cuda12]" (or cuda13 if the driver needs it; tell me which and why) and check that jax.devices() shows a CUDA device. Ask before any sudo and before downloads over 1 GB. Download the 2.8° deterministic, 1.4° stochastic and 2.8° stochastic_precip checkpoints into ~/ema-data/neuralgcm/ with SHA-256s. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 (NeuralGCM smoke test and initial condition). Outside the EMA repo, write ~/ema-data/neuralgcm/prep_ic.py following the forecasting quick start (docs/inference_demo.ipynb of github.com/neuralgcm/neuralgcm): load deterministic_2_8_deg.pkl; open the ARCO-ERA5 zarr anonymously; select ONE time (2020-02-14T00) of model.input_variables + model.forcing_variables (with the demo's 24-hour shift of forcings); before running, estimate the download size from the zarr metadata and ask me if it's over 1 GB; regrid conservatively; save ic_2020-02-14_2p8.nc, and also a land-sea mask (where sea_surface_temperature was NaN before fill_nan_with_nearest). Then run a 2-day unroll twice in one process and once in a fresh process, and report: the first-call (compile) time, the second-call time, the fresh-process time with JAX_COMPILATION_CACHE_DIR set to ~/ema-data/neuralgcm/jaxcache, peak memory, and the global-mean T850 at day 2. Don't touch EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (NeuralGCM, prepare the deterministic 2.8° example). Plan mode first; show me the plan. Create examples/neuralgcm/sst_2p8/ following docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/: ngcm.template (sst_offset = $sst_offset, t_ic_offset = $t_ic_offset) and run.py, which reads the deck; loads the checkpoint, IC file and mask from NGCM_DATA (absolute, ~/ema-data/neuralgcm); adds sst_offset to sea_surface_temperature over ocean only and t_ic_offset to the initial temperature; seeds jax.random.key(int(os.environ.get("EMA_REPLICATE", 0))); unrolls 5 days with persistence forcing; and prints "EMA_OUTPUT %.12e" for the cos(lat)-weighted global mean of temperature at 850 hPa at day 5, plus the neuralgcm and jax versions and the checkpoint's SHA-256. model.json: command [the ema-neuralgcm env's absolute python, "run.py"]; env NGCM_DATA, JAX_COMPILATION_CACHE_DIR, XLA_FLAGS or thread limits only if Stage 3 showed a need; timeout_s = 4 × the cold time. Inputs: sst_offset 0 [-2, 2], t_ic_offset 0 [-1, 1]. Hand check: +1 K SST gives a warmer day-5 T850 than 0. Then `ema profile examples/neuralgcm/sst_2p8/model.json -n 3` and report cold and warm times. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (NeuralGCM, prepare the stochastic examples). Plan mode first. Create examples/neuralgcm/stoch_1p4/ (v1/stochastic_1_4_deg.pkl; regrid the same ERA5 time to its grid with prep_ic.py) and examples/neuralgcm/precip_2p8/ (v1_precip/stochastic_precip_2_8_deg.pkl) by the pattern of sst_2p8. For precip_2p8, first list model.output_variables and tell me the precipitation variable's name and units before choosing the output (mean over days 6–10). Both seed from EMA_REPLICATE. Hand check for each: two runs with EMA_REPLICATE=1 and 2 at the nominal point differ; two runs with the same value agree. Then `ema profile ... -n 3` for each (on AWS if the 1.4° model takes more than 5 min on the Mac). Stop and report; don't run a campaign.
```

```text
Stage 5 (NeuralGCM, first campaign). For examples/neuralgcm/sst_2p8/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on sst_offset (n 9), and morris (n_traj 6). Run `ema estimate`, show me the run count and time, and ask before `ema run`. Use -j 2 at most on the Mac (memory). Report: whether repeats agree, the curve1d shape, the morris ranking, and whether both inputs matter at day 5. Expected: deterministic; monotone increasing in both; near-additive. Then propose, without running it, a repeat + morris campaign on precip_2p8 with output_noise from repeat. Stop and report.
```

```text
Stage 6 (NeuralGCM troubleshooting). An EMA run of examples/neuralgcm/<example> fails or is slow. Diagnose read-only first, from stdout.txt, stderr.txt and ema_run.json, then run run.py by hand in a copied run directory. Check: jax/jaxlib/dm-haiku version mismatches (AttributeError inside haiku or jax internals; conda list); per-run time dominated by XLA compilation (compare the cold and warm times; is JAX_COMPILATION_CACHE_DIR set and writable, and does it grow?); pickle load errors (a checkpoint from a different neuralgcm version); NaN from the SST offset applied over land or sea ice (check the mask); memory (the 1.4° model on an 8–16 GB machine); thread oversubscription when EMA runs -j > 1 (XLA uses all cores; limit it with XLA_FLAGS="--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1" if needed, which is unconfirmed for this jax version); network access at run time (runs must read only local files). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License: code Apache-2.0, but **weights CC BY-SA 4.0**. Results derived from the weights may carry share-alike obligations if redistributed **(check with the analyst's organization)**.
- Threads: XLA on CPU uses every core. With EMA `-j N`, limit threads per run, or use `-j 1` and let XLA parallelize.
- Determinism and noise: the deterministic checkpoints are deterministic up to floating-point reduction order. The stochastic ones take `rng_key`: seed it from `EMA_REPLICATE` so repeated runs differ and reruns reproduce. `repeat` measures the spread.
- Run time: compilation dominates short rollouts. Use the persistent compilation cache, keep shapes fixed (the same lead time and output interval in every run), and change inputs only through values, never array shapes.
- Version pitfalls: `dm-haiku` is in maintenance, and its newest release wants jax ≥ 0.11, while conda-forge's osx-64 `jaxlib` is 0.10.2. This is the most likely failure on the Intel Mac. neuralgcm's last release is from July 2025, while the repo is active, so pin 1.2.2 and the checkpoint.
- Data: ARCO-ERA5 is public and anonymous, but a careless `sel` streams gigabytes. Prepare the IC once, and never read the cloud during an EMA run.
- Sources: https://github.com/neuralgcm/neuralgcm, https://github.com/neuralgcm/neuralgcm/releases, https://neuralgcm.readthedocs.io, https://neuralgcm.readthedocs.io/en/latest/inference_demo.html, https://neuralgcm.readthedocs.io/en/latest/checkpoints.html, https://storage.googleapis.com/storage/v1/b/neuralgcm/o?prefix=models/ (checkpoint sizes), https://pypi.org/project/neuralgcm/, https://pypi.org/project/jaxlib/#files, https://pypi.org/project/jax/, https://pypi.org/project/dm-haiku/, https://anaconda.org/conda-forge/jaxlib, https://anaconda.org/conda-forge/neuralgcm, https://anaconda.org/conda-forge/dm-haiku, https://anaconda.org/conda-forge/dinosaur-dycore, https://anaconda.org/conda-forge/tensorstore, https://arxiv.org/abs/2311.07222

---

#### ClimaX

**What it is.** ClimaX is a vision-transformer "foundation model" for weather and climate from Microsoft Research. It is pretrained on CMIP6 and fine-tuned for downstream tasks (global and regional forecasting, ClimateBench climate projection). Language: Python (PyTorch 1.12 + PyTorch Lightning 1.8). License: MIT (code and the Hugging Face weights). **It is unmaintained:**
- the last commit and last release are **v0.3.1 (2023-09-30)**, and the Hugging Face weights date from 2023-10-11;
- the pinned environment (`docker/environment.yml`) is Python 3.8.16, PyTorch 1.12.1 and CUDA 11.3;
- the name `climax` on PyPI is an **unrelated** package (0.5.0, 2021), so never `pip install climax`.

Checkpoints (https://huggingface.co/tungnd/climax): `5.625deg.ckpt` (432 MB) and `1.40625deg.ckpt` (443 MB) are **pretrained only**. The repo also holds `vits.ckpt`, `vitb.ckpt` and `vitl.ckpt` (99 MB–1.26 GB), which the docs don't describe **(unconfirmed what they are)**. **No fine-tuned forecasting checkpoint is published.** The docs (`docs/usage.md`) cover pretraining and fine-tuning only, with no inference-only script, and their example fine-tuning runs use 8 GPUs.
Data: ERA5 at 5.625° from WeatherBench (https://dataserv.ub.tum.de/index.php/s/m1524895; size of the needed variables **(unconfirmed; tens of GB)**), preprocessed to `.npz` shards with `src/data_preprocessing/nc2np_equally_era5.py`. Or ClimateBench (https://doi.org/10.5281/zenodo.5196512) for climate projection.
**Fit: poor, and AWS GPU only.** Before EMA can run anything, you must fine-tune on a GPU. The narrowest useful configuration is **ClimateBench climate projection at 5.625°**: its inputs are the scenario's global emissions of CO2, CH4, SO2 and black carbon, which are exactly the kind of few scalar inputs EMA varies, and its output is a global-mean surface-temperature map. The second option is **global forecasting at 5.625° with one lead time (72 h)**. Once fine-tuned, one forward pass at 5.625° (32 × 64 grid) is cheap even on a CPU *(estimate)*. Unless the analyst specifically needs ClimaX, prefer ACE or NeuralGCM, which ship ready-to-run weights.

**Install on an Intel Mac.** Not recommended. The official environment needs CUDA 11.3 and PyTorch 1.12.1 from the `pytorch` channel. That channel stopped publishing conda packages, and the environment mixes in the `defaults` channel, which this document avoids. A CPU-only env from conda-forge (`pytorch` 2.13 osx-64 + an old `pytorch-lightning` 1.8) is untested and likely to break on Lightning/torch API changes **(unconfirmed)**. If inference on the Mac is ever needed, export the fine-tuned network from AWS as TorchScript or ONNX and run it in a small conda-forge env **(to be designed; unconfirmed that the model exports cleanly)**.
Sources: https://github.com/microsoft/ClimaX, https://raw.githubusercontent.com/microsoft/ClimaX/main/docker/environment.yml, https://raw.githubusercontent.com/microsoft/ClimaX/main/docs/install.md

**Install on AWS (Ubuntu 24.04 EC2).** Use a `g5.2xlarge` or `g6.2xlarge` (1 GPU, 8 vCPU, 32 GB) with the Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04), and 300 GB of gp3 for WeatherBench plus the shards.
1. The repo's route is `conda env create --file docker/environment.yml` + `pip install -e .`. That env is CUDA 11.3. Whether it runs on the AMI's newer driver is **(unconfirmed)**, though newer drivers generally run older CUDA runtimes.
2. More robust: build the repo's own Docker image (`cd docker && docker build -t climax .`; the docs write `ClimaX`, but Docker tags must be lowercase) and run it with `--gpus all`. That needs the NVIDIA Container Toolkit, which the Base AMI includes **(unconfirmed for the 24.04 AMI)**. Record the built image's digest.
3. Check:
   ```bash
   python -c "import torch, pytorch_lightning as pl, climax; print(torch.__version__, pl.__version__, torch.cuda.is_available())"
   ```
4. Fine-tune once (the cost of this step dominates; don't use 8 GPUs, use one):
   ```bash
   python src/climax/global_forecast/train.py --config configs/global_forecast_climax.yaml \
     --trainer.devices=1 --trainer.max_epochs=5 --data.root_dir=/data/5.625deg_npz \
     --data.predict_range=72 --data.out_variables=['z_500','t_850','t2m'] --data.batch_size=16 \
     --model.pretrained_path='https://huggingface.co/tungnd/climax/resolve/main/5.625deg.ckpt'
   ```
   `max_epochs=5` is a smoke-level choice. The docs use 50 epochs on 8 GPUs, and a single-GPU wall time is **(unconfirmed; hours to days)**.

Sources: https://raw.githubusercontent.com/microsoft/ClimaX/main/docs/usage.md, https://raw.githubusercontent.com/microsoft/ClimaX/main/docs/install.md, https://huggingface.co/tungnd/climax

**Preparing the examples for EMA.** A driver `run.py` in the ClimaX env loads the **fine-tuned** Lightning checkpoint once per run (from `~/ema-data/climax/`, with its SHA-256 recorded), builds one input tensor, applies the perturbation, runs one forward pass, un-normalizes with `normalize_mean.npz`/`normalize_std.npz`, and prints a cos(latitude)-weighted global mean. Inputs arrive through a key = value deck. How to build one sample outside the Lightning DataModule is **(unconfirmed)**: read `src/climax/global_forecast/datamodule.py` first.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Global forecasting, `src/climax/global_forecast/train.py` + `configs/global_forecast_climax.yaml`, fine-tuned at 5.625°, `predict_range=72` (https://github.com/microsoft/ClimaX/blob/main/docs/usage.md) | ViT emulator of ERA5 3-day forecast | `t850_offset` 0 K [−2, 2] (uniform, added to the input `t_850`); `z500_offset` 0 m²/s² [−500, 500]; start sample index fixed | global-mean `t2m` at +72 h | near-linear, monotone in `t850_offset`. `z500_offset` possibly negligible or unphysical (a uniform geopotential shift has no dynamical meaning, so a network may still respond: a test of learned physics). Deterministic | GPU: 5–15 s, mostly checkpoint load; CPU after export: under 10 s *(estimate)* | cli | regex |
| ClimateBench climate projection, `src/climax/climate_projection/` (usage.md, "Climate Projection"), fine-tuned at 5.625° | emulator of NorESM2 surface temperature response to emissions | `co2_scale` 1 [0.5, 2] (log), `so2_scale` 1 [0, 2], `ch4_scale` 1 [0.5, 2] (log), scaling the SSP2-4.5 input maps for one target year (input variable names and shapes **(unconfirmed)**; read the ClimateBench loader first) | global-mean `tas` for the target year | increasing in CO2 and CH4, decreasing in SO2 (aerosol cooling); CO2 dominant (`morris`/`sobol`); near-linear in ln(CO2) under `scale: log`. Out-of-range scalings extrapolate beyond the ClimateBench scenarios: watch for saturation | GPU: 5–15 s; CPU after export: seconds *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 (ClimaX, read-only check; AWS GPU instance only). I'm considering ClimaX (microsoft/ClimaX v0.3.1, last updated 2023-09-30; unmaintained) for EMA. Read-only: report OS, uname -m, nvidia-smi (GPU model, driver, CUDA version), docker and whether it can see the GPU (docker info | grep -i runtime; don't run a container), conda, free disk (need ≥ 300 GB), and RAM. Don't install anything, and don't read .env. Recommend: build the repo's Docker image (tag climax, lowercase) or conda env create from docker/environment.yml, and say which fits this driver. If this is my Intel Mac, stop and tell me ClimaX is AWS-only in this plan. Stop and report; don't continue to the next stage.
```

```text
Stage 2b (ClimaX, install on AWS). Clone github.com/microsoft/ClimaX at tag v0.3.1 into ~/src/ClimaX (outside the EMA repo). Build its Docker image from docker/ with tag climax (ask me first; it's several GB), or, if I choose conda, conda env create --file docker/environment.yml (it uses the pytorch and defaults channels; tell me that first). Never install into EMA's .venv, never pip install the unrelated PyPI package "climax", and never read .env. Ask before any sudo. Check: torch.cuda.is_available() inside the image or env, and import climax. Record the image digest (docker image inspect). Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 (ClimaX, data and a smoke fine-tune). Ask me before each download; report its size first. Download only the WeatherBench 5.625° variables that global_forecast_climax.yaml uses (list them from the config first), into /data/5.625deg, then run src/data_preprocessing/nc2np_equally_era5.py as in docs/usage.md into /data/5.625deg_npz. Then run global_forecast/train.py with --trainer.devices=1 --trainer.max_epochs=1 --data.predict_range=72 and the 5.625deg pretrained checkpoint URL, and report the time per epoch, GPU memory, the validation RMSE it logs, and where it saved the checkpoint. Don't start a longer fine-tune. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (ClimaX, prepare the 72-h forecast example). Only after I've approved and finished a fine-tune whose checkpoint is in ~/ema-data/climax/. Plan mode first. Read src/climax/global_forecast/module.py and datamodule.py and explain how to build one input sample and un-normalize the output outside Lightning. Then create examples/climax/forecast72/ with a deck template (t850_offset = $t850_offset, z500_offset = $z500_offset) and run.py (in the climax env or `docker run --rm --gpus all -v $EMA_WORKDIR:/work -w /work climax@sha256:<digest> python run.py`, with run.py as a static file so the container can see it; see section 2 of docs/brainstorms/pde_packages_onboarding.md). It loads the checkpoint, takes one fixed test sample, adds the offsets, runs a forward pass, and prints EMA_OUTPUT of the cos(lat)-weighted global-mean t2m at +72 h, plus the checkpoint's SHA-256. Hand check: t850_offset +1 gives a warmer t2m than 0. Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (ClimaX, prepare the ClimateBench projection example). Plan mode first; only if I've fine-tuned the climate-projection task. Read src/climax/climate_projection/ and report the input variables (names, shapes, units) and how a target year is selected. Propose inputs co2_scale 1 [0.5, 2] (log), so2_scale 1 [0, 2], ch4_scale 1 [0.5, 2] (log), scaling the SSP2-4.5 input maps for one target year, and output the global-mean tas for that year. Create examples/climax/climatebench/ by the pattern of forecast72. Hand check: co2_scale 2 is warmer than 1, and so2_scale 2 is cooler than 1. Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 (ClimaX, first campaign). For examples/climax/climatebench/model.json (or forecast72), write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), and linear_coeffs with log_output false (n 24). Run `ema estimate`, show the run count and time, and ask before `ema run` (-j 1 on one GPU). Report: determinism, morris ranking, linear R², and signs. Expected: CO2 dominant and positive, SO2 negative, CH4 smaller. Then suggest, without running it, a surrogate_check to see how simple the fine-tuned network's response is. Stop and report.
```

```text
Stage 6 (ClimaX troubleshooting). A ClimaX EMA run fails. Diagnose read-only first: CUDA 11.3 runtime vs the driver (torch.cuda.is_available() False; nvidia-smi); Lightning 1.8 checkpoint loading errors (keys or hyperparameters missing, a checkpoint from a different config); normalization files not found (normalize_mean.npz/normalize_std.npz paths); variable order mismatches between the checkpoint and the sample (the config's variables list); Docker errors (GPU not visible: --gpus all, container toolkit; files owned by root: --user); per-run time dominated by the checkpoint load. Report the cause and a proposed fix. Ask before changing the image, env, or model.json.
```

**Gotchas and sources.**
- License: MIT (code and weights). WeatherBench/ERA5 data carry Copernicus terms, and ClimateBench its own (see Zenodo).
- Maintenance: no commits since 2023-09-30. Expect dependency rot: PyTorch 1.12, Lightning 1.8, Python 3.8 (end of life). Pin everything, and keep the Docker image digest.
- Fine-tuning is required, and its cost dominates. Budget GPU hours before committing. The prices of `g5`/`g6` instances are **(unconfirmed)**.
- Determinism: one forward pass in eval mode is deterministic up to cuDNN algorithm choice. Set `torch.backends.cudnn.deterministic = True` in `run.py`, and still run `repeat`.
- Scientific caveat: a single-lead-time ViT forecast is a static map from inputs to output, so EMA characterizes the network, not atmospheric dynamics.
- Sources: https://github.com/microsoft/ClimaX, https://github.com/microsoft/ClimaX/releases, https://raw.githubusercontent.com/microsoft/ClimaX/main/docs/usage.md, https://raw.githubusercontent.com/microsoft/ClimaX/main/docs/install.md, https://raw.githubusercontent.com/microsoft/ClimaX/main/docker/environment.yml, https://huggingface.co/tungnd/climax, https://pypi.org/project/climax/ (the unrelated package), https://dataserv.ub.tum.de/index.php/s/m1524895, https://doi.org/10.5281/zenodo.5196512, https://arxiv.org/abs/2301.10343

---

---

### 4.10 Quantum chemistry, cheminformatics, and molecular dynamics: PySCF, RDKit, OpenMM, LAMMPS, NAMD, VMD

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions come from PyPI's JSON API, anaconda.org's conda-forge file lists, GitHub releases, and the projects' own download pages, all read today. Run times are estimates from the examples' sizes and the timings in their own logs; every one is marked *(estimate)* and must be confirmed with `ema profile`. Notes common to the group:

- **Two kinds of fit.** PySCF and RDKit are deterministic programs: the same inputs give the same number, up to SCF or minimizer tolerances. OpenMM, LAMMPS and NAMD run **molecular dynamics**, which is chaotic: an average over a short run depends on the random seed. For them `repeat` is not optional. It measures the noise, and every later diagnostic gets that noise as `output_noise`. EMA passes `EMA_REPLICATE` (0, 1, 2, ...) to every command-line program, so each driver or input script must seed its thermostat and initial velocities from it: seed = a fixed base + `EMA_REPLICATE`. Otherwise OpenMM (seed 0 means "pick one at random") and NAMD (seed from the clock) give a different answer on every run, and replicate 0 isn't reproducible. Each MD package also gets a deterministic example (a minimization or a single-point energy).
- **VMD is not a model.** It is a visualization and trajectory-analysis program. It appears here only as an optional output step after an MD run.
- **Intel Mac.** conda-forge builds `osx-64` for PySCF 2.14.0, RDKit 2026.03.6, OpenMM 8.6.1 and LAMMPS 2025.07.22 (stable 22Jul2025 update 6), all uploaded in September 2026. PyPI is less even: PySCF and OpenMM have Intel wheels, **RDKit stopped publishing macOS x86_64 wheels after 2025.9.3**, and LAMMPS's PyPI wheel is unofficial. NAMD 3.0.3 ships a `MacOS-universal-multicore` binary (Apple Silicon and Intel). **VMD 2.0 has no Intel Mac build**; the last one is 1.9.4 alpha (2023-06-08). No Homebrew anywhere.
- **Licenses.** PySCF (Apache-2.0), RDKit (BSD-3-Clause), OpenMM (MIT/LGPL), and LAMMPS (GPL-2.0) are open source. **NAMD and VMD are not.** Their downloads need a registration and login at ks.uiuc.edu, the license allows only "academic, research and internal business purposes", and it forbids redistribution. No script can install them. The analyst downloads them by hand, and their files never go into the EMA repo.
- **Wiring.** Each package lives in its own conda env (`ema-<pkg>`), never in EMA's `.venv`. Every model is a command-line model: for a Python package the command is the env's absolute `python` path plus a driver next to `model.json`, as in the FEniCSx section. LAMMPS and NAMD take their own input scripts. For LAMMPS, inputs go on the command line with `-var name $name`, so its `$`-heavy scripts stay static files. NAMD configs are Tcl, so a NAMD template needs every literal `$` written as `$$`.
- **Threads.** Set `OMP_NUM_THREADS=1` (PySCF, LAMMPS's OPENMP package), `OPENMM_CPU_THREADS=1` (OpenMM's CPU platform), and `+p1` (NAMD) in each spec, and let EMA's `-j N` do the parallel work.
- **AWS.** A `c7i.2xlarge` (8 vCPU, 16 GB) is enough for every example here with `-j 8`. The MD campaigns need many repeats, so a `c7i.4xlarge` with `-j 16` halves their wall time. Use a 50 GB gp3 volume: the NAMD tutorial archive alone is 155 MB, and the conda envs are a few GB. Check current prices on the AWS pricing page **(unconfirmed; prices vary by region)**.

---

#### PySCF

**What it is.** The Python-based Simulations of Chemistry Framework: Hartree–Fock, DFT, coupled cluster, CASSCF and more for molecules and periodic systems. Written in Python, with C kernels (libcint, libxc). Apache-2.0. Current release **v2.14.0 (GitHub release 2026-07-18)**. conda-forge rebuilt it on 2026-09-12. Examples: the `examples/` directory of https://github.com/pyscf/pyscf has **471 `.py` scripts** at v2.14.0 (for example `examples/scf/`, `examples/dft/`, `examples/cc/`, `examples/mcscf/`), and the user guide is at https://pyscf.org/user/index.html. PySCF fits EMA well. A single-point energy of a small molecule in a small basis takes about a second, and it is deterministic up to the SCF convergence tolerance. Its SCF can also land on different solutions (RHF vs UHF, symmetry breaking), which gives real kinks and plateaus in the output.

**Install on an Intel Mac.** PyPI has a single `pyscf-2.14.0-py3-none-macosx_10_9_x86_64.whl` that serves every Python 3 version. conda-forge also has `pyscf` 2.14.0 for osx-64, but its build strings list only py310 and py311, so it's unclear whether it installs with Python 3.12 **(unconfirmed)**. The surest route is a conda env for Python and NumPy, with the pip wheel on top.
1. Install Miniforge (osx-64) if there is no conda or mamba:
   ```bash
   curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
   bash Miniforge3-MacOSX-x86_64.sh -b -p "$HOME/miniforge3"
   ```
2. Create the env and add the wheel:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-pyscf -c conda-forge python=3.12 numpy scipy h5py pip
   ~/miniforge3/envs/ema-pyscf/bin/python -m pip install --only-binary=:all: pyscf==2.14.0
   ```
   (The all-conda alternative is `mamba create -n ema-pyscf -c conda-forge python=3.11 pyscf=2.14.0`.)
3. Check:
   ```bash
   ~/miniforge3/envs/ema-pyscf/bin/python -c "import pyscf; print(pyscf.__version__); from pyscf import gto, scf; print(scf.RHF(gto.M(atom='H 0 0 0; H 0 0 0.74', basis='sto-3g', verbose=0)).kernel())"
   ```
   Expect `2.14.0` and an energy near −1.117 Hartree (the STO-3G H2 value; check it against `examples/scf/16-h2_scan.py`'s printout).

Known problems: PySCF uses OpenMP in its C kernels, so set `OMP_NUM_THREADS=1`. It writes a checkpoint file (`chkfile`) to `$PYSCF_TMPDIR` (default: the system temp directory) on every SCF, so point `PYSCF_TMPDIR` at the run directory or set `mf.chkfile = None` in the driver **(unconfirmed that `None` disables it in 2.14)**.
Sources: https://pypi.org/project/pyscf/2.14.0/#files, https://anaconda.org/conda-forge/pyscf/files, https://pyscf.org/user/install.html, https://github.com/pyscf/pyscf/releases/tag/v2.14.0

**Install on AWS (Ubuntu 24.04 EC2).**
1. Use the same env as on the Mac, with Miniforge's Linux installer. PyPI has manylinux x86_64 wheels, and conda-forge has linux-64 2.14.0:
   ```bash
   curl -LO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   bash Miniforge3-Linux-x86_64.sh -b -p "$HOME/miniforge3"
   ~/miniforge3/bin/mamba create -n ema-pyscf -c conda-forge python=3.12 numpy scipy h5py pip
   ~/miniforge3/envs/ema-pyscf/bin/python -m pip install --only-binary=:all: pyscf==2.14.0
   ```
2. There is no apt package on noble (`python3-pyscf` isn't in the archive) and no official Docker image **(none found)**.
3. The check is the same as on the Mac.
Sources: https://pyscf.org/user/install.html, https://pypi.org/project/pyscf/#files, https://packages.ubuntu.com/noble/ (searched: no pyscf)

**Preparing the examples for EMA.** Each example is a loop over geometries. The recipe:
- Turn the loop body into a driver, `run.py`, that computes **one** geometry.
- Pass inputs as command-line arguments (`["<env>/bin/python", "run.py", "--R", "$R", ...]`, like `examples/beam/model_args.json`), so there is no deck and no `$` problem.
- Set `verbose=0` and print one line, `output = %.12e`.
- Pin `conv_tol` (1e-10) and the DFT grid (`mf.grids.level`) in the driver, and print `pyscf.__version__` to stdout.
- Never reuse a density matrix from a previous geometry, as the scan examples do: each EMA run starts cold, so the initial guess must be deterministic and stated.
- A failed SCF (`mf.converged` False) exits non-zero, so that EMA records a failed run instead of a wrong number.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/scf/56-h2_symm_breaking.py` (https://github.com/pyscf/pyscf/blob/v2.14.0/examples/scf/56-h2_symm_breaking.py): H2, RHF vs UHF with a HOMO–LUMO mixed guess (Szabo–Ostlund §3.8.7), STO-3G | H2 dissociation; UHF breaks spin symmetry past the Coulson–Fischer point | `R` (bond length, Å) 1.5 [0.5, 3.0]; `q` (HOMO–LUMO mixing angle of the guess, rad) 0.785 [0.05, 1.5] | ΔE = E(UHF) − E(RHF) in Hartree; second model: UHF ⟨S²⟩ from `mf.spin_square()` | ΔE is exactly 0 (to the SCF tolerance) below the Coulson–Fischer point (about 1.2 Å in STO-3G; a textbook value, **(unconfirmed here)**) and negative beyond it: a **plateau with an edge** that curve1d on `R` should locate; ⟨S²⟩ rises from 0 at the same point (a kink); `q` is **negligible** except near 0, where the guess no longer breaks symmetry and UHF can stay on the RHF solution (a region where ΔE = 0 at large R) | ~1 s, mostly the import *(estimate)* | cli (env python + `run.py`, inputs as args) | regex on stdout |
| `examples/scf/01-h2o.py` (https://github.com/pyscf/pyscf/blob/v2.14.0/examples/scf/01-h2o.py): water, RHF/cc-pVDZ | electronic energy against geometry | `r_OH` (Å) 0.96 [0.85, 1.20]; `angle` (HOH, degrees) 104.5 [95, 120]; `conv_tol` 1e-9 [1e-11, 1e-6] (log) | total RHF energy (Hartree) | a smooth bowl with its minimum inside the input box, so **not monotone** in either geometry input; nearly quadratic, so a `surrogate_check` with `poly` should meet its target; a weak stretch–bend interaction; `conv_tol` **negligible** (the energy error is far below the geometry effect) but it sets a roughness floor that finite_diff with tiny steps would see | ~1–2 s *(estimate)* | cli | regex |
| `examples/dft/24-custom_xc_functional.py` (https://github.com/pyscf/pyscf/blob/v2.14.0/examples/dft/24-custom_xc_functional.py): water, a B3LYP-like functional built with `parse_xc`, cc-pVDZ | hybrid DFT; the exact-exchange fraction | `a0` (exact-exchange fraction) 0.20 [0, 0.5]; `c_lyp` (LYP share of correlation, the rest VWN) 0.81 [0.5, 1.0]; xc string `f"HF*{a0} + {1-a0}*B88, {c_lyp}*LYP + {1-c_lyp}*VWN"` (the driver builds it) | HOMO–LUMO gap in eV (`mf.mo_energy`) | gap **increases almost linearly with `a0`** (a well-known trend): `linear_coeffs` R² near 1; `c_lyp` small, perhaps **possibly negligible** for the gap (it isn't for the total energy, a second model); deterministic with a fixed grid | 3–10 s *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard PySCF 2.14.0 examples into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, any existing env named ema-pyscf, Python versions available, and free disk space. Don't install anything, and don't read .env. Recommend a route: a Miniforge env `ema-pyscf` (python=3.12, numpy, scipy, h5py from conda-forge) plus the PyPI wheel pyscf==2.14.0 (it has a macosx x86_64 wheel and manylinux wheels). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install PySCF on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-pyscf -c conda-forge python=3.12 numpy scipy h5py pip`, then `<env>/bin/python -m pip install --only-binary=:all: pyscf==2.14.0`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import pyscf; print(pyscf.__version__)"` and an RHF/STO-3G H2 energy at 0.74 Å. Report the env's absolute python path. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install PySCF on this AWS EC2 instance (Ubuntu 24.04, x86_64). Use Miniforge's Linux x86_64 installer (ask me first) and the same env as on my Mac: `ema-pyscf` with python=3.12 numpy scipy h5py pip from conda-forge, then pip install --only-binary=:all: pyscf==2.14.0. Never use EMA's .venv, and never read .env. Ask before any sudo. Check the version and the H2 energy as in Stage 2a, and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — PySCF smoke test. In a scratch directory outside the EMA repo, download examples/scf/16-h2_scan.py and examples/scf/56-h2_symm_breaking.py from the v2.14.0 tag of github.com/pyscf/pyscf. Run both with the ema-pyscf env's python and OMP_NUM_THREADS=1, and time them. Report the last lines of each (the R, E(RHF), E(UHF) table of the second one), and the R where E(UHF) first drops below E(RHF). Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the PySCF H2 symmetry-breaking example for EMA. Enter plan mode first and show me the plan. Source: examples/scf/56-h2_symm_breaking.py (PySCF 2.14.0). Write examples/pyscf/h2_breaksym/run.py, which computes ONE geometry: H2 at bond length --R (Å), STO-3G, RHF from the default guess, and UHF from the example's init_guess_mixed(mol, q) with --q (don't reuse density matrices between geometries). Set conv_tol 1e-10 and verbose 0. Exit non-zero if either SCF did not converge. Print `pyscf <version>` and `delta_E = <E_UHF - E_RHF, %.12e>`. Follow docs/applications.md, docs/guides/input_deck_model.md and examples/beam/model_args.json (inputs as command-line arguments). The command is the ema-pyscf env's absolute python path (not $EMA_PYTHON), then run.py --R $R --q $q. Inputs: R 1.5 [0.5, 3.0], q 0.785 [0.05, 1.5]. env: OMP_NUM_THREADS=1 and PYSCF_TMPDIR=$EMA_WORKDIR (check that EMA substitutes $EMA_WORKDIR in env values; if it doesn't, set chkfile off in the driver instead). timeout_s 120. Write a second model_s2.json that shares run.py and reads `S2 = ...` (UHF <S^2>). Check by hand: at R = 0.74, delta_E is 0 to about 1e-9; at R = 2.5, it is negative. Then run `ema profile examples/pyscf/h2_breaksym/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the PySCF water geometry example. Plan mode first. Source: examples/scf/01-h2o.py (PySCF 2.14.0). Put it in examples/pyscf/h2o_geometry/run.py: build water from --r_OH (Å) and --angle (HOH, degrees) in a symmetric geometry, cc-pVDZ, RHF, conv_tol from --conv_tol, symmetry off, verbose 0; exit non-zero if not converged; print `energy = %.12e`. Command-line model like examples/beam/model_args.json with the ema-pyscf env's absolute python path. Inputs: r_OH 0.96 [0.85, 1.20], angle 104.5 [95, 120], conv_tol 1e-9 [1e-11, 1e-6] with scale log. env OMP_NUM_THREADS=1. Check by hand that the energy near r_OH 0.96, angle 104.5 is lower than at both corners (0.85, 95) and (1.20, 120). Then `ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the PySCF hybrid-functional example. Plan mode first. Source: examples/dft/24-custom_xc_functional.py (PySCF 2.14.0), the parse_xc part. Put it in examples/pyscf/h2o_hybrid/run.py: water at the example's geometry, cc-pVDZ, RKS with mf.xc = f"HF*{a0} + {1-a0}*B88, {c_lyp}*LYP + {1-c_lyp}*VWN", grids.level fixed at 3, conv_tol 1e-10, verbose 0. First check by hand that a0 = 0.2, c_lyp = 0.81 and the example's B3LYP-style string give close energies (they differ in the LDA share; report the difference and don't try to match it). Print `gap_eV = %.12e` (LUMO − HOMO from mf.mo_energy, times 27.211386). Exit non-zero if not converged. Inputs: a0 0.2 [0, 0.5], c_lyp 0.81 [0.5, 1.0]. Write model_energy.json too, reading `energy = ...`. Then `ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first PySCF campaign. For examples/pyscf/h2_breaksym/model.json, write campaign.json with repeat (n_points 2, replicates 2), curve1d on R (n 41), and morris (n_traj 8). Run `ema estimate` and report the run count and estimated time; ask me before `ema run`. Afterwards report: whether repeats are identical (they should be: deterministic), where curve1d puts the plateau edge or kink in R (expected near 1.2 Å for STO-3G), whether morris finds q negligible, and any failed runs. Then suggest (don't run) curve1d on R for model_s2.json. Stop and report.
```

```text
Stage 6 — PySCF troubleshooting. An EMA PySCF model (examples/pyscf/<example>) fails, is slow, or gives odd values. Diagnose read-only first: run the driver by hand in a copied run directory with the ema-pyscf env's python. Check for: SCF not converged (print mf.converged and the cycle count; try level_shift or newton() only with my OK, since they change the answer at instabilities); UHF collapsing to the RHF solution (the guess; check <S^2>); OpenMP oversubscription (OMP_NUM_THREADS); chkfile or tmp-directory errors (PYSCF_TMPDIR); DFT grid warnings; a regex that doesn't match the printed line; `could not start` (a wrong interpreter path in model.json). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License Apache-2.0.
- Threads: OpenMP in libcint, libxc and PySCF's own C code. Set `OMP_NUM_THREADS=1`. Parallel reductions change the last digits.
- Determinism: SCF is deterministic for a fixed guess, basis, grid and thread count. The energy error scales like the SCF tolerance (energy `conv_tol`, default 1e-9), so tighten it to 1e-10 or below if finite_diff steps are small. DFT integration grids move with the atoms, which adds a small, noise-like roughness to geometry scans. Keep `grids.level` fixed and print it.
- Multiple solutions: RHF/UHF instabilities and symmetry breaking are real features of the method, not bugs. The output depends on the initial guess, so the guess must be a fixed part of the driver. Never pass one run's density matrix to the next, as the scan examples do: EMA's runs are independent.
- Run time: tiny molecules in small bases take about a second, most of it the Python import. Correlated methods (CCSD, CASSCF) and larger bases grow fast; profile before a campaign.
- Version pitfalls: v2.14 made `init_guess_breaksym = 'mix'` a built-in (the example's docstring says so). Other options change between minor releases, so pin 2.14.0 and print the version in each run.
- Sources: https://pyscf.org, https://pyscf.org/user/install.html, https://pyscf.org/user/index.html, https://github.com/pyscf/pyscf, https://github.com/pyscf/pyscf/releases/tag/v2.14.0, https://github.com/pyscf/pyscf/tree/v2.14.0/examples, https://github.com/pyscf/pyscf/blob/v2.14.0/examples/scf/56-h2_symm_breaking.py, https://github.com/pyscf/pyscf/blob/v2.14.0/examples/scf/01-h2o.py, https://github.com/pyscf/pyscf/blob/v2.14.0/examples/scf/17-stability.py, https://github.com/pyscf/pyscf/blob/v2.14.0/examples/dft/24-custom_xc_functional.py, https://pypi.org/project/pyscf/#files, https://anaconda.org/conda-forge/pyscf/files

---

#### RDKit

**What it is.** A cheminformatics toolkit: molecules from SMILES, substructure search, descriptors, fingerprints, 2D depiction, and 3D conformer generation (ETKDG) with the MMFF94 and UFF force fields. C++ with Python wrappers. BSD-3-Clause. Current release **2026.03.6 (GitHub release `Release_2026_03_6`, 2026-08-28)**; the next quarterly release (2026.09) was not out on 2026-09-24. Examples: the "Getting Started with the RDKit in Python" guide (https://www.rdkit.org/docs/GettingStartedInPython.html, section "Working with 3D Molecules") and the RDKit Cookbook (https://www.rdkit.org/docs/Cookbook.html, about 40 recipes, most of them 2D: drawing, SMARTS, descriptors). **The fit is unusual.** RDKit is not a simulator, and most of its API maps a molecule (a discrete object) to a descriptor, which gives an EMA model no continuous inputs. The parts that fit are the 3D ones: a force-field energy as a function of continuous geometric or force-field settings, and conformer search, whose output is random through the ETKDG seed. Descriptor pipelines don't fit and are left out.

**Install on an Intel Mac.** **PyPI has had no macOS x86_64 wheels since 2025.9.3.** 2026.3.x has only `macosx_11_0_arm64` wheels, so `pip install rdkit` on an Intel Mac would fall back to an old version or fail. conda-forge builds `rdkit` 2026.03.6 for osx-64 (Python 3.10–3.14), so use it.
1. Install Miniforge (osx-64) if needed (see PySCF).
2. Create the env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-rdkit -c conda-forge python=3.12 rdkit=2026.03.6
   ```
3. Check:
   ```bash
   ~/miniforge3/envs/ema-rdkit/bin/python -c "import rdkit; print(rdkit.__version__); from rdkit import Chem; from rdkit.Chem import AllChem; m=Chem.AddHs(Chem.MolFromSmiles('CCCCC')); print(AllChem.EmbedMolecule(m, randomSeed=42), AllChem.MMFFOptimizeMolecule(m))"
   ```
   Expect `2026.03.6` and `0 0` (the embedding succeeded, and the minimization converged).

Known problems: none specific. Don't `pip install rdkit` into this env: pip would pull a different build on top of the conda one.
Sources: https://www.rdkit.org/docs/Install.html, https://anaconda.org/conda-forge/rdkit/files, https://pypi.org/project/rdkit/#files (2026.3.6: arm64 only for macOS), https://pypi.org/project/rdkit/2025.9.3/#files

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same conda env as on the Mac (Miniforge Linux installer, then `mamba create -n ema-rdkit -c conda-forge python=3.12 rdkit=2026.03.6`).
2. Alternative: a venv with `pip install rdkit==2026.3.6` (manylinux_2_28 x86_64 wheels exist for cp310 and up). apt's `python3-rdkit` on noble is 202309.3, too old to match the Mac; don't use it.
3. The check is the same as on the Mac.
Sources: https://pypi.org/project/rdkit/#files, https://packages.ubuntu.com/noble/python3-rdkit, https://anaconda.org/conda-forge/rdkit/files

**Preparing the examples for EMA.** A driver, `run.py`, takes the inputs as command-line arguments and prints one number. Molecules are fixed SMILES inside the driver. Integer settings (the number of conformers) arrive as floats and are rounded in the driver, so expect steps in the output. Seeds: `params.randomSeed = 0xf00d + int(os.environ.get("EMA_REPLICATE", "0"))`, with `numThreads = 1` so the result doesn't depend on thread scheduling. The first example is the Getting Started guide's conformer workflow. The second is not a docs recipe: it is built from the documented force-field API (`MMFFGetMoleculeProperties`, `MMFFGetMoleculeForceField`, `MMFFAddTorsionConstraint`, `rdMolTransforms.SetDihedralDeg`), which I checked in the 2026.03.6 source and the `rdForceField` API page.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| "Working with 3D Molecules" (https://www.rdkit.org/docs/GettingStartedInPython.html#working-with-3d-molecules): `EmbedMultipleConfs` with ETKDGv3, then `MMFFOptimizeMoleculeConfs`; the molecule is the Cookbook's ETKDG macrocycle `C(OC(CCCCCCC(OCCSC(CCCCCC1)=O)=O)OCCSC1=O)N1CCOCC1` (https://www.rdkit.org/docs/Cookbook.html, "Conformer Generation with ETKDG") | a stochastic conformer search, with MMFF94 minimization | `n_confs` 30 [5, 300] (log; rounded to an integer); `diel` (MMFF dielectric constant, `SetMMFFDielectricConstant`) 1 [1, 80] (log); `max_iters` 500 [50, 2000] (log) | lowest MMFF94 energy (kcal/mol) among converged conformers | **noisy**: `repeat` shows the seed's spread, largest at small `n_confs`; the minimum decreases with `n_confs` and levels off (a **plateau**); steps from the integer rounding; `diel` smooth and monotone (the electrostatic energy scales like 1/ε); `max_iters` a plateau once minimizations converge, so **possibly negligible** above a few hundred | 5–30 s, growing with `n_confs` *(estimate)* | cli (env python + `run.py`, inputs as args) | regex |
| relaxed two-torsion scan of n-pentane (built from the documented API, see above) | MMFF94 conformational energy; the "pentane interference" | `phi1` 180 [−180, 180]; `phi2` 180 [−180, 180] (C1–C2–C3–C4 and C2–C3–C4–C5, degrees; the other coordinates relaxed with `MMFFAddTorsionConstraint` at force constant 1e4) | MMFF94 energy of the relaxed structure, recomputed **without** the constraint term | periodic, with minima near 60°, 180° and −60° for each torsion; **not additive**: the g+g− corners (+60°, −60°) are penalized (the syn-pentane interaction), so sobol shows an interaction and surface2d shows its location; small **jumps** where a methyl rotor flips during relaxation (nonsmooth); deterministic, with a fixed embedding seed | < 1 s after a ~0.5 s import *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard RDKit 2026.03.6 as EMA command-line models (conformer energies with MMFF94). Run only read-only commands and report: OS, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists, any env named ema-rdkit, and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge env `ema-rdkit` with rdkit=2026.03.6 (osx-64 builds exist; PyPI has no macOS x86_64 wheel after 2025.9.3, so don't pip install on an Intel Mac). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install RDKit on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-rdkit -c conda-forge python=3.12 rdkit=2026.03.6`. Never install into EMA's .venv, never pip install rdkit into this env, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check: `<env>/bin/python -c "import rdkit; print(rdkit.__version__)"`, then embed and MMFF-optimize pentane with randomSeed=42 (expect 0 0). Report the env's absolute python path. Stop at the first error and report it; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install RDKit on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64; ask me first) and the env `ema-rdkit` with python=3.12 rdkit=2026.03.6 from conda-forge, as on my Mac. Don't use apt's python3-rdkit (2023.09). Never use EMA's .venv, never read .env, and ask before any sudo. Check as in Stage 2a and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — RDKit smoke test. In a scratch directory outside the repo, with the ema-rdkit env's python, run the "Working with 3D Molecules" snippet from https://www.rdkit.org/docs/GettingStartedInPython.html: EmbedMultipleConfs on the Cookbook macrocycle SMILES (Cookbook, "Conformer Generation with ETKDG") with ETKDGv3, numConfs 30, randomSeed 0xf00d, numThreads 1; then MMFFOptimizeMoleculeConfs. Run it twice with the same seed and once with another, and time each. Report the lowest energy of each run: the same seed should give identical numbers, and a different seed a different one. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the RDKit conformer-search example for EMA. Enter plan mode first and show me the plan. Write examples/rdkit/confsearch/run.py (RDKit 2026.03.6): the Cookbook macrocycle SMILES, AddHs, ETKDGv3 with randomSeed = 0xf00d + int(os.environ.get("EMA_REPLICATE", "0")) and numThreads 1, EmbedMultipleConfs with numConfs = round(--n_confs); MMFF94 properties with SetMMFFDielectricConstant(--diel); for each conformer, MMFFGetMoleculeForceField and Minimize(maxIts=round(--max_iters)). Print `rdkit <version>`, the number of converged conformers, and `min_energy = %.12e` over the converged ones; exit non-zero if none converged or embedding failed. Command-line model like examples/beam/model_args.json, with the ema-rdkit env's absolute python path (not $EMA_PYTHON). Inputs: n_confs 30 [5, 300] scale log, diel 1 [1, 80] scale log, max_iters 500 [50, 2000] scale log. timeout_s 300. Check by hand: the same EMA_REPLICATE gives the same number, and a different one gives a different number. Then `ema profile examples/rdkit/confsearch/model.json -n 5` and report time per run at the nominal values and at n_confs 300. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the RDKit pentane torsion example. Plan mode first. Write examples/rdkit/pentane_torsions/run.py (RDKit 2026.03.6): n-pentane from SMILES CCCCC, AddHs, EmbedMolecule with a fixed randomSeed 42 (no EMA_REPLICATE: this model is deterministic), then an MMFF optimization; set the two backbone dihedrals with rdMolTransforms.SetDihedralDeg to --phi1 and --phi2; build the MMFF force field, add MMFFAddTorsionConstraint for both (relative False, min = max = the target, force constant 1e4), and Minimize(maxIts=2000). Then recompute the energy with a fresh force field without constraints and print `energy = %.12e`, plus the achieved dihedrals. Exit non-zero if Minimize doesn't return 0. Inputs: phi1 180 [-180, 180], phi2 180 [-180, 180]. Check by hand: (180, 180) is the lowest of the 9 combinations of 60/180/-60, and (60, -60) is clearly higher than (60, 60). Then `ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first RDKit campaign. For examples/rdkit/confsearch/model.json, write campaign.json with repeat (n_points 3, replicates 5), then curve1d on n_confs (n 12), and morris (n_traj 6), with the noise measured by repeat applied. Run `ema estimate`, report the run count and time, and ask me before `ema run`. Afterwards report: the seed noise at each repeat point, whether curve1d shows the minimum leveling off in n_confs (and any steps from the rounding), the morris ranking, and whether max_iters is (possibly) negligible. Then suggest (don't run) surface2d on phi1 × phi2 for examples/rdkit/pentane_torsions. Stop and report.
```

```text
Stage 6 — RDKit troubleshooting. An EMA RDKit model (examples/rdkit/<example>) fails or gives odd values. Diagnose read-only first: run the driver by hand in a copied run directory with the ema-rdkit env's python and EMA_REPLICATE=0. Check for: embedding failures (EmbedMultipleConfs returns fewer ids; macrocycles may need useRandomCoords or more attempts, ask me first); MMFF parameters missing (MMFFHasAllMoleculeParams); minimizations that don't converge (a non-zero return, or not_converged 1); nondeterminism with the same seed (numThreads not 1); torsion constraints not reached (print achieved dihedrals); a wrong interpreter path in model.json; a regex that doesn't match. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License BSD-3-Clause.
- Threads: `EmbedMultipleConfs` and `MMFFOptimizeMoleculeConfs` run single-threaded by default (`numThreads` 1). Keep them that way, since EMA runs in parallel.
- Determinism and noise: ETKDG is random. With a fixed `randomSeed` (and one thread) it is reproducible, and the docs' examples use `randomSeed=0xf00d`. Seed from `EMA_REPLICATE` so that `repeat` measures the search's spread, and pass that spread as `output_noise`. The torsion scan is deterministic, but a relaxed scan can switch to another local minimum between neighbouring inputs, which shows up as small jumps.
- Integer settings (`n_confs`, `max_iters`) arrive as continuous inputs. Round them in the driver and expect flat steps between integers.
- Intel Mac: PyPI's last macOS x86_64 wheel is 2025.9.3. Use conda-forge.
- Version pitfalls: `AllChem` functions move to `rdDistGeom` and `rdForceFieldHelpers` over time, and the Cookbook notes ETKDG versions. Pin 2026.03.6 and print `rdkit.__version__`.
- Sources: https://www.rdkit.org, https://github.com/rdkit/rdkit, https://github.com/rdkit/rdkit/releases/tag/Release_2026_03_6, https://www.rdkit.org/docs/Install.html, https://www.rdkit.org/docs/GettingStartedInPython.html, https://www.rdkit.org/docs/Cookbook.html, https://www.rdkit.org/docs/source/rdkit.ForceField.rdForceField.html, https://github.com/rdkit/rdkit/blob/Release_2026_03_6/Code/GraphMol/ForceFieldHelpers/Wrap/rdForceFields.cpp, https://pypi.org/project/rdkit/#files, https://anaconda.org/conda-forge/rdkit/files, https://packages.ubuntu.com/noble/python3-rdkit

---

#### OpenMM

**What it is.** A toolkit for molecular dynamics: a C++ library with Python bindings, running on CPU, CUDA, OpenCL and HIP. It reads Amber, CHARMM, GROMACS and PDB inputs through `openmm.app`. MIT for most of the code, LGPL for the CUDA and OpenCL platforms (conda-forge lists it as LGPL-3.0-or-later). Current release **8.6.1 (GitHub release 2026-09-11)**. Examples: `examples/python-examples/` in https://github.com/openmm/openmm has six scripts (`simulatePdb.py`, `simulateAmber.py`, `simulateCharmm.py`, `simulateGromacs.py`, `simulateTinker.py`, `argon-chemical-potential.py`) with their input files. The User Guide's "Running Simulations" chapter walks through them (https://docs.openmm.org/latest/userguide/application/02_running_sims.html), and the OpenMM Cookbook (https://openmm.github.io/openmm-cookbook/) has more notebooks **(count unconfirmed)**. Fit: an MD average is a **noisy** output. The seed must come from `EMA_REPLICATE`, `repeat` comes first, and the runs have to be long enough that the noise is smaller than the effects being looked for. Every MD integrator's default seed is 0, which picks a new random seed each time a Context is created. A single-point energy is the deterministic alternative.

**Install on an Intel Mac.** conda-forge has `openmm` 8.6.1 for osx-64 (Python 3.11–3.14). PyPI has `macosx_10_12_universal2` wheels for cp311–cp314, which include x86_64, and an x86_64 wheel for cp310. On an Intel Mac the platforms are CPU, Reference, and OpenCL (Apple's deprecated OpenCL, "included with the operating system"). Use CPU.
1. Install Miniforge (see PySCF).
2. Create the env, with `pymbar` for the argon example:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-openmm -c conda-forge python=3.12 openmm=8.6.1 pymbar=4.2.0
   ```
3. Check:
   ```bash
   OPENMM_CPU_THREADS=1 ~/miniforge3/envs/ema-openmm/bin/python -m openmm.testInstallation
   ```
   It lists the platforms and compares their forces. Expect Reference, CPU and OpenCL, with small differences.

Known problems: OpenCL on a Mac with only integrated Intel graphics may fail or be slower than CPU. Force `Platform.getPlatformByName('CPU')` in every driver.
Sources: https://docs.openmm.org/latest/userguide/application/01_getting_started.html, https://anaconda.org/conda-forge/openmm/files, https://pypi.org/project/openmm/#files, https://github.com/openmm/openmm/releases/tag/8.6.1

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same conda env (Miniforge Linux installer, then `mamba create -n ema-openmm -c conda-forge python=3.12 openmm=8.6.1 pymbar=4.2.0`). No GPU is needed for these examples.
2. Alternative: a venv with `pip install openmm==8.6.1 pymbar` (manylinux_2_34 x86_64 wheels). apt's `python3-openmm` on noble is 8.0.0, too old. Don't use it.
3. The check is the same (`python -m openmm.testInstallation`, which lists CPU and Reference on a GPU-less instance).
Sources: https://docs.openmm.org/latest/userguide/application/01_getting_started.html, https://pypi.org/project/openmm/#files, https://packages.ubuntu.com/noble/python3-openmm

**Preparing the examples for EMA.** Each example becomes a driver, `run.py`, with the inputs as command-line arguments. In each driver:
- Choose the CPU platform with `{'Threads': '1'}`.
- Remove the `DCDReporter`.
- Replace the stdout `StateDataReporter` with a loop that collects `getState(getEnergy=True).getPotentialEnergy()` every N steps after an equilibration period, and print the mean as `output = %.12e` (kJ/mol).
- Seed from `EMA_REPLICATE`: `integrator.setRandomNumberSeed(1000 + rep)`, `context.setVelocitiesToTemperature(T, 1000 + rep)`, and `numpy.random.seed(rep)` where the script uses NumPy random numbers.
- Treat NaN coordinates or energies (a blown-up integration) as a failure: exit non-zero.
- Keep the example's input files (`.pdb`, `.psf`, parameter files) as static files next to `model.json`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/python-examples/simulateCharmm.py` (https://github.com/openmm/openmm/blob/8.6.1/examples/python-examples/simulateCharmm.py) with `ala_ala_ala.psf/.pdb`, `charmm22.rtf/.par`: tri-alanine in vacuum, `NoCutoff`, HBonds constraints, `LangevinMiddleIntegrator` | Langevin MD of a small peptide | `T` (K) 300 [250, 400]; `friction` (1/ps) 1 [0.1, 10] (log); `dt` (fs) 2 [1, 5]; run fixed at 25,000 steps of equilibration plus 100,000 of production | mean potential energy over production (kJ/mol) | **noisy** (`repeat` first); nearly **linear, increasing in `T`** (equipartition plus anharmonic terms); `friction` should be **negligible** for an equilibrium average (it changes only the sampling efficiency, so the noise); a small bias growing with `dt`, and **failed runs** (blow-ups) possible near 5 fs | 5–20 s on one thread *(estimate)* | cli (env python + `run.py`, inputs as args) | regex |
| `examples/python-examples/simulatePdb.py` (https://github.com/openmm/openmm/blob/8.6.1/examples/python-examples/simulatePdb.py) with `input.pdb` (8,867 atoms, 8,283 of them in water), `amber19-all.xml` + `amber19/tip3pfb.xml`, PME | the **deterministic alternative**: a single-point energy, no dynamics | `cutoff` (nm) 1.0 [0.8, 1.4]; `ewald_tol` 5e-4 [1e-5, 1e-3] (log) (`createSystem(..., nonbondedCutoff=..., ewaldErrorTolerance=...)`) | potential energy of the unminimized structure (kJ/mol) | small effects: PME makes the electrostatic energy nearly independent of the cutoff, and `ewald_tol` sets its accuracy; the hard Lennard-Jones cutoff gives **many tiny jumps** as atom pairs cross it, which finite_diff sees as roughness while `repeat` shows zero noise, a lesson in deterministic nonsmoothness | 2–5 s, mostly force-field setup *(estimate)* | cli | regex |
| `examples/python-examples/argon-chemical-potential.py` (https://github.com/openmm/openmm/blob/8.6.1/examples/python-examples/argon-chemical-potential.py): 216 Lennard-Jones argon atoms, alchemical insertion at 5 λ values, MBAR (needs `pymbar`) | the excess chemical potential of a Lennard-Jones fluid | `rho` (reduced density ρσ³) 0.85 [0.5, 0.95]; `T` (K) 300 [150, 400]; `collision` (1/ps) 5 [1, 50] (log) | free energy of inserting one argon atom (kT), from the script's last line | **noisy** (the script reports its own MBAR error, which `repeat` should match roughly); **strongly increasing and convex in `rho`** (packing); smaller in kT as `T` rises; `collision` **negligible** apart from noise | 20–60 s *(estimate)* | cli | regex on `Free energy of inserting argon particle: (\S+) \+-` |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard OpenMM 8.6.1 examples into EMA as command-line models. Run only read-only commands and report: OS, CPU architecture, the number of cores, whether conda/mamba (Miniforge) exists, any env named ema-openmm, a GPU if any (system_profiler SPDisplaysDataType on macOS, nvidia-smi on Linux), and free disk space. Don't install anything, and don't read .env. Recommend a route: conda-forge env `ema-openmm` with openmm=8.6.1 and pymbar=4.2.0 (osx-64 and linux-64 builds exist), using the CPU platform with one thread per run. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install OpenMM on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-openmm -c conda-forge python=3.12 openmm=8.6.1 pymbar=4.2.0`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `OPENMM_CPU_THREADS=1 <env>/bin/python -m openmm.testInstallation` and report the platforms it lists and their force differences. Report the env's absolute python path. Stop at the first error and report it; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install OpenMM on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64; ask me first), then the env `ema-openmm` with python=3.12 openmm=8.6.1 pymbar=4.2.0 from conda-forge. Don't use apt's python3-openmm (8.0.0). Never use EMA's .venv, never read .env, and ask before any sudo. Check with python -m openmm.testInstallation (expect CPU and Reference) and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — OpenMM smoke test. In a scratch directory outside the repo, download examples/python-examples/simulateCharmm.py and its files (ala_ala_ala.psf, ala_ala_ala.pdb, charmm22.rtf, charmm22.par) from the 8.6.1 tag of github.com/openmm/openmm. Run it with the ema-openmm env's python and OPENMM_CPU_THREADS=1, and time it. Then run a copy with the DCDReporter removed, the CPU platform forced, and 100000 steps, and time that too. Report the last reporter lines, both wall times, and the steps per second. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the OpenMM tri-alanine example for EMA. Enter plan mode first and show me the plan. Source: examples/python-examples/simulateCharmm.py (OpenMM 8.6.1). Write examples/openmm/ala3_langevin/run.py: the same PSF, PDB and CHARMM22 files (static files next to model.json), NoCutoff, HBonds; LangevinMiddleIntegrator(--T kelvin, --friction /ps, --dt fs); the CPU platform with Threads 1; seed = 1000 + int(os.environ.get("EMA_REPLICATE", "0")) for integrator.setRandomNumberSeed and setVelocitiesToTemperature; minimizeEnergy, 25000 equilibration steps, then 100000 production steps, sampling the potential energy every 100 steps. Print `openmm <version>` and `mean_PE = %.12e` (kJ/mol); exit non-zero if any energy is NaN. No DCD output. Command-line model like examples/beam/model_args.json with the ema-openmm env's absolute python path (not $EMA_PYTHON); env OPENMM_CPU_THREADS=1, OMP_NUM_THREADS=1. Inputs: T 300 [250, 400], friction 1 [0.1, 10] scale log, dt 2 [1, 5]. timeout_s 600. Check by hand: the same EMA_REPLICATE gives the same number twice (report whether it's bitwise identical), and different replicates differ. Then `ema profile examples/openmm/ala3_langevin/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the OpenMM single-point example. Plan mode first. Source: examples/python-examples/simulatePdb.py (OpenMM 8.6.1). Write examples/openmm/pdb_energy/run.py: input.pdb as a static file, ForceField('amber19-all.xml', 'amber19/tip3pfb.xml'), createSystem(nonbondedMethod=PME, nonbondedCutoff=--cutoff nm, ewaldErrorTolerance=--ewald_tol, constraints=HBonds), the CPU platform with Threads 1, positions from the PDB, NO minimization and NO dynamics; print `energy = %.12e` (kJ/mol). Inputs: cutoff 1.0 [0.8, 1.4], ewald_tol 5e-4 [1e-5, 1e-3] scale log. Check by hand that two runs give identical numbers. Then `ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare the OpenMM argon chemical-potential example. Plan mode first. Source: examples/python-examples/argon-chemical-potential.py (OpenMM 8.6.1). Copy it into examples/openmm/argon_mu/run.py, changing only: reduced_density, temperature and collision_rate come from --rho, --T (K) and --collision (1/ps); numpy.random.seed(rep) before the random initial positions and integrator.setRandomNumberSeed(1000 + rep) for each LangevinIntegrator, where rep = int(os.environ.get("EMA_REPLICATE", "0")); the Context uses the CPU platform with Threads 1; the final print uses %.6f. Keep the step counts. Output regex on `Free energy of inserting argon particle: (\S+) \+-`. Inputs: rho 0.85 [0.5, 0.95], T 300 [150, 400], collision 5 [1, 50] scale log. timeout_s 900. Check pymbar's API (subsample_correlated_data, MBAR.compute_free_energy_differences) against pymbar 4.2.0. Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first OpenMM campaign. For examples/openmm/ala3_langevin/model.json, write campaign.json with repeat first (n_points 3, replicates 6), then morris (n_traj 6) and curve1d on T (n 9), with the noise measured by repeat applied to both. Run `ema estimate`, report the run count and time, and ask me before `ema run` (use -j equal to the physical cores minus one). Afterwards report: the noise (standard deviation of mean_PE across replicates) against the change over the T range; whether friction is (possibly) negligible; any failed runs and their dt; and whether curve1d on T is monotone and close to linear. Expected: T dominant and nearly linear, friction negligible within the noise, possible failures at large dt. Stop and report.
```

```text
Stage 6 — OpenMM troubleshooting. An EMA OpenMM model (examples/openmm/<example>) fails, is slow, or is noisier than expected. Diagnose read-only first: run the driver by hand in a copied run directory with the ema-openmm env's python and EMA_REPLICATE=0. Check for: the wrong platform (print context.getPlatform().getName()); threads (OPENMM_CPU_THREADS, and the Threads property); NaN energies or "Particle coordinate is NaN" (dt too large, bad minimization); force-field file not found (amber19 files need OpenMM >= the version the example targets); missing seeds (two runs with the same EMA_REPLICATE differ); pymbar API or version errors; a regex that doesn't match. For noise, compare the replicate spread with the run length and suggest a longer production run rather than more replicates when the spread swamps the effects. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License MIT, with LGPL for the GPU platforms. Fine for use as an external program.
- Threads: the CPU platform uses every logical core unless `OPENMM_CPU_THREADS` or the `Threads` property says otherwise. Set 1.
- Determinism and noise: an MD average is a random variable. Seed every integrator and velocity draw from `EMA_REPLICATE` (default seed 0 means a new random seed for each Context). Whether the CPU platform is **bitwise** reproducible for the same seed is **(unconfirmed)**: its docs say the single-precision CPU and CUDA platforms "are not deterministic" in one case, so let `repeat` decide. The noise falls roughly as one over the square root of the production length, so a longer run is usually a better buy than more replicates.
- Run time: a 33-atom vacuum peptide runs thousands of steps per second on one core, while the 8,867-atom PME system in `simulatePdb.py` runs far slower. MD of that system (10,000 steps of 4 fs) is minutes per run on one CPU thread *(estimate)*, which is why it appears here only as a single-point energy. On AWS, a GPU instance would change that, but EMA's parallel runs and a single GPU don't mix well; stay on CPU.
- Version pitfalls: the 8.6.1 examples use `amber19-all.xml`. Older releases shipped `amber14`, so match the example to the installed version. apt's 8.0.0 is too old.
- Sources: https://openmm.org, https://github.com/openmm/openmm, https://github.com/openmm/openmm/releases/tag/8.6.1, https://github.com/openmm/openmm/tree/8.6.1/examples/python-examples, https://github.com/openmm/openmm/blob/8.6.1/examples/README.md, https://docs.openmm.org/latest/userguide/application/01_getting_started.html, https://docs.openmm.org/latest/userguide/application/02_running_sims.html, https://docs.openmm.org/latest/userguide/library/04_platform_specifics.html, https://openmm.github.io/openmm-cookbook/, https://pypi.org/project/openmm/#files, https://anaconda.org/conda-forge/openmm/files, https://anaconda.org/conda-forge/pymbar/files, https://packages.ubuntu.com/noble/python3-openmm

---

#### LAMMPS

**What it is.** Large-scale Atomic/Molecular Massively Parallel Simulator (Sandia): classical MD for atoms, molecules, metals and coarse-grained particles, driven by its own input-script language. C++. GPL-2.0-only. Releases: the current **stable is 22 Jul 2025, update 6 (`stable_22Jul2025_update6`, 2026-09-03)**. Feature releases continue (`patch_2Sep2026`, 2026-09-03, a "stable release candidate"). conda-forge's `lammps` 2025.07.22 is built from `stable_22Jul2025_update6` (build 6, 2026-09-21). Examples: the `examples/` directory of https://github.com/lammps/lammps has about 90 entries (`melt`, `crack`, `indent`, `min`, `ELASTIC`, `VISCOSITY`, `peptide`, ...), described at https://docs.lammps.org/Examples.html. Each has `in.*` scripts and reference `log.*` files. Fit: good, with two caveats. Most examples are MD, so their outputs are noisy averages (seed from `EMA_REPLICATE`). And LAMMPS uses `$` for its own variables, so pass inputs with `-var` rather than templating the script.

**Install on an Intel Mac.** conda-forge builds `lammps` 2025.07.22 for osx-64, in `nompi`, `mpich` and `openmpi` variants for Python 3.11–3.14. Its executable is `lmp` (with `lmp_serial` as a link in the `nompi` build). LAMMPS's own macOS page recommends Homebrew (`brew install lammps`), which has no Intel bottles now; don't use it. PyPI's `lammps` 2025.7.22.4.0 has a `macosx_11_0_x86_64` wheel, but it is **unofficial** (built by the `lammps-wheel` project), and whether it installs an `lmp` executable is **(unconfirmed)**.
1. Install Miniforge (see PySCF).
2. Create the env with the serial build (EMA does the parallel work):
   ```bash
   ~/miniforge3/bin/mamba create -n ema-lammps -c conda-forge python=3.12 "lammps=2025.07.22=*nompi*"
   ```
3. Get the examples from the same tag, since the conda package may not include them **(unconfirmed)**:
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -LO https://github.com/lammps/lammps/archive/refs/tags/stable_22Jul2025_update6.tar.gz
   tar xf stable_22Jul2025_update6.tar.gz
   ```
   The archive is a few hundred MB **(size unconfirmed)**. Downloading only `examples/melt/` and `examples/ELASTIC/` from GitHub is enough.
4. Check:
   ```bash
   ~/miniforge3/envs/ema-lammps/bin/lmp -h | head -20
   cd ~/src/lammps-stable_22Jul2025_update6/examples/melt && OMP_NUM_THREADS=1 ~/miniforge3/envs/ema-lammps/bin/lmp -in in.melt
   ```
   `-h` prints the version and the installed packages (expect MANYBODY, which provides `pair_style sw`, and OPENMP). The melt run should end near the reference log's step 250 (Temp 1.66, Press 5.75). Those exact values come from a 2021 build, so expect the same to a few digits, not bitwise.

Known problems: `lmp` with no `-in` reads its script from stdin, and EMA gives it `/dev/null`, so always pass `-in`. The OPENMP package is compiled in, so set `OMP_NUM_THREADS=1`.
Sources: https://docs.lammps.org/Install_mac.html, https://docs.lammps.org/Install_conda.html, https://anaconda.org/conda-forge/lammps/files, https://github.com/conda-forge/lammps-feedstock/blob/main/recipe/meta.yaml, https://github.com/conda-forge/lammps-feedstock/blob/main/recipe/build.sh, https://pypi.org/project/lammps/#files, https://github.com/lammps/lammps/releases

**Install on AWS (Ubuntu 24.04 EC2).**
1. Preferred: the same conda env as on the Mac (Miniforge Linux installer, then `lammps=2025.07.22=*nompi*`), so both machines run the same version.
2. apt fallback: `sudo apt install lammps` installs `lmp` version 20240207 (the stable 7 Feb 2024) on noble, older than conda's. The two examples below should run on it **(unconfirmed)**, but results won't match the Mac's to the last digit.
3. Docker: the official `lammps/lammps` images on Docker Hub were last updated in 2022 (`stable_29Sep2021_*`, `patch_7Jan2022_*`). Too old; don't use them.
4. The check is the same.
Sources: https://docs.lammps.org/Install_linux.html, https://packages.ubuntu.com/noble/lammps, https://hub.docker.com/r/lammps/lammps/tags

**Preparing the examples for EMA.** Command-line variables are the clean route. In a copy of the example's script, define each input as an `index`-style variable (`variable rho index 0.8442`). A `-var rho <value>` on the command line then takes precedence, because LAMMPS ignores a later `index` definition of an existing variable. The command is `["<env>/bin/lmp", "-in", "in.ema", "-var", "rho", "$rho", ..., "-nocite", "-log", "log.lammps"]`. The script stays a static file, so its `${...}` and `$(...)` need no `$$`.
- Seeds: `variable rep getenv EMA_REPLICATE`, then a velocity seed of `$(87287+v_rep)`. Check how LAMMPS formats an immediate `$()` value as an integer (the `$(expr:%.0f)` form) **(unconfirmed)**. Set `EMA_REPLICATE=0` when running by hand, since `getenv` returns an empty string otherwise.
- Output: add `print "EMA_OUTPUT ${value}"` at the end and read it with a regex on stdout (screen output goes to stdout).
- Limitation: `-var` values that start with `-` are misread as switches. Keep inputs positive, or shift them.
- Potential files the example needs (`Si.sw`) are static files, or a template when an input lives in them. `Si.sw` has no `$`, so it needs no escaping.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `examples/melt/in.melt` (https://github.com/lammps/lammps/blob/stable_22Jul2025_update6/examples/melt/in.melt): fcc Lennard-Jones solid melting under NVE; shrunk from 10³ to 6³ cells (864 atoms), 1,000 steps of equilibration, then 2,000 of production with `fix ave/time` on the pressure; `neigh_modify every 1 delay 0 check yes` instead of the example's `check no` | Lennard-Jones melt, reduced units | `rho` (lattice density) 0.8442 [0.70, 1.00]; `T0` (initial temperature of `velocity create`) 3.0 [1.0, 4.0]; `rc` (cutoff, σ) 2.5 [2.0, 3.5] | time-averaged pressure (reduced units) | **noisy** (seeded velocities; `repeat` first); pressure **strongly increasing in `rho`** (steep, near a power law at high density) and increasing in `T0`; `rc` a modest monotone effect (a truncated attraction, no tail correction); a change of slope where low `T0` and high `rho` leave the crystal unmelted (a **kink** or regime boundary for curve1d on `T0`); interaction between `rho` and `T0` | 3–6 s *(estimate, scaled from the example's log: 4,000 atoms × 250 steps in 1.6 s)* | cli (conda `lmp`, inputs as `-var`) | regex `EMA_OUTPUT (\S+)` |
| `examples/ELASTIC/in.elastic` with `init.mod`, `potential.mod`, `displace.mod`, `Si.sw` (https://github.com/lammps/lammps/tree/stable_22Jul2025_update6/examples/ELASTIC): elastic constants of Stillinger–Weber silicon at 0 K by finite strains and energy minimization; 192 atoms | lattice statics; finite-difference elastic constants | `up` (strain step) 1e-6 [1e-8, 1e-3] (log), via `-var` after changing `init.mod`'s `variable up equal` to `index`; `epsilon` (eV) 2.1683 [1.5, 3.0] (log); `sigma` (Å) 2.0951 [1.9, 2.3] (log); `lambda` 21.0 [15, 30] (the last three in a templated `Si.sw`) | bulk modulus (GPa), from the script's `Bulk Modulus = ...` line; second model: `C44all` | **deterministic** (fixed `atomjiggle` seed); an exact **power law** B ∝ ε σ⁻³ (SW's energy and length scales, after `box/relax`): `linear_coeffs(log_output=True)` should find exponents 1 and −3; **`lambda` negligible for B** (a hydrostatic strain doesn't change bond angles, so the three-body term drops out), but not for C44 (the second model), a clean test of `negligible`; `up` negligible in the middle of its range, with **roundoff noise at tiny `up`** and nonlinear drift at large `up`, so curve1d on `up` shows a plateau between two rough ends | 1–2 s *(estimate)* | cli (`-var up` + templated `Si.sw`) | regex `Bulk Modulus = (\S+) GPa` |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard LAMMPS (stable 22Jul2025 update 6) examples into EMA as command-line models. Run only read-only commands and report: OS, CPU architecture, the number of cores, whether conda/mamba (Miniforge) exists, any env named ema-lammps, any lmp or lmp_serial on PATH (and its version from `lmp -h | head`), Homebrew (brew --version; don't use it), Docker, and free disk space. Don't install anything, and don't read .env. Recommend a route: the conda-forge env `ema-lammps` with lammps=2025.07.22 in its nompi build (osx-64 and linux-64 exist; it is stable_22Jul2025_update6). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install LAMMPS on this Intel Mac. Use Miniforge (conda-forge only, never defaults): `mamba create -n ema-lammps -c conda-forge python=3.12 "lammps=2025.07.22=*nompi*"`. Never install into EMA's .venv, never use Homebrew, and never read .env. Ask me before installing Miniforge, before any sudo, and before any download over 1 GB. Then download only examples/melt and examples/ELASTIC from the stable_22Jul2025_update6 tag of github.com/lammps/lammps into ~/src/lammps-examples (ask before downloading the full source archive instead). Check: `<env>/bin/lmp -h | head -30` (report the version and whether MANYBODY and OPENMP are listed), then run in.melt with OMP_NUM_THREADS=1 and `-in in.melt` and compare the step-250 line with log.8Apr21.melt.g++.1. Report the absolute path of lmp. Stop at the first error and report; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install LAMMPS on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64; ask me first), then the env `ema-lammps` with "lammps=2025.07.22=*nompi*" from conda-forge, as on my Mac. If conda fails, report and propose (don't run) `sudo apt install lammps` (20240207 on noble). Don't use the lammps/lammps Docker images (last updated 2022). Never use EMA's .venv, never read .env, ask before any sudo. Download the melt and ELASTIC examples and check as in Stage 2a. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — LAMMPS smoke test. In ~/src/lammps-examples, with the ema-lammps env and OMP_NUM_THREADS=1: run melt/in.melt (`lmp -in in.melt -nocite`) and ELASTIC/in.elastic (`lmp -in in.elastic -nocite`, from inside ELASTIC/ so the include files are found). Time both. Report the melt run's last thermo line against the reference log, the ELASTIC run's printed C11all, C12all, C44all and Bulk Modulus (the script's comments give the SW analytical values C11 = 151.4, C12 = 76.4, C44 = 56.4 GPa), and both wall times. Then run in.melt once with `-var foo 1` to confirm that an unused variable doesn't break it. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the LAMMPS melt example for EMA. Enter plan mode first and show me the plan. Source: examples/melt/in.melt (stable_22Jul2025_update6). Write examples/lammps/melt/in.ema, a static copy with: `variable rho index 0.8442`, `variable T0 index 3.0`, `variable rc index 2.5` at the top; `variable rep getenv EMA_REPLICATE`; lattice fcc ${rho}; region 0 6 in each direction; velocity all create ${T0} with a seed of 87287 plus rep (verify the integer formatting of $() against the docs); pair_style lj/cut ${rc} and pair_coeff 1 1 1.0 1.0 ${rc}; neigh_modify every 1 delay 0 check yes; run 1000; then fix ave/time on c_thermo_press over a 2000-step production run; print "EMA_OUTPUT <the average, %.10e>". No dumps. model.json (read docs/guides/input_deck_model.md, examples/beam/model_args.json, examples/cantera/model.json): command [<ema-lammps env's absolute lmp path>, "-in", "in.ema", "-var", "rho", "$rho", "-var", "T0", "$T0", "-var", "rc", "$rc", "-nocite", "-log", "log.lammps"], static file in.ema, env OMP_NUM_THREADS=1, output regex "EMA_OUTPUT (\S+)" on stdout, timeout_s 120. Inputs: rho 0.8442 [0.70, 1.00], T0 3.0 [1.0, 4.0], rc 2.5 [2.0, 3.5]. Check by hand with EMA_REPLICATE=0 twice (identical?) and 1 (different). Then `ema profile examples/lammps/melt/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the LAMMPS ELASTIC example. Plan mode first. Source: examples/ELASTIC (stable_22Jul2025_update6). In examples/lammps/elastic/: static copies of in.elastic, potential.mod and displace.mod; init.mod as a static copy with only `variable up equal 1.0e-6` changed to `variable up index 1.0e-6`; Si.sw as a template (Si.sw.template, rendered to Si.sw) with $epsilon, $sigma and $lambda in the first line's epsilon, sigma and lambda fields (Si.sw has no other `$`; check). Command: [<absolute lmp path>, "-in", "in.elastic", "-var", "up", "$up", "-nocite", "-log", "log.lammps"]. Output regex "Bulk Modulus = (\S+) GPa" on stdout; a second model_c44.json reading "Elastic Constant C44all = (\S+) GPa". Inputs: up 1e-6 [1e-8, 1e-3] scale log, epsilon 2.1683 [1.5, 3.0] scale log, sigma 2.0951 [1.9, 2.3] scale log, lambda 21.0 [15, 30]. number_format ".10g". env OMP_NUM_THREADS=1, timeout_s 120. Check by hand: nominal values reproduce Stage 3's numbers; doubling epsilon doubles B; changing lambda leaves B almost unchanged but moves C44. Then `ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first LAMMPS campaign. For examples/lammps/elastic/model.json (deterministic), write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 8), linear_coeffs with log_output true, and curve1d on up (n 21). Run `ema estimate`, report the run count and time, and ask me before `ema run`. Afterwards report: repeatability, the exponents linear_coeffs finds for epsilon and sigma (expected 1 and -3) and whether power_law is set, whether lambda is flagged negligible, and what curve1d shows at the small and large ends of up. Then suggest (don't run) the same morris for model_c44.json, and a campaign for examples/lammps/melt starting with repeat (n_points 3, replicates 5). Stop and report.
```

```text
Stage 6 — LAMMPS troubleshooting. An EMA LAMMPS model (examples/lammps/<example>) fails or gives odd values. Diagnose read-only first from the run directory's stdout.txt, stderr.txt and log.lammps, then by running the command by hand in a copied run directory with EMA_REPLICATE=0. Check for: "ERROR: Unknown command" or "Illegal ... command" (the version of lmp vs the example's tag); a -var ignored because the script defines that variable in a style other than index (then the script's own value wins silently: print the variable at the top); a -var value that starts with "-"; "Cannot open file" (a static file or an include not copied into the run directory); "Lost atoms" (a timestep or neighbor-list problem at extreme inputs, a real failure region); `getenv` returning an empty string (EMA_REPLICATE unset when run by hand); OMP threads; a missing package in `lmp -h` (pair_style sw needs MANYBODY). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License GPL-2.0-only. Fine for use as an external program, and the `examples/` files may be copied into the repo with their license.
- Parallelism: use the `nompi` conda build and one process per run. The conda build includes the OPENMP package, so set `OMP_NUM_THREADS=1`. MPI domain decomposition changes the summation order, so results would depend on the rank count.
- Determinism and noise: a serial run with the same seed is reproducible on one machine and build **(expected; confirm with `repeat`)**. Different seeds give different MD averages, and the noise falls with the production length. Minimizations (ELASTIC) are deterministic, but their answer depends on `etol`/`ftol`, and a finite-difference strain `up` that is too small is swamped by roundoff (the script's comments say to check that the results don't depend on `up`).
- `$` everywhere: LAMMPS scripts use `$x`, `${name}` and `$(expr)`. Pass inputs with `-var` into `index` variables and keep the scripts static. A templated LAMMPS script would need every `$` doubled.
- Variable styles: `equal`, `string` and several other styles are redefined each time the script reaches them, so they override a command-line `-var`, while an `index` definition is ignored when the variable already exists. Change the example's definition to `index` for each input.
- Version pitfalls: stable releases get updates, and feature releases add and rename commands. Pin `stable_22Jul2025_update6` for both the binary and the examples. apt's 20240207 is older.
- Sources: https://www.lammps.org, https://github.com/lammps/lammps, https://github.com/lammps/lammps/releases, https://docs.lammps.org/Examples.html, https://docs.lammps.org/Run_options.html, https://docs.lammps.org/variable.html, https://docs.lammps.org/Install_mac.html, https://docs.lammps.org/Install_linux.html, https://docs.lammps.org/Install_conda.html, https://github.com/lammps/lammps/tree/stable_22Jul2025_update6/examples/melt, https://github.com/lammps/lammps/tree/stable_22Jul2025_update6/examples/ELASTIC, https://anaconda.org/conda-forge/lammps/files, https://github.com/conda-forge/lammps-feedstock, https://pypi.org/project/lammps/, https://packages.ubuntu.com/noble/lammps, https://hub.docker.com/r/lammps/lammps/tags

---

#### NAMD

**What it is.** NAnoscale Molecular Dynamics (Theoretical and Computational Biophysics Group, UIUC): parallel biomolecular MD with CHARMM and Amber force fields, configured by Tcl config files. C++ on Charm++. **License: the non-open-source "NAMD license", free for "academic, research and internal business purposes only".** Commercial use needs a commercial license, and redistribution is forbidden ("Licensee agrees to provide the Software only to any other person or entity who has registered with Illinois"). Current release **3.0.3 (2026-07-24, a bugfix release)**; 3.0.2 is from 2025-08-27. Binaries **require registration and login** at https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD, so **no script or Claude Code prompt can install NAMD**: the analyst downloads it by hand. Examples: the NAMD Tutorial (ubiquitin; https://www.ks.uiuc.edu/Training/Tutorials/namd-index.html). Its files are a public archive, `namd-tutorial-files.tar.gz` (155 MB), with 14 sections, `1-1-build` to `3-2-pullcf`, browsable at https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/. Fit: medium. Like every MD code the outputs are noisy averages, NAMD's default seed comes from the clock, and the tutorial systems are larger than EMA's ideal (1,231 atoms in implicit solvent is the smallest), so runs take tens of seconds.

**Install on an Intel Mac.** NAMD 3.0.3 has a `MacOS-universal-multicore` build ("Apple silicon and Intel-based"), so it runs natively. There is no conda-forge package (`namd` is absent from conda-forge) and no Homebrew formula to rely on.
1. Register and log in at the download page, and download the 3.0.3 `MacOS-universal-multicore` archive by hand. The file name is probably `NAMD_3.0.3_MacOS-universal-multicore.tar.gz` **(unconfirmed)**.
2. Unpack it outside the EMA repo:
   ```bash
   mkdir -p ~/opt && cd ~/opt
   tar xzf ~/Downloads/NAMD_3.0.3_MacOS-universal-multicore.tar.gz
   ```
   If macOS refuses to run the unsigned binary, clear the quarantine flag on that directory only: `xattr -dr com.apple.quarantine ~/opt/NAMD_3.0.3_MacOS-universal-multicore` **(unconfirmed whether it's needed)**.
3. Get the tutorial files (a public download of 155 MB, no registration):
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -LO https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files.tar.gz
   tar xzf namd-tutorial-files.tar.gz
   ```
4. Check:
   ```bash
   ~/opt/NAMD_3.0.3_MacOS-universal-multicore/namd3 +p1 --version 2>&1 | head -5
   ```
   (whether `--version` is accepted is **(unconfirmed)**; otherwise run a config and read the `Info: NAMD 3.0.3` line).

Known problems: the multicore build uses threads (`+p1` for one). The release notes' quick test (`namd3 src/alanin`, a 66-atom system) refers to the source tree, and whether the binary archive includes `src/alanin` is **(unconfirmed)**.
Sources: https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD, https://www.ks.uiuc.edu/Research/namd/3.0.3/notes.html, https://www.ks.uiuc.edu/Research/namd/license.html, https://www.ks.uiuc.edu/Training/Tutorials/namd-index.html

**Install on AWS (Ubuntu 24.04 EC2).** The same manual route: download `Linux-x86_64-multicore` (3.0.3) on your own machine after logging in, and copy it to the instance with `scp`. The registration page doesn't suit `curl` from the instance. Unpack it into `~/opt`, and check as on the Mac. There is no apt package and no conda package. NVIDIA's NGC catalogue has NAMD containers for GPUs, but they need an NGC account and are not suited to EMA's serial CPU runs **(not checked in detail)**. Get the tutorial files with `curl` as on the Mac.
Sources: https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD, https://www.ks.uiuc.edu/Research/namd/3.0.3/notes.html

**Preparing the examples for EMA.** NAMD configs are Tcl. Inputs go into a template of the tutorial's config, in which every literal `$` must be written `$$` (`$$temperature`, `$$outputname`), and EMA's inputs are `$T`, `$ion`, and so on.
- Seed: add `seed [expr {1000 + $$env(EMA_REPLICATE)}]`. Tcl's `env` array reads the environment; check that NAMD's Tcl exposes it **(unconfirmed)**.
- Static files: the structure and parameter files the config names (`ubq.psf`, `ubq.pdb`, `par_all27_prot_lipid.inp`). Rewrite their `../common/...` paths to bare file names, since static files are copied flat into the run directory.
- Command: `["<abs path>/namd3", "+p1", "ubq.conf"]`.
- Parser: NAMD prints `ENERGY:` lines to stdout (the tutorial's log has the columns `TS BOND ANGLE DIHED IMPRP ELECT VDW BOUNDARY MISC KINETIC TOTAL TEMP POTENTIAL TOTAL3 TEMPAVG`). An isolated `python` output parser (`parse.py`) averages `POTENTIAL` over the production steps.
- Files: the tutorial config writes a DCD every 250 steps and restarts every 500. Turn them off, or leave them in the run directory, which is disposable.
- Licensing: don't commit the NAMD binary, and check the tutorial files' terms before committing them **(unconfirmed)**. The model directory can instead name them as files downloaded in Stage 2.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `1-4-gbis/ubq_gbis_eq.conf` (https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/1-4-gbis/ubq_gbis_eq.conf): ubiquitin (1,231 atoms) in generalized Born implicit solvent, Langevin at 310 K; shortened from 100 minimization + 2,500 MD steps to 100 + 1,000 (2 fs) | implicit-solvent protein MD | `T` (K) 310 [290, 350]; `ion` (`ionConcentration`, M) 0.3 [0.0, 1.0]; `damping` (`langevinDamping`, 1/ps) 1 [0.2, 5] (log) | mean `POTENTIAL` (kcal/mol) over the last 500 steps | **noisy**: a 1 ps average of a 1,231-atom protein fluctuates by tens of kcal/mol *(estimate)*, so `repeat` must come first; `T` clearly increasing (heat capacity); `ion` a monotone screening effect, possibly **buried in the noise** (the honest outcome to report); `damping` **negligible** for the average | 20–60 s on one core *(estimate: the tutorial's log shows 0.074 s/step on one 2011-era CPU with NAMD 2.8)* | cli (`namd3 +p1`, templated config) | python parser (average of `ENERGY:` lines) |
| the same config, **minimization only** (`minimize 500`, no `run`, no `reinitvels`) | the deterministic alternative: the GBIS energy after minimization | `ion` 0.3 [0.0, 1.0]; `cutoff` 14 [10, 18] Å (with `switchdist` = cutoff − 1 and `pairlistdist` = cutoff + 2, set by the template); `alphaCutoff` 12 [8, 12] Å (it must stay ≤ `cutoff`) | final `POTENTIAL` after minimization | deterministic with `+p1` **(unconfirmed; check with `repeat`)**; `ion` monotone; `cutoff` smooth but not negligible (switched interactions, long range); small **jumps** where the minimizer lands in a different local minimum (nonsmooth) | 10–30 s *(estimate)* | cli | python parser (last `ENERGY:` line) |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I want to onboard NAMD 3.0.3 (non-open-source license; I download it myself after registering) as an EMA command-line model. Run only read-only commands and report: OS, CPU architecture, the number of cores, whether a NAMD directory exists under ~/opt or ~/Downloads (ls only; report the file names you find), whether ~/src/namd-tutorial-files exists, and free disk space. Don't install or download anything, don't try to download NAMD (it needs a login), and don't read .env. Tell me which NAMD archive to download for this machine (MacOS-universal-multicore on a Mac, Linux-x86_64-multicore on Linux). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — set up NAMD on this Intel Mac. I have downloaded the NAMD 3.0.3 MacOS-universal-multicore archive to ~/Downloads myself (tell me if you can't find it; don't try to download it). Unpack it into ~/opt (ask me first). Never put NAMD files in the EMA repo, never install into EMA's .venv, and never read .env. If macOS blocks the binary, report the exact message and ask me before clearing the quarantine flag on that one directory. Then, after asking me, download the public NAMD tutorial files (https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files.tar.gz, 155 MB) into ~/src and unpack them. Check by running namd3 +p1 on a copy of 1-4-gbis/ubq_gbis_eq.conf shortened to `minimize 10` and `run 100`, in a scratch copy of the tutorial tree, and report the `Info: NAMD` version line, the Benchmark line (s/step), and the last ENERGY: line. Ask before any sudo. Stop at the first error and report; don't improvise. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — set up NAMD on this AWS EC2 instance (Ubuntu 24.04, x86_64). I will copy the NAMD 3.0.3 Linux-x86_64-multicore archive to ~/ myself with scp; wait for it, and don't try to download NAMD. Unpack it into ~/opt (ask first), download and unpack the public tutorial files into ~/src as on the Mac (ask first), and check with the same shortened GBIS run. Never put NAMD files in the EMA repo, never use EMA's .venv, never read .env, and ask before any sudo. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — NAMD smoke test. In a scratch copy of ~/src/namd-tutorial-files, run 1-4-gbis/ubq_gbis_eq.conf unchanged with namd3 +p1, and time it; then once more with +p2. Report the Benchmark lines (s/step), total wall times, the RANDOM NUMBER SEED line of each run, and the last ENERGY: line of each. Confirm that the two runs had different seeds (the clock) and different energies. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the NAMD GBIS MD example for EMA. Enter plan mode first and show me the plan. Source: namd-tutorial-files/1-4-gbis/ubq_gbis_eq.conf (NAMD 3.0.3). In examples/namd/ubq_gbis_md/ write ubq.conf.template: a copy with every literal `$` doubled to `$$` (read docs/guides/input_deck_model.md on `$`), `set temperature $T`, ionConcentration $ion, langevinDamping $damping, file paths as bare names (ubq.psf, ubq.pdb, par_all27_prot_lipid.inp), dcdfreq and restartfreq off, outputEnergies 10, minimize 100, reinitvels, run 1000, and a seed from Tcl: `seed [expr {1000 + $$env(EMA_REPLICATE)}]` (check that NAMD accepts it; report the RANDOM NUMBER SEED line). Don't copy the NAMD binary or the tutorial's structure files into the repo; tell me how you plan to reference them (static files by absolute path, or copied at run time) and ask me first. Output: an isolated python parser, parse.py, that averages the POTENTIAL column of the ENERGY: lines of stdout.txt with TS > 600. Command [<absolute path of namd3>, "+p1", "ubq.conf"]. Inputs: T 310 [290, 350], ion 0.3 [0.0, 1.0], damping 1 [0.2, 5] scale log. timeout_s 600. Check by hand: EMA_REPLICATE=0 twice (identical?) and 1 (different). Then `ema profile examples/namd/ubq_gbis_md/model.json -n 3` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare the NAMD GBIS minimization example. Plan mode first. Same source and file handling as Stage 4.1, in examples/namd/ubq_gbis_min/: minimize 500, no reinitvels and no run; inputs ion 0.3 [0.0, 1.0], cutoff 14 [10, 18], alphaCutoff 12 [8, 12], with switchdist and pairlistdist computed in the template's Tcl from $cutoff (switchdist = cutoff - 1, pairlistdist = cutoff + 2; use `$$` for Tcl's own variables). Output: POTENTIAL of the last ENERGY: line (the python parser). Check by hand that two runs at the nominal values give identical numbers, and that alphaCutoff > cutoff is refused by NAMD or should be (tell me which). Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first NAMD campaign. Start with examples/namd/ubq_gbis_min/model.json (deterministic): repeat (n_points 2, replicates 2) and morris (n_traj 5). Then for examples/namd/ubq_gbis_md/model.json: repeat only (n_points 3, replicates 5). Run `ema estimate` for both, report run counts and hours, and ask me before each `ema run`. Afterwards report: whether the minimization is repeatable, the morris ranking; for the MD model the replicate spread against the change in mean POTENTIAL across the T range. Recommend (don't run) whether a morris on the MD model is worth its cost, or whether the production run must be longer first. Stop and report.
```

```text
Stage 6 — NAMD troubleshooting. An EMA NAMD model (examples/namd/<example>) fails. Diagnose read-only first from the run directory's stdout.txt and stderr.txt, then by running the rendered ubq.conf by hand in a copied run directory with EMA_REPLICATE=0. Check for: a template error (a single `$` that EMA tried to substitute: a missing input name, or a Tcl variable not doubled); "Unable to open" (a structure or parameter path that still points at ../common); FATAL ERROR on a parameter (cutoff, switchdist, pairlistdist, or alphaCutoff inconsistent); the seed line (env(EMA_REPLICATE) not set, or not visible to Tcl); macOS blocking the binary; +p threads fighting EMA's -j; a parser that finds no ENERGY: lines (outputEnergies too large). Report the cause and a proposed fix. Ask before changing anything.
```

**Gotchas and sources.**
- License: non-open-source. Registration is required, use is limited to academic, research and internal business purposes, redistribution is forbidden, and publications must acknowledge NAMD. Never commit NAMD binaries or source-derived files into EMA, and never automate the download.
- Parallelism: run `+p1` per EMA run. The multicore build otherwise takes threads, and Charm++ load balancing changes the summation order.
- Determinism and noise: the default seed comes from the clock, so set `seed` from `EMA_REPLICATE`. MD averages are noisy, and the tutorial runs (picoseconds) are far too short for small effects. Measure the noise first, and lengthen the production run before adding inputs.
- Run time: tens of seconds per run for the smallest tutorial system *(estimate)*. The explicit-water tutorials (`1-2-sphere`, `1-3-box`) are several times larger. Leave them to AWS, or don't use them.
- `$` in configs: Tcl uses `$` everywhere, so a template needs `$$`. Or keep the config static and have a tiny Tcl `source`d file hold only the inputs (that file is then the only template).
- Version pitfalls: the tutorial's example output is from NAMD 2.8 (2011). Keywords still work in 3.0 **(unconfirmed for every keyword)**, but numbers won't match the old logs exactly.
- Sources: https://www.ks.uiuc.edu/Research/namd/, https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD, https://www.ks.uiuc.edu/Research/namd/license.html, https://www.ks.uiuc.edu/Research/namd/3.0.3/notes.html, https://www.ks.uiuc.edu/Training/Tutorials/namd-index.html, https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/, https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/1-4-gbis/ubq_gbis_eq.conf, https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/1-4-gbis/example-output/ubq_gbis_eq.log, https://anaconda.org/conda-forge/namd (not found)

---

#### VMD

**What it is.** Visual Molecular Dynamics (TCBG, UIUC): a program for visualizing and analysing molecular structures and trajectories, scriptable in Tcl and Python, and able to run without graphics (`vmd -dispdev text -e script.tcl`). C++. **License: the non-open-source VMD license** ("academic, research and internal business purposes only"; registration required; redistribution forbidden). Its plugins are under the UIUC Open Source License. Releases on the download page: **VMD 2.0.0 (2026-03-25)** and 2.0.1 alpha (2026-04-21), with Linux x86_64 builds and an Apple Silicon build (2.0.0b1). VMD 1.9.4 alpha (2023-06-08) is the **last release with a macOS x86_64 build** ("MacOS 10.15, x86_64"). Examples: the VMD tutorials (https://www.ks.uiuc.edu/Training/Tutorials/), and the NAMD tutorial's `rmsd.tcl` (`1-2-sphere/rmsd.tcl`) and `residue_rmsd.tcl` (`2-1-rmsd/`). **VMD is not a model and doesn't fit EMA by itself:** it maps nothing from scalar inputs to a scalar output. Its only role here is an **output step** after an MD run from NAMD, OpenMM or LAMMPS: read the trajectory and reduce it to one number (a mean RMSD or radius of gyration). **For EMA, MDAnalysis (conda-forge 2.10.0) or mdtraj (1.11.1) in the MD package's own env is simpler**, and so is OpenMM's own `getState`: they are open source, install from conda-forge on osx-64, and can run inside a Python driver or an isolated EMA output parser. Use VMD only if the analyst already has VMD Tcl scripts worth keeping.

**Install on an Intel Mac.**
1. Register and log in at https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=VMD, and download **VMD 1.9.4 alpha, "MacOS 10.15, x86_64"** by hand. VMD 2.0 has no Intel Mac build. The exact file name and whether 1.9.4a runs on the current macOS are **(unconfirmed)**.
2. Install the app bundle into `~/Applications` (not system-wide). The text-mode command is the `vmd` launcher script inside the bundle; its path is **(unconfirmed)**, so find it with `find ~/Applications -name 'vmd*' -maxdepth 4`.
3. Check:
   ```bash
   "<path to vmd launcher>" -dispdev text -eofexit < /dev/null
   ```
   It should print the VMD banner and exit.
4. The Python alternative on osx-64 is conda-forge's `vmd-python` 3.1.7 (a Python module built from VMD's source; license "VMD"). It installs with `mamba create -n ema-vmd -c conda-forge python=3.12 vmd-python=3.1.7`. Whether it installs for Python 3.12 is **(unconfirmed)**.

Sources: https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=VMD, https://www.ks.uiuc.edu/Research/vmd/, https://www.ks.uiuc.edu/Research/vmd/current/LICENSE.html, https://anaconda.org/conda-forge/vmd-python/files

**Install on AWS (Ubuntu 24.04 EC2).**
1. Download **VMD 2.0.0, LINUX_64 (RHEL 8+)** by hand after logging in, and copy it to the instance with `scp`. The build is for RHEL 8+ with OpenGL, CUDA and OptiX. Whether it runs text-mode on Ubuntu 24.04 without an X server or a GPU is **(unconfirmed)**. VMD's Linux archives usually have a `./configure` step that sets the install directory; install under `~/opt`, not `/usr/local`, so no sudo is needed **(unconfirmed for 2.0)**.
2. conda-forge alternatives on linux-64: `vmd` 1.9.3 (uploaded 2025-04-01) and `vmd-python` 3.1.7. What the `vmd` package contains (full program or text mode) is **(unconfirmed)**.
3. Check: `vmd -dispdev text -eofexit < /dev/null`.
Sources: https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=VMD, https://anaconda.org/conda-forge/vmd/files, https://anaconda.org/conda-forge/vmd-python/files

**Preparing the examples for EMA.** VMD is used as the second step of a two-step command. A wrapper script `run.sh` in the model directory (hashed by EMA) runs the MD program, then `vmd -dispdev text -e analysis.tcl -args <psf> <dcd>`, where `analysis.tcl` prints `EMA_OUTPUT <value>` and exits. Keep `analysis.tcl` a static file, so its Tcl `$` needs no escaping. The table's structure column describes the whole pipeline. The MDAnalysis equivalent is a five-line isolated `python` output parser, which avoids a second licensed program and a shell wrapper.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| NAMD `1-4-gbis` MD (as in the NAMD section, with `dcdfreq 50` switched back on) + `1-2-sphere/rmsd.tcl` (https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/1-2-sphere/rmsd.tcl), changed to print the mean backbone RMSD instead of writing `rmsd.dat` | protein backbone drift from the start structure in implicit solvent | `T` (K) 310 [290, 350]; `ion` (M) 0.3 [0.0, 1.0] | mean backbone RMSD (Å) over the trajectory | **noisy** (seeded MD; `repeat` first); increasing in `T`; `ion` probably within the noise over a 2 ps run; a short run mostly measures the thermal fluctuation, not unfolding, so expect a small, smooth effect | NAMD run + 2–5 s for VMD start-up and analysis *(estimate)* | cli (`run.sh`: `namd3` then `vmd -dispdev text`) | regex `EMA_OUTPUT (\S+)` |
| OpenMM tri-alanine (OpenMM section, Stage 4.1) writing a DCD every 1,000 steps + a VMD script using `measure rgyr` | peptide compactness | `T` 300 [250, 400]; `friction` 1 [0.1, 10] (log) | mean radius of gyration (Å) | **noisy**; weakly increasing with `T`; `friction` **negligible** | OpenMM run + 2–5 s *(estimate)* | cli (`run.sh`) | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine (read-only). I may use VMD (non-open-source license; I download it myself after registering) as a text-mode analysis step after MD runs in EMA. Run only read-only commands and report: OS, CPU architecture, whether a VMD app or vmd launcher exists (look in /Applications, ~/Applications, ~/opt; `which vmd`), whether conda/mamba exists and any env with mdanalysis or mdtraj, and whether ema-namd or ema-openmm models exist in examples/. Don't install or download anything, and don't read .env. Tell me plainly whether MDAnalysis or mdtraj in the MD package's env would do the same job, and which VMD build fits this machine (1.9.4a MacOS x86_64 on an Intel Mac; 2.0.0 LINUX_64 on Linux). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — set up VMD on this Intel Mac. I have downloaded VMD 1.9.4 alpha for MacOS x86_64 to ~/Downloads myself; don't try to download it. Install it into ~/Applications only (ask me first; no sudo, no Homebrew). Never put VMD files in the EMA repo, never install into EMA's .venv, and never read .env. Find the text-mode launcher inside the bundle and check it with `<launcher> -dispdev text -eofexit < /dev/null`, and report its absolute path and the version banner. If macOS blocks it, report the message and ask me before changing anything. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b — set up VMD on this AWS EC2 instance (Ubuntu 24.04). I will scp VMD 2.0.0 LINUX_64 to ~/ myself; wait for it. Unpack and install it under ~/opt without sudo (read its README or configure script first and show me the install settings before running them). Check with `vmd -dispdev text -eofexit < /dev/null` and report whether it starts without X or a GPU. If it needs system libraries, list them and ask me before any `sudo apt install`. Never use EMA's .venv, never read .env. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — VMD smoke test. In a scratch directory, use the NAMD tutorial's 1-4-gbis example output (ubq.psf from common/example-output and ubq_gbis_eq.dcd from 1-4-gbis/example-output, both in ~/src/namd-tutorial-files). Write a scratch copy of 1-2-sphere/rmsd.tcl that loads them (mol new ubq.psf; mol addfile ubq_gbis_eq.dcd waitfor all), computes the backbone RMSD per frame as the original does, prints `EMA_OUTPUT <mean>` and quits. Run it with `vmd -dispdev text -e rmsd_mean.tcl` and time it. If MDAnalysis is available in some conda env, compute the same mean with it and compare. Report both numbers and the times. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — add a VMD RMSD step to the NAMD GBIS example. Plan mode first. Only after examples/namd/ubq_gbis_md works (NAMD Stage 4.1). Create examples/namd/ubq_gbis_rmsd/ sharing that example's template, with dcdfreq 50, a static analysis.tcl (the Stage 3 script, taking the psf and dcd names from -args), and a run.sh wrapper that runs namd3 +p1 ubq.conf and then `<absolute vmd launcher> -dispdev text -e analysis.tcl -args ubq.psf <outputname>.dcd`, exiting non-zero if either step fails. The command is ["/bin/sh", "run.sh"] or run.sh itself (see how docs/guides/input_deck_model.md treats scripts the command names, so the hash covers run.sh). Output regex "EMA_OUTPUT (\S+)" on stdout. Inputs: T 310 [290, 350], ion 0.3 [0.0, 1.0]. Also write, for comparison, model_mda.json with no VMD: an isolated python output parser using MDAnalysis from a conda env (ask me before creating that env). Then `ema profile ... -n 3` for both and report the time VMD adds. Stop and report; don't run a campaign.
```

```text
Stage 5 — first campaign with the VMD step. For examples/namd/ubq_gbis_rmsd/model.json, write campaign.json with repeat only (n_points 3, replicates 4). Run `ema estimate` and ask me before `ema run`. Report the replicate spread of the mean RMSD against the change across T, whether the VMD and MDAnalysis outputs agree on the same run directories, and the time per run spent in VMD. Recommend (don't act on) whether to keep VMD or switch to MDAnalysis. Stop and report.
```

```text
Stage 6 — VMD troubleshooting. The VMD step of an EMA model fails. Diagnose read-only first from stdout.txt and stderr.txt of a run directory, then by running the vmd command by hand in a copy of it. Check for: VMD trying to open a display (missing -dispdev text); the script not exiting (a missing `quit`/`exit`, so the run hits its timeout); stdin (EMA gives /dev/null, so use -e, not a pipe); `-args` misparsed; a DCD that doesn't exist yet or is empty (dcdfreq larger than the run); psf/dcd atom-count mismatches; the launcher path in run.sh. Report the cause and a proposed fix. Ask before changing anything.
```

**Gotchas and sources.**
- License: non-open-source. Registration is required, use is noncommercial or internal, and redistribution is forbidden. Never commit VMD into the repo or automate its download.
- It isn't a model: VMD adds nothing EMA needs that MDAnalysis, mdtraj or the MD package's own reporters can't do, and it costs a second licensed install, a shell wrapper, and a few seconds of start-up per run *(estimate)*.
- Intel Mac: only the 1.9.4 alpha (2023) has an x86_64 macOS build. VMD 2.0 dropped it.
- Headless use: `-dispdev text` for no graphics. EMA's stdin is `/dev/null`, so pass scripts with `-e`, and end them with `quit`.
- Determinism: the analysis itself is deterministic. The noise comes from the MD run before it.
- `$`: VMD scripts are Tcl. Keep them static files, not templates.
- Sources: https://www.ks.uiuc.edu/Research/vmd/, https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=VMD, https://www.ks.uiuc.edu/Research/vmd/current/LICENSE.html, https://www.ks.uiuc.edu/Training/Tutorials/, https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/1-2-sphere/rmsd.tcl, https://www.ks.uiuc.edu/Training/Tutorials/namd/namd-tutorial-files/2-1-rmsd/, https://anaconda.org/conda-forge/vmd/files, https://anaconda.org/conda-forge/vmd-python/files, https://anaconda.org/conda-forge/mdanalysis/files, https://anaconda.org/conda-forge/mdtraj/files

---

### 4.11 Biology, medicine, and biomechanics: PhysiCell, COBRApy, CellBender, Scanpy, OpenSim, SimVascular

Desk research, checked 2026-09-24. Nothing here was installed or run. Versions and platform facts come from the GitHub release and tag APIs, PyPI's JSON file lists, and anaconda.org's file lists for conda-forge and opensim-org, all read today. Every run time is an estimate from the example's size, marked *(estimate)*, and must be confirmed with `ema profile`. **(unconfirmed)** marks what I could not verify.

Notes common to the group:
- **Only some of these are simulators.** PhysiCell (agent-based), OpenSim (multibody dynamics with muscles) and SimVascular's 0D/1D solvers (hemodynamics) are simulators in the usual sense. COBRApy solves a linear program, so its output is piecewise linear by construction. Scanpy and CellBender are **data-analysis pipelines**: EMA can probe how a pipeline's result depends on its tuning parameters on a fixed dataset, which is a legitimate use, but the "model" is the pipeline plus the data. Each section says so.
- **Stochastic codes.** PhysiCell, CellBender (neural-network training) and Scanpy's Leiden clustering use random numbers with a seed. EMA passes `EMA_REPLICATE` (0 for ordinary designs, 1, 2, ... for `repeat`) in the environment of command-line programs, not as a template placeholder (`src/ema/core/models/cli.py`, `BUILTIN_NAMES`). So each of these needs a small driver that reads `EMA_REPLICATE` and sets the seed. With a fixed seed per replicate the output is a deterministic but rough function of the inputs (changing an input shifts the random stream): `repeat` measures the scatter, and `output_noise` must be passed to the shape diagnostics.
- **Integer outputs** (cell counts, number of clusters, cells called) make plateaus and jumps everywhere. `nonsmooth` and `curve1d` will report them; that is correct, not a bug.
- **Intel Mac facts found today:** PyPI has no macOS x86_64 wheels for `torch` after 2.2.2, or for `numba`/`llvmlite` after 0.62.1, but **conda-forge builds `pytorch` 2.13.0 and `numba` 0.67/0.68rc1 for osx-64**, so the Intel routes below use Miniforge. conda-forge also builds a real GCC (`gcc`/`gxx` 16.2.0) for osx-64, which PhysiCell needs for OpenMP. OpenSim's newest wheel is `macosx_15_0_universal2`, which needs macOS 15; this machine (Darwin 23.6) is macOS 14.
- **AWS instance.** A `c7i.xlarge` (4 vCPU, 8 GB) is enough for every laptop configuration below with `-j 4`; a `c7i.2xlarge` for `-j 8`. CellBender on a full (untrimmed) dataset needs a GPU instance such as `g4dn.xlarge` (one NVIDIA T4) **(unconfirmed current price and availability by region)**. SimVascular's 3D solver (svMultiPhysics) is out of scope for EMA-sized runs; if it is ever tried, use a `c7i.8xlarge` or larger.

---

#### PhysiCell

**What it is.** An open-source, physics-based, agent-based simulator of multicellular systems in 2D and 3D: each cell is an agent with a cycle, death, volume, motility and secretion, coupled to diffusing substrates solved by BioFVM. C++ (C++11) with OpenMP. License BSD-3-Clause (`licenses/PhysiCell.txt`). Current release **1.14.2 (20 January 2025)**; it is still the latest tag and `VERSION.txt` on `master` and `development` today, although the repository was pushed to on 2026-09-24. Sample projects live in `sample_projects/` of https://github.com/MathCancer/PhysiCell and are populated with `make <name>`; `make list-projects` lists 18 plus 6 intracellular ones (`template`, `biorobots-sample`, `cancer-biorobots-sample`, `cancer-immune-sample`, `celltypes3-sample`, `heterogeneity-sample`, `pred-prey-farmer`, `virus-macrophage-sample`, `worm-sample`, `interaction-sample`, `mechano-sample`, `rules-sample`, `physimess-sample`, `custom-division-sample`, `asymmetric-division-sample`, `immune-function-sample`, `episode-sample`, ...). Each project's settings are one XML file, `config/PhysiCell_settings.xml`, with a `<user_parameters>` block, and the binary takes that file's path as its only argument (`main.cpp`: `load_PhysiCell_config_file( argv[1] )`).
Fit with EMA: good, with caveats. Runs take tens of seconds to minutes, the output is an integer count, and the model is stochastic, so `repeat` is essential and the diagnostics must be told the noise.

**Install on an Intel Mac.** There are no binaries and no conda package; you compile it. PhysiCell's README says macOS users must set `PHYSICELL_CPP` to an "OpenMP-enabled g++"; Apple clang does not accept the Makefile's `-fopenmp`. Homebrew's `gcc` is out (Tier 3, no Intel bottles), so use conda-forge's GCC for osx-64.
1. Install Miniforge (osx-64) if there is none, as in 4.1.
2. Create an env with GCC 15 and make:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-physicell -c conda-forge gxx=15.3.0 gcc=15.3.0 make
   ```
3. Get the source and build the template project:
   ```bash
   mkdir -p ~/src && cd ~/src
   curl -L -o PhysiCell-1.14.2.tar.gz https://github.com/MathCancer/PhysiCell/archive/refs/tags/1.14.2.tar.gz
   tar xf PhysiCell-1.14.2.tar.gz && mv PhysiCell-1.14.2 PhysiCell-template && cd PhysiCell-template
   conda activate ema-physicell
   ls $CONDA_PREFIX/bin/*g++*        # find the compiler's name
   export PHYSICELL_CPP="$CONDA_PREFIX/bin/g++ -Wl,-rpath,$CONDA_PREFIX/lib"
   make template && make
   ```
4. Check: `./project` runs the template (5 cells, 7200 min) and writes `output/`.

Known problems: whether the `gxx` package installs a plain `g++` name on osx-64 (rather than only `x86_64-apple-darwin13.4.0-g++`) is **(unconfirmed)**; the `ls` finds it. The Makefile does not pass `LDFLAGS`, so the binary may not find `libgomp.1.dylib` at run time ("Library not loaded"); the `-Wl,-rpath` in `PHYSICELL_CPP` is meant to fix that **(unconfirmed that conda's osx-64 `libgcc` ships `libgomp`)**. The Makefile uses `-march=native`, so a binary built on one machine may not run on an older CPU. Fallbacks: (a) Docker Desktop with an `ubuntu:24.04` image pinned by digest, building with `build-essential` inside it (the AWS recipe), and the container as the command; (b) Apple clang with conda-forge `llvm-openmp` (`-Xpreprocessor -fopenmp -lomp`), which needs Makefile edits.
Sources: https://github.com/MathCancer/PhysiCell (README, NOTE 1), https://github.com/MathCancer/PhysiCell/releases/tag/1.14.2, https://github.com/MathCancer/PhysiCell/blob/1.14.2/Makefile, https://anaconda.org/conda-forge/gxx (osx-64 15.3.0 and 16.2.0 builds), https://anaconda.org/conda-forge/llvm-openmp.

**Install on AWS (Ubuntu 24.04 EC2).** Ubuntu's GCC 13 has OpenMP, so this is the easy platform.
1. Compiler and tools:
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential git
   ```
2. Source, one copy per project (`make <project>` overwrites `main.cpp`, `custom_modules/` and `config/`):
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone --depth 1 --branch 1.14.2 https://github.com/MathCancer/PhysiCell.git PhysiCell-template
   cd PhysiCell-template && make template && make -j 4
   ```
3. Check: `./project` completes and prints `total agents: ...` lines.
Docker fallback: the same steps in a Dockerfile `FROM ubuntu:24.04@sha256:<digest>`. There is no official PhysiCell image **(unconfirmed; none found)**.
Sources: https://github.com/MathCancer/PhysiCell, https://packages.ubuntu.com/noble/build-essential.

**Preparing the examples for EMA.** The recipe:
- Build each sample project in its own copy of the source tree, and copy its binary into `examples/physicell/<example>/`, so the version hash covers it.
- Make `config/PhysiCell_settings.xml` a `string.Template` (the XML has no `$`, so nothing needs escaping) rendered to `config/PhysiCell_settings.xml` in the run directory. Render `config/cells.csv` (if the project uses it) as a placeholder-free template to `config/cells.csv`, since static files are copied flat.
- In the template: set `<omp_num_threads>1</omp_num_threads>`; turn `<SVG><enable>` off and set `<full_data><interval>` to `max_time` (file output dominates otherwise); shorten `max_time` where noted.
- Seed: a driver `run.py` run with `$EMA_PYTHON` (standard library only) replaces the `<random_seed>` value in the rendered XML with `1000 + EMA_REPLICATE`, then runs the binary with `config/PhysiCell_settings.xml`. The output folder `output` is created by PhysiCell itself (`create_output_directory` in `modules/PhysiCell_settings.cpp`).
- Output: every sample's `main.cpp` prints `total agents: N` through `display_simulation_status`; a regex with `"match": "last"` reads the final one. For a per-type count, add a few lines at the end of the copied `main.cpp` that count live cells of one type and print `EMA_OUTPUT <count>`.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `make template` (`sample_projects/template/`, https://github.com/MathCancer/PhysiCell/tree/1.14.2/sample_projects/template) | 5 cells growing in 2D, flow-cytometry-separated cycle (phase durations 300, 480, 240, 60 min), apoptosis 5.31667e-05 1/min, 7200 min | G0/G1 duration 300 [150, 900] (log); S duration 480 [240, 720]; apoptosis rate 5.3e-5 [1e-5, 5e-4] (log) | final `total agents` | decreasing in both durations and in apoptosis rate; roughly exponential growth, so ln N is close to linear in 1/(cycle time) and in the death rate (`linear_coeffs` with `log_output` fits well; not a power law); integer steps and seed noise (`repeat`) | 5–30 s *(estimate)* | cli (`$EMA_PYTHON run.py`, binary in model dir) | regex `total agents: (\d+)`, last |
| `make virus-macrophage-sample` (`sample_projects/virus_macrophage/`) | 1000 epithelial cells, 10 infected, 50 macrophages; virus (D = 1e3 µm²/min) and interferon diffuse; 2880 min | `number_of_macrophages` 50 [10, 150] (integer); `fraction_released_at_death` 1.0 [0.2, 1.0]; virus `diffusion_coefficient` 1e3 [1e2, 1e4] (log) | live epithelial cells at the end (added `EMA_OUTPUT` print) | infection either spreads or is contained: a threshold in macrophage count and virus diffusion, so `curve1d` and `nonsmooth` should show a steep, noisy transition; interaction between macrophages and diffusion; large seed noise near the threshold | 30 s–3 min *(estimate)* | cli | regex `EMA_OUTPUT (\S+)` |
| `make heterogeneity-sample` (the default `make`; `sample_projects/heterogeneity/`) | 2D tumour of cancer cells whose proliferation scales with a per-cell oncoprotein drawn from a truncated normal; oxygen-limited; `max_time` 64800 min shortened to 7200 | `oncoprotein_mean` 1 [0.5, 1.5]; `oncoprotein_sd` 0.25 [0, 0.5]; `tumor_radius` 250 → 100 fixed; cycle rate 0.00072 [0.0004, 0.0012] 1/min | final `total agents` | increasing in the mean and the cycle rate, weak in the sd (possibly negligible); product-like interaction of mean and rate (log output helps); seed noise | 1–5 min at 7200 min *(estimate)*; the full 45 days is much longer | cli | regex `total agents: (\d+)`, last |

**Claude Code prompts.**

```text
Stage 1 — check the machine for PhysiCell (read-only). I want to onboard PhysiCell 1.14.2 sample projects into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, Homebrew version (don't use it on an Intel Mac), Docker (docker version, whether the daemon runs), compilers on PATH (cc --version, g++ --version, and whether g++ is really Apple clang), make, and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, a conda-forge env `ema-physicell` with gxx/gcc 15.3.0 and make (Apple clang lacks OpenMP), with Docker ubuntu:24.04 + build-essential as the fallback; on Ubuntu 24.04, apt build-essential. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install PhysiCell on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-physicell -c conda-forge gxx=15.3.0 gcc=15.3.0 make`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Download https://github.com/MathCancer/PhysiCell/archive/refs/tags/1.14.2.tar.gz into ~/src and unpack it as ~/src/PhysiCell-template. In the env, find the GCC C++ compiler (ls $CONDA_PREFIX/bin/*g++*), set PHYSICELL_CPP to "<that compiler> -Wl,-rpath,$CONDA_PREFIX/lib", run `make template` and `make`. Check that ./project starts, prints "total agents", and that `otool -L project` resolves libgomp. Stop at the first error and report it with the command's output; don't improvise workarounds (if -fopenmp or libgomp fails, report and propose the Docker fallback, don't run it). Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install PhysiCell on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before any sudo, then `sudo apt-get install -y build-essential git`. Never touch EMA's .venv, and never read .env. Clone tag 1.14.2 of https://github.com/MathCancer/PhysiCell.git three times, into ~/src/PhysiCell-template, ~/src/PhysiCell-virus and ~/src/PhysiCell-heterogeneity, and in each run `make template` / `make virus-macrophage-sample` / `make heterogeneity-sample` followed by `make -j 4`. Report the three binaries' names and paths and g++ --version. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — PhysiCell smoke test. In ~/src/PhysiCell-template (built in Stage 2), copy config/PhysiCell_settings.xml to a scratch file, set omp_num_threads to 1, turn SVG output off, set the full_data interval to 7200, and run `time ./project <scratch xml>` twice with the same random_seed and once with a different seed. Report the last "total agents" line of each run, the wall times, and whether the two same-seed runs agree exactly. Don't change anything in EMA. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare PhysiCell's template project for EMA. Enter plan mode first and show me the plan. Source: sample_projects/template of PhysiCell 1.14.2 (built in ~/src/PhysiCell-template). Create examples/physicell/template/ with: the compiled binary `project` copied in (so the hash covers it); PhysiCell_settings.template (from config/PhysiCell_settings.xml, with omp_num_threads 1, SVG off, full_data interval 7200, max_time 7200, and placeholders for the G0/G1 duration (index 0) = 300 [150, 900] (scale log), the S duration (index 1) = 480 [240, 720], and the apoptosis death_rate = 5.31667e-05 [1e-5, 5e-4] (scale log)), rendered to config/PhysiCell_settings.xml; config/cells.csv rendered as a template without placeholders; and run.py, run with $EMA_PYTHON (standard library only), that sets <random_seed> to 1000 + int(os.environ.get("EMA_REPLICATE", "0")) in the rendered XML and runs ./project config/PhysiCell_settings.xml. Output: regex `total agents: (\d+)` on stdout with "match": "last". Follow docs/applications.md, docs/guides/input_deck_model.md and examples/cantera/. Set env OMP_NUM_THREADS=1 and timeout_s 600. Check by hand that nominal inputs reproduce Stage 3's count for the same seed. Then run `.venv/bin/ema profile examples/physicell/template/model.json -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare PhysiCell's virus-macrophage project. Plan mode first. Source: sample_projects/virus_macrophage of PhysiCell 1.14.2 (~/src/PhysiCell-virus). Copy main.cpp's project into a build copy, add at the end of main (before the final save) a loop that counts live cells whose type name is "epithelial cell" and prints `EMA_OUTPUT <count>`; show me the diff before building. Build with the same compiler as Stage 2 and copy the binary (virus-sample) into examples/physicell/virus_macrophage/. Template the settings XML as in Stage 4.1 (omp_num_threads 1, SVG off), with inputs number_of_macrophages = 50 [10, 150], fraction_released_at_death = 1.0 [0.2, 1.0], and the virus diffusion_coefficient = 1e3 [1e2, 1e4] (scale log). Seed through run.py and EMA_REPLICATE as before. Output regex `EMA_OUTPUT (\S+)`. timeout_s 1800. Check by hand one run with 10 and one with 150 macrophages and report both counts. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare PhysiCell's heterogeneity project. Plan mode first. Source: sample_projects/heterogeneity (~/src/PhysiCell-heterogeneity, binary `heterogeneity`). Put it in examples/physicell/heterogeneity/ as in Stage 4.1: max_time 7200 (not 64800; say so in the description), tumor_radius 100, omp_num_threads 1, SVG off; inputs oncoprotein_mean = 1 [0.5, 1.5], oncoprotein_sd = 0.25 [0, 0.5], and the cancer cell's cycle rate = 0.00072 [0.0004, 0.0012]. Seed through run.py. Output: regex `total agents: (\d+)`, last. timeout_s 1800. Then `.venv/bin/ema profile ... -n 5` and report time per run. Stop and report; don't run a campaign.
```

```text
Stage 5 — first PhysiCell campaign. For examples/physicell/template/model.json, write campaign.json with repeat (n_points 3, replicates 4) first, then morris (n_traj 6), and a linear_coeffs with log_output. Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before `ema run` (use -j 4). After it runs, report: the run-to-run scatter repeat measured (relative to the mean count), whether morris ranks apoptosis rate and G0/G1 duration above S duration, the log-output fit's CV R² and signs, and any failed runs. Expected: counts fall with every input; noise of a few percent. Suggest (don't run) curve1d on the G0/G1 duration with output_noise from repeat. Stop and report.
```

```text
Stage 6 — PhysiCell troubleshooting. An EMA PhysiCell model (examples/physicell/<example>) fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt and ema_run.json, then by running run.py by hand in a copied run directory. Check for: "Library not loaded: libgomp" (rpath; don't use DYLD_LIBRARY_PATH), "Illegal instruction" (-march=native binary on another CPU), an XML parse error (a placeholder left unrendered, or an unescaped `$`), config/cells.csv not found (static files are flat; it must be rendered to config/), threads oversubscribed (omp_num_threads not 1, OMP_NUM_THREADS), a seed that doesn't change with EMA_REPLICATE (repeat shows zero scatter), SVG or full-data output left on (slow), and a regex that matches an early "total agents" line. Report the cause and a proposed fix. Ask before changing the env, the binary, or model.json.
```

**Gotchas and sources.**
- License BSD-3-Clause; bundled BioFVM, pugixml and MaBoSS have their own licenses in `licenses/`.
- Threads: set `<omp_num_threads>1</omp_num_threads>` in the template and `OMP_NUM_THREADS=1` in `env`; EMA's `-j N` gives the parallelism. Multithreaded runs are not reproducible even with a fixed seed **(unconfirmed, but likely: cell updates run in parallel loops)**.
- Noise: the seed comes from `<options><random_seed>` (an integer; empty, `random` or `system_clock` seeds from the clock, `modules/PhysiCell_settings.cpp`). Always seed from `EMA_REPLICATE`; a clock seed makes cached runs meaningless. Expect `repeat` to show real scatter and pass `output_noise` to `curve1d`/`nonsmooth`.
- Run time: dominated by diffusion steps (`dt_diffusion` 0.01 min) times voxels, plus cell count. Shorten `max_time` and shrink the domain before anything else; turn off SVG.
- `main.cpp` calls `system("cp ...")` to copy the settings into `output/`; it needs `/bin/sh` and `cp`, which exist in run directories on both platforms.
- Each `make <project>` rewrites the tree, so keep one source copy per project; `make reset` restores the template **(unconfirmed exact target name in 1.14.2; `make data-cleanup` and `make reset` appear in older docs)**.
- Sources: https://github.com/MathCancer/PhysiCell, https://github.com/MathCancer/PhysiCell/releases/tag/1.14.2, https://github.com/MathCancer/PhysiCell/blob/1.14.2/Makefile, https://github.com/MathCancer/PhysiCell/blob/1.14.2/sample_projects/template/config/PhysiCell_settings.xml, https://github.com/MathCancer/PhysiCell/blob/1.14.2/sample_projects/virus_macrophage/config/PhysiCell_settings.xml, https://github.com/MathCancer/PhysiCell/blob/1.14.2/sample_projects/heterogeneity/config/PhysiCell_settings.xml, https://github.com/MathCancer/PhysiCell/blob/1.14.2/modules/PhysiCell_settings.cpp, https://github.com/MathCancer/PhysiCell/blob/1.14.2/modules/PhysiCell_various_outputs.cpp, https://github.com/MathCancer/PhysiCell/blob/1.14.2/licenses/PhysiCell.txt, http://physicell.org, https://anaconda.org/conda-forge/gxx, https://github.com/physicell-training/ws2023/blob/main/agenda.md

---

#### COBRApy

**What it is.** Constraint-based reconstruction and analysis of metabolic networks in Python: flux balance analysis (FBA), flux variability, deletions, production envelopes, sampling, and dynamic FBA. An FBA solve is a linear program (LP). Python; license LGPL-2.0-or-later or GPL-2.0-or-later. Current release **0.32.1 (11 August 2026)**. The bundled "textbook" *E. coli* core model loads with `cobra.io.load_model("textbook")`. The user guide (about 16 notebook pages) is at https://cobrapy.readthedocs.io/en/latest/, source https://github.com/opencobra/cobrapy.
Fit with EMA: excellent and unusual. The optimal growth rate of an LP is a **concave, piecewise-linear** function of the bounds, with kinks where the optimal basis changes and plateaus where a bound stops binding. That is exactly what `nonsmooth` and `curve1d` are built to find, and the answer is known exactly. Infeasible LPs give failed runs, so there is also a failure region. Runs take a second or two, mostly import time.

**Install on an Intel Mac.** conda-forge's `cobra` 0.32.1 is noarch and `swiglpk` 5.0.13 (the GLPK solver) is built for osx-64; PyPI also has Intel wheels for `swiglpk` and `python-libsbml`, so either route works. Use conda for consistency with the other packages.
1. Miniforge as in 4.1.
2. Env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-cobra -c conda-forge python=3.12 cobra=0.32.1 scipy
   ```
   (`scipy` is only for the dFBA example's `solve_ivp`.)
3. Check:
   ```bash
   ~/miniforge3/envs/ema-cobra/bin/python -c "import cobra; m = cobra.io.load_model('textbook'); print(cobra.__version__, m.solver.interface.__name__, m.slim_optimize())"
   ```
   Expect 0.32.1, `optlang.glpk_interface`, and about 0.874.
Known problems: `load_model` looks in a local cache first and may try to download other models from BiGG; "textbook" is bundled **(unconfirmed that it never touches the network)**. pip alternative: `python3.12 -m venv ~/venvs/ema-cobra && ~/venvs/ema-cobra/bin/pip install cobra==0.32.1`.
Sources: https://pypi.org/project/cobra/, https://anaconda.org/conda-forge/cobra, https://anaconda.org/conda-forge/swiglpk, https://pypi.org/project/swiglpk/#files, https://cobrapy.readthedocs.io/en/latest/getting_started.html.

**Install on AWS (Ubuntu 24.04 EC2).** The same Miniforge env (recommended), or a venv with pip (`python3-venv` from apt, then `pip install cobra==0.32.1 scipy`). No Docker needed. Check as on the Mac.
Sources: https://pypi.org/project/cobra/, https://github.com/conda-forge/miniforge.

**Preparing the examples for EMA.** A driver `run.py` run with the env's absolute `python` reads a key = value deck (like `examples/cantera/`), sets reaction bounds, calls `model.slim_optimize(error_value=float("nan"))`, and exits non-zero (after printing the solver status) when the result is NaN, so an infeasible LP is a failed run rather than a number. Print `growth = %.12e`. GLPK's tolerances (about 1e-7 **(unconfirmed default)**) set the output's roughness; the objective value is unique even when the fluxes are not.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| "Simulating with FBA", textbook model (https://cobrapy.readthedocs.io/en/latest/simulating.html) | FBA of *E. coli* core metabolism, maximize `Biomass_Ecoli_core`; the page's solution has glucose uptake 10, oxygen uptake 21.8, growth about 0.874 | `glc` (max glucose uptake, `EX_glc__D_e.lower_bound = -glc`) 10 [0, 20]; `o2` (max oxygen uptake, `EX_o2_e.lower_bound = -o2`) 20 [0, 40]; `atpm` (`ATPM.lower_bound`, 8.39 in the model **(unconfirmed; print it)**) 8.39 [0, 20] | optimal growth rate (1/h) | concave and piecewise linear: nondecreasing in `glc` and `o2`, nonincreasing in `atpm`; a kink and then a plateau in `o2` once oxygen stops binding (near 21.8 at glc 10, and proportionally elsewhere); kinks where the network switches to fermentation; a **failure region** (infeasible) where `glc` is too small to pay `atpm`; `linear_coeffs` fits well but not exactly; `surrogate_check` with a smooth kind should miss the kinks | 1–2 s, mostly import *(estimate)* | cli (env python + `run.py`) | regex `growth = (\S+)` |
| "Dynamic FBA" (https://cobrapy.readthedocs.io/en/latest/dfba.html) | textbook model inside an ODE for biomass and glucose; uptake `-Vmax·G/(Km+G)` with Vmax 10, Km 5; X0 0.1, G0 10; `solve_ivp` BDF, rtol 1e-6, atol 1e-8, to t = 15 with a glucose-depletion event (about t = 5.80) | `vmax` 10 [5, 20]; `km` 5 [0.5, 20] (log); `g0` 10 [5, 20]; `x0` 0.1 [0.02, 0.5] (log) | (a) final biomass; (b) depletion time (second `model.json`) | (a) close to X0 + yield·G0, so nearly linear in `g0` and `x0`, with `vmax` and `km` near-negligible; (b) depletion time falls roughly like ln(G0/X0)/μ: under `log_output`, strong dependence on `x0`, weaker on `vmax`, `km`; ODE tolerance noise at the 1e-6 level; event detection makes (b) slightly rough | 2–20 s (an LP per right-hand-side call; the page calls it "not production ready") *(estimate)* | cli | regex |

**Claude Code prompts.**

```text
Stage 1 — check the machine for COBRApy (read-only). I want to onboard COBRApy 0.32.1 (with its bundled "textbook" E. coli core model) into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture (uname -m), whether conda/mamba (Miniforge) exists and where, any env named ema-cobra, python3 versions on PATH, and free disk space. Don't install anything, and don't read .env. Recommend a route: a conda-forge env `ema-cobra` with python=3.12 cobra=0.32.1 scipy (cobra is noarch; swiglpk has osx-64 and linux-64 builds), or a pip venv as the fallback. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install COBRApy on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-cobra -c conda-forge python=3.12 cobra=0.32.1 scipy`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import cobra; m = cobra.io.load_model('textbook'); print(cobra.__version__, m.solver.interface.__name__, m.slim_optimize())"` and report the env's absolute python path. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install COBRApy on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64 installer) and an env `ema-cobra` with python=3.12 cobra=0.32.1 scipy from conda-forge, the same as on my Mac. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. If conda fails, report and propose (don't run) a venv with pip install cobra==0.32.1 scipy. Check as on the Mac and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — COBRApy smoke test. With the ema-cobra env's python, in a scratch directory outside the EMA repo: load the textbook model, print the bounds of EX_glc__D_e, EX_o2_e and ATPM, run model.optimize() and print the objective value and the fluxes of those three reactions (expect about 0.874, -10 and -21.8), then set EX_o2_e.lower_bound = 0 and print the anaerobic growth, then set ATPM.lower_bound = 100 and print what slim_optimize(error_value=float("nan")) and optimize().status return. Time the whole script. Report all values. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare COBRApy FBA growth as an EMA model. Enter plan mode first and show me the plan. Source: the "Simulating with FBA" page of the COBRApy docs (textbook model). Create examples/cobra/fba_growth/ with a driver run.py and a deck template (follow examples/cantera/ and docs/guides/input_deck_model.md): inputs glc = 10 [0, 20] (sets EX_glc__D_e.lower_bound = -glc), o2 = 20 [0, 40] (EX_o2_e.lower_bound = -o2), atpm = the model's ATPM lower bound [0, 20] (print the nominal first and use it). The driver prints the cobra version, then `growth = %.12e` from slim_optimize(error_value=nan), and exits with status 1 after printing the solver status if the result is NaN (infeasible is a failed run, not a zero). The command is the ema-cobra env's absolute python path and run.py; env OMP_NUM_THREADS=1; timeout_s 60. Check by hand: nominal inputs with o2 = 1000 give about 0.874; doubling glc at o2 = 1000 roughly doubles growth only while ATPM is small relative to it (report the numbers, don't claim). Then `.venv/bin/ema profile examples/cobra/fba_growth/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare COBRApy dynamic FBA. Plan mode first. Source: the "Dynamic FBA (dFBA)" page of the COBRApy docs; copy its code into examples/cobra/dfba/run.py, remove plotting and tqdm, and read vmax = 10 [5, 20], km = 5 [0.5, 20] (scale log), g0 = 10 [5, 20], x0 = 0.1 [0.02, 0.5] (scale log) from a deck. Keep BDF with rtol 1e-6 and atol 1e-8, t_span (0, 15), and the page's termination event. Print `final biomass = %.12e` and `depletion time = %.12e` (NaN, and exit 1, if the event never fires). Write two model.json files sharing the template and driver (model_biomass.json and model_time.json), like examples/beam/'s variants. timeout_s 300. Check by hand that nominal inputs give a depletion time near 5.8, as on the page. Then `.venv/bin/ema profile ... -n 5` for one of them. Stop and report; don't run a campaign.
```

```text
Stage 5 — first COBRApy campaign. For examples/cobra/fba_growth/model.json, write campaign.json with repeat (n_points 2, replicates 2) to confirm determinism, curve1d on o2 (n 41), surface2d on glc × o2 (a 15 × 15 grid), nonsmooth, and morris (n_traj 10). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before `ema run`. After it runs, report: whether repeats are identical, where curve1d finds kinks and whether it reports a plateau above the oxygen requirement, what nonsmooth reports, where the failed (infeasible) runs are, and morris's ranking and monotone flags. Expected: piecewise linear, concave, kinks along lines in the glc × o2 plane, a plateau in o2, failures at small glc with large atpm. Suggest (don't run) a surrogate_check with kind linear to show what a smooth fit misses. Stop and report.
```

```text
Stage 6 — COBRApy troubleshooting. An EMA COBRApy model (examples/cobra/<example>) fails or gives odd values. Diagnose read-only first by running run.py by hand in a copied run directory with the ema-cobra env's python. Check for: a solver other than GLPK being picked up (m.solver.interface), load_model trying to reach the network or a cache directory that isn't writable, infeasible LPs returned as 0 instead of NaN (the driver must exit non-zero), reaction ids that differ from EX_glc__D_e / EX_o2_e / ATPM, sign mistakes on uptake bounds (uptake is a negative lower bound), dFBA runs that hit the timeout (the LP inside every RHS call), and a regex that doesn't match. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License LGPL-2.0-or-later or GPL-2.0-or-later: fine for use as an external program. GLPK itself is GPL.
- Determinism: GLPK's simplex is deterministic for a given input, so `repeat` should show identical outputs. Degenerate optima have several flux vectors with the same growth; read only the objective, never an individual flux, unless it is pinned (pFBA).
- The structure is the point: kinks are real (basis changes). Don't smooth them away, and don't expect a polynomial `surrogate_check` to pass across them.
- Failure region: an infeasible LP must be a failed run (NaN), not a zero growth; otherwise EMA sees a flat plateau instead of a failure region.
- Threads: GLPK is serial; set `OMP_NUM_THREADS=1` anyway (numpy).
- Version pitfalls: reaction ids follow BiGG (`EX_glc__D_e` with two underscores); older tutorials use `EX_glc_e`. `load_model` replaced older `cobra.test.create_test_model`.
- Sources: https://github.com/opencobra/cobrapy, https://github.com/opencobra/cobrapy/releases, https://pypi.org/project/cobra/, https://cobrapy.readthedocs.io/en/latest/, https://cobrapy.readthedocs.io/en/latest/simulating.html, https://cobrapy.readthedocs.io/en/latest/dfba.html, https://cobrapy.readthedocs.io/en/latest/phenotype_phase_plane.html, https://cobrapy.readthedocs.io/en/latest/solvers.html, https://anaconda.org/conda-forge/cobra, https://anaconda.org/conda-forge/swiglpk, https://pypi.org/project/swiglpk/

---

#### CellBender

**What it is.** A deep generative model that removes ambient-RNA and barcode-swapping counts from raw droplet single-cell RNA-seq count matrices (`cellbender remove-background`), trained per dataset by stochastic variational inference (Pyro on PyTorch). Python; license BSD-3-Clause. Current release **0.4.0 (15 August 2026)**; its notes say it "matches the outputs of v0.3.2 and v0.3.0" and only updates Python compatibility to 3.10–3.12. Docs and a quick-start tutorial at https://cellbender.readthedocs.io/en/latest/; the only example is `examples/remove_background/generate_tiny_10x_dataset.py`, which builds a trimmed 10x heart10k dataset (500 cell barcodes, 50,000 empty barcodes, 100 genes).
Fit with EMA: **poor, but possible on the tiny dataset.** This is a data-processing tool with neural-network training, not a simulator. The documentation says the full dataset "requires a CUDA-enabled GPU (e.g. NVIDIA Tesla T4) and takes about 30 minutes", while the tiny dataset finishes "within a minute or two (after 150 epochs)" on a CPU. So the only EMA-sized use is the tiny dataset with few epochs, probing how the result depends on CellBender's settings. A real dataset means AWS GPU only, at about 30 minutes per run, which is a few dozen runs per day, not a campaign.

**Install on an Intel Mac.** PyPI has no macOS x86_64 `torch` wheel after 2.2.2, but conda-forge builds `pytorch` 2.13.0 for osx-64. CellBender itself is pure Python on PyPI (it is not on conda-forge). So: conda for PyTorch and the compiled dependencies, then pip for CellBender alone.
1. Miniforge as in 4.1.
2. Env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-cellbender -c conda-forge python=3.12 pytorch=2.13.0 pyro-ppl pytables anndata scipy pandas matplotlib psutil pip
   ~/miniforge3/envs/ema-cellbender/bin/pip install cellbender==0.4.0
   ```
3. Check:
   ```bash
   ~/miniforge3/envs/ema-cellbender/bin/python -c "import torch, cellbender; print(torch.__version__, cellbender.__version__)"
   ~/miniforge3/envs/ema-cellbender/bin/cellbender remove-background --help | head
   ```
Known problems: pip must see the conda `pytorch` as satisfying `torch` and not try to fetch a wheel (there is none for Intel Macs); if it tries, stop **(unconfirmed that it won't)**. Whether `pyro-ppl` on conda-forge is current enough (CellBender needs `pyro-ppl>=1.8.4`) is **(unconfirmed)**; pip can install it instead. The tutorial's script uses `wget`, which macOS lacks; download the heart10k raw `.h5` with `curl` first (its size is **(unconfirmed)**, likely a few hundred MB).
Sources: https://github.com/broadinstitute/CellBender (README), https://github.com/broadinstitute/CellBender/releases/tag/v0.4.0, https://pypi.org/project/cellbender/, https://pypi.org/project/torch/#files, https://anaconda.org/conda-forge/pytorch, https://cellbender.readthedocs.io/en/latest/installation/index.html.

**Install on AWS (Ubuntu 24.04 EC2).** For the tiny dataset a CPU instance (`c7i.xlarge`) is enough. Preferred: a venv with pip, since Linux `torch` wheels exist:
```bash
sudo apt-get install -y python3-venv        # ask first
python3 -m venv ~/venvs/ema-cellbender
~/venvs/ema-cellbender/bin/pip install cellbender==0.4.0
~/venvs/ema-cellbender/bin/python -c "import torch, cellbender; print(torch.__version__, torch.cuda.is_available())"
```
The default Linux `torch` wheel bundles CUDA libraries (several GB); a CPU-only wheel from `https://download.pytorch.org/whl/cpu` is much smaller **(unconfirmed which torch version the resolver picks)**. For a full dataset use a GPU instance (`g4dn.xlarge`) with the official image `us.gcr.io/broad-dsde-methods/cellbender:0.4.0` (the README lists tags `latest`, `0.3.0`, `0.3.2`, `0.4.0`), pinned by digest and run with `--gpus all` **(unconfirmed that the image still pulls from gcr.io, which Google has been migrating to Artifact Registry)**.
Sources: https://github.com/broadinstitute/CellBender (README, "Using The Official Docker Image"), https://pytorch.org/get-started/locally/, https://pypi.org/project/cellbender/.

**Preparing the examples for EMA.** CellBender is a command-line tool with options, so the inputs can go straight into the command, but the seed can't: CellBender has no `--seed` option and seeds from `consts.RANDOM_SEED = 1234` (`cellbender/remove_background/consts.py`; `run.py` calls `pyro.util.set_rng_seed(consts.RANDOM_SEED)`). So use a driver `run.py` (with the env's python) that sets `cellbender.remove_background.consts.RANDOM_SEED = 1234 + EMA_REPLICATE` and then calls CellBender's command-line entry point with the options **(unconfirmed that patching the constant before the call takes effect)**. The tiny input `.h5ad` (made once by the tutorial script) sits next to `model.json`, named as a command argument, so it is passed by absolute path and hashed. Output: `<name>_metrics.csv` has one `name,value` row per metric (`fraction_counts_removed`, `found_cells`, `ratio_of_found_cells_to_expected_cells`, ...), written with `float_format="%.3f"`, so fractions are **quantized to 0.001**. For a finer output, read the `.h5` or compute the fraction in the driver. Add `--cpu-threads 1` so that EMA's `-j` controls parallelism.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| Quick-start tutorial, tiny heart10k (https://cellbender.readthedocs.io/en/latest/tutorial/index.html; `examples/remove_background/generate_tiny_10x_dataset.py`) | ambient-RNA removal by SVI on 50,500 barcodes × 100 genes; tutorial options `--expected-cells 500 --total-droplets-included 2000`, 150 epochs (default) | `--fpr` 0.01 [0.0, 0.1]; `--epochs` 50 [20, 150] (integer); `--learning-rate` 1e-4 [2e-5, 5e-4] (log); `--expected-cells` 500 [100, 1000] (integer) | `fraction_counts_removed` | increasing in `fpr` (the target false-positive rate controls how much is removed); `expected-cells` near-negligible (the tutorial says the output "remains virtually the same" at 100 and 1000); `epochs` and `learning-rate` interact (under-trained runs); training noise from the seed (`repeat`); 0.001 quantization steps | 30–90 s at 50 epochs on CPU *(estimate)* | cli (env python + `run.py`) | regex on `tiny_output_metrics.csv`: `fraction_counts_removed,(\S+)` |
| same dataset and settings | same | same | `found_cells` (a second `model.json`) | an integer plateau near 500 with jumps; possibly insensitive to `fpr`; `nonsmooth` finds jumps everywhere | same | cli | regex `found_cells,(\S+)` |

**Claude Code prompts.**

```text
Stage 1 — check the machine for CellBender (read-only). I want to try CellBender 0.4.0 remove-background on its tiny tutorial dataset as an EMA command-line model. Run only read-only commands and report: OS and version, CPU architecture, number of cores and RAM, whether conda/mamba (Miniforge) exists and where, python3 versions, any NVIDIA GPU (nvidia-smi, Linux only), Docker, curl and wget, and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, a conda-forge env `ema-cellbender` with python=3.12 pytorch=2.13.0 (PyPI has no Intel-Mac torch wheel after 2.2.2) plus `pip install cellbender==0.4.0`; on Ubuntu, a venv with pip (CPU is enough for the tiny dataset; a real dataset needs a GPU instance). Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install CellBender on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-cellbender -c conda-forge python=3.12 pytorch=2.13.0 pyro-ppl pytables anndata scipy pandas matplotlib psutil pip`, then `<env>/bin/pip install cellbender==0.4.0`. If pip tries to download a torch wheel, stop and report instead of letting it. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import torch, cellbender; print(torch.__version__, cellbender.__version__)"` and `<env>/bin/cellbender remove-background --help`. Report the env's absolute paths. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install CellBender on this AWS EC2 instance (Ubuntu 24.04, x86_64, CPU only). Ask me before any sudo (python3-venv), then create ~/venvs/ema-cellbender and `pip install cellbender==0.4.0`. Before installing, tell me which torch wheel pip will pick and its download size; if it is the CUDA build and over 1 GB, ask me whether to use the CPU-only index (https://download.pytorch.org/whl/cpu) instead. Never use EMA's .venv, and never read .env. Check the import and `cellbender remove-background --help`. Do not pull the GPU Docker image. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — CellBender smoke test. In a scratch directory outside the EMA repo, download https://raw.githubusercontent.com/broadinstitute/CellBender/v0.4.0/examples/remove_background/generate_tiny_10x_dataset.py. It downloads the 10x heart10k raw matrix with wget; tell me the file's size (curl -sI) and ask me before downloading it, then fetch it with curl to the file name the script expects, and run the script with the env's python to make tiny_raw_feature_bc_matrix.h5ad. Then time `cellbender remove-background --input tiny_raw_feature_bc_matrix.h5ad --output tiny_output.h5 --expected-cells 500 --total-droplets-included 2000 --epochs 50 --cpu-threads 1`. Report the wall time, the files written, and the contents of tiny_output_metrics.csv. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare CellBender's tiny tutorial as an EMA model. Enter plan mode first and show me the plan. Create examples/cellbender/tiny/ with tiny_raw_feature_bc_matrix.h5ad from Stage 3 (say its size; if over 50 MB, ask me before putting it in the repo and propose keeping it outside with its path in the description), and a driver run.py (run with the ema-cellbender env's absolute python) that sets cellbender.remove_background.consts.RANDOM_SEED = 1234 + int(os.environ.get("EMA_REPLICATE", "0")), prints the seed and the cellbender version, then runs remove-background with --input <the .h5ad argument> --output tiny_output.h5 --total-droplets-included 2000 --cpu-threads 1 and the inputs fpr = 0.01 [0, 0.1], epochs = 50 [20, 150], learning_rate = 1e-4 [2e-5, 5e-4] (scale log), expected_cells = 500 [100, 1000], passed as command arguments like examples/beam/model_args.json. First check in CellBender's source that patching the constant before the call changes the seed it uses, and tell me how you checked. Output: regex `fraction_counts_removed,(\S+)` on tiny_output_metrics.csv; a second model_found_cells.json with `found_cells,(\S+)`. number_format for the integers must print integers. env OMP_NUM_THREADS=1, timeout_s 900. Check by hand that two replicates with EMA_REPLICATE 0 and 1 differ and two with the same value agree. Then `.venv/bin/ema profile examples/cellbender/tiny/model.json -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first CellBender campaign (small). For examples/cellbender/tiny/model.json, write campaign.json with repeat (n_points 2, replicates 4) and morris (n_traj 4). Use `.venv/bin/ema estimate` and report the run count and estimated time; if it is over 3 hours at -j 2, propose cutting it and ask. Ask me before `ema run`. After it runs, report: the run-to-run scatter and whether it exceeds the 0.001 quantization, morris's ranking (fpr expected first, expected_cells near-negligible), and failed runs. Suggest (don't run) curve1d on fpr with output_noise from repeat. Stop and report.
```

```text
Stage 6 — CellBender troubleshooting. An EMA CellBender model fails or is slow. Diagnose read-only first, from the run directory's stdout.txt, stderr.txt, the CellBender .log file, and ema_run.json. Check for: pip having replaced conda's torch (torch.__version__, torch.__file__), a checkpoint (ckpt.tar.gz) being reused from somewhere other than the fresh run directory, training failures ("ELBO" fail-fraction messages, --num-training-tries), learning rates that diverge (NaN loss), threads oversubscribed (--cpu-threads, OMP_NUM_THREADS), the input .h5ad not found (it must be named as a command argument or a static file), a seed that ignores EMA_REPLICATE, and timeouts (epochs × data size). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License BSD-3-Clause.
- It is training, so it is noisy: the fixed internal seed makes each run repeatable on one machine (with one thread) **(unconfirmed on CPU)**, but different seeds give different answers. Measure the scatter with `repeat` and pass `output_noise`.
- The metrics file rounds to three decimals; small effects vanish into steps of 0.001.
- Cost: minutes per run on CPU for the tiny dataset; about 30 minutes per run on a T4 for a real dataset, by the tutorial. A real-data campaign is AWS GPU only, and small.
- CellBender writes checkpoints (`--checkpoint`, default on) and can resume from them; in EMA's fresh run directories there is nothing to resume, which is what we want.
- Avoid v0.3.1 (the README warns its output count matrices were wrong).
- Sources: https://github.com/broadinstitute/CellBender, https://github.com/broadinstitute/CellBender/releases/tag/v0.4.0, https://cellbender.readthedocs.io/en/latest/, https://cellbender.readthedocs.io/en/latest/tutorial/index.html, https://github.com/broadinstitute/CellBender/blob/v0.4.0/cellbender/remove_background/argparser.py, https://github.com/broadinstitute/CellBender/blob/v0.4.0/cellbender/remove_background/consts.py, https://github.com/broadinstitute/CellBender/blob/v0.4.0/cellbender/remove_background/run.py, https://github.com/broadinstitute/CellBender/blob/v0.4.0/examples/remove_background/generate_tiny_10x_dataset.py, https://pypi.org/project/cellbender/, https://pypi.org/project/torch/, https://anaconda.org/conda-forge/pytorch

---

#### Scanpy

**What it is.** A toolkit for single-cell gene-expression analysis built on AnnData: quality control, normalization, highly variable genes, PCA, neighbour graphs, clustering (Leiden), embeddings, and differential expression. Python; license BSD-3-Clause. Current release **1.12.4 (27 August 2026)**; 1.13.0a2 is a pre-release. Tutorials at https://scanpy.readthedocs.io/en/stable/tutorials/ (source `docs/tutorials/` of https://github.com/scverse/scanpy, about eight notebooks); the classic one is "Preprocessing and clustering 3k PBMCs (legacy workflow)" (`docs/tutorials/basics/clustering-2017.ipynb`), whose data come from `sc.datasets.pbmc3k()` (`https://exampledata.scverse.org/scanpy/pbmc3k_raw.h5ad`).
Fit with EMA: honest but unusual. Scanpy is an **analysis pipeline**, not a simulator; the model is "this pipeline on this dataset", and the inputs are its tuning parameters. That is a real question analysts ask (how sensitive is my clustering to `n_neighbors`, `n_pcs`, resolution?). The number of clusters is an integer, so it is all plateaus and jumps; a continuous score (silhouette) is the better output for most diagnostics.

**Install on an Intel Mac.** Scanpy is pure Python (noarch on conda-forge), but it needs `numba`, and PyPI has no macOS x86_64 `numba`/`llvmlite` wheels after 0.62.1, while conda-forge builds `numba` for osx-64 today. `leidenalg` and `python-igraph` are built for osx-64 on conda-forge; `scikit-misc` (needed by the tutorial's `flavor="seurat_v3"`) too.
1. Miniforge as in 4.1.
2. Env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-scanpy -c conda-forge python=3.12 scanpy=1.12.4 python-igraph leidenalg scikit-misc
   ```
3. Check:
   ```bash
   ~/miniforge3/envs/ema-scanpy/bin/python -c "import scanpy as sc, numba, igraph, skmisc; print(sc.__version__, numba.__version__, igraph.__version__)"
   ```
Known problems: scanpy 1.12 requires Python ≥ 3.12. The first call of each numba-compiled function compiles it (seconds); numba caches to `__pycache__` next to the package when it can **(unconfirmed for every scanpy function)**, so the first run is slower.
Sources: https://pypi.org/project/scanpy/, https://anaconda.org/conda-forge/scanpy, https://anaconda.org/conda-forge/numba (osx-64 builds), https://pypi.org/project/numba/#files, https://anaconda.org/conda-forge/leidenalg, https://anaconda.org/conda-forge/python-igraph, https://anaconda.org/conda-forge/scikit-misc, https://scanpy.readthedocs.io/en/stable/installation.html.

**Install on AWS (Ubuntu 24.04 EC2).** The same Miniforge env (recommended, identical versions), or a venv: `pip install "scanpy[leiden,skmisc]==1.12.4"` (Linux wheels exist for everything). Check as on the Mac.
Sources: https://pypi.org/project/scanpy/, https://scanpy.readthedocs.io/en/stable/installation.html.

**Preparing the examples for EMA.** A driver `run.py` (the env's python) reproduces the tutorial's steps with inputs from a deck:
- Once, outside EMA: download `pbmc3k_raw.h5ad` with `sc.datasets.pbmc3k()`, apply the fixed QC (`filter_cells(min_genes=200)`, `filter_genes(min_cells=3)`, 200 < genes < 2500, `pct_counts_mt` < 5), and save `pbmc3k_qc.h5ad` next to `model.json` (a few MB), named on the command line so it is hashed.
- Per run: `normalize_total(target_sum=1e4)`, `log1p`, `highly_variable_genes(layer="counts", n_top_genes=..., flavor="seurat_v3")`, `regress_out` and `scale(max_value=10)` (these two are slow; an optional `fast` variant leaves `regress_out` out and says so), `pca(svd_solver="arpack")`, `neighbors(n_neighbors=..., n_pcs=...)`, `leiden(resolution=..., flavor="igraph", n_iterations=2, random_state=EMA_REPLICATE)`.
- For 2,638 cells, `neighbors` uses exact distances (scanpy uses its dense path below 8192 cells and never pynndescent below 4096, `neighbors/__init__.py`), so the only randomness is Leiden's (and ARPACK's start vector, which scanpy seeds).
- Print `n_clusters = <int>` and `silhouette = <%.12e>` (scikit-learn's `silhouette_score` on the first `n_pcs` PCs with the Leiden labels; NaN, and exit 1, if there is only one cluster).

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| "Preprocessing and clustering 3k PBMCs (legacy workflow)" (https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering-2017.html; `docs/tutorials/basics/clustering-2017.ipynb`) | 2,638 PBMCs after QC; tutorial settings n_top_genes 2000, n_pcs 40, n_neighbors 10, Leiden resolution 0.7 (`flavor="igraph"`, `n_iterations=2`, `random_state=0`) | `resolution` 0.7 [0.2, 2.0] (log); `n_neighbors` 10 [5, 50] (integer); `n_pcs` 40 [10, 50] (integer); `n_top_genes` 2000 [500, 4000] (integer) | number of Leiden clusters | increasing in `resolution` (dominant) and decreasing in `n_neighbors`; an integer staircase, so `nonsmooth` finds jumps everywhere; `n_pcs` and `n_top_genes` weaker, possibly negligible; seed noise shows as occasional ±1 (`repeat`) | 10–40 s with `regress_out`, 5–15 s without *(estimate)* | cli (env python + `run.py`) | regex `n_clusters = (\d+)` |
| same pipeline | same | same | silhouette score of the Leiden labels in PCA space (a second `model.json`) | more continuous, but still piecewise: jumps where the cluster count changes; decreasing in `resolution` beyond the natural cell-type count (about 8 at the tutorial settings); interaction between `resolution` and `n_neighbors` | same | cli | regex `silhouette = (\S+)` |

**Claude Code prompts.**

```text
Stage 1 — check the machine for Scanpy (read-only). I want to onboard Scanpy 1.12.4's pbmc3k clustering tutorial into EMA as a command-line model. Run only read-only commands and report: OS and version, CPU architecture, whether conda/mamba (Miniforge) exists and where, any env named ema-scanpy, python3 versions, and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac, a conda-forge env `ema-scanpy` with python=3.12 scanpy=1.12.4 python-igraph leidenalg scikit-misc (PyPI has no Intel-Mac numba wheels after 0.62.1; conda-forge still builds osx-64); on Ubuntu, the same env or a pip venv with scanpy[leiden,skmisc]. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install Scanpy on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-scanpy -c conda-forge python=3.12 scanpy=1.12.4 python-igraph leidenalg scikit-misc`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import scanpy as sc, numba, igraph, skmisc; print(sc.__version__, numba.__version__)"` and report the env's absolute python path. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install Scanpy on this AWS EC2 instance (Ubuntu 24.04, x86_64). Preferred: Miniforge (Linux x86_64) and an env `ema-scanpy` with the same packages and versions as on my Mac. Never use EMA's .venv, and never read .env. Ask before any sudo and before downloads over 1 GB. If conda fails, propose (don't run) a venv with `pip install "scanpy[leiden,skmisc]==1.12.4"`. Check as on the Mac and report the absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — Scanpy smoke test. With the ema-scanpy env's python, in a scratch directory outside the EMA repo (set sc.settings.datasetdir to it), load sc.datasets.pbmc3k() and run the legacy tutorial's steps (docs/tutorials/basics/clustering-2017.ipynb of scanpy 1.12.4: QC, normalize_total, log1p, highly_variable_genes seurat_v3 with layer="counts", regress_out, scale, pca arpack, neighbors 10/40, leiden resolution 0.7 flavor igraph n_iterations 2 random_state 0), with no plotting and no UMAP. Time each step, and run the whole script twice. Report the cell count after QC (expect 2,638), the number of clusters (the page reports 8), step times for both runs (the second shows numba caching), and whether the two runs agree. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare the Scanpy pbmc3k clustering pipeline for EMA. Enter plan mode first and show me the plan. Create examples/scanpy/pbmc3k/ with: prepare.py (run once by hand, not by EMA) that writes pbmc3k_qc.h5ad (the tutorial's QC applied, counts kept in layers["counts"]) next to model.json and reports its size; run.py (the ema-scanpy env's absolute python) that reads a deck with resolution = 0.7 [0.2, 2.0] (scale log), n_neighbors = 10 [5, 50], n_pcs = 40 [10, 50], n_top_genes = 2000 [500, 4000], rounds the integers, runs the per-run steps with leiden random_state = int(os.environ.get("EMA_REPLICATE", "0")), and prints scanpy's version, `n_clusters = <int>` and `silhouette = %.12e`. Pass pbmc3k_qc.h5ad as a command argument so it is hashed. Two model.json files sharing the template and driver (model_nclusters.json, model_silhouette.json), like examples/beam/. env OMP_NUM_THREADS=1, NUMBA_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1; timeout_s 300. Check by hand that nominal inputs give the tutorial's 8 clusters. Then `.venv/bin/ema profile examples/scanpy/pbmc3k/model_nclusters.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — a faster Scanpy variant. Plan mode first. In examples/scanpy/pbmc3k/, add a boolean deck setting (not an input) that skips regress_out, and a third model.json (model_nclusters_fast.json) that uses it; its description must say regress_out is left out. Profile both with `.venv/bin/ema profile ... -n 5` and report the time saved and whether the nominal cluster count changes. Stop and report; don't run a campaign.
```

```text
Stage 5 — first Scanpy campaign. For examples/scanpy/pbmc3k/model_silhouette.json (or the fast variant if Stage 4.2 showed it keeps 8 clusters), write campaign.json with repeat (n_points 3, replicates 4), morris (n_traj 6), and curve1d on resolution (n 21). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before `ema run` (-j 4). After it runs, report: the seed scatter, morris's ranking (resolution expected first), which inputs are (possibly) negligible, and what curve1d and its nonsmooth features show along resolution. Expected: jumps where the cluster count changes. Suggest (don't run) the same campaign on model_nclusters.json. Stop and report.
```

```text
Stage 6 — Scanpy troubleshooting. An EMA Scanpy model fails or is slow. Diagnose read-only first by running run.py by hand in a copied run directory with the ema-scanpy env's python. Check for: numba compiling on every run (a cache directory that isn't writable; NUMBA_CACHE_DIR), threads oversubscribed (NUMBA_NUM_THREADS, OMP_NUM_THREADS, OPENBLAS_NUM_THREADS), leidenalg vs igraph flavor warnings, skmisc missing for seurat_v3, n_pcs larger than the PCs computed, silhouette failing with one cluster (it must be a failed run), a dataset download attempted inside a run (the driver must only read pbmc3k_qc.h5ad), and a regex that doesn't match. Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License BSD-3-Clause.
- It is a pipeline on one dataset: conclusions are about this dataset. Say so in the `model.json` description.
- Noise: Leiden's `random_state` is the main source; seed it from `EMA_REPLICATE`. The integer output makes `repeat`'s scatter coarse (0 or ±1).
- Threads: numba, BLAS and igraph can all use threads; pin them to 1.
- Version pitfalls: the tutorial uses `flavor="igraph"` and `n_iterations=2`, the announced future default; scanpy still warns when `flavor` is not given. The newer "Preprocessing and clustering" tutorial (`clustering.ipynb`) uses a different dataset and adds doublet detection, which is another source of randomness.
- Sources: https://github.com/scverse/scanpy, https://github.com/scverse/scanpy/releases, https://pypi.org/project/scanpy/, https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering-2017.html, https://github.com/scverse/scanpy/blob/main/docs/tutorials/basics/clustering-2017.ipynb, https://github.com/scverse/scanpy/blob/1.12.4/src/scanpy/datasets/_datasets.py, https://github.com/scverse/scanpy/blob/1.12.4/src/scanpy/neighbors/__init__.py, https://github.com/scverse/scanpy/blob/1.12.4/src/scanpy/tools/_leiden.py, https://anaconda.org/conda-forge/scanpy, https://anaconda.org/conda-forge/numba, https://pypi.org/project/numba/

---

#### OpenSim

**What it is.** Musculoskeletal modelling and simulation: multibody dynamics (Simbody) with Hill-type muscles, controllers, contact, and tools for inverse kinematics and dynamics, static optimization, and optimal control (Moco). C++ with Python, Java and MATLAB bindings (SWIG). License Apache-2.0. Current release **4.6**: conda packages (channel `opensim-org`) dated 2026-04-13 and PyPI wheels (`opensim` 4.6-1/4.6-2) from 2026-04-26, with the GitHub release page dated 2026-07-09. Examples: `Bindings/Python/examples/` (about ten scripts, including `build_simple_arm_model.py` and `dynamic_walker_example_optimization.py`), eight Python tutorial notebooks in `Bindings/Python/tutorials/`, and C++ examples in `OpenSim/Examples/` (about 20, including `OptimizationExample_Arm26` with `Arm26_Optimize.osim`), all in https://github.com/opensim-org/opensim-core. User documentation: https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/overview.

**Install on an Intel Mac.** Checked today:
- `opensim-org::opensim` on anaconda.org: osx-64 builds stop at **4.5.1** (Python 3.9–3.11, numpy 1.25, August 2024); 4.5.2 and 4.6 have no osx-64 build.
- PyPI `opensim` 4.6: `macosx_15_0_universal2` wheels for Python 3.11–3.13, which need **macOS 15**; this machine is macOS 14 (Darwin 23.6), so pip will refuse them. Whether they contain an x86_64 slice is **(unconfirmed)**.
- The GitHub 4.5.2 release has an `opensim-core-4.5.2-...-mac-x86_64.zip` (C++ install); the unofficial `pyopensim` 4.5.2.0 (neurobionics) has `macosx_11_0_universal2` wheels.

Recommended: the official conda 4.5.1 in its own env; the examples used below exist at the 4.5.1 tag. Fallback for 4.6 parity with AWS: Docker Desktop with a `python:3.12-slim` image (pinned by digest) plus `pip install opensim==4.6`.
1. Miniforge as in 4.1.
2. Env:
   ```bash
   ~/miniforge3/bin/mamba create -n ema-opensim -c opensim-org -c conda-forge python=3.11 opensim=4.5.1
   ```
3. Check:
   ```bash
   ~/miniforge3/envs/ema-opensim/bin/python -c "import opensim as osim; print(osim.GetVersionAndDate())"
   ```
Known problems: mixing the `opensim-org` channel with conda-forge may pull an old numpy (the build pins numpy 1.25) **(unconfirmed conflicts)**. The official docs describe the conda route as `conda install -c opensim-org opensim` **(unconfirmed exact page wording)**.
Sources: https://anaconda.org/opensim-org/opensim (file list), https://pypi.org/project/opensim/#files, https://github.com/opensim-org/opensim-core/releases, https://pypi.org/project/pyopensim/, https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53085346/Scripting+in+Python.

**Install on AWS (Ubuntu 24.04 EC2).** PyPI has `manylinux_2_28_x86_64` wheels of 4.6 for Python 3.11–3.13, and Ubuntu 24.04's glibc (2.39) satisfies them:
```bash
sudo apt-get install -y python3-venv        # ask first
python3 -m venv ~/venvs/ema-opensim
~/venvs/ema-opensim/bin/pip install opensim==4.6
~/venvs/ema-opensim/bin/python -c "import opensim as osim; print(osim.GetVersionAndDate())"
```
Fallbacks: conda `mamba create -n ema-opensim -c opensim-org -c conda-forge python=3.12 opensim=4.6` (linux-64 builds exist), or the GitHub `opensim-core-4.6-ubuntu24-linux.zip`. To compare with the Mac, also install 4.5.1 in a second env and run the nominal points in both.
Sources: https://pypi.org/project/opensim/#files, https://anaconda.org/opensim-org/opensim, https://github.com/opensim-org/opensim-core/releases/tag/4.6.

**Preparing the examples for EMA.** Each example becomes a driver `run.py` (the env's python) that reads a key = value deck, builds or loads the model, sets the inputs through the API, runs `osim.Manager` with a tight integrator accuracy (`manager.setIntegratorAccuracy(1e-7)`, tighter than the C++ example's 1e-5), and prints one number. Remove `printToXML`, visualization and reporters. Keep `.osim` files next to `model.json`, named on the command line so they are hashed. Integrator failures raise exceptions: let the driver exit non-zero.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| `Bindings/Python/examples/build_simple_arm_model.py` (https://github.com/opensim-org/opensim-core/blob/4.6/Bindings/Python/examples/build_simple_arm_model.py) | two-body arm, shoulder locked, elbow pin joint; one Millard2012 biceps (max isometric force 200, optimal fibre 0.6, tendon slack 0.55); excitation steps 0.3 → 1.0 between t 0.5 and 3; integrate to 10 s | `f_max` 200 [100, 400]; `l_opt` 0.6 [0.45, 0.75]; `l_slack` 0.55 [0.45, 0.65]; `u_high` 1.0 [0.3, 1.0] | elbow angle at t = 10 s | increasing in `f_max` and `u_high`; strong, nonlinear dependence on `l_slack` with a **kink** where the tendon goes slack (no passive force) and on `l_opt` (force–length curve); possibly several equilibria (jumps) since the elbow has no range limit; interactions `f_max` × `u_high` | 1–5 s *(estimate)* | cli (env python + `run.py`) | regex `elbow_angle = (\S+)` |
| `OpenSim/Examples/OptimizationExample_Arm26/` (`Arm26_Optimize.osim`, `OptimizationExample.cpp`) | planar arm with 2 coordinates and 6 Thelen2003 muscles (TRIlong, TRIlat, TRImed, BIClong, BICshort, BRA); constant excitations; integrate to 0.25 s from rest | excitation of `BIClong` 0.5 [0.01, 0.99]; `BRA` 0.5 [0.01, 0.99]; `TRIlong` 0.02 [0.01, 0.99]; others fixed at 0.02 (the example's start); scale of BIClong's max isometric force 1 [0.5, 1.5] | forward (x) velocity of the `r_ulna_radius_hand` mass centre at 0.25 s (the example's objective, negated) | monotone: increasing in flexor excitations, decreasing in triceps excitation (antagonists interact); activation dynamics and force–velocity make it smooth but curved; `active_subspace` may find one dominant direction (net flexor drive); range limits of `r_elbow_flex` (0 to 2.27 rad) may clamp at high drive (kink) | 0.5–3 s *(estimate)* | cli | regex `hand_vx = (\S+)` |
| `Bindings/Python/examples/dynamic_walker_example_optimization.py` with `dynamic_walker_example_model.osim` | planar passive walker with Hunt–Crossley foot/knee/hip contact on a platform; the script optimizes 9 initial conditions with CMA-ES for distance travelled in 10 s | initial pelvis speed `vx0` 0.1 [0, 2] (the script's bounds); left hip angle (default ±0.3 around the model's default) **(range unconfirmed; read the default first)**; right knee angle (same) | pelvis x at t = 10 s | **strongly nonsmooth**: falls and gait changes make jumps and a rough, chaotic-looking surface; large failure regions if the integrator gives up; `nonsmooth` and `curve1d` should report jumps; `surrogate_check` should fail | 5–60 s (contact, stiff) *(estimate)* | cli | regex `distance = (\S+)` |

**Claude Code prompts.**

```text
Stage 1 — check the machine for OpenSim (read-only). I want to onboard OpenSim Python examples into EMA as command-line models. Run only read-only commands and report: OS and exact macOS version (sw_vers; the 4.6 wheels need macOS 15), CPU architecture, whether conda/mamba (Miniforge) exists and where, any env named ema-opensim, python3 versions, Docker (docker version, daemon running), and free disk space. Don't install anything, and don't read .env. Recommend a route: on an Intel Mac below macOS 15, a conda env `ema-opensim` with opensim=4.5.1 from the opensim-org channel (its last osx-64 build), with Docker python:3.12-slim + pip opensim==4.6 as the fallback; on Ubuntu 24.04, a venv with pip install opensim==4.6. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install OpenSim on this Intel Mac. Use Miniforge: `mamba create -n ema-opensim -c opensim-org -c conda-forge python=3.11 opensim=4.5.1`. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge, before any sudo or Homebrew change, and before any download over 1 GB. Check with `<env>/bin/python -c "import opensim as osim; print(osim.GetVersionAndDate())"` and report the env's absolute python path and the numpy version it got. If the solve fails, report the conflict; don't try other channels or pip on your own. Stop at the first error and report it with the command's output. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install OpenSim on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before any sudo (python3-venv), then create ~/venvs/ema-opensim with python3 (3.12) and `pip install opensim==4.6` (manylinux wheels). Never use EMA's .venv, and never read .env. Check with `import opensim as osim; print(osim.GetVersionAndDate())`. If the import fails for a missing system library, report it and propose (don't run) the apt package or the conda route (-c opensim-org opensim=4.6). Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — OpenSim smoke test. In a scratch directory outside the EMA repo, download build_simple_arm_model.py from Bindings/Python/examples of github.com/opensim-org/opensim-core at the tag matching the installed version (4.5.1 on the Mac, 4.6 on AWS), and run it with the env's python. Time it. Report the ConsoleReporter's last lines (fiber force and elbow angle at t = 10), the wall time, and the files it wrote. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare OpenSim's simple arm for EMA. Enter plan mode first and show me the plan. Source: Bindings/Python/examples/build_simple_arm_model.py (tag matching the installed OpenSim). Create examples/opensim/simple_arm/ with run.py (the ema-opensim env's absolute python) that reads a deck with f_max = 200 [100, 400], l_opt = 0.6 [0.45, 0.75], l_slack = 0.55 [0.45, 0.65], u_high = 1.0 [0.3, 1.0] (the StepFunction's end value), builds the same model without geometry, reporter or printToXML, sets the integrator accuracy to 1e-7, integrates to 10 s, and prints the OpenSim version and `elbow_angle = %.12e` (radians). Follow examples/cantera/ and docs/guides/input_deck_model.md. env OMP_NUM_THREADS=1; timeout_s 120. Check by hand that nominal inputs reproduce Stage 3's elbow angle. Then `.venv/bin/ema profile examples/opensim/simple_arm/model.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare OpenSim's Arm26 example. Plan mode first. Source: OpenSim/Examples/OptimizationExample_Arm26/ (Arm26_Optimize.osim and OptimizationExample.cpp) of opensim-core at the installed tag. Copy Arm26_Optimize.osim into examples/opensim/arm26/ and pass it as a command argument. run.py loads it, adds a PrescribedController with a Constant excitation per muscle (BIClong = 0.5 [0.01, 0.99], BRA = 0.5 [0.01, 0.99], TRIlong = 0.02 [0.01, 0.99], the other three fixed at 0.02), scales BIClong's max_isometric_force by f_scale = 1 [0.5, 1.5], equilibrates muscles, integrates from 0 to 0.25 s with accuracy 1e-7, and prints `hand_vx = %.12e`, the x velocity of r_ulna_radius_hand's mass center in ground, as in the C++ example. First confirm in the C++ source how it sets the initial state and controls, and match it. timeout_s 120. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare OpenSim's dynamic walker. Plan mode first. Source: Bindings/Python/examples/dynamic_walker_example_optimization.py and dynamic_walker_example_model.osim (installed tag); no cma needed. Put the .osim in examples/opensim/walker/ and write run.py that sets the initial pelvis speed vx0 = 0.1 [0, 2], the left hip angle and the right knee angle (read their defaults from the model first and propose ranges of ±0.3 rad around them; tell me before using them), integrates 10 s, and prints `distance = %.12e` (the final Pelvis_tx value, as the script does). Let integrator exceptions exit non-zero. timeout_s 600. Run three points by hand and report their times and distances. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first OpenSim campaign. For examples/opensim/arm26/model.json, write campaign.json with repeat (n_points 2, replicates 2) to confirm determinism, morris (n_traj 8), and sobol (n_base 64). Use `.venv/bin/ema estimate` to report the run count and estimated time, and ask me before `ema run` (-j 4). After it runs, report: whether repeats are identical, morris's ranking and monotone flags (BIClong and BRA should increase hand_vx, TRIlong decrease it), sobol's interaction share, and any failed runs. Suggest (don't run) active_subspace to test for one dominant direction. Stop and report.
```

```text
Stage 6 — OpenSim troubleshooting. An EMA OpenSim model fails or is slow. Diagnose read-only first by running run.py by hand in a copied run directory with the env's python. Check for: `import opensim` failures (numpy ABI mismatch with the conda build, a library not found), the .osim not found (it must be a command argument or a static file), geometry files the .osim references but aren't needed (warnings only), integrator failures or very small steps (contact stiffness, accuracy too tight, timeouts), muscle equilibration failures at extreme tendon slack or fibre lengths, results that differ from 4.5.1 to 4.6 (report both), and threads (OMP_NUM_THREADS). Report the cause and a proposed fix. Ask before changing the env or model.json.
```

**Gotchas and sources.**
- License Apache-2.0.
- Platform: the Mac (4.5.1) and AWS (4.6) routes differ in version; record the version in each `model.json` description and compare nominal outputs before merging results.
- Determinism: forward integration is deterministic on one machine; the integrator's error control makes the output a slightly rough function of the inputs, so keep the accuracy tight (1e-7 or less) or measure with `repeat`.
- Contact models (the walker) are stiff and sensitive; long runs and failures are data, not bugs.
- Threads: Simbody may use threads in some components **(unconfirmed)**; set `OMP_NUM_THREADS=1`.
- Sources: https://opensim.stanford.edu, https://github.com/opensim-org/opensim-core, https://github.com/opensim-org/opensim-core/releases/tag/4.6, https://github.com/opensim-org/opensim-core/releases/tag/4.5.2, https://github.com/opensim-org/opensim-core/tree/4.6/Bindings/Python/examples, https://github.com/opensim-org/opensim-core/tree/4.6/Bindings/Python/tutorials, https://github.com/opensim-org/opensim-core/tree/4.6/OpenSim/Examples/OptimizationExample_Arm26, https://anaconda.org/opensim-org/opensim, https://pypi.org/project/opensim/, https://pypi.org/project/pyopensim/, https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/overview

---

#### SimVascular (svZeroDSolver and svOneDSolver)

**What it is.** SimVascular is a pipeline for patient-specific blood-flow simulation: image segmentation and modelling in a GUI, then solvers at three fidelities: svMultiPhysics (3D finite elements), svOneDSolver (1D deformable-vessel networks) and svZeroDSolver (0D lumped-parameter networks). C++; svZeroDSolver and svMultiPhysics are BSD-3-Clause, svOneDSolver has its own Stanford/UC copyright licence (`LICENSE.txt`). Releases: svZeroDSolver **v3.0 (19 May 2025)** is the latest tag, while `master` is active (pushed 2026-09-15) and its `pyproject.toml` still says version 2.0; svOneDSolver has no numbered releases (latest commit 2026-08-10); svMultiPhysics' latest release is `March_2025`; the GUI's last installers are 2023-05 (Ubuntu 20 `.deb`, Windows) and 2022-07 (a macOS Catalina `.dmg`), plus SimTK downloads **(unconfirmed which are newer)**. Examples: svZeroDSolver's `tests/cases/` (about 44 input JSON files with reference results), svOneDSolver's documentation examples (`01_simpleArtery_Flow.in`, `02_simpleArtery_Resistance.in`, `04_simpleArtery_Pressure.in`, `05_bifurcation_RCR.in`, `12_AortoFem_Pulse_R.in`) at https://simvascular.github.io/documentation/rom_simulation.html, and patient models in the Vascular Model Repository (https://www.vascularmodel.com).
Fit with EMA: the GUI pipeline can't be automated, and the 3D solver is hours per run on a cluster. **svZeroDSolver fits perfectly** (JSON in, CSV out, milliseconds per run); svOneDSolver fits well (a text deck, seconds per run). Recommend 0D first, 1D second, 3D only on AWS and not for campaigns.

**Install on an Intel Mac.** Neither solver is on PyPI or conda-forge; both build from source with CMake and a C++17 compiler. Xcode's clang works (no OpenMP needed). svZeroDSolver's CMake downloads Eigen, pybind11, nlohmann/json and pybind11_json at build time (`FetchContent`).
1. Xcode Command Line Tools (`xcode-select --install`), and Miniforge as in 4.1 for cmake and Python.
2. svZeroDSolver at tag v3.0 (the docs' recommended pip route, pinned):
   ```bash
   ~/miniforge3/bin/mamba create -n ema-svzerod -c conda-forge python=3.12 cmake ninja git pip numpy pandas
   ~/miniforge3/envs/ema-svzerod/bin/pip install "git+https://github.com/simvascular/svZeroDSolver.git@v3.0"
   ~/miniforge3/envs/ema-svzerod/bin/svzerodsolver --help   # or run a test case
   ```
3. svOneDSolver (default skyline solver, no external libraries):
   ```bash
   mkdir -p ~/src && cd ~/src
   git clone https://github.com/SimVascular/svOneDSolver.git
   git -C svOneDSolver rev-parse HEAD            # record the commit
   mkdir svOneDSolver_build && cd svOneDSolver_build
   ~/miniforge3/envs/ema-svzerod/bin/cmake -DCMAKE_BUILD_TYPE=Release ../svOneDSolver
   make -j 4
   ls bin/OneDSolver
   ```
Known problems: that `svzerodsolver` accepts `--help` is **(unconfirmed)**; the documented check is `svzerodsolver tests/cases/steadyFlow_RLC_R.json out.csv`. The README's platform badge says macOS and Ubuntu, but Intel-Mac builds are untested by me. The 2022 GUI `.dmg` is irrelevant here.
Sources: https://github.com/SimVascular/svZeroDSolver, https://simvascular.github.io/documentation/rom_simulation.html (0D install and user guide; source in https://github.com/SimVascular/SimVascular.github.io/tree/main/documentation/rom_simulation), https://github.com/SimVascular/svZeroDSolver/blob/v3.0/CMakeLists.txt, https://github.com/SimVascular/svOneDSolver (README: build and usage), https://github.com/SimVascular/SimVascular/releases.

**Install on AWS (Ubuntu 24.04 EC2).** The same recipe: `sudo apt-get install -y build-essential git` (ask first), Miniforge env `ema-svzerod` as on the Mac, pip install from the v3.0 tag, and the svOneDSolver CMake build. For the 3D solver, Docker Hub has `simvascular/solver:latest` and `simvascular/svmultiphysics:latest` (amd64 only, `latest` only; pin by digest) on a `c7i.8xlarge`; that is outside this plan.
Sources: https://simvascular.github.io/documentation/rom_simulation.html, https://hub.docker.com/r/simvascular/solver/tags, https://hub.docker.com/r/simvascular/svmultiphysics/tags.

**Preparing the examples for EMA.** svZeroDSolver: make the test-case JSON a `string.Template` (JSON has no `$`) with placeholders for the chosen values, render it to `case.json`, and run `["<env>/bin/svzerodsolver", "case.json", "out.csv"]` (the entry point `pysvzerod:run_simulation_cli`). Set `"output_all_cycles": false` so only the last cycle is written, and raise `number_of_cardiac_cycles` until the output stops changing. A small isolated `python` output parser (standard library `csv` only) reads `out.csv` (columns `name, time, flow_in, flow_out, pressure_in, pressure_out` for vessel-based output) and returns the mean or the max − min of one column over the last cycle. svOneDSolver: make the `.in` deck a template and run `[".../bin/OneDSolver", "case.in"]`; with `OUTPUT TEXT` it writes one text file per segment and quantity (rows are positions along the segment, columns are saved times), whose exact names (such as `<model><segment>_pressure.dat`) are **(unconfirmed)**; a python parser reads the inlet row over the last cycle.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| svZeroDSolver `tests/cases/pulsatileFlow_R_RCR.json` (https://github.com/SimVascular/svZeroDSolver/blob/v3.0/tests/cases/pulsatileFlow_R_RCR.json) | pulsatile inflow Q(t) = 2.5 sin(2πt) + 2.2 (period 1 s) through a resistor R_poiseuille 100 into an RCR outlet (Rp 1000, C 1e-4, Rd 1000, Pd 0); 10 cycles × 201 points | `R` 100 [50, 200]; `Rp` 1000 [500, 2000]; `C` 1e-4 [1e-5, 1e-3] (log); `Rd` 1000 [500, 2000] | (a) mean inlet pressure over the last cycle; (b) inlet pulse pressure (max − min), a second `model.json` | (a) **exactly** Q̄ (R + Rp + Rd) with Q̄ = 2.2: linear, no interactions, `C` negligible (a sharp known-answer test); (b) decreasing in `C`, increasing in `Rp`; a Windkessel transition at Rd·C ≈ period: `curve1d` on `C` (log) shows a sigmoid-like fall; `linear_coeffs` with `log_output` finds near-power-law pieces | < 0.5 s, mostly start-up *(estimate)* | cli (template + solver CLI) | python (CSV, last cycle) |
| svZeroDSolver `tests/cases/closedLoopHeart_singleVessel.json` | closed-loop heart and pulmonary circulation (time-varying elastance chambers, valves) with one aortic vessel and a closed-loop RCR; 10 cycles × 100 points | LV systolic elastance `Elv_s` 3.125 [2, 4.5]; RCR `Rd` 1.356 [1.0, 2.0]; RCR `C` 0.238 [0.15, 0.35]; RV `Erv_s` 2.125 [1.5, 3] | mean aortic inlet pressure over the last cycle | increasing in `Elv_s` and `Rd`; `C` weak on the mean; `Erv_s` weaker (acts through the pulmonary loop); valve switching may leave small kinks; Newton failures at extremes would show as a failure region; check periodicity (raise cycles) | < 1 s *(estimate)* | cli | python (CSV) |
| svOneDSolver `05_bifurcation_RCR.in` (https://github.com/SimVascular/SimVascular.github.io/blob/main/documentation/rom_simulation/1d-solver/files/05_bifurcation_RCR.in) | 1D aorta (50 elements) splitting into two iliacs with RCR outlets (Rp 90, C 0.0008, Rd 1200); Olufsen material (k1 2e7, k2 −22.5267, k3 8.65e5); dt 0.001, 10000 steps | `Rp` 90 [45, 180]; `C` 8e-4 [2e-4, 3.2e-3] (log); `Rd` 1200 [600, 2400]; `k3` 8.65e5 [4e5, 1.6e6] (log; wall stiffness) | aortic inlet pulse pressure over the last cycle | increasing in `k3` (stiffer wall, faster waves, higher pulse pressure) and in `Rp`; decreasing in `C`; smooth; wave reflection makes interactions between `k3` and the RCR values; solver failures at extreme stiffness | 2–20 s *(estimate)* | cli | python (per-segment text file) |

**Claude Code prompts.**

```text
Stage 1 — check the machine for SimVascular's 0D and 1D solvers (read-only). I want to onboard svZeroDSolver (tag v3.0) and svOneDSolver into EMA as command-line models. Run only read-only commands and report: OS and version, CPU architecture, Xcode Command Line Tools (xcode-select -p, clang --version) or build-essential on Linux, cmake and git versions, whether conda/mamba (Miniforge) exists and where, Docker, and free disk space. Don't install anything, and don't read .env. Recommend a route: a conda-forge env `ema-svzerod` (python 3.12, cmake, ninja, git) and `pip install git+https://github.com/simvascular/svZeroDSolver.git@v3.0`; svOneDSolver built with CMake in ~/src; the 3D solver not at all. Stop and report; don't continue to the next stage.
```

```text
Stage 2a — install svZeroDSolver and svOneDSolver on this Intel Mac. Use Miniforge (conda-forge only, never the defaults channel): `mamba create -n ema-svzerod -c conda-forge python=3.12 cmake ninja git pip numpy pandas`, then `<env>/bin/pip install "git+https://github.com/simvascular/svZeroDSolver.git@v3.0"` (the build downloads Eigen, pybind11 and nlohmann/json; that is expected). Then clone https://github.com/SimVascular/svOneDSolver.git into ~/src, record the commit hash, and build it out of source in ~/src/svOneDSolver_build with the env's cmake (Release) and make. Never install into EMA's .venv, and never read .env. Ask me before installing Miniforge or the Xcode tools, before any sudo or Homebrew change, and before any download over 1 GB. Check: `<env>/bin/svzerodsolver <svZeroDSolver v3.0 source>/tests/cases/steadyFlow_RLC_R.json out.csv` and that ~/src/svOneDSolver_build/bin/OneDSolver exists. Stop at the first error and report it with the command's output; don't improvise workarounds. Stop and report; don't continue to the next stage.
```

```text
Stage 2b — install svZeroDSolver and svOneDSolver on this AWS EC2 instance (Ubuntu 24.04, x86_64). Ask me before any sudo (build-essential git). Then the same as on my Mac: Miniforge env `ema-svzerod`, pip install from the v3.0 tag, and the svOneDSolver CMake build, recording its commit (use the same commit as on the Mac if I give you one). Never use EMA's .venv, and never read .env. Don't pull the svMultiPhysics images. Check as on the Mac. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 — SimVascular 0D/1D smoke test. In a scratch directory outside the EMA repo: (1) run svzerodsolver on tests/cases/pulsatileFlow_R_RCR.json and on closedLoopHeart_singleVessel.json from the v3.0 source, time each, and compare the first against the analytic values in its "description" block (inlet pressure 4620 at the start of the cycle); (2) download 05_bifurcation_RCR.in from https://raw.githubusercontent.com/SimVascular/SimVascular.github.io/main/documentation/rom_simulation/1d-solver/files/05_bifurcation_RCR.in, run OneDSolver on it, time it, and list the output files with their shapes (rows × columns). Report the times, the CSV columns, and the 1D output file names. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 — prepare svZeroDSolver's R-RCR case for EMA. Enter plan mode first and show me the plan. Source: tests/cases/pulsatileFlow_R_RCR.json (svZeroDSolver v3.0). Create examples/simvascular/zerod_rcr/ with case.template (the JSON with placeholders for R_poiseuille = 100 [50, 200], Rp = 1000 [500, 2000], C = 1e-4 [1e-5, 1e-3] (scale log), Rd = 1000 [500, 2000]; output_all_cycles false; number_of_cardiac_cycles 20), rendered to case.json; command [<ema-svzerod env>/bin/svzerodsolver, case.json, out.csv]; and parse_rcr.py, an isolated python output parser using only the standard library, with two functions: the mean of pressure_in and the max minus min of pressure_in for branch0_seg0 over the rows written. Two model.json files (model_mean.json, model_pulse.json) sharing the template, like examples/beam/. timeout_s 60. Check by hand: the mean at nominal equals 2.2 × (100 + 1000 + 1000) = 4620 to several digits, and doubling C leaves it unchanged. Then `.venv/bin/ema profile examples/simvascular/zerod_rcr/model_mean.json -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.2 — prepare svZeroDSolver's closed-loop heart case. Plan mode first. Source: tests/cases/closedLoopHeart_singleVessel.json (v3.0). Put it in examples/simvascular/zerod_heart/ as in Stage 4.1, with placeholders for Elv_s = 3.125 [2, 4.5], Erv_s = 2.125 [1.5, 3], and the RCR_aorta Rd = 1.356 [1.0, 2.0] and C = 0.238 [0.15, 0.35]; keep every other value. Output: the mean pressure_in of branch0_seg0 over the last cycle (python parser). First run the nominal case with 10, 20 and 40 cycles and report how much the output changes; choose the cycle count with me. timeout_s 60. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 4.3 — prepare svOneDSolver's bifurcation for EMA. Plan mode first. Source: 05_bifurcation_RCR.in from the SimVascular documentation (Stage 3). Put it in examples/simvascular/oned_bifurcation/ as case.template with placeholders for the RCR_VALS table (Rp = 90 [45, 180], C = 8e-4 [2e-4, 3.2e-3] (scale log), Rd = 1200 [600, 2400]) and the material's k3 = 8.65e5 [4e5, 1.6e6] (scale log); keep everything else. Command: [~/src/svOneDSolver_build/bin/OneDSolver as an absolute path, case.in]; note in the description that the binary isn't hashed and give its commit. Output: an isolated python parser that reads the Aorta segment's pressure file (use the name you found in Stage 3), takes the inlet row, and returns max − min over the columns of the last 0.9 s cycle (the inflow table's period). timeout_s 300. Check by hand that raising k3 raises the pulse pressure. Then `.venv/bin/ema profile ... -n 5`. Stop and report; don't run a campaign.
```

```text
Stage 5 — first SimVascular campaign. For examples/simvascular/zerod_rcr/model_mean.json and model_pulse.json, write campaign files with repeat (n_points 2, replicates 2), sobol (n_base 256) and, for the pulse model, curve1d on C (n 21) and linear_coeffs with log_output. Use `.venv/bin/ema estimate` for each and report run counts and estimated times, and ask me before `ema run`. After they run, report: whether repeats are identical; for the mean, whether linear_coeffs is exact and C is flagged negligible (the known answer: mean = 2.2 (R + Rp + Rd)); for the pulse pressure, sobol's ranking and interaction share and what curve1d shows along C. Suggest (don't run) the same campaign on the closed-loop heart. Stop and report.
```

```text
Stage 6 — SimVascular 0D/1D troubleshooting. An EMA SimVascular model fails or gives odd values. Diagnose read-only first, from the run directory's files and by running the command by hand in a copied run directory. Check for: a JSON template that no longer parses after rendering (number_format producing invalid JSON, a placeholder left in), Newton non-convergence messages (absolute_tolerance, time steps per cycle), outputs that still drift between cycles (too few cycles; compare the last two), output_all_cycles left true (the parser then averages over every cycle), the 1D solver's output file name or layout differing from what the parser expects, 1D instability at extreme stiffness or time step, and a pip build that fetched a different svZeroDSolver than v3.0. Report the cause and a proposed fix. Ask before changing the env, the build, or model.json.
```

**Gotchas and sources.**
- Licenses: svZeroDSolver and svMultiPhysics BSD-3-Clause; svOneDSolver its own permissive-looking Stanford/UC licence (read `LICENSE.txt`).
- Version pinning: svZeroDSolver's newest code is on `master` (its `pyproject.toml` says 2.0 while the last tag is v3.0), so pin the tag and record it; svOneDSolver has no releases, so record the commit. Both binaries live outside the model directory and are not hashed.
- Determinism: both solvers are deterministic; outputs depend on Newton tolerances and time steps at the level of those tolerances.
- Periodic state: lumped and 1D models need several cycles to become periodic; the time constant Rd·C sets how many. Too few cycles make the output depend on C through the transient, which EMA would report as structure.
- Units: the test cases use CGS or mmHg-based units inconsistently between cases (see the `_comment_` fields); keep each case's units and say so in the description.
- Sources: https://simvascular.github.io, https://github.com/SimVascular, https://github.com/SimVascular/svZeroDSolver, https://github.com/SimVascular/svZeroDSolver/releases, https://github.com/SimVascular/svZeroDSolver/tree/v3.0/tests/cases, https://github.com/SimVascular/svZeroDSolver/blob/master/pyproject.toml, https://simvascular.github.io/svZeroDSolver/, https://simvascular.github.io/documentation/rom_simulation.html, https://github.com/SimVascular/SimVascular.github.io/tree/main/documentation/rom_simulation, https://github.com/SimVascular/svOneDSolver, https://github.com/SimVascular/svMultiPhysics, https://github.com/SimVascular/SimVascular/releases, https://hub.docker.com/r/simvascular/solver, https://hub.docker.com/r/simvascular/svmultiphysics, https://www.vascularmodel.com

---

### 4.12 Visualization tools: PyVista and VisIt (post-processing, not models)

Desk research, checked 2026-09-24. Nothing here was installed or run. **Neither package is a model.** They have no inputs to vary and no output to analyse, so EMA can't run a campaign on them. They are listed because many packages in sections 4.1–4.4 write fields (VTK/VTU, XDMF, OpenFOAM cases, Exodus), while EMA needs **one scalar per run**. A post-processor turns a field into that scalar: an integral over a surface, a maximum along a probe line, the area where a field exceeds a threshold. It also draws figures of selected runs. The "examples" below are therefore reductions applied to examples this document already prepares. The "model" in each row is the upstream package's example, and PyVista or VisIt supplies its output.

How a reduction fits EMA's constraints:
- **Not as a `python` output parser.** EMA runs a `python` parser in an isolated child of **EMA's own interpreter**, so the parser could import PyVista only if PyVista were installed into EMA's `.venv`, which this plan forbids.
- **Instead, make the reduction the last step of the run.** Either the driver (already running in the package's env) imports PyVista, or a wrapper script in the model directory runs the solver and then `<ema-pyvista python> reduce.py`. The script prints `EMA_OUTPUT <value>`, and a `regex` parser reads it. The wrapper and `reduce.py` sit next to `model.json`, so EMA's version hash covers them.
- **Prefer the solver's own reduction when it has one.** Examples: FEniCSx's `assemble_scalar`, OpenFOAM function objects (`probes`, `surfaceFieldValue`), SU2's `history.csv`, Elmer's `SaveScalars`. These are cheaper (no field written to disk) and exact on the solver's own discretization. Use a post-processor when the quantity needs geometry the solver doesn't offer, when the code has no such hook, or when the same reduction should apply to several codes.
- **AWS instance:** a reduction adds under a few seconds per run, so use the upstream package's instance (section 3). No GPU is needed: reductions don't render, and figures can render off-screen.

---

#### PyVista

**What it is.** PyVista is a Pythonic interface to VTK: it reads meshes and fields, filters them (slice, clip, threshold, integrate, sample along a line), and plots them. Language: Python. License: MIT. Current release **pyvista 0.49.0 (2026-09-08)**, which requires Python ≥ 3.10 and `vtk>=9.3.1,<9.8.0` (excluding 9.4.0 and 9.4.1). VTK's current release is **9.7.0 (2026-08-15)**.
Examples: the gallery at https://docs.pyvista.org/examples/ (hundreds of scripts; the "Filtering" section holds the reductions used here: "Integrate Data", "Plot Over Line"; source in `examples/` of https://github.com/pyvista/pyvista).
Readers relevant to this document, from `pyvista.read`'s extension table in 0.49.0:

| format | reader |
|---|---|
| `.vtu` | `XMLUnstructuredGridReader` |
| `.pvd` | `PVDReader` |
| `.xdmf` | `XdmfReader` |
| `.foam` | `POpenFOAMReader` |
| `.e`, `.exo` | `ExodusIIReader` |
| CGNS | `CGNSReader` |
| other formats | `meshio`, if installed |

ADIOS2 `.bp` (FEniCSx's `VTXWriter`) is not in the table **(unconfirmed whether VTK 9.7's ADIOS2 reader is in the pip wheel)**.
**Fit.** PyVista has no model to analyse. Its role is (a) the reduction step inside a run, and (b) figures of chosen runs for the analyst, outside EMA.

**Install on an Intel Mac.** Pip works here, unlike for the ML emulators. PyPI has `vtk` 9.7.0 wheels for **macOS x86_64 (`macosx_10_10_x86_64`) for CPython 3.10–3.14**, about 111 MB each, and `pyvista` is pure Python. conda-forge also has `vtk` 9.7.0 for osx-64 and `pyvista` 0.49.0 (noarch). Two routes:
1. **Into the package's own env** (for FEniCSx, Firedrake, NGSolve, SfePy and other Python packages): add it there from conda-forge, so the driver can import it:
   ```bash
   ~/miniforge3/bin/mamba install -n fenicsx-0.11 -c conda-forge pyvista=0.49.0
   ```
2. **A standalone env for wrapper scripts** (for compiled codes and Docker routes, such as OpenFOAM, SU2 and Elmer):
   ```bash
   ~/miniforge3/bin/mamba create -n ema-pyvista -c conda-forge python=3.12 pyvista=0.49.0 vtk=9.7.0 numpy
   # or, with any Python 3.10–3.14 that is NOT EMA's .venv:
   python3.12 -m venv ~/envs/ema-pyvista && ~/envs/ema-pyvista/bin/pip install pyvista==0.49.0 vtk==9.7.0
   ```
3. Check (no window opens):
   ```bash
   ~/miniforge3/envs/ema-pyvista/bin/python -c "import pyvista as pv, vtk; print(pv.__version__, vtk.vtkVersion.GetVTKVersion()); s=pv.Sphere(); s.point_data['one']=1.0; print(s.integrate_data()['Area'][0])"
   ```
   Expect `0.49.0 9.7.0` and an area close to π.

Known problems:
- Mixing conda's and pip's VTK in one env breaks imports. Pick one.
- Plotting on macOS pulls in `pyobjc-framework-Cocoa` (a pyvista dependency on darwin).
- Reductions don't need a display.

Sources: https://pypi.org/project/vtk/#files, https://pypi.org/project/pyvista/, https://anaconda.org/conda-forge/vtk, https://anaconda.org/conda-forge/pyvista, https://docs.pyvista.org/getting-started/installation.html

**Install on AWS (Ubuntu 24.04 EC2).** Pip in a venv (Linux `vtk` 9.7.0 wheels exist for CPython 3.10–3.14), or the same conda env:
```bash
sudo apt-get install -y python3-venv          # ask first; only if missing
python3 -m venv ~/envs/ema-pyvista && ~/envs/ema-pyvista/bin/pip install pyvista==0.49.0 vtk==9.7.0
~/envs/ema-pyvista/bin/python -c "import pyvista as pv; print(pv.Report())"
```
Headless: filtering needs no display. For figures, use `pv.OFF_SCREEN = True` or `pv.start_xvfb()` (needs `xvfb` from apt). Whether the pip VTK 9.7 wheel falls back to off-screen OSMesa/EGL without X is **(unconfirmed)**. Official Docker images exist (`ghcr.io/pyvista/pyvista`) **(unconfirmed tags)**, but a venv is simpler.
Sources: https://docs.pyvista.org/getting-started/installation.html, https://pypi.org/project/vtk/#files

**Preparing the examples for EMA.** Write one reusable helper, `examples/_post/pv_reduce.py` (a proposed location; each model directory gets its own copy, so EMA hashes it). It holds a few functions: `read_last(path)` (the last time step of a `.foam`, `.pvd` or `.vtu`), `integrate(mesh, field)`, `line_extreme(mesh, field, a, b, n, kind)`, and `surface_extreme(mesh, patch, field, kind)`, plus a command-line entry `python pv_reduce.py <spec.json>` that prints `EMA_OUTPUT %.12e`. A model then uses either:
- **A wrapper** (compiled or Docker solvers): the command is `["<ema-pyvista python>", "run_and_reduce.py"]`. `run_and_reduce.py` runs the solver command with `subprocess.run(..., check=True)`, then the reduction. It is a static file in the model directory. With Docker, the solver runs in the container and the reduction on the host, since both see the run directory.
- **The driver** (Python solvers): `import pyvista` at the end of `run.py`.

The solver must write the field, so re-enable the VTU/field output that the upstream sections turned off for speed, but only the last time step. Rules for stable scalars:
- Integrate rather than take maxima of nodal values.
- Sample along a fixed line with a fixed `resolution`.
- Interpolate (`sample_over_line` uses probe filtering) rather than pick nearest nodes, so the scalar doesn't jump when the mesh moves.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| OpenFOAM cavity, `examples/openfoam/cavity/` from this document's §4.3 (ESI `tutorials/incompressible/icoFoam/cavity/cavity`) | the upstream model: transient laminar lid-driven cavity; PyVista reads the case through an empty `case.foam` file (`POpenFOAMReader`) at the last time | as in §4.3: `U_lid` 1 [0.5, 2] (log), `nu` 0.01 [0.002, 0.02] (log) | min of Ux/U_lid along the vertical centreline x = 0.05 (`sample_over_line`, 200 points): the classic Ghia benchmark quantity | depends on Re = U_lid·L/nu only, so the two inputs collapse onto one direction: `active_subspace` should find one dimension along ln U_lid − ln nu. Monotone (stronger backflow at higher Re). Compare with §4.3's probe output: both should rank the inputs the same | cavity time (§4.3) + 1–2 s for the PyVista import and reduction *(estimate)* | cli (Docker or native solver + host wrapper) | regex |
| SU2 NACA 0012, `examples/su2/naca...` from §4.3 (`QuickStart/inv_NACA0012.cfg`) with `OUTPUT_FILES= (RESTART, SURFACE_PARAVIEW)` | the upstream model: inviscid transonic Euler; PyVista reads `surface_flow.vtu` | `MACH` 0.8 [0.5, 0.85]; `AOA` 1.25° [−2, 4] | chordwise shock position on the upper surface: the x/c of the largest drop in `Pressure_Coefficient` along the upper surface (field name **(unconfirmed)**; list the arrays first) | absent (NaN or fixed "no shock" value) below the critical Mach number, then moving aft with Mach: a **kink** at shock onset, and piecewise-constant steps at the surface resolution. `nonsmooth` and `curve1d` should report both "at this resolution". Mach × AOA interaction | SU2 time (§4.3) + 1 s *(estimate)* | cli (wrapper) | regex |
| FEniCSx Robin, `examples/fenicsx/robin/` (§4.1): a **counterexample** | steady heat conduction; the driver already computes ∫u dx with `assemble_scalar` | as in §4.1 | ∫u dx computed two ways: in DOLFINx and by `integrate_data` on a VTU written by `dolfinx.io.VTKFile` | the two should agree to discretization precision. If they don't, the VTU path interpolated or lost cells. Use it as a test of the helper, then keep the DOLFINx integral in the model | + 1–2 s *(estimate)* | cli (driver) | regex |

**Claude Code prompts.**

```text
Stage 1 (PyVista, read-only check). I want PyVista 0.49.0 (VTK 9.7.0) as a post-processor that turns simulation output into one scalar per EMA run. It will never be installed into EMA's .venv, because EMA's python output parsers run with EMA's own interpreter, so the reduction must run inside the model's command. Read-only: report OS, uname -m, Pythons available outside EMA's .venv (which -a python3 python3.12; Miniforge envs), whether any env already has pyvista or vtk (conda list -n <env> pyvista vtk), whether a display exists (on Linux: $DISPLAY, xvfb-run), and free disk. Don't install anything, and don't read .env. Recommend: add pyvista to the package's own conda env for Python solvers, and a separate ema-pyvista env for compiled or Docker solvers. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (PyVista, install on the Intel Mac). Create ~/miniforge3 env ema-pyvista from conda-forge only: python=3.12 pyvista=0.49.0 vtk=9.7.0 numpy (never EMA's .venv, never the defaults channel, and never read .env). Ask before installing Miniforge and before any Homebrew change or sudo. Don't mix pip VTK into a conda env. Check: print pyvista and VTK versions, and integrate a constant field over pv.Sphere() (the area should be close to pi) without opening a window. Report the env's absolute python path. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b (PyVista, install on AWS Ubuntu 24.04). Create a venv ~/envs/ema-pyvista with the system python3 (ask me before sudo apt-get install python3-venv if it's missing) and pip install pyvista==0.49.0 vtk==9.7.0 (never EMA's .venv, and never read .env). Check versions and the sphere integral as on the Mac. Then check that off-screen rendering works: pv.OFF_SCREEN = True; save a screenshot of a sphere to /tmp/pv.png. If it fails, report the error and propose, without installing, either xvfb or an OSMesa/EGL VTK build. Stop and report; don't continue to the next stage.
```

```text
Stage 3 (PyVista smoke test on real output). Take one completed run directory of an existing model that writes VTK data: for OpenFOAM, run the §4.3 cavity case once by hand outside EMA; or any .vtu from examples/su2 or examples/elmer, if prepared. With the ema-pyvista python, read it (for OpenFOAM, create an empty case.foam and use pv.POpenFOAMReader; set_active_time_value(reader.time_values[-1])), and report: the blocks and arrays (names, point or cell data), the bounds, integrate_data() of one scalar array, sample_over_line along a line you name, and the time each step takes, including `import pyvista`. Don't change the model. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (PyVista, reduction for the OpenFOAM cavity). Plan mode first; show me the plan. Write a reusable helper pv_reduce.py (functions read_last, integrate, line_extreme, surface_extreme, and a CLI that takes a small JSON spec and prints "EMA_OUTPUT %.12e"; docstrings in NumPy style) and copy it into a new model examples/openfoam/cavity_centreline/, which reuses examples/openfoam/cavity/'s templates. Add a static wrapper run_and_reduce.py that runs the same solver command as cavity/model.json (Docker or native, as installed) with subprocess.run(check=True), creates case.foam, and runs the reduction: the min of Ux/U_lid along x = 0.05, y from 0 to 0.1, 200 points, at the last time (U_lid read from the rendered 0/U, or passed as an argument). Make controlDict write only the final time. model.json: command [the ema-pyvista env's absolute python, "run_and_reduce.py"], regex parser on EMA_OUTPUT, timeout_s 3 × the cavity's. Hand check: the value at the nominal point is negative and between -0.5 and 0 (backflow on the centreline). Then `ema profile examples/openfoam/cavity_centreline/model.json -n 3` and report the solver time vs the reduction time. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (PyVista, reduction for SU2 NACA 0012). Plan mode first. Create examples/su2/naca_shock/ from examples/su2/<the naca model>/, with OUTPUT_FILES= (RESTART, SURFACE_PARAVIEW) and output written only at the end. First list surface_flow.vtu's arrays and tell me the pressure-coefficient array's name. Add surface_extreme-style logic to pv_reduce.py (copy it into the directory): order the upper-surface points by x/c, and report the x/c of the steepest drop in Cp, or -1 if the drop is below a threshold relative to the Cp range (say which threshold and why; EMA's rule is that thresholds scale with the output). The wrapper runs SU2_CFD, then the reduction. Hand check at MACH 0.8, AOA 1.25 (a shock expected on the upper surface) and at MACH 0.5 (none expected). Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 (PyVista, first campaign with a reduction). For examples/openfoam/cavity_centreline/model.json, write campaign.json with repeat (n_points 2, replicates 2), morris (n_traj 6), and active_subspace (the smallest valid size; check its spec in docs/diagnostics/). Run `ema estimate`, show me the run count and time, and ask before `ema run`. Report: repeatability, the morris ranking, whether active_subspace finds one dimension, and its direction (expected: roughly equal and opposite weights on ln U_lid and ln nu, because the output depends on Re only). Stop and report.
```

```text
Stage 6 (PyVista troubleshooting). A model whose output comes from pv_reduce.py fails or gives odd values. Diagnose read-only first: run the wrapper by hand in a copied run directory. Check: `import pyvista` or `vtk` errors (the wrong interpreter in model.json; pip and conda VTK mixed); the reader finding no time steps (OpenFOAM: case.foam missing, or the final time not written; reader.time_values); the array missing or renamed (point vs cell data; call cell_data_to_point_data before sampling); sample_over_line returning NaN or zeros outside the mesh (the line's end points on or just outside the boundary: pull them in by a small relative tolerance); values that jump with mesh changes (nearest-node picking instead of interpolation); a reduction slower than the solver (reading all time steps; read only the last); files left behind in the run directory filling the disk. Report the cause and a proposed fix. Ask before changing the helper or model.json.
```

**Gotchas and sources.**
- License: MIT (PyVista) and BSD-3-Clause (VTK).
- Threads: VTK filters are mostly serial here. Set `OMP_NUM_THREADS=1` in the model's `env` anyway, since some VTK builds use SMP tools.
- Determinism: reading and integrating are deterministic. Line sampling depends on `resolution` and on probe tolerance. Fix both in the spec, and record them in the model description.
- Run time: `import pyvista` costs about 0.5–2 s per run *(estimate)*, which matters only for sub-second solvers. Reading a large multi-time case can exceed the solve, so read only the last time step.
- Version pitfalls: pyvista 0.49 accepts VTK 9.3.1–9.7.x (not 9.4.0 or 9.4.1). Array names differ between solver versions, so the helper should fail loudly (no output line → a failed run) when an array is missing, never silently return 0.
- Plotting for the analyst (figures of selected runs) is outside EMA's figures and data cards. Label those figures as illustrations, not results.
- Sources: https://pyvista.org, https://github.com/pyvista/pyvista, https://github.com/pyvista/pyvista/releases, https://pypi.org/project/pyvista/, https://pypi.org/project/vtk/#files, https://anaconda.org/conda-forge/vtk, https://anaconda.org/conda-forge/pyvista, https://docs.pyvista.org/getting-started/installation.html, https://docs.pyvista.org/examples/, https://docs.pyvista.org/api/core/_autosummary/pyvista.datasetfilters.integrate_data (integrate_data: "Area or volume is also provided in point data"; it uses `vtkIntegrateAttributes`)

---

#### VisIt

**What it is.** VisIt is LLNL's parallel visualization and analysis application: a GUI plus a Python command-line interface. You run a script headless with `visit -nowin -cli -s script.py`. It reads more than a hundred formats, including Silo, Exodus, VTK, OpenFOAM, Xdmf and many lab formats. License: BSD-3-Clause. Current release **VisIt 3.5.0 (2026-04-29)**: it bundles Python 3.13.9 and dropped Python 2. Its new `visit_launcher` module imports VisIt into a standalone Python.
**Intel Mac: 3.5.0 has no Intel binary.** Its macOS download is `visit3_5_0.darwin24-arm64.dmg` only. The last Intel-Mac binaries are **VisIt 3.4.2 (2024-12-20)**: `visit3_4_2.darwin22-x86_64.dmg` (785 MB) or `.txz` (332 MB), built on macOS 13.
Examples: the Python scripting tutorial (https://visit-sphinx-github-user-manual.readthedocs.io/en/3.4rc/tutorials/Scripting.html), the CLI manual, and the regression-testing notes on visitusers.org. Scalar reductions are queries: `Query("Weighted Variable Sum")` (a cell sum weighted by volume or area, i.e. an integral), `Query("Max")`, `Query("Variable Sum")`, followed by `GetQueryOutputValue()`. Lineouts use `Lineout(...)`.
**Fit.** VisIt has no model to analyse. It plays the same role as PyVista, but it is **heavy**: a 600 MB install, several seconds to start a headless viewer and engine per run *(estimate)*, and a bundled Python that can't import the solver's packages. **Prefer PyVista** unless:
- the data are in a format only VisIt reads well (Silo, some lab formats);
- the team already has VisIt query scripts to reuse;
- a query needs VisIt's specific algorithms (for example, its connected-components or its RZ revolved-volume weighting).

**Install on an Intel Mac.** Two routes, both without Homebrew:
1. **VisIt 3.4.2 native** (the last Intel build): download `visit3_4_2.darwin22-x86_64.dmg` from the GitHub release (785 MB; ask first). Drag `VisIt.app` to `/Applications`. The CLI is then `/Applications/VisIt.app/Contents/Resources/bin/visit`.
   ```bash
   curl -LO https://github.com/visit-dav/visit/releases/download/v3.4.2/visit3_4_2.darwin22-x86_64.dmg
   /Applications/VisIt.app/Contents/Resources/bin/visit -version
   ```
   Gatekeeper may block the unsigned app on first launch **(unconfirmed)**. Clear it by opening it once from Finder, not by disabling Gatekeeper.
2. **VisIt 3.5.0 in Docker** (linux/amd64): there's no official image **(unconfirmed; none found)**. Build one from `ubuntu:24.04` pinned by digest, adding `visit3_5_0.linux-x86_64-ubuntu24.tar.gz` (607 MB) unpacked with the release's `visit-install3_5_0` script, and run `visit -nowin -cli -s` inside it. This fits models whose solver already runs in Docker.

Check: `visit -nowin -cli -s check.py`, where `check.py` prints `Version()` and calls `sys.exit(0)`.
Sources: https://github.com/visit-dav/visit/releases (asset lists for v3.5.0 and v3.4.2), https://visit-dav.github.io/visit-website/releases-as-tables/, https://visit-sphinx-github-user-manual.readthedocs.io/en/3.4rc/tutorials/Scripting.html

**Install on AWS (Ubuntu 24.04 EC2).** VisIt 3.5.0 has an Ubuntu 24.04 build:
```bash
cd ~/src
curl -LO https://github.com/visit-dav/visit/releases/download/v3.5.0/visit3_5_0.linux-x86_64-ubuntu24.tar.gz
curl -LO https://github.com/visit-dav/visit/releases/download/v3.5.0/visit-install3_5_0
curl -LO https://github.com/visit-dav/visit/releases/download/v3.5.0/visit_checksums_and_sizes.txt
sha256sum visit3_5_0.linux-x86_64-ubuntu24.tar.gz    # compare with the checksums file
bash visit-install3_5_0 3.5.0 linux-x86_64-ubuntu24 ~/opt/visit   # argument order per INSTALL_NOTES (unconfirmed)
~/opt/visit/bin/visit -version
```
Headless: `-nowin` renders off-screen with the bundled Mesa. Missing system libraries (for example `libGL`, `libxkbcommon`) may need apt packages **(unconfirmed which; ask before sudo)**.
Sources: https://github.com/visit-dav/visit/releases/tag/v3.5.0, https://github.com/visit-dav/visit/releases/download/v3.5.0/INSTALL_NOTES_3_5_0

**Preparing the examples for EMA.**
- **Wrapper.** A static `run_and_reduce.py` (or `.sh`), run by any Python outside EMA's venv, runs the solver, then `visit -nowin -cli -s reduce_visit.py -args <file> <var>`. `-args` passes arguments to the script **(unconfirmed spelling; check `visit -help`)**.
- **The script.** `reduce_visit.py` does `OpenDatabase(file)`, `AddPlot("Pseudocolor", var)`, `DrawPlots()`, `Query("Weighted Variable Sum")` (or `"Max"`), then `print("EMA_OUTPUT %.12e" % GetQueryOutputValue())` and `sys.exit(0)`.
- **Lineouts.** `Lineout(start, end, samples)` creates a curve in a second window. Reading its values back needs `GetPlotInformation()` or a `"Lineout"` query **(unconfirmed API; test in Stage 3)**.
- **Output handling.** VisIt prints banners and warnings on stdout, so the regex must anchor on `EMA_OUTPUT`. VisIt 3.5 writes `visitlog.py` (renamable with `-python-log-file`) into the working directory, which is the run directory, which is fine.

| example (path/URL) | physics | inputs: nominal [range] | output(s) | expected structure EMA should find | est. time/run (laptop config) | model type | parser |
|---|---|---|---|---|---|---|---|
| OpenFOAM pitzDaily, `examples/openfoam/pitzdaily/` from §4.3 (ESI `tutorials/incompressible/simpleFoam/pitzDaily`); VisIt opens `case.foam` | the upstream model: steady RANS backward-facing step | as in §4.3: `U_in` 10 [5, 15] (log), `nu` 1e-5 [5e-6, 2e-5] (log), `I` 0.05 [0.01, 0.1] | area of the recirculation zone: `Weighted Variable Sum` of an expression `if(lt(U_X, 0), 1, 0)` over the domain (VisIt expression syntax **(unconfirmed)**) | increasing then saturating with Re (U_in/nu), with `I` a weaker effect; steps at cell resolution (an indicator function summed over cells), which `nonsmooth` should label "at this resolution" | pitzDaily time + 3–10 s of VisIt start-up *(estimate)* | cli (wrapper) | regex |
| Elmer CavityLid, `examples/elmer/cavity...` from §4.2 (`fem/tests/CavityLid`), with `ResultOutputSolver` writing VTU at the end | the upstream model: steady lid-driven cavity FEM | as in §4.2: `Density`, `Viscosity`, lid velocity (all log) | kinetic energy ∫ ½ρ\|u\|² dA: `Weighted Variable Sum` of an expression on `velocity` | depends on Re (one active direction) and scales with ρ·U² (a power law: `linear_coeffs(log_output=True)` should find exponents near 1 for density and 2 for lid velocity, modified by the Re dependence) | Elmer time + 3–10 s *(estimate)* | cli (wrapper) | regex |

**Claude Code prompts.**

```text
Stage 1 (VisIt, read-only check). I'm considering VisIt as a scripted post-processor for EMA runs (visit -nowin -cli -s). Read-only: report OS and version, uname -m, whether VisIt is already installed (/Applications/VisIt.app, `which visit`, ~/opt/visit) and its version, Docker, free disk, and on Linux whether libGL/Mesa libraries are present (ldconfig -p | grep -i -E "libGL|OSMesa"). Don't install anything, and don't read .env. Recommend: on the Intel Mac, VisIt 3.4.2 darwin22-x86_64 (3.5.0 has no Intel build) or 3.5.0 inside a linux/amd64 container; on Ubuntu 24.04, the 3.5.0 ubuntu24 tarball. Also say whether PyVista would do the same job here more simply. Stop and report; don't continue to the next stage.
```

```text
Stage 2a (VisIt, install on the Intel Mac). Ask me first: download visit3_4_2.darwin22-x86_64.dmg (785 MB) from github.com/visit-dav/visit/releases/tag/v3.4.2, verify it against that release's visit_checksums_and_sizes.txt, and tell me when to drag VisIt.app to /Applications (I'll do it; don't use sudo). No Homebrew, never EMA's .venv, and never read .env. Then check: /Applications/VisIt.app/Contents/Resources/bin/visit -version, and a headless script check.py that prints Version() and exits with sys.exit(0), run with -nowin -cli -s. Report both outputs and the wall time of the headless start-up. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 2b (VisIt, install on AWS Ubuntu 24.04). Ask me before downloading visit3_5_0.linux-x86_64-ubuntu24.tar.gz (607 MB) and visit-install3_5_0 from the v3.5.0 GitHub release into ~/src; verify the checksum; read INSTALL_NOTES_3_5_0 for visit-install's argument order, then install into ~/opt/visit (no sudo). Never EMA's .venv, and never read .env. Check `~/opt/visit/bin/visit -version` and the same headless check.py. If shared libraries are missing, list them (ldd on the engine binary) and propose apt packages; ask before sudo. Stop at the first error and report; don't continue to the next stage.
```

```text
Stage 3 (VisIt smoke test on real output). Using one completed run directory of an existing model (the §4.3 OpenFOAM pitzDaily case run once by hand, with an empty case.foam), write /tmp/q.py for visit -nowin -cli -s: OpenDatabase the case at its last time state, list the variables (from GetMetaData or the database's metadata), AddPlot("Pseudocolor", "p"), DrawPlots(), Query("Weighted Variable Sum"), Query("Max"), and print each GetQueryOutputValue(). Also try Lineout along a line you choose and find how to read its values back in this version (GetPlotInformation or a query); tell me what worked. Report the values, the VisIt start-up time, and the query time. Don't change any model. Stop and report; don't continue to the next stage.
```

```text
Stage 4.1 (VisIt, reduction for OpenFOAM pitzDaily). Plan mode first. Create examples/openfoam/pitzdaily_recirc/ reusing examples/openfoam/pitzdaily/'s templates. Add a static wrapper run_and_reduce.py (run by a Python outside EMA's .venv; say which one) that runs the same solver command as pitzdaily/model.json with subprocess.run(check=True), creates case.foam, then runs `<absolute visit path> -nowin -cli -s reduce_visit.py` with the file and variable passed as arguments (confirm the -args spelling with visit -help). reduce_visit.py defines the expression recirc = if(lt(U_X, 0), 1, 0) (check VisIt's expression syntax and the velocity component names in Stage 3's variable list), plots it, runs Query("Weighted Variable Sum"), and prints "EMA_OUTPUT %.12e" then sys.exit(0). Regex parser anchored on ^EMA_OUTPUT. Hand check: a positive area at the nominal point, larger at U_in 15 than at 5. Then `ema profile ... -n 3` and report solver vs VisIt time. If VisIt adds more than half the run time, say so and propose the PyVista equivalent. Stop and report; don't run a campaign.
```

```text
Stage 4.2 (VisIt, reduction for Elmer CavityLid). Plan mode first; only if examples/elmer/ has a CavityLid model. Create examples/elmer/cavity_ke/: add a ResultOutputSolver writing VTU at the end (check the Elmer section of docs/brainstorms/pde_packages_onboarding.md and Elmer's docs for the keywords), and a VisIt reduction of kinetic energy 0.5*rho*|velocity|^2 integrated with Weighted Variable Sum (rho from the deck, passed as an argument). Wrapper and parser as in pitzdaily_recirc. Hand check: doubling the lid velocity at fixed Re (scale the viscosity too) multiplies the output by about 4. Then `ema profile ... -n 3`. Stop and report; don't run a campaign.
```

```text
Stage 5 (VisIt, first campaign with a reduction). For examples/openfoam/pitzdaily_recirc/model.json, write campaign.json with repeat (n_points 2, replicates 2) and morris (n_traj 6). Run `ema estimate` (it prices VisIt's start-up into each run) and ask me before `ema run`. Report repeatability, the morris ranking, any failed runs (VisIt errors count as failures: say which), and whether nonsmooth-looking behaviour comes from the cell-count indicator. Expected: U_in and nu matter through Re; I is weaker. Stop and report.
```

```text
Stage 6 (VisIt troubleshooting). A model whose output comes from VisIt fails or is slow. Diagnose read-only first: run the wrapper by hand in a copied run directory. Check: VisIt not found (a relative path, or the app moved); the viewer or engine failing to start headless (missing libGL/OSMesa on Linux; the -nowin flag); the script hanging because it doesn't call sys.exit (runs then hit timeout_s); OpenDatabase failing (case.foam missing, the wrong time state; use TimeSliderSetState to go to the last); an expression error (component names, syntax); query output printed in a different format (anchor the regex on EMA_OUTPUT); stdout flooded by warnings; start-up time dominating. Report the cause and a proposed fix, including whether PyVista would remove the problem. Ask before changing anything.
```

**Gotchas and sources.**
- License: BSD-3-Clause.
- Parallelism: run the serial engine (the default with `-nowin -cli`). Don't launch VisIt's parallel engine inside EMA runs.
- Determinism: queries are deterministic for a given file.
- Run time: every run starts a viewer and an engine: several seconds *(estimate)*, often longer than the reduction. That matters for thousands of runs.
- Version pitfalls: Intel-Mac users are stuck at 3.4.2 natively, while AWS runs 3.5.0, so a reduction script must work on both (check query names and `GetQueryOutputValue`'s return type, a float or a tuple, on each).
- Python: VisIt's CLI runs its **own bundled Python** (3.13.9 in 3.5.0), which can't import numpy from the solver's env **(unconfirmed whether numpy is bundled)**. Keep `reduce_visit.py` to VisIt's API plus the standard library.
- When to prefer PyVista: almost always for EMA. It is a pip or conda package with Intel-Mac wheels, starts in about a second, and lives in the same Python as a Python solver's driver. Choose VisIt only for its formats, for existing scripts, or for its specific queries.
- Sources: https://visit-dav.github.io, https://github.com/visit-dav/visit, https://github.com/visit-dav/visit/releases, https://visit-dav.github.io/visit-website/releases-as-tables/, https://raw.githubusercontent.com/visit-dav/visit/v3.5.0/src/resources/help/en_US/relnotes3.5.0.html, https://visit-sphinx-github-user-manual.readthedocs.io/en/3.4rc/tutorials/Scripting.html, https://visit-sphinx-github-user-manual.readthedocs.io/en/v3.2.2/cli_manual/index.html, https://visitusers.org/index.php?title=VisIt-tutorial-Advanced-PythonQuery


## 5. Comparison and a suggested order

### Summary

The time per run is the laptop-size configuration from each section. All of these times are estimates for `ema profile` to measure.

| package | Intel Mac route | AWS (Ubuntu 24.04) route | how inputs reach it | time per run (est.) | difficulty |
|---|---|---|---|---|---|
| scikit-fem | pip or conda (pure Python) | same | driver + deck | < 1 s | easy |
| FiPy | conda-forge (noarch) or pip | same | driver + deck | about 1 s (dendrite: > 10 s) | easy |
| NGSolve | pip wheels (Python 3.12) | pip, or PPA | driver + deck | seconds | easy |
| py-pde | conda, with numba pinned to 0.62 (no osx-64 builds after that) | conda or pip | driver + deck | seconds | easy |
| SfePy | conda (PyPI has only an sdist) | conda | driver + deck | seconds | easy |
| FEniCSx | conda-forge `fenics-dolfinx=0.11.0` | conda (PPA or Docker as fallbacks) | driver + deck | 1–3 s once the JIT cache is warm | easy to medium |
| Dedalus | conda-forge | conda | driver + deck | seconds | easy to medium |
| Devito | pip | pip | driver + deck (JIT) | seconds | easy to medium |
| PETSc | conda-forge 3.25.5, plus the source tarball to compile the tutorials | conda (apt has only 3.19) | compiled tutorial + **command-line options** | < 1 s to a few s | medium |
| SU2 | conda-forge `su2=8.5.0` | conda or release zip | `.cfg` template | seconds to > 10 s | medium |
| FreeFEM | conda 4.13, or the 4.15 `.dmg` (the last with an Intel build) | conda or apt 4.13 | `.edp` script + `getARGV` arguments | seconds | medium |
| MFEM | serial source build, v4.10 | same | compiled example + command-line options | < 1 s to seconds | medium |
| PyClaw | source build (meson + gfortran in conda; no Intel wheel for 5.14) | pip | driver + deck | seconds | medium on the Mac |
| deal.II | Docker 9.7.1 (no Intel `.dmg` or Homebrew) | PPA 9.6.0 | compiled step + `.prm` template | seconds | medium to hard |
| Firedrake | Docker (Intel Macs unsupported) | native `firedrake-configure` | driver + deck | seconds | medium to hard |
| DUNE (dune-fem) | Miniforge + `pip install dune-fem` 2.12 (source build; unconfirmed on Intel) | venv + pip | driver + deck (JIT) | seconds, after a long first build | hard |
| OpenFOAM | Docker only (no Intel app, conda is linux-64 only) | ESI apt, or Docker | case dictionaries as templates (`$$`) | 5–10+ s | hard |
| MOOSE | Docker `idaholab/moose` (amd64) | conda `moose` | `.i` template (`$$` for `${...}`) | seconds | hard |
| Elmer | a locally built Docker image | native source build | `.sif` template (`$$` for MATC) | seconds | hard |

The packages added in 4.5–4.12, in the same format. Times are estimates from each section.

| package | Intel Mac route | AWS (Ubuntu 24.04) route | how inputs reach it | time per run (est.) | difficulty |
|---|---|---|---|---|---|
| COBRApy | conda-forge (`cobra` noarch, `swiglpk` osx-64) | same, or pip | driver + deck | 1–2 s | easy |
| GTSAM | pip `gtsam==4.3.0` (universal2 wheels) | pip | driver + command-line options | about 0.5 s | easy |
| SLEPc | added to the `ema-petsc` env (`slepc=3.25.2`) | same | compiled tutorial + command-line options | < 0.5 s | easy (after PETSc) |
| AMReX | conda-forge compilers + tutorial source at 26.09 | apt compilers + same source | `inputs` file + `key=value` command-line overrides | < 2 s to 30 s | easy to medium |
| WarpX | conda-forge `warpx=26.09` (needs an AVX2 CPU) | same | `inputs` file + command-line overrides; seed from `EMA_REPLICATE` | < 2 s to minutes | easy |
| climlab | conda-forge | same | driver + deck | 1–20 s | easy |
| PySCF | conda env + pip wheel `pyscf==2.14.0` | same | driver + command-line options | 1–10 s | easy |
| RDKit | conda-forge (no Intel PyPI wheel since 2025.9.3) | conda or pip | driver + command-line options | < 1 s to 30 s | easy |
| SimVascular (0D, 1D) | conda env + svZeroDSolver built from the v3.0 tag; svOneDSolver by CMake | same | JSON or `.in` template | < 1 s (0D), 2–20 s (1D) | easy (0D) to medium (1D) |
| Meep | conda-forge `pymeep=1.34.0` (Python 3.12) | same | driver + command-line options | 2–40 s | easy to medium |
| EnergyPlus | official macOS x86_64 tarball, 26.1.0 | Ubuntu 24.04 tarball | `.idf` template; sqlite output | 2–60 s | easy to medium |
| Scanpy | conda-forge (numba osx-64) | conda or pip | driver + deck; Leiden seed from `EMA_REPLICATE` | 5–40 s | easy to medium |
| LAMMPS | conda-forge `lammps` (nompi) | same | `-var` command-line options, static `in.*` scripts | 1–6 s | medium |
| OpenMM | conda-forge `openmm=8.6.1` | same | driver + command-line options; seed from `EMA_REPLICATE` | 2–60 s | medium |
| OpenSees | conda-forge `opensees=3.8.0` (pip wheels are arm64 only) | conda, or pip `openseespy` | driver + deck | < 1 s to 40 s | medium |
| PyChrono | conda-forge `pychrono=10.0.0` (headless: no Irrlicht) | same | driver + deck | ≤ 3 s | medium |
| OpenSim | conda `opensim-org::opensim=4.5.1` (the last osx-64 build) | pip `opensim==4.6` | driver + deck | 1–60 s | medium |
| Trilinos | conda-forge `trilinos`/`pytrilinos` 16.2.0 | same; Spack for 17.x | PyTrilinos script + command-line options | < 1 s to 3 s | medium |
| hIPPYlib | conda-forge legacy `fenics=2019.1.0` + pip `hippylib==3.2.0` | same | driver + deck | 10 s to 2 min | medium |
| DifferentialEquations.jl | juliaup, Julia 1.12.7, pinned `Manifest.toml` | same, or Docker `julia:1.12.7` | `run.jl` + deck | 2–10 s (start-up dominates; sysimage helps) | medium |
| Nek5000 | source build (serial, conda-forge compilers); NekRS needs a GPU | apt compilers + source build | `.par` template; compiled per case | 10 s to 5 min | medium |
| PFLOTRAN | source build against PETSc 3.24.5 (not `ema-petsc`), or Docker `pflotran/petsc` | same | `.in` template; parser on the observation file | 1–10 s | medium (the build is hard) |
| WRF | a Docker image built from `ubuntu:24.04` | native source build | namelist + sounding written by a driver; netCDF read in the driver | 5 s to 6 min | medium |
| libMesh | INL conda `moose-libmesh` (osx-64, macOS ≥ 13.3) | same, or Spack | GetPot `key=value` command-line overrides | < 0.5 s to 30 s | medium to hard |
| PhysiCell | conda-forge `gxx` (real GCC with OpenMP), or Docker | apt build-essential | XML settings template; seed from `EMA_REPLICATE` | 5 s to 5 min | medium to hard |
| NeuralGCM | conda-forge env (jaxlib osx-64; no Intel PyPI wheel) | conda + pip; GPU for fine grids | driver + deck; seed from `EMA_REPLICATE` | 5 s to 3 min | medium to hard |
| ACE | conda-forge pytorch (CPU) + `fme==2026.5.1` | GPU instance (g5/g6) | driver writes the inference YAML | 1–5 min on CPU, 5–60 s on GPU | medium to hard |
| OpenFAST | conda-forge `openfast=5.0.0` + a built controller | same | static case + driver editing keyed lines; TurbSim seed from `EMA_REPLICATE` | 20–90 s | hard |
| SAMRAI | source build (no conda; Spack stops at 4.5.0) | same | `.input` template + an edited `main.cpp` | 1 s to 5 min | hard (weakest fit in 4.6) |
| MFiX | NETL conda channel after manual registration | same, c7i.4xlarge or larger | `.mfx` template | 5 min to 2 h | hard (AWS for campaigns) |
| NAMD | manual download after registration (not open source) | manual download | Tcl config template (`$$`) | 10–60 s | hard |
| CESM (SCAM only) | Docker `escomp/cesm-2.2` | same, or a CIME port | `atm_in` via a driver; netCDF read in the driver | 20 s to 3 min, after a 20–40 min build | hard |
| E3SM (SCM only) | none supported (a Dockerfile is only planned) | native CIME `linux-generic` build | `atm_in` via a driver | 10–60 s | hard (AWS only) |
| ICON (bubble only) | build inside `iconmodel/icon-dev` (amd64) | native build | namelist template | about 11 s (bubble); aquaplanet minutes | hard |
| ClimaX | not recommended (unmaintained since 2023) | GPU only, after fine-tuning it yourself | driver + deck | 5–15 s once fine-tuned | hard |
| CellBender | conda-forge pytorch + pip | GPU for real data | command-line options via a driver | 30–90 s tiny data; ~30 min on GPU for real data | hard, poor fit |

Not models, so not in the table: **VMD** (an analysis step after an MD run; MDAnalysis or mdtraj do it more simply), and **PyVista** and **VisIt** (post-processors that reduce another model's output to a scalar; PyVista adds 1–2 s per run and is the one to use).

### Suggested order

1. **scikit-fem first.** It is pure Python, and its runs take under a second. Several of its examples have exact answers (the wire's `k_core` is negligible). So it tests EMA's diagnostics against known structure as much as it onboards a package, and it's the cheapest place to settle the common "env python + driver + deck" pattern that ten of these packages share.
2. **Then the other packages with a Python driver:** FiPy, FEniCSx, NGSolve, py-pde, SfePy, Dedalus and Devito. All of them reuse that pattern. FEniCSx comes early because it is the best-known of them.
3. **Then the compiled codes whose inputs are command-line options:** PETSc and MFEM. They need no template at all, since the options carry `$placeholders` in the command. After them, the deck-based codes: SU2 and FreeFEM.
4. **Then Docker or source-build codes, preferably on AWS,** where most of them install natively: deal.II, PyClaw on the Mac, Firedrake, DUNE, MOOSE, Elmer, and OpenFOAM last. OpenFOAM's case directories are the hardest fit for EMA, as the next list explains.

5. **From 4.5–4.12, start with the known answers.** COBRApy (growth piecewise linear in its bounds: exact kinks and plateaus), SimVascular's 0D solver (the capacitance is exactly negligible for mean pressure), LAMMPS's ELASTIC example (the bulk modulus is an exact power law in ε and σ) and GTSAM's pose graph (invariant to scaling every noise sigma together) test EMA's diagnostics as much as they onboard a package, so take them right after scikit-fem. Then the easy conda routes (SLEPc, AMReX, WarpX, climlab, PySCF, RDKit, Meep, EnergyPlus, Scanpy), the stochastic codes that exercise `repeat` and `EMA_REPLICATE` (OpenMM, PhysiCell, WarpX's PIC noise), and last the AWS-only or registration-gated ones (MFiX, NAMD, CESM, E3SM, ICON, ClimaX, CellBender).

Onboarding pure-Python packages on the Intel Mac and the heavy stacks on AWS makes sense: Homebrew no longer builds for Intel Macs, and six of the codes need Docker there.

### What EMA would need to make the hard ones easy (ideas only, nothing planned)

- **Static directories.** `static_files` are copied flat, by file name. OpenFOAM's `0/`, `constant/` and `system/` need to keep their layout. Today, every file must be a template, with every `$` escaped as `$$`, or a static archive that a driver unpacks. A `static_dirs` entry, covered by the hash, would remove that work.
- **Several outputs per command-line model.** A PDE run usually yields several outputs worth studying (drag and lift, peak and mean). Today each needs its own `model.json`, and since the output parser is part of the version hash, the models don't share cached runs: every output reruns the simulation. Reading several outputs from one run would cut the cost of these codes by that factor.
- **A container model type.** It would hash the image digest into the model version, set the user and the mounts, and keep a cache volume (FEniCSx, Devito and DUNE compile code just in time) between runs.
- **Recording the environment.** For a Python package in a conda env, the version hash covers the driver but not the interpreter or the package. A model could name its env and have `provenance` record the versions of its packages.
- **An output parser in the model's environment.** A `python` parser runs under EMA's interpreter, so netCDF, VTK and HDF5 outputs need a driver that prints the scalar (section 2). Letting a model name the interpreter its parser runs in would remove those wrapper scripts.
- **UM-Bridge**, already in the candidate table of `docs/applications.md`. It would reach models that are already served over HTTP.
