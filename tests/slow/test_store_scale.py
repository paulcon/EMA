"""The store across its real chunk boundaries (slow tier; data_model.md §6, §8: Q1, Q6, Q7, Q15 read in chunks of
30,000 rows).

70,001 runs (two whole chunks and a remainder) are stored as batch calls; each chunked read must return every row,
in the order asked for. Correctness only: §6's timing target (Q1 on 10⁶ points in under 10 s) is deferred by record
0072, with the measured times in plan 06's Notes.
"""

import numpy as np
import pytest

from ema.store import CHUNK_ROWS, Store
from ema.types.identity import point_hash
from tests.support import store as world

N = 2 * CHUNK_ROWS + 10_001


@pytest.mark.slow
def test_chunked_reads_return_every_row_in_order(tmp_path):
    rng = np.random.default_rng(6)
    with Store.open(str(tmp_path)) as store:
        mv = world.load(store)
        points = rng.random((N, 3)).tolist()
        ks = world.keys(mv, points)
        approval = world.approve(store, mv, ks)
        runs = [world.ok_run(k, mv, approval, y=float(i)) for i, k in enumerate(ks)]
        for start in range(0, N, 10_000):
            world.record_batch(store, runs[start : start + 10_000])
        current = store.current_runs(mv, [point_hash(p) for p in points])
        assert len(current) == N
        assert all(current[(k.point_hash, 0)].run_id == k.run_id for k in ks[::997])
        order = rng.permutation(N)
        asked = world.ids([runs[i] for i in order])
        columns = store.runs_by_id(asked, points=True)
        assert np.array_equal(columns.run_ids, asked)
        assert np.array_equal(columns.values["y"], order.astype(np.float64))
        assert np.array_equal(columns.points, np.array(points)[order])
        res = world.store_result(store, world.result(mv, [runs[i] for i in order], approval=approval))
        assert np.array_equal(store.get_result(res.result_id).provenance.run_ids, asked)
        design_order = store.result_runs(res.result_id)
        assert np.array_equal(design_order.run_ids, asked)
        assert np.array_equal(design_order.values["y"], order.astype(np.float64))
