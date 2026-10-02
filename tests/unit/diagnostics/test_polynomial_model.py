"""The polynomial model's known answers (diagnostics/polynomial_model.md: PM1-PM12, Expected answers, the mock report).

Run batches come from the reference models' functions on the convergent design (tests/support/reference.py), or from
the batch builder with y set by the test (tests/support/diagnostics.py). The fast tests run at the default sizes or
smaller; the expected answers at 20,000 runs, the golden report, and C18 at d = 20 with the defaults are slow
(contracts.md, Test tiers; record 0079).
"""

from __future__ import annotations

import dataclasses
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.diagnostics import base
from ema.diagnostics import polynomial_model as pm
from ema.numerics import basis as bases
from ema.numerics.fitting import Fit
from ema.numerics.intervals import Interval
from ema.report import render
from ema.types.design import Design
from ema.types.errors import RequestError
from ema.types.identity import reuse_key
from ema.types.requests import Progress
from ema.types.results import DiagnosticResult, Estimate
from ema.types.runs import RunBatch
from tests.contracts.basis import FakeTensor
from tests.contracts.diagnostic import D20_SECONDS
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.designs import identity as design_identity
from tests.support.fakes import FakeIntervalMethod, registered_interval_method
from tests.support.reports import differences, mock_report

PM = base.get("polynomial_model")
#: The expected answers' design (polynomial_model.md, Expected answers): 20,000 runs, seed 0.
KNOWN_ANSWER = {"n_min": 5000, "alpha": "0.5", "level": 1, "seed": 0}


def evaluate(
    id: str, tmp_path: Path, *, figures: bool = False, **kw: Any
) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """Evaluate the polynomial model on a reference model's runs; without its figures unless asked."""
    case = reference.prepare(PM if figures else sd.NoFigures(PM), id, **kw)
    made = reference.batch(case, id)
    return case, made, sd.evaluate(case, made, tmp_path)


def table(result: DiagnosticResult, key: str) -> dict[str, Estimate]:
    """An estimates table (or ``extra``'s coefficients) by estimate key."""
    (found,) = [t for t in (*result.estimates, *result.extra) if t.key == key]
    return {e.key: e for e in found.estimates}


def values(result: DiagnosticResult, key: str) -> dict[str, float]:
    return {k: e.value for k, e in table(result, key).items()}


def coefficient(result: DiagnosticResult, alpha: tuple[int, ...]) -> float:
    return values(result, "coefficients")["c:" + ",".join(map(str, alpha))]


def levels(result: DiagnosticResult) -> dict[str, list[Any]]:
    (found,) = [t for t in result.observations if t.key == "levels"]
    return {row[0].key: [o.value for o in row] for row in found.rows}


def codes(result: DiagnosticResult) -> list[str]:
    return [n.code for n in result.notes]


def custom(case: sd.Case, points: np.ndarray, y: np.ndarray) -> RunBatch:
    """A batch on given points (one level), with y given: for fixtures a convergent design can't make."""
    design = Design(case.design.identity, points, np.zeros(len(points), dtype=np.int64), (len(points),), None)
    return sd.batch(case, y=y, z=y, design=design)


# --------------------------------------------------------------------------------------------------------------
# Declarations and the request (PM1)


def test_the_declarations_are_the_specs():
    """polynomial_model.md, Parameters and Named constants; uncertainty.md, Per diagnostic (the tag, the method)."""
    rows = {p.name: (p.default_text, p.changes_design) for p in PM.parameters}
    assert rows == {
        "degree": ("2", "yes (through n_min's default)"),
        "n_min": ("2P", "yes"),
        "alpha": ("0.7072", "yes"),
        "level": ("2", "yes"),
        "seed": ("0", "yes"),
        "sampler": ("random", "yes"),
        "basis": ("total_degree", "no"),
    }
    assert (pm.POLY_DEGREE, pm.POLY_NMIN, pm.POLY_ALPHA, pm.POLY_LEVEL, pm.POLY_MIN_RUNS) == (2, 2, "0.7072", 2, 2)
    assert pm.POLY_BOOT_TAG == 2**32 + 3 and PM.spawn_tags == (pm.POLY_BOOT_TAG,)
    assert (PM.interval_method, PM.header_rows, PM.has_estimates, PM.constant_note) == (
        "bootstrap",
        ("Fit",),
        True,
        True,
    )
    assert PM.nesting == ("degree", "level") and PM.takes_space
    assert PM.min_runs(8, {"degree": 3}) == (330, "twice its 165 coefficients at degree 3")


@pytest.mark.parametrize(("id", "degree", "n_min"), [("R3", 2, 90), ("R3", 3, 330), ("R1", 2, 30), ("R11", 10, 132)])
def test_n_min_defaults_to_twice_the_terms(id, degree, n_min):
    """polynomial_model.md, Parameters: n_min = 2P, P = C(d + p, p) (d = 8, p = 2: 90; d = 8, p = 3: 330)."""
    spec = reference.model(id).spec
    request = base.make_request(PM, spec, reference_space(id), None, {"degree": degree})
    assert request.params["n_min"] == n_min
    assert dict(request.params) == {
        "degree": degree, "n_min": n_min, "alpha": "0.7072", "level": 2, "seed": 0, "sampler": "random",
        "basis": "total_degree",
    }  # fmt: skip


