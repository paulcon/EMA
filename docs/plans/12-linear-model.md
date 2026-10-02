# 12. The linear model

**Status:** in progress (demo; record 0066); its choices are record 0078. **Branch:** `demo-12-linear`.
**Updated:** 2026-10-02.

## Goal

The linear model diagnostic registers itself: a least-squares fit of the model prediction in unit coordinates
over a convergent design, its coefficients, relative residual, R², and leave-one-out error with bootstrap
variability intervals, the fit at each level as observations, three figures, and a report that matches the
spec's mock.

## Implements

- **`diagnostics/linear_model.md`:** LM1–LM10, the parameters and defaults, the computation (QR fit, relative
  residual, R², LOO by PRESS), the uncertainty section (the bootstrap over level L; LOO on distinct runs;
  undefined resamples), the minimum and degenerate cases, the figures, the mock report as the golden report, the
  expected answers, the named constants (`LINEAR_NMIN`, `LINEAR_ALPHA`, `LINEAR_LEVEL`, `LINEAR_MIN_RUNS`,
  `LINEAR_BOOT_TAG`).
- **`uncertainty.md`:** the bootstrap as the linear model uses it (0040, 0041; V1–V7 through `ema.numerics.intervals`),
  each usable run's level passed to the method (the seam for subsampling the levels).
- **`contracts.md`:** C1–C19 run over it by registration (`tests/contracts/diagnostic.py`).
- **Records:** 0068 (`ema.numerics.fitting`), 0073 (plain Unicode text, a table's `title` under it, `seed` and
  `distinct` in the interval settings), 0075 (the base API).

## Out of scope for this step

- The workspace, the runner, and the store (step 14): the known-answer tests build run batches from the reference
  models' functions (`tests/support/reference.py`), as step 09's do.
- Subsampling the levels (the spec's "Later").

## Tasks

1. This plan and record 0078.
2. Tests first: `tests/unit/diagnostics/test_linear_model.py` (the declarations, LM1–LM9, R4a, R4b, R5 y and z,
   the golden report; LM10's known answers at 20,000 runs in the slow tier).
3. Code `src/ema/diagnostics/linear_model.py` and `src/ema/diagnostics/_fits.py` (helpers the polynomial model
   may share: the sampler reader, a fit's values, the bootstrap's two estimators, the per-level table).
4. `docs/index.md`'s API list.
5. Run every check in `CLAUDE.md` (the fast tier with `-n auto`, record 0084); measure the lines.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run
  mypy`; `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto
  tests/unit/diagnostics/test_linear_model.py`.
- Lines of `linear_model.py` (and `_fits.py`) against the roadmap's 300.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0078's, numbered as there, one line each.

1. `sampler` is read as any name, and refused when the design is built ("sampler X comes in a later version",
   designs.md's wording), so C14's other value parses.
2. The per-level table's coefficients are printed without units, and its title names them ("Coefficients in
   m³/yr."), as the mock does (DIAG-10d); with a dimensionless model prediction the title has no such sentence.
3. With a constant model prediction, no per-level table: its fits are of one value (only rounding in the slopes);
   the shared observations stay.
4. A fit of rank below d + 1 on level L's usable runs: no estimates, and a note naming the rank (0051's rule).
5. A point estimate that is undefined with a defined fit (the LOO error, a run of leverage 1): no estimate, and a
   note saying why (uncertainty.md, Rules).
6. Undefined resamples are counted per estimate, keyed by the estimate's label (V4; record 0073 item 4).
7. The coefficients table's title names the log ranges: "(r through its logarithm)", "(r, k through their
   logarithms)", nothing with none.
8. Keys: estimates `intercept`, `slope`, `relative_residual`, `r2`, `loo`; the per-level table's `usable` and
   the same; a column below the minimum, or a value undefined, is "none".
9. The slopes figure names the model parameters as its x tick labels, set with matplotlib directly and escaped by
   `plotting.axis_label` (no categorical-axis helper in `ema.plotting`; no shared file changed).
10. Each usable run's level is passed to the interval method (uncertainty.md: "with their levels when the design
    has them"); the bootstrap ignores it.
11. The example request (contract): the defaults and seed 0; at d = 3, 8, 16, 32 runs.

## Notes

- **Built:** `src/ema/diagnostics/linear_model.py` (`LinearModel`, registered; `LINEAR_ALPHA`, `LINEAR_LEVEL`,
  `LINEAR_BOOT_TAG`, `linear_nmin`, `linear_min_runs`), `src/ema/diagnostics/_fits.py` (private: `SamplerName`,
  `fit_values`, `loo_error`, `estimators`, `level_of`, `per_level`, `bins`), and
  `tests/unit/diagnostics/test_linear_model.py`. Shared files: `docs/index.md` (a block of its own),
  `tests/slow/test_wheel.py` (the two modules), `tests/unit/diagnostics/test_base.py` (its registry test named only
  `point_run` in "the diagnostics are ..."; now any sorted list ending in it, for steps 10–13).
- **Tests:** 20 fast and 5 slow in `test_linear_model.py` (LM1–LM9, R4a, R4b, R5 y and z, the golden report; LM10's
  known answers at 20,000 runs for R1, R2, R3, R7, R10, slow); the contract's 19 checks over the linear model pass.
  The golden report matches the mock with no difference, its intervals included (the bootstrap from
  `LINEAR_BOOT_TAG`'s stream reproduces `docs/checks/linear_model.out`'s to 4 digits). Every known answer is within
  its tolerance. Tests of point estimates use a stub interval method (`Skipped`), so only LM2, LM4, the golden
  report, and the contract pay for the bootstrap.
- **Times** (the machine at a load average of 9–15, with other steps' agents running): the whole fast tier with
  `-n auto`, 1,677 passed, 31 skipped, in about 140 s (the brief's baseline was 22 s on a quieter machine); this
  step's share, about 25 s of CPU in the contract (C7 alone about 5 s: 11 bootstraps) and 9 s in its own tests,
  spread over 8 workers. The slow known answers: 21–44 s each, 51 s with `-n auto`. Each bootstrap is about 2,000
  calls of `fitting.least_squares`, 0.15–0.5 s, dominated by the wrappers' call overhead (record 0078,
  Consequences).
- **Size** (code lines without docstrings, comments, or blanks, counted as step 09 did): `linear_model.py` 294,
  `_fits.py` 59: 353 against the roadmap's 300. Ruff's formatter puts each of the parameter table's 8 arguments on a
  line of its own (34 lines for 5 parameters).
- **v1:** nothing read, run, or ported; the independent numbers are `docs/checks/linear_model.py`'s.
- **Deferrals:** none of the spec's items.
- **Checked by eye:** the three figures on R3's mock (the shadow's curvature about the fitted line, the slopes with
  their bars and the model parameters' names, the residuals' 8 bins).
