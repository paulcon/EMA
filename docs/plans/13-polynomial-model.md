# 13. The polynomial model

**Status:** in progress (demo; record 0066); its choices are record 0079. **Branch:** `demo-13-polynomial`.
**Updated:** 2026-10-02 (Review round 1 on `demo-13fix`).

## Goal

The polynomial model is a registered diagnostic: on a convergent design, a least-squares fit of the model
prediction in the orthonormal Legendre terms of total degree ≤ p, with its relative residual, R², leave-one-out
error, Sobol indices, and root energy per degree, each with a bootstrap interval; the coefficients in the result;
the fit at each level as observations; four figures; and a report that matches its mock.

## Implements

- **`diagnostics/polynomial_model.md`:** PM1–PM12; the parameters and their defaults (2P, 0.7072, level 2), the
  Fit header row, the computation (QR fit, PRESS, Sudret's indices, √E_k), the uncertainty (refits as drawn, LOO on
  distinct runs, undefined resamples counted), the degenerate cases (too few, constant, rank below P, V = 0), the
  figures, the progress (A's size, refits), the named constants, the expected answers, and the mock report.
- **`uncertainty.md`:** the bootstrap through the interval-method seam (`POLY_BOOT_TAG` = 2³² + 3), the line
  under each table with `seed` and `distinct` (record 0073 items 4, 19), the coefficients in `extra` (0041).
- **`contracts.md`:** C1–C19 over the polynomial model (by registering it); C18 at d = 20 with the defaults in
  the slow tier; C29's last clause (the basis name in the request's identity, record 0068's deferral).
- **Records:** 0012, 0039 (no shadows), 0041, 0048 (open markers), 0049 (V = 0), 0051 (the rank rule, figures with
  no estimates), 0052, 0068 (the numerics, no 1-D BLAS), 0073 (plain Unicode, tab cells, titles), 0075 (the base).

## Out of scope for this step

- The store and the runner: PM10's rerun with 0 new runs and PM11's reuse through the runner are the workspace's
  (step 14); here the design's nesting, an interrupt, and a rerun on the same batch are tested.
- Other bases (hyperbolic cross, OMP): refused as later, as the spec says.

## Tasks

1. Plan and record 0079.
2. Tests first: `tests/unit/diagnostics/test_polynomial_model.py` (PM1–PM12, C29's clause, R4a/R4b, R5; the
   golden report, the expected answers at 20,000 runs, and C18 at d = 20 in the slow tier).
3. Code `src/ema/diagnostics/polynomial_model.py`, registered, so C1–C19 run over it.
4. `docs/index.md` (a block of its own), `tests/slow/test_wheel.py` (the module).
5. Every check in `CLAUDE.md`; measure the lines and the tiers' times.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run
  mypy`; `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto
  tests/unit/diagnostics/test_polynomial_model.py`.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0079's, numbered as there, one line each.

1. The example request is degree 1, level 2 (32 runs at d = 3): the contract stays quick; C18 at d = 20 with the
   defaults is a slow test of this step.
2. `sampler` and `basis` are read as any non-empty name and refused when the design is built ("X comes in a later
   version"), before any run; C14 parses a second value before preparing it.
3. `basis`'s "Changes the design?" reads "no (one basis in v2.0: another is refused)"; the bit-for-bit design under
   another basis is tested with a fake basis registered (C29's clause).
4. `POLY_NMIN` and `POLY_MIN_RUNS` are the factor 2 of "2P".
5. `SPECTRUM_YMIN` = 10⁻¹⁷ is defined here too, relative to the largest √E_k (coordinate lines' is built in step 11).
6. The result's keys: tables `fit`, `loo`, `sobol`, `decay`, `levels`, and `extra`'s `coefficients` (keys
   `c:<multi-index>`, labels "ψ₁(rw)·ψ₁(Hu)", "ψ₀").
7. Undefined resamples are counted per estimate, keyed by a short name ("R²", "rw total", "√E_2").
8. The per-level table shows "none" below 2P usable runs, at rank below P, or where a number is 0/0.
9. Rank below P at level L: the note, no estimates, the observations; the Fit header row is always written.
10. LOO undefined on the usable runs (a leverage of 1): its table left out, and a note.
11. V = 0: no Sobol table, the note, the decay table (zeros), and the fit and residual figures only.
12. Progress: "A: n × P, size" first, then the refits about once a second (and the first and last), with the time
    left.
13. The figures' details: the coefficients in the fit figure's data card; strips at ŷ in both panels; the Sobol
    panel's x axis "model parameter"; the decay card's `ymin` and `below_limit`.
14. `fitting.least_squares` calls LAPACK's `dtrtrs` directly (what `solve_triangular` calls): the same numbers,
    a third less per refit.
15. R2's expected answers at p = 10 compute no intervals (`NoIntervals`, in the test): the estimates don't depend on
    them, and the bootstrap's 1000 refits of 20,000 × 286 take about 15 minutes.
16. C18 at d = 20 with the defaults keeps `D20_SECONDS` = 60 s; under heavy load it fails (Notes).

Review round 1 (record 0079, items 17–25):

17. `D20_SECONDS` = 180 s, twice the measured CPU time of one evaluation at d = 20 (91 s; both refits counted).
18. `SPECTRUM_YMIN` lives in `_lines.py` only; the polynomial model imports it.
19. One reader for a registry's name, `base.Name`: any well-formed name; schema the pattern with `examples`.
20. `basis` is the spec's plain "no"; C14 passes a "no" refused as "comes in a later version" (C29 tests it), and
    refuses a declaration other than "yes", "no", or "yes (…)".
21. V = 0 on real runs: R11's space, degree 1, 8 symmetric runs; skipped where LAPACK gives no exact zeros.
22. The LOO-undefined note is tested (6 runs, one of leverage 1).
23. R2 at p = 10 without intervals is a Test-tiers exception for the owner.
24. This step's fast-tier share is in record 0084.
25. Nits: `dtrtrs`'s info < 0 is an illegal argument; the fit card keeps a non-finite ŷ₋ₖ as null; the Sobol
    legend's swatches are dots with bars; R5's z tested.

## Notes

- **Built:** `src/ema/diagnostics/polynomial_model.py` (452 code lines without docstrings, comments, or blanks,
  against the roadmap's 400); `tests/unit/diagnostics/test_polynomial_model.py` (35 tests: 29 fast, 6 slow). Shared
  files: `src/ema/numerics/fitting.py` (choice 14, +3 lines), `docs/index.md` (a block of its own),
  `tests/slow/test_wheel.py` (the module).
- **The mock report** on R3 matches with no difference (0073 item 6's Provenance edit applied in the test); the
  report was right on the first run, every interval to 4 digits, as `docs/checks/polynomial_model.out` has them.
- **Times, measured while other agents' tests kept the machine's load average at 20–150 on 8 cores** (no idle
  measurement was possible): the fast tier with `-n auto` 39–70 s with this step and 17–37 s without; this step's
  tests sum to about 66 s of the run's 153 s of test time (the contract's 19 checks about 45 s, at 0.7–1.5 s per
  evaluation of 2,000 small QR fits; C2 alone 15 s). The slow tier for this step with `-n auto`: 5 min 21 s
  (R11's bootstrap 313 s, R1 and R10 76 s each, C18 at d = 20 190 s, the golden report 8 s, R2 4 s).
- **C18 at d = 20 with the defaults fails its 60 s under that load:** 134–268 s (155 ms per resample at load 36,
  70 ms at load 12); `contracts.md`'s 19 s was idle and as drawn only, and the LOO refits on distinct runs about
  double it. To be rerun on an idle machine (record 0079 item 16).
- **Verified on the coordinator's merge of step 09's review fixes** (`acfed84`, extracted to a scratch directory
  with this step's files on top): the diagnostic contract and every diagnostics test pass (210 passed).
- **Review round 1** (`demo-13fix`): one C18 evaluation at d = 20 with the defaults, alone, at a load average of
  5–9: 62 s wall, 91 s CPU (QR 42 s, the SVDs of R 11 s, the rest 3 s); in the slow run with `-n auto`, 80 s,
  under the new `D20_SECONDS` = 180 s. That slow run (this step's slow tests and `tests/contracts/diagnostic.py`
  with `--slow -n auto`): 3 min 14 s (R11 at p = 10 125 s, C18 80 s, R1 and R10 at 20,000 runs 32 and 27 s). The
  fast tier with `-n auto`: 41.5 s and 67.6 s wall in two runs at a load of 4–10; this step's share 45 s of 232 s
  of test time (record 0084, Review round 2). `polynomial_model.py`: 453 code lines; `src/ema` 10 fewer net.
- **Fixed on the way:** `docs/index.md`'s step 15 and 16 blocks, broken by the MCP merge (an unclosed `eval-rst`
  fence: the docs build failed with `-E`), are two blocks again.
- **Deferrals:** PM10's and PM11's store parts to step 14 (the seams: `AnalysisContext.on_progress`, the
  convergent design's nesting); the progress throttle's clock (record 0079).
