"""The run lock: one process at a time makes runs in a workspace (data_model.md §10; architecture.md §5; trust.md).

``fcntl.flock(LOCK_EX | LOCK_NB)`` on a descriptor of ``run.lock`` kept open while the lock is held, so it excludes
a second holder in the same process as well as in another (a per-process POSIX lock would not), and is released when
the descriptor closes or the process exits. The holder writes its process id, host, and start time into the file,
so a second process is refused naming it. Only the workspace that makes runs takes it.

**Fork caveat** (review round 1): ``flock`` belongs to the open file description, which a child made by
``os.fork`` without ``exec`` shares, so such a child keeps the lock held after its parent releases it, until the
child exits. The descriptor is opened non-inheritable (Python's default), so a child started by ``subprocess`` or
by ``multiprocessing``'s "spawn" or "forkserver" doesn't hold it: the runner (step 07) starts model processes that
way, never with a bare fork or ``multiprocessing``'s "fork".
"""

import fcntl
import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from ema.types.errors import WorkspaceBusy
from ema.types.text import timestamp_text


def _holder(fd: int) -> str:
    try:
        text = os.pread(fd, 1024, 0).decode("utf-8", "replace").strip()
    except OSError:
        text = ""
    return text or "another process"


def _this_process() -> str:
    return f"process {os.getpid()} on {socket.gethostname()}"


@contextmanager
def run_lock(path: str) -> Iterator[None]:
    """Hold the run lock at ``path`` for a ``with`` block.

    Parameters
    ----------
    path
        The workspace's ``run.lock``; created when missing.

    Raises
    ------
    WorkspaceBusy
        When another holder, in this process or another, has it; the message names the holder and the lock, and
        says "another workspace of this process" when the holder is this process (another thread's workspace).
    """
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = _holder(fd)
            who = "another workspace of this process" if holder.startswith(_this_process()) else "another process"
            raise WorkspaceBusy(f"{who} is making runs in this workspace ({holder}); it holds {path}") from None
        holder = f"{_this_process()}, since {timestamp_text(datetime.now(UTC))}"
        os.ftruncate(fd, 0)
        os.pwrite(fd, holder.encode("utf-8") + b"\n", 0)
        try:
            yield
        finally:
            os.ftruncate(fd, 0)
    finally:
        os.close(fd)  # releases the lock
