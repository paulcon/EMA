# Contracts and degenerate cases

**Status:** accepted; C46–C56 provisional until the data model (step 8), architecture (step 9), and guides
(step 13). **Updated:** 2026-10-01. **Depends on:** P1–P7; `scope.md`; `model_interface.md` (M1–M21),
`designs.md` (G1–G17), `diagnostics/shared.md` (S1–S10) and the six diagnostic specs, `uncertainty.md`
(V1–V7); records 0008, 0010, 0011, 0015–0019, 0022, 0025–0030, 0032–0043, 0045–0048, 0051, 0052.

> The promises each interface makes, written so each becomes one `check_*` function run over every
> implementation (`../notes/v1/lessons_learned_answers_2026-09-27.md` §4). This file is the test plan: Claude
> writes the checks from it before writing the code they check. Written from an interview on 2026-09-30 (TODO
> step 7).

## What a contract is here

- **A contract** is a list of promises every implementation of one interface keeps, each checked by one
  `check_*` function in `tests/contracts/<interface>.py` (`architecture.md` §10): `diagnostic.py`,
  `design.py`, `sampler.py`, `basis.py`, `interval.py`, `model.py`, `store.py`, `workspace.py`, and
  `tools.py`, each run over every registered implementation with `pytest.mark.parametrize`.
- **This file holds** the promises that hold for every implementation, each with an id C1…, the spec
  requirements it generalizes, its check, and its negative control. **A spec holds** what one implementation
  promises (scatter's known answers, a generator's sizes, a golden report); those are that spec's own tests,
  and are not repeated here.
- **A run batch** is the runs a diagnostic receives, in the design's order (C56); not a batch model's call
  (0025), which this file calls a batch call.
- **How every implementation is reached:** a registry per interface; an example request per implementation
  (`example_request(d)`: small, valid diagnostic parameters for d varied model parameters), so a check can
  build any implementation without knowing which it is.
- **Checked against the other specs** (2026-09-30, after acceptance and before the commit): corrections listed
  in `STATUS.md`'s step-7 entry.
