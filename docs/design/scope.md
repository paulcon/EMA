# Scope of v2.0

**Status:** accepted. **Updated:** 2026-09-30 (0022, 0025). **Depends on:** OD-2 (0006), OD-5 (0012), OD-6 (0014),
OD-7 (0016, 0019), OD-8 (0017), OD-14 (0013); records 0015, 0018, 0020, 0021.

> What the first release does, what it explicitly doesn't, and the size budgets that keep it small. When
> something new comes up, the question is "is it in this file?", and if not, it waits for a later version.

## In v2.0

| Area | In scope |
|---|---|
| Unit of work | one diagnostic evaluation, with its report (0006) |
| Model interfaces | a Python function; a command-line simulation code with an input deck and an output parser (0014) |
| Running | one model call at a time (a run, or a batch of a Python function model, 0025), on the user's computer; ready for parallel and remote runs later (0015) |
| Designs | point, uniform, convergent (nested uniform), and lines: coordinate, random, or given (0012, 0013) |
| Diagnostics | point run, scatter, coordinate lines, lines, linear model, polynomial model (0012) |
| Model predictions | scalars only, of models not declared noisy (0021); several per model, one analyzed per diagnostic evaluation (0022) |
| Interfaces | Python (`ema.workspace`) and a CLI that calls it |
| Agent | an MCP server: run and read, and set up models from specs; at most 10 tools (0016) |
| Interpretation | none (0017) |
| Model output | kept in each run's directory for inspection outside EMA, with a setting to limit it, and a lookup (0020) |
| Reports | one per diagnostic evaluation: Markdown with TeX math and PNG figures, the reference; a PDF through pandoc when installed (0018) |

- **Lines** draws m random lines, or takes lines the analyst gives, each an anchor and a direction (0012).
- **The polynomial model's report** has U4's lean set (the residual and cross-validated error, the Sobol
  first-order and total indices, a 1-D shadow, a histogram of the residuals) and the decay of its
  coefficients (0012).
- **Ready for parallel and remote runs (0015).** The later specs provide: only the main process writes the
  store; runs are counted against the approval when they start; each run has its own run directory; a
  diagnostic result doesn't depend on the order runs finish; a run has three phases (prepare, execute,
  collect) with only file-based data between them; each run records where it ran; and the model interface
  leaves open whether one model on two machines is one model version. v2.0 has no executor interface.

## Not in v2.0

> The explicit "no" list. Each line says why, or when it might come.

- **Diagnostic campaigns**, studies that vary the model parameter space, and synthesis or comparison across
  diagnostic evaluations: a later version, with its own decision record (0005, 0006).
- **The active subspace and a 2-D shadow** in the polynomial model's report: later, each with its own
  estimator, figure, and known answers (0012).
- **Quadrature and sparse grids:** later, with a projection path in the polynomial model (0013).
- **Formula models** (v1's third kind): not planned; a formula is a one-line Python function (0014).
- **Local parallel runs:** later, as one small build step with its own record (0015).
- **Remote or cluster runs:** later, as several build steps, with decisions in the model interface, data
  model, and trust specs (0015).
- **Array model predictions** (fields, time series): later, as one or two build steps; until then, arrays stay
  in the run directories (0020, 0021).
- **Models declared noisy:** later, as about one build step, plus a section on replicates in each diagnostic
  spec; `noisy: true` is refused. The point run still measures noise (P7, 0011, 0021).
- **Surrogates:** no surrogate objects, and no export of fitted surrogates; analysts build surrogates in
  their own tools from exported runs (`purpose.md`, U4).
- **v1's other diagnostics** (finite differences, Fourier, Morris, nonsmoothness, sampled Sobol, 2-D surfaces,
  surrogate checks, the active subspace): later, each with its own spec and known answers (0012).
- **Deleting kept run directories from EMA** (a clean-up command): the analyst deletes them by hand (0020).
- **Interpretation, advice, and next steps:** later, labeled experimental and kept apart, under P2's rules
  (0017).
- **An own chat loop:** not planned; the agent is an MCP server (0016).
- **Agent-written model code:** the agent drafts model specs only (0016).
- **HTML reports; byte-identical PDFs:** later, if needed (0018).

## Size budgets

> Going over one is a decision, recorded in `docs/decisions/`, not a drift.

