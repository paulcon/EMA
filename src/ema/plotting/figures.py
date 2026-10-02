"""Figures: one PNG per figure with a JSON data card beside it (diagnostics/shared.md, Figures; S9, S10; 0018).

architecture.md §6 (3a): ``new_figure``, ``axis_label``, ``strip``, ``save``; and the drawing helpers the six
diagnostics' figures need (record 0073; docs/plans/08-figures-and-reports.md, The API the diagnostics call).

Figures are drawn on ``matplotlib.figure.Figure`` with the Agg canvas, never through ``pyplot``, and every function
here runs under matplotlib's default rcParams, then EMA's fixed style (``style.context``; record 0073 item 8), so the
user's backend and rcParams are left alone, and neither changes a figure: not its extent (``axes.xmargin``), nor how
its text is set (``text.usetex`` off, so a spec's text never reaches LaTeX; T10). A spec's names and units print literally (T10): ``axis_label`` and ``title`` escape ``$``, so mathtext never
reads them; EMA's own labels may use mathtext (``axis(..., own=True)``).
"""

import functools
import json
import math
import re
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import matplotlib
import matplotlib.style
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure as MplFigure
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import blended_transform_factory

from ema.types.identity import ID_DTYPE, hex_ids
from ema.types.results import Figure
from ema.types.runs import FailureKind

#: The reference palette's first three categorical slots (all-pairs safe) and its ink (record 0073 item 8).
INK, MUTED = "#0b0b0b", "#52514e"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")

#: EMA's fixed style, over matplotlib's defaults: DejaVu Sans (matplotlib's own), an ASCII minus as in the report
#: (0044), no grid, and never LaTeX (T10).
_RC: dict[str, Any] = {
    "text.usetex": False,
    "font.family": "DejaVu Sans",
    "mathtext.fontset": "dejavusans",
    "font.size": 9.0,
    "axes.titlesize": 10.0,
    "axes.labelsize": 9.0,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "axes.unicode_minus": False,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "lines.linewidth": 1.5,
    "lines.markersize": 4.0,
    "figure.dpi": 100.0,
    "savefig.dpi": 150.0,
}
_PANEL_SIZE = (4.0, 3.0)  # inches
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")  # a figure's name: a plain file name, safe in a Markdown link
_STRIP_Y = -0.05  # the strip's place, in axes coordinates: just below the x axis
#: Held for the whole of each styled call: ``style.context`` sets matplotlib's process-wide rcParams, so two threads
#: drawing at once would read each other's, or the user's (architecture.md §8, Threads; record 0073, review round 2).
#: Reentrant, since a styled function may call another.
_STYLE_LOCK = threading.RLock()


