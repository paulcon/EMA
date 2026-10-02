"""The environment a model gets, the program's lookup, and the Python child (trust.md, T2, T9; M2, M9; 0026, 0057;
record 0069 item 34, record 0071)."""

import json
import os
import py_compile
from pathlib import Path

import pytest

from ema.models import sandbox
from ema.models.collect import collect
from ema.models.execute import execute
from ema.models.prepare import prepare
from ema.models.processes import ModelProcesses
from ema.models.sandbox import BASE_ENV, describe_exit, find_program, model_environment
from ema.models.spec import load_spec
from ema.types.model import CommandLine, ModelParameter, ModelSpec, PredictionSpec, PythonFunction
from ema.types.runs import FailureKind, RunKey, RunStatus
from tests.support.models import APPROVAL, copy_model, point


def spec(**fields) -> ModelSpec:
    return ModelSpec(
        "m", "d", PythonFunction("model.py:f"), (ModelParameter("a", "", "", 1.0),), (PredictionSpec("y", "", ""),),
        **fields,
    )  # fmt: skip


class TestEnvironment:
    def test_base_env_is_trust_md_list(self):
        assert set(BASE_ENV) == {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TZ", "LANG",
                                 "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"}  # fmt: skip

    def test_t2_only_the_base_pass_env_and_env(self):
        environ = {"PATH": "/usr/bin", "HOME": "/h", "LC_ALL": "C", "LCX": "no", "ANTHROPIC_API_KEY": "secret",
                   "LM_LICENSE_FILE": "27000@lic", "OMP_NUM_THREADS": "8"}  # fmt: skip
        env = model_environment(spec(pass_env=("LM_LICENSE_FILE", "UNSET_NAME"), env={"HOME": "/x"}), environ)
        assert env == {"PATH": "/usr/bin", "HOME": "/x", "LC_ALL": "C", "LM_LICENSE_FILE": "27000@lic"}

    def test_t2_empty_and_relative_base_path_entries_are_dropped(self):
        env = model_environment(spec(), {"PATH": "/usr/bin::bin:./x:/opt/bin:"})
        assert env["PATH"] == "/usr/bin:/opt/bin"

    def test_an_env_path_is_taken_as_written(self):
        env = model_environment(spec(env={"PATH": "/opt/a:/opt/b"}), {"PATH": "/usr/bin:"})
        assert env["PATH"] == "/opt/a:/opt/b"

    def test_a_pass_env_name_in_the_base_changes_nothing(self):
        environ = {"PATH": "/usr/bin", "HOME": "/h"}
        assert model_environment(spec(pass_env=("HOME",)), environ) == model_environment(spec(), environ)

    def test_reads_ema_environment_by_default(self, monkeypatch):
        monkeypatch.setenv("EMA_SANDBOX_SECRET", "x")
        monkeypatch.setenv("LANG", "C")
        env = model_environment(spec())
        assert "EMA_SANDBOX_SECRET" not in env and env["LANG"] == "C"


class TestFindProgram:
    def test_a_name_on_the_models_path(self, tmp_path):
        program = tmp_path / "bin" / "solver"
        program.parent.mkdir()
        program.write_text("#!/bin/sh\n")
        program.chmod(0o755)
        assert find_program("solver", {"PATH": f"/nonexistent:{program.parent}"}, None) == str(program)
        assert find_program("solver", {"PATH": "/nonexistent"}, None) is None

    def test_a_path_with_a_slash_is_resolved_in_the_directory(self, tmp_path):
        (tmp_path / "solver").write_text("#!/bin/sh\n")
        assert find_program("./solver", {}, str(tmp_path)) is None, "not executable"
        (tmp_path / "solver").chmod(0o755)
        assert find_program("./solver", {}, str(tmp_path)) == str(tmp_path / "solver")
        assert find_program("/bin/sh", {}, str(tmp_path)) == "/bin/sh"

    def test_a_relative_path_entry_is_never_searched(self, tmp_path, monkeypatch):
        """T2: with no absolute entry naming it, a program left in the working directory isn't found."""
        (tmp_path / "solver").write_text("#!/bin/sh\n")
        (tmp_path / "solver").chmod(0o755)
        monkeypatch.chdir(tmp_path)
        env = model_environment(spec(), {"PATH": "/usr/bin::."})
        assert find_program("solver", env, str(tmp_path)) is None


def test_describe_exit():
    assert describe_exit(2, "") == "exited with code 2"
    assert describe_exit(-9, "") == "killed by signal SIGKILL"
    assert describe_exit(-9, "the child ") == "the child was killed by signal SIGKILL"


