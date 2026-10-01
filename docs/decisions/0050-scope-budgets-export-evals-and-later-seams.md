# 0050. Leave run budgets and live evals out of v2.0, give export its own spec, and list the later seams in scope

**Date:** 2026-10-01. **Status:** accepted. **Resolves:** OD-15, OD-19 (consistency review, Q8).

## Context

- **Budgets (OD-15).**
  - The glossary defines a budget as "the most runs or seconds a request may use". U4 passes
    `budget=ema.Budget(max_seconds=3600)` and is "refused: 960 new runs, about 80 min, over the budget".
  - `scope.md` never says whether budgets are in v2.0, and P3 lists them as "Open".
  - STATUS says OD-15 blocks the data model (step 8).
- **Export.** `purpose.md` and U5 promise it. U5 specifies "a CSV of runs and a JSON file" holding a diagnostic
  result's runs, its design, and the result with its provenance, which "reading it back" reproduces. No spec
  owns the format, and scope's "In v2.0" table has no export or reproduce row (U8).
- **Live evals (OD-19).** 0016 plans "about 10 eval scenarios", and OD-19 "must be decided before the MCP build
  step". U9 is tested with a scripted MCP client, at no API cost.
- **Surrogates.** Scope says "no export of fitted surrogates". The polynomial model's coefficients, with their
  multi-indices and intervals, are in its diagnostic result (0041), which U5 exports.
- **`purpose.md`** says "EMA estimates the time to complete a diagnostic evaluation" and "variability intervals
  for all estimates". The price covers the model runs only (P3; `polynomial_model.md` rejected an analysis-time
  estimate), and an interval may be "none" (0041).
- **Deferrals in specs, missing from scope's "Not in v2.0":** other samplers (`designs.md`, 0032); the
  hyperellipsoid; chunked designs; other bases (`polynomial_model.md`); subsampling the levels
  (`linear_model.md`); memory and CPU limits and an in-process option (0026); a python output parser (0027); a
  real simulator as a reference model (R9).
- **No use case exercises** the lines diagnostic, the run-directory lookup (0020), PDF output (0018), `keep`
  (0028), or a batch Python model (0025). `adding_a_use_case.md` warns that "a feature with no use case behind it
  has no test of the path an analyst takes".

## Decision

We will:

1. **Leave run budgets out of v2.0 (OD-15).** The approval, after its price, is the only cap on new runs. A
   later version may add budgets with their own record.
2. **Give export its own spec,** `docs/design/export.md`, written before the data model (step 8): its files
   and columns, what it holds, and that reading it back gives the same values bit for bit. Scope's "In v2.0"
   table gains:
   - "Export: the runs a diagnostic result used, its design, and the result with its provenance, as CSV and
     JSON (U5; `export.md`)";
   - "Reproduce: a stored diagnostic result recomputed from its provenance (U8)".
3. **Leave live evals out of v2.0 (OD-19).** The MCP server is tested with the scripted client (U9). Live evals,
   their scenarios, and their monthly budget come with a later version.
4. **Reword scope's surrogates line:** "no surrogate objects, and no function to evaluate a fit; a fit's
   coefficients are numbers in its diagnostic result, exported with it (0041)".
5. **Reword `purpose.md`:**
   - "EMA estimates the time of the model runs a diagnostic evaluation needs";
   - "Reports include variability intervals for every estimate, or the reason there is none".
6. **Add one line to scope's "Not in v2.0":** "Seams kept, implementations later: other samplers, model
   parameter space shapes, and bases; chunked designs; other interval methods; memory and CPU limits; a python
   output parser; a real simulator as a reference model (R9); each in its spec." Drop scope's second mention of
   the active subspace.
7. **State in `use_cases.md`'s introduction** that the lines diagnostic, the run-directory lookup, PDF output,
   `keep`, and batch Python models are tested by their specs' tests and the contracts, not by a use case.

## Alternatives considered

- **Budgets per request,** as U4 and the glossary assumed: one type and one check. Not chosen: the approval
  already shows the price before any run, and v2.0 runs serially on the user's own computer.
- **Budgets per workspace:** a stored ledger and a reset rule. Not chosen, for the same reason.
- **Export in the data model's spec:** not chosen. The export is a user-facing format with its own read-back
  promise, and is easier to review on its own.
- **Live evals in v2.0,** about 10 scenarios run when asked: not chosen. The scripted client tests the server's
  contract at no cost, and live evals can wait until the server is used.
- **Price the analysis time too:** not chosen. It needs a flop model per diagnostic and a change to P3.
- **Extend U1 and U2** to exercise the untested features: not chosen. The use cases stay short.

## Consequences

- **`../design/scope.md`** (accepted):
  - Decisions 2, 4, and 6.
  - "Not in v2.0" adds "Run budgets (0050)" and "Live evals of the MCP server; the server is tested with a
    scripted client (U9, 0050)".
  - The v1 table's `evals/` row: "leave; later (0050)".
- **`../design/purpose.md`** (accepted): Decision 5.
- **`../design/principles.md`** (accepted): P3's "Open: budgets (OD-15) may add a second cap beside the
  approval" becomes "Budgets: not in v2.0 (0050)".
- **`../design/glossary.md`** (accepted): the "budget" row says "(later; not in v2.0, 0050)".
- **`../design/use_cases.md`** (accepted):
  - U4 drops the budget. `r3` at level 2 asks with its price (960 new runs, about 80 min); the analyst declines,
    and runs level 1. The narrative says "The analyst declines the degree-3 run at level 2 as too long".
  - "Done when": "the level-2 price shows 960 new runs, about 80 min; declining makes no run".
  - The asks drop `ema.Budget`, and step 12's OD-19 line.
  - Decision 7 in the introduction.
- **`../design/trust.md`** (step 10): the approval shows the model and the price, with no "budget left".
- **`../design/architecture.md`** (step 9): no `budget` argument and no `ema.Budget`, which frees a name.
- **`../design/data_model.md`** (step 8): Q5's "<campaign / budget>" goes; there is no budget table.
- **`docs/design/export.md`:** a new spec, `empty`, then `draft`; TODO adds it before step 8. README's files
  list adds it.
- **`STATUS.md`:** OD-15 and OD-19 move to "Decided", naming this record.
- **`TODO.md`:** step 8's "Decide: OD-15" goes. Step 12's "OD-19 (eval budget…)" goes.
