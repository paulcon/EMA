"""Lines' known answers (diagnostics/lines.md: LN1-LN9, Expected answers, the mock report).

Run batches come from the reference models' functions on the random or given lines design
(tests/support/reference.py). The per-line computation is coordinate lines' (``_lines.py``), so CL2 and CL3's tests
cover it; these check the wiring (LN2), and the rates against exact rational arithmetic on the same runs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.diagnostics import base
from ema.diagnostics.lines import LINES_M, LINES_N, LINES_TABLE_COLUMNS
from ema.report import render
from ema.types.errors import NotFound, RequestError
from ema.types.results import DiagnosticResult
from ema.types.runs import FailureKind, RunBatch
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.reports import differences, mock_report
from tests.unit.diagnostics.test_coordinate_lines import exact_rate

LINES = base.get("lines")
R7_RATES = (0.8166077, 0.6447274, 0.2184303, 0.07051713, 0.1891380)


def evaluate(
    id: str, tmp_path: Path, *, figures: bool = False, fn: Any = None, **kw: Any
) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """Evaluate lines on a reference model's function; without figures unless asked."""
    case = reference.prepare(LINES if figures else sd.NoFigures(LINES), id, **kw)
    made = reference.batch(case, id, fn=fn)
    return case, made, sd.evaluate(case, made, tmp_path)


def rows(result: DiagnosticResult) -> list[tuple[Any, ...]]:
    """The rates table: each line's (usable, length, range, degrees, rate)."""
    table = next(t for t in result.observations if t.key == "line_rates")
    return [tuple(o.value for o in row) for row in table.rows]


def given(*directions: dict[str, float], anchor: dict[str, float] | None = None) -> list[dict[str, Any]]:
    return [{"anchor": dict(anchor or {}), "direction": d} for d in directions]


def test_the_declarations_are_the_specs():
    """lines.md: Parameters and Named constants; no interval method, no tag, no estimates; nested in m and n."""
    assert (LINES.takes_space, LINES.interval_method, LINES.spawn_tags, LINES.has_estimates) == (True, None, (), False)
    assert [(p.name, p.default_text, p.changes_design) for p in LINES.parameters] == [
        ("m", "5", "yes"),
        ("lines", "none", "yes"),
        ("n", "17", "yes"),
        ("seed", "0", "yes (random lines)"),
    ]
    assert LINES.nesting == ("m", "n") and (LINES_M, LINES_N, LINES_TABLE_COLUMNS) == (5, 17, 5)
    spec = reference.model("R7").spec
    assert dict(base.make_request(LINES, spec, {"a": [-1, 1]}).params) == {"m": 5, "lines": None, "n": 17, "seed": 0}
    with_lines = base.make_request(LINES, spec, {"a": [-1, 1]}, params={"lines": given({"a": 1})})
    assert with_lines.params["m"] is None


def test_ln1_each_mode_is_its_generator():
    """LN1: random lines are random_lines(space, m, n, seed), given lines lines(space, lines, n), bit for bit."""
    for params, kind, design_params in (
        ({}, "random_lines", {"m": 5, "n": 17}),
        ({"lines": given({"a": 1, "e": 1}), "n": 9}, "lines", {"lines": given({"a": 1.0, "e": 1.0}), "n": 9}),
    ):
        case = reference.prepare(LINES, "R7", params=params)
        space = base.request_space(case.request, case.spec)
        ident = base.identity(kind, space, design_params, case.spec, case.model_version_id, seed=0)
        design = generators.get(kind).build(ident, case.spec)
        assert case.identity == ident
        assert np.array_equal(case.design.points, design.points) and case.design.lines == design.lines


