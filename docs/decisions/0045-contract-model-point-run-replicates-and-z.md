# 0045. Keep the quadratic contract model; give the point run's replicates and z their own fixture rules

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q3).

## Context

- **The contract model** (`../design/contracts.md`) is
  - at d = 3: f = a + b² + 0.05·a·log₁₀ c;
  - at d = 1: a + a²;
  - at d = 20: x₁ + x₂² + 0.1·x₃·x₄.

  In unit coordinates each is a polynomial of degree 2.
- **No rates.** Along any line, coordinate or random, f has k* ≤ 2, so coordinate lines and lines compute no
  decay rate on it. The rate parts of C5 (`UNITS_LOG_TOL`) and C6 are never exercised by the contract, and the
  polynomial model at p ≥ 2 fits it exactly. A term such as 0.2·sin(3b) would give k* = 8 along b and on
  random lines, and a relative residual of 0.10 at p = 2 (computed 2026-10-01). Rates and fit quality are
  already tested by each diagnostic's own known answers: CL3's fixture, CL8 and LN7 on R2, the rates on R7,
  and the polynomial model on R11 and R2.
- **The point run.** Its run batch is replicates at one point of a deterministic f, so every replicate is
  equal and the "varies" path is never run. Failure masks "over a's range" mean nothing at one point.
- **z** ("missing wherever b > 0.5") is undefined at d = 1 and d = 20, which have no b.

## Decision

We will:

1. **Keep the contract model as written.** On it, coordinate lines and lines compute no rate (k* ≤ 2), and the
   contract checks the no-rate path. The rate and fit-quality cases are left to the diagnostics' own
   known-answer tests, which `contracts.md` names.
2. **Give the point run's fixture its replicate values.** Replicate r at the point is f(x)·(1 + r·2⁻³⁰),
   distinct as doubles, so "varies" holds. Every replicate equals f(x) in the constant case. The point run's
   failure masks are by replicate number: every 7th; a contiguous block of replicates; the last 30%.
3. **Define z at d = 1 and d = 20:** z = f + 1, missing wherever the first model parameter is in its top
   quarter (a > 1.5 at d = 1; x₁ > 0.5 at d = 20). At d = 3 it stays missing wherever b > 0.5.

## Alternatives considered

- **Add 0.2·sin(3·) to the contract model** (on b, a, and x₂ at d = 3, 1, and 20): rates along b and on random
  lines, and residuals in the fits. Not chosen: the known-answer tests already cover rates and fits, and the
  contract model stays a simple quadratic whose every number is easy to check by hand.
- **A second fixture function only for the rate and fit checks:** not chosen, for the same reason.
- **The point run's replicates only, with z left at d = 3:** not chosen; every degenerate case then runs at
  every d.

## Consequences

- **`../design/contracts.md`** (accepted):
  - The contract model gains Decision 2's replicate rule and failure masks, and Decision 3's z.
  - A sentence under it: "On it, coordinate lines and lines compute no rate (k* ≤ 2); rates and fit quality are
    tested by CL3, CL8, LN7, and the polynomial model's known answers."
  - C5's and C6's rate clauses name those tests as where they apply.
- **`../design/diagnostics/point_run.md`:** no change. Its known answers on R6 stand; the fixture only feeds
  the contract.
- **Later:** if a diagnostic is added whose contract needs a non-polynomial f, its record revisits Decision 1.
