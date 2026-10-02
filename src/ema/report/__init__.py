"""The Markdown report of a diagnostic result, and its PDF (architecture.md §6, layer 3a; 0018; record 0073).

``render`` lays out a stored result and its model version's spec (diagnostics/shared.md, S1-S4), and ``to_pdf``
makes the PDF through pandoc and lualatex (0059 item 8). This package never imports ``ema.diagnostics`` (§1).
"""

from ema.report.pdf import to_pdf
from ema.report.render import EXPLAIN_INTERVALS, render

__all__ = ["EXPLAIN_INTERVALS", "render", "to_pdf"]
