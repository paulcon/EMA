"""The polynomial model: a least-squares polynomial fit of the model prediction in unit coordinates.

diagnostics/polynomial_model.md (PM1-PM12): on a convergent design, the fit over level L's usable runs in the
orthonormal Legendre terms of total degree <= p; its relative residual, R², and leave-one-out error (PRESS); the
first-order and total Sobol indices of the fitted polynomial; the root energy √E_k per total degree; bootstrap
intervals from the polynomial model's stream (``POLY_BOOT_TAG``), the P coefficients in ``extra`` (0041); the fit at
each level as observations, the relative residual and R² among them, without intervals (0085); four figures. Records
0012, 0039, 0041, 0049, 0051, 0052, 0068 (the numerics), 0073 (plain Unicode text, tab-separated label cells, titles
under tables), 0075 (the base), 0079 (this step's choices), and 0085.
"""

import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from ema.designs import samplers
from ema.diagnostics._fits import IN_SAMPLE_SENTENCE, LEVELS_SENTENCE
from ema.diagnostics._lines import SPECTRUM_YMIN
from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
    DecimalText,
    DiagnosticBase,
    DiagnosticParameter,
    Integer,
    Name,
    Transform,
    estimate,
    identity,
    interval_info,
    register,
    seed_parameter,
)
from ema.numerics import basis as bases
from ema.numerics._vector import matvec
from ema.numerics.fitting import least_squares, press, r2, relative_residual
from ema.numerics.intervals import Estimator, Interval
from ema.numerics.sobol import degree_energy, sobol_indices
from ema.plotting import figures as plotting
from ema.types.design import DesignIdentity
from ema.types.errors import RequestError
from ema.types.model import ModelSpec
from ema.types.requests import Progress
from ema.types.results import (
    DiagnosticResult,
    Estimate,
    EstimateTable,
    Figure,
    Note,
    Observation,
    ObservationTable,
)
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.space import ModelParameterSpace, Scale

#: The default degree p: the smallest step past the linear model (polynomial_model.md, Named constants).
POLY_DEGREE = 2
#: n_min's default is ``POLY_NMIN``·P: twice the coefficients, as U4 assumes.
POLY_NMIN = 2
#: The default error factor per level, as the linear model's: the points about double per level.
POLY_ALPHA = "0.7072"
#: The default last level: about 8P points (G7).
POLY_LEVEL = 2
#: The fewest usable runs for estimates is ``POLY_MIN_RUNS``·P: a resample keeps about 1.26P distinct runs.
POLY_MIN_RUNS = 2
#: The spawn key of the polynomial model's bootstrap stream (shared.md, Random draws in a diagnostic).
POLY_BOOT_TAG = 2**32 + 3
#: The bootstrap's progress is reported about this often, in seconds (PM10).
PROGRESS_SECONDS = 1.0

_SAMPLER = "the sampler (0032); convergent needs a nested one."
_BASIS = "the set of terms; v2.0 accepts only total_degree. Part of the request's identity, not the design's."
_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_FIT, _SOBOL, _DECAY, _RESIDUALS = (f"polynomial_model_{s}" for s in ("fit", "sobol", "decay", "residuals"))
_TABLES = {"loo": Transform.UNCHANGED, "sobol": Transform.UNCHANGED}
_TABLES |= {"levels": Transform.UNCHANGED, "decay": Transform.SCALED}


def n_terms(d: int, degree: int) -> int:
    """Return P = C(d + p, p), the number of terms of total degree at most p (PM2)."""
    return math.comb(d + degree, degree)


def _n_min(d: int, others: Mapping[str, Any]) -> int:
    return POLY_NMIN * n_terms(d, int(others["degree"]))


def _term_label(alpha: Sequence[int], names: Sequence[str]) -> str:
    """Return a term's name: "ψ₁(rw)·ψ₁(Hu)"; "ψ₀" for the constant."""
    parts = [f"ψ{str(k).translate(_SUBSCRIPTS)}({name})" for k, name in zip(alpha, names, strict=True) if k]
    return "·".join(parts) or "ψ₀"


