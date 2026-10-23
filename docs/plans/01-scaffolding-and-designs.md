# 01. Scaffolding, the design types, and the design generators

**Status:** in progress (demo; record 0066): approved 2026-10-01, built through task 8 on `demo` without the Review A
and end stops (0066); its further choices are record 0067. **Branch:** `demo`. **Updated:** 2026-10-01.

## Goal

> One or two sentences: what exists at the end of this step that didn't before.

The repository builds, tests, lints, checks its layers, and builds its docs with the commands in `CLAUDE.md`
(0059). Layers 0 and 1 hold what a design needs: the parts of `ema.types` that describe a model's model
parameters, a model parameter space, and a design, with the hashes and text rules that need nothing else; and
`ema.designs`, the `random` sampler and the six design generators, which keep the design generator and sampler
contracts (C20–C28) and G1–G18.

## Implements

> The accepted specs and ids this step builds. Nothing outside this list.

- **Record 0059** (items 1–7 and 9): `.python-version`, `pyproject.toml`, `uv.lock`, the root `conftest.py`,
  `docs/conf.py`, `docs/index.md`, `.github/workflows/checks.yml`; each tool's scope; the import contracts for
  the packages that exist. **Record 0060:** `license = "MIT"`.
- **`docs/design/architecture.md`:**
  - §1: AR1, AR2, AR4, AR5, AR6, AR7 and the reference models' contract, each over the packages this step makes
    (§10, 0059); AR3 comes with `ema.cli` and `ema.mcp`.
  - §2: the layout of `src/ema/types/` (the modules below) and `src/ema/designs/`.
  - §3, `ema.types`:
    - `errors.py`: every error in the table, with `retryable`;
    - `text.py`: `fmt` (S3, 0044) and `duration` (0061, 0062, 0063, with its eleven known answers);
    - `streams.py`: `spawned`;
    - `identity.py`: `TrackedFile`, `canonical_json`, `sha256_hex`, `point_hash`, `run_id`, `batch_call_id`,
      `decimal_fraction`, `model_version_label`;
    - `model.py`: the dataclasses (`Limits`, `ModelParameter`, the three parser settings, `PredictionSpec`,
      `FileEntry`, `PythonFunction`, `InputDeck`, `CommandLine`, `Keep`, `ModelSpec`), `ModelSpec.parameter`
      and `ModelSpec.prediction`; values in model parameter units as doubles (0061);
    - `space.py`: `Scale`, `Range`, `ModelParameterSpace`, every method;
    - `design.py`: `DesignIdentity`, `Line`, `Design`, `DesignStructure`.
  - §4, `ema.designs`: `samplers.py` (`Sampler`, `register`, `get`, `names`, `Random`), `generators.py`
    (`DesignGenerator`, `register`, `get`, `names`, `MAX_DESIGN_POINTS`, `GOLDEN_UNIT_TOL`), `point.py`,
    `uniform.py`, `convergent.py`, `lines.py` (`SHARED_ANCHOR_TOL`); generators called with an identity only
    (0061 item 4); an identity of another generator or sampler version refused, naming both (0061, 0062).
  - §10: the fast tier's AST test, AR7's part (no module in `ema` imports the root package).
- **`docs/design/designs.md`:** G1–G18 (G18 by 0065); the model parameter space, its JSON form, unit coordinates, the maps
  and the map back (0047, 0061); Determinism across machines (0062); Samplers; every generator.
- **`docs/design/data_model.md` §3.4:** canonical JSON; doubles for model parameter values (0061); the point
  hash; the run id's bytes; the batch call id; a design's identity; alpha's decimal string (0047).
