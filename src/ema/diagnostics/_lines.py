"""The per-line computation and figure that coordinate lines and lines share.

coordinate_lines.md, Computation and Figures; lines.md, Computation; architecture.md §6, ``_lines.py``; records 0034,
0035, 0038, 0048, 0051, 0077. Each line of a lines design (its rows in ``Design.lines``, n evenly spaced points end to
end) is analyzed alone: its usable runs, its range, and, when every run on it is usable and it isn't constant, its Gram
spectrum (``ema.numerics.gram``), the degrees k* of its tail above the floor (``LINE_RATE_FLOOR`` of the line's range,
P6) within the window K = floor((n - 1)/2), and the decay rate over them (CL2, CL3, LN2). ``LinesDiagnostic`` is the two
diagnostics' common base: one observations row per line, a note per constant line, one two-panel figure per line; each
subclass says what a line is called, where its points sit on the figure's x axis, and its design.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from ema.diagnostics.base import AnalysisContext, Computation, DiagnosticBase, Transform
from ema.numerics.gram import decay_rate, degrees_above_floor, gram_coefficients, tail
from ema.numerics.tolerance import is_constant, tolerance
from ema.plotting import axis, card_points, empty_panel, new_figure, points, save, spectrum, strip, title, vline
from ema.types.design import Line
from ema.types.results import DiagnosticResult, Figure, Note, Observation, ObservationTable
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.text import fmt

#: The tail T(k) is fitted while above this fraction of the line's range (coordinate_lines.md; P6).
LINE_RATE_FLOOR = 1e-10
#: The fit uses degrees 1 ... floor((n - 1)·½): the top degrees see only the middle of the line.
LINE_RATE_WINDOW = 0.5
#: The fewest degrees a rate is fitted to.
LINE_RATE_MIN_DEGREES = 3
#: The smallest n accepted: K = floor((n - 1)/2) >= LINE_RATE_MIN_DEGREES.
COORD_MIN_N = 7
#: The fewest usable runs for a diagnostic result with observations: the shared observations need one.
COORD_MIN_RUNS = 1
#: The spectrum panel's lower y limit; a value below it is an open marker on the bottom edge (0048).
SPECTRUM_YMIN = 1e-17
#: How far a decay rate may move under y -> a·y + b (0048); under a·y alone, ``UNITS_LOG_TOL`` = 1e-12. A test
#: tolerance (CL8, LN7, C5), named here as the spec names it.
RATE_SHIFT_TOL = 1e-5

#: Each observation's change under y -> a·y + b (C5). The flag marks the rate's fit, decided at the floor through
#: log10 T(k): the rate, and k*, its degrees (C5's rate tolerances; C6 leaves both out, contracts.md; record 0077).
LINE_TRANSFORMS = MappingProxyType(
    {
        ("line_rates", "usable"): (Transform.UNCHANGED, False),
        ("line_rates", "length"): (Transform.UNCHANGED, False),
        ("line_rates", "range"): (Transform.SCALED, False),
        ("line_rates", "degrees"): (Transform.UNCHANGED, True),
        ("line_rates", "rate"): (Transform.UNCHANGED, True),
    }
)


def window(n: int) -> int:
    """Return K = floor((n - 1)·``LINE_RATE_WINDOW``), the highest degree the rate's fit uses."""
    return int((n - 1) * LINE_RATE_WINDOW)


