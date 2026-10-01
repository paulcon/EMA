# 0018. Write reports in Markdown with TeX math, and make PDFs with pandoc when it is installed

**Date:** 2026-09-29. **Status:** accepted; its step-12 plan amended by 0059. **Resolves:** none (TODO step 3, scope).

## Context

`../design/purpose.md` promises a report for each diagnostic evaluation, with plots and variability
intervals. The use cases require a report that is byte-identical when the same steps run again (U1), and
when a diagnostic result is reproduced (U8), and that the analyst can share with colleagues or in a paper's
supplement (U1, U2). The architecture draft renders Markdown (`../design/architecture.md` §6).

Reports name estimates such as Sobol indices, S_i and S_T,i, with their intervals. Markdown has no single
convention for math: GitHub renders `$…$`, and many viewers show it raw. The routes to a PDF considered were:
reportlab (pure Python; math as Unicode, or matplotlib's mathtext as images), pandoc with LaTeX (full TeX
math; a system install), matplotlib alone (every page a figure), and WeasyPrint (no math; system libraries).

## Decision

We will write one report per diagnostic evaluation, in Markdown, with PNG figures, each with its data card.

- **Math in the report text is TeX,** between `$…$`. Figures use matplotlib's mathtext.
- **The Markdown report is the reference:** it, the figures' data cards, and the diagnostic result are
  byte-identical on rerun and on reproduction (U1, U8).
- **A PDF is made by pandoc, with LaTeX, when the user has them installed.** EMA doesn't depend on either;
  without them, asking for a PDF gives an error that says what to install. The PDF is not held to byte
  identity; a test checks that it contains the report's numbers.

## Alternatives considered

- **Unicode math, no TeX:** readable in every Markdown viewer, but no display formulas, and a PDF route with
  weaker math.
- **reportlab:** pure Python, no system install, and byte-identical output, but a second renderer of about
  300–500 lines, a runtime dependency, and math only as Unicode or mathtext images.
- **matplotlib alone:** no new dependency, and mathtext everywhere, but text and tables laid out by hand.
- **WeasyPrint:** good typesetting, but no math, and system libraries to install on macOS.
- **No PDF in v2.0:** the least work; the analyst converts the Markdown themselves.

## Consequences

- **`../design/scope.md`:** the reports row, and "Not in v2.0": HTML reports.
- **`../design/architecture.md`** (step 9): how a PDF is asked for (a CLI flag and a workspace argument, or a
  function), counted against the budgets of public names and CLI commands.
- **Step 12:** pandoc and a LaTeX distribution are an optional install, planned as staged steps for the owner
  (`../../CLAUDE.md`, "Costs and installs"); the PDF test is skipped when they are missing.
- **Step 6:** each diagnostic spec's mock report uses TeX for its symbols.
- The Markdown shows `$…$` raw in viewers that don't render math.
