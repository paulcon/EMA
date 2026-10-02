"""The workspace contract (contracts.md C53; architecture.md §9): each use case U1-U8 runs as written and meets its
"Done when", on the reference models; the get-started guide's Python blocks run as written on R2 (0060).

``check_use_case`` is parametrized over the use cases, and ``check_get_started`` runs the guide; both are slow tier.
U9 is the MCP server's (step 15, ``tests/contracts/tools.py``); C54 joins with the CLI (step 16). A use case needs
the diagnostics it names: until a diagnostic is registered (scatter, coordinate lines, the linear and polynomial
models are built on parallel branches), the use case runs up to the first step that needs it and is skipped there,
naming it (record 0080). The negative control: a workspace that runs before showing the price fails every use case
that makes a new run (``RunsBeforeAsking``); its meta-test runs U7, whose point run exists now.
"""

import contextlib
import dataclasses
import io
import os
import re
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import ema
import ema.reference_models
from ema.store import Store
from ema.workspace import Workspace, open_workspace
from tests.support.workspace import PI_SPACE, Asked, RunsBeforeAsking, copy_reference, registered

GUIDE = Path(__file__).resolve().parents[2] / "docs" / "guides" / "get_started.md"
R2 = ema.reference_models.path("R2")

Opener = Callable[[Path], Workspace]


def need(*diagnostics: str) -> None:
    """Skip the rest of a use case when a diagnostic it names isn't registered yet (record 0080)."""
    missing = [d for d in diagnostics if not registered(d)]
    if missing:
        pytest.skip(f"needs {', '.join(missing)}, built on another branch; runs once it is merged")


def runs_in(w: Workspace) -> int:
    return len(os.listdir(os.path.join(w.path, "runs")))


def u1(opener: Opener, tmp: Path) -> None:
    """U1 on R2: two questions (1 new, time unknown; then 200 new with a time), 200 new in the header, a figure per
    model parameter, and the same steps again asking nothing, with a byte-identical report (P3, P4)."""
    ws = opener(tmp / "beam_study")
    ws.load_model(R2)
    ws.describe_model("ishigami")
    asked = Asked()
    ws.test_model("ishigami", approve=asked)
    need("scatter")
    result = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    report = ws.report(result)
    assert asked.prices[0] == "1 new run, 0 reused, time unknown", asked.prices
    assert asked.prices[1].startswith("200 new runs, 0 reused, about ") and len(asked.prices) == 2
    assert (result.counts.new, result.counts.reused, sum(result.counts.failed.values())) == (200, 0, 0)
    assert len([f for f in result.figures if any(p in f.name for p in ("x1", "x2", "x3"))]) >= 3
    before = runs_in(ws)
    again = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    assert len(asked.prices) == 2 and runs_in(ws) == before and again == result
    assert ws.report(again).markdown == report.markdown


def u2(opener: Opener, tmp: Path) -> None:
    """U2 on R8 (a command-line program): the first approval shows what runs; an interrupted evaluation keeps its k
    runs; the rerun prices the rest as new and k + 1 as reused, and runs exactly those; again asks nothing."""
    ws = opener(tmp / "heat_study")
    spec = copy_reference("R8", tmp / "models")
    ws.load_model(spec)
    asked = Asked()
    ws.test_model("r8", approve=asked)
    first = asked.questions[0]
    assert first.first_for_version and "Command:" in first.text and "Input deck" in first.text
    need("coordinate_lines")
    space = ema.reference_models.space("R8")
    price = ws.price("r8", "coordinate_lines", space, n=17)
    k = 5

    def stop(progress: ema.Progress) -> None:
        if progress.phase == "runs" and progress.done == k:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        ws.run("r8", "coordinate_lines", space, n=17, approve=asked, on_progress=stop)
    assert not asked.questions[-1].first_for_version
    asked = Asked()
    result = ws.run("r8", "coordinate_lines", space, n=17, approve=asked)
    assert asked.prices[0].startswith(f"{price.new - k} new runs, {price.reused + k} reused")
    assert result.counts.new == price.new - k
    again = Asked()
    ws.run("r8", "coordinate_lines", space, n=17, approve=again)
    assert again.questions == []


