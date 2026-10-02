"""Scatter's known answers (diagnostics/scatter.md: SC1-SC10, Expected answers, the mock report as its golden report).

Run batches come from the reference models' functions on the uniform design (tests/support/reference.py). The
contract (C1-C19, tests/contracts/diagnostic.py) runs over scatter once it is registered: C8 is SC5's and S8's "another
tag moves the intervals, not the design", C7 is S10's byte-identical data cards. Where a test is about estimates, not
their intervals, it uses ``NoIntervals`` (a 1000-resample bootstrap costs about 0.25 s); the golden report, SC5, and
SC9's slow variant use the bootstrap. The known answers at n = 20,000 are slow (record 0076).
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
from collections.abc import Callable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema import reference_models
from ema.designs import samplers
from ema.diagnostics import base
from ema.diagnostics.scatter import (
    HISTOGRAM,
    SCATTER_BOOT_TAG,
    SCATTER_MIN_RUNS,
    SCATTER_N,
    figure_name,
    scatter_bins,
)
from ema.numerics.intervals import Estimator, Interval
from ema.report import render
from ema.types.design import Design
from ema.types.errors import RequestError
from ema.types.identity import hex_ids
from ema.types.results import DiagnosticResult
from ema.types.runs import FailureKind, RunBatch
from ema.types.space import ModelParameterSpace
from ema.types.streams import spawned
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.reports import differences, mock_report

SCATTER = base.get("scatter")
#: shared.md, Named constants.
KNOWN_ANSWER_N = 20_000
KNOWN_ANSWER_SDS = 5  # the tolerances below are scatter.md's, already 5 standard deviations


class NoIntervals:
    """An interval method that calls no estimator and gives every estimate "none": for the tests about estimates."""

    name = "none_here"

    @property
    def settings(self) -> dict[str, Any]:
        return {}

    def intervals(
        self,
        usable: np.ndarray,
        levels: np.ndarray | None,
        estimators: Sequence[Estimator],
        stream: np.random.Generator,
        on_step: Callable[[int, int], None] | None = None,
    ) -> dict[str, tuple[Interval, ...]]:
        return {e.name: tuple(Interval(None, "not computed here", 0) for _ in e.labels) for e in estimators}


def r5(**point: float) -> Any:
    """R5's function, with its timeout region failing at once: a timeout, without the 0.2 s wait (reference.py)."""
    f = reference.function("R5")
    if point["a"] < -0.8 and point["b"] < -0.8:
        raise reference._Timeout
    return f(**point)


def prepare(id: str, *, figures: bool = False, intervals: bool = False, **kw: Any) -> sd.Case:
    """Prepare scatter on a reference model; without its figures, and with ``NoIntervals``, unless asked."""
    case = reference.prepare(SCATTER if figures else sd.NoFigures(SCATTER), id, **kw)
    if not intervals:
        case.ctx = dataclasses.replace(case.ctx, interval_method=NoIntervals())
    return case


def run(id: str, tmp_path: Path, **kw: Any) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    case = prepare(id, **kw)
    made = reference.batch(case, id, fn=r5 if id == "R5" else None)
    return case, made, sd.evaluate(case, made, tmp_path)


def values(result: DiagnosticResult, key: str) -> dict[str, float]:
    """One estimates table's values by label."""
    (table,) = [t for t in result.estimates if t.key == key]
    return {e.label: e.value for e in table.estimates}


def card(directory: Path, name: str) -> dict[str, Any]:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------------------------
# Declarations and the design (SC1)


def test_the_declarations_are_the_specs():
    """scatter.md, Parameters and Named constants: n 200, seed 0, sampler random, each changes the design; the
    bootstrap from tag 2³² + 1 (S8); nested in n (U3); a minimum of 10 usable runs; one bin rule for both."""
    assert (SCATTER_N, SCATTER_MIN_RUNS, SCATTER_BOOT_TAG) == (200, 10, 2**32 + 1)
    assert (SCATTER.takes_space, SCATTER.interval_method, SCATTER.spawn_tags) == (True, "bootstrap", (2**32 + 1,))
    assert (SCATTER.has_estimates, SCATTER.constant_note, SCATTER.nesting) == (True, True, ("n",))
    rows = {p.name: (p.default, p.changes_design) for p in SCATTER.parameters}
    assert rows == {"n": (200, "yes"), "seed": (0, "yes"), "sampler": ("random", "yes")}
    assert SCATTER.min_runs(3, {})[0] == 10
    assert [scatter_bins(n) for n in (10, 15, 16, 200, 20_000)] == [3, 3, 4, 14, 141]


