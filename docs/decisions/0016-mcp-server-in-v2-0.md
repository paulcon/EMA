# 0016. Ship an MCP server in v2.0, with use case U9

**Date:** 2026-09-29. **Status:** accepted; its live evals amended by 0050 (later). **Resolves:** OD-7.

## Context

v1 had its own chat loop: 26 agent tools, a 1,600-word system prompt, about 5,800 lines in `agent/`, and about
$244 of live API spend, much of it on the eval gate ($15–20 per change to the prompt or a tool;
`../notes/v1/lessons_learned_2026-09-27.md` §2, §10). Its lessons suggest a few coarse tools, numbers rendered
by the harness, and shipping EMA as an MCP server, so that Claude Code, Claude Desktop, or any MCP client can
drive it with no chat loop to maintain (§8). They give the agent three jobs: set up a model, run a diagnostic,
and measure cost (§14).

OD-7's options were none, an MCP server, or an own chat loop; the suggestion was none in v2.0, MCP after. The
architecture draft already has `ema.mcp` in layer 5, each tool one `Workspace` call, with approval through MCP
elicitation (`../design/architecture.md` §8). No accepted use case covers an agent, and a feature with no use
case has no test of the path an analyst takes (`../notes/adding_a_use_case.md`).

Estimated effort: the server is a thin adapter, about 200–400 lines on the `mcp` Python SDK, plus the result
envelope, one reviewed file of tool descriptions, and about 10 eval scenarios. Live evals are the recurring
cost (OD-19).

## Decision

We will ship an MCP server in v2.0, `ema.mcp`, started by `ema mcp`.

- **Its tools run and read, and set up models from specs.** Each tool is one `Workspace` call: list and
  describe models and diagnostics; propose a model spec and save it; test a model; estimate; run a diagnostic;
  get a diagnostic result, a report, or a figure. At most 10 tools.
- **The agent writes model specs only.** `propose_model` drafts a model spec (JSON) for a Python function or a
  simulation code the analyst already has; `save_model` saves it only after the analyst approves the spec. The
  agent writes no code that EMA runs.
- **Every approval goes to the analyst,** through MCP elicitation, with the same price and wording as the
  terminal prompt (P3). A declined or unanswered elicitation is a no.
- **Tool results carry result ids and text rendered by EMA from the store** (P1, as clarified by 0019).
- **It is the last build step,** after the core, the Python API, and the CLI, as v1's lessons advise.
- **Use case U9** is added to `../design/use_cases.md`:

  > ## U9 The same through an MCP client
  >
  > - **Steps, as typed:** the analyst from U1 uses an MCP client (such as Claude Desktop) with EMA's MCP
  >   server, in a fresh workspace, and asks in their own words to set up `beam.py` as a model, test it, and
  >   run scatter over the same model parameter space with n = 200 and seed 1. The client's agent calls:
  >   `propose_model` (a model spec for `beam.py`), `save_model`, `test_model`, `run_diagnostic`, and
  >   `get_result`, and the analyst opens the report through its resource, `ema://results/{id}/report`.
  > - **What EMA asks, and when:** three elicitations: the model spec, before it is saved (the model
  >   parameters, units, nominal values, and the file); the test run: 1 new, 0 reused, time unknown; and
  >   scatter: 200 new, 0 reused, about 0.2 s. The client's agent answers none of them.
  > - **What they get:** tool results with result ids and EMA's rendered text; the same report as U1.
  > - **Done when:** on R2, with a scripted MCP client (no LLM, so no API cost):
  >   - the three elicitations come in that order, with U1's prices;
  >   - a declined elicitation saves no model spec, or makes no run;
  >   - every number in a tool result equals the stored value it names (P1);
  >   - the report read through the resource is byte-identical to U1's report on R2 (P4);
  >   - no tool writes a file that EMA runs.

## Alternatives considered

- **No agent in v2.0; MCP later:** the suggestion. The core is verified first, with no eval cost, but the agent
  and its evals would come in a later version, and the workspace API wouldn't be checked against an agent's
  needs until then.
- **An own chat loop:** full control over replies (v1's revise mode), but v1 spent about 5,800 lines, most of its
  eval failures, and most of its API spend on it.
- **Run and read only**, with no model setup: fewer tools and no agent-drafted specs, but setting up a model
  is the job where analysts most need help (v1's lessons, §14).
- **The agent also writes wrappers:** it would help more with awkward simulation codes, but it is agent-written
  code that EMA runs, which OD-11 and the trust spec would have to isolate.

## Consequences

- **`../design/scope.md`:** the agent row says an MCP server; the budget of 10 agent tools applies in v2.0.
- **`../design/use_cases.md`** (accepted): U9 is added, with its row in the table (P1, P3, P4; OD-7), and
  what it asks of other specs.
- **`../design/principles.md`** (accepted): P1 is clarified for MCP clients (0019).
- **`../design/architecture.md` §8** (step 9): the MCP tools, at most 10; the server's instructions (0019).
- **`../design/trust.md`** (step 10): approvals through MCP elicitation; the agent writes specs only.
- **OD-11** (step 4) stays open: the agent writes no code, so "only models the agent writes" is not needed
  for v2.0.
- **OD-19** (step 12) must be decided before the MCP build step: the monthly budget for live evals. The U9
  test uses a scripted client, with no API cost.
- **`STATUS.md`:** OD-7 moves to "Decided", naming this record, when it is accepted (0001).
