"""The linear model's known answers (diagnostics/linear_model.md: LM1-LM10, Expected answers, the mock report).

Run batches come from the reference models' functions on the convergent design (tests/support/reference.py), or
from the contract model with failures set by masks (tests/support/diagnostics.py). LM10's known answers at 20,000
runs are in the slow tier; the golden report (R3, the defaults, seed 3) is in the fast one. C1-C19 run over the
linear model in tests/contracts/diagnostic.py.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.diagnostics import _fits, base
from ema.diagnostics.linear_model import (
    LINEAR_ALPHA,
    LINEAR_BOOT_TAG,
    LINEAR_LEVEL,
    _loo_note,
    linear_min_runs,
    linear_nmin,
)
from ema.numerics import fitting
from ema.numerics.intervals import Bootstrap, Estimator, Interval
from ema.report import render
from ema.types.errors import RequestError
from ema.types.results import DiagnosticResult
from ema.types.runs import RunBatch, RunKey
from ema.types.streams import spawned
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.reports import IN_SAMPLE, differences, mock_report

LINEAR = base.get("linear_model")
#: linear_model.md, Expected answers: n_min = 5000, alpha = 0.5, level 1 (20,000 runs), seed 0.
KNOWN = {"n_min": 5000, "alpha": 0.5, "level": 1, "seed": 0}


class Skipped:
    """An interval method that computes no interval, for the tests of point estimates: the bootstrap's 2,000 refits
    cost 0.2-0.5 s an evaluation. The intervals are tested by LM2, LM4, the golden report, and C5-C8, C19."""

    name = "skipped"

    @property
    def settings(self) -> dict[str, Any]:
        return {}

    def intervals(self, usable: Any, levels: Any, estimators: Any, stream: Any, on_step: Any = None) -> Any:
        return {e.name: tuple(Interval(None, "not computed in this test", 0) for _ in e.labels) for e in estimators}


def evaluate(
    id: str, out: Path, *, figures: bool = False, bootstrap: bool = False, **kw: Any
) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """Evaluate the linear model on a reference model's runs; without its figures or the bootstrap unless asked."""
    case = reference.prepare(LINEAR if figures else sd.NoFigures(LINEAR), id, **kw)
    if not bootstrap:
        case = dataclasses.replace(case, ctx=dataclasses.replace(case.ctx, interval_method=Skipped()))
    made = reference.batch(case, id)
    return case, made, sd.evaluate(case, made, out)


def values(result: DiagnosticResult, key: str) -> dict[str, float]:
    """An estimates table's values by label."""
    table = next(t for t in result.estimates if t.key == key)
    return {e.label: e.value for e in table.estimates}


def table(result: DiagnosticResult, key: str) -> Any:
    return next(t for t in result.estimates if t.key == key)


def levels(result: DiagnosticResult) -> dict[str, list[Any]]:
    """The per-level table, by row label."""
    found = next(t for t in result.observations if t.key == "levels")
    return {row[0].label: [o.value for o in row] for row in found.rows}


def in_sample(result: DiagnosticResult) -> dict[str, float]:
    """Level L's relative residual and R²: observations, in the per-level table's last column (record 0085)."""
    rows = levels(result)
    return {"rel": rows["Relative residual"][-1], "R²": rows["R²"][-1]}


def unit(case: sd.Case, run_batch: RunBatch) -> np.ndarray:
    return case.ctx.space.to_unit(case.spec, run_batch.design.points)


def lstsq(U: np.ndarray, y: np.ndarray) -> np.ndarray:
    """An independent fit: numpy's lstsq (SVD), not the diagnostic's QR."""
    A = np.column_stack([np.ones(len(y)), U])
    return np.linalg.lstsq(A, y, rcond=None)[0]


@pytest.fixture(scope="module")
def golden(tmp_path_factory: pytest.TempPathFactory) -> tuple[sd.Case, RunBatch, DiagnosticResult, Path]:
    """The mock report's evaluation: R3, the defaults, seed 3, its 72 runs new (linear_model.md, Mock report)."""
    out = tmp_path_factory.mktemp("golden")
    case = reference.prepare(LINEAR, "R3", params={"seed": 3})
    made = reference.batch(case, "R3")
    made = RunBatch(design=made.design, runs=made.runs, new=np.ones(len(made.design), dtype=bool))
    return case, made, sd.evaluate(case, made, out), out