def reference_space(id: str) -> dict[str, Any]:
    from ema import reference_models

    return dict(reference_models.space(id))


def test_pm1_the_design_is_convergent_bit_for_bit():
    """PM1: the design equals the convergent generator's with the request's n_min, alpha, level, seed, sampler, and
    space, bit for bit; R3 at the defaults has levels 90, 180, 360 (the mock report)."""
    case = reference.prepare(PM, "R3", params={"seed": 3})
    spec = case.spec
    ident = design_identity(spec, "convergent", case.request.space, seed=3, n_min=90, alpha="0.7072", level=2)
    ident = dataclasses.replace(ident, model_version_id=case.model_version_id)
    built = generators.get("convergent").build(ident, spec)
    assert case.identity == ident and case.design.levels == (90, 180, 360)
    assert np.array_equal(case.design.points, built.points)
    unit = 2 * np.random.default_rng(3).random((360, 8)) - 1  # the random sampler's rows (0032)
    assert np.allclose(case.ctx.space.to_unit(spec, case.design.points), unit, rtol=0, atol=1e-12)


@pytest.mark.parametrize(
    ("params", "space", "match"),
    [
        ({"degree": 0}, None, "degree"),
        ({"basis": "hyperbolic_cross"}, None, "basis hyperbolic_cross comes in a later version"),
        ({"sampler": "sobol"}, None, "sampler sobol comes in a later version"),
        ({}, {"a": 1.0, "b": 0.5, "c": 15.0, "k": 10.0}, "at least one varied model parameter"),
    ],
)
def test_pm1_refusals_before_building(params, space, match):
    """PM1: degree 0, a basis other than total_degree ("comes in a later version"), and a space with no varied model
    parameter are refused before building; a sampler that isn't registered too (0032)."""
    with pytest.raises(RequestError, match=match):
        reference.prepare(PM, "R1", params=params, space=space)


def test_c29_the_basis_is_in_the_requests_identity_not_the_designs(tmp_path):
    """C29's last clause (record 0068's deferral): with a second basis registered, a request naming it has the same
    design, bit for bit, and another reuse key, so another result id."""
    bases.register(FakeTensor())
    try:
        one = reference.prepare(PM, "R10")
        two = reference.prepare(PM, "R10", params={"basis": "fake_tensor"})
    finally:
        bases.unregister("fake_tensor")
    assert one.identity == two.identity and np.array_equal(one.design.points, two.design.points)
    assert one.request.params["basis"] == "total_degree" and two.request.params["basis"] == "fake_tensor"
    ids = reference.batch(one, "R10").runs.run_ids
    versions = sd.VERSIONS
    assert reuse_key(one.model_version_id, one.request, ids, versions) != reuse_key(
        two.model_version_id, two.request, ids, versions
    )


def test_pm11_degree_3_after_degree_2_reuses_its_runs():
    """PM11 (U4): R3, degree 3 at level 1 after degree 2 at level 2, same seed: the first 360 points are the
    earlier design's, bit for bit, so 300 runs are new; level 2 after level 1 reuses every run (G7)."""
    two = reference.prepare(PM, "R3", params={"seed": 3}).design
    three = reference.prepare(PM, "R3", params={"seed": 3, "degree": 3, "level": 1}).design
    assert three.levels == (330, 660) and len(three) - len(two) == 300
    assert np.array_equal(three.points[: len(two)], two.points)
    one = reference.prepare(PM, "R3", params={"seed": 3, "level": 1}).design
    assert np.array_equal(two.points[: len(one)], one.points)


# --------------------------------------------------------------------------------------------------------------
# The fit, its numbers, and their known answers (PM2-PM4)


def test_pm2_p_is_c_of_d_plus_p():
    """PM2: P = C(d + p, p) for d = 1 ... 8, p = 1 ... 4, as the terms the basis builds."""
    for d in range(1, 9):
        for p in range(1, 5):
            assert pm.n_terms(d, p) == math.comb(d + p, p) == len(bases.get("total_degree").terms(d, p))


def test_pm2_pm4_r10_exact_recovery(tmp_path):
    """PM2, PM4 (Expected answers, R10 at p = 2, here at 2P = 30 runs: exact for any design that determines
    the fit): ψ₁(a) 2, ψ₂(b) 0.5, ψ₁(a)ψ₁(c) 1.5, the rest 0, within 1e-12; relative residual and LOO 0, R² 1; the
    indices 4/6.5, 0.25/6.5, 0, 0 and 6.25/6.5, 0.25/6.5, 2.25/6.5, 0; √E_1 = 2, √E_2 = √2.5."""
    _, _, result = evaluate("R10", tmp_path, params={"level": 0})
    exact_r10(result)


