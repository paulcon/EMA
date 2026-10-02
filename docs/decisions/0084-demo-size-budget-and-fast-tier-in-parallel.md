# 0084. Let the demo build pass the source-line budget, measured at the end; run the fast tier in parallel

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

- **Size.** `scope.md` budgets 8,300 source lines (0064); `architecture.md` §11 splits them by package. After
  waves 1–4 of the demo build (steps 01–09 and T), `src/ema` holds about 7,560 code lines (no docstrings,
  comments, or blank lines; the reference models apart), against §11's 6,400 or so for the same packages:

  | Package | Measured | §11 |
  |---|---|---|
  | `ema.types` | 2,164 | 860 |
  | `ema.designs` | 586 | 388 |
  | `ema.numerics` | 359 | 553 |
  | `ema.models` | 1,349 | 1,323 |
  | `ema.store` | 1,216 | 715 |
  | `ema.plotting`, `ema.report` | 697 | 540 |
  | `ema.runner`, `ema.approval` | about 364 | 418 |
  | `ema.diagnostics` (base, point run) | 780 | part of 2,004 |

  Most of the overrun is validation the reviews asked for (refusals with field paths, strict JSON readers,
  cross-checks in the result types, the store's invariants), not features. The four diagnostics, the workspace,
  the CLI, and the MCP server remain; at the same ratio the total ends near 10,500.
- **The fast tier's time.** `contracts.md` budgets the fast tier at 30 s (serial, as `CLAUDE.md`'s command runs
  it). After wave 4 it takes 40–46 s serially on this Mac when idle, and 19 s with `-n auto`
  (pytest-xdist, already a dev dependency). Most of the time is real processes (the model adapter and runner
  contracts) and the determinism checks at memory offsets (0068), which the reviews made stronger.

## Decision

We will:

1. **Not trim the code to the budget during the demo build.** Each step reports its counts; the final count is
   measured at the end of the demo build (step 17), and this record is then amended with a proposed budget, or a
   list of what to cut, for the owner to choose.
2. **Run the fast tier with `-n auto`** during the demo build: `uv run pytest -q -n auto && uv run lint-imports`,
   with the 30 s budget on its wall-clock time. The serial command still passes; it is just slower.

## Alternatives considered

- **Trim now:** the reviews' refusals and checks are what the extra lines buy; trimming them before the demo
  trades correctness for a count.
- **Move more tests to the slow tier:** would hide the process and determinism contracts from the check run
  after every edit.

## Consequences

- Spec edits on acceptance: `scope.md`'s budget and `architecture.md` §11's table (with the final counts);
  `contracts.md`'s Test tiers ("serially" becomes "with `-n auto`"); `CLAUDE.md`'s fast-tier command.
- Agents in waves 5–8 check the fast tier with `-n auto` (`docs/notes/demo_agent_brief.md`).
