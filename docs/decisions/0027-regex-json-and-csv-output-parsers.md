# 0027. Read model predictions with regex, JSON, and CSV output parsers

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** OD-20.

## Context

A command-line model's model predictions are read from its model output by output parsers (0003). v2.0's
model predictions are scalars (0021), and a model may have several (0022), each with its own parser.

v1 had four kinds (`../../../EMA-v1/src/ema/core/models/parsers.py`): `regex` (a pattern with one group, the
first or last match), `json` (a dotted key), `csv` (a column and a row), and `python` (a function
`parse(run_dir) -> float` in the model's files, run in an isolated child). Each reads a file in the run
directory, or the captured `stdout` or `stderr`. Only `python` runs user code. Scope lists `parsers.py` as
"rewrite, reading it", with only the kinds OD-20 chooses.

## Decision

We will support three output parser kinds in v2.0, each returning one scalar:

- **`regex`:** `file`, `pattern` (exactly one group, or a group named `value`), and `match` (`first` or `last`;
  default `last`).
- **`json`:** `file` and `key`, a dotted path whose integer parts index lists.
- **`csv`:** `file`, `column` (a header name or an index), `row` (default `-1`, the last), and an optional
  `delimiter`.

`file` is a path relative to the run directory, or `stdout` or `stderr`. A parser that can't find its file,
its match, or its key, or reads a value that isn't a finite number, makes that model prediction missing, with
a reason naming the parser and what it didn't find (0022).

A model output none of these reads is handled by the command itself: a wrapper script that runs the program
and writes the model predictions to a JSON file.

## Alternatives considered

- **Also `python` (v1):** any model output can be read, but it is a second kind of user code in a
  command-line model, with its own tracked file and isolated child. A wrapper script writing JSON does the
  same. Later: about 40 lines on 0026's child; nothing to prepare now beyond parsers chosen by kind.
- **Only `regex` and `json`:** one kind fewer, but a solver's convergence history in a CSV file would need a
  wrapper script.

## Consequences

- **`../design/model_interface.md`:** the command-line section lists the three kinds and their settings; the
  add-a-model guide shows the JSON wrapper.
- **`../design/contracts.md`** (step 7): each kind has known-answer tests, and a test for each way it can fail
  (no file, no match, no key, not a number, not finite).
- **Versions:** a parser's settings are part of the model version.
- **`../../STATUS.md`:** OD-20 moves to "Decided", naming this record, when it is accepted (0001).