def exact_r10(result: DiagnosticResult) -> None:
    coef = values(result, "coefficients")
    want = {"c:1,0,0,0": 2.0, "c:0,2,0,0": 0.5, "c:1,0,1,0": 1.5}
    assert len(coef) == 15 and list(coef)[:5] == ["c:0,0,0,0", "c:1,0,0,0", "c:0,1,0,0", "c:0,0,1,0", "c:0,0,0,1"]
    for key, value in coef.items():
        assert abs(value - want.get(key, 0.0)) <= 1e-12, (key, value)
    fit = values(result, "fit")
    assert abs(fit["rel_residual"]) <= 1e-12 and abs(fit["r2"] - 1) <= 1e-12
    assert abs(values(result, "loo")["loo"]) <= 1e-12
    sobol = values(result, "sobol")
    first = np.array([sobol[f"first:{n}"] for n in "abce"])
    total = np.array([sobol[f"total:{n}"] for n in "abce"])
    assert np.allclose(first, np.array([4, 0.25, 0, 0]) / 6.5, rtol=0, atol=1e-12)
    assert np.allclose(total, np.array([6.25, 0.25, 2.25, 0]) / 6.5, rtol=0, atol=1e-12)
    energy = values(result, "decay")
    assert abs(energy["energy:1"] - 2.0) <= 1e-12 and abs(energy["energy:2"] - math.sqrt(2.5)) <= 1e-12


def exact_r1(result: DiagnosticResult) -> None:
    """R1 at p = 2: ψ₁ terms √3, -1/√3, 0, 2/√3; c_0 = 10; first = total = 9/14, 1/14, 0, 4/14; √E = √(14/3), 0."""
    r3 = math.sqrt(3)
    want = {"c:0,0,0,0": 10.0, "c:1,0,0,0": r3, "c:0,1,0,0": -1 / r3, "c:0,0,0,1": 2 / r3}
    for key, value in values(result, "coefficients").items():
        assert abs(value - want.get(key, 0.0)) <= 1e-12, (key, value)
    assert abs(values(result, "fit")["rel_residual"]) <= 1e-12 and abs(values(result, "fit")["r2"] - 1) <= 1e-12
    assert abs(values(result, "loo")["loo"]) <= 1e-12
    sobol = values(result, "sobol")
    for name, share in zip("abck", (9 / 14, 1 / 14, 0.0, 4 / 14), strict=True):
        assert abs(sobol[f"first:{name}"] - share) <= 1e-12 and abs(sobol[f"total:{name}"] - share) <= 1e-12
    energy = values(result, "decay")
    assert abs(energy["energy:1"] - math.sqrt(14 / 3)) <= 1e-12 and abs(energy["energy:2"]) <= 1e-12


def test_pm4_r1_exact(tmp_path):
    """PM4 (Expected answers, R1 at p = 2, here at 2P = 30 runs): linear in unit coordinates (k through its
    logarithm), so exact; the intervals of about rounding's width (Minimum runs and degenerate cases)."""
    _, _, result = evaluate("R1", tmp_path, params={"level": 0})
    exact_r1(result)
    lo, hi = table(result, "fit")["rel_residual"].interval or (math.nan, math.nan)
    assert 0 <= lo <= hi <= 1e-12


def test_pm4_coefficients_set_by_hand(tmp_path):
    """PM4: y = ψ₁(a) + 2ψ₁(a)ψ₁(b) + 3ψ₂(b) on R11's space (d = 2): V = 14; first-order 1/14, 9/14; total 5/14,
    13/14; √E_1 = 1, √E_2 = √13; the decay table's rows "1, 2 terms" and "2, 3 terms"."""
    case = reference.prepare(sd.NoFigures(PM), "R11")
    u = case.ctx.space.to_unit(case.spec, case.design.points)
    psi1, psi2 = math.sqrt(3) * u, math.sqrt(5) * (3 * u**2 - 1) / 2
    y = psi1[:, 0] + 2 * psi1[:, 0] * psi1[:, 1] + 3 * psi2[:, 1]
    result = sd.evaluate(case, sd.batch(case, y=y, z=y), tmp_path)
    sobol = values(result, "sobol")
    got = [sobol["first:a"], sobol["first:b"], sobol["total:a"], sobol["total:b"]]
    assert np.allclose(got, np.array([1, 9, 5, 13]) / 14, rtol=0, atol=1e-12)
    energy = table(result, "decay")
    assert [e.label for e in energy.values()] == ["1\t2", "2\t3"]
    assert np.allclose([e.value for e in energy.values()], [1.0, math.sqrt(13)], rtol=0, atol=1e-12)
    assert "1 | 2 | 1 |" in render(result, case.spec)  # the label's tab is two cells (record 0073 item 3)


