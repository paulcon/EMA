"""``ema.approval``: asking, the questions' text, and recording every answer (P3; trust.md T3, T4, T6, T7, T8, What
needs a yes; use_cases.md U1, U2; 0049; record 0074)."""

import io
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ema.approval import ask, ask_approval, ask_confirmation
from ema.models.spec import LoadedModel, load_spec
from ema.runner import price, resolve
from ema.store import Store
from ema.types.errors import ApprovalDeclined, CannotAsk, ModelChanged, NotFound
from ema.types.identity import model_version_label, sha256_hex
from ema.types.requests import ApprovalRequest, ConfirmationRequest, TestRunRequest
from tests.support import store as world
from tests.support.models import copy_model, point
from tests.support.runner import design

U202E = chr(0x202E)


@contextmanager
def toy(tmp_path: Path, kind: str = "command_line", edit: Any = None) -> Iterator[tuple[Store, LoadedModel]]:
    """A store with a copy of a toy loaded (no runs)."""
    path = copy_model(kind, tmp_path / "models")
    if edit is not None:
        spec = json.loads(path.read_text())
        edit(spec, path.parent)
        path.write_text(json.dumps(spec))
    model = load_spec(str(path))
    with Store.open(tmp_path / "ws") as store:
        store.record_loading(model.spec, model.spec_path, model.files)
        yield store, model


class Asked:
    """An approver that records each question and gives answers in turn (an exception is raised)."""

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.questions: list[ApprovalRequest | ConfirmationRequest] = []

    def __call__(self, question: ApprovalRequest | ConfirmationRequest) -> bool:
        self.questions.append(question)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def asking(store: Store, model: LoadedModel, approve: Any, *, test_run: bool = False, points: Any = None) -> str:
    """Resolve, price, and ask, as the workspace does (architecture.md §7, step 6)."""
    rows = design(points or [point(0)])
    res = resolve(rows, model, store, retry_failed=False)
    if test_run:
        return ask_approval(store=store, model=model, asked_for="test_run", request=TestRunRequest(tuple(point(0))),
                            design=None, resolution=res, price=price(res, store), approve=approve)  # fmt: skip
    request = world.request(prediction="y")
    return ask_approval(store=store, model=model, asked_for="diagnostic_evaluation", request=request,
                        design=world.identity(model.model_version_id, request), resolution=res,
                        price=price(res, store), approve=approve)  # fmt: skip


def test_every_question_asked_is_recorded_and_none_when_nobody_can_be_asked(tmp_path):
    """T3: yes, no, an exception in the approver, and approve=None: three records and none, in order."""
    with toy(tmp_path) as (store, model):
        approver = Asked(True, False, RuntimeError("the client went away"))
        approval = asking(store, model, approver, test_run=True)
        with pytest.raises(ApprovalDeclined, match="declined"):
            asking(store, model, approver, points=[point(0, a=2.0)])
        with pytest.raises(ApprovalDeclined) as raised:
            asking(store, model, approver, points=[point(0, a=3.0)])
        assert not isinstance(raised.value, CannotAsk)
        with pytest.raises(CannotAsk):
            asking(store, model, None, points=[point(0, a=4.0)])
        records = store.approvals()
        assert [r.answer for r in records] == [True, False, False]
        assert [r.question for r in records] == [q.text for q in approver.questions]
        assert records[0].approval_id == approval and records[0].asked_for == "test_run"
        assert [len(store.approval_points(r.approval_id)) for r in records] == [1, 0, 0]


def test_only_true_is_a_yes(tmp_path):
    with toy(tmp_path) as (store, model):
        for answer in ("yes", 1, None):
            with pytest.raises(ApprovalDeclined):
                asking(store, model, Asked(answer))
        assert [r.answer for r in store.approvals()] == [False, False, False]


def test_ctrl_c_at_the_question_is_recorded_as_no_and_passes_through(tmp_path):
    with toy(tmp_path) as (store, model):
        with pytest.raises(KeyboardInterrupt):
            asking(store, model, Asked(KeyboardInterrupt()))
        assert [r.answer for r in store.approvals()] == [False]


