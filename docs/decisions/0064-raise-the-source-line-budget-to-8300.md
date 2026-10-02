# 0064. Raise the source-line budget to 8,300

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none ("Before the first line of code", `TODO.md`).

## Context

`scope.md` budgets 8,000 source lines in `ema`, without tests and reference models; `architecture.md` §11
estimated 7,940 after 0057. Records 0061, 0062, and 0063, from the consistency check before code
(`../notes/consistency_review_2026-10-01_before_code.md`), each fix a contradiction or gap between accepted
specs, and add code. An independent estimate, package by package, of what they add (round 4 of that check):

| Package | §11 | Added | What for |
|---|---|---|---|
| `ema.types` | 775 | 60–110 | model parameter values as doubles; `DesignStructure` and its JSON; `duration()`'s rule; the stderr tail |
| `ema.numerics` | 550 | 0–5 | the fits call the map back |
| `ema.designs` | 350 | 25–50 | the map back; generator and sampler version refusals; given lines' fixed coordinates |
| `ema.models` | 1,300 | 16–30 | `remove_tree`; capturing the stderr tail |
| `ema.store` | 700 | 10–20 | Q7's tails; Q15's points |
| `ema.runner`, `ema.approval` | 410 | 0–15 | `replay_batch`, less T9's deletion moved out |
| `ema.diagnostics` | 2,000 | 2–6 | the `seed` rows |
| `ema.workspace` | 610 | 55–95 | `reproduce`: versions, the per-range rebuild check, the differences' wording; the root's check |
| `ema.cli`, `ema.mcp` | 705 | 5–12 | the lazy `ema mcp` import; exit 2 |
| **Total** | **7,940** | **173–343** | **8,113–8,283** |

`scope.md` says going over a budget is a decision, recorded, not a drift.

## Decision

We will raise the budget for source lines in `ema` (without tests and reference models) from 8,000 to 8,300,
and update `architecture.md` §11's estimates to the middle of each package's range above: about 8,200 in all,
100 under the budget. Each build step's plan still reports its package's count against §11.

## Alternatives considered

- **Keep 8,000 and cut 110–280 lines:** the candidates were `reproduce`'s rebuild check (a replay would use only
  the stored design, and say nothing of a generator that changed) and the per-range tolerance. Each cut gives
  back a check the reviews asked for, to meet a number set before these rules existed.
- **Decide later,** at the build step that crosses the budget: leaves §11 knowingly wrong, and the overrun
  would be found package by package instead of decided once.

## Consequences

- **`../design/scope.md`:** the budget row reads 8,300 (0064).
- **`../design/architecture.md`:** §11's per-package estimates and total (about 8,200), and its line on the
  margin.
- **`../design/trust.md`:** its closing sentence on the budget names 8,300.
