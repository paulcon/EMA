"""Layer 3b: approval, P3's one module: asking for the user's yes, and recording every answer (T3).

The questions are asked before new runs, and before saving a model spec an MCP client drafted.

architecture.md §6 (``ema.approval``); trust.md (What needs a yes; Paths: hidden characters as codes, strings EMA
didn't write in code spans and fenced blocks; T3, T4, T6, T7, T8); data_model.md W2, W3, Q3, Q4; use_cases.md U1,
U2, U9; records 0016, 0029, 0049, 0054, 0057, 0074.

v1's approval rules that ``scope.md`` keeps are placed by layer (0057): the checks a spec needs are in
``ema.types.model`` and ``ema.models.files``, the environment in ``ema.models.sandbox``; asking and recording,
and the questions' text, are here.
"""

import json
import os
import re
import sys
import unicodedata

import numpy as np

from ema.models.files import check_files, open_regular
from ema.models.spec import LoadedModel, resolve_program
from ema.store import Store
from ema.types.design import DesignIdentity
from ema.types.errors import ApprovalDeclined, CannotAsk
from ema.types.identity import model_version_label, sha256_hex
from ema.types.model import CommandLine, PythonFunction
from ema.types.requests import ApprovalRequest, Approver, ConfirmationRequest, Request, TestRunRequest
from ema.types.runs import Price, Resolution

#: The hidden characters' categories (trust.md, Paths; T7): printed in a question as codes.
_HIDDEN = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
#: Hidden characters printed as themselves: tab, and the joiners U+200C and U+200D (the spec's checks allow them).
_SHOWN = frozenset({"\t", "‌", "‍"})
_TICKS = re.compile("`+")


def _visible(text: str, *, lines: bool) -> str:
    """Write each hidden character as its code (a backslash, u, and 4 hex digits); a line feed only in a block (T7)."""
    out = []
    for ch in text:
        if (ch == "\n" and lines) or ch in _SHOWN or unicodedata.category(ch) not in _HIDDEN:
            out.append(ch)
        else:
            code = ord(ch)
            out.append(f"\\u{code:04x}" if code < 0x10000 else f"\\U{code:08x}")
    return "".join(out)


def _longest_ticks(text: str) -> int:
    return max((len(run) for run in _TICKS.findall(text)), default=0)


def _span(text: str, *, path: bool = False) -> str:
    """Show a string EMA didn't write, on one line: a code span, its backticks longer than any run in it (T7).

    In a path a backslash is doubled, so a backslash typed in a name can't pass for a hidden character's code.
    """
    shown = _visible(text.replace("\\", "\\\\") if path else text, lines=False)
    if not shown:
        return "(empty)"
    ticks = "`" * (_longest_ticks(shown) + 1)
    padded = shown.startswith("`") or shown.endswith("`") or (shown[0] == shown[-1] == " " and shown.strip())
    return f"{ticks} {shown} {ticks}" if padded else f"{ticks}{shown}{ticks}"


def fenced(text: str) -> str:
    """Show a text EMA didn't write, of several lines: a fenced block, longer than any run of backticks in it (T7).

    Public for the workspace, which fences a drafted spec's text and a failed run's stderr tail with it (record
    0080, Review round 1), so the T7 rule has one home.
    """
    shown = _visible(text, lines=True)
    fence = "`" * max(3, _longest_ticks(shown) + 1)
    return f"{fence}\n{shown if shown.endswith(chr(10)) else shown + chr(10)}{fence}"


def _file_text(model: LoadedModel, relative: str) -> str:
    try:
        with open_regular(os.path.join(model.model_dir, *relative.split("/"))) as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return f"(couldn't be read: {e.strerror})"


def _what_runs(model: LoadedModel, program: str | None, pass_env: dict[str, bool]) -> list[str]:
    """Write the first approval's details (U2, 0029, trust.md What needs a yes, T8): what each run starts."""
    spec, interface = model.spec, model.spec.interface
    lines = ["", "The model version's first approval: what each run starts."]
    if isinstance(interface, CommandLine):
        lines.append(f"Command: {_span(json.dumps(list(interface.command), ensure_ascii=False))}")
        lines.append(f"Program: {_span(program, path=True)}" if program else
                     f"Program: {_span(interface.command[0])}, not found on the model's PATH")  # fmt: skip
        for deck in interface.input_decks:
            lines.append(
                f"Input deck {_span(deck.writes, path=True)}, from the template {_span(deck.template, path=True)}:"
            )
            lines.append(fenced(_file_text(model, deck.template)))
    else:
        lines.append(f"Function: {_span(interface.function)}")
        lines.append(f"Interpreter: {_span(program or sys.executable, path=True)}")
    where = (
        "each batch call's directory"
        if isinstance(interface, PythonFunction) and interface.batch
        else "each run directory"
    )
    if spec.files:
        lines.append(f"Files in {where}:")
        lines += [f"- {_span(f.path, path=True)}" + (" (shared: a link to a read-only stored copy)" if f.shared else "")
                  for f in spec.files]  # fmt: skip
    else:
        lines.append(f"Files in {where}: none.")
    if spec.env or pass_env:
        lines.append("Environment beyond EMA's base variables:")
        lines += [f"- {_span(f'{name}={value}')}" for name, value in spec.env.items()]
        lines += [f"- {_span(name)}: passed from EMA's environment, {'set' if is_set else 'not set'}"
                  for name, is_set in pass_env.items()]  # fmt: skip
    else:
        lines.append("Environment: EMA's base variables only.")
    return lines


