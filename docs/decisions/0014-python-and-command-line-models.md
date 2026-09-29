# 0014. Support Python functions and command-line simulation codes in v2.0

**Date:** 2026-09-29. **Status:** accepted. **Resolves:** OD-6.

## Context

`../design/purpose.md` (accepted) says the computational model "may be a Python function or an external
simulation code executed by command line and specified by an input deck". The accepted use cases need both: a
Python function in U1, U4, and U5, and a command-line simulation code with an input deck template and an
output parser in U2, U3, and U6.

v1 had three kinds of model: a Python function, a command line with an input deck template, and a formula
written in the model spec (`../../../EMA-v1/src/ema/core/models/expression.py`). Its model spec grew many
options, which the version hash then had to cover one by one (`../notes/v1/lessons_learned_2026-09-27.md`
§12).

## Decision

We will support two kinds of model in v2.0:

- **a Python function**, in a file the model spec names;
- **a command-line simulation code**, run in a run directory from an input deck template, with its model
  predictions read by an output parser.

v1's third kind, a formula in the model spec, is not in v2.0.

## Alternatives considered

- **A Python function only:** one adapter, but U2, U3, and part of U6 would go, and `purpose.md` would change.
- **A command line only**, with Python models behind a small command-line wrapper: one adapter, but U1's
  cheap path gets heavier, and each run pays for starting a process.
- **Also a formula:** no file to write for a one-line model, but it needs its own parser, and its own hashing
  and isolation rules. A formula is a one-line Python function, and the reference models are written as
  Python functions.

## Consequences

- **`../design/scope.md`:** the model interfaces row lists the two kinds; "Not in v2.0" lists formula models.
- **`../design/model_interface.md`** (step 4) specifies both, with OD-9, OD-10, OD-11, and OD-20.
- **`../design/architecture.md` §5:** `load_model` chooses between two classes.
- **`STATUS.md`:** OD-6 moves to "Decided", naming this record, when it is accepted (0001).
