"""The diagnostic result and its parts (architecture.md §3, results.py; record 0070).

C17 at the type level: strict JSON, loads back equal, every double exact, the design structure included (0063),
a "none" interval as null with its reason (0041); its negative control, a NaN estimate, is refused. Also 0036
(never empty), I11 (canonical JSON), S2's counts, V4/V6's interval information, and U8's and §7's shown text.
"""

import json
import math
import struct
from datetime import UTC, datetime
from types import MappingProxyType

import numpy as np
import pytest

from ema.types.design import DesignIdentity, DesignStructure, Line
from ema.types.identity import ID_DTYPE, canonical_json, id_array
from ema.types.requests import Request
from ema.types.results import (
    Counts,
    DiagnosticResult,
    Estimate,
    EstimateTable,
    Figure,
    IntervalInfo,
    MeasuredNoisy,
    Note,
    Observation,
    ObservationTable,
    Provenance,
    Reproduction,
    ResultSummary,
)
from ema.types.runs import FailureKind

MV = "ab" * 32
RID = "12" * 32
# Doubles that must come back bit for bit (C17): -0.0, a subnormal, the smallest normal / 3, 0.1, a large one.
AWKWARD = (-0.0, 5e-324, 2.2250738585072014e-308 / 3, 0.1, 1e300, -0.009447123456789)


def bits(x):
    return struct.pack("<d", x)


def request():
    return Request(
        diagnostic="scatter",
        prediction="y",
        space={"a": [0.0, 2.0], "c": {"range": [0.01, 100.0], "scale": "log"}, "h": 0.5},
        params={"n": 3, "seed": 1},
    )


def identity():
    return DesignIdentity(
        model_version_id=MV,
        kind="uniform",
        space=request().space,
        params={"n": 3},
        seed=1,
        sampler="random",
        sampler_version="1",
        generator_version="1",
    )


def noisy(**kw):
    fields = {
        "result_id": "34" * 32,
        "model_version_id": MV,
        "prediction": "y",
        "point": (1.0, 1.0, 0.5),
        "runs": 11,
        "std": 0.0123,
        "made_at": datetime(2026, 10, 1, 14, 3, 7, 123000, tzinfo=UTC),
    }
    fields.update(kw)
    return MeasuredNoisy(**fields)


def provenance(**kw):
    fields = {
        "ema": "2.0.0.dev0",
        "numpy": "2.5.3",
        "scipy": "1.16.0",
        "matplotlib": "3.10.0",
        "model_version_id": MV,
        "request": request(),
        "design": identity(),
        "run_ids": id_array(["0a" * 32, "0b" * 32, "0a" * 32]),
        "approval_id": "ef" * 32,
        "spawn_tags": (2**32 + 1,),
        "measured_noisy_read": (noisy(),),
        "design_structure": DesignStructure(
            levels=(1, 3),
            lines=(
                Line(
                    anchor=(1.0, AWKWARD[2], 0.5),
                    direction=(0.6, -0.8),
                    ends=((0.0, 0.01, 0.5), (2.0, 100.0, 0.5)),
                    rows=(0, 3),
                ),
            ),
        ),
    }
    fields.update(kw)
    return Provenance(**fields)


def counts(**kw):
    fields = {
        "rows": 3,
        "runs": 2,
        "new": 1,
        "reused": 1,
        "failed": {FailureKind.TIMEOUT: 1},
        "missing": 0,
        "usable": 1,
    }
    fields.update(kw)
    return Counts(**fields)


def interval_info(**kw):
    fields = {
        "method": "bootstrap",
        "settings": {"resamples": 1000, "percentiles": [0.5, 99.5], "seed": 1},
        "n_usable": 166,
        "undefined": {"S_T,a": 3},
    }
    fields.update(kw)
    return IntervalInfo(**fields)


def estimates():
    return EstimateTable(
        key="rank_correlation",
        title="Rank correlation with y",
        columns=("Model parameter", "Rank correlation", "Variability interval"),
        estimates=(
            Estimate(key="rank_correlation", label="a", value=AWKWARD[5], interval=(-0.5, 0.25), reason=None),
            Estimate(
                key="rank_correlation",
                label="c",
                value=-0.0,
                interval=None,
                reason="none: 7 of 1000 resamples defined, fewer than 201",
            ),
        ),
        units="",
        interval=interval_info(),
    )


def observations():
    return ObservationTable(
        key="shared",
        title="Of the 1 usable runs",
        columns=("Of the 1 usable runs", "y"),
        rows=(
            (Observation(key="min", label="Minimum", value=AWKWARD[1], units="K"),),
            (Observation(key="count", label="Distinct", value=1, units=""),),
            (Observation(key="kind", label="Replicate 2", value="timeout", units=""),),
        ),
    )


