# 0032. Draw uniform points from numpy's PCG64, behind a sampler interface ready for others

**Date:** 2026-09-30. **Status:** accepted; its sampler interface amended by 0033. **Resolves:** OD-13.

## Context

OD-13 asked how the uniform design draws its points: an own seeded stream, `scipy.stats.qmc`, or both.

- **Nesting is relied on.** U3 and U5 (accepted) need a smaller uniform design with the same seed to be the
  first points of a larger one, and of a convergent design, so its runs are reused. v1 drew
  `default_rng(seed).random((n, d))` row by row, which gives this for every n (`../../../EMA-v1/src/ema/core/doe.py`,
  `uniform`), and never used `scipy.stats.qmc`. Its lessons: owning the designs "gave control, and exact
  deterministic sharing between designs, which the cache relies on" (`../notes/v1/lessons_learned_2026-09-27.md`).
- **Sobol** (scrambled, in `scipy.stats.qmc`) is also nested, and fills the space more evenly, but it is
  balanced only at powers of 2; U4's convergent sizes (2 × the number of coefficients, doubled at each level)
  aren't. v1's feature plan proposed it as a hashed design parameter (`../notes/v1/feature-plan-2026-09-26.md`).
  Latin hypercube and minimum-distance designs aren't nested.
- **numpy's stability promise** (NEP 19): a bit generator's raw stream is stable across versions; a
  `Generator` method's may change in a feature release. Today `Generator.random` on PCG64 is exactly
  (x >> 11)·2⁻⁵³ of one raw draw; checked with numpy 2.5.3, including `advance()` to a later row.
- **Chunked designs** (a later version, `../design/designs.md`) need rows [a, b) of a design without rows
  0 … a − 1.
- The owner wants to plan for choosable samplers, Sobol and beyond, but build only the simple one now.

## Decision

We will draw uniform points with a `random` sampler, behind a sampler interface that other samplers can join
later.

- **A `sampler` field** in the uniform and convergent designs' requests, part of the design's identity with
  the sampler's version. v2.0 accepts only `"random"`, the default; another name is refused as coming in a
  later version.
- **The interface:** `name`, `version`, `unit_rows(seed, d, start, stop)`, `nested`, and `balanced_sizes`.
  Uniform accepts any sampler; convergent requires a nested one.
- **`random`:** PCG64 seeded from the request; each double is (x >> 11)·2⁻⁵³ of one raw 64-bit draw, row by
  row, so it is nested for every n, and row i is reached with `advance(i·d)`.
- **Stability:** unit-cube points, and points in linear ranges, are the same across numpy versions and
  machines; points in log ranges only with the same machine and versions (P4), since `exp` can differ in the
  last bit. A golden-points test pins both.
- **Tested** with a fake sampler in the tests. Sobol, Halton, Latin hypercube, and minimum-distance samplers
  are listed in `designs.md` as later, each with its effort.

## Alternatives considered

- **`scipy.stats.qmc` Sobol only:** more even, and nested, but convergent's sizes would be powers of 2 (U4's
  change), and its scrambling may change between scipy versions.
- **Both, choosable in v2.0:** twice the tests and known answers now, for a gain in evenness no use case asks
  for yet.
- **`Generator.random()` directly:** the same numbers today, but numpy may change them in a feature release,
  and jumping to a row relies on an implementation detail.
- **The `sampler` field without an interface:** lighter, but the seam is untested, and adding Sobol could
  reshape the uniform and convergent code.

## Consequences

- **`../design/designs.md`:** a Samplers section; the uniform row takes `sampler`; G1's reach as above.
- **Adding a sampler later:** a record, known answers, and a class; Sobol is 30–50 lines, plus a rule for
  convergent's sizes at its balanced sizes.
- **Data model (step 8):** a design's identity holds the sampler's name and version.
- **Architecture (step 9):** `designs/` gains the sampler interface and `random`; the uniform and convergent
  stubs take `sampler`.
- **`../../STATUS.md`:** OD-13 moves to "Decided", naming this record, when it is accepted (0001).
