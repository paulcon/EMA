"""Preparing a call (model_interface.md, A run; M5, M10, M15; 0025, 0030; trust.md, T9; record 0071)."""

import json
import os
from pathlib import Path

import pytest

from ema.models.prepare import number_text, prepare
from ema.models.sandbox import model_environment
from ema.models.spec import load_spec
from ema.types.errors import ModelChanged
from ema.types.identity import batch_call_id
from ema.types.runs import RunKey
from tests.support.models import APPROVAL, copy_model, point


@pytest.mark.parametrize(
    ("value", "text"),
    [(0.1, "0.1"), (64.0, "64"), (-2.5, "-2.5"), (1e-300, "1e-300"), (1e16, "1e+16"), (123456789012345.0,
     "123456789012345"), (1 / 3, "0.3333333333333333"), (-0.0, "-0"), (5e-324, "5e-324")],
)  # fmt: skip
def test_m10_the_number_rule(value, text):
    assert number_text(value) == text
    assert float(text) == value and str(float(text)) == str(value)


def keys(model, *points):
    return [RunKey.make(model.model_version_id, p, 0, 0) for p in points]


def test_a_run_directory_holds_its_point_decks_and_files(tmp_path):
    model = load_spec(str(copy_model("command_line", tmp_path)))
    (key,) = keys(model, point(4, a=0.1))
    call = prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    run_dir = Path(call.call_dir)
    assert call.run_dirs == (str(run_dir),) and run_dir == tmp_path / "runs" / key.run_id
    assert json.loads((run_dir / "point.json").read_text()) == {"a": 0.1, "b": 0.5, "mode": 4.0}
    assert (run_dir / "deck.in").read_text() == "a = 0.1\nb = 0.5\nmode = 4\ncost = $5\n"
    assert (run_dir / "solver.py").read_bytes() == (tmp_path / "command_line" / "solver.py").read_bytes()
    assert (run_dir / "mesh.dat").is_symlink()
    assert call.command == ("python3", "solver.py", "deck.in") and call.timeout_s == 10
    assert dict(call.env) == model_environment(model.spec) and call.approval_id == APPROVAL


def test_a_copied_file_keeps_its_path_and_its_executable_bit(tmp_path):
    spec_path = copy_model("command_line", tmp_path)
    (spec_path.parent / "bin").mkdir()
    (spec_path.parent / "bin" / "tool").write_text("#!/bin/sh\n")
    (spec_path.parent / "bin" / "tool").chmod(0o755)
    spec = json.loads(spec_path.read_text())
    spec["files"].append("bin/tool")
    spec_path.write_text(json.dumps(spec))
    model = load_spec(str(spec_path))
    call = prepare(model, keys(model, point()), str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    assert os.access(Path(call.call_dir, "bin", "tool"), os.X_OK)


def test_a_leftover_directory_is_deleted_without_following_its_links(tmp_path):
    """data_model.md §6: prepare clears a directory a call that never finished left at the path it needs (T9)."""
    model = load_spec(str(copy_model("python", tmp_path)))
    (key,) = keys(model, point())
    leftover = tmp_path / "runs" / key.run_id
    leftover.mkdir(parents=True)
    data = tmp_path / "data"
    data.mkdir()
    (data / "keep.txt").write_text("kept")
    (leftover / "data").symlink_to(data)
    (leftover / "stdout.txt").write_text("old")
    prepare(model, [key], str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    assert sorted(p.name for p in leftover.iterdir()) == ["helper.py", "mesh.dat", "point.json"]
    assert (data / "keep.txt").read_text() == "kept"


def test_a_batch_call_runs_in_its_batch_directory(tmp_path):
    """0025: each run keeps its own directory; the call's files are in the batch directory beside them."""
    model = load_spec(str(copy_model("batch", tmp_path)))
    batch_keys = keys(model, point(0, a=1.0), point(0, a=2.0))
    call = prepare(model, batch_keys, str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    assert Path(call.call_dir).name == batch_call_id([k.run_id for k in batch_keys])
    assert (Path(call.call_dir) / "mesh.dat").is_symlink() and call.command is None
    for run_dir in call.run_dirs:
        assert [p.name for p in Path(run_dir).iterdir()] == ["point.json"]


def test_refuses_a_call_that_isnt_one(tmp_path):
    model = load_spec(str(copy_model("python", tmp_path)))
    with pytest.raises(ValueError, match="one run"):
        prepare(model, keys(model, point(), point(a=2.0)), str(tmp_path), str(tmp_path), approval_id=APPROVAL)
    with pytest.raises(ValueError, match="one run"):
        prepare(model, [], str(tmp_path), str(tmp_path), approval_id=APPROVAL)
    with pytest.raises(ValueError, match="M5"):
        prepare(model, keys(model, (1.0, 0.5)), str(tmp_path), str(tmp_path), approval_id=APPROVAL)


def test_m15_a_shared_file_is_stored_once_read_only(tmp_path):
    model = load_spec(str(copy_model("python", tmp_path)))
    calls = [prepare(model, keys(model, point(a=float(i))), str(tmp_path / "runs"), str(tmp_path / "files"),
                     approval_id=APPROVAL) for i in range(3)]  # fmt: skip
    (copy,) = (tmp_path / "files").glob("*/mesh.dat")
    assert copy.parent.name == next(f.sha256 for f in model.files if f.path == "mesh.dat")
    assert not os.access(copy, os.W_OK)
    assert all(os.readlink(Path(c.call_dir, "mesh.dat")) == str(copy) for c in calls)
    assert [p.name for p in copy.parent.iterdir()] == ["mesh.dat"], "a temporary copy was left behind"


def test_m16_a_shared_file_edited_since_loading_is_refused(tmp_path):
    spec_path = copy_model("python", tmp_path)
    model = load_spec(str(spec_path))
    (spec_path.parent / "mesh.dat").write_text("9.0\n")
    with pytest.raises(ModelChanged, match="mesh.dat changed since loading"):
        prepare(model, keys(model, point()), str(tmp_path / "runs"), str(tmp_path / "files"), approval_id=APPROVAL)
    assert not list((tmp_path / "files").glob("*/*")), "a wrong copy was stored"
