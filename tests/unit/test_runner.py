"""``ema.runner`` beyond its contract (tests/contracts/runner.py): resolve's refusals, price's text, run_new's
refusals and progress, read_batch and replay_batch (architecture.md §6; data_model.md Q1, Q2, Q13, Q15; P3; 0063)."""

from dataclasses import replace

import numpy as np
import pytest

from ema.runner import price, read_batch, replay_batch, resolve, run_new
from ema.types.design import DesignStructure
from ema.types.identity import id_array
from ema.types.requests import Progress
from ema.types.runs import Resolution
from tests.support import store as world
from tests.support.models import point
from tests.support.runner import design, opened_world, row_run_ids, workbench


def test_resolve_refuses_another_model_version_and_a_wrong_width():
    with opened_world() as (store, model):
        with pytest.raises(ValueError, match="3 values, not 2"):
            resolve(design([(1.0, 2.0)]), model, store, retry_failed=False)
        identity = world.identity("ab" * 32)
        other = replace(design([(1.0, 2.0, 3.0)]), identity=identity)
        with pytest.raises(ValueError, match="model version"):
            resolve(other, model, store, retry_failed=False)


def test_resolve_an_empty_design_and_a_new_model_version():
    with opened_world() as (store, model):
        empty = resolve(design(np.zeros((0, 3))), model, store, retry_failed=False)
        assert empty.new_keys == () and len(empty.row_runs) == 0
        res = resolve(design([(1.0, 2.0, 3.0), (1.0, 2.0, 3.0)]), model, store, retry_failed=False)
        assert len(res.new_keys) == 1 and list(res.row_keys) == [0, 0]
        p = price(res, store)
        assert p.text == "1 new run, 0 reused, time unknown"


def test_price_estimates_from_the_stored_runs_mean():
    """Q2: new × the mean of every stored run of the model version, any status (U2's price)."""
    with opened_world() as (store, model):
        mv = model.model_version_id
        world.made(store, mv, [(1.0, 0.0, 0.5)])  # time_s 0.25
        res = resolve(design([(1.0, 0.0, 0.5)] + [(float(i), 1.0, 0.5) for i in range(8)]), model, store,
                      retry_failed=False)  # fmt: skip
        p = price(res, store)
        assert (p.new, p.reused, p.time_s, p.from_runs) == (8, 1, 2.0, 1)
        assert p.text == "8 new runs, 1 reused, about 2 s (from 1 stored run)"


def test_read_batch_refuses_a_row_count_that_isnt_the_designs():
    with opened_world() as (store, model):
        _, runs = world.made(store, model.model_version_id, [(1.0, 0.0, 0.5)])
        with pytest.raises(ValueError, match="one run id per design row"):
            read_batch(design([(1.0, 0.0, 0.5)] * 2), world.ids(runs), store, new_approval=None)


def test_replay_batch_builds_the_design_from_the_stored_points():
    """U8, 0062, 0063: the provenance's run ids in its order, the points from the store, the structure from it."""
    with opened_world() as (store, model):
        mv = model.model_version_id
        approval, runs = world.made(store, mv, [(1.0, 0.0, 0.5), (2.0, 0.0, 0.5)])
        rows = [runs[1], runs[0], runs[1]]
        res = world.result(mv, rows, approval=approval)
        structure = DesignStructure(levels=(1, 3), lines=None)
        provenance = replace(res.provenance, design_structure=structure)
        batch = replay_batch(provenance, store)
        assert np.array_equal(batch.design.points, [[2.0, 0.0, 0.5], [1.0, 0.0, 0.5], [2.0, 0.0, 0.5]])
        assert batch.design.identity == provenance.design and batch.design.levels == (1, 3)
        assert list(batch.new) == [True, True, True]
        assert np.array_equal(batch.runs.run_ids, id_array([r.run_id for r in rows]))
        none = replay_batch(replace(provenance, approval_id=None), store)
        assert not none.new.any()


def test_run_new_refuses_a_declined_approval_and_another_model_version():
    """P3: Q13 before the first call; nothing starts."""
    with workbench() as w:
        model = w.model()
        res = resolve(design([point(0)]), model, w.store, retry_failed=False)
        declined = w.approve(res, answer=False)
        with pytest.raises(ValueError, match="answered no"):
            run_new(model, res, declined, w.store, w.processes)
        other = w.model(edit=lambda s: s.update(description="another"), name="other")
        foreign = resolve(design([point(0)]), other, w.store, retry_failed=False)
        approval = w.approve(foreign)
        with pytest.raises(ValueError, match="model version"):
            run_new(model, replace_mv(res, other.model_version_id), approval, w.store, w.processes)
        with pytest.raises(ValueError, match="model version"):
            run_new(model, res, approval, w.store, w.processes)  # an approval of another model version
        assert w.calls() == []


def replace_mv(res: Resolution, mv: str) -> Resolution:
    return Resolution(res.design, mv, res.row_runs, res.row_keys, res.new_keys, res.reused_failed)


def test_run_new_reports_progress_and_keeps_runs_when_the_callback_raises():
    """PM10, C49: "0/n runs" first, then after each call; an exception from the callback keeps the runs made."""
    with workbench() as w:
        model = w.model()
        res = resolve(design([point(0, a=float(i)) for i in range(3)]), model, w.store, retry_failed=False)
        approval = w.approve(res)
        seen: list[Progress] = []
        assert run_new(model, res, approval, w.store, w.processes, on_progress=seen.append) == 3
        assert [p.text for p in seen] == ["0/3 runs", "1/3 runs", "2/3 runs", "3/3 runs"]
        assert run_new(model, resolve(res.design, model, w.store, retry_failed=False), approval, w.store,
                       w.processes) == 0  # fmt: skip

        def fail(progress: Progress) -> None:
            if progress.done == 1:
                raise RuntimeError("the callback failed")

        more = resolve(design([point(0, a=10.0 + i) for i in range(3)]), model, w.store, retry_failed=False)
        with pytest.raises(RuntimeError):
            run_new(model, more, w.approve(more), w.store, w.processes, on_progress=fail)
        assert len(w.stored(model, [point(0, a=10.0 + i) for i in range(3)])) == 1


@pytest.mark.slow
def test_a_batch_call_is_stored_with_its_batch_call_and_read_in_design_order():
    """W4 with a batch call (0025); C56 through read_batch after run_new."""
    with workbench() as w:
        model = w.model("batch", lambda s: s.update(batch_size=None))
        points = [point(0, a=float(i)) for i in range(4)]
        rows = design([points[2], points[0], points[1], points[3], points[0]])
        res = resolve(rows, model, w.store, retry_failed=False)
        approval = w.approve(res)
        assert run_new(model, res, approval, w.store, w.processes) == 4
        batch = read_batch(rows, row_run_ids(res), w.store, new_approval=approval)
        assert list(batch.runs.values["y"]) == [p[0] + 2 * p[1] for p in rows.points]
        assert batch.new.all()
        (call,) = {w.store.get_run(batch.run_id(i)).batch_call_id for i in range(len(rows))}
        assert w.store.batch_call(call).size == 4