def test_sc1_the_design_is_the_samplers_rows_mapped_to_the_space():
    """SC1 and the mock report: R2, n = 200, seed 1: the points are default_rng(1).random((200, 3)) mapped to the
    space, bit for bit (0032); the identity is uniform's, with n, the seed, and the sampler."""
    case = prepare("R2", params={"n": 200, "seed": 1})
    assert dict(case.request.params) == {"n": 200, "seed": 1, "sampler": "random"}
    space = ModelParameterSpace.parse(reference_models.space("R2"))
    want = space.from_cube(case.spec, np.random.default_rng(1).random((200, 3)))
    assert np.array_equal(case.design.points, want)
    ident = case.identity
    assert (ident.kind, dict(ident.params), ident.seed, ident.sampler) == ("uniform", {"n": 200}, 1, "random")
    assert ident.sampler_version == samplers.get("random").version


def test_sc1_a_space_with_nothing_varied_is_refused_before_building():
    """SC1: a space holding every model parameter is refused; so is a sampler that comes later (G17)."""
    with pytest.raises(RequestError, match="needs a varied model parameter"):
        prepare("R1", space={})
    with pytest.raises(RequestError, match="needs a varied model parameter"):
        prepare("R1", space={"a": 1.0, "b": 0.0, "c": 15.0, "k": 10.0})
    with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
        prepare("R1", params={"sampler": "sobol"})
    with pytest.raises(RequestError, match="sampler"):
        prepare("R1", params={"sampler": 3})


def test_nested_in_n():
    """scatter.md, Parameters (G4, U3): n = 300's first 200 points are n = 200's, bit for bit."""
    small = prepare("R2", params={"n": 200}).design.points
    big = prepare("R2", params={"n": 300}).design.points
    assert np.array_equal(big[:200], small)


# --------------------------------------------------------------------------------------------------------------
# The estimates (SC2-SC4, SC7)


def test_sc4_a_hand_computed_fixture_of_12_runs(tmp_path):
    """SC4: 12 runs of R10, y the rank of a (0 to 11): B = 3 bins of 4, bin means 1.5, 5.5, 9.5 around 5.5; η² =
    4·(16 + 0 + 16)/143 = 128/143; S = 1 - (15/143)(11/9) = 34/39; ρ = 1; the mean 5.5 and the standard deviation
    √13 (ddof 1)."""
    case = prepare("R10", params={"n": 12, "seed": 2})
    a = case.design.points[:, 0]
    y = np.argsort(np.argsort(a)).astype(float)
    result = sd.evaluate(case, sd.batch(case, y=y, z=y), tmp_path)
    assert values(result, "moments") == {"Mean": 5.5, "Standard deviation": pytest.approx(math.sqrt(13), rel=1e-15)}
    assert values(result, "rank_correlation")["a"] == 1.0
    assert values(result, "binned_index")["a"] == pytest.approx(float(Fraction(34, 39)), rel=1e-14)
    (table,) = [t for t in result.estimates if t.key == "binned_index"]
    assert table.title == "3 bins." and table.interval.settings["distinct"] == "the index"


def test_sc4_the_index_is_not_clipped(tmp_path):
    """SC4: R1's c has no effect; at n = 200, seed 10, its index is negative, and reported as computed (-0.0297)."""
    _, _, result = run("R1", tmp_path, params={"n": 200, "seed": 10})
    s = values(result, "binned_index")
    assert -0.031 < s["c"] < -0.028, s


def test_sc3_the_log_scale_changes_no_rank_correlation_or_index(tmp_path):
    """SC3: R1 with k on its log range, and a fixture with k linear over the same unit coordinates and the same y:
    identical ρ and S, bit for bit."""
    log = prepare("R1", params={"n": 60})
    made = reference.batch(log, "R1")
    space = {**reference_models.space("R1"), "k": [1, 100]}
    linear = prepare("R1", space=space, params={"n": 60})
    assert not np.array_equal(linear.design.points[:, 3], log.design.points[:, 3])
    assert np.array_equal(linear.ctx.space.to_unit(linear.spec, linear.design.points)[:, :3],
                          log.ctx.space.to_unit(log.spec, log.design.points)[:, :3])  # fmt: skip
    y = made.runs.values["y"]
    one = sd.evaluate(log, made, tmp_path / "log")
    two = sd.evaluate(linear, sd.batch(linear, y=y, z=y), tmp_path / "linear")
    for key in ("rank_correlation", "binned_index"):
        assert values(one, key) == values(two, key)