def result(**kw):
    fields = {
        "result_id": RID,
        "diagnostic": "scatter",
        "title": "Scatter",
        "model_version_id": MV,
        "prediction": "y",
        "counts": counts(),
        "header_rows": (("Fit", "degree 2, Legendre, 10 terms"),),
        "notes": (Note(code="not_usable", text="1 of 2 runs is not usable for y: 1 failed (timeout)."),),
        "estimates": (estimates(),),
        "observations": (observations(),),
        "figures": (Figure(name="scatter_y", png="scatter_y.png", card="scatter_y.json", caption="y against each"),),
        "extra": (),
        "measured_noisy": None,
        "provenance": provenance(),
    }
    fields.update(kw)
    return DiagnosticResult(**fields)


class TestEstimate:
    def test_value_as_double(self):
        e = Estimate(key="mean", label="mean", value=3, interval=(2, 4), reason=None)
        assert isinstance(e.value, float) and e.interval == (2.0, 4.0)

    @pytest.mark.parametrize(
        "kw",
        [
            {"value": math.nan},  # C17's negative control
            {"value": math.inf},
            {"value": True},
            {"interval": None, "reason": None},  # "none" needs its reason (0041)
            {"interval": None, "reason": ""},
            {"interval": (1.0, 2.0), "reason": "x"},
            {"interval": (2.0, 1.0)},
            {"interval": (math.nan, 1.0)},
        ],
    )
    def test_refusals(self, kw):
        fields = {"key": "mean", "label": "mean", "value": 1.0, "interval": (0.0, 2.0), "reason": None}
        fields.update(kw)
        with pytest.raises(ValueError):
            Estimate(**fields)


class TestParts:
    def test_interval_info_read_only(self):
        info = interval_info()
        assert isinstance(info.settings, MappingProxyType) and isinstance(info.undefined, MappingProxyType)
        assert info.settings["percentiles"] == (0.5, 99.5)

    def test_interval_info_refuses_negative_counts(self):
        with pytest.raises(ValueError):
            interval_info(undefined={"a": -1})

    @pytest.mark.parametrize("value", [math.nan, True, None])
    def test_observation_refusals(self, value):
        with pytest.raises(ValueError):
            Observation(key="min", label="Minimum", value=value, units="")

    def test_counts_fill_every_kind(self):
        c = counts()
        assert dict(c.failed) == {FailureKind.ERROR: 0, FailureKind.TIMEOUT: 1, FailureKind.UNREAD: 0}
        assert isinstance(c.failed, MappingProxyType)

    @pytest.mark.parametrize(
        "kw",
        [
            {"new": 2},  # new + reused != runs
            {"usable": 2},  # failed + missing + usable != runs
            {"runs": 4, "new": 3},  # more runs than rows
            {"missing": -1, "usable": 2},
        ],
    )
    def test_counts_refusals(self, kw):
        with pytest.raises(ValueError):
            counts(**kw)

    def test_measured_noisy_timestamp(self):
        """§3.2: a timestamp is UTC to the millisecond."""
        m = noisy(made_at=datetime(2026, 10, 1, 14, 3, 7, 123999, tzinfo=UTC))
        assert m.made_at == datetime(2026, 10, 1, 14, 3, 7, 123000, tzinfo=UTC)
        with pytest.raises(ValueError):
            noisy(made_at=datetime(2026, 10, 1))  # noqa: DTZ001
        assert noisy(made_at=None, std=None).std is None


class TestProvenance:
    def test_run_ids_array(self):
        p = provenance(run_ids=["0a" * 32, "0b" * 32])
        assert p.run_ids.dtype == ID_DTYPE and not p.run_ids.flags.writeable

    def test_round_trip_and_equality(self):
        p = provenance()
        back = Provenance.from_canonical(json.loads(canonical_json(p.canonical())))
        assert back == p
        assert provenance(numpy="2.4.0") != p

    def test_canonical_holds_ids_as_hex(self):
        form = provenance().canonical()
        assert form["run_ids"] == ["0a" * 32, "0b" * 32, "0a" * 32]
        assert form["design_structure"]["levels"] == [1, 3]


