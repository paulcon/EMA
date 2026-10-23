"""Paths as files, and the tracked files' hashes (trust.md T1, T7's links; M16; architecture.md §5, files.py)."""

import contextlib
import dataclasses
import hashlib
import os
import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

from ema.models import files as files_module
from ema.models.files import check_files, hash_files, is_within, leads_to_credentials, open_regular, same_file
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


@contextlib.contextmanager
def no_hang(seconds: int = 5) -> Iterator[None]:
    """Fail, rather than hang, when a FIFO blocks a read (review item 6)."""

    def alarm(signum, frame):
        raise AssertionError("blocked reading a FIFO")

    previous = signal.signal(signal.SIGALRM, alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


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

    @pytest.mark.parametrize("insensitive", [True, False])
    def test_both_branches_of_the_probe(self, tmp_path, monkeypatch, insensitive):
        """Review item 18: either answer of the case probe, whatever the file system the tests run on."""
        monkeypatch.setattr(files_module, "_case_insensitive", lambda path: insensitive)
        assert same_file(tmp_path / "New.json", tmp_path / "new.JSON") is insensitive
        assert same_file(tmp_path / "x" / "A", tmp_path / "x" / "a") is insensitive
        assert not same_file(tmp_path / "x" / "a", tmp_path / "x" / "b")


class TestCaseProbe:
    """Review item 3: the file system asked is the one of the nearest existing directory, not of its parent."""

    def test_pathconf_and_the_probe_agree(self, tmp_path, monkeypatch):
        (tmp_path / "Data.txt").write_text("x")
        asked = files_module._case_insensitive(str(tmp_path / "new" / "file.json"))
        monkeypatch.setattr(files_module, "_pathconf_case_insensitive", lambda directory: None)
        assert files_module._case_insensitive(str(tmp_path / "new" / "file.json")) == asked
        assert asked == case_insensitive(tmp_path)

    def test_the_probe_looks_inside_the_nearest_directory(self, tmp_path, monkeypatch):
        """A mount point's own name is on its parent's file system; an entry inside it is on its own."""
        monkeypatch.setattr(files_module, "_pathconf_case_insensitive", lambda directory: None)
        (tmp_path / "2024").mkdir()
        (tmp_path / "2024" / "Mesh.dat").write_text("x")
        probed: list[str] = []
        real = files_module._swaps_to_itself

        def spy(path: str) -> bool | None:
            probed.append(path)
            return real(path)

        monkeypatch.setattr(files_module, "_swaps_to_itself", spy)
        files_module._case_insensitive(str(tmp_path / "2024" / "new.json"))
        assert probed == [str(tmp_path / "2024" / "Mesh.dat")]

    def test_the_probe_falls_back_to_the_parents(self, tmp_path, monkeypatch):
        monkeypatch.setattr(files_module, "_pathconf_case_insensitive", lambda directory: None)
        (tmp_path / "2024").mkdir()
        (tmp_path / "2024" / "123").write_text("x")
        assert files_module._case_insensitive(str(tmp_path / "2024" / "new.json")) == case_insensitive(tmp_path)


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
        with pytest.raises(SpecError, match=r"files\[0\].*not a regular file"):
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

    def test_a_link_beside_its_target_and_hard_links_are_two_entries(self, tmp_path):
        """Review item 5: both are legitimate aliases (each copied into the run directory by its own name)."""
        spec_path = copy_model("python", tmp_path)
        model_dir = spec_path.parent
        (model_dir / "alias.dat").symlink_to(model_dir / "mesh.dat")
        os.link(model_dir / "mesh.dat", model_dir / "hard.dat")
        spec = ModelSpec.from_json(spec_path.read_text())
        spec = dataclasses.replace(spec, files=spec.files + (FileEntry("alias.dat"), FileEntry("hard.dat")))
        paths = [f.path for f in hash_files(spec, str(model_dir))]
        assert paths == ["alias.dat", "hard.dat", "helper.py", "mesh.dat", "model.py"]

    def test_two_spellings_of_one_entry(self, tmp_path):
        """The function's file named again in another case: one entry, refused on a case-insensitive system."""
        spec_path = copy_model("python", tmp_path)
        spec = ModelSpec.from_json(spec_path.read_text())
        spec = dataclasses.replace(spec, files=spec.files + (FileEntry("MODEL.py"),))
        expected = "same file" if case_insensitive(spec_path.parent) else "isn't in the model's directory"
        with pytest.raises(SpecError, match=rf"files\[2\].*{expected}"):
            hash_files(spec, str(spec_path.parent))

    def test_a_fifo_is_refused(self, tmp_path):
        """Review item 6: a FIFO named as a file is refused, never read."""
        spec_path = copy_model("python", tmp_path)
        (spec_path.parent / "mesh.dat").unlink()
        os.mkfifo(spec_path.parent / "mesh.dat")
        with no_hang(), pytest.raises(SpecError, match=r"files\[1\].*not a regular file"):
            hash_files(ModelSpec.from_json(spec_path.read_text()), str(spec_path.parent))

    def test_a_name_starting_with_two_dots_is_below_the_model(self, tmp_path):
        """Review item 12: ``..mesh.dat`` is in the model's directory, so only its name is matched (T7)."""
        model_dir = tmp_path / ".docker" / "model"
        model_dir.mkdir(parents=True)
        (model_dir / "..mesh.dat").write_text("x")
        assert leads_to_credentials(str(model_dir / "..mesh.dat"), str(model_dir)) is None
        assert leads_to_credentials(str(model_dir / "..mesh.dat"), str(tmp_path / "other")) is not None


class TestOpenRegular:
    def test_regular_files_only(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"abc")
        with open_regular(str(tmp_path / "a.txt")) as f:
            assert f.read() == b"abc"
        os.mkfifo(tmp_path / "pipe")
        for path in (tmp_path / "pipe", tmp_path):
            with no_hang(), pytest.raises(OSError, match="not a regular file"):
                open_regular(str(path))
        with pytest.raises(FileNotFoundError):
            open_regular(str(tmp_path / "nope"))


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
        with pytest.raises(ModelChanged, match="model.py.*load the model again"):
            check_files(model)

    def test_a_tracked_file_that_becomes_a_fifo(self, tmp_path):
        """Review item 6: the check doesn't block; the file changed."""
        model = load_spec(str(copy_model("python", tmp_path)))
        os.remove(Path(model.model_dir) / "mesh.dat")
        os.mkfifo(Path(model.model_dir) / "mesh.dat")
        with no_hang(), pytest.raises(ModelChanged, match="mesh.dat.*not a regular file"):
            check_files(model)


class TestRemoveTree:
    """T9, 0061: run and batch directories are deleted without following links."""

    def test_a_link_inside_is_removed_never_its_target(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "big.h5").write_text("kept")
        run_dir = tmp_path / "run"
        (run_dir / "sub").mkdir(parents=True)
        (run_dir / "sub" / "data").symlink_to(data)
        (run_dir / "file.txt").symlink_to(data / "big.h5")
        files_module.remove_tree(run_dir)
        assert not run_dir.exists() and (data / "big.h5").read_text() == "kept"

    def test_read_only_directories_are_emptied(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "locked").mkdir(parents=True)
        (run_dir / "locked" / "x").write_text("x")
        (run_dir / "locked").chmod(0o500)
        files_module.remove_tree(str(run_dir))
        assert not run_dir.exists()

    def test_nested_directories_without_read_or_search_permission(self, tmp_path):
        """Review round 1 (record 0071): emptied at any depth; nothing above the path is changed."""
        run_dir = tmp_path / "run"
        (run_dir / "a" / "b" / "c").mkdir(parents=True)
        (run_dir / "a" / "b" / "c" / "f").write_text("x")
        (run_dir / "a" / "g").write_text("y")
        for directory, mode in (("a/b/c", 0o000), ("a/b", 0o000), ("a", 0o100), (".", 0o500)):
            (run_dir / directory).chmod(mode)
        tmp_path.chmod(0o755)
        files_module.remove_tree(run_dir)
        assert not run_dir.exists() and (tmp_path.stat().st_mode & 0o777) == 0o755

    def test_a_directory_above_the_path_is_never_made_writable(self, tmp_path):
        parent = tmp_path / "parent"
        (parent / "run").mkdir(parents=True)
        parent.chmod(0o555)
        try:
            with pytest.raises(PermissionError):
                files_module.remove_tree(parent / "run")
            assert (parent.stat().st_mode & 0o777) == 0o555
        finally:
            parent.chmod(0o755)

    def test_a_link_or_nothing_at_the_path(self, tmp_path):
        target = tmp_path / "target"
        target.mkdir()
        (tmp_path / "link").symlink_to(target)
        files_module.remove_tree(tmp_path / "link")
        assert target.is_dir() and not (tmp_path / "link").exists()
        files_module.remove_tree(tmp_path / "nothing")


class TestWriteOwn:
    """T9: EMA's own files are written without following a link the model left."""

    def test_a_link_left_at_the_name_is_replaced(self, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_text("data")
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "run.json").symlink_to(outside)
        files_module.write_own(str(run_dir), "run.json", b"{}")
        assert outside.read_text() == "data" and (run_dir / "run.json").read_text() == "{}"
        assert not (run_dir / "run.json").is_symlink()

    def test_a_directory_at_the_name_or_a_linked_directory_is_refused(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "run.json").mkdir(parents=True)
        with pytest.raises(OSError):
            files_module.write_own(str(run_dir), "run.json", b"{}")
        (tmp_path / "linked").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
        (tmp_path / "elsewhere").mkdir()
        with pytest.raises(OSError):
            files_module.write_own(str(tmp_path / "linked"), "run.json", b"{}")
        assert not (tmp_path / "elsewhere" / "run.json").exists()
