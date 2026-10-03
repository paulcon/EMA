# 0069. Step 03's provisional choices: the model spec's JSON form, loading, and the model's files

**Date:** 2026-10-02. **Status:** accepted (2026-10-02, by the owner; drafted as proposed under 0066). **Resolves:** none.

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
6. **Names:** model parameter and model prediction names are ASCII Python identifiers that aren't keywords (soft
   keywords such as `match` are allowed; ASCII since review round 1, item 26); a model's name is `[a-z0-9_-]+`;
   the `ema_` prefix is matched as written (M21).
7. **Refuse, beyond the specs' list:** a path listed twice in `files`; a deck's `writes` written by two decks, or
   onto a listed file (compared case-folded, and as directories, since review round 1, item 31); a `pass_env` name
   twice; `gt` with `ge`, or `lt` with `le`. The function's file or a
   template may also be listed in `files`; it is tracked once, with the listed entry's `shared` mark.
8. **Check each parser at loading:** a regex compiles, with one group or a group named `value`, and `match` is
   `first` or `last`; a JSON key has no empty part; a CSV `column` is a non-empty header or an integer, `row` an
   integer, and `delimiter` one character; a parser's `file` is `stdout`, `stderr`, or a relative path.
9. **EMA's own file names** (`EMA_FILE_NAMES`) are compared case-folded against the whole of a deck's `writes` or a
   listed file's path, and (since review round 1, item 31) against its first part, as a case-insensitive file
   system would; `out/run.json` loads, `run.json/x` doesn't.
10. *(Reversed in review round 1: credentials-file names are now refused on every path in a spec, a deck's
    `writes` and a parser's `file` included; see item 27.)*
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

14. **`load_spec` keeps the spec's path as given** (made absolute, nothing normalized) for messages, and takes the
    model's directory from the spec's file with its links resolved (`dirname(realpath(path))`); a link to the
    spec, from any directory, or to its directory, is the same model version (C33). *(Corrected in review round 1,
    item 29: the first version took the model's directory from the path as given, so a link to the spec from
    another directory failed to load.)*
15. **`hash_files` refuses,** naming the field: a missing file (a dangling link included), one that isn't a regular
    file (a directory, a FIFO), one whose link leads to a credentials file, and two entries that are one directory
    entry (two spellings of one name, item 30); fields are taken in the spec's order, so the later entry is named. A link's target is matched below the model's directory when it
    lies there, and whole when it doesn't (trust.md, Paths).
16. **`same_file` asks the file system of the nearest existing directory whether it is case-insensitive** (item 28:
    `pathconf`'s `_PC_CASE_SENSITIVE` on macOS, else a probe of an entry inside that directory, else of its own
    name and its parents'); with no letters anywhere, it compares case-sensitively. `is_within` compares each ancestor of
    the resolved path with the directory by `same_file`. Both accept path-like arguments.
17. **A function file that doesn't parse is refused at loading** (`SpecError` naming `function`), since every run
    would fail; it is still never imported.
18. **M17 resolves** `import a.b` to `a.py`, `a/__init__.py`, `a/b.py`, `a/b/__init__.py`, against the model's
    directory only (item 34); `from a import x` also tries `a/x.py`; a relative import resolves from the file's
    directory; a candidate outside the model's directory is ignored. One warning per file, in source order (by
    line and column; the first version said `ast.walk`'s order was the source's, which it isn't for an import
    inside a function), naming the file and the import.
19. **M10 at loading:** a template that isn't UTF-8 text, a `$` that isn't `$name`, `${name}`, or `$$`, and a
    name that isn't a model parameter, each refused naming the field, the template, and the line.
20. **`save_spec` raises `PathRefused`** (not `SpecError`: it is about the path) for a name not ending in `.json`
    (in any case, item 36), a directory that doesn't exist, a link to nothing, an existing file with other bytes
    or that isn't a regular file, and a file or a link that appears at the path before the exclusive create; with
    the same bytes it writes nothing. It raises `SpecError` when `from_json` refuses the text it would write.
21. **`check_files` raises `ModelChanged`** naming the model version's label, the first file that changed, is gone,
    or is no longer a regular file, and "load the model again for a new model version".
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

**Review round 1** (the independent review's findings, with the coordinator's rulings)

26. **Model parameter and model prediction names are ASCII identifiers** (`[A-Za-z_][A-Za-z0-9_]*`, not a
    keyword), a provisional clarification of model_interface.md's Names: Python reads a non-ASCII identifier in
    its NFKC form, so `µ` (U+00B5) is `μ` (U+03BC) and `ﬁ` is `fi` to it, and `f(**{"µ": 1})` would fail after the
    runs were approved and paid for; `string.Template`'s names are ASCII too. A refusal says "ASCII". A function's
    name (`file.py:f`) may stay non-ASCII, but must be its own NFKC form (`ﬁt` is refused, naming `fit`), since
    `def ﬁt` defines `fit`.
27. **Credentials-file names are refused on every path a spec names** (reverses item 10): the spec's own path, the
    function's file, the templates, `files`, a deck's `writes`, and a parser's `file` (not the streams `stdout`
    and `stderr`), following model_interface.md's broader wording (The model spec, bullet 2: "A credentials file
    …, named directly or reached through a link, is refused") and T7.