@pytest.mark.parametrize(
    ("params", "space", "match"),
    [
        ({"m": 3, "lines": given({"a": 1})}, None, "not both"),
        ({"m": None}, None, r"\(given lines\)$"),
        ({"n": 6}, None, "n"),
        ({}, {"a": 0.1}, "varies no model parameter"),
        ({"lines": given({"a": 1}, anchor={"a": 2.0})}, None, "outside its range"),
        ({"lines": given({"a": 0.0})}, None, "zero"),
        ({"lines": given({"a": 1})}, {"b": [-1, 1]}, "which the space holds"),
        ({"lines": given({"q": 1})}, None, "q"),
    ],
)
def test_ln1_refusals_before_building(params, space, match):
    """LN1, G14: both m and lines (or neither); n < 7; no varied model parameter; an anchor outside the space, a zero direction,
    a direction naming a held model parameter or an unknown name: each refused before the design is built."""
    with pytest.raises((RequestError, NotFound), match=match):
        reference.prepare(LINES, "R7", params=params, space=space)


@pytest.mark.parametrize(("n", "want"), [(17, 0.2025713), (33, 0.1082395), (65, 0.05902797)])
def test_ln2_r7_given_line_across_the_kink(n, want, tmp_path):
    """LN2 and Expected answers: R7's given line through the nominal point, direction (a, e) = (1, 1): length 2√2
    exactly; the rate within 1e-6, and within 1e-9 of exact rational arithmetic on the same runs."""
    _, made, result = evaluate("R7", tmp_path, params={"lines": given({"a": 1, "e": 1}), "n": n})
    ((usable, length, _, degrees, rate),) = rows(result)
    k_star, exact = exact_rate(made.runs.values["y"])
    assert usable == f"{n} of {n}" and length == 2 * math.sqrt(2) and degrees == f"{k_star} of {(n - 1) // 2}"
    assert rate == pytest.approx(want, abs=1e-6) and exact is not None and abs(rate - exact) <= 1e-9


def test_ln3_r7_random_lines_at_the_defaults(tmp_path):
    """LN3 and Expected answers: R7, m = 5, n = 17, seed 0: one row per line in line order, each rate within 1e-6
    (and 1e-9 of exact rational arithmetic); the mock's lengths and ranges; no summary across lines."""
    case, made, result = evaluate("R7", tmp_path)
    found = rows(result)
    y = made.runs.values["y"]
    lengths, ranges = (0.6417, 2.665, 2.367, 2.17, 2.275), (0.4261, 0.3665, 1.274, 1.132, 1.102)
    for line, row, rate, length, rng in zip(case.design.lines, found, R7_RATES, lengths, ranges, strict=True):
        _, exact = exact_rate(y[slice(*line.rows)])
        assert row[0] == "17 of 17" and row[3] == "8 of 8"
        assert row[4] == pytest.approx(rate, abs=1e-6) and exact is not None and abs(row[4] - exact) <= 1e-9
        assert f"{row[1]:.4g}" == f"{length:.4g}" and f"{row[2]:.4g}" == f"{rng:.4g}"
    assert [t.key for t in result.observations] == ["shared", "ends_0", "line_rates"] and not result.notes


def test_ln4_the_ends_tables(tmp_path):
    """LN4: R3 with m = 7: two tables of ends, of 5 and 2 lines, 8 rows each in the model spec's order, each cell
    "from → to" in model parameter units, from the line's recorded ends."""
    case, _, result = evaluate("R3", tmp_path, params={"m": 7})
    tables = [t for t in result.observations if t.key.startswith("ends_")]
    assert [len(t.columns) for t in tables] == [6, 3] and [len(t.rows) for t in tables] == [8, 8]
    assert tables[1].columns == ("Model parameter", "Line 5", "Line 6")
    assert [row[0].label for row in tables[0].rows] == [p.name for p in case.spec.parameters]
    first = case.design.lines[0].ends
    assert tables[0].rows[0][0].value == f"{first[0][0]:.4g} → {first[1][0]:.4g}"
    assert tables[0].rows[0][0].units == "m"


