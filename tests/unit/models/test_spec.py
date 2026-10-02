"""Loading a model spec, a stored model, and saving a drafted spec (architecture.md §5, spec.py).

M10's template names, M17's unlisted imports, T4's "loading never imports", T6's ``save_spec``, and the spec's own
path (T7).
"""

import json
import os
from pathlib import Path

import pytest

from ema.models.spec import LoadedModel, load_spec, save_spec, stored_model
from ema.types.errors import PathRefused, SpecError
from ema.types.identity import version_hash
from ema.types.model import Keep, ModelSpec
from tests.support.models import MODELS, copy_model


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

    def test_a_function_file_that_does_not_parse(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "model.py").write_text("def f(a, b:\n")
        with pytest.raises(SpecError, match="function.*model.py"):
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
        import shutil

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

    def test_from_imports_and_relative_imports(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / "lib").mkdir()
        (model_dir / "lib" / "__init__.py").write_text("")
        (model_dir / "lib" / "tool.py").write_text("")
        (model_dir / "near.py").write_text("")
        (model_dir / "model.py").write_text(
            "from helper import scale\nfrom lib import tool\nfrom . import near\n\ndef f(a, b):\n    return a\n"
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

    def test_name_and_parent(self, tmp_path):
        with pytest.raises(PathRefused, match=r"\.json"):
            save_spec(self.spec(), str(tmp_path / "model.txt"))
        with pytest.raises(PathRefused, match="no-such-dir"):
            save_spec(self.spec(), str(tmp_path / "no-such-dir" / "model.json"))
