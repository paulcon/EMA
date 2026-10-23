"""The environment a model gets, and the isolated child a Python model runs in (trust.md; 0026, 0057; M2, M9, T2).

**The environment** (``model_environment``) is built from three parts and nothing else: the base variables in
``BASE_ENV`` that EMA's environment has (empty and relative ``PATH`` entries dropped), the spec's ``pass_env``
names with their values in EMA's environment, and the spec's ``env``, which takes precedence. Both kinds of model
get it; EMA adds no variable of its own.

**The child** (``Child``) runs one model version's Python function, one call at a time. It is started on EMA's own
interpreter by its worker's path (``_worker.py``), in its own process group, with the model's environment and stdin
from ``/dev/null``; it replaces its ``sys.path`` with EMA's, made absolute, received over its own pipe, and puts the
model's directory first. Parent and child speak one line of JSON per message over two pipes of their own, each
request carrying a sequence number its reply echoes; nothing is unpickled. A call's streams go to ``stdout.txt``
and ``stderr.txt`` in its directory; what the child writes outside a call goes to EMA's stderr, never its stdout
(the MCP server's channel). A timeout, a crash, or any exception during an exchange (Ctrl-C included) kills the
child's process group, so a solver the function started goes too, and the next call starts a new child.

**Ctrl-C while a process starts** is held (``InterruptHeld``): from just before ``Popen`` until the process is bound
where the code that kills it on an exception can reach it, a SIGINT only sets a flag; the previous handler is
restored inside that code's ``try`` and the SIGINT delivered to it again, so it raises ``KeyboardInterrupt`` there and
the process is killed (M20, C39). A process's exit is seen without reaping it (``has_exited``), so its process
group can't be another's when it is killed.

Ported from EMA v1 at v1-final: ``src/ema/core/models/_sandbox.py`` (``IsolatedFunction``'s pipes, sequence numbers,
``select`` loop, and process-group kill), re-reviewed against trust.md: v1's memory and CPU limits, its withheld
variables, its output-parser kind, and its profiling are dropped; the environment is the allowlist above; the
child's ``sys.path`` comes over its pipe; a call's streams go to the call's directory.
"""

import json
import os
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ema.types.model import ModelSpec

#: The variables a model gets from EMA's environment whatever its spec says, when EMA's environment has them
#: (trust.md, The environment a model gets), with every ``LC_*``.
BASE_ENV = (
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TZ", "LANG", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH",
)  # fmt: skip
#: The worker the child runs, started by its path (trust.md, Running a model).
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_worker.py")
#: Seconds a new child may take to start and import the function, beside the call's own timeout (as v1's): a
#: library's import is not the call, and a short ``timeout_s`` mustn't fail every call of a model that imports slowly.
START_TIMEOUT_S = 60.0
#: Bytes of a reply read at a time.
_READ = 1 << 20
#: The longest reply line the child may send beside its runs (64 MiB); a call's limit adds ``_RUN_VALUE_BYTES`` for
#: each run's every value (``reply_limit``), and a longer line is the child's death.
MAX_REPLY_BYTES = 64 << 20
#: Bytes allowed in a reply for one value of one run, its prediction's name aside: a number (at most 24 characters),
#: or a reason (the worker's are a sentence; EMA keeps 500 characters of one), with JSON's punctuation.
_RUN_VALUE_BYTES = 640
#: Seconds between checks that the child is alive while a reply is awaited: a descendant holding the replies pipe
#: open would otherwise hide the child's death until the timeout.
_ALIVE_CHECK_S = 0.5
#: Characters of a child's error kept (``collect`` shortens a reason to one line of 500).
_ERROR_CHARS = 1000


class InterruptHeld:
    """Hold Ctrl-C (SIGINT) while a process starts, until the code that kills it can (M20, C39; record 0071).

    Made just before ``Popen``: until ``release``, a SIGINT only sets a flag, so ``KeyboardInterrupt`` can't be raised
    inside ``Popen`` after the fork, where the process would be left running with nothing bound to kill it.
    ``release`` (called first inside the ``try`` whose handler kills the process) restores the previous handler and,
    when a SIGINT came meanwhile, delivers it again (``signal.raise_signal``), so the previous handler runs there:
    Python's raises ``KeyboardInterrupt``. Signals are never blocked (a blocked mask is inherited by the program).
    Outside the main thread, where Python runs no signal handler, nothing is held.
    """

    def __init__(self) -> None:
        self.pending = False
        self._previous: Any = None
        if threading.current_thread() is threading.main_thread() and signal.getsignal(signal.SIGINT) is not None:
            self._previous = signal.signal(signal.SIGINT, self._hold)

    def _hold(self, signum: int, frame: object) -> None:
        self.pending = True

    def release(self) -> None:
        """Restore the previous SIGINT handler, and deliver a SIGINT that came while it was held."""
        previous, self._previous = self._previous, None
        if previous is None:
            return
        signal.signal(signal.SIGINT, previous)
        if self.pending:
            self.pending = False
            signal.raise_signal(signal.SIGINT)


