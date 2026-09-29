# 0009. Call the models with known answers reference models

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** none (TODO step 1, the glossary's review).

## Context

EMA's specs call the models with known answers, used to test EMA and loaded by users as examples, "sample
models" (ids S1, S2, …, in `../design/sample_models.md`). The word "sample" already means two other things in
the glossary: it is a standard term for a design (a set of points) and for a run (one evaluation), and
`../design/purpose.md` speaks of "sampling the model". A reader of "sample model" may take it for a model
that samples, or a sampled model.

The name appears in the accepted P4, P6, and P7 (their "Tested by" lines), in CLAUDE.md, in the proposed
record 0002, in `README.md`'s id scheme, in `TODO.md` step 11, and in the skeletons of `contracts.md`, the
diagnostic template, and the get-started guide, which has the user load one (S2, Ishigami).

## Decision

We will call a model with known answers, used to test EMA and as an example for users, a **reference model**.

- **Ids:** R1, R2, …, replacing S1, S2, …. The prefix R is not otherwise used.
- **File:** `docs/design/sample_models.md` becomes `docs/design/reference_models.md`.
- **Glossary:** a row for "reference model": a model with known answers, used to test EMA's diagnostics and as
  an example for users (`reference_models.md`). "Sample" stays a standard term for a design and a run.

## Alternatives considered

- **Keep "sample model":** no change, but "sample" keeps three meanings.
- **Benchmark model:** familiar from test-function libraries (Ishigami, borehole), but it suggests
  performance measurement to some readers.
- **Test model:** clear in tests, but odd for a user loading an example; and T is taken by trust-boundary ids.
- **Known-answer model:** the most literal, but long.
- **Keep the prefix S:** fewer edits, but the id would no longer match the name.

## Consequences

- **`../design/principles.md`:** the "Tested by" lines of P4, P6, and P7 say "reference models" and "a noisy
  reference model". No principle's statement changes.
- **`../design/sample_models.md`** is renamed `../design/reference_models.md`; its title, and its ids S1–S9,
  become R1–R9.
- **`../../README.md`:** the id row "S | sample model" becomes "R | reference model", and the file list
  changes.
- **`../../CLAUDE.md`:** "running it on a sample model" becomes "running it on a reference model".
- **`../../TODO.md`** step 11 and **`../../STATUS.md`**'s spec table use the new name and file.
- **`../design/contracts.md`**, **`../design/diagnostics/_template.md`**, and
  **`../guides/get_started.md`** use the new name and ids (the guide: "Load a reference model (R2,
  Ishigami)").
- **Record 0002** (proposed) says "against the reference models".
- **`../notes/`** is not changed: notes are background, in the words of their time.
