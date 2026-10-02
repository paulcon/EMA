"""Coordinate lines' known answers (diagnostics/coordinate_lines.md: CL1-CL10, Expected answers, the mock report).

Run batches come from the reference models' functions on the coordinate lines design (tests/support/reference.py);
R8, a program, runs through the runner in the slow golden report test (record 0058; build roadmap, step 11). The
exact-rational rate (``exact_rate``) is the spec's test helper: the Gram coefficients of the runs' doubles in
``fractions``, then the rate in doubles (coordinate_lines.md, Tests it implies).
"""

from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.diagnostics import _lines, base
from ema.diagnostics._lines import LineAnalysis, draw_spectrum
from ema.diagnostics.coordinate_lines import COORD_N
from ema.numerics.gram import gram_coefficients
from ema.plotting import new_figure
from ema.report import render
from ema.types.errors import RequestError
from ema.types.results import DiagnosticResult
from ema.types.runs import FailureKind, RunBatch
from tests.support import diagnostics as sd
from tests.support import reference
from tests.support.numerics import _exact_gram

CL = base.get("coordinate_lines")
#: log10 of the golden ratio: R7's c line's limit (the Bernstein ellipse through the poles ±i/2).
LOG10_PHI = math.log10((1 + math.sqrt(5)) / 2)


def exact_rate(y: np.ndarray) -> tuple[int, float | None]:
    """k* and the rate of a complete line by exact rational arithmetic (coordinate_lines.md, Expected answers): c_k²
    and T(k)² = var - sum_(1 <= j < k) c_j² exact, the floor 10⁻¹⁰ of the range exact; log10 and the slope in
    doubles."""
    n = len(y)
    K = (n - 1) // 2
    p, norms = _exact_gram(n, K)
    yf = [Fraction(float(v)) for v in y]
    mean = sum(yf, Fraction(0)) / n
    T2 = [Fraction(0), sum(((v - mean) ** 2 for v in yf), Fraction(0)) / n]
    for k in range(1, K):
        ip = sum((a * b for a, b in zip(yf, p[k], strict=True)), Fraction(0)) / n
        T2.append(T2[-1] - ip * ip / norms[k])
    floor = (Fraction(1, 10**10) * (max(yf) - min(yf))) ** 2
    k_star = next((k - 1 for k in range(1, K + 1) if not T2[k] > floor), K)
    if k_star < 3:
        return k_star, None
    logT = [0.5 * (math.log10(T2[k].numerator) - math.log10(T2[k].denominator)) for k in range(1, k_star + 1)]
    return k_star, -float(np.polyfit(np.arange(1, k_star + 1), logT, 1)[0])


def r8_by_r7() -> Any:
    """R8's function, as R7 with f and g of no effect: R8's spec and design without its program (fast tier)."""
    r7 = reference.function("R7")
    return lambda a, b, c, e, f, g: r7(a=a, b=b, c=c, e=e)


def evaluate(
    id: str, tmp_path: Path, *, figures: bool = False, fn: Any = None, **kw: Any
) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """Evaluate coordinate lines on a reference model's function; without figures unless asked."""
    case = reference.prepare(CL if figures else sd.NoFigures(CL), id, **kw)
    made = reference.batch(case, id, fn=fn)
    return case, made, sd.evaluate(case, made, tmp_path)


def rows(result: DiagnosticResult) -> dict[str, tuple[Any, ...]]:
    """The rates table: each model parameter's (usable, range, degrees, rate)."""
    table = next(t for t in result.observations if t.key == "line_rates")
    return {row[0].label: tuple(o.value for o in row) for row in table.rows}


def notes(result: DiagnosticResult) -> list[str]:
    return [n.text for n in result.notes]