def test_the_first_approval_shows_what_runs_and_later_ones_dont(tmp_path, monkeypatch):
    """U2, trust.md What needs a yes, T8: the command, the program's path, the template, the files, and the
    environment the spec sets, each pass_env name with "set" or "not set" and never its value; the price."""
    monkeypatch.setenv("LM_LICENSE_FILE", "27000@license-host")

    def edit(spec: dict[str, Any], _: Path) -> None:
        spec["pass_env"] = ["LM_LICENSE_FILE", "NOT_SET_HERE_EMA"]
        spec["env"]["OMP_NUM_THREADS"] = "1"

    monkeypatch.delenv("NOT_SET_HERE_EMA", raising=False)
    with toy(tmp_path, edit=edit) as (store, model):
        approver = Asked(False, True, True)
        with pytest.raises(ApprovalDeclined):
            asking(store, model, approver, test_run=True)
        asking(store, model, approver, test_run=True)
        asking(store, model, approver, points=[point(0, a=2.0)])
        declined, first, later = approver.questions
        label = model_version_label(model.spec.name, model.model_version_id)
        assert first.first_for_version and declined.first_for_version and not later.first_for_version
        assert first.text == declined.text
        text = first.text
        assert f"`{label}`" in text and "the test run at the nominal point" in text
        assert "Price: 1 new run, 0 reused, time unknown" in text
        assert '`["python3", "solver.py", "deck.in"]`' in text
        assert first.program and f"`{first.program}`" in text and first.program.endswith("python3")
        template = (Path(model.model_dir) / "deck.in.template").read_text()
        assert template in text and "`deck.in.template`" in text and "`deck.in`" in text
        assert "`solver.py`" in text and "`mesh.dat`" in text
        assert "`OMP_NUM_THREADS=1`" in text and "`LM_LICENSE_FILE`: passed from EMA's environment, set" in text
        assert "`NOT_SET_HERE_EMA`: passed from EMA's environment, not set" in text
        assert "27000@license-host" not in text and "license-host" not in store.approvals()[1].question
        assert dict(first.pass_env) == {"LM_LICENSE_FILE": True, "NOT_SET_HERE_EMA": False}
        assert first.command == ("python3", "solver.py", "deck.in") and first.function is None
        assert "solver.py" not in later.text and "Command" not in later.text
        assert f"`{label}`" in later.text and "scatter on `y`" in later.text and "Price: 1 new run" in later.text


def test_a_python_functions_first_approval_shows_the_function_and_the_interpreter(tmp_path):
    """0029: a Python function's `function` in place of the command, and the child's interpreter."""
    with toy(tmp_path, "python") as (store, model):
        approver = Asked(True)
        asking(store, model, approver)
        (question,) = approver.questions
        assert question.function == "model.py:f" and question.command is None
        assert "`model.py:f`" in question.text and f"`{sys.executable}`" in question.text
        assert "`helper.py`" in question.text and "`mesh.dat` (shared" in question.text


def test_hidden_characters_print_as_codes_and_text_ema_didnt_write_is_fenced(tmp_path):
    """T7: a template with U+202E shows `\\u202e`, and its lines as lines; a line of three backticks shows as typed,
    inside a longer fence."""

    def edit(spec: dict[str, Any], directory: Path) -> None:
        (directory / "deck.in.template").write_text(f"a = $a\nb = $b {U202E}cba\n```\nmode = $mode\n", encoding="utf-8")

    with toy(tmp_path, edit=edit) as (store, model):
        approver = Asked(True)
        asking(store, model, approver)
        text = approver.questions[0].text
        assert U202E not in text
        assert "a = $a\nb = $b \\u202ecba\n```\nmode = $mode\n" in text
        assert "\n````\na = $a" in text and "mode = $mode\n````" in text


def test_no_question_for_no_new_runs_and_a_price_that_isnt_the_resolutions(tmp_path):
    with toy(tmp_path) as (store, model):
        res = resolve(design([point(0)]), model, store, retry_failed=False)
        request = TestRunRequest(tuple(point(0)))
        for wrong in (replace(price(res, store), new=2), replace(price(res, store), reused=1, from_runs=1, time_s=1.0)):
            with pytest.raises(ValueError, match="isn't the resolution's"):
                ask_approval(store=store, model=model, asked_for="test_run", request=request, design=None,
                             resolution=res, price=wrong, approve=Asked(True))  # fmt: skip
        empty = resolve(design(np.zeros((0, 3))), model, store, retry_failed=False)
        with pytest.raises(ValueError, match="no new runs"):
            ask_approval(store=store, model=model, asked_for="test_run", request=request, design=None,
                         resolution=empty, price=price(empty, store), approve=Asked(True))  # fmt: skip
        assert store.approvals() == ()


def test_a_design_that_isnt_asked_fors_and_an_unknown_model_version_ask_nothing(tmp_path):
    """W3, T3 (record 0074, review round 1): checked before the question is rendered or asked, so nothing is."""
    approver = Asked(True)
    with toy(tmp_path) as (store, model):
        res = resolve(design([point(0)]), model, store, retry_failed=False)
        request = world.request(prediction="y")
        identity = world.identity(model.model_version_id, request)
        for asked_for, req, dsg in (("test_run", TestRunRequest(tuple(point(0))), identity),
                                    ("diagnostic_evaluation", request, None)):  # fmt: skip
            with pytest.raises(ValueError, match="a design exactly when"):
                ask_approval(store=store, model=model, asked_for=asked_for, request=req, design=dsg, resolution=res,
                             price=price(res, store), approve=approver)  # fmt: skip
        assert store.approvals() == ()
    with Store.open(tmp_path / "empty") as empty:
        res = resolve(design([point(0)]), model, empty, retry_failed=False)
        with pytest.raises(NotFound):
            ask_approval(store=empty, model=model, asked_for="test_run", request=TestRunRequest(tuple(point(0))),
                         design=None, resolution=res, price=price(res, empty), approve=approver)  # fmt: skip
        assert empty.approvals() == ()
    assert approver.questions == []


