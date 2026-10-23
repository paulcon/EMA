"""The store contract (contracts.md, the store's parts of C46, C50–C52, C56, and C17's round trip through the store):
one check per invariant of data_model.md §9, I1–I12.

The implementation is the store's class, opened on a fresh workspace by each check (``tests.support.store``). Each
check has a broken toy, a subclass of ``Store`` that differs from it in one way, and must fail it (contracts.md,
Negative controls); ``test_every_check_fails_on_its_broken_toy`` is the meta-test. The runner's parts of C46–C49
and C56 (the cap counted when a call starts, an interrupt during a call) are in ``tests/contracts/runner.py``; the
workspace's parts of C50 and C51 (a repeated request asks nothing; a replay gives an identical result) are step 14's.
"""

from __future__ import annotations

import inspect
import math
import os
import struct
import sys
from dataclasses import replace
from typing import Any

import numpy as np
import pytest

from ema.store import Store
from ema.types.errors import NotFound
from ema.types.identity import id_array, point_hash, run_id
from ema.types.results import Counts, DiagnosticResult
from ema.types.runs import FailureKind, Run, RunKey, RunStatus
from tests.support import store as world


def bits(x: float) -> bytes:
    return struct.pack("<d", x)


def refused(fn: Any, *args: Any, **kw: Any) -> bool:
    """Tell whether ``fn`` refuses its arguments with ``ValueError`` (a store's precondition) or ``NotFound``."""
    try:
        fn(*args, **kw)
    except (ValueError, NotFound):
        return True
    return False


# --------------------------------------------------------------------------------------------------------------
# The checks


def check_append_only(store_class: type[Store]) -> None:
    """I1 (C49): no row is updated; only W6 deletes, and only a diagnostic result's rows (runs, approvals kept)."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        (k,) = world.keys(mv, [(1.0, 0.0, 0.5)])
        approval = world.approve(store, mv, [k])
        failed = world.failed_run(k, mv, approval)
        store.record_call([failed])
        res = world.store_result(store, world.result(mv, [failed], approval=approval))
        before = (store.get_run(failed.run_id), store.approvals(), store.get_result(res.result_id))
        # More writes: a retry beside the failed run, a new loading of the same name, another approval.
        retry_key = world.keys(mv, [(1.0, 0.0, 0.5)], attempt=1)
        retry_approval = world.approve(store, mv, retry_key)
        store.record_call([world.ok_run(retry_key[0], mv, retry_approval)])
        world.load(store, world.spec(description="Edited."))
        assert store.get_run(failed.run_id) == before[0], "a failed run was changed by its retry"
        assert store.approvals()[: len(before[1])] == before[1], "an earlier approval was changed"
        assert store.get_result(res.result_id) == before[2], "an earlier diagnostic result was changed"
        store.delete_result(res.result_id)
        assert store.find_result(res.result_id) is None
        assert store.get_run(failed.run_id) == before[0], "W6 deleted a run"
        assert store.approvals()[: len(before[1])] == before[1], "W6 deleted an approval"
        assert len(store.runs_by_id(world.ids([failed]))) == 1


def check_retry_beside_failed(store_class: type[Store]) -> None:
    """I2 (C46, C47): attempts 0 … k with no gap, each but the last failed; the current run is the last."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        x = (1.0, 0.25, 0.5)
        (k0,) = world.keys(mv, [x])
        a0 = world.approve(store, mv, [k0])
        store.record_call([world.failed_run(k0, mv, a0)])
        (k2,) = world.keys(mv, [x], attempt=2)
        a2 = world.approve(store, mv, [k2])
        assert refused(store.record_call, [world.ok_run(k2, mv, a2)]), "an attempt with a gap was stored"
        (k1,) = world.keys(mv, [x], attempt=1)
        a1 = world.approve(store, mv, [k1])
        store.record_call([world.ok_run(k1, mv, a1)])
        current = store.current_runs(mv, [k0.point_hash])
        assert current[(k0.point_hash, 0)].run_id == k1.run_id, "the current run is not the last attempt"
        assert store.get_run(k0.run_id).status is RunStatus.FAILED, "the failed run is not kept beside its retry"
        (k2b,) = world.keys(mv, [x], attempt=2)
        a3 = world.approve(store, mv, [k2b])
        assert refused(store.record_call, [world.ok_run(k2b, mv, a3)]), "an ok run was retried"


