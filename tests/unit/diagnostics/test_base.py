"""``ema.diagnostics.base``: parameters and their parsing, the request, one identity per design, the registry, the
precheck's notes, and ``evaluate``'s refusals (architecture.md §6, §7; diagnostics/shared.md; records 0067, 0075).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.designs import generators, samplers
from ema.diagnostics import base
from ema.diagnostics.base import (
    AnalysisContext,
    Computation,
    DecimalText,
    DiagnosticParameter,
    GivenLines,
    Integer,
    Name,
    Point,
)
from ema.report import render
from ema.types.design import Design
from ema.types.errors import NotFound, RequestError
from ema.types.identity import canonical_json, sha256_hex
from ema.types.requests import Progress
from ema.types.results import MeasuredNoisy, Observation, ObservationTable
from ema.types.runs import FailureKind
from ema.types.space import ModelParameterSpace
from tests.support import diagnostics as sd
from tests.support.designs import CONTRACT, CONTRACT_SPACE, model_version_id
from tests.support.diagnostics import Toy

POINT_RUN = base.get("point_run")


# Parameters and their parsing (§7: one parsing for Python, the CLI's --param, and MCP's params; C55)


@pytest.mark.parametrize("value", [3, 3.0, "3", np.int64(3), np.float64(3.0)])
def test_an_integer_has_one_form(value):
    p = DiagnosticParameter("n", "integer ≥ 1", 1, "1", "n.", "yes", 2, Integer(1))
    assert p.parse(value) == 3 and type(p.parse(value)) is int


@pytest.mark.parametrize("value", [True, 0, -1, 2.5, "two", None, [3]])
def test_an_integer_refuses_what_isnt_one(value):
    p = DiagnosticParameter("n", "integer ≥ 1", 1, "1", "n.", "yes", 2, Integer(1))
    with pytest.raises(RequestError, match="diagnostic parameter n"):
        p.parse(value)


@pytest.mark.parametrize("value", [0.7072, "0.7072", "0.70720", "7.072e-1", np.float64(0.7072), "+0.7072"])
def test_alpha_is_its_decimal_text(value):
    """0047; record 0067's hand-off: a float alpha and its text are one value, its shortest decimal."""
    assert DecimalText(0.0, 1.0).read(value, "alpha") == "0.7072"


@pytest.mark.parametrize("value", [1, 0, "1/3", " 0.5", "0x0.8", float("nan"), True, "1.0"])
def test_alpha_outside_or_not_a_decimal_is_refused(value):
    with pytest.raises(RequestError, match="alpha"):
        DecimalText(0.0, 1.0).read(value, "alpha")


def test_alpha_text_keeps_its_decimal_through_parse():
    """0047 item 3 ("the JSON form keeps its text"); record 0075 item 4 and Review round 1 (m1): ``parse`` gives
    ``DecimalText`` the text as written, so a decimal that isn't its double's shortest form stays itself, and padded
    text is refused, as ``read`` refuses it."""
    alpha = DiagnosticParameter("alpha", "decimal in (0, 1)", "0.7072", "0.7072", "alpha.", "yes", "0.5",
                                DecimalText(0.0, 1.0))  # fmt: skip
    assert alpha.parse("0.70720000000000000001") == "0.70720000000000000001"
    assert alpha.parse("0.70720") == alpha.parse("7.072e-1") == alpha.parse(0.7072) == "0.7072"
    for padded in (" 0.7072", "0.7072 ", "\n0.7072"):
        with pytest.raises(RequestError, match="alpha"):
            alpha.parse(padded)


def test_a_point_reads_numbers_as_doubles():
    assert Point().read({"a": 1, "b": np.float64(0.5)}, "x") == {"a": 1.0, "b": 0.5}
    for bad in ([1, 2], {"a": "1"}, {"a": True}, {1: 2.0}, {"a": float("inf")}):
        with pytest.raises(RequestError, match="x"):
            Point().read(bad, "x")


