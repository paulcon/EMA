"""The workspace end to end on millisecond models: architecture.md §7's order, and the use cases' "Done when" items
that need no diagnostic but the point run and the contract's toy (step 14; record 0080).

The toy stands in for scatter (``tests.support.workspace``); the use cases as written, with the real diagnostics,
are ``tests/contracts/workspace.py``'s (slow tier, C53).
"""

import dataclasses
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

import ema
import ema.reference_models
from ema.store import Store
from ema.types.errors import (
    ApprovalDeclined,
    CannotAsk,
    DesignTooLarge,
    EMAError,
    ModelChanged,
    NotFound,
    RequestError,
    WorkspaceBusy,
)
from ema.types.identity import hex_ids
from ema.types.requests import ApprovalRequest
from ema.types.runs import FailureKind, RunStatus
from ema.workspace import Workspace, open_workspace
from tests.support.models import copy_model
from tests.support.workspace import PI_SPACE, Asked, toy_registered

R2 = ema.reference_models.path("R2")
R5_SPACE = {"a": (-1.0, 1.0), "b": (-1.0, 1.0)}


@pytest.fixture
def toy():
    with toy_registered() as t:
        yield t


@pytest.fixture
def ws(tmp_path):
    with open_workspace(tmp_path / "ws") as w:
        yield w


def runs_stored(w: Workspace) -> int:
    return len(os.listdir(os.path.join(w.path, "runs")))


# -- opening (§7; data_model.md §1) ----------------------------------------------------------------------------


def test_open_workspace_creates_it_and_the_root_reexports_are_lazy(tmp_path):
    """open_workspace creates the workspace; ``ema.open_workspace`` and the result types come from the root (AR7)."""
    with ema.open_workspace(tmp_path / "w") as w:
        assert w.path == str((tmp_path / "w").resolve()) or w.path == os.path.abspath(tmp_path / "w")
        assert os.path.isfile(os.path.join(w.path, "ema.db"))
    assert ema.Workspace is Workspace and ema.DiagnosticResult.__name__ == "DiagnosticResult"
    code = "import ema.types, sys; assert 'ema.workspace' not in sys.modules and 'matplotlib' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True)


# -- models (W1, U6, 0054) --------------------------------------------------------------------------------------


def test_load_model_says_what_it_made(ws, tmp_path):
    """Loading asks nothing and runs nothing; a repeated loading says nothing changed (W1; get-started step 3)."""
    first = ws.load_model(R2)
    assert str(first).startswith("Loaded ishigami@")
    assert "3 model parameters (x1, x2, x3), 1 model prediction (y)" in first.text
    assert first.new_version and first.replaced is None
    again = ws.load_model(R2)
    assert not again.new_version and "Already loaded" in again.text
    assert [m.name for m in ws.list_models()] == ["ishigami"]
    description = ws.describe_model("ishigami")
    assert "x1: nominal 0.0" in description.text and "Model predictions:" in description.text
    with pytest.raises(NotFound, match="ishigami"):
        ws.describe_model("beam")


def test_a_changed_file_is_refused_until_loaded_again(ws, tmp_path, toy):
    """U6: a run whose file changed since loading is refused, naming the file; loading again makes a new model
    version, which has no stored runs (time unknown) and reuses none; the old result is unchanged (P3, P5; M16)."""
    spec = copy_model("python", tmp_path / "toy")
    ws.load_model(spec)
    asked = Asked()
    space = {"a": (0.0, 2.0), "b": (-1.0, 1.0)}
    old = ws.run("toy", "toy", space, prediction="y", n=12, seed=1, approve=asked)
    old_report = ws.report(old).markdown
    (spec.parent / "helper.py").write_text((spec.parent / "helper.py").read_text() + "\n# edited\n")
    with pytest.raises(ModelChanged, match="helper.py"):
        ws.run("toy", "toy", space, prediction="y", n=12, seed=1, approve=asked)
    assert len(asked.questions) == 1
    loading = ws.load_model(spec)
    assert loading.new_version and loading.changed_files == ("helper.py changed",)
    assert "New model version" in loading.text and "was toy@" in loading.text
    new = ws.run("toy", "toy", space, prediction="y", n=12, seed=1, approve=asked)
    assert asked.prices[-1] == "12 new runs, 0 reused, time unknown"
    assert new.model_version_id != old.model_version_id and new.counts.reused == 0
    assert ws.report(old).markdown == old_report
    listed = ws.list_results(model="toy")
    assert {r.result_id for r in listed} == {old.result_id, new.result_id}
    assert len({r.model_version for r in listed}) == 2


