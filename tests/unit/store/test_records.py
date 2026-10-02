"""The store's writes and reads, one by one (data_model.md §7, §8: W1–W6, Q1–Q15)."""

import itertools
import os
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from ema.store import ApprovedPoint, BatchCall, Loading, Store
from ema.types.design import DesignIdentity
from ema.types.errors import AmbiguousId, NotFound, RequestError
from ema.types.identity import batch_call_id, id_array, point_hash, reuse_key, sha256_hex
from ema.types.model import Keep
from ema.types.requests import TestRunRequest
from ema.types.results import MeasuredNoisy
from ema.types.runs import FailureKind, Price, RunStatus
from tests.support import store as world


@pytest.fixture
def store(tmp_path):
    with Store.open(str(tmp_path / "ws")) as s:
        yield s


def _recent(when: datetime) -> bool:
    return when.tzinfo is UTC and abs((datetime.now(UTC) - when).total_seconds()) < 60


# W1, Q3, Q14 -------------------------------------------------------------------------------------------------


def test_a_loading_records_the_version_and_the_settings(store):
    spec = replace(world.spec(), keep=Keep.INCOMPLETE, batch_size=8, timeout_s=12.5)
    mv = store.record_loading(spec, world.SPEC_PATH, world.FILES)
    loading = store.current_loading("toy")
    assert isinstance(loading, Loading)
    assert (loading.name, loading.model_version_id, loading.spec_path) == ("toy", mv, world.SPEC_PATH)
    assert (loading.keep, loading.batch_size, loading.timeout_s) == (Keep.INCOMPLETE, 8, 12.5)
    assert _recent(loading.loaded_at)
    version = store.model_version(mv)
    assert version.spec == world.spec()  # without its settings (0029)
    assert version.files == world.FILES and version.name == "toy" and _recent(version.created_at)
    assert store.current_loading("other") is None


def test_a_repeated_loading_adds_a_loading_only(store):
    """W1: the name now means this version, path, and settings (0054)."""
    first = world.load(store)
    other = store.record_loading(world.spec(description="v2"), "/models/v2/model.json", world.FILES)
    again = store.record_loading(replace(world.spec(), keep=Keep.NONE), "/elsewhere/model.json", world.FILES)
    assert again == first != other
    loading = store.current_loading("toy")
    assert (loading.model_version_id, loading.spec_path, loading.keep) == (first, "/elsewhere/model.json", Keep.NONE)
    assert loading.loading == 3


def test_a_loading_needs_an_absolute_spec_path(store):
    with pytest.raises(ValueError, match="absolute"):
        store.record_loading(world.spec(), "model.json", world.FILES)


def test_an_unknown_model_version_is_not_found(store):
    with pytest.raises(NotFound):
        store.model_version("ab" * 32)


# W2, W3, Q4, Q12, Q13 ----------------------------------------------------------------------------------------


def test_confirmations_are_kept_in_order(store):
    store.record_confirmation("/models/a.json", "aa" * 32, "Save it?", True)
    store.record_confirmation("/models/b.json", "bb" * 32, "Save it again?", False)
    first, second = store.confirmations()
    assert (first.spec_path, first.spec_sha256, first.question, first.answer) == (
        "/models/a.json",
        "aa" * 32,
        "Save it?",
        True,
    )
    assert (second.confirmation, second.answer) == (2, False)
    assert _recent(first.asked_at)


def test_every_answer_is_stored_and_ids_count_the_approvals_before(store):
    """W3 (T3): yes and no stored; the id hashes the number of approvals before it (0062)."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5)])
    no = world.approve(store, mv, ks, answer=False)
    yes = world.approve(store, mv, ks)
    assert no != yes
    first, second = store.approvals()
    assert (first.approval_id, first.answer, second.approval_id, second.answer) == (no, False, yes, True)
    assert second.request == world.request() and second.design == world.identity(mv)
    assert (second.new, second.reused, second.reused_failed, second.time_s) == (1, 0, 0, None)
    assert second.question.startswith("Run 1 new run")
    assert store.approval_points(yes) == (ApprovedPoint(yes, ks[0].point_hash, 0),)
    assert store.approval_points(no) == ()


def test_has_approval_needs_a_yes(store):
    """Q4: the first approval shows the command; a declined one doesn't count."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5)])
    world.approve(store, mv, ks, answer=False)
    assert not store.has_approval(mv)
    world.approve(store, mv, ks)
    assert store.has_approval(mv)


