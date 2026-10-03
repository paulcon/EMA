"""The command line, ``ema`` (architecture.md §8; build step 16; record 0082).

Each command through ``main(argv)``, with stdout and stderr captured and a workspace in a temporary directory, on
R2 (the Ishigami function): the 13 commands, the approval on stderr (``--yes`` still shown and recorded; no terminal
and no ``--yes`` is a no; P3, W3), the exit codes (0, 1, 2, 130), ``ema report``'s streams (0060), and ``ema mcp``'s
root checks and lazy import (T5; 0061). That each command prints exactly what its workspace function returned is C54's
check, ``tests/contracts/workspace.py``.
"""

import io
import json
import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

import ema.reference_models
from ema import cli
from ema.cli import main
from ema.types.requests import Progress
from ema.types.summaries import Report
from ema.workspace import Workspace, open_workspace

R2 = ema.reference_models.path("R2")
R2_SPACE = str(Path(R2).parent / "space.json")
SCATTER = ["scatter", "--space", R2_SPACE, "--param", "n=20", "--param", "seed=1"]


class Terminal(io.StringIO):
    """A stdin that is a terminal, holding the answers typed."""

    def isatty(self) -> bool:
        return True


class Interrupting(Terminal):
    """A terminal whose user presses Ctrl-C at the question."""

    def readline(self, size: int = -1) -> str:
        raise KeyboardInterrupt


@dataclass
class Ran:
    code: int
    out: str
    err: str


@pytest.fixture
def ema_cli(capsys, monkeypatch):
    """Run ``ema`` with argv; stdin is not a terminal unless given."""

    def run(*argv: str, stdin: io.StringIO | None = None) -> Ran:
        monkeypatch.setattr(sys, "stdin", stdin if stdin is not None else io.StringIO(""))
        capsys.readouterr()
        code = main(list(argv))
        captured = capsys.readouterr()
        return Ran(code, captured.out, captured.err)

    return run


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """A workspace on R2 with the test run, a scatter result (n = 20), and a point run, made through the CLI."""
    tmp = tmp_path_factory.mktemp("cli")
    w = str(tmp / "ws")
    saved = sys.stdin, sys.stdout, sys.stderr
    sys.stdin, sys.stdout, sys.stderr = io.StringIO(""), io.StringIO(), io.StringIO()
    try:
        assert main(["--workspace", w, "model", "add", R2]) == 0
        assert main(["--workspace", w, "model", "test", "ishigami", "--yes"]) == 0
        assert main(["--workspace", w, "run", "ishigami", *SCATTER, "--yes"]) == 0
        assert main(["--workspace", w, "run", "ishigami", "point_run", "--param", 'x={"x1": 1.0}', "--yes"]) == 0
    finally:
        sys.stdin, sys.stdout, sys.stderr = saved
    with open_workspace(w) as ws:
        results = {r.diagnostic: r.short_id for r in ws.list_results()}
    return {"ws": w, "tmp": tmp, **results}


# -- models and diagnostics --------------------------------------------------------------------------------------


def test_model_add_prints_the_loading_and_asks_nothing(ema_cli, tmp_path):
    """``ema model add`` loads the spec (W1): stdout is the loading's text; nothing is asked."""
    ran = ema_cli("--workspace", str(tmp_path / "ws"), "model", "add", R2)
    assert ran.code == 0 and ran.out.startswith("Loaded ishigami@") and ran.err == ""
    again = ema_cli("model", "add", R2, "--workspace", str(tmp_path / "ws"))  # --workspace after the command too
    assert again.code == 0 and "Already loaded: nothing changed" in again.out


def test_model_test_without_a_terminal_or_yes_is_a_no(ema_cli, tmp_path):
    """No terminal and no ``--yes``: the question is shown, there is no answer, which is a no: exit 1, no run (§8)."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    ran = ema_cli("--workspace", w, "model", "test", "ishigami")
    assert ran.code == 1 and ran.out == ""
    assert "Price: 1 new run, 0 reused, time unknown" in ran.err
    assert "Approve? [y/N] no answer: no terminal, and no --yes" in ran.err
    assert "declined: no runs made" in ran.err
    assert os.listdir(os.path.join(w, "runs")) == []


def test_model_test_with_yes_still_shows_the_question(ema_cli, tmp_path):
    """``--yes`` approves in advance: the price and the question are still shown on stderr (W3; trust.md)."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    ran = ema_cli("--workspace", w, "model", "test", "ishigami", "--yes")
    assert ran.code == 0, ran.err
    assert "Price: 1 new run, 0 reused, time unknown" in ran.err and "Approve? [y/N] y (--yes)" in ran.err
    assert "Function: `ishigami.py:f`" in ran.err  # the first approval's details (U2)
    assert ran.out.startswith("Run ") and ": ok; y = 0; at x1 = 0" in ran.out
    stored = ema_cli("--workspace", w, "model", "test", "ishigami")  # stored: asks nothing (C50)
    assert stored.code == 0 and stored.err == "" and stored.out == ran.out


