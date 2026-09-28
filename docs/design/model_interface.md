# Model interface

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Depends on:** OD-3, OD-6, OD-9, OD-10, OD-11, OD-20.

> The hardest thing to change later. This spec says what a model is to EMA: what it takes, what it returns,
> how it fails, and what makes a new version. `architecture.md` §3 and §5 have stubs for
> `ModelParameter`, `ModelSpec`, `Model`, and the adapters. The questions are from your 2026-09-23 notes.

## What a model takes

> The parameters (name, units, description, nominal value, scale, constraint), fixed parameters (OD-10),
> and anything else a run needs (files, environment).

<…>

## What a model returns

> Outputs: names, units, shapes (OD-9). What happens when one output fails and the others don't.

<…>

## Interfaces

### Python function

> How the function is found (`file.py:f` or `package.module:f`), how it is called (one point, or a batch
> if `parallel`), and whether it runs isolated (OD-11).

<…>

### Command line

> The input-deck template, the command, the run directory, the output parsers (OD-20), the timeout, and
> what the program is told (environment, replicate).

<…>

## Failures

> How a failed run is recorded, and how the analyst learns why (your "any way to get an explanation for
> failures?"): the exception, the exit code, stderr, a missing output file.

<…>

## Versions

> What the version hash covers (the spec without its location, and the tracked files) and what it doesn't
> (modules the model imports, installed packages, absolute-path programs). Where the box and scales live
> (in the design, not the spec).

<…>

## Requirements

> Numbered, so tests and code can cite them.

| Id | Requirement | Test |
|---|---|---|
| M1 | A failed run returns NaN outputs with a status and an error message; `evaluate` never raises for a bad point. | <…> |
| M2 | A command-line program gets stdin from `/dev/null` and no variable from `.env`. | <…> |
| M3 | Editing a tracked file changes the version; moving the model's directory doesn't. | <…> |
| M… | <…> | <…> |

## Open questions

- <…>
