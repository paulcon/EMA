# EMA: lessons learned, for a fresh start

2026-09-27, main at 22253f3. Written to help decide whether and how to rebuild EMA. It draws on the git history, the code, CLAUDE.md, the memory notes, the 2026-09-23 review, the code atlas, the reliability framework report, the OpenRouter cost addendum, `docs/guides/agent_evals.md`, and the notes in this folder (`ema-redesign.md`, `ema-notes.md`, and the daily brainstorms). Numbers were measured today unless a source is named.

## 1. Summary

The core ideas were right, and most of them should carry over:
- the core computes with no LLM;
- runs belong to a model version and are cached;
- designs are deterministic;
- budgets are checked before anything runs;
- the harness, not the model, computes every number;
- one contract suite checks every diagnostic.

What went wrong is scope and speed, not the foundation:
- **Too much was built too fast to review.** In seven days: 75 commits, about 82,000 inserted lines, 12 diagnostics, 26 agent tools, 12 CLI commands, 31 eval scenarios, and 84,000 words of docs (brainstorms excluded). Five large efforts overlapped. The owner's own review items from 2026-09-22 (the numerics, the diagnostic descriptions, the uncertainty estimates) are still open, while features went on landing above them.
- **Interpretation drove most of the complexity.** Flags, advice, synthesis, findings, and surrogates, plus the checks that police the agent's prose, make up about 5,500 of 28,000 source lines. They also caused most eval failures and most of the reliability work. Making them "experimental" at the end took six phases and touched every layer, including the database schema.
- **Rules accreted where a simpler design was needed.** CLAUDE.md has grown to 7,400 words, with 36 design rules. Many of those rules record a bug fix: "compute from the inputs the model actually read", "a gap of failed runs creates false jumps", "model directories never stay on `sys.path`". Each one is a correct rule, but together they are a specification nobody wrote on purpose.
- **Checking free-text prose is a losing game.** The grounding check and the split check parse the agent's replies after the fact. Every fix to them needed a new exemption: hedges, proposals, "10^-16", rewrites that add numbers. Structured output, where the harness renders every number, would remove that whole category.

The recommendation, in one line: rebuild a small core by hand to your own spec (the tables in `ema-redesign.md`), and port proven pieces from v1 only after reading them. Add the agent last, with the narrow job your note gives it: set up a model, run a diagnostic, measure cost.

## 2. What was built, in numbers

| Measure | Value |
|---|---|
| Time span | 2026-09-21 to 2026-09-27 (7 days) |
| Commits | 75 (2, 13, 24, 15, 8, 6, 7 per day) |
| Churn | +81,875 / −9,054 lines |
| `src/ema` | 27,969 lines of Python: core 11,854 (models 2,611), diagnostics 7,892, agent 5,771, test functions 1,411, `cli.py` 1,032 |
| `evals/` (code) | 5,807 lines; results on disk 3.0 GB |
| `tests/` | 13,029 lines, about 1,700 tests (3 min on 8 CPUs, 10 min serially) |
| Docs | 67 Markdown files; 84k words without brainstorms, 276k with them |
| CLAUDE.md | 7,367 words, 36 design rules |
| Largest files | `store.py` 1,412, `diagnostics/base.py` 1,253, `surrogate_build.py` 1,207, `campaign.py` 1,047, `cli.py` 1,032 |
| Agent surface | 26 tools, a 1,600-word system prompt, about 10,500 tokens of prompt and tools per session |
| Database | 7 tables, schema version 3 after 6 days, 12 `ALTER TABLE` migrations |
| Live API spend | about $244 (section 10) |

The efforts that overlapped:
- the feature plan (P0–P4);
- the 2026-09-23 review (11 work packages in four waves);
- the reliability framework (R1–R6);
- the code-atlas refactor (5 steps);
- the experimental split (6 phases).

Each came with its own plan file, branch scheme, memory note, and report. The memory notes now carry state that exists nowhere else, such as which snapshot baseline goes with which phase.

## 3. How control was lost

Looking back, five patterns stand out.

