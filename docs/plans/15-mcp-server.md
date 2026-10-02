# 15. The MCP server

**Status:** in progress (demo; record 0066). **Branch:** `demo-15-mcp`. **Updated:** 2026-10-02.

## Goal

`ema.mcp`, layer 5: an MCP server over stdio with `architecture.md` §8's 10 tools and resources, each one workspace
call, its approvals and confirmations asked of the user by elicitation, its tool descriptions and instructions in one
reviewed file (`tools.md`), so that an MCP client (Claude Code, Claude Desktop) can drive EMA end to end (U9).

## Implements

- `architecture.md` §8, `ema.mcp`: the 10 tools, the four resource templates (report, figure PNG, data card,
  diagnostic), the envelope `{ok, data, text, see, error: {message, retryable}}`, two `Workspace`s on two dedicated
  one-worker threads, approvals and confirmations by elicitation with `ELICITATION_TIMEOUT_S` = 900, a client without
  elicitation refused before any question, `params` as one JSON object described by `diagnostics(name)`, `tools.md`
  (0019), confinement (T5); §10's AR1 (`ema.mcp` above `ema.workspace`), AR3 (its forbidden contract), AR4, AR5 and
  the reference models' contract over `ema.mcp`.
- `use_cases.md` U9; `contracts.md` C55 (`check_tool`) and C53's U9 (`check_use_case_u9`, slow tier).
- `trust.md` T4 (through MCP the yes is an elicitation; no elicitation, no question), T5 (the root; resources by
  name), T9 (the protocol stream stays clean: a model that prints at import and in each call), and "Model output and
  the MCP client" (the instructions say reasons and stderr lines are quoted model output).
- `export.md` E7 (export inside the root only, through the workspace's root).
- Records 0016, 0019, 0053, 0056, 0057, 0061 (`ema.cli` over `ema.mcp`), 0080 (`on_progress` raising stops a run).
- The `mcp` extra (`ema[mcp]`), and `ema[mcp]` in the `dev` group (0059 item 3).

## Out of scope for this step

- `ema mcp` itself (the CLI, step 16, merged on `demo` in parallel: it calls `ema.mcp.server.serve`).
- Live evals with an LLM client (`scope.md`; OD-19): the tests use a scripted client, with no API cost.
- The 2026-07-28 protocol era (stateless requests, elicitation as a retried call): record 0081 item 2.

## Tasks

1. Read the MCP SDK 2.2.0's source in `.venv` (the low-level `Server`, `serve_loop`, `stdio_server`, elicitation,
   progress, the in-memory streams and `Client`); add the extra (`uv add --optional mcp mcp`) and the dev group entry.
