# Principles

**Status:** accepted. **Updated:** 2026-09-30 (P1 clarified by 0019; P7's "Open" settled by 0021; held candidate updated by 0026; P3's hash settings by 0029, and its tracked files by 0031; P2's list by 0034; P6's constant by 0035, and its check by 0036).

## Accepted

### P1 Numbers come from EMA

Every number in a diagnostic result, report, figure, data card, or tool result is computed by EMA from
stored runs, and stored with the diagnostic result. No LLM computes, rounds, or restates a number in anything
EMA produces. An MCP client's own replies are outside EMA: EMA gives them result ids and its own rendered
text, and the report is the reference (0019).

- **Why:** an LLM makes arithmetic and transcription errors that look right, and a user can't tell a
  generated number from a computed one. A number must be reproducible from the stored runs and the diagnostic
  parameters. With the store as the one source, the report, the CLI, and a later agent can't disagree.
- **Enforced by:** an import-linter contract: no module in `ema` imports an LLM SDK
  (`architecture.md` §1). The report renderer and the figure code accept only stored diagnostic results.
  The MCP server's tools return result ids and text that EMA renders from the store. The server's
  instructions ask the client to quote that text and to point the analyst to the report, rather than restate
  numbers (0016, 0019).
- **Tested by:** the import-linter contract, in the fast tier; a test that rebuilds a report from the store
  alone and requires byte-identical output; with a scripted MCP client, every number in a tool result equals
  the stored value it names (U9).

### P2 Results first; interpretation is separate

A diagnostic result holds only estimates, observations, counts, notes, and figures (0034). Interpretation is
any comparison with a heuristic threshold, and anything that says what a number means or what to do next. It
is never part of a diagnostic result or of a report's main body; if EMA produces any, it is labeled
experimental and kept in its own section (OD-8). Every heuristic threshold used in interpretation is a named
constant, documented in the spec that uses it.

- **Why:** the user is the domain expert (`purpose.md`): EMA gives evidence, and judging what it means for the
  model is the user's job. Thresholds are heuristics that will be revised, and a diagnostic result must not
  change when they do. Named thresholds can be found, checked, and challenged in the spec, and versioned
  together, so a change is visible.
- **Enforced by:** separate types: `DiagnosticResult` has no field for a verdict, and `interpret()` in
  `ema.experimental` returns a separate `Interpretation`. An import-linter contract: nothing in layers 0–3
  imports `ema.experimental` (`architecture.md` §11). Separate storage: interpretations have their own table,
  keyed by the diagnostic result and the version of the rules, and their own renderer. Ruff's
  magic-value-comparison rule (PLR2004) in `ema.experimental`.