def test_sc7_a_change_of_units(tmp_path):
    """SC7 (0048): y -> a·y + b with a = 2⁻¹⁰, b = 3 on R2: the mean a·ȳ + b and the standard deviation a·s; ρ, S, and
    the notes unchanged, exactly under a·y, within C5's tolerances under the shift."""
    case = prepare("R2", params={"n": 50})
    y = reference.batch(case, "R2").runs.values["y"]
    a, b = 2.0**-10, 3.0
    ref = sd.evaluate(case, sd.batch(case, y=y, z=y), tmp_path / "ref")
    scaled = sd.evaluate(case, sd.batch(case, y=a * y, z=y), tmp_path / "scaled")
    both = sd.evaluate(case, sd.batch(case, y=a * y + b, z=y), tmp_path / "both")
    m, m2, m3 = (values(r, "moments") for r in (ref, scaled, both))
    assert m2 == {"Mean": a * m["Mean"], "Standard deviation": a * m["Standard deviation"]}
    assert m3["Mean"] == pytest.approx(a * m["Mean"] + b, abs=1e-9 * a * np.ptp(y))
    assert m3["Standard deviation"] == pytest.approx(a * m["Standard deviation"], abs=1e-9 * a * np.ptp(y))
    for key in ("rank_correlation", "binned_index"):
        assert values(scaled, key) == values(ref, key)
        for name, v in values(both, key).items():
            assert v == pytest.approx(values(ref, key)[name], abs=1e-9)
    assert [n.code for n in scaled.notes] == [n.code for n in both.notes] == [n.code for n in ref.notes] == []


# --------------------------------------------------------------------------------------------------------------
# Intervals (SC5)


def test_sc5_undefined_resamples_are_dropped_and_counted(tmp_path):
    """SC5 (V4): a two-valued y at n = 10, one run 1 and the rest 0: ρ and S are undefined on each resample without
    that run (0/0); the line under each table counts them; the mean and standard deviation never are."""
    case = prepare("R2", intervals=True, params={"n": 10, "seed": 4})
    y = np.zeros(10)
    y[6] = 1.0
    result = sd.evaluate(case, sd.batch(case, y=y, z=y), tmp_path)
    draws = spawned(4, SCATTER_BOOT_TAG).integers(0, 10, (1000, 10))
    without = int(sum(6 not in row for row in draws))
    assert 250 < without < 450  # about 1000·0.9¹⁰
    tables = {t.key: t for t in result.estimates}
    assert dict(tables["moments"].interval.undefined) == {}
    for key in ("rank_correlation", "binned_index"):
        assert dict(tables[key].interval.undefined) == {"x1": without, "x2": without, "x3": without}
    report = render(result, case.spec)
    line = f"Undefined resamples, dropped: x1 {without}, x2 {without}, x3 {without}."
    assert report.count(line) == 2, report


# --------------------------------------------------------------------------------------------------------------
# Too few, constant, failed (SC6, SC8, SC9; S2, S5, S9; 0051)

R5_UNIT_SQUARE = {"a": [0, 1], "b": [0, 1]}  # a + b > 1 fails (error): about half the runs


def test_sc6_nine_usable_runs_give_no_estimates(tmp_path):
    """SC6 (S6): R5 on [0, 1]², n = 20, seed 1: 9 usable runs: counts, the too-few note, the observations, no
    estimates; the figures are the panels with their strips and no bin means, and the histogram (0051)."""
    case, _, result = run("R5", tmp_path, figures=True, space=R5_UNIT_SQUARE, params={"n": 20, "seed": 1},
                          prediction="y")  # fmt: skip
    assert result.counts.usable == 9 and not result.estimates and result.observations
    too_few = next(n.text for n in result.notes if n.code == "too_few")
    assert too_few.startswith("9 usable runs; scatter needs at least 10 (")
    assert [f.name for f in result.figures] == ["scatter_a", "scatter_b", HISTOGRAM]
    panel = card(tmp_path, "scatter_a")["panels"][0]
    assert "bins" not in panel and len(panel["points"]) == 9 and len(panel["not_usable"]) == 11
    assert result.figures[0].caption == "y against each model parameter."
    assert sum(card(tmp_path, HISTOGRAM)["panels"][0]["counts"]) == 9
    assert "## Estimates" not in render(result, case.spec)