def _styled[F: Callable[..., Any]](fn: F) -> F:
    """Run ``fn`` under matplotlib's default rcParams (not the user's), then EMA's style (record 0073 item 8).

    The style is applied and restored under ``_STYLE_LOCK``, so a draw in another thread never changes it meanwhile
    (S10, P4).
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with _STYLE_LOCK, matplotlib.style.context(["default", _RC]):
            return fn(*args, **kwargs)

    return cast(F, wrapper)


def _literal(text: str) -> str:
    """Escape ``$`` so mathtext doesn't read a spec's text (T10)."""
    return text.replace("$", r"\$")


def axis_label(name: str, units: str) -> str:
    r"""Return ``name [units]``, or ``name`` when dimensionless, printed literally (shared.md, Figures; S9; T10).

    Examples
    --------
    >>> axis_label("T_max", "K"), axis_label("y", ""), axis_label("x", "$m$")
    ('T_max [K]', 'y', 'x [\\$m\\$]')
    """
    return _literal(f"{name} [{units}]" if units else name)


@_styled
def new_figure(n_panels: int, *, stacked: bool = False) -> tuple[MplFigure, Sequence[Axes]]:
    """Return a figure with ``n_panels`` panels, side by side, or one above another when ``stacked``.

    The figure has the Agg canvas; nothing is shown or registered with ``pyplot``.
    """
    if n_panels < 1:
        raise ValueError(f"a figure has at least one panel, not {n_panels}")
    rows, cols = (n_panels, 1) if stacked else (1, n_panels)
    fig = MplFigure(figsize=(_PANEL_SIZE[0] * cols, _PANEL_SIZE[1] * rows), layout="constrained")
    FigureCanvasAgg(fig)
    axes = fig.subplots(rows, cols, squeeze=False)
    return fig, tuple(axes.ravel())


@_styled
def axis(
    ax: Axes,
    which: str,
    name: str,
    units: str,
    *,
    log: bool | None = None,
    own: bool = False,
    extent: tuple[float, float] | None = None,
    integer: bool = False,
) -> dict[str, Any]:
    """Label and scale one axis, after the panel is drawn, and return its data card entry (shared.md; 0049).

    Parameters
    ----------
    ax
        The panel.
    which
        "x" or "y".
    name, units
        The axis's quantity and its units ("" when dimensionless); printed literally, unless ``own``.
    log
        A log axis (a log range's model parameter); None keeps the panel's scale (``spectrum`` and ``intervals``
        with ``ymin`` set theirs to log).
    own
        ``name`` is EMA's own label, which may use mathtext (``"$|c_k|$ / range"``).
    extent
        The shown interval; otherwise matplotlib's, from the data drawn.
    integer
        Integer ticks only (the replicate, the degree).

    Returns
    -------
    dict
        ``{"label", "units", "scale", "extent"}``.
    """
    if which not in ("x", "y"):
        raise ValueError(f"an axis is x or y, not {which!r}")
    label = (f"{name} [{_literal(units)}]" if units else name) if own else axis_label(name, units)
    target = ax.xaxis if which == "x" else ax.yaxis
    if log is not None:
        (ax.set_xscale if which == "x" else ax.set_yscale)("log" if log else "linear")
    scale = ax.get_xscale() if which == "x" else ax.get_yscale()
    (ax.set_xlabel if which == "x" else ax.set_ylabel)(label)
    if extent is not None:
        (ax.set_xlim if which == "x" else ax.set_ylim)(float(extent[0]), float(extent[1]))
    if integer:
        target.set_major_locator(MaxNLocator(integer=True))
    shown = ax.get_xlim() if which == "x" else ax.get_ylim()
    return {"label": label, "units": units, "scale": scale, "extent": [float(shown[0]), float(shown[1])]}


@_styled
def title(ax: Axes, text: str) -> None:
    """Title a panel with a spec's name, or "line 0", printed literally (T10)."""
    ax.set_title(_literal(text), color=INK)


@_styled
def points(ax: Axes, x: np.ndarray, y: np.ndarray, *, joined: bool = False, series: int = 0) -> None:
    """Draw one marker per usable run; ``joined`` links them in order (along a line, or by replicate)."""
    ax.plot(x, y, marker="o", linestyle="-" if joined else "none", color=SERIES[series], markersize=4, linewidth=1)


@_styled
def line(ax: Axes, x: np.ndarray, y: np.ndarray, *, style: str = "solid", series: int = 1, label: str = "") -> None:
    """Draw a polyline: a fitted line, ``y = ŷ``, the tail fit; ``label`` names it in a legend."""
    ax.plot(x, y, linestyle=style, color=SERIES[series], linewidth=1.5, label=_literal(label) or None)
    if label:
        ax.legend(frameon=False, loc="best")


@_styled
def vline(ax: Axes, x: float) -> None:
    """Draw a dotted vertical line: the anchor's value (coordinate_lines.md)."""
    ax.axvline(x, linestyle=":", color=MUTED, linewidth=1)


@_styled
def hline(ax: Axes, y: float, *, dashed: bool = False) -> None:
    """Draw a horizontal reference line: 0 (thin), or the floor (dashed)."""
    ax.axhline(y, linestyle="--" if dashed else "-", color=MUTED, linewidth=0.8)


@_styled
def bin_means(ax: Axes, lo: np.ndarray, hi: np.ndarray, means: np.ndarray) -> None:
    """Draw each bin's mean from its smallest to its largest x, joined as a step line (scatter.md, Figures)."""
    xs = np.ravel(np.column_stack([lo, hi]))
    ys = np.repeat(np.asarray(means, dtype=float), 2)
    ax.plot(xs, ys, color=SERIES[1], linewidth=1.5)


@_styled
def histogram(ax: Axes, edges: np.ndarray, counts: np.ndarray) -> None:
    """Draw bars over the bins ``edges[i]`` to ``edges[i + 1]``, ``counts[i]`` high (scatter's, the residuals')."""
    edges = np.asarray(edges, dtype=float)
    ax.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color=SERIES[0], edgecolor="white", linewidth=1)


def _floor(ax: Axes, x: np.ndarray, ymin: float) -> None:
    """Make ``ymin`` the panel's lower limit, exactly, while the top still follows the data: a sticky edge."""
    (anchor,) = ax.plot(x[:1], [ymin], linestyle="none", marker="")
    anchor.sticky_edges.y.append(ymin)