28. **The case probe asks the right file system** (T1): the nearest existing *directory* of a path that doesn't
    exist, since the next part's name lies on that directory's file system (a mount point's own name lies on its
    parent's). On macOS it asks `pathconf(directory, _PC_CASE_SENSITIVE)` (in `os.pathconf_names` where Python
    lists it, else Darwin's number, 11); elsewhere, or when `pathconf` can't say, it probes an entry inside the
    directory (`os.scandir`, the first whose name has letters), and only with none, the directory's own name and
    its parents'.
29. **The model's directory is the spec's, its links resolved** (corrects item 14).
30. **Two entries are refused as one file only when they are one directory entry:** the same file by `os.lstat`
    (device and inode, the link itself for a link), in the same directory, with names equal NFC and case-folded.
    A link beside its target, and two hard links, are two entries (each is copied into the run directory by its
    own name).
31. **Run-directory paths are compared case-folded and as directories:** `files` among themselves, and each deck's
    `writes` against `files` and the decks before it, are refused when equal case-folded (`Plate.in` and
    `plate.in`), or when one is a directory of the other (`out` and `out/mesh.dat`), since a run directory can't
    hold both. EMA's own names are refused as the first part too (item 9).
32. **Only regular files are read,** opened without blocking (`O_NONBLOCK`, then `fstat`), so a FIFO or a device
    named as the spec, a tracked file, or the save path is refused (`SpecError`, `PathRefused`), never waited on;
    a tracked file that becomes one is a `ModelChanged`. `ema.models.files.open_regular` does this for both modules.
33. **Every failure of the reader is a `SpecError`:** an integer too large for a double (`OverflowError`, caught in
    `ema.types._values`, refused as not finite or not an integer), a spec nested too deeply for the parser
    (`RecursionError`), and a function file that `ast.parse` can't parse for a null byte, a parser overflow
    (`MemoryError`), or depth (`RecursionError`), naming the field or the file. `NaN` and `Infinity` are kept by
    the parser until their field is known, and refused naming it (`timeout_s: NaN is not a number …`).
34. **M17 resolves module names against the model's directory only,** matching trust.md's Python function bullet
    (the child's `sys.path` is the model's directory first, then EMA's); the function file's own directory isn't on
    it. A relative import still resolves from the file's directory, as when the file is imported as a module of
    its package. **For step 05:** start the child with the model's directory first on `sys.path`, and don't add the
    function file's own directory; if step 05 imports a function file in a subdirectory as a dotted module
    (`sub.model`), relative imports work and agree with this check; if it imports it by its file's location, they
    fail at run time, and this check should then stop resolving them.
35. **A parser's `file` of `./stdout` or `./stderr` is refused** as ambiguous with the stream (`stdout` and
    `stderr` as written are the streams).
36. **`save_spec`** accepts `.JSON` in any case, names a link to nothing as such, and reads its text back with
    `ModelSpec.from_json` before writing, so a spec built in Python that loading would refuse is never saved.
37. **`ema.models.files.leads_to_credentials` and `open_regular` are public** (not re-exported by `ema.models`),
    since `spec.py` uses them; no private name crosses modules.

The size budget (the review's item 10) is the coordinator's.

## Questions for the owner

- **A model's name like `-rf`** loads (`[a-z0-9_-]+`); a name starting with `-` could read as an option where a
  later step passes it on a command line (the CLI's arguments). Should a model's name start with a letter or a
  digit?
- **The order of `files` and of `pass_env`** is in the model version as written: listing the same files, or the
  same variables, in another order is a new model version. Should either be sorted before hashing (as tracked
  files' digests already are)?

## Deferrals

None of the step's ids. The question text of T7 and T8 is step 07's; T5's root check (with `is_within`) is step 14's;
C34 is finished by the runner (step 07).

## Spec edits on acceptance

- **`model_interface.md`, The model spec, Names:** "Model parameter and model prediction names are ASCII Python
  identifiers (`[A-Za-z_][A-Za-z0-9_]*`, not a keyword)" (item 26).
- Clarifications that would help later readers: `architecture.md` §3, `types/model.py`'s public names
  (`CREDENTIAL_WORDS`, `EMA_FILE_NAMES`, `hidden_character`, `is_credentials_file`), and §5, the errors `save_spec`
  raises (item 20) and `files.py`'s `leads_to_credentials` and `open_regular` (item 37).

## Alternatives considered

- **`to_json` as canonical JSON:** one line, sorted keys; unreadable in a confirmation and a saved file.
- **No credentials-name checks on `writes` and a parser's `file`** (the first version, item 10): they name files
  inside the run directory; reversed in review, since model_interface.md's wording covers every path in a spec.
- **Taking the model's directory from the spec's path as given** (the first version, item 14): a link to the spec
  from another directory then failed to load, its files looked for beside the link.
- **Non-ASCII names that are their own NFKC form:** would work as keyword arguments, but not in templates
  (`string.Template` names are ASCII), and the rule would be harder to state.
- **Warning, not refusing, a function file that doesn't parse:** every run would fail with the same error.

## Consequences

- **Size:** code lines (without docstrings, comments, blank lines, and re-exports): `ema.types.model` 553, of
  which 443 are this step's (the trust lists and their two functions about 60, `from_json`'s reader about 330,
  `to_json`'s writer about 50) against §11's about 275 for the spec's validation and trust's checks; `identity.py`
  6; `_values.py` +5; `ema.models` 302 (`spec.py` 142, `files.py` 148, `__init__.py` 12). Step 03 is about 755
  lines against the roadmap's 450 (665 before review round 1, which added about 90: the case probe, regular
  files, the entry check, and the run-directory overlaps): over by about 305, mostly the reader's field paths and refusals (each field named, as
  `architecture.md` §3 asks) and the parsers' checks. The budget record is the coordinator's to propose; the
  reader could be shortened by a table-driven schema, at some cost in the messages' precision.
- `tests/contracts/model.py` exists; steps 04 and 05 add C31, C32, C34–C45 to it.