def test_sc6_ten_usable_runs_give_estimates(tmp_path):
    """SC6: R5 on [0, 1]², n = 20, seed 0: 10 usable runs, estimates; 3 bins."""
    _, _, result = run("R5", tmp_path, space=R5_UNIT_SQUARE, params={"n": 20, "seed": 0}, prediction="y")
    assert result.counts.usable == 10 and [t.key for t in result.estimates] == [
        "moments",
        "rank_correlation",
        "binned_index",
    ]
    assert result.estimates[2].title == "3 bins."


def test_all_failed_draws_the_strips_only(tmp_path):
    """Degenerate cases (0051): every run failed: no estimates or observations; the panels with only their strips,
    and no histogram."""
    _, _, result = run("R5", tmp_path, figures=True, space={"a": [0.6, 1], "b": [0.6, 1]}, params={"n": 12},
                       prediction="y")  # fmt: skip
    assert result.counts.usable == 0 and not result.estimates and not result.observations
    assert [f.name for f in result.figures] == ["scatter_a", "scatter_b"]
    panel = card(tmp_path, "scatter_b")["panels"][0]
    assert panel["points"] == [] and len(panel["not_usable"]) == 12


def test_s5_r4a_is_constant_and_r4b_is_not(tmp_path):
    """S5 (0035) and the Expected answers: R4a: the constant note, the observations, no estimates, the panels and no
    histogram; R4b: estimates, and a relative spread of 8·10⁻¹³ within 1%."""
    _, _, constant = run("R4a", tmp_path / "a", figures=True)
    assert "constant" in [n.code for n in constant.notes] and not constant.estimates and constant.observations
    assert [f.name for f in constant.figures] == ["scatter_a", "scatter_b", "scatter_c"]
    _, _, wiggle = run("R4b", tmp_path / "b")
    assert wiggle.estimates and "constant" not in [n.code for n in wiggle.notes]
    spread = {row[0].key: row[0].value for row in wiggle.observations[0].rows}["spread"]
    assert spread == pytest.approx(8e-13, rel=0.01)


def r5_regions(points: np.ndarray, prediction: str) -> dict[str, np.ndarray]:
    """R5's regions (reference_models.md): error where a + b > 1; timeout where a, b < -0.8; z missing where b > 0.8."""
    a, b = points[:, 0], points[:, 1]
    error = a + b > 1
    timeout = (a < -0.8) & (b < -0.8) & ~error
    missing = (b > 0.8) & ~error & ~timeout if prediction == "z" else np.zeros(len(a), dtype=bool)
    return {"error": error, "timeout": timeout, "missing": missing}


@pytest.mark.parametrize("prediction", ["y", "z"])
def test_s2_s9_sc8_r5_counts_strips_and_figures(prediction, tmp_path):
    """S2, S9, SC8, and the Expected answers: R5 at n = 200: the runs not usable are the design's points with
    a + b > 1 (error), a, b < -0.8 (timeout), and, for z, b > 0.8 (missing); the header counts them by kind; 2 scatter
    figures and a histogram of ⌊√n_u⌋ bins; each strip holds every run not usable, once, with its kind, its count
    the header's; every point is a usable run, with its run id."""
    case, made, result = run("R5", tmp_path, figures=True, params={"n": 200}, prediction=prediction)
    regions = r5_regions(case.design.points, prediction)
    counts = result.counts
    assert counts.failed[FailureKind.ERROR] == int(regions["error"].sum()) > 0
    assert counts.failed[FailureKind.TIMEOUT] == int(regions["timeout"].sum()) > 0
    assert counts.missing == int(regions["missing"].sum())
    not_usable = regions["error"] | regions["timeout"] | regions["missing"]
    assert counts.usable == 200 - int(not_usable.sum())
    header = render(result, case.spec).split("## ", 1)[0]
    errors, timeouts = counts.failed[FailureKind.ERROR], counts.failed[FailureKind.TIMEOUT]
    row = (f"| Runs | 200: 0 new, 200 reused; {errors + timeouts} failed ({errors} error, {timeouts} timeout); "
           f"{counts.missing} missing {prediction}; {counts.usable} usable |")  # fmt: skip
    assert row in header, header
    assert [f.name for f in result.figures] == ["scatter_a", "scatter_b", HISTOGRAM]
    hexes = hex_ids(made.runs.run_ids)
    usable = made.usable(prediction)
    for name in ("scatter_a", "scatter_b"):
        panel = card(tmp_path, name)["panels"][0]
        strip = panel["not_usable"]
        assert len(strip) == counts.runs - counts.usable == int(not_usable.sum())
        kinds = {e["run_id"]: e["kind"] for e in strip}
        for i in np.flatnonzero(not_usable):
            want = "error" if regions["error"][i] else "timeout" if regions["timeout"][i] else "missing"
            assert kinds[hexes[i]] == want
        assert sorted(p["run_id"] for p in panel["points"]) == sorted(hexes[i] for i in np.flatnonzero(usable))
        assert len(panel["bins"]) == scatter_bins(counts.usable)
    histogram = card(tmp_path, HISTOGRAM)["panels"][0]
    assert len(histogram["counts"]) == scatter_bins(counts.usable) and sum(histogram["counts"]) == counts.usable
    caption = result.figures[2].caption
    assert caption.endswith(f"The {counts.runs - counts.usable} runs not usable are not in it."), caption


