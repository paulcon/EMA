"""Executing and collecting a call: what the contract doesn't cover (M19, M20; T2, T9; 0028, 0057; record 0071).

``ema.runner`` will be the only importer of ``ema.models.execute`` in ``ema`` (AR4); tests call it directly.
"""

import json
import os
import select
from pathlib import Path

import pytest

from ema.models.collect import collect, discard, keep_or_remove, kept, stderr_tail
from ema.models.execute import execute
from ema.models.prepare import prepare
from ema.models.processes import ModelProcesses
from ema.models.spec import load_spec, resolve_program
from ema.types.runs import FailureKind, RunKey, RunStatus
from tests.support.models import APPROVAL, copy_model, gone, point


def command_model(tmp_path: Path, command: list[str], *, script: str | None = None, env: dict | None = None,
                  parser: dict | None = None, keep: str = "all"):  # fmt: skip
    """A one-parameter command-line model; ``script`` is written to ``prog``, listed and executable."""
    directory = tmp_path / "model"
    directory.mkdir()
    files = []
    if script is not None:
        (directory / "prog").write_text(script)
        (directory / "prog").chmod(0o755)
        files.append("prog")
    spec = {"name": "c", "description": "d", "interface": "command_line", "command": command, "files": files,
            "parameters": [{"name": "a", "units": "", "nominal": 1.0, "description": "a"}],
            "predictions": [{"name": "y", "units": "", "description": "y",
                             "parser": parser or {"kind": "regex", "file": "stdout", "pattern": "y = (\\S+)"}}],
            "keep": keep, "timeout_s": 5}  # fmt: skip
    if env is not None:
        spec["env"] = env
    (directory / "model.json").write_text(json.dumps(spec))
    return load_spec(str(directory / "model.json"))


def run(model, tmp_path: Path, x: float = 1.0, processes=None, between=None):
    key = RunKey.make(model.model_version_id, (x,) if len(model.spec.parameters) == 1 else point(x), 0, 0)
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    executed = execute(model, call, processes or ModelProcesses())
    if between is not None:
        between(Path(call.call_dir))
    (result,) = collect(model, executed)
    return result, call


def test_m19_a_program_given_with_a_slash_runs_from_the_run_directory(tmp_path):
    model = command_model(tmp_path, ["./prog"], script="#!/bin/sh\necho y = 2.5\n")
    result, call = run(model, tmp_path)
    assert result.status is RunStatus.OK and result.predictions["y"] == 2.5
    assert result.program == os.path.join(call.call_dir, "prog") and result.exit_code == 0
    assert resolve_program(model) == str(tmp_path.resolve() / "model" / "prog")


def test_t2_a_program_left_in_the_run_directory_is_not_run_from_a_base_path_ending_in_a_colon(tmp_path, monkeypatch):
    """A base PATH ending in ':' (the run directory, to a shell) doesn't run the copy in the run directory."""
    monkeypatch.setenv("PATH", f"{os.environ['PATH']}:")
    model = command_model(tmp_path, ["prog"], script="#!/bin/sh\necho y = 2.5\n")
    result, _ = run(model, tmp_path)
    assert result.kind is FailureKind.ERROR and result.reason == "couldn't start prog: not found on the model's PATH"
    assert result.program == "prog" and resolve_program(model) is None


def test_m20_what_a_finished_program_left_running_is_killed(tmp_path):
    """Record 0071: the program's process group is killed when it exits, so nothing writes to its directory later."""
    model = command_model(
        tmp_path, ["sh", "-c", "sleep 30 & echo $! > bg.pid; echo y = 1"], env={"PATH": "/bin:/usr/bin"}
    )
    result, call = run(model, tmp_path)
    assert result.status is RunStatus.OK
    assert gone([int(Path(call.call_dir, "bg.pid").read_text())])


def test_t9_a_parsers_file_linked_out_of_the_run_directory_is_missing(tmp_path):
    outside = tmp_path / "secret.json"
    outside.write_text('{"y": 7}')
    model = command_model(tmp_path, ["sh", "-c", f"ln -s {outside} out.json"], env={"PATH": "/bin:/usr/bin"},
                          parser={"kind": "json", "file": "out.json", "key": "y"})  # fmt: skip
    result, _ = run(model, tmp_path)
    assert result.kind is FailureKind.UNREAD and "out.json: outside the run directory" in result.reason


