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
relaxes an accepted rule (review round 1 tightens T10's pandoc reader, item 11), and three mock reports would
change in a word or a parenthesis on acceptance (Spec edits).

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
   escaped in pandoc's Markdown). Any line ending (`str.splitlines`: `\r\n`, `\r`, U+2028, ...) inside a table cell,
   a table's title, or a caption becomes a space. `.`, `-`, `+`, `:`, `=`, `(`, `)`, `{`, `}`, and `!` are not
   escaped inside a line, but a result's text does start lines (a note, its later lines, a table's title, a
   caption; review round 1 corrected this item, which said it never does), so there a block marker is escaped
   too: `-`, `+`, `:`, or `=` first (a list, a rule, a setext underline, a definition), or the `.` or `)` of `1.`,
   `a)`, `(iv)` before a space. A note's blank lines are dropped and its first line's leading spaces, so no line
   of it is code. A model version prints as its escaped name, `@`, and 12 hex digits: an `@` inside a word is no
   citation. Figure labels escape `$` (`axis_label`), so mathtext never reads a spec's text; EMA's own labels may
   use mathtext (`axis(..., own=True)`).

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
   from the store keeps (canonical JSON sorts keys), so the line is byte-identical on a rebuild (S10). As the mocks
   write them (review round 1): `anchor`, `basis`, `degree`, and `level` print as "level 2", "anchor {}" (a
   parameter that names one of a family), the others as "n = 200"; the point run's runs as "runs: 5 (replicates
   0–4)". Reused runs are not in the line (the header's Runs row counts them; where they came from isn't in a
   result).
7. **Figures:** an image's alt text is the figure's name (a result has no alt text); consecutive figures with
   one caption share a paragraph, then "Data card(s): `a.json`, `b.json`." The point run's measured-noisy record
   prints "The model prediction varies at this point, so name@12 is recorded as measured noisy in y." under its
   observations.

**Figures (`ema.plotting`)**

8. **Style without global changes:** figures are drawn on `matplotlib.figure.Figure` with the Agg canvas, never
   through `pyplot`, and every function in `ema.plotting` runs under matplotlib's default rcParams and then EMA's
   fixed ones (`matplotlib.style.context(["default", _RC])`), so a user's backend and rcParams are left alone and
   change no figure: not its extent (`axes.xmargin`, `axes.autolimit_mode`), nor its text (`text.usetex` is off
   in `_RC`, so a spec's text never reaches LaTeX, T10) (§6's "set once in the module": one dictionary, `_RC`;
   review round 1 replaced `rc_context(_RC)`, which started from the user's rcParams). About 2 ms per call. Colors are
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
    markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart --sandbox --pdf-engine=lualatex` with each font
    named and its directory's absolute path; `report.pdf` is copied beside `report.md`. TeX math in dollars is off
    (review round 1: `$\input{/etc/hosts}$` reached lualatex as math, T10), which costs nothing: the report writes
    no math (`EXPLAIN_INTERVALS` and its sentences have no `$`, and every `$` in a result is escaped); `smart` is off,
    so "--" and quotes print as written; `--sandbox` keeps pandoc to the report and its figures. A temporary path
    with `%`, `#`, `~`, or a space is refused. `PandocMissing` when pandoc or lualatex isn't found, or lualatex
    names a missing file or font; `PdfFailed` otherwise, with LaTeX's error line (a line starting `!` first), or
    when pandoc warns it couldn't fetch a figure. One PDF takes about 4-7 s.

**Tests**

12. **The golden comparator** (`tests/support/reports.py`, 0044) parses a report into its title, sections, tables,
    paragraphs, and notes, and compares them with a mock: numbers with a decimal point or an exponent within one
    unit in the 4th significant digit, integers exactly (S3 prints counts, sizes, and seeds in full; review round
    1: "999 resamples" passed for "1000"), text as rendered (escapes removed, images by file), ids (12 hex digits,
    or an approval's), model version labels, and the model's name not compared, and the Provenance line compared
    too, without its EMA and library versions and with the request's parameters as a set (item 6). A computed
    number that `fmt` prints without a decimal point (1000 to 9999) compares exactly too; a diagnostic step that
    meets one passes `skip` or edits its mock. The diagnostic steps call `differences(rendered,
    mock_report(name))`. Step 08 checks each of the six mocks, rebuilt by hand as a result
    (`tests/unit/report/test_golden.py`), with the two edits of items 1 and 3 applied to the scatter mock in the
    test, and item 6's to the polynomial model's.

**Review round 1** (the independent review of step 08; each fixes a finding)

13. **The shared anchor's rule in one place:** `ema.designs.lines.lines_through_anchor(identity, spec)` returns the
    varied model parameters whose coordinate line has the anchor's run as its middle point, by the rule
    `CoordinateLines` builds with (one private predicate both use); the report's Design row calls it (item 5). The
    report had indexed the varied model parameters' unit coordinates by position among all model parameters,
    which failed when a held one came before a varied one.
14. **The sampler's rate** prints only when the registered sampler's version is the stored `sampler_version`
    (S10, P1: another version's rate is not this design's); otherwise "sampler random 0" alone.
15. **File names:** `save` refuses a figure name that isn't letters, digits, `_`, and `-`, starting with a letter or
    digit, and `render` refuses a stored figure whose PNG or card isn't a plain file name (letters, digits, `_`,
    `-`, `.`, not starting with `.`, no `..`), so an image link can't break or leave the directory (T10).
16. **A NaN in `spectrum` or `intervals`** is drawn as nothing, not as an open marker (0048's markers are for values
    below the lower limit).
17. **GitHub-flavored viewers:** a reader of `report.md` on GitHub may see a bare URL in a model's message as a link
    and `:name:` as an emoji. Accepted: pandoc's reader does neither, the text is unchanged, and escaping every
    `:` and `/` would make the Markdown unreadable as text.
18. **The size overrun:** `ema.plotting` and `ema.report` are 697 code lines against `architecture.md` §11's 540
    (`ema.plotting` 290, 38 of them re-exports; `ema.report` 407: `render.py` 321, `pdf.py` 83), 157 over. About
    120 are the drawing helpers (item 9), figure code §11 counted in the diagnostics' estimates, which shrink by as
    much; about 37 are review round 1's fixes (escaping a line's start, file names, the sampler's version, the
    Provenance line's forms). Proposed: §11's line becomes 700 and `ema.diagnostics`' 1,850 (the total unchanged),
    to be checked when steps 09-13 measure their modules. `ema.designs` grows by 10 (item 13).
19. **`IntervalInfo.settings`' keys** are a convention between the diagnostics and the report: the method's own
    (`resamples`, `percentiles`, `min_defined`), and the diagnostic's `seed` and `distinct` (what is recomputed on
    the distinct runs, "the index"); the report prints `min_defined` nowhere and any other key as `key = value`
    (item 4). Proposed as the rule for steps 09-13, with the spec edits below.