@pytest.mark.parametrize(
    ("prediction", "intervals"),
    [("y", False), ("z", False), pytest.param("y", True, marks=pytest.mark.slow)],
)
def test_sc9_estimates_use_the_usable_runs_only(prediction, intervals, tmp_path):
    """SC9 and the Expected answers (U3): R5, y and z, at n = 200: every estimate equals scatter's on a design of the
    usable runs alone; with the bootstrap, every interval too (its resamples are positions among the usable runs)."""
    case = prepare("R5", intervals=intervals, params={"n": 200}, prediction=prediction)
    made = reference.batch(case, "R5", fn=r5)
    usable = made.usable(prediction)
    assert not usable.all()
    d = case.design
    alone = Design(identity=d.identity, points=d.points[usable], replicates=d.replicates[usable], levels=None,
                   lines=None)  # fmt: skip
    first = sd.evaluate(case, made, tmp_path / "all")
    second = sd.evaluate(case, reference.batch(case, "R5", design=alone, fn=r5), tmp_path / "alone")
    assert second.counts.usable == first.counts.usable == int(usable.sum())
    assert first.estimates == second.estimates


# --------------------------------------------------------------------------------------------------------------
# The golden report and the figures (SC8, SC10; S1-S4, S9; 0044)


def test_sc10_the_golden_report(tmp_path):
    """SC10 (0044): R2, n = 200, seed 1, through the bootstrap: the mock report, structure and numbers within one unit
    in the 4th digit. The mock is edited as record 0073 says (items 1 and 3: "ρ" and "Sᵢ" for TeX, the table's title
    "14 bins." opening the line under it); its runs are new, as the mock's. The figures: one per varied model
    parameter with the 14 bins' means over their x ranges, every panel with the same y limits, and the histogram."""
    case = prepare("R2", figures=True, intervals=True, params={"n": 200, "seed": 1})
    made = reference.batch(case, "R2")
    made = RunBatch(design=made.design, runs=made.runs, new=np.ones(200, dtype=bool))
    result = sd.evaluate(case, made, tmp_path)
    mock = mock_report("scatter").replace("$\\rho$", "ρ").replace("$S_i$", "Sᵢ")
    line = "Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, the index"
    mock = mock.replace(line, "14 bins. " + line).replace("seed 1. 14 bins.", "seed 1.")
    found = differences(render(result, case.spec), mock)
    assert found == [], found
    y = made.runs.values["y"]
    extents = []
    for j, name in enumerate(("x1", "x2", "x3")):
        panel = card(tmp_path, f"scatter_{name}")["panels"][0]
        extents.append(panel["y"]["extent"])
        bins = panel["bins"]
        assert len(bins) == 14 and [b["n"] for b in bins] == [15] * 4 + [14] * 10
        order = np.argsort(case.design.points[:, j], kind="stable")
        groups = np.array_split(order, 14)
        assert [b["mean"] for b in bins] == [float(np.mean(y[g])) for g in groups]
        assert all(b["x_lo"] <= b["x_hi"] for b in bins) and bins[0]["x_lo"] == case.design.points[order[0], j]
        assert panel["x"]["label"] == name and panel["y"]["label"] == "y" and panel["not_usable"] == []
    assert extents[0] == extents[1] == extents[2]
    histogram = card(tmp_path, HISTOGRAM)["panels"][0]
    assert histogram["edges"][0] == float(y.min()) and histogram["edges"][-1] == float(y.max())
    assert sum(histogram["counts"]) == 200 and len(histogram["counts"]) == 14
    assert histogram["y"]["label"] == "number of runs"


