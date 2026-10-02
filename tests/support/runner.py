"""A workbench for the runner's and approval's tests (step 07): a fresh workspace's store, copies of the toys in
``tests/models`` loaded and recorded there (W1), the workspace's children, and the log of the points each toy was
called at (``TOY_CALLS``, ``tests.support.models``).

Approvals are recorded directly (W3) here, so a test can approve fewer keys than a resolution holds; ``ema.approval``
has its own tests.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ema.models.processes import ModelProcesses
from ema.models.spec import LoadedModel, load_spec
from ema.store import Store
from ema.types.design import Design
from ema.types.identity import point_hash
from ema.types.runs import Price, Resolution, Run, RunKey
from tests.support import store as world
from tests.support.models import copy_model


def design(points: Sequence[Sequence[float]], replicates: Sequence[int] | None = None) -> Design:
    """A design with no identity (as the test run's) of these complete points."""
    reps = np.zeros(len(points), dtype=np.int64) if replicates is None else np.asarray(replicates, dtype=np.int64)
    array = np.asarray(points, dtype=np.float64)
    return Design(None, array.reshape(len(points), -1) if array.size else np.zeros((0, 3)), reps, None, None)


def row_run_ids(resolution: Resolution) -> np.ndarray:
    """Each design row's run id: the stored run's, or its new key's (what the workspace builds, architecture.md §6)."""
    ids = resolution.row_runs.copy()
    for row in np.flatnonzero(resolution.row_keys >= 0):
        ids[row] = bytes.fromhex(resolution.new_keys[resolution.row_keys[row]].run_id)
    return ids


@dataclass
class Workbench:
    """A temporary workspace with its store and children; the toys are copied under ``root``."""

    root: Path
    store: Store
    processes: ModelProcesses
    log: Path
    copies: dict[str, Path] = field(default_factory=dict)

    def model(
        self, kind: str = "python", edit: Callable[[dict[str, Any]], None] | None = None, name: str | None = None
    ) -> LoadedModel:
        """Copy the toy ``kind`` once per ``name``, log its calls, edit its spec, load it, and record the loading."""
        name = name or kind
        if name not in self.copies:
            self.copies[name] = copy_model(kind, self.root / name)
        path = self.copies[name]
        spec = json.loads(path.read_text())
        spec.setdefault("env", {})["TOY_CALLS"] = str(self.log)
        if spec["interface"] == "command_line":
            spec["env"]["PATH"] = f"{os.path.dirname(sys.executable)}:/usr/bin:/bin"
        if edit is not None:
            edit(spec)
        path.write_text(json.dumps(spec, indent=2))
        model = load_spec(str(path))
        assert self.store.record_loading(model.spec, model.spec_path, model.files) == model.model_version_id
        return model

    def approve(self, resolution: Resolution, keys: Sequence[RunKey] | None = None, *, answer: bool = True) -> str:
        """Record an approval (W3) of ``keys`` (by default every new key of the resolution); return its id."""
        keys = resolution.new_keys if keys is None else tuple(keys)
        price = Price.make(new=len(keys), reused=0, time_s=None, from_runs=0)
        request = world.request()
        return self.store.record_approval(
            model_version_id=resolution.model_version_id,
            asked_for="diagnostic_evaluation",
            request=request,
            design=world.identity(resolution.model_version_id, request),
            price=price,
            question=f"Price: {price.text}",
            answer=answer,
            points=keys,
        )

    def calls(self) -> list[tuple[float, ...]]:
        """The points the toys were called at, in order."""
        if not self.log.exists():
            return []
        return [tuple(json.loads(line)) for line in self.log.read_text().splitlines()]

    def stored(self, model: LoadedModel, points: Sequence[Sequence[float]]) -> dict[tuple[str, int], Run]:
        """The current stored runs at these points (Q1)."""
        return self.store.current_runs(model.model_version_id, [point_hash(p) for p in points])

    def run_dir(self, run_id: str) -> Path:
        return Path(self.store.layout.run_dir(run_id))


@contextmanager
def workbench() -> Iterator[Workbench]:
    """A workbench in a temporary directory; its children stopped and its store closed at the end."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = Store.open(root / "ws")
        processes = ModelProcesses()
        try:
            yield Workbench(root, store, processes, root / "calls.log")
        finally:
            processes.close()
            store.close()
            for directory, _, _ in os.walk(tmp):
                os.chmod(directory, 0o700)


@contextmanager
def opened_world() -> Iterator[tuple[Store, LoadedModel]]:
    """A fresh store with the store's toy model version recorded, and that model as loaded (no files, no runs)."""
    from ema.models.spec import stored_model

    with tempfile.TemporaryDirectory() as tmp, Store.open(os.path.join(tmp, "ws")) as store:
        mv = world.load(store)
        model = stored_model(world.spec(), world.FILES, world.SPEC_PATH)
        assert model.model_version_id == mv
        yield store, model