def test_the_declarations_are_the_specs():
    """coordinate_lines.md: Parameters and Named constants; no interval method, no tag, no estimates; nested in n."""
    assert (CL.takes_space, CL.interval_method, CL.spawn_tags, CL.has_estimates) == (True, None, (), False)
    assert {p.name: (p.default, p.changes_design) for p in CL.parameters} == {
        "n": (17, "yes"),
        "anchor": ({}, "yes"),
        "seed": (0, "no"),
    }
    assert CL.nesting == ("n",) and CL.min_runs(6, {})[0] == _lines.COORD_MIN_RUNS == 1
    assert (COORD_N, _lines.COORD_MIN_N, _lines.LINE_RATE_MIN_DEGREES) == (17, 7, 3)
    assert (_lines.LINE_RATE_FLOOR, _lines.LINE_RATE_WINDOW, _lines.SPECTRUM_YMIN) == (1e-10, 0.5, 1e-17)
    assert _lines.RATE_SHIFT_TOL == 1e-5 and [_lines.window(n) for n in (7, 16, 17, 33)] == [3, 7, 8, 16]


def test_cl1_the_design_is_the_generators_and_refusals_come_before_building():
    """CL1: the design is coordinate_lines(...) bit for bit; n = 6, a space holding every model parameter, and the
    anchor at b's lo (a point of b's line, off center; 0051) are refused before building, naming b."""
    case = reference.prepare(CL, "R7")
    space = base.request_space(case.request, case.spec)
    ident = base.identity("coordinate_lines", space, {"n": 17, "anchor": {}}, case.spec, case.model_version_id, seed=0)
    design = generators.get("coordinate_lines").build(ident, case.spec)
    assert np.array_equal(case.design.points, design.points) and case.design.lines == design.lines
    assert case.identity == ident
    with pytest.raises(RequestError, match="n"):
        reference.prepare(CL, "R7", params={"n": 6})
    with pytest.raises(RequestError, match="varies no model parameter"):
        reference.prepare(CL, "R7", space={"a": 0.1})
    with pytest.raises(RequestError, match="model parameter b"):
        reference.prepare(CL, "R7", params={"anchor": {"b": -1.0}})
    assert len(reference.prepare(CL, "R7", params={"n": 16}).design) == 64  # any n >= 7, even included


@pytest.mark.parametrize(
    ("n", "expected"),
    [(17, (0.1811111, 0.06916461, 0.1957442, 0.1811111)), (33, (0.1103366, 0.03749946, 0.2088262, 0.1103366))],
)
def test_cl2_cl3_r7_rates_and_exact_rational_arithmetic(n, expected, tmp_path):
    """Expected answers, R7 (and R8) along a, b, c, e at n = 17 and 33: within 1e-6; and each within 1e-9 of exact
    rational arithmetic on the same runs' doubles, with the same k* (CL2, CL3)."""
    case, made, result = evaluate("R7", tmp_path, params={"n": n})
    found = rows(result)
    y = made.runs.values["y"]
    for line, name, want in zip(case.design.lines, "abce", expected, strict=True):
        usable, _, degrees, rate = found[name]
        k_star, exact = exact_rate(y[slice(*line.rows)])
        assert usable == f"{n} of {n}" and degrees == f"{k_star} of {(n - 1) // 2}"
        assert rate == pytest.approx(want, abs=1e-6) and exact is not None and abs(rate - exact) <= 1e-9


def test_cl3_the_constructed_spectrum_has_rate_1():
    """CL3: y = sum_k 10⁻ᵏ G_k at n = 33: rate 1 within 1e-6 (0048)."""
    n = 33
    G = n * np.array([gram_coefficients(e) for e in np.eye(n)])
    analysis = _lines.analyze(G @ (10.0 ** -np.arange(n)), np.ones(n, dtype=bool), all_constant=False)
    assert analysis.fit is not None and analysis.k_star is not None and analysis.k_star >= 3
    assert analysis.fit[0] == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("n", [33, 65, 129])
def test_r7_along_c_converges_to_log10_phi(n, tmp_path):
    """Expected answers: R7 along c (R11's g) at n = 33, 65, 129: log10 φ = 0.2090 within 0.01."""
    _, _, result = evaluate("R7", tmp_path, params={"n": n}, space={"c": [-1, 1]})
    assert abs(rows(result)["c"][3] - LOG10_PHI) <= 0.01


