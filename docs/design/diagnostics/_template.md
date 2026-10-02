# <Diagnostic name>

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Module:** `ema/diagnostics/<name>.py`.

> Copy this file to `<name>.md` for each diagnostic in v2.0 (OD-5). The five-row table is the one from
> `../../notes/v1/ema-redesign.md`. Every other section makes the table precise enough to test. Draw the mock report by
> hand first: if the report isn't what you'd want to read, change the table.

## Summary

| | |
|---|---|
| **User provides** | <parameters, with defaults> |
| **Design** | <generator from `../designs.md`, and its settings> |
| **Compute** | <what is computed, from which runs> |
| **Plots** | <each figure: what's on each axis> |
| **Report** | <the numbers, with intervals, and the notes> |

## Parameters

| Name | Type | Default | Meaning | Changes the design? |
|---|---|---|---|---|
| <…> | <…> | <…> | <…> | <yes or no> |
| `seed` | integer ≥ 0 | 0 | <its draws; or "recorded; no random draws"> | <yes or no> |

## Computation

> The formulas, with references. What is computed from which runs. How failed runs are handled.

<…>

## Uncertainty

> The interval method for each estimate (`../uncertainty.md`, OD-12), and what the report says when there is
> none.

<…>

## Minimum runs and degenerate cases

- **Fewest usable runs for any number:** <…>
- **All runs failed:** <counts and a note; no numbers>
- **Constant model prediction:** <…>
- **<Other cases from `../contracts.md`>:** <…>

## Figures

> For each figure: its panels, axes and labels (with units), what is drawn for failed runs, and what goes in
> its data card.

<…>

## Mock report

> By hand: exactly what the report section looks like for one reference model (from `../reference_models.md`),
> with real or plausible numbers. This is the target.

```markdown
<…>
```

## Expected answers

> For each reference model this diagnostic will be tested on: the values the result must contain, with
> tolerances, and where they come from (analytic, literature, brute force).

| Reference model | Quantity | Expected | Tolerance | Source |
|---|---|---|---|---|
| <R1> | <…> | <…> | <…> | <…> |

## Named constants

| Name | Value | Meaning | Why this value |
|---|---|---|---|
| <…> | <…> | <…> | <…> |