def test_the_test_runs_approval_has_no_design(store):
    mv = world.load(store)
    nominal = (1.0, 0.0, 0.5)
    approval = world.approve(store, mv, world.keys(mv, [nominal]), req=TestRunRequest(nominal))
    (stored,) = store.approvals()
    assert (stored.approval_id, stored.asked_for, stored.design) == (approval, "test_run", None)
    assert stored.request == TestRunRequest(nominal)


def test_an_approval_is_refused_when_malformed(store):
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5)])
    common = {"model_version_id": mv, "question": "?", "answer": True}
    price = Price.make(new=1, reused=0, time_s=None, from_runs=0)
    with pytest.raises(ValueError, match="no new runs"):
        store.record_approval(asked_for="diagnostic_evaluation", request=world.request(), design=world.identity(mv),
                              price=Price.make(new=0, reused=0, time_s=None, from_runs=0), points=[], **common)  # fmt: skip
    with pytest.raises(ValueError, match="points are"):
        store.record_approval(asked_for="diagnostic_evaluation", request=world.request(), design=world.identity(mv),
                              price=Price.make(new=2, reused=0, time_s=None, from_runs=0), points=ks, **common)  # fmt: skip
    with pytest.raises(ValueError, match="design"):
        store.record_approval(asked_for="diagnostic_evaluation", request=world.request(), design=None, price=price,
                              points=ks, **common)  # fmt: skip
    with pytest.raises(ValueError, match="twice"):
        store.record_approval(asked_for="diagnostic_evaluation", request=world.request(), design=world.identity(mv),
                              price=Price.make(new=2, reused=0, time_s=None, from_runs=0), points=ks * 2, **common)  # fmt: skip
    with pytest.raises(NotFound):
        store.record_approval(asked_for="diagnostic_evaluation", request=world.request(), design=world.identity(mv),
                              price=price, points=ks, **{**common, "model_version_id": "ee" * 32})  # fmt: skip
    assert store.approvals() == ()


def test_coverage_of_an_unknown_approval_is_not_found(store):
    with pytest.raises(NotFound):
        store.approval_coverage("ab" * 32, [])


# W4, Q1, Q2, Q9 ----------------------------------------------------------------------------------------------


def test_run_times_count_every_stored_run(store):
    """Q2: every stored run, any status, and their mean time; None when there is none."""
    mv = world.load(store)
    assert store.run_times(mv) == (0, None)
    ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    world.record_runs(
        store, [world.ok_run(ks[0], mv, approval, time_s=1.0), world.failed_run(ks[1], mv, approval, time_s=2.0)]
    )
    assert store.run_times(mv) == (2, 1.5)


def test_current_runs_read_in_chunks(tmp_path):
    """Q1 looks points up in chunks (30,000 by default; 2 here)."""

    class Small(Store):
        chunk_rows = 2

    with Small.open(str(tmp_path)) as store:
        mv = world.load(store)
        points = [(float(i), 0.0, 0.5) for i in range(5)]
        approval, runs = world.made(store, mv, points)
        found = store.current_runs(mv, [point_hash(p) for p in points] + [point_hash((9.0, 0.0, 0.5))])
        assert {k: r.run_id for k, r in found.items()} == {
            (point_hash(p), 0): r.run_id for p, r in zip(points, runs, strict=True)
        }
        columns = store.runs_by_id(world.ids(runs[::-1] + runs), points=True)
        assert np.array_equal(columns.run_ids, world.ids(runs[::-1] + runs))
        assert list(columns.values["y"]) == [4.0, 3.0, 2.0, 1.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0]
        res = world.store_result(store, world.result(mv, runs + runs[:1], approval=approval))
        assert np.array_equal(store.get_result(res.result_id).provenance.run_ids, world.ids(runs + runs[:1]))
        assert len(store.result_runs(res.result_id)) == 6