1. **Features came from brainstorm lists faster than their design settled.** The 2026-09-22 note lists 21 features. Within three days most of them existed: surrogates, synthesis, advice, log scale, `active_subspace`, reuse, profiling, traces, and the benchmark. Each was reasonable, but none had the one-page spec that `ema-redesign.md` now asks for (*User provides / Design / Compute / Plots / Report*).
2. **The central distinction was decided last.** "Is this a result or an interpretation?" shaped the database (`interpretation_text`, `campaigns.experimental`), the diagnostic contract (`factual_flags`, `without_interpretation`, `Presentation.interpretation`), the report layout, every tool's result shape (`derived` against `experimental`), two system prompts, a new harness check, and new eval scenarios. Deciding it on day 1 would have cost a paragraph. Deciding it on day 6 cost six phases and two live gates.
3. **The campaign became the unit, not the diagnostic.** Budgets, justification, synthesis, reuse, next steps, findings, and reports all hang off the campaign. Your note, "do just one diagnostic with report at a time", describes a simpler model that covers the essentials.
4. **Bug fixes became rules, and rules became checks.** That is good discipline in itself. But once the rules number 36, adding a diagnostic means satisfying about 15 contract checks, and the checklist in CLAUDE.md runs to a dozen steps. The rules are the right lessons (section 12), and v2 should design them in from the start, not bolt them on.
5. **Review lagged generation.** The code is clean line by line: the atlas measured 0.2% duplication and no import cycles. The loss of control is conceptual. There are more concepts (campaign, diagnostic, design, flag, factual flag, interpretation, finding, next step, synthesis, disagreement, reuse, surrogate, approval, provenance, grounding, split) than one person can hold while also checking the numerics.

## 4. Testing components

**What worked**
- **The contract suite** (`tests/diagnostic_contract.py`) is the project's best asset, and the review said so too. Every diagnostic gets these checks automatically:
  - cost, and partial and clustered failures;
  - no claims when every run fails;
  - strict JSON and determinism;
  - units invariance at 1e±12;
  - speed at d = 20;
  - constant output;
  - nested designs.
  Most of the numerical bugs the review found sat in gaps in its coverage, not in the pattern.
- **Known answers and independent checks:**
  - analytic Ishigami and Sobol-G indices;
  - exact recovery of polynomials;
  - bootstrap coverage checked over 100 seeds.
- **Test functions with computed ground truth** (`truth.json`), and a benchmark scored against a committed baseline.
- **Offline replay of the chat loop** (`agent/replay.py`): a real `ChatSession` and SDK, driven by scripted replies with no API call.
- **Snapshot comparisons for refactors** (`tools/snapshot/`): 26 campaigns before and after a change, compared field by field. This made the five refactor steps safe.
- **Docs tested against real runs:** walkthrough numbers are re-checked, and the terminology test enforces the glossary.

**What went wrong**
- **The gates themselves passed vacuously**, and nothing tested them:
  - the benchmark comparison ignored flags that disappeared (L8);
  - eval checks accepted any "0" (A6);
  - grounding counted its own revise note as a source (A3).
- **Degenerate inputs were an afterthought.** A constant output, a gap of failed runs, noise on a finer grid, and a zero bootstrap each produced false claims (G1, L1, L2, G4). Each was patched diagnostic by diagnostic before shared helpers existed.
- **The suite grew with the rules** to about 1,700 tests and 10 minutes serially. Many tests pin wording and shapes (docs text, card keys), so an intended change breaks dozens of them.
- **Results are not bit-reproducible:** about 1e-15 relative noise appears even with single-threaded BLAS, so snapshot comparisons need tolerances learned from repeated runs.

**For v2**
- Define a contract for **every component interface**, not only diagnostics:
  - model adapters: failures come back as NaN, a timeout is honoured, the environment is scrubbed;
  - the store: round trips, the cache key, migrations;
  - designs: determinism, bounds, nesting.
- Generate degenerate cases from day one with **property-based tests** (Hypothesis): constant, NaN runs, NaN gaps, units scaling, noise, d = 1 and d = 20.
- **Test the gates.** Any check that decides pass or fail gets a mutation test: remove an item or insert a fabricated number, and expect a failure.
- Use an **independent oracle** for each estimator: SALib, brute-force quadrature, or finer sampling in a test-only dependency.
- Keep **two tiers:** a fast tier under 30 s for every edit, and a slow tier (end-to-end, walkthroughs, wheel build) run before merging.
- Use **golden reports:** store a report and its data for a few reference campaigns, and review a diff when it changes. This replaces many small shape-pinning tests.