def test_ln5_r10_given_lines_constant_line_note(tmp_path):
    """LN5 and Expected answers (0058): R10's given lines through the nominal point, directions (a, e) = (1, 1) and
    e: one note, "y is the same in all 17 usable runs along line 1: -0.559."; line 0 k* = 1 and no rate; line 1
    none: constant."""
    _, _, result = evaluate("R10", tmp_path, params={"lines": given({"a": 1, "e": 1}, {"e": 1})})
    assert [n.text for n in result.notes] == ["y is the same in all 17 usable runs along line 1: -0.559."]
    (line0, line1) = rows(result)
    assert line0[3:] == ("1 of 8", "none") and line1[2:] == (0.0, "0 of 8", "none: constant")


def test_ln5_r4a_the_shared_note_only(tmp_path):
    """LN5: R4a, the shared constant note only; each line none: constant."""
    _, _, result = evaluate("R4a", tmp_path)
    assert [n.code for n in result.notes] == ["constant"]
    assert all(row[4] == "none: constant" for row in rows(result))


@pytest.mark.parametrize(("id", "k_star"), [("R1", "1 of 8"), ("R10", "2 of 8")])
def test_polynomial_models_have_no_rate_on_any_line(id, k_star, tmp_path):
    """Expected answers: R1 and R10, random, m = 5, seed 0: k* = 1 (R1) and 2 (R10) on every line; no rate."""
    _, _, result = evaluate(id, tmp_path)
    assert all(row[3:] == (k_star, "none") for row in rows(result))


def test_ln6_a_given_lines_anchor_is_marked(tmp_path):
    """LN6: R7's given line across the kink: one PNG; x is the distance along the line, 0 to its length; the anchor
    marked at distance √2; the card holds the line's anchor, direction, ends, and length."""
    _, _, result = evaluate("R7", tmp_path, figures=True, params={"lines": given({"a": 1, "e": 1})})
    (figure,) = result.figures
    card = json.loads((tmp_path / figure.card).read_text(encoding="utf-8"))
    top = card["panels"][0]
    xs = [p["x"] for p in top["points"]]
    assert figure.name == "lines_0" and xs[0] == 0.0 and xs[-1] == pytest.approx(2 * math.sqrt(2), abs=1e-15)
    assert top["anchor"] == pytest.approx(math.sqrt(2), abs=1e-15)
    assert top["x"]["label"] == "distance along line 0 (unit coordinates)"
    assert card["line"]["length"] == 2 * math.sqrt(2) and card["line"]["direction"] == [1.0, 0.0, 0.0, 1.0]


@pytest.mark.parametrize("n", [17, 33])
def test_ln7_changes_of_units(n, tmp_path):
    """LN7: R2 under y -> 2⁻¹⁰·y + 3: rates within RATE_SHIFT_TOL, k* and notes identical, ranges times 2⁻¹⁰;
    under 2⁻¹⁰·y alone, rates within 1e-12 and ranges exact; lengths and ends unchanged."""
    r2 = reference.function("R2")
    _, _, ref = evaluate("R2", tmp_path / "ref", params={"n": n})
    for b, tol in ((3.0, 1e-5), (0.0, 1e-12)):
        _, _, got = evaluate("R2", tmp_path / str(b), params={"n": n}, fn=lambda _b=b, **x: 2.0**-10 * r2(**x) + _b)
        assert [n.text for n in got.notes] == [n.text for n in ref.notes]
        assert got.observations[1] == ref.observations[1]  # the ends
        for g, r in zip(rows(got), rows(ref), strict=True):
            assert (g[0], g[1], g[3]) == (r[0], r[1], r[3])
            assert g[2] == 2.0**-10 * r[2] if not b else abs(g[2] - 2.0**-10 * r[2]) <= 1e-15
            assert abs(g[4] - r[4]) <= tol


def test_ln8_nested_in_m_and_n():
    """LN8: R7, m = 6 after m = 5 makes 17 new runs; n = 33 after n = 17 makes 16 new runs per line."""

    def ids(**params: Any) -> set[str]:
        case = reference.prepare(LINES, "R7", params=params)
        return set(sd.batch(case, y=np.zeros(len(case.design)), z=np.zeros(len(case.design))).runs.run_ids.tolist())

    five = ids()
    assert len(ids(m=6) - five) == 17 and len(ids(n=33) - five) == 5 * 16


