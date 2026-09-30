# 0031. Add "run directory" to the glossary, and say in P3 which files the model version covers

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 4; wording that follows 0015, 0020,
0028, 0029, 0030).

## Context

Records 0015, 0020, 0028, and 0030, and `../design/model_interface.md`, use "run directory" throughout: the
directory a run is prepared, executed, and collected in. The glossary (accepted) has no row for it. v1 called
it the `workdir`.

P3's "Enforced by" (accepted) says the model version hash covers "the contents of every file the model reads".
Record 0029 decided otherwise: the hash covers the files the model spec names (the Python function's file,
the input deck templates, and the listed files), and not modules found elsewhere, installed packages, or
programs on `PATH` or given by an absolute path; loading warns about an unlisted local import. Read literally,
P3 promises more than EMA checks.

## Decision

- **Glossary:** a row for **run directory**: "the directory a run is prepared, executed, and collected in, at
  `<workspace>/runs/<run id>/`; it holds what the run saw and wrote (its input decks, its files, copied or
  linked, and its streams) and a record of the run, and is kept or deleted by the model spec's `keep` setting
  (0015, 0020, 0028, 0030)". Standard terms: working directory, scratch directory. Avoid: workdir.
- **P3's "Enforced by":** "and the contents of every file the model reads (`model_interface.md`)" becomes "and
  the contents of every file the model spec names: the Python function's file, the input deck templates, and
  the listed files; modules found elsewhere, installed packages, and programs outside the model's files are
  not covered, and each run records its program's path (`model_interface.md`, 0029)". P3's statement is
  unchanged.

## Alternatives considered

- **Leave P3 as written:** shorter, but it claims a check EMA doesn't make; a user reading it would expect an
  edited installed package to make a new model version.
- **No glossary row:** "run directory" is plain enough, but it is a public idea (the lookup, 0020; `keep`), and
  v1's `workdir` would creep back into names.

## Consequences

- **`../design/glossary.md`** (accepted): the row above, after "run".
- **`../design/principles.md`** (accepted): P3's "Enforced by" as above.
- **The terminology test** (0008) doesn't change; "workdir" joins its list only if a later record decides so.
