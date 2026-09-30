# Adding a reference model

**Written:** 2026-09-30. A short guide to adding a reference model to `../design/reference_models.md`: when
to add one, how, the checks it has to pass, and what it can be used for once it's there. The rules themselves
are in `../../CLAUDE.md`, `../../README.md`, `../decisions/README.md`, and record 0009. Where this guide and
those files differ, those files win.

## What a reference model is for

A reference model is a model with known answers (glossary; record 0009). With it, "done" means "matches what
was worked out independently", not "the tests Claude wrote pass". Once a reference model is in the list, it
can be used to:

- **Test a diagnostic against known answers.** Each diagnostic spec's "Expected answers" table names
  reference models, quantities, tolerances, and sources (`../design/diagnostics/`). These become the
  known-answer tests. For example: R1's linear coefficients, R2's Sobol indices, R7's kink locations.
- **Test the degenerate cases.** R4a (constant), R4b (a 10⁻¹² wiggle, 0035), R5 (failed runs of each kind,
  and a missing model prediction), and R6 (hidden noise) exercise P6 and P7 in every diagnostic, through the
  diagnostic contract (`../design/contracts.md`, step 7).
- **Run the use cases' "Done when" tests.** Each use case names the reference model its workspace contract
  test runs on: U1 on R2, U2 on R8, U3 on R5, U4 on R10 and R2, U7 on R6 and R1 (`../design/use_cases.md`).
- **Check prices, reuse, and determinism.** A cheap Python reference model makes P3's and P4's tests fast: the
  same request twice, nested designs, a changed file, and golden reports compared exactly (P4).
- **Compare v2 with v1.** Where v1 has the same function (`../EMA-v1`, `src/ema/testfunctions/library.py`),
  running v1 at the same seed, in v1's own virtual environment, is an independent source of numbers
  (`../../CLAUDE.md`, "v1").
- **Exercise an interface.** R8 runs through the command-line path: an input deck, an output parser, and a
  shared file (0027, 0030).
- **Serve as examples.** The guides (`../guides/`, step 13) can use a reference model where they need a
  model whose answers the reader can check. Whether reference models ship with `ema` is for the architecture
  (step 9).

## When to add one

Add a reference model when a diagnostic, a use case, or a contract needs a known answer that no model in the
list gives. For example: a new diagnostic whose estimate none of the models pins down, a structure the list
lacks (a ridge, a discontinuity along a diagonal), a new kind of failure, or a new interface.

Before adding one, check whether an existing model, over another model parameter space or at another point,
gives the answer. R7 along a given line is a different test from R7 along a coordinate line, with no new
model. If a small change to an existing model would do, and that model's answers don't change, extend it
instead, with a variant id (R4a, R4b).

## Steps

1. **Check the table** at the top of `reference_models.md`. Is the structure new, or a variant?
2. **Take the next id:** R12, R13, … (or a letter variant, R6c). Ids are never renumbered or reused: tests,
   specs, and commits cite them.
3. **Choose the formula for its answers.** The expected answers must come from somewhere other than EMA's
   code: analytic (R1, R2, R10), by construction (R5, R7), quadrature (R11), brute force at a large sample
   size (R3), or the literature. Prefer a formula whose answers are analytic.
4. **Write its section** from the template below, in the glossary's words: the formula, each model
   parameter's range, scale, units, and nominal value, the model predictions, the interface, and what it does
   in each region.
5. **Add its row** to the table at the top.
6. **Add its expected answers** to each diagnostic spec that uses it ("Expected answers": quantity, expected
   value, tolerance, source). Step 11 gathers them into `reference_models.md`, and checks each against an
   independent source.
7. **Check it** against the list below.
8. **Get it accepted.** While `reference_models.md` is a draft, edit it directly. Once it is accepted (step
   11), adding a model is a change to an accepted spec: draft a decision record with status `proposed`,
   saying what the model adds and which specs' answers it feeds.
9. **Commit it all together:** `reference_models.md`, the diagnostic specs whose answers it adds, the record
   if one is needed, and `../../STATUS.md`.

## Checks

- **The answers are independent.** No expected value is computed by the code it tests. When the source is
  brute force, it is a separate script, run at a size where its own error is well below the tolerance, and
  its size and seed are recorded with the value.
- **Every tolerance says where it comes from.**
  - "Exact" for analytic answers the diagnostic should reproduce to rounding, such as a polynomial's
    coefficients recovered by a polynomial model of its degree or more.
  - A sampling bound, with the probability that it fails by chance, for a model with noise (R6: 10⁻⁶).
  - For brute force, the source's own error plus the diagnostic's.
- **Noise comes from fresh entropy.** A noisy model draws from the OS, not a fixed seed. Seeded when the
  child starts, a replicate made in a fresh child would repeat an earlier child's draws, and hide the noise
  (point run interview, 2026-09-30). Its tests check sampling bounds, never golden bytes.
- **Nominal values sit at the centers** of the ranges (the geometric center for a log range), so coordinate
  lines through the nominal point share it when n is odd (`../design/designs.md`, G12). A log range's
  nominal is written with enough digits to fall within 10⁻¹² of the center in unit coordinates (R3's r:
  2236.06797749979).
- **Features sit off the grids.** A kink or a jump at a place no coordinate line's points hit for n = 17, 33,
  or 65 (not a multiple of 1/8, 1/16, or 1/32 of the range in unit coordinates), so no run lands exactly on
  it (R7: 0.6 and 0.2).
- **It fits the model interface** (`../design/model_interface.md`): scalar model predictions, declared
  deterministic (`noisy: true` is refused, 0021); a Python function written with numpy, so it also works on a
  batch of points (0025), and brute force can evaluate millions of points at once; limits where the formula
  needs them (a log range needs lo > 0).
- **It is cheap.** Milliseconds per run, except where the point of the model is its cost: a timeout region
  (R5) puts every test that reaches it in the slow tier.
- **It fits the budget.** Reference models have 1,000 source lines in all (`../design/scope.md`). A real
  simulator that needs a third-party install is not a reference model in v2.0 (R9).

## Template

The section in `reference_models.md`:

````markdown
### R<n> <short name>

f = <formula>; <model parameters> in <ranges>, <scale>, nominal <values>.

| Model parameter | Range | Scale | Units | Nominal |
|---|---|---|---|---|
| <name> | [<lo>, <hi>] | linear | <units> | <center> |

- **Structure:** <what it has, and where: features by location, model parameters with no effect, noise, failure
  regions by kind>
- **Why it's here:** <the diagnostic, use case, or contract that needs it, and the answer no other model gives>
- **Expected answers:** <the quantities, or "in `diagnostics/<name>.md`">; source: <analytic, by construction,
  quadrature, brute force (size, seed), literature (citation)>
- **v1:** <v1's function of the same name, and what differs; or "none">
````

Its row in the table at the top:

```markdown
| R<n> | <model> | Python | <d> | <structure it has> | <why it's here> | <source of the expected answers> |
```