- **Tested by:** a test that builds a report with and without interpretations and requires the main body to be
  byte-identical (v1's `check_summary_ignores_interpretation`); the import-linter contract; a test that every
  threshold constant is named in a spec, and every threshold a spec names is a constant.

### P3 Everything that decides a run is hashed; every new run is priced and approved

Everything that decides what a run does (the model's spec, the contents of its files, and the point) is part
of the run's key and of its approval. A stored run is reused only when its model version and point match
(0005, 0006). A new run happens only after the user approves that diagnostic evaluation's new runs (0006).
The approval shows the price (how many runs are new, how many are reused, and the estimated time, or
"unknown"), and EMA never makes more new runs than it approved.

- **Why:** a run can take hours on the user's computer, and `purpose.md` promises both reuse of runs and a
  question before running. A model is arbitrary code, so an approval is informed only if it covers everything
  that decides what the code does. A stale run corrupts a diagnostic result with no visible sign. Tying each
  run to a model version makes a diagnostic result reproducible. One definition of "what decides a run" serves
  both the key and the approval, so the two can't drift apart (v1's bug A1). `purpose.md` promises a time
  estimate before running; an approval is informed only if it shows how many runs and how long; and making
  more runs than approved spends the user's time without their yes.
- **Enforced by:** the store keys runs by model version hash and point hash, and has no other lookup. The model
  version hash covers the spec, except the settings `keep`, `batch_size`, and `timeout_s` (0020, 0025,
  0029), and the contents of every file the model spec names: the Python function's file, the input deck
  templates, and the listed files; modules found elsewhere, installed packages, and programs outside the
  model's files are not covered, and each run records its program's path (`model_interface.md`, 0029). The
  scheduler is the only code that runs a model: it checks the store first, and refuses a new run unless an
  approval matches its model version hash and point. One approval module, from day 1 (`trust.md`); an
  approval records the model version hash and the new points it covers. Model files are compared as files
  (samefile, casefold), never as strings. The workspace prices the design against the store (new vs reused)
  before asking, and the approval records that price; the scheduler stops at the approved number of new
  runs. The time estimate comes from stored run durations for that model version, and is "unknown" when
  there are none.
- **Tested by:** change one byte in a model file: the model version changes, and no run is reused. Run the
  same diagnostic evaluation twice: the second makes no new runs and asks for no approval. Two designs in
  different model parameter spaces reuse runs at their shared points. Approve, change one byte in a model
  file, and run: the run is refused. A design with k of its n points stored: the price says n−k new, and
  exactly n−k runs are made. The scheduler refuses one run more than the approval states. With no stored
  durations, the price says the time is unknown.
- **Open:** budgets (OD-15) may add a second cap beside the approval.

### P4 Diagnostic evaluations are deterministic

With the same EMA and library versions, the same request gives the same design, and with the same runs, the
same diagnostic result, including its variability intervals. Every random draw is seeded from the request.

- **Why:** `purpose.md` promises that each diagnostic evaluation and its diagnostic result can be reproduced.
  The same request gives the same points, so a repeated or overlapping request finds its runs in the store
  (P3). Golden reports, snapshot comparisons, and checks against v1 at the same seed all need exact repeats.
- **Enforced by:** every random draw takes its seed from the request, with derived seeds from a spawned
  `SeedSequence`; when the user gives no seed, EMA picks one and records it (P5). Layers 0–1 take a seed
  argument for any randomness (`architecture.md` §1), and Ruff's NPY002 bans numpy's legacy global random
  functions.
- **Tested by:** the design generator contract: the same arguments give bit-identical points, and a different
  seed gives different points. The diagnostic contract: the same request with the same runs gives an
  identical diagnostic result, intervals included. Golden reports for the reference models, compared exactly in
  the slow tier.

### P5 Every diagnostic result records its provenance

Every diagnostic result records its provenance: EMA's version, the library versions, the model version, the
request (the model parameter space and the diagnostic parameters, including the seed), the runs it used, and
the approvals.

- **Why:** `purpose.md` promises the data and metadata needed to reproduce each diagnostic evaluation. A user,
  or a reviewer of their paper, can see what produced a number, including which runs and whose approval.
  Exported runs and diagnostic results carry what other tools need to use them. When a rerun differs,
  comparing the two provenance records says why: a new model version, a new library, or a new seed.
- **Enforced by:** `DiagnosticResult` can't be constructed without a `Provenance` (a required field, with no
  default). The store writes a diagnostic result and its provenance in one transaction.
- **Tested by:** delete a stored diagnostic result, rerun it from its provenance and the stored runs, and
  require an identical result. The store contract: no diagnostic result without provenance, and no
  provenance without its runs and approvals. Change the seed, or the model version, and rerun: the two
  provenance records differ in exactly that field.

### P6 No data, no estimates; no dependence on units

A failed run counts as not usable, and every diagnostic produces a diagnostic result however many runs
failed. When a diagnostic evaluation has too few usable runs, or a model prediction that is constant (the
same value in every usable run, 0035), its diagnostic result holds counts and a note, and no estimates. Every
tolerance on a model prediction is relative to that model prediction's range, so changing its units
(y → a·y + b, with a > 0) changes no note.