def test_a_batch_call_is_stored_with_its_runs(store):
    """W4 for a batch call (0025); Q9 reads it."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    runs = [world.ok_run(k, mv, approval) for k in ks]
    call = world.record_batch(store, runs, time_s=0.5)
    assert call.batch_call_id == batch_call_id([r.run_id for r in runs])
    assert store.batch_call(call.batch_call_id) == BatchCall(call.batch_call_id, 2, 0.5)
    assert store.get_run(runs[0].run_id).batch_call_id == call.batch_call_id
    with pytest.raises(NotFound):
        store.batch_call("ab" * 32)


def test_a_call_is_refused_when_malformed(store):
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    runs = [world.ok_run(k, mv, approval) for k in ks]
    with pytest.raises(ValueError, match="one run"):
        store.record_call(runs)  # several runs, no batch call
    with pytest.raises(ValueError):
        store.record_call([])
    wrong = BatchCall("ab" * 32, 2, 1.0)
    with pytest.raises(ValueError, match="batch call"):
        store.record_call([replace(r, batch_call_id=wrong.batch_call_id) for r in runs], wrong)
    with pytest.raises(ValueError, match="twice"):
        call = BatchCall(batch_call_id([runs[0].run_id] * 2), 2, 1.0)
        store.record_call([replace(runs[0], batch_call_id=call.batch_call_id)] * 2, call)
    assert store.run_times(mv) == (0, None)


def test_get_run_and_runs_at_a_point(store):
    """Q9: a run by its id; a result's runs at a point, one per replicate."""
    mv = world.load(store)
    x = (1.0, 0.0, 0.5)
    ks = [world.keys(mv, [x], replicate=r)[0] for r in (2, 1)]
    approval = world.approve(store, mv, ks)
    runs = [world.ok_run(k, mv, approval) for k in ks]
    world.record_runs(store, runs)
    res = world.store_result(store, world.result(mv, runs, approval=approval))
    assert [r.replicate for r in store.runs_at(res.result_id, point_hash(x))] == [1, 2]
    assert store.runs_at(res.result_id, point_hash((0.0, 0.0, 0.5))) == ()
    with pytest.raises(NotFound):
        store.get_run("ab" * 32)
    with pytest.raises(NotFound):
        store.runs_at("ab" * 32, point_hash(x))


# W5, W6, Q5–Q8, Q10, Q15 -------------------------------------------------------------------------------------


def test_a_point_runs_result_reads_back_equal_to_the_evaluated_one(store):
    """Record 0072 (the coordinator's ruling on wave 2's m1): inside a result, its own measured-noisy record has
    made_at None; the table keeps made_at, which Q10 reads; Q6 returns the result's own record with made_at None."""
    mv = world.load(store)
    x = (1.0, 0.0, 0.5)
    ks = [world.keys(mv, [x], replicate=r)[0] for r in (1, 2, 3)]
    approval = world.approve(store, mv, ks)
    runs = [world.ok_run(k, mv, approval, y=1.0 + 2.0**-30 * k.replicate) for k in ks]
    world.record_runs(store, runs)
    evaluated = world.result(mv, runs, approval=approval, req=world.request(diagnostic="point_run"),
                             noisy=world.noisy_record(mv, x))  # fmt: skip
    assert evaluated.measured_noisy.made_at is None
    world.store_result(store, evaluated)
    read_back = store.get_result(evaluated.result_id)
    assert read_back == evaluated and read_back.to_json() == evaluated.to_json()
    assert read_back.measured_noisy.made_at is None
    (row,) = store.measured_noisy(mv, "y")
    assert _recent(row.made_at) and replace(row, made_at=None) == evaluated.measured_noisy