def r5_failing_seed(*, level_0_short: bool) -> int:
    """The first seed whose R5 design at the defaults fails somewhere (in level 0, when asked), with no run in R5's
    timeout corner (a < -0.8 and b < -0.8 sleeps to the spec's timeout: 0.2 s a run)."""
    for seed in range(200):
        case = reference.prepare(sd.NoFigures(LINEAR), "R5", params={"seed": seed}, prediction="y")
        a, b = case.design.points[:, 0], case.design.points[:, 1]
        fails = a + b > 1
        first = case.design.levels[0]
        if not ((a < -0.8) & (b < -0.8)).any() and fails.any() and fails[:first].any() == level_0_short:
            return seed
    raise AssertionError("no such seed")  # pragma: no cover


# --------------------------------------------------------------------------------------------------------------
# The declarations and the parameters


def test_the_declarations_are_the_specs():
    """linear_model.md, Summary, Parameters, Named constants: the bootstrap from its own stream, nested in level."""
    assert (LINEAR.takes_space, LINEAR.interval_method, LINEAR.spawn_tags) == (True, "bootstrap", (2**32 + 2,))
    assert LINEAR_BOOT_TAG == 2**32 + 2 and (LINEAR.has_estimates, LINEAR.constant_note) == (True, True)
    assert LINEAR.nesting == ("level",) and LINEAR.header_rows == ()
    rows = {p.name: (p.default_text, p.changes_design) for p in LINEAR.parameters}
    assert rows == {
        "n_min": ("2(d + 1)", "yes"),
        "alpha": ("0.7072", "yes"),
        "level": ("2", "yes"),
        "seed": ("0", "yes"),
        "sampler": ("random", "yes"),
    }
    assert (LINEAR_ALPHA, LINEAR_LEVEL) == ("0.7072", 2)
    assert [linear_nmin(d) for d in (1, 3, 8)] == [linear_min_runs(d) for d in (1, 3, 8)] == [4, 8, 18]
    assert LINEAR.min_runs(8, {}) == (18, "twice its 9 coefficients")


def test_the_defaults_at_d_8_are_18_36_72_runs():
    """linear_model.md, Parameters: n_min = 2(d + 1), alpha = 0.7072, level 2: 18, 36, 72 points at d = 8."""
    case = reference.prepare(LINEAR, "R3")
    assert dict(case.request.params) == {"n_min": 18, "alpha": "0.7072", "level": 2, "seed": 0, "sampler": "random"}
    assert case.design.levels == (18, 36, 72) and len(case.design) == 72


# --------------------------------------------------------------------------------------------------------------
# LM1: the design


def test_lm1_the_design_is_convergent_bit_for_bit():
    """LM1: the design is convergent with the request's n_min, alpha, level, seed, sampler, and space: R3's points
    are the `random` sampler's rows, ``default_rng(3).random((72, 8))``, mapped to the space (0032)."""
    case = reference.prepare(LINEAR, "R3", params={"seed": 3})
    ident = case.identity
    assert (ident.kind, dict(ident.params), ident.seed, ident.sampler) == (
        "convergent",
        {"n_min": 18, "alpha": "0.7072", "level": 2},
        3,
        "random",
    )
    rows = np.random.default_rng(3).random((72, 8))
    assert np.array_equal(case.design.points, case.ctx.space.from_cube(case.spec, rows))
    other = generators.get("convergent").build(ident, case.spec)
    assert np.array_equal(other.points, case.design.points) and other.levels == (18, 36, 72)


def test_lm1_a_space_with_no_varied_model_parameter_is_refused_before_building():
    """LM1: a space holding every model parameter is refused; so is a sampler that comes later (designs.md)."""
    held = {"a": 1.0, "b": 0.0, "c": 15.0, "k": 10.0}
    with pytest.raises(RequestError, match="varies at least one model parameter"):
        reference.prepare(LINEAR, "R1", space=held)
    with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
        reference.prepare(LINEAR, "R1", params={"sampler": "sobol"})
    with pytest.raises(RequestError, match="sampler is a name, such as random"):
        reference.prepare(LINEAR, "R1", params={"sampler": 3})


# --------------------------------------------------------------------------------------------------------------
# LM2, LM3: the fit, how well it fits, and how well it predicts


