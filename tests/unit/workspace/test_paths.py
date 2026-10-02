"""The workspace's root (trust.md T5; 0057, 0061 item 12) and saving a drafted model spec (T6; U9; W2, 0049)."""

import hashlib
import json
import os
from pathlib import Path

import pytest

import ema.reference_models
from ema.types.errors import ApprovalDeclined, CannotAsk, PathRefused, SpecError
from ema.types.requests import ConfirmationRequest
from ema.workspace import open_workspace
from tests.support.workspace import Asked, copy_reference


def drafted(function: str = "ishigami.py:f", **extra) -> dict:
    """A drafted spec of R2, as an MCP client would send it."""
    spec = json.loads(Path(ema.reference_models.path("R2")).read_text())
    spec["function"] = function
    spec.update(extra)
    return spec


@pytest.fixture
def project(tmp_path):
    """A root with R2's function in it, a workspace outside it, and a workspace inside it."""
    root = tmp_path / "project"
    root.mkdir()
    copy_reference("R2", root)
    (root / "r2" / "model.json").unlink()
    open_workspace(root / "inner").close()
    with open_workspace(tmp_path / "ws", root=root) as w:
        yield w, root, tmp_path


def test_a_root_inside_a_workspace_is_refused(tmp_path):
    """0061 item 12: a root that is a workspace, or inside one, is refused when opening; so is a missing root."""
    open_workspace(tmp_path / "w").close()
    for bad in (tmp_path / "w", tmp_path / "w" / "runs", tmp_path / "missing"):
        with pytest.raises(PathRefused):
            open_workspace(tmp_path / "x", root=bad)


def test_a_relative_workspace_resolves_against_the_root(tmp_path):
    """trust.md, The MCP server's root: a relative workspace, and the default, resolve against the root."""
    with open_workspace(root=tmp_path) as w:
        assert w.path == os.path.join(os.path.realpath(tmp_path), "ema_workspace")


def test_path_arguments_are_confined_to_the_root(project):
    """T5: outside the root, ``..`` climbing out, a link pointing out, inside a workspace, a hidden character, and a
    credentials file: each refused, with nothing read, asked, or written."""
    ws, root, tmp = project
    outside = tmp / "elsewhere"
    outside.mkdir()
    (root / "out").symlink_to(outside)
    asked = Asked()
    for bad in (str(outside / "m.json"), "../elsewhere/m.json", "out/m.json", "inner/m.json", "inner/runs/m.json",
                "r2/m\u202e.json", ".ssh/m.json", "secrets.json"):  # fmt: skip
        with pytest.raises(PathRefused):
            ws.save_model(drafted(), bad, confirm=asked)
        with pytest.raises(PathRefused):
            ws.export("0" * 64, bad.removesuffix(".json"))
    assert asked.questions == [] and list(outside.iterdir()) == []
    assert ws._store.confirmations() == ()


def test_a_drafted_specs_files_stay_inside_the_root(project):
    """T5: a drafted spec whose function file links outside the root is refused, its target not read."""
    ws, root, tmp = project
    (tmp / "far.py").write_text("def f(x1, x2, x3):\n    return 0.0\n")
    (root / "r2" / "near.py").symlink_to(tmp / "far.py")
    with pytest.raises(PathRefused, match="outside the root"):
        ws.propose_model(drafted("near.py:f"), "r2/model.json")


def test_propose_then_save_writes_the_bytes_shown(project):
    """U9, T6: propose_model validates and renders, saving nothing; save_model asks with the absolute path and the
    full text, writes exactly those bytes (their hash recorded), and loads the spec."""
    ws, root, _ = project
    proposal = ws.propose_model(drafted(), "r2/model.json")
    target = Path(os.path.realpath(root)) / "r2" / "model.json"
    assert proposal.path == str(target) and proposal.missing_files == () and not target.exists()
    assert proposal.spec_text in proposal.text
    with pytest.raises(CannotAsk):
        ws.save_model(drafted(), "r2/model.json", confirm=None)
    with pytest.raises(ApprovalDeclined):
        ws.save_model(drafted(), "r2/model.json", confirm=Asked(answer=False))
    assert not target.exists()
    asked = Asked()
    loading = ws.save_model(drafted(), "r2/model.json", confirm=asked)
    (question,) = asked.questions
    assert isinstance(question, ConfirmationRequest) and question.spec_path == str(target)
    assert target.read_text() == proposal.spec_text == question.spec_text
    recorded = ws._store.confirmations()[-1]
    assert recorded.answer and recorded.spec_sha256 == hashlib.sha256(target.read_bytes()).hexdigest()
    assert loading.model.name == "ishigami" and str(loading).startswith("Loaded ishigami@")
    again = Asked()
    ws.save_model(drafted(), "r2/model.json", confirm=again)
    assert "already saved, unchanged: load it?" in again.questions[0].text