def _approval_request(store: Store, model: LoadedModel, asked_for: str, request: Request | TestRunRequest,
                      price: Price) -> ApprovalRequest:  # fmt: skip
    """Render the question (P3, U2, trust.md): the model version and the price; on its first approval, what runs."""
    spec, interface = model.spec, model.spec.interface
    label = model_version_label(spec.name, model.model_version_id)
    first = not store.has_approval(model.model_version_id)
    if first:  # the templates shown are the model version's own (M16, P3; record 0074, item 25)
        check_files(model)
    program = resolve_program(model)
    pass_env = {name: name in os.environ for name in spec.pass_env}
    if isinstance(request, TestRunRequest):
        what = "the test run at the nominal point"
    else:
        what = f"{request.diagnostic} on {_span(request.prediction)}"
    lines = [f"New runs of the model version {_span(label)}: {what}.", f"Price: {price.text}"]
    if first:
        lines += _what_runs(model, program, pass_env)
    command = tuple(interface.command) if isinstance(interface, CommandLine) else None
    decks = interface.input_decks if isinstance(interface, CommandLine) else ()
    return ApprovalRequest(
        asked_for="test_run" if asked_for == "test_run" else "diagnostic_evaluation",
        model_version=label,
        price=price,
        first_for_version=first,
        command=command,
        program=program,
        templates={deck.template: _file_text(model, deck.template) for deck in decks},
        files=tuple(f.path for f in spec.files),
        function=interface.function if isinstance(interface, PythonFunction) else None,
        env=dict(spec.env),
        pass_env=pass_env,
        text="\n".join(lines),
    )


def _answer(approve: Approver, question: ApprovalRequest | ConfirmationRequest) -> tuple[bool, str]:
    """Ask: only ``True`` is a yes (record 0074, item 11); an exception is a no, with its reason."""
    try:
        return approve(question) is True, ""
    except Exception as e:  # noqa: BLE001  (an approver that fails says no: trust.md, No answer is a no)
        return False, f" (the question failed: {_span(f'{type(e).__name__}: {e}')})"


def ask_approval(
    *,
    store: Store,
    model: LoadedModel,
    asked_for: str,
    request: Request | TestRunRequest,
    design: DesignIdentity | None,
    resolution: Resolution,
    price: Price,
    approve: Approver | None,
) -> str:
    """Ask for the user's yes to new runs, and record the question and its answer (P3; T3, T4; W3).

    The question shows the model version and the price; on the model version's first approval (Q4) also what each
    run starts: the command and the program's resolved path, or a Python function's ``function`` and the child's
    interpreter, the input deck templates, the files, and the environment the spec sets (U2, 0029, trust.md). Only
    ``True`` is a yes; an exception from ``approve`` is a no, recorded; Ctrl-C at the question is recorded as a no
    and passes through.

    Parameters
    ----------
    store
        The workspace's store, whose run lock the caller holds.
    model
        The loaded model.
    asked_for
        "diagnostic_evaluation" or "test_run" (0049).
    request
        The canonical request, or the test run's.
    design
        The design's identity; None for the test run.
    resolution
        The resolved design: its new keys are the approved points.
    price
        Its price.
    approve
        The approver; None when nobody can be asked (an MCP client without elicitation).

    Returns
    -------
    str
        The approval id.

    Raises
    ------
    CannotAsk
        With ``approve=None``, at once: nothing is rendered or recorded, since nothing was asked (T3).
    ApprovalDeclined
        On a no ("declined: no runs made").
    ValueError
        For no new runs (C50), a price that isn't the resolution's, or a request or design that isn't
        ``asked_for``'s; nothing is asked or recorded.
    NotFound
        For a model version the store doesn't hold; nothing is asked or recorded.
    ModelChanged
        On a first approval, when a tracked file changed since loading; nothing is asked or recorded.
    """
    if approve is None:
        raise CannotAsk("nobody can be asked to approve new runs: use the CLI or Python; nothing was asked (P3)")
    if not resolution.new_keys:
        raise ValueError("no approval is asked for no new runs (C50)")
    if resolution.model_version_id != model.model_version_id:
        raise ValueError("the resolution is of another model version than the model's")
    stored = resolution.row_runs[resolution.row_keys < 0]
    reused = len(np.unique(stored)) if len(stored) else 0
    if (price.new, price.reused, price.reused_failed) != (len(resolution.new_keys), reused, resolution.reused_failed):
        raise ValueError(f"the price ({price.text}) isn't the resolution's ({len(resolution.new_keys)} new runs, "
                         f"{reused} reused)")  # fmt: skip
    if (asked_for == "test_run") != isinstance(request, TestRunRequest) or asked_for not in (
        "test_run",
        "diagnostic_evaluation",
    ):
        raise ValueError(f"an approval for {asked_for!r} doesn't take a {type(request).__name__}")
    if (design is None) != (asked_for == "test_run"):
        raise ValueError("an approval has a design exactly when it is for a diagnostic evaluation (0049)")
    store.model_version(model.model_version_id)  # NotFound before anything is asked (W3; T3)
    question = _approval_request(store, model, asked_for, request, price)

    def record(answer: bool) -> str:
        return store.record_approval(model_version_id=model.model_version_id, asked_for=asked_for, request=request,
                                     design=design, price=price, question=question.text, answer=answer,
                                     points=resolution.new_keys)  # fmt: skip

    try:
        yes, why = _answer(approve, question)
    except BaseException:  # Ctrl-C at the question: recorded as a no (T3), and passed through
        record(False)
        raise
    approval_id = record(yes)
    if not yes:
        raise ApprovalDeclined(f"declined: no runs made{why}")
    return approval_id