**Review round 2** (a finding left on step 08; fixed with a test)

20. **EMA's styled calls hold one lock** (`figures._STYLE_LOCK`, an `RLock`; S10, P4; `architecture.md` §8,
    Threads): `style.context` sets process-wide rcParams, so two threads drawing at once gave differing PNGs and
    could leave EMA's style in the user's rcParams; now each figure's bytes are the single-threaded ones.

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
  `stacked`; "fixed rcParams, set once in the module" read as item 8 (matplotlib's defaults, then EMA's).
- **`diagnostics/polynomial_model.md`, Mock report:** the Provenance line's "runs: 360 (72 reused from the linear
  model's evaluation)" becomes "runs: 360" (item 6).
- **`trust.md` T10:** pandoc's reader is `markdown-raw_tex-raw_html-raw_attribute-tex_math_dollars-smart`, run with
  `--sandbox` (item 11); a block marker at a line's start is escaped too (item 2).
- **`architecture.md` §4, `ema.designs`:** `lines.py` adds `lines_through_anchor` (item 13).
- **`architecture.md` §11:** `ema.plotting`, `ema.report` 700; `ema.diagnostics` 1,850 (item 18).
- **`uncertainty.md`, the bootstrap's "Gives", and `architecture.md` §5's `IntervalInfo`:** the settings are the
  method's (`resamples`, `percentiles`, `min_defined`) and the diagnostic's `seed` and `distinct` (item 19).
  `data_model.md` is unchanged: settings are inside the stored result's JSON.

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

- **Size:** `ema.plotting` 290 code lines (38 of them re-exports), `ema.report` 407 (`render.py` 321, `pdf.py`
  83): 697 against §11's 540 (item 18).
- Steps 09-13 build their figures with `ema.plotting` and check their golden reports with
  `tests/support/reports.py`; their results follow items 1, 3, and 4.
- The fast tier gains 49 tests (about 1.5 s) and review round 1's 29 (about 1 s); the slow tier 5 PDF and pandoc
  tests (about 25 s serially, skipped without pandoc).