def test_given_lines_read_as_doubles():
    lines = [{"anchor": {"a": 1}, "direction": {"a": 1, "b": 2}}]
    assert GivenLines().read(lines, "lines") == [{"anchor": {"a": 1.0}, "direction": {"a": 1.0, "b": 2.0}}]
    assert GivenLines().read(None, "lines") is None
    for bad in ([], [{"anchor": {}}], [{"direction": {}, "extra": 1}], "a line"):
        with pytest.raises(RequestError, match="lines"):
            GivenLines().read(bad, "lines")


def test_a_name_is_any_well_formed_name_and_the_registry_refuses_one_it_lacks():
    """Records 0076 item 4, 0078 item 1, 0079 (Review round 1): one reader for a registry's name (sampler, basis).
    Any well-formed name is read, "sobol" too, so C14 can read a second value; what isn't a name is refused, naming
    the registered ones; the registry refuses an unregistered name when the design is built ("comes in a later
    version"). The schema: the name's anchored pattern, the registered names as examples, no enum."""
    sampler = Name(samplers.names)
    assert sampler.read("random", "sampler") == "random" and sampler.read("sobol", "sampler") == "sobol"
    for bad in (3, "", "-x", "random sampler", None):
        with pytest.raises(RequestError, match="sampler is a name, such as random"):
            sampler.read(bad, "sampler")
    with pytest.raises(RequestError, match="sampler sobol comes in a later version"):
        samplers.get("sobol")
    schema = sampler.schema()
    assert schema == {"type": "string", "pattern": schema["pattern"], "examples": list(samplers.names())}
    assert re.search(schema["pattern"], "sobol") and not re.search(schema["pattern"], "x sobol")
    for diagnostic in ("scatter", "linear_model", "polynomial_model"):
        readers = {p.name: p.reader for p in base.get(diagnostic).parameters}
        assert isinstance(readers["sampler"], Name), diagnostic


def test_text_is_read_as_json_or_a_bare_string():
    """architecture.md §8: --param k=v is a JSON value, or a bare string."""
    x = POINT_RUN.parameters[0]
    assert x.parse('{"a": 1}') == {"a": 1.0} == x.parse({"a": 1})
    sampler = DiagnosticParameter("sampler", "name", "random", "random", "the sampler.", "yes", "random",
                                  Name(samplers.names))  # fmt: skip
    assert sampler.parse("random") == "random"


def test_each_parameter_has_a_json_schema_with_its_meaning():
    """C55: every schema field described; the default given when it is a value."""
    for p in POINT_RUN.parameters:
        schema = p.json_schema()
        assert schema["description"].startswith(p.meaning) and "Default" in schema["description"]
        assert schema["default"] == p.default
        json.dumps(schema)
    assert POINT_RUN.parameters[1].json_schema()["type"] == "integer"
    rule = DiagnosticParameter("n_min", "integer ≥ 1", lambda d, others: 2 * (d + 1), "2(d + 1)", "n.", "yes", 3,
                               Integer(1))  # fmt: skip
    assert "default" not in rule.json_schema() and rule.info().default is None


def test_describe_lists_every_parameter():
    summary = base.describe(POINT_RUN)
    assert summary.name == "point_run" and not summary.takes_space
    assert [p.name for p in summary.parameters] == ["x", "repeats", "seed"]
    assert "repeats: integer ≥ 0, default 4" in summary.text


# The request (§7, step 2)


def test_the_request_fills_in_defaults_and_the_only_prediction():
    spec = sd.MODELS[1][0]  # two predictions: y and z
    with pytest.raises(RequestError, match="several model predictions"):
        base.make_request(POINT_RUN, spec, None, None, {})
    request = base.make_request(POINT_RUN, spec, None, "y", {})
    assert dict(request.params) == {"x": {}, "repeats": 4, "seed": 0} and request.space is None