def test_pm3_loo_equals_explicit_refits(tmp_path):
    """PM3: a fixture of 12 runs in d = 2, p = 2 (R11, n_min = 12, level 0): the LOO error by PRESS equals 12
    explicit refits within 1e-12; the relative residual and R² as their formulas."""
    case, made, result = evaluate("R11", tmp_path, params={"n_min": 12, "level": 0})
    u = case.ctx.space.to_unit(case.spec, made.design.points)
    terms = bases.get("total_degree").terms(2, 2)
    A, y = bases.get("total_degree").evaluate(u, terms), made.runs.values["y"]
    held = []
    for k in range(12):
        keep = np.arange(12) != k
        c = np.linalg.lstsq(A[keep], y[keep], rcond=None)[0]
        held.append(y[k] - float(np.sum(A[k] * c)))
    spread = math.sqrt(float(np.sum((y - y.mean()) ** 2)))
    assert abs(values(result, "loo")["loo"] - math.sqrt(float(np.sum(np.square(held)))) / spread) <= 1e-12
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    r = y - np.sum(A * c, axis=1)
    rr = math.sqrt(float(np.sum(r * r))) / spread
    assert (
        abs(values(result, "fit")["rel_residual"] - rr) <= 1e-12
        and abs(values(result, "fit")["r2"] - (1 - rr**2)) <= 1e-12
    )


# --------------------------------------------------------------------------------------------------------------
# Intervals (PM5), degenerate cases (PM7, 0049), and units (PM8)


def test_pm5_at_2p_runs_the_undefined_resamples_are_counted(tmp_path):
    """PM5: R10 at exactly 2P = 30 runs (n_min = 30, level 0): some resamples' A has rank below P, and some have
    fewer than P + 1 distinct runs for LOO; each estimate's count is in its table's line (V4); the same resamples
    for every estimate drawn (the fit's estimates share their count)."""
    case, _, result = evaluate("R10", tmp_path, params={"n_min": 30, "level": 0})
    fit, loo = table(result, "fit"), table(result, "loo")
    infos = {t.key: dict(t.interval.undefined) for t in result.estimates}
    assert infos["fit"] == {"relative residual": infos["fit"]["relative residual"], "R²": infos["fit"]["R²"]}
    assert infos["fit"]["R²"] == infos["fit"]["relative residual"] > 0 and fit["r2"].interval is not None
    assert infos["loo"]["leave-one-out error"] > infos["fit"]["R²"]  # LOO needs P + 1 distinct runs
    assert len({n for t in ("sobol", "decay") for n in infos[t].values()}) == 1
    assert loo["loo"].interval is not None
    report = render(result, case.spec)
    assert f"Undefined resamples, dropped: R² {infos['fit']['R²']}, relative residual" in report
    assert report.count("Undefined resamples, dropped:") == 4


def test_pm5_the_fake_interval_method_names_itself(tmp_path):
    """V7 (uncertainty.md): a fake interval method replaces the bootstrap in every table, the coefficients' too."""
    with registered_interval_method(FakeIntervalMethod()) as fake:
        case = reference.prepare(sd.NoFigures(PM), "R10")
        ctx = dataclasses.replace(case.ctx, interval_method=fake)
        result = sd.evaluate(case, reference.batch(case, "R10"), tmp_path, ctx=ctx)
    assert {t.interval.method for t in (*result.estimates, *result.extra)} == {"fake_range"}


def test_pm7_one_below_2p_and_at_it(tmp_path):
    """PM7: 2P - 1 usable runs: counts, the note naming 2P, no estimates; the shared observations and the per-level
    table stay; at 2P, estimates (R11, P = 6, n_min = 12, level 0, one run failed or none)."""
    case = reference.prepare(sd.NoFigures(PM), "R11", params={"n_min": 12, "level": 0})
    y = reference.batch(case, "R11").runs.values["y"]
    below = sd.evaluate(case, sd.batch(case, y=y, z=y, failed=np.arange(12) == 5), tmp_path / "below")
    assert not below.estimates and not below.extra
    text = next(n.text for n in below.notes if n.code == "too_few")
    assert text == "11 usable runs; polynomial model needs at least 12 (twice its 6 coefficients at degree 2)."
    assert levels(below)["usable"] == ["11 of 12"] and levels(below)["r2"] == ["none"]
    assert [t.key for t in below.observations] == ["shared", "levels"]
    at = sd.evaluate(case, sd.batch(case, y=y, z=y), tmp_path / "at")
    assert at.estimates and levels(at)["usable"] == ["12 of 12"] and isinstance(levels(at)["r2"][0], float)


def test_pm7_a_of_rank_below_p(tmp_path):
    """PM7 (0051): usable runs that take p = 2 values along a: ψ₂(a) is then a sum of 1 and ψ₁(a), so A has rank 5
    of 6: the note, no estimates, no figures; the observations stay, the level's column "none"."""
    case = reference.prepare(PM, "R11", params={"n_min": 12, "level": 0})
    rng = np.random.default_rng(1)
    points = np.column_stack([np.where(np.arange(12) % 2, 0.5, -0.5), rng.uniform(-1, 1, 12)])
    y = points[:, 0] + points[:, 1] ** 2
    result = sd.evaluate(case, custom(case, points, y), tmp_path)
    assert next(n.text for n in result.notes if n.code == "rank") == (
        "The 12 usable runs don't determine the degree-2 polynomial: A has rank 5 of 6."
    )
    assert not result.estimates and not result.figures and levels(result)["loo"] == ["none"]
    assert result.header_rows == (("Fit", "degree 2, total_degree basis: 6 terms"),)