def test_cl4_cl6_r8_rows_and_constant_lines(tmp_path):
    """CL4, CL6, the mock's observations: R8 at n = 17 (R7's function): one row per model parameter, in order; f and
    g constant: range 0, "0 of 8", "none: constant", and one note each, after the shared ones."""
    case, _, result = evaluate("R8", tmp_path, fn=r8_by_r7())
    assert list(rows(result)) == ["a", "b", "c", "e", "f", "g"]
    found = rows(result)
    for name, (rng, rate) in {"a": (0.4, 0.1811111), "b": (1.0, 0.06916461), "c": (0.8, 0.1957442)}.items():
        assert found[name][:3] == ("17 of 17", pytest.approx(rng, abs=1e-15), "8 of 8")
        assert found[name][3] == pytest.approx(rate, abs=1e-6)
    assert found["f"] == found["g"] == ("17 of 17", 0.0, "0 of 8", "none: constant")
    assert notes(result) == [f"y is the same in all 17 usable runs along {v}: 1." for v in "fg"]
    assert result.counts.runs == 97 and len(case.design) == 102


def test_r1_lines_are_linear_and_c_is_constant(tmp_path):
    """Expected answers, R1: along a, b, k (k on a log range) k* = 1 and no rate; along c, the note and none: constant."""
    _, _, result = evaluate("R1", tmp_path)
    found = rows(result)
    for name in "abk":
        assert found[name][2:] == ("1 of 8", "none")
    assert found["c"][2:] == ("0 of 8", "none: constant")
    assert notes(result) == ["y is the same in all 17 usable runs along c: 10."]


def test_r10_degrees_and_constant_lines(tmp_path):
    """Expected answers, R10 along a, b, c, e: k* = 1, 2, 0, 0; c and e constant, with notes (CL6)."""
    _, _, result = evaluate("R10", tmp_path)
    assert [row[2] for row in rows(result).values()] == ["1 of 8", "2 of 8", "0 of 8", "0 of 8"]
    assert [row[3] for row in rows(result).values()] == ["none", "none", "none: constant", "none: constant"]
    assert [n.split(":")[0] for n in notes(result)] == [f"y is the same in all 17 usable runs along {v}" for v in "ce"]


def test_r2_along_x3_is_constant_at_0(tmp_path):
    """Expected answers, R2 along x3 through the nominal point: y = sin 0 = 0 exactly; the note."""
    _, _, result = evaluate("R2", tmp_path)
    assert notes(result) == ["y is the same in all 17 usable runs along x3: 0."]


def test_r3_rates_at_n_17(tmp_path):
    """Expected answers, R3 at n = 17: the eight rates within 2e-4 (0058), k* exactly; Hu and Hl linear."""
    want = {
        "rw": (1.642241, 7),
        "r": (3.143281, 4),
        "Tu": (0.8161252, 8),
        "Hu": (None, 1),
        "Tl": (0.8160101, 8),
        "Hl": (None, 1),
        "L": (0.9904442, 8),
        "Kw": (3.630201, 3),
    }
    _, _, result = evaluate("R3", tmp_path)
    found = rows(result)
    assert list(found) == list(want)
    for name, (rate, k_star) in want.items():
        assert found[name][2] == f"{k_star} of 8"
        if rate is None:
            assert found[name][3] == "none"
        else:
            assert found[name][3] == pytest.approx(rate, abs=2e-4), name


def test_r4a_is_constant_and_r4b_is_not(tmp_path):
    """CL6 and Expected answers: R4a, the shared note only, each line "none: constant"; R4b, a rate with k* >= 3 on
    each line and no note (0035)."""
    _, _, constant = evaluate("R4a", tmp_path / "a")
    assert [n.code for n in constant.notes] == ["constant"]
    assert all(row[1:] == (0.0, "0 of 8", "none: constant") for row in rows(constant).values())
    _, _, wiggle = evaluate("R4b", tmp_path / "b")
    assert not wiggle.notes
    for _, _, degrees, rate in rows(wiggle).values():
        assert int(degrees.split()[0]) >= 3 and isinstance(rate, float)