def test_lm2_r1_is_exact_in_unit_coordinates(tmp_path: Path):
    """LM2: R1 at the defaults: 10; 3, -1, 0, 2 within 1e-12; the relative residual and LOO at rounding, R² = 1, and
    intervals of about that width (linear_model.md, Exactly linear)."""
    _, _, result = evaluate("R1", tmp_path, bootstrap=True)
    got = values(result, "coefficients")
    for label, want in {"Intercept": 10.0, "a": 3.0, "b": -1.0, "c": 0.0, "k": 2.0}.items():
        assert abs(got[label] - want) <= 1e-12, (label, got[label])
    fit = in_sample(result)
    assert fit["rel"] <= 1e-12 and abs(fit["R²"] - 1.0) <= 1e-12
    assert values(result, "loo")["Leave-one-out error, relative"] <= 1e-12
    for t in result.estimates:
        for e in t.estimates:
            assert e.interval is not None and e.interval[1] - e.interval[0] <= 1e-12, (e.label, e.interval)


def test_lm2_r1_with_k_on_a_linear_range_is_not_exact(tmp_path: Path):
    """LM2: a log scale is part of the unit coordinates (0024): with k's range linear, R1 isn't linear in u."""
    space = {"a": [0, 2], "b": [-1, 1], "c": [10, 20], "k": [1, 100]}
    _, _, result = evaluate("R1", tmp_path, space=space)
    assert in_sample(result)["rel"] > 0.01


def test_lm3_a_hand_computed_fit_of_6_runs_in_d_1():
    """LM3: u = -1, -0.6, ..., 1 and y = 1, 2, 2, 3, 5, 4: intercept 17/6, slope 25/14 (Σuy / Σu², ū = 0); the
    relative residual, R², and the LOO error by PRESS equal explicit refits within 1e-12."""
    u = np.array([-1.0, -0.6, -0.2, 0.2, 0.6, 1.0])
    y = np.array([1.0, 2.0, 2.0, 3.0, 5.0, 4.0])
    A = np.column_stack([np.ones(6), u])
    got = _fits.fit_values(A, y)
    assert np.allclose(got[:2], [17 / 6, 25 / 14], rtol=0, atol=1e-12)
    r = y - (17 / 6 + 25 / 14 * u)
    spread = math.sqrt(float(np.sum((y - 17 / 6) ** 2)))
    assert abs(got[2] - math.sqrt(float(np.sum(r**2))) / spread) <= 1e-12
    assert abs(got[3] - (1 - float(np.sum(r**2)) / spread**2)) <= 1e-12
    held_out = [y[k] - np.polyval(np.polyfit(np.delete(u, k), np.delete(y, k), 1), u[k]) for k in range(6)]
    assert abs(got[4] - math.sqrt(float(np.sum(np.square(held_out)))) / spread) <= 1e-12


def test_lm3_through_the_diagnostic_loo_equals_explicit_refits(tmp_path: Path):
    """LM3: on 6 runs in d = 1 (the contract model's design, y chosen), the estimates equal an independent fit and
    explicit leave-one-out refits within 1e-12."""
    case = sd.prepare(sd.NoFigures(LINEAR), 1, params={"n_min": 6, "level": 0}, interval_method=Skipped())
    y = np.array([0.3, -1.2, 2.5, 0.7, 1.9, -0.4])
    made = sd.batch(case, y=y)
    result = sd.evaluate(case, made, tmp_path)
    u = unit(case, made)[:, 0]
    beta = lstsq(u[:, None], y)
    got = values(result, "coefficients")
    assert abs(got["Intercept"] - beta[0]) <= 1e-12 and abs(got["a"] - beta[1]) <= 1e-12
    held_out = [y[k] - np.polyval(np.polyfit(np.delete(u, k), np.delete(y, k), 1), u[k]) for k in range(6)]
    want = math.sqrt(float(np.sum(np.square(held_out)))) / math.sqrt(float(np.sum((y - y.mean()) ** 2)))
    assert abs(values(result, "loo")["Leave-one-out error, relative"] - want) <= 1e-12


# --------------------------------------------------------------------------------------------------------------
# LM4: the intervals