def _meaning(store: Store, spec_text: str, saved: bool) -> str | None:
    """Say what the drafted spec's name means now, when it is loaded (0054, T6)."""
    try:
        name = json.loads(spec_text)["name"]
    except (ValueError, TypeError, KeyError):
        return None
    loading = store.current_loading(name) if isinstance(name, str) else None
    if loading is None:
        return None
    label = model_version_label(name, loading.model_version_id)
    doing = "loading" if saved else "saving"
    return (
        f"{_span(name)} now means {_span(label)} at {_span(loading.spec_path, path=True)}; {doing} makes it "
        "mean this spec."
    )


def _same_bytes(path: str, data: bytes) -> bool:
    try:
        with open_regular(path) as f:
            return f.read(len(data) + 1) == data
    except OSError:
        return False


def ask_confirmation(*, store: Store, spec_path: str, spec_text: str, confirm: Approver | None) -> None:
    """Ask for the user's yes to saving a model spec an MCP client drafted, and record it (W2; 0049; T3, T6).

    The question shows the absolute path, what the spec's name means now when it is loaded (Q3, 0054), and the
    spec's full text, as it will be written; a file at the path with the same bytes asks "already saved, unchanged:
    load it?".

    Parameters
    ----------
    store
        The workspace's store.
    spec_path
        Absolute, its parent resolved through its links (T6).
    spec_text
        The spec's exact text.
    confirm
        The approver; None when nobody can be asked.

    Raises
    ------
    CannotAsk
        With ``confirm=None``, at once; nothing is recorded.
    ApprovalDeclined
        On a no.
    ValueError
        For a relative path.
    """
    if confirm is None:
        raise CannotAsk("nobody can be asked to confirm saving a model spec: nothing was asked or saved (P3)")
    if not os.path.isabs(spec_path):
        raise ValueError(f"a model spec is saved at an absolute path, not {spec_path!r}")
    data = spec_text.encode("utf-8")
    saved = _same_bytes(spec_path, data)
    replaces = _meaning(store, spec_text, saved)
    shown = _span(spec_path, path=True)
    first = (f"{shown} is already saved, unchanged: load it?" if saved else
             f"Save the model spec an MCP client drafted to {shown}?")  # fmt: skip
    lines = [first, *([replaces] if replaces else []), "The spec's full text:", fenced(spec_text)]
    question = ConfirmationRequest(spec_path, replaces, spec_text, "\n".join(lines))
    try:
        yes, why = _answer(confirm, question)
    except BaseException:
        store.record_confirmation(spec_path, sha256_hex(data), question.text, False)
        raise
    store.record_confirmation(spec_path, sha256_hex(data), question.text, yes)
    if not yes:
        raise ApprovalDeclined(f"declined: no model spec saved{why}")


def ask(question: ApprovalRequest | ConfirmationRequest) -> bool:
    """Ask on the terminal (``ema.ask``): the question and ``Approve? [y/N]`` on stderr, the answer from stdin.

    The terminal approver. Nothing is written to stdout (T9). "y" or "yes", in any case, is a yes; anything else, end of input, or no
    stdin is a no.

    Parameters
    ----------
    question
        The question.

    Returns
    -------
    bool
        The answer.
    """
    prompt = "Approve? [y/N] " if isinstance(question, ApprovalRequest) else "Confirm? [y/N] "
    sys.stderr.write(f"{question.text}\n{prompt}")
    sys.stderr.flush()
    try:
        line = sys.stdin.readline() if sys.stdin is not None else ""
    except (OSError, ValueError):
        line = ""
    return line.strip().lower() in ("y", "yes")
