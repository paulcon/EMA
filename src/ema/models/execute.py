"""Execute a prepared call: run the model (model_interface.md, A run; M2, M9, M20; trust.md, Running a model).

Only ``ema.runner`` imports this module (AR4): it is the one code that starts a model.

- **A command** runs without a shell, its program resolved against the model's own ``PATH`` (or, with a ``/``,
  against the run directory), in its own process group, with the run directory as its working directory, stdin
  from ``/dev/null``, and its streams in ``stdout.txt`` and ``stderr.txt``. A timeout or Ctrl-C kills the group
  (M20, C39).
- **A Python function** runs in its model version's child, taken from ``processes`` (``ModelProcesses``; 0026).
  The model predictions it returned are written to each run's ``predictions.json`` without following a link
  (0028; T9), for ``collect`` to read.

Ctrl-C (``KeyboardInterrupt``) kills the call and is raised again, also when it comes while the program starts
(``sandbox.InterruptHeld``); deleting the stopped call's directories is the runner's (``discard``, 0028).
"""

import json
import math
import os
import select
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

from ema.models.files import write_own
from ema.models.prepare import PreparedCall
from ema.models.processes import ModelProcesses
from ema.models.sandbox import InterruptHeld, find_program, has_exited, kill_group, readable
from ema.models.spec import LoadedModel
from ema.types.model import CommandLine

#: Characters of a model prediction's missing reason kept from the child's reply.
_REASON_CHARS = 500
#: A call's stream is created exclusively, never through a link (T9).
_CREATE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


@dataclass(frozen=True)
class ExecutedCall:
    """A call that ran (architecture.md §5).

    Attributes
    ----------
    prepared : PreparedCall
        The call.
    exit_code : int or None
        The program's exit code, -N for signal N; None for a Python function, a program that couldn't start, or a
        timeout.
    timed_out : bool
        The call ran past its timeout.
    error : str or None
        The one-line reason the call failed, where known: the function raised, its child died, or the program
        couldn't start.
    time_s : float
        The call's time.
    host : str
        Where it ran (0015).
    program : str
        The program's resolved path; the child's interpreter for a Python function (0029).
    run_errors : tuple of str or None
        For each run, why EMA couldn't write its ``predictions.json`` (kind ``error``, 0057), or None.
    """

    prepared: PreparedCall
    exit_code: int | None
    timed_out: bool
    error: str | None
    time_s: float
    host: str
    program: str
    run_errors: tuple[str | None, ...] = ()


def _wait(proc: subprocess.Popen[bytes], timeout_s: float) -> None:
    """Wait for the program to exit, without reaping it; ``TimeoutExpired`` past ``timeout_s``.

    Woken by its exit (a pidfd, or kqueue), not by ``Popen.wait``'s polling, whose sleeps add up to 50 ms to a run;
    each wakeup is checked with ``has_exited``, so an early one only waits again. Where neither can be had (a pidfd
    refused by an old kernel or a seccomp filter), it checks every 5 ms. The program isn't reaped, so its process
    group is still its own when ``kill_group`` kills it (record 0071, choice 3).
    """
    deadline = time.monotonic() + timeout_s
    pidfd: int | None = None
    queue: Any = None
    try:
        try:
            if hasattr(os, "pidfd_open"):
                pidfd = os.pidfd_open(proc.pid)
            elif hasattr(select, "kqueue"):
                queue = select.kqueue()
                # registered before the first check, so an exit from then on wakes the wait
                exit_event = select.kevent(proc.pid, select.KQ_FILTER_PROC, select.KQ_EV_ADD, select.KQ_NOTE_EXIT)
                queue.control([exit_event], 0, 0)
        except OSError:  # ENOSYS, EPERM; ESRCH for one that has exited: checked below
            if queue is not None:
                queue.close()
            queue = None
        while not has_exited(proc):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout_s)
            if pidfd is not None:
                readable(pidfd, remaining)
            elif queue is not None:
                queue.control(None, 1, remaining)
            else:
                time.sleep(min(remaining, 0.005))
    finally:
        if pidfd is not None:
            os.close(pidfd)
        if queue is not None:
            queue.close()


def _start(call: PreparedCall, program: str, env: dict[str, str]) -> tuple[subprocess.Popen[bytes], float] | str:
    """Start the program; return it and its start time, or why it couldn't start.

    Its streams are created exclusively, without following a link.
    """
    assert call.command is not None
    fds: list[int] = []
    try:
        for name in ("stdout.txt", "stderr.txt"):
            fds.append(os.open(os.path.join(call.call_dir, name), _CREATE, 0o644))
        start = time.perf_counter()
        proc = subprocess.Popen(
            list(call.command), executable=program, cwd=call.call_dir, env=env, stdin=subprocess.DEVNULL,
            stdout=fds[0], stderr=fds[1], start_new_session=True,
        )  # fmt: skip
        return proc, start
    except OSError as e:
        stream = f"{os.path.basename(e.filename)}: " if len(fds) < 2 and e.filename else ""
        return f"couldn't start {call.command[0]}: {stream}{e.strerror}"
    finally:
        for fd in fds:
            os.close(fd)


