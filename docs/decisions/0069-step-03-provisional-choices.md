# 0069. Step 03's provisional choices: the model spec's JSON form, loading, and the model's files

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Build step 03 (`../plans/03-model-specs.md`) was built on `demo-03-model-specs` without the owner's review (0066):
`ModelSpec.from_json`, `to_json`, `versioned_json`; `version_hash`; `ema.models.spec` (`LoadedModel`,
`load_spec`, `stored_model`, `save_spec`) and `ema.models.files` (`hash_files`, `same_file`, `is_within`,
`check_files`); C33. The specs (`../design/model_interface.md`, `../design/trust.md`, `../design/architecture.md`
§3 and §5, `../design/data_model.md` §3.4, `../design/contracts.md`) leave some details open. Each choice below
keeps P1–P7 and the specs' intent, and changes no accepted rule. v1's `agent/approval.py` (`is_secret`) and its
tests were read; the lists were rewritten, not copied.

## Decision

We will, provisionally:

**The JSON form (`ema.types.model`)**

1. **Write `to_json` indented** (2 spaces, the field table's order, a final newline, non-ASCII kept), since it is
   the text `save_spec` writes and a confirmation shows (T6); `versioned_json` is the canonical JSON of the same
   object without `keep`, `batch_size`, and `timeout_s`, and `version_hash` embeds it as an object.
2. **Write every key in `to_json`:** `batch_size` (`null` by default), `limits` (`{}` when none), `files` as
   `{"path", "shared"}`, a parser with its defaults; a Python function's spec has no `command` or parser keys, and
   a command-line model's no `function` or `batch`. `from_json` reads it back equal.
3. **Normalize paths when read:** empty and `.` parts dropped, so `./mesh.dat` and `mesh.dat` are one model
   version (M3's "a default written out or left out"). An absolute path, a `..` part, or an empty path is refused.
4. **Refuse each field of the other interface** (`function` and `batch` on a command-line model; `command` and
   `input_decks` on a Python function) as an unknown key, and `batch_size` (other than `null`) on a model that
   isn't a batch function; `batch_size` reads an integral float as an integer (0067 item 8).
5. **A function is `file.py:f`:** the file a relative path ending in `.py`, `f` an identifier that isn't a keyword.
6. **Names:** model parameter and model prediction names are Python identifiers that aren't keywords (soft
   keywords such as `match` are allowed); a model's name is `[a-z0-9_-]+`; the `ema_` prefix is matched as written
   (M21).
7. **Refuse, beyond the specs' list:** a path listed twice in `files`; a deck's `writes` written by two decks, or
   onto a listed file; a `pass_env` name twice; `gt` with `ge`, or `lt` with `le`. The function's file or a
   template may also be listed in `files`; it is tracked once, with the listed entry's `shared` mark.
8. **Check each parser at loading:** a regex compiles, with one group or a group named `value`, and `match` is
   `first` or `last`; a JSON key has no empty part; a CSV `column` is a non-empty header or an integer, `row` an
   integer, and `delimiter` one character; a parser's `file` is `stdout`, `stderr`, or a relative path.
9. **EMA's own file names** (`EMA_FILE_NAMES`) are compared case-folded against the whole of a deck's `writes` or a
   listed file's path, as a case-insensitive file system would; `out/run.json` loads.
10. **Credentials-file names are checked on the fields `trust.md` lists:** the spec's own path, the function's file,
    the templates, and `files`; a deck's `writes` and a parser's `file` (inside the run directory) are not.
11. **The credentials-file lists** (`is_credentials_file`, rewritten from v1's): `.env`, `*.env`, and `.env.*` but
    `.env.example`, `.env.sample`, `.env.template`; login, token, SSH key, shell start-up, and history files by name;
    `credential(s)` or `secret(s)` as a word part split at `.`, `_`, `-`; the suffixes `.pem`, `.p8`, `.p12`,
    `.pfx`, `.ppk`, `.jks`, `.keystore`, `.kdbx`, `.gpg`, `.tfvars` (not `.key`); the directories `.ssh`, `.aws`,
    `.azure`, `.gnupg`, `.docker`, `.kube`, `.password-store`, `.config/gcloud`, `.config/gh`, `.config/op`. v1's
    `identity` and `.claude.json` names are left out (ordinary names in a model's directory).
12. **`hidden_character`, `is_credentials_file`, `CREDENTIAL_WORDS`, and `EMA_FILE_NAMES` are public** in
    `ema.types.model` (and re-exported by `ema.types`), for `ema.models`, `ema.approval`, and the workspace's root
    check; the other lists are private.
13. **Messages:** a `SpecError` names its field as a path (`parameters[0].limits.gt`, `env.PATH`, `files[1]`); a
    hidden character as `U+202E`, and a key holding one by its `ascii()` form; `load_spec` puts the spec's path
    first. A duplicate key is found by an `object_pairs_hook` that remembers it, so it is reported with its path;
    `NaN` and `Infinity` in the text are refused; a number that overflows to infinity is refused as not finite.

**Loading and files (`ema.models`)**

14. **`load_spec` keeps the spec's absolute path as given,** links not resolved, so the model's directory is the
    one the user named; a link to the spec, or to its directory, is the same model version (C33).
15. **`hash_files` refuses,** naming the field: a missing file (a dangling link included), one that isn't a regular
    file (a directory), one whose link leads to a credentials file, and two entries that are one file (by device
    and inode, so a link and its target, or two spellings on a case-insensitive file system); fields are taken in
    the spec's order, so the later entry is named. A link's target is matched below the model's directory when it
    lies there, and whole when it doesn't (trust.md, Paths).
16. **`same_file` probes case-sensitivity** by swapping the case of the nearest existing path component that has
    letters, and asking `samefile`; with none, it compares case-sensitively. `is_within` compares each ancestor of
    the resolved path with the directory by `same_file`. Both accept path-like arguments.
17. **A function file that doesn't parse is refused at loading** (`SpecError` naming `function`), since every run
    would fail; it is still never imported.
18. **M17 resolves** `import a.b` to `a.py`, `a/__init__.py`, `a/b.py`, `a/b/__init__.py`, against the model's
    directory and the function file's own; `from a import x` also tries `a/x.py`; a relative import resolves from
    the file's directory; a candidate outside the model's directory is ignored. One warning per file, in the
    order the imports appear (`ast.walk`), naming the file and the import.
19. **M10 at loading:** a template that isn't UTF-8 text, a `$` that isn't `$name`, `${name}`, or `$$`, and a
    name that isn't a model parameter, each refused naming the field, the template, and the line.
20. **`save_spec` raises `PathRefused`** (not `SpecError`: it is about the path) for a name not ending in `.json`,
    a directory that doesn't exist, an existing file with other bytes, and a file or a link that appears at the
    path before the exclusive create; with the same bytes it writes nothing.
21. **`check_files` raises `ModelChanged`** naming the model version's label, the first file that changed or is
    gone, and "load the model again for a new model version".
22. **`stored_model`** sorts the files by path and computes the model version from the spec and files it is given,
    reading no file; its warnings are empty.
23. **`ema/models/__init__.py` re-exports** `spec.py`'s and `files.py`'s public names; the AST test checks that
    it imports no module named `execute`, with a negative control.

**Tests**

24. **The test models** are in `tests/models/` (`python`, `batch`, `command_line`, `imports`), out of pytest's
    collection (the root `conftest.py`); `tests.support.models.copy_model` copies one into a temporary directory.
25. **The model adapter contract's implementation** is `Adapter(kind, load)`, a test model and how it is loaded;
    steps 04 and 05 add to it. C33's three broken toys hash the files' paths (contracts.md's negative control),
    cover the settings, and cover the model's directory; each was checked to fail for its own reason.

## Deferrals

None of the step's ids. The question text of T7 and T8 is step 07's; T5's root check (with `is_within`) is step 14's;
C34 is finished by the runner (step 07).

## Spec edits on acceptance

None is required. Clarifications that would help later readers: `architecture.md` §3, `types/model.py`'s public
names (`CREDENTIAL_WORDS`, `EMA_FILE_NAMES`, `hidden_character`, `is_credentials_file`), and §5, the errors
`save_spec` raises (item 20).

## Alternatives considered

- **`to_json` as canonical JSON:** one line, sorted keys; unreadable in a confirmation and a saved file.
- **Credentials-name checks on `writes` and a parser's `file` too:** they name files inside the run directory,
  which EMA writes or reads there only; refusing them stops nothing.
- **Resolving the spec's path through links:** would make the model's directory the target's, which the user
  didn't name, and would change which files are tracked when a spec is a link.
- **Warning, not refusing, a function file that doesn't parse:** every run would fail with the same error.

## Consequences

- **Size:** code lines (without docstrings, comments, blank lines, and re-exports): `ema.types.model` 530, of
  which 420 are this step's (the trust lists and their two functions about 60, `from_json`'s reader about 310,
  `to_json`'s writer about 50) against §11's about 275 for the spec's validation and trust's checks; `identity.py`
  6; `ema.models` 239 (`spec.py` 129, `files.py` 98, `__init__.py` 12). Step 03 is about 665 lines against the
  roadmap's 450: over by about 215, mostly the reader's field paths and refusals (each field named, as
  `architecture.md` §3 asks) and the parsers' checks. The budget record is the coordinator's to propose; the
  reader could be shortened by a table-driven schema, at some cost in the messages' precision.
- `tests/contracts/model.py` exists; steps 04 and 05 add C31, C32, C34–C45 to it.
