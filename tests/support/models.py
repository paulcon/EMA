"""The test models in ``tests/models`` (contracts.md, the model adapter contract's millisecond models).

- ``python``: a Python function with a listed helper module and a shared file, two model predictions (y, z);
- ``batch``: the same function as a batch, one model prediction (y);
- ``command_line``: a program run by Python, with an input deck and a shared file, two model predictions (y read
  by the JSON parser from ``out.json``, w by a regex from stdout);
- ``imports``: a function file whose imports resolve to unlisted files (M17), and which writes a marker file when
  imported (T4: loading never imports it).

The first three have model parameters a, b, and ``mode``, which picks the toy's behaviour (for a batch, any row's
mode applies to the call, but 6, row by row):

====  ==========================================================================================================
mode  behaviour
====  ==========================================================================================================
0     y = a + 2 b + scale (scale read from mesh.dat, 0.0); z = y + 1; w = a - b
1     error: the function raises ZeroDivisionError; the program writes good output and exits 1 (M12)
2     crash: the function calls ``os._exit(3)``; the program kills itself with SIGKILL
3     hang: starts a child process that sleeps, writes both pids to ``pids.json``, and sleeps 60 s
4     inspect: writes ``inspect.json`` (its environment, what stdin gave, its pid, what it received), then as 0
5     writes to the shared file ``mesh.dat`` (a permission error)
6     y is NaN (z and w read)
7     returns, or writes, no model prediction
8     prints a line to stdout and one to stderr, then as 0
9     one model prediction missing: z (the function, which also returns an extra name), or w (the program)
10    returns something that isn't model predictions: a string, or a batch's array of the wrong shape
====  ==========================================================================================================

A test copies a model into a temporary directory before changing or loading it, so nothing is written beside the
originals.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODELS = Path(__file__).resolve().parent.parent / "models"
KINDS = ("python", "batch", "command_line")
APPROVAL = "a" * 64


def copy_model(kind: str, directory: Path) -> Path:
    """Copy the test model ``kind`` into ``directory``; return its spec's path."""
    target = directory / kind
    shutil.copytree(MODELS / kind, target)
    return target / "model.json"


def point(mode: float = 0.0, a: float = 1.0, b: float = 0.5) -> tuple[float, float, float]:
    """A complete point of the toys, in their order (a, b, mode)."""
    return (a, b, float(mode))


@dataclass
class Bench:
    """A temporary workspace's directories, copies of a toy, and the children, for running the toys.

    ``adapter`` is the contract's ``Adapter`` (its load, prepare, execute, collect, ...), so a broken toy runs
    through the same steps.
    """

    adapter: Any
    root: Path
    processes: Any
    copies: dict[str, Path] = field(default_factory=dict)

    @property
    def runs_dir(self) -> Path:
        return self.root / "ws" / "runs"

    @property
    def shared_dir(self) -> Path:
        return self.root / "ws" / "files"

    def spec_path(self, name: str = "m", kind: str | None = None) -> Path:
        """The spec of the copy ``name`` of the toy (the adapter's kind by default), copied once."""
        if name not in self.copies:
            path = self.copies[name] = copy_model(kind or self.adapter.kind, self.root / name)
            spec = json.loads(path.read_text())
            if spec["interface"] == "command_line":
                # The project's interpreter as python3: macOS's /usr/bin/python3 is a shim that adds variables of
                # its own (CPATH, SDKROOT, ...) to the program's environment, and takes 60 ms more to start.
                spec["env"]["PATH"] = f"{os.path.dirname(sys.executable)}:{spec['env']['PATH']}"
                path.write_text(json.dumps(spec, indent=2))
        return self.copies[name]

    def model(self, edit: Callable[[dict[str, Any]], None] | None = None, name: str = "m", kind: str | None = None):
        """Load a copy of the toy, its spec edited first (a variant is its own copy, so give it its own name)."""
        path = self.spec_path(name, kind)
        if edit is not None:
            spec = json.loads(path.read_text())
            edit(spec)
            path.write_text(json.dumps(spec, indent=2))
        return self.adapter.load(str(path))

    def prepare(self, model: Any, points: Sequence[Sequence[float]], replicate: int = 0) -> Any:
        from ema.types.runs import RunKey

        keys = [RunKey.make(model.model_version_id, p, replicate, 0) for p in points]
        return self.adapter.prepare(model, keys, str(self.runs_dir), str(self.shared_dir), approval_id=APPROVAL)

    def call(self, model: Any, points: Sequence[Sequence[float]]) -> tuple[Any, Any, tuple[Any, ...]]:
        """One call: prepare, execute, collect."""
        prepared = self.prepare(model, points)
        executed = self.adapter.execute(model, prepared, self.processes)
        return prepared, executed, self.adapter.collect(model, executed)

    def runs(self, model: Any, *points: Sequence[float]) -> tuple[Any, ...]:
        """The runs at ``points``: one batch call for a batch model, else one call per point."""
        from ema.types.model import PythonFunction

        if isinstance(model.spec.interface, PythonFunction) and model.spec.interface.batch:
            return self.call(model, points)[2]
        return tuple(run for p in points for run in self.call(model, [p])[2])


@contextmanager
def bench(adapter: Any) -> Iterator[Bench]:
    """A bench in a temporary directory, its children stopped at the end."""
    import tempfile

    from ema.models.processes import ModelProcesses

    processes = ModelProcesses()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            yield Bench(adapter, Path(tmp).resolve(), processes)
        finally:
            processes.close()
            for directory, _, _ in os.walk(tmp):
                os.chmod(directory, 0o700)


def alive(pid: int) -> bool:
    """Tell whether a process exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gone(pids: Sequence[int], within: float = 2.0) -> bool:
    """Tell whether every process in ``pids`` is gone within ``within`` seconds (a killed orphan is reaped by
    init, not by EMA, so it may outlive the kill by a moment)."""
    import time

    deadline = time.monotonic() + within
    while any(alive(p) for p in pids):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


@contextmanager
def interrupt_after(seconds: float) -> Iterator[None]:
    """Send this process SIGINT after ``seconds`` (Ctrl-C), with Python's own handler."""
    import signal
    import threading

    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    timer = threading.Timer(seconds, os.kill, (os.getpid(), signal.SIGINT))
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        signal.signal(signal.SIGINT, previous)
