# 0060. Install from GitHub with uv, test the get-started guide, license EMA under MIT, and accept C53–C55

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (TODO step 13, guides as outlines).

## Context

Step 13 writes the four guides as outlines (`../guides/`) and walks each through `ema.workspace` on paper
(`../design/architecture.md` §7–§8), so that any awkward step changes the workspace before code exists.
`../design/contracts.md`'s C53–C55 were provisional until then (0056).

The walk-through, step by step against U1–U9, needed no new workspace function. It found:

- **A reference model can't be named from the CLI.** The import contract "Reference models are data beside the
  layers" (`architecture.md` §10) forbids `ema.cli` from importing `ema.reference_models`, so `ema model add` has
  no way to reach R2. In Python, `ema.reference_models.path(id)` gives the model's directory (§11), while
  `load_model` takes the spec's path.
- **`ema report ID` prints the Markdown only.** The analyst knows the short id, but the file lives at
  `results/<full result id>/report.md`.
- **Installing:** the repository is private on GitHub, and the name `ema` on PyPI is held by an empty 0.0
  placeholder ("a project repository"), so publishing there would need another distribution name.
- **Testing the guides:** `architecture.md` §9 runs the workspace contract over "the guides' examples", but
  the use cases' models (the beam, the heat solver, the lens) are illustrative; only the reference models run.
- **Outside contributors:** the owner chose that the add-a-diagnostic guide serves them too. The repository
  has no license, so a contribution's terms were unstated.

The owner answered four questions in the interview (install, tested examples, run-a-diagnostic's coverage,
add-a-diagnostic's audience) and one more (the license); the rest are the walk-through's.

## Decision

1. **Install from GitHub with uv.** Python and notebooks:
   `uv add "ema @ git+https://github.com/pauls-code-projects/EMA@v2.0"` in the analyst's project; the CLI
   and the MCP server: `uv tool install "ema[mcp] @ git+…@v2.0"`. Read access to the repository is needed.
   Nothing is published; the distribution name stays `ema`. Publishing on PyPI later is about half a day and
   a record, with another distribution name; `import ema` stays.
2. **Get started is in Python,** on R2 loaded with `ws.load_model(ema.reference_models.path("R2"))`, after
   `import ema.reference_models` (the root package doesn't re-export it, `architecture.md` §2). Its MCP
   step opens the same workspace, where the model loaded from Python is listed (T5 confines path arguments
   only). The CLI is shown in the other guides, with the analyst's own files.
3. **`ema.reference_models.path(id)` returns the model spec's path** (its `model.json`), not its directory.
   R2's model name is `ishigami` (added to `reference_models.md`), and its model prediction `y`. The other
   reference models' names are their build step's.
4. **`ema report ID` prints the report's path on stderr,** after the Markdown on stdout (and the PDF's path
   with `--pdf`): the CLI prints `Report.path` and `Report.pdf` as given. A path is not a number, so AR3 and
   C54 hold.
5. **Get started's Python blocks run as a test,** as written, on R2 from an installed EMA, in the slow tier:
   C53 gains them (`check_get_started`). The other guides keep the use cases' models as illustrations, tested
   through the use cases' "Done when" (C53). §9's "the guides' examples" becomes "get started's examples".
6. **Run-a-diagnostic has a section each** for an interruption and its resume (U2), failed runs and
   `retry_failed` (U3), reuse across diagnostics (U5), measured noise (U7), and reproducing (U8). U6 stays in
   add-a-model.
7. **Add-a-diagnostic is for the owner, Claude Code, and outside contributors.** Each v2.0 diagnostic's build
   step follows it. Contributors come in by invitation to the repository, under `CLAUDE.md`'s working rules:
   a spec in `draft`, a record `proposed`, and only the owner accepts. A new diagnostic changes `scope.md`'s
   list (0012) and its size budget, so it comes with a record.
8. **EMA is licensed under MIT** (`LICENSE`, copyright 2026 Paul G Constantine). Contributions come in under
   it. The first plan's `pyproject.toml` sets `license = "MIT"`. The license doesn't make the repository public.
9. **C53–C55 are accepted,** with C53 as item 5 extends it.
10. **Unattended runs** are shown in the run-a-diagnostic guide as `ema run … --yes`, or a Python approver that
    prints the question and returns True; both questions are rendered and recorded (W3). No new name.

## Alternatives considered

- **Install from a clone** (`uv sync`, then `uv run …` from inside it): the simplest for the owner, but every
  command needs `uv run` from the clone, and an MCP client's configuration needs `uv run --directory`.
- **Publish on PyPI at v2.0:** `uv add` by name, but it needs a new distribution name, an account, a
  publishing workflow, and a record. It stays open for later.
- **A CLI flag naming a reference model** (`ema model add --reference R2`): it needs `ema.cli` to import
  `ema.reference_models`, which the import contract forbids, or a workspace name (the budget is 19 of 20).
- **Every guide's examples run as tests:** runnable beam and R8 in place of the heat solver, at about 120
  test lines, but less realistic stories. **None run:** cheapest, but get started could drift from the code.
- **A fifth guide** for failures, model changes, and noise; or **leaving them to the reports' notes.**
- **Add-a-diagnostic for the owner and Claude Code only,** or **no such guide in v2.0.**
- **Decide the license before the first contribution;** or **BSD-3-Clause** (numpy's and scipy's), or
  **Apache-2.0** (an explicit patent grant). The owner chose MIT now.

## Consequences

- **`../guides/`:** the four outlines, as written in step 13.
- **`../../LICENSE`:** the MIT license. **`../../README.md`:** the license in its layout.
- **`../design/architecture.md`:** §8's `ema report ID [--pdf]` row adds "its path on stderr"; §9's workspace
  row reads "the use cases U1–U9 and get started's examples (slow tier)"; §11's `path(id)` "gives one's model
  spec"; its "Updated" line.
- **`../design/architecture.md`, `../design/trust.md`, `../design/model_interface.md`:** their "Guides (step
  13)" asks marked done (`../guides/`, 0060).
- **`../design/contracts.md`:** the status line and the section's "Provisional until the guides (step 13)"
  go; C53 adds get started's Python blocks, run as written on R2 (`check_get_started`); the slow tier lists
  them; its "Updated" line.
- **`../design/reference_models.md`:** R2's model name, `ishigami`.
- **`../plans/_template.md`:** the branch placeholder follows `CLAUDE.md`, `build-NN-<topic>` (a plain error
  found in step 13's review).
- **`../../TODO.md`:** step 13 done; "Before the first line of code" gains the first plan's `license = "MIT"`.
- **`../../STATUS.md`:** step 13 done; the contracts row no longer provisional.
- **`README.md`** (this directory): the 0060 row.
- **Later:** publishing on PyPI needs a distribution name other than `ema`. A guide whose examples become
  runnable joins C53's test.