def test_a_change_during_the_runs_keeps_the_runs_made(ws, tmp_path, toy):
    """U6: a change between an approval and its runs is refused at the next call, and the runs before it are kept."""
    spec = copy_model("python", tmp_path / "toy")
    ws.load_model(spec)
    helper = spec.parent / "helper.py"

    def edit(progress):
        if progress.phase == "runs" and progress.done == 3:
            helper.write_text(helper.read_text() + "\n# edited\n")

    with pytest.raises(ModelChanged, match="helper.py"):
        ws.run("toy", "toy", {"a": (0.0, 2.0)}, prediction="y", n=10, seed=1, approve=Asked(), on_progress=edit)
    assert runs_stored(ws) == 3
    assert ws.list_results() == []


# -- the test run (0049) ---------------------------------------------------------------------------------------


def test_test_model_asks_once_then_reuses(ws):
    """The test run: priced and approved like any new run (1 new, 0 reused, time unknown); stored: no question."""
    ws.load_model(R2)
    with pytest.raises(CannotAsk):
        ws.test_model("ishigami", approve=None)
    asked = Asked(answer=False)
    with pytest.raises(ApprovalDeclined, match="declined: no runs made"):
        ws.test_model("ishigami", approve=asked)
    assert runs_stored(ws) == 0
    asked = Asked()
    info = ws.test_model("ishigami", approve=asked)
    assert asked.prices == ["1 new run, 0 reused, time unknown"]
    assert isinstance(asked.questions[0], ApprovalRequest) and asked.questions[0].first_for_version
    assert info.status is RunStatus.OK and info.predictions == {"y": 0.0}
    assert str(info).startswith(f"Run {info.short_id}: ok; y = 0; at x1 = 0, x2 = 0, x3 = 0")
    assert ws.test_model("ishigami", approve=None).run_id == info.run_id
    assert ws.run_dirs(info.short_id)[0].run_dir == os.path.join(ws.path, "runs", info.run_id)


# -- one diagnostic evaluation (§7; P3, C50) -------------------------------------------------------------------


def test_the_first_look_asks_twice_and_repeats_ask_nothing(ws, toy):
    """U1's "Done when" with the toy in scatter's place: two questions with their prices, the header's counts, and
    a repeated request that asks nothing, runs nothing, and returns the same result and report (P3, P4; C50)."""
    ws.load_model(R2)
    asked = Asked()
    ws.test_model("ishigami", approve=asked)
    assert str(ws.price("ishigami", "toy", PI_SPACE, n=40, seed=1)).startswith("40 new runs, 0 reused, about ")
    result = ws.run("ishigami", "toy", PI_SPACE, n=40, seed=1, approve=asked)
    assert asked.prices[0] == "1 new run, 0 reused, time unknown"
    assert asked.prices[1].startswith("40 new runs, 0 reused, about ") and "(from 1 stored run)" in asked.prices[1]
    assert not asked.questions[1].first_for_version
    assert (result.counts.new, result.counts.reused, result.counts.runs) == (40, 0, 40)
    assert str(result) == (f"Diagnostic result {result.shown.short_id}: toy on {result.shown.model_version}, y; 40 "
                           f"runs: 40 new, 0 reused, 0 failed; report: ema report {result.shown.short_id}")  # fmt: skip
    report = ws.report(result)
    assert report.path == os.path.join(ws.path, "results", result.result_id, "report.md")
    assert "| Runs | 40: 40 new, 0 reused; 0 failed; 0 missing y; 40 usable |" in report.markdown
    before = runs_stored(ws)
    again = ws.run("ishigami", "toy", PI_SPACE, n=40, seed=1, approve=None)
    assert again == result and again.result_id == result.result_id and len(asked.questions) == 2
    assert runs_stored(ws) == before and ws.report(again).markdown == report.markdown
    short = result.shown.short_id  # the repeat says it is the stored result, then its counts as made (0081 item 28)
    assert str(again) == (f"Diagnostic result {short}: the stored result of the same request; no new runs, nothing "
                          f"asked. As made: toy on {result.shown.model_version}, y; 40 runs: 40 new, 0 reused, 0 "
                          f"failed; report: ema report {short}")  # fmt: skip
    assert str(ws.get_result(short)) == str(result)  # reading a result back is not a repeat
    assert ws.get_result(result.shown.short_id) == result
    with pytest.raises(NotFound):
        ws.get_result("ffffffff")