def test_a_terminal_answers_the_question(ema_cli, tmp_path):
    """On a terminal, the answer is read from stdin (``ema.ask``): "y" is a yes, anything else a no."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    no = ema_cli("--workspace", w, "model", "test", "ishigami", stdin=Terminal("n\n"))
    assert no.code == 1 and "Approve? [y/N] " in no.err and "declined: no runs made" in no.err
    yes = ema_cli("--workspace", w, "model", "test", "ishigami", stdin=Terminal("y\n"))
    assert yes.code == 0 and yes.out.startswith("Run ")


def test_ctrl_c_at_the_question_exits_130(ema_cli, tmp_path):
    """Ctrl-C at the question is a no, recorded, and exits 130 with no run made (T3; §8)."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    ran = ema_cli("--workspace", w, "model", "test", "ishigami", stdin=Interrupting())
    assert ran.code == 130 and "Stopped: every finished run is stored." in ran.err
    assert os.listdir(os.path.join(w, "runs")) == []


def test_models_and_diagnostics_list_and_describe(ema_cli, session):
    w = session["ws"]
    models = ema_cli("--workspace", w, "models")
    assert models.code == 0 and models.out.startswith("ishigami@") and models.out.count("\n") == 1
    described = ema_cli("--workspace", w, "models", "ishigami")
    assert described.code == 0 and "Model parameters:" in described.out and "- x3" in described.out
    listed = ema_cli("--workspace", w, "diagnostics")
    names = [block.split(":", 1)[0] for block in listed.out.split("\n\n")]
    assert listed.code == 0 and {"point_run", "scatter"} <= set(names) and names == sorted(names)
    scatter = ema_cli("--workspace", w, "diagnostics", "scatter")
    assert scatter.code == 0 and "n: integer ≥ 1, default 200" in scatter.out
    missing = ema_cli("--workspace", w, "models", "nope")
    assert missing.code == 1 and missing.out == "" and missing.err.startswith("ema: ")


def test_an_empty_workspace_lists_nothing_on_stdout(ema_cli, tmp_path):
    for command in ("models", "results"):
        ran = ema_cli("--workspace", str(tmp_path / "ws"), command)
        assert ran.code == 0 and ran.out == "" and ran.err.startswith("No ")


# -- price and run -----------------------------------------------------------------------------------------------


def test_price_asks_nothing_and_runs_nothing(ema_cli, session):
    """``ema price`` (P3; Q2): a stored request prices 0 new; another seed prices 20 new; nothing asked or made."""
    w = session["ws"]
    before = len(os.listdir(os.path.join(w, "runs")))
    stored = ema_cli("--workspace", w, "price", "ishigami", *SCATTER)
    assert stored.code == 0 and stored.out.startswith("0 new runs, ") and stored.err == ""
    other = ema_cli("--workspace", w, "price", "ishigami", "scatter", "--space", R2_SPACE, "--param", "n=20",
                    "--param", "seed=2", "--param", "sampler=random")  # fmt: skip
    assert other.code == 0 and other.out.startswith("20 new runs, 0 reused, about ") and other.err == ""
    assert len(os.listdir(os.path.join(w, "runs"))) == before
    twice = ema_cli("--workspace", w, "price", "ishigami", *SCATTER, "--param", "n=21")
    assert twice.code == 2 and "--param n is given twice" in twice.err


