"""The runner's parts of the store contract and of the model adapter contract (contracts.md; architecture.md §9).

The store contract runs "with the runner and millisecond models for C47–C49 (the cap counted at a call's start, an
interrupt)": here are the runner's parts of C46–C49 and C56. Record 0071 left the model adapter contract's C34 (a
call refused when a file changed), C37 (calls sized to ``batch_size`` and to what remains approved), and C41 (``keep``
applied, and a stopped run) to be finished through ``run_new``: here too.

The implementation is ``ema.runner``'s functions, bundled as a ``Runner``. Each check has broken toys, each a
``Runner`` that differs from the real one in one way; a broken ``run_new`` is a subclass of the runner's loop
(``ema.runner._Loop``) that changes one step (no monkeypatching, 0065). ``test_every_check_fails_on_its_broken_toy``
is the meta-test. The checks that run a model use the Python toy, or the batch toy for C37 (``tests/models``), which
log each point they are called at, so a call refused before it starts is seen never to reach the model. The checks
over the Python toy for C46–C49 and C56 are the fast tier's; C34's, C37's, and C41's checks, the command-line
variants, and the meta-test of the checks that run a model are the slow tier's (record 0074).
"""

from __future__ import annotations

import inspect
import os
import signal
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pytest

from ema import runner
from ema.runner import _Loop
from ema.types.errors import ModelChanged
from ema.types.identity import point_hash, run_id
from ema.types.runs import FailureKind, Run, RunKey, RunStatus
from tests.support import store as world
from tests.support.models import point
from tests.support.runner import design, opened_world, row_run_ids, workbench

#: Seconds from a call's start to Ctrl-C in the checks that stop a call (the toy's hang sleeps 60 s).
INTERRUPT_S = 0.1


@contextmanager
def ctrl_c_after(done: int) -> Iterator[Callable[[Any], None]]:
    """Yield an ``on_progress`` that presses Ctrl-C ``INTERRUPT_S`` after the progress reaches ``done`` runs, that is
    during the next call, with Python's own handler (started from the progress, so a loaded machine can't move it
    into an earlier call)."""
    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    timers: list[threading.Timer] = []

    def on_progress(progress: Any) -> None:
        if progress.done == done and not timers:
            timers.append(threading.Timer(INTERRUPT_S, os.kill, (os.getpid(), signal.SIGINT)))
            timers[0].start()

    try:
        yield on_progress
    finally:
        for timer in timers:
            timer.cancel()
        signal.signal(signal.SIGINT, previous)


def loop_runner(loop: type[_Loop]) -> Callable[..., int]:
    """``run_new`` with another loop."""

    def run_new(model: Any, resolution: Any, approval_id: str, store: Any, processes: Any, *,
                on_progress: Any = None) -> int:  # fmt: skip
        return loop(model, resolution, approval_id, store, processes, on_progress).run()

    return run_new


@dataclass(frozen=True)
class Runner:
    """The runner's functions; a broken toy replaces one. ``kind`` is the toy a check over a model runs."""

    kind: str = "python"
    resolve: Callable[..., Any] = runner.resolve
    price: Callable[..., Any] = runner.price
    run_new: Callable[..., int] = runner.run_new
    read_batch: Callable[..., Any] = runner.read_batch


def refused(fn: Callable[[], Any], error: type[BaseException] = ValueError) -> bool:
    """Tell whether ``fn`` raises ``error`` (``run_new`` refuses a call its approval doesn't cover: ValueError)."""
    try:
        fn()
    except error:
        return True
    return False


def interrupted(fn: Callable[[], Any]) -> bool:
    """Tell whether ``fn`` ends with ``KeyboardInterrupt``."""
    return refused(fn, KeyboardInterrupt)


# --------------------------------------------------------------------------------------------------------------
# The checks over stored runs (no model runs)