def has_exited(proc: subprocess.Popen[bytes]) -> bool:
    """Tell whether a process has exited, without reaping it (record 0071).

    A process not yet reaped keeps its process id, so its process group can't be a new process's when it is killed.
    """
    if proc.returncode is not None:
        return True
    try:
        return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    except ChildProcessError:  # reaped elsewhere
        return proc.poll() is not None


def readable(fd: int, timeout_s: float) -> bool:
    """Wait up to ``timeout_s`` for ``fd`` to be readable (``poll``: no limit on the descriptor's number)."""
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    return bool(poller.poll(max(0, int(timeout_s * 1000) + 1)))


def reply_limit(n_runs: int, predictions: Sequence[str]) -> int:
    """Return the longest reply line a call of ``n_runs`` runs may have (M8, M1; record 0071, review round 2).

    ``MAX_REPLY_BYTES``, and for each run ``_RUN_VALUE_BYTES`` per model prediction and one more, with each
    prediction's name as JSON writes it: a batch call's reply holds every run, so a fixed limit would make the
    child's death of a correct model's reply past about a million runs.
    """
    names = sum(len(json.dumps(name)) for name in predictions)
    return MAX_REPLY_BYTES + n_runs * ((len(predictions) + 1) * _RUN_VALUE_BYTES + names)


def kill_group(proc: subprocess.Popen[bytes]) -> int:
    """Kill a process's group, then reap the process; its exit code (M20).

    Ctrl-C is held meanwhile, so a second one can't leave the group running.
    """
    held = InterruptHeld()
    try:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        return proc.wait()
    finally:
        held.release()


def _in_base(name: str) -> bool:
    return name in BASE_ENV or name.startswith("LC_")