def test_run_shows_the_question_progress_and_result(ema_cli, tmp_path):
    """``ema run --yes``: the question on stderr, the progress on stderr, the result's text on stdout; again asks
    nothing and prints the same (C50); the space file and ``--param`` values parsed by the diagnostic (§8)."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    ran = ema_cli("--workspace", w, "run", "ishigami", *SCATTER, "--yes")
    assert ran.code == 0, ran.err
    assert "Price: 20 new runs, 0 reused, time unknown" in ran.err and "Approve? [y/N] y (--yes)" in ran.err
    assert "20/20 runs" in ran.err.splitlines()
    assert ran.out.startswith("Diagnostic result ") and "20 runs: 20 new, 0 reused, 0 failed" in ran.out
    again = ema_cli("--workspace", w, "run", "ishigami", *SCATTER)
    head = ran.out.split(": ", 1)[0] + ": "  # the repeat names the stored result first (record 0081 item 28)
    stored = head + "the stored result of the same request; no new runs, nothing asked. As made: "
    assert again.code == 0 and again.out == stored + ran.out.removeprefix(head) and "Approve?" not in again.err


def test_run_without_yes_or_terminal_makes_no_run(ema_cli, tmp_path):
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    ran = ema_cli("--workspace", w, "run", "ishigami", *SCATTER)
    assert ran.code == 1 and "declined: no runs made" in ran.err and os.listdir(os.path.join(w, "runs")) == []


def test_ctrl_c_during_the_runs_keeps_them_and_exits_130(ema_cli, tmp_path, monkeypatch):
    """Ctrl-C during the runs: exit 130, every finished run stored (C49); the rerun prices only the rest as new."""
    w = str(tmp_path / "ws")
    ema_cli("--workspace", w, "model", "add", R2)
    seen = cli.ProgressLine.__call__

    def interrupt(self: cli.ProgressLine, progress: Progress) -> None:
        seen(self, progress)
        if progress.phase == "runs" and progress.done == 5:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli.ProgressLine, "__call__", interrupt)
    ran = ema_cli("--workspace", w, "run", "ishigami", *SCATTER, "--yes")
    assert ran.code == 130 and "Stopped at 5/20 runs: every finished run is stored." in ran.err
    monkeypatch.undo()
    price = ema_cli("--workspace", w, "price", "ishigami", *SCATTER)
    assert price.out.startswith("15 new runs, 5 reused")


def test_bad_usage_exits_2(ema_cli, session, tmp_path):
    """Bad usage exits 2 and runs nothing (§8): argparse's errors, a malformed ``--param``, a ``--param`` naming an
    option, an unreadable or malformed space file, an ID with filters, no command."""
    w = session["ws"]
    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"x1": [0, 1], "x1": [0, 2]}')
    for argv in (
        ["bogus"],
        ["run", "ishigami"],
        ["price", "ishigami", "scatter", "--space", R2_SPACE, "--param", "n"],
        ["price", "ishigami", "scatter", "--space", R2_SPACE, "--param", "prediction=y"],
        ["price", "ishigami", "scatter", "--space", str(tmp_path / "missing.json")],
        ["price", "ishigami", "scatter", "--space", str(bad_json)],
        ["results", session["scatter"], "--model", "ishigami"],
        [],
    ):
        ran = ema_cli("--workspace", w, *argv)
        assert ran.code == 2 and ran.out == "", (argv, ran)
    assert ema_cli("--help").code == 0


def test_a_param_naming_runs_own_argument_says_where_it_goes(ema_cli, session):
    """Record 0082, Review round 1 (m2, n4): ``--param`` naming ``model``, ``diagnostic``, ``self``, or any of
    ``run``'s own keywords is bad usage (exit 2) saying where it goes (``approve`` is ``--yes``), never a
    ``TypeError``'s traceback."""
    w = session["ws"]
    for name, where in (("model", "MODEL"), ("diagnostic", "DIAGNOSTIC"), ("self", "nothing"), ("space", "--space"),
                        ("retry_failed", "--retry-failed"), ("approve", "--yes"), ("on_progress", "stderr")):  # fmt: skip
        for command in ("price", "run"):
            ran = ema_cli("--workspace", w, command, "ishigami", "point_run", "--param", f"{name}=1")
            assert ran.code == 2 and ran.out == "", (name, ran)
            assert f"--param {name} isn't a diagnostic parameter" in ran.err and where in ran.err, ran.err
            assert "Traceback" not in ran.err


def test_a_workspace_that_cant_be_made_is_ema_s_error(ema_cli, tmp_path):
    """Record 0082, Review round 1 (m2): ``--workspace`` where none can be made prints "ema: <reason>" and exits 1,
    not a traceback."""
    blocker = tmp_path / "file"
    blocker.write_text("")
    for workspace in ("/nonexistent/ema_workspace", str(blocker / "ema_workspace")):
        ran = ema_cli("--workspace", workspace, "models")
        assert ran.code == 1 and ran.out == "" and ran.err.startswith("ema: "), ran
        assert "Traceback" not in ran.err


