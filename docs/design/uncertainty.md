# Uncertainty

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Depends on:** OD-4, OD-12.

> One page: the interval methods EMA uses, what each interval means, and which method each v2.0 diagnostic
> uses. Your `../notes/v1/diagnostic-notes.md` lists the candidates: bootstrap, refinement and convergence,
> cross-validation and resampling, held-out error.

## What an interval means in EMA

> In your words (OD-4): what a "variation interval" is, and how it differs from a confidence or credible
> interval. This is the text the reports and the glossary will use.

<…>

## Methods

| Method | What varies | Assumptions | Cost | Used by |
|---|---|---|---|---|
| bootstrap | <resamples of the runs> | <…> | <no new runs> | <…> |
| convergence | <successive refinements of the design> | <…> | <new runs per level> | <…> |
| cross-validation | <…> | <…> | <…> | <…> |
| held-out error | <…> | <…> | <…> | <…> |

## Rules

- <Every estimate carries its interval, its method, and its level.>
- <With no interval (too few runs, zero resamples), the report says so, and no claim is made that needs one.>
- <Resamples are seeded from the design's seed, so results are deterministic.>
- <…>

## Per diagnostic

| Diagnostic | Estimate | Method | Level | Default resamples or levels |
|---|---|---|---|---|
| <…> | <…> | <…> | <…> | <…> |
