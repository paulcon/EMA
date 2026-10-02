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
_READ = 1 << 16


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
    """

    runs: tuple[dict[str, Any], ...] | None
    error: str | None = None
    timed_out: bool = False
    traceback: str = ""


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

        By its file, as a module of the model's directory: ``sub/model.py`` is ``sub.model`` (0069 item 34).
        """
        requests_r, requests_w = os.pipe()
        replies_r, replies_w = os.pipe()
        try:
            self._proc = subprocess.Popen(
                [sys.executable, WORKER, str(requests_r), str(replies_w)],
                stdin=subprocess.DEVNULL, stdout=2, env=dict(env), cwd=cwd, pass_fds=(requests_r, replies_w),
                start_new_session=True,
            )  # fmt: skip
        except BaseException:
            for fd in (requests_w, replies_r):
                os.close(fd)
            raise
        finally:
            for fd in (requests_r, replies_w):
                os.close(fd)
        self._requests = os.fdopen(requests_w, "wb")
        self._replies = replies_r
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
        if "error" in reply:
            self.close()
            raise _ImportFailed(f"couldn't load {self.function}: {reply['error']}", reply.get("traceback", ""))

    def _exchange(self, message: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        """Send one message and read its reply within ``timeout_s``; any exception (Ctrl-C too) kills the child."""
        assert self._proc is not None and self._requests is not None and self._replies is not None
        self._seq += 1
        seq = self._seq
        try:
            try:
                self._requests.write(json.dumps({**message, "seq": seq}).encode() + b"\n")
                self._requests.flush()
            except OSError:
                raise _Died(self._death()) from None
            deadline = time.monotonic() + timeout_s
            line = b""
            while b"\n" not in line:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _TimedOut()
                ready, _, _ = select.select([self._replies], [], [], remaining)
                if ready:
                    chunk = os.read(self._replies, _READ)
                    if not chunk:
                        raise _Died(self._death())
                    line += chunk
            line, _, extra = line.partition(b"\n")
            try:
                reply = json.loads(line)
            except ValueError:
                raise _Died(f"the child's reply to request {seq} isn't JSON") from None
            if extra or not isinstance(reply, dict) or reply.get("seq") != seq:
                raise _Died(f"the child answered out of step (to request {seq})")
            return reply
        except BaseException:
            self.close()
            raise

    def _death(self) -> str:
        """Say how the child died, and forget it."""
        assert self._proc is not None
        try:
            code = self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            code = None
        self.close()
        return "the child stopped answering" if code is None else describe_exit(code, "the child ")

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
            Each run's model predictions, or why the call failed.
        """
        try:
            if self._proc is not None and self._proc.poll() is not None:
                self.close()
            if self._proc is None:
                self._start(env, call_dir, max(timeout_s, START_TIMEOUT_S))
            reply = self._exchange({"call_dir": call_dir, "points": [list(p) for p in points]}, timeout_s)
        except _TimedOut:
            return Outcome(None, timed_out=True)
        except _Died as e:
            return Outcome(None, error=str(e))
        except _ImportFailed as e:
            return Outcome(None, error=e.reason, traceback=e.traceback)
        if "error" in reply:
            return Outcome(None, error=str(reply["error"]))
        runs = reply.get("runs")
        if not isinstance(runs, list) or len(runs) != len(points):
            return Outcome(None, error="the child's reply holds no model predictions for this call")
        return Outcome(tuple(runs))

    def close(self) -> None:
        """Kill the child's process group, wait for it, and close the pipes."""
        proc, self._proc = self._proc, None
        requests, self._requests = self._requests, None
        replies, self._replies = self._replies, None
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
        if requests is not None:
            try:
                requests.close()
            except OSError:
                pass
        if replies is not None:
            os.close(replies)


class _ImportFailed(Exception):
    """The child couldn't import the function."""

    def __init__(self, reason: str, traceback: str) -> None:
        super().__init__(reason)
        self.reason, self.traceback = reason, traceback
