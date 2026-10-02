"""Requests, the test run's request, the questions, and progress (architecture.md §3, requests.py; record 0070).

data_model.md §3.4 (the request's canonical form, the test run's; 0061's doubles); P3; U2's progress line.
"""

import math
from types import MappingProxyType

import numpy as np
import pytest

from ema.types.errors import RequestError
from ema.types.identity import canonical_json
from ema.types.requests import ApprovalRequest, ConfirmationRequest, Progress, Request, TestRunRequest
from ema.types.runs import Price


def make_request(**kw):
    fields = {
        "diagnostic": "scatter",
        "prediction": "y",
        "space": {"b": [0, 1], "a": {"range": [1e-2, 1e2], "scale": "log"}, "h": 3},
        "params": {"n": 200, "seed": 1, "lines": [{"anchor": {"a": 1.0}}]},
    }
    fields.update(kw)
    return Request(**fields)


class TestRequest:
    def test_canonical_form(self):
        """§3.4: every range written {"range": [lo, hi], "scale": ...}, held values and ends as doubles."""
        r = make_request()
        assert r.canonical() == {
            "diagnostic": "scatter",
            "prediction": "y",
            "space": {
                "a": {"range": [0.01, 100.0], "scale": "log"},
                "b": {"range": [0.0, 1.0], "scale": "linear"},
                "h": 3.0,
            },
            "params": {"n": 200, "seed": 1, "lines": [{"anchor": {"a": 1.0}}]},
        }
        assert canonical_json(r.canonical()) == canonical_json(make_request(space=dict(r.space)).canonical())

    def test_read_only(self):
        r = make_request()
        assert isinstance(r.params, MappingProxyType) and isinstance(r.space, MappingProxyType)
        assert isinstance(r.params["lines"], tuple)
        with pytest.raises(TypeError):
            r.params["n"] = 3  # type: ignore[index]

    def test_point_run_has_no_space(self):
        """U7: the point run takes no space; its form has null."""
        r = make_request(diagnostic="point_run", space=None, params={"repeats": 10, "seed": 0, "x": {"a": 1.0}})
        assert r.canonical()["space"] is None

    def test_rebuilds_from_its_canonical_form(self):
        r = make_request()
        assert Request(**r.canonical()) == r

    def test_malformed_space_refused(self):
        with pytest.raises(RequestError):
            make_request(space={"a": [1.0]})

    @pytest.mark.parametrize("value", [math.nan, np.int64(3), np.array([1.0])])
    def test_not_strict_json_refused(self, value):
        """Record 0070, item 9; numpy's numbers aren't JSON data (ValueError, not TypeError: review round 1)."""
        with pytest.raises(ValueError):
            make_request(params={"x": value})

    @pytest.mark.parametrize(
        "kw",
        [
            {"params": {"n": 200, "seed": 1.0, "lines": [{"anchor": {"a": 1.0}}]}},  # seed 1.0 isn't 1 (§3.4)
            {"space": {"b": [-0.0, 1], "a": {"range": [1e-2, 1e2], "scale": "log"}, "h": 3}},  # -0.0 isn't 0.0
        ],
    )
    def test_equal_exactly_when_canonical_json_is(self, kw):
        """Review round 1: equality agrees with the request's identity (its canonical JSON, §3.4)."""
        r, other = make_request(), make_request(**kw)
        assert canonical_json(r.canonical()) != canonical_json(other.canonical())
        assert r != other
        assert make_request() == r and hash(make_request()) == hash(r)


class TestTestRunRequest:
    def test_canonical(self):
        """§3.4: {"test_run": {"point": [...]}}."""
        t = TestRunRequest(point=(45, 1e4))
        assert t.point == (45.0, 1e4)
        assert canonical_json(t.canonical()) == '{"test_run":{"point":[45.0,10000.0]}}'

    def test_non_finite_refused(self):
        with pytest.raises(ValueError):
            TestRunRequest(point=(math.inf,))

    def test_not_collected_by_pytest(self):
        assert TestRunRequest.__test__ is False


def price():
    return Price.make(new=1, reused=0, time_s=None, from_runs=0)


class TestQuestions:
    def test_approval_request(self):
        q = ApprovalRequest(
            asked_for="test_run",
            model_version="heat@b204a1c3d5e6",
            price=price(),
            first_for_version=True,
            command=("./heat_solver", "plate.in"),
            program="/models/heat/heat_solver",
            templates={"plate.in.template": "k = $k\n"},
            files=("solver.cfg",),
            function=None,
            env={"OMP_NUM_THREADS": "1"},
            pass_env={"LICENSE_SERVER": True},
            text="Run heat@b204a1c3d5e6?\nPrice: 1 new run, 0 reused, time unknown",
        )
        assert str(q) == q.text
        assert isinstance(q.templates, MappingProxyType) and isinstance(q.env, MappingProxyType)
        assert isinstance(q.pass_env, MappingProxyType)

    def test_approval_request_refuses_another_purpose(self):
        with pytest.raises(ValueError):
            ApprovalRequest(
                asked_for="export",  # type: ignore[arg-type]
                model_version="m@0",
                price=price(),
                first_for_version=False,
                command=None,
                program=None,
                templates={},
                files=(),
                function="beam.py:f",
                env={},
                pass_env={},
                text="t",
            )

    def test_confirmation_request(self):
        q = ConfirmationRequest(spec_path="/p/beam/model.json", replaces=None, spec_text="{}", text="Save it?")
        assert str(q) == "Save it?"


class TestProgress:
    def test_runs_line(self):
        """U2: "40/96 runs"."""
        p = Progress.of_runs(40, 96)
        assert (p.phase, p.done, p.total, p.text, str(p)) == ("runs", 40, 96, "40/96 runs", "40/96 runs")

    def test_analysis(self):
        p = Progress(phase="analysis", done=230, total=1000, text="bootstrap: 230 of 1000 refits, about 6 min left")
        assert str(p) == p.text

    @pytest.mark.parametrize(("phase", "done", "total"), [("runs", 5, 4), ("runs", -1, 4), ("other", 0, 1)])
    def test_refusals(self, phase, done, total):
        with pytest.raises(ValueError):
            Progress(phase=phase, done=done, total=total, text="x")