def test_new_runs_are_refused_before_any_question(ws, toy):
    """approve=None with new runs: CannotAsk, nothing asked or recorded; a no: ApprovalDeclined, no runs (P3; U4)."""
    ws.load_model(R2)
    with pytest.raises(CannotAsk):
        ws.run("ishigami", "toy", PI_SPACE, n=10, approve=None)
    store = ws._store
    assert store.approvals() == ()
    with pytest.raises(ApprovalDeclined, match="declined: no runs made"):
        ws.run("ishigami", "toy", PI_SPACE, n=10, approve=Asked(answer=False))
    assert [a.answer for a in store.approvals()] == [False] and runs_stored(ws) == 0


def test_the_request_is_checked_before_anything_is_asked(ws, toy):
    """The point run takes no space; any other diagnostic needs one (U7); the cap is refused (G5); unknown names."""
    ws.load_model(R2)
    asked = Asked()
    with pytest.raises(RequestError, match="toy needs a model parameter space"):
        ws.run("ishigami", "toy", approve=asked)
    with pytest.raises(RequestError, match="point run takes no model parameter space"):
        ws.run("ishigami", "point_run", PI_SPACE, approve=asked)
    with pytest.raises(DesignTooLarge):
        ws.run("ishigami", "toy", PI_SPACE, n=10_000_001, approve=asked)
    with pytest.raises(RequestError, match="no diagnostic parameter m"):
        ws.price("ishigami", "toy", PI_SPACE, m=3)
    with pytest.raises(NotFound, match="no diagnostic 'nope'"):
        ws.describe_diagnostic("nope")
    assert asked.questions == []
    assert {"point_run", "toy"} <= {d.name for d in ws.list_diagnostics()}


def test_the_run_lock_refuses_a_second_maker_of_runs(ws, toy):
    """One process makes runs at a time (data_model.md §10): a held lock is WorkspaceBusy; prices need no lock."""
    ws.load_model(R2)
    other = Store.open(ws.path)
    try:
        with other.run_lock():
            assert ws.price("ishigami", "toy", PI_SPACE, n=5).new == 5
            with pytest.raises(WorkspaceBusy):
                ws.run("ishigami", "toy", PI_SPACE, n=5, approve=Asked())
    finally:
        other.close()
    assert runs_stored(ws) == 0


def test_a_workspace_is_bound_to_its_thread(ws, toy):
    """Review round 1, m4 and n2: a workspace used from another thread is refused with EMA's error, not SQLite's;
    the run lock held by another workspace of this process says so."""
    ws.load_model(R2)
    with ThreadPoolExecutor(1) as pool, pytest.raises(EMAError, match="opened on another thread"):
        pool.submit(ws.list_results).result()
    assert ws.list_results() == []
    with (
        open_workspace(ws.path) as other,
        other._store.run_lock(),
        pytest.raises(WorkspaceBusy, match="another workspace of this process"),
    ):
        ws.run("ishigami", "toy", PI_SPACE, n=5, approve=Asked())