def write_model(directory: Path, source: str, function: str = "model.py:f", files=()) -> Path:
    """A one-parameter Python model whose function file is ``source``."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / function.partition(":")[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    model = {"name": "m", "description": "d", "interface": "python_function", "function": function,
             "files": list(files), "parameters": [{"name": "a", "units": "", "nominal": 1.0, "description": "a"}],
             "predictions": [{"name": "y", "units": "", "description": "y"}], "timeout_s": 10}  # fmt: skip
    (directory / "model.json").write_text(json.dumps(model))
    return directory / "model.json"


@pytest.fixture
def processes():
    p = ModelProcesses()
    yield p
    p.close()


def run_once(spec_path: Path, tmp_path: Path, processes, x: float = 1.0, env_edit=None):
    model = load_spec(str(spec_path))
    key = RunKey.make(model.model_version_id, (x,), 0, 0)
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    if env_edit is not None:
        call = env_edit(call)
    (run,) = collect(model, execute(model, call, processes))
    return run, Path(call.call_dir)


class TestChild:
    def test_t2_imports_through_emas_sys_path_and_not_pythonpath(self, tmp_path, processes, monkeypatch):
        """The child imports what EMA can (a module reachable only through EMA's sys.path), and a PYTHONPATH in the
        model's environment doesn't change its imports; the model's directory is first, the worker's isn't there."""
        reachable = tmp_path / "ema_path"
        reachable.mkdir()
        (reachable / "ema_t2_probe.py").write_text("VALUE = 2.0\n")
        shadow = tmp_path / "shadow"
        shadow.mkdir()
        (shadow / "helper.py").write_text("VALUE = 99.0\n")
        monkeypatch.syspath_prepend(str(reachable))
        source = (
            "import json, os, sys\nimport ema, numpy, ema_t2_probe, helper\n"
            "def f(a):\n"
            "    json.dump({'path': sys.path, 'env': os.environ.get('PYTHONPATH')}, open('seen.json', 'w'))\n"
            "    return ema_t2_probe.VALUE + helper.VALUE\n"
        )  # fmt: skip
        spec_path = write_model(tmp_path / "m", source, files=["helper.py"])
        (tmp_path / "m" / "helper.py").write_text("VALUE = 1.0\n")
        text = json.loads(spec_path.read_text())
        text["env"] = {"PYTHONPATH": str(shadow)}
        spec_path.write_text(json.dumps(text))
        run, where = run_once(spec_path, tmp_path, processes)
        assert run.status is RunStatus.OK and run.predictions["y"] == 3.0, run
        seen = json.loads((where / "seen.json").read_text())
        model_dir = str((tmp_path / "m").resolve())
        assert seen["path"][0] == model_dir and seen["env"] == str(shadow)
        assert str(shadow) not in seen["path"] and str(Path(sandbox.WORKER).parent) not in seen["path"]
        assert all(os.path.isabs(p) for p in seen["path"])

    def test_omp_num_threads_is_set_when_the_child_starts(self, tmp_path, processes):
        """T2: a variable a library reads when it loads takes effect (the toy reads it at import)."""
        model = load_spec(str(copy_model("python", tmp_path)))
        key = RunKey.make(model.model_version_id, point(4), 0, 0)
        call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
        execute(model, call, processes)
        assert json.loads(Path(call.call_dir, "inspect.json").read_text())["started_with"] == "1"

    def test_0069_item_34_a_function_in_a_subdirectory_is_a_dotted_module(self, tmp_path, processes):
        spec_path = write_model(tmp_path / "m", "from .helper import VALUE\ndef f(a):\n    return a + VALUE\n",
                                function="sub/model.py:f", files=["sub/helper.py"])  # fmt: skip
        (tmp_path / "m" / "sub" / "helper.py").write_text("VALUE = 0.5\n")
        run, _ = run_once(spec_path, tmp_path, processes)
        assert run.status is RunStatus.OK and run.predictions["y"] == 1.5, run

    def test_p3_a_stale_cached_pyc_is_never_run(self, tmp_path, processes):
        """A cached .pyc with the source's size and time to the second would run old code under a new version."""
        old, new = "def f(a):\n    return 1.0\n", "def f(a):\n    return 2.0\n"
        spec_path = write_model(tmp_path / "m", old)
        source = tmp_path / "m" / "model.py"
        py_compile.compile(str(source))
        stamp = source.stat()
        source.write_text(new)
        os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        run, _ = run_once(spec_path, tmp_path, processes)
        assert run.predictions["y"] == 2.0

    def test_an_import_failure_fails_the_run_with_its_traceback(self, tmp_path, processes):
        spec_path = write_model(tmp_path / "m", "import no_such_module_ema\ndef f(a):\n    return a\n")
        run, where = run_once(spec_path, tmp_path, processes)
        assert run.kind is FailureKind.ERROR and run.reason.startswith("couldn't load model.py:f: ModuleNotFoundError")
        assert "model.py:1" in run.reason and "no_such_module_ema" in run.stderr_tail
        assert "Traceback" in (where / "stderr.txt").read_text()

    def test_t9_streams_never_reach_emas_stdout(self, tmp_path, processes, capfd):
        """What the function prints at import goes to EMA's stderr, and in a call to the call's files."""
        model = load_spec(str(copy_model("python", tmp_path)))
        key = RunKey.make(model.model_version_id, point(8), 0, 0)
        call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
        (run,) = collect(model, execute(model, call, processes))
        assert run.status is RunStatus.OK
        out, err = capfd.readouterr()
        assert out == "" and "printed at import" in err
        assert Path(call.call_dir, "stdout.txt").read_text() == "out-line\n"
        assert Path(call.call_dir, "stderr.txt").read_text() == "err-line\n"

    def test_sys_exit_fails_the_call_and_keeps_the_child(self, tmp_path, processes):
        spec_path = write_model(
            tmp_path / "m", "import os, sys\ndef f(a):\n    if a < 0: sys.exit(4)\n    return os.getpid()\n"
        )
        first, _ = run_once(spec_path, tmp_path, processes)
        failed, _ = run_once(spec_path, tmp_path, processes, x=-1.0)
        again, _ = run_once(spec_path, tmp_path, processes, x=2.0)
        assert failed.kind is FailureKind.ERROR and failed.reason.startswith("SystemExit: 4")
        assert again.predictions["y"] == first.predictions["y"]

    def test_m7_returns(self, tmp_path, processes):
        """M7: a float, a mapping, a non-finite value, and extra names; a number for two model predictions fails."""
        source = (
            "import math\n"
            "def f(a):\n"
            "    return {1: 1.0, 2: {'y': 1.0}, 3: {'y': math.nan}, 4: {'y': 1.0, 'zz': 2.0}, 5: {'y': 'x'}}[int(a)]\n"
        )
        spec_path = write_model(tmp_path / "m", source)
        results = [run_once(spec_path, tmp_path, processes, x=float(i))[0] for i in range(1, 6)]
        assert [r.predictions.get("y") for r in results] == [1.0, 1.0, None, 1.0, None]
        assert results[2].kind is FailureKind.UNREAD and "nan" in results[2].reason
        assert "str, not a number" in results[4].reason
        text = json.loads(spec_path.read_text())
        text["predictions"].append({"name": "z", "units": "", "description": "z"})
        spec_path.write_text(json.dumps(text))
        run, _ = run_once(spec_path, tmp_path, processes, x=1.0)
        assert run.kind is FailureKind.ERROR and "returns a mapping" in run.reason


def test_the_model_package_never_unpickles():
    """C38, M9: nothing in ema.models imports a module that runs code to read data."""
    import ast

    source = Path(sandbox.__file__).parent
    for path in source.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            names += [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not {n.split(".")[0] for n in names} & {"pickle", "marshal", "shelve", "dill", "cloudpickle"}, path


def test_a_command_model_has_no_child():
    from ema.models.spec import LoadedModel

    command = ModelSpec("c", "d", CommandLine(("prog",)), (ModelParameter("a", "", "", 1.0),),
                        (PredictionSpec("y", "", "", None),))  # fmt: skip
    with pytest.raises(TypeError, match="not a Python function"):
        ModelProcesses().child(LoadedModel(command, "/x/model.json", "/x", (), "c" * 64, ()))


def test_processes_keep_at_most_max_children(tmp_path, monkeypatch):
    from ema.models import processes as processes_module

    monkeypatch.setattr(processes_module, "MAX_CHILDREN", 1)
    p = ModelProcesses()
    try:
        first = write_model(tmp_path / "one", "def f(a):\n    return a\n")
        second = write_model(tmp_path / "two", "def f(a):\n    return 2 * a\n")
        run_once(first, tmp_path / "w1", p)
        child = p.child(load_spec(str(first)))
        pid = child.pid
        assert pid is not None
        run_once(second, tmp_path / "w2", p)
        assert child.pid is None, "the least recently used child wasn't stopped"
    finally:
        p.close()
