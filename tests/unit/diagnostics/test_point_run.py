"""The point run's known answers (diagnostics/point_run.md: PT1-PT9, Expected answers, the mock report's shape).

Run batches come from the reference models' functions on the point design (tests/support/reference.py). The R6
tests check sampling bounds only: R6 draws its noise from fresh entropy, so they fail with probability about 1e-6
(point_run.md, Expected answers).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from ema.designs import generators
from ema.diagnostics import base
from ema.diagnostics.point_run import POINT_RUN_MIN_RUNS, POINT_RUN_REPEATS
from ema.report import render
from ema.types.errors import RequestError
from ema.types.results import MeasuredNoisy
from ema.types.runs import FailureKind, RunKey
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.reports import differences, mock_report

POINT_RUN = base.get("point_run")
#: χ² with 100 degrees of freedom, two-sided probability 1e-6 (point_run.md, Expected answers).
CHI2_BOUNDS = (0.6735, 1.3603)


def evaluate(id: str, tmp_path: Path, figures: bool = False, **kw: object) -> tuple[sd.Case, object, object]:
    """Evaluate the point run on a reference model's runs; without its figure unless asked (0.1 s each)."""
    case = reference.prepare(POINT_RUN if figures else sd.NoFigures(POINT_RUN), id, **kw)  # type: ignore[arg-type]
    made = reference.batch(case, id)
    return case, made, sd.evaluate(case, made, tmp_path)


def observations(result: object) -> dict[str, object]:
    (table,) = result.observations  # type: ignore[attr-defined]
    return {row[0].label: row[0].value for row in table.rows}


def test_the_declarations_are_the_specs():
    """point_run.md: no space (U7), the parameters and defaults, no interval method or tag, no estimates, no
    constant note (PT6), nested in repeats, a minimum of 1."""
    assert (POINT_RUN.takes_space, POINT_RUN.interval_method, POINT_RUN.spawn_tags) == (False, None, ())
    assert (POINT_RUN.has_estimates, POINT_RUN.constant_note, POINT_RUN.nesting) == (False, False, ("repeats",))
    rows = {p.name: (p.default, p.changes_design) for p in POINT_RUN.parameters}
    assert rows == {"x": ({}, "yes"), "repeats": (4, "yes"), "seed": (0, "no")}
    assert POINT_RUN_REPEATS == 4 and POINT_RUN.min_runs(4, {})[0] == POINT_RUN_MIN_RUNS == 1


def test_pt1_the_defaults_are_the_nominal_point_with_replicates_0_to_4():
    """PT1: the nominal point, replicates 0-4; replicate 0 is the test run's key, so it is reused (0011, 0049)."""
    case = reference.prepare(POINT_RUN, "R1")
    assert dict(case.request.params) == {"x": {}, "repeats": 4, "seed": 0}
    nominal = [p.nominal for p in case.spec.parameters]
    assert np.array_equal(case.design.points, np.tile(nominal, (5, 1)))
    assert case.design.replicates.tolist() == [0, 1, 2, 3, 4]
    test_run = RunKey.make(case.model_version_id, nominal, 0, 0).run_id
    assert reference.batch(case, "R1").run_id(0) == test_run
    more = reference.prepare(POINT_RUN, "R1", params={"repeats": 10}).design
    assert np.array_equal(more.points[:5], case.design.points) and more.replicates[:5].tolist() == [0, 1, 2, 3, 4]


def test_pt2_r1_observations_and_no_estimates(tmp_path):
    """PT2 and the Expected answers on R1: replicate 0 = 10, mean 10, standard deviation 0, distinct values 1, relative
    spread 0, exactly; no notes, no measured-noisy line, no Estimates section."""
    case, _, result = evaluate("R1", tmp_path)
    assert observations(result) == {
        "Replicate 0": 10.0,
        "Mean": 10.0,
        "Standard deviation (ddof 1)": 0.0,
        "Distinct values": 1,
        "Minimum": 10.0,
        "Maximum": 10.0,
        "(max - min) / max|y|": 0.0,
    }
    assert result.observations[0].title == "Of the 5 runs at the point"
    assert not result.estimates and not result.notes and result.measured_noisy is None
    report = render(result, case.spec)
    assert "## Estimates" not in report and "## Notes" not in report and "measured noisy" not in report


def test_pt6_r4a_has_one_distinct_value_and_no_note(tmp_path):
    """PT6: R4a, 4 repeats: distinct values 1; no "constant" note."""
    _, _, result = evaluate("R4a", tmp_path)
    assert observations(result)["Distinct values"] == 1 and not result.notes


