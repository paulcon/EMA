# 0049. Widen approval and price to every new run, give the point design a space, and add the review's glossary rows

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** none (consistency review, Q7).

## Context

The later specs outgrew some of the glossary's rows (`../design/glossary.md`; consistency review,
`../notes/consistency_review_2026-10-01.md`):

- **Approval and price.** "approval" is "the user's yes to a diagnostic evaluation's new runs", and "price"
  is "what a diagnostic evaluation will cost". U1's `test_model` asks for its one run (1 new, 0 reused) outside
  any diagnostic evaluation. 0016's `save_model` saves a model spec "only after the analyst approves the spec",
  which isn't about runs; 0007 narrowed "approval" to runs.
- **The point design.** "each design has exactly one" model parameter space (0005), and "design" is "a set of
  points in one model parameter space". `../design/designs.md` says the point design has "no model parameter
  space (U7)".
- **The model version.** "a model's spec plus the contents of its files". 0029 narrowed it: the spec except
  its location, `keep`, `batch_size`, and `timeout_s`, plus the files the spec names. 0031 fixed the same
  overstatement in P3, not in the glossary.
- **An estimate's value "none".** `../design/uncertainty.md` lets the polynomial model's Sobol indices have the
  value "none" when the fitted polynomial is constant (0/0). The "estimate" row and 0041 allow only the
  interval to be "none".
- **Words with no row:**
  - "usable run" (about 250 uses; defined only in `shared.md`);
  - "request" (P4, P5, the provenance line);
  - "unit coordinates" (printed in reports);
  - "call" and "batch call" (`contracts.md` uses "batch" for two things; `scope.md` says "model call", which
    the "run" row's Avoid column lists);
  - "range" of a model prediction (P6: every tolerance is relative to it).
- **Two names that collide.** "Unit cube" means [0, 1)^d (C28, the sampler) and [−1, 1]^d (`designs.md`'s
  lines, `lines.md`). The data-card key `limits` (an axis's) collides with a model parameter's limits, and
  data-card keys are public names (0008).
- **"r" in one R3 report** is a model parameter, the sampler's rate ("r = 0.5"), the residual ("‖r‖"), and a
  rank ("rank r of P").

## Decision

We will:

1. **approval:** "the user's yes to new runs (a diagnostic evaluation's, or the test run's), given after EMA
   shows their price; it covers everything that decides what those runs do (P3)". **price:** "what new runs
   will cost, stated before any of them runs (a diagnostic evaluation's, or the test run's): how many runs are
   new, how many are reused, and the estimated time, or 'unknown' (P3)".
2. **New rows:**
   - **test run:** "one run at the nominal point, made by `test_model` to check a model, priced and approved
     like any new run; a stored run like any other (U1)".
   - **confirmation:** "the user's yes to saving a model spec an MCP client drafted, after EMA shows it in
     full (0016); not an approval, which is about runs".
3. **The point design has a model parameter space** that holds every model parameter at the point's value,
   with none varied. The "model parameter space" row's "each design has exactly one" stands. `designs.md`'s
   point design builds that space from `x` and the nominal values. No other generator accepts a space with
   nothing varied.
4. **model version:** "a model's spec (except its location, `keep`, `batch_size`, and `timeout_s`) plus the
   contents of the files the spec names, identified by a hash (0029)". The "model spec" row's last sentence
   says the same.
5. **The polynomial model with a constant fitted polynomial** reports no Sobol estimates, and a note says
   why. The "estimate" row stands: only the interval may be "none" (0041). `uncertainty.md` and
   `polynomial_model.md` drop the value "none".
6. **More new rows:**
   - **usable run:** "a run that is ok and read the model prediction a diagnostic evaluation analyzes; a failed
     run, or one missing that model prediction, is not usable (P6, 0022)".
   - **request:** "what one diagnostic evaluation is asked for: the model version, the model prediction, the
     diagnostic, its parameters, the model parameter space, and the seed; it decides the design (P4, 0006,
     0046)".
   - **unit coordinates:** "each varied model parameter mapped to [−1, 1], through its logarithm on a log scale
     (`designs.md`, 0047); 'the unit cube' is [0, 1)^d, the sampler's (C28)".
   - **call:** "one execution of a model by EMA: a run, or a batch call of a Python function (0025)". "model
     call" leaves the "run" row's Avoid column.
   - **range (of a model prediction):** "max − min over the usable runs; every tolerance on a model prediction
     is relative to it (P6)".
7. **Reword "unit cube" where it means [−1, 1]^d:** `designs.md`, "A line is straight in unit coordinates";
   `lines.md`, "the diagonal of [−1, 1]^d, 2√d".
8. **Rename the data-card key** for an axis's shown interval from `limits` to `extent`.
9. **Relabel in the reports:**
   - the design row: "sampler random 1 (rate ½)";
   - the residual: "‖y − ŷ‖ / ‖y − mean‖";
   - the rank note: "rank k of P".

   R3's model parameter keeps the name r.

## Alternatives considered

- **The test run as a point run with repeats = 0:** approval and price unchanged. Not chosen: the test run
  would get a diagnostic result and a report it doesn't need.
- **Widen "approval" to model specs:** one word for both kinds of consent. Not chosen: 0007 narrowed approval
  to runs, the thing P3 prices.
- **"Each design but the point design has a space":** not chosen. A degenerate space keeps one rule for every
  design, the space's JSON form, and the design identity (0046).
- **Allow an estimate's value to be "none":** not chosen; a note says it with no new kind of estimate.
- **Keep the data-card key `limits`, or keep "r" in the labels:** each is clear in context, but they are
  public names and printed text under the glossary's rules (0008).

## Consequences

- **`../design/glossary.md`** (accepted): Decisions 1, 2, 4, and 6. The "model parameter space" row adds
  "(the point design's holds every model parameter at the point, 0049)".
- **`../design/designs.md`** (accepted):
  - Point: "No model parameter space (U7)" becomes Decision 3.
  - Lines: Decision 7.
  - The generators that vary model parameters refuse a space with none varied (as SC1 does); the point
    design takes one.
- **`../design/diagnostics/point_run.md`** (accepted): its header's space row shows the point's space, every
  model parameter held. U7's "run for the point run needs no model parameter space" still holds: the user gives
  `x`, and EMA builds the space.
- **`../design/diagnostics/polynomial_model.md`, `../design/uncertainty.md`** (accepted): Decision 5, with the
  note's text.
- **`../design/diagnostics/lines.md`** (accepted): Decision 7.
- **`../design/diagnostics/shared.md`** (accepted): data cards' axes use `extent` (Decision 8).
- **The mock reports** (accepted): `linear_model.md` and `polynomial_model.md` take Decision 9's labels; every
  mock's design row takes "(rate ½)".
- **`../design/use_cases.md`, U1** (accepted): `test_model`'s approval is an approval under Decision 1; no
  change of text.
- **`../design/trust.md`** (step 10) and **`../design/architecture.md`** (step 9): `save_model` asks for a
  confirmation through MCP elicitation. `Workspace.estimate` and `CostEstimate` return a price, and their
  names are step 9's to settle.
- **`../design/data_model.md`** (step 8): an approval may belong to a test run; a confirmation is recorded
  with the model spec it saved.
