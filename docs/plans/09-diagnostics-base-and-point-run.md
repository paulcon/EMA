# 09. Diagnostics base, the diagnostic contract, the point run, and the reference models

**Status:** in progress (demo; record 0066); its choices are record 0075. **Branch:** `demo-09-diagnostics`.
**Updated:** 2026-10-02.

## Goal

A diagnostic is one module that registers itself: `ema.diagnostics.base` parses its diagnostic parameters (the
same parsing for Python, the CLI's `--param`, and MCP's `params`), runs the shared precheck, its `compute`, and
its figures, and builds the diagnostic result; the diagnostic contract (C1–C19) runs over every registered
diagnostic and a toy, each check with a broken toy; the point run is the first diagnostic; and the reference
models R1–R11 (but R9) ship in `ema/reference_models/`.

## Implements

- **`architecture.md` §6 (`ema.diagnostics`):** `DiagnosticParameter` (with `parse`, `json_schema`),
  `Transform`, `Diagnostic`, `AnalysisContext`, `Computation`, `evaluate`, `register`, `get`, `names`,
  `unregister` (0065); §7 step 2 (the request: parameters and space parsed, defaults filled) and step 8 (how the
  workspace calls `evaluate`); §1 and §10 (layer 3b; the reference models' contract); §11 (`ema.reference_models`,
  `path(id)`).
- **`diagnostics/shared.md`:** the precheck (usable runs, the minimum, constant; P6), the shared observations
  (C10), the shared notes in order (runs not usable with at most 5 reasons, S7; reused failed runs, 0010; too few;
  all failed; no usable run, 0051; constant, 0035; measured noisy, P7), random draws (spawned streams, S8),
  figures (S9, S10).
- **`diagnostics/point_run.md`:** PT1–PT9 at this layer, its observations, "varies", measured noisy, the
  figure, its expected answers (R1, R4a, R5, R6a, R6b).
