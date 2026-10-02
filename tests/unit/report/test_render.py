"""``ema.report.render``: the report's sections, header, numbers, intervals, and escaping (S1-S4, S10; V4, V6, V7;
T10; 0042, 0044, 0051, 0055; record 0073)."""

import re

import pytest

from ema.report import EXPLAIN_INTERVALS, render
from ema.types.results import DiagnosticResult, Note
from ema.types.runs import FailureKind
from tests.support.reports import parse, unescape
from tests.support.results import etable, make_result, make_spec, otable, shared
from tests.unit.report.test_golden import coordinate_lines_r8, point_run_r6a, scatter_r2


def headings(report: str) -> list[str]:
    return [line[3:] for line in report.splitlines() if line.startswith("## ")]


def header(report: str) -> dict[str, str]:
    return {row[0]: row[1] for _, rows in parse(report).sections[""] for row in rows[1:]}


ABC = make_spec("abc", [("a", "", 1.0), ("b", "", 0.0), ("c", "K", 2.0)], ("T_max", "K", "peak temperature"))


def simple(**kw):
    """A scatter-like result on ABC: a varied, b held at a value, c at its nominal value."""
    fields = {
        "diagnostic": "scatter",
        "title": "Scatter",
        "space": {"a": [0, 2], "b": 0.5},
        "params": {"n": 20, "sampler": "random", "seed": 0},
        "kind": "uniform",
        "design_params": {"n": 20},
        "seed": 0,
        "sampler": "random",
        "rows": 20,
        "runs": 20,
        "new": 20,
        "usable": 20,
        "observations": [shared(20, "T_max", 1.0, 2.0, 0.5, "K")],
    }
    fields.update(kw)
    return make_result(ABC, **fields)


# S1: the sections, in order; an empty one left out (0051)


def test_sections_in_order():
    spec, result = scatter_r2()
    report = render(result, spec)
    assert report.startswith("# Scatter: r2, y\n\n| | |\n|---|---|\n")
    assert headings(report) == ["Estimates", "Observations", "Figures", "Provenance"]
    assert report.endswith(".\n") and not report.endswith("\n\n")


def test_empty_sections_left_out_with_their_opening_sentence():
    """All runs failed: the header, the note, and the provenance; no explanation of intervals (S1, S4, C1)."""
    note = Note("all_failed", "All 20 runs failed: 20 failed (error).")
    result = simple(new=20, usable=0, failed={FailureKind.ERROR: 20}, notes=[note], observations=[])
    report = render(result, ABC)
    assert headings(report) == ["Notes", "Provenance"]
    assert EXPLAIN_INTERVALS not in report


def test_notes_section_and_a_note_of_several_lines():
    text = "3 of 20 runs are not usable for T_max: 3 failed (error).\nMost frequent reasons:\n  3  exited with code 3"
    report = render(simple(usable=17, failed={FailureKind.ERROR: 3}, notes=[Note("not_usable", text)]), ABC)
    assert headings(report)[0] == "Notes"
    assert (
        "\n- 3 of 20 runs are not usable for T\\_max: 3 failed (error).\n  Most frequent reasons:\n    3  exited"
        in report
    )


# S2: the header


def test_header_rows():
    report = render(simple(), ABC)
    rows = header(report)
    assert list(rows) == ["Model version", "Model prediction", "Space", "Held", "Design", "Runs"]
    assert re.fullmatch(r"abc@[0-9a-f]{12}", rows["Model version"])  # 0055
    assert rows["Model prediction"] == "T_max: peak temperature, K"
    assert rows["Space"] == "a [0, 2]"
    assert rows["Held"] == "b = 0.5 (held value); c = 2 K (nominal)"  # 0051
    assert rows["Design"] == "uniform, n = 20, sampler random 1 (rate ½), seed 0"
    assert rows["Runs"] == "20: 20 new, 0 reused; 0 failed; 0 missing T_max; 20 usable"


