"""Execute a prepared call: run the model (model_interface.md, A run; M2, M9, M20; trust.md, Running a model).

Only ``ema.runner`` imports this module (AR4): it is the one code that starts a model.

- **A command** runs without a shell, its program resolved against the model's own ``PATH`` (or, with a ``/``,
  against the run directory), in its own process group, with the run directory as its working directory, stdin
  from ``/dev/null``, and its streams in ``stdout.txt`` and ``stderr.txt``. A timeout or Ctrl-C kills the group
  (M20, C39).
- **A Python function** runs in its model version's child, taken from ``processes`` (``ModelProcesses``; 0026).
  The model predictions it returned are written to each run's ``predictions.json`` without following a link
  (0028; T9), for ``collect`` to read.

Ctrl-C (``KeyboardInterrupt``) kills the call and is raised again; deleting the stopped call's directories is the
runner's (``discard``, 0028).
"""

import json
import os
import select
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass

from ema.models.files import write_own
from ema.models.prepare import PreparedCall
from ema.models.processes import ModelProcesses
from ema.models.sandbox import find_program
from ema.models.spec import LoadedModel
from ema.types.model import CommandLine


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


def _wait(proc: subprocess.Popen[bytes], timeout_s: float) -> int:
    """Wait for the program to exit; ``TimeoutExpired`` past ``timeout_s``.

    Woken by its exit (a pidfd, or kqueue), not by ``Popen.wait``'s polling, whose sleeps add up to 50 ms to a run;
    each wakeup is checked with ``poll``, so an early one only waits again.
    """
    deadline = time.monotonic() + timeout_s
    if hasattr(os, "pidfd_open"):
        try:
            fd = os.pidfd_open(proc.pid)
        except ProcessLookupError:
            return proc.wait()
        try:
            while proc.poll() is None:
                if deadline - time.monotonic() <= 0:
                    raise subprocess.TimeoutExpired(proc.args, timeout_s)
                select.select([fd], [], [], deadline - time.monotonic())
        finally:
            os.close(fd)
        return proc.wait()
    if not hasattr(select, "kqueue"):
        return proc.wait(timeout=timeout_s)
    queue = select.kqueue()
    try:
        try:  # registered before the first poll, so an exit from then on wakes the wait
            queue.control([select.kevent(proc.pid, select.KQ_FILTER_PROC, select.KQ_EV_ADD, select.KQ_NOTE_EXIT)], 0, 0)
        except ProcessLookupError:
            return proc.wait()
        while proc.poll() is None:
            if deadline - time.monotonic() <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout_s)
            queue.control(None, 1, deadline - time.monotonic())
    finally:
        queue.close()
    return proc.wait()


def _kill(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


def _run_command(call: PreparedCall, host: str) -> ExecutedCall:
    assert call.command is not None
    env = dict(call.env)
    program = find_program(call.command[0], env, call.call_dir)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    start = time.perf_counter()
    if program is None:
        error = f"couldn't start {call.command[0]}: not found on the model's PATH"
        return ExecutedCall(call, None, False, error, time.perf_counter() - start, host, call.command[0])
    out = os.open(os.path.join(call.call_dir, "stdout.txt"), flags, 0o644)
    err = os.open(os.path.join(call.call_dir, "stderr.txt"), flags, 0o644)
    try:
        start = time.perf_counter()
        proc = subprocess.Popen(
            list(call.command), executable=program, cwd=call.call_dir, env=env, stdin=subprocess.DEVNULL,
            stdout=out, stderr=err, start_new_session=True,
        )  # fmt: skip
    except OSError as e:
        error = f"couldn't start {call.command[0]}: {e.strerror}"
        return ExecutedCall(call, None, False, error, time.perf_counter() - start, host, program)
    finally:
        os.close(out)
        os.close(err)
    try:
        code = _wait(proc, call.timeout_s)
    except subprocess.TimeoutExpired:
        _kill(proc)
        return ExecutedCall(call, None, True, None, time.perf_counter() - start, host, program)
    except BaseException:
        _kill(proc)
        raise
    elapsed = time.perf_counter() - start
    try:
        os.killpg(proc.pid, signal.SIGKILL)  # what the program started and left running (M20)
    except (ProcessLookupError, PermissionError):
        pass
    return ExecutedCall(call, code, False, None, elapsed, host, program)


def _write_predictions(run_dir: str, run: object, names: list[str]) -> str | None:
    """Write one run's ``predictions.json`` without following a link; the reason it couldn't be, or None."""
    if not isinstance(run, dict):
        return "predictions.json: the child's reply holds no model predictions for this run"
    content = {
        key: {k: v for k, v in dict(run.get(key) or {}).items() if k in names} for key in ("predictions", "missing")
    }
    try:
        write_own(run_dir, "predictions.json", (json.dumps(content, indent=2, allow_nan=False) + "\n").encode())
    except (OSError, TypeError, ValueError) as e:
        return f"predictions.json: couldn't be written: {getattr(e, 'strerror', None) or e}"
    return None


def _run_function(model: LoadedModel, call: PreparedCall, processes: ModelProcesses, host: str) -> ExecutedCall:
    child = processes.child(model)
    points = [key.point for key in call.keys]
    start = time.perf_counter()
    outcome = child.call(call.call_dir, points, call.env, call.timeout_s)
    elapsed = time.perf_counter() - start
    if outcome.traceback:
        try:
            write_own(call.call_dir, "stderr.txt", outcome.traceback.encode())
        except OSError:
            pass
    errors: tuple[str | None, ...] = ()
    if outcome.runs is not None:
        names = [p.name for p in model.spec.predictions]
        errors = tuple(_write_predictions(d, r, names) for d, r in zip(call.run_dirs, outcome.runs, strict=True))
    return ExecutedCall(call, None, outcome.timed_out, outcome.error, elapsed, host, sys.executable, errors)


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