def test_an_ema_error_exits_1(ema_cli, session):
    """An ``EMAError`` exits 1 with its message on stderr: a request refused (a bad parameter value), an unknown id."""
    w = session["ws"]
    for argv in (["price", "ishigami", "scatter", "--space", R2_SPACE, "--param", "n=0"],
                 ["price", "ishigami", "scatter"], ["report", "ffff"], ["price", "nope", "scatter"]):  # fmt: skip
        ran = ema_cli("--workspace", w, *argv)
        assert ran.code == 1 and ran.out == "" and ran.err.startswith("ema: "), (argv, ran)


# -- results ---------------------------------------------------------------------------------------------------


def test_results_list_filter_and_show(ema_cli, session):
    w, sid = session["ws"], session["scatter"]
    listed = ema_cli("--workspace", w, "results")
    assert listed.code == 0 and listed.out.count("Diagnostic result ") == 2
    only = ema_cli("--workspace", w, "results", "--diagnostic", "scatter")
    assert only.out.count("Diagnostic result ") == 1 and f"Diagnostic result {sid}: scatter" in only.out
    shown = ema_cli("--workspace", w, "results", sid)
    assert shown.code == 0 and shown.out.startswith(f"Diagnostic result {sid}: scatter on ishigami@")


def test_report_prints_the_markdown_and_its_path_on_stderr(ema_cli, session):
    """``ema report ID``: the Markdown on stdout, byte for byte the file's; the file's path on stderr (0060)."""
    ran = ema_cli("--workspace", session["ws"], "report", session["scatter"])
    assert ran.code == 0
    path = ran.err.removeprefix("Report: ").strip()
    assert ran.err == f"Report: {path}\n" and path.endswith("report.md")
    assert Path(path).read_bytes() == ran.out.encode("utf-8")


def test_report_pdf_path_on_stderr(ema_cli, session, monkeypatch):
    """With ``--pdf``, the PDF's path follows the report's, on stderr, as the workspace returned it (0060)."""
    asked = {}

    def report(self: Workspace, result: str, *, pdf: bool = False) -> Report:
        asked["pdf"] = pdf
        return Report("ab" * 32, "# R\n", "/w/results/ab/report.md", "/w/results/ab/report.pdf")

    monkeypatch.setattr(Workspace, "report", report)
    ran = ema_cli("--workspace", session["ws"], "report", "abab", "--pdf")
    assert ran.code == 0 and asked["pdf"] is True and ran.out == "# R\n"
    assert ran.err == "Report: /w/results/ab/report.md\nPDF: /w/results/ab/report.pdf\n"


def test_failed_runs_run_dirs_reproduce_and_export(ema_cli, session, tmp_path):
    w = session["ws"]
    failed = ema_cli("--workspace", w, "failed-runs", session["scatter"])
    assert failed.code == 0 and failed.out == "" and failed.err.startswith("No failed runs")
    point = tmp_path / "point.json"
    point.write_text(json.dumps({"x1": 1.0, "x2": 0.0, "x3": 0.0}))
    dirs = ema_cli("--workspace", w, "run-dirs", session["point_run"], "--point", str(point))
    assert dirs.code == 0 and dirs.out.startswith("Run ") and "at x1 = 1, x2 = 0, x3 = 0" in dirs.out
    run_id = dirs.out.split()[1].rstrip(":")
    one = ema_cli("--workspace", w, "run-dirs", run_id)
    assert one.code == 0 and one.out.startswith(f"Run {run_id}:") and one.out.count("\nRun ") == 0
    point.write_text(json.dumps({"x1": "one"}))
    assert ema_cli("--workspace", w, "run-dirs", session["point_run"], "--point", str(point)).code == 2
    replay = ema_cli("--workspace", w, "reproduce", session["scatter"])
    assert replay.code == 0 and "identical" in replay.out
    target = tmp_path / "export"
    exported = ema_cli("--workspace", w, "export", session["scatter"], str(target))
    assert exported.code == 0 and exported.out == f"{target}\n"
    assert {"runs.csv", "result.json", "report"} <= set(os.listdir(target))
    refused = ema_cli("--workspace", w, "export", session["scatter"], str(target))  # not empty now (E1)
    assert refused.code == 1 and refused.err.startswith("ema: ")