def test_lm4_at_2_d_plus_1_runs_the_undefined_resamples_are_counted_under_the_table(tmp_path: Path):
    """LM4, V4: at 2(d + 1) = 4 runs in d = 1, about 34% of resamples have too few distinct runs for LOO, and 1.6%
    a rank below 2 (uncertainty.md's table): dropped, counted per estimate, and in the line under each table; the
    bootstrap reports its 1000 resamples through the one progress callback (PM10). Another LINEAR_BOOT_TAG moves
    the intervals and not the design: C8, over this diagnostic (tests/contracts/diagnostic.py)."""
    seen: list[Any] = []
    case = sd.prepare(sd.NoFigures(LINEAR), 1, params={"level": 0}, on_progress=seen.append)
    assert len(case.design) == 4
    result = sd.evaluate(case, sd.batch(case), tmp_path)
    assert len(seen) == 1000 and seen[-1].phase == "analysis" and seen[-1].done == seen[-1].total == 1000  # PM10
    loo = table(result, "loo")
    dropped = loo.interval.undefined["Leave-one-out error, relative"]
    assert 250 <= dropped <= 450, dropped
    rank = table(result, "coefficients").interval.undefined
    assert set(rank) == {"Intercept", "a"} and rank["Intercept"] == rank["a"] and 3 <= rank["a"] <= 40, rank
    assert dict(loo.interval.settings)["distinct"] == "the error" and dict(loo.interval.settings)["seed"] == 0
    report = render(result, case.spec)
    assert f"Undefined resamples, dropped: Leave-one-out error, relative {dropped}." in report
    assert f"Undefined resamples, dropped: Intercept {rank['a']}, a {rank['a']}." in report


def test_0085_the_in_sample_measures_are_observations_without_intervals(golden: Any):
    """Record 0085: the relative residual and R² are not estimates; level L's are the per-level table's last column,
    equal to the fit on the usable runs, and the line under that table says why they have no interval. The
    coefficients and the LOO error keep theirs."""
    case, made, result, _ = golden
    assert [t.key for t in result.estimates] == ["coefficients", "loo"]
    labels = {e.label for t in result.estimates for e in t.estimates}
    assert not labels & {"Relative residual ‖y - ŷ‖ / ‖y - mean‖", "R²"}
    assert all(e.interval is not None for t in result.estimates for e in t.estimates)
    rows = np.flatnonzero(made.usable("y"))
    A = np.column_stack([np.ones(len(made.design)), unit(case, made)])
    rel, r2, _ = _fits.fit_values(A[rows], made.runs.values["y"][rows])[-3:]
    assert in_sample(result) == {"rel": rel, "R²": r2}
    per_level = next(t for t in result.observations if t.key == "levels")
    assert per_level.title.endswith(f"among its first points. {IN_SAMPLE}")
    report = render(result, case.spec)
    assert IN_SAMPLE in " ".join(report.split("## Observations")[1].split("## Figures")[0].split())


def test_0085_dropping_the_in_sample_measures_leaves_the_other_intervals_bit_for_bit():
    """Record 0085, Consequences: the bootstrap draws its resamples whatever the estimators (V2), so the
    coefficients' and LOO's intervals are those of the estimators that also refitted the relative residual and R²."""
    rng = np.random.default_rng(5)
    A = np.column_stack([np.ones(12), rng.uniform(-1, 1, (12, 2))])
    y = A @ np.array([1.0, 2.0, -0.5]) + 0.3 * rng.standard_normal(12)
    rows, keys = np.arange(12), ("intercept", "slope", "slope")
    now = _fits.estimators(A, y, keys)
    before = (
        Estimator(
            "coefficients",
            (*keys, "relative_residual", "r2"),
            lambda i: _fits.fit_values(A[i], y[i])[:-1],
            False,
        ),
        now[1],
    )
    method = Bootstrap()
    got = method.intervals(rows, None, now, spawned(0, LINEAR_BOOT_TAG))
    old = method.intervals(rows, None, before, spawned(0, LINEAR_BOOT_TAG))
    assert got["coefficients"] == old["coefficients"][:3] and got["loo"] == old["loo"]
    assert all(iv.bounds is not None for iv in got["coefficients"])


# --------------------------------------------------------------------------------------------------------------
# LM5, LM6: the levels, and too few usable runs