def test_list_results_by_label_honors_the_name(ws, toy):
    """Review round 1, n4 (Q8): a model version's label names its model; another name is NotFound."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=5, seed=1, approve=Asked())
    label = result.shown.model_version
    assert [r.result_id for r in ws.list_results(model_version=label)] == [result.result_id]
    prefix = label.split("@")[1]
    assert [r.result_id for r in ws.list_results(model_version=prefix[:6])] == [result.result_id]
    with pytest.raises(NotFound, match="a version of 'ishigami'"):
        ws.list_results(model_version=f"beam@{prefix}")


def test_an_interrupted_evaluation_keeps_its_runs_and_a_rerun_matches(tmp_path, toy):
    """C49: Ctrl-C keeps every finished run and stores no result; the rerun asks for the rest, its counts and
    approval are its own, and its estimates and observations equal an uninterrupted evaluation's."""

    def stop(progress):
        if progress.phase == "runs" and progress.done == 4:
            raise KeyboardInterrupt

    with open_workspace(tmp_path / "a") as a, open_workspace(tmp_path / "b") as b:
        for w in (a, b):
            w.load_model(R2)
        with pytest.raises(KeyboardInterrupt):
            a.run("ishigami", "toy", PI_SPACE, n=20, seed=2, approve=Asked(), on_progress=stop)
        assert runs_stored(a) == 4 and a.list_results() == []
        asked = Asked()
        rerun = a.run("ishigami", "toy", PI_SPACE, n=20, seed=2, approve=asked)
        assert asked.prices[0].startswith("16 new runs, 4 reused")
        assert (rerun.counts.new, rerun.counts.reused) == (16, 4)
        whole = b.run("ishigami", "toy", PI_SPACE, n=20, seed=2, approve=Asked())
        on = json.loads(rerun.to_json()), json.loads(whole.to_json())
        for key in ("estimates", "observations", "figures"):
            assert on[0][key] == on[1][key]
        cards = [
            {f.card: (Path(w.path) / "results" / r.result_id / f.card).read_bytes() for f in r.figures}
            for w, r in ((a, rerun), (b, whole))
        ]
        assert cards[0] and cards[0] == cards[1]  # the figures' values (review round 1, m5)


def _without(value, key):
    """A JSON value with every entry named ``key`` left out, at any depth."""
    if isinstance(value, dict):
        return {k: _without(v, key) for k, v in value.items() if k != key}
    if isinstance(value, list):
        return [_without(v, key) for v in value]
    return value


def test_a_seed_or_model_version_change_differs_in_that_field_and_what_it_decides(tmp_path, toy):
    """C51 end to end (review round 1, m5): rerunning with another seed gives a provenance differing in the seed
    (in the request and the design), the runs used, and their approval, and in nothing else; with another model
    version, in the model version (its own and the design's), the runs used, and their approval."""
    spec = copy_model("python", tmp_path / "toy")
    space = {"a": (0.0, 2.0), "b": (-1.0, 1.0)}
    with open_workspace(tmp_path / "ws") as w:
        w.load_model(spec)
        first = w.run("toy", "toy", space, prediction="y", n=6, seed=1, approve=Asked()).provenance.canonical()
        seeded = w.run("toy", "toy", space, prediction="y", n=6, seed=2, approve=Asked()).provenance.canonical()
        assert {k for k in first if first[k] != seeded[k]} == {"request", "design", "run_ids", "approval_id"}
        for k in ("request", "design"):
            assert first[k] != seeded[k] and _without(first[k], "seed") == _without(seeded[k], "seed")
        (spec.parent / "helper.py").write_text((spec.parent / "helper.py").read_text() + "\n# edited\n")
        w.load_model(spec)
        versioned = w.run("toy", "toy", space, prediction="y", n=6, seed=1, approve=Asked()).provenance.canonical()
        assert {k for k in first if first[k] != versioned[k]} == {"model_version_id", "design", "run_ids",
                                                                   "approval_id"}  # fmt: skip
        mv = "model_version_id"
        assert _without(first["design"], mv) == _without(versioned["design"], mv)


# -- failures (U3; C47) ----------------------------------------------------------------------------------------