def test_save_refuses_before_asking(project):
    """T6: an invalid spec, another file at the path, a name not ending in .json, and a missing parent are refused
    before anything is asked; a spec naming files that don't exist yet lists them."""
    ws, root, _ = project
    (root / "r2" / "other.json").write_text("{}\n")
    asked = Asked()
    with pytest.raises(SpecError):
        ws.save_model({"name": "x"}, "r2/new.json", confirm=asked)
    for path in ("r2/other.json", "r2/model.txt", "nowhere/model.json"):
        with pytest.raises(PathRefused):
            ws.save_model(drafted(), path, confirm=asked)
    assert asked.questions == []
    assert ws.propose_model(drafted("later.py:f"), "r2/later.json").missing_files == ("later.py",)


def test_a_linked_spec_names_the_files_beside_its_target(project, monkeypatch):
    """Review round 1, M1 (T5; C33): a spec that is a link names the files beside its target, as loading reads them,
    so a function file there linking out of the root is refused by propose_model, save_model, and load_model, and
    load_model refuses before the spec's files are read or hashed."""
    ws, root, tmp = project
    (tmp / "far.py").write_text("def f(x1, x2, x3):\n    return 0.0\n")
    text = ws.propose_model(drafted(), "r2/model.json").spec_text
    (root / "b").mkdir()
    (root / "b" / "model.json").write_text(text)
    (root / "b" / "ishigami.py").symlink_to(tmp / "far.py")
    (root / "a").mkdir()
    (root / "a" / "model.json").symlink_to(root / "b" / "model.json")
    (root / "c").symlink_to(root / "b", target_is_directory=True)
    asked = Asked()
    with pytest.raises(PathRefused, match="ishigami.py resolves outside the root"):
        ws.propose_model(drafted(), "a/model.json")
    with pytest.raises(PathRefused, match="ishigami.py resolves outside the root"):
        ws.save_model(drafted(), "a/model.json", confirm=asked)
    assert asked.questions == [] and ws._store.confirmations() == ()
    loaded = []
    monkeypatch.setattr("ema.workspace.load_spec", lambda path: loaded.append(path))
    for path in ("a/model.json", "b/model.json", "c/model.json"):
        with pytest.raises(PathRefused, match="ishigami.py resolves outside the root"):
            ws.load_model(path)
    assert loaded == [] and ws.list_models() == []


def test_propose_model_never_blocks_on_a_fifo(project):
    """Review round 1, m3 (T6): a FIFO at the proposed path is refused at once, not opened for reading and waited on."""
    import signal

    ws, root, _ = project
    os.mkfifo(root / "r2" / "fifo.json")

    def stuck(signum, frame):
        raise TimeoutError("propose_model blocked on a FIFO")

    previous = signal.signal(signal.SIGALRM, stuck)
    signal.alarm(10)
    try:
        with pytest.raises(PathRefused, match="isn't a file EMA can read"):
            ws.propose_model(drafted(), "r2/fifo.json")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def test_an_export_never_makes_a_credentials_directory(project):
    """Review round 1, n3 (T5, T7): an export into a new ``.ssh`` or ``.aws`` directory is refused, nothing written."""
    ws, root, _ = project
    for bad in (".ssh", "deep/.aws", ".config/gcloud"):
        with pytest.raises(PathRefused, match="credentials"):
            ws.export("0" * 64, bad)
    assert not (root / ".ssh").exists() and not (root / "deep").exists()
