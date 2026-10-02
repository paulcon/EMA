# 0073. Step 08's provisional choices: the report's layout rules, its escaping, the plotting helpers, and the PDF

**Date:** 2026-10-02. **Status:** proposed (provisional; record 0066). **Resolves:** none.

## Context

Step 08 builds `ema.plotting` and `ema.report` (`architecture.md` §6, 3a; plan `../plans/08-figures-and-reports.md`).
`diagnostics/shared.md` gives the report's sections, header, number format, and the line under each estimates
table; each diagnostic spec's mock report gives its shape; `trust.md` T10 says text EMA didn't write prints
literally; 0059 item 8 says how the PDF is made. The result types (step T, record 0070) fix what a result holds,
and §1 says the report renders a stored result and its spec only. Several things a report must print have no
field of their own (the text under a table, a figure's alt text, which estimates share a row), and the specs
don't say which text in a result is EMA's Markdown and which is plain. The choices below fill those gaps; none
changes an accepted rule, and two mock reports would change in a word or two on acceptance (Spec edits).

## Decision

We will, provisionally:

**Text and escaping (T10)**

1. **Every text field of a result is plain text, and the report escapes all of it** (labels, columns, titles,
   notes, captions, header rows, observation text), as it escapes the spec's names, descriptions, and units. A
   result can't mark which part of a note is a model's failure reason or which part of a column heading is a
   spec's name ("| Of the 200 usable runs | y |"), so the report can't escape only those. EMA's own symbols in a
   result are therefore Unicode, not TeX: "Rank correlation ρ", "Binned first-order index Sᵢ", "√E_k", "R²",
   "‖y - ŷ‖". The report's own sentences (`EXPLAIN_INTERVALS`, the headings, the line under a table) are the only
   Markdown it writes unescaped. The stored result stays plain data, not Markdown.
2. **Escaped characters:** `` \ ` * _ [ ] < > $ | ~ ^ @ # & ``, each with a backslash (any ASCII punctuation can be
   escaped in pandoc's Markdown); a newline inside a table cell becomes a space. `.`, `-`, `(`, `)`, `{`, `}`, and
   `!` are not escaped: they act only after an escaped character or at a line's start, where a result's text never
   is (a note's later lines are indented under it). A model version prints as its escaped name, `@`, and 12 hex
   digits: an `@` inside a word is no citation. Figure labels escape `$` (`axis_label`), so mathtext never reads a
   spec's text; EMA's own labels may use mathtext (`axis(..., own=True)`).

**Tables and lines (S1, S4)**

3. **Table conventions** a diagnostic follows: an estimates table's `columns` are the row heading, then a value
   heading and an interval heading per estimate of a row; estimates with the same label form one row, in order
   (the polynomial model's Sobol table, two per row). An observations table's are the row heading, then one per
   observation; a row's name is its first observation's label. A label may hold several leading cells separated
   by tabs (the decay table's degree and its number of terms). A table's `title`, unless it repeats the row
   heading, is printed under the table (an observations table: "Decay rate: ..."; an estimates table: before
   "Variability intervals: ...", the linear model's "y ≈ intercept + Σ slope·u, ..."). A table whose rows don't
   fit its columns is refused with `ValueError`.
4. **The line under an estimates table** is built from its `IntervalInfo`: "Variability intervals: <method> over
   the <n> usable runs", then the settings `resamples`, `distinct` ("<what> recomputed on the distinct runs of
   each resample"), `percentiles`, any other key as `key = value` (sorted; a fake method's, V7), and `seed`;
   `min_defined` is not printed (a constant of `uncertainty.md`). Then each "none" estimate, "<label>: none:
   <reason>." (V6), and "Undefined resamples, dropped: <key> <count>." (V4, keys sorted). A diagnostic records
   `seed` and `distinct` in the settings beside the method's own.
5. **The header's rows** come from the spec, the request, and the design identity: Model prediction "name:
   description, units"; Space "name [lo, hi] units, log" per varied model parameter, "; "-separated; Held "name =
   value units (held value | nominal)", or "none"; the point run's Space "the point a = 1, ... (all nominal);
   every model parameter held" and no Held row (0049); Design per generator kind (uniform, convergent with its
   levels' sizes from the design structure, point, coordinate lines with the anchor and the lines it is on by the
   generator's rule, `SHARED_ANCHOR_TOL`, random lines, given lines); the sampler's rate from the sampler registry
   when it is still registered; Runs "N: new, reused; F failed (k error, ...); M missing y; U usable".
6. **The Provenance line:** "EMA v; numpy v, scipy v, matplotlib v; model version name@12; request: <diagnostic>,
   space as above, <parameters sorted by name, `key = value`, the sampler as "sampler random 1">, seed s,
   prediction y; runs: N; approvals: <12 hex digits> (k new runs)", or "approvals: none (no new runs)". The
   mocks order the request's parameters as each spec lists them; a sorted order is the one a result read back
   from the store keeps (canonical JSON sorts keys), so the line is byte-identical on a rebuild (S10).
7. **Figures:** an image's alt text is the figure's name (a result has no alt text); consecutive figures with
   one caption share a paragraph, then "Data card(s): `a.json`, `b.json`." The point run's measured-noisy record
   prints "The model prediction varies at this point, so name@12 is recorded as measured noisy in y." under its
   observations.

**Figures (`ema.plotting`)**

8. **Style without global changes:** figures are drawn on `matplotlib.figure.Figure` with the Agg canvas, never
   through `pyplot`, and every function in `ema.plotting` runs under `rc_context` with EMA's fixed rcParams, so a
   user's backend and rcParams are left alone (§6's "set once in the module": one dictionary, `_RC`). Colors are
   the reference palette's first three categorical slots (blue, orange, aqua: distinct for color-blind readers
   in every pair) and a muted ink for the × strip and reference lines; ticks use an ASCII minus, as the report.
9. **The helpers beyond §6's four names** (`axis`, `title`, `points`, `line`, `vline`, `hline`, `bin_means`,
   `histogram`, `intervals`, `spectrum`, `empty_panel`, `card_points`, `card_text`), so the six diagnostics draw
   one way and stay small; the plan's table says which diagnostic uses each. `strip` takes `run_ids` and returns
   the card's entries; `new_figure` takes `stacked`; `axis(..., log=None)` keeps a scale `spectrum` or `intervals`
   set. A log panel's lower limit is pinned with a sticky edge, so values below it are open markers on the
   bottom edge (0048) and the top still follows the data.
10. **PNGs and cards:** a PNG is written at 150 dpi with a tight bounding box and no `Software` or time chunk, so
    a rerun on one machine writes the same bytes; a card is `json.dumps` with sorted keys, indent 2, non-ASCII
    kept, and a final newline (S10), numpy values converted, ids as hex, NaN and infinity refused before any file
    is written. The card's layout is `{"name", "panels": [{"x", "y", "points", "not_usable", ...}], ...}`.

**The PDF (0059 item 8)**

11. **`to_pdf` works in a temporary directory:** it checks every figure the report names exists (else
    `PdfFailed`, since pandoc drops a missing one with exit 0), copies the report, its figures, and matplotlib's
    eight DejaVu files (Serif and Sans Mono, four each) there, and runs `pandoc -f
    markdown-raw_tex-raw_html-raw_attribute --pdf-engine=lualatex` with each font named and its directory's
    absolute path; `report.pdf` is copied beside `report.md`. A temporary path with `%`, `#`, `~`, or a space is
    refused. `PandocMissing` when pandoc or lualatex isn't found, or lualatex names a missing file or font;
    `PdfFailed` otherwise, with LaTeX's error line, or when pandoc warns it couldn't fetch a figure. One PDF takes
    about 4-7 s.

**Tests**

12. **The golden comparator** (`tests/support/reports.py`, 0044) parses a report into its title, sections, tables,
    paragraphs, and notes, and compares them with a mock: numbers within one unit in the 4th significant digit,
    text as rendered (escapes removed, images by file), model version labels and the model's name not compared,
    and the Provenance section by its presence. The diagnostic steps call `differences(rendered,
    mock_report(name))`. Step 08 checks each of the six mocks, rebuilt by hand as a result
    (`tests/unit/report/test_golden.py`), with the two edits of items 1 and 3 applied to the scatter mock in the
    test.

## Deferrals

- **Alt text from the diagnostic** (item 7): a figure's name is its alt text until `Figure` holds one; adding a
  field is a schema change for the store (about an hour with step 06's schema).
- **Polishing the PDF** (0059: "PDF polish" may be deferred): the layout is pandoc's default with 2 cm margins;
  wide tables wrap. About an hour (a header template, smaller table text).
- **A forbidden contract "the report doesn't import `ema.diagnostics`"** (§1): the layers contract will enforce it
  once step 09 adds layer 3b; nothing to do here.

## Spec edits on acceptance

- **`diagnostics/scatter.md`, Mock report:** "Rank correlation $\rho$" and "Binned first-order index $S_i$" become
  "Rank correlation ρ" and "Binned first-order index Sᵢ" (item 1); the binned index's line reads "14 bins.
  Variability intervals: ..., seed 1." (item 3: the table's title opens its line).
- **`diagnostics/shared.md`, The report:** "Markdown with TeX math" could add "(the report's own; text in a result
  is plain, escaped)" (item 1); the Provenance line's parameters in sorted order (item 6).
- **`architecture.md` §6:** the plotting helpers (item 9), `strip`'s `run_ids` and return value, `new_figure`'s
  `stacked`; "fixed rcParams, set once in the module" read as item 8.

## Alternatives considered

- **Diagnostics write Markdown, escaping spec text themselves:** EMA's TeX would survive in results, but a stored
  result would hold Markdown escapes, the MCP server's structured data would show them, and every diagnostic
  would need the escaping right; one escape in one place is simpler to test (T10).
- **Escaping only the spec's names when they appear in a result's text:** not reliable (a name `y` is inside
  "y against x1").
- **New result fields** (a caption under each table, alt text, cells beside a label): a schema change for the
  store (step 06), being built at the same time; the title field and tab-separated cells carry them now.
- **`matplotlib.use("Agg")` and a global `rcParams.update`:** simplest, but importing EMA would change a
  notebook's backend and style.
- **Running pandoc in the report's directory:** a path with `%`, `#`, or `~` breaks lualatex (0059).

## Consequences

- **Size:** `ema.plotting` 284 code lines (38 of them re-exports), `ema.report` 376 (`render.py` 294, `pdf.py`
  79): 660 against §11's 540. The helpers of item 9 (about 120 lines) are figure code the diagnostics' estimates
  (§11) counted in their own modules, which shrink by as much.
- Steps 09-13 build their figures with `ema.plotting` and check their golden reports with
  `tests/support/reports.py`; their results follow items 1, 3, and 4.
- The fast tier gains 49 tests (about 1.5 s); the slow tier 3 PDF tests (about 20 s, skipped without pandoc).