def test_failed_runs_are_listed_reused_and_retried(ws, toy):
    """U3 on R5 with the toy: each failed run with its kind and reason; a later design reuses the failed runs and its
    price says so; with retry_failed exactly the failed points run again, beside the runs they replace (C47)."""
    ws.load_model(ema.reference_models.path("R5"))
    first = ws.run("r5", "toy", R5_SPACE, prediction="y", n=24, seed=2, approve=Asked())
    failed = ws.failed_runs(first)
    assert failed and len(failed) == sum(first.counts.failed.values())
    for info in failed:
        a, b = info.point["a"], info.point["b"]
        assert info.status is RunStatus.FAILED
        if info.kind is FailureKind.ERROR:
            assert a + b > 1 and "no convergence" in info.reason and "stderr" in info.text
        else:
            assert info.kind is FailureKind.TIMEOUT and a < -0.8 and b < -0.8
    missing_z = ws.failed_runs(ws.run("r5", "toy", R5_SPACE, prediction="z", n=24, seed=2, approve=None))
    assert len(missing_z) > len(failed)
    assert all(i.point["b"] > 0.8 for i in missing_z if i.status is RunStatus.OK)
    asked = Asked()
    bigger = ws.run("r5", "toy", R5_SPACE, prediction="y", n=30, seed=2, approve=asked)
    k = len(failed)
    assert f"6 new runs, 24 reused, of which {k} failed" in asked.prices[0]
    assert "reused_failed" in [n.code for n in bigger.notes]
    asked = Asked()
    ws.run("r5", "toy", R5_SPACE, prediction="y", n=30, seed=2, retry_failed=True, approve=asked)
    retried = sum(bigger.counts.failed.values())
    assert asked.prices[0].startswith(f"{retried} new run")


# -- the point run and measured noise (U7; C52, PT4) -----------------------------------------------------------


def test_a_noisy_model_is_measured_and_noted_and_earlier_results_unchanged(ws, toy):
    """U7 on R6a: the point run reuses the test run as replicate 0; it records the model version as measured noisy,
    and a later result carries the note, while an earlier result is unchanged (P7; C52)."""
    ws.load_model(ema.reference_models.path("R6a"))
    space = {"a": (0.0, 2.0), "b": (-1.0, 1.0)}
    ws.test_model("r6a", approve=Asked())
    earlier = ws.run("r6a", "toy", space, n=10, seed=4, approve=Asked())
    asked = Asked()
    point = ws.run("r6a", "point_run", repeats=4, approve=asked)
    assert asked.prices[0].startswith("4 new runs, 1 reused")
    assert point.measured_noisy is not None and point.measured_noisy.runs == 5
    assert ws.run("r6a", "point_run", repeats=4, approve=None) == point
    later = ws.run("r6a", "toy", space, n=12, seed=4, approve=Asked())
    assert "measured_noisy" in [n.code for n in later.notes]
    assert ws.get_result(earlier.result_id).to_json() == earlier.to_json()
    infos = ws.run_dirs(point.result_id, point={})
    assert [i.replicate for i in infos] == [0, 1, 2, 3, 4]


def test_a_deterministic_model_measures_no_noise(ws):
    """U7: on a deterministic reference model, the repeats measure no variation, and no record is made."""
    ws.load_model(R2)
    point = ws.run("ishigami", "point_run", repeats=3, approve=Asked())
    assert point.measured_noisy is None


# -- the report (data_model.md §6; P1) -------------------------------------------------------------------------


def test_a_missing_result_directory_is_rebuilt_byte_identical(ws, toy):
    """The report and the data cards rebuilt from the store alone are byte-identical (P1's test, S10)."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=15, seed=1, approve=Asked())
    directory = Path(ws.path) / "results" / result.result_id
    files = {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix in (".md", ".json")}
    shutil.rmtree(directory)
    report = ws.report(result.result_id[:8])
    assert report.markdown.encode() == files["report.md"]
    assert {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix in (".md", ".json")} == files
    (directory / "toy.json").unlink()
    ws.report(result)
    assert (directory / "toy.json").read_bytes() == files["toy.json"]


def test_rebuilds_at_once_all_succeed_with_the_same_bytes(ws, toy):
    """Review round 1, m1 (data_model.md §6): three threads, each with its own workspace (a workspace stays on its
    thread), rebuilding a result directory missing its figure, all succeed, and leave the same bytes."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=10, seed=1, approve=Asked())
    directory = Path(ws.path) / "results" / result.result_id
    files = {p.name: p.read_bytes() for p in directory.iterdir()}
    barrier = threading.Barrier(3)

    def rebuild():
        with open_workspace(ws.path) as w:
            barrier.wait(30)
            return w.report(result.result_id).markdown

    for _ in range(3):
        (directory / "toy.png").unlink()
        with ThreadPoolExecutor(3) as pool:
            reports = [f.result() for f in [pool.submit(rebuild) for _ in range(3)]]
        assert {r.encode() for r in reports} == {files["report.md"]}
        assert {p.name: p.read_bytes() for p in directory.iterdir()} == files
    assert not [p for p in directory.parent.iterdir() if p.name.startswith(".")]


