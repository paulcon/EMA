"""What the workspace returns about models, diagnostics, reports, and runs (architecture.md §3, summaries.py).

Each prints as its text (EMA's rendering, P1; AR3); mappings are read-only (record 0070).
"""

from types import MappingProxyType

import pytest

from ema.types.model import Limits, ModelParameter, ModelSpec, PredictionSpec, PythonFunction
from ema.types.runs import FailureKind, RunStatus
from ema.types.summaries import (
    DiagnosticParameterInfo,
    DiagnosticSummary,
    LoadingSummary,
    ModelDescription,
    ModelSummary,
    Proposal,
    Report,
    RunInfo,
)


def spec():
    return ModelSpec(
        name="beam",
        description="a cantilever beam",
        interface=PythonFunction(function="beam.py:f"),
        parameters=(
            ModelParameter(
                name="E", units="Pa", description="modulus", nominal=200e9, limits=Limits(lower=0, lower_strict=True)
            ),
        ),
        predictions=(PredictionSpec(name="d", units="m", description="tip deflection"),),
    )


def model_summary():
    return ModelSummary(
        name="beam",
        model_version="beam@91c0aaaaaaaa",
        parameters=["E"],
        predictions=["d"],
        spec_path="/p/beam/model.json",
        text="beam@91c0aaaaaaaa: 1 model parameter, 1 model prediction",
    )


def test_model_summary_and_description():
    m = model_summary()
    assert m.parameters == ("E",) and str(m) == m.text
    d = ModelDescription(model=m, spec=spec(), text="E [Pa]: nominal 2e+11")
    assert str(d) == d.text and d.spec.name == "beam"


def test_proposal():
    p = Proposal(spec=spec(), path="/p/beam/model.json", spec_text="{}\n", missing_files=["beam.py"], text="t")
    assert p.missing_files == ("beam.py",) and str(p) == "t"


def test_report_prints_as_its_markdown():
    r = Report(result_id="12" * 32, markdown="# Scatter: beam, d\n", path="/w/results/x/report.md", pdf=None)
    assert str(r) == "# Scatter: beam, d\n"


def test_loading_summary():
    s = LoadingSummary(
        model=model_summary(),
        new_version=True,
        replaced="was beam@3f2a00000000",
        changed_files=["beam.py changed"],
        warnings=[],
        text="New model version beam@91c0aaaaaaaa (was beam@3f2a00000000): beam.py changed",
    )
    assert s.changed_files == ("beam.py changed",) and str(s) == s.text


def test_diagnostic_summary():
    info = DiagnosticParameterInfo(
        name="n",
        type="integer ≥ 1",
        default=None,
        default_text="required",
        meaning="the number of points",
        changes_design="yes",
        json_schema={"type": "integer", "minimum": 1},
    )
    assert isinstance(info.json_schema, MappingProxyType)
    s = DiagnosticSummary(name="scatter", summary="s", takes_space=True, parameters=[info], text="scatter: s")
    assert s.parameters == (info,) and str(s) == "scatter: s"


class TestRunInfo:
    def make(self, **kw):
        fields = {
            "run_id": "cd" * 32,
            "short_id": "cdcd",
            "row": 3,
            "point": {"E": 2e11},
            "replicate": 0,
            "status": RunStatus.FAILED,
            "kind": FailureKind.TIMEOUT,
            "reason": "timeout after 600 s",
            "stderr_tail": "line 1\nline 2",
            "predictions": {},
            "run_dir": None,
            "batch_dir": None,
            "text": "Run cdcd: failed (timeout): timeout after 600 s",
        }
        fields.update(kw)
        return RunInfo(**fields)

    def test_read_only_and_prints_its_text(self):
        info = self.make()
        assert isinstance(info.point, MappingProxyType) and isinstance(info.predictions, MappingProxyType)
        assert str(info) == info.text

    def test_kind_exactly_when_failed(self):
        with pytest.raises(ValueError):
            self.make(status=RunStatus.OK)
        with pytest.raises(ValueError):
            self.make(kind=None)
