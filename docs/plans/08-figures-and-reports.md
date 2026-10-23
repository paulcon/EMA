# 08. Figures and reports

**Status:** in progress (demo; record 0066); its choices are record 0073. **Branch:** `demo-08-reports`.
**Updated:** 2026-10-02 (review round 1).

## Goal

A stored diagnostic result and its model spec render as the Markdown report of `diagnostics/shared.md`
(`ema.report.render`), byte-identical when rebuilt from the store, with a PDF through pandoc and lualatex when
they are installed (`to_pdf`); and the diagnostics (steps 09–13) have one small module, `ema.plotting`, that
draws every figure their specs name, as a PNG with its JSON data card.

## Implements

- **`architecture.md` §6 (3a):** `ema.plotting` (`new_figure`, `axis_label`, `strip`, `save`, "the Agg backend
  and fixed rcParams, set once in the module") and the drawing helpers below; `ema.report` (`EXPLAIN_INTERVALS`,
  `render`, `to_pdf`). §1 (AR1: `ema.plotting | ema.report` above layer 2; the report never imports
  `ema.diagnostics`); §10 (the contracts grow: AR1's layer, AR4, AR5, the reference models' contract).
- **`diagnostics/shared.md`:** S1 (the sections in order, an empty one left out), S2 (the header), S3 (numbers by
  `fmt`, integers in full, ids as 12 hex digits, 0055), S4 (`EXPLAIN_INTERVALS` once; one line under each
  estimates table; "none" with its reason, V6), S9 (run ids in the data cards; the strip), S10 (data cards
  byte-identical; the report a pure function of the stored result and spec); Figures (axes `name [units]`, the
  strip below the axes, the data card's axes with `extent`, 0049).
- **Each diagnostic spec's Report, Figures, and Mock report sections:** the report's shape; the figures' kinds.
- **`uncertainty.md`:** the bootstrap's line under the table (step 6), "none: <reason>" (Rules), V4's count of
  undefined resamples in the line, V7 (a fake method's name in the line).
- **`trust.md` T10:** text EMA didn't write prints literally: the report escapes it for Markdown (a block marker at
  a line's start too), pandoc reads with `-f markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart
  --sandbox` (record 0073 item 11, stricter than T10's), and figure labels escape `$` and never reach LaTeX.
- **Records:** 0018 (Markdown with PNG figures; the optional PDF), 0042 (the explanation once per report), 0044
  (golden reports: structure, and numbers within one unit in the 4th digit), 0048 (open markers below the
  spectrum's axis), 0055 (ids as 12 hex digits), 0059 item 8 (lualatex with matplotlib's DejaVu fonts;
  `PandocMissing`, `PdfFailed`).

## Out of scope for this step

- Each diagnostic's figures and its golden report on its reference model (steps 09–13, which call this step's
  functions); C11's `check_report` and C12's `check_figures` (step 09).
- Writing `report.md` into a result's directory, and `Report` (the workspace, step 14).

## Tasks

1. Plan and record 0073.
2. Tests first: `tests/unit/report/test_render.py` (S1–S4, V6, V7, T10, purity), `test_golden.py` (each
   diagnostic spec's mock report, rebuilt as a `DiagnosticResult` by hand, rendered and compared by
   `tests/support/reports.py`, the golden comparator the diagnostic steps reuse, 0044),
   `tests/unit/plotting/test_plotting.py` (labels, the strip, open markers, data cards byte-identical, PNGs
   deterministic), and the slow `tests/slow/test_pdf.py` (0018's numbers and figures in the PDF; T10).
3. Code `src/ema/plotting/__init__.py` and `src/ema/report/__init__.py`; the import contracts; the API reference.
4. Run every check in `CLAUDE.md`; measure the lines.

## The API the diagnostics call

`ema.plotting` (every function draws through its fixed style; the caller passes plain arrays):

| Name | What it draws or returns | Used by |
|---|---|---|
| `new_figure(n_panels, *, stacked=False)` | a figure and its panels, side by side (or stacked) | every figure |
| `axis_label(name, units)` | `name [units]`, `$` escaped (T10) | the axes |
| `axis(ax, which, name, units, *, log=None, own=False, extent=None, integer=False)` | labels and scales one axis (`log=None` keeps the panel's scale; `own=True`: EMA's mathtext, not escaped), and returns its data card entry `{label, units, scale, extent}` (0049); call it after drawing | every axis |
| `title(ax, text)` | a panel's title (a model parameter's name, "line 0"), escaped | scatter, coordinate lines, lines |
| `points(ax, x, y, *, joined=False, series=0)` | one marker per usable run; joined in order along a line or the replicates | scatter, point run, lines, fits |
| `line(ax, x, y, *, style="solid")` | a polyline: a fitted line, `y = ŷ`, the tail fit | linear and polynomial models, lines |
| `vline(ax, x)`, `hline(ax, y, *, dashed=False)` | the anchor (dotted); a line at 0; the floor (dashed) | coordinate lines, point run, slopes |
| `bin_means(ax, lo, hi, means)` | each bin's mean from its smallest to its largest x | scatter |
| `histogram(ax, edges, counts)` | bars over equal-width bins | scatter, the fits' residuals |
| `intervals(ax, x, values, lo, hi, *, offset=0.0, ymin=None, series=0)` | points with their variability intervals as bars; on a log axis, a value below `ymin` an open marker on the bottom edge (0048) | linear model's slopes; Sobol indices; √E_k |
| `spectrum(ax, k, values, *, ymin, floor, fit=None, window=None)` | the Gram spectrum: one marker per degree, open on the bottom edge below `ymin` (0048), the tail fit, the floor dashed, the degrees above K shaded | coordinate lines, lines |
| `empty_panel(ax, text)` | the kept, empty panel with its reason ("no spectrum: constant") | coordinate lines, lines |
| `strip(ax, x, kinds, log, *, run_ids=None)` | each run not usable as × below the axes, the count and kinds in its label; returns the card's entries `{x, kind, run_id}` | every panel along a model parameter, the replicate, a line, w·u, ŷ |
| `card_points(run_ids, **columns)` | a data card's points: `[{run_id, <column>: value, ...}]`, ids as hex | every card |
| `save(fig, card, out_dir, name, caption)` | `name.png` and `name.json` (canonical JSON, indented 2, a final newline; S10), returns the `Figure`; `name` is letters, digits, `_`, `-` | every figure |

**A data card** is `{"name", "panels": [{"x": axis, "y": axis, "points": [...], "not_usable": [...], ...}],
...}`: each panel's axes from `axis`, its points from `card_points` (a point from a run has `run_id`, one from a
computed number has none, C12), its strip's entries from `strip`, and the figure's own numbers beside them (bin
edges and counts, c_k and T(k), K, k*, β and r, w, β₀, ‖β‖). Every number is a full double; numpy values and
arrays are converted, NaN and infinity refused.

`ema.report`: `render(result, spec)` and `to_pdf(report_path)`; what the diagnostics put in a result, so the
report reads as their mock:

- **An estimates table** has `columns` = the row heading, then a value heading and an interval heading for each
  estimate of a row; estimates with one label make one row, in order (the polynomial model's Sobol table: two
  per row). A label may hold several leading cells, separated by tabs (the decay table's "1\t8": the degree and
  its terms). Its `title`, unless it repeats the row heading, opens the line under the table, before
  "Variability intervals: ..." (the linear model's "y ≈ intercept + Σ slope·u, ...").
- **`IntervalInfo.settings`:** the method's own (`resamples`, `percentiles`; `min_defined` not printed), and the
  diagnostic's `seed` and `distinct` (what is recomputed on the distinct runs: "the index", "the error"); any
  other key prints as `key = value` (a fake method's, V7). `undefined` counts print as "Undefined resamples,
  dropped: x1 3."
- **An observations table** has `columns` = the row heading, then one per observation of a row; a row's name is
  its first observation's `label` (tab-separated cells, as above). Its `title`, unless it repeats the row heading
  (the shared table's "Of the 200 usable runs"), is the line under the table (coordinate lines' "Decay rate:
  ...").
- **Text in a result is plain, not Markdown:** labels, columns, titles, notes, captions, and header rows are
  escaped by the report (T10), so EMA's own symbols in them are Unicode (ρ, Sᵢ, √E_k, R², ‖y - ŷ‖), not TeX.
- **Notes** print as a list, a note's later lines indented under it (blank lines dropped). **Figures** with one caption are grouped:
  their images, then the caption and "Data cards: `a.json`, `b.json`." **The point run's** measured-noisy record
  prints its sentence under the observations.
- **The coordinate lines' Design row** names the lines through the anchor by
  `ema.designs.lines.lines_through_anchor(identity, spec)`, the generator's own rule (record 0073 item 13).

## Checks before reporting done

- `uv run pytest -q && uv run lint-imports`; `uv run ruff check && uv run ruff format --check && uv run mypy`;
  `uv run sphinx-build -W --keep-going docs docs/_build/html`; `uv run pytest -q --slow -n auto tests/slow/test_pdf.py`.
- Lines of `ema.plotting` and `ema.report` against `architecture.md` §11's 540 (Notes).

## Stop condition

All checks pass; the report goes to the coordinator (0066). Nothing committed.

## Choices made here

Each is record 0073's, numbered as there, one line each.

1. A result's text is plain; the report escapes all of it (T10), so EMA's own symbols in a result are Unicode.
2. Escaped: `` \ ` * _ [ ] < > $ | ~ ^ @ # & ``, and a block marker at a line's start; any line ending in a cell, a
   title, or a caption becomes a space; a version label's `@` isn't.
3. Tables: estimates with one label form a row; tab-separated leading cells; a table's title printed under it.
4. The line under an estimates table is built from `IntervalInfo` (method, n, resamples, distinct, percentiles,
   other keys, seed; "none" reasons; undefined counts).
5. The header's rows come from the spec, the request, and the design identity; the Design row per generator kind.
6. The Provenance line's request parameters are sorted by name (seed last), as a stored result keeps them; "level 2"
   as the mocks write it; the point run's "runs: 5 (replicates 0–4)".
7. A figure's alt text is its name; figures with one caption share a paragraph.
8. No `pyplot`, no global rcParams: matplotlib's defaults, then `_RC`, in each function (`text.usetex` off), the Agg
   canvas; the reference palette's 3 slots.
9. Drawing helpers beyond §6's four names, so the diagnostics draw one way; a log panel's floor is a sticky edge.
10. PNGs without `Software` or time chunks, 150 dpi, tight; cards sorted, indent 2, strict, a final newline.
11. `to_pdf` runs pandoc in a temporary directory with copies of the report, figures, and fonts; TeX math and
    `smart` off, `--sandbox`.
12. The golden comparator in `tests/support/reports.py`, for steps 09-13; the six mocks checked here; integers
    exactly, the Provenance line compared.
13. Review round 1: `lines_through_anchor` in `ema.designs.lines`, the shared anchor's rule in one place.
14. Review round 1: the sampler's rate only for the stored sampler version.
15. Review round 1: figure names and files plain (`save`, `render`).
16. Review round 1: a NaN drawn as nothing.
17. Review round 1: GitHub's autolinks and emoji accepted.
18. Review round 1: the size overrun, 697 against 540, proposed as §11's 700 and the diagnostics' 1,850.
19. Review round 1: `IntervalInfo.settings`' keys (`seed`, `distinct`) as the diagnostics' convention.
20. Review round 2: one lock (`figures._STYLE_LOCK`) held for each styled call, so threads drawing at once agree.

## Notes

- **Built:** `src/ema/plotting/{__init__,figures}.py`, `src/ema/report/{__init__,render,pdf}.py`; tests in
  `tests/unit/report/{test_render,test_golden,test_to_pdf}.py`, `tests/unit/plotting/test_plotting.py`,
  `tests/slow/test_pdf.py`; support in `tests/support/{reports,results}.py`. Shared files extended:
  `pyproject.toml` (AR1's layer 3a, AR4, AR5, the reference models' contract), `docs/index.md` (a block of its
  own).
- **Times:** fast tier 1,140 passed, 4 skipped, in about 15 s (this step's 49 tests in about 1.5 s); the slow tier
  with `-n auto`, 1,144 passed in about 30 s (this step's 3 PDF tests about 20 s serially).
- **Size** (code lines without docstrings, comments, or blanks): `ema.plotting` 284 (38 re-exports),
  `ema.report` 376; 660 against §11's 540 (record 0073, Consequences: the drawing helpers, about 120, are figure
  code moved out of the diagnostics).
- **Review round 1** (record 0073 items 2, 6, 8, 11, 12 revised; 13-19 new). Fixed: the coordinate lines' Design
  row failed (IndexError) with a held model parameter before a varied one; a user's `text.usetex` sent a spec's
  text to LaTeX and `axes.xmargin` changed a card's extent; `$...$` in a report reached lualatex as math, and
  `smart` rewrote "--"; a block marker at a line's start in a note, a table's title, or a caption made a list or
  rule; only `\n` ended a line; the sampler's rate was read for any version; `PdfFailed` could name a line before
  LaTeX's `!` line; the comparator let integers differ by one and skipped Provenance; the Provenance line's
  `level 2`, `anchor {}`, and "(replicates 0–4)" differed from the mocks; a NaN was drawn as an open marker;
  figure file names weren't checked. Each has a test (29 in the fast tier, 2 in the slow). Times: fast tier
  1,169 passed, 6 skipped, in about 20 s; the slow tier with `-n auto`, 1,175 passed in about 32 s. Size:
  `ema.plotting` 290 (38 re-exports), `ema.report` 407 (`render.py` 321, `pdf.py` 83): 697 against 540 (item
  18); `ema.designs` grows by 10 (`lines.py` 236).
- **Checked by eye:** a coordinate line's two panels (the strip, the open markers on the bottom edge, the tail
  fit, the floor, the window), a scatter panel with bin means, a log panel of intervals, and the linear model's
  mock as a PDF (DejaVu Serif, tables, "≈", "‖", "²").
- **v1:** nothing read or ported (`core/report.py` is rewritten from v2's specs).
- **Deferrals:** alt text from the diagnostic (a `Figure` field, a schema change); PDF polish; the contract that
  the report doesn't import `ema.diagnostics` comes with step 09's layer 3b.
- **For the diagnostic steps:** follow the plan's "The API the diagnostics call"; record `seed` and `distinct` in
  `IntervalInfo.settings`; write EMA's symbols in Unicode; call `tests.support.reports.differences(render(...),
  mock_report("<spec>"))` in the golden report test, applying the scatter mock's two edits (record 0073).
