# Consistency review of the design documents, 2026-10-01

Ten independent reviewers each read the whole doc set (specs, records 0001–0042, TODO, STATUS, README,
CLAUDE.md, plans, guides, notes; v1's notes skimmed). Each went deepest on one area: terminology, ids and
references, records against specs, numbers, data model, architecture, contracts, redundancy, necessity, and
how an implementer would read the specs. Their findings were merged, the disputed ones checked by computation,
and plain errors corrected in place (uncommitted). Decisions are left to you.

## Overall

- **Numbers:** sound. Every mock report reproduces to its printed digits: scatter, linear model, polynomial
  model, coordinate lines, and lines. So do the undefined-resample table, the convergent sizes, the χ² bounds,
  and R10's and R11's values. The few numeric errors are listed below.
- **Ids:** sound. All 216 id definitions are unique, gap-free, and defined where README says. All 1,645 id
  citations resolve. The decisions index matches all 42 records.
- **Accepted specs:** they mostly agree. About a dozen real contradictions are left, and they need your
  decisions (Q1–Q10).
- **Drafts:** `architecture.md` and the `data_model.md` template predate almost every record and contradict
  them in dozens of places. Step 9 should rewrite `architecture.md` from the specs' asks, not patch it.
- **Readiness:** TODO steps 8–10 name only part of what the specs and records ask of them. The lists below
  collect the rest.

## Corrected in place (uncommitted, in the working tree)

Plain errors only: stale cross-references, numbers that contradict their own source, and wrong citations or
paths.

| File | Correction |
|---|---|
| `use_cases.md` | U1: one figure per model parameter, as scatter makes, not one figure with panels (two places). U2: the space is given with `--space FILE`, no longer "open" (two places). U3: the polynomial model needs 168 runs (2P), not 84 (two places). U3: `r4`'s price assumes none of `r3`'s 100 new runs failed. U7: "varies" is exact, as the point run's spec settled. "Loading asks nothing" no longer cites OD-11. The name budget is 20, not 15. |
| `scope.md` | Platform question settled for v2.0 (0029); v1 table cites 0026, 0027 (regex, json, csv), 0040 instead of open ODs |
| `glossary.md` | Removed "Terms marked OD-n wait on that decision" (none left); output parser (0003, 0027); experimental (P2; none in v2.0, 0017) |
| `principles.md` | Held "One-way layers" candidate: `ema.mcp` is in v2.0 (0016), not "later" |
| `model_interface.md` | M8: an exception, a timeout, or a wrong shape fails every run in the call, as its own prose says (C37 already did); the designs ask about zero-width ranges marked answered by 0033 |
| `contracts.md` | Seams citation: the basis comes from `polynomial_model.md`, not 0039. P3's tests include C33. C12: "a computed number", since Gram coefficients are observations. C15 cites G11 and scatter's and coordinate lines' Nested. C37: "batch call". C46: a retry of a failed run is allowed (0010), which C47 already requires. |
| `diagnostics/shared.md` | The bootstrap-range example names its stream: `default_rng(0)`, verified, not scatter's. The spawn-tag reasoning is corrected: `SeedSequence` stores 2³² + 1 as the words (1, 1), so tags are distinct only while design streams spawn no children. The path is `../designs.md`. |
| `diagnostics/scatter.md` | The constants row is named `SCATTER_HIST_BINS`, as the text cites it |
| `diagnostics/linear_model.md` | Subsampling rescale ((n₀/n₁)^(−2r) − 1)^(−1/2): with −r it gave 1.554, not the stated 1, at doubling levels; "meter" |
| `diagnostics/polynomial_model.md` | Matrix sizes at the defaults are 14161 × 1771 and 84,964 × 10,626 (exact convergent sizes, not 8P); the R3 r-total example matches the mock (4.3·10⁻⁵ [1.7·10⁻⁵, 2.2·10⁻⁴]) |
| `diagnostics/coordinate_lines.md` | Rounding passes the floor below about 10⁻⁶ of \|y\| (10⁻¹⁶/10⁻¹⁰), not 10⁻⁴ (two places; measured 2·10⁻⁷ at n = 17) |
| `designs.md` | 0.7072⁻² = 1.99947 (was 1.9994) |
| `architecture.md` (draft) | A banner lists what records supersede, and the import-linter `|` vs `:` (verified in its docs). §12: the nine rows settled by records are struck, with each record cited. |
| `data_model.md` (template) | Status "template"; banner listing what to strike before filling it in |
| `trust.md` (empty) | Depends on 0016, 0019, 0020, 0026, 0029, 0030; the second boundary is the MCP client, in v2.0 |
| guides | "box", "outputs", "scale" on a model parameter → the glossary's words (0024) |
| `notes/adding_a_use_case.md` | The next id is U10 |
| `diagnostics/_template.md` | "Constant model prediction" |
| `TODO.md` | Step 8 points to this report's "Step 8 inputs" and decides OD-15 before Q5. Step 9 points to "Step 9 inputs", and its §12 line is cut to the two items still open. Step 10 notes the three words for user code. Step 12: the principles are already in CLAUDE.md. |

Also corrected in place:

| File | Correction |
|---|---|
| `STATUS.md` | "Updated" is 2026-10-01; "Now" and "Next" point to this review; statuses add template and outline; OD-19 is "live evals of the MCP server (0016)", blocking setup (12) and the MCP build step; OD-12's record is "0040 (amended by 0041)"; only §12's open items join the table |
| `docs/decisions/0008-…md` and the index | "accepted; its generated-text list amended by 0042", as 0040 is marked for 0041 |
| `CLAUDE.md` | "(T<…>)" → "(M2 in `model_interface.md`; T2 in `trust.md`)" |

Checked and left as they are, because the records say so:

- **U4's interval example** ("convergence over the design's levels, OD-12"): 0040 says it "is an example only,
  and stays as history".
- **P2's "Enforced by"** (`ema.experimental`): 0017 says "P2 is unchanged… The parts of its enforcement that
  concern `ema.experimental` apply when the package is added."

Left for you (conventions, not errors):

- **Record citations:** CLAUDE.md and README say "D0007"; every doc and commit says "0007". Pick one.
- **"One branch per step (`step-NN-topic`)"** in CLAUDE.md: say "build step", and that plans number build steps
  from 01, apart from TODO's steps (your memory already says design steps commit on main).
- **Refinement marks:** 0015 (by 0025, 0029, 0030), 0020 (by 0028), 0023 and 0032 (by 0033), and 0034's
  glossary row (by 0042) carry no mark. `decisions/README.md` lists only "superseded by". Add "amended by NNNN
  (what)", and the in-place correction rule the project uses but no document states.
- **`docs/plans/_template.md`:** no "Ported from v1" or "Ids implemented" field, though CLAUDE.md and `scope.md`
  require both in a plan.

## Decisions needed (each would be a `proposed` record, for an interview)

**Q1. What a failed run is.** M4, C35, the glossary, and 0022 say a run fails "only when none is read". M12, C39,
and `model_interface.md`'s prose say a nonzero exit fails the run "even when the model predictions can be read".
Suggested: failed means the call errored, timed out, or exited nonzero, or no model prediction was read. M4 then
applies to runs that finished cleanly. This amends the glossary row and 0022's consequence.

**Q2. What a golden report is compared against.** Five specs require golden reports "byte-identical" to mocks
that cannot match them as written:
- placeholder hashes and 4-hex ids;
- `R2@8e41`, while model names must be lowercase;
- fixed library versions, and R3's log ranges are promised only on one machine;
- U+2212 minus signs (scatter 15, linear 29, lines 14), while S3's `format(x, ".4g")` writes ASCII "-";
- integers through `.4g` (20,000 → "2e+04"), and S3's parse test would read ids such as "7e22" as numbers.

Suggested: the golden file is EMA's output on the reference model, written at step 11 after review against the
mock, then compared byte for byte, with ids, hashes, and library versions masked. Counts, sizes, seeds, degrees,
and levels print in full. Pick ASCII "-" (and fix the mocks in place) or U+2212 (a rule).

**Q3. The contract model is degree 2 in unit coordinates.** f = 1 + u₁ + u₂² + 0.1(1 + u₁)u₃, and the d = 1 and
d = 20 variants are quadratic too. Verified: every coordinate line and every random line has k* ≤ 2, so no
decay rate is ever computed. C5's `UNITS_LOG_TOL`, C6's rate exemption, and LN and CL rate checks are vacuous.
The polynomial model at p ≥ 2 fits it exactly. The point run's replicates at one x are identical. z ("missing
where b > 0.5") is undefined at d = 1 and d = 20. Suggested:
- add a non-polynomial term, such as 0.2·sin(3b), with an analogue at d = 1 and d = 20;
- give the point run's fixture replicate values directly;
- define z at d = 1 and d = 20.

**Q4. A design's identity leaves out the model version** (`designs.md`, 0032). Held values at nominal,
coordinate lines' anchor, the point design's x, and column order all come from the model version. So two
versions can give different points under one design identity. Suggested: add the model version hash, or the
resolved held values and order.

**Q5. Unit-coordinate maps aren't pinned for bit-for-bit points** (G10, C21). Verified:
- the log map exp(log lo + (log hi − log lo)·u) exceeds hi at u = 1 − 2⁻⁵³ in 13% of ranges;
- exp(log b) ≠ b for 52%;
- the centered form ½(lo + hi) + ½(hi − lo)·z misses hi at z = 1 in 13%, while lo + (hi − lo)·u never did (2·10⁶
  ranges).

Suggested: state z = 2u − 1, the linear and log formulas, the clamp, and that a face end is set to lo or hi
exactly. Also state which end of a line is t = 0 (the lines mock reproduces only with "the end reached against
the direction"), and how alpha keeps its decimal through a Python float (`Fraction(repr(alpha))`).

**Q6. Tolerances that fail as written:**
- CL8, LN7, and C5 say rates are within 10⁻⁹ under y → a·y + b. Measured with Lanczos and full
  reorthogonalization: 10⁻¹¹ at n = 17, but 6.7·10⁻⁷ at n = 33 on R2 along x₁.
- CL3's fixture (rate 1 within 10⁻⁹) gives 1.1·10⁻⁸ or 7·10⁻¹⁰ depending on implementation details.
- PM9's "R11 at p = 10: 5 open markers" can't pass. The odd degrees' √E_k are 10⁻⁴ of the largest (Monte
  Carlo bias), not below 10⁻¹⁷.
- Lanczos gives no exact parity zeros either (3·10⁻¹⁸ to 4·10⁻¹⁷), and the polynomial model and coordinate
  lines use two different open-marker rules.
- SC7, LM7, and PM8 say "unchanged" under a shift, with no tolerance (C5 has one).

**Q7. Glossary batch** (rows the later specs outgrew):
- "approval" and "price" are defined for a diagnostic evaluation only, but `test_model`'s run and `save_model`'s
  consent sit outside one.
- "each design has exactly one" model parameter space, but the point design has none.
- "model version" and "model spec" claim "the contents of its files", while 0029 covers only the files the spec
  names, minus `keep`, `batch_size`, and `timeout_s`.
- An estimate whose value is "none" (`uncertainty.md`, the polynomial model's Sobol indices), while 0041 allows
  only the interval to be none.
- New rows: usable run, request, unit coordinates, call / batch call (contracts says "batch" for two things;
  scope uses "model call", which the glossary avoids), range (of a model prediction).
- "unit cube" means both [0, 1)^d and [−1, 1]^d.
- The data-card key `limits` (axis limits) collides with a model parameter's limits.
- "r" means a model parameter, the sampler's rate, a residual, and a rank in one R3 report.
- `Workspace.estimate`, `ema estimate`, and `CostEstimate` return a price, not an estimate.

**Q8. Scope gaps:**
- **OD-15:** are run budgets in v2.0 at all? U4 and the glossary use them, and STATUS says it blocks step 8.
- **Export:** it has no spec home (U5 says CSV and JSON; architecture says `.npz`), and scope's In table lacks
  export and reproduce.
- **Live evals:** in v2.0 or not (OD-19, 0016)?
- **Surrogates:** "no export of fitted surrogates", yet the polynomial coefficients are in the exported result.
- **`purpose.md`:** it promises a time estimate for the whole evaluation (the price covers runs only; the
  polynomial analysis can take 54 min at d = 20) and intervals "for all estimates" (0041 allows none).
- **Later list:** the samplers, the hyperellipsoid, chunked designs, other bases and interval methods, and
  resource limits are deferred in their specs but missing from scope's "Not in v2.0".
- **Budgets:**
  - The 8,000-line budget is about 7,975–8,045 on paper, before 0022, 0024, 0029, the Gram spectrum, the seams,
    the PDF route, and an approval module.
  - The workspace has 19 names counted, and 20–21 with a PDF function and `close()`, against a budget of 20.
    State the counting rule.
- **Use cases:** none exercises the lines diagnostic, the run-directory lookup, PDF output, `estimate`, `keep`,
  or a batch Python model in a "Done when".

**Q9. Smaller rule questions:**
- Which sections and figures appear when there are no estimates (S1). A note for "every run ok but missing this
  model prediction". A numerical rank rule (`RANK_RTOL`).
- P6 and S5's test say every diagnostic gives the constant note; the point run doesn't (PT6, C4).
- A no-nested-spawn rule, and C8 checking key words.
- CL7's header when the anchor is a line end. `designs.md`'s "shares no point with the others" is false then.
- S2's test on R5 can't hold a value and a nominal one (R5 has only a and b; scatter refuses nothing varied).
- The order of failure reasons in the note (the example lists 27, 3, 4; it may be grouped by kind).
- P7 says "a model measured as noisy"; the point run records noise per model prediction.
- P3 says "no other lookup"; 0020 looks runs up by run id.
- P4 says "EMA picks one" seed; `designs.md` says 0.
- C49 doesn't check that a stopped run isn't stored (`model_interface.md`).

**Q10. Editorial consolidation** (no behavior change; one editorial record covers the accepted specs; about
4,800 words saved):
- **Bootstrap:** defined in 5 places (`shared.md`, `uncertainty.md`, scatter, linear, polynomial), with its
  constants in two tables, each pointing to the other. Make `uncertainty.md` the one home.
- **Constants:** `KNOWN_ANSWER_N` is defined 3 times; define it once.
- **Contracts:** C20–C27 and C31–C45 restate G and M rows word for word, and have drifted (C37/M8; C33/M3).
  Write each as its id plus any difference.
- **Spec sections:**
  - "Tests it implies" repeats the contracts.
  - "What this spec asks" sections are mostly applied history; keep only the asks of steps 8–13.
  - 54 inline "(interview, 2026-09-30)" tags.
- **`STATUS.md`:** the Done entries (about 1,500 words) retell the records; use one line per step with the
  record ids. TODO's "Decided" lines repeat STATUS.
- **`notes/decision_workflow.md`:** merge into `decisions/README.md`, which it defers to.
- **`reference_models.md`:** make Expected answers an index into the diagnostic specs, not a copy.
- **`docs/notes/v1/`:**
  - 7 of 18 files are cited. 11 are uncited, including `pde_packages_onboarding.md` (133k of the 181k words),
    `openrouter_migration.md`, and `eval_paraphrases.md`, which concern v1's agent stack. Index them, or leave
    them to `../EMA-v1`.
  - `data_model_spec_template.md` duplicates `data_model.md`.

## Numbers to recheck at step 11 (expected answers)

- **R3 brute-force values** carry Monte Carlo noise in the last digit. Hu and Hl must have equal and opposite
  slopes (f depends on Hu − Hl, with equal ranges); the spec has 16.08 and −16.10. By quadrature: intercept
  77.757, relative residual 0.2304, degree-2 residual 0.0341.
- **R2's x₃ first-order "limit 0.0029"** (`polynomial_model.md`, Not chosen): the projection's limit is 0
  analytically. State what 0.0029 is.
- **Hyperbolic cross "65 terms at d = 8, p = 3":** no common definition gives 65. Π(αᵢ + 1) ≤ 4 gives 53.
- **`BOOTSTRAP_RESAMPLES` rationale:** "stable to about 0.01 of the interval". Each end's standard deviation
  measures 2.7–2.8% of the width.
- **Lines "within 0.005 for the long lines":** line 3 at n = 65 is 0.0056 off.
- **Coordinate lines' all-degrees rates:** 0.225 recomputes as 0.223.
- **"8P" at level 2:** exact only for P ≤ 237 (and "8(d + 1)" for d ≤ 235).
- **The Tu slope example "1.4·10⁻⁷ per m²/yr":** not reproduced (about 3.5–5.6·10⁻⁹).
- **Expected answers' source:** keep the "scratch script, 2026-09-30" computations in the repository, so step 11
  can rerun them.

## Step 8 inputs (data model)

- **Design identity:** includes the model version (Q4), and the sampler's name and version (0032).
- **Reusing a stored diagnostic result (C50):**
  - The reuse key: the canonical request, with the model version and the model prediction, but not `approve`
    or `retry_failed`; plus the ordered run ids the design resolves to now.
  - C50 conflicts with 0010's retry: after `r4`'s retry, does `r1` return its old result?
  - Is EMA's version, or a named constant, in the key?
- **Provenance enough to replay (C51, U8):** the measured-noisy records read, and the evaluation's own approval
  as distinct from the approvals of reused runs. The mocks disagree here: coordinate lines lists the reused
  runs' approvals, while the point run and polynomial model list only their own.
- **Model name → location, current version, and settings across processes:**
  - W1 "writes nothing" for a repeated version, but 0029 says "settings stored, the latest loading's values
    apply";
  - what two directories with the same name do.
- **Which run is current at a key:** after a retry (0010), against the template's I4 and append-only I1.
  Options: a `replaces_run_id` column, or latest wins.
- **Approvals:** what an approval is attached to (a request, or the test run); single use; whether declines are
  stored (T3); whether its points are stored as a list or as the design plus a count.
- **Canonical encodings and hashes:** the model version, the point key (`float.hex` turns −0.0 into a second
  key; verified), the request (defaults filled in, keys sorted), ids (full stored, display length; 4-hex ids
  collide at about 300), and data-card JSON. Strict JSON round-trips every double, −0.0 and subnormals included
  (verified).
- **Columns:** the one-line reason apart from the stderr tail (the note groups by it); the exit code or signal;
  the batch directory's path and keep rule (0025); the Python model's "program path"; whether a failed run has
  prediction rows.
- **Scale:** the 10⁷-point cap means no `IN (…)` list. Measured on 10⁶ stored runs: chunked `IN` of 30,000 took
  2.9 s, and a join on a temporary table 8.4 s. Hashing points: 1 s per 10⁶ × 20 as raw bytes, 9 s through
  `float.hex` (about 10 s and 90 s at the cap).
- **Commits:** one per call. Measured: 0.26 ms per run with WAL and `synchronous=FULL`. A directory is written
  before its row, so an orphan directory is ignored.
- **The price's time estimate:** which stored durations count (ok only? timeouts? per host? mean or median?).
- **Asks the TODO line missed:**
  - each model prediction's status and reason (0022);
  - a run's batch (0025);
  - settings stored with the model (0029);
  - the `files/` store (0030);
  - the measured-noisy record (`point_run.md`, U7);
  - a repeated request (`shared.md`);
  - "none" stored as null with its reason, and spawn tags (C17, 0041);
  - run ids in data cards (0037);
  - no `campaigns` table, and stable result ids (0006);
  - the `designs.space` column, nullable for the point design;
  - where reports, PNGs, and data cards live.

## Step 9 inputs (architecture)

- **Rewrite §3–§9 from the specs.** Renames:
  - `Box` → the space, `--box` → `--space`;
  - `qoi` → `prediction`;
  - `DiagnosticRun` → `DiagnosticResult` / `DiagnosticEvaluation`;
  - `OutputSpec` → `PredictionSpec`;
  - `estimate`/`CostEstimate` → price (Q7);
  - `cached` → reused.

  Drop:
  - `Constraint` and `scale` on `ModelParameter`;
  - `parallel` and `typical_run_time_s`;
  - `TIMEOUT` and `INVALID_INPUT`;
  - `Estimate.level` and `convergence_interval`;
  - k-fold cross-validation (the fits use PRESS);
  - `fourier.py`, `random_lines.py`, and `plane.py`;
  - `point(box, …)`;
  - sizes as n_min·alpha^k (the accepted formula is ⌈n_min·alpha^(−l/r)⌉).
- **§11 import contracts:**
  - `|` forbids sibling imports, so diagnostics → plotting needs `:` or its own layer;
  - P1's "no LLM SDK" contract is missing;
  - layer 0's `ModelSpec.load` and `save` do file I/O, against the held "no I/O in layers 0–1".
- **Interfaces the specs name:** the sampler (name, version, `unit_rows`, nested, balanced sizes, rate), the
  basis, the interval method, and the output parsers. Each diagnostic declares `example_request(d)`, its
  minimum, its unit transforms, its spawn tags, whether it has estimates, its strips, "Changes the design?", and
  its nesting (C3–C15). Also the analysis progress hook (PM10) and P6's one tolerance function.
- **The diagnostic entry point must take** the run batch with replicate numbers and new/reused flags, the
  measured-noisy records, and the interval method and tags through a registry (C8, C16, C19 need them without
  monkeypatching).
- **An approval module (P3: "from day 1").** `run` returns a stored result (C50), records the approval (T3),
  writes provenance in one transaction (C51), and refuses changed files (U6). `test_model(approve=)`. Where
  `ema.ask` lives.
- **MCP:**
  - 0016's list is 12 tools as written; one 10-tool set: `models(name?)`, `diagnostics(name?)`,
    `propose_model`, `save_model`, `test_model`, `price`, `run_diagnostic`, `results(id?)`, `get_figure`,
    `failed_runs`, with the report as a resource.
  - What happens without the elicitation capability (suggested: refuse new runs).
  - `next_step` restricted to procedural hints (0017).
  - `params` as a JSON object described by `diagnostics(name)` (C55).
- **The model spec's field table:** type, required, default, whether it is in the model version, and whether
  unknown keys are refused.
- **Re-estimate the source lines per module** against 8,000; set the workspace name-counting rule; decide
  whether reference models ship with `ema`.

## Step 10 inputs (trust)

- **One word** for the code EMA isolates: the specs say user code, model code, and model programs.
- **Environment:**
  - an allowlist for the child's environment (the exposure is EMA's own process environment, as the
    environment an MCP client passes; EMA never loads `.env`);
  - the child runs on `sys.executable`;
  - whether credential-like `env` values in a spec are refused.
- **Paths:**
  - no `..` or absolute paths in `files` and the parser's `file`;
  - MCP path arguments confined to a directory named at `ema mcp` start;
  - the write path shown in `save_model`'s elicitation.
- **Rows to drop or replace:**
  - drop "saving a file that becomes code" (0016: the agent writes no code EMA runs);
  - replace "saving a command-line model" with `save_model` and the first run of a model version (U1, U2);
  - no "limits" (0026).
- **T1 and T2:** cite P3, C33, M2, and C32 instead of restating them.

## Experiments run

| Check | Result |
|---|---|
| Scatter mock bootstrap range on its own stream | [2.71, 4.33] at 1000; the doc's [2.72, 4.45] and [2.31, 4.71] are `default_rng(0)` (now named) |
| Polynomial convergent sizes at d = 20, exact rational alpha | 3542, 7083, 14161 (P = 1771); 21252, 42493, 84964 (P = 10626) |
| Map endpoints, 2·10⁶ random ranges | lo + (hi − lo)·1 = hi always; centered form misses 13%; log map overshoots 13%; exp(log b) ≠ b 52% |
| Strict JSON round trip, 10⁵ doubles over 10^±300, subnormals, −0.0 | all equal; `float.hex(−0.0)` ≠ `float.hex(0.0)` |
| SHA-256 of points, 10⁶ × 20 | 1 s raw bytes; 9 s through `float.hex` |
| SeedSequence keys | (2³² + 1,) = (1, 1) = child 1 of key (1,): scatter's tag stream equals a child of random line 1's stream |
| SQLite, 10⁶ runs, pricing 10⁶ points | chunked `IN` 2.9 s; temp-table join 8.4 s; insert 13.7 s |
| Coordinate-line rates under 2⁻¹⁰y + 3 (R2, x₁) | 1.0·10⁻¹¹ at n = 17, 6.7·10⁻⁷ at n = 33 |
| import-linter layers | `|` = independent siblings (may not import each other), `:` = may (docs, layers.md) |
| Reviewers, independently | All 5 mock reports to every printed digit; the undefined-resample table; χ² bounds; convergent sizes; R10 and R11; U2/U4/U5 prices |

Not run (they need code or installs):
- the fast tier's 30 s budget. A reviewer's estimate is about 40 s unvectorized; it fits only with vectorized
  bootstraps, and the first plan should say so;
- C5's bit-exactness for PRESS and Sobol;
- a scrubbed-environment import test;
- the MCP elicitation fallback.

The reviewers' and my scripts were in this job's scratch directory, which is deleted with the job; the
numbers above are their results.
