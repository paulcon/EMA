# 0013. Leave quadrature and sparse grids for a later version

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** OD-14.

## Context

The owner's early notes ask "Integration grids?" (`../design/architecture.md` §4, "Decide"). Quadrature grids
(tensor Gauss rules) and sparse grids (Smolyak) are designs for computing a polynomial approximation by
projection, and integrals, with known accuracy for smooth models. The linear and polynomial models in v2.0 fit
by least squares on convergent designs, nested uniform designs that reuse each other's runs and a scatter's
runs (U4, U5; record 0012).

## Decision

We will leave quadrature and sparse grids out of v2.0. They may come in a later version, with their own
design generators, a projection path in the polynomial model, and their own known answers.

## Alternatives considered

- **In v2.0:** projection on a sparse grid is cheaper than least squares for very smooth models, but it adds a
  design generator, a second fitting path in the polynomial model, and known answers for both, before the
  least-squares path is verified. Grid points are also not nested with uniform designs, so they would share
  few runs with scatter and convergent designs.
- **Never:** quadrature is a UQ method, but the purpose page reframes such methods as diagnostics; a
  convergence check on a sparse grid could be one. Ruling it out now isn't needed.

## Consequences

- **`../design/scope.md`:** "Not in v2.0" lists quadrature and sparse grids, as "later".
- **`../design/designs.md`** (step 5): v2.0's designs are point, uniform, convergent, and lines.
- **`../design/architecture.md` §4:** the "Integration grids?" item is settled.
- **`STATUS.md`:** OD-14 moves to "Decided", naming this record, when it is accepted (0001).
