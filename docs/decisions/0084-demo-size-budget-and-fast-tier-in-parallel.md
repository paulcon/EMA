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

**Review round 1** (step 12's review measured the bootstrapped diagnostics' cost: about 30 s of CPU each in the
diagnostic contract; fixed on `demo-diagfix`)

3. **A lean interval method in the diagnostic contract's checks that don't test the intervals:**
   `tests.support.fakes.LeanIntervalMethod`, the fake interval method (C30) with 25 resamples drawn from the stream
   it is given, the range of the defined values, and "none" under 5 defined. `run_in(..., lean=True)` gives it to
   a diagnostic with an interval method in C2, C3, C4, C5, C6, C10, C16, C17, and C7's recomputations at the 8
   memory offsets; C1, C7's two full evaluations, C8, C9, C11, C12, C18 keep the registry's bootstrap, and C19 its
   spy. The lean method still runs the diagnostic's own estimators on resamples, so C5's transform checks keep
   their force (an interval's ends are a min and a max of estimates, exact under a·y with a a power of 2), as do C7's
   offsets (each resample's fit at each offset) and C2's independence of the runs not usable. Every broken toy
   still fails its check (the meta-test); the lean method keeps C30's promises (the interval contract runs over it);
   a test pins where it is used. A diagnostic with no interval method is unchanged.
4. **Measured** on this Mac (8 cores), never quiet: other agents' tests held the load average at 12–28 throughout.
   Each tree run back to back, alternating, `pytest -q -n auto`:

   | | Load average (1 min) | Wall | CPU (user) |
   |---|---|---|---|
   | Before (c36d3c8), run 1 | 12.8 | 47.7 s | 182 s |
   | After, run 1 | 12.3 | 31.8 s | 151 s |
   | Before, run 2 | 15.7 | 76.3 s | 182 s |
   | After, run 2 | 27.0 | 53.3 s | 169 s |

   The diagnostic contract alone (`tests/contracts/diagnostic.py`, `-n auto`, load 22–28): 36.2 s → 15.1 s wall,
   and its tests' summed time 187 s → 61 s (the linear model's 84 → 19 s, scatter's 48 → 15 s, coordinate lines'
   24 → 11 s, the toy's 13 → 3 s). The 30 s budget holds at a load average near 12, not above it; the remaining
   longest fast tests are the bootstrap's own determinism tests (`tests/unit/numerics/test_determinism.py`, about
   4–12 s each) and the checks that keep the bootstrap (C9, C7, C11 over the linear model, 3–4 s each).

**Review round 2** (step 13's review asked for the polynomial model's share; measured on `demo-13fix`, every wave
merged: the six diagnostics, the workspace, the CLI, the MCP server)

5. **The polynomial model's share of the fast tier**, from the run's JUnit times, `pytest -q -n auto` at a load
   average of 4–10 on 8 cores: its own fast tests (`tests/unit/diagnostics/test_polynomial_model.py`, 32) 27.6 s,
   and the diagnostic contract's 19 checks over it (with the lean method where item 3 gives it) 17.5 s: 45 s of the
   tier's 232 s of test time, about a fifth. The tier took 41.5 s wall in that run (2002 passed, 61 skipped), and
   67.6 s in a run a few minutes earlier at a similar load: over the 30 s budget with every wave merged. This
   step's longest are its R5 tests (y with figures, 2–4 s; z, 1.5 s), C7 (`check_deterministic`, 4 s), and C1
   (`check_never_empty`, 3.6 s), which keep the bootstrap by item 3. Proposed: nothing moves now; the budget is
   among item 1's numbers measured at the end of the demo build (step 17), with this share named there.

## Alternatives considered

- **Trim now:** the reviews' refusals and checks are what the extra lines buy; trimming them before the demo
  trades correctness for a count.
- **Move more tests to the slow tier:** would hide the process and determinism contracts from the check run
  after every edit.
- **The lean method everywhere in the contract** (item 3): C8 (another tag moves the intervals), C9, C11 (the line
  under each table), C12, and C18 read what the bootstrap writes or how long it takes; they keep it.
- **A leaner fit in `ema.numerics.fitting`** (record 0078, Consequences): speeds the diagnostics themselves, not
  only the tests; step 02's module, shared with the polynomial model, left for the final cleanup.

## Consequences

- Spec edits on acceptance: `scope.md`'s budget and `architecture.md` §11's table (with the final counts);
  `contracts.md`'s Test tiers ("serially" becomes "with `-n auto`"); `CLAUDE.md`'s fast-tier command.
- Agents in waves 5–8 check the fast tier with `-n auto` (`docs/notes/demo_agent_brief.md`).
- Spec edits on acceptance (Review round 1): `contracts.md`, The contract model: the checks that don't test the
  intervals (C2–C6, C10, C16, C17, C7 at its offsets) may give a diagnostic the lean fake interval method; the
  others keep the registered one. The polynomial model (step 13) gets the lean method in those checks with no
  change of its own.