def test_t9_run_json_left_as_a_link_is_replaced_and_its_target_unchanged(tmp_path):
    outside = tmp_path / "data.txt"
    outside.write_text("data")
    model = command_model(tmp_path, ["sh", "-c", f"ln -s {outside} run.json; echo y = 1"], env={"PATH": "/bin"})
    result, call = run(model, tmp_path)
    assert result.status is RunStatus.OK and outside.read_text() == "data"
    record = Path(call.call_dir, "run.json")
    assert not record.is_symlink() and json.loads(record.read_text())["run_id"] == result.run_id


def test_t9_a_directory_at_run_json_fails_the_run(tmp_path):
    model = command_model(tmp_path, ["sh", "-c", "mkdir run.json; echo y = 1"], env={"PATH": "/bin"})
    result, _ = run(model, tmp_path)
    assert result.kind is FailureKind.ERROR and result.reason.startswith("run.json: couldn't be written:")
    assert result.predictions == {}


def test_t9_predictions_json_left_as_a_link_by_the_function(tmp_path):
    """EMA's predictions.json is written without following the link a function left; the target is unchanged."""
    outside = tmp_path / "data.txt"
    outside.write_text("data")
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / "model.py").write_text(f"import os\ndef f(a):\n    os.symlink({str(outside)!r}, 'predictions.json')\n"
                                        "    return a\n")  # fmt: skip
    spec = {"name": "p", "description": "d", "interface": "python_function", "function": "model.py:f",
            "parameters": [{"name": "a", "units": "", "nominal": 1.0, "description": "a"}],
            "predictions": [{"name": "y", "units": "", "description": "y"}]}  # fmt: skip
    (directory / "model.json").write_text(json.dumps(spec))
    processes = ModelProcesses()
    try:
        result, call = run(load_spec(str(directory / "model.json")), tmp_path, 3.0, processes)
    finally:
        processes.close()
    assert result.predictions["y"] == 3.0 and outside.read_text() == "data"
    assert not Path(call.call_dir, "predictions.json").is_symlink()


def test_the_stderr_tail_is_its_last_15_lines(tmp_path):
    lines = "; ".join(f"echo line{i} >&2" for i in range(20))
    model = command_model(tmp_path, ["sh", "-c", f"{lines}; exit 3"], env={"PATH": "/bin"})
    result, call = run(model, tmp_path)
    assert result.reason == "exited with code 3" and result.exit_code == 3
    assert result.stderr_tail == "\n".join(f"line{i}" for i in range(5, 20))
    assert stderr_tail(call.call_dir) == result.stderr_tail


def test_a_run_reads_its_predictions_only_from_files_never_its_memory(tmp_path):
    """M13 at the collect level: a deleted predictions.json makes the run fail, kind error."""
    model = load_spec(str(copy_model("python", tmp_path)))
    processes = ModelProcesses()
    try:
        result, _ = run(model, tmp_path, 0.0, processes, between=lambda d: Path(d, "predictions.json").unlink())
    finally:
        processes.close()
    assert result.kind is FailureKind.ERROR and result.reason.startswith("predictions.json: couldn't be read")


@pytest.mark.parametrize(
    ("keep", "complete", "missing", "failed"),
    [("all", True, True, True), ("incomplete", False, True, True), ("none", False, False, False)],
)
def test_m14_kept(tmp_path, keep, complete, missing, failed):
    spec_path = copy_model("python", tmp_path)
    text = json.loads(spec_path.read_text())
    text["keep"] = keep
    spec_path.write_text(json.dumps(text))
    model = load_spec(str(spec_path))
    processes = ModelProcesses()
    try:
        results = [run(model, tmp_path, mode, processes)[0] for mode in (0, 9, 1)]
    finally:
        processes.close()
    assert [kept(model, r) for r in results] == [complete, missing, failed]