def test_w5_refuses_a_made_at_it_would_set(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    noisy = replace(world.noisy_record(mv, (1.0, 0.0, 0.5)), made_at=datetime.now(UTC))
    res = world.result(mv, runs, approval=approval, noisy=noisy)
    with pytest.raises(ValueError, match="made_at"):
        world.store_result(store, res)


def test_w5_refuses_a_result_id_that_is_not_its_reuse_keys(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    res = world.result(mv, runs, approval=approval)
    other = replace(res, result_id="ab" * 32, provenance=res.provenance)
    with pytest.raises(ValueError, match="reuse key"):
        world.store_result(store, other)


def test_w5_refuses_runs_of_another_model_version(store):
    mv = world.load(store)
    other = world.load(store, world.spec(name="other"))
    _, runs = world.made(store, other, [(1.0, 0.0, 0.5)])
    foreign = [replace(r, model_version_id=mv) for r in runs]  # same ids: the store finds them under `other`
    with pytest.raises(ValueError, match="model version"):
        world.store_result(store, world.result(mv, foreign, approval=None))


def test_w5_refuses_an_approval_answered_no(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    no = world.approve(store, mv, world.keys(mv, [(2.0, 0.0, 0.5)]), answer=False)
    res = world.result(mv, runs, approval=approval)
    res = replace(res, provenance=replace(res.provenance, approval_id=no))
    with pytest.raises(ValueError):
        world.store_result(store, res)


def test_find_result_and_get_result(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    res = world.result(mv, runs, approval=approval)
    assert store.find_result(res.result_id) is None
    with pytest.raises(NotFound):
        store.get_result(res.result_id)
    world.store_result(store, res)
    assert store.find_result(res.result_id) == res == store.get_result(res.result_id)


def test_a_results_runs_hold_every_column(store):
    """Q7: points, status, kind, reason, stderr tail, model predictions, time, host, program, batch, approval."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    ok = world.ok_run(ks[0], mv, approval, z=None, time_s=2.0)
    failed = world.failed_run(ks[1], mv, approval, kind=FailureKind.UNREAD, host="host-2")
    call = world.record_batch(store, [world.ok_run(ks[2], mv, approval)], time_s=4.0)
    store.record_call([ok])
    store.record_call([failed])
    rows = [ok, failed, store.get_run(ks[2].run_id), ok]
    res = world.store_result(store, world.result(mv, rows, approval=approval))
    c = store.result_runs(res.result_id)
    assert len(c) == 4
    assert c.points.tolist() == [list(r.point) for r in rows]
    assert c.replicates.tolist() == [0, 0, 0, 0]
    assert c.status.tolist() == [0, 1, 0, 0] and c.kind.tolist() == [-1, FailureKind.UNREAD.code, -1, -1]
    assert c.values["y"][[0, 2, 3]].tolist() == [1.5, 1.5, 1.5] and np.isnan(c.values["y"][1])
    assert np.isnan(c.values["z"][[0, 1, 3]]).all() and c.values["z"][2] == 2.5
    assert c.missing == {"z": {ok.run_id: ok.missing["z"]}}
    assert c.reasons == {failed.run_id: "exited with code 2"}
    assert c.stderr_tails == {failed.run_id: failed.stderr_tail}
    assert c.time_s.tolist() == [2.0, 0.25, 0.25, 2.0]
    assert c.host.tolist() == ["host-1", "host-2", "host-1", "host-1"]
    assert c.program.tolist() == ["/usr/bin/python3"] * 4
    assert c.batch_call_ids.tolist()[2] == bytes.fromhex(call.batch_call_id)
    assert c.batch_call_ids.tolist()[0] == bytes(32)
    assert (c.approval_ids == id_array([approval])[0]).all()
    with pytest.raises(NotFound):
        store.result_runs("ab" * 32)


def test_runs_by_id_leaves_out_points_and_tails_unless_asked(store):
    """Q15: points only when asked (a replay, 0062); stderr tails left empty (0061)."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    failed = world.failed_run(ks[0], mv, approval)
    store.record_call([failed])
    columns = store.runs_by_id([failed.run_id])
    assert columns.points is None and columns.stderr_tails == {} and columns.reasons == {failed.run_id: failed.reason}
    assert set(columns.values) == {"y", "z"}  # every model prediction of the spec, NaN for a failed run
    with pytest.raises(NotFound, match="1 of 2 runs"):
        store.runs_by_id([failed.run_id, "ab" * 32])
    assert len(store.runs_by_id([])) == 0


def test_list_results_newest_first_with_filters(store):
    """Q8: summaries by model name, model version, diagnostic, or model prediction, newest first."""
    mv = world.load(store)
    other = world.load(store, world.spec(name="other"))
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    a2, runs2 = world.made(store, other, [(1.0, 0.0, 0.5)])
    first = world.store_result(store, world.result(mv, runs, approval=approval))
    second = world.store_result(store, world.result(mv, runs, approval=None, req=world.request(prediction="z", seed=2)))
    third = world.store_result(store, world.result(other, runs2, approval=a2, req=world.request(diagnostic="lines")))
    listed = store.list_results()
    assert [s.result_id for s in listed] == [third.result_id, second.result_id, first.result_id]
    assert [s.result_id for s in store.list_results(name="toy")] == [second.result_id, first.result_id]
    assert [s.result_id for s in store.list_results(model_version_id=other)] == [third.result_id]
    assert [s.result_id for s in store.list_results(diagnostic="lines")] == [third.result_id]
    assert [s.result_id for s in store.list_results(prediction="z")] == [second.result_id]
    summary = listed[-1]
    assert summary.model_version == f"toy@{mv[:12]}" and summary.short_id == store.short("result", first.result_id)
    assert summary.text == (
        f"Diagnostic result {summary.short_id}: scatter on toy@{mv[:12]}, y; 1 runs: 1 new, 0 reused, 0 failed; "
        f"report: ema report {summary.short_id}"
    )
    assert _recent(summary.made_at)


def test_delete_result_removes_its_rows_and_directory(store):
    """W6: its measured-noisy, result_runs, and results rows, then its directory; runs and approvals kept."""
    mv = world.load(store)
    x = (1.0, 0.0, 0.5)
    approval, runs = world.made(store, mv, [x])
    res = world.store_result(store, world.result(mv, runs, approval=approval, noisy=world.noisy_record(mv, x)))
    assert os.path.isdir(store.layout.result_dir(res.result_id))
    store.delete_result(res.result_id)
    assert store.find_result(res.result_id) is None and store.measured_noisy(mv, "y") == ()
    assert not os.path.exists(store.layout.result_dir(res.result_id))
    assert store.get_run(runs[0].run_id) == runs[0] and len(store.approvals()) == 1
    replay = store.runs_by_id(res.provenance.run_ids, points=True)  # a replay reads them after deletion (Q15)
    assert replay.points.tolist() == [list(x)]
    with pytest.raises(NotFound):
        store.delete_result(res.result_id)


# Q11 ---------------------------------------------------------------------------------------------------------


def test_resolve_and_short_ids(store):
    """Q11: a prefix of at least 4 hex digits naming one id; the shortest unique prefix, at least 4 digits."""
    mv = world.load(store)
    ks = world.keys(mv, [(float(i), 0.0, 0.5) for i in range(40)])
    approval = world.approve(store, mv, ks)
    world.record_runs(store, [world.ok_run(k, mv, approval) for k in ks])
    ids = sorted(k.run_id for k in ks)
    for i, rid in enumerate(ids):
        shortest = store.short("run", rid)
        common = max(
            (
                len(os.path.commonprefix([rid, n]))
                for n in (ids[i - 1] if i else "", ids[i + 1] if i + 1 < len(ids) else "")
            ),
        )
        assert shortest == rid[: max(4, common + 1)]
        assert store.resolve("run", shortest) == rid
        assert store.resolve("run", rid.upper()) == rid
    assert store.resolve("model_version", mv[:4]) == mv
    assert store.short("approval", approval) == approval[:4]


def test_resolve_refusals(store):
    mv = world.load(store)
    with pytest.raises(RequestError, match="4 to 64 hex digits"):
        store.resolve("model_version", mv[:3])
    with pytest.raises(RequestError):
        store.resolve("model_version", "zzzz")
    with pytest.raises(NotFound):
        store.resolve("result", mv[:8])
    with pytest.raises(NotFound):
        store.short("result", mv)
    with pytest.raises(ValueError, match="kind"):
        store.resolve("loading", mv[:8])


def test_an_ambiguous_prefix_lists_the_ids(store):
    mv = world.load(store)
    ks = world.keys(mv, [(float(i), 0.0, 0.5) for i in range(2000)])
    approval = world.approve(store, mv, ks)
    world.record_batch(store, [world.ok_run(k, mv, approval) for k in ks])
    ordered = sorted(k.run_id for k in ks)
    a, b = next((a, b) for a, b in itertools.pairwise(ordered) if a[:4] == b[:4])
    with pytest.raises(AmbiguousId) as error:
        store.resolve("run", a[:4])
    assert store.short("run", a) in str(error.value) and store.short("run", b) in str(error.value)


def test_measured_noisy_round_trip(store):
    mv = world.load(store)
    x = (1.0, 0.0, 0.5)
    approval, runs = world.made(store, mv, [x])
    world.store_result(store, world.result(mv, runs, approval=approval, noisy=world.noisy_record(mv, x, std=None)))
    (row,) = store.measured_noisy(mv, "y")
    assert isinstance(row, MeasuredNoisy) and row.std is None and row.point == x and row.runs == 4


def test_the_design_identity_is_stored_with_the_result_and_the_approval(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    res = world.store_result(store, world.result(mv, runs, approval=approval))
    assert isinstance(store.get_result(res.result_id).provenance.design, DesignIdentity)
    assert store.approvals()[0].design == store.get_result(res.result_id).provenance.design


# The result directory (§6) -----------------------------------------------------------------------------------


def test_the_result_directory_is_renamed_into_place(store):
    rid = "ab" * 32
    with store.result_directory(rid) as tmp:
        assert os.path.dirname(tmp) == store.layout.results and tmp != store.layout.result_dir(rid)
        with open(os.path.join(tmp, "report.md"), "w") as f:
            f.write("x")
    assert os.listdir(store.layout.results) == [rid]
    with open(os.path.join(store.layout.result_dir(rid), "report.md")) as f:
        assert f.read() == "x"


def test_a_leftover_directory_with_no_row_is_replaced(store):
    rid = "ab" * 32
    os.makedirs(os.path.join(store.layout.result_dir(rid), "old"))
    with store.result_directory(rid) as tmp:
        open(os.path.join(tmp, "report.md"), "w").close()
    assert os.listdir(store.layout.result_dir(rid)) == ["report.md"]


def test_a_directory_with_a_row_is_kept(store):
    mv = world.load(store)
    approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
    res = world.store_result(store, world.result(mv, runs, approval=approval))
    with store.result_directory(res.result_id) as tmp:
        open(os.path.join(tmp, "other.md"), "w").close()
    assert os.listdir(store.layout.result_dir(res.result_id)) == ["report.md"]
    assert os.listdir(store.layout.results) == [res.result_id]


def test_a_failed_analysis_leaves_no_directory(store):
    rid = "ab" * 32
    with pytest.raises(RuntimeError), store.result_directory(rid):
        raise RuntimeError("analysis failed")
    assert os.listdir(store.layout.results) == []


def test_ids_are_the_same_in_two_fresh_workspaces(tmp_path):
    """§3.4: the same work in two fresh workspaces gets the same ids."""
    found = []
    for name in ("one", "two"):
        with Store.open(str(tmp_path / name)) as store:
            mv = world.load(store)
            approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5)])
            res = world.store_result(store, world.result(mv, runs, approval=approval))
            found.append((mv, approval, runs[0].run_id, res.result_id))
    assert found[0] == found[1]
    assert found[0][3] == sha256_hex(reuse_key(found[0][0], world.request(), [found[0][2]], world.VERSIONS))


def test_a_runs_status_reads_back(store):
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    store.record_call([world.failed_run(ks[0], mv, approval, kind=FailureKind.TIMEOUT, exit_code=None)])
    run = store.get_run(ks[0].run_id)
    assert (run.status, run.kind, run.exit_code) == (RunStatus.FAILED, FailureKind.TIMEOUT, None)


def test_a_stored_run_passes_runs_own_checks(store):
    """Q1 builds stored runs without checking them again (record 0072): they must pass ``Run``'s checks."""
    mv = world.load(store)
    ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
    approval = world.approve(store, mv, ks)
    world.record_runs(store, [world.ok_run(ks[0], mv, approval, z=None), world.failed_run(ks[1], mv, approval)])
    for run in store.current_runs(mv, [k.point_hash for k in ks]).values():
        assert replace(run) == run  # replace builds a new Run, through __post_init__'s checks
        assert isinstance(run.point, tuple) and all(type(v) is float for v in run.point)
        with pytest.raises(TypeError):
            run.predictions["y"] = 0.0  # read-only, as Run makes it


def test_the_store_never_updates_a_row():
    """I1: no public name updates, and no statement in the package is an UPDATE (W6 alone deletes)."""
    import inspect
    import re

    import ema.store.store as module

    source = inspect.getsource(module)
    assert not re.search(r"\bUPDATE\b|\bREPLACE\b|\bUPSERT\b|ON CONFLICT", source)
    assert [m.start() for m in re.finditer(r"\bDELETE FROM\b", source)] and "def delete_result" in source
    public = [n for n in dir(Store) if not n.startswith("_")]
    assert not [n for n in public if n.startswith(("update", "set_", "replace", "edit"))]
