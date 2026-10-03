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
   Amended in review round 1 (item 18): `approve` defaults to true, so Accept with it left out is a yes.
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
   `Workspace` on its own thread, then the threads. Review round 1 adds SIGTERM (item 19) and items 21–22.
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

## Review round 1

The independent review of steps 15 and 16, and the coordinator's rulings; each fix is on `demo-15fix`, with a test.

17. **A spec file at `save_model`'s path holding the same spec is loaded, never rewritten** (ruling A; M2; T6, U9):
    when the file's `ModelSpec.from_json(text).to_json()` equals the drafted spec's rendered text (the same spec,
    hand-formatted), `propose_model` shows the file's own text ("Already saved at …, the same spec") and
    `save_model` asks "already saved, unchanged: load it?" with those bytes, records their hash, writes nothing,
    and loads the file after the yes; a file changed between the question and the load is refused. A file holding
    another spec is still refused before asking. So an agent loads a model spec already in the root (the demo's
    `model.json` files) with `save_model(its text, its path)`. In the workspace: record 0080 item 29.
18. **Item 6, amended: the form's `approve` is checked by default** (ruling B; m5): its schema carries
    `"default": true`, so Accept on the form showing the price is a yes, also when the client sends `{}` or no
    content (the default applies). `approve` false, or anything but the boolean true, decline, cancel, a client
    error, and no answer within `ELICITATION_TIMEOUT_S` stay a no.
19. **SIGTERM is a stop, as Ctrl-C and a disconnect are** (m1): `serve` installs `EmaServer.terminate`, which
    cancels every open call (each stops between two runs, every finished run stored; a question waiting is a no),
    refuses new calls, closes both workspaces on their threads once their calls end (the run lock released, the
    model children stopped), then ends the process by the signal (exit status −15); a second SIGTERM ends it at
    once. On a disconnect, `serve` closes the workspaces the same way, so no model child outlives the server.
    What remains: a model call under way is not killed; it finishes (up to the model's timeout) and is stored
    before the server exits. Killing it would store a failed run made by the shutdown, which a rerun would then
    reuse (C47). A client that sends SIGKILL first leaves that child to finish its call and exit on its closed
    pipe.
20. **`params` naming a tool's own argument is a `RequestError`** (m2): `model`, `diagnostic`, `space`,
    `prediction`, `retry_failed`, `approve`, `on_progress`, and `self` each get "space isn't a diagnostic
    parameter: it goes in the tool's own `space` argument, not in params" (or "no argument"), never the workspace's
    `TypeError`.
21. **A reply the SDK can't read is a no at once** (m3): a client's reply whose `result` isn't a JSON object (or
    that has neither `result` nor `error`) fails the SDK's message validation, and the SDK drops it, which left the
    question waiting 900 s. `EmaServer.run` relays the read stream and turns such a reply into a JSON-RPC error
    for its id (`_answered`, reading the id from pydantic's error input), so the question fails at once and is a
    no, recorded. A reply with an unknown `action` or a malformed `content` already failed at once.
22. **A cancel is never lost, and a queued call never asks** (n1, n2; T3): `_Call` keeps the question's future
    before it checks `cancelled` again, and a cancelled question is answered no (`_ask` returns False). A call
    cancelled before it starts (queued behind a run, at a disconnect) returns "stopped: …" without calling the
    workspace, so nothing is asked or recorded.
23. **`results` with an `id` and a filter is refused** (n5), as `ema results ID --model …` is.
24. **`data` refuses a non-finite number** (n6; P1, C55): EMA's types hold finite numbers only (C17's strict JSON
    for results; a run's model predictions finite or missing; a spec's doubles, a price's time, finite), so
    `_plain` raises on one, which the envelope reports as EMA's failure, rather than writing null (a number made
    to vanish) or a string standing in for it.
25. **`Stopped` is in `ema.types.errors`** (n7), with the other errors, and re-exported by `ema.types`.
26. **`tools.md`** (rulings A, n8, n9): `save_model` says a spec file with the same spec is loaded after a yes,
    never rewritten, and that a `model.json` already in the root loads this way; the instructions' example space
    uses ±3.141592653589793 ("write π as 3.141592653589793: a request's numbers are part of what names its stored
    result"), say a relative path resolves against the root, say `params` never holds a tool's own argument, and
    that "ema report …" in `text` names the command-line command while the report is read through its resource.

**After the demo's rehearsal (2026-10-02)**

27. **The instructions ask the client not to interpret.** In the owner's rehearsal in Claude Code, the client
    quoted EMA's line and then explained what the intervals meant for each model parameter, drawing on what it
    knows about the Ishigami function. EMA's own output held no interpretation (P2, 0017), but `tools.md` asked
    the client only not to restate numbers (P1). It now also says: EMA reports results without interpretation;
    don't interpret unless the user asks; if you do, say it is your own reading, not EMA's, and keep it apart from
    what you quote of EMA's. This is a request to the client, not enforcement: a client may still interpret, as
    it may still restate a number. Spec edits on acceptance: `architecture.md` §8, the instructions' list (with
    P1's "quote EMA's text"), and a line in `principles.md` P2 that an MCP client's interpretation is the
    client's, asked to be labeled as such.

28. **A repeated request says it returned the stored result.** In the rehearsal, the client priced a scatter
    ("0 new runs, 200 reused") and ran it; EMA returned the stored result (no form, the same id, no run made: the
    store held the same 205 runs and 2 approvals), but its line was the stored result's own, "200 runs: 200 new,
    0 reused", the counts of the evaluation that made it. The client read that as the run disagreeing with the
    price, and told the user the price check was wrong. The workspace's `run` now marks a result returned for a
    repeated request (C50), and its shown text says so first: "Diagnostic result 6f6b: the stored result of the
    same request; no new runs, nothing asked. As made: scatter on …; 200 runs: 200 new, …". The CLI and the MCP
    server show it unchanged (C54, C55); `get_result` and `results` keep the plain line. Spec edits on
    acceptance: `architecture.md` §7, What is shown (a repeated request's text), and U1's repeat line.

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
  (if kept), the elicitation's form (with its default, item 18), SIGTERM (item 19), and `params_schema`; §10 gains
  the MCP AR3 contract's extra forbidden modules; `scope.md`'s dependency line names `mcp>=2.2.0`. Review round 1:
  `architecture.md` §7 `save_model` and `trust.md` T6 (its rule, its test, and "The path `save_model` writes"):
  "the same spec" rather than "the same bytes" (item 17); §3's errors table gains `Stopped` (item 25).
- `ema.mcp` is 527 code lines against the roadmap's 410 (0084: measured, not trimmed). After review round 1, 626
  (`server.py` 598, docstrings included): the SIGTERM handling, the reply relay, and the reserved names.
- Deferred, each with its effort and seam: the lowest-versions job for the bound (15 min; the bound in
  `pyproject.toml`); live evals (OD-19); the 2026-07-28 era (about half a day plus a workspace change separating the
  price's question from the run under the lock; the seam is `EmaServer.run`).
- `docs/notes/demo_mcp.md` says how to register the server with Claude Code and Claude Desktop, and gives a demo.