def test_a_batch_directory_goes_with_the_last_of_its_runs(tmp_path):
    model = load_spec(str(copy_model("batch", tmp_path)))
    processes = ModelProcesses()
    try:
        batch = [RunKey.make(model.model_version_id, point(m, a=float(i)), 0, 0) for i, m in enumerate((0, 6))]
        call = prepare(model, batch, str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
        runs = collect(model, execute(model, call, processes))
    finally:
        processes.close()
    keep_or_remove(model, call, runs)  # keep "incomplete": the NaN row's run is kept, and the batch directory
    assert [Path(d).exists() for d in call.run_dirs] == [False, True] and Path(call.call_dir).exists()
    discard(call)
    assert not any(Path(d).exists() for d in (*call.run_dirs, call.call_dir))


@pytest.fixture
def python_sigint():
    """Python's own SIGINT handler (Ctrl-C raises KeyboardInterrupt), restored afterwards."""
    import signal

    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    yield
    signal.signal(signal.SIGINT, previous)


def test_m20_c39_ctrl_c_inside_popen_kills_the_program(tmp_path, monkeypatch, python_sigint):
    """Review round 1 (record 0071): a SIGINT inside Popen, after the fork, is held and delivered once the program
    can be killed; the program is gone and KeyboardInterrupt is raised."""
    import signal
    import subprocess

    started = []
    real = subprocess.Popen

    class Interrupted(real):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            started.append(self.pid)
            os.kill(os.getpid(), signal.SIGINT)  # Ctrl-C before Popen returns

    model = command_model(tmp_path, ["sh", "-c", "sleep 30"], env={"PATH": "/bin"})
    key = RunKey.make(model.model_version_id, (1.0,), 0, 0)
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    monkeypatch.setattr(subprocess, "Popen", Interrupted)
    with pytest.raises(KeyboardInterrupt):
        execute(model, call, ModelProcesses())
    assert started and gone(started)
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_m20_a_sigint_ignored_before_the_start_stays_ignored(tmp_path, monkeypatch):
    """The held SIGINT goes to the handler that was there: one that ignores it lets the run finish."""
    import signal
    import subprocess

    real = subprocess.Popen

    class Interrupted(real):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            os.kill(os.getpid(), signal.SIGINT)

    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        model = command_model(tmp_path, ["sh", "-c", "echo y = 2"], env={"PATH": "/bin"})
        monkeypatch.setattr(subprocess, "Popen", Interrupted)
        result, _ = run(model, tmp_path)
    finally:
        signal.signal(signal.SIGINT, previous)
    assert result.status is RunStatus.OK and result.predictions["y"] == 2.0


@pytest.mark.parametrize(
    "error", [OSError(38, "Function not implemented"), PermissionError(1, "Operation not permitted")]
)
def test_a_refused_pidfd_falls_back_to_polling(tmp_path, monkeypatch, error):
    """Review round 1: ENOSYS (an old kernel) or EPERM (a seccomp filter) from pidfd_open fails no run."""

    def refused(pid, flags=0):
        raise error

    monkeypatch.setattr(os, "pidfd_open", refused, raising=False)
    (tmp_path / "ok").mkdir()
    model = command_model(tmp_path / "ok", ["sh", "-c", "echo y = 2"], env={"PATH": "/bin"})
    result, _ = run(model, tmp_path / "ok")
    assert result.status is RunStatus.OK and result.predictions["y"] == 2.0 and result.exit_code == 0
    (tmp_path / "slow").mkdir()
    model = command_model(tmp_path / "slow", ["sh", "-c", "sleep 30"], env={"PATH": "/bin"})
    text = json.loads(Path(model.spec_path).read_text())
    text["timeout_s"] = 0.2
    Path(model.spec_path).write_text(json.dumps(text))
    result, _ = run(load_spec(model.spec_path), tmp_path / "slow")
    assert result.kind is FailureKind.TIMEOUT and result.time_s < 2


def with_timeout(model, timeout_s: float):
    text = json.loads(Path(model.spec_path).read_text())
    text["timeout_s"] = timeout_s
    Path(model.spec_path).write_text(json.dumps(text))
    return load_spec(model.spec_path)


@pytest.mark.parametrize("wait", ["pidfd", "kqueue"])
def test_m1_a_timeout_of_centuries_raises_nothing(tmp_path, monkeypatch, wait):
    """Review round 2 (record 0071; M1, M20): ``poll`` takes whole milliseconds as a C int, and kqueue a timespec, so
    a ``timeout_s`` past about 24.8 days (here 1e300) overflowed; each wait is capped at 60 s and checked again."""
    if wait == "pidfd":  # a pidfd that is always readable: each wakeup is early, and only waits again

        def always_readable(pid, flags=0):
            r, w = os.pipe()
            os.close(w)
            return r

        monkeypatch.setattr(os, "pidfd_open", always_readable, raising=False)
    elif hasattr(os, "pidfd_open") or not hasattr(select, "kqueue"):
        pytest.skip("kqueue is used only where there is no pidfd")
    model = with_timeout(command_model(tmp_path, ["sh", "-c", "sleep 0.1; echo y = 2"], env={"PATH": "/bin"}), 1e300)
    result, _ = run(model, tmp_path)
    assert result.status is RunStatus.OK and result.predictions["y"] == 2.0 and result.time_s < 5


def test_m1_a_number_beyond_a_double_in_predictions_json_is_missing(tmp_path):
    """Review round 1: collect never raises (an integer of 400 digits isn't a finite double)."""
    model = load_spec(str(copy_model("python", tmp_path)))
    huge = "1" + "0" * 400

    def rewrite(directory):
        Path(directory, "predictions.json").unlink()
        Path(directory, "predictions.json").write_text(f'{{"predictions": {{"y": {huge}, "z": 2}}, "missing": {{}}}}')

    processes = ModelProcesses()
    try:
        result, _ = run(model, tmp_path, 0.0, processes, between=rewrite)
    finally:
        processes.close()
    assert result.status is RunStatus.OK and result.predictions == {"y": None, "z": 2.0}
    assert result.missing == {"y": "predictions.json: not a finite number"}


@pytest.mark.parametrize("content", ['{"predictions": [["y", 1]], "missing": {}}', "[" * 100_000, "5"])
def test_m1_predictions_json_that_isnt_emas_fails_the_run(tmp_path, content):
    model = load_spec(str(copy_model("python", tmp_path)))

    def rewrite(directory):
        Path(directory, "predictions.json").unlink()
        Path(directory, "predictions.json").write_text(content)

    processes = ModelProcesses()
    try:
        result, _ = run(model, tmp_path, 0.0, processes, between=rewrite)
    finally:
        processes.close()
    assert result.kind is FailureKind.ERROR and result.reason == "predictions.json: not EMA's model predictions"


def test_the_stderr_tail_reads_only_the_end_and_only_for_a_failed_run(tmp_path, monkeypatch):
    """Review round 1: the last 64 KiB of a large stderr.txt; a run that is ok reads none."""
    from ema.models import collect as collect_module

    lines = "head\n" * 400_000 + "".join(f"line{i}\n" for i in range(20))
    model = command_model(tmp_path, ["sh", "-c", "cat big >&2; exit 3"], env={"PATH": "/bin"})
    key = RunKey.make(model.model_version_id, (1.0,), 0, 0)
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    Path(call.call_dir, "big").write_text(lines)
    (result,) = collect(model, execute(model, call, ModelProcesses()))
    assert result.stderr_tail == "\n".join(f"line{i}" for i in range(5, 20))
    from ema.models.parsers import read_inside

    data, _ = read_inside(call.call_dir, "stderr.txt", 1 << 16)
    assert data is not None and len(data) == 1 << 16 and data.endswith(b"line19\n")

    def never(call_dir):
        raise AssertionError("an ok run's stderr was read")

    monkeypatch.setattr(collect_module, "stderr_tail", never)
    (tmp_path / "ok").mkdir()
    ok = command_model(tmp_path / "ok", ["sh", "-c", "echo y = 1"], env={"PATH": "/bin"})
    result, _ = run(ok, tmp_path / "ok")
    assert result.status is RunStatus.OK and result.stderr_tail is None


def test_m1_a_stream_file_the_call_cant_create_fails_the_run(tmp_path):
    """Review round 1: stdout.txt already in the run directory fails the run, kind error; nothing raises."""
    model = command_model(tmp_path, ["sh", "-c", "echo y = 1"], env={"PATH": "/bin"})
    key = RunKey.make(model.model_version_id, (1.0,), 0, 0)
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    Path(call.call_dir, "stderr.txt").write_text("left")
    (result,) = collect(model, execute(model, call, ModelProcesses()))
    assert result.kind is FailureKind.ERROR and result.reason.startswith("couldn't start sh: stderr.txt:")
