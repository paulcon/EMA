"""The isolated child's worker: ``python .../ema/models/_worker.py REQUESTS REPLIES`` (0026; M9; trust.md).

Started by ``ema.models.sandbox.Child`` by its file's path. Before it imports anything but ``os`` and ``sys``, it
reads EMA's ``sys.path`` from its requests pipe (its length, a newline, then the entries, absolute, separated by NUL
bytes, the model's directory first) and replaces its own with it, so a ``PYTHONPATH`` in the model's environment,
or this file's own directory, changes nothing it imports. Then it reads one JSON message per line: the first names
the function, which it imports as a module of the model's directory (``sub/model.py`` is ``sub.model``; 0069 item
34), compiled from source, never from a cached ``.pyc`` (a stale cache would run old code under a new model version;
P3); each later one is a call, run with the call's directory as the working directory and the call's streams
in its ``stdout.txt`` and ``stderr.txt``. Each reply is one line of JSON, echoing the request's ``seq``; nothing is
pickled. Outside a call, the worker's stdout and stderr are EMA's stderr.

Ported from EMA v1 at v1-final: ``src/ema/core/models/_worker.py`` (the protocol loop and its replies), re-reviewed
against the trust boundary (trust.md): v1's memory and CPU limits, its watchdog, its output-parser kind, and its
profiling are dropped.
"""

import os
import sys

#: Characters of an exception's message kept in a one-line reason.
REASON_CHARS = 300


def _receive_path(fd: int) -> list[str]:
    """Read EMA's ``sys.path`` from the requests pipe, using nothing but ``os``."""
    digits = b""
    while not digits.endswith(b"\n"):
        byte = os.read(fd, 1)
        if not byte:
            raise SystemExit(1)
        digits += byte
    size, blob = int(digits), b""
    while len(blob) < size:
        chunk = os.read(fd, size - len(blob))
        if not chunk:
            raise SystemExit(1)
        blob += chunk
    return [os.fsdecode(p) for p in blob.split(b"\0") if p]


def _source_only_hook(model_dir: str, others: list[str]):  # type: ignore[no-untyped-def]
    """Make a path hook that loads the model's own modules from their source, never from a cached ``.pyc``.

    The model's own modules are those in its directory, but not in an entry of EMA's ``sys.path`` (``others``) inside
    it, nor below it in a ``site-packages`` or ``dist-packages`` directory: a project's ``.venv`` in the model's
    directory, or a library EMA imports from there, is loaded as EMA loads it (record 0071).
    """
    from importlib.machinery import (
        EXTENSION_SUFFIXES,
        SOURCE_SUFFIXES,
        ExtensionFileLoader,
        FileFinder,
        SourceFileLoader,
    )

    class SourceOnly(SourceFileLoader):
        def get_code(self, fullname: str):  # type: ignore[no-untyped-def]
            path = self.get_filename(fullname)
            return compile(self.get_data(path), path, "exec", dont_inherit=True)

    inside = os.path.join(model_dir, "")
    reals = (os.path.join(os.path.realpath(p), "") for p in others)
    foreign = tuple(p for p in reals if p != inside and p.startswith(inside))
    libraries = {"site-packages", "dist-packages"}

    def hook(path: str) -> FileFinder:
        real = os.path.join(os.path.realpath(path or "."), "")
        below = real[len(inside) :].split(os.sep) if real.startswith(inside) else None
        if below is None or real.startswith(foreign) or libraries & set(below):
            raise ImportError("not one of the model's own directories")
        return FileFinder(path, (SourceOnly, SOURCE_SUFFIXES), (ExtensionFileLoader, EXTENSION_SUFFIXES))

    return hook


def _reason(error: BaseException, model_dir: str) -> str:
    """Say why a call failed, on one line (model_interface.md, Failures).

    "ZeroDivisionError: division by zero at beam.py:14", at the innermost frame in the model's directory.
    """
    import traceback

    where = ""
    for frame in traceback.extract_tb(error.__traceback__):
        path = os.path.realpath(frame.filename)
        if path.startswith(os.path.join(model_dir, "")):
            where = f" at {os.path.relpath(path, model_dir)}:{frame.lineno}"
    try:
        message = " ".join(str(error).split())
    except Exception:  # noqa: BLE001  (an exception whose message can't be made)
        message = ""
    if len(message) > REASON_CHARS:
        message = message[: REASON_CHARS - 1] + "…"
    return f"{type(error).__name__}{': ' if message else ''}{message}{where}"


class _Wrong(Exception):
    """The function returned something that isn't model predictions; fails the call (M7, M8)."""


def _number(value: object) -> float | None:
    """Read a value as a float, infinite for an integer beyond a double's range; None for anything else (M7).

    Bools (numpy's too), strings (numpy's too), bytes, and complex numbers are not numbers.
    """
    import math

    numpy = sys.modules.get("numpy")
    excluded: tuple[type, ...] = (bool, str, bytes, complex)
    if numpy is not None:
        excluded += (numpy.bool_, numpy.complexfloating)
    if isinstance(value, excluded):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except OverflowError:
        return math.inf
    except (TypeError, ValueError):
        return None


