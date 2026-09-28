# Scope of v2.0

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Depends on:** OD-2, OD-5, OD-6, OD-7, OD-8, OD-14.

> What the first release does, what it explicitly doesn't, and the size budgets that keep it small. When
> something new comes up, the question is "is it in this file?", and if not, it waits for a later version.

## In v2.0

| Area | In scope |
|---|---|
| Model interfaces | <Python function; command line> |
| Designs | <point, uniform, convergent, line> |
| Diagnostics | <3–4 from OD-5> |
| Outputs | <scalar; multiple outputs in the schema (OD-9)> |
| Interfaces | <Python (workspace), CLI> |
| Agent | <none (OD-7)> |
| Interpretation | <none (OD-8)> |
| Reports | <one per diagnostic: Markdown with figures> |

## Not in v2.0

> The explicit "no" list. Each line says why, or when it might come.

- <Campaigns (OD-2)>
- <Surrogates>
- <Synthesis across diagnostics; advice; next steps>
- <Remote or cluster runs>
- <A web front end>
- <Spatiotemporal outputs beyond storing them>
- <…>

## Size budgets

> Going over one is a decision, recorded in `docs/decisions/`, not a drift.

| Measure | Budget |
|---|---|
| Source lines (without tests) | <5,000> |
| Public names in `ema.workspace` | <15> |
| CLI commands | <10> |
| Agent tools, when there is an agent | <10> |
| CLAUDE.md | <1,500 words> |
| Fast test tier | <30 s> |
| Runtime dependencies | <numpy, scipy, matplotlib, …> |

## What comes from v1

> v2 is a rebuild (decision 0002). v1 is at `../EMA-v1`, tag `v1-final`, for reference only. List which v1
> modules are read, re-reviewed, and ported, and which are left behind. The table in
> `../notes/v1/lessons_learned_2026-09-27.md` §13 is a starting point. A port is named in a plan and in its
> commit message.

| v1 module | Port, rewrite, or leave | Why |
|---|---|---|
| `core/models/_sandbox.py`, `_worker.py` | <…> | <…> |
| `agent/approval.py` | <…> | <…> |
| `core/legendre.py` | <…> | <…> |
| `testfunctions/` (with `truth.py`) | <…> | <…> |
| `tests/diagnostic_contract.py` | <…> | <…> |
| <…> | <…> | <…> |
