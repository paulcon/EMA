"""Loading a model spec, a stored model, and saving a drafted spec (architecture.md §5, spec.py).

M10's template names, M17's unlisted imports, T4's "loading never imports", T6's ``save_spec``, and the spec's own
path (T7).
"""

import dataclasses
import json
import os
import shutil
from pathlib import Path

import pytest

from ema.models.spec import LoadedModel, load_spec, save_spec, stored_model
from ema.types.errors import PathRefused, SpecError
from ema.types.identity import version_hash
from ema.types.model import Keep, ModelSpec
from tests.support.models import MODELS, copy_model
from tests.unit.models.test_files import no_hang


def write_spec(spec_path: Path, **changes) -> None:
    data = json.loads(spec_path.read_text())
    data.update(changes)
    spec_path.write_text(json.dumps(data))


class TestLoadSpec:
    def test_loaded_model(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        model = load_spec(str(spec_path))
        assert isinstance(model, LoadedModel)
        assert model.spec_path == str(spec_path) and os.path.isabs(model.spec_path)
        assert model.model_dir == str(spec_path.parent)
        assert [f.path for f in model.files] == ["helper.py", "mesh.dat", "model.py"]
        assert model.model_version_id == version_hash(model.spec, model.files)
        assert model.warnings == ()
        assert model.spec.timeout_s == 10.0

    def test_a_relative_path_is_made_absolute(self, tmp_path, monkeypatch):
        spec_path = copy_model("batch", tmp_path)
        monkeypatch.chdir(spec_path.parent)
        model = load_spec("model.json")
        assert model.spec_path == str(spec_path)
        assert model.model_version_id == load_spec(str(spec_path)).model_version_id

    def test_a_link_to_the_spec_from_another_directory(self, tmp_path):
        """Review item 4: the model's directory is the spec's, its links resolved; the path shown is as given."""
        spec_path = copy_model("python", tmp_path / "real")
        (tmp_path / "elsewhere").mkdir()
        link = tmp_path / "elsewhere" / "beam.json"
        link.symlink_to(spec_path)
        model = load_spec(str(link))
        assert model.spec_path == str(link) and model.model_dir == str(spec_path.parent)
        assert model.model_version_id == load_spec(str(spec_path)).model_version_id
        stored = stored_model(model.spec, model.files, str(link))
        assert stored.model_dir == model.model_dir and stored.spec_path == str(link)

    def test_a_dotdot_through_a_link_is_resolved_after_the_link(self, tmp_path):
        """``link/../model.json`` is the file beside the link's target, not beside the link (no normpath first)."""
        spec_path = copy_model("python", tmp_path / "a")
        (spec_path.parent / "sub").mkdir()
        (tmp_path / "c").mkdir()
        (tmp_path / "c" / "link").symlink_to(spec_path.parent / "sub", target_is_directory=True)
        model = load_spec(str(tmp_path / "c" / "link" / ".." / "model.json"))
        assert model.model_dir == str(spec_path.parent)

    def test_a_fifo_spec_is_refused(self, tmp_path):
        """Review item 6: loading doesn't block reading a FIFO."""
        os.mkfifo(tmp_path / "model.json")
        with no_hang(), pytest.raises(SpecError, match="not a regular file"):
            load_spec(str(tmp_path / "model.json"))

    def test_errors_name_the_spec_and_the_field(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        write_spec(spec_path, noisy=True)
        with pytest.raises(SpecError, match=rf"{spec_path}: noisy"):
            load_spec(str(spec_path))

    def test_missing_or_unreadable(self, tmp_path):
        with pytest.raises(SpecError, match="nope.json"):
            load_spec(str(tmp_path / "nope.json"))
        (tmp_path / "bad.json").write_bytes(b'{"name": "\xff"}')
        with pytest.raises(SpecError, match="UTF-8"):
            load_spec(str(tmp_path / "bad.json"))
        (tmp_path / "dir.json").mkdir()
        with pytest.raises(SpecError, match="dir.json"):
            load_spec(str(tmp_path / "dir.json"))

    def test_the_spec_itself_a_credentials_file(self, tmp_path):
        """T7: the spec's own path, a link's target included."""
        spec_path = copy_model("python", tmp_path)
        secret = spec_path.parent / "client_secret.json"
        secret.write_text(spec_path.read_text())
        with pytest.raises(SpecError, match="credentials"):
            load_spec(str(secret))
        (tmp_path / ".ssh").mkdir()
        (tmp_path / ".ssh" / "model.json").write_text(spec_path.read_text())
        spec_path.unlink()
        spec_path.symlink_to(tmp_path / ".ssh" / "model.json")
        with pytest.raises(SpecError, match="credentials"):
            load_spec(str(spec_path))

    @pytest.mark.parametrize(
        "source", ["def f(a, b:\n", "x = 1\x00\n", "x = " + "-" * 100000 + "1\n", "x = a" + ".b" * 100000 + "\n"]
    )
    def test_a_function_file_that_does_not_parse(self, tmp_path, source):
        """Review item 7: a null byte, a parser overflow (MemoryError), and a deep tree (RecursionError) too."""
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "model.py").write_text(source)
        with pytest.raises(SpecError, match="function.*model.py.*doesn't parse"):
            load_spec(str(spec_path))


class TestTemplates:
    """M10: a template name that isn't a model parameter is refused at loading; ``$$`` and ``${b}`` load."""

    def test_the_test_model_loads(self, tmp_path):
        assert load_spec(str(copy_model("command_line", tmp_path))).spec.name == "toy_command"

    @pytest.mark.parametrize(
        ("template", "fragment"),
        [("a = $a\nb = $nope\n", "$nope"), ("a = ${y}\n", "$y"), ("x = $a\ncost = $ 5\n", "line 2")],
    )
    def test_refused(self, tmp_path, template, fragment):
        spec_path = copy_model("command_line", tmp_path)
        (spec_path.parent / "deck.in.template").write_text(template)
        with pytest.raises(SpecError, match=r"input_decks\[0\].template") as info:
            load_spec(str(spec_path))
        assert fragment in str(info.value)

    def test_not_utf8(self, tmp_path):
        spec_path = copy_model("command_line", tmp_path)
        (spec_path.parent / "deck.in.template").write_bytes(b"a = $a\n\xff\n")
        with pytest.raises(SpecError, match=r"input_decks\[0\].template.*UTF-8"):
            load_spec(str(spec_path))


class TestImports:
    """M17 and T4: unlisted local imports warned about, and the function's file never imported."""

    def test_warnings_and_no_import(self, tmp_path):
        spec_path = tmp_path / "imports" / "model.json"
        shutil.copytree(MODELS / "imports", spec_path.parent)
        model = load_spec(str(spec_path))
        assert not (spec_path.parent / "IMPORTED").exists(), "loading imported the function's file"
        assert not (spec_path.parent / "IMPORTED_PKG").exists(), "loading imported a package the file names"
        warned = " ".join(model.warnings)
        assert len(model.warnings) == 3
        for name in ("helper.py", "pkg/__init__.py", "pkg/sub.py"):
            assert name in warned
        for name in ("listed.py", "numpy", "os.py"):
            assert name not in warned

    def test_a_listed_helper_gives_no_warning(self, tmp_path):
        assert load_spec(str(copy_model("python", tmp_path))).warnings == ()

    def test_names_resolve_against_the_model_directory_only(self, tmp_path):
        """Review item 11: the child's sys.path has the model's directory first, not the function file's own."""
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / "sub").mkdir()
        (model_dir / "sub" / "model.py").write_text("import nearby\nimport top\n\ndef f(a, b, mode):\n    return a\n")
        (model_dir / "sub" / "nearby.py").write_text("")
        (model_dir / "top.py").write_text("")
        write_spec(spec_path, function="sub/model.py:f")
        warned = load_spec(str(spec_path)).warnings
        assert len(warned) == 1 and "resolves to top.py" in warned[0]

    def test_warnings_in_source_order(self, tmp_path):
        """Review item 16: an import inside a function, before a top-level one, is warned about first."""
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / "first.py").write_text("")
        (model_dir / "second.py").write_text("")
        (model_dir / "model.py").write_text("def f(a, b, mode):\n    import first\n    return a\n\nimport second\n")
        warned = load_spec(str(spec_path)).warnings
        assert [w.split(" resolves to ")[1].split(",")[0] for w in warned] == ["first.py", "second.py"]

    def test_from_imports_and_relative_imports(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / "lib").mkdir()
        (model_dir / "lib" / "__init__.py").write_text("")
        (model_dir / "lib" / "tool.py").write_text("")
        (model_dir / "near.py").write_text("")
        (model_dir / "model.py").write_text(
            "from helper import scale\nfrom lib import tool\nfrom . import near\n\ndef f(a, b, mode):\n    return a\n"
        )
        warned = load_spec(str(spec_path)).warnings
        assert [w.split(" resolves to ")[1].split(",")[0] for w in warned] == [
            "lib/__init__.py",
            "lib/tool.py",
            "near.py",
        ]