def test_cl5_runs_not_usable_on_a_line(tmp_path):
    """CL5 and Expected answers: R5, prediction z, along b: b = 0.875 and 1 missing z; 15 of 17 usable; no spectrum,
    k*, or rate; the range over the usable runs."""
    case, made, result = evaluate("R5", tmp_path, prediction="z")
    line = case.design.lines[1]
    usable = made.usable("z")[slice(*line.rows)]
    assert case.design.points[slice(*line.rows)][~usable, 1].tolist() == [0.875, 1.0]
    z = made.runs.values["z"][slice(*line.rows)][usable]
    assert rows(result)["b"] == ("15 of 17", float(z.max() - z.min()), "none", "none: 2 runs not usable")


@pytest.mark.parametrize(
    ("anchor", "n", "said"),
    [
        ({}, 17, "all 6 lines share the anchor's run"),
        ({"b": 0.3}, 17, "lines through the anchor: a, c, e, f, g"),
        ({}, 16, "lines through the anchor: none (n is even)"),
    ],
)
def test_cl7_the_design_row_says_which_lines_contain_the_anchor(anchor, n, said, tmp_path):
    """CL7: 6 model parameters (R8's spec): centered at n = 17; the anchor off center in b; n = 16."""
    case = reference.prepare(sd.NoFigures(CL), "R8", params={"anchor": anchor, "n": n})
    made = sd.batch(case, y=case.design.points.sum(axis=1), z=case.design.points.sum(axis=1))
    report = render(sd.evaluate(case, made, tmp_path), case.spec)
    design_row = next(line for line in report.split("\n") if line.startswith("| Design |"))
    assert design_row.endswith(f"; {said} |"), design_row


@pytest.mark.parametrize("n", [17, 33])
def test_cl8_changes_of_units(n, tmp_path):
    """CL8: R2 under y -> 2⁻¹⁰·y + 3: rates within RATE_SHIFT_TOL, k* and notes identical, ranges times 2⁻¹⁰; under
    2⁻¹⁰·y alone, rates within 1e-12 and ranges exact."""
    r2 = reference.function("R2")
    _, _, ref = evaluate("R2", tmp_path / "ref", params={"n": n})
    for b, tol in ((3.0, _lines.RATE_SHIFT_TOL), (0.0, 1e-12)):
        _, _, got = evaluate("R2", tmp_path / str(b), params={"n": n}, fn=lambda _b=b, **x: 2.0**-10 * r2(**x) + _b)
        assert notes(got) == [t.replace(": 0.", f": {3 if b else 0}.") for t in notes(ref)]
        for name, (usable, rng, degrees, rate) in rows(ref).items():
            g_usable, g_rng, g_degrees, g_rate = rows(got)[name]
            assert (g_usable, g_degrees) == (usable, degrees)
            assert g_rng == 2.0**-10 * rng if not b else abs(g_rng - 2.0**-10 * rng) <= 1e-15
            assert g_rate == rate if isinstance(rate, str) else abs(g_rate - rate) <= tol