- **Why:** an estimate from three runs, or from a flat model prediction (0/0), prints as precisely as any
  other, and its variability interval may not show the problem. v1 argued degenerate cases more than once
  (whether a constant surface is additive, record 0001); one rule settles them for every diagnostic. Counts
  and a note tell the user what to do: run more points, or widen the model parameter space. Units are the
  user's choice: a note that appears in Pa and vanishes in kPa is an artifact, not evidence. Model predictions
  in physical units span many orders of magnitude, and with several model predictions in different units
  (OD-9), only relative tolerances treat them alike.
- **Enforced by:** one precheck in the diagnostic base, run before `compute`, so no diagnostic can skip it.
  The minimum number of usable runs is a named constant, documented in each diagnostic's spec (0035); every
  such threshold is dimensionless, and its spec says what it is relative to. One function in `ema.numerics`
  makes every tolerance on a model prediction from its range, and diagnostics use no absolute tolerance on
  model predictions. `DiagnosticResult` refuses to be built with no estimates, no observations, and no note
  (0036).
- **Tested by:** the diagnostic contract, over every diagnostic: too few runs, all runs failed, and a
  constant model prediction each give counts and a note, with no estimates; a constant plus a 10⁻¹² wiggle
  (R4b) gives estimates (0035). A constant
  model among the reference models, with its expected report. Known-answer tests one run below, and at, the
  minimum number of usable runs. The diagnostic contract: y → a·y + b leaves every note unchanged, and
  transforms each estimate as the diagnostic's spec says.

### P7 Noise is explicit

EMA treats a model as deterministic: one run per model version and point. A model is treated as noisy only
when its spec says so, or when repeated runs at one point have measured variation; then the repeats are stored
as replicates, and the diagnostic result reports the measured variation.

- **Why:** reuse (P3) and determinism (P4) assume a run's model predictions depend only on the model version
  and the point. Unmeasured noise reads as roughness and hides smoothness, the structure EMA looks for. A
  solver tolerance or an internal random seed can make a model noisy without the user knowing, so noise is
  measured, not assumed.
- **Enforced by:** the model spec has a `noisy` field, false by default, and the store key includes a
  replicate number: 0 for a deterministic model, except the point run's repeats, which are numbered 1, 2, …
  (0011). The point run diagnostic (OD-5) repeats runs at one point and stores the measured variation with
  the model version. Every diagnostic result for a model measured as noisy carries a note saying so.
- **Tested by:** the store contract: for a deterministic model, EMA never makes a second run at a stored
  point, except the point run's repeats (0011). A noisy reference model: the point run reports its
  variation, and later diagnostic results carry the note. A model declared deterministic that returns
  different values on repeats is caught by the point run, and gets a note.
- **Open (settled):** models declared noisy are not in v2.0; `noisy: true` is refused, and the point run still
  measures noise (0021).

## Candidates

> Held until the step that decides what they depend on. Candidates dropped on 2026-09-29, and why, are in
> record 0007 (`../decisions/0007-choose-the-principles.md`).

- **User code runs isolated, without EMA's secrets.** Split from "Nothing runs without approval" (now P3).
  OD-11 is decided: every Python model runs in an isolated child process (0026). Waits on `trust.md`.
- **One-way layers.** Each layer imports only from the layers below it. The interfaces (`ema.cli`, and later
  `ema.mcp`) hold no logic, and `ema.workspace` is the one place that orchestrates. Layers 0–1 (types,
  numerics, designs) do no I/O. Held until `architecture.md` is accepted (step 9). Answers so far:
  - Why: with all logic in the workspace, the notebook, the CLI, and a later agent behave the same; layers 0–1
    without I/O can be checked with known-answer tests and no fixtures.
  - Enforced by: import-linter's layers contract (`architecture.md` §11); a forbidden contract keeping `os`,
    `pathlib`, `subprocess`, `sqlite3`, and other I/O libraries out of layers 0–1; each CLI command parses its
    arguments, calls one workspace function, and formats the result.
  - Tested by: `uv run lint-imports` in the fast tier; a test that every CLI command's result equals the result
    of the workspace function it calls.