## 5. Database structure

**What worked**
- **The run cache:** runs belong to a model version, keyed by `(model_id, input_hash, replicate)`. Failed runs are never reused, and overlapping designs cost nothing. This is the feature that makes exploration cheap. Keep it.
- **Approvals and provenance in the database.** Write-ahead logging with an NFS fallback. Migrations that old workspaces survive.

**What went wrong**
- **The schema changed three times in six days.** Twelve columns arrived by `ALTER TABLE`: budgets, provenance, owner PID, heartbeat, replicate, `diag_id`, `experimental`, and `interpretation_text`.
- **One scalar output is built in:** `runs.output REAL`. Multi-QoI (P5) and spatiotemporal outputs would need another migration and changes to every diagnostic.
- **Designs are not first-class.** A diagnostic stores `design_json` without its points, and reaches them only through `diagnostic_runs`. So "which diagnostics can the stored runs compute?" (`reuse.py`) re-hashes every point against the whole cache. Your redesign note already gives designs a table.
- **Much lives in JSON blobs:** `spec_json`, `inputs_json`, `result_json`, `params_json`. None of it can be queried, and each consumer parses it its own way.
- **State is split between the database and files:**
  - `report.md`, `events.jsonl`, `reuse.json`, and `synthesis/`;
  - figures and their data cards;
  - session traces and run directories.
  Keeping them consistent took explicit code: reaping writes its own event, and the report is marked out of date.
- **The version hash encodes policy.** It excludes each input's `scale` and `base_dir`, so changing a scale rewrites the stored spec for every campaign of that version (a known limitation).
- **Performance was an afterthought:** one commit per run spent 2.8 s of a 4.4 s diagnostic (C4).

**For v2**
- Tables close to your note:
  - `models` (spec and version);
  - `designs` (type, box, scales, parameters, and **its points**, by reference);
  - `runs` (model version, inputs, status, timing);
  - `outputs` (`run_id`, `qoi`, and a value or an array reference), so multiple outputs exist from day 1;
  - `diagnostics` (design, parameters, values and intervals, figure references);
  - `reports`.
- **The input box and scales belong to the design, not the model.** The model version then covers only what changes the model's behaviour, and the scale problem disappears.
- **The database is the single source of truth.** Every file (report, figures, exports) is derived and can be regenerated.
- **Store arrays as arrays** (`.npz` or Parquet with a content hash), and keep JSON for small metadata.
- **Batch commits from the start,** and design for one writer with many readers.
- Settle the schema through a written spec and one review before the first run is stored. A migration is cheap to write, but it holds the design in place.

## 6. User interface

**What exists**
- 12 CLI commands with many flags.
- Campaign JSON files.
- `ema chat`, the terminal agent.
- `report.md` with figures, and a JSON data card for each figure.
- A Python library, documented in the scripting guide.
- No web front end (P6.1 was planned as a read-only local server).

**What went wrong**
- **Getting started is hard.** Your own 2026-09-24 note asks: "How does it get started? What is a campaign file? Where is my workspace? Where are these help strings stored?" The docs are extensive (84k words) but grew around features, not around the path a new analyst takes.
- **The interface was designed around the agent.** The richest path is `ema chat`. The plain path (Python or CLI) inherited the campaign machinery without being designed as the main product.
- **The report tries to do everything:**
  - results, *Across diagnostics*, and *Available from stored runs*;
  - approvals and provenance;
  - an experimental section of interpretation and next steps.
  Your note "drop interpretation and focus on plots" points to a leaner report.
- **Tutorials quote verbatim agent transcripts** (recorded with Opus while the default is now Haiku). Each agent change makes them stale, and re-recording costs money.

**For v2**
- **Figures are the product.** For each diagnostic, design the figure and the one-screen report first, then derive the data it needs. The *Plots* and *Report* rows of your tables do exactly this.
- **Layer the interfaces:**
  1. a Python API that works in a notebook (`ema.run(model, "scatter", n=200)` returns a result with `.values`, `.intervals`, `.figures`, and `.report()`);
  2. a thin CLI over it;
  3. the agent over the same API.
  Each layer adds convenience, never capability.