def _run(items: object, names: list[str]) -> dict[str, dict[str, object]]:
    """One run's model predictions from a mapping by name: each finite number read, any other missing (M7)."""
    import math
    from collections.abc import Mapping
    from numbers import Integral

    assert isinstance(items, Mapping)
    run: dict[str, dict[str, object]] = {"predictions": {}, "missing": {}}
    for name in names:
        if name not in items:
            run["missing"][name] = "the function didn't return it"
            continue
        value = _number(items[name])
        if value is None:
            run["missing"][name] = f"the function returned {type(items[name]).__name__}, not a number"
        elif isinstance(items[name], Integral) and not math.isfinite(value):
            run["missing"][name] = "the function returned an integer beyond a double's range"
        elif not math.isfinite(value):
            run["missing"][name] = f"the function returned {value!r}"
        else:
            run["predictions"][name] = value
    return run


def _single(value: object, names: list[str]) -> list[dict[str, dict[str, object]]]:
    from collections.abc import Mapping

    if isinstance(value, Mapping):
        return [_run(value, names)]
    if _number(value) is None:
        raise _Wrong(f"the function returned {type(value).__name__}, not a number or a mapping of model predictions")
    if len(names) != 1:
        raise _Wrong(f"the function returned a number; a model with {len(names)} model predictions returns a mapping")
    return [_run({names[0]: value}, names)]


def _batch(value: object, names: list[str], n: int) -> list[dict[str, dict[str, object]]]:
    from collections.abc import Mapping

    import numpy as np

    if not isinstance(value, Mapping):
        if len(names) != 1:
            raise _Wrong(
                f"the function returned an array; a model with {len(names)} model predictions returns a mapping"
            )
        value = {names[0]: value}
    columns = {}
    for name in names:
        if name in value:
            raw = value[name]  # each element read as a single call's value is (M7): a string in it isn't a number
            column = raw if isinstance(raw, np.ndarray) else np.asarray(raw, dtype=object)
            if column.shape != (n,):
                raise _Wrong(f"the function returned shape {column.shape} for {name}; a batch of {n} needs ({n},)")
            columns[name] = column
    return [_run({k: v[i] for k, v in columns.items()}, names) for i in range(n)]


def _flush() -> None:
    """Flush ``sys.stdout`` and ``sys.stderr``, whatever the model made of them."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:  # noqa: BLE001, S110  (a stream the model replaced or closed)
            pass


def _say(text: str) -> None:
    """Write to file descriptor 2 (the call's ``stderr.txt``), after what the function wrote there."""
    _flush()
    data = text.encode(errors="replace")
    while data:
        data = data[os.write(2, data) :]


def _call(func, init: dict, request: dict, model_dir: str) -> dict:  # type: ignore[no-untyped-def, type-arg]
    """Run one call in its directory, with its streams in its files.

    Afterwards the worker's file descriptors 1 and 2, and ``sys.stdout`` and ``sys.stderr``, are restored whatever
    the function did to them.
    """
    import traceback

    out = None
    try:
        os.chdir(request["call_dir"])
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        out = os.open("stdout.txt", flags, 0o644)
        err = os.open("stderr.txt", flags, 0o644)
    except OSError as e:
        if out is not None:
            os.close(out)
        return {"error": f"{e.filename or 'the call directory'}: couldn't be written: {e.strerror}"}
    _flush()
    streams = sys.stdout, sys.stderr
    saved = os.dup(1), os.dup(2)
    os.dup2(out, 1)
    os.dup2(err, 2)
    os.close(out)
    os.close(err)
    try:
        points, names = request["points"], init["predictions"]
        if init["batch"]:
            import numpy as np

            return {"runs": _batch(func(np.asarray(points, dtype=float)), names, len(points))}
        return {"runs": _single(func(**dict(zip(init["parameters"], points[0], strict=True))), names)}
    except _Wrong as e:
        _say(f"{e}\n")
        return {"error": str(e)}
    except BaseException as e:  # noqa: BLE001  (SystemExit included: the call fails, the child stays)
        _say(traceback.format_exc())
        return {"error": _reason(e, model_dir)}
    finally:
        _flush()
        sys.stdout, sys.stderr = streams
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        os.close(saved[0])
        os.close(saved[1])


def main(requests_fd: int, replies_fd: int) -> None:
    """Receive ``sys.path``, import the function, then answer one call per request until the pipe closes."""
    paths = _receive_path(requests_fd)
    model_dir = paths[0]
    sys.path[:] = paths[1:]
    import importlib
    import json
    import traceback

    for fd in (requests_fd, replies_fd):
        os.set_inheritable(fd, False)
    requests = os.fdopen(requests_fd, "rb")
    replies = os.fdopen(replies_fd, "wb")

    def reply(seq: object, message: dict) -> None:  # type: ignore[type-arg]
        replies.write(json.dumps({"seq": seq, **message}, allow_nan=False).encode() + b"\n")
        replies.flush()

    init = json.loads(requests.readline())
    sys.path.insert(0, model_dir)
    sys.path_hooks.insert(0, _source_only_hook(model_dir, paths[1:]))
    sys.path_importer_cache.clear()
    try:
        func = getattr(importlib.import_module(init["module"]), init["function"])
        if not callable(func):
            raise TypeError(f"{init['function']} is not a function")
    except BaseException as e:  # noqa: BLE001  (anything the import raises fails the call)
        reply(init.get("seq"), {"error": _reason(e, model_dir), "traceback": traceback.format_exc()})
        return
    reply(init.get("seq"), {"ready": True})
    for line in requests:
        request = json.loads(line)
        reply(request.get("seq"), _call(func, init, request, model_dir))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