def test_0049_a_constant_fitted_polynomial_has_no_sobol_indices(tmp_path, monkeypatch):
    """0049: V = 0 (every c_α with α ≠ 0 exactly 0, though y varies; a QR rarely gives exact zeros, so the fit is
    wrapped to zero them): the fit's numbers, no Sobol estimates, the note; the fit and residual figures only."""
    real = pm.least_squares

    def flat(A: np.ndarray, y: np.ndarray) -> Fit:
        fit = real(A, y)
        coef = np.where(np.arange(A.shape[1]) == 0, fit.coefficients, 0.0)
        return Fit(coef, y - coef[0], fit.rank, fit.leverages)

    monkeypatch.setattr(pm, "least_squares", flat)
    _, _, result = evaluate("R11", tmp_path, figures=True)
    assert [t.key for t in result.estimates] == ["fit", "loo", "decay"]
    assert "The fitted polynomial is constant (V = 0), so it has no Sobol indices." in [n.text for n in result.notes]
    assert set(values(result, "decay").values()) == {0.0}
    assert [f.name for f in result.figures] == ["polynomial_model_fit", "polynomial_model_residuals"]


def test_0049_v_0_on_runs_that_give_exact_zeros(tmp_path):
    """0049, without a wrapped fit (record 0079 item 11, Review round 1): R11's space, degree 1, 8 runs at
    (±0.375, ±0.375) with y = 0 and at (±1, ±1) with y = 1: y varies, and by symmetry the fit's ψ₁ coefficients
    are 0. Where this LAPACK gives them exactly 0, V = 0: the note, no Sobol table, the decay table's 0, the fit and
    residual figures only; where it doesn't, the test is skipped (the wrapped test above still runs)."""
    case = reference.prepare(PM, "R11", params={"degree": 1, "n_min": 8, "level": 0})
    points = np.array([(s * r, t * r) for r in (0.375, 1.0) for s in (-1, 1) for t in (-1, 1)])
    y = (np.abs(points[:, 0]) > 0.5).astype(float)
    result = sd.evaluate(case, custom(case, points, y), tmp_path)
    coef = values(result, "coefficients")
    if (coef["c:1,0"], coef["c:0,1"]) != (0.0, 0.0):
        pytest.skip(f"this LAPACK's QR gives ψ₁ coefficients {coef['c:1,0']}, {coef['c:0,1']}, not exactly 0")
    assert coef["c:0,0"] == pytest.approx(0.5, rel=1e-15)
    assert [t.key for t in result.estimates] == ["fit", "loo", "decay"]
    assert [n.text for n in result.notes] == ["The fitted polynomial is constant (V = 0), so it has no Sobol indices."]
    assert values(result, "decay") == {"energy:1": 0.0}
    assert [f.name for f in result.figures] == ["polynomial_model_fit", "polynomial_model_residuals"]


def test_loo_undefined_on_a_run_of_leverage_1(tmp_path):
    """Record 0079 item 10 (Review round 1): 6 runs, d = 2, p = 1, five at a = 0.5 and one at a = -0.3: the lone
    run alone sets ψ₁(a)'s coefficient, so its leverage is 1 and the LOO error is undefined. The note, no Held out
    table, "none" in the per-level table; the fit figure's right panel draws 5 runs, and its data card keeps the
    sixth with a null held-out prediction (PM9's data card: each point's run id, y, ŷ, and ŷ₋ₖ)."""
    case = reference.prepare(PM, "R11", params={"degree": 1, "n_min": 6, "level": 0})
    a, b = np.array([0.5] * 5 + [-0.3]), np.array([-0.9, -0.4, 0.1, 0.5, 0.8, 0.2])
    result = sd.evaluate(case, custom(case, np.column_stack([a, b]), a + b**2), tmp_path)
    assert [n.text for n in result.notes] == ["The leave-one-out error is undefined: a usable run has leverage 1."]
    assert [t.key for t in result.estimates] == ["fit", "sobol", "decay"]
    assert levels(result)["loo"] == ["none"] and isinstance(levels(result)["r2"][0], float)
    right = json.loads((tmp_path / "polynomial_model_fit.json").read_text())["panels"][1]
    assert len(right["points"]) == 6 and [p["held_out"] is None for p in right["points"]] == [False] * 5 + [True]
    assert right["points"][5]["x"] is None and all(isinstance(p["x"], float) for p in right["points"][:5])


@pytest.mark.parametrize(("id", "estimates"), [("R4a", False), ("R4b", True)])
def test_r4_constant_and_its_wiggle(id, estimates, tmp_path):
    """Expected answers (0035): R4a is constant: the note, no estimates; R4b's 1e-12 wiggle has estimates."""
    _, _, result = evaluate(id, tmp_path)
    assert bool(result.estimates) == estimates and ("constant" in codes(result)) != estimates


