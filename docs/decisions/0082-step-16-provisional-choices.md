# 0082. Step 16's provisional choices: the CLI

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

## Context

Build step 16 (`../plans/16-cli.md`) builds `ema.cli`, layer 5, and the `ema` console script, on `demo-16-cli`,
without the owner's review (0066). `architecture.md` §8 gives the 13 commands, the global `--workspace`, the approval
on stderr, `--yes`, the exit codes, and `ema mcp --root`; AR3 lets `ema.cli` import only `ema.workspace` and
`ema.types`, and `ema.mcp` lazily in its `mcp` command (0061 item 8); C54 asks that each command's result equal the
workspace function it calls. The workspace (step 14) returns a type that prints as EMA's text for every method, and
re-exports `ask` (0080 item 15). The MCP server (step 15) is built in parallel; the coordinator fixed the seam:
`ema mcp` calls `ema.mcp.server.serve(root=<absolute root>, workspace=<workspace>)`. Some details are open in §8;
each choice keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

1. **Keep one module, `src/ema/cli.py`,** as `architecture.md` §2's layout has it (the task's wording was
   `src/ema/cli/`): 270 code lines need no package, and `ema = "ema.cli:main"` is the same either way.
2. **Accept `--workspace` before or after the command** (`ema --workspace w run …` and `ema run … --workspace w`):
   each subcommand takes it too, with no default of its own, so the global default stays `ema_workspace`.
3. **Pass `--param` values to the workspace as text.** `DiagnosticParameter.parse` already reads text as JSON when it
   is JSON and as a bare string otherwise (and `DecimalText` keeps the text as written, so `alpha=0.7072` stays that
   decimal), so the CLI parses nothing and the CLI, Python, and MCP requests get one reuse key (0061). A `--param`
   without `=`, with an empty name, given twice, or naming one of `run`'s own keywords (`space`, `prediction`,
   `retry_failed`, `approve`, `on_progress`, which have options of their own) is bad usage, exit 2.