def test_the_request_refuses_unknown_parameters_and_spaces():
    with pytest.raises(RequestError, match=r"no diagnostic parameter n \(its parameters: x, repeats, seed\)"):
        base.make_request(POINT_RUN, CONTRACT, None, "y", {"n": 3})
    with pytest.raises(RequestError, match="takes no model parameter space"):
        base.make_request(POINT_RUN, CONTRACT, CONTRACT_SPACE, "y", {})
    with pytest.raises(RequestError, match="toy needs a model parameter space"):
        base.make_request(Toy(), CONTRACT, None, "y", {})
    with pytest.raises(RequestError, match="limit"):
        base.make_request(Toy(), CONTRACT, {**CONTRACT_SPACE, "c": [-1, 1]}, "y", {})


def test_a_default_may_be_a_rule_of_d_and_the_others():
    class Rule(Toy):
        parameters = (
            DiagnosticParameter(
                "n", "integer ≥ 1", lambda d, others: 2 * (d + 1), "2(d + 1)", "n.", "yes", 3, Integer(1)
            ),
            base.seed_parameter("the seed.", "yes"),
        )

    request = base.make_request(Rule(), CONTRACT, CONTRACT_SPACE, "y", {})
    assert request.params["n"] == 8


# One identity per design (record 0067's hand-off)


@pytest.mark.parametrize(
    ("one", "other"),
    [
        ({"repeats": 3}, {"repeats": 3.0}),
        ({"repeats": 3}, {"repeats": "3"}),
        ({"x": {"a": 1}}, {"x": {"a": 1.0}}),
        ({"x": {"a": 1}}, {"x": '{"a": 1.0}'}),
        ({"seed": 2}, {"seed": 2.0}),
    ],
)
def test_one_design_has_one_identity(one, other):
    """n = 3.0 and 3, x's integers and doubles, a seed 2.0 and 2: one request, one identity, byte for byte."""
    a = sd.prepare(POINT_RUN, params=one)
    b = sd.prepare(POINT_RUN, params=other)
    assert canonical_json(a.request.canonical()) == canonical_json(b.request.canonical())
    assert canonical_json(a.identity.canonical()) == canonical_json(b.identity.canonical())


def test_integers_in_the_space_give_one_identity():
    toy = Toy()
    spec = CONTRACT
    ints = base.make_request(toy, spec, {"a": [0, 2], "b": [-1, 1], "c": {"range": [0.01, 100], "scale": "log"}},
                             "y", {"n": 5.0})  # fmt: skip
    floats = base.make_request(toy, spec, CONTRACT_SPACE, "y", {"n": 5})
    assert canonical_json(ints.canonical()) == canonical_json(floats.canonical())
    mv = model_version_id(spec)
    one = toy.design_identity(base.request_space(ints, spec), ints.params, spec, mv)
    two = toy.design_identity(base.request_space(floats, spec), floats.params, spec, mv)
    assert canonical_json(one.canonical()) == canonical_json(two.canonical())


def test_alpha_as_a_float_or_text_is_one_convergent_identity():
    """A float alpha and its decimal text make one identity, which the convergent generator reads (0047)."""
    alpha = DiagnosticParameter("alpha", "decimal in (0, 1)", "0.7072", "0.7072", "alpha.", "yes", "0.5",
                                DecimalText(0.0, 1.0))  # fmt: skip
    space = ModelParameterSpace.parse(CONTRACT_SPACE)
    mv = model_version_id(CONTRACT)
    made = []
    for value in (0.7072, "0.7072", "7.0720e-1"):
        params = {"n_min": 4, "alpha": alpha.parse(value), "level": 2}
        made.append(base.identity("convergent", space, params, CONTRACT, mv, seed=0, sampler="random"))
    assert len({canonical_json(i.canonical()) for i in made}) == 1
    assert len(generators.get("convergent").build(made[0], CONTRACT)) > 4


def test_an_identity_refuses_values_that_arent_canonical():
    space = ModelParameterSpace.parse(CONTRACT_SPACE)
    mv = model_version_id(CONTRACT)
    for params, seed in (({"n": np.int64(3)}, 0), ({"n": 3}, 1.0), ({"n": np.float64(3.0)}, 0)):
        with pytest.raises(TypeError, match="canonical|seed"):
            base.identity("uniform", space, params, CONTRACT, mv, seed=seed, sampler="random")  # type: ignore[arg-type]


