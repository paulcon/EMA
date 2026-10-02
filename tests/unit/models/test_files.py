"""Paths as files, and the tracked files' hashes (trust.md T1, T7's links; M16; architecture.md §5, files.py)."""

import dataclasses
import hashlib
import os
from pathlib import Path

import pytest

from ema.models.files import check_files, hash_files, is_within, same_file
from ema.models.spec import load_spec
from ema.types.errors import ModelChanged, SpecError
from ema.types.identity import TrackedFile
from ema.types.model import FileEntry, ModelSpec
from tests.support.models import copy_model


def case_insensitive(directory: Path) -> bool:
    probe = directory / "probe-Case.txt"
    probe.write_text("x")
    try:
        return (directory / "PROBE-CASE.TXT").exists()
    finally:
        probe.unlink()


class TestSameFile:
    def test_spellings_of_one_file(self, tmp_path):
        (tmp_path / "d").mkdir()
        (tmp_path / "d" / "model.json").write_text("{}")
        (tmp_path / "link").symlink_to(tmp_path / "d")
        assert same_file(tmp_path / "d" / "model.json", tmp_path / "d" / ".." / "d" / "model.json")
        assert same_file(str(tmp_path / "link" / "model.json"), str(tmp_path / "d" / "model.json"))
        assert not same_file(tmp_path / "d" / "model.json", tmp_path / "d")

    def test_paths_that_do_not_exist(self, tmp_path):
        assert same_file(tmp_path / "x" / ".." / "y", tmp_path / "y")
        assert not same_file(tmp_path / "x", tmp_path / "y")
        (tmp_path / "link").symlink_to(tmp_path / "real")
        assert same_file(tmp_path / "link" / "a", tmp_path / "real" / "a")

    def test_case(self, tmp_path):
        """T1: on a case-insensitive file system MODEL.JSON is model.json; on a case-sensitive one, two files."""
        (tmp_path / "model.json").write_text("{}")
        if case_insensitive(tmp_path):
            assert same_file(tmp_path / "MODEL.JSON", tmp_path / "model.json")
            assert same_file(tmp_path / "New.json", tmp_path / "new.JSON")  # neither exists
        else:
            (tmp_path / "MODEL.JSON").write_text("{}")
            assert not same_file(tmp_path / "MODEL.JSON", tmp_path / "model.json")
            assert not same_file(tmp_path / "New.json", tmp_path / "new.JSON")


class TestIsWithin:
    def test_t1_cases(self, tmp_path):
        root = tmp_path / "root"
        (root / "sub").mkdir(parents=True)
        assert is_within(root, root)
        assert is_within(root / "sub", root)
        assert is_within(root / "not" / "yet" / "made.json", root)
        assert not is_within(root / ".." / "x", root)
        assert not is_within(tmp_path, root)
        assert not is_within(tmp_path / "rootx", root)

    def test_links(self, tmp_path):
        root, outside = tmp_path / "root", tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        (root / "out").symlink_to(outside)
        (outside / "in").symlink_to(root)
        assert not is_within(root / "out" / "file", root)
        assert is_within(outside / "in" / "file", root)

    def test_case(self, tmp_path):
        root = tmp_path / "Root"
        root.mkdir()
        assert is_within(tmp_path / "ROOT" / "x", root) == case_insensitive(tmp_path)