@pytest.mark.parametrize("n", [33, 65, 129])
def test_r11_rates_from_the_nearest_pole(n, tmp_path):
    """Expected answers: R11, random, m = 10, seed 0: log10 ρ of each line's Bernstein ellipse through its nearest
    pole: 0.2090 for lines 0, 1, 3, 4, 5, 6, 9; 0.7532, 0.2555, 0.3568 for lines 2, 7, 8; within 0.02."""
    want = [0.2090] * 10
    want[2], want[7], want[8] = 0.7532, 0.2555, 0.3568
    _, _, result = evaluate("R11", tmp_path, params={"m": 10, "n": n})
    for j, (row, rate) in enumerate(zip(rows(result), want, strict=True)):
        assert abs(row[4] - rate) <= 0.02, (j, row[4])


def test_the_provenance_line_leaves_out_m_with_given_lines(tmp_path):
    """The request's m is none with given lines (lines.md, Two modes): the Provenance line names the lines, not m;
    the Design row says "given lines"."""
    case, _, result = evaluate("R7", tmp_path, params={"lines": given({"a": 1})})
    report = render(result, case.spec)
    assert "| Design | given lines, 1 lines, n = 17 |" in report
    provenance = report.split("## Provenance\n\n", 1)[1]
    assert ", m = " not in provenance and 'lines = \\[{"anchor":{},"direction":{"a":1.0}}\\]' in provenance


# --------------------------------------------------------------------------------------------------------------
# The slow tier: the golden report (5 figures) and R5 (its timeouts cost 0.2 s each)


@pytest.mark.slow
def test_ln9_golden_report_r7_random_lines(tmp_path):
    """LN9, LN3, LN6: R7 random lines at the defaults, every run new: the mock report (0044); 5 PNGs, a random
    line's anchor not marked."""
    case = reference.prepare(LINES, "R7")
    made = reference.batch(case, "R7")
    made = RunBatch(made.design, made.runs, np.ones(len(case.design), dtype=bool))
    result = sd.evaluate(case, made, tmp_path)
    assert differences(render(result, case.spec), mock_report("lines")) == []
    assert [f.name for f in result.figures] == [f"lines_{j}" for j in range(5)]
    for f in result.figures:
        assert json.loads((tmp_path / f.card).read_text(encoding="utf-8"))["panels"][0]["anchor"] is None


@pytest.mark.slow
@pytest.mark.parametrize("prediction", ["y", "z"])
def test_ln5_r5_random_lines_runs_not_usable(prediction, tmp_path):
    """LN5 and Expected answers: R5, random, m = 5, n = 17, seed 0: the runs in each failure region fail, by kind
    (line 3: 2 errors and 2 timeouts; line 4: 2 runs missing z); "none: k runs not usable" on each line with any."""
    case, made, result = evaluate("R5", tmp_path, prediction=prediction)
    kinds = made.runs.kind
    line3 = slice(*case.design.lines[3].rows)
    assert int((kinds[line3] == FailureKind.ERROR.code).sum()) == 2
    assert int((kinds[line3] == FailureKind.TIMEOUT.code).sum()) == 2
    usable = made.usable(prediction)
    for line, row in zip(case.design.lines, rows(result), strict=True):
        missing = int((~usable[slice(*line.rows)]).sum())
        assert row[0] == f"{17 - missing} of 17"
        if missing:
            assert row[4] == f"none: {missing} run{'s' if missing > 1 else ''} not usable" and row[3] == "none"
    want = {"y": [0, 0, 0, 4, 0], "z": [0, 0, 0, 4, 2]}[prediction]
    assert [int((~usable[slice(*line.rows)]).sum()) for line in case.design.lines] == want