@dataclass(frozen=True, eq=False)
class LineAnalysis:
    """One line's numbers (coordinate_lines.md, Observations for each line; CL2-CL6).

    Attributes
    ----------
    n, K : int
        The line's points, and its window.
    usable : int
        Its usable runs (rows).
    y_range : float or None
        Max - min over its usable runs; None with none usable.
    c : numpy.ndarray or None
        The Gram coefficients c_0 ... c_(n-1); None with no spectrum.
    T : numpy.ndarray or None
        The tail T(k), k = 0 ... n - 1.
    k_star : int or None
        The degrees above the floor; 0 for a constant line; None with runs not usable.
    floor : float or None
        ``LINE_RATE_FLOOR`` times the line's range.
    fit : tuple of float or None
        (rate, intercept of log10 T at k = 0), or None when k* < 3.
    reason : str or None
        Why the line has no rate: "constant", "2 runs not usable"; None with one.
    constant : float or None
        The line's one value, when it is a constant line among others that vary (its note).
    """

    n: int
    K: int
    usable: int
    y_range: float | None
    c: np.ndarray | None = None
    T: np.ndarray | None = None
    k_star: int | None = None
    floor: float | None = None
    fit: tuple[float, float] | None = None
    reason: str | None = None
    constant: float | None = None

    def cells(self, label: str, units: str) -> tuple[Observation, ...]:
        """Return the row's usable, range, degrees, and rate (as "k* of K", "none", "none: constant")."""
        if self.y_range is None:
            span: Observation = Observation("range", label, "none", "")
        else:
            span = Observation("range", label, self.y_range, units)
        degrees = "none" if self.k_star is None else f"{self.k_star} of {self.K}"
        if self.fit is not None:
            rate: float | str = self.fit[0]
        else:
            rate = f"none: {self.reason}" if self.reason else "none"
        return (
            Observation("usable", label, f"{self.usable} of {self.n}", ""),
            span,
            Observation("degrees", label, degrees, ""),
            Observation("rate", label, rate, ""),
        )


def analyze(y: np.ndarray, usable: np.ndarray, *, all_constant: bool) -> LineAnalysis:
    """Analyze one line's values ``y`` (``(n,)``, in its order) with its usable rows (CL2-CL6, LN2, LN5).

    A line with any run not usable has no spectrum, k*, or rate ("none: 2 runs not usable"); when every usable run
    of the diagnostic gives one double (``all_constant``), each line is "none: constant", with no note of its own;
    a constant line among others (two or more usable runs, one double) is "0 of K", "none: constant", and a note.
    """
    n, K = len(y), window(len(y))
    k = int(np.sum(usable))
    if not k:
        return LineAnalysis(n, K, 0, None, reason=_not_usable(n))
    values = y[usable]
    y_range = float(np.max(values) - np.min(values))
    constant = k >= 2 and is_constant(values)
    complete = k == n
    if all_constant:
        return LineAnalysis(n, K, k, y_range, k_star=0 if complete else None, reason="constant")
    if not complete:
        value = float(values[0]) if constant else None
        return LineAnalysis(n, K, k, y_range, reason=_not_usable(n - k), constant=value)
    if constant:
        return LineAnalysis(n, K, k, y_range, k_star=0, reason="constant", constant=float(values[0]))
    c = gram_coefficients(y)
    T = tail(c)
    floor = tolerance(y, LINE_RATE_FLOOR)
    k_star = degrees_above_floor(T[: K + 1], floor)
    fit = decay_rate(T, k_star, LINE_RATE_MIN_DEGREES)
    return LineAnalysis(n, K, k, y_range, c, T, k_star, floor, fit)


def _not_usable(count: int) -> str:
    return f"{count} run{'' if count == 1 else 's'} not usable"


def _with_units(text: str, units: str) -> str:
    return f"{text} {units}" if units else text


def _kinds(batch: RunBatch, rows: np.ndarray) -> list[Any]:
    """Each row's kind for the strip: its failure kind, or "missing" for an ok run missing the model prediction."""
    runs = batch.runs
    return [
        FailureKind.from_code(int(runs.kind[r])) if runs.status[r] == RunStatus.FAILED.code else "missing" for r in rows
    ]


