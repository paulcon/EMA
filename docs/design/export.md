# Export

**Status:** empty. **Updated:** 2026-10-01. **Depends on:** 0050, U5, U8, P5.

> What `export` writes, so an analyst can use a diagnostic result's runs in another tool, and how reading it
> back gives the same values bit for bit. Written before the data model (TODO step 8), which stores what this
> spec reads (0050).

## What an export holds

> From U5: the runs a diagnostic result used, its design, and the diagnostic result with its provenance.

<…>

## Files and columns

> From U5: a CSV of runs and a JSON file (not `.npz`). For each: the file names, the columns or keys, the
> number format (full doubles, strict JSON, C17), and how a failed run and a missing model prediction appear.

<…>

## Reading it back

> U5's "Done when": reading it back gives the same model parameter values and model predictions, bit for bit.

<…>

## Requirements

| Id | Requirement | Test |
|---|---|---|
| <…> | <…> | <…> |

## What this spec asks of other documents

- **Data model (step 8):** <…>
- **Architecture (step 9):** `Workspace.export` and `ema export` (U5).
