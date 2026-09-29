# 0012. Put six diagnostics in v2.0

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** OD-5.

## Context

v1 had 12 diagnostics, each with heuristic thresholds, and they were more than one person could verify in a
week (`../notes/v1/lessons_learned_2026-09-27.md` §12). The lessons suggest starting with "the diagnostics you
would use yourself: scatter, coordinate lines, a linear model, and a polynomial model", verifying each against
analytic answers before adding the next, and a size budget of "5 diagnostics at first" (§11). OD-5 suggested
3–4 of its six options: point run, scatter, coordinate lines, random lines, linear model, and polynomial model.

The accepted use cases use five of them (`../design/use_cases.md`): scatter (U1, U3, U5), coordinate lines
(U2), the linear and polynomial models (U4, U5), and the point run (U7). The accepted P7 and record 0011
depend on the point run: it is how a model's noise is measured. U2 asks which diagnostic runs a single, finer
line through a kink, and U4 leaves the active subspace, a 2-D shadow, and the decay of the coefficients out of
the polynomial model's lean report, for scope to decide.

## Decision

We will put six diagnostics in v2.0:

| Diagnostic | Design | What it's for |
|---|---|---|
| point run | point, with repeats | the model prediction at one point, and its measured variation (P7, 0011) |
| scatter | uniform | the model prediction against each model parameter (U1) |
| coordinate lines | lines along each coordinate direction, through the nominal point | smoothness along each model parameter (U2) |
| lines | m random lines, or lines the analyst gives (an anchor and a direction each) | smoothness along other directions, or along one line through a kink (U2) |
| linear model | convergent | a least-squares linear fit: its coefficients and residuals (U4) |
| polynomial model | convergent | a least-squares polynomial fit: its errors, Sobol indices, and the decay of its coefficients (U4) |

- **Lines** replaces OD-5's "random lines": one diagnostic draws m random lines, or takes the lines the
  analyst gives. Coordinate lines stays separate, with its own report (one panel per model parameter).
- **The linear model** is its own diagnostic, not the polynomial model at degree 1: its report has the
  coefficients with their variability intervals (U4).
- **The polynomial model's report** adds the decay of its coefficients to U4's lean set. The active subspace
  and a 2-D shadow are not in v2.0.

## Alternatives considered

- **The five in the use cases** (without random lines): fits U1–U8, but no diagnostic looks along directions
  other than the coordinate ones, and U2's single line would need another home.
- **Four, without the point run:** closer to OD-5's suggestion, but P7 and 0011 would need a new record, and
  U7 would go.
- **A separate line diagnostic beside random lines** (seven): two specs, designs, and sets of known answers
  for what differs only in how the lines are chosen.
- **The single line as an option on coordinate lines** (a subset of model parameters and another anchor):
  covers U2's kink, but only along a coordinate direction.
- **One "lines" diagnostic for coordinate, random, and given lines** (five): the least code, but coordinate
  lines' report, one panel per model parameter through the nominal point, is the one U2 asks for, and would
  become an option of a more general diagnostic.
- **The linear model as the polynomial model at degree 1:** one fewer spec and estimator, but the polynomial
  model's report would have to show coefficients at degree 1 and Sobol indices otherwise.
- **All three of U4's extras:** the active subspace and a 2-D shadow each need their own estimator, figure,
  and known answers; they can come later with their own specs.

## Consequences

- **`../design/scope.md`:** the diagnostics row lists the six; "Not in v2.0" lists the active subspace and a
  2-D shadow; the size budget for diagnostics is 6.
- **Step 6:** six diagnostic specs, each with known answers. The lines spec covers both random and given
  lines; the polynomial model's spec covers the decay of the coefficients, and its known answers.
- **`../design/designs.md`** (step 5): the lines design takes m random lines, or given anchors and directions,
  besides coordinate lines.
- **`../design/use_cases.md`** (accepted): U2's "(which diagnostic runs a single line is for OD-5)" becomes
  "(the lines diagnostic, with the line given)". U4's "whether they are in v2.0 is for scope (step 3) and the
  polynomial model's spec (step 6)" becomes "the decay of the coefficients is in v2.0 (0012); the active
  subspace and a 2-D shadow are not". The table's OD-5 entries stay, as history.
- **`STATUS.md`:** OD-5 moves to "Decided", naming this record, when it is accepted (0001).
- Six diagnostics is one more than the lessons' "5 at first". Each is still verified against known answers
  before the next starts (step 6, and the build order).