def _log_names(ctx: AnalysisContext) -> str:
    """Return " (r through its logarithm)" for the log-scale varied model parameters, or ""."""
    logs = [n for n in ctx.space.varied(ctx.spec) if ctx.space.ranges[n].scale is Scale.LOG]
    if not logs:
        return ""
    if len(logs) == 1:
        return f" ({logs[0]} through its logarithm)"
    return f" ({', '.join(logs[:-1])} and {logs[-1]} through their logarithms)"


def _finite_or_none(value: float) -> float | str:
    return float(value) if math.isfinite(value) else "none"


def _bytes(n: int) -> str:
    """Return a size in kB, MB, or GB to 2 significant digits: "200 MB", "7.2 GB"."""
    for unit, size in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if n >= size:
            return f"{float(f'{n / size:.2g}'):g} {unit}"
    return f"{n} B"


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} s"
    if seconds < 3600:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"


class _Fit:
    """One fit's numbers on a set of runs: the coefficients, relative residual, R², Sobol indices, √E_k, LOO.

    ``drawn`` holds those with intervals refitted as drawn: the Sobol indices, √E_k, and the coefficients. The
    relative residual and R² are observations, with no interval (record 0085); a resample computes neither.
    """

    def __init__(self, A: np.ndarray, y: np.ndarray, terms: np.ndarray, *, resample: bool = False) -> None:
        self.fit = least_squares(A, y)
        self.rank = self.fit.rank
        coef = self.fit.coefficients
        self.first, self.total = sobol_indices(coef, terms, y=y)
        self.drawn = np.concatenate((self.first, self.total, degree_energy(coef, terms), coef))
        self.relative_residual = math.nan if resample else relative_residual(y, self.fit)
        self.r2 = math.nan if resample else r2(y, self.fit)
        self.loo = math.nan if resample else press(A, y, self.fit)  # a resample's is on its distinct runs