@pytest.mark.slow  # two PNGs; C12 checks the strips in the fast tier
def test_cl9_the_figures_on_r5(tmp_path):
    """CL9: one PNG per varied model parameter; the × strip's count equals the header's; b's spectrum panel is kept,
    empty, with the reason; the card's c_k are the line's Gram coefficients, and its rate is the result's."""
    case, made, result = evaluate("R5", tmp_path, figures=True, prediction="z")
    assert [f.name for f in result.figures] == ["coordinate_lines_a", "coordinate_lines_b"]
    cards = [json.loads((tmp_path / f.card).read_text(encoding="utf-8")) for f in result.figures]
    strips = sum(len(card["panels"][0]["not_usable"]) for card in cards)
    assert strips == result.counts.runs - result.counts.usable == 2
    assert cards[1]["panels"][1]["text"] == "no spectrum: 2 runs not usable" and cards[1]["spectrum"]["reason"]
    line = case.design.lines[0]
    assert cards[0]["spectrum"]["c"] == gram_coefficients(made.runs.values["z"][slice(*line.rows)]).tolist()
    assert cards[0]["spectrum"]["rate"] is None and rows(result)["a"][3] == "none"
    assert cards[0]["panels"][0]["anchor"] == 0.0 and cards[0]["panels"][0]["x"]["label"] == "a"


def test_cl9_a_value_below_the_panel_is_an_open_marker_on_the_bottom_edge():
    """CL9 (0048): a constructed spectrum with one value below SPECTRUM_YMIN: one open marker on the bottom edge."""
    c = np.array([1.0, 0.5, 1e-3, 0.0, 1e-5, 1e-6, 1e-7])
    T = np.sqrt(np.cumsum((c * c)[::-1])[::-1])
    analysis = LineAnalysis(7, 3, 7, 1.0, c, T, 3, 1e-10, (2.0, 0.0))
    _fig, (ax,) = new_figure(1)
    panel, numbers = draw_spectrum(ax, analysis)
    open_markers = [ln for ln in ax.get_lines() if ln.get_markerfacecolor() == "none"]
    assert len(open_markers) == 1 and open_markers[0].get_ydata().tolist() == [_lines.SPECTRUM_YMIN]
    assert open_markers[0].get_xdata().tolist() == [3.0] and ax.get_ylim()[0] == _lines.SPECTRUM_YMIN
    assert numbers["c"] is c and len(panel["points"]) == 6


def test_the_seed_is_recorded_and_changes_nothing(tmp_path):
    """coordinate_lines.md: another seed is another diagnostic evaluation with the same numbers (C8, 0061)."""
    _, made, first = evaluate("R7", tmp_path / "a")
    other = reference.prepare(sd.NoFigures(CL), "R7", params={"seed": 7})
    second = sd.evaluate(other, made, tmp_path / "b")
    assert second.result_id != first.result_id and second.observations == first.observations
    assert second.provenance.request.params["seed"] == 7


# --------------------------------------------------------------------------------------------------------------
# The refinements to n = 129; R8 through the runner (the slow tier)


class _Interrupted(Exception):
    """Stops the first evaluation's runs, as Ctrl-C would (U2's interrupted evaluation; C49)."""


def run_r8_through_the_runner(root: Path) -> tuple[sd.Case, RunBatch, str]:
    """U2 on R8 through ``ema.runner`` and ``ema.approval`` with a temporary store: the first evaluation interrupted
    after 41 runs, then its rerun, which reuses them and makes the other 56 (the mock report's header)."""
    from ema import approval, runner
    from ema.models.processes import ModelProcesses
    from ema.store import Store
    from tests.support.runner import row_run_ids

    model = reference.model("R8")
    case = reference.prepare(CL, "R8")
    assert case.model_version_id == model.model_version_id
    with Store.open(root / "ws") as store:
        store.record_loading(model.spec, model.spec_path, model.files)
        processes = ModelProcesses()
        try:

            def approve(resolution: Any) -> str:
                price = runner.price(resolution, store)
                return approval.ask_approval(store=store, model=model, asked_for="diagnostic_evaluation",
                                             request=case.request, design=case.identity, resolution=resolution,
                                             price=price, approve=lambda question: True)  # fmt: skip

            def stop(progress: Any) -> None:
                if progress.done == 41:
                    raise _Interrupted

            first = runner.resolve(case.design, model, store, retry_failed=False)
            with pytest.raises(_Interrupted):
                runner.run_new(model, first, approve(first), store, processes, on_progress=stop)
            rerun = runner.resolve(case.design, model, store, retry_failed=False)
            assert len(rerun.new_keys) == 56
            approval_id = approve(rerun)
            assert runner.run_new(model, rerun, approval_id, store, processes) == 56
            made = runner.read_batch(case.design, row_run_ids(rerun), store, new_approval=approval_id)
        finally:
            processes.close()
    return case, made, approval_id


