# 03. Model specs and loading

**Status:** in progress (demo; record 0066); its choices are record 0069. **Branch:** `demo-03-model-specs`.
**Updated:** 2026-10-02.

## Goal

A model spec is read from its JSON file, checked (everything `trust.md` puts in `ema.types.model`, and what needs
files in `ema.models`), and hashed into its model version; a loaded model's tracked files can be checked again
before a call; a drafted spec can be saved without overwriting anything.

## Implements

- **`docs/design/architecture.md`:**
  - §3, `types/model.py`: `ModelSpec.from_json`, `to_json`, `versioned_json`; the field table; `CREDENTIAL_WORDS`
    and the credentials-file lists (`trust.md`, Where the rules live).
  - §3, `types/identity.py`: `version_hash`.
  - §5, `models/spec.py`: `LoadedModel`, `load_spec`, `stored_model`, `save_spec` (not `resolve_program`, step 04's).
  - §5, `models/files.py`: `hash_files`, `same_file`, `is_within`, `check_files` (not `remove_tree`, step 04's).
  - §10: `ema.models` in the import contracts; the AST check that `ema/models/__init__.py` doesn't import `execute`.
- **`docs/design/model_interface.md`:** the model spec's rules (paths, strings, names, `noisy`); M3; M10's
  template names; M16's hash check (`check_files`; the runner calls it in step 07); M17; M18; M21.
- **`docs/design/trust.md`:** T1; T7 (but the question text, step 07's); T8 (but the stored question); T2's spec
  checks (`pass_env` beside `env`, an `env` `PATH`'s entries); T6's `save_spec` (exclusive create, same bytes,
  a different file refused).
- **`docs/design/data_model.md` §3.4:** the model version's hash.
- **`docs/design/contracts.md`:** C33 (`check_model_version`) with its negative controls, in
  `tests/contracts/model.py`, over a Python function, a batch Python function, and a command-line model.
- **v1:** `agent/approval.py`'s `is_secret` and its tests, read; the lists rewritten (not copied).

## Out of scope for this step

- `resolve_program`, `remove_tree`, the environment (`BASE_ENV`, `model_environment`), and the three phases: step 04.
- The first approval's text (T7's codes and code spans, T8's "set"): step 07. The MCP root (T5): step 14.
- C31, C32, C34–C45: steps 04 and 05 (C34 is finished by the runner, step 07).

## Tasks

1. Test models in `tests/models/` (a Python function, a batch function, a command-line model, a function file
   with imports); `tests/models` kept out of pytest's collection.
2. Tests first: `tests/unit/types/test_model_json.py` (from_json, to_json, versioned_json; M18, M21, T2, T7, T8),
   `tests/unit/types/test_version_hash.py`, `tests/unit/models/test_files.py` (T1, the credentials through links,
   `check_files`), `tests/unit/models/test_spec.py` (M10, M17, T4's no-import, `stored_model`, `save_spec`), and
   the contract `tests/contracts/model.py` (C33 and its broken toys).
3. The code: `ema/types/model.py`, `identity.py`'s `version_hash`, `ema/models/{__init__,spec,files}.py`.
4. The import contracts, the AST test, the API reference, and the terminology test's coverage.
5. The checks in `CLAUDE.md`.

## Checks before reporting done

- Fast tier, lint, import contracts, docs with `-W`; no slow tests in this step.
- Lines against §11: `ema.types` (the spec's validation ~200 and trust's checks ~75) and `ema.models`'s share
  (paths and links ~20, `spec.py` and `files.py`).

## Stop condition

All checks pass; report to the coordinator (record 0066), and wait for the review.

## Choices made here

Each is in record 0069, with why; the numbers match.

1. `to_json` indented (2 spaces, the field table's order, a final newline); `versioned_json` canonical, without the settings.
2. `to_json` writes every key (`batch_size` null, `limits` `{}`); no keys of the other interface.
3. Paths normalized when read (empty and `.` parts dropped); absolute, `..`, and empty paths refused.
4. Fields of the other interface refused as unknown keys; `batch_size` only on a batch function.
5. A function is `file.py:f`, `f` an identifier that isn't a keyword.
6. Names: ASCII identifiers, not keywords (soft keywords allowed); a model's name `[a-z0-9_-]+`.
7. Also refused: duplicate `files` paths, colliding `writes` (case-folded), a `pass_env` name twice, `gt` with `ge`.
8. Parsers checked at loading (regex groups, JSON key parts, CSV column, row, and delimiter, `file`).
9. EMA's own file names compared case-folded against the whole path and its first part.
10. (Reversed in review round 1; see 27.)
11. The credentials lists rewritten from v1's (no `.key`, `identity`, or `.claude.json`).
12. `hidden_character`, `is_credentials_file`, `CREDENTIAL_WORDS`, `EMA_FILE_NAMES` public in `ema.types.model`.
13. Messages name the field as a path; `load_spec` prefixes the spec's path; NaN and Infinity refused.
14. `load_spec` keeps the spec's path as given, for messages; the model's directory is the spec's, links resolved.
15. `hash_files` refuses missing files, non-regular files, credentials through links, and one entry named twice.
16. `same_file` asks the nearest existing directory's file system about case; `is_within` compares each ancestor.
17. A function file that doesn't parse is refused at loading.
18. M17's resolution: the model's directory; `from a import x` tries `a/x.py`; relative imports; source order.
19. M10 at loading: non-UTF-8 text, an invalid `$`, and an unknown name refused, naming the line.
20. `save_spec` raises `PathRefused` (and `SpecError` for a spec loading would refuse); the same bytes write nothing.
21. `check_files` raises `ModelChanged` naming the label, the file, and what to do.
22. `stored_model` sorts the files and reads no file.
23. `ema/models/__init__.py` re-exports spec's and files' names; the AST test checks it imports no `execute`.
24. Test models in `tests/models/`, out of collection; `tests.support.models.copy_model`.
25. The adapter contract's implementation is `Adapter(kind, load)`; C33 has three broken toys.

Review round 1:

26. Model parameter and model prediction names are ASCII identifiers (a function's name its own NFKC form).
27. Credentials-file names refused on every path in a spec, `writes` and a parser's `file` included (reverses 10).
28. The case probe: `pathconf` on macOS, else an entry inside the nearest existing directory, else its parents.
29. The model's directory is `dirname(realpath(spec))` (corrects 14).
30. Two entries are one file only when one directory entry (`lstat`); links beside targets and hard links load.
31. Run-directory paths compared case-folded and as directories (`out` and `out/mesh.dat` refused).
32. Only regular files read, opened without blocking (`open_regular`); a FIFO is refused, never waited on.
33. Overflow, nesting, and `ast.parse`'s other errors are `SpecError`s; `NaN` names its field.
34. M17 against the model's directory only (trust.md's `sys.path`); what step 05 must keep to agree.
35. A parser's `file` of `./stdout` refused as ambiguous with the stream.
36. `save_spec`: `.JSON` in any case, a link to nothing named, the text checked with `from_json` first.
37. `leads_to_credentials` and `open_regular` public in `ema.models.files`.

## Notes

- **Built:** `src/ema/types/model.py` (the JSON form and trust's checks), `identity.py`'s `version_hash`,
  `src/ema/models/{__init__,spec,files}.py`; tests in `tests/unit/types/test_model_json.py`,
  `test_version_hash.py`, `tests/unit/models/test_{files,spec}.py`, `tests/contracts/model.py` (C33), and the
  models in `tests/models/`. Shared files extended: `pyproject.toml` (AR1, AR4, AR5, the reference models'
  contract), `docs/index.md`, `src/ema/types/__init__.py` (appended), `tests/unit/test_ast.py`, the root
  `conftest.py` (`tests/models` not collected).
- **Times:** fast tier 667 tests in about 2 s; no slow tests in this step.
- **Size** (code lines without docstrings, comments, or blanks): `ema.types.model` +443 (§11: about 275),
  `identity.py` +6, `_values.py` +5, `ema.models` 302; about 755 against the roadmap's 450 (record 0069,
  Consequences; review round 1 added about 90).
- **Review round 1:** the independent review's majors (credentials names on `writes` and a parser's `file`; ASCII
  names) and minors 3–9 and 11, and its nits, fixed with a test each (choices 26–37, record 0069); each new test
  was checked to fail on the first version. The two questions for the owner are in record 0069. The size budget
  is the coordinator's.
- **v1:** `agent/approval.py`'s `is_secret` and `tests/test_approval.py` read; nothing ported.
- **Deferrals:** none of the step's ids. T7's and T8's question text (step 07), T5's root (step 14), and C34's
  runner part (step 07) are other steps'.