def check_reuse(impl: Runner) -> None:
    """C46 (P3, P7; I2, I3): a design row's key is its model version, its exact point, and its replicate; a stored
    run there is reused; a key repeated in the design is one new run; another replicate, or a point that differs in
    any bit (the 7th digit, or -0.0 for 0.0), is a new key."""
    with opened_world() as (store, model):
        mv = model.model_version_id
        p1, p2 = (1.0, 0.0, 0.5), (2.0, 1.0, 0.5)
        _, (r1, r2) = world.made(store, mv, [p1, p2])
        near, signed = (1.0000001, 0.0, 0.5), (1.0, -0.0, 0.5)
        rows = [p1, near, p1, p2, p1, signed, near]
        reps = [0, 0, 0, 0, 1, 0, 0]
        res = impl.resolve(design(rows, reps), model, store, retry_failed=False)
        assert res.model_version_id == mv
        stored = [r1.run_id, None, r1.run_id, r2.run_id, None, None, None]
        for row, expected in enumerate(stored):
            if expected is None:
                assert res.row_keys[row] >= 0, f"row {row} should be new"
            else:
                assert res.row_keys[row] == -1 and bytes(res.row_runs[row]).hex() == expected, f"row {row} not reused"
        expected_keys = [RunKey.make(mv, near, 0, 0), RunKey.make(mv, p1, 1, 0), RunKey.make(mv, signed, 0, 0)]
        assert list(res.new_keys) == expected_keys, res.new_keys
        assert res.row_keys[1] == res.row_keys[6], "a key repeated in the design isn't one new run"
        assert res.reused_failed == 0
        price = impl.price(res, store)
        assert (price.new, price.reused) == (3, 2), price


def check_failed_reused(impl: Runner) -> None:
    """C47 (0010; I2): a failed run is reused unless retry is asked, and the price counts it ("of which 1 failed");
    with retry, exactly the failed points are new, each as the next attempt beside the run it replaces."""
    with opened_world() as (store, model):
        mv = model.model_version_id
        p1, p2, p3 = (1.0, 0.0, 0.5), (2.0, 0.0, 0.5), (3.0, 0.0, 0.5)
        k1, k2, k3 = world.keys(mv, [p1, p2, p3])
        approval = world.approve(store, mv, [k1, k2, k3])
        world.record_runs(store, [world.ok_run(k1, mv, approval), world.failed_run(k2, mv, approval)])
        world.record_runs(store, [world.failed_run(k3, mv, approval)])
        retry = RunKey.make(mv, p3, 0, 1)
        world.record_runs(store, [world.ok_run(retry, mv, world.approve(store, mv, [retry]))])
        rows = design([p1, p2, p3, p2])
        kept = impl.resolve(rows, model, store, retry_failed=False)
        assert not kept.new_keys and kept.reused_failed == 1, (kept.new_keys, kept.reused_failed)
        assert bytes(kept.row_runs[2]).hex() == retry.run_id, "the current run at a key isn't its last attempt"
        price = impl.price(kept, store)
        assert (price.new, price.reused, price.reused_failed) == (0, 3, 1)
        assert "3 reused, of which 1 failed" in price.text, price.text
        again = impl.resolve(rows, model, store, retry_failed=True)
        assert list(again.new_keys) == [RunKey.make(mv, p2, 0, 1)], again.new_keys
        assert again.new_keys[0].run_id == run_id(mv, point_hash(p2), 0, 1)
        assert again.reused_failed == 0 and list(again.row_keys) == [-1, 0, -1, 0]


def check_design_order(impl: Runner) -> None:
    """C56 (0015, P4; I9): the batch is in the design's order, whatever order its runs were made in, a repeated row
    repeated; a row is new exactly when its run's approval is the new one (E6)."""
    with opened_world() as (store, model):
        mv = model.model_version_id
        p1, p2, p3 = (1.0, 0.0, 0.5), (2.0, 0.0, 0.5), (3.0, 0.0, 0.5)
        _, (r3,) = world.made(store, mv, [p3])
        _, (r1,) = world.made(store, mv, [p1])
        a2, (r2,) = world.made(store, mv, [p2])
        rows = design([p1, p2, p3, p1])
        res = impl.resolve(rows, model, store, retry_failed=False)
        batch = impl.read_batch(rows, row_run_ids(res), store, new_approval=a2)
        order = [r1.run_id, r2.run_id, r3.run_id, r1.run_id]
        assert [bytes(i).hex() for i in batch.runs.run_ids] == order, "the batch isn't in the design's order"
        assert list(batch.new) == [False, True, False, False]
        assert list(batch.runs.values["y"]) == [r.predictions["y"] for r in (r1, r2, r3, r1)]
        assert not impl.read_batch(rows, row_run_ids(res), store, new_approval=None).new.any()


# --------------------------------------------------------------------------------------------------------------
# The checks over a model (millisecond toys)