def model_environment(spec: ModelSpec, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the whole environment a model gets (trust.md, The environment a model gets; T2, M2).

    Parameters
    ----------
    spec
        The model spec: its ``pass_env`` names and its ``env``.
    environ
        EMA's environment; ``os.environ`` by default.

    Returns
    -------
    dict
        The base variables EMA's environment has (``BASE_ENV`` and every ``LC_*``), with empty and relative
        entries dropped from its ``PATH``; each ``pass_env`` name EMA's environment has, with its value there; and
        the spec's ``env``, which takes precedence. Nothing else.
    """
    environ = os.environ if environ is None else environ
    env = {name: value for name, value in environ.items() if _in_base(name)}
    if "PATH" in env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep) if os.path.isabs(p))
    env.update({name: environ[name] for name in spec.pass_env if name in environ})
    env.update(spec.env)
    return env


def find_program(program: str, env: Mapping[str, str], directory: str | None) -> str | None:
    """Resolve a command's program as ``execute`` runs it (trust.md, The environment a model gets; M19).

    Parameters
    ----------
    program
        The command's first string.
    env
        The model's environment (``model_environment``), whose ``PATH`` a name is looked up on.
    directory
        Where a path with a ``/`` is resolved: the run directory, or, before any run, the model's directory.

    Returns
    -------
    str or None
        The program's absolute path, or None when it isn't there, or isn't an executable file.
    """
    if "/" in program:
        path = os.path.normpath(os.path.join(directory or os.getcwd(), program))
        return path if os.path.isfile(path) and os.access(path, os.X_OK) else None
    found = shutil.which(program, path=env.get("PATH", ""))
    return None if found is None else os.path.abspath(found)


def describe_exit(code: int, what: str) -> str:
    """Say how a process ended, after ``what`` (model_interface.md, Failures).

    "exited with code 2", or "killed by signal SIGKILL".
    """
    if code >= 0:
        return f"{what}exited with code {code}"
    try:
        name = signal.Signals(-code).name
    except ValueError:
        name = str(-code)
    return f"{what}{'was ' if what else ''}killed by signal {name}"


@dataclass(frozen=True)
class Outcome:
    """What one call of a child gave (``Child.call``).

    Attributes
    ----------
    runs : tuple of dict or None
        Each run's ``predictions.json`` object (``{"predictions": ..., "missing": ...}``), in the call's order;
        None when the call failed.
    error : str or None
        The one-line reason the call failed: an exception, the child's death, or its import.
    timed_out : bool
        The call ran past its timeout.
    traceback : str
        The traceback of a failure the call's streams don't hold (the function file's import), for its
        ``stderr.txt``.
    time_s : float
        The call's time, from the request's send to its reply; a new child's start and import are not in it (the
        start's own time when the call failed there, record 0071).
    """

    runs: tuple[dict[str, Any], ...] | None
    error: str | None = None
    timed_out: bool = False
    traceback: str = ""
    time_s: float = 0.0


class _Died(Exception):
    """The child died; the message says how."""


class _TimedOut(Exception):
    """A reply didn't come within the time allowed."""


@dataclass(eq=False)
class Child:
    """One model version's isolated child (0026; M9, C38).

    Parameters
    ----------
    model_dir
        The model's directory, first on the child's ``sys.path``.
    function
        The spec's ``function``, ``"file.py:f"``.
    batch
        Whether ``f`` takes a batch of points.
    parameters, predictions
        The spec's names, in its order.
    """

    model_dir: str
    function: str
    batch: bool
    parameters: tuple[str, ...]
    predictions: tuple[str, ...]
    _proc: subprocess.Popen[bytes] | None = field(default=None, init=False)
    _requests: Any = field(default=None, init=False)
    _replies: int | None = field(default=None, init=False)
    _seq: int = field(default=0, init=False)

    @property
    def pid(self) -> int | None:
        """The running child's process id (its process group's), or None."""
        return None if self._proc is None else self._proc.pid

    def _start(self, env: Mapping[str, str], cwd: str, timeout_s: float) -> None:
        """Start the child, and wait until it has imported the function.

        By its file, as a module of the model's directory: ``sub/model.py`` is ``sub.model`` (0069 item 34). Ctrl-C
        is held from before ``Popen`` until the child is bound, and any exception from then on (Ctrl-C too) kills it,
        so a child that never received its ``sys.path`` is never kept (M20, C39).
        """
        held = InterruptHeld()
        try:
            self._spawn(env, cwd)
        except BaseException:
            try:
                self.close()
            finally:
                held.release()
            raise
        try:
            held.release()
            paths = [self.model_dir] + [os.path.abspath(p) for p in sys.path]
            blob = b"\0".join(os.fsencode(p) for p in dict.fromkeys(paths))
            module, _, name = self.function.rpartition(":")
            init = {"module": module.removesuffix(".py").replace("/", "."), "function": name, "batch": self.batch,
                    "parameters": list(self.parameters), "predictions": list(self.predictions)}  # fmt: skip
            try:
                self._requests.write(b"%d\n" % len(blob) + blob)
            except OSError:
                raise _Died(self._death()) from None
            reply = self._exchange(init, timeout_s)
        except BaseException:
            self.close()
            raise
        if "error" in reply:
            self.close()
            raise _ImportFailed(f"couldn't load {self.function}: {_error(reply)}", str(reply.get("traceback", "")))

    def _spawn(self, env: Mapping[str, str], cwd: str) -> None:
        """Start the worker, with its two pipes; the descriptors not kept are closed whatever happens."""
        fds: list[int] = []
        try:
            fds.extend(os.pipe())
            fds.extend(os.pipe())
            requests_r, requests_w, replies_r, replies_w = fds
            self._proc = subprocess.Popen(
                [sys.executable, WORKER, str(requests_r), str(replies_w)],
                stdin=subprocess.DEVNULL, stdout=2, env=dict(env), cwd=cwd, pass_fds=(requests_r, replies_w),
                start_new_session=True,
            )  # fmt: skip
            self._requests = os.fdopen(requests_w, "wb")
            self._replies = replies_r
            fds = [requests_r, replies_w]
        finally:
            for fd in fds:
                os.close(fd)

    def _exchange(self, message: dict[str, Any], timeout_s: float, limit: int | None = None) -> dict[str, Any]:
        """Send one message and read its reply within ``timeout_s``; any exception (Ctrl-C too) kills the child.

        The child's death is seen even when a process it started holds the replies pipe open (it is checked every
        half second); a reply line longer than ``limit`` bytes (``MAX_REPLY_BYTES`` by default; a call's is
        ``reply_limit``) is the child's death, seen as soon as it is read: no more than one byte past it is read.
        """
        assert self._proc is not None and self._requests is not None and self._replies is not None
        limit = MAX_REPLY_BYTES if limit is None else limit
        self._seq += 1
        seq = self._seq
        try:
            try:
                self._requests.write(json.dumps({**message, "seq": seq}).encode() + b"\n")
                self._requests.flush()
            except OSError:
                raise _Died(self._death()) from None
            deadline, buffer, searched = time.monotonic() + timeout_s, bytearray(), 0
            while (end := buffer.find(b"\n", searched)) < 0:  # only the new chunk is searched
                if len(buffer) > limit:  # the chunk just read, with no end of line in it, passed the limit
                    raise _Died(self._too_long(seq, limit, message))
                searched, remaining = len(buffer), deadline - time.monotonic()
                if remaining <= 0:
                    raise _TimedOut()
                if readable(self._replies, min(remaining, _ALIVE_CHECK_S)):
                    chunk = os.read(self._replies, min(_READ, limit + 1 - len(buffer)))
                    if not chunk:
                        raise _Died(self._death())
                    buffer += chunk
                elif has_exited(self._proc):
                    raise _Died(self._death())
            try:
                reply = json.loads(bytes(buffer[:end]))
            except (ValueError, RecursionError):
                raise _Died(f"the child's reply to request {seq} isn't JSON it can read") from None
            in_step = isinstance(reply, dict) and type(reply.get("seq")) is int and reply["seq"] == seq
            if len(buffer) > end + 1 or not in_step:
                raise _Died(f"the child answered out of step (to request {seq})")
            return reply
        except BaseException:
            self.close()
            raise

    def _too_long(self, seq: int, limit: int, message: dict[str, Any]) -> str:
        """Say that a reply passed its limit; for a batch call, that a smaller ``batch_size`` makes it shorter."""
        text = f"the child's reply to request {seq} is longer than {limit >> 20} MiB"
        points = message.get("points")
        if self.batch and isinstance(points, list):
            n = len(points)
            text += f" (a batch of {n} run{'' if n == 1 else 's'}; a smaller batch_size makes a shorter reply)"
        return text

    def _death(self) -> str:
        """Say how the child died (waiting up to 5 s for its exit), and forget it."""
        proc, deadline = self._proc, time.monotonic() + 5
        assert proc is not None
        while not (exited := has_exited(proc)) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.close()  # reaps it: its exit code is set
        return describe_exit(proc.returncode or 0, "the child ") if exited else "the child stopped answering"

    def call(
        self, call_dir: str, points: Sequence[Sequence[float]], env: Mapping[str, str], timeout_s: float
    ) -> Outcome:
        """Run the function on a call's points in the child, starting one when there is none.

        Parameters
        ----------
        call_dir
            The call's working directory, where its streams go (the run directory, or the batch directory).
        points
            One point, or a batch call's points, each in the spec's order.
        env
            The model's environment, used when a child is started.
        timeout_s
            The call's timeout. A new child's start and import are allowed ``max(timeout_s, START_TIMEOUT_S)``.

        Returns
        -------
        Outcome
            Each run's model predictions, or why the call failed, and the call's time (not the start's).
        """
        start, phase = time.perf_counter(), "couldn't start the child"
        try:
            if self._proc is not None and has_exited(self._proc):
                self.close()
            if self._proc is None:
                self._start(env, call_dir, max(timeout_s, START_TIMEOUT_S))
            start, phase = time.perf_counter(), "couldn't exchange the call with the child"
            limit = reply_limit(len(points), self.predictions)
            reply = self._exchange({"call_dir": call_dir, "points": [list(p) for p in points]}, timeout_s, limit)
        except _TimedOut:
            return Outcome(None, timed_out=True, time_s=time.perf_counter() - start)
        except (_Died, _ImportFailed, OSError) as e:  # OSError: starting the worker, or a pipe's error (M1)
            error = f"{phase}: {e.strerror or e}" if isinstance(e, OSError) else str(e)
            traceback = e.traceback if isinstance(e, _ImportFailed) else ""
            return Outcome(None, error=error, traceback=traceback, time_s=time.perf_counter() - start)
        elapsed = time.perf_counter() - start
        if "error" in reply:
            return Outcome(None, error=_error(reply), time_s=elapsed)
        runs = reply.get("runs")
        if not isinstance(runs, list) or len(runs) != len(points):
            return Outcome(None, error="the child's reply holds no model predictions for this call", time_s=elapsed)
        return Outcome(tuple(runs), time_s=elapsed)

    def close(self) -> None:
        """Kill the child's process group, reap it, and close the pipes (Ctrl-C held meanwhile)."""
        held = InterruptHeld()
        try:
            proc, self._proc = self._proc, None
            requests, self._requests = self._requests, None
            replies, self._replies = self._replies, None
            if proc is not None:
                kill_group(proc)
            if requests is not None:
                try:
                    requests.close()
                except OSError:
                    pass
            if replies is not None:
                os.close(replies)
        finally:
            held.release()


def _error(reply: dict[str, Any]) -> str:
    """Return the child's error as a string of at most ``_ERROR_CHARS`` characters."""
    error = reply["error"]
    return error[:_ERROR_CHARS] if isinstance(error, str) else "the child's error isn't text"


class _ImportFailed(Exception):
    """The child couldn't import the function; the message says why."""

    def __init__(self, reason: str, traceback: str) -> None:
        super().__init__(reason)
        self.traceback = traceback