- **`contracts.md`:** C1–C19 (`tests/contracts/diagnostic.py`) with the toy, a broken toy per check, and the
  meta-test; C47's note (the reused-failed note); C52's part here (the point run's record, filled by `evaluate`).
- **`uncertainty.md`:** the interval-method seam as a diagnostic reads it (`AnalysisContext.interval_method`,
  C19), `IntervalInfo` with `seed` and `distinct` (record 0073).
- **`reference_models.md`:** R1–R8, R10, R11 as model specs with their function files, R8 a command-line
  program with its input deck, parser, and shared file.
- **Hand-offs:** record 0067's Deferrals (one canonical design identity: integers as integers, alpha as its
  decimal text, values and directions as doubles); record 0068 item 1 (each diagnostic's compute repeated at
  8 memory offsets with the heap scrambled, in C7); record 0073 (plain Unicode text in results, tab-separated
  leading cells, a table's `title` under it, `seed` and `distinct` in the interval settings).
- **Principles:** P1 (every number from the runs), P2 (no interpretation in results), P4 (C7, the offsets),
  P5 (the provenance checked against the request and the spawn tags), P6 (the precheck), P7 (measured noisy).

## Out of scope for this step

- The runner, the store, the workspace (steps 06, 07, 14): PT1's price and rerun, PT4's and PT5's store parts
  (C52's record written by W5, the later result read through Q10), and C47's retry are tested end to end at step
  14. Here the point run's design, run ids, and `evaluate` are tested on batches built directly.
- The other five diagnostics (steps 10–13); R9 (later).

## Tasks

1. Plan and record 0075.
2. Tests first: `tests/contracts/diagnostic.py` (C1–C19, the toy in `tests/support/diagnostics.py`, broken toys,
   the meta-test); `tests/unit/diagnostics/test_base.py` (parameters, the request, canonical identities, the
   precheck's notes, `evaluate`'s refusals, the registry); `tests/unit/diagnostics/test_point_run.py` (PT1–PT9 on
   the reference models' functions, the expected answers, the mock's structure);
   `tests/unit/test_reference_models.py` (each spec loads; each function's truths).
3. Code `src/ema/diagnostics/{__init__,base,point_run}.py` and `src/ema/reference_models/`.
4. Extend `pyproject.toml` (AR1's layer 3b, AR4, AR5, the reference models' contract; Ruff and mypy exclude
   `src/ema/reference_models/`), `docs/index.md` (a block of its own), the wheel test.
5. Run every check in `CLAUDE.md`; measure the lines.

## Adding a diagnostic (steps 10–13)

One module in `src/ema/diagnostics/`, ending with `register(<Diagnostic>())`; nothing else to edit: the package
imports every module in it that isn't `base` or private (`_lines.py` is imported by the modules that use it).
The module:

- subclasses `base.DiagnosticBase` (defaults for `example_request`, `observation_scope`, `transform` from a
  `TRANSFORMS` mapping, the shared observations' transforms, `strips`), and sets the declarations (`name`,
  `title`, `summary`, `takes_space`, `parameters`, `interval_method`, `spawn_tags`, `has_estimates`,
  `header_rows`, `constant_note`, `nesting`);
- builds its `parameters` from `base.DiagnosticParameter` with the readers `Integer`, `DecimalText`, `Point`,
  `Name`, `GivenLines` (`parse` canonicalizes, so one design has one identity), and `base.seed_parameter`;
- writes `design_identity` with `base.identity(...)` (kind, space, the generator's parameters, seed, sampler);
- writes `compute(batch, ctx, *, estimates_allowed)`: with no usable run, it returns its own notes only; below
  its minimum, or with a constant model prediction, no estimates (evaluate refuses them); its intervals from
  `ctx.interval_method` on `ctx.stream(tag)`, recorded with `base.interval_info(ctx, n_usable, distinct=...)` and
  `base.estimate(...)`; its own rows of the shared observations table, if any, under the table key `"shared"`
  (the point run's), its other observation tables after;
- writes `figures(batch, result, ctx, out_dir)` with `ema.plotting`, from the batch and the stored result only;
- runs the contract by being registered (`tests/contracts/diagnostic.py` parametrizes over `names()` and the
  toy), and adds its known-answer and golden report tests with `tests/support/diagnostics.py`'s batch builder,
  `tests/support/reference.py`'s reference model functions, and `tests/support/reports.py`'s comparator.

## Checks before reporting done

- `uv run pytest -q && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto` for this step's
  slow tests.
- Lines of `ema.diagnostics` against §11's "base and precheck ~300" and the point run's share; the reference
  models against their 1,000.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0075's, numbered as there, one line each.

1. Importing `ema.diagnostics` imports each public module; a diagnostic registers itself: one module, no other edit.
2. `DiagnosticBase` gives the defaults; the protocol's declarations are read-only, so class attributes meet them.
3. `DiagnosticParameter.reader` (`Integer`, `DecimalText`, `Point`, `Name`, `GivenLines`): one parsing, JSON text or a
   bare string; `json_schema` with meaning and default (C55).
4. One identity per design: the readers canonicalize (3.0 → 3, alpha → its shortest decimal text, values → doubles);
   `base.identity` refuses what isn't canonical.
5. Shared helpers in `base` for steps 10–14: `make_request`, `request_space`, `identity`, `describe`, `estimate`,
   `interval_info`, `make_provenance`, `library_versions`, the context's `seed`, `stream`, `on_step`.
6. `compute` is always called; `evaluate` refuses estimates when not allowed and observations of no usable run.
7. The shared observations are `evaluate`'s table `"shared"`; a diagnostic's own `"shared"` rows go first in it.
8. Counts are of distinct runs; "constant" needs two usable runs; too few and constant give both notes.
9. The shared notes' texts and order (not usable, reused failed, all failed / no usable / too few, constant,
   measured noisy), the `failed_runs` id as 12 hex digits.
10. `evaluate` checks the provenance's request and spawn tags; it fills the point run's record's ids.
11. The point run's one table (Replicate 0 or its kind, mean, standard deviation or "none", distinct values, then the
    shared rows); 9 repeats in its example request; the figure's labels as the spec and the mock write them.
12. Negative controls where `evaluate` keeps the promise (C1, C3, C10, C13, C14, C16, C19), as built.
13. C2 shifts the usable runs too, to catch a toy that fills failed runs' y with 0.
14. C5's shift tolerance has a floor of 16 ulps of |b| + max|y| (the point run's fixture spans 2⁻²⁸).
15. C6 is skipped when the offset merges the fixture's distinct values (the point run's exemption, as a rule).
16. C7 repeats `compute` at 8 memory offsets, the arrays read-only through their bases, the heap scrambled.
17. C8 changes a copy's `spawn_tags`; C18 asserts 60 s per evaluation.
18. Checks about numbers and notes run without figures (`NoFigures`); C1, C7, C11, C12 draw them.
19. Reference models `r1`, `ishigami`, `r3`, … `r11`, each with `model.json`, its files, and `space.json` (`space(id)`).
20. Prediction descriptions empty but R3's, so headers read as the mocks; limits only where the model needs them.
21. R8 `["python3", "r8.py", "x.in"]`, standard library only; R6 noise from fresh entropy; R5's regions as specified.
22. R2 and R3 ported from v1's `library.py` (bit-identical to v1); `truth.py` not ported (Monte Carlo numbers).
23. AR1's layer 3b with optional `(ema.runner) | (ema.approval)` until step 07 merges; reference models excluded
    from Ruff and mypy.

Review round 1:

24. The point run's mean and standard deviation from the deviations from the first usable value: exact for a constant.
25. `DecimalText` reads text as written (`reads_text`): "0.70720000000000000001" stays itself; " 0.7072" is refused.
26. C6's skip is `pytest.skip` with a reason, for the point run only (`C6_EXEMPT`); the toy never skips.
27. C2's kind cell is exactly replicate 0's new kind.
28. C10's "Of the N runs at the point" for the point run only.
29. C5 compares the notes' texts without their numbers and ids, beside their codes.
30. The notes are plain text: `ws.failed_runs("…") lists each one.`, "retry_failed=True runs them again.", no backticks.

## Notes

- **Built:** `src/ema/diagnostics/{__init__,base,point_run}.py`; `src/ema/reference_models/` (`__init__.py` and
  `r1`, `r2`, `r3`, `r4a`, `r4b`, `r5`, `r6a`, `r6b`, `r7`, `r8`, `r10`, `r11`); tests in
  `tests/contracts/diagnostic.py`, `tests/unit/diagnostics/{test_base,test_point_run}.py`,
  `tests/unit/test_reference_models.py`; support in `tests/support/{diagnostics,reference}.py`. Shared files
  extended: `pyproject.toml` (AR1's layer 3b, AR4, AR5, the reference models' contract, Ruff's and mypy's
  excludes), `docs/index.md` (a block of its own), `tests/slow/test_wheel.py` (the new modules and data files).
- **Tests:** 166 fast (the contract 58: 19 checks over the point run and the toy, the meta-test's 19, one more; the
  base 59; the point run 18; the reference models 31) and 1 slow (R5's timeout). The fast tier: 1,306 passed, 5
  skipped, in about 22–24 s on a loaded machine (other steps' agents running); this step's share about 6.5 s.
- **Size** (code lines without docstrings, comments, or blanks): `ema.diagnostics` 787 after review round 1 (`base.py` 620,
  `point_run.py` 160, `__init__.py` 7; 780 before) against the roadmap's 500 and §11's "base and precheck ~300": record 0075, Consequences.
  The reference models: 82 lines of Python and 187 of specs and data, against their 1,000.
- **v1:** ported `src/ema/testfunctions/library.py`'s `ishigami` and `borehole` (R2, R3), bit-identical to v1 at
  200 points run in `../EMA-v1/.venv`; read `tests/diagnostic_contract.py` (its checks' shape); `truth.py` read, not
  ported.
- **Deferrals:** PT1's price and rerun, PT4/PT5's store parts, C47's retry, and C52's W5 to step 14; R8 through the
  runner to step 11; merging `demo-08-reports` to the coordinator (the permission system refused the merge here).
- **Review round 1:** the review's major M1 (the point run's mean and standard deviation of a constant), minors
  m1, m2, m3, m5, a round-2 minor (backticks in the notes), and the C5 nit fixed with a test each (choices 24–30,
  record 0075); the tests of M1, m1, and the notes were checked to fail on the first version (m2's, m3's, and m5's are
  the contract's own assertions; the −0.0 test pins kept behavior). m4 (C11's "no line under an estimates
  table") recorded as not buildable, and −0.0 kept as its own point (`data_model.md` §3.4), in record 0075. Behavior
  steps 10–14 see: the not-usable and reused-failed notes' texts lose their backticks; C6 fails, not skips, for a
  diagnostic other than the point run whose fixture the offset merges; C10 requires "Of the n usable runs"; C5
  compares the notes' texts; `DecimalText` text is not read as JSON.
- **For steps 10–13:** see "Adding a diagnostic" above; `tests/support/diagnostics.py` (`prepare`, `batch`,
  `evaluate`, `NoFigures`) and `tests/support/reference.py` (`prepare`, `batch` on a reference model's function)
  build the known-answer tests; keep the contract's time in mind (about 2 s per diagnostic).
