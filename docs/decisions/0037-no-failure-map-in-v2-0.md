# 0037. Show runs that aren't usable along each model parameter only; two-model-parameter plots later

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 6, scatter's spec; TODO step 7's
"Decide:" line on U3's failure map).

## Context

- **U3** (accepted) says of scatter's report: "Each panel marks the failed runs at their model parameter values
  (a marker along the bottom axis). A failure map shows failed and usable runs in each pair of model
  parameters, for a failure region that depends on two at once."
- **TODO step 7** has a "Decide:" line: whether every diagnostic's report adds U3's failure map when runs fail,
  or only scatter's.
- **What a pair plot adds:** a failure region that depends on two model parameters together (R5's a + b > 1,
  or its corner a, b < −0.8) is smeared in each one-model-parameter strip, and plain in the pair's panel.
- **What it costs:** d(d − 1)/2 panels: 28 at d = 8, 45 at d = 10, 190 at d = 20, most showing nothing, since a
  failure region usually involves one or two model parameters; a region in three is smeared in every pair.
- In scatter's interview (2026-09-30), offered a capped lower-triangular grid, every pair, or one-model-
  parameter views only, the owner chose the last, with two-model-parameter plots noted for later.

## Decision

We will show runs that aren't usable only along each model parameter in v2.0: the × strip below each panel
whose x axis is a model parameter (`../design/diagnostics/shared.md`). No report has a failure map of pairs.

- **U3's "What they get," `r1`,** reads: "the header counts 200 runs: 34 failed (30 errors, 4 timeouts), 166
  usable. Each panel marks the failed runs at their model parameter values (a marker in a strip below the
  axes). A note counts the failed runs by reason. Estimates come from the usable runs only."
- **Scope's "Not in v2.0"** gains: "**Two-model-parameter plots** (a failure map of failed and usable runs in
  each pair of model parameters, and pair plots of the model prediction): later. About one small build step:
  60–100 lines of figure code, a cap on the number of pairs (a named constant), and known answers on R5 (the
  triangle a + b > 1 and the corner a, b < −0.8) and R10 (the a·c interaction). Kept ready now: figures are
  made from the stored runs and the diagnostic result alone, and every data card holds each point's run id, so
  a later figure needs no new runs and no change to any design or estimate (0037)."
- **TODO step 7's "Decide:" line** on the failure map is removed: settled here.

## Alternatives considered

- **A lower-triangular grid, capped at 10 model parameters:** sees two-model-parameter regions, at up to 45
  panels, with a rule for which model parameters are left out.
- **Every pair, always:** complete, but 190 small panels at d = 20.

## Consequences

- **`../design/use_cases.md`** (accepted): U3's `r1` text, as above; in "What the use cases ask of other
  specs," the Contracts line drops "U3's failure map ('Decide:' line on step 7)".
- **`../design/scope.md`** (accepted): the "Not in v2.0" line above.
- **`../../TODO.md`:** step 7's "Decide:" line on the failure map is removed.
- **`../design/diagnostics/shared.md`** and **`scatter.md`** (drafts): no failure map; the × strips only.
- **`../design/reference_models.md`:** R5's error region still depends on a and b together; the reason given
  becomes the later pair plots, and a check that each strip shows the region's projection.
- An analyst who needs the pairs exports the runs (U5) and plots them in their own tool until then.