- **`docs/design/contracts.md`:** C20–C27 (design generator contract) and C28 (sampler contract), each with its
  negative control and the meta-test that every check has one; the degenerate cases that apply to designs (d = 1,
  d = 20, a nominal value at a range's end, a log range over 10⁻⁶ to 10⁶, repeated points); the fast tier.
- **The terminology test** (0008, the glossary's header), over the public identifiers and the error messages
  this step makes.
- **Record 0065:** `unregister` in the two registries this step makes; the refusals (G18, and G14's and G15's
  added tests); the four words in the terminology test; a given line's anchor and direction.
- **Records:** 0005 (the hyperrectangle, `ModelParameterSpace`, the shape seam), 0011 (replicates), 0012 (the lines), 0023 (held values), 0024 (scales and limits), 0032, 0033,
  0046, 0047, 0049, 0051; 0061 items 1 (the identity's seed), 4, 6, 7, 14, 15 (`duration`); 0062 items 1, 3, 4,
  5; 0063 item 1 (the `DesignStructure` type only) and item 3.

Each spec above is `accepted`. Nothing from v1 is ported or read in this step.

## Out of scope for this step

- `ModelSpec.from_json`, `to_json`, and `versioned_json`, with their checks (M18, M21, T7, T8, unknown keys);
  `version_hash`; and the credentials lists. They come with model loading (roadmap step 03), where M3, M10, and
  M17 are tested, and v1's `is_secret` is read.
- `approval_id` and `reuse_key` (they need `Request`); `types/runs.py`, `results.py`, `requests.py`, and
  `summaries.py`: each with the first step that uses it (`docs/notes/build_roadmap.md`).
- `ema.numerics`, the basis and interval-method registries, and every layer above 1.
- The replay's rebuild check and its per-range tolerance (0063 item 2): `ema.workspace` (`_reproduce.py`).
- AR3's contract, and the AST test's parts for `ema.cli` and `ema/models/__init__.py`.
- The reference models, and Ruff's and mypy's exclusion of `src/ema/reference_models/` (with them).
- The wheel's data files (`schema.sql`, `tools.md`, the reference models): the wheel-build test starts here and
  checks each as its step adds it.
- Starting GitHub Actions. The workflow is written here; the owner starts it after merging and pushing (0059).

## Questions before approval

Answered by the owner on 2026-10-01, each with the suggested option. Questions 1, 3, 4, and 5 are record 0065,
accepted and applied to the specs the same day.

1. **How a test removes a fake from a registry** (`architecture.md` §4 requires the removal, and names no
   function for it): every registry gets `unregister(name)`, which refuses a name not registered (0065 item 1).
2. **How much of `ema.types` this step builds:** the modules designs need (Implements); `runs.py`,
   `results.py`, `requests.py`, `summaries.py`, and the model spec's JSON come with the steps that first use
   them (`docs/notes/build_roadmap.md`).
3. **Requests no spec refused** (generator parameters outside their floors, non-finite or non-numeric values,
   malformed spaces, an anchor naming an unknown name, an empty list of given lines, a sampler whose 1/r isn't an
   integer): refused in layer 1 with `RequestError`, as G18 and extended G14 and G15 tests (0065 item 2).
4. **The terminology test's list** gains "analyst", "user code", "model code", and "model program" in generated
   text (0065 item 3).
5. **A given line's anchor and direction:** the direction kept as given, not normalized; the anchor's unnamed
   varied model parameters at z = 0, the geometric center on a log range (0065 item 4).
6. **The line budget** (`ema.types` forecast near 1,500 lines, the total near 8,840 against 8,300; Notes): this
   step reports its measured counts and the projection from them, and if the projection still crosses 8,300,
   proposes the budget record before step 02's plan.

## Choices made here

Not in a spec, and small; listed so the review can object.

- **EMA's version** in `pyproject.toml` is `2.0.0.dev0` until the release (the mock reports show "EMA 2.0.0").
- **Generator and sampler versions** start at `"1"`.
- **`Line`'s tuples:** `anchor` and both `ends` are complete points (every model parameter, in the spec's
  order, as a row of `Design.points`); `direction` has one component per varied model parameter, in the spec's
  order, since held ones have no unit coordinate.
- **A block's `Design`** (`build(identity, spec, start, stop)`, G6) holds the block's points and replicates,
  and the whole design's `levels` and `lines`, whose rows index the whole design.
- **The batch call id** hashes its runs' ids as hex text (UTF-8), concatenated in call order with no separator.
- **Values in model parameter units are doubles wherever built:** `Limits`, `ModelParameter`, `Range`, and the
  space's held values turn an `int` into a `float` in `__post_init__`, and refuse a bool (0065), so a spec or space built in Python agrees
  with one parsed from JSON (0061 item 6). The values in `DesignIdentity.params` (a point's `x`, anchors, given
  directions) become doubles when the diagnostic parameters are parsed (roadmap step 09; 0061: "when parsed");
  here the generators convert them on reading, so an `int` and a `float` give the same points.
- **The point design's identity:** `build` reads `x` and `repeats` from `params`, and refuses an identity whose
  `space` isn't `ModelParameterSpace.at_point(spec, x).canonical()` (0049).
- **The guides' two code blocks with a literal `…`** (`docs/guides/run_a_diagnostic.md`, steps 2 and 7) fail
  Pygments under `-W`: the Python block gets `...`, and the JSON block is fenced as `text`, a plain fix (0052)
  named in the commit, rather than a suppressed warning that would hide others.
- **Random lines' norm** is computed elementwise (`np.sqrt(np.sum(v * v))`), not through BLAS (`STATUS.md`'s
  Accelerate warning); the cross-machine comparison is in unit coordinates either way (0062).
- **All three runtime dependencies** (numpy, scipy, matplotlib) are declared now, at the lower bounds 0059
  found (2.1.0, 1.14.1, 3.9.2), confirmed at locking as the first releases with wheels for Python 3.13, so the
  lockfile and the lowest-versions job are set up once. scipy and matplotlib are unused until later steps.
- **Contract modules are collected by pytest** under `tests/contracts/` only, by a hook in that directory's
  `conftest.py` that collects its modules and their `check_*` functions, so each `check_*` is a test
  parametrized over the implementations, can also be called directly with a broken toy, and a later
  `check_files` imported elsewhere is never collected (the consistency review's D, BUILD-7). The slow tier is a
  `slow` marker, skipped unless `--slow` is given.
- **Sphinx's autosummary pages** are generated into `docs/_autosummary/`, ignored by git.
- **Golden points:** the golden-points test is written with its fixed requests at task 3; its expected values
  are filled in from the first build on this Mac (task 5), after each is checked against the independent
  constructions below, and shown at the final review.

## Tasks

1. **Branch** `build-01-scaffolding-and-designs` from `main`, once this plan is approved and committed on
   `main`.
2. **Scaffolding** (0059):
   - `.python-version` (`3.14`); `pyproject.toml`: the project (name `ema`, `requires-python = ">=3.13"`,
     `license = "MIT"`, `license-files = ["LICENSE"]`), the runtime dependencies, the `uv_build` backend with
     the package in `src/ema/`, the `dev` group (pytest, pytest-xdist, Ruff, mypy, import-linter, Sphinx, MyST,
     furo, each bounded below at its release when first locked), and each tool's settings as 0059 item 4 gives
     them; the import contracts for `ema.types` and `ema.designs` (the layers contract as
     `["ema.designs", "ema.types"]`, since import-linter refuses a layer that doesn't exist; AR2; AR4; AR5; AR6;
     the reference models' contract).
   - `uv sync`, which writes `uv.lock` and installs into the project's `.venv` only (no system install).
   - The root `conftest.py`: the `--slow` option, the `slow` marker, `collect_ignore` for
     `src/ema/reference_models/`.
   - `src/ema/__init__.py`: lazy re-exports (PEP 562) of the errors, the only public names of the root that exist
     yet (AR7).
   - `docs/conf.py` (MyST, furo, autodoc, autosummary, napoleon; `design/`, `decisions/`, `notes/`, `plans/`,
     `checks/` excluded; a dataclass's fields described once) and `docs/index.md` (the guides, and the API
     reference of the modules that exist).
   - `.github/workflows/checks.yml`, `workflow_dispatch` only, on Linux (0059 item 7): lint, the import
     contracts, and the docs on 3.14, the site kept as the run's artifact; both tiers on 3.14 with
     `uv sync --locked`; both tiers on 3.13 with `UV_PYTHON=3.13` and `UV_RESOLUTION=lowest-direct` for the
     whole job.
   - `.gitignore`: `docs/_autosummary/`, `dist/`, `.mypy_cache/`, `.ruff_cache/`.
   - **AR2 on EMA's own code** (0059 item 9): add `import os` to an `ema.types` module, run `uv run lint-imports`,
     see AR2 fail naming `ema.types -> os`, and remove the line. The output goes in Notes.
3. **Tests first, from the specs** (CLAUDE.md), citing the ids each implements:
   - `tests/contracts/design.py`: `check_deterministic` … `check_bad_space` (C20–C27), run over the six
     generators and a toy, with the per-generator table (seeded or not, the nesting claimed, an example identity,
     one over the cap; 0061), a broken toy per check (each the Negative control column), and the meta-test.
     C24's "no array allocated" is measured with `tracemalloc` around a build of n = 10,000,001.
   - `tests/contracts/sampler.py`: `check_sampler` (C28) over `random`, a fake nested sampler, and a fake that
     isn't nested, registered and unregistered by fixtures (0065 item 1); its two broken toys.
   - `tests/unit/designs/`: each G's Test column (G1–G18), on models built in Python (the heat model of G9; the
     contract model's d = 3, d = 1, and d = 20 spaces): G7's sizes
     (18, 36, 72, 144; 18, 37, 73, 145; 18, 72, 288), G10's exact ends and the map back's known answers, G12's
     102 rows and 97 distinct points (98, 102, 96), G13's m = 5 and 6 at seed 1, and line 3 alone; G14's and G15's
     added refusals, and G18's (0065). Also the
     refusals in no G test: a space holding every model parameter, refused by every generator but point
     (`designs.md`, Nothing varied; 0049), and a point's `x` naming an unknown model parameter; and the
     degenerate cases for designs: d = 1, d = 20, a log range over 10⁻⁶ to 10⁶ (inside, exact ends, the map back),
     and a nominal value at a range's end (coordinate lines refuse it, naming the model parameter; 0051).
   - **Independent constructions** (known answers not from EMA's code): the `random` sampler's rows equal
     `np.random.default_rng(seed).random((n, d))` bit for bit (`designs.md`: "the same as numpy's
     `Generator.random` today"); random lines' anchors, directions, and ends at seed 0, given lines on R7's and R10's
     spaces, and coordinate lines on R1's and R3's (which have log ranges), agree within `GOLDEN_UNIT_TOL` in unit
     coordinates with the step-11 scripts (`docs/checks/gram_rates.py`'s `random_line`, `given_line`,
     `coordinate_line`; written from the specs, with no EMA code); and points in a log range equal
     `np.clip(np.exp(np.log(lo) + (np.log(hi) - np.log(lo)) * u), lo, hi)` computed directly, the ends set to lo
     and hi (`designs.md`, Unit coordinates).
   - **The golden-points test** (G1, 0062): fixed requests for the `random` sampler's unit rows, a linear
     range (bit for bit), a log range, random lines, and a line through a space with a log range (in unit
     coordinates within `GOLDEN_UNIT_TOL`), with |ln lo|, |ln hi| ≤ 64 and ln hi − ln lo ≥ 1.
   - `tests/unit/types/`: canonical JSON (key order, compact, non-ASCII kept, NaN refused, −0.0 and a subnormal
     round trip); the point hash (8·d little-endian bytes; −0.0 and 0.0 differ); the run id's bytes (hex text,
     then two 8-byte integers) and the batch call id (bytes and hex the same); `decimal_fraction` (0.7072 →
     7072/10000, `"0.9"` → 9/10); `model_version_label`; `fmt` (S3); `duration`'s eleven known answers;
     `spawned` against `Generator(PCG64(SeedSequence(seed, spawn_key=key)))`; the space's JSON form (a 2-list,
     an object with a scale, a held number, a 2-tuple, integers read as doubles), `validate` (G15, M6),
     `canonical`, the maps, `from_cube`, `clip_line`; mappings read-only; each error's `retryable`.
   - The terminology test (0008) and the AST test (AR7).
   - The wheel-build test (slow tier): `uv build` into a temporary directory; the wheel holds `ema/` and its
     modules.
   - **Review A:** show the tests and the scaffolding, with the commands' output; wait (Stop condition).
4. **Code** `ema.types` (the modules above) and `ema.designs` until the tests pass, each public name with a
   NumPy-style docstring citing its ids, and each module within AR2's imports.
5. **Golden values:** fill in the golden-points test from this Mac's build, each value first checked against
   the independent constructions of task 3.
6. **Docs:** the API reference of `ema.types` and `ema.designs` builds with `-W`.
7. **Measure:** the fast tier's time (serial) and the slow tier's (`-n auto`); source lines of `ema.types` and
   `ema.designs`; and, in a scratch copy of the repository (the lowest resolution rewrites `uv.lock`), both
   tiers with `UV_PYTHON=3.13` and `UV_RESOLUTION=lowest-direct`, as the workflow's third job runs them.
8. **Update `STATUS.md`**, and this plan's status block and Notes.

## Checks before reporting done

- The fast tier passes in under 30 s, serially: `uv run pytest -q && uv run lint-imports`.
- Both tiers pass: `uv run pytest -q --slow -n auto`; and on 3.13 at the lowest versions (task 7).
- Lint passes: `uv run ruff check && uv run ruff format --check && uv run mypy`.
- The docs build: `uv run sphinx-build -W --keep-going docs docs/_build/html`.
- AR2 confirmed failing on a forbidden import, and passing without it (task 2).
- Every check in `tests/contracts/design.py` and `sampler.py` fails on its broken toy (the meta-test).
- Source lines: `ema.designs` against `architecture.md` §11's 388; this step's `ema.types` modules (about 505
  expected), with the projection for all of `ema.types` against §11's 860 and the total against `scope.md`'s
  8,300 (Notes; question 6).

## Stop condition

> Where Claude stops and waits for review.

- **Review A,** after task 3: the scaffolding in place, its lint, import, and docs commands passing, and every
  test written (failing where code is missing). Stop, show them, and wait.
- **The end,** after task 8: every check above passes, `STATUS.md` and this plan are updated, and nothing is
  committed. Stop and wait for review; commit only when asked.
- **Anywhere:** a spec silent or unclear on something a task needs, or a test that can't pass as the spec is
  written, stops the step; it becomes a question, an OD row, or a proposed record.

## Notes

> Anything learned during the step: surprises, spec gaps found (each becomes an OD row), follow-ups.

- **A likely overrun in `ema.types`, known before coding** (question 6). §11 itemizes about 460 of its 860 lines
  (the model spec's validation ~275, `identity.py` ~100, the doubles, `DesignStructure`, and `duration()` ~85),
  which leaves about 400 for everything else. This step's other modules (the model dataclasses, the space, the
  design types, the errors, `fmt`, the streams) take about 350 of those, for §3's 153 stub lines; with its
  itemized parts (`identity.py` ~70, and the ~85), this step is about 505 lines of `ema.types`, and about 890
  with designs. At the same ratio, `runs.py`, `results.py`, `requests.py`, and `summaries.py` (301 stub lines)
  come to about 690, so `ema.types` would end near 1,500, about 640 over 860, and §11's 8,200 near 8,840,
  over `scope.md`'s 8,300. The step reports its actual count and the projection from it.
- From the consistency review (D, BUILD-7 and BUILD-8): collecting the contract modules (Choices) is settled
  here; the reference models' Ruff and mypy exclusions are their step's.
- **Built on `demo` (record 0066),** through task 8 with no stop at Review A; `STATUS.md` is the coordinator's.
  The choices beyond this plan's list (30) are record 0067, `proposed (provisional; record 0066)`.
- **AR2 on EMA's own code** (task 2): with `import os` added to `ema/types/text.py`, `uv run lint-imports` gave
  "AR2 No I/O in layers 0-1 BROKEN ... ema.types is not allowed to import os: ema.types.text -> os (l.4)"
  (5 kept, 1 broken); without it, 6 kept, 0 broken.
- **Ruff 0.16 formats Markdown** (Python code blocks in `.md` files): its first `ruff format` rewrote six accepted
  documents, restored from `HEAD` at once; `*.md` is excluded from Ruff (0067 item 2).
- **Tests:** 407 (406 in the fast tier, 5 of them doctests; 1 slow, the wheel build): the design contract's 8 checks
  over the six generators and the toy, the sampler contract over `random` and two fakes, both meta-tests, G1–G18,
  the independent constructions, the golden points, the terminology and AST tests. Each broken toy was run once
  against its check and fails it for the intended reason.
- **Times** (this Mac, 2026-10-01): the fast tier 1.3 s serially (`uv run pytest -q`; budget 30 s); both tiers
  2.1 s with `-n auto`; `lint-imports` about 1 s.
- **Source lines** (code lines: no docstrings, comments, or blank lines; physical lines in brackets): `ema.types`
  this step's modules 494 [1,242], with its `__init__.py`'s 92 lines of re-exports beside them; `ema.designs` 496
  [815] against §11's 388 (`lines.py` 230 against "about 150"). The projection: `ema.types` near the forecast
  above (about 1,500 in all), and `ema.designs` about 110 over, so the total near 8,950 against `scope.md`'s 8,300
  (question 6: the budget record is the coordinator's to propose).
- **Golden values** (task 5): recorded from this Mac's build (numpy 2.5.3), each first checked against numpy's
  `Generator.random`, lo + (hi − lo)·u, the log map computed directly, and step 11's `random_line` and
  `given_line`.
- **Deferred** (0066, 0067): the 3.13 lowest-versions run in a scratch copy (task 7); the workflow's third job is
  written. About 15 minutes later.
- **Review round 1** (2026-10-02; 0067 items 31–38, and two deferrals): convergent's sizes are exact and cheap
  for any level (M1: n_min + L over the cap refused at once; a guarded float estimate per level, exact bounds
  where it is unsure; 0067 item 24 corrected); the seed normalized before drawing (m1); alpha text must be a
  decimal (m2), and identity canonicalization handed to step 09; the meta-tests expect each broken toy's own
  failure (m4); C21 checks each end's bounding coordinates exactly (m3); C28 checks what EMA hashes (m5);
  lines' `size` makes `build`'s checks, and 0051's check makes a few points a line (m6, m8); the nits. A block of
  a lines design still makes every line's segment: deferred (0067). Tests: 472 in the fast tier (4.1 s
  serially). `ema.designs` 556 code lines, from 496.

