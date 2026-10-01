# 0029. Say what the model version covers, and check it before every call

**Date:** 2026-09-30. **Status:** accepted; its list of what is not covered amended by 0057 (`pass_env` values). **Resolves:** none (TODO step 4; the open platform question in
0015).

## Context

P3 (accepted): "Everything that decides what a run does (the model's spec, the contents of its files, and the
point) is part of the run's key and of its approval." The model version hash "covers the spec and the
contents of every file the model reads". Records 0020 and 0025 already leave two settings out of the model
version, `keep` and `batch_size`, since they don't decide what a run computes; record 0024 puts limits in.

v1 hashed the spec without its location and without each input's scale, plus the contents of its tracked
files (the function's source, templates, static and data files, a python parser's source, and command
arguments naming files in the model's directory). It did not cover modules the function imports, installed
packages, or programs found on `PATH` or given by an absolute path; its guide suggested a version string in
the description as a workaround (`../../../EMA-v1/docs/guides/input_deck_model.md`, "When is it a new
model?"). v1 re-hashed the model before each diagnostic.

Record 0015 left open whether one model on two machines (a binary built for each) is one model version.

U6 needs a run refused when a tracked file changed since the model was loaded, with the file named. A
timed-out run is failed, and reused unless the user asks to retry (0010).

## Decision

- **The spec, but not its settings.** The version hash covers the whole model spec except its location and
  three settings that don't decide what a run computes: `keep` (0020), `batch_size` (0025), and `timeout_s`.
  A timed-out run is run again with `retry_failed` (0010), not with a new model version. Descriptions, units,
  and nominal values are covered: editing one makes a new model version, and each stored diagnostic result
  keeps the labels it was made with (P4, U8).
- **Tracked files:** the Python function's file, the input deck templates, and the files the spec lists. At
  loading, EMA reads the function file's imports, and warns about each that resolves to a file in the model's
  directory that the spec doesn't list.
- **Not tracked:** modules found elsewhere, installed packages, and programs found on `PATH` or given by an
  absolute path. Each run records the resolved path of its command's program and its host (0015); the first
  approval for a model version shows the path (U2).
- **The platform question (0015), for v2.0:** follows from what is tracked. A program copied as a model file
  is tracked, so a build for another platform is another model version; a program outside the model's files
  isn't, so the model is one version on every machine.
- **Checked before each call.** The tracked files are hashed in full before every call (a run, or a batch,
  0025). A call whose model version no longer matches is refused, naming the file that changed (U6).
- **Moving** the model's directory doesn't change the model version (M3).

## Alternatives considered

- **Only the fields that decide a run** (leaving out descriptions, units, and nominal values): edits to labels
  keep the runs, but one model version then has several specs, and each diagnostic result must store which
  one's labels it used.
- **Everything, the timeout too:** the simplest rule, but raising the timeout to rescue timed-out runs would
  discard every good run.
- **Refuse unlisted local imports:** stricter for P3, but a helper that is deliberately untracked couldn't be
  used.
- **Track the whole model directory:** nothing forgotten, but a log or a plot written there makes a new
  version.
- **Hash the resolved program too:** a recompiled system solver would make a new version, but `mpirun` or a
  wrapper script is hashed rather than the solver behind it, and one model is a different version on each
  machine.
- **A full hash per diagnostic evaluation, and sizes and times per call:** cheaper for large files, but a
  same-size edit within the file system's time resolution goes unseen (v1's `.pyc` lesson).

## Consequences

- **`../design/principles.md`** (accepted): P3's statement is unchanged; its "Enforced by" line gains "except
  the settings `keep`, `batch_size`, and `timeout_s` (0020, 0025, 0029)" after "The model version hash covers
  the spec".
- **`../design/model_interface.md`:** the Versions section.
- **`../design/data_model.md`** (step 8): a model version stores its spec; the settings are stored with the
  model, the latest loading's values applying; each run stores its program's resolved path and its host.
- **`../design/contracts.md`** (step 7): change one byte in a listed file, a template, or the function's file:
  a new model version. Change `timeout_s`, `keep`, or `batch_size`: the same one. An unlisted local import
  gives the warning. Editing a tracked file between two calls refuses the second, naming the file (U6).
- **Cost:** hashing takes about 1 s per GB of tracked files before each call.
- **The platform question** in 0015 is settled for v2.0; remote runs (later) may revisit it.
