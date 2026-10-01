# 0039. Plot the polynomial model's fit against y; its shadows come with the active subspace

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (corrects U4 and `scope.md`).

## Context

A shadow plot shows the model prediction against the model parameters projected on the first one (1-D) or two
(2-D) eigenvectors of the gradient's second-moment matrix C = E[∇f ∇fᵀ], here estimated from a fitted
approximation: the active subspace's leading directions. For a linear fit the gradient is the constant vector
of slopes β, so C = ββᵀ, and its first eigenvector is β/‖β‖: the linear model's figure of y against w·u, with
w = β/‖β‖ (`../design/diagnostics/linear_model.md`, accepted), is a 1-D shadow.

For a polynomial fit, the gradient varies, and the shadow needs C's eigenvectors, which is estimating the
active subspace. Record 0012 and `../design/scope.md` put the active subspace and a 2-D shadow in a later
version. But U4 (accepted) lists in the polynomial model's lean set "a 1-D shadow (the model prediction against
the fitted polynomial)", and `scope.md` (accepted) repeats "a 1-D shadow". That is a plot of y against the fit's
predictions ŷ, not a shadow. The owner pointed this out in the polynomial model's interview (2026-09-30), and
chose to plot y both against ŷ and against each run's held-out prediction ŷ₋ₖ.

## Decision

We will:

- give the polynomial model's report one figure of the fit, with two panels and the same axes: y against the
  fitted values ŷ_k, and y against the held-out predictions ŷ₋ₖ = y_k − r_k / (1 − h_kk) (from the same leverages
  as the LOO error, with no refits), each with the line y = ŷ;
- not call it a shadow. The polynomial model has no shadow in v2.0; its 1-D and 2-D shadows come with the
  active subspace, later, from the gradient of the fitted polynomial;
- keep the linear model's shadow as it is: for a linear fit it is the 1-D shadow.

## Alternatives considered

- **A shadow on the polynomial's average gradient direction** (E[∇f], from the degree-1 coefficients): cheap,
  but it is the linear model's direction, not C's first eigenvector, and it would be misnamed for a model whose
  gradient changes direction (R2).
- **The 1-D shadow now** (C from the polynomial's gradient, its first eigenvector): about 60–100 lines and its
  own known answers, which is the active subspace that 0012 put later.
- **Only one of the two panels:** y against ŷ alone is optimistic at 2P runs; y against ŷ₋ₖ alone hides how much
  the in-sample fit flatters it.

## Consequences

- **`../design/use_cases.md`** (accepted), U4's "What they get": "a 1-D shadow (the model prediction against the
  fitted polynomial)" becomes "the model prediction against the fitted polynomial and against its held-out
  predictions"; "The active subspace, a 2-D shadow, and the decay of the coefficients are not in this lean set;
  … the active subspace and a 2-D shadow are not" becomes "… the active subspace and its 1-D and 2-D shadows
  are not". The scope summary near its end changes the same way.
- **`../design/scope.md`** (accepted): the polynomial model's report has "the model prediction against the
  fitted and held-out predictions" in place of "a 1-D shadow"; "Not in v2.0" reads "the active subspace and its
  1-D and 2-D shadows in the polynomial model's report".
- **Glossary** (accepted): a row for "shadow plot": the model prediction against the model parameters, in unit
  coordinates, projected on the first one or two eigenvectors of the gradient's second-moment matrix of a fitted
  approximation; for a linear fit, on the direction of its slopes.
- **`../design/diagnostics/polynomial_model.md`:** the figure, `polynomial_model_fit.png`.
- **`../design/architecture.md`** (draft, step 9): the polynomial model's row drops the active subspace and
  "shadows".
- Record 0012 is unchanged: it already puts the active subspace and a 2-D shadow later.