class TestStoredModel:
    def test_matches_loading(self, tmp_path):
        loaded = load_spec(str(copy_model("command_line", tmp_path)))
        stored_spec = ModelSpec.from_json(loaded.spec.versioned_json())
        stored = stored_model(stored_spec, tuple(reversed(loaded.files)), loaded.spec_path)
        assert stored.model_version_id == loaded.model_version_id
        assert stored.files == loaded.files and stored.model_dir == loaded.model_dir
        assert stored.spec.keep is Keep.ALL and stored.warnings == ()


class TestSaveSpec:
    """T6's write: exactly the bytes of ``to_json``, an exclusive create, nothing overwritten."""

    def spec(self) -> ModelSpec:
        return load_spec(str(MODELS / "python" / "model.json")).spec

    def test_writes_to_json(self, tmp_path):
        spec = self.spec()
        save_spec(spec, str(tmp_path / "model.json"))
        assert (tmp_path / "model.json").read_bytes() == spec.to_json().encode("utf-8")
        assert ModelSpec.from_json((tmp_path / "model.json").read_text()) == spec

    def test_same_bytes_write_nothing(self, tmp_path):
        spec, path = self.spec(), tmp_path / "model.json"
        save_spec(spec, str(path))
        os.utime(path, (0, 0))
        save_spec(spec, str(path))
        assert path.stat().st_mtime == 0

    def test_a_different_file_refused(self, tmp_path):
        path = tmp_path / "model.json"
        path.write_text("{}")
        with pytest.raises(PathRefused, match="model.json"):
            save_spec(self.spec(), str(path))
        assert path.read_text() == "{}"

    def test_a_link_left_at_the_path_is_kept(self, tmp_path):
        path = tmp_path / "model.json"
        path.symlink_to(tmp_path / "elsewhere.json")
        with pytest.raises(PathRefused):
            save_spec(self.spec(), str(path))
        assert path.is_symlink() and not (tmp_path / "elsewhere.json").exists()

    def test_a_link_to_nothing(self, tmp_path):
        """Review item 14: named as such, not as a file that appeared meanwhile."""
        path = tmp_path / "model.json"
        path.symlink_to(tmp_path / "elsewhere.json")
        with pytest.raises(PathRefused, match="link to nothing"):
            save_spec(self.spec(), str(path))

    def test_a_fifo_at_the_path(self, tmp_path):
        os.mkfifo(tmp_path / "model.json")
        with no_hang(), pytest.raises(PathRefused, match="not a regular file"):
            save_spec(self.spec(), str(tmp_path / "model.json"))

    def test_upper_case_json_and_a_spec_loading_would_refuse(self, tmp_path):
        """Review item 14: ``.JSON`` is a JSON file; a spec built in Python with a bad name is never written."""
        save_spec(self.spec(), str(tmp_path / "MODEL.JSON"))
        assert ModelSpec.from_json((tmp_path / "MODEL.JSON").read_text()) == self.spec()
        bad = dataclasses.replace(self.spec(), name="Not A Name")
        with pytest.raises(SpecError, match="name"):
            save_spec(bad, str(tmp_path / "bad.json"))
        assert not (tmp_path / "bad.json").exists()

    def test_name_and_parent(self, tmp_path):
        with pytest.raises(PathRefused, match=r"\.json"):
            save_spec(self.spec(), str(tmp_path / "model.txt"))
        with pytest.raises(PathRefused, match="no-such-dir"):
            save_spec(self.spec(), str(tmp_path / "no-such-dir" / "model.json"))


