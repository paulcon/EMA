# 16. The CLI

**Status:** in progress (demo; record 0066). **Branch:** `demo-16-cli`. **Updated:** 2026-10-02.

## Goal

`ema.cli`, layer 5, and the `ema` console script: `architecture.md` §8's 13 commands, each parsing its arguments,
calling one workspace function, and printing the text EMA rendered (C54; P1); `ema mcp` imports `ema.mcp` lazily.

## Implements

- `architecture.md` §8 (`ema.cli`): the 13 commands, the global `--workspace`, `--space FILE`, `--param k=v`, the
  approval on stderr and `--yes`, the exit codes 0/1/2/130, `ema report`'s streams (0060), `ema mcp --root` (T5);
  §1's AR1 and AR3; §10's AST check that `ema mcp`'s import is lazy (0061 item 8).
- `trust.md` T5 (`ema mcp`'s refused roots exit 2), What needs a yes (`--yes` still shown and recorded; no answer is
  a no).
- `contracts.md` C54 (`check_cli_matches_workspace`, over every command but `mcp`).
- Records 0060 (items 4, 10), 0061 (items 8, 12), 0080 (item 15: `ema.workspace` re-exports `ask`).

## Out of scope for this step

- The MCP server (`ema.mcp`, step 15, on a parallel branch): `ema mcp` calls `ema.mcp.server.serve(root=,
  workspace=)`, the seam the coordinator fixed; tested here with a stand-in module.
- `propose_model` and `save_model` (§8: not in the CLI).

## Tasks

1. Tests: `tests/unit/test_cli.py` (each command through `main(argv)` on R2, the approval, the exit codes, Ctrl-C,
   `ema mcp`'s root and missing extra, the progress line); C54's check and its negative control in
   `tests/contracts/workspace.py`; the lazy-import AST check in `tests/unit/test_ast.py`; the wheel's module and
   console script in `tests/slow/test_wheel.py`.
2. `src/ema/cli.py`; `[project.scripts] ema = "ema.cli:main"`.
3. `pyproject.toml`'s import contracts (AR1, AR3, AR4, AR5, the reference models'); `docs/index.md`'s block.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow tests/slow/test_wheel.py`.
- `ema.cli`'s lines against §11 (`ema.cli` and `ema.mcp` 714 together; the roadmap's 300 for the CLI).

## Stop condition

The checks pass; report to the coordinator (record 0066). When step 15 merges, the coordinator adds `ema.mcp` to AR1
(between `ema.cli` and `ema.workspace`) and to AR3's sources, and runs `ema mcp` against the real server.

## Choices made here

Each is in record 0082, with why.

1. One module, `src/ema/cli.py`, as §2's layout has it (the task said `src/ema/cli/`); `ema.cli:main` either way.
2. `--workspace` is accepted before or after the command.
3. `--param` values go to the workspace as text, which the diagnostic's `DiagnosticParameter.parse` reads (JSON, or a
   bare string); a missing `=`, a name given twice, or one of `run`'s own keywords is bad usage (exit 2).
4. `--space` and `--point` files: JSON objects, a duplicate key or NaN refused; unreadable or not an object is bad
   usage (exit 2); an object the workspace refuses is a `RequestError` (exit 1).
5. No terminal and no `--yes`: the question is shown with "no answer: no terminal, and no --yes", and the answer is a
   no, recorded (exit 1); `--yes` shows "Approve? [y/N] y (--yes)", recorded as a yes.
6. Lists: one item per line, a blank line between items when any spans lines; an empty list prints nothing on stdout
   and a one-line note on stderr.
7. `ema report` writes the Markdown exactly as the file holds it; `Report: <path>` (and `PDF: <path>`) on stderr.
8. `ema export` prints the export's absolute directory; `ema results ID` with filters is bad usage.
9. Progress: rewritten in place on a terminal; otherwise a line at each tenth of each phase.
10. Ctrl-C: exit 130 with "Stopped at <the last progress text>: every finished run is stored."
11. Errors: "ema: <message>" on stderr, exit 1; `ema reproduce` exits 0 whatever it finds.
12. `ema mcp`: `--root` required, absolute, not `/` (after resolving links), checked before the import; a missing
    `ema.mcp` names the extra, exit 2; `PathRefused` out of `serve` (the root refused by `open_workspace`) exits 2.
13. The import contracts: `ema.cli` on top of AR1 (above `ema.workspace` until `ema.mcp` exists), AR3 over `ema.cli`.
14. C54's check spies on `Workspace`'s methods: one call, §8's, and stdout exactly its returned text.

## Notes

- **Size:** `ema.cli` 271 code lines (no docstrings, comments, or blanks; 404 in all) against the roadmap's 300 and
  §11's 714 for `ema.cli` and `ema.mcp` together.
- **Tests:** the fast tier gains 22 CLI tests (about 13 s with `-n auto`), C54's 15 checks and its meta-test (about
  6 s), and 2 AST tests; the slow wheel test checks `ema/cli.py` and the console script.
- **Deferred:** `ema mcp` against the real server (step 15; one test with the scripted client, about 20 lines; the
  seam is `serve(root=, workspace=)`). `--pdf` is tested with a stubbed `Workspace.report` only (pandoc is the slow
  tier's `tests/slow/test_pdf.py`). U2's transcript as typed on the CLI, as a slow test (about 40 lines; C54 covers
  each command).
