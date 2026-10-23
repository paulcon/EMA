# 14. The workspace

**Status:** in progress (demo; record 0066). **Branch:** `demo-14-workspace`. **Updated:** 2026-10-02.

## Goal

`ema.workspace`, layer 4: `open_workspace` and `Workspace`'s 18 methods, the one place that orchestrates a diagnostic
evaluation in `architecture.md` §7's order, so that the MCP server (step 15) and the CLI (step 16) call one function
per tool or command and show EMA's text. The root re-exports it lazily.

## Implements

- `architecture.md` §7 (all of it): `open_workspace`, `Workspace` (19 public names of `scope.md`'s 20, `close`
  included), "One diagnostic evaluation, in order" (`_evaluate.py`), `test_model`, `reproduce` (`_reproduce.py`),
  `export` (`_export.py`), the errors, what is shown; §2's `workspace/` layout; AR1, AR4, AR5, AR7.
- `use_cases.md` U1–U8 as typed against the workspace (U9 is step 15's).
- `export.md` E1–E6 (E7 through the root, T5).
- `data_model.md` Q11 (ids by prefix), §6 (a result's directory, rebuilt from the store), §9 Replay, §10 the run lock.
- `trust.md` T5 (the root, 0061 item 12), T6 (`save_model`).
- Records 0054 (reuse key, own approval, latest loading), 0055 (replay from provenance), 0062, 0063 (replay from
  stored points; the rebuilt design's check per range).
- `contracts.md` C53 (U1–U8 and the get-started guide, slow tier), and C47, C49, C50, C51, C52 end to end.

## Out of scope for this step

- U9 and C55 (the MCP server, step 15); C54 (the CLI, step 16).
- The diagnostics other than the point run (steps 10–13, on parallel branches): the use cases that need them are
  written as they will run and skip at their first step that needs one.

## Tasks

1. Tests from the specs: `tests/unit/workspace/` (fast: the order, P3's questions and refusals, C47, C49, C50, C51,
   C52, U6, U7, U8, E1–E6, T5, T6, the rebuilt directory) with the contract's toy diagnostic in scatter's place, and
   `tests/contracts/workspace.py` (C53: `check_use_case` over U1–U8, `check_get_started`, and the negative control's
   meta-test).
2. `src/ema/workspace/`: `__init__.py`, `_evaluate.py`, `_reproduce.py`, `_export.py`.
3. `Store.model_names()` for `list_models` (item 3 of the record).
4. The root's lazy re-exports; `pyproject.toml`'s import contracts; `docs/index.md`'s block.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto tests/contracts/workspace.py`.

## Stop condition

The checks pass; report to the coordinator (record 0066). The coordinator re-runs `tests/contracts/workspace.py
--slow` after merging steps 10–13, when the skipped use cases run.

## Choices made here

Each also in record 0080, with its reason.

1. The workspace's modules are §2's four; `_evaluate.py` also holds the test run, a result directory's rebuild, the
   replay's analysis, and the run's shown text (`RunInfo`), so each rule has one home.
2. The analysis and the report use the model version's spec as stored (Q14); runs use it with the loading's
   settings (`stored_model`), so a rebuild or a replay reads the same spec.
3. `Store.model_names()`, a read beside Q3, for `list_models` (the store had no list of names).
4. With a root, a relative workspace path and relative path arguments resolve against the root.
5. Under a root, a path argument with a hidden character, outside the root, inside a workspace, or naming a
   credentials file (below the root) is `PathRefused`; so is a drafted spec's existing file resolving outside it;
   `load_model` is checked as `propose_model` and `save_model` are.
6. `propose_model` refuses what `save_model` would (a name not ending in `.json`, a missing parent, another file at
   the path) before anything else, so the agent learns it before a question.
7. `report` rebuilds a result's directory when any of its files is missing (report, PNG, data card): the stale
   directory is removed first, since the store keeps a directory that has a row.
8. `reproduce` compares results by their JSON: counted estimates, observations, and extra estimates; tables'
   headings; title, counts, header, notes, figures, the measured-noisy record; then each data card and the
   report byte for byte. With the original's directory missing, its files are drawn again from it into a temporary
   directory, so nothing is written to the workspace.
9. A generator's or sampler's version that differs is one of the provenance's version differences ("design
   generator uniform: 2 here, 1 there"); no generator registered is a sentence; neither rebuilds nor raises.
10. Export: `PathRefused` for a directory that isn't empty; `result.json`'s `spec` is the model version's
    (`versioned_json`, without the loading's settings); the column dictionary's kinds are "ema", "model parameter",
    "model prediction", with a model parameter's scale and range, or its held value.
11. `failed_runs` lists each distinct run once, at its first design row, through Q7 and Q9.
12. `RunInfo.text`: "Run 5d02: ok; y = 0.002026; at a = 1, b = 0.5; run directory: …", or "Run 9b3e, row 3:
    failed (error): <reason>; …", numbers by `fmt`; a stderr tail quoted in a fenced block (T7's helpers in
    `ema.approval`, reused).
13. `LoadingSummary.text`: "Loaded name@12: 3 model parameters (x1, x2, x3), 1 model prediction (y)", then "New model
    version name@12 (was name@12 at /path): helper.py changed", or "The same model version, from another spec
    file (…)", or "Already loaded: nothing changed"; warnings each on a line.
14. `on_progress` raising stops a run between calls (C49): the cancellation hook for the MCP server's worker
    thread, documented on `run`.
15. `ema.workspace` re-exports `ask`, so the CLI imports only `ema.workspace` and `ema.types` (AR3).
16. The root re-exports, lazily, the workspace, `ask`, the errors, and the types the workspace returns.

## Notes

- Tests: 25 fast (about 35 s serially; about 2 s each, most of it the toy's bootstrap and figure), 11 in the
  contract module (2 run now: the meta-test and the get-started guide up to its first scatter block; U1–U8 run up to
  the first step that needs an unmerged diagnostic, then skip, naming it).
- Checked by hand: with the toy registered under the name "scatter", U3 (up to the polynomial model), U6, U7, and U8
  pass as written; U1 fails only on "a figure per model parameter", which the toy doesn't draw.
- Deferred: AmbiguousId through the workspace is the store's (tested there); a 10⁷-row `failed_runs` reads each
  failed run by Q9 (about 1 ms each); building the `RunInfo`s from Q7's columns would be about 20 lines.
- Checked against `demo` at 8e236a6 (steps 07's and 09's fixes, and scatter, merged), in an exported copy with this
  step's files and shared-file changes applied: the fast tier passes (1741), and the slow contract module runs U1,
  U6, U7, and U8 as written and passing; U3 and the get-started guide run up to the polynomial model; U2 and U4 skip.
- Review round 1 (`demo-14fix`; record 0080, items 18–28): a linked spec's files are checked beside its target,
  and `load_model` checks them before `load_spec` reads any (M1); a result directory is rebuilt by moving an
  incomplete one aside under the store's write lock, never deleted in place (`Store.result_directory`'s
  `complete`; m1); `reproduce`'s design check catches any exception (m2); `propose_model` reads with
  `open_regular` (m3); a workspace refuses a call from another thread with `EMAError` (m4); the interrupted
  evaluation's test compares the data cards, and a C51 test changes the seed and the model version (m5);
  `ema.approval.fenced` is public (n1); the run lock names "another workspace of this process" (n2); an export
  into a new `.ssh` or `.aws` directory is refused (n3); a label's name is honored by `list_results` (n4); `_reproduce`
  reads each file once (n5); `describe_model` keeps exact values (n6, disagreed: they are the spec's inputs, not
  computed numbers). 8 fast tests added (33 in `tests/unit/workspace`); the workspace's code is 886 lines.