def test_resolve_program(tmp_path):
    """U2, 0029: what the first approval shows before any run (M19's resolution; C44 compares it with a run's)."""
    import sys

    from ema.models.spec import resolve_program

    assert resolve_program(load_spec(str(copy_model("python", tmp_path / "p")))) == sys.executable
    spec_path = copy_model("command_line", tmp_path / "c")
    text = json.loads(spec_path.read_text())
    text["env"]["PATH"] = "/bin"
    text["command"] = ["sh", "-c", "x"]
    spec_path.write_text(json.dumps(text))
    assert resolve_program(load_spec(str(spec_path))) == "/bin/sh"
    text["command"] = ["ema-no-such-program"]
    spec_path.write_text(json.dumps(text))
    assert resolve_program(load_spec(str(spec_path))) is None


class TestSignature:
    """Record 0081 item 29: a function whose arguments EMA can't call it with is refused at loading, before any run.

    EMA calls a function with every model parameter by name (the toy's are a, b, mode), and a batch function with
    one positional argument, the points' array (0025); a function bound other than by a plain ``def`` isn't checked.
    """

    @pytest.mark.parametrize(
        ("source", "fragment"),
        [
            ("def f(a, b):\n    return a\n", "it has no argument mode"),
            ("def f(a, b, mode, c):\n    return a\n", "its argument c isn't a model parameter and has no default"),
            ("def f(x, y, z):\n    return x\n", "it has no argument a"),
            ("def f(a, /, b, mode):\n    return a\n", "a is positional-only"),
            ("def g(a, b, mode):\n    return a\n", "model.py defines no f at its top level"),
        ],
    )
    def test_refused_naming_the_mismatch(self, tmp_path, source, fragment):
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "model.py").write_text(source)
        with pytest.raises(SpecError, match=f"function: model.py:f.*{fragment}"):
            load_spec(str(spec_path))

    @pytest.mark.parametrize(
        "source",
        [
            "def f(a, b, mode):\n    return a\n",
            "def f(mode, b, a, c=1.0):\n    return a\n",
            "def f(*, a, b, mode, scale=2.0):\n    return a\n",
            "def f(a, **rest):\n    return a\n",
            "import functools\n\n@functools.cache\ndef f(x):\n    return x\n",  # decorated: not checked
            "def _g(x):\n    return x\n\nf = _g\n",  # assigned: not checked
            "from helper import *\n",  # a star import may bind f: not checked
        ],
    )
    def test_allowed_or_not_checked(self, tmp_path, source):
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "model.py").write_text(source)
        assert load_spec(str(spec_path)).spec.interface.function == "model.py:f"

    @pytest.mark.parametrize(
        ("source", "ok"),
        [
            ("def f(X):\n    return X\n", True),
            ("def f(X, scale=1.0):\n    return X\n", True),
            ("def f(*points):\n    return points[0]\n", True),
            ("def f(X, Y):\n    return X\n", False),
            ("def f(*, X):\n    return X\n", False),
            ("def f(a, b, mode):\n    return a\n", False),
        ],
    )
    def test_a_batch_function_takes_one_positional_argument(self, tmp_path, source, ok):
        spec_path = copy_model("batch", tmp_path)
        (spec_path.parent / "model.py").write_text(source)
        if ok:
            load_spec(str(spec_path))
        else:
            with pytest.raises(SpecError, match="a batch function takes one positional argument"):
                load_spec(str(spec_path))