@pytest.mark.slow
def test_cl10_r8_golden_report_through_the_runner(tmp_path):
    """CL10, CL4, CL6, CL9: U2 on R8, a command-line program, run through the runner (record 0058's step 11): the
    report is the mock report (0044: structure, and numbers within one unit in the 4th digit), its rates within 1e-6
    of the Expected answers; 6 PNGs, 2 with "no spectrum: constant"; the data cards byte-identical on a rerun of the
    analysis (S10)."""
    from tests.support.reports import differences, mock_report

    case, made, approval_id = run_r8_through_the_runner(tmp_path)
    provenance = base.make_provenance(made, case.ctx, CL, case.model_version_id, approval_id=approval_id,
                                      versions=sd.VERSIONS)  # fmt: skip
    results = [
        base.evaluate(CL, made, case.ctx, provenance, sd.result_id(case, made), str(tmp_path / out))
        for out in ("one", "two")
    ]
    result = results[0]
    assert differences(render(result, case.spec), mock_report("coordinate_lines")) == []
    found = rows(result)
    for name, want in zip("abce", (0.1811111, 0.06916461, 0.1957442, 0.1811111), strict=True):
        assert found[name][3] == pytest.approx(want, abs=1e-6)
    assert [f.name for f in result.figures] == [f"coordinate_lines_{v}" for v in "abcefg"]
    texts = [json.loads((tmp_path / "one" / f.card).read_text())["panels"][1].get("text") for f in result.figures]
    assert texts == [None] * 4 + ["no spectrum: constant"] * 2
    for f in result.figures:
        assert (tmp_path / "one" / f.card).read_bytes() == (tmp_path / "two" / f.card).read_bytes()


def test_r7_rates_under_refinement(tmp_path):
    """Expected answers: each rate over the one before, n = 17 -> 33 -> 65 -> 129: along a and b within [0.45, 0.65]
    (a kink, a jump: halved), along c within [0.95, 1.1] (analytic)."""
    rates = {}
    for n in (17, 33, 65, 129):
        _, _, result = evaluate("R7", tmp_path / str(n), params={"n": n})
        rates[n] = rows(result)
    for before, after in ((17, 33), (33, 65), (65, 129)):
        for name, (lo, hi) in {"a": (0.45, 0.65), "b": (0.45, 0.65), "c": (0.95, 1.1)}.items():
            assert lo <= rates[after][name][3] / rates[before][name][3] <= hi, (name, before, after)


def test_the_contract_fixture_makes_a_shared_anchor_one_run(tmp_path):
    """The diagnostic contract's batch builder (step 09's review, M2; record 0077): a run in several rows (the shared
    anchor) is one run: failed at every row when any of its rows is masked, with one kind and reason."""
    case = sd.prepare(sd.NoFigures(CL))
    ids = sd.batch(case).runs.run_ids
    middle = [line.rows[0] + 4 for line in case.design.lines]  # n = 9: each line's middle row is the anchor's run
    assert len({ids[r].tobytes() for r in middle}) == 1
    mask = np.zeros(len(case.design), dtype=bool)
    mask[middle[1]] = True
    mask[0] = True
    made = sd.batch(case, failed=mask, kinds=[FailureKind.ERROR, FailureKind.TIMEOUT])
    assert (
        made.runs.kind[middle].tolist() == [FailureKind.TIMEOUT.code] * 3
        and made.runs.kind[0] == FailureKind.ERROR.code
    )
    result = sd.evaluate(case, made, tmp_path)
    assert result.counts.failed[FailureKind.TIMEOUT] == 1 and result.counts.failed[FailureKind.ERROR] == 1