def check_run_keys(store_class: type[Store]) -> None:
    """I3: a run's point hash is its point's and its id its key's hash; W4 refuses any other id."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        (k,) = world.keys(mv, [(1.0, 0.5, 0.5)])
        approval = world.approve(store, mv, [k])
        wrong = replace(world.ok_run(k, mv, approval), run_id=run_id(mv, k.point_hash, 1, 0))
        assert refused(store.record_call, [wrong]), "a run whose id is not its key's hash was stored"
        moved = replace(world.ok_run(k, mv, approval), point=(1.0, 0.5, 0.25))
        assert refused(store.record_call, [moved]), "a run whose point is not its key's was stored"
        store.record_call([world.ok_run(k, mv, approval)])
        run = store.get_run(k.run_id)
        assert run_id(mv, point_hash(run.point), run.replicate, run.attempt) == run.run_id


def check_reuse(store_class: type[Store]) -> None:
    """C46 (I2, I3): a stored run is found at its model version, exact point, and replicate, and nowhere else."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        other = world.load(store, world.spec(name="other"))
        x = (0.1234567891, -0.0, 0.5)
        _, (run,) = world.made(store, mv, [x])
        found = store.current_runs(mv, [point_hash(x)])
        reused = found.get((point_hash(x), 0))
        assert reused is not None and reused.run_id == run.run_id, "a stored run is not reused at its exact point"
        near = (math.nextafter(x[0], 1.0), -0.0, 0.5)
        zero = (x[0], 0.0, 0.5)
        assert store.current_runs(mv, [point_hash(near), point_hash(zero)]) == {}, "a run reused at another point"
        assert store.current_runs(other, [point_hash(x)]) == {}, "a run reused for another model version"
        assert (point_hash(x), 1) not in store.current_runs(mv, [point_hash(x)])


def check_approval_cap(store_class: type[Store]) -> None:
    """I4 (C48, P3): a run only under an approval answered yes for its model version, at one of its points, once."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        other = world.load(store, world.spec(name="other"))
        ka, kb, kc = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
        declined = world.approve(store, mv, [ka], answer=False)
        assert refused(store.record_call, [world.ok_run(ka, mv, declined)]), "a run under a declined approval"
        approval = world.approve(store, mv, [ka, kb])
        assert refused(store.record_call, [world.ok_run(kc, mv, approval)]), "a run at a point not approved"
        (ko,) = world.keys(other, [(0.0, 0.0, 0.5)])
        assert refused(store.record_call, [world.ok_run(ko, other, approval)]), "a run of another model version"
        coverage = store.approval_coverage(approval, [ka, kb, kc])
        assert coverage.covered == (True, True, False) and coverage.model_version_id == mv
        store.record_call([world.failed_run(ka, mv, approval)])
        assert store.approval_coverage(approval, [ka, kb]).covered == (False, True), "a run key still covered"
        (ka1,) = world.keys(mv, [ka.point], attempt=1)
        assert refused(store.record_call, [world.ok_run(ka1, mv, approval)]), "two runs of one approval at a key"
        assert store.approval_coverage(declined, [ka]).covered == (False,)


def check_interrupt(store_class: type[Store]) -> None:
    """I5 (C49): a call's runs are stored together or not at all."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
        approval = world.approve(store, mv, ks[:2])  # the third key is not approved: the call is refused whole
        runs = [world.ok_run(k, mv, approval) for k in ks]
        with pytest.raises(ValueError):
            world.record_batch(store, runs)
        assert store.current_runs(mv, [k.point_hash for k in ks]) == {}, "part of a refused call was stored"
        assert store.run_times(mv) == (0, None)
        call = world.record_batch(store, runs[:2], time_s=0.5)
        assert {r.batch_call_id for r in store.current_runs(mv, [k.point_hash for k in ks]).values()} == {
            call.batch_call_id
        }
        assert store.batch_call(call.batch_call_id) == call