- **Write your four guides before the code** (get started, link a model, run a diagnostic, define a diagnostic), and let them decide the API. If a guide is hard to write, the API is wrong.
- If a browser view comes later, make it read-only over the database: a list of models, diagnostics, and figures.

## 7. Agent reliability

**What worked**
- **The harness computes, so the model doesn't have to.** Estimates carry:
  - `if_run`, `share_of_budget`, and priced `cheaper_options`;
  - `check_at_nominal` for formula models;
  - the noise `repeat` measured, applied automatically.
  Grounding failures from arithmetic fell sharply after these (the 2026-09-23 matrix).
- **Rules enforced in code change behaviour; advice sentences don't.** This is the reliability report's strongest finding. Examples of enforced rules:
  - the per-turn approval limit;
  - the force rule for surrogates;
  - `record_findings` refusing confident claims the evidence contradicts;
  - the budget refusal.
- **Revise mode lets a cheap model match expensive ones:** Haiku 4.5 passed 39/39 repeats at $0.78 a run, against $4.50–6 for Opus 5.
- **Safety measured by explicit constraints, not an LLM judge:** no high-severity breach in about 1,550 paid repeats, plus 1,614 rescored offline.
- **A gate with statistics:** a paired bootstrap on the pass rate, R_prompt ≥ 0.9, and zero breaches. It caught a real regression (the first post-split gate) and cleared a false alarm: a control run showed the calibration drop was variation between sessions.

**What went wrong**
- **The grounding check is a parser of free prose.** Each fix opened a new hole:
  - hedges ("e.g.") and proposals ("a cap of 900 runs");
  - trailing zeros and "0.56 percent";
  - the revise note laundering numbers;
  - "10^-16";
  - rewrites introducing new numbers (17 of the 19 unsupported numbers in the failed gate).
  It now has two rewrite rounds and a fallback to the draft.
- **The split check** (interpretive words only after an "Experimental" line) sends back about half of all replies. In interpreting sessions it sends back all of them, and a third of the rewrites still misplace the words. There, it costs more than it fixes.
- **Interpretation is the least reliable output:**
  - confident wrong findings went 5 → 10 between references;
  - stated confidence barely discriminates (AUROC 0.64 [0.49, 0.84]);
  - R_prompt on the truth-scored scenarios was 0.74, against about 0.95 for conduct.
- **Variation between sessions is large.** Detecting a change needs K = 5 repeats of 31 scenarios, plus paraphrases, at about $15–20 per change.

**For v2**
- **Give the agent jobs whose correctness is structural:**
  - set up a model: was the spec approved, and does it load and run at nominal?
  - run a diagnostic: was it priced, approved, and within budget?
  - report cost.
  Each of these passes or fails on a tool call and its approval, not on prose.
- **Let the harness render every number.** Have the agent write replies with references (`{diag:3f2a.values.S_T.x1}` or `{est:…if_run}`) that the harness fills from the database, and refuse a digit in the model's own text outside quoted settings. That removes grounding and its rewrites entirely. (An alternative with the same effect: structured replies, a JSON schema of `{result_refs, text}`.)
- **If interpretation returns, keep it out of chat.** Produce it as a separate, clearly labelled document, generated on request from stored results, and scored against test functions with known truth. It then needs no word-level policing inside conversation.
- **Carry over the gate's method**, not its size. Start with about 10 scenarios, the safety constraints, and the paired comparison, and grow only as incidents demand.

## 8. The API for LLMs (the tool surface)