def check_approval_cap(impl: Runner) -> None:
    """C48 (P3, 0015, M8; I4): no more new runs than approved, counted when a call starts, so a call the approval
    doesn't cover never starts; with k of n points stored the price says n - k new, and n - k runs are made; with no
    stored runs the time is unknown; a design in another model parameter space reuses the runs at shared points."""
    with workbench() as w:
        model = w.model(impl.kind)
        points = [point(0, a=float(i)) for i in range(5)]
        first = impl.resolve(design(points[:2]), model, w.store, retry_failed=False)
        price = impl.price(first, w.store)
        assert (price.new, price.time_s, price.from_runs) == (2, None, 0) and "time unknown" in price.text, price
        assert impl.run_new(model, first, w.approve(first), w.store, w.processes) == 2
        res = impl.resolve(design(points), model, w.store, retry_failed=False)
        price = impl.price(res, w.store)
        assert (price.new, price.reused, price.from_runs) == (3, 2, 2) and price.time_s is not None, price
        partial = w.approve(res, res.new_keys[:2])
        assert refused(lambda: impl.run_new(model, res, partial, w.store, w.processes)), "an uncovered key was run"
        assert w.calls() == points[:4], f"the model was called outside its approval: {w.calls()}"
        assert len(w.stored(model, points)) == 4
        assert not w.run_dir(res.new_keys[2].run_id).exists()
        other = design([points[1], point(0, a=7.5)])
        shared = impl.resolve(other, model, w.store, retry_failed=False)
        assert list(shared.row_keys) == [-1, 0] and len(shared.new_keys) == 1


def check_run_once(impl: Runner) -> None:
    """C46, C48 (P3; I2, I4; M14): a key's run is made once. A stale resolution, whose keys were run since under
    another approval that covers them too, is refused before its call starts (Q13 counts only its own approval's
    runs): the model isn't called again, and the stored runs keep their directories."""
    with workbench() as w:
        model = w.model(impl.kind, lambda s: s.update(keep="all"))
        points = [point(0, a=1.0), point(0, a=2.0)]
        stale = impl.resolve(design(points), model, w.store, retry_failed=False)
        first, second = w.approve(stale), w.approve(stale)
        assert impl.run_new(model, stale, first, w.store, w.processes) == 2
        made = {key: run.run_id for key, run in w.stored(model, points).items()}
        assert refused(lambda: impl.run_new(model, stale, second, w.store, w.processes)), "a key was run twice"
        assert w.calls() == points, f"the model was called again at a key already run: {w.calls()}"
        assert {key: run.run_id for key, run in w.stored(model, points).items()} == made
        for run_id in made.values():
            assert (w.run_dir(run_id) / "run.json").is_file(), "a stored run's directory was deleted"


def check_interrupt(impl: Runner) -> None:
    """C49 (0015, 0028, 0051; I1, I5): Ctrl-C between calls keeps every finished run, and a rerun makes only the
    others; Ctrl-C during a call kills it, stores no record of the run stopped partway, and keeps the finished ones."""
    with workbench() as w:
        model = w.model(impl.kind)
        points = [point(0, a=float(i)) for i in range(4)]
        res = impl.resolve(design(points), model, w.store, retry_failed=False)

        def stop_after_two(progress: Any) -> None:
            if progress.done >= 2:
                raise KeyboardInterrupt

        approval = w.approve(res)
        stopped = interrupted(lambda: impl.run_new(model, res, approval, w.store, w.processes,
                                                   on_progress=stop_after_two))  # fmt: skip
        assert stopped, "Ctrl-C between calls didn't stop the evaluation"
        assert set(w.stored(model, points)) == {(point_hash(p), 0) for p in points[:2]}, "finished runs weren't kept"
        rerun = impl.resolve(design(points), model, w.store, retry_failed=False)
        assert len(rerun.new_keys) == 2
        assert impl.run_new(model, rerun, w.approve(rerun), w.store, w.processes) == 2
        assert w.calls() == points, "a finished run was made again"
        hang = point(3, a=9.0)
        res = impl.resolve(design([point(0, a=8.0), hang]), model, w.store, retry_failed=False)
        approval = w.approve(res)
        with ctrl_c_after(1) as press:
            stopped = interrupted(lambda: impl.run_new(model, res, approval, w.store, w.processes, on_progress=press))
        assert stopped, "Ctrl-C during a call didn't stop it"
        assert list(w.stored(model, [hang])) == [], "a run stopped partway was stored"
        assert len(w.stored(model, [point(0, a=8.0)])) == 1, "the finished run before it wasn't kept"