# The registry (0065)


def test_register_and_unregister():
    toy = Toy()
    base.register(toy)
    try:
        assert "toy" in base.names() and base.get("toy") is toy
        with pytest.raises(ValueError, match="already registered"):
            base.register(Toy())
    finally:
        base.unregister("toy")
    assert "toy" not in base.names()
    with pytest.raises(ValueError, match="no diagnostic toy"):
        base.unregister("toy")
    with pytest.raises(NotFound, match="the diagnostics are .*point_run"):  # any registered (steps 10-13)
        base.get("toy")


def test_register_refuses_a_spawn_tag_below_2_32_or_taken():
    class Low(Toy):
        name = "low"
        spawn_tags = (5,)

    with pytest.raises(ValueError, match="spawn tag 5"):
        base.register(Low())
    base.register(Toy())
    try:

        class Same(Toy):
            name = "same"

        with pytest.raises(ValueError, match="already used"):
            base.register(Same())
    finally:
        base.unregister("toy")


def test_every_module_in_the_package_registers_itself():
    """Record 0075 item 1: importing ema.diagnostics imports each diagnostic module."""
    assert "point_run" in base.names()


# The context


def test_the_context_streams_and_progress():
    seen: list[Progress] = []
    case = sd.prepare(Toy(), on_progress=seen.append)
    with pytest.raises(ValueError, match="2\\*\\*32"):
        case.ctx.stream(7)
    a, b = case.ctx.stream(sd.TOY_TAG).random(3), case.ctx.stream(sd.TOY_TAG).random(3)
    assert np.array_equal(a, b)
    step = case.ctx.on_step("bootstrap")
    assert step is not None
    step(230, 1000)
    assert seen[-1].text == "bootstrap: 230 of 1000 resamples" and seen[-1].phase == "analysis"
    assert sd.prepare(Toy()).ctx.on_step("bootstrap") is None


def test_evaluate_reports_the_bootstraps_progress(tmp_path):
    """PM10's one callback: the analysis's progress through on_progress."""
    seen: list[Progress] = []
    case = sd.prepare(sd.NoFigures(Toy()), on_progress=seen.append)
    sd.evaluate(case, sd.batch(case), tmp_path)
    assert len(seen) == 1000 and seen[-1].done == seen[-1].total == 1000


# The precheck's notes (shared.md, Notes; S7)


def notes_of(result: Any, code: str) -> str:
    (text,) = [n.text for n in result.notes if n.code == code]
    return text


def test_s7_at_most_5_reasons_by_count_then_design_order(tmp_path):
    """S7: 7 distinct reasons: 5 listed verbatim with counts, by count, ties by the first run; the rest summed."""
    case = sd.prepare(sd.NoFigures(Toy()))
    failed = np.zeros(40, dtype=bool)
    failed[:12] = True
    reasons = ["r1", "r2", "r3", "r1", "r4", "r5", "r6", "r7", "r1", "r3", "r6", "r6"]
    result = sd.evaluate(case, sd.batch(case, failed=failed, reasons=reasons), tmp_path)
    text = notes_of(result, "not_usable")
    assert text.split("\n") == [
        "12 of 40 runs are not usable for y: 12 failed (error).",
        "Most frequent reasons:",
        "  3  r1",
        "  3  r6",
        "  2  r3",
        "  1  r2",
        "  1  r4",
        "  2  (2 other reasons)",
        f'Estimates use the 28 usable runs. ws.failed_runs("{result.result_id[:12]}") lists each one.',
    ]


def test_missing_runs_are_counted_with_their_reasons(tmp_path):
    case = sd.prepare(sd.NoFigures(Toy()))
    missing = np.arange(40) < 3
    result = sd.evaluate(case, sd.batch(case, missing_y=missing), tmp_path)
    assert result.counts.missing == 3 and result.counts.usable == 37
    text = notes_of(result, "not_usable")
    assert text.startswith("3 of 40 runs are not usable for y: 3 missing y.") and "  3  y = (\\S+) not found" in text