class PolynomialModel(DiagnosticBase):
    """The polynomial model (polynomial_model.md): its declarations, design, numbers, and figures."""

    name = "polynomial_model"
    title = "Polynomial model"
    summary = (
        "a least-squares polynomial fit in unit coordinates over a convergent design: its fit, leave-one-out "
        "error, Sobol indices, and root energy per degree"
    )
    # Each row: name, type, default, default's text, meaning, changes the design?, a second value, reader (C14, C55).
    parameters = (
        *(
            DiagnosticParameter(*row)
            for row in (
                ("degree", "integer ≥ 1", POLY_DEGREE, "2", "p, the largest total degree of a term.",
                 "yes (through n_min's default)", 3, Integer(1)),
                ("n_min", "integer ≥ 1", _n_min, "2P", "the size of level 0; P = C(d + p, p) terms.", "yes", 30,
                 Integer(1)),
                ("alpha", "decimal in (0, 1)", POLY_ALPHA, POLY_ALPHA, "the error factor per level (designs.md).",
                 "yes", "0.5", DecimalText(0.0, 1.0)),
                ("level", "integer ≥ 0", POLY_LEVEL, "2", "L, the last level.", "yes", 1, Integer(0)),
            )
        ),
        seed_parameter("the design's seed, and the bootstrap's.", "yes"),
        DiagnosticParameter("sampler", "name", "random", "random", _SAMPLER, "yes", "sobol", Name(samplers.names)),
        DiagnosticParameter("basis", "name", "total_degree", "total_degree", _BASIS, "no", "hyperbolic_cross",
                            Name(bases.names)),
    )  # fmt: skip
    interval_method = "bootstrap"
    spawn_tags = (POLY_BOOT_TAG,)
    has_estimates = True
    header_rows = ("Fit",)
    constant_note = True
    nesting = ("degree", "level")

    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]:
        """Return each number's change under y -> a·y + b (PM8).

        c_0 is a·c_0 + b; c_α and √E_k are scaled by a; the rest are unchanged.
        """
        if table_key == "shared":
            return super().transform(table_key, key)
        if table_key == "coefficients":
            constant = set(key.removeprefix("c:").split(",")) == {"0"}
            return (Transform.AFFINE if constant else Transform.SCALED), False
        return _TABLES[table_key], False

    def strips(self, batch: RunBatch, result: DiagnosticResult) -> Mapping[tuple[str, int], np.ndarray]:
        """Return the fit figure's two panels, each over every run (PM9, C12)."""
        every = np.ones(len(batch.design), dtype=bool)
        return {(_FIT, 0): every, (_FIT, 1): every}

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return degree 1, level 2: 8, 16, 32 points at d = 3.

        Enough for the contract's failure masks, and quick; C18 at d = 20 with the defaults is the slow tier's
        (record 0079).
        """
        return {"degree": 1, "level": 2, "seed": 3}

    def min_runs(self, d: int, params: Mapping[str, Any]) -> tuple[int, str]:
        """Return 2P (``POLY_MIN_RUNS``), and why (PM7)."""
        degree = int(params["degree"])
        P = n_terms(d, degree)
        return POLY_MIN_RUNS * P, f"twice its {P} coefficients at degree {degree}"

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the convergent design's identity (PM1): the basis is the request's, not the design's.

        Raises
        ------
        RequestError
            For a space with no varied model parameter.
        """
        if space is None or not space.varied(spec):
            raise RequestError("the polynomial model needs a space with at least one varied model parameter")
        bases.get(params["basis"])  # "basis X comes in a later version"; the sampler's is identity's (PM1)
        chosen = {"n_min": params["n_min"], "alpha": params["alpha"], "level": params["level"]}
        return identity(
            "convergent", space, chosen, spec, model_version_id, seed=params["seed"], sampler=params["sampler"]
        )

    # ----------------------------------------------------------------------------------------------------------
    # The numbers

    def compute(self, batch: RunBatch, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        """Return the fit's estimates, the coefficients in ``extra``, and the per-level table (PM2-PM7, PM10).

        The estimates are level L's, with intervals from the interval method on the polynomial model's stream; none
        below 2P usable runs or with a constant model prediction (``estimates_allowed``), and none, with a note,
        when A has rank below P (0051).
        """
        params = ctx.request.params
        degree, basis = int(params["degree"]), bases.get(params["basis"])
        names = ctx.space.varied(ctx.spec)
        terms = basis.terms(len(names), degree)
        P = len(terms)
        header = (("Fit", f"degree {degree}, {basis.name} basis: {P} terms"),)
        usable = batch.usable(ctx.request.prediction)
        if not usable.any():
            return Computation(header_rows=header)
        A_all = basis.evaluate(ctx.space.to_unit(ctx.spec, batch.design.points), terms)
        y_all = batch.runs.values[ctx.request.prediction]
        sizes = batch.design.levels or (len(batch.design),)
        levels, level_fits = self._levels(A_all, y_all, usable, terms, sizes, names)
        if not estimates_allowed:
            return Computation(observations=(levels,), header_rows=header)
        rows = np.flatnonzero(usable)
        point = level_fits[-1] or _Fit(A_all[rows], y_all[rows], terms)
        if point.rank < P:
            text = (
                f"The {len(rows)} usable runs don't determine the degree-{degree} polynomial: "
                f"A has rank {point.rank} of {P}."
            )
            return Computation(observations=(levels,), notes=(Note("rank", text),), header_rows=header)
        found = self._bootstrap(ctx, A_all, y_all, rows, np.searchsorted(sizes, rows, side="right"), terms, P)
        estimates, extra, notes = self._tables(ctx, point, found, terms, names, len(rows), degree)
        return Computation(estimates=estimates, observations=(levels,), notes=notes, header_rows=header, extra=extra)

    def _levels(
        self,
        A: np.ndarray,
        y: np.ndarray,
        usable: np.ndarray,
        terms: np.ndarray,
        sizes: Sequence[int],
        names: Sequence[str],
    ) -> tuple[ObservationTable, list[_Fit | None]]:
        """Fit each level on its usable runs among its first n_l points: "none" below 2P or of rank below P (PM6)."""
        P = len(terms)
        fits: list[_Fit | None] = []
        columns: list[list[Observation]] = [[] for _ in range(4 + len(names))]
        for n_l in sizes:
            rows = np.flatnonzero(usable[:n_l])
            fit = _Fit(A[rows], y[rows], terms) if len(rows) >= POLY_MIN_RUNS * P else None
            fits.append(fit)
            ok = fit is not None and fit.rank == P
            values = [math.nan] * (3 + len(names))
            if fit is not None and ok:
                values = [fit.relative_residual, fit.r2, fit.loo, *map(float, fit.total)]
            columns[0].append(Observation("usable", "Usable runs", f"{len(rows)} of {n_l}", ""))
            labels = ["Relative residual", "R²", "Leave-one-out error", f"Total index of {names[0]}", *names[1:]]
            keys = ["rel_residual", "r2", "loo", *(f"total:{n}" for n in names)]
            for k, (key, label, value) in enumerate(zip(keys, labels, values, strict=True)):
                columns[k + 1].append(Observation(key, label, _finite_or_none(value), ""))
        heading = ("The fit at each level", *(f"Level {lvl}" for lvl in range(len(sizes))))
        title = f"{LEVELS_SENTENCE} {IN_SAMPLE_SENTENCE}"
        return ObservationTable("levels", title, heading, tuple(map(tuple, columns))), fits

    def _bootstrap(
        self,
        ctx: AnalysisContext,
        A: np.ndarray,
        y: np.ndarray,
        rows: np.ndarray,
        levels: np.ndarray,
        terms: np.ndarray,
        P: int,
    ) -> dict[str, tuple[Interval, ...]]:
        """Run the interval method (PM5): refits as drawn, LOO on each resample's distinct runs.

        The refits as drawn give the Sobol indices, √E_k, and the coefficients; not the relative residual and R²
        (record 0085).
        """
        d, p = terms.shape[1], int(terms.sum(axis=1).max())

        def drawn(i: np.ndarray) -> np.ndarray:
            return _Fit(A[i], y[i], terms, resample=True).drawn

        def distinct(i: np.ndarray) -> np.ndarray:
            if len(i) < P + 1:
                return np.array([math.nan])
            Ai, yi = A[i], y[i]
            return np.array([press(Ai, yi, least_squares(Ai, yi))])

        labels = (*(f"first{j}" for j in range(d)), *(f"total{j}" for j in range(d)))
        labels += (*(f"energy{k}" for k in range(1, p + 1)), *(f"c{t}" for t in range(P)))
        estimators = [Estimator("drawn", labels, drawn, False), Estimator("distinct", ("loo",), distinct, True)]
        method = ctx.interval_method
        assert method is not None  # the polynomial model declares the bootstrap (C19)
        stream = ctx.stream(self.spawn_tags[0])
        return method.intervals(rows, levels, estimators, stream, self._progress(ctx, len(rows), P))

    def _progress(self, ctx: AnalysisContext, n: int, P: int) -> Callable[[int, int], None] | None:
        """Report A's shape and memory, then the refits about once a second, with the time left (PM10)."""
        report = ctx.on_progress
        if report is None:
            return None
        report(Progress("analysis", 0, 0, f"A: {n} × {P}, {_bytes(8 * n * P)}"))
        start = time.monotonic()
        last = [start]

        def step(done: int, total: int) -> None:
            now = time.monotonic()
            if done in (1, total) or now - last[0] >= PROGRESS_SECONDS:
                last[0] = now
                left = _duration((now - start) / done * (total - done))
                report(Progress("analysis", done, total, f"bootstrap: {done} of {total} refits, about {left} left"))

        return step

    def _tables(
        self,
        ctx: AnalysisContext,
        point: _Fit,
        found: dict[str, tuple[Interval, ...]],
        terms: np.ndarray,
        names: Sequence[str],
        n_u: int,
        degree: int,
    ) -> tuple[tuple[EstimateTable, ...], tuple[EstimateTable, ...], tuple[Note, ...]]:
        """Build the three tables of estimates, the coefficients' table (``extra``), and the notes (S4, 0041, 0049).

        The relative residual and R² are not among them: they are the per-level table's observations (record 0085).
        """
        units, d = ctx.prediction.units, len(names)
        drawn, values = found["drawn"], point.drawn
        undefined: dict[str, dict[str, int]] = {}

        def one(table: str, key: str, label: str, j: int, shown: str) -> Estimate:
            interval = drawn[j]
            undefined.setdefault(table, {})[shown] = interval.undefined
            return estimate(key, label, float(values[j]), interval)

        def table(key: str, title: str, columns: tuple[str, ...], rows: Sequence[Estimate], **kw: Any) -> EstimateTable:
            info = interval_info(ctx, n_u, distinct=kw.get("distinct"), undefined=undefined.get(key))
            return EstimateTable(key, title, columns, tuple(rows), kw.get("units", ""), info)

        one_value = ("Estimate", "Variability interval")
        tables: list[EstimateTable] = []
        notes: list[Note] = []
        if math.isfinite(point.loo):
            (loo,) = found["distinct"]
            undefined["loo"] = {"leave-one-out error": loo.undefined}
            row = (estimate("loo", "Leave-one-out error, relative", point.loo, loo),)
            tables.append(table("loo", "Held out", ("Held out", *one_value), row, distinct="the error"))
        else:
            notes.append(Note("loo_undefined", "The leave-one-out error is undefined: a usable run has leverage 1."))
        if np.isfinite(point.first).all():
            sobol = []
            for i, name in enumerate(names):
                sobol.append(one("sobol", f"first:{name}", name, i, f"{name} first-order"))
                sobol.append(one("sobol", f"total:{name}", name, d + i, f"{name} total"))
            title = (
                f"Of the degree-{degree} polynomial fitted to the runs, under the uniform distribution in unit "
                f"coordinates{_log_names(ctx)}."
            )
            heading = ("Sobol indices of the fitted polynomial", "First-order", "Variability interval", "Total")
            tables.append(table("sobol", title, (*heading, "Variability interval"), sobol))
        else:
            notes.append(Note("constant_fit", "The fitted polynomial is constant (V = 0), so it has no Sobol indices."))
        counts = np.bincount(terms.sum(axis=1), minlength=degree + 1)
        decay = [
            one("decay", f"energy:{k}", f"{k}\t{counts[k]}", 2 * d + k - 1, f"√E_{k}") for k in range(1, degree + 1)
        ]
        title = "√E_k: the standard deviation of the fitted polynomial's terms of total degree k."
        heading = ("Total degree k", "Terms", "Root energy √E_k", "Variability interval")
        tables.append(table("decay", title, heading, decay, units=units))
        first = 2 * d + degree
        coefficients = [
            one("coefficients", "c:" + ",".join(map(str, alpha)), _term_label(alpha, names), first + t, f"c{t}")
            for t, alpha in enumerate(terms.tolist())
        ]
        title = "The coefficients of the fitted polynomial, each of a term of the orthonormal Legendre basis."
        extra = (
            table("coefficients", title, ("Term", "Coefficient", "Variability interval"), coefficients, units=units),
        )
        return tuple(tables), extra, tuple(notes)

    # ----------------------------------------------------------------------------------------------------------
    # The figures

    def figures(
        self, batch: RunBatch, result: DiagnosticResult, ctx: AnalysisContext, out_dir: str
    ) -> tuple[Figure, ...]:
        """Draw the fit's two panels, the Sobol indices, √E_k against the degree, and the residuals (PM9).

        From the runs and the stored result only (P1; 0039, 0048, 0051): ŷ from the stored coefficients, the
        leverages from A's QR. None without estimates; with V = 0, no Sobol or decay figure.
        """
        if not result.estimates:
            return ()
        p, units = ctx.request.prediction, ctx.prediction.units
        tables = {t.key: t for t in (*result.estimates, *result.extra)}
        coefficients = tables["coefficients"].estimates
        basis = bases.get(ctx.request.params["basis"])
        names = ctx.space.varied(ctx.spec)
        terms = basis.terms(len(names), int(ctx.request.params["degree"]))
        A = basis.evaluate(ctx.space.to_unit(ctx.spec, batch.design.points), terms)
        fitted = matvec(A, np.array([e.value for e in coefficients]))
        usable = batch.usable(p)
        y = batch.runs.values[p][usable]
        leverages = least_squares(A[usable], y).leverages
        residuals = y - fitted[usable]
        with np.errstate(divide="ignore", invalid="ignore"):
            held = y - residuals / (1.0 - leverages)
        out = [self._fit_figure(batch, ctx, fitted, held, coefficients, terms, out_dir)]
        if "sobol" in tables:
            out.append(self._sobol_figure(tables["sobol"], names, out_dir))
        energies = tables["decay"].estimates
        if max(e.value for e in energies) > 0:
            out.append(self._decay_figure(energies, p, units, out_dir))
        bins = math.isqrt(len(y))
        counts, edges = np.histogram(residuals, bins)
        fig, (ax,) = plotting.new_figure(1)
        plotting.histogram(ax, edges, counts)
        panel = {
            "x": plotting.axis(ax, "x", f"residual of {p}", units),
            "y": plotting.axis(ax, "y", "number of runs", "", integer=True),
            "bins": [{"lo": edges[i], "hi": edges[i + 1], "count": counts[i]} for i in range(bins)],
        }
        caption = f"The residuals of the {len(y)} usable runs, {bins} bins."
        out.append(plotting.save(fig, {"panels": [panel]}, out_dir, _RESIDUALS, caption))
        return tuple(out)

    def _fit_figure(
        self,
        batch: RunBatch,
        ctx: AnalysisContext,
        fitted: np.ndarray,
        held: np.ndarray,
        coefficients: Sequence[Estimate],
        terms: np.ndarray,
        out_dir: str,
    ) -> Figure:
        """Y against ŷ (left) and against ŷ₋ₖ (right), each with y = ŷ and a strip of the runs not usable at ŷ."""
        p, units = ctx.request.prediction, ctx.prediction.units
        usable = batch.usable(p)
        y, ids = batch.runs.values[p], batch.runs.run_ids
        shown = np.isfinite(held)
        not_usable = np.flatnonzero(~usable)
        kinds: list[Any] = [
            FailureKind.from_code(int(batch.runs.kind[r]))
            if batch.runs.status[r] == RunStatus.FAILED.code
            else "missing"
            for r in not_usable
        ]
        fig, axes = plotting.new_figure(2)
        panels = []
        for ax, x, label in ((axes[0], fitted[usable], f"fitted {p}"), (axes[1], held, f"held-out prediction of {p}")):
            keep = shown if x is held else np.ones(len(x), dtype=bool)
            plotting.points(ax, x[keep], y[usable][keep])
            ends = np.array([min(x[keep].min(), y[usable].min()), max(x[keep].max(), y[usable].max())])
            plotting.line(ax, ends, ends)
            strip = plotting.strip(ax, fitted[not_usable], kinds, False, run_ids=ids[not_usable])
            # Every usable run, a held-out prediction that isn't finite (a leverage of 1) as null: not drawn (PM9).
            points = plotting.card_points(
                ids[usable],
                x=np.where(keep, x, 0.0),
                y=y[usable],
                fitted=fitted[usable],
                held_out=np.where(shown, held, 0.0),
            )
            for point, k, h in zip(points, keep, shown, strict=True):
                point["x"] = point["x"] if k else None
                point["held_out"] = point["held_out"] if h else None
            panels.append(
                {
                    "x": plotting.axis(ax, "x", label, units),
                    "y": plotting.axis(ax, "y", p, units),
                    "points": points,
                    "not_usable": strip,
                }
            )
        card = {
            "panels": panels,
            "coefficients": [
                {"multi_index": alpha, "term": e.label, "value": e.value, "interval": e.interval}
                for alpha, e in zip(terms.tolist(), coefficients, strict=True)
            ],
        }
        caption = (
            f"{p} against the fitted polynomial (left) and against each run's held-out prediction (right), "
            "with the line y = ŷ."
        )
        return plotting.save(fig, card, out_dir, _FIT, caption)

    def _sobol_figure(self, table: EstimateTable, names: Sequence[str], out_dir: str) -> Figure:
        """Draw the first-order and total index of each varied model parameter, side by side, with intervals."""
        fig, (ax,) = plotting.new_figure(1)
        x = np.arange(len(names), dtype=float)
        rows = []
        for series, kind in enumerate(("first", "total")):
            found = [next(e for e in table.estimates if e.key == f"{kind}:{n}") for n in names]
            values = np.array([e.value for e in found])
            lo = np.array([e.interval[0] if e.interval else e.value for e in found])
            hi = np.array([e.interval[1] if e.interval else e.value for e in found])
            label = "first-order" if series == 0 else "total"
            plotting.intervals(ax, x, values, lo, hi, offset=0.15 * (2 * series - 1), series=series, label=label)
            rows.append(found)
        ax.set_xticks(x, [plotting.axis_label(n, "") for n in names], rotation=90 if len(names) > 8 else 0)
        panel = {
            "x": plotting.axis(ax, "x", "model parameter", ""),
            "y": plotting.axis(ax, "y", "Sobol index of the fitted polynomial", "", extent=(0.0, 1.0)),
            "points": [
                {
                    "parameter": n,
                    "first": f.value,
                    "first_interval": f.interval,
                    "total": t.value,
                    "total_interval": t.interval,
                }
                for n, f, t in zip(names, *rows, strict=True)
            ],
        }
        caption = "The first-order and total Sobol indices of the fitted polynomial, with their variability intervals."
        return plotting.save(fig, {"panels": [panel]}, out_dir, _SOBOL, caption)

    def _decay_figure(self, energies: Sequence[Estimate], p: str, units: str, out_dir: str) -> Figure:
        """√E_k against k on a log axis, with intervals; below ``SPECTRUM_YMIN`` of the largest, an open marker."""
        fig, (ax,) = plotting.new_figure(1)
        k = np.arange(1, len(energies) + 1, dtype=float)
        values = np.array([e.value for e in energies])
        lo = np.array([e.interval[0] if e.interval else e.value for e in energies])
        hi = np.array([e.interval[1] if e.interval else e.value for e in energies])
        ymin = SPECTRUM_YMIN * float(values.max())
        plotting.intervals(ax, k, values, lo, hi, ymin=ymin)
        panel = {
            "x": plotting.axis(ax, "x", "total degree k", "", integer=True),
            "y": plotting.axis(ax, "y", "root energy at degree k", units),
            "ymin": ymin,
            "below_limit": [int(j) for j, v in zip(k, values, strict=True) if v < ymin],
            "points": [
                {"k": int(j), "terms": int(e.label.split("\t")[1]), "root_energy": e.value, "interval": e.interval}
                for j, e in zip(k, energies, strict=True)
            ],
        }
        caption = "√E_k against the total degree k, with variability intervals" + (f", in {units}." if units else ".")
        return plotting.save(fig, {"panels": [panel]}, out_dir, _DECAY, caption)


register(PolynomialModel())