def test_pm8_units_r2_at_p_4(tmp_path):
    """PM8: R2 at p = 4 (70 runs, level 0) with a = 2⁻¹⁰, b = 3: under a·y, c_0, c_α, √E_k times a and the relative
    residual, R², LOO, Sobol indices, and notes unchanged, exactly; under y + b, c_0 + b and the rest unchanged,
    within C5's tolerances (UNITS_RTOL relative to the range in y's units, absolute when dimensionless)."""
    case = reference.prepare(sd.NoFigures(PM), "R2", params={"degree": 4, "n_min": 70, "level": 0})
    y = reference.batch(case, "R2").runs.values["y"]
    a, b = 2.0**-10, 3.0
    ref, scaled, shifted = (
        sd.evaluate(case, sd.batch(case, y=v, z=v), tmp_path / str(k)) for k, v in enumerate((y, a * y, y + b))
    )
    assert codes(ref) == codes(scaled) == codes(shifted) and ref.counts == scaled.counts == shifted.counts
    for key in ("fit", "loo", "sobol", "decay", "coefficients"):
        for k, e in table(ref, key).items():
            transform, _ = PM.transform(key, k)
            s, h = table(scaled, key)[k], table(shifted, key)[k]
            factor = 1.0 if transform is base.Transform.UNCHANGED else a
            assert s.value == factor * e.value and s.interval == tuple(factor * v for v in e.interval), (key, k)
            want = e.value + (b if transform is base.Transform.AFFINE else 0.0)
            tol = 1e-9 * (float(np.ptp(y)) if transform is not base.Transform.UNCHANGED else 1.0)
            assert abs(h.value - want) <= tol + 16 * np.finfo(float).eps * (b + np.abs(y).max()), (key, k)
    assert PM.transform("coefficients", "c:0,0,0") == (base.Transform.AFFINE, False)
    assert PM.transform("coefficients", "c:0,4,0") == (base.Transform.SCALED, False)


# --------------------------------------------------------------------------------------------------------------
# The per-level table (PM6), R5's failures, and the figures (PM9)


def test_pm6_pm9_r5_level_0_too_few_and_the_strips(tmp_path):
    """PM6: R5 (fails where a + b > 1), n_min = 12: level 0 has fewer than 2P = 12 usable runs, so its column is
    "none"; the later levels are fitted on their usable runs. PM9: four figures; each fit panel's strip holds every
    run that isn't usable, with the header's count; the histogram has floor(sqrt(n_u)) bins. Expected answers:
    every estimate equals the polynomial model computed on the usable runs alone (U3)."""
    case, made, result = evaluate("R5", tmp_path, figures=True, params={"n_min": 12}, prediction="y")
    table_ = levels(result)
    usable = made.usable("y")
    assert table_["usable"] == [f"{int(usable[:n].sum())} of {n}" for n in (12, 24, 48)]
    assert int(usable[:12].sum()) < 12 and table_["r2"][0] == "none" and isinstance(table_["r2"][2], float)
    assert [f.name for f in result.figures] == [f"polynomial_model_{s}" for s in ("fit", "sobol", "decay", "residuals")]
    card = json.loads((tmp_path / "polynomial_model_fit.json").read_text())
    not_usable = result.counts.runs - result.counts.usable
    assert not_usable > 0 and [len(p["not_usable"]) for p in card["panels"]] == [not_usable, not_usable]
    assert [p["x"]["label"] for p in card["panels"]] == ["fitted y", "held-out prediction of y"]
    assert len(card["coefficients"]) == 6 and card["coefficients"][4]["multi_index"] == [1, 1]
    bins = json.loads((tmp_path / "polynomial_model_residuals.json").read_text())["panels"][0]["bins"]
    assert len(bins) == math.isqrt(result.counts.usable) and sum(b["count"] for b in bins) == result.counts.usable
    alone = sd.evaluate(case, sd.batch(case, y=made.runs.values["y"], z=made.runs.values["z"], failed=~usable),
                        tmp_path / "alone")  # fmt: skip
    assert alone.estimates == result.estimates and alone.extra == result.extra


def test_r5_z_every_estimate_is_the_usable_runs_alone(tmp_path):
    """Expected answers (R5, z; U3): z, missing where y isn't and failed where y fails, gives every estimate of the
    polynomial model on its usable runs alone; each fit panel's strip holds every run not usable for z (PM9)."""
    _, made, result = evaluate("R5", tmp_path, figures=True, params={"n_min": 12}, prediction="z")
    usable = made.usable("z")
    assert result.estimates and (~usable).sum() > (~made.usable("y")).sum()  # z is missing on more runs
    card = json.loads((tmp_path / "polynomial_model_fit.json").read_text())
    assert [len(p["not_usable"]) for p in card["panels"]] == [int((~usable).sum())] * 2
    bare = reference.prepare(sd.NoFigures(PM), "R5", params={"n_min": 12}, prediction="z")
    alone = sd.evaluate(bare, sd.batch(bare, y=made.runs.values["y"], z=made.runs.values["z"], failed=~usable),
                        tmp_path / "alone")  # fmt: skip
    assert alone.estimates == result.estimates and alone.extra == result.extra