def test_space_with_units_and_log_scale_and_no_held():
    spec = make_spec("m", [("a", "m", 1.0), ("r", "m", 10.0)])
    result = make_result(
        spec,
        diagnostic="scatter",
        title="Scatter",
        space={"a": [0, 2], "r": {"range": [1, 5e4], "scale": "log"}},
        params={"n": 20, "seed": 0},
        kind="uniform",
        design_params={"n": 20},
        seed=0,
        sampler="random",
        rows=20,
        runs=20,
        new=20,
        usable=20,
        observations=[shared(20, "y", 1.0, 2.0, 0.5)],
    )
    report = render(result, spec)
    assert header(report)["Space"] == "a [0, 2] m; r [1, 5e+04] m, log"
    assert header(report)["Held"] == "none"


def test_runs_by_kind_and_missing():
    """U3's r1: failed by kind, missing z, usable (S2)."""
    result = simple(
        rows=20, runs=20, new=20, usable=12, missing=2, failed={FailureKind.ERROR: 5, FailureKind.TIMEOUT: 1}
    )
    assert (
        header(render(result, ABC))["Runs"]
        == "20: 20 new, 0 reused; 6 failed (5 error, 1 timeout); 2 missing T_max; 12 usable"
    )


def test_point_run_header_has_no_held_row():
    """C11: the point run's Space row holds every model parameter, with no Held row (0049)."""
    spec, result = point_run_r6a()
    rows = header(render(result, spec))
    assert "Held" not in rows
    assert rows["Space"] == "the point a = 1, b = 0, c = 15, k = 10 (all nominal); every model parameter held"
    assert rows["Design"] == "point, repeats = 4 (replicates 0–4)"


def test_diagnostic_header_rows_after_design():
    rows = list(header(render(simple(header_rows=[("Fit", "degree 2, total_degree basis: 6 terms")]), ABC)))
    assert rows[-3:] == ["Design", "Fit", "Runs"]


def test_coordinate_lines_design_row_says_which_lines_hold_the_anchor():
    spec, result = coordinate_lines_r8()
    assert header(render(result, spec))["Design"].endswith("(all nominal); all 6 lines share the anchor's run")
    names = ["a", "b", "c", "e", "f", "g"]

    def design(n, anchor):
        r = make_result(
            spec,
            diagnostic="coordinate_lines",
            title="Coordinate lines",
            space={k: [-1, 1] for k in names},
            params={"n": n, "anchor": anchor, "seed": 0},
            kind="coordinate_lines",
            design_params={"n": n, "anchor": anchor},
            seed=0,
            rows=6 * n,
            runs=6 * n,
            new=6 * n,
            usable=6 * n,
            observations=[shared(6 * n, "y", 0.0, 1.0, 1.0)],
        )
        return header(render(r, spec))["Design"]

    assert design(16, {}).endswith("lines through the anchor: none (n is even)")
    off = design(17, {"a": 0.3, "b": 0.7})
    assert "anchor a = 0.3, b = 0.7, c = 0, e = 0, f = 0, g = 0 (a, b given; the others nominal)" in off
    assert off.endswith("lines through the anchor: c, e, f, g")


# S3: numbers (0044)


def test_numbers_four_digits_ascii_minus_integers_in_full():
    table = otable("own", ("Of the runs", "y"), [("Small", -0.0094471234), ("Count", 123456), ("Big", 12345.678)])
    report = render(simple(observations=[table]), ABC)
    assert "| Small | -0.009447 |" in report
    assert "| Count | 123456 |" in report
    assert "| Big | 1.235e+04 |" in report
    assert "−" not in report  # no Unicode minus


def test_values_with_units():
    table = otable("own", ("Of the runs", "T_max"), [("Minimum", 412.34)], units="K")
    assert "| Minimum | 412.3 K |" in render(simple(observations=[table]), ABC)


