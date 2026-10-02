# 0080. Step 14's provisional choices: the workspace

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 14 (`../plans/14-workspace.md`) builds `ema.workspace`, layer 4, on `demo-14-workspace`, without the
owner's review (0066). `architecture.md` §7 gives its names, signatures, and the order of one diagnostic evaluation;
`use_cases.md`, `export.md`, `data_model.md` (§6, §9, §10), `trust.md` (T5, T6), and records 0054, 0055, 0062, 0063
give its behaviour. The steps before it settled the lower layers' calls (0070–0075). Only the point run is
registered on this branch: scatter, the lines diagnostics, and the linear and polynomial models are built in
parallel. Some details are open in the specs; each choice keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

1. **Keep §2's four modules.** `_evaluate.py` holds §7's steps 1–9, the test run (steps 1, 4, 6), a result
   directory's rebuild (`data_model.md` §6), the replay's analysis, and a run's shown text, so each rule has one
   home; `__init__.py` holds `open_workspace`, `Workspace`, the root's checks, and the models' texts.
2. **Analyse and render with the model version's stored spec** (Q14), and run with it plus the loading's settings
   (`stored_model`, 0054): a rebuild or a replay from the store reads the same spec, so its report is byte-identical
   (P1, S10).
3. **Add `Store.model_names()`**, a read beside Q3 (`SELECT DISTINCT name FROM loadings`), for `list_models`: the
   store had no list of model names, and only the store opens the database (AR5).
4. **Resolve relative paths against the root** when one is given: the workspace's path (trust.md says so for
   `ema mcp`) and every path argument, since an MCP server's working directory is the client's choice.
5. **Under a root, refuse a path argument** with a hidden character, outside the root, inside any workspace (an
   ancestor holding `ema.db`), or naming a credentials file below the root (`PathRefused`, T5, T7); and a drafted
   spec's existing file whose resolved target lies outside the root. `load_model` is checked as `propose_model` and
   `save_model` are (§7: "every method that takes a path"). A root that isn't an existing directory is refused too.
6. **`propose_model` refuses what `save_model` would** before anything else: a name not ending in `.json`, a parent
   that doesn't exist, another file at the path (`PathRefused`). The agent learns it before the user is asked.
   `missing_files` lists the spec's named files that don't exist yet; the text holds the full spec, fenced (T7).
7. **`report` rebuilds a result's directory when any of its files is missing** (the report, a PNG, a data card),
   removing the incomplete directory first, since the store's `result_directory` keeps one that has a row. The
   figures are drawn from the stored result (its figures emptied, as `evaluate` draws them) and its runs replayed
   from its provenance.
8. **`reproduce` compares by the results' JSON:** the estimates, observation cells, and extra estimates that differ,
   counted ("2 estimates"); tables' headings; the title, counts, header, notes, figures, and measured-noisy record by
   name; then each data card ("data card toy") and the report ("report") byte for byte. With the original's directory
   missing, its files are drawn again from it into a temporary directory, so `reproduce` writes nothing to the
   workspace.
9. **A generator's or sampler's version that differs is a version difference** ("design generator uniform: 2 here,
   1 there", in `Reproduction.make`'s `versions`), and nothing is rebuilt; no generator or sampler registered for
   the identity is a sentence ("no design generator X here: the design was not rebuilt"); a rebuild that raises is
   "the design could not be rebuilt: …". Rows beyond the per-range tolerance are named, the first 10 and a count
   ("design points differ at rows 3, 17, and 4 more"). Never raises (0062, 0063).
10. **Export:** a directory that isn't empty, or a file, is `PathRefused`, before anything is written; `result.json`
    is written with its five keys in `export.md`'s order (`json.dumps`, not the canonical encoder, which sorts keys);
    its `spec` is the model version's (`versioned_json`: without the loading's settings, as a model version covers
    them); the column dictionary's kinds are "ema", "model parameter", and "model prediction", with a model
    parameter's scale and range in the design's space, or its held value.
11. **`failed_runs`** lists each run not usable for the result's model prediction once, at its first design row, in
    design order (Q7 to find them, Q9 to read each).