@pytest.mark.parametrize(("id", "sigma"), [("R6a", 0.05), ("R6b", 1e-7)])
def test_r6_standard_deviation_within_its_sampling_bounds(id, sigma, tmp_path):
    """Expected answers: R6a's standard deviation 0.05, R6b's 1e-7, at 100 repeats, within the χ² bounds."""
    _, _, result = evaluate(id, tmp_path, params={"repeats": 100})
    std = observations(result)["Standard deviation (ddof 1)"]
    assert CHI2_BOUNDS[0] * sigma <= std <= CHI2_BOUNDS[1] * sigma, std


@pytest.mark.parametrize("id", ["R6a", "R6b"])
def test_pt3_pt4_r6_varies_and_is_recorded_measured_noisy(id, tmp_path):
    """PT3, PT4: R6a and R6b vary at 4 repeats; the result records the model version as measured noisy in y, with
    the point, the runs, and the standard deviation (C52's record; W5 stores it at step 14)."""
    case, _, result = evaluate(id, tmp_path)
    m = result.measured_noisy
    assert m is not None and observations(result)["Distinct values"] == 5
    assert (m.result_id, m.model_version_id, m.prediction) == (result.result_id, case.model_version_id, "y")
    assert m.point == tuple(p.nominal for p in case.spec.parameters) and m.runs == 5
    assert m.std == observations(result)["Standard deviation (ddof 1)"]
    assert "recorded as measured noisy in y" in render(result, case.spec)


def test_pt3_a_failed_replicate_or_one_ulp_varies(tmp_path):
    """PT3: replicate 2 failed: varies; replicate 3 one unit in the last place off: varies; equal: doesn't."""
    case = reference.prepare(sd.NoFigures(POINT_RUN), "R1")
    y = np.full(5, 10.0)
    failed = sd.evaluate(case, sd.batch(case, y=y, failed=np.arange(5) == 2), tmp_path / "a")
    assert failed.measured_noisy is not None and failed.measured_noisy.std == 0.0
    ulp = y.copy()
    ulp[3] = np.nextafter(10.0, 11.0)
    off = sd.evaluate(case, sd.batch(case, y=ulp), tmp_path / "b")
    assert off.measured_noisy is not None and observations(off)["Distinct values"] == 2
    same = sd.evaluate(case, sd.batch(case, y=y), tmp_path / "c")
    assert same.measured_noisy is None


def test_pt4_a_later_result_carries_the_note_with_its_own_range(tmp_path):
    """PT4 (at this layer; through the store at step 14): with R6a's record in the context, a later result for y
    carries the note, the standard deviation as a fraction of that result's range; one for another prediction not."""
    _case, _, first = evaluate("R6a", tmp_path / "first")
    record = first.measured_noisy
    later = reference.prepare(sd.NoFigures(POINT_RUN), "R6a", params={"x": {"a": 2.0}}, measured_noisy=(record,))
    made = reference.batch(later, "R6a")
    result = sd.evaluate(later, made, tmp_path / "later")
    (text,) = [n.text for n in result.notes if n.code == "measured_noisy"]
    y = made.runs.values["y"]
    assert f"by point run {first.result_id[:12]} (5 runs at the nominal point)" in text
    assert f"{record.std / (y.max() - y.min()):.4g} of the range of y" in text, text
    other = MeasuredNoisy(record.result_id, record.model_version_id, "z", record.point, 5, record.std, None)
    quiet = reference.prepare(sd.NoFigures(POINT_RUN), "R6a", measured_noisy=(other,))
    assert not [n for n in sd.evaluate(quiet, reference.batch(quiet, "R6a"), tmp_path / "z").notes]


def test_pt7_no_repeats(tmp_path):
    """PT7: R6a with repeats = 0: one run, the note, no standard deviation, nothing recorded as noisy."""
    _, _, result = evaluate("R6a", tmp_path, params={"repeats": 0})
    assert result.counts.runs == 1 and result.measured_noisy is None
    assert [n.text for n in result.notes] == ["No repeats: the variation was not measured."]
    assert observations(result)["Standard deviation (ddof 1)"] == "none"