def test_reused_failed_runs_are_noted_and_new_ones_arent(tmp_path):
    """0010, C47's note: the reused runs that had failed, and that retry_failed runs them again."""
    case = sd.prepare(sd.NoFigures(Toy()))
    failed = np.arange(40) < 4
    reused = sd.evaluate(case, sd.batch(case, failed=failed), tmp_path / "a")
    assert notes_of(reused, "reused_failed") == (
        "4 of the 40 reused runs had failed before; retry_failed=True runs them again."
    )
    new = sd.batch(case, failed=failed, new=failed)
    fresh = sd.evaluate(case, new, tmp_path / "b")
    assert "reused_failed" not in [n.code for n in fresh.notes]
    assert (fresh.counts.new, fresh.counts.reused) == (4, 36) and fresh.provenance.approval_id == sd.APPROVAL


def test_the_notes_are_plain_text_with_no_markdown(tmp_path):
    """Record 0073 item 1 (a result's text is plain, the report escapes it); record 0075, Review round 1: the
    not-usable and reused-failed notes name ws.failed_runs and retry_failed without backticks, so the report shows
    them as written, not as literal backticks."""
    case = sd.prepare(sd.NoFigures(Toy()))
    result = sd.evaluate(case, sd.batch(case, failed=np.arange(40) < 4), tmp_path)
    texts = [n.text for n in result.notes if n.code in ("not_usable", "reused_failed")]
    assert len(texts) == 2 and not any("`" in t for t in texts), texts
    notes = render(result, case.spec).split("## Notes", 1)[1].split("\n## ", 1)[0]
    assert "`" not in notes and f'ws.failed\\_runs("{result.result_id[:12]}")' in notes, notes


def test_too_few_constant_all_failed_and_no_usable_notes(tmp_path):
    case = sd.prepare(sd.NoFigures(Toy()))
    few = sd.evaluate(case, sd.batch(case, failed=np.arange(40) >= 3), tmp_path / "a")
    assert (
        notes_of(few, "too_few") == "3 usable runs; toy needs at least 5 (a standard deviation from at least 5 runs)."
    )
    assert not few.estimates and few.observations
    constant = sd.evaluate(case, sd.batch(case, y=np.full(40, 0.25)), tmp_path / "b")
    assert notes_of(constant, "constant") == "y is the same in all 40 usable runs: 0.25."
    failed = sd.evaluate(case, sd.batch(case, failed=np.ones(40, bool)), tmp_path / "c")
    assert notes_of(failed, "all_failed") == "All 40 runs failed: no estimates or observations."
    zcase = sd.prepare(sd.NoFigures(Toy()), prediction="z")
    nowhere = sd.evaluate(zcase, sd.batch(zcase, z=np.full(40, np.nan)), tmp_path / "d")
    assert notes_of(nowhere, "no_usable") == "No run is usable for z: 0 failed, 40 missing z."


def test_counts_are_of_distinct_runs(tmp_path):
    """S2: a run shared by two design rows (a shared anchor, G12) is one run in the header."""
    case = sd.prepare(sd.NoFigures(POINT_RUN))
    d = case.design
    rows = [0, 1, 1, 2]
    shared = Design(d.identity, d.points[rows], d.replicates[rows], None, None)
    result = sd.evaluate(case, sd.batch(case, design=shared, failed=np.array([0, 1, 1, 0], bool)), tmp_path)
    assert (result.counts.rows, result.counts.runs, result.counts.usable) == (4, 3, 2)
    assert result.counts.failed[FailureKind.ERROR] == 1


