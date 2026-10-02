# Build roadmap (draft, 2026-10-01)

> A draft order for the build steps after plan 01, so each plan can be written knowing what comes before and
> after it. It is a note, not a spec or a plan: each step still gets its own plan in `docs/plans/`, written
> after the step before it is reviewed and merged (`docs/plans/README.md`), and that plan may move, split, or
> merge steps here. Nothing in this note decides anything a spec or record decides.

## How the order was chosen

- **From the bottom of the layers up** (`docs/design/architecture.md` §1, AR1): each step's packages import only
  what earlier steps built, so each is tested without the layers above it.
- **Each step keeps whole contracts** (`docs/design/contracts.md`): a step that builds an interface writes its
  contract checks, toy, and broken toys first (CLAUDE.md's "Tests first").
- **A contract is listed where its checks can first run;** one that needs later layers (C34, C37, C41, C46,
  C47, C49, C50, C51, C52, C56, and some S tests) is listed again where it is finished.
- **Unknowns early:** BLAS determinism (`STATUS.md`, Next) is measured at the start of `ema.numerics`, before
  any fit depends on it; the sandbox port, v1's largest, gets a step of its own.
- **Types arrive with their first user:** each module of `ema.types` is written in the step whose code and tests
  first use it (plan 01, question 2).
- **Reference answers as soon as there is something to check:** each diagnostic's step meets its spec's
  expected answers on the reference models, and writes its golden report; the workspace step then reruns them
  end to end.
- **Size:** each step's lines come from `architecture.md` §11; the rows add to about 8,300, against `scope.md`'s
  8,300. `ema.types` will probably end about 640 lines over §11's 860 (plan 01, Notes and question 6), which puts
  the total near 8,840, so a record raising the budget, or trimming elsewhere, is expected.

## The steps

| Step | Topic | Packages and modules | Specs and ids | Contracts | v1 (`../EMA-v1`, `v1-final`) | Source lines (about) |
|---|---|---|---|---|---|---|
| 01 | scaffolding and designs | the scaffolding (0059); `ema.types`: errors, text, streams, identity (in part), model (dataclasses), space, design; `ema.designs` | G1–G18, §3.4, 0059 | C20–C28 | none | 890 |
| 02 | numerics | `ema.numerics`: basis, gram, fitting, sobol, stats, intervals, tolerance | V1–V7, the diagnostic specs' numerics, P6's tolerance | C29, C30 | port `core/legendre.py` after re-review; read `diagnostics/_uncertainty.py` | 550 |
| 03 | model specs and loading | `ModelSpec.from_json`, `to_json`, `versioned_json`; `version_hash`; `ema.models.spec` (but `resolve_program`), `files` | M3, M10 (template names), M16's hash check, M17, M18, M21; T1, T7 (but the question text), T8; T2's spec checks (`pass_env` beside `env`, an `env` `PATH`'s entries) | C33 | read `agent/approval.py`'s `is_secret` and its tests (rewrite the lists) | 450 |
| 04 | running a command-line model | `types/runs.py`'s `RunStatus`, `FailureKind`, `Run`, `RunKey`; `ema.models`: prepare, execute (a command), collect, parsers, `remove_tree`, `resolve_program`; `sandbox.py`'s environment (`BASE_ENV`, `model_environment`); `processes.py`'s `ModelProcesses` type | M1, M2, M4, M5, M10–M16, M19, M20; T2, T9; §10's AST check on `ema/models/__init__.py` | C31, C32, C34–C36, C39–C45 | read `core/models/cli.py`, `parsers.py` | 640 |
| 05 | the Python model's child | `ema.models.sandbox`'s child, `_worker`, `processes`; a Python function and a batch | M7, M8, M9, 0025, 0026 | C37, C38; C31–C45 again for Python | port `core/models/_sandbox.py`, `_worker.py` after re-review; read `python_fn.py` | 520 |
| 06 | the store | `types/runs.py`'s `RunColumns`; `requests.py`'s `Request`, `TestRunRequest`; `results.py` (with `to_json`, `from_json`); `approval_id`, `reuse_key`; `ema.store` | Q1–Q15, W1–W6, I1–I12, §11 migrations | the store's parts of C46, C50–C52, C56; C17's round trip of a result | read `core/provenance.py` (`core/store.py` is rewritten from v2's specs) | 820 |
| 07 | runner and approval | `ema.runner`, `ema.approval`; `types/runs.py`'s `Resolution`, `RunBatch`, `Price`; `ApprovalRequest`, `ConfirmationRequest`, `Approver`, `Progress` | P3; T3, T4 (asking), T7's question text; 0010, 0015 | C46, C56; the runner's parts of C47–C49; C34, C37, C41 finished (`run_new` checks the files, sizes calls to what remains approved, and applies `keep`) | read `agent/approval.py` (its rules, rewritten) | 440 |
| 08 | figures and reports | `ema.plotting`, `ema.report` (`render`, `EXPLAIN_INTERVALS`, `to_pdf`) | S1–S4, S9, S10; T10; 0018, 0042, 0044 | (C11, C12 run in step 09) | none (`core/report.py` is rewritten from v2's specs) | 540 |
| 09 | diagnostics, their contract, the point run, and the reference models | `ema.diagnostics.base` (the precheck, `evaluate`), the diagnostic contract's toy and broken toys; `point_run.py`; `ema/reference_models/` (R1–R11 but R9, which is later) | S1–S7, PT1–PT9, `reference_models.md`, P6, P7 | C1–C19; C47's note; C52 | port `testfunctions/library.py`, `truth.py` after re-review; read `tests/diagnostic_contract.py`; run v1 for numbers | 500 (and about 400 of the reference models' own 1,000: ten models, each a spec and a function, R8 a program) |
| 10 | scatter | `scatter.py` | SC1–SC10; S8, and S2's and S9's tests (scatter on R5) finished; S1, S4–S7, and S10 grow with each diagnostic, complete at 13 | C1–C19 over it | run v1 for numbers | 250 |
| 11 | coordinate lines and lines | `_lines.py`, `coordinate_lines.py`, `lines.py`; R8 through `ema.runner` | CL1–CL10, LN1–LN9, 0038, 0048 | C1–C19 over them | run v1 for numbers | 550 |
| 12 | linear model | `linear_model.py` | LM1–LM10, 0040 | C1–C19 over it | run v1 for numbers | 300 |
| 13 | polynomial model | `polynomial_model.py` | PM1–PM12, 0039, 0041 | C1–C19 over it; C18 at d = 20 (slow) | run v1 for numbers | 400 |
| 14 | the workspace | `ema.workspace` (`_evaluate`, `_reproduce`, `_export`); `types/summaries.py`; the root's re-exports; `ema.ask` | U1–U8, E1–E7, Q11; T5's root check in `open_workspace(root=)` (0061 item 12); T6; 0054, 0055, 0062, 0063 | C53 (U1–U8, the get-started guide); C47, C49, C50, C51 end to end | none | 745 |
| 15 | the MCP server | `ema.mcp` (`server.py`, `tools.md`); the `mcp` extra, and `ema[mcp]` in the `dev` group (0059 item 3) | U9, 0016, 0019, 0053, 0056; T4, T5; AR3's contract, over `ema.mcp` | C55; C53's U9 | none (0016) | 410 |
| 16 | the CLI | `ema.cli`, the `ema` console script, `ema mcp` importing `ema.mcp` lazily; `ema.cli` added to AR3's contract | `architecture.md` §8; exit codes; T5's exit 2 | C54; §10's AST check on `ema mcp`'s import | none (`cli.py` is rewritten from v2's specs) | 300 |
| 17 | guides and release | the guides' full text; README; the wheel's contents; budgets audited | `docs/guides/`, `scope.md` | C53's guide checks | none | 0 |

The diagnostics' line estimates (steps 09–13) add to about 2,000 of `architecture.md` §11's 2,004, split by the
spec sizes ("base and precheck ~300; the six, 150–400 each").

## What each step watches for

- **01:** see its plan. After it is merged and pushed, the owner starts `checks.yml` once, to measure its time
  (0059: 30–35 min estimated).
- **02, first task:** measure `qr`, `lstsq`, the Lanczos process, and `Q.T @ y` at the polynomial model's size
  on this Mac (50 calls, in one process and across processes), as `STATUS.md`'s Next says; stop there, and
  propose a record if any varies (single-threaded BLAS through `threadpoolctl` would be a new dependency; the
  exact Gram basis would contradict `coordinate_lines.md`). The bootstrap's `IntervalMethod` and the basis
  registry use `unregister` (0065).
- **03:** the model spec's checks are `ema.types.model`'s (layer 0, no files); the checks that need files are
  `load_spec`'s (`trust.md`, Where the rules live).
- **04 and 05:** the model adapter contract's toys are millisecond models in `tests/models/`. The sandbox port
  is re-reviewed against `trust.md` before it is copied, and the port named in the commit message.
- **06:** the store's schema is not shipped before v2.0, so changes to it are cheapest here (0063). `RunColumns`
  reads in chunks of 30,000 rows.
- **07:** the cap counted when a call starts (C48), and Ctrl-C between and during calls (C49), with the
  millisecond models.
- **08:** lualatex's fonts from matplotlib's files, and its pitfalls (0059 item 8); the PDF tests are slow and
  skip on `PandocMissing`.
- **09:** the contract model (`contracts.md`) is a fixture, not a reference model. Until step 14, the known
  answers build run batches from a reference model's function on the generator's design, as the contract does;
  R8, a program, runs through `ema.runner` in step 11. Ruff and mypy exclude `src/ema/reference_models/`
  (the consistency review's D). Every diagnostic step writes its golden report (0044) with `ema.report`.
- **11:** C5's and C6's rate tolerances (`UNITS_LOG_TOL`, `RATE_SHIFT_TOL`) and the shared anchor's rows.
- **12:** the per-level table's coefficients and their units (the consistency review's D, DIAG-10d).
- **13:** the known-answer tests take about 9 min serially (`polynomial_model.md`): the slow tier's 10 min
  target (with `-n auto`) is checked here, and a plan that misses it proposes a fix or a new target
  (`contracts.md`, Test tiers).
- **14:** the 19 public names against `scope.md`'s 20; U8's replay across a generator version (C51, a test
  generator registered at two versions); `reproduce`'s rebuild check per range (0063).
- **15:** 10 tools of 10; the `mcp` extra's lower bound at its first release with elicitation; U9 with a
  scripted client; no live evals (`scope.md`).
- **16:** 13 commands of 15; `ema mcp` imports `ema.mcp` lazily (AR3, 0061), checked by the AST test; the CLI
  comes after the MCP server, since that command needs it.
- **17:** each guide walked through on an installed EMA; `scope.md`'s budgets reported; the first plan for
  anything after v2.0 starts from `scope.md`'s "Not in v2.0".

## In every step

- The import contracts grow with the packages (0059 item 4), and the terminology test with the public names and
  generated text (0008).
- The Sphinx API reference grows with the modules, built with `-W`.
- The plan reports its package's lines against §11, and the tiers' times against their budget (fast, 30 s) and
  target (slow, 10 min).
- `STATUS.md` is updated in the step's commit.