def check_prediction_rows(store_class: type[Store]) -> None:
    """I6 (0022, 0043): an ok run has every model prediction of its spec, each a value or a reason; a failed one none."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        ks = world.keys(mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
        approval = world.approve(store, mv, ks)
        partial = replace(world.ok_run(ks[0], mv, approval), predictions={"y": 1.0}, missing={})
        assert refused(store.record_call, [partial]), "an ok run without every model prediction was stored"
        stray = replace(world.ok_run(ks[0], mv, approval), predictions={"y": 1.0, "z": 2.0, "w": 3.0})
        assert refused(store.record_call, [stray]), "a model prediction not in the spec was stored"
        missing = world.ok_run(ks[1], mv, approval, z=None)
        failed = world.failed_run(ks[2], mv, approval, kind=FailureKind.TIMEOUT, exit_code=None)
        world.record_runs(store, [missing, failed])
        assert store.get_run(missing.run_id) == missing
        assert store.get_run(failed.run_id) == failed
        columns = store.runs_by_id(world.ids([missing, failed]))
        assert columns.values["y"][0] == 1.5 and np.isnan(columns.values["z"]).all()
        assert columns.missing["z"] == {missing.run_id: missing.missing["z"]}
        assert columns.reasons == {failed.run_id: failed.reason}


def check_repeat(store_class: type[Store]) -> None:
    """I7 (C50): at most one diagnostic result per reuse key; a second W5 of it writes nothing and returns the first."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        approval, runs = world.made(store, mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
        first = world.result(mv, runs, approval=approval, note="the first")
        assert world.store_result(store, first) == first
        again = world.result(mv, runs, approval=approval, note="computed again, meanwhile")
        assert again.result_id == first.result_id
        assert world.store_result(store, again) == first, "a repeated result was not the stored one"
        assert store.find_result(first.result_id) == first
        assert len(store.list_results()) == 1
        assert os.listdir(store.layout.results) == [first.result_id], "a second result directory was kept"


def check_provenance(store_class: type[Store]) -> None:
    """I8 (C51): a result exists only with its provenance and one ``result_runs`` row per design row, in one write."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        approval, runs = world.made(store, mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
        rows = [runs[0], runs[1], runs[0]]  # rows at the same point share a run
        res = world.store_result(store, world.result(mv, rows, approval=approval))
        assert len(store.result_runs(res.result_id)) == 3, "not one result_runs row per design row"
        stored = store.get_result(res.result_id)
        assert np.array_equal(stored.provenance.run_ids, world.ids(rows)), "the provenance's runs are not its rows"
        assert stored.provenance.approval_id == approval
        (ghost,) = world.keys(mv, [(9.0, 0.0, 0.5)])
        unknown = world.result(mv, [runs[0], world.ok_run(ghost, mv, approval)], approval=approval)
        with pytest.raises((ValueError, NotFound)):
            world.store_result(store, unknown)
        assert store.find_result(unknown.result_id) is None, "a result was stored without its runs"
        undirected = world.result(mv, runs[:1], approval=approval)
        assert refused(store.record_result, undirected), "a result was stored with no directory in place"


def check_design_order(store_class: type[Store]) -> None:
    """I9 (C56): ``result_runs`` is in design order, and runs are read in the order given, a repeated id repeated."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        points = [(float(i), 0.0, 0.5) for i in range(6)]
        ks = world.keys(mv, points)
        approval = world.approve(store, mv, ks)
        runs = [world.ok_run(k, mv, approval, y=float(i)) for i, k in enumerate(ks)]
        world.record_runs(store, [runs[i] for i in (4, 1, 5, 0, 3, 2)])  # finished in another order
        order = [runs[i] for i in (3, 0, 5, 3, 1, 4, 2)]
        columns = store.runs_by_id(world.ids(order))
        assert np.array_equal(columns.run_ids, world.ids(order)), "runs not read in the order given"
        assert list(columns.values["y"]) == [3.0, 0.0, 5.0, 3.0, 1.0, 4.0, 2.0]
        res = world.store_result(store, world.result(mv, order, approval=approval))
        assert np.array_equal(store.result_runs(res.result_id).run_ids, world.ids(order)), "not in design order"