# S4: the explanation once, and the line under each table (0042; V4, V6, V7)


def test_explanation_once_and_a_line_under_each_table():
    spec, result = scatter_r2()
    report = render(result, spec)
    assert report.count(EXPLAIN_INTERVALS) == 1
    assert len(re.findall("confidence interval", report)) == 1
    estimates = parse(report).sections["Estimates"]
    kinds = [k for k, _ in estimates]
    assert kinds == ["paragraph", "table", "paragraph", "table", "paragraph", "table", "paragraph"]
    assert estimates[2][1] == (
        "Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, 0.5th to 99.5th percentiles, seed 1."
    )
    assert estimates[6][1] == (
        "14 bins. Variability intervals: bootstrap over the 200 usable runs, 1000 resamples, the index recomputed "
        "on the distinct runs of each resample, 0.5th to 99.5th percentiles, seed 1."
    )


def test_none_interval_with_its_reason():
    """V6: "none" in the cell, and the reason in the line under the table."""
    reason = "150 of 1000 resamples defined, fewer than 201"
    table = etable(
        "rho",
        ("Model parameter", "Rank correlation ρ", "Variability interval"),
        [("a", 0.5, 0.4, 0.6), ("b", 0.01, None, reason)],
        n_usable=20,
        seed=0,
        undefined={"b": 850},
    )
    report = render(simple(estimates=[table]), ABC)
    assert "| b | 0.01 | none |" in report
    line = parse(report).sections["Estimates"][2][1]
    assert line.endswith(f"seed 0. b: none: {reason}. Undefined resamples, dropped: b 850.")


def test_a_fake_method_is_named_in_the_line():
    """V7, C19: another interval method's name and settings are in the line under its table."""
    table = etable(
        "m",
        ("Model prediction", "Estimate", "Variability interval"),
        [("Mean", 1.0, 0.9, 1.1)],
        n_usable=20,
        seed=0,
        method="fake",
    )
    line = parse(render(simple(estimates=[table]), ABC)).sections["Estimates"][2][1]
    assert line.startswith("Variability intervals: fake over the 20 usable runs")


def test_two_estimates_per_row_and_label_cells():
    table = etable(
        "sobol",
        ("Sobol indices", "First-order", "Variability interval", "Total", "Variability interval"),
        [("a", 0.5, 0.4, 0.6, 0.7, 0.6, 0.8)],
        n_usable=20,
        seed=0,
    )
    decay = etable(
        "decay",
        ("k", "Terms", "√E_k", "Variability interval"),
        [("1\t2", 4.0, 3.0, 5.0)],
        n_usable=20,
        seed=0,
        units="K",
    )
    report = render(simple(estimates=[table, decay]), ABC)
    assert "| a | 0.5 | [0.4, 0.6] | 0.7 | [0.6, 0.8] |" in report
    assert "| 1 | 2 | 4 K | [3, 5] K |" in report


def test_a_table_whose_columns_dont_fit_is_refused():
    table = etable("m", ("Model prediction", "Estimate"), [("Mean", 1.0, 0.9, 1.1)], n_usable=20, seed=0)
    with pytest.raises(ValueError, match="columns"):
        render(simple(estimates=[table]), ABC)


# Observations, figures, provenance


def test_observation_table_title_under_it_unless_it_is_the_row_heading():
    t = otable("x", ("Line", "Range"), [("0", 1.5)], title="Observations of the 17 runs on each line.")
    observations = parse(render(simple(observations=[shared(20, "T_max", 1.0, 2.0, 0.5, "K"), t]), ABC)).sections[
        "Observations"
    ]
    assert [k for k, _ in observations] == ["table", "table", "paragraph"]
    assert observations[2][1] == "Observations of the 17 runs on each line."


def test_measured_noisy_sentence():
    spec, result = point_run_r6a()
    report = render(result, spec)
    assert re.search(
        r"The model prediction varies at this point, so r6a@[0-9a-f]{12} is recorded as measured noisy in y\.", report
    )