# -- reproduce (U8; C51; 0055, 0062, 0063) ---------------------------------------------------------------------


def test_reproduce_is_identical_and_writes_nothing(ws, toy):
    """U8: a replay is identical, and makes no run; a deleted result replays identical from its provenance (C51)."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=15, seed=1, approve=Asked())
    before = runs_stored(ws), len(ws._store.approvals())
    check = ws.reproduce(result.shown.short_id)
    assert check.identical is True and check.differences == () and check.provenance_differences == ()
    assert (
        str(check)
        == f"Diagnostic result {result.shown.short_id}: identical (estimates, intervals, notes, figures' data cards)."
    )
    assert (runs_stored(ws), len(ws._store.approvals())) == before
    provenance = ws.get_result(result).provenance
    ws._store.delete_result(result.result_id)
    alone = ws.reproduce(provenance)
    assert alone.identical is None and alone.result.to_json() == result.to_json()
    given = ws.reproduce(ema.DiagnosticResult.from_json(result.to_json()))
    assert given.identical is True
    assert ws.list_results() == []


def test_reproduce_names_a_changed_library_version(ws, toy):
    """U8: with one library version changed, the check names exactly that provenance field."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=12, seed=1, approve=Asked())
    other = dataclasses.replace(result.provenance, numpy="0.0.1")
    check = ws.reproduce(dataclasses.replace(result, provenance=other))
    here = ema.diagnostics.base.library_versions()["numpy"]
    assert check.provenance_differences == (f"numpy: {here} here, 0.0.1 there",)
    assert f"Provenance differs in numpy ({here} here, 0.0.1 there)." in check.text


def test_reproduce_across_a_generator_version(ws, toy):
    """C51, 0063: after a design generator's version changes, the replay uses the stored points, is identical, and
    names the versions; a rebuilt design that differs is named by its rows (a test generator at two versions)."""
    from ema.designs import generators

    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=12, seed=1, approve=Asked())
    uniform = generators.get("uniform")

    @dataclasses.dataclass
    class Later:
        name: str = "uniform"
        version: str = "2"

        def size(self, identity, spec):
            return uniform.size(dataclasses.replace(identity, generator_version="1"), spec)

        def build(self, identity, spec, start=0, stop=None):
            design = uniform.build(dataclasses.replace(identity, generator_version="1"), spec, start, stop)
            points = np.array(design.points)
            points[3, 0] = np.nextafter(points[3, 0], 10.0) + 1e-6
            return dataclasses.replace(design, identity=identity, points=points)

    generators.unregister("uniform")
    try:
        generators.register(Later())
        check = ws.reproduce(result)
        assert check.identical is True
        assert check.provenance_differences == ("design generator uniform: 2 here, 1 there",)
        generators.unregister("uniform")
        generators.register(Later(version="1"))
        check = ws.reproduce(result)
        assert check.identical is True and check.provenance_differences == ("design points differ at rows 3",)
        assert "Design points differ at rows 3." in check.text
    finally:
        generators.unregister("uniform")
        generators.register(uniform)


def test_reproduce_never_raises_for_a_generator_that_raises(ws, toy):
    """Review round 1, m2 (0062, 0063): a generator whose build raises any exception is a sentence; the replay,
    from the stored points, is still identical."""
    from ema.designs import generators

    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=8, seed=1, approve=Asked())
    uniform = generators.get("uniform")

    @dataclasses.dataclass
    class Broken:
        name: str = "uniform"
        version: str = uniform.version

        def size(self, identity, spec):
            return uniform.size(identity, spec)

        def build(self, identity, spec, start=0, stop=None):
            raise ValueError("boom")

    generators.unregister("uniform")
    try:
        generators.register(Broken())
        check = ws.reproduce(result)
    finally:
        generators.unregister("uniform")
        generators.register(uniform)
    assert check.identical is True
    assert check.provenance_differences == ("the design could not be rebuilt: ValueError: boom",)