- **Negative controls** (v1's `test_diagnostic_contract.py`): each contract has a toy implementation, kept in
  the tests and not registered, that keeps every promise; and, for each check, a broken toy that differs from
  it in one way and must fail that check. A meta-test requires every check to have a broken toy, so no check
  can pass vacuously.
- **Settled in the interview** (2026-09-30): shared promises only; diagnostics checked on run batches built
  directly; the declarations on each diagnostic; a negative control for every check of every contract; the contract
  model and the degenerate cases as listed; C5 exact under powers of 2; C6 kept; C1–C4 and C9–C10 as drafted; the
  run order moved from C7 to the store (C56); C8 checks diagnostics with no tag; C11–C19 as drafted, with C13's
  replicate keys and C14's diagnostic parameters left unused in a mode; C20–C45 as drafted, with C21's and C27's
  wording fixed; C46–C56 provisional, as drafted; the test tiers below.
- **Through the public interface only:** a check calls what a user of the interface calls; it doesn't read an
  implementation's internals.

## The contract model

The diagnostic contract runs on **run batches built directly** in the tests, with no model runs: each run
record's status, failure kind, reason, and model predictions are set by the fixture. The values come from a
fixture function (tests only; not a reference model):

- **d = 3** (the default): a ∈ [0, 2] linear, b ∈ [−1, 1] linear, c ∈ [10⁻², 10²] log, each with its nominal
  value at its range's center (1, 0, and 1), and h held at its nominal value; f = a + b² + 0.05·a·log₁₀ c (a
  trend, curvature, and a small interaction, unequal ranges, as v1's), and the model prediction y = f; a
  second model prediction z = f + 1, missing wherever b > 0.5. The degenerate cases below build other model
  predictions from f.
- **d = 1:** a only, f = a + a². **d = 20:** x₁ … x₂₀ ∈ [−1, 1], nominal 0, f = x₁ + x₂² + 0.1·x₃·x₄.
- **z at d = 1 and d = 20:** z = f + 1, missing wherever the first model parameter is in its top quarter
  (a > 1.5 at d = 1; x₁ > 0.5 at d = 20) (0045).
- **The point run's batch:** replicate r at the point is f(x)·(1 + r·2⁻³⁰), distinct as doubles, so the model
  prediction varies; in the constant case, every replicate equals the case's value (0045).
- **Failures** are a mask over the design's rows, with a kind per run (error, timeout, unread) and a reason.
  The point run's masks are by replicate number: every 7th; a contiguous block of replicates; the last 30%
  (0045).

On it, coordinate lines and lines compute no rate (k* ≤ 2); rates and fit quality are tested by CL3, CL8, LN7,
and the polynomial model's known answers (0045).

The model adapter contract runs real models: a Python function, the same function as a batch, and a
command-line program, each a few lines in `tests/models/`, taking milliseconds per run.

## Degenerate cases

The cases the contracts run against.

| Case | Applies to | Generated by |
|---|---|---|
| every run failed, of each kind | diagnostics | the contract model, every row masked |
| one usable run; the minimum − 1; the minimum | diagnostics | the contract model, masked down to k usable runs, k from the diagnostic's declared minimum |
| failures at random (every 7th run); in one contiguous block of a's range (the middle quarter); at one end (a in the top 30%) | diagnostics | masks over the contract model |
| one model prediction missing, another read (0022) | diagnostics, models | z on the contract model; a command-line model with two output parsers |
| z missing in every run, every run ok: no usable run (0051) | diagnostics | z on the contract model, missing in every row |
| constant: every usable run the same double (0035) | diagnostics | y = 7 |
| constant to rounding: 7·(1 + 10⁻¹⁵·f), distinct as doubles (0035; R4b's reference model is the same case at about 4·10⁻¹³) | diagnostics | the contract model's f |
| large offset, small variation: 10⁶ + 10⁻³·f | diagnostics | the contract model's f |
| change of units: y → a·y with a = 2⁻⁴⁰ and 2⁴⁰ (about 10∓¹²); y → y + b with b = 3·max\|y\| | diagnostics | the contract model; powers of 2 keep distinct values distinct, and the shift loses about 2 bits, small enough not to merge the contract model's values (0035) |
| d = 1; d = 20 (the polynomial model at p = 10 and p = 2) | designs, diagnostics | the contract model's variants |
| a nominal value or an anchor at a range's end (coordinate lines: refused, naming the model parameter, 0051) | designs | the contract model, with a's nominal moved to 0 |
| a log range over many decades (10⁻⁶ to 10⁶) | designs, diagnostics | the contract model with c's range widened |
| repeated points in one design (coordinate lines' shared anchor, G12) | designs, store | coordinate lines at n odd, anchored at the nominal point (the centers) |
| measured noisy in this model prediction (P7) | diagnostics | the model version's record, set by the fixture |
| timeout; crash (exception, nonzero exit, `os._exit`, a signal); unreadable model output; a missing output file; reads stdin; Ctrl-C during a run; writes to a shared file; reads a variable set in `.env` | models | `tests/models/` |
| runs finishing in another order | store | the same batch, shuffled |
| interrupted between runs, and during the analysis | store, workspace | an exception raised from the progress callback |

## Diagnostic contract

`tests/contracts/diagnostic.py`, over every registered diagnostic and the toy.

| Id | Promise | Generalizes | Check | Negative control |
|---|---|---|---|---|
| C1 | With every run failed: the counts by kind and the note; no estimates and no observations; the report has the sections its spec gives it (C11). | P6, S1, PT8, 0034 | `check_all_failed` | reports the minimum and maximum of no runs as NaN observations |
| C2 | With failures at random, in a block, or at one end, or with this model prediction missing on runs where another is read: the counts by kind equal the batch's; the note, with at most 5 reasons verbatim (S7); and no estimate or observation computed from the usable runs changes when a run that isn't usable changes (its kind, reason, or other model predictions); an observation that reports a run's kind (the point run's replicate rows, `point_run.md`) shows the new kind. | P6, S7, SC9, 0022 | `check_partial_failures` | fills failed runs' y with 0; uses an `ok` run missing this model prediction |
| C3 | The diagnostic declares its minimum number of usable runs, as a function of d and its diagnostic parameters; one below it: counts, the note naming it, no estimates, and the observations that need fewer runs; at it: estimates (or, with no estimates in its spec, its observations). Where the minimum is 1 (the point run, coordinate lines, lines), one below is C1's case, with C1's note. | P6, S6, 0034 | `check_minimum` | makes estimates one run below its declared minimum |
| C4 | A model prediction the same double in every usable run: the constant note, the shared observations, no estimates (the point run: no note, PT6); constant to rounding (10⁻¹⁵ relative): no constant note, and estimates (or, with no estimates in its spec, its observations). | P6, S5, 0035, PT6 | `check_constant` | calls a range below 10⁻¹⁰ of max\|y\| constant |
| C5 | y → a·y (a = 2⁻⁴⁰, 2⁴⁰) and y → y + b: the notes, counts, and usable runs unchanged; each estimate and observation transforms as the diagnostic declares it (unchanged; times a; a·v + b; or unchanged under a·y only, as the shared relative spread, (max − min)/max\|y\|, which a shift changes). The notes are the same notes, their values in y's units transformed as declared. Under a·y, exactly, bit for bit, except a number declared as computed through a logarithm (coordinate lines' and lines' rates), within `UNITS_LOG_TOL` = 10⁻¹²; under y + b, within `UNITS_RTOL` = 10⁻⁹, relative to a·(the range of y) for a number in y's units, and absolute for a dimensionless one, except a number computed through a logarithm, within `RATE_SHIFT_TOL` = 10⁻⁵ with k* unchanged (`coordinate_lines.md`, 0048). The contract model gives no rates, so the clauses for a number computed through a logarithm apply in CL8's and LN7's tests (0045). | P6, 0035, 0045, 0048, SC7, CL8, LN7, LM7, PM8; `point_run.md` (Tests it implies) | `check_units` | a constant test with an absolute tolerance (range < 10⁻⁸) |
| C6 | 10⁶ + 10⁻³·f: no constant note, and each estimate and observation equals f's, transformed as declared, within `OFFSET_RTOL` = 10⁻⁶, relative to the range of y over the usable runs for a number in y's units (P6), and absolute for a dimensionless one; except the observations that a cutoff at a fraction of a line's range decides (coordinate lines' and lines' k* and rates), which rounding limits here, and the relative spread (C5). The contract model gives no rates; rates are tested by CL3, CL8, and LN7 (0045). | P6, 0045 | `check_large_offset` | the variance as mean(y²) − mean(y)² |
| C7 | The same request and batch give an identical diagnostic result (every double bit for bit, intervals included), and byte-identical data cards and report. The batch is in the design's order (C56). | P4, S10 | `check_deterministic` | seeds its draws from the clock |
| C8 | A diagnostic with its own draws declares its spawn tags, one per diagnostic and estimator stream (`shared.md`), each ≥ 2³² and unique among the registered diagnostics, and records them in its diagnostic result (0041); changing one changes the intervals and not the design. A diagnostic that declares none gives the same numbers for two requests that differ only in the seed, on the same batch. No registered stream's spawn key, as 32-bit words, equals another's or a design stream's (0051). | S8, V1, P4, 0051 | `check_spawn_tag` | draws from `default_rng(seed + 1)`; declares no tag, and draws from the seed |
| C9 | Every degenerate case gives a diagnostic result with an estimate, an observation, or a note; a diagnostic whose spec promises estimates gives estimates or a note. | 0036, P6 | `check_never_empty` | returns no note and no observation for a constant model prediction |
| C10 | With one or more usable runs, the shared observations (minimum, maximum, relative spread), labeled with what they are of ("of the n usable runs"; the point run's "of the 5 runs at the point"). | `shared.md` (Observations), 0034 | `check_shared_observations` | leaves out the relative spread |
| C11 | The report: S1's sections in order, empty Notes left out, and the Estimates section left out by a diagnostic whose spec has none (the point run, PT2; coordinate lines and lines); the header's rows (S2; the point run's Point row in place of Space and Held); every number as S3 says (`format(x, ".4g")` of its stored double, an ASCII minus, integers in full; 0044); one line under each estimates table naming its method and settings, and the Estimates section opening with `EXPLAIN_INTERVALS`, the report's only "confidence interval" (S4, 0042); a "none" interval cell with its reason (V6). | S1–S4, V6, PT2 | `check_report` | numbers to 6 digits; an estimates table with no line under it; "Not confidence intervals." under each table |
| C12 | Every figure has a PNG and a data card; every point drawn from a run has its run id (a point drawn from a computed number, such as a slope or a Gram coefficient, has none); every axis is labeled `name [units]`, or `name` when dimensionless; no panel for a held model parameter. In every panel with a strip (along a model parameter, `shared.md`; the replicate, `point_run.md`; the distance along a line, `lines.md`; w·u and ŷ, the linear and polynomial models), each run of that panel's runs that isn't usable appears once, with its kind (a run shared by lines appears in each line's panel); where the panel's runs are all the runs, the strip's count equals the header's. | S9, 0018 | `check_figures` | leaves failed runs out of the strip |
| C13 | The design's size, computed from the request before building, equals its rows; its distinct (point, replicate) keys are the runs the price counts (0011). | P3, G3 | `check_price` | a size off by one |
| C14 | Changing a diagnostic parameter whose spec says "Changes the design? no" leaves the design bit for bit; changing one marked "yes" changes it, or is refused, or leaves it bit for bit where its spec says so (lines' `seed` with given lines; the polynomial model's `degree` with `n_min` given). | the specs' diagnostic parameter tables | `check_design_parameters` | `prediction` moves the design |
| C15 | Each nesting the diagnostic's spec claims holds: the smaller request's points are points of the larger, bit for bit, so its runs are reused. | G4, G11, LN8, LM9, PM11; `scatter.md` and `coordinate_lines.md` (Nested); `point_run.md` (Parameters, replicates) | `check_nesting` | reseeds when n changes |
| C16 | With the model version measured noisy in this model prediction, the result carries the note, with the standard deviation as a fraction of this result's range; with another model prediction measured, no note. | P7, PT4, PT5 | `check_noisy_note` | builds its notes without the precheck's |
| C17 | The diagnostic result is strict JSON (no NaN or infinity) and loads back equal, every double exact; an interval that is "none" is stored as null, with its reason (0041). | P5, 0041; data model (step 8) | `check_round_trip` | stores a NaN estimate |
| C18 | d = 1 and d = 20 give a diagnostic result; in the slow tier, within `D20_SECONDS` (below). | v1's `check_fast_at_d20` | `check_dimensions` | assumes d ≥ 2 |
| C19 | A diagnostic with intervals takes them from the interval-method interface: a fake method replaces the bootstrap, and its name is in the result and the line under each table. | V7, 0040 | `check_interval_seam` | calls the bootstrap directly |

**Declared by each diagnostic,** for the checks: its example request; its minimum (C3); each estimate's and
observation's change under y → a·y + b, and whether it is computed through a logarithm (C5); its spawn tags
(C8); whether its spec promises estimates (C9); whether its report has an Estimates section, and its own header
rows (C11); which panels have strips, and over which runs (C12); each diagnostic parameter's "Changes the
design?" value, with a second value to change it to (C14); and its nesting claims (C15). Each comes from the
diagnostic's spec, and its known-answer tests check the declaration against the spec's text.

**Not checked:** a failure map of pairs of model parameters, which no v2.0 diagnostic draws (0037).

## Design generator contract

`tests/contracts/design.py`, over every registered design generator and the toy.

| Id | Promise | Generalizes | Check | Negative control |
|---|---|---|---|---|
| C20 | G1, with another seed only where the generator takes one; and the same request for two model versions that differ in a nominal value gives two designs, with different points where a model parameter is held at its nominal value (0046). | G1, P4, 0046 | `check_deterministic` | draws from numpy's global generator |
| C21 | Every point is inside the space's closed ranges and every limit; held values are exact; where the generator puts a point on a face (lines), it is exactly the range's end, log ranges included. | G2, G10, 0047 | `check_inside` | maps a log range by exp(ln lo + (ln hi − ln lo)·u) without the clamp or the exact end, which puts a point outside the closed range (0047) |
| C22 | G3. | G3 | `check_size` | a size off by one |
| C23 | G4. | G4, G7, G11, G13 | `check_nesting` | reseeds when n changes |
| C24 | G5, and no array is allocated before the refusal. | G5 | `check_too_large` | allocates, then checks |
| C25 | G6. | G6 | `check_blocks` | reseeds each block |
| C26 | G16. | G16 | `check_column_order` | columns in the space's order |
| C27 | G15, for a generator that takes a space; and the space is refused before building, naming, for a limit, the limit (M6). | G15, M6 | `check_bad_space` | builds before validating |

## Sampler, basis, and interval-method contracts

The seams kept for later implementations (0032; `diagnostics/polynomial_model.md`, the basis; 0040), each with
its v2.0 implementation and a fake registered in the tests.

| Id | Interface | Promise | Generalizes | Check | Negative control |
|---|---|---|---|---|---|
| C28 | sampler | Rows in [0, 1)^d, the same for the same seed; rows [start, stop) made alone equal those rows of the whole; it declares its name and version (hashed with the request: changing either changes the design's identity), its rate r, whether it is nested, and its balanced sizes; a nested sampler's n rows are the first n of any larger request. | G17, `designs.md` (the sampler interface), 0032, 0033 | `check_sampler` | declares nested, and isn't; a version left out of the hash |
| C29 | basis | P terms in the stated order, the constant first, orthonormal under the uniform measure on [−1, 1]^d (Gauss–Legendre Gram matrix within 10⁻¹³ of I); its name is part of the request's identity. | PM1, PM2 | `check_basis` | unnormalized Legendre terms |
| C30 | interval method | What any method promises (`uncertainty.md`, the interface): the same runs, estimators, and stream give the same intervals, bit for bit, and another stream gives other intervals (V1); an estimator marked "distinct runs" receives each index set's distinct runs, once each, in the design's order (V3); undefined values are dropped and counted (V4); each estimate gets an interval or "none" with its reason, and the method's name and settings. The bootstrap's own rules (V2, V5, V6) are its tests in `uncertainty.md`. | V1, V3, V4 | `check_interval_method` | four broken toys: ignores the stream it is given, and draws from a fixed seed; passes duplicates to a "distinct runs" estimator; keeps NaN values; gives "none" with no reason |

## Model adapter contract

`tests/contracts/model.py`, over a Python function, a batch Python function, and a command-line model, each
where the promise applies.

| Id | Promise | Generalizes | Applies to | Check | Negative control |
|---|---|---|---|---|---|
| C31 | M1. | M1 | all | `check_failure_is_a_record` | re-raises the model's exception |
| C32 | M2. | M2, 0026 | all | `check_no_stdin_no_secrets` | passes the parent's environment |
| C33 | M3, and files are compared as files. | M3, P3, 0029 | all | `check_model_version` | hashes the files' paths |
| C34 | M16, and the runs already made are kept. | M16, U6 | all | `check_rehash` | hashes once, at loading |
| C35 | M4 (a run that finished cleanly is failed only when none is read, kind `unread`; 0043), and a non-finite value is missing (M7, M11). | M4, M7, M11, 0043 | all | `check_predictions_read_or_missing` | fails the run when any model prediction is missing |
| C36 | M5. | M5 | all | `check_complete_points` | passes the varied model parameters only |
| C37 | M8. | M8, 0025, `model_interface.md` (Batch) | batch | `check_batch` | fills the last batch past the approved count |
| C38 | M9. | M9, 0026 | Python, batch | `check_isolation` | runs the function in process |
| C39 | A command runs without a shell, in its own process group, killed whole by a timeout or Ctrl-C; a nonzero exit fails the run even when the model predictions can be read. | M12, M20 | command line | `check_process` | `shell=True` |
| C40 | M13. | M13, 0028 | all | `check_collect_from_files` | returns the function's values in memory |
| C41 | M14. | M14, 0028 | all | `check_keep` | keeps a stopped run's directory |
| C42 | M15. | M15, 0030 | all | `check_shared_files` | copies the file into each run directory |
| C43 | M10. | M10 | command line | `check_templates` | writes values with `%g` |
| C44 | M19. | M19, 0029 | all | `check_run_record` | records the command as typed |
| C45 | M11, and a parser doesn't follow a link out of the run directory. | M11, 0027, 0030 | regex, json, csv | `check_parser` | parses `inf` as a value |

M6 is C27; M17 (the unlisted-import warning) and M18 (`noisy: true` refused) are about loading one model spec,
and stay `model_interface.md`'s own tests.

## Store contract

`tests/contracts/store.py`. Provisional: the data model (step 8) writes its invariants I1…, and each promise
here then cites them. C56 was added in the interview, after C55; ids are not renumbered.

| Id | Promise | Generalizes | Check | Negative control |
|---|---|---|---|---|
| C46 | Runs are keyed by model version, point, and replicate; a stored run is reused; a deterministic model gets no second run at a stored point, except the point run's replicates and a retry of a failed run (0010). | P3, P7, 0010, 0011 | `check_reuse` | keys points by their values printed to 6 significant digits |
| C47 | A failed run is reused unless retry is asked; the price counts the reused failed runs ("200 reused, of which 34 failed"), and the report's note says how many and that `retry_failed` runs them again; with retry asked, exactly the design's failed points run again, each stored beside the failed run it replaces. | 0010, U3 | `check_failed_reused` | retries failed runs without being asked |
| C48 | No more new runs than approved, counted when a run starts; with k of n points stored, the price says n − k new, and n − k runs are made; with no stored durations for the model version, the price's time is "unknown"; two designs in different model parameter spaces reuse the runs at their shared points. | P3, 0015, M8 | `check_approval_cap` | counts runs when they finish |
| C49 | An interrupted diagnostic evaluation keeps every finished run and stores no diagnostic result, and stores no record of a run stopped partway (`model_interface.md`, 0028, 0051); a rerun makes no new run for the finished runs, and gives the same result. | 0015, 0028, 0051, PM10 | `check_interrupt` | one transaction per diagnostic evaluation; stores the stopped run as failed |
| C50 | A repeated request returns the stored diagnostic result, with no new computation, no new run, and no approval asked, and a byte-identical report. | `shared.md` (The report) | `check_repeat` | recomputes |
| C51 | No diagnostic result without its provenance, the runs it used, and their approvals, written in one transaction; deleting a result and rerunning from its provenance gives an identical result; changing the seed, or the model version, and rerunning gives provenance records that differ in that field and in what it decides (the runs used and their approvals, when the design or the model version changes), and in nothing else. | P5 | `check_provenance` | writes the result before its provenance |
| C52 | A model version measured noisy is recorded with the point run that measured it, for that model prediction; earlier diagnostic results are unchanged. | P7, PT4, PT5, U7 | `check_measured_noisy` | rewrites earlier results' notes |
| C56 | The batch handed to a diagnostic is in the design's order, whatever order its runs finished in; so the diagnostic result doesn't depend on that order. | 0015, P4 | `check_design_order` | hands runs over in the order they finished |

## Workspace and MCP contracts

Provisional until `architecture.md` (step 9) and the guides (step 13). `architecture.md` §10 runs the workspace
contract over the guides' examples; C53 adds the use cases.

| Id | Promise | Generalizes | Check | Negative control |
|---|---|---|---|---|
| C53 | Each use case U1–U9 runs as written, and meets its "Done when" (no budgets in v2.0, 0050). | `use_cases.md` | `check_use_case`, one parametrized check over the use cases, slow tier | a workspace that runs before showing the price fails every use case that makes a new run |
| C54 | Each CLI command's result equals the workspace function it calls. | the held principle "One-way layers" | `check_cli_matches_workspace` | a command that formats its own numbers |
| C55 | Every MCP tool returns the envelope, has a description for every schema field, and marks errors `retryable` or not; every number in a tool result equals the stored value it names. | P1, 0016, 0019, U9 | `check_tool` | a tool that rounds a number itself |

## Other tests the principles name

Not contracts (they don't run over implementations of an interface). With these C rows, they are every test the
principles name: P3's in C33, C34, C46, C48, and C50; P4's in C7 and C20; P5's in C51; P6's in C1–C6; P7's in
C16, C46, and C52.

| Test | Principle | Tier |
|---|---|---|
| No module in `ema` imports an LLM SDK (import-linter) | P1 | fast |
| A report rebuilt from the store alone is byte-identical | P1 | fast |
| Every heuristic threshold is a named constant in a spec, and the reverse (none in v2.0, 0017) | P2 | fast |
| A report's main body is byte-identical with and without interpretations; nothing in layers 0–3 imports `ema.experimental` (import-linter) | P2 | none in v2.0: no `ema.experimental` (0017); added with it |
| The terminology test: public names and generated text (0008) | glossary | fast |
| Golden reports for the reference models: structure, and numbers within one unit in the 4th digit (`diagnostics/shared.md`, 0044) | P4 | slow |
| Each reference model's expected answers (`reference_models.md`, step 11) | | slow |

## Test tiers

| Tier | Contains | Budget | Runs |
|---|---|---|---|
| fast | unit tests; the contracts on run batches built directly, and on millisecond models; doctests; import-linter | 30 s, serial: a size budget (`scope.md`) | after every edit |
| slow | the use cases end to end; reference models' expected answers and golden reports; C18 at d = 20 for the polynomial model, and every d = 20 timing; the command-line reference models; the wheel build | 10 min with `-n auto`: a target | before a step is reported done |

- **Budgets:** the fast tier's 30 s is one of `scope.md`'s size budgets: going over it is a decision record,
  not a drift. The slow tier's 10 min is a target: each build step's plan reports the tiers' times, and a step
  that exceeds it says so, and proposes a fix or a new target. The polynomial model's known-answer tests alone
  take about 9 min serially (`polynomial_model.md`), so they run in parallel with the rest.
- **No patched constants:** every check uses `BOOTSTRAP_RESAMPLES` = 1000, as users run it. The one expensive
  case, the polynomial model at d = 20 (1000 refits of a 1848 × 231 matrix, about 19 s, measured 2026-09-30),
  runs in the slow tier; the other diagnostics run C18 at d = 20 in the fast tier (the linear model's 1000
  refits at d = 20 take about 0.1 s).
- **`D20_SECONDS`:** 60 s for one diagnostic evaluation at d = 20 with the defaults, in the slow tier.

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| `UNITS_SCALES` | (2⁻⁴⁰, 2⁴⁰) | the scalings C5 applies | about 10∓¹², as v1's; powers of 2 keep distinct values distinct (0035) |
| `UNITS_SHIFT` | 3·max\|y\| | the shift C5 applies | moves every value, and loses about 2 bits, which merges no two of the contract model's values |
| `UNITS_RTOL` | 10⁻⁹ | C5's tolerance under the shift: relative to a·(the range of y) in y's units, absolute when dimensionless | measured: 2·10⁻¹⁵ on the contract model (scatter, the linear fit; 2026-09-30) |
| `UNITS_LOG_TOL` | 10⁻¹² | C5's tolerance under a power-of-2 scaling alone, for a number computed through a logarithm | log₁₀ rounds at about 10⁻¹⁵; every other number is exact (measured: 0); as CL8 and LN7 under a·y alone; under a shift they use `RATE_SHIFT_TOL` (0048) |
| `OFFSET_RTOL` | 10⁻⁶ | C6's tolerance | 10⁶ + 10⁻³·f keeps about 7 of f's digits; measured worst 1.9·10⁻⁷ (scatter's binned index); the variance by mean(y²) − mean(y)² is 100% off |
| `ROUNDING_WIGGLE` | 10⁻¹⁵ | the relative wiggle of "constant to rounding" | 0035's case: about 25 units in the last place of 7, at the contract model's largest f (3.2) |
| `D20_SECONDS` | 60 | the slow tier's time for one diagnostic evaluation at d = 20 | the polynomial model's bootstrap alone takes about 19 s |

## What this spec asks of other documents

- **Architecture (step 9):** the registries; each diagnostic's declarations for the checks (above); a
  progress callback during the analysis, which C49 interrupts from (`on_progress` is on the run service only;
  PM10 asks for the analysis phase); §10's contract table: the model contract over a Python function, a batch
  Python function, and a command-line model (0025, 0026: every Python model isolated), rows for the sampler,
  basis, and interval-method contracts, and the workspace contract over the use cases too (C53).
- **Data model (step 8):** invariants I1… for C46–C52 and C56; the template's I4 (one run per key with a
  reusable status) against 0010 (a failed run reused, a retry stored beside it); its store test at
  `tests/contracts/store.py`, not `tests/test_store_contract.py`; a run's failure kind and reason, host, and
  resolved program path (C31, C44), in place of one `error` column; whether a repeated request's stored result
  is reused when a later EMA version changes a named constant such as `BOOTSTRAP_RESAMPLES` (C50; the constants
  are not part of a request's identity, `uncertainty.md`); the polynomial coefficients' intervals (0041).