def test_pm9_a_value_below_the_decay_figures_limit_is_an_open_marker(tmp_path):
    """PM9 (0048): a constructed spectrum with one √E_k below SPECTRUM_YMIN of the largest: one open marker on the
    bottom edge, named in the card."""
    case = reference.prepare(sd.NoFigures(PM), "R10", params={"degree": 3, "n_min": 70, "level": 0})
    made = reference.batch(case, "R10")
    result = sd.evaluate(case, made, tmp_path / "first")
    assert next(n for n in result.estimates if n.key == "decay").estimates[2].value < 1e-14  # rounding, not 0
    decay = next(t for t in result.estimates if t.key == "decay")
    zero = dataclasses.replace(decay.estimates[2], value=0.0, interval=(0.0, 0.0))
    changed = dataclasses.replace(decay, estimates=(*decay.estimates[:2], zero))
    built = dataclasses.replace(result, estimates=tuple(changed if t.key == "decay" else t for t in result.estimates))
    figures = PM.figures(made, built, case.ctx, str(tmp_path / "second"))
    assert "polynomial_model_decay" in [f.name for f in figures]
    panel = json.loads((tmp_path / "second" / "polynomial_model_decay.json").read_text())["panels"][0]
    assert panel["below_limit"] == [3] and panel["ymin"] == pytest.approx(pm.SPECTRUM_YMIN * 2.0, rel=1e-12)
    assert [p["terms"] for p in panel["points"]] == [4, 10, 20] and panel["y"]["scale"] == "log"


# --------------------------------------------------------------------------------------------------------------
# Progress and interruption (PM10)


def test_pm10_progress_and_an_interrupt(tmp_path):
    """PM10: A's shape and size first, then the refits, monotone, up to 1000 of 1000; an exception from the
    callback stops the evaluation with no result, and a rerun on the same runs gives the same result (the store's
    part, 0 new runs, is the workspace's: step 14)."""
    seen: list[Progress] = []
    case = reference.prepare(sd.NoFigures(PM), "R2", params={"degree": 4, "n_min": 70, "level": 0})
    made = reference.batch(case, "R2")
    ctx = dataclasses.replace(case.ctx, on_progress=seen.append)
    result = sd.evaluate(case, made, tmp_path / "one", ctx=ctx)
    assert seen[0].text == "A: 70 × 35, 20 kB" and seen[0].phase == "analysis"
    done = [p.done for p in seen[1:]]
    assert done[0] == 1 and done[-1] == 1000 and done == sorted(done) and {p.total for p in seen[1:]} == {1000}
    assert seen[-1].text.startswith("bootstrap: 1000 of 1000 refits, about ")

    class Stop(Exception):
        pass

    def stop(progress: Progress) -> None:
        if progress.done >= 1:
            raise Stop

    with pytest.raises(Stop):
        sd.evaluate(case, made, tmp_path / "two", ctx=dataclasses.replace(case.ctx, on_progress=stop))
    assert sd.evaluate(case, made, tmp_path / "three").to_json() == result.to_json()


def test_sizes_and_durations_as_progress_writes_them():
    """PM10's texts: "A: 14161 × 1771, 200 MB"; d = 20, p = 4 at the defaults is 7.2 GB."""
    assert pm._bytes(14161 * 1771 * 8) == "200 MB" and pm._bytes(84964 * 10626 * 8) == "7.2 GB"
    assert pm._bytes(500) == "500 B" and pm._duration(30) == "30 s" and pm._duration(360) == "6 min"


# --------------------------------------------------------------------------------------------------------------
# The slow tier: the golden report, the expected answers at 20,000 runs, C18 at d = 20


@pytest.mark.slow
def test_pm12_the_golden_report(tmp_path):
    """PM12 (0044): R3, p = 2, seed 3, the defaults, its first 72 runs reused from the linear model's: the mock
    report, with record 0073 item 6's Provenance edit ("runs: 360")."""
    case = reference.prepare(PM, "R3", params={"seed": 3})
    made = reference.batch(case, "R3")
    made = RunBatch(design=made.design, runs=made.runs, new=np.arange(len(case.design)) >= 72)
    report = render(sd.evaluate(case, made, tmp_path), case.spec)
    mock = mock_report("polynomial_model")
    edited = mock.replace("runs: 360 (72 reused from the linear model's evaluation)", "runs: 360")
    assert edited != mock
    found = differences(report, edited)
    assert found == [], found


@pytest.mark.slow
@pytest.mark.parametrize("id", ["R1", "R10"])
def test_pm12_r1_r10_exact_at_20000_runs(id, tmp_path):
    """PM12 (Expected answers): R1 and R10 at p = 2, 20,000 runs, seed 0: exact within 1e-12."""
    _, _, result = evaluate(id, tmp_path, params=KNOWN_ANSWER)
    assert result.counts.usable == 20000
    (exact_r1 if id == "R1" else exact_r10)(result)