class LinesDiagnostic(DiagnosticBase):
    """What coordinate lines and lines share: observations only, no draws, one row and one figure per line.

    A subclass sets the declarations and parameters, ``design_identity``, and the hooks: ``label`` (a line's row
    label and its note's "along ..."), ``title_of`` (its figure's title), ``figure_name``, ``caption``, ``position``
    (each point's x on the figure, its axis, and the anchor's mark), ``line_card``, and ``extra`` (lines' Length and
    ends tables).
    """

    takes_space = True
    interval_method = None
    spawn_tags = ()
    has_estimates = False
    constant_note = True
    TRANSFORMS = LINE_TRANSFORMS
    #: The observations table's first column, its columns after "Usable" (lines' "Length"), and the start of its
    #: title, before the rate's sentence (lines' "Length: in unit coordinates. ").
    row_head = "Model parameter"
    extra_columns: tuple[str, ...] = ()
    title_lead = ""

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return ``COORD_MIN_RUNS``: the shared observations need one usable run."""
        return COORD_MIN_RUNS, "the shared observations need one"

    # The hooks

    def label(self, j: int, line: Line, ctx: AnalysisContext) -> tuple[str, str]:
        """Return line j's row label, and the words after "along" in its note."""
        raise NotImplementedError

    def title_of(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return line j's figure title."""
        raise NotImplementedError

    def figure_name(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return line j's figure name."""
        raise NotImplementedError

    def caption(self, ctx: AnalysisContext) -> str:
        """Return every line's figure caption (one, so the report prints them in one paragraph)."""
        raise NotImplementedError

    def position(
        self, batch: RunBatch, j: int, line: Line, ctx: AnalysisContext
    ) -> tuple[np.ndarray, str, str, bool, float | None]:
        """Return each point's x on line j's figure, the x axis's name, units, and log scale, and the anchor's x."""
        raise NotImplementedError

    def line_card(self, j: int, line: Line, ctx: AnalysisContext) -> dict[str, Any]:
        """Return the data card's description of line j."""
        raise NotImplementedError

    def extra(
        self, batch: RunBatch, ctx: AnalysisContext
    ) -> tuple[tuple[ObservationTable, ...], list[tuple[Observation, ...]]]:
        """Return the tables before the rates' table, and each line's cells after its label (lines' Length)."""
        return (), [() for _ in batch.design.lines or ()]

    # The shared work

    def analyses(self, batch: RunBatch, ctx: AnalysisContext) -> list[LineAnalysis]:
        """Return each line's analysis, in line order."""
        p = ctx.request.prediction
        usable = batch.usable(p)
        y = batch.runs.values[p]
        ids = batch.runs.run_ids[usable]
        all_constant = len(np.unique(ids)) >= 2 and is_constant(y[usable])
        lines = batch.design.lines or ()
        return [analyze(y[slice(*ln.rows)], usable[slice(*ln.rows)], all_constant=all_constant) for ln in lines]

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return one row per line (usable, range, k* of K, rate), and a note per constant line (CL4-CL6, LN3, LN5)."""
        if not batch.usable(ctx.request.prediction).any():
            return Computation()
        p, units = ctx.request.prediction, ctx.prediction.units
        lines = batch.design.lines or ()
        found = self.analyses(batch, ctx)
        tables, extra = self.extra(batch, ctx)
        rows, notes = [], []
        for j, (line, a) in enumerate(zip(lines, found, strict=True)):
            label, along = self.label(j, line, ctx)
            cells = a.cells(label, units)
            rows.append((cells[0], *extra[j], *cells[1:]))
            if a.constant is not None:
                value = _with_units(fmt(a.constant), units)
                notes.append(
                    Note("constant_line", f"{p} is the same in all {a.usable} usable runs along {along}: {value}.")
                )
        n = int(ctx.request.params["n"])
        heading = (
            f"{self.title_lead}Decay rate: minus the least-squares slope of log₁₀ of the Gram spectrum's tail against "
            f"the degree, over the degrees whose tail is above 10⁻¹⁰ of the line's range, at most K = {window(n)}. "
            f"Observations of the {n} runs on each line; no variability intervals."
        )
        columns = (self.row_head, "Usable", *self.extra_columns, "Range", "Degrees above the floor",
                   "Decay rate (decades per degree)")  # fmt: skip
        table = ObservationTable("line_rates", heading, columns, tuple(rows))
        return Computation(observations=(*tables, table), notes=tuple(notes))

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return each line's top panel: its own rows (C12)."""
        out = {}
        for figure, line in zip(result.figures, batch.design.lines or (), strict=False):
            mask = np.zeros(len(batch.design), dtype=bool)
            mask[slice(*line.rows)] = True
            out[(figure.name, 0)] = mask
        return out

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw one PNG per line: y along it, and its Gram spectrum, or the reason it has none (CL9, LN6; 0051)."""
        found = self.analyses(batch, ctx)
        lines = batch.design.lines or ()
        return tuple(
            self.draw(batch, ctx, j, line, a, out_dir) for j, (line, a) in enumerate(zip(lines, found, strict=True))
        )

    def draw(self, batch: RunBatch, ctx: AnalysisContext, j: int, line: Line, a: LineAnalysis, out_dir: str) -> Figure:
        """Draw line j's figure and write its data card."""
        p, units = ctx.request.prediction, ctx.prediction.units
        rows = np.arange(*line.rows)
        usable = batch.usable(p)[rows]
        y, ids = batch.runs.values[p][rows], batch.runs.run_ids[rows]
        x, name, x_units, log, mark = self.position(batch, j, line, ctx)
        fig, (top, bottom) = new_figure(2, stacked=True)
        points(top, x[usable], y[usable], joined=True)
        if mark is not None:
            vline(top, mark)
        entries = strip(top, x[~usable], _kinds(batch, rows[~usable]), log, run_ids=ids[~usable])
        title(top, self.title_of(j, line, ctx))
        top_card = {
            "x": axis(top, "x", name, x_units, log=log),
            "y": axis(top, "y", p, units),
            "points": card_points(ids[usable], x=x[usable], y=y[usable]),
            "not_usable": entries,
            "anchor": mark,
        }
        bottom_card, numbers = draw_spectrum(bottom, a)
        card = {"panels": [top_card, bottom_card], "line": self.line_card(j, line, ctx), "spectrum": numbers}
        return save(fig, card, out_dir, self.figure_name(j, line, ctx), self.caption(ctx))


def draw_spectrum(ax: Any, a: LineAnalysis) -> tuple[dict[str, Any], dict[str, Any]]:
    """Draw a line's spectrum panel, and return the panel's card and the spectrum's numbers for the data card.

    ``|c_k| / range`` against k, the tail fit, the floor, the window; or the panel kept empty, with the reason (CL9;
    0048, 0051).
    """
    k = np.arange(1, a.n, dtype=float)
    if a.c is None or not a.y_range:
        x_axis = axis(ax, "x", "degree k", "", integer=True)
        y_axis = axis(ax, "y", "|c_k| / range", "")
        empty_panel(ax, f"no spectrum: {a.reason}")
        return {"x": x_axis, "y": y_axis, "points": [], "text": f"no spectrum: {a.reason}"}, {"reason": a.reason}
    values = np.abs(a.c[1:]) / a.y_range
    shift = math.log10(a.y_range)
    fit = None if a.fit is None else (a.fit[1] - shift, a.fit[0], int(a.k_star or 0))
    spectrum(ax, k, values, ymin=SPECTRUM_YMIN, floor=LINE_RATE_FLOOR, fit=fit, window=a.K)
    panel = {
        "x": axis(ax, "x", "degree k", "", integer=True),
        "y": axis(ax, "y", "|c_k| / range", ""),
        "points": card_points(None, k=k, value=values),
    }
    numbers = {
        "c": a.c,
        "T": a.T,
        "K": a.K,
        "k_star": a.k_star,
        "floor": a.floor,
        "floor_fraction": LINE_RATE_FLOOR,
        "rate": None if a.fit is None else a.fit[0],
        "intercept": None if fit is None else fit[0],
        "intercept_of": "log10(T(k) / range)",
    }
    return panel, numbers