def _open_below(ax: Axes, x: np.ndarray, values: np.ndarray, ymin: float, series: int) -> np.ndarray:
    """Draw values below ``ymin`` as open markers on the bottom edge (0048); return the mask of those drawn so.

    A NaN is not below ``ymin``: it is drawn as nothing, not as an open marker.
    """
    below = np.asarray(values, dtype=float) < ymin
    if below.any():
        ax.plot(x[below], np.full(int(below.sum()), ymin), marker="o", linestyle="none", markerfacecolor="none",
                markeredgecolor=SERIES[series], markersize=5, clip_on=False)  # fmt: skip
    return below


@_styled
def intervals(
    ax: Axes,
    x: np.ndarray,
    values: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    *,
    offset: float = 0.0,
    ymin: float | None = None,
    series: int = 0,
    label: str = "",
) -> None:
    """Draw each value with its variability interval as a bar (the slopes, the Sobol indices, √E_k).

    With ``ymin``, the y axis is log from ``ymin``, and a value below it is an open marker on the bottom edge (0048);
    its bar is drawn from ``ymin`` up. ``offset`` shifts the points along x, to set two side by side. ``label``
    names the series in a legend whose swatch is a dot with its bar, as drawn (record 0079, Review round 1).
    """
    x = np.asarray(x, dtype=float) + offset
    values, lo, hi = (np.asarray(a, dtype=float) for a in (values, lo, hi))
    shown = np.ones(len(x), dtype=bool)
    if ymin is not None:
        ax.set_yscale("log")
        shown = ~_open_below(ax, x, values, ymin, series)
        lo, hi = np.maximum(lo, ymin), np.maximum(hi, ymin)
        _floor(ax, x, ymin)
    bars = ax.vlines(x, lo, hi, color=SERIES[series], linewidth=1.5)
    if ymin is not None:
        bars.sticky_edges.y.append(ymin)
    ax.plot(x[shown], values[shown], marker="o", linestyle="none", color=SERIES[series], markersize=5)
    if label:  # an empty dot-and-bar, for the legend's swatch only
        empty = np.empty(0)
        ax.errorbar(empty, empty, yerr=np.empty((2, 0)), fmt="o", color=SERIES[series], markersize=5, elinewidth=1.5,
                    label=_literal(label))  # fmt: skip
        ax.legend(frameon=False, loc="best")


@_styled
def spectrum(
    ax: Axes,
    k: np.ndarray,
    values: np.ndarray,
    *,
    ymin: float,
    floor: float,
    fit: tuple[float, float, int] | None = None,
    window: int | None = None,
) -> None:
    """Draw a line's Gram spectrum, ``|c_k| / range`` against k (coordinate_lines.md, lines.md, Figures; 0048).

    Parameters
    ----------
    ax
        The bottom panel.
    k, values
        The degrees 1 ... n - 1 and ``|c_k| / range``; a value below ``ymin`` (an exact zero, or rounding) is an open
        marker on the bottom edge.
    ymin
        The panel's lower limit (``SPECTRUM_YMIN``).
    floor
        Drawn dashed.
    fit
        (β, r, k*): the tail fit 10^(β - r·k) over k = 1 ... k*, labeled "tail fit".
    window
        K: the degrees above it are shaded.
    """
    k = np.asarray(k, dtype=float)
    values = np.asarray(values, dtype=float)
    ax.set_yscale("log")
    below = _open_below(ax, k, values, ymin, 0)
    ax.plot(k[~below], values[~below], marker="o", linestyle="none", color=SERIES[0], markersize=4)
    ax.axhline(floor, linestyle="--", color=MUTED, linewidth=0.8)
    if window is not None and len(k) and window < k.max():
        ax.axvspan(window + 0.5, k.max() + 0.5, color=MUTED, alpha=0.12, linewidth=0)
    if fit is not None:
        beta, rate, kstar = fit
        ks = np.arange(1, int(kstar) + 1, dtype=float)
        line(ax, ks, 10.0 ** (beta - rate * ks), label="tail fit")
    _floor(ax, k, ymin)


@_styled
def empty_panel(ax: Axes, text: str) -> None:
    """Keep a panel, empty, with the reason it is ("no spectrum: constant"), so every line has one layout."""
    ax.text(0.5, 0.5, _literal(text), transform=ax.transAxes, ha="center", va="center", color=MUTED)
    ax.set_xticks([])
    ax.set_yticks([])