class TestHashFiles:
    def test_tracked_files(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        spec = ModelSpec.from_json(spec_path.read_text())
        files = hash_files(spec, str(spec_path.parent))
        expected = [
            TrackedFile(name, hashlib.sha256((spec_path.parent / name).read_bytes()).hexdigest(), name == "mesh.dat")
            for name in ("helper.py", "mesh.dat", "model.py")
        ]
        assert list(files) == expected

    def test_templates_are_tracked(self, tmp_path):
        spec_path = copy_model("command_line", tmp_path)
        files = hash_files(ModelSpec.from_json(spec_path.read_text()), str(spec_path.parent))
        assert [f.path for f in files] == ["deck.in.template", "mesh.dat", "solver.py"]

    def test_a_missing_file_or_a_directory(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        spec = ModelSpec.from_json(spec_path.read_text())
        (spec_path.parent / "helper.py").unlink()
        with pytest.raises(SpecError, match=r"files\[0\].*helper.py"):
            hash_files(spec, str(spec_path.parent))
        (spec_path.parent / "helper.py").mkdir()
        with pytest.raises(SpecError, match=r"files\[0\].*not a file"):
            hash_files(spec, str(spec_path.parent))
        (spec_path.parent / "helper.py").rmdir()
        (spec_path.parent / "helper.py").symlink_to(tmp_path / "nowhere")
        with pytest.raises(SpecError, match=r"files\[0\]"):
            hash_files(spec, str(spec_path.parent))

    def test_a_link_to_a_credentials_file(self, tmp_path):
        """T7: mesh.dat linked to ~/.ssh/id_rsa is refused at loading, naming the field."""
        home = tmp_path / "home"
        (home / ".ssh").mkdir(parents=True)
        (home / ".ssh" / "id_rsa").write_text("KEY")
        (home / ".ssh" / "config").write_text("Host x")
        spec_path = copy_model("python", tmp_path)
        spec = ModelSpec.from_json(spec_path.read_text())
        mesh = spec_path.parent / "mesh.dat"
        for target in (home / ".ssh" / "id_rsa", home / ".ssh" / "config"):
            mesh.unlink()
            mesh.symlink_to(target)
            with pytest.raises(SpecError, match=r"files\[1\].*credentials"):
                hash_files(spec, str(spec_path.parent))

    def test_a_credentials_directory_below_the_model_reached_by_a_link(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / ".aws").mkdir()
        (model_dir / ".aws" / "data").write_text("x")
        (model_dir / "mesh.dat").unlink()
        (model_dir / "mesh.dat").symlink_to(model_dir / ".aws" / "data")
        with pytest.raises(SpecError, match="credentials"):
            hash_files(ModelSpec.from_json(spec_path.read_text()), str(model_dir))

    def test_a_link_to_an_ordinary_file_is_followed(self, tmp_path):
        data = tmp_path / "data" / "mesh.h5"
        data.parent.mkdir()
        data.write_text("1.0\n")
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "mesh.dat").unlink()
        (spec_path.parent / "mesh.dat").symlink_to(data)
        files = hash_files(ModelSpec.from_json(spec_path.read_text()), str(spec_path.parent))
        assert files[1] == TrackedFile("mesh.dat", hashlib.sha256(b"1.0\n").hexdigest(), True)

    def test_a_model_directory_under_a_credentials_directory_loads(self, tmp_path):
        """T7: a model directory under ~/.docker/ loads; only the part below the model's directory is matched."""
        spec_path = copy_model("python", tmp_path / ".docker" / "models")
        assert load_spec(str(spec_path)).files

    def test_two_entries_naming_one_file(self, tmp_path):
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "alias.dat").symlink_to(spec_path.parent / "mesh.dat")
        spec = ModelSpec.from_json(spec_path.read_text())
        spec = dataclasses.replace(spec, files=spec.files + (FileEntry("alias.dat"),))
        with pytest.raises(SpecError, match=r"files\[2\].*same file"):
            hash_files(spec, str(spec_path.parent))


class TestCheckFiles:
    """M16: the tracked files hashed again before a call; a change refused, naming the file."""

    def test_unchanged(self, tmp_path):
        check_files(load_spec(str(copy_model("command_line", tmp_path))))

    @pytest.mark.parametrize("name", ["deck.in.template", "solver.py", "mesh.dat"])
    def test_one_byte_changed(self, tmp_path, name):
        model = load_spec(str(copy_model("command_line", tmp_path)))
        path = Path(model.model_dir) / name
        path.write_bytes(path.read_bytes() + b" ")
        with pytest.raises(ModelChanged, match=rf"{name}.*changed") as info:
            check_files(model)
        assert "toy_command@" in str(info.value)

    def test_missing(self, tmp_path):
        model = load_spec(str(copy_model("python", tmp_path)))
        os.remove(Path(model.model_dir) / "model.py")
        with pytest.raises(ModelChanged, match="model.py"):
            check_files(model)