2. Write `tools.md` (instructions and the 10 tools' descriptions), then the tests: `tests/unit/mcp/test_server.py`
   (16 tests), `tests/contracts/tools.py` (C55's `check_tool` over the 10 tools, its negative control, U9 slow),
   `tests/support/mcp.py` (an in-memory scripted client, an elicitation that records and answers, a stdio peer that
   checks every stdout line is JSON-RPC).
3. Write `ema/mcp/server.py` (`serve`, `EmaServer`, the tool list from `tools.md`), `ema/mcp/__main__.py`
   (`python -m ema.mcp --root DIR`), `ema/mcp/__init__.py`.
4. Extend `pyproject.toml`'s contracts and `docs/index.md`; write `docs/notes/demo_mcp.md` (registering with Claude
   Code and Claude Desktop, a demo root, a 5-minute script); check the server answers `initialize` and `tools/list`
   from a real subprocess, also launched through `uv run --project`.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run pytest -q --slow -n auto tests/contracts/tools.py`.
- `uv run ruff check && uv run ruff format --check && uv run mypy`; `uv run sphinx-build -W --keep-going docs ...`.
- `ema.mcp`'s source lines against `architecture.md` §11 (`ema.cli`, `ema.mcp`: 714; the roadmap's 410 for this
  step).

## Stop condition

The checks pass; report to the coordinator, who reviews (0066) and merges.

## Choices made here

Each is in record 0081 with its reason.

1. The extra's lower bound is `mcp>=2.2.0`, the release the code is written and tested against, not 1.9.0 (the first
   with elicitation): 2.x moved and renamed the APIs used (`FastMCP` became `MCPServer`; the low-level server's
   handlers are constructor arguments; `serve_loop`).
2. The server speaks the handshake era only (`initialize`, protocol 2024-11-05 to 2025-11-25), through the SDK's
   `serve_loop` rather than `Server.run`'s dual-era loop: the 2026-07-28 era forbids server-initiated requests, so
   an approval couldn't be asked while the run lock is held (§7 step 6). A client that probes `server/discover` first
   falls back to `initialize` (tested).
3. `python -m ema.mcp --root DIR [--workspace DIR]`, provisional, for the demo before the CLI merged; it exits 2 on
   `PathRefused`, as `ema mcp` does.
4. The low-level `Server`, with input schemas written in `server.py` and descriptions read from `tools.md`; a tool or
   argument without a description there is refused at start (C55, 0019).
5. The envelope is both the tool result's structured content and its one text block (as JSON), with an output schema;
   on an error, `text` repeats the message.
6. An elicitation's form is one required boolean, `approve`: a yes is `accept` with `approve` true; decline, cancel,
   accept with false, an error, a timeout, or a cancelled call are a no.
7. A client "with elicitation" declares the capability and its connection can send requests; otherwise the
   workspace gets `approve=None` / `confirm=None` and refuses before any question (`CannotAsk`), the message prefixed
   "this client can't ask the user (it has no elicitation)".
8. Progress: each `Progress` becomes a notification with EMA's text as its message, its value cumulative over the
   phases so it only increases; at most one every `PROGRESS_INTERVAL_S` = 0.2 s but each phase's first and last.
9. Cancellation: a cancelled call (or a client that leaves) makes the next `on_progress` raise `Stopped`, an
   `EMAError` (every finished run stored, 0080), and answers a pending question no.
10. `data` is the returned type as strict JSON: dataclasses field by field without `text`, enums as their values,
    timestamps as EMA's text, a spec as its JSON, a result as its `to_json()` without the run ids plus `short_id` and
    `model_version`; `diagnostics(name)` adds `params_schema`, the object `params` must meet.
11. `see` lists the report and figure resources (and `ema://diagnostics/{name}`), and `failed_runs(id=...)` when a
    row isn't usable: what holds more, never a next step (0017).
12. `list_resources` lists each diagnostic, each stored result's report, and its figures and data cards; resources
    are looked up by name: a figure is served only when its name is one of the result's figures, and the file name
    is the stored one.
13. AR3's forbidden contract for `ema.mcp` also forbids `numpy`, `scipy`, `matplotlib`, and `ema.reference_models`,
    so the server can compute no number itself (P1).
14. `serve` (and `EmaServer`) refuse a relative root and `/` themselves, beside `open_workspace`'s refusals.
15. Each `Workspace` is opened, used, and closed on its own one-worker thread (SQLite's thread affinity).
16. `params` or `space` sent as JSON text that parses to an object is read as that object (agents sometimes do).

## Notes

- **Size:** `ema.mcp` is 527 code lines (`server.py` 499, `__main__.py` 23, `__init__.py` 5; no blank or comment
  lines, docstrings included), against the roadmap's 410 and §11's 714 for `ema.cli` and `ema.mcp` together. Record
  0084: measured, not trimmed.
- **Deferred:** the lowest-versions check of `mcp>=2.2.0` (with the lowest-versions CI job; about 15 min, the
  seam is the bound in `pyproject.toml`); live evals (OD-19); the 2026-07-28 era (about half a day: the approval
  would become a priced question returned as `InputRequiredResult` and asked again on the retry, which needs the
  workspace to separate "ask" from "run under the lock"; the seam is `EmaServer.run`).
- **For the demo:** `docs/notes/demo_mcp.md`.
- **Review round 1** (on `demo-15fix`; record 0081, Review round 1, items 17–26; record 0080 items 29–30): a spec
  file at `save_model`'s path holding the same spec, hand-formatted, is asked "already saved, unchanged: load it?"
  and loaded, never rewritten (ruling A); the form's `approve` defaults to true (ruling B); SIGTERM stops as a
  disconnect does, then ends the process by the signal; `params` naming a tool's own argument is a `RequestError`;
  a reply whose result isn't an object is a no at once; a cancel is never lost and a queued call never asks;
  `results(id, filter)` is refused; `data` refuses a non-finite number; `Stopped` is in `ema.types.errors`;
  `tools.md` reworded. Not done: killing a model call under way at a stop (it finishes and is stored; record 0081
  item 19 says why). Tests: 10 more in `tests/unit/mcp` (3 over stdio: a cancel during the form, a disconnect and a
  SIGTERM during a run, malformed answers); `ema.mcp` is now 626 code lines (`server.py` 598).