# -- export (E1-E6) --------------------------------------------------------------------------------------------


def test_export_writes_the_runs_and_the_result_bit_for_bit(ws, tmp_path, toy):
    """E1-E6 on R5 with z: one row per design row in design order, every number read back bit for bit, each missing
    model prediction with its reason, ema_new for the result's own runs, result.json loading back equal; a second
    export into the same directory is refused and changes nothing."""
    ws.load_model(ema.reference_models.path("R5"))
    ws.run("r5", "toy", R5_SPACE, prediction="y", n=10, seed=2, approve=Asked())
    result = ws.run("r5", "toy", R5_SPACE, prediction="y", n=24, seed=2, approve=Asked())
    out = tmp_path / "export"
    assert ws.export(result, out) == str(out)
    import csv

    with open(out / "runs.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    header = list(rows[0])
    assert header[:11] == ["ema_row", "ema_run_id", "ema_replicate", "ema_status", "ema_kind", "ema_reason",
                           "ema_new", "ema_time_s", "ema_run_dir", "ema_host", "ema_program"]  # fmt: skip
    assert header[11:] == ["a", "b", "y", "z", "ema_missing"]
    stored = ws._store.result_runs(result.result_id)
    assert [r["ema_run_id"] for r in rows] == list(hex_ids(stored.run_ids))
    for i, r in enumerate(rows):
        assert [float(r["a"]), float(r["b"])] == stored.points[i].tolist()
        for name in ("y", "z"):
            value = stored.values[name][i]
            assert (r[name] == "") if math.isnan(value) else float(r[name]) == value
        if r["ema_status"] == "ok" and float(r["b"]) > 0.8:
            assert r["ema_missing"].startswith("z: ")
        if r["ema_status"] == "failed":
            assert r["ema_missing"] == "" and r["ema_kind"] in ("error", "timeout") and r["ema_reason"]
    assert sum(r["ema_new"] == "true" for r in rows) == result.counts.new == 14
    document = json.loads((out / "result.json").read_text())
    assert list(document) == ["export_format", "design", "spec", "columns", "result"]
    assert set(header) <= set(document["columns"])
    assert ema.DiagnosticResult.from_json(json.dumps(document["result"])) == result
    assert (out / "report" / "report.md").read_bytes() == Path(ws.report(result).path).read_bytes()
    listing = sorted(os.listdir(out))
    with pytest.raises(ema.PathRefused, match="isn't an empty directory"):
        ws.export(result, out)
    assert sorted(os.listdir(out)) == listing


def test_export_with_a_pdf_that_cant_be_made_writes_nothing(ws, tmp_path, toy, monkeypatch):
    """Record 0081 item 31: when the PDF can't be made (here, no pandoc), PandocMissing, and no directory is made."""
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=12, seed=1, approve=Asked())
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "pandoc" else real(name, *a, **k))
    with pytest.raises(ema.PandocMissing):
        ws.export(result, tmp_path / "no_pdf", pdf=True)
    assert not (tmp_path / "no_pdf").exists()


@pytest.mark.slow
def test_export_with_pdf_writes_it_beside_the_report(ws, tmp_path, toy):
    """Record 0081 item 31: ``pdf=True`` adds report/report.pdf beside the report's Markdown, which is unchanged."""
    if shutil.which("pandoc") is None or shutil.which("lualatex") is None:
        pytest.skip("pandoc or lualatex isn't installed")
    ws.load_model(R2)
    result = ws.run("ishigami", "toy", PI_SPACE, n=12, seed=1, approve=Asked())
    out = tmp_path / "with_pdf"
    ws.export(result, out, pdf=True)
    assert (out / "report" / "report.pdf").read_bytes().startswith(b"%PDF")
    assert (out / "report" / "report.md").read_bytes() == Path(ws.report(result).path).read_bytes()


def test_export_numbers_are_17_digits():
    """E3: ``%.17g`` reads back every double bit for bit, subnormals and -0.0 included."""
    from ema.workspace._export import _number

    for x in (0.1, -0.0, 5e-324, 1.7976931348623157e308, 1e-300, -2.5e300, 1 / 3):
        assert float(_number(x)).hex() == x.hex()
    assert _number(float("nan")) == ""