# -- ema mcp (T5; 0061) ------------------------------------------------------------------------------------------


@pytest.fixture
def fake_server(monkeypatch):
    """Stand in for ``ema.mcp.server`` (step 15): ``serve`` opens the workspace under the root, as the server does."""
    calls: list[dict[str, str]] = []

    def serve(*, root: str, workspace: str) -> None:
        calls.append({"root": root, "workspace": workspace})
        open_workspace(workspace, root=root).close()

    package, module = types.ModuleType("ema.mcp"), types.ModuleType("ema.mcp.server")
    module.serve = serve  # type: ignore[attr-defined]
    package.server = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ema.mcp", package)
    monkeypatch.setitem(sys.modules, "ema.mcp.server", module)
    return calls


def test_mcp_refuses_a_missing_relative_or_slash_root(ema_cli, fake_server):
    """``ema mcp`` without ``--root``, with a relative one, or with ``/``: exit 2, the server not started (T5)."""
    for argv in (["mcp"], ["mcp", "--root", "project"], ["mcp", "--root", "/"], ["mcp", "--root", "//."]):
        ran = ema_cli(*argv)
        assert ran.code == 2 and ran.out == "", (argv, ran)
    assert fake_server == []


def test_mcp_refuses_a_root_inside_a_workspace(ema_cli, fake_server, tmp_path):
    """A root inside a workspace (its ``runs/``) is refused at start by ``open_workspace``: exit 2 (T5; 0061)."""
    open_workspace(tmp_path / "other").close()
    ran = ema_cli("mcp", "--root", str(tmp_path / "other" / "runs"))
    assert ran.code == 2 and "inside the workspace" in ran.err
    missing = ema_cli("mcp", "--root", str(tmp_path / "nowhere"))
    assert missing.code == 2


def test_mcp_starts_the_server_with_the_root_and_workspace(ema_cli, fake_server, tmp_path):
    """``serve(root=, workspace=)``: the absolute root, and ``--workspace`` as given (resolved against the root)."""
    ran = ema_cli("--workspace", "study", "mcp", "--root", str(tmp_path))
    assert ran.code == 0 and ran.out == ""
    assert fake_server == [{"root": str(tmp_path), "workspace": "study"}]
    assert os.path.isfile(tmp_path / "study" / "ema.db")


def test_mcp_without_the_extra_says_what_to_install(ema_cli, monkeypatch, tmp_path):
    """Without ``ema[mcp]``, the import fails: the message names the extra, exit 2 (0061)."""
    monkeypatch.setitem(sys.modules, "ema.mcp.server", None)  # import fails, with or without ema.mcp installed
    ran = ema_cli("mcp", "--root", str(tmp_path))
    assert ran.code == 2 and "ema[mcp]" in ran.err and ran.out == ""


# -- the progress line -----------------------------------------------------------------------------------------


class _Stream(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__()
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty


def test_progress_line_on_a_terminal_and_in_a_log(monkeypatch):
    """On a terminal the line is rewritten in place; otherwise a line at each tenth and at the end (PM10)."""
    monkeypatch.setattr(sys, "stderr", _Stream(tty=False))
    line = cli.ProgressLine()
    for done in range(101):
        line(Progress.of_runs(done, 100))
    logged = sys.stderr.getvalue().splitlines()
    assert logged == [f"{d}/100 runs" for d in range(0, 101, 10)]
    monkeypatch.setattr(sys, "stderr", _Stream(tty=True))
    line = cli.ProgressLine()
    line(Progress.of_runs(9, 10))
    line(Progress.of_runs(10, 10))
    line.end()
    assert sys.stderr.getvalue() == "\r9/10 runs\r10/10 runs\n"


def test_export_pdf_that_cant_be_made_is_an_error_and_writes_nothing(ema_cli, session, tmp_path, monkeypatch):
    """``ema export ID DIR --pdf`` (record 0081 item 31): with no pandoc, "ema: …" naming it, exit 1, no directory."""
    import shutil

    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "pandoc" else real(name, *a, **k))
    target = tmp_path / "pdf_export"
    done = ema_cli("--workspace", session["ws"], "export", session["scatter"], str(target), "--pdf")
    assert done.code == 1 and done.err.startswith("ema: ") and "pandoc" in done.err and not target.exists()