**What exists**
- 26 `@beta_tool` functions whose docstrings are the tool descriptions.
- A 1,600-word system prompt in two variants.
- About 10,500 tokens of fixed prefix per session.
- Result conventions arrived late (the atlas's step 5):
  - `derived` against `experimental`;
  - `next_step`, `declined(...)`, and `budget_refusal`;
  - `RETRY_ONCE` / `RETRY_WONT_HELP` on every error.
- Any docstring edit is a prompt change, and needs the $15–20 gate.

**What went wrong**
- **Too many tools, shaped like the core's functions,** not like the analyst's tasks: `list_directory`, `read_file`, `write_model_file`, `get_model_spec`, `save_model_spec`, `import_model`, `create_python_model`, and more.
- **Result shapes differed by tool** until a dedicated refactor. The agent had to learn each shape separately.
- **Coupled to Anthropic throughout:**
  - `beta_tool` and `tool_runner`;
  - the fallbacks beta and the thinking tables;
  - cassettes recorded as Anthropic SSE;
  - traces with Anthropic usage keys;
  - the withheld environment variable names.
  The OpenRouter plan found this manageable through Anthropic's own endpoint, but a different provider's native API would touch replay, traces, and grounding.
- **Caching was set up late.** Cache writes were 65% of all spend until a system-prompt breakpoint was added on 2026-09-27. That cut the cost per repeat from $0.047 to $0.036 (as written) and from $0.029 to $0.017 (paraphrased).

**For v2**
- **Design fewer, coarser tools** around tasks: `describe_model`, `propose_model` (which returns a spec for approval), `estimate`, `run_diagnostic`, `get_result`, `get_figure`. Aim for fewer than 10.
- **One result envelope for every tool:** `{ok, data, next_step, error: {message, retryable}}`, typed with pydantic and turned into JSON Schema once. Snapshot the schemas in a test; v1 did this by hand at each refactor.
- **Keep tools as plain functions in the core API,** with a thin adapter per provider. Tool descriptions live in one reviewed file. Their token count is a budget, checked by a test.
- **Consider shipping EMA as an MCP server.** Claude Code, Claude Desktop, or any MCP client could then drive EMA with no chat loop to maintain. You would lose revise mode's control over replies, but if the harness renders numbers (section 7) that matters less. Keep your own loop only if the evals show you need it.
- **Cache from day one:** a breakpoint after the tools and system prompt, measured in the first eval run.

## 9. Dependencies

**Now**
- **Runtime:** numpy, scipy, joblib, matplotlib, scikit-learn, and anthropic, **all unpinned** (the review flagged it). scikit-learn is used only for two surrogates (OMP and GP), imported lazily.
- **Extras:**
  - apps: swmm-toolkit, flopy, and cantera, plus the MODFLOW binary, which needs flags on an Intel Mac;
  - docs: Sphinx, myst, furo, and mermaid;
  - dev: pytest, xdist, ruff, and setuptools, for the offline wheel build.
- **Python 3.14 locally, and 3.11 in CI.**

**Built by hand where libraries exist**
- designs (`scipy.stats.qmc` has Sobol, Halton, Latin hypercube, and discrepancy measures);
- the Sobol and Morris estimators (SALib);
- the Legendre basis (partly in `numpy.polynomial.legendre`);
- the isolation protocol (a JSON-lines worker);
- a scheduler with an `Executor` interface for remote runs that never came;
- a number parser for grounding.

Owning these gave control, and exact deterministic sharing between designs, which the cache relies on. But each needed its own verification, and several of the review's bugs lived there (the stencil at a bound, the sandbox after Ctrl-C).

**For v2**
- **Decide per component whether to own it or borrow it.** Borrow designs and standard estimators, and use them as test oracles even where you own the code. Own the parts that are EMA: the cache, the model adapters, the report.
- **Keep the core installable without the LLM SDK** (an `ema[agent]` extra) and without scikit-learn.
- **Pin lower bounds and keep a lockfile** (uv), so an SDK change can't silently alter the agent's behaviour between gate runs.
- **Keep the real applications out of the core repository's test path** (marked `external` today). Do the same in v2 from the start.

## 10. Cost

**API spend on EMA's own agent:** about **$244** in total.
- $185.05 over 16,564 requests up to 2026-09-27 01:48 UTC, priced from traces in the OpenRouter addendum:
  - the model and effort comparison, $85 (46%);
  - reliability evals and gates, $80;
  - early harness evals on Opus, $19.
- $58.63 more in results files on 2026-09-27: the exp5 and exp6 gates, the split-fix and truth runs, and the passing gate.
- Not counted:
  - Claude Code's own usage in building EMA, which is billed separately and was not measured here;
  - the first day's Opus sessions for the tutorials, guessed at $5–20.

**Where it went**
- Nearly half was one comparison of models. Opus 5 alone was 44% of the traced spend.
- **Cache writes were 65%** until the breakpoint fix, because every eval repeat is a new session that writes the whole prefix again.
- **The recurring cost is the gate:** $15–20 per change to the prompt, a tool description, or a harness rule on Haiku (about $9 with the staged K = 2 paraphrases used today).
- **Time is a cost too:**
  - eval runs take 15–40 minutes;
  - the test suite takes 3–10 minutes;
  - reading and classifying every failure before trusting a gate, which the method requires, took hours per gate.

**For v2**
- A smaller surface (fewer tools, a shorter prompt, harness-rendered numbers) means fewer tokens per request, fewer scenarios, and fewer failure classes to read.
- Compare models once, early, with a small suite. Use OpenRouter's cheaper candidates only after they pass the gate, since their quality is unmeasured.
- Budget the agent's development explicitly. For example: "the gate may run at most once per week, and at most $X per month."
- Model runs cost money too. Keep budgets checked before anything runs, which v1 got right.

## 11. Workflows

**Development workflow (you with Claude Code)**
- **What worked:**
  - plans before code;
  - a branch per phase, with a review gate;
  - parallel worktrees, each with its own venv (needed because isolated children don't see `PYTHONPATH`);
  - "commit only when asked";
  - classifying every eval failure before acting on it;
  - replaying offline before paying for a run.
- **What went wrong:**
  - Five efforts ran in parallel on stacked branches for days.
  - Status lived in memory notes and plan files outside the repo.
  - Reports went to the gitignored brainstorms folder, so the history of decisions is partly lost to git.
  - Three branch schemes coexisted (stacked, one branch per phase from main, and worktrees cherry-picked into one line).
  - Claude generated faster than you could review the numerics.
  - CLAUDE.md became the architecture document by accretion. Each new rule made the next session more careful and the codebase harder to change.

**The analysis workflow (what EMA does)**
- **v1:** model → campaign (budget, justification) → diagnostics → synthesis, reuse, and advice → report with an experimental section → findings.
- **Your redesign:** choose a model → choose a diagnostic and its design parameters → run the design → compute values and intervals → report.
- The second is the essential core. Everything else is optional, and can be layered on once the core is trusted.

**For v2**
- **One effort at a time,** and an owner's review gate before the next feature starts, especially for the numerics. A feature isn't done until you have read its spec and its figure.
- **Size budgets as explicit constraints,** for example: core under 5,000 lines, fewer than 10 tools, CLAUDE.md under 1,500 words, 5 diagnostics at first. Breaking one is a decision, not a drift.
- **Keep CLAUDE.md for principles and commands.** Put rules in code and tests, and in a design document you write yourself. Your note says "Claude Code does well with structured design principles": give it a few, and not 36.
- **Commit decision records to the repository** (`docs/decisions/NNN-title.md`, one page each), so the history survives outside memory notes.
- **Spec each diagnostic in your table format first,** then have Claude implement it against that spec and the contract suite.

## 12. Other lessons

- **Numerics need an owner.** Twelve diagnostics, each with heuristic thresholds (named constants and documented, but still heuristics), were more than one person could verify in a week. Start with the diagnostics you would use yourself: scatter, coordinate lines, a linear model, and a polynomial model (your note's list). Verify each against analytic answers before adding the next.
- **"No data, no claims" and units invariance were the right invariants.** Put them into the diagnostic base class at the start (a shared `precheck`, a flatness test relative to the output's range, intervals required for any "negligible"), not into each diagnostic after a bug.
- **Intervals by default was the right call.** Keep it, and give each diagnostic one uncertainty method chosen by you (bootstrap, refinement, cross-validation, or held-out error; your note lists them).
- **The trust boundary deserves to be a module from day 1.** Before `approval.py` existed, the approval logic lived inside an 850-line closure, which led to the one critical bug (A1: `MODEL.JSON` on a case-insensitive filesystem). Rules to keep:
  - one mechanism runs every piece of user code: isolated, scrubbed environment, timeout, stdin from `/dev/null`;
  - paths are compared as files (`samefile`, casefold), never as strings;
  - credentials files are refused;
  - approval covers everything that decides what a run does.
- **The model interface is the first thing to get right.** Your 2026-09-23 questions are still the right ones:
  - What does a model take?
  - What does it produce?
  - Which parameters are fixed rather than design inputs?
  - Can it evaluate many points at once (your "parallel flag")?
  - Can it explain a failure?

  v1's three kinds (Python function, command line with a deck template, and formula) plus isolation are a good menu. Its spec grew many options (`number_format`, `data_files`, `static_files`, `env`, `python_path`, output parsers of five kinds), which the version hash then had to cover one by one.
- **Terminology pays off.** The glossary, with a test that enforces it, kept 84k words of docs consistent. Start v2 with the glossary, in your nomenclature ("variation intervals"), connected to the standard terms.
- **Determinism and provenance** (seeded designs, a shared seed stream, a recorded environment) made the cache, snapshots, and gate comparisons possible. Keep them.
- **Docs that quote the agent verbatim go stale with every agent change.** Prefer docs driven by the Python API or CLI, whose output is deterministic and can be regenerated by a script.

## 13. What to carry over from v1

Each piece should be read and re-reviewed before porting, not copied wholesale.

| Keep, largely as is | Keep the idea, rebuild smaller | Leave behind (or re-add later as optional) |
|---|---|---|
| Run cache keyed by model version, input hash, and replicate | The contract suite, extended to every interface | Campaign-level synthesis, disagreements, and reuse listing |
| `_sandbox.py` / `_worker.py` isolation (after re-review) | The store, with designs and outputs as tables | Advice rules and next steps |
| The `approval.py` rules and their tests | Model spec and adapters (fewer options) | Findings and their confidence rules |
| `legendre.py`, and the test functions with `truth.py` | The report: figures first, one screen per diagnostic | The split check, and the grounding checker's prose parsing |
| Deterministic designs and shared seed streams | The eval gate: about 10 scenarios, the safety constraints, a paired comparison | Surrogate building (until the core is trusted) |
| The glossary and its test | Tool results in one envelope | Verbatim-transcript tutorials |
| Replay for offline agent tests | Profiling and the budget check before any run | 26 fine-grained tools |

## 14. A possible order for v2

Each step ends with your review. Nothing goes to the next step until the current one is read and accepted.

1. **Write it down, by hand:**
   - principles (up to 10);
   - glossary;
   - model interface;
   - the database tables;
   - the table spec for the first 3–4 diagnostics;
   - the four guides as outlines.

   Stop condition: you can explain every table and column.
2. **Core, no LLM:**
   - model adapters (Python function and command line), with isolation;
   - designs (uniform, line, and grid; borrow from `scipy.stats.qmc` where possible);
   - scheduler and cache;
   - store.

   Contract tests and property tests throughout. Stop condition: the fast tier runs in under 30 s.
3. **Diagnostics, one at a time:**
   - scatter, then coordinate lines, then the linear model, then the polynomial model;
   - each with its figure, its report, and a known-answer test against an independent oracle.

   You review the numbers and the figure before the next one starts.
4. **Python API, then the CLI,** driven by the "Get started" and "Run a diagnostic" guides.
5. **The agent,** with the three uses in your note:
   - a few coarse tools, harness-rendered numbers, and caching;
   - about 10 scenarios with safety constraints;
   - a model comparison done once.

   Consider MCP first.
6. **Only then, optional layers:** interpretation (as a separate, labelled document scored against truth), more diagnostics, surrogates, multiple outputs, and remote runs. Each one gets its own spec and review gate.

## 15. Questions to settle before starting

- **Rebuild or refactor?** v1's core is sound and tested, and the atlas showed it can be restructured safely with snapshots. Another option is to *delete* the experimental layers from v1 (about 5,500 source lines, plus most of the evals), make designs and outputs tables, and cut the tools to 10. That gets much of the benefit at lower risk. A rebuild buys a design you own completely, at the cost of re-verifying what already works.
- **Campaign or single diagnostic** as the unit? Budgets and approvals can attach to either.
- **Your own chat loop, or MCP** behind an existing client?
- **Multiple outputs:** designed in now, even if implemented later?
- **Which 3–4 diagnostics** make the first release, and which uncertainty method each one uses?
- **How much money and time per month** goes to agent evals?