@_styled
def strip(
    ax: Axes, x: np.ndarray, kinds: Sequence[FailureKind], log: bool, *, run_ids: np.ndarray | None = None
) -> list[dict[str, Any]]:
    """Draw each run that isn't usable as one × below the axes, at its x, with the count in the strip's label.

    shared.md, Runs not usable; C12. ``log`` sets the x axis's scale. Returns the data card's entries, one per run,
    in the order given: ``{"x", "kind", "run_id"}`` (``run_id`` when ``run_ids`` is given; a kind is a failure's,
    or ``FailureKind``'s value).
    """
    x = np.asarray(x, dtype=float)
    if len(x) != len(kinds) or (run_ids is not None and len(run_ids) != len(x)):
        raise ValueError(f"a strip needs one kind (and run id) per x: {len(x)} x, {len(kinds)} kinds")
    ax.set_xscale("log" if log else "linear")
    entries = card_points(run_ids, x=x)
    for entry, kind in zip(entries, kinds, strict=True):
        entry["kind"] = kind.value if isinstance(kind, FailureKind) else str(kind)
    if not len(x):
        return entries
    transform = blended_transform_factory(ax.transData, ax.transAxes)
    ax.plot(x, np.full(len(x), _STRIP_Y), marker="x", linestyle="none", color=MUTED, markersize=5,
            transform=transform, clip_on=False)  # fmt: skip
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
    by_kind = ", ".join(f"{n} {kind}" for kind, n in counts.items())
    ax.text(1.02, _STRIP_Y, f"× {len(x)} not usable\n({by_kind})", transform=ax.transAxes, ha="left",
            va="center", fontsize=7, color=MUTED)  # fmt: skip
    ax.tick_params(axis="x", pad=10)
    return entries


def _plain(x: Any, where: str) -> Any:
    """JSON data from a card: numpy values and arrays converted, ids as hex; NaN and infinity refused (S10)."""
    if isinstance(x, Mapping):
        return {str(k): _plain(v, f"{where}.{k}") for k, v in x.items()}
    if isinstance(x, np.ndarray):
        if x.dtype == ID_DTYPE:
            return list(hex_ids(x))
        return [_plain(v, where) for v in x.tolist()]
    if isinstance(x, (list, tuple)):
        return [_plain(v, where) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(x):
            raise ValueError(f"a data card is strict JSON: {where} is {x!r}")
        return float(x)
    if x is None or isinstance(x, str):
        return x
    raise ValueError(f"a data card is strict JSON: {where} is a {type(x).__name__}")


def card_points(run_ids: np.ndarray | None, **columns: np.ndarray) -> list[dict[str, Any]]:
    """Return a data card's points: one object per point, its run id first when drawn from a run (S9, C12).

    Parameters
    ----------
    run_ids
        ``(n,)`` of ``ID_DTYPE``, or hex text; None for points drawn from computed numbers.
    **columns
        Each an ``(n,)`` array: the point's coordinates and values ("x", "y", "replicate", ...).

    Raises
    ------
    ValueError
        For columns of different lengths, or a value that isn't finite.
    """
    lengths = {len(v) for v in columns.values()} | ({len(run_ids)} if run_ids is not None else set())
    if len(lengths) > 1:
        raise ValueError(f"a card's columns have one length, not {sorted(lengths)}")
    n = lengths.pop() if lengths else 0
    ids = list(hex_ids(run_ids)) if run_ids is not None else None
    values = {name: _plain(np.asarray(v), name) for name, v in columns.items()}
    out = []
    for i in range(n):
        point: dict[str, Any] = {} if ids is None else {"run_id": ids[i]}
        point.update({name: v[i] for name, v in values.items()})
        out.append(point)
    return out


def card_text(card: Mapping[str, Any]) -> str:
    """Return a data card's text: JSON with sorted keys, indented 2, non-ASCII kept, and a final newline (S10)."""
    return json.dumps(_plain(card, "card"), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


@_styled
def save(fig: MplFigure, card: Mapping[str, Any], out_dir: str, name: str, caption: str) -> Figure:
    """Write ``<name>.png`` and its data card ``<name>.json`` into ``out_dir``, and return the ``Figure``.

    The card gets the figure's name (shared.md: "the figure's name; for each panel, each axis ... and every plotted
    value"), and is checked as strict JSON before anything is written. The PNG has no ``Software`` or time chunk,
    so a rerun on one machine writes the same bytes; S10 holds the card to it.

    Raises
    ------
    ValueError
        For a name that isn't a plain file name (letters, digits, ``_``, ``-``), a card that isn't strict JSON, or
        a card that names another figure.
    """
    if not _NAME.fullmatch(name):
        raise ValueError(f"a figure's name is letters, digits, _, and -, as a file name, not {name!r}")
    if card.get("name", name) != name:
        raise ValueError(f"the card names the figure {card['name']!r}, not {name!r}")
    text = card_text({**card, "name": name})
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    png, json_name = f"{name}.png", f"{name}.json"
    fig.savefig(directory / png, format="png", metadata={"Software": None}, bbox_inches="tight", pad_inches=0.1)
    (directory / json_name).write_text(text, encoding="utf-8")
    return Figure(name=name, png=png, card=json_name, caption=caption)