def test_lm5_a_level_with_too_few_usable_runs_has_none(tmp_path: Path):
    """LM5: R5 where level 0 has fewer than 2(d + 1) = 6 usable runs: "none" in its column; each level fitted on its
    usable runs among its first points."""
    case, made, result = evaluate("R5", tmp_path, prediction="y", params={"seed": r5_failing_seed(level_0_short=True)})
    usable = made.usable("y")
    rows = levels(result)
    sizes = case.design.levels
    assert rows["Usable runs"] == [f"{int(usable[:n].sum())} of {n}" for n in sizes]
    assert all(v == "none" for label, column in rows.items() if label != "Usable runs" for v in column[:1])
    U, y = unit(case, made), made.runs.values["y"]
    for k, n in enumerate(sizes[1:], 1):
        take = np.flatnonzero(usable[:n])
        beta = lstsq(U[take], y[take])
        assert np.allclose([rows["Intercept"][k], rows["a"][k], rows["b"][k]], beta, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("usable", [5, 6])
def test_lm6_below_2_d_plus_1_usable_runs_counts_a_note_and_no_estimates(usable: int, tmp_path: Path):
    """LM6, S6: R5 (d = 2) with 2d + 1 = 5 usable runs: counts, the note, no estimates, the observations (shared and
    per level) stay; with 2(d + 1) = 6: estimates. (No figures without estimates: R4a's test.)"""
    case = reference.prepare(sd.NoFigures(LINEAR), "R5", params={"seed": 1}, prediction="y")
    case = dataclasses.replace(case, ctx=dataclasses.replace(case.ctx, interval_method=Skipped()))
    a, b = case.design.points[:, 0], case.design.points[:, 1]
    failed = np.arange(len(case.design)) >= usable
    made = sd.batch(case, y=a + b**2, z=a - b, failed=failed)
    result = sd.evaluate(case, made, tmp_path)
    assert result.counts.usable == usable
    if usable < 6:
        assert not result.estimates
        assert "5 usable runs; linear model needs at least 6 (twice its 3 coefficients)." in [
            n.text for n in result.notes
        ]
        assert [t.key for t in result.observations] == ["shared", "levels"]
        assert levels(result)["Intercept"] == ["none"] * 3
    else:
        assert [t.key for t in result.estimates] == ["coefficients", "loo"]


def test_r4a_constant_gives_the_note_and_no_estimates(tmp_path: Path):
    """R4a: the "constant" note; no estimates, no per-level table (record 0078 item 3), no figures (0051)."""
    _, _, result = evaluate("R4a", tmp_path, figures=True)
    assert "constant" in [n.code for n in result.notes]
    assert not result.estimates and not result.figures
    assert [t.key for t in result.observations] == ["shared"]


def test_r4b_wiggle_gives_estimates(tmp_path: Path):
    """R4b, 0035: not constant, so estimates of its wiggle."""
    _, _, result = evaluate("R4b", tmp_path)
    assert "constant" not in [n.code for n in result.notes]
    assert [t.key for t in result.estimates] == ["coefficients", "loo"]


@pytest.mark.parametrize("prediction", ["y", "z"])
def test_r5_every_estimate_is_the_fit_on_the_usable_runs_alone(prediction: str, tmp_path: Path):
    """R5, y and z (U3): the failed runs and those missing z are left out of every estimate."""
    case, made, result = evaluate(
        "R5", tmp_path, prediction=prediction, params={"seed": r5_failing_seed(level_0_short=False)}
    )
    usable = made.usable(prediction)
    assert 0 < int(usable.sum()) < len(made.design)
    y = made.runs.values[prediction][usable]
    beta = lstsq(unit(case, made)[usable], y)
    assert np.allclose(list(values(result, "coefficients").values()), beta, rtol=1e-12, atol=1e-12)
    residual = y - np.column_stack([np.ones(len(y)), unit(case, made)[usable]]) @ beta
    rel = math.sqrt(float(np.sum(residual**2)) / float(np.sum((y - y.mean()) ** 2)))
    assert abs(in_sample(result)["rel"] - rel) <= 1e-12


def crafted(tmp_path: Path, change: Any) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """The contract model (d = 3: a, b, c log) on the defaults' design with its points changed by ``change``, every
    run usable (record 0078 items 4, 5; Review round 1)."""
    case = sd.prepare(sd.NoFigures(LINEAR))
    case = dataclasses.replace(case, ctx=dataclasses.replace(case.ctx, interval_method=Skipped()))
    points = np.array(case.design.points)
    change(points)
    made = sd.batch(case, design=dataclasses.replace(case.design, points=points))
    return case, made, sd.evaluate(case, made, tmp_path)


def test_a_rank_deficient_fit_gives_its_note_and_no_estimates(tmp_path: Path):
    """Record 0078 item 4 (0051's rule): a at its midpoint in every run (u_a = 0), so A = [1, u] has rank 3 < 4: the
    rank-deficient note with the fit's own rank, no estimates; the per-level table stays, "none" in each level."""

    def flat_a(points: np.ndarray) -> None:
        points[:, 0] = 1.0  # a in [0, 2]: unit coordinate 0, exactly

    _, made, result = crafted(tmp_path, flat_a)
    assert result.counts.usable == len(made.design) == 32
    assert not result.estimates
    (text,) = [n.text for n in result.notes if n.code == "rank_deficient"]
    assert (
        text
        == "The usable runs' unit coordinates have rank 3 with the constant, below the fit's 4 coefficients: no fit."
    )
    assert levels(result)["Intercept"] == ["none"] * 3 and levels(result)["a"] == ["none"] * 3


def leverage_one_row(rows: int, fit_of: Any) -> int:
    """The first row k whose leverage is exactly 1 in floating point when it alone moves one unit coordinate
    (``fit_of(k)`` gives that fit): in exact arithmetic every such row has leverage 1, in doubles some 1 ± 2⁻⁵²."""
    for k in range(rows):
        if fit_of(k).leverages[k] == 1.0:
            return k
    raise AssertionError("no row of leverage exactly 1")  # pragma: no cover


def test_a_run_of_leverage_1_leaves_the_loo_error_undefined_with_its_note(tmp_path: Path):
    """Record 0078 item 5 (Review round 1): c = 1 (u_c = 0) in every run but one, c = 10 (u_c = 0.5), whose leverage
    is then exactly 1: the coefficients' table, no LOO estimate, and the note naming the leverage."""

    def lone_c(k: int) -> Any:
        def change(points: np.ndarray) -> None:
            points[:, 2] = 1.0
            points[k, 2] = 10.0

        return change

    case = sd.prepare(sd.NoFigures(LINEAR))

    def fit_of(k: int) -> Any:
        points = np.array(case.design.points)
        lone_c(k)(points)
        A = np.column_stack([np.ones(len(points)), case.ctx.space.to_unit(case.spec, points)])
        return fitting.least_squares(A, sd.f(case.spec, points))

    k = leverage_one_row(len(case.design), fit_of)
    _, _, result = crafted(tmp_path, lone_c(k))
    assert [t.key for t in result.estimates] == ["coefficients"]
    assert [(n.code, n.text) for n in result.notes] == [
        ("loo_undefined", "The leave-one-out error is undefined: a usable run has leverage 1.")
    ]


def test_the_loo_note_names_leverage_1_only_when_a_run_has_it():
    """Record 0078 item 5 (Review round 1): with no run of leverage exactly 1 (an overflow), the note says only that
    the error is undefined on these runs; with one, it names it."""
    A = np.column_stack([np.ones(10), np.linspace(-1, 1, 10)])
    y = np.arange(10.0) ** 2
    assert _loo_note(A, y).text == "The leave-one-out error is undefined on these runs."

    def lone(k: int) -> np.ndarray:
        return np.column_stack([A, np.eye(10)[:, k]])

    k = leverage_one_row(10, lambda k: fitting.least_squares(lone(k), y))
    assert _loo_note(lone(k), y).text == "The leave-one-out error is undefined: a usable run has leverage 1."


def test_the_parameters_schema_patterns_are_anchored():
    """Review round 1: a JSON schema's pattern matches anywhere in the text, so alpha's decimal text and the
    sampler's name are anchored with ^ and $; their readers refuse the same texts."""
    by_name = {p.name: p for p in LINEAR.parameters}
    decimal = by_name["alpha"].reader.schema()["anyOf"][1]["pattern"]
    sampler = by_name["sampler"].reader.schema()["pattern"]
    for pattern in (decimal, sampler):
        assert pattern.startswith("^") and pattern.endswith("$")
    assert re.search(decimal, "0.7072") and not re.search(decimal, "x0.7072") and not re.search(decimal, "0.5 or 2")
    assert re.search(sampler, "random") and not re.search(sampler, "random sampler") and not re.search(sampler, "-x")


# --------------------------------------------------------------------------------------------------------------
# LM7: units


def test_lm7_units_change_the_coefficients_as_stated_and_nothing_else(tmp_path: Path):
    """LM7: R2 with y -> a·y + b, a = 2⁻¹⁰, b = 3: β₀ -> a·β₀ + b, βᵢ -> a·βᵢ, the relative residual, R² (observations,
    0085), and LOO unchanged; exactly under a·y, within C5's tolerances under the shift (0048); the notes unchanged."""
    case, made, ref = evaluate("R2", tmp_path / "ref")
    y = np.asarray(made.runs.values["y"])
    a, b = 2.0**-10, 3.0

    def with_y(new: np.ndarray) -> DiagnosticResult:
        runs = dataclasses.replace(made.runs, values={"y": new})
        return sd.evaluate(
            case, RunBatch(design=made.design, runs=runs, new=made.new), tmp_path / str(len(list(tmp_path.iterdir())))
        )

    scaled, both = with_y(a * y), with_y(a * y + b)
    y_range = float(np.ptp(y))
    for got, shift in ((scaled, 0.0), (both, b)):
        assert [n.code for n in got.notes] == [n.code for n in ref.notes]
        for k, v in in_sample(got).items():  # observations now (record 0085), as PM8
            assert (v == in_sample(ref)[k]) if shift == 0.0 else abs(v - in_sample(ref)[k]) <= 1e-9, k
        for tg, tr in zip(got.estimates, ref.estimates, strict=True):
            for eg, er in zip(tg.estimates, tr.estimates, strict=True):
                pairs = [(eg.value, er.value), *zip(eg.interval or (), er.interval or (), strict=True)]
                for vg, vr in pairs:
                    if er.key == "intercept":
                        want, tol = a * vr + shift, 1e-9 * a * y_range
                    elif er.key == "slope":
                        want, tol = a * vr, 1e-9 * a * y_range
                    else:
                        want, tol = vr, 1e-9
                    assert (vg == want) if shift == 0.0 else abs(vg - want) <= tol, (er.label, vg, want)


# --------------------------------------------------------------------------------------------------------------
# LM8: the figures


def test_lm8_r5_the_strip_holds_every_run_not_usable(tmp_path: Path):
    """LM8: R5 at the defaults: the shadow's strip count equals the header's; the slopes (with their intervals: the
    golden report's test); the residuals in ⌊√n_u⌋ bins; every point from a run has its run id (S9)."""
    _, _, result = evaluate(
        "R5", tmp_path, figures=True, prediction="y", params={"seed": r5_failing_seed(level_0_short=False)}
    )
    cards = {f.name: json.loads((tmp_path / f.card).read_text(encoding="utf-8")) for f in result.figures}
    assert list(cards) == ["linear_model_shadow", "linear_model_coefficients", "linear_model_residuals"]
    shadow = cards["linear_model_shadow"]
    (panel,) = shadow["panels"]
    assert len(panel["not_usable"]) == result.counts.runs - result.counts.usable > 0
    assert len(panel["points"]) == result.counts.usable and all("run_id" in p for p in panel["points"])
    beta = [e.value for e in table(result, "coefficients").estimates]
    norm = math.sqrt(sum(v * v for v in beta[1:]))
    assert shadow["intercept"] == beta[0] and abs(shadow["norm"] - norm) <= 1e-15 * norm
    assert [w["parameter"] for w in shadow["w"]] == ["a", "b"] and panel["x"]["label"] == "w·u"
    (slopes,) = cards["linear_model_coefficients"]["panels"]
    assert [p["parameter"] for p in slopes["points"]] == ["a", "b"] and slopes["y"]["label"] == "slope"
    residuals = cards["linear_model_residuals"]
    assert (
        len(residuals["counts"]) == math.isqrt(result.counts.usable)
        and sum(residuals["counts"]) == result.counts.usable
    )
    assert residuals["panels"][0]["x"]["label"] == "residual of y"


# --------------------------------------------------------------------------------------------------------------
# LM9: nesting


def test_lm9_level_3_after_level_2_reuses_every_run_and_starts_with_a_scatters_points():
    """LM9: R3 at level 3 after level 2: the first 72 points are level 2's, so 72 runs are new (G7); and the design's
    first points are a uniform design's with the same seed and sampler (U5)."""
    two = reference.prepare(sd.NoFigures(LINEAR), "R3", params={"seed": 3})
    three = reference.prepare(sd.NoFigures(LINEAR), "R3", params={"seed": 3, "level": 3})
    assert three.design.levels == (18, 36, 72, 144)

    def ids(case: sd.Case) -> set[str]:
        return {RunKey.make(case.model_version_id, p, 0, 0).run_id for p in case.design.points}

    assert len(ids(three) - ids(two)) == 72 and ids(two) <= ids(three)
    scatter = base.identity(
        "uniform", two.ctx.space, {"n": 72}, two.spec, two.model_version_id, seed=3, sampler="random"
    )
    assert np.array_equal(generators.get("uniform").build(scatter, two.spec).points, two.design.points)


# --------------------------------------------------------------------------------------------------------------
# LM10: the golden report and the known answers


def test_lm10_the_golden_report_is_the_mock(golden: Any):
    """LM10, 0044: R3, the defaults, seed 3: the mock report, numbers within one unit in the 4th digit (its
    intervals included: the bootstrap from LINEAR_BOOT_TAG's stream, checked by docs/checks/linear_model.py); the
    relative residual and R² as observations (record 0085)."""
    case, _, result, out = golden
    assert differences(render(result, case.spec), mock_report("linear_model")) == []
    rows = levels(result)  # to more digits than the report shows (docs/checks/linear_model.out)
    assert [round(v, 4) for v in rows["Relative residual"]] == [0.1408, 0.2038, 0.2335]
    assert [round(v, 4) for v in rows["Leave-one-out error"]] == [0.2934, 0.2879, 0.2716]
    assert table(result, "coefficients").interval.undefined == {} and table(result, "loo").interval.undefined == {}
    per_level = next(t for t in result.observations if t.key == "levels")  # record 0078 item 2, Review round 1
    units = {row[0].label: {o.units for o in row if not isinstance(o.value, str)} for row in per_level.rows}
    assert per_level.title.startswith("Coefficients in m³/yr. ")  # so the report prints them once, as the mock does
    assert units["Intercept"] == units["rw"] == {"m³/yr"} and units["Relative residual"] == {""}
    assert (out / "linear_model_shadow.png").stat().st_size > 0
    card = json.loads((out / "linear_model_coefficients.json").read_text(encoding="utf-8"))
    slopes = table(result, "coefficients").estimates[1:]
    assert [(p["slope"], tuple(p["interval"])) for p in card["panels"][0]["points"]] == [
        (e.value, e.interval) for e in slopes
    ]


EXPECTED: dict[str, dict[str, tuple[float, float]]] = {
    "R1": {
        "Intercept": (10, 1e-12), "a": (3, 1e-12), "b": (-1, 1e-12), "c": (0, 1e-12), "k": (2, 1e-12),
        "rel": (0, 1e-12), "R²": (1, 1e-12), "loo": (0, 1e-12),
    },
    "R2": {
        "Intercept": (3.5, 0.11), "x1": (3 / math.pi * (1 + 0.02 * math.pi**4), 0.18), "x2": (0, 0.22),
        "x3": (0, 0.24), "rel": (0.8995, 0.010), "R²": (0.1908, 0.018), "loo": (0.8995, 0.010),
    },
    "R7": {
        "Intercept": (1.068, 0.016), "a": (0.2230, 0.024), "b": (0.72, 0.025), "c": (0, 0.024), "e": (0.2230, 0.029),
        "rel": (0.6739, 0.014), "R²": (0.5458, 0.019), "loo": (0.6739, 0.014),
    },
    "R10": {
        "Intercept": (0, 0.060), "a": (2 * math.sqrt(3), 0.12), "b": (0, 0.098), "c": (0, 0.13), "e": (0, 0.10),
        "rel": (math.sqrt(2.5 / 6.5), 0.016), "R²": (4 / 6.5, 0.020), "loo": (math.sqrt(2.5 / 6.5), 0.016),
    },
    "R3": {
        "Intercept": (77.76, 0.32), "rw": (71.49, 0.91), "r": (-0.16, 0.68), "Tu": (0.00, 0.64), "Hu": (16.09, 0.73),
        "Tl": (0.15, 0.69), "Hl": (-16.09, 0.87), "L": (-15.62, 0.70), "Kw": (7.73, 0.64), "rel": (0.2304, 0.0064),
        "loo": (0.2304, 0.0064),
    },
}  # fmt: skip


@pytest.mark.slow
@pytest.mark.parametrize("id", list(EXPECTED))
def test_lm10_known_answers_at_20000_runs(id: str, tmp_path: Path):
    """LM10, linear_model.md's Expected answers: n_min = 5000, alpha = 0.5, level 1, seed 0 (20,000 runs), each
    within 5 standard deviations over designs (KNOWN_ANSWER_SDS), recomputed by docs/checks/linear_model.py; the
    LOO error within the relative residual's tolerance of its limit."""
    _, made, result = evaluate(id, tmp_path, params=KNOWN)
    assert len(made.design) == 20_000 and result.counts.usable == 20_000
    got = {
        **values(result, "coefficients"),
        **in_sample(result),
        "loo": values(result, "loo")["Leave-one-out error, relative"],
    }
    for label, (want, tol) in EXPECTED[id].items():
        assert abs(got[label] - want) <= tol, (id, label, got[label], want, tol)