def check_refused_call(impl: Runner) -> None:
    """C34 (M16, U6): the tracked files are hashed again before every call; after an edit the next call is refused,
    naming the file, and the runs already made are kept, with their directories."""
    with workbench() as w:
        model = w.model(impl.kind)
        points = [point(0, a=float(i)) for i in range(3)]
        res = impl.resolve(design(points), model, w.store, retry_failed=False)
        tracked = "solver.py" if impl.kind == "command_line" else "model.py"
        source = w.copies[impl.kind].parent / tracked

        def edit_after_one(progress: Any) -> None:
            if progress.done == 1:
                source.write_text(source.read_text() + "\n")

        approval = w.approve(res)
        try:
            impl.run_new(model, res, approval, w.store, w.processes, on_progress=edit_after_one)
        except ModelChanged as e:
            assert tracked in str(e), str(e)
        else:
            raise AssertionError("a call after an edit wasn't refused")
        assert w.calls() == points[:1], f"a call ran after the edit: {w.calls()}"
        (made,) = w.stored(model, points).values()
        assert (w.run_dir(made.run_id) / "run.json").is_file(), "the run already made wasn't kept"
        assert not w.run_dir(res.new_keys[1].run_id).exists()


def check_batch_sizes(impl: Runner) -> None:
    """C37 (M8, 0025): no call holds more than ``batch_size`` points, or more than remain approved (``batch_size``
    3 over 10 points, 7 approved: calls of 3, 3, and 1, then the refusal before the eighth point)."""
    with workbench() as w:
        model = w.model("batch")
        assert model.spec.batch_size == 3
        points = [point(0, a=float(i)) for i in range(10)]
        res = impl.resolve(design(points), model, w.store, retry_failed=False)
        approval = w.approve(res, res.new_keys[:7])
        assert refused(lambda: impl.run_new(model, res, approval, w.store, w.processes)), "an uncovered key was run"
        assert w.calls() == points[:7], f"the model was called outside its approval: {w.calls()}"
        runs = w.stored(model, points)
        sizes = [w.store.batch_call(runs[(point_hash(p), 0)].batch_call_id).size for p in points[:7]]
        assert sizes == [3, 3, 3, 3, 3, 3, 1], sizes
        rest = impl.resolve(design(points), model, w.store, retry_failed=False)
        assert impl.run_new(model, rest, w.approve(rest), w.store, w.processes) == 3
        assert w.calls() == points


def check_keep_applied(impl: Runner) -> None:
    """C41 (M14, 0020, 0028): ``run_new`` applies ``keep`` after storing a call's runs (``incomplete``: a complete
    run's directory deleted, a run with a model prediction missing kept), and a stopped call leaves no directory."""
    with workbench() as w:
        model = w.model(impl.kind, lambda s: s.update(keep="incomplete"))
        complete, incomplete = point(0), point(9, a=2.0)
        res = impl.resolve(design([complete, incomplete]), model, w.store, retry_failed=False)
        assert impl.run_new(model, res, w.approve(res), w.store, w.processes) == 2
        runs = w.stored(model, [complete, incomplete])
        assert not w.run_dir(runs[(point_hash(complete), 0)].run_id).exists(), "a complete run's directory was kept"
        assert w.run_dir(runs[(point_hash(incomplete), 0)].run_id).exists(), "an incomplete run's directory was deleted"
        res = impl.resolve(design([point(3, a=4.0)]), model, w.store, retry_failed=False)
        approval = w.approve(res)
        with ctrl_c_after(0) as press:
            assert interrupted(lambda: impl.run_new(model, res, approval, w.store, w.processes, on_progress=press))
        assert not w.run_dir(res.new_keys[0].run_id).exists(), "a stopped run's directory was kept"


# --------------------------------------------------------------------------------------------------------------
# Broken toys


def resolve_six_digits(dsg: Any, model: Any, store: Any, *, retry_failed: bool) -> Any:
    """Keys points by their values printed to 6 significant digits (C46's negative control)."""
    rounded = np.vectorize(lambda v: float(f"{v:.6g}"))(np.asarray(dsg.points))
    return runner.resolve(replace(dsg, points=rounded), model, store, retry_failed=retry_failed)


def resolve_always_retrying(dsg: Any, model: Any, store: Any, *, retry_failed: bool) -> Any:
    """Retries failed runs without being asked (C47's negative control)."""
    return runner.resolve(dsg, model, store, retry_failed=True)


def read_batch_sorted(dsg: Any, run_ids: Any, store: Any, *, new_approval: Any) -> Any:
    """Hands runs over in another order than the design's: by run id, as a set of runs would (C56's control)."""
    return runner.read_batch(dsg, np.sort(np.asarray(run_ids)), store, new_approval=new_approval)


class CountsAtFinish(_Loop):
    """Counts runs when they finish: no Q13 before a call, only W4's check after it (C48's negative control)."""

    def next_call(self, pending: tuple[RunKey, ...]) -> tuple[RunKey, ...]:
        return pending[: self.size]


