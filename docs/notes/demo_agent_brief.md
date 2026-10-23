# Brief for the agents building the demo (record 0066)

> Read this first, then `CLAUDE.md`, then your step's specs. A note, not a spec.

## The situation

EMA v2 is fully specified in `docs/design/` (all accepted) and has, until now, no code. The owner needs a working
demo of EMA through its MCP server by the end of 2026-10-02 and is not available to answer questions. Record
0066 (`docs/decisions/0066-build-a-demo-autonomously-on-a-demo-branch.md`) replaces the owner's review with
independent agent reviews. The order of work is `docs/notes/build_roadmap.md`, in waves (`docs/notes/demo_build.md`).

## How to work, as an implementing agent

1. **Read** `CLAUDE.md`, your step's row in `docs/notes/build_roadmap.md` (and "What each step watches for"), and
   every spec and id it names. `docs/design/architecture.md` gives each module's public names and signatures:
   follow them. `docs/design/contracts.md` gives the contract checks. Read only the parts you need of the big
   specs (use `grep -n` on headings and ids).
2. **Write your plan** in `docs/plans/NN-<topic>.md` from `docs/plans/_template.md`, short: status
   "in progress (demo; record 0066)", Goal, Implements, Out of scope, Tasks, Choices made here, Notes. (Step 01's
   plan already exists and was approved: follow it, and only update its status block and Notes.)
3. **Tests first:** write the contract checks and the known-answer tests from the specs, citing ids in
   docstrings, then write the code until they pass. Every public name gets a NumPy-style docstring citing its ids.
4. **Decide, don't ask.** Where a spec is silent, unclear, or contradicts another, make the reasonable choice that
   best keeps the principles (P1–P7) and the specs' intent, and list it under "Choices made here" in your plan,
   one line each, with why. Also write those choices into your step's decision record
   (`docs/decisions/NNNN-<slug>.md`, from `0000-template.md`, number given in your task; status
   `proposed (provisional; record 0066)`). Do not edit accepted specs; if a choice would change one, say so in
   the record ("Spec edits on acceptance: ..."). Do not edit `docs/decisions/README.md` or `STATUS.md`; the
   coordinator does.
5. **Deadline pragmatism.** What matters most is a correct, tested path from a model spec to a diagnostic result
   and its report, through the workspace and the MCP server. Keep the specs' rules for correctness, determinism
   (P4), provenance (P5), approval (P3), and numbers (P1). You may defer peripheral items (the lowest-versions CI
   job, exhaustive degenerate cases beyond the important ones, slow-tier timing targets, PDF polish); list each
   deferral in the plan's Notes and in the record, with the effort to add it later and the seam kept for it.
   Never fake a number, a test, or an interval to get green (`none: reason` is better than a patched estimate).
6. **Checks** (all must pass before you report): `uv run pytest -q -n auto && uv run lint-imports` (the fast
   tier in parallel, record 0084);
   `uv run ruff check && uv run ruff format --check && uv run mypy`;
   `uv run sphinx-build -W --keep-going docs docs/_build/html` (add your modules to the API reference). Run the
   slow tier for your package if it has slow tests: `uv run pytest -q --slow -n auto <your tests>`.
7. **Boundaries.** Touch only your step's packages, tests, plan, record, and the shared files your step must
   extend (`pyproject.toml`'s import contracts and dependencies, `docs/index.md`'s API list, `src/ema/__init__.py`
   re-exports, `ema/types/__init__.py`). Don't run git commands that change state (no commit, checkout, merge,
   stash, reset; the permission system refuses them); the coordinator commits and merges. Never read `.env`. v1 (`../EMA-v1`, tag `v1-final`) is read-only
   reference: port only the files your roadmap row names, and name each port in your report. Run v1 only with
   `../EMA-v1/.venv/bin/python`. No paid API calls. Don't install anything outside the project's `.venv` (adding
   a Python dependency with `uv add` is fine; say so in the record).
8. **Report back** (your final message): what you built (files), test counts and the checks' output summary,
   source lines per package against `architecture.md` §11, every choice and deferral (one line each), ports from
   v1, and anything you think the reviewer should look at hardest.

## How to work, as a reviewing agent

You did not write this code. Review the step against its plan, its specs and ids, `contracts.md`, P1–P7, and
AR1–AR7: look for wrong numbers, broken contracts, missing refusals, nondeterminism, untested paths, tests that
pass for the wrong reason, layering violations, and choices that contradict an accepted spec or record. Run the
checks yourself. Do not edit code. Report findings ranked by severity (blocker, major, minor, nit), each with
file:line, the spec id, a concrete failure scenario, and a suggested fix. Say plainly when the step is in good
shape.

## How to work, as a fixing agent

Fix the review's blocker and major findings, and the minor ones that are cheap; for each finding, say fixed,
not fixed (why), or disagreed (why, citing the spec). Add a test for each bug you fix. Record any new choice in
the step's plan and record, as above. Run all the checks.
