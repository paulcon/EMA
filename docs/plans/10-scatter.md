# 10. Scatter

**Status:** in progress (demo; record 0066); its choices are record 0076. **Branch:** `demo-10-scatter`.
**Updated:** 2026-10-02.

## Goal

Scatter is registered: one module, `src/ema/diagnostics/scatter.py`, ending with `register(Scatter())`, giving the
mean, standard deviation, rank correlations, and binned first-order indices of a uniform design's usable runs with
bootstrap intervals, its figures, and the mock report as its golden report.

## Implements

- **`diagnostics/scatter.md`:** SC1–SC10, the computation, the bootstrap's differences (distinct runs for the
  index, the undefined resamples), the minimum and degenerate cases, the figures, the mock report, the expected
  answers, the named constants (`SCATTER_N`, `SCATTER_MIN_RUNS`, `SCATTER_BOOT_TAG`, `SCATTER_HIST_BINS`).
- **`diagnostics/shared.md`:** S8 (tag 2³² + 1); S2's and S9's tests (scatter on R5); S1, S4–S7, S10 for scatter
  (the contract and the golden report).
- **`uncertainty.md`:** the bootstrap through `ctx.interval_method` (C19), the index on each resample's distinct
  runs (V3), undefined resamples counted (V4).
- **`contracts.md`:** C1–C19 run over scatter once registered.
- **Records:** 0068 (the numerics; no vector-vector BLAS), 0073 items 1, 3, 4 (Unicode symbols, a table's title
  under it, `seed` and `distinct`), 0075 (the base's API).

## Out of scope for this step

- The workspace (step 14): here batches are built from the reference models' functions on the generator's design.
- Two-model-parameter views (0037).

## Tasks

1. Plan and record 0076.
2. Tests: `tests/unit/diagnostics/test_scatter.py` (declarations; SC1 design and refusals; SC3; SC4 by hand and
   negative; SC5 undefined counts; SC6 at 9 and 10; SC7; SC8, S2, S9 on R5; SC9; degenerate figures; S5 on R4a,
   R4b; the golden report; the known answers, slow); `tests/unit/numerics/test_stats.py` (the column-wise forms).
3. Code `scatter.py`; column-wise estimators in `ema.numerics.stats` (record 0076 item 11).
4. `docs/index.md` (a block of its own), `tests/slow/test_wheel.py` (the module).
5. Run every check; measure the lines.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto` on this step's tests.
- `scatter.py`'s lines against the roadmap's 250.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0076's, numbered as there, one line each.

1. Three estimates tables (`moments`, `rank_correlation`, `binned_index`), keyed by the model parameter's name.
2. ρ and S from the design's values in model parameter units (the same order as unit coordinates).
3. Undefined resamples counted per model parameter in each table's line.
4. `sampler` read as any name; the design refuses an unregistered one with G17's words.
5. Example request n = 20, seed 3.
6. A space with nothing varied refused in `design_identity`, before building.
7. Every scatter figure's y limits the usable range ± 5%; the cards' `parameter` and `bins`.
8. Bin means only with estimates; the captions.
9. The histogram only when the usable y has a range (none with one usable run); its caption counts the runs not
   usable.
10. A model parameter named `histogram` is drawn as `scatter-histogram.png`.
11. Column-wise `rank_correlations`, `binned_indices`, and a numpy `average_ranks` in `ema.numerics.stats`.
12. Estimate-only tests with a fake interval method; R5's timeout raised at once; known answers slow.

## Notes

- **Built:** `src/ema/diagnostics/scatter.py`; `src/ema/numerics/stats.py` extended (item 11); tests in
  `tests/unit/diagnostics/test_scatter.py` and `tests/unit/numerics/test_stats.py`. Shared files extended:
  `docs/index.md` (a block of its own), `tests/slow/test_wheel.py` (the module).
- **The mock report** is reproduced to every printed digit on R2, n = 200, seed 1; the edits to the mock are record
  0073's (items 1, 3), applied in the test.
- **Size:** `scatter.py` 242 code lines against 250; `stats.py` 32 -> 59.
- **Deferrals:** v1's numbers not run (the mock's are an independent computation, `docs/checks/scatter.py`).