class AsksQ13Only(_Loop):
    """Asks Q13 only, which counts this approval's runs, not whether a key was run under another (I4's control)."""

    def next_call(self, pending: tuple[RunKey, ...]) -> tuple[RunKey, ...]:
        candidate = pending[: self.size]
        coverage = self.store.approval_coverage(self.approval_id, candidate)
        covered = next((i for i, c in enumerate(coverage.covered) if not c), len(candidate))
        if not covered:
            raise ValueError("not covered")
        return candidate[:covered]


class FillsLastBatch(_Loop):
    """Fills the last batch past the approved count: Q13 asked of a call's first key only (C37's control)."""

    def next_call(self, pending: tuple[RunKey, ...]) -> tuple[RunKey, ...]:
        super().next_call(pending[:1])
        return pending[: self.size]


class OneTransaction(_Loop):
    """Stores the runs once, at the end of the evaluation (C49's negative control)."""

    def run(self) -> int:
        self.held: list[tuple[Any, Any]] = []
        made = super().run()
        for runs, executed in self.held:
            super().record(runs, executed)
        return made

    def record(self, runs: Any, executed: Any) -> None:
        self.held.append((runs, executed))


class StoresStopped(_Loop):
    """Stores the stopped run as failed (C49's negative control)."""

    def stopped(self, keys: Any, prepared: Any) -> None:
        if sys.exc_info()[0] is KeyboardInterrupt:
            mv = self.model.model_version_id
            self.store.record_call([Run(k.run_id, mv, k.point, k.replicate, k.attempt, RunStatus.FAILED,
                                        FailureKind.ERROR, "stopped", None, None, {}, {}, 0.0, None, "host", "python",
                                        self.approval_id) for k in keys[:1]])  # fmt: skip
        super().stopped(keys, prepared)


class ChecksOnce(_Loop):
    """Hashes the files once, before the first call (C34's negative control)."""

    def check(self) -> None:
        if not getattr(self, "checked", False):
            self.checked = True
            super().check()


class KeepsAll(_Loop):
    """Applies no ``keep`` setting (C41's negative control)."""

    def keep(self, prepared: Any, runs: Any) -> None:
        pass


class DiscardsNothing(_Loop):
    """Keeps a stopped run's directory (C41's negative control)."""

    def stopped(self, keys: Any, prepared: Any) -> None:
        pass


BROKEN: dict[str, list[Runner]] = {
    "check_reuse": [Runner(resolve=resolve_six_digits)],
    "check_failed_reused": [Runner(resolve=resolve_always_retrying)],
    "check_design_order": [Runner(read_batch=read_batch_sorted)],
    "check_approval_cap": [Runner(run_new=loop_runner(CountsAtFinish))],
    "check_run_once": [Runner(run_new=loop_runner(AsksQ13Only))],
    "check_interrupt": [Runner(run_new=loop_runner(OneTransaction)), Runner(run_new=loop_runner(StoresStopped))],
    "check_refused_call": [Runner(run_new=loop_runner(ChecksOnce))],
    "check_batch_sizes": [Runner(run_new=loop_runner(FillsLastBatch))],
    "check_keep_applied": [Runner(run_new=loop_runner(KeepsAll)), Runner(run_new=loop_runner(DiscardsNothing))],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}

#: The checks that run no model: over the Python kind only, as their runs are made by hand.
STORED_ONLY = ("check_reuse", "check_failed_reused", "check_design_order")
#: The toys each check over a model runs (C37 is the batch model's); the command-line variants are slow.
RUN_OVER = {"check_batch_sizes": ("batch",)}
#: The fast tier's checks over a model (contracts.md, Test tiers: 30 s); the rest are slow (record 0074).
FAST = ("check_approval_cap", "check_interrupt", "check_run_once")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "impl" in metafunc.fixturenames:
        name = metafunc.function.__name__
        kinds = ("python",) if name in STORED_ONLY else RUN_OVER.get(name, ("python", "command_line"))
        fast = name in STORED_ONLY or name in FAST
        params = [pytest.param(Runner(kind=k), id=k, marks=[] if fast and k == "python" else [pytest.mark.slow])
                  for k in kinds]  # fmt: skip
        metafunc.parametrize("impl", params)


@pytest.mark.parametrize(
    "check", [pytest.param(c, marks=[] if c in STORED_ONLY else [pytest.mark.slow]) for c in sorted(CHECKS)]
)
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)