def test_figures_grouped_by_caption():
    spec, result = scatter_r2()
    figures = parse(render(result, spec)).sections["Figures"]
    assert [k for k, _ in figures] == ["paragraph"] * 4
    assert figures[1][1] == (
        "y against each model parameter, with the means of the 14 bins of the binned index. Data cards: "
        "`scatter_x1.json`, `scatter_x2.json`, `scatter_x3.json`."
    )
    assert figures[3][1] == "y over the 200 usable runs, 14 bins. Data card: `scatter_histogram.json`."
    assert "![scatter\\_x1](scatter_x1.png) ![scatter\\_x2](scatter_x2.png)" in render(result, spec)


def test_provenance_line():
    """P5, 0054, 0055: the versions, the model version, the request, the runs, and the approval's 12 hex digits."""
    spec, result = scatter_r2()
    line = parse(render(result, spec)).sections["Provenance"][0][1]
    assert re.fullmatch(
        r"EMA 2\.0\.0; numpy 2\.3\.1, scipy 1\.16\.0, matplotlib 3\.10\.0; model version r2@[0-9a-f]{12}; request: "
        r"scatter, space as above, n = 200, sampler random 1, seed 1, prediction y; runs: 200; approvals: "
        r"[0-9a-f]{12} \(200 new runs\)\.",
        line,
    ), line
    spec, result = point_run_r6a()
    line = parse(render(result, spec)).sections["Provenance"][0][1]
    assert "request: point run, repeats = 4, x = {}, seed 0, prediction y; runs: 5; approvals:" in line
    no_new = simple(new=0, observations=[shared(20, "T_max", 1.0, 2.0, 0.5, "K")])
    assert parse(render(no_new, ABC)).sections["Provenance"][0][1].endswith("approvals: none (no new runs).")


# S10, P1: a pure function of the stored result and spec


def test_rebuilt_from_its_json_byte_identical():
    for build in (scatter_r2, point_run_r6a, coordinate_lines_r8):
        spec, result = build()
        report = render(result, spec)
        assert render(DiagnosticResult.from_json(result.to_json()), spec) == report
        assert render(result, spec) == report


def test_refuses_a_spec_without_the_prediction():
    _, result = scatter_r2()
    with pytest.raises(ValueError, match="model prediction y"):
        render(result, ABC)


# T10: text EMA didn't write prints literally


ATTACK = r"$\input{/etc/hosts}$ *x* [a](b)"


def test_text_ema_didnt_write_is_escaped():
    spec = make_spec("t10", [("a", "", 1.0)], ("_T_", ATTACK, ATTACK))
    note = Note(
        "not_usable", f"1 of 20 runs is not usable for _T_: 1 failed (error).\nMost frequent reasons:\n  1  {ATTACK}"
    )
    result = make_result(
        spec,
        diagnostic="scatter",
        title="Scatter",
        space={"a": [0, 2]},
        params={"n": 20, "seed": 0},
        kind="uniform",
        design_params={"n": 20},
        seed=0,
        sampler="random",
        rows=20,
        runs=20,
        new=20,
        usable=19,
        failed={FailureKind.ERROR: 1},
        notes=[note],
        observations=[shared(19, "_T_", 1.0, 2.0, 0.5, ATTACK)],
    )
    report = render(result, spec)
    escaped = r"\$\\input{/etc/hosts}\$ \*x\* \[a\](b)"
    assert f"\\_T\\_: {escaped}, {escaped}" in report
    assert f"1  {escaped}" in report
    assert "# Scatter: t10, \\_T\\_" in report
    assert ATTACK not in report and "_T_" not in report
    assert report.count(escaped) == 5  # the description and units in the header, the units of min and max, the reason
    assert unescape(f"\\_T\\_: {escaped}") == f"_T_: {ATTACK}"