def check_measured_noisy(store_class: type[Store]) -> None:
    """I10 (C52): a point run's record is stored with its result, read newest first; earlier results unchanged."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        x = (1.0, 0.0, 0.5)
        point_run = world.request(diagnostic="point_run")
        ks = [world.keys(mv, [x], replicate=r)[0] for r in (1, 2)]
        approval = world.approve(store, mv, ks, req=point_run)
        runs = [world.ok_run(k, mv, approval, y=1.0 + k.replicate) for k in ks]
        world.record_runs(store, runs)
        first = world.result(mv, runs, approval=approval, req=point_run, noisy=world.noisy_record(mv, x))
        world.store_result(store, first)
        quiet = world.store_result(store, world.result(mv, runs, approval=None))  # reuses the point run's runs
        (read,) = store.measured_noisy(mv, "y")
        assert read.result_id == first.result_id and read.made_at is not None and read.std == 0.125
        assert store.measured_noisy(mv, "z") == ()
        scatter = world.result(mv, runs, approval=None, req=world.request(seed=3), noisy=world.noisy_record(mv, x))
        assert refused(world.store_result, store, scatter), "a measured-noisy record with a result not a point run's"
        second_req = world.request(diagnostic="point_run", seed=2)
        more = [world.keys(mv, [x], replicate=r)[0] for r in (3, 4)]
        second_approval = world.approve(store, mv, more, req=second_req)
        more_runs = [world.ok_run(k, mv, second_approval, y=1.0 + k.replicate) for k in more]
        world.record_runs(store, more_runs)
        noisy = world.noisy_record(mv, x, std=0.5)
        second = world.result(mv, runs + more_runs, approval=second_approval, req=second_req, noisy=noisy)
        world.store_result(store, second)
        records = [m.result_id for m in store.measured_noisy(mv, "y")]
        assert records == [second.result_id, first.result_id], "not every record, newest first"
        assert store.get_result(first.result_id) == first, "an earlier point run's result changed"
        assert store.get_result(quiet.result_id) == quiet, "an earlier result changed"


def check_round_trip(store_class: type[Store]) -> None:
    """I11 (C17): every stored record loads back equal, every double exact; "none" stored as null with its reason."""
    awkward = (-0.0, 5e-324, 2.2250738585072014e-308 / 3, 0.1, 1e300, -1 / 3)
    with world.opened(store_class) as store:
        mv = world.load(store)
        assert store.model_version(mv).spec == world.spec()
        points = [(v, -v, 0.5) for v in awkward]
        ks = world.keys(mv, points)
        point_run = world.request(diagnostic="point_run")
        approval = world.approve(store, mv, ks, req=point_run)
        runs = [world.ok_run(k, mv, approval, y=v, z=-v) for k, v in zip(ks, awkward, strict=True)]
        world.record_runs(store, runs)
        for run in runs:
            back = store.get_run(run.run_id)
            assert back == run, "a run did not load back equal"
            assert [bits(v) for v in back.point] == [bits(v) for v in run.point], "a point's bits changed"
            values = [back.predictions["y"], run.predictions["y"]]
            assert None not in values and bits(values[0]) == bits(values[1]), "a value's bits changed"  # type: ignore[arg-type]
        columns = store.runs_by_id(world.ids(runs), points=True)
        assert columns.points is not None
        assert columns.points.tobytes() == np.array(points).tobytes()
        assert columns.values["y"].tobytes() == np.array(awkward).tobytes()
        noisy = world.noisy_record(mv, points[0], std=None)
        res = world.result(mv, runs, approval=approval, req=point_run, noisy=noisy)
        world.store_result(store, res)
        stored = store.get_result(res.result_id)
        assert stored == res and stored.to_json() == res.to_json(), "a result did not load back equal"
        assert stored.measured_noisy is not None and stored.measured_noisy.made_at is None


def check_new_runs(store_class: type[Store]) -> None:
    """I12 (E6): a result's new runs are exactly the runs made under its approval."""
    with world.opened(store_class) as store:
        mv = world.load(store)
        old_approval, old = world.made(store, mv, [(0.0, 0.0, 0.5)])
        approval, new = world.made(store, mv, [(1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
        good = world.result(mv, old + new, approval=approval)
        world.store_result(store, good)
        columns = store.result_runs(good.result_id)
        is_new = columns.approval_ids == id_array([approval])[0]
        assert list(is_new) == [False, True, True]
        assert is_new.sum() == good.counts.new
        c = good.counts
        lying = world.result(mv, old + new, approval=approval, req=world.request(seed=5), note="claims 1 new run")
        lying = replace(lying, counts=Counts(c.rows, c.runs, 1, c.reused + 1, c.failed, c.missing, c.usable))
        assert refused(world.store_result, store, lying), "a result whose new runs aren't its approval's"
        stranger = world.result(mv, old, approval=old_approval, note="its approval's runs aren't its own")
        stranger = replace(stranger, provenance=replace(stranger.provenance, approval_id=approval))
        assert refused(world.store_result, store, stranger), "a result with another evaluation's approval"
        # Subsets: a result using 1 of its approval's 2 runs; an approval of 2 runs with 1 made (C49: no result).
        both_approval, both = world.made(store, mv, [(3.0, 0.0, 0.5), (4.0, 0.0, 0.5)])
        half = world.result(mv, both[:1], approval=both_approval)
        assert refused(world.store_result, store, half), "a result with part of its approval's runs"
        ks = world.keys(mv, [(5.0, 0.0, 0.5), (6.0, 0.0, 0.5)])
        unfinished = world.approve(store, mv, ks)
        (made,) = [world.ok_run(ks[0], mv, unfinished)]
        store.record_call([made])
        interrupted = world.result(mv, [made], approval=unfinished)
        assert refused(world.store_result, store, interrupted), "a result whose approval's runs weren't all made"
        # An approval is used by the diagnostic evaluation that asked for it (§5.4).
        asked = world.request(seed=7)
        other_approval, others = world.made(store, mv, [(7.0, 0.0, 0.5)], req=asked)
        elsewhere = world.result(mv, others, approval=other_approval, req=world.request(seed=8))
        assert refused(world.store_result, store, elsewhere), "a result citing an approval asked for another request"
        # ... and once: a second result citing it is refused (here, the same request under other library versions).
        again = world.result(mv, old + new, approval=approval, versions={**world.VERSIONS, "numpy": "2.3.2"})
        assert again.result_id != good.result_id
        assert refused(world.store_result, store, again), "a second result citing an approval already used"


# --------------------------------------------------------------------------------------------------------------
# Broken toys: each differs from the store in one way (contracts.md, Negative controls)


class RetryOverwrites(Store):
    """Rewrites a failed run's row when its retry is stored (I1)."""

    def record_call(self, runs: Any, batch_call: Any = None) -> None:
        super().record_call(runs, batch_call)
        for run in runs:
            if run.attempt > 0:
                old = run_id(run.model_version_id, point_hash(run.point), run.replicate, run.attempt - 1)
                with self._write() as c:
                    c.execute(
                        "UPDATE runs SET reason = 'replaced by its retry' WHERE run_id = ?", (bytes.fromhex(old),)
                    )


class FirstAttemptCurrent(Store):
    """Takes the first attempt at a key as its current run (I2)."""

    def current_runs(self, model_version_id: str, point_hashes: Any) -> dict[tuple[str, int], Run]:
        found = super().current_runs(model_version_id, point_hashes)
        return {k: self.get_run(run_id(model_version_id, k[0], k[1], 0)) for k in found}


class NoKeyCheck(Store):
    """Stores a run with any id (I3)."""

    def _check_keys(self, runs: Any, batch_call: Any) -> list[str]:
        return [point_hash(r.point) for r in runs]


class SixDigits(Store):
    """Keys points by their values printed to 6 significant digits (C46's negative control)."""

    @staticmethod
    def _six(point: Any) -> tuple[float, ...]:
        return tuple(float(f"{v:.6g}") for v in point)

    def record_approval(self, *, points: Any, **kw: Any) -> str:
        points = [RunKey.make(kw["model_version_id"], self._six(k.point), k.replicate, k.attempt) for k in points]
        return super().record_approval(points=points, **kw)

    def record_call(self, runs: Any, batch_call: Any = None) -> None:
        rounded = []
        for r in runs:
            point = self._six(r.point)
            rounded.append(
                replace(r, point=point, run_id=run_id(r.model_version_id, point_hash(point), r.replicate, r.attempt))
            )
        super().record_call(rounded, batch_call)


class NoApprovalCheck(Store):
    """Stores a run under any approval (I4)."""

    def _check_approvals(self, c: Any, runs: Any, hashes: Any) -> None:
        return None


class RunByRun(Store):
    """Stores a call's runs one transaction each (I5's negative control: "one transaction per run")."""

    def record_call(self, runs: Any, batch_call: Any = None) -> None:
        for run in runs:
            super().record_call([replace(run, batch_call_id=None)])


class NoPredictionCheck(Store):
    """Stores an ok run with any set of model predictions (I6)."""

    def _check_predictions(self, c: Any, runs: Any) -> None:
        return None


class ReplacesRepeat(Store):
    """Replaces a stored result by a repeated one (I7's negative control: "recomputes")."""

    def record_result(self, result: DiagnosticResult) -> DiagnosticResult:
        if self.find_result(result.result_id) is not None:
            self.delete_result(result.result_id)
            os.makedirs(self.layout.result_dir(result.result_id))
        return super().record_result(result)


class DistinctRowsOnly(Store):
    """Writes one ``result_runs`` row per distinct run, not per design row (I8)."""

    def _result_rows(self, result: DiagnosticResult) -> Any:
        seen: set[bytes] = set()
        for row, rid in super()._result_rows(result):
            if rid not in seen:
                seen.add(rid)
                yield row, rid


class StoredOrder(Store):
    """Hands runs over in the order they were stored, not the order asked for (C56's negative control)."""

    def runs_by_id(self, run_ids: Any, *, points: bool = False) -> Any:
        stored = list(self._conn.execute("SELECT run_id FROM runs ORDER BY rowid"))
        asked = {bytes(i) for i in id_array(run_ids)}
        order = [r[0] for r in stored if r[0] in asked]
        return super().runs_by_id([o.hex() for o in order], points=points)


class LatestNoiseOnly(Store):
    """Keeps only the latest point run's record, deleting the earlier point runs' results (C52's negative control)."""

    def record_result(self, result: DiagnosticResult) -> DiagnosticResult:
        if result.measured_noisy is not None:
            for earlier in self.measured_noisy(result.model_version_id, result.prediction):
                self.delete_result(earlier.result_id)
        return super().record_result(result)


class FifteenDigits(Store):
    """Writes model predictions to 15 significant digits (I11)."""

    def record_call(self, runs: Any, batch_call: Any = None) -> None:
        def cut(v: float | None) -> float | None:
            return None if v is None else float(f"{v:.15g}")

        super().record_call(
            [replace(r, predictions={k: cut(v) for k, v in r.predictions.items()}) for r in runs], batch_call
        )


class NoNewRunsCheck(Store):
    """Stores a result whatever its new runs and approval (I12)."""

    def _check_result_runs(self, c: Any, result: DiagnosticResult) -> None:
        return None


class CountsOnly(Store):
    """Checks only that a result's counted new runs are its runs under its approval, not all of the approval's (I12)."""

    def _check_new_runs(self, c: Any, result: DiagnosticResult, own: Any, priced: Any, new: int) -> None:
        super()._check_new_runs(c, result, None, None, new)


class AnyRequestsApproval(Store):
    """Takes an approval asked for any request (§5.4)."""

    def _check_approval_request(self, result: DiagnosticResult, request: str) -> None:
        return None


class ApprovalUsedTwice(Store):
    """Lets several results cite one approval (§5.4: an approval is used once)."""

    def _check_approval_unused(self, c: Any, result: DiagnosticResult, own: bytes) -> None:
        return None


class NoiseFromAnyResult(Store):
    """Stores a measured-noisy record with any diagnostic's result (I10)."""

    def _check_noisy(self, result: DiagnosticResult) -> None:
        return None


BROKEN: dict[str, list[type[Store]]] = {
    "check_append_only": [RetryOverwrites],
    "check_retry_beside_failed": [FirstAttemptCurrent],
    "check_run_keys": [NoKeyCheck],
    "check_reuse": [SixDigits],
    "check_approval_cap": [NoApprovalCheck],
    "check_interrupt": [RunByRun],
    "check_prediction_rows": [NoPredictionCheck],
    "check_repeat": [ReplacesRepeat],
    "check_provenance": [DistinctRowsOnly],
    "check_design_order": [StoredOrder],
    "check_measured_noisy": [LatestNoiseOnly, NoiseFromAnyResult],
    "check_round_trip": [FifteenDigits],
    "check_new_runs": [NoNewRunsCheck, CountsOnly, AnyRequestsApproval, ApprovalUsedTwice],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=[Store], ids=lambda c: c.__name__)
def store_class(request: pytest.FixtureRequest) -> type[Store]:
    return request.param


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)


def test_every_invariant_has_a_check() -> None:
    """data_model.md §9 names a check for each of I1–I12; C46 has its own (contracts.md)."""
    named = {
        "check_append_only", "check_retry_beside_failed", "check_run_keys", "check_approval_cap", "check_interrupt",
        "check_prediction_rows", "check_repeat", "check_provenance", "check_design_order", "check_measured_noisy",
        "check_round_trip", "check_new_runs", "check_reuse",
    }  # fmt: skip
    assert set(CHECKS) == named