| Measure | Budget |
|---|---|
| Diagnostics | 6 (0012) |
| Source lines in `ema` (without tests and reference models) | 8,000 |
| Source lines of reference models | 1,000 |
| Public names in `ema.workspace` (`open_workspace` and the `Workspace` methods) | 20 |
| CLI commands (`ema model add` and `ema model test` count as two) | 15 |
| MCP tools | 10 (0016) |
| CLAUDE.md | 1,500 words |
| Fast test tier | 30 s |
| Runtime dependencies | numpy, scipy, matplotlib; `ema[mcp]` adds the `mcp` SDK; pandoc is an optional system tool (0018) |

- **Where the numbers come from** (2026-09-29): the source lines are estimated at about half of each v1
  counterpart: models ~1,500, store ~700, designs and numerics ~850, diagnostics ~2,200, types, runner,
  approval, and workspace ~1,300, plotting and reports ~500, CLI and MCP ~700; about 7,800 in all. v1's
  `testfunctions/` was 1,411 lines.
- **Names and commands:** the architecture draft has 16 public names and 10 CLI commands; the use cases and
  0020 add `failed_runs`, `reproduce`, and the run-directory lookup, which makes 19 and 13.
- **Dependencies:** a new runtime dependency, in core or in an extra, is a decision with a record.

## What comes from v1

> v2 is a rebuild (decision 0002). v1 is at `../EMA-v1`, tag `v1-final`, for reference only. List which v1
> modules are read, re-reviewed, and ported, and which are left behind. The table in
> `../notes/v1/lessons_learned_2026-09-27.md` §13 is a starting point. A port is named in a plan and in its
> commit message.

| v1 module (under `src/ema/` unless named) | Port, rewrite, or leave | Why |
|---|---|---|
| `core/models/_sandbox.py`, `_worker.py` | port, after re-review | isolation of model code, verified in v1 (534 lines); the trust spec (step 10) and OD-11 decide how it is used |
| `core/legendre.py` | port, after re-review | the Legendre basis (205 lines), for the linear and polynomial models |
| `testfunctions/library.py`, `truth.py` | port, after re-review | the reference models and their known answers (step 11) |
| `agent/approval.py` | rewrite, reading its rules and tests | v2's trust module keeps its rules (paths compared as files, credentials refused, approval covers what decides a run), but v1's is built around its own agent (0016) |
| `core/models/cli.py`, `python_fn.py` | rewrite, reading their edge cases | the three phases of a run (0015) and kept run directories (0020); v1's handling of paths, process groups, and stdin is the checklist |
| `core/models/parsers.py` | rewrite, reading it | only the kinds OD-20 chooses (step 4) |
| `core/provenance.py` | rewrite, reading it | provenance per diagnostic result, not per campaign (P5, 0006) |
| `diagnostics/_uncertainty.py` | rewrite, reading it | the interval method per diagnostic (OD-12, step 7) |
| `tests/diagnostic_contract.py` (repository root) | rewrite, reading it | v2's diagnostic contract (P4, P6; step 7) |
| `core/doe.py`, `core/store.py`, `core/report.py`, `cli.py` | rewrite from v2's specs | v2's designs (step 5), data model (step 8), reports (0018), and CLI (step 9) differ from v1's |
| `diagnostics/scatter.py`, `curve1d.py`, `repeat.py`, `linear_coeffs.py`, `fourier.py` | rewrite from v2's specs; run v1 as a source of numbers | scatter, coordinate lines, point run, linear model, and polynomial model (0012, step 6); v1 at the same seed checks v2's numbers |
| `core/scheduler.py` | leave | no executor interface in v2.0 (0015) |
| `core/models/expression.py` | leave | no formula models (0014) |
| `core/campaign.py`, `synthesis.py`, `advice.py`, `reuse.py`, findings | leave | no campaigns or interpretation (0006, 0017) |
| `core/surrogates.py`, `surrogate_build.py` | leave | no surrogates |
| the other diagnostics | leave | not in v2.0 (0012) |
| `agent/` (except approval's rules), grounding and split checks | leave | the agent is an MCP server whose tool results EMA renders (0016, 0019) |
| `evals/` (repository root) | leave | U9 is tested with a scripted MCP client; live evals wait for OD-19 |