#: polynomial_model.md, Expected answers: (expected, tolerance) at p = 10, 20,000 runs, seed 0.
R2_ANSWERS = {
    "first": ([0.313905, 0.442411, 0.0], [4.1e-5, 5.1e-5, 1e-5]),
    "total": ([0.557589, 0.442411, 0.243684], [5.1e-5, 5.1e-5, 4.1e-5]),
    "energy": (
        [1.62542, 0.594723, 1.88396, 1.95229, 1.18024, 1.35741, 0.364431, 0.339391, 0.0502251, 0.0459147],
        [1e-4 * t for t in (1.9, 2.4, 2.2, 2.4, 2.2, 2.6, 3.2, 2.7, 3.2, 3.2)],
    ),
    "rel_residual": ([0.00137138], [7.5e-5]),
    "loo": ([0.00137138], [7.5e-5]),
}
R11_ANSWERS = {
    "first": ([0.448617, 0.448617], [2.9e-4, 3.3e-4]),
    "total": ([0.551383, 0.551383], [3.3e-4, 2.9e-4]),
    "energy": (
        [0.0, 0.191472, 0.0, 0.0952851, 0.0, 0.0434089, 0.0, 0.0189107, 0.0, 0.00802035],
        [1e-4 * t for t in (1.1, 2.1, 1.7, 3.2, 2.7, 4.1, 3.2, 4.6, 3.9, 5.3)],
    ),
    "rel_residual": ([0.0167170], [9.6e-4]),
    "loo": ([0.0167170], [9.6e-4]),
}


def check_answers(result: DiagnosticResult, names: str, answers: dict[str, Any]) -> None:
    sobol, energy = values(result, "sobol"), values(result, "decay")
    got = {
        "first": [sobol[f"first:{n}"] for n in names],
        "total": [sobol[f"total:{n}"] for n in names],
        "energy": [energy[f"energy:{k}"] for k in range(1, 11)],
        "rel_residual": [values(result, "fit")["rel_residual"]],
        "loo": [values(result, "loo")["loo"]],
    }
    for key, (want, tol) in answers.items():
        for j, (g, w, t) in enumerate(zip(got[key], want, tol, strict=True)):
            assert abs(g - w) <= t, f"{key}[{j}]: {g}, expected {w} within {t}"


@pytest.mark.slow
def test_pm12_r11_at_p_10(tmp_path):
    """PM12 (Expected answers): R11 at p = 10, 20,000 runs, seed 0, the bootstrap as users run it: the indices,
    √E_1 ... √E_10 (odd degrees 0 in the model), the relative residual and LOO, within their tolerances."""
    _, _, result = evaluate("R11", tmp_path, params={**KNOWN_ANSWER, "degree": 10})
    check_answers(result, "ab", R11_ANSWERS)
    assert all(e.interval is not None for t in result.estimates for e in t.estimates)


class NoIntervals:
    """An interval method that computes none: for a known-answer test of the estimates alone (record 0079 item 15).

    Every interval is "none", with its reason; the estimates don't depend on the interval method (V7's seam).
    """

    name = "no_intervals"

    @property
    def settings(self) -> dict[str, Any]:
        return {}

    def intervals(self, usable: Any, levels: Any, estimators: Any, stream: Any, on_step: Any = None) -> Any:
        none = Interval(None, "not computed in this known-answer test", 0)
        return {e.name: (none,) * len(e.labels) for e in estimators}


@pytest.mark.slow
def test_pm12_r2_at_p_10(tmp_path):
    """PM12 (Expected answers): R2 (Ishigami) at p = 10, 20,000 runs, seed 0: the analytic indices, the
    quadrature's √E_k, relative residual, and LOO, within their tolerances. The estimates don't depend on the
    interval method, so this test computes no intervals: the bootstrap's 1000 refits of 20,000 × 286 (as drawn and
    on distinct runs) take about 15 minutes, over the slow tier's 10-minute target (record 0079 item 15; the
    bootstrap's own known answers are the golden report's, PM5's, and R1's, R10's, and R11's at 20,000 runs)."""
    with registered_interval_method(NoIntervals()) as method:
        case = reference.prepare(sd.NoFigures(PM), "R2", params={**KNOWN_ANSWER, "degree": 10})
        ctx = dataclasses.replace(case.ctx, interval_method=method)
        result = sd.evaluate(case, reference.batch(case, "R2"), tmp_path, ctx=ctx)
    assert result.counts.usable == 20000
    check_answers(result, ("x1", "x2", "x3"), R2_ANSWERS)  # type: ignore[arg-type]


@pytest.mark.slow
def test_c18_at_d_20_with_the_defaults_within_d20_seconds(tmp_path):
    """C18 (contracts.md, Test tiers): the contract model at d = 20 with the defaults (P = 231, 1848 runs, 1000
    resamples, each a refit as drawn and one on its distinct runs for LOO: 2000 QR fits): a result with estimates,
    within D20_SECONDS of wall-clock time (record 0079 item 16, Review round 1)."""
    case = sd.prepare(sd.NoFigures(PM), 20, params={"degree": 2, "level": 2, "seed": 0})
    assert len(case.design) == 1848
    made = sd.batch(case)
    start, cpu = time.perf_counter(), time.process_time()
    result = sd.evaluate(case, made, tmp_path)
    elapsed, cpu = time.perf_counter() - start, time.process_time() - cpu
    assert result.estimates and elapsed < D20_SECONDS, f"{elapsed:.0f} s wall, {cpu:.0f} s CPU"
