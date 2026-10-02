"""The model adapter contract (contracts.md, C31–C45), over a Python function, a batch, and a command-line model.

Its implementation is how a model is loaded and run: ``Adapter``, the three phases of a call (``prepare``,
``execute``, ``collect``; 0015), the files' check before a call (``check_files``), and what follows a call (``keep``,
and a stopped call's ``discard``), over the toys in ``tests/models`` (``tests.support.models``, whose ``mode``
picks a toy's behaviour). Each check runs over the kinds of model ``contracts.md`` gives it ("Run over"): all three,
the batch model, the Python models, or the command-line model; ``check_parser`` runs over the registered output
parsers. Every check has broken toys, each an ``Adapter`` (or a parser) that differs from the real one in one way,
and ``test_every_check_fails_on_its_broken_toy`` is the meta-test.

Step 03 wrote C33; steps 04 and 05 add the rest. Finished in step 07 (the runner), in ``tests/contracts/runner.py``:
C34's call refused through ``run_new`` (``check_refused_call``), C37's calls sized to ``batch_size`` and to what
remains approved (``check_batch_sizes``), and C41's ``keep`` and stopped run through ``run_new``
(``check_keep_applied``) (records 0071, 0074).
"""

from __future__ import annotations

import importlib.util
import inspect
import io
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from ema.models import files, parsers
from ema.models.collect import collect, discard, keep_or_remove
from ema.models.execute import ExecutedCall, execute
from ema.models.files import is_within, write_own
from ema.models.prepare import prepare
from ema.models.spec import LoadedModel, load_spec, resolve_program
from ema.types.errors import ModelChanged, SpecError
from ema.types.identity import TrackedFile, batch_call_id, canonical_json, sha256_hex, version_hash
from ema.types.model import CsvParser, JsonParser, RegexParser
from ema.types.runs import FailureKind, RunStatus
from tests.support.models import KINDS, bench, copy_model, gone, interrupt_after, point

#: Seconds a toy may run in the checks that time out (its sleep is 60 s).
TIMEOUT_S = 0.25
#: Seconds before Ctrl-C in the checks that stop a call.
INTERRUPT_S = 0.2


@dataclass(frozen=True)
class Adapter:
    """One test model, and how it is loaded and run."""

    kind: str
    load: Callable[[str], LoadedModel] = load_spec
    prepare: Callable[..., Any] = prepare
    execute: Callable[..., Any] = execute
    collect: Callable[..., Any] = collect
    check_files: Callable[[LoadedModel], None] = files.check_files
    keep_or_remove: Callable[..., None] = keep_or_remove
    discard: Callable[..., None] = discard


def short_timeout(spec: dict[str, Any]) -> None:
    spec["timeout_s"] = TIMEOUT_S


def stopped(adapter: Any, model: LoadedModel, prepared: Any, processes: Any) -> bool:
    """Execute a call and press Ctrl-C during it; tell whether ``KeyboardInterrupt`` came out (C49's and M9's)."""
    try:
        with interrupt_after(INTERRUPT_S):
            adapter.execute(model, prepared, processes)
    except KeyboardInterrupt:
        return True
    return False


def runs_never_raising(b: Any, model: LoadedModel, *points: Any) -> tuple[Any, ...]:
    """M1: the adapter never raises for a point."""
    try:
        return b.runs(model, *points)
    except Exception as e:
        raise AssertionError(f"the adapter raised for a point: {e!r}") from e


def call_dir(run: Any, b: Any) -> Path:
    """The directory a run's call ran in: its run directory, or its batch directory."""
    return b.runs_dir / (run.batch_call_id or run.run_id)


# --------------------------------------------------------------------------------------------------------------
# C33 (step 03)


def tracked_names(spec: dict[str, Any]) -> list[str]:
    """The files a spec's model version covers, read from its JSON (model_interface.md, Versions)."""
    names = [spec["function"].rpartition(":")[0]] if "function" in spec else []
    names += [deck["template"] for deck in spec.get("input_decks", [])]
    names += [f if isinstance(f, str) else f["path"] for f in spec.get("files", [])]
    return list(dict.fromkeys(names))


def covered_changes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Specs that differ from ``spec`` in one covered field each (M3, 0029)."""
    out = []

    def changed(edit: Callable[[dict[str, Any]], None]) -> None:
        copy = json.loads(json.dumps(spec))
        edit(copy)
        out.append(copy)

    changed(lambda s: s.update(name=s["name"] + "_2"))
    changed(lambda s: s.update(description=s["description"] + "."))
    changed(lambda s: s["parameters"][0].update(units="km"))
    changed(lambda s: s["parameters"][0].update(nominal=s["parameters"][0]["nominal"] + 0.25))
    changed(lambda s: s["parameters"][0].update(description="another"))
    changed(lambda s: s["parameters"][1].update(limits={"lt": 100}))
    changed(lambda s: s["predictions"][0].update(description="another"))
    changed(lambda s: s["predictions"][0].update(units="km"))
    changed(lambda s: s.update(env={**s.get("env", {}), "X_FLAG": "1"}))
    changed(lambda s: s.update(pass_env=[*s.get("pass_env", []), "X_HOST"]))
    changed(
        lambda s: s.update(
            files=[
                {"path": "mesh.dat", "shared": False} if f == {"path": "mesh.dat", "shared": True} else f
                for f in s["files"]
            ]
        )
    )
    if spec["interface"] == "python_function":
        changed(lambda s: s.update(function="model.py:g"))
        changed(lambda s: s.update(batch=not s.get("batch", False), batch_size=None))
    else:
        changed(lambda s: s.update(command=[*s["command"], "--fast"]))
        changed(lambda s: s["predictions"][0]["parser"].update(key="z"))
    return out


def settings_changes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Specs that differ from ``spec`` only in settings, defaults written out, or key order (M3, 0029)."""
    out = [
        {**spec, "keep": "none"},
        {**spec, "timeout_s": 1},
        {**spec, "noisy": False, "pass_env": spec.get("pass_env", [])},
    ]
    if spec.get("batch"):
        out.append({**spec, "batch_size": 7})
    out.append(dict(reversed(list(spec.items()))))
    return out


