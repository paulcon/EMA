"""Figures with their data cards (architecture.md §6, layer 3a; diagnostics/shared.md, Figures; record 0073).

The diagnostics draw every figure through these functions: ``new_figure``, the drawing helpers, ``axis`` for each
axis and its data card entry, ``strip`` for the runs not usable, ``card_points``, and ``save``.
"""

from ema.plotting.figures import (
    axis,
    axis_label,
    bin_means,
    card_points,
    card_text,
    empty_panel,
    histogram,
    hline,
    intervals,
    line,
    new_figure,
    points,
    save,
    spectrum,
    strip,
    title,
    vline,
)

__all__ = [
    "axis",
    "axis_label",
    "bin_means",
    "card_points",
    "card_text",
    "empty_panel",
    "histogram",
    "hline",
    "intervals",
    "line",
    "new_figure",
    "points",
    "save",
    "spectrum",
    "strip",
    "title",
    "vline",
]