def test_pt8_every_run_failed(tmp_path):
    """PT8 and the Expected answers: R5 at a = b = 0.9: 5 failed (error), the note, no observations; the figure has
    the strip only (0051)."""
    _, _made, result = evaluate("R5", tmp_path, figures=True, params={"x": {"a": 0.9, "b": 0.9}}, prediction="y")
    assert result.counts.failed[FailureKind.ERROR] == 5 and result.counts.usable == 0
    assert not result.observations and result.measured_noisy is None
    assert "ValueError: no convergence" in next(n.text for n in result.notes if n.code == "not_usable")
    card = json.loads((tmp_path / "point_run.json").read_text())
    assert card["panels"][0]["points"] == [] and len(card["panels"][0]["not_usable"]) == 5


def test_r5_z_is_usable_at_the_nominal_point(tmp_path):
    """Expected answers: R5 at the nominal point, prediction z: 5 runs usable for z."""
    _, _, result = evaluate("R5", tmp_path, prediction="z")
    assert result.counts.usable == 5 and result.prediction == "z"


def test_pt9_the_figure_with_replicate_0_failed(tmp_path):
    """PT9: R5 fixture with replicate 0 failed: deviations from the mean of the usable runs, named in the y label;
    one point per usable run in replicate order, one × for the failed run; the Replicate 0 row says its kind."""
    case = reference.prepare(POINT_RUN, "R5", prediction="y")
    values = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    made = sd.batch(case, y=values, z=values, failed=np.arange(5) == 0)
    result = sd.evaluate(case, made, tmp_path)
    panel = json.loads((tmp_path / "point_run.json").read_text())["panels"][0]
    assert panel["y"]["label"] == "y − the mean of the usable runs"
    assert [p["replicate"] for p in panel["points"]] == [1, 2, 3, 4]
    assert [p["deviation"] for p in panel["points"]] == [-1.5, -0.5, 0.5, 1.5]
    assert [(s["x"], s["kind"]) for s in panel["not_usable"]] == [(0.0, "error")]
    assert observations(result)["Replicate 0"] == "failed (error)"
    assert result.figures[0].caption == "y - the mean of the usable runs against the replicate number, 0 to 4."


def test_x_outside_the_limits_or_unknown_is_refused():
    """point_run.md: x outside the limits, or an unknown name, is refused before any run (G9)."""
    with pytest.raises(RequestError, match="limit"):
        reference.prepare(POINT_RUN, "R1", params={"x": {"k": -1.0}})
    with pytest.raises(RequestError, match="not a model parameter"):
        reference.prepare(POINT_RUN, "R1", params={"x": {"q": 1.0}})
    with pytest.raises(RequestError, match="takes no model parameter space"):
        base.make_request(POINT_RUN, reference.model("R1").spec, {"a": [0, 2]})


def test_the_seed_is_recorded_and_changes_nothing(tmp_path):
    """point_run.md: a request with another seed is another diagnostic evaluation with the same numbers (C8, 0061)."""
    _, made, first = evaluate("R1", tmp_path / "a")
    other = reference.prepare(sd.NoFigures(POINT_RUN), "R1", params={"seed": 7})
    second = sd.evaluate(other, made, tmp_path / "b")
    assert second.result_id != first.result_id and second.provenance.request.params["seed"] == 7
    assert second.observations == first.observations


def test_the_report_has_the_mocks_shape(tmp_path):
    """The mock report on R6a (point_run.md): its sections, header rows, observation labels, sentence, and figure;
    the numbers are draws, so they aren't compared (there is no golden report, shared.md)."""
    case = reference.prepare(POINT_RUN, "R6a")
    made = reference.batch(case, "R6a")
    made = sd.batch(case, y=made.runs.values["y"], new=np.arange(5) > 0)
    report = render(sd.evaluate(case, made, tmp_path), case.spec)

    def shape(text: str) -> str:
        return re.sub(r"(?<![\w@])-?\d+(\.\d+)?(e[+-]\d+)?(?![\w])", "N", text)

    found = differences(shape(report), shape(mock_report("point_run")), skip=("Provenance",))
    assert found == [], found


def test_the_point_design_is_the_generators():
    """The identity names the point generator at its version, with x and repeats only (0061; designs.md, Point)."""
    case = reference.prepare(POINT_RUN, "R1", params={"x": {"a": 1}, "repeats": 2.0})
    ident = case.identity
    assert (ident.kind, ident.generator_version, ident.sampler) == ("point", generators.get("point").version, None)
    assert dict(ident.params) == {"x": {"a": 1.0}, "repeats": 2}
    assert generators.get("point").size(ident, case.spec) == 3 == len(case.design)
    assert case.design.points[0][0] == 1.0