class TestDiagnosticResult:
    def test_round_trip_c17(self):
        """C17: strict JSON; loads back equal; every double exact; the design structure included."""
        r = result()
        text = r.to_json()
        json.loads(text, parse_constant=lambda c: pytest.fail(f"not strict JSON: {c}"))
        assert text == canonical_json(json.loads(text))  # I11: canonical
        back = DiagnosticResult.from_json(text)
        assert back == r and back.to_json() == text
        est = back.estimates[0].estimates
        assert bits(est[0].value) == bits(AWKWARD[5]) and bits(est[1].value) == bits(-0.0)
        assert bits(back.observations[0].rows[0][0].value) == bits(AWKWARD[1])
        line = back.provenance.design_structure.lines[0]
        assert bits(line.anchor[1]) == bits(AWKWARD[2])
        assert back.observations[0].rows[1][0].value == 1 and isinstance(back.observations[0].rows[1][0].value, int)
        assert back.provenance.measured_noisy_read == (noisy(),)
        assert back.counts == r.counts

    def test_none_interval_is_null_with_its_reason(self):
        """0041: "none" stored as null, with its reason."""
        data = json.loads(result().to_json())
        stored = data["estimates"][0]["estimates"][1]
        assert stored["interval"] is None and stored["reason"].startswith("none: 7 of 1000")

    def test_shown_left_out_and_not_compared(self):
        r = result()
        summary = ResultSummary.make(
            r, short_id="1212", model_version="beam@abababababab", made_at=datetime(2026, 10, 1, tzinfo=UTC)
        )
        shown = result(shown=summary)
        assert shown == r and shown.to_json() == r.to_json()
        assert str(shown) == summary.text

    def test_str_without_shown(self):
        assert str(result()) == f"Diagnostic result {RID[:12]}: scatter, y"

    def test_measured_noisy_and_extra_round_trip(self):
        r = result(measured_noisy=noisy(), extra=(estimates(),), observations=(), estimates=())
        assert DiagnosticResult.from_json(r.to_json()) == r

    def test_never_empty_0036(self):
        with pytest.raises(ValueError):
            result(notes=(), estimates=(), observations=())

    def test_provenance_must_match(self):
        with pytest.raises(ValueError):
            result(provenance=provenance(model_version_id="cd" * 32))
        with pytest.raises(ValueError):
            result(counts=counts(rows=4))

    def test_differs_when_a_double_differs(self):
        other = result(estimates=(estimates(),), extra=())
        assert other == result()
        changed = EstimateTable(**{**estimates().__dict__, "units": "K"})
        assert result(estimates=(changed,)) != result()

    def test_from_json_refuses_malformed(self):
        with pytest.raises(ValueError):
            DiagnosticResult.from_json('{"result_id": 1}')
        with pytest.raises(ValueError):
            DiagnosticResult.from_json("[1, NaN]")


class TestShownText:
    def test_result_summary_text(self):
        """§7: "Diagnostic result 3f2a: scatter on beam@91c0…, T_max; 200 runs: 200 new, 0 reused, 0 failed;
        report: ema report 3f2a"."""
        r = result(
            prediction="T_max",
            counts=Counts(rows=3, runs=3, new=3, reused=0, failed={}, missing=0, usable=3),
            notes=(),
            provenance=provenance(request=Request(**{**request().canonical(), "prediction": "T_max"})),
        )
        s = ResultSummary.make(
            r, short_id="3f2a", model_version="beam@91c0aaaaaaaa", made_at=datetime(2026, 10, 1, tzinfo=UTC)
        )
        assert (
            s.text
            == "Diagnostic result 3f2a: scatter on beam@91c0aaaaaaaa, T_max; 3 runs: 3 new, 0 reused, 0 failed; report: ema report 3f2a"
        )
        assert (s.result_id, s.runs, s.failed, s.diagnostic, s.prediction) == (RID, 3, 0, "scatter", "T_max")
        assert str(s) == s.text

    def test_failed_counted_over_kinds(self):
        s = ResultSummary.make(
            result(), short_id="1212", model_version="m@ab", made_at=datetime(2026, 10, 1, tzinfo=UTC)
        )
        assert s.failed == 1 and "2 runs: 1 new, 1 reused, 1 failed" in s.text

    def test_reproduction_identical(self):
        """U8: "Diagnostic result 3f2a: identical (estimates, intervals, notes, figures' data cards).\""""
        r = result()
        rep = Reproduction.make(r, short_id="3f2a", identical=True, differences=(), provenance_differences=())
        assert rep.text == "Diagnostic result 3f2a: identical (estimates, intervals, notes, figures' data cards)."
        assert rep.result_id == RID and str(rep) == rep.text

    def test_reproduction_differs(self):
        """U8: "Differs: 2 estimates. Provenance differs in numpy (2.3.1 here, 2.4.0 there).\""""
        rep = Reproduction.make(
            result(),
            short_id="3f2a",
            identical=False,
            differences=("2 estimates",),
            provenance_differences=("numpy: 2.3.1 here, 2.4.0 there",),
        )
        assert rep.text == "Differs: 2 estimates. Provenance differs in numpy (2.3.1 here, 2.4.0 there)."

    def test_reproduction_design_check_and_no_original(self):
        rep = Reproduction.make(
            result(),
            short_id="3f2a",
            identical=None,
            differences=(),
            provenance_differences=("numpy: 2.3.1 here, 2.4.0 there", "design points differ at rows 3, 17"),
        )
        assert rep.text == (
            "Diagnostic result 3f2a: replayed from its provenance, with no original to compare. "
            "Provenance differs in numpy (2.3.1 here, 2.4.0 there). Design points differ at rows 3, 17."
        )


def test_arrays_in_the_provenance_compare_by_value():
    a, b = provenance(), provenance(run_ids=np.array(provenance().run_ids))
    assert a == b
