# 0030. Store large model files once, read-only, and link them into run directories

**Date:** 2026-09-30. **Status:** accepted. **Resolves:** none (TODO step 4; the model's files).

## Context

A model spec lists the files a run needs: a solver binary, a configuration file, a mesh. The draft of
`../design/model_interface.md` copies each into every run directory, keeping their relative paths, so a run
directory is self-contained (0015's *prepare*: "builds a self-contained run directory (the input deck, the
model's files, the command)"), and a kept one shows what its run read (0020).

A simulation code may read a very large file that doesn't change between runs, such as a fine mesh of
gigabytes. Copying it into every run directory costs its size in disk per kept run, and about 1–2 s per GB of
copy time per run. v1 copied its static files into every run directory, and had a built-in `EMA_BASE_DIR` for
templates that named files in the model's directory instead.

Record 0029 hashes every tracked file in full before each call, whichever way it reaches the run.

## Decision

We will let the model spec mark a listed file as shared. A shared file is stored once, read-only, and linked
into each run directory. Unmarked files are copied, as before. The rule is the same for both kinds of model.

- **Marked in the spec:** `{"path": "mesh.dat", "shared": true}` in the list of files. `shared` is part of
  the model version (0029), since it changes what a run directory holds.
- **Stored once:** before the first run that needs it, EMA copies the file into the workspace at
  `<workspace>/files/<sha256>/<name>`, named by its contents, and makes the copy read-only. Two model
  versions with the same file share one copy.
- **Linked:** *prepare* makes a symbolic link at the file's relative path in the run directory, pointing to
  the stored copy. The program reads the file under its usual name.
- **Never changes:** a stored copy is never written. Editing the source file makes a new hash, a new model
  version (0029), and a new copy, so a kept run directory still points to the file its run read (0020).
- **Read-only for the model:** a program or function that tries to write to a shared file gets a permission
  error, and its run fails with that reason.
- **Deleting** stored copies is by hand, like run directories (0020); a run directory whose shared file was
  deleted has a dangling link, and EMA needs neither to reuse a stored run.

0015's self-contained run directory now reads: self-contained, or linked to read-only copies in the
workspace.

## Alternatives considered

- **Copy every file (the draft):** one rule, but a large file costs its size per kept run and its copy time
  per run.
- **Share every file:** the least disk, but a program that edits one of its input files in place fails, and a
  kept run directory is mostly links.
- **Read in place** (`${EMA_MODEL_DIR}/mesh.dat` in a template, like v1's `EMA_BASE_DIR`): the cheapest, but
  the run directory isn't self-contained, a kept one doesn't show what its run read, and a later executor on
  another machine can't use it.
- **Link to the file in the model's directory:** no copy at all, but an edit to the source changes what every
  kept run directory shows, and a program could write to the model's own file.

## Consequences

- **`../design/model_interface.md`:** the command-line and Python function sections list files, copied or
  shared; the run directory holds links to shared files.
- **Record 0015** (accepted) is refined, not superseded: *prepare* builds a run directory that is
  self-contained, or linked to read-only copies in the workspace.
- **`../design/data_model.md`** (step 8): the stored copies under `<workspace>/files/`, named by hash.
- **`../design/trust.md`** (step 10): EMA writes stored copies read-only, and never follows a link out of a
  run directory when it reads model output.
- **`../design/contracts.md`** (step 7): a shared file is copied once for many runs; a run that writes to it
  fails with a permission error; editing the source makes a new model version and a new copy, and the old
  run directories still point to the old one.
- **Later remote runs** (0015) copy each stored file once per machine, and link it the same way.
- **Size:** about 40–60 source lines and their tests.