def u3(opener: Opener, tmp: Path) -> None:
    """U3 on R5: exactly the known region fails, with reasons; the polynomial model with too few usable runs gives no
    estimates; a larger design reuses the failed runs and says so; retry_failed runs exactly the failed points."""
    ws = opener(tmp / "heat_study")
    ws.load_model(ema.reference_models.path("R5"))
    need("scatter")
    wide = {"a": (-1.0, 1.0), "b": (-1.0, 1.0)}
    asked = Asked()
    r1 = ws.run("r5", "scatter", wide, prediction="y", n=200, seed=2, approve=asked)
    failed = ws.failed_runs(r1)
    assert failed and all(i.point["a"] + i.point["b"] > 1 or (i.point["a"] < -0.8 and i.point["b"] < -0.8)
                          for i in failed)  # fmt: skip
    k = len(failed)
    assert sum(r1.counts.failed.values()) == k and "not_usable" in [n.code for n in r1.notes]
    r3 = ws.run("r5", "scatter", wide, prediction="y", n=300, seed=2, approve=asked)
    assert asked.prices[-1].startswith(f"100 new runs, 200 reused, of which {k} failed")
    assert "reused_failed" in [n.code for n in r3.notes]
    retry = sum(r3.counts.failed.values())
    ws.run("r5", "scatter", wide, prediction="y", n=300, seed=2, retry_failed=True, approve=asked)
    assert asked.prices[-1].startswith(f"{retry} new run")
    need("polynomial_model")
    r2 = ws.run("r5", "polynomial_model", wide, prediction="y", degree=3, level=0, approve=asked)
    if r2.counts.usable < 20:
        assert r2.estimates == ()


def u4(opener: Opener, tmp: Path) -> None:
    """U4 on R2: nested convergent designs reuse the smaller ones' runs; a declined run makes none; the same steps
    again give identical results (P4)."""
    ws = opener(tmp / "lens_study")
    ws.load_model(R2)
    need("linear_model", "polynomial_model")
    asked = Asked()
    r1 = ws.run("ishigami", "linear_model", PI_SPACE, level=2, seed=3, approve=asked)
    r2 = ws.run("ishigami", "polynomial_model", PI_SPACE, degree=2, level=2, seed=3, approve=asked)
    assert r2.counts.reused >= 1
    before = runs_in(ws)
    with pytest.raises(ema.ApprovalDeclined):
        ws.run("ishigami", "polynomial_model", PI_SPACE, degree=3, level=2, seed=3, approve=Asked(answer=False))
    assert runs_in(ws) == before
    r3 = ws.run("ishigami", "polynomial_model", PI_SPACE, degree=3, level=1, seed=3, approve=asked)
    for r, kw in ((r1, {"level": 2}), (r2, {"degree": 2, "level": 2}), (r3, {"degree": 3, "level": 1})):
        name = r.diagnostic
        assert ws.run("ishigami", name, PI_SPACE, seed=3, approve=None, **kw) == r


def u5(opener: Opener, tmp: Path) -> None:
    """U5 on R2 after U1: the polynomial model reuses scatter's 200 points; the repeat asks nothing; the export
    holds exactly its runs, read back bit for bit (E1-E6)."""
    ws = opener(tmp / "beam_study")
    ws.load_model(R2)
    need("scatter", "polynomial_model")
    asked = Asked()
    ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    r2 = ws.run("ishigami", "polynomial_model", PI_SPACE, degree=2, level=4, seed=1, approve=asked)
    assert asked.prices[-1].startswith("120 new runs, 200 reused")
    r3 = ws.run("ishigami", "polynomial_model", PI_SPACE, degree=2, level=4, seed=1, approve=asked)
    assert r3 == r2 and len(asked.prices) == 2
    out = Path(ws.export(r2.result_id, tmp / "beam_runs"))
    rows = (out / "runs.csv").read_text().splitlines()
    assert len(rows) == 1 + 320 and sum(",true," in r for r in rows) == 120


def u6(opener: Opener, tmp: Path) -> None:
    """U6 on a copy of R2: a changed file is refused, naming it; loading again makes a new model version with no
    stored runs; the old report is unchanged; listing results shows both (P3, P5)."""
    ws = opener(tmp / "beam_study")
    spec = copy_reference("R2", tmp / "models")
    ws.load_model(spec)
    need("scatter")
    asked = Asked()
    old = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    old_report = ws.report(old).markdown
    function = spec.parent / "ishigami.py"
    function.write_text(function.read_text() + "\n# fixed\n")
    with pytest.raises(ema.ModelChanged, match="ishigami.py"):
        ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    loading = ws.load_model(spec)
    assert loading.new_version and loading.changed_files == ("ishigami.py changed",)
    new = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=asked)
    assert asked.prices[-1] == "200 new runs, 0 reused, time unknown"
    assert ws.report(old).markdown == old_report and old.model_version_id != new.model_version_id
    assert {r.result_id for r in ws.list_results(model="ishigami")} == {old.result_id, new.result_id}