def test_a_model_parameter_named_histogram_keeps_its_own_figure():
    """Record 0076: a model parameter named histogram is drawn as scatter-histogram; the rest as scatter_<name>."""
    assert figure_name("x1") == "scatter_x1"
    assert figure_name("histogram") == "scatter-histogram" != HISTOGRAM
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", figure_name("_a"))


# --------------------------------------------------------------------------------------------------------------
# The known answers at n = 20,000 (SC2-SC4, SC10; slow)

#: scatter.md, Expected answers: (quantity, label) -> (expected, tolerance).
EXPECTED: dict[str, dict[tuple[str, str], tuple[float, float]]] = {
    "R1": {
        ("moments", "Mean"): (10.0, 0.089),
        ("moments", "Standard deviation"): (math.sqrt(14 / 3), 0.045),
        ("rank_correlation", "a"): (0.8073, 0.012),
        ("rank_correlation", "b"): (-0.2525, 0.034),
        ("rank_correlation", "c"): (0.0, 0.036),
        ("rank_correlation", "k"): (0.5156, 0.027),
        ("binned_index", "a"): (9 / 14, 0.017),
        ("binned_index", "b"): (1 / 14, 0.018),
        ("binned_index", "c"): (0.0, 0.004),
        ("binned_index", "k"): (4 / 14, 0.026),
    },
    "R2": {
        ("moments", "Mean"): (3.5, 0.12),
        ("moments", "Standard deviation"): (3.721, 0.11),
        ("rank_correlation", "x1"): (0.4374, 0.026),
        ("rank_correlation", "x2"): (0.0, 0.038),
        ("rank_correlation", "x3"): (0.0, 0.043),
        ("binned_index", "x1"): (0.3139, 0.022),
        ("binned_index", "x2"): (0.4424, 0.027),
        ("binned_index", "x3"): (0.0, 0.006),
    },
    "R10": {
        ("moments", "Mean"): (0.0, 0.094),
        ("moments", "Standard deviation"): (math.sqrt(6.5), 0.070),
        ("rank_correlation", "a"): (0.7980, 0.017),
        ("rank_correlation", "b"): (0.0, 0.036),
        ("rank_correlation", "c"): (0.0, 0.040),
        ("rank_correlation", "e"): (0.0, 0.034),
        ("binned_index", "a"): (0.6154, 0.021),
        ("binned_index", "b"): (0.0385, 0.013),
        ("binned_index", "c"): (0.0, 0.006),
        ("binned_index", "e"): (0.0, 0.004),
    },
}


@pytest.mark.slow
@pytest.mark.parametrize("id", list(EXPECTED))
def test_sc2_sc10_known_answers(id, tmp_path):
    """SC2-SC4, SC10: the Expected answers at n = 20,000, seed 0, random sampler, each within its tolerance (5
    standard deviations over designs, scatter.md)."""
    _, _, result = run(id, tmp_path, params={"n": KNOWN_ANSWER_N, "seed": 0})
    assert result.counts.usable == KNOWN_ANSWER_N
    for (key, label), (want, tol) in EXPECTED[id].items():
        got = values(result, key)[label]
        assert abs(got - want) <= tol, f"{id} {key} {label}: {got}, expected {want} within {tol}"


@pytest.mark.slow
def test_r4b_relative_spread_at_the_known_answer_n(tmp_path):
    """Expected answers (0035): R4b at n = 20,000, seed 0: estimates, and the relative spread 8.0007·10⁻¹³ (scatter.out)
    within 1%."""
    _, _, result = run("R4b", tmp_path, params={"n": KNOWN_ANSWER_N, "seed": 0})
    spread = {row[0].key: row[0].value for row in result.observations[0].rows}["spread"]
    assert result.estimates and spread == pytest.approx(8.0007e-13, rel=0.01)
