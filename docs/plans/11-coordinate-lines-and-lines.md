# 11. Coordinate lines and lines

**Status:** in progress (demo; record 0066); its choices are record 0077. **Branch:** `demo-11-lines`.
**Updated:** 2026-10-02.

## Goal

Coordinate lines and lines are registered diagnostics: each line's Gram spectrum, degrees above the floor, and
decay rate as observations, one figure per line, the reports matching both mocks; R8, a command-line program, runs
through the runner for its golden report.

## Implements

- **`diagnostics/coordinate_lines.md`:** CL1–CL10, the Named constants, the Expected answers, the mock report and
  figures.
- **`diagnostics/lines.md`:** LN1–LN9, the two modes, the ends tables, the Expected answers, the mock report and
  figures.
- **`diagnostics/shared.md`:** the report's sections, the notes (a constant line's), the figures and data cards
  (S9, S10) for these two.
- **`contracts.md`:** C1–C19 over both (registered); C5's and C6's rules for the rate (0048); the shared anchor's
  rows in the contract's fixture.
- **Records:** 0038 (the Gram spectrum, observations only), 0048 (rate tolerances, open markers), 0058 (R3's
  tolerance, R10's given lines), 0068 (`ema.numerics.gram`: the caller's window and floor), 0073 (plotting and
  report conventions, `lines_through_anchor`), 0075 (the base).
- **`reference_models.md`:** R1, R2, R3, R4a, R4b, R5, R7, R8 (through `ema.runner`), R10, R11 as these specs use them.

## Out of scope for this step

- The workspace (step 14): the reuse key, W5, the rerun's price come from it; here the R8 test drives the runner and
  approval directly, and the other known answers build batches from the reference models' functions.
- The other diagnostics (steps 10, 12, 13).

## Tasks

1. Plan and record 0077.
2. Tests first: `tests/unit/diagnostics/test_coordinate_lines.py` (CL1–CL10, the Expected answers, the exact-rational
   helper, R8 through the runner, slow), `tests/unit/diagnostics/test_lines.py` (LN1–LN9, the Expected answers, the
   golden report and R5, slow); the contract's fixture fix for runs in several rows.
3. Code `src/ema/diagnostics/{_lines,coordinate_lines,lines}.py`.
4. Extend `docs/index.md` (a block of its own), the wheel test's modules; the Provenance line's none parameters.
5. Run every check in `CLAUDE.md`; measure the lines.

## Checks before reporting done

- `uv run pytest -q -n auto && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto` for this step's tests.
- Lines of the three modules against the roadmap's 550.

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0077's, numbered as there, one line each.

1. One base, `LinesDiagnostic`, with hooks; a line's analysis `analyze`, its spectrum panel `draw_spectrum`.
2. Cells by precedence: no usable run; the diagnostic constant; runs not usable; a constant line; the spectrum.
3. Usable and degrees as text, range and length as doubles, the rate a double or "none ..."; ends as `fmt` text.
4. k* is declared with the rate's "through a logarithm" flag: C5 holds it exactly, C6 leaves it out with the rate.
5. Two stacked panels; the anchor marked but on random lines; one caption; the card's `panels`, `line`, `spectrum`.
6. CL9's card c_k are checked against the line's Gram coefficients; the result holds no c_k.
7. Length and distances from the recorded ends in unit coordinates.
8. `design_identity` asks the generator for the size: every refusal comes before building.
9. The identity's seed is the request's, as the point run's.
10. `m`'s default is none with `lines`; both, or neither, are refused.
11. The Provenance line leaves out a none parameter (`render.py`, one line).
12. Small example requests (n = 9, m = 2) with nested other values.
13. Table keys `ends_0`..., `line_rates`; the note's code `constant_line`.
14. The contract's batch builder: a run in several rows is one run; C2 counts distinct runs.
15. C6 skips numbers declared through a logarithm.
16. Step 09's registry test accepts other registered diagnostics.
17. R8 through the runner, interrupted after 41 runs and rerun: the mock's 56 new, 41 reused (slow).
18. The exact-rational rate as a test helper.

## Notes

- **Built:** `src/ema/diagnostics/{_lines,coordinate_lines,lines}.py`; tests in
  `tests/unit/diagnostics/{test_coordinate_lines,test_lines}.py`. Shared files changed: `src/ema/report/render.py`
  (one line), `tests/contracts/diagnostic.py`, `tests/support/diagnostics.py`, `tests/unit/diagnostics/test_base.py`
  (one line), `docs/index.md`, `tests/slow/test_wheel.py`.
- **Size** (code lines without docstrings, comments, or blanks; step 09's count): `_lines.py` 222,
  `coordinate_lines.py` 84, `lines.py` 148: 454 against the roadmap's 550.
- **v1:** not run. Every expected answer was already checked independently by `docs/checks/gram_rates.py` (step 11
  of the design, 2026-10-01); the tests compare EMA with the specs' values and with exact rational arithmetic on the
  same runs (within 10⁻⁹ on R7's lines). Nothing ported.
- **Deferrals:** none of the specs' requirements.
- **The fast tier:** this step's tests take about 2 s serially on a quiet machine (LN6's one PNG the largest share),
  plus the contract's 38 checks over the two diagnostics, about 7 s serially (18 two-panel PNGs, 0.1–0.4 s each);
  `-n auto` spreads both. The slow tier: R8 through the runner (about 20 s), R7's golden report (5 PNGs), CL9's
  figures on R5, and R5's random lines (timeouts).
- **Review round 1** (0 blockers, 0 major, 1 minor, 3 nits; fixed on `demo-diagfix`, record 0077 items 19–20): a
  parametrized test of `analyze(...).cells(...)`'s precedence over four paths; C6's skip of numbers through a
  logarithm limited to `C6_LOG_SKIP` = coordinate lines and lines, with a broken toy in the meta-test.
