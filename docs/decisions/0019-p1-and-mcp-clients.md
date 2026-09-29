# 0019. Clarify that P1 covers what EMA produces, including its tool results

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** none (TODO step 3; follows from 0016).

## Context

P1 (accepted, record 0007) says: "Every number in a diagnostic result, report, figure, or data card is
computed by EMA from stored runs, and stored with the diagnostic result. No LLM computes, rounds, or restates
one." Its enforcement says: "When an agent exists (OD-7), its tools return result ids, and the harness, not
the LLM, renders the numbers."

With an MCP server in v2.0 (0016), the harness belongs to the MCP client (Claude Code, Claude Desktop), not to
EMA. EMA controls only what its tools return. The client's model writes its own replies to the analyst, and
may restate or round EMA's numbers; EMA can neither prevent that nor test it. v1 tried to police its own
agent's prose after the fact, and every fix needed a new exemption
(`../notes/v1/lessons_learned_2026-09-27.md` §1).

## Decision

We will clarify P1's scope and enforcement, without weakening it for what EMA produces.

- **Statement:** "Every number in a diagnostic result, report, figure, data card, or tool result is computed
  by EMA from stored runs, and stored with the diagnostic result. No LLM computes, rounds, or restates a
  number in anything EMA produces. An MCP client's own replies are outside EMA: EMA gives them result ids and
  its own rendered text, and the report is the reference."
- **Enforced by** (replacing the sentence on agents): "The MCP server's tools return result ids and text that
  EMA renders from the store. The server's instructions ask the client to quote that text and to point the
  analyst to the report, rather than restate numbers."
- **Tested by** (added): "With a scripted MCP client, every number in a tool result equals the stored value it
  names (U9)."

## Alternatives considered

- **Leave P1 as written:** its "no LLM restates one" would then promise something about the client's replies
  that EMA can't keep or test.
- **Clarify P1 without server instructions:** the same promise, but the client gets no guidance; the
  instructions cost a few lines and help the common case.
- **No agent in v2.0:** keeps P1 as written until an agent exists, but reverses 0016.

## Consequences

- **`../design/principles.md`** (accepted): P1's statement, "Enforced by", and "Tested by" change as above.
- **`../design/architecture.md` §8** (step 9): the server's instructions, reviewed in the same file as the tool
  descriptions.
- **`../design/use_cases.md`:** U9's "Done when" tests the tool results (0016).
- Whether a client restates numbers faithfully is measured, if at all, by live evals (OD-19), not promised.