def _run_command(call: PreparedCall, host: str) -> ExecutedCall:
    assert call.command is not None
    env = dict(call.env)
    start = time.perf_counter()
    program = find_program(call.command[0], env, call.call_dir)
    if program is None:
        error = f"couldn't start {call.command[0]}: not found on the model's PATH"
        return ExecutedCall(call, None, False, error, time.perf_counter() - start, host, call.command[0])
    held, proc = InterruptHeld(), None  # Ctrl-C in Popen, after the fork, would leave the program running (M20, C39)
    try:
        started = _start(call, program, env)
        if isinstance(started, str):
            return ExecutedCall(call, None, False, started, time.perf_counter() - start, host, program)
        proc, start = started
        held.release()  # delivers a Ctrl-C that came meanwhile, now that the program can be killed
        _wait(proc, call.timeout_s)
    except subprocess.TimeoutExpired:
        assert proc is not None
        kill_group(proc)
        return ExecutedCall(call, None, True, None, time.perf_counter() - start, host, program)
    except BaseException:
        if proc is not None:
            kill_group(proc)
        raise
    finally:
        held.release()
    elapsed = time.perf_counter() - start
    code = kill_group(proc)  # what the program started and left running goes with it (M20; record 0071, choice 3)
    return ExecutedCall(call, code, False, None, elapsed, host, program)


def _finite(value: object) -> bool:
    """Tell whether a value is a JSON number (not a bool) that is a finite double."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _write_predictions(run_dir: str, run: object, names: list[str]) -> str | None:
    """Write one run's ``predictions.json`` without following a link; the reason it couldn't be, or None.

    The child's reply is checked again here (M1): only finite numbers are kept, and only text as a reason.
    """
    predictions = run.get("predictions") if isinstance(run, dict) else None
    missing = run.get("missing") if isinstance(run, dict) else None
    if not isinstance(predictions, dict) or not isinstance(missing, dict):
        return "predictions.json: the child's reply holds no model predictions for this run"
    values = {k: float(v) for k, v in predictions.items() if k in names and _finite(v)}
    reasons = {k: v[:_REASON_CHARS] for k, v in missing.items() if k in names and isinstance(v, str)}
    for name in names:
        if name in predictions and name not in values:
            reasons[name] = "the child's reply holds no finite number for it"
    content = {"predictions": values, "missing": reasons}
    try:
        write_own(run_dir, "predictions.json", (json.dumps(content, indent=2, allow_nan=False) + "\n").encode())
    except (OSError, TypeError, ValueError) as e:
        return f"predictions.json: couldn't be written: {getattr(e, 'strerror', None) or e}"
    return None


def _run_function(model: LoadedModel, call: PreparedCall, processes: ModelProcesses, host: str) -> ExecutedCall:
    child = processes.child(model)
    points = [key.point for key in call.keys]
    outcome = child.call(call.call_dir, points, call.env, call.timeout_s)
    if outcome.traceback:
        try:
            write_own(call.call_dir, "stderr.txt", outcome.traceback.encode())
        except OSError:
            pass
    errors: tuple[str | None, ...] = ()
    if outcome.runs is not None:
        names = [p.name for p in model.spec.predictions]
        errors = tuple(_write_predictions(d, r, names) for d, r in zip(call.run_dirs, outcome.runs, strict=True))
    return ExecutedCall(call, None, outcome.timed_out, outcome.error, outcome.time_s, host, sys.executable, errors)


def execute(model: LoadedModel, call: PreparedCall, processes: ModelProcesses) -> ExecutedCall:
    """Run a prepared call (M2, M9, M20; 0026, 0028).

    Never raises for a point (M1): a failure is in the result, for ``collect``. Ctrl-C kills the call (the
    command's process group, or the child's) and is raised again.

    Parameters
    ----------
    model
        The loaded model.
    call
        The prepared call.
    processes
        The workspace's children, one per Python model version.

    Returns
    -------
    ExecutedCall
        The exit status, the timing, the host, and the program.
    """
    host = socket.gethostname()
    if isinstance(model.spec.interface, CommandLine):
        return _run_command(call, host)
    return _run_function(model, call, processes, host)