def check_model_version(adapter: Any) -> None:
    """C33: M3 (a tracked file's byte, or a covered field, changes the model version; the directory's location,
    ``keep``, ``batch_size``, and ``timeout_s`` don't), and files compared as files (their contents, however the
    spec and the files are reached)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        spec_path = copy_model(adapter.kind, root / "a")
        model_dir = spec_path.parent
        original = json.loads(spec_path.read_text())

        def version(path: Path = spec_path) -> str:
            return adapter.load(str(path)).model_version_id

        base = version()
        assert version() == base, "loading twice gave two model versions"

        shutil.copytree(model_dir, root / "moved")
        assert version(root / "moved" / "model.json") == base, "moving the model's directory changed its version"
        (root / "alias").symlink_to(model_dir)
        assert version(root / "alias" / "model.json") == base, "a link to the directory changed the version"
        assert version(model_dir / ".." / model_dir.name / "model.json") == base
        (root / "elsewhere").mkdir()
        (root / "elsewhere" / "linked.json").symlink_to(spec_path)
        assert version(root / "elsewhere" / "linked.json") == base, "a link to the spec changed the model version"

        for variant in settings_changes(original):
            spec_path.write_text(json.dumps(variant, indent=4))
            assert version() == base, f"a setting or a default changed the model version: {variant}"

        seen = {base}
        for variant in covered_changes(original):
            spec_path.write_text(json.dumps(variant))
            changed = version()
            assert changed not in seen, f"a covered field didn't change the model version: {variant}"
            seen.add(changed)
        spec_path.write_text(json.dumps(original))
        assert version() == base

        for name in tracked_names(original):
            path = model_dir / name
            content = path.read_bytes()
            path.write_bytes(content + b" ")
            changed = version()
            assert changed not in seen, f"one byte changed in {name} didn't change the model version"
            seen.add(changed)
            path.write_bytes(content)
        assert version() == base

        outside = root / "data" / "mesh.dat"
        outside.parent.mkdir()
        shutil.copyfile(model_dir / "mesh.dat", outside)
        (model_dir / "mesh.dat").unlink()
        (model_dir / "mesh.dat").symlink_to(outside)
        assert version() == base, "a link to a file with the same contents changed the model version"
        outside.write_bytes(outside.read_bytes() + b"1")
        assert version() not in seen, "editing a linked file's target didn't change the model version"


# --------------------------------------------------------------------------------------------------------------
# Broken toys


# --------------------------------------------------------------------------------------------------------------
# C31, C32, C34–C44 (steps 04 and 05)


def check_failure_is_a_record(adapter: Any) -> None:
    """C31, M1: a function that raises, a program that exits nonzero, a crash (``os._exit``, a signal), a timeout,
    and a program that can't start each give a failed run of the right kind, with a one-line reason and no model
    predictions; nothing is raised."""
    command = adapter.kind == "command_line"
    with bench(adapter) as b:
        model = b.model(short_timeout)
        expected = {
            1: (FailureKind.ERROR, "exited with code 1" if command else "ZeroDivisionError: "),
            2: (FailureKind.ERROR, "killed by signal SIGKILL" if command else "the child exited with code 3"),
            3: (FailureKind.TIMEOUT, f"timeout after {TIMEOUT_S:g} s"),
        }
        for mode, (kind, reason) in expected.items():
            (run,) = runs_never_raising(b, model, point(mode))
            assert run.status is RunStatus.FAILED and run.kind is kind, (mode, run)
            assert reason in run.reason and "\n" not in run.reason, run.reason
            assert dict(run.predictions) == {} and dict(run.missing) == {}
        (run,) = runs_never_raising(b, model, point(1))
        if not command:
            assert "model.py:" in run.reason and "ZeroDivisionError" in run.stderr_tail, run
        else:
            assert run.exit_code == 1
            other = b.model(lambda s: s.update(command=["ema-no-such-program", "x"]), name="missing")
            (run,) = b.runs(other, point())
            assert run.kind is FailureKind.ERROR and "couldn't start ema-no-such-program" in run.reason
            assert run.exit_code is None


def check_no_stdin_no_secrets(adapter: Any) -> None:
    """C32, M2 and T2: a model gets end of file on stdin, and exactly the base variables EMA has, its ``pass_env``,
    and its ``env`` (which overrides the base): not a variable set in EMA's environment and in a ``.env`` beside the
    spec, and none EMA adds."""
    saved = {k: os.environ.get(k) for k in ("EMA_C32_SECRET", "EMA_C32_PASSED", "LC_EMA_C32")}
    os.environ.update(EMA_C32_SECRET="leaked", EMA_C32_PASSED="passed", LC_EMA_C32="base")
    try:
        with bench(adapter) as b:

            def edit(spec: dict[str, Any]) -> None:
                spec["pass_env"] = [*spec.get("pass_env", []), "EMA_C32_PASSED", "EMA_C32_UNSET"]
                spec["env"] = {**spec.get("env", {}), "HOME": "/ema-c32-home", "EMA_C32_SET": "set"}

            spec_path = b.spec_path()
            (spec_path.parent / ".env").write_text("EMA_C32_SECRET=leaked\nEMA_C32_DOTENV=1\n")
            model = b.model(edit)
            (run,) = b.runs(model, point(4))[:1]
            assert run.status is RunStatus.OK, run
            seen = json.loads((call_dir(run, b) / "inspect.json").read_text())
            env = seen["env"]
            assert seen["stdin"] == "", "the model read something from stdin"
            assert "EMA_C32_SECRET" not in env and "EMA_C32_DOTENV" not in env, "a secret reached the model"
            assert env["EMA_C32_PASSED"] == "passed" and env["EMA_C32_SET"] == "set" and env["LC_EMA_C32"] == "base"
            assert env["HOME"] == "/ema-c32-home", "the spec's env didn't override the base"
            assert "PATH" in env and "EMA_C32_UNSET" not in env
            allowed = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TZ", "LANG", "LD_LIBRARY_PATH"}
            allowed |= {"DYLD_LIBRARY_PATH", *model.spec.pass_env, *model.spec.env}
            extra = {k for k in env if k not in allowed and not k.startswith("LC_")} - {"__CF_USER_TEXT_ENCODING"}
            assert not extra, f"the model got variables it shouldn't: {sorted(extra)}"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def tracked_file(kind: str) -> str:
    return {"python": "model.py", "batch": "model.py", "command_line": "deck.in.template"}[kind]


def check_rehash(adapter: Any) -> None:
    """C34, M16: the tracked files are hashed again before a call; after an edit the next call is refused, naming
    the file, and the run already made is kept (its directory and ``run.json``). (The runner's refusal of the call
    is ``tests/contracts/runner.py``'s ``check_refused_call``.)"""
    with bench(adapter) as b:
        model = b.model()
        (first,) = b.runs(model, point())[:1]
        assert first.status is RunStatus.OK
        adapter.check_files(model)
        path = b.spec_path().parent / tracked_file(adapter.kind)
        path.write_text(path.read_text() + "\n")
        try:
            adapter.check_files(model)
        except ModelChanged as e:
            assert tracked_file(adapter.kind) in str(e), str(e)
        else:
            raise AssertionError("an edited tracked file wasn't found before the call")
        assert (b.runs_dir / first.run_id / "run.json").is_file(), "the run already made wasn't kept"


def check_predictions_read_or_missing(adapter: Any) -> None:
    """C35, M4 (0043), M7, M11: each model prediction is read, or missing with its own reason (a non-finite value
    included); a run that finished cleanly fails, kind ``unread``, only when none is read."""
    with bench(adapter) as b:
        model = b.model()
        names = [p.name for p in model.spec.predictions]
        if adapter.kind == "batch":
            nan_run, fine = b.runs(model, point(6), point(0))
            assert nan_run.status is RunStatus.FAILED and nan_run.kind is FailureKind.UNREAD, nan_run
            assert "nan" in nan_run.reason
            assert fine.status is RunStatus.OK and fine.predictions == {"y": 2.0}
        else:
            for mode, missing in ((9, names[1]), (6, "y")):
                (run,) = b.runs(model, point(mode))
                assert run.status is RunStatus.OK, (mode, run)
                assert run.predictions[missing] is None and run.missing[missing], run
                assert all(run.predictions[n] is not None for n in names if n != missing), run
            assert "nan" in b.runs(model, point(6))[0].missing["y"].lower()
        for run in b.runs(model, point(7), point(7)):
            assert run.status is RunStatus.FAILED and run.kind is FailureKind.UNREAD, run
            assert all(n in run.reason for n in names), run.reason


def check_complete_points(adapter: Any) -> None:
    """C36, M5: a model receives a value for every model parameter, held ones (at their nominal values) included."""
    with bench(adapter) as b:
        model = b.model()
        (run,) = b.runs(model, point(4))[:1]
        assert run.status is RunStatus.OK, run
        where = call_dir(run, b)
        seen = json.loads((where / "inspect.json").read_text())
        names = [p.name for p in model.spec.parameters]
        if adapter.kind == "python":
            assert seen["received"] == {"a": 1.0, "b": 0.5, "mode": 4}
        elif adapter.kind == "batch":
            assert seen["received"] == [[1.0, 0.5, 4.0]]
        else:
            assert {k: float(v) for k, v in seen["deck"].items() if k != "cost"} == {"a": 1.0, "b": 0.5, "mode": 4.0}
        stored = json.loads((b.runs_dir / run.run_id / "point.json").read_text())
        assert list(stored) == names and run.point == (1.0, 0.5, 4.0)


def check_batch(adapter: Any) -> None:
    """C37, M8 (0025): a batch call gives the same model predictions as the same function one point at a time; a
    non-finite row is missing for its run only; an exception or a wrong shape fails every run in the call, with one
    reason; each run records the call's time divided by its size, and the call's id. (Calls sized to ``batch_size``
    and to what remains approved are ``tests/contracts/runner.py``'s ``check_batch_sizes``.)"""
    with bench(adapter) as b:
        model = b.model()
        points = [point(0, a=x / 7, b=1 / (x + 3)) for x in range(5)]
        together = b.runs(model, *points)
        alone = [b.call(model, [p])[2][0] for p in points]
        assert [r.predictions for r in together] == [r.predictions for r in alone], "batch and one at a time differ"
        assert [r.predictions["y"] for r in together] == [p[0] + 2 * p[1] for p in points]
        _, executed, runs = b.call(model, points)
        ids = [r.run_id for r in runs]
        assert all(r.batch_call_id == batch_call_id(ids) for r in runs)
        assert all(r.time_s == executed.time_s / len(points) for r in runs)
        nan_rows = b.runs(model, point(0), point(6), point(0, a=2.0))
        assert [r.status for r in nan_rows] == [RunStatus.OK, RunStatus.FAILED, RunStatus.OK]
        for modes in ((0, 1, 0), (10, 0)):
            failed = b.runs(model, *[point(m, a=float(i)) for i, m in enumerate(modes)])
            assert all(r.status is RunStatus.FAILED and r.kind is FailureKind.ERROR for r in failed), failed
            assert len({r.reason for r in failed}) == 1, [r.reason for r in failed]


def check_isolation(adapter: Any) -> None:
    """C38, M9 (0026): a Python model runs in a child of its own, not in EMA's process; a crash, a timeout, or
    Ctrl-C kills its process group (a process the function started included), and the next call starts a new
    child."""
    with bench(adapter) as b:
        model = b.model(short_timeout)

        def pid_of_call() -> int:
            (run,) = b.runs(model, point(4))[:1]
            assert run.status is RunStatus.OK, run
            return int(json.loads((call_dir(run, b) / "inspect.json").read_text())["pid"])

        first = pid_of_call()
        assert first != os.getpid(), "the function ran in EMA's process"
        assert pid_of_call() == first, "a child wasn't kept between calls"
        (crash,) = b.runs(model, point(2))[:1]
        assert crash.kind is FailureKind.ERROR and "exited with code 3" in crash.reason
        second = pid_of_call()
        assert second != first and gone([first]), "a crashed child wasn't replaced"
        (hung,) = b.runs(model, point(3))[:1]
        assert hung.kind is FailureKind.TIMEOUT, hung
        pids = json.loads((call_dir(hung, b) / "pids.json").read_text())
        assert gone([pids["self"], pids["child"]]), "a timeout left a process of the call running"
        third = pid_of_call()
        assert third != second
        prepared = b.prepare(model, [point(3)])
        assert stopped(adapter, model, prepared, b.processes), "Ctrl-C didn't stop the call"
        pids = json.loads((Path(prepared.call_dir) / "pids.json").read_text())
        assert gone([pids["self"], pids["child"], third]), "Ctrl-C left a process of the call running"
        assert pid_of_call() not in (first, second, third)


def check_process(adapter: Any) -> None:
    """C39, M12, M20: a command runs without a shell (an argument with ``;`` is passed as written), in its own
    process group, which a timeout or Ctrl-C kills whole; a nonzero exit fails the run even when its model
    predictions can be read."""
    with bench(adapter) as b:
        literal = "x; echo injected > injected.txt"
        model = b.model(lambda s: s.update(command=[*s["command"], literal], timeout_s=TIMEOUT_S))
        (run,) = b.runs(model, point(4))
        seen = json.loads((b.runs_dir / run.run_id / "inspect.json").read_text())
        assert seen["argv"][-1] == literal and not (b.runs_dir / run.run_id / "injected.txt").exists()
        (run,) = b.runs(model, point(1))
        assert json.loads((b.runs_dir / run.run_id / "out.json").read_text())["y"] == 2.0
        assert run.status is RunStatus.FAILED and run.reason == "exited with code 1", run
        (run,) = b.runs(model, point(3))
        assert run.kind is FailureKind.TIMEOUT and run.exit_code is None, run
        pids = json.loads((b.runs_dir / run.run_id / "pids.json").read_text())
        assert gone([pids["self"], pids["child"]]), "a timeout left the program's processes running"
        prepared = b.prepare(model, [point(3, a=2.0)])
        assert stopped(adapter, model, prepared, b.processes), "Ctrl-C didn't stop the call"
        pids = json.loads((Path(prepared.call_dir) / "pids.json").read_text())
        assert gone([pids["self"], pids["child"]]), "Ctrl-C left the program's processes running"


def check_collect_from_files(adapter: Any) -> None:
    """C40, M13 (0028): collect reads the model predictions from files only: ``predictions.json`` for a Python
    function, the output parsers' files for a program; it never uses values held in memory."""
    with bench(adapter) as b:
        model = b.model()
        prepared, executed, (run,) = b.call(model, [point()])
        assert run.predictions["y"] == 2.0
        run_dir = Path(prepared.run_dirs[0])
        if adapter.kind == "command_line":
            (run_dir / "out.json").write_text('{"y": 99.0}')
        else:
            stored = json.loads((run_dir / "predictions.json").read_text())
            assert stored["predictions"]["y"] == 2.0, "predictions.json doesn't hold the stored values"
            stored["predictions"]["y"] = 99.0
            (run_dir / "predictions.json").write_text(json.dumps(stored))
        (again,) = adapter.collect(model, executed)
        assert again.predictions["y"] == 99.0, "collect didn't read the model predictions from the files"


def check_keep(adapter: Any) -> None:
    """C41, M14 (0020, 0028): ``keep`` keeps all, incomplete (failed, or a model prediction missing), or no run
    directories; a batch directory goes with the last of its runs'; a stopped call leaves no directory."""
    with bench(adapter) as b:
        incomplete = 6 if adapter.kind == "batch" else 9
        for keep in ("all", "incomplete", "none"):
            model = b.model(lambda s, keep=keep: s.update(keep=keep), name=f"keep-{keep}")
            cases = {"complete": point(0), "incomplete": point(incomplete, a=2.0), "failed": point(1, a=3.0)}
            for case, p in cases.items():
                prepared, _, runs = b.call(model, [p])
                adapter.keep_or_remove(model, prepared, runs)
                expected = keep == "all" or (keep == "incomplete" and case != "complete")
                assert Path(prepared.run_dirs[0]).exists() == expected, (keep, case)
                assert Path(prepared.call_dir).exists() == expected, (keep, case, "the call's directory")
        model = b.model(short_timeout)
        prepared = b.prepare(model, [point(3, a=4.0)])
        assert stopped(adapter, model, prepared, b.processes), "Ctrl-C didn't stop the call"
        adapter.discard(prepared)
        assert not any(Path(d).exists() for d in (*prepared.run_dirs, prepared.call_dir)), "a stopped run was kept"


def check_shared_files(adapter: Any) -> None:
    """C42, M15 (0030): a shared file is stored once, read-only, and linked into each run's directory; a model that
    writes to it fails; editing the source makes a new model version and a new stored copy, and older run
    directories still point to the old one."""
    with bench(adapter) as b:
        model = b.model()
        n = 4 if adapter.kind == "command_line" else 10  # a program's run costs a process start, about 50 ms
        runs = b.runs(model, *[point(0, a=float(i)) for i in range(n)])
        assert all(r.status is RunStatus.OK for r in runs)
        copies = sorted(b.shared_dir.glob("*/mesh.dat"))
        assert len(copies) == 1 and not os.access(copies[0], os.W_OK), "not one read-only stored copy"
        for run in runs:
            link = call_dir(run, b) / "mesh.dat"
            assert link.is_symlink() and os.path.samefile(link, copies[0]), "a run's shared file isn't the link"
        (written,) = b.runs(model, point(5))[:1]
        assert written.kind is FailureKind.ERROR, written
        assert copies[0].read_text() == "0.0\n"
        (b.spec_path().parent / "mesh.dat").write_text("1.0\n")
        edited = b.model()
        assert edited.model_version_id != model.model_version_id
        (run,) = b.runs(edited, point(0, a=1.0))[:1]
        assert run.predictions["y"] == 3.0 and len(list(b.shared_dir.glob("*/mesh.dat"))) == 2
        assert (call_dir(runs[0], b) / "mesh.dat").read_text() == "0.0\n", "an older run directory changed"


def check_templates(adapter: Any) -> None:
    """C43, M10: every value is written so that it reads back as the same double, a whole number with no decimal
    point; ``$$`` writes ``$``; a template name that isn't a model parameter is refused at loading."""
    with bench(adapter) as b:
        model = b.model()
        for p in ((0.1, 1e-300, 0.0), (64.0, -2.5, 3.0), (1 / 3, 0.1 + 0.2, -0.0)):
            prepared = b.prepare(model, [p])
            lines = (Path(prepared.call_dir) / "deck.in").read_text().splitlines()
            deck = dict(line.split(" = ") for line in lines)
            assert [float(deck[n]) for n in ("a", "b", "mode")] == list(p)
            assert all(math.copysign(1, float(deck[n])) == math.copysign(1, v) for n, v in zip("ab", p, strict=False))
            assert deck["cost"] == "$5"
            assert all(deck[n] == "64" for n in ("a",) if p[0] == 64.0) and "." not in deck["mode"]
        (b.spec_path().parent / "deck.in.template").write_text("a = $a\nx = $nope\n")
        try:
            adapter.load(str(b.spec_path()))
        except SpecError as e:
            assert "$nope" in str(e), str(e)
        else:
            raise AssertionError("a template name that isn't a model parameter loaded")


def check_run_record(adapter: Any) -> None:
    """C44, M19 (0029): each run records its host and its program's resolved path (a command found on ``PATH``: its
    absolute path; a Python function: the child's interpreter), as ``resolve_program`` shows it before any run; its
    ``run.json`` holds the same record."""
    with bench(adapter) as b:
        model = b.model()
        (run,) = b.runs(model, point())[:1]
        assert run.host == socket.gethostname()
        if adapter.kind == "command_line":
            found = shutil.which("python3", path=model.spec.env["PATH"])
            assert found is not None and run.program == os.path.abspath(found), run.program
        else:
            assert run.program == sys.executable
        assert os.path.isabs(run.program) and resolve_program(model) == run.program
        record = json.loads((b.runs_dir / run.run_id / "run.json").read_text())
        assert record["program"] == run.program and record["host"] == run.host
        assert record["status"] == "ok" and record["predictions"] == dict(run.predictions)
        assert record["point"] == dict(zip(["a", "b", "mode"], run.point, strict=True))


PARSER_CASES: dict[str, list[tuple[Any, str, float | str]]] = {
    # (settings, the file's text, the value read or a fragment of the reason it is missing)
    "regex": [
        (RegexParser("plate.out", r"T_max = (\S+)"), "T_max = 1\nT_max = 2.5e3\n", 2500.0),
        (RegexParser("plate.out", r"T_max = (\S+)", "first"), "T_max = 1\nT_max = 2.5e3\n", 1.0),
        (RegexParser("plate.out", r"T_max = (?P<value>\S+) (\S+)"), "T_max = -4 K\n", -4.0),
        (RegexParser("stdout", r"w = (\S+)"), "w = 0.5\n", 0.5),
        (RegexParser("plate.out", r"T_max = (\S+)"), "nothing here\n", "pattern not found"),
        (RegexParser("plate.out", r"T_max = (\S+)"), "T_max = inf\n", "not a finite number"),
        (RegexParser("plate.out", r"T_max = (\S+)"), "T_max = nan\n", "not a finite number"),
        (RegexParser("plate.out", r"T_max = (\S+)"), "T_max = hot\n", "not a number"),
    ],
    "json": [
        (JsonParser("out.json", "forces.drag"), '{"forces": {"drag": 0.25}}', 0.25),
        (JsonParser("out.json", "history.1.y"), '{"history": [{"y": 1}, {"y": 2}]}', 2.0),
        (JsonParser("out.json", "forces.lift"), '{"forces": {"drag": 0.25}}', "no key forces.lift"),
        (JsonParser("out.json", "y"), '{"y": Infinity}', "not a finite number"),
        (JsonParser("out.json", "y"), '{"y": true}', "not a number"),
        (JsonParser("out.json", "y"), "{", "not JSON"),
    ],
    "csv": [
        (CsvParser("h.csv", "drag"), "t,drag\n0,1.5\n1,2.5\n", 2.5),
        (CsvParser("h.csv", "drag", 0), "t, drag\n0,1.5\n1,2.5\n", 1.5),
        (CsvParser("h.csv", 1, 0, ";"), "0;7\n1;8\n", 7.0),
        (CsvParser("h.csv", "lift"), "t,drag\n0,1.5\n", "no column lift"),
        (CsvParser("h.csv", "drag", 5), "t,drag\n0,1.5\n", "no row 5"),
        (CsvParser("h.csv", "drag"), "t,drag\n0,-inf\n", "not a finite number"),
    ],
}


def check_parser(parser: Any) -> None:
    """C45, M11 (0027, 0030): each output parser kind reads its known answers, and makes the model prediction
    missing, with a reason, when it finds no file, no match or key, or a value that isn't a finite number; it never
    follows a link out of the run directory."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        run_dir, outside = root / "run", root / "outside"
        outside.mkdir()
        for i, (settings, text, expected) in enumerate(PARSER_CASES[parser.kind]):
            run_dir = root / f"run{i}"
            run_dir.mkdir()
            name = {"stdout": "stdout.txt", "stderr": "stderr.txt"}.get(settings.file, settings.file)
            (run_dir / name).write_text(text)
            value, reason = parser.read(settings, str(run_dir))
            if isinstance(expected, float):
                assert value == expected and reason is None, (settings, text, value, reason)
            else:
                assert value is None and expected in reason and settings.file in reason, (settings, reason)
            (run_dir / name).unlink()
            value, reason = parser.read(settings, str(run_dir))
            assert value is None and reason == f"{settings.file}: not found", reason
            good = (
                next(t for s, t, e in PARSER_CASES[parser.kind] if isinstance(e, float) and s == settings)
                if (isinstance(expected, float))
                else None
            )
            if good is not None:
                (outside / name).write_text(good)
                (run_dir / name).symlink_to(outside / name)
                value, reason = parser.read(settings, str(run_dir))
                assert value is None and reason == f"{settings.file}: outside the run directory", reason


# --------------------------------------------------------------------------------------------------------------
# Broken toys


def load_hashing_paths(path: str) -> LoadedModel:
    """Hashes the files' paths, not their contents."""
    model = load_spec(path)
    files = tuple(TrackedFile(f.path, sha256_hex(f.path), f.shared) for f in model.files)
    return replace(model, files=files, model_version_id=version_hash(model.spec, files))


def load_hashing_settings(path: str) -> LoadedModel:
    """Covers ``keep``, ``batch_size``, and ``timeout_s``."""
    model = load_spec(path)
    return replace(model, model_version_id=sha256_hex(model.spec.to_json() + model.model_version_id))


def load_hashing_location(path: str) -> LoadedModel:
    """Covers the model's directory."""
    model = load_spec(path)
    return replace(model, model_version_id=sha256_hex(canonical_json([model.model_dir, model.model_version_id])))


def execute_raising(model: LoadedModel, call: Any, processes: Any) -> Any:
    """Re-raises the model's failure (C31's negative control)."""
    executed = execute(model, call, processes)
    if executed.error or executed.timed_out or executed.exit_code:
        raise RuntimeError(executed.error or "the model failed")
    return executed


def prepare_with_parent_environment(model: LoadedModel, keys: Any, runs_dir: str, shared_dir: str, **kw: Any) -> Any:
    """Passes the parent's environment (C32's negative control)."""
    return replace(prepare(model, keys, runs_dir, shared_dir, **kw), env=dict(os.environ))


def files_checked_once(model: LoadedModel) -> None:
    """Hashes once, at loading (C34's negative control)."""


def collect_failing_any_missing(model: LoadedModel, call: Any) -> Any:
    """Fails the run when any model prediction is missing (C35's negative control)."""
    runs = collect(model, call)
    return tuple(
        replace(r, status=RunStatus.FAILED, kind=FailureKind.UNREAD, reason="missing", predictions={}, missing={})
        if r.missing
        else r
        for r in runs
    )


def execute_varied_only(model: LoadedModel, call: Any, processes: Any) -> Any:
    """Passes the varied model parameters only, not those at their nominal values (C36's negative control)."""
    varied = [i for i, p in enumerate(model.spec.parameters) if any(k.point[i] != p.nominal for k in call.keys)]
    spec = replace(model.spec, parameters=tuple(model.spec.parameters[i] for i in varied))
    reduced = replace(model, spec=spec, model_version_id="b" * 64)
    keys = tuple(replace(k, point=tuple(k.point[i] for i in varied)) for k in call.keys)
    return replace(execute(reduced, replace(call, keys=keys), processes), prepared=call)


def collect_failing_first_run_only(model: LoadedModel, call: Any) -> Any:
    """A failed batch call fails its first run only, with the call's reason (C37's negative control)."""
    runs = collect(model, call)
    if call.error is None:
        return runs
    rest = collect(model, replace(call, error=None))[1:]
    return (runs[0], *rest)


def execute_in_process(model: LoadedModel, call: Any, processes: Any) -> Any:
    """Runs the function in EMA's process (C38's negative control); only its ``mode`` 4 is ever called here."""
    file, _, name = model.spec.interface.function.rpartition(":")
    spec = importlib.util.spec_from_file_location("broken_in_process", os.path.join(model.model_dir, file))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, model.model_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(model.model_dir)
        sys.modules.pop("helper", None)
    names = [p.name for p in model.spec.parameters]
    error = None
    for key, run_dir in zip(call.keys, call.run_dirs, strict=True):
        cwd, stdin = os.getcwd(), sys.stdin
        os.chdir(call.call_dir)
        sys.stdin = io.StringIO("")
        try:
            value = getattr(module, name)(**dict(zip(names, key.point, strict=True)))
            out = value if isinstance(value, dict) else {model.spec.predictions[0].name: float(value)}
            write_own(run_dir, "predictions.json", json.dumps({"predictions": out, "missing": {}}).encode())
        except Exception as e:  # noqa: BLE001  (the broken toy records any failure)
            error = str(e)
        finally:
            os.chdir(cwd)
            sys.stdin = stdin
    return ExecutedCall(call, None, False, error, 0.0, socket.gethostname(), sys.executable)


def execute_through_a_shell(model: LoadedModel, call: Any, processes: Any) -> Any:
    """``shell=True`` (C39's negative control)."""
    with open(os.path.join(call.call_dir, "stdout.txt"), "w") as out:
        code = subprocess.call(" ".join(call.command), shell=True, cwd=call.call_dir, env=dict(call.env), stdout=out,
                               stdin=subprocess.DEVNULL)  # fmt: skip
    return ExecutedCall(call, code, False, None, 0.0, socket.gethostname(), "/bin/sh")


_IN_MEMORY: dict[str, Any] = {}


def execute_remembering(model: LoadedModel, call: Any, processes: Any) -> Any:
    executed = execute(model, call, processes)
    _IN_MEMORY[call.call_dir] = collect(model, executed)
    return executed


def collect_from_memory(model: LoadedModel, call: Any) -> Any:
    """Returns the values the call gave, held in memory (C40's negative control, with ``execute_remembering``)."""
    return _IN_MEMORY[call.prepared.call_dir]


def keep_everything(model: LoadedModel, call: Any, runs: Any) -> None:
    """Applies no ``keep`` setting (C41's negative control)."""


def discard_nothing(call: Any) -> None:
    """Keeps a stopped run's directory (C41's negative control)."""


def prepare_copying_shared(model: LoadedModel, keys: Any, runs_dir: str, shared_dir: str, **kw: Any) -> Any:
    """Copies a shared file into each run directory (C42's negative control)."""
    prepared = prepare(model, keys, runs_dir, shared_dir, **kw)
    for entry in model.spec.files:
        path = Path(prepared.call_dir, entry.path)
        if path.is_symlink():
            data = path.read_bytes()
            path.unlink()
            path.write_bytes(data)
    return prepared


def prepare_with_g(model: LoadedModel, keys: Any, runs_dir: str, shared_dir: str, **kw: Any) -> Any:
    """Writes values with ``%g`` (C43's negative control)."""
    prepared = prepare(model, keys, runs_dir, shared_dir, **kw)
    names = [p.name for p in model.spec.parameters]
    deck = Path(prepared.call_dir, "deck.in")
    lines = [f"{n} = {v:g}" for n, v in zip(names, keys[0].point, strict=True)]
    deck.write_text("\n".join([*lines, "cost = $5"]) + "\n")
    return prepared


def collect_command_as_typed(model: LoadedModel, call: Any) -> Any:
    """Records the command as typed (C44's negative control)."""
    return tuple(replace(r, program=model.spec.interface.command[0]) for r in collect(model, call))


class RegexReadingInf:
    """Parses ``inf`` as a value (C45's negative control)."""

    kind = "regex"

    def read(self, settings: Any, run_dir: str) -> tuple[float | None, str | None]:
        import re

        path = os.path.join(run_dir, {"stdout": "stdout.txt"}.get(settings.file, settings.file))
        if not os.path.exists(path):
            return None, f"{settings.file}: not found"
        if not is_within(path, run_dir):
            return None, f"{settings.file}: outside the run directory"
        found = list(re.finditer(settings.pattern, Path(path).read_text()))
        if not found:
            return None, f"{settings.file}: pattern not found"
        m = found[0] if settings.match == "first" else found[-1]
        raw = m.group("value") if "value" in m.re.groupindex else m.group(1)
        try:
            return float(raw), None
        except ValueError:
            return None, f"{settings.file}: {raw!r} is not a number"


class JsonFollowingLinks:
    """Follows a link out of the run directory (C45's negative control)."""

    kind = "json"

    def read(self, settings: Any, run_dir: str) -> tuple[float | None, str | None]:
        if not os.path.lexists(os.path.join(run_dir, settings.file)):
            return None, f"{settings.file}: not found"
        os.rename(os.path.join(run_dir, settings.file), os.path.join(run_dir, "followed.json"))
        os.symlink(os.path.realpath(os.path.join(run_dir, "followed.json")), os.path.join(run_dir, settings.file))
        return parsers.get("json").read(replace(settings, file="followed.json"), run_dir)


BROKEN: dict[str, list[Any]] = {
    "check_model_version": [
        Adapter("command_line", load_hashing_paths),
        Adapter("python", load_hashing_settings),
        Adapter("batch", load_hashing_location),
    ],
    "check_failure_is_a_record": [Adapter("python", execute=execute_raising)],
    "check_no_stdin_no_secrets": [Adapter("command_line", prepare=prepare_with_parent_environment)],
    "check_rehash": [Adapter("python", check_files=files_checked_once)],
    "check_predictions_read_or_missing": [Adapter("command_line", collect=collect_failing_any_missing)],
    "check_complete_points": [Adapter("python", execute=execute_varied_only)],
    "check_batch": [Adapter("batch", collect=collect_failing_first_run_only)],
    "check_isolation": [Adapter("python", execute=execute_in_process)],
    "check_process": [Adapter("command_line", execute=execute_through_a_shell)],
    "check_collect_from_files": [Adapter("python", execute=execute_remembering, collect=collect_from_memory)],
    "check_keep": [Adapter("python", keep_or_remove=keep_everything), Adapter("python", discard=discard_nothing)],
    "check_shared_files": [Adapter("command_line", prepare=prepare_copying_shared)],
    "check_templates": [Adapter("command_line", prepare=prepare_with_g)],
    "check_run_record": [Adapter("command_line", collect=collect_command_as_typed)],
    "check_parser": [RegexReadingInf(), JsonFollowingLinks()],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}

#: The kinds of model each check runs over (contracts.md, "Run over"); all three when not listed.
RUN_OVER = {
    "check_batch": ("batch",),
    "check_isolation": ("python", "batch"),
    "check_process": ("command_line",),
    "check_templates": ("command_line",),
}


#: The variants in the slow tier (contracts.md, Test tiers: the fast tier's 30 s): a batch variant that runs the
#: Python variant's child again, with timeouts and Ctrl-C; and ``check_keep`` over a program (nine process starts),
#: whose rule reads only the runs' statuses, as over the Python model, and whose Ctrl-C ``check_process`` checks.
SLOW = {
    "check_failure_is_a_record": ("batch",),
    "check_isolation": ("batch",),
    "check_keep": ("batch", "command_line"),
}


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "adapter" in metafunc.fixturenames:
        name = metafunc.function.__name__
        kinds = RUN_OVER.get(name, KINDS)
        params = [pytest.param(Adapter(k), marks=[pytest.mark.slow] if k in SLOW.get(name, ()) else [], id=k)
                  for k in kinds]  # fmt: skip
        metafunc.parametrize("adapter", params)
    if "parser" in metafunc.fixturenames:
        metafunc.parametrize("parser", [parsers.get(k) for k in parsers.names()], ids=list(parsers.names()))


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)