def u7(opener: Opener, tmp: Path) -> None:
    """U7 on R6a (noisy, declared deterministic): the point run's 10 repeats, replicate 0 reused from the test run;
    the measured variation recorded; a later result carries the note; a repeat makes no run; R2 measures none."""
    ws = opener(tmp / "heat_study")
    ws.load_model(ema.reference_models.path("R6a"))
    asked = Asked(runs_dir=Path(ws.path) / "runs")
    ws.test_model("r6a", approve=asked)
    p = ws.run("r6a", "point_run", repeats=10, approve=asked)
    assert asked.prices[-1].startswith("10 new runs, 1 reused"), asked.prices
    assert asked.stored_when_asked == [0, 1], "a run was made before its question (P3)"
    assert p.measured_noisy is not None and "Standard deviation" in ws.report(p).markdown
    before = runs_in(ws)
    assert ws.run("r6a", "point_run", repeats=10, approve=None) == p and runs_in(ws) == before
    ws.load_model(R2)
    assert ws.run("ishigami", "point_run", repeats=3, approve=asked).measured_noisy is None
    need("scatter")
    space = {"a": (0.0, 2.0), "b": (-1.0, 1.0)}
    r = ws.run("r6a", "scatter", space, n=200, seed=4, approve=asked)
    assert "measured_noisy" in [n.code for n in r.notes]


def u8(opener: Opener, tmp: Path) -> None:
    """U8 on R2: in a copy of the workspace, reproducing is identical with a byte-identical report and no run; a
    deleted result replays identical from its provenance; a changed library version is named."""
    ws = opener(tmp / "beam_study")
    ws.load_model(R2)
    need("scatter")
    result = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=Asked())
    report = ws.report(result).markdown
    ws.close()
    shutil.copytree(tmp / "beam_study", tmp / "copy_of_beam_study")
    copy = opener(tmp / "copy_of_beam_study")
    before = runs_in(copy)
    copy.list_results()
    check = copy.reproduce(result.result_id[:4])
    assert check.identical is True and str(check).endswith(
        "identical (estimates, intervals, notes, figures' data cards)."
    )
    assert copy.report(result.result_id).markdown == report and runs_in(copy) == before
    provenance = copy.get_result(result.result_id).provenance
    copy._store.delete_result(result.result_id)
    assert copy.reproduce(provenance).result.to_json() == result.to_json()
    other = dataclasses.replace(result, provenance=dataclasses.replace(provenance, scipy="0.0.1"))
    assert [d.split(":")[0] for d in copy.reproduce(other).provenance_differences] == ["scipy"]


USE_CASES = {"U1": u1, "U2": u2, "U3": u3, "U4": u4, "U5": u5, "U6": u6, "U7": u7, "U8": u8}


def opened(path: Path) -> Workspace:
    return open_workspace(path)


@pytest.mark.slow
@pytest.mark.parametrize("use_case", list(USE_CASES))
def check_use_case(use_case: str, tmp_path: Path) -> None:
    """C53: the use case runs as written and meets its "Done when"."""
    opened_now: list[Workspace] = []

    def opener(path: Path) -> Workspace:
        w = opened(path)
        opened_now.append(w)
        return w

    try:
        USE_CASES[use_case](opener, tmp_path)
    finally:
        for w in opened_now:
            with contextlib.suppress(Exception):
                w.close()


def _python_blocks(text: str) -> list[str]:
    return re.findall(r"^ *```python\n(.*?)^ *```", text, flags=re.DOTALL | re.MULTILINE)


@pytest.mark.slow
def check_get_started(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """C53, 0060: the get-started guide's Python blocks run as written on R2, answering y to each question."""
    blocks = [re.sub(r"^ {3}", "", b, flags=re.MULTILINE) for b in _python_blocks(GUIDE.read_text())]
    assert len(blocks) >= 6
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("y\n" * 20))
    namespace: dict[str, object] = {}
    try:
        for block in blocks:
            for name in re.findall(r'ws\.(?:run|price)\("ishigami", "(\w+)"', block):
                need(name)
            exec(compile(block, str(GUIDE), "exec"), namespace)  # noqa: S102  (the guide, as written)
    finally:
        ws = namespace.get("ws")
        if isinstance(ws, Workspace):
            ws.close()
    out = capsys.readouterr().out
    assert "Loaded ishigami@" in out


def test_a_workspace_that_runs_before_asking_fails_the_use_cases(tmp_path: Path) -> None:
    """C53's negative control: a workspace that makes its runs before showing the price fails U7 (meta-test)."""
    broken: list[Workspace] = []

    def opener(path: Path) -> Workspace:
        w = RunsBeforeAsking(Store.open(path))
        broken.append(w)
        return w

    try:
        with pytest.raises(AssertionError):
            u7(opener, tmp_path)
    finally:
        for w in broken:
            w.close()
