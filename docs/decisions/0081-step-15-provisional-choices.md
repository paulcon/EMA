# 0081. Step 15's provisional choices: the MCP server

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 15 (`../plans/15-mcp-server.md`) builds `ema.mcp`, layer 5, on `demo-15-mcp`, without the owner's review
(0066). `architecture.md` §8 gives its tools, resources, envelope, threads, and approvals; `use_cases.md` U9,
`trust.md` (T4, T5, T9), `export.md` E7, `contracts.md` C55, and records 0016, 0019, 0053, 0056, 0057, 0061, and 0080
give its behaviour. The MCP Python SDK installed is 2.2.0, whose API differs from 1.x (`FastMCP` is now `MCPServer`;
the low-level `Server` takes its handlers as constructor arguments), and which speaks two protocol eras: the
`initialize` handshake (2024-11-05 to 2025-11-25), where a server may send requests such as `elicitation/create`
while a tool call is open, and the 2026-07-28 era, stateless, where it may not, and a question is instead returned as
an `InputRequiredResult` and the client calls the tool again with the answer. Some details are open in the specs;
each choice keeps P1–P7 and the specs' intent.

## Decision

We will, provisionally:

1. **Bound the extra at `mcp>=2.2.0`** (added with `uv add --optional mcp mcp`; `ema[mcp]` joins the `dev` group,
   0059 item 3). The roadmap asks for the first release with elicitation, which is 1.9.0; but the server uses 2.x's
   API (the low-level `Server`'s constructor handlers, `mcp.server.runner.serve_loop`, `ServerSession.elicit_form`),
   so the bound is the release it is written and tested against. Lowering it needs the lowest-versions job, deferred.
2. **Speak the handshake era only:** the server drives the SDK's `serve_loop` (handshake-only) rather than
   `Server.run`'s dual-era loop. §7 step 6 holds the run lock while the approval waits, and the price shown must be
   the price run (trust.md); the 2026-07-28 era can't ask inside a call, so it would need the workspace to price,
   return, and run on a second call under a lock taken again. A client that probes `server/discover` first gets an
   error and falls back to `initialize`, and elicitation works (tested with the SDK's client in `auto` mode).
3. **`python -m ema.mcp --root DIR [--workspace DIR]`** (`ema/mcp/__main__.py`) starts the server, as `ema mcp` does,
   for the demo before the CLI (step 16) merged; a root refused (`PathRefused`) is exit 2 with the message on stderr.
   Provisional: once `ema mcp` exists, the owner may keep it (it needs no console script) or remove it.
4. **The low-level `Server`, with the input schemas in `server.py` and every description in `tools.md`.** The server
   reads `tools.md` at start (instructions; each tool's description; one line per argument) and refuses to start when
   a tool or an argument it serves has no description there, or `tools.md` describes one it doesn't serve (C55, 0019).
   Arguments are checked against the schema (names, required ones, JSON types) before the workspace is called; a bad
   argument is an error envelope (`RequestError`), not a protocol error.
5. **The envelope is the structured content and the one text block** (its JSON), with the envelope's output schema on
   every tool, so a client that reads only text sees all of it. On an error, `data` is null and `text` repeats the
   message. `is_error` is set when `ok` is false.
6. **An elicitation's form is one required boolean, `approve`**, and its message the question's text, the terminal's
   (0016). Only `accept` with `approve` true is a yes; decline, cancel, `accept` with false, a client error, no answer
   within `ELICITATION_TIMEOUT_S` = 900 s, and a cancelled call are a no (recorded as asked, W3), so nothing runs.
7. **Who can be asked:** a client that declares the elicitation capability on a connection that can send requests.
   Otherwise the workspace is called with `approve=None` (`confirm=None`), which refuses new runs and saving before
   any question and records nothing (`CannotAsk`); the message is prefixed "this client can't ask the user (it has no
   elicitation)". Reads, prices, and repeated requests work (C50).
8. **Progress notifications** carry EMA's text (`Progress.text`) as their message; their value is cumulative over the
   runs and analysis phases, so it only increases (MCP requires it); at most one every `PROGRESS_INTERVAL_S` = 0.2 s,
   but each phase's first and last always go. Each is sent from the worker thread on the event loop, waited for up
   to 10 s; one that fails is dropped and never stops a run.
9. **Cancellation:** a call the client cancels, or one still open when the client leaves, is marked: its next
   `on_progress` raises `Stopped` (an `EMAError`; record 0080's hook, every finished run stored), and a question it
   is waiting on is answered no. A queued call that hasn't started never runs. On disconnect, the server closes each
   `Workspace` on its own thread, then the threads.
10. **`data` as strict JSON:** a returned dataclass field by field, without `text` (the envelope has it); enums as
    their values; timestamps as EMA's timestamp text; a model spec as its JSON; a diagnostic result as its
    `to_json()` without the provenance's run ids (§8: an export holds them), plus `short_id` and `model_version`.
    Every double passes through unchanged, so each number equals the stored value (P1, C55). `diagnostics(name)` adds
    `params_schema`, the JSON schema of the whole `params` object (each parameter's schema as the workspace has it).
11. **`see`** lists what holds more: a result's report, figure, and data card resources; `failed_runs(id=...)` when
    some row isn't usable; `ema://diagnostics/{name}`. Never a next step (0017).
12. **Resources:** `resources/list` lists each diagnostic, each stored result's report, and its figures and data
    cards; four templates are listed. A figure is served only when `{name}` is one of the result's figures, from the
    file name stored with it (a base name), in the directory `report(id)` returns (rebuilt when missing), so no
    argument is joined into a path (T5). An unknown result, figure, or URI is MCP's "resource not found" (-32002).
    `ema://diagnostics/{name}` returns the same envelope as `diagnostics(name)`, as JSON.
13. **AR3's contract for `ema.mcp`** forbids, beside the lower EMA packages and `ema.cli`, `ema.reference_models`,
    `numpy`, `scipy`, and `matplotlib` (direct imports), so the server can compute no number (P1). It is named "AR3
    The MCP server calls only the workspace", beside the CLI's AR3 contract (merged in parallel).
14. **`serve` refuses a relative root and `/` itself** (`PathRefused`), beside `open_workspace`'s refusals (not an
    existing directory, inside or equal to a workspace), so `python -m ema.mcp` refuses what `ema mcp` refuses (T5).
15. **Two `Workspace`s, each opened, used, and closed on its own one-worker thread** (§8; SQLite's thread affinity):
    `save_model`, `test_model`, `run_diagnostic`, and `export` on the writing one; the rest and the resources on the
    other.
16. **An object argument sent as its JSON text** (`params`, `space`) is read as that object when it parses to one; an
    agent sometimes sends an object as a string. Anything else is refused, naming the argument and its JSON type.

## Alternatives considered

- **Pin `mcp>=1.9`, using `FastMCP`:** the installed SDK is 2.2.0 and the code would not run on it; 1.x would also
  need its own testing.
- **Serve both eras, refusing questions on the 2026 era** (treating it as a client without elicitation): a modern
  client could then never run anything; falling back to the handshake keeps it working.
- **`MCPServer` (the high-level server):** its schemas come from type hints, and the descriptions would live in
  Python annotations rather than `tools.md`; its stdio runner is the dual-era loop.
- **A form with no field** for a yes: some clients render nothing to confirm; a required boolean is explicit.
- **No progress throttle:** a design of 10⁴ runs would send 10⁴ notifications.

## Consequences

- Spec edits on acceptance: `architecture.md` §8 names the extra's bound, the handshake era, `python -m ema.mcp`
  (if kept), the elicitation's form, and `params_schema`; §10 gains the MCP AR3 contract's extra forbidden modules;
  `scope.md`'s dependency line names `mcp>=2.2.0`.
- `ema.mcp` is 527 code lines against the roadmap's 410 (0084: measured, not trimmed).
- Deferred, each with its effort and seam: the lowest-versions job for the bound (15 min; the bound in
  `pyproject.toml`); live evals (OD-19); the 2026-07-28 era (about half a day plus a workspace change separating the
  price's question from the run under the lock; the seam is `EmaServer.run`).
- `docs/notes/demo_mcp.md` says how to register the server with Claude Code and Claude Desktop, and gives a demo.