12. **What a run shows** (`RunInfo.text`): "Run 5d02: ok; y = 0.002026; at a = 1, b = 0.5; run directory: …", or
    "Run 9b3e, row 3: failed (error): <reason>; at …", replicates other than 0 named; numbers by `fmt` (S3); a
    failed run's stderr tail after "Its stderr's last lines (the model's own output, quoted):" in a fenced block
    (trust.md, Model output and the MCP client), with `ema.approval`'s T7 helpers, reused rather than copied.
13. **What loading shows** (`LoadingSummary.text`): "Loaded name@12: 3 model parameters (x1, x2, x3), 1 model
    prediction (y)" (the get-started guide), then one of "New model version name@12 (was name@12 at /path):
    helper.py changed" (U6; "the model spec changed" first when the spec did; files added or removed named), "The
    same model version, from another spec file (was … at /path)" (0054's move), or "Already loaded: nothing
    changed"; then each warning (M17). `ModelSummary.text` and `ModelDescription.text` list the same counts, the spec
    path, and each model parameter's units, nominal value, limits, and description.
14. **`on_progress` is `run`'s cancellation hook:** an exception it raises stops the evaluation between two calls,
    every finished run kept and no result stored (C49), which a caller off the main thread (the MCP server, where
    Ctrl-C can't reach a call) can use; no call-level kill (the coordinator's note for step 15).
15. **`ema.workspace` re-exports `ask`,** so the CLI, which imports only `ema.workspace` and `ema.types` (AR3), can
    pass the terminal approver. It is not counted (§7's counting rule).
16. **The root re-exports, lazily,** `open_workspace`, `Workspace`, `ResultRef`, `ask`, the errors, and the types the
    workspace returns (`DiagnosticResult`, `Provenance`, `ResultSummary`, `Reproduction`, the result tables,
    `Price`, `Progress`, the questions, and `summaries.py`'s types).
17. **Tests with a stand-in:** the contract's toy diagnostic (a uniform design, bootstrap intervals, a figure) is
    registered by the fast tests in scatter's place, so §7's order is tested end to end before the other
    diagnostics merge; `tests/contracts/workspace.py` holds the use cases as written, each skipping at its first
    step that needs an unregistered diagnostic, naming it. C53's negative control is `RunsBeforeAsking`, a workspace
    that makes a diagnostic evaluation's runs with a yes nobody gave; the meta-test runs U7 with it.

## Deferrals

- **The use cases that need scatter, coordinate lines, or the linear and polynomial models** run once those are
  merged (`uv run pytest -q --slow tests/contracts/workspace.py`): U1 and U8 (scatter), U2 (coordinate lines on R8),
  U3 (scatter, then the polynomial model), U4 (linear and polynomial), U5 (scatter and polynomial), U6 (scatter), U7
  (scatter after its point run), and the get-started guide from its step 5. Their parameter names are the use
  cases'; a diagnostic that names them otherwise fails there, which is the check working.
- **Checked on `demo` at 8e236a6** (scatter merged): U1, U6, U7, and U8 pass as written; U3 and the guide run
  up to the polynomial model.
- **`failed_runs` at 10⁷ rows** reads each failed run by Q9 (about 1 ms each); building the `RunInfo`s from Q7's
  columns is about 20 lines.

## Spec edits on acceptance

- `architecture.md` §7: items 4–7, 9, 14, 15; `Workspace(store, root)` is built by `open_workspace` only.
- `data_model.md` §8: Q3's `model_names()` (item 3).
- `export.md`: `result.json`'s `spec` is the model version's (item 10); the column dictionary's kinds.
- `use_cases.md` and the guides: the shown texts of items 12 and 13 where they show "<…>".

## Alternatives considered

- **A private `_paths.py` or `_show.py` module:** clearer, but §2 lists four modules, and the texts are short.
- **Listing model names from Q8's results:** misses a model with no result.
- **`propose_model` only describing an existing file at the path:** `save_model` would then refuse after the agent
  told the user it was ready.
- **Comparing results field by field in Python objects:** the JSON is the one form C17 promises, and compares every
  double bit for bit (−0.0 included).

## Consequences

- **Size:** `ema.workspace` 830 code lines (no docstrings, comments, or blanks: `__init__.py` 333, `_evaluate.py` 252, `_reproduce.py` 154, `_export.py` 91) against §11's 685
  and the roadmap's 745; `ema.diagnostics.base` already holds the request, identity, and provenance helpers the
  estimate counted (record 0075).
- **Tests:** the fast tier gains 25 tests (about 35 s serially, 2 s each); the slow tier 10 (U1–U8, the guide, and
  their skips until steps 10–13 merge).
- Steps 15 and 16 call one workspace method per tool or command; every method returns a type that prints as EMA's
  text, so they format no number (P1; C54, C55).
