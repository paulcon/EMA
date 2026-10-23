"""Several processes writing the same diagnostic result at once (data_model.md §6, W5; I7; record 0056; review round 1,
M1): each gets the one stored result, and no temporary directory is left in ``results/``.

The workers are started once, with "spawn" (as the runner starts processes; the run lock's fork caveat), and meet at
a barrier before each trial, so their result directories and W5s overlap.
"""

import multiprocessing
import os
from typing import Any

from ema.store import Store
from tests.support import store as world

WORKERS = 4
TRIALS = 12


def _worker(trials: list[tuple[str, list[str], str]], barrier: Any, out: Any) -> None:
    """Write each trial's result: its directory (a report and some data cards), then W5; report what W5 returned."""
    for trial, (root, run_ids, approval) in enumerate(trials):
        try:
            with Store.open(root, create=False) as store:
                runs = [store.get_run(r) for r in run_ids]
                res = world.result(runs[0].model_version_id, runs, approval=approval)
                barrier.wait()
                with store.result_directory(res.result_id) as directory:
                    world.write_report(directory, "# Scatter\n" + "x" * 10_000)
                    for i in range(20):
                        with open(os.path.join(directory, f"card{i}.json"), "w", encoding="utf-8") as f:
                            f.write("{}\n" * 200)
                stored = store.record_result(res)
                out.put((trial, "ok", stored.result_id, stored.to_json() == res.to_json()))
        except Exception as error:  # noqa: BLE001 -- any error is reported to the test, which fails on it
            out.put((trial, "error", f"{type(error).__name__}: {error}", False))


def test_processes_writing_one_result_at_once_all_get_the_stored_one(tmp_path):
    trials, expected = [], []
    for trial in range(TRIALS):
        root = str(tmp_path / f"ws{trial}")
        with Store.open(root) as store:
            mv = world.load(store)
            approval, runs = world.made(store, mv, [(0.0, 0.0, 0.5), (1.0, 0.0, 0.5)])
            if trial % 2:  # a leftover directory, with no row, in place before the race
                os.makedirs(
                    os.path.join(store.layout.result_dir(world.result(mv, runs, approval=approval).result_id), "old")
                )
        trials.append((root, [r.run_id for r in runs], approval))
        expected.append(world.result(mv, runs, approval=approval).result_id)

    ctx = multiprocessing.get_context("spawn")
    barrier, out = ctx.Barrier(WORKERS), ctx.Queue()
    workers = [ctx.Process(target=_worker, args=(trials, barrier, out)) for _ in range(WORKERS)]
    for w in workers:
        w.start()
    reports = [out.get(timeout=120) for _ in range(WORKERS * TRIALS)]
    for w in workers:
        w.join(timeout=60)

    errors = [r for r in reports if r[1] != "ok"]
    assert not errors, f"{len(errors)} of {len(reports)} writes failed, such as {errors[0]}"
    for trial, rid in enumerate(expected):
        got = [r for r in reports if r[0] == trial]
        assert len(got) == WORKERS and all(r[2] == rid and r[3] for r in got), "a writer got another result"
        root = trials[trial][0]
        assert os.listdir(os.path.join(root, "results")) == [rid], "a temporary or leftover directory was left"
        assert sorted(os.listdir(os.path.join(root, "results", rid))) == sorted(
            ["report.md"] + [f"card{i}.json" for i in range(20)]
        )
        with Store.open(root, create=False) as store:
            assert [s.result_id for s in store.list_results()] == [rid]