def test_the_measured_noisy_notes(tmp_path):
    """P7, point_run.md: one note per point run, newest first, with the fraction of this result's range; the forms
    with no fraction."""
    spec = CONTRACT
    mv = model_version_id(spec)
    nominal = tuple(p.nominal for p in spec.parameters)
    elsewhere = (1.5, 0.0, 1.0, 0.5)
    records = (
        MeasuredNoisy(sha256_hex("new"), mv, "y", nominal, 11, 2e-7, None),
        MeasuredNoisy(sha256_hex("old"), mv, "y", elsewhere, 5, None, None),
    )
    case = sd.prepare(sd.NoFigures(Toy()), measured_noisy=records)
    made = sd.batch(case)
    result = sd.evaluate(case, made, tmp_path / "a")
    y = made.runs.values["y"]
    one, two = [n.text for n in result.notes if n.code == "measured_noisy"]
    assert one == (
        f"contract@{mv[:12]} was measured noisy in y by point run {sha256_hex('new')[:12]} (11 runs at the nominal "
        f"point): standard deviation 2e-07, {2e-7 / (y.max() - y.min()):.4g} of the range of y in this diagnostic's "
        f"runs ({y.max() - y.min():.4g})."
    )
    assert "(5 runs at the point a = 1.5, b = 0, c = 1, h = 0.5)" in two and "standard deviation none" in two
    flat = sd.evaluate(case, sd.batch(case, y=np.full(40, 3.0)), tmp_path / "b")
    assert "the range of y in this diagnostic's runs is 0, so no fraction" in flat.notes[1].text


# evaluate's refusals (P5, P6)


class Greedy(Toy):
    """Makes estimates whatever the precheck says."""

    def compute(self, run_batch: Any, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        return super().compute(run_batch, ctx, estimates_allowed=True)


class SeesNothing(Toy):
    """Makes an observation of no usable run."""

    def compute(self, run_batch: Any, ctx: AnalysisContext, *, estimates_allowed: bool) -> Computation:
        row = (Observation("count", "Count", 0, ""),)
        return Computation(observations=(ObservationTable("t", "t", ("t", "y"), (row,)),))


def test_evaluate_refuses_estimates_below_the_minimum_or_of_a_constant(tmp_path):
    case = sd.prepare(sd.NoFigures(Greedy()))
    with pytest.raises(ValueError, match="below its minimum"):
        sd.evaluate(case, sd.batch(case, failed=np.arange(40) >= 3), tmp_path / "a")
    with pytest.raises(ValueError, match="constant"):
        sd.evaluate(case, sd.batch(case, y=np.full(40, 1.0)), tmp_path / "b")


def test_evaluate_refuses_observations_of_no_usable_run(tmp_path):
    case = sd.prepare(sd.NoFigures(SeesNothing()))
    with pytest.raises(ValueError, match="no usable run"):
        sd.evaluate(case, sd.batch(case, failed=np.ones(40, bool)), tmp_path)


def test_evaluate_refuses_a_provenance_of_another_request(tmp_path):
    case = sd.prepare(sd.NoFigures(Toy()))
    made = sd.batch(case)
    other = sd.prepare(sd.NoFigures(Toy()), params={"n": 30})
    provenance = base.make_provenance(made, other.ctx, case.diagnostic, case.model_version_id, approval_id=None,
                                      versions=sd.VERSIONS)  # fmt: skip
    with pytest.raises(ValueError, match="another request"):
        base.evaluate(case.diagnostic, made, case.ctx, provenance, sha256_hex("r"), str(tmp_path))


def test_the_result_is_its_json_round_trip_and_the_point_runs_record_is_its_own(tmp_path):
    """C17, C52: the result as stored; the point run's record carries the result's id and model version."""
    case = sd.prepare(POINT_RUN)
    result = sd.evaluate(case, sd.batch(case), tmp_path)
    assert result.measured_noisy is not None and result.measured_noisy.result_id == result.result_id
    assert type(result).from_json(result.to_json()).to_json() == result.to_json()
    assert [f.name for f in result.figures] == ["point_run"] and (Path(tmp_path) / "point_run.png").exists()


def test_library_versions_name_the_four():
    assert sorted(base.library_versions()) == ["ema", "matplotlib", "numpy", "scipy"]
