# Trust boundary

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Depends on:** 0016, 0019, 0020, 0026, 0029, 0030 (OD-7 and
OD-11 are decided).

> What EMA trusts, what it doesn't, and the rules at each crossing. There are two boundaries: the user's
> model code → EMA; and, through the MCP server in v2.0 (0016), the MCP client → EMA. The v1 rules, and the
> bugs behind them, are in v1's `src/ema/agent/approval.py` and `core/models/_sandbox.py`.

## What needs approval

| Action | Approval shows | Asked by |
|---|---|---|
| running a design with new runs | <the model, the price> (no budgets in v2.0, 0050) | <workspace `approve=` callback> |
| saving a command-line model | <the command, every file written or copied, the environment> | <…> |
| saving a file that becomes code | <its full text> | <…> |
| <…> | <…> | <…> |

## Running user code

> One mechanism for every piece of user code: isolated process, scrubbed environment, timeout, limits,
> stdin from `/dev/null`, and no unpickling of what it sends back.

<…>

## Secrets

> Which variables and files are never passed to model code, and never read by any tool.

<…>

## Rules

| Id | Rule | Test |
|---|---|---|
| T1 | Paths are compared as files (`samefile`, case-folded), never as strings. | <…> |
| T2 | Model programs never receive a variable from `.env`. | <…> |
| T3 | Every approval is recorded with its question and answer. | <…> |
| T… | <…> | <…> |