4. **Read `--space FILE` and `--point FILE` as JSON objects,** refusing a duplicate key and `NaN`/`Infinity` (as a
   model spec's reading does), so the text the user wrote is the request EMA hashes. A file that can't be read, isn't
   JSON, or isn't an object is bad usage (exit 2); an object the workspace refuses is its `RequestError` (exit 1). A
   point's values must be numbers (exit 2), since `run_dirs` takes floats.
5. **Answer the approval as §8 says, and record every answer.** The question on stderr, then `Approve? [y/N]`. With
   `--yes`, the line reads `Approve? [y/N] y (--yes)` and the answer is a yes, recorded with the question by
   `ema.approval` (W3). With no terminal on stdin and no `--yes`, the line reads `Approve? [y/N] no answer: no
   terminal, and no --yes`, and the answer is a no, recorded (`ApprovalDeclined`, exit 1), as trust.md's "no answer
   is a no". On a terminal, `ema.ask` reads the answer.
6. **Print lists one item per line,** with a blank line between items when any spans several lines (diagnostics,
   run information); an empty list prints nothing on stdout, and a one-line note on stderr ("No models loaded."), so
   a script reading stdout sees no text that isn't EMA's.
7. **Write `ema report`'s Markdown exactly as the file holds it** (no newline added), so `ema report ID > r.md` is
   byte-identical to the report; then `Report: <path>`, and `PDF: <path>` with `--pdf`, on stderr (0060 item 4).
8. **`ema export` prints the export's absolute directory,** the workspace's return; **`ema results ID` with a filter**
   is bad usage (the filters list results; an ID shows one).
9. **The progress line** (§8, "a progress line on stderr"): EMA's `Progress.text`, rewritten in place on a terminal;
   otherwise one line at each tenth of each phase (the bootstrap reports each of its 1,000 resamples, which a log
   doesn't need).
10. **Ctrl-C exits 130** with "Stopped at <the last progress text>: every finished run is stored." (or "Stopped: …"
    before any progress). U2's transcript shows "Stopped: 40 runs stored."; counting the runs would be a number the CLI
    made (P1, C54), so it quotes EMA's last progress text ("40/96 runs") instead.
11. **An `EMAError` prints "ema: <message>" on stderr and exits 1;** argparse's usage errors print the usage and exit
    2, and so does `ema` with no command. `ema reproduce` exits 0 whatever it finds: its text says whether the replay
    is identical, and exit 1 is for an `EMAError` (§8).
12. **`ema mcp`:** `--root` is required (argparse), absolute, and not `/` once links are resolved; these are checked
    before the import, exit 2 (T5). Then `from ema.mcp.server import serve`, inside `_mcp` only; an `ImportError` prints
    "ema mcp needs the ema[mcp] extra: uv sync --extra mcp (or pip install 'ema[mcp]')" and exits 2.
    `serve(root=<normalized root>, workspace=<--workspace as given>)`: a relative workspace resolves against the root
    in `open_workspace` (0057 item 5); a `PathRefused` out of `serve` (the root missing, or inside a workspace, refused
    by `open_workspace(root=)`; 0061 item 12) exits 2. The import carries a `type: ignore` for mypy on an install
    without `ema.mcp`.
13. **The import contracts on this branch:** AR1's layers put `ema.cli` above `ema.workspace` (a layers contract can't
    name `ema.mcp` before it exists; step 15's merge puts it between them); AR3's forbidden contract has `ema.cli` as
    its only source (step 15 adds `ema.mcp`); `ema.cli` joins the sources of AR4, AR5, and the reference models'
    contract. §10's AST check that `ema.cli` imports `ema.mcp` only inside `_mcp` is in `tests/unit/test_ast.py`, with
    a negative control.
14. **C54's check** (`check_cli_matches_workspace`, in `tests/contracts/workspace.py`, §9's "Workspace and CLI" module,
    fast tier) spies on `Workspace`'s 15 methods the CLI may call: each command (all but `mcp`) calls exactly one, its
    §8 function, and prints exactly the text that function returned. Its negative control is a CLI that rounds the
    numbers in a report.

## Review round 1

The independent review of steps 15 and 16 (record 0081, Review round 1); each fix is on `demo-15fix`, with a test.

15. **A `--param` naming one of the request's own arguments says where it goes** (m2, n4; amends item 3): the
    reserved names are now `model`, `diagnostic`, `space`, `prediction`, `retry_failed`, `approve`, `on_progress`,
    and `self`, each bad usage (exit 2): "--param approve isn't a diagnostic parameter: it goes in --yes (ema run),
    or your answer to the question"; `model` and `diagnostic` name the positional arguments. Before, `model`,
    `diagnostic`, and `self` reached the workspace as a `TypeError` with a traceback, and `approve` named a
    `--approve` option that doesn't exist.
16. **An `OSError` prints "ema: <message>" and exits 1** (m2; amends item 11): a `--workspace` that can't be made or
    opened (`/nonexistent/…`, under a file) is the system's reason, not a traceback; exit 1, as an `EMAError`, since
    it isn't bad usage of the command line.

## Alternatives considered

- **`approve=None` with no terminal** (`CannotAsk`, nothing recorded): §8 and trust.md say no answer is a no; showing
  the question and recording the no keeps a log's reader able to see what was refused.
- **Reading the answer from a piped stdin** (as `ema.ask` does in Python): §8 says no terminal is no answer, so a
  script must say `--yes`, which is shown and recorded as given in advance.
- **Counting the stored runs on Ctrl-C** ("Stopped: 40 runs stored."): a number the CLI made; the workspace returns
  none on an interrupt.
- **One progress line per update in a log:** 1,000 lines for one bootstrap.
- **A package `src/ema/cli/`:** the task's wording, but §2 says `cli.py`, and nothing needs a second module.

## Consequences

- **Size:** `ema.cli` 271 code lines (no docstrings, comments, or blanks; 404 in all), against the roadmap's 300 and
  §11's 714 for `ema.cli` and `ema.mcp` together. After review round 1, 283.
- **Tests:** the fast tier gains 22 CLI tests, C54's 15 checks and its meta-test, and 2 AST tests; the slow wheel test
  checks `ema/cli.py` and the `ema` entry point. Review round 1 adds 2 CLI tests (items 15, 16).
- **Deferred:** `ema mcp` against the real server, with the scripted client, after step 15 merges (about 20 lines;
  the seam is `serve(root=, workspace=)`); `--pdf` is tested with a stubbed `Workspace.report` (pandoc's PDFs are
  `tests/slow/test_pdf.py`'s); U2's transcript as typed, as a slow test (about 40 lines).
- **At step 15's merge:** add `ema.mcp` to AR1 between `ema.cli` and `ema.workspace`, and to AR3's sources; the
  `type: ignore` on the lazy import stays harmless (`unused-ignore` is listed).

## Spec edits on acceptance

- `architecture.md` §8: items 2–12 (the streams, lists, `--yes`'s line, no terminal's line, the progress line,
  Ctrl-C's line, `ema export`'s output, the usage errors); items 15–16 (the reserved `--param` names, and exit 1
  for an `OSError`).
- `use_cases.md` U2's transcript: "Stopped at 40/96 runs: every finished run is stored." (item 10).