def test_a_first_approval_after_a_template_changed_asks_nothing(tmp_path):
    """M16, P3 (record 0074, review round 1): the first approval shows the model version's own templates."""
    with toy(tmp_path) as (store, model):
        template = Path(model.model_dir) / "deck.in.template"
        template.write_text(template.read_text() + "x = 1\n")
        approver = Asked(True)
        with pytest.raises(ModelChanged, match="deck.in.template"):
            asking(store, model, approver, test_run=True)
        assert approver.questions == [] and store.approvals() == ()


def test_an_approvers_failure_shows_its_hidden_characters_as_codes(tmp_path):
    """T7: the reason a failed question gives is text EMA didn't write."""
    with toy(tmp_path) as (store, model):
        with pytest.raises(ApprovalDeclined) as raised:
            asking(store, model, Asked(RuntimeError("gone\x1b[2K")))
        message = str(raised.value)
        assert "\x1b" not in message and "`RuntimeError: gone\\u001b[2K`" in message, message


def test_a_backslash_in_a_path_is_doubled_so_it_cant_pass_for_a_code(tmp_path):
    """T7 (record 0074, review round 1): a path holding a backslash and "u202e" isn't shown as U+202E is."""
    with Store.open(tmp_path / "ws") as store:
        approver = Asked(True)
        target = tmp_path / f"a\\u202e{U202E}.json"
        ask_confirmation(store=store, spec_path=str(target), spec_text='{"name": "fresh"}\n', confirm=approver)
        assert "a\\\\u202e\\u202e.json" in approver.questions[0].text


def test_the_confirmation_shows_the_path_what_the_name_means_now_and_the_full_text(tmp_path):
    """T6, 0054: the absolute path, the loaded name's meaning, the full text; recorded with its hash (W2)."""
    with toy(tmp_path) as (store, model):
        spec_text = (Path(model.spec_path)).read_text()
        target = tmp_path / "drafts" / "<!-- x -->.json"
        target.parent.mkdir()
        approver = Asked(True, False)
        ask_confirmation(store=store, spec_path=str(target), spec_text=spec_text, confirm=approver)
        question = approver.questions[0]
        assert isinstance(question, ConfirmationRequest)
        label = model_version_label(model.spec.name, model.model_version_id)
        assert f"`{target}`" in question.text and spec_text in question.text
        assert question.replaces and f"`{label}`" in question.replaces and f"`{model.spec_path}`" in question.replaces
        assert question.replaces in question.text
        target.write_text(spec_text)
        with pytest.raises(ApprovalDeclined):
            ask_confirmation(store=store, spec_path=str(target), spec_text=spec_text, confirm=approver)
        assert "already saved, unchanged: load it?" in approver.questions[1].text
        records = store.confirmations()
        assert [r.answer for r in records] == [True, False]
        assert records[0].spec_sha256 == sha256_hex(spec_text.encode())
        assert records[0].question == question.text and records[0].spec_path == str(target)
        with pytest.raises(CannotAsk):
            ask_confirmation(store=store, spec_path=str(target), spec_text=spec_text, confirm=None)
        with pytest.raises(ValueError, match="absolute"):
            ask_confirmation(store=store, spec_path="x.json", spec_text=spec_text, confirm=approver)
        assert len(store.confirmations()) == 2


def test_a_new_names_confirmation_says_nothing_of_a_meaning(tmp_path):
    with Store.open(tmp_path / "ws") as store:
        approver = Asked(True)
        ask_confirmation(store=store, spec_path=str(tmp_path / "m.json"), spec_text='{"name": "fresh"}\n',
                         confirm=approver)  # fmt: skip
        assert approver.questions[0].replaces is None


@pytest.mark.parametrize(("typed", "expected"), [("y\n", True), ("YES\n", True), ("n\n", False), ("\n", False),
                                                 ("", False), ("maybe\n", False)])  # fmt: skip
def test_ask_reads_y_or_n_and_end_of_input_is_a_no(typed, expected, monkeypatch, capsys):
    """ema.ask: the question and its prompt on stderr, nothing on stdout (T9), y/N from stdin."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(typed))
    question = ConfirmationRequest("/x/m.json", None, "{}", "Save it?")
    assert ask(question) is expected
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("Save it?\n") and "[y/N]" in err
