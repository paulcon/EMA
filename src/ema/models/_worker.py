"""The isolated child's worker: ``python .../ema/models/_worker.py REQUESTS REPLIES`` (0026; M9; trust.md).

Started by ``ema.models.sandbox.Child`` by its file's path. Before it imports anything but ``os`` and ``sys``, it
reads EMA's ``sys.path`` from its requests pipe (its length, a newline, then the entries, absolute, separated by NUL
bytes, the model's directory first) and replaces its own with it, so a ``PYTHONPATH`` in the model's environment,
or this file's own directory, changes nothing it imports. Then it reads one JSON message per line: the first names
the function, which it imports as a module of the model's directory (``sub/model.py`` is ``sub.model``, 0069 item
34), compiled from source, never from a cached ``.pyc`` (P3: a stale cache would run old code under a new model
version); each later one is a call, run with the call's directory as the working directory and the call's streams
in its ``stdout.txt`` and ``stderr.txt``. Each reply is one line of JSON, echoing the request's ``seq``; nothing is
pickled. Outside a call, the worker's stdout and stderr are EMA's stderr.

Ported from EMA v1 at v1-final: ``src/ema/core/models/_worker.py`` (the protocol loop and its replies), re-reviewed
against trust.md: v1's memory and CPU limits, its watchdog, its output-parser kind, and its profiling are dropped.
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


def _source_only_hook(model_dir: str):  # type: ignore[no-untyped-def]
    """Make a path hook that loads the model's own modules from their source, never from a cached ``.pyc``."""
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

    def hook(path: str) -> FileFinder:
        real = os.path.realpath(path or ".")
        if real != model_dir and not real.startswith(inside):
            raise ImportError("not in the model's directory")
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
    message = " ".join(str(error).split())
    if len(message) > REASON_CHARS:
        message = message[: REASON_CHARS - 1] + "…"
    return f"{type(error).__name__}{': ' if message else ''}{message}{where}"


class _Wrong(Exception):
    """The function returned something that isn't model predictions; fails the call (M7, M8)."""


def _number(value: object) -> float | None:
    if isinstance(value, (bool, str, bytes)):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _run(items: object, names: list[str]) -> dict[str, dict[str, object]]:
    """One run's model predictions from a mapping by name: each finite number read, any other missing (M7)."""
    import math
    from collections.abc import Mapping

    assert isinstance(items, Mapping)
    run: dict[str, dict[str, object]] = {"predictions": {}, "missing": {}}
    for name in names:
        if name not in items:
            run["missing"][name] = "the function didn't return it"
            continue
        value = _number(items[name])
        if value is None:
            run["missing"][name] = f"the function returned {type(items[name]).__name__}, not a number"
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
            column = np.asarray(value[name], dtype=float)
            if column.shape != (n,):
                raise _Wrong(f"the function returned shape {column.shape} for {name}; a batch of {n} needs ({n},)")
            columns[name] = column
    return [_run({k: float(v[i]) for k, v in columns.items()}, names) for i in range(n)]


def _call(func, init: dict, request: dict, model_dir: str) -> dict:  # type: ignore[no-untyped-def, type-arg]
    """Run one call in its directory, with its streams in its files."""
    import traceback

    try:
        os.chdir(request["call_dir"])
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        out = os.open("stdout.txt", flags, 0o644)
        err = os.open("stderr.txt", flags, 0o644)
    except OSError as e:
        return {"error": f"{e.filename or 'the call directory'}: couldn't be written: {e.strerror}"}
    sys.stdout.flush()
    sys.stderr.flush()
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
        print(e, file=sys.stderr)
        return {"error": str(e)}
    except BaseException as e:  # noqa: BLE001  (SystemExit included: the call fails, the child stays)
        traceback.print_exc()
        return {"error": _reason(e, model_dir)}
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
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
    sys.path_hooks.insert(0, _source_only_hook(model_dir))
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
