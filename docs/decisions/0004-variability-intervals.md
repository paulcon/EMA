# 0004. Call EMA's intervals variability intervals

**Date:** 2026-09-28. **Status:** accepted. **Resolves:** OD-4.

## Context

Every estimate EMA reports has an interval (`../design/purpose.md`; the candidate principle "Every estimate
has an interval"). The methods under consideration are the bootstrap, refinement and convergence,
cross-validation and resampling, and held-out error (`../notes/v1/diagnostic-notes.md`); OD-12 chooses one per
diagnostic.

These intervals describe how an estimate depends on the finite set of runs a diagnostic used. A convergence
interval comes from a deterministic sequence of designs, and has no probability model behind it. A bootstrap
interval is a confidence interval only under assumptions about the runs that EMA doesn't check. Readers who
see "confidence interval" or "error bar" will assume a coverage guarantee, or an error, that EMA can't
promise.

The owner's notes ask for their own nomenclature, linked to the standard terms: "'variation intervals'
compared to _confidence intervals_ or _credible intervals_" (`../notes/v1/ema-redesign.md`, "Glossary";
`../notes/v1/lessons_learned_2026-09-27.md` §12). `../design/purpose.md` uses "variability intervals".

`../design/architecture.md` §3 names the field `Estimate.interval`, and says the term decides that name and the
words in reports.

## Decision

We will call the interval attached to every estimate a **variability interval**.

A variability interval shows how much an estimate changes when the runs behind it change: when they are
resampled, when the design is refined, or when some runs are held out. The interval's method, and its
settings (such as the number of resamples and the percentiles), are always reported with it. It measures
how much the estimate depends on the runs the diagnostic used. It is not a statement about uncertainty in
the model, its parameters, or the system the model represents. It is not a confidence interval or a
credible interval: it carries no coverage probability, even when its method is one that makes confidence
intervals under assumptions EMA doesn't check.

- **In documents, reports, and messages,** the term is "variability interval". "Confidence interval", "CI",
  "credible interval", and "error bar" are not used for EMA's intervals, except to explain the difference.
- **In code,** the short form `interval` is used, as in `Estimate.interval` and `ema.numerics.intervals`.
- **In figures,** the bars drawn for intervals are labeled as variability intervals, with their method.

## Alternatives considered

- **Variation interval:** the owner's earlier term (`../notes/v1/ema-redesign.md`). The term "variability" is
  preferred because it indicates that the estimate is able to vary over a range of values depending on 
  parameters of the estimation method such as the number of design points. The term "variation" is more vague.
- **Confidence interval:** familiar to every reader, but it promises a coverage probability that most of
  EMA's methods don't give, and the convergence method has no probability model at all.
- **Credible interval:** Bayesian; EMA has no prior or posterior.
- **Uncertainty interval, or error bar:** too easily read as uncertainty in the model's predictions, or as an
  error, which is what EMA is not (`../design/purpose.md`: "not an uncertainty quantification software
  package").
- **Plain "interval":** short, but it says nothing about what the interval means. It is kept as the short
  form in code.

## Consequences

- **Glossary:** the row "variation interval (OD-4)" becomes "variability interval", with this definition,
  linked to confidence, credible, and bootstrap intervals; the Avoid column lists "confidence interval", "CI",
  and "error bar".
- **`../design/uncertainty.md`:** its section "What an interval means in EMA" takes this definition, and
  says for each method what it varies.
- **`STATUS.md`:** OD-4 moves to "Decided", naming this record.
- **`../design/architecture.md`:** the open item in §3 and the row in §12 are closed; `Estimate.interval` keeps
  its name, and `Estimate` records the method and its settings.
- **Reports and figures** have to say, near every interval, which method made it. The report template, and
  the mock reports in the diagnostic specs, show where.
- **A terminology test** checks that EMA's own text doesn't call its intervals confidence intervals.
- **Users who know statistics** may still read the intervals as confidence intervals. The first report a user
  sees, and the get-started guide, have to explain the difference.
