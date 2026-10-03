"""Layer 5: the command line, ``ema`` (architecture.md §8; scope.md's 13 commands of 15).

Presentation only (AR3): each command parses its arguments, calls one workspace function, and writes the text EMA
rendered, so it formats no number (C54; P1). It imports only ``ema.workspace`` and ``ema.types``; the ``mcp`` command
imports ``ema.mcp.server`` lazily, inside the command, since it needs the ``ema[mcp]`` extra (record 0061).

Streams: the result on stdout; questions, progress, paths of a report, and errors on stderr (0060; trust.md T9).
Exit codes: 0 success; 1 an ``EMAError`` (a declined approval included) or an ``OSError``; 2 bad usage, or ``ema mcp``'s root refused
at start (T5; 0061); 130 Ctrl-C.
"""

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any, NoReturn

from ema.types.errors import EMAError, PathRefused
from ema.types.requests import ApprovalRequest, ConfirmationRequest, Progress
from ema.workspace import Workspace, ask, open_workspace

__all__ = ["main"]

#: ``run``'s and ``price``'s own arguments, which a ``--param`` can't name, and where each goes instead (0082 item 3;
#: Review round 1, m2 and n4): never the workspace's ``TypeError``.
RESERVED_PARAMS = {
    "model": "the MODEL argument",
    "diagnostic": "the DIAGNOSTIC argument",
    "space": "--space FILE",
    "prediction": "--prediction",
    "retry_failed": "--retry-failed",
    "approve": "--yes (ema run), or your answer to the question",
    "on_progress": "nothing: the progress line is on stderr",
    "self": "nothing",
}

EXTRA_MISSING = "ema mcp needs the ema[mcp] extra: uv sync --extra mcp (or pip install 'ema[mcp]')"


class UsageError(Exception):
    """Bad usage found after argparse: an unreadable ``--space`` file, a malformed ``--param`` (exit 2)."""


class _Parser(argparse.ArgumentParser):
    """An argument parser that raises ``UsageError`` instead of exiting, so ``main`` returns its code."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(f"{self.format_usage()}{self.prog}: error: {message}")


# -- reading the arguments ---------------------------------------------------------------------------------------


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"the key {key!r} appears twice")
        out[key] = value
    return out


def _refuse_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} isn't JSON")


def _json_file(path: str, what: str) -> dict[str, Any]:
    """Read a JSON object from a file (``--space``, ``--point``): a duplicate key or NaN refused (UsageError)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=_strict_object, parse_constant=_refuse_constant)
    except OSError as error:
        raise UsageError(f"{what} {path}: {error.strerror or error}") from None
    except ValueError as error:
        raise UsageError(f"{what} {path} isn't a JSON object: {error}") from None
    if not isinstance(data, dict):
        raise UsageError(f"{what} {path} isn't a JSON object")
    return data


def _params(given: Sequence[str] | None) -> dict[str, str]:
    """Read ``--param k=v`` options into text values, which the diagnostic's ``DiagnosticParameter`` parses (§8)."""
    params: dict[str, str] = {}
    for item in given or ():
        key, sep, value = item.partition("=")
        key = key.strip()
        if not sep or not key:
            raise UsageError(f"--param {item!r}: write it as name=value")
        if key in RESERVED_PARAMS:
            raise UsageError(f"--param {key} isn't a diagnostic parameter: it goes in {RESERVED_PARAMS[key]}")
        if key in params:
            raise UsageError(f"--param {key} is given twice")
        params[key] = value
    return params


def _point(path: str) -> dict[str, float]:
    point = _json_file(path, "the point file")
    for name, value in point.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UsageError(f"the point file {path}: {name}'s value is a number, not {value!r}")
    return point


# -- writing ---------------------------------------------------------------------------------------------------


def _out(text: str) -> None:
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    sys.stdout.flush()


def _err(text: str) -> None:
    sys.stderr.write(text + "\n")
    sys.stderr.flush()


def shown(items: Sequence[object]) -> str:
    """EMA's texts of a list, one after another: a blank line between them when any takes several lines (C54)."""
    texts = [str(item) for item in items]
    return ("\n\n" if any("\n" in t for t in texts) else "\n").join(texts)


def _out_all(items: Sequence[object], none: str) -> None:
    if items:
        _out(shown(items))
    else:
        _err(none)


# -- the approver and the progress line ------------------------------------------------------------------------


def approver(yes: bool) -> Callable[[ApprovalRequest | ConfirmationRequest], bool]:
    """Build the CLI's approver: the question on stderr, then ``Approve? [y/N]`` (architecture.md §8; trust.md, P3).

    With ``yes`` the answer is given in advance: the question is still shown, and recorded with its yes (W3). With
    no terminal on stdin and no ``--yes``, there is no answer, which is a no (recorded as a no).
    """

    def approve(question: ApprovalRequest | ConfirmationRequest) -> bool:
        prompt = "Approve? [y/N]" if isinstance(question, ApprovalRequest) else "Confirm? [y/N]"
        if yes:
            _err(f"{question.text}\n{prompt} y (--yes)")
            return True
        stdin = sys.stdin
        if stdin is None or not stdin.isatty():
            _err(f"{question.text}\n{prompt} no answer: no terminal, and no --yes")
            return False
        return ask(question)

    return approve


class ProgressLine:
    """Show EMA's progress text on stderr (PM10): rewritten in place on a terminal, else a line at each tenth."""

    def __init__(self) -> None:
        self.last: Progress | None = None
        self._step: tuple[str, int, int] | None = None
        self._tty = bool(getattr(sys.stderr, "isatty", lambda: False)())
        self._width = 0

    def __call__(self, progress: Progress) -> None:
        self.last = progress
        if self._tty:
            pad = max(0, self._width - len(progress.text))
            sys.stderr.write("\r" + progress.text + " " * pad)
            self._width = len(progress.text)
            sys.stderr.flush()
            return
        step = (progress.phase, progress.total, 10 * progress.done // max(progress.total, 1))
        if step != self._step:
            self._step = step
            _err(progress.text)

    def end(self) -> None:
        """End the line on a terminal."""
        if self._tty and self._width:
            sys.stderr.write("\n")
            sys.stderr.flush()
            self._width = 0


# -- the commands: each calls one workspace function ------------------------------------------------------------


def _model(ws: Workspace, args: argparse.Namespace) -> None:
    if args.action == "add":
        _out(str(ws.load_model(args.path)))
    else:
        _out(str(ws.test_model(args.name, approve=approver(args.yes))))


def _models(ws: Workspace, args: argparse.Namespace) -> None:
    if args.name is not None:
        _out(str(ws.describe_model(args.name)))
    else:
        _out_all(ws.list_models(), "No models loaded.")


def _diagnostics(ws: Workspace, args: argparse.Namespace) -> None:
    if args.name is not None:
        _out(str(ws.describe_diagnostic(args.name)))
    else:
        _out_all(ws.list_diagnostics(), "No diagnostics registered.")


def _request(args: argparse.Namespace) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    space = _json_file(args.space, "the space file") if args.space is not None else None
    keywords: dict[str, Any] = {"prediction": args.prediction, "retry_failed": args.retry_failed}
    return space, keywords | _params(args.param)


def _price(ws: Workspace, args: argparse.Namespace) -> None:
    space, keywords = _request(args)
    _out(str(ws.price(args.model, args.diagnostic, space, **keywords)))


def _run(ws: Workspace, args: argparse.Namespace) -> None:
    space, keywords = _request(args)
    line = args.progress
    try:
        result = ws.run(args.model, args.diagnostic, space, approve=approver(args.yes), on_progress=line, **keywords)
    finally:
        line.end()
    _out(str(result))


def _results(ws: Workspace, args: argparse.Namespace) -> None:
    filters = {"model": args.model, "model_version": args.model_version, "diagnostic": args.diagnostic,
               "prediction": args.prediction}  # fmt: skip
    if args.id is not None:
        if any(v is not None for v in filters.values()):
            raise UsageError("ema results: give an ID, or filters to list results, not both")
        _out(str(ws.get_result(args.id)))
    else:
        _out_all(ws.list_results(**filters), "No diagnostic results.")


def _report(ws: Workspace, args: argparse.Namespace) -> None:
    report = ws.report(args.id, pdf=args.pdf)
    sys.stdout.write(report.markdown)  # as the file holds it, byte for byte (U9's "byte-identical")
    sys.stdout.flush()
    _err(f"Report: {report.path}")
    if report.pdf is not None:
        _err(f"PDF: {report.pdf}")


def _failed_runs(ws: Workspace, args: argparse.Namespace) -> None:
    _out_all(ws.failed_runs(args.id), "No failed runs: every run is usable for the result's model prediction.")


def _run_dirs(ws: Workspace, args: argparse.Namespace) -> None:
    point = _point(args.point) if args.point is not None else None
    _out_all(ws.run_dirs(args.id, point=point), "No runs at that point.")


def _reproduce(ws: Workspace, args: argparse.Namespace) -> None:
    _out(str(ws.reproduce(args.id)))


def _export(ws: Workspace, args: argparse.Namespace) -> None:
    _out(ws.export(args.id, args.directory, pdf=args.pdf))


def _mcp(args: argparse.Namespace) -> int:
    """Start the MCP server, confined to ``--root`` (T5; 0057, 0061); exit 2 for a root refused at start.

    ``ema.mcp`` is imported here only (AR3; architecture.md §10's AST check), since it needs the ``ema[mcp]`` extra.
    """
    root = args.root
    if not os.path.isabs(root):
        raise UsageError(f"ema mcp: --root {root} is relative; name the directory by its absolute path (T5)")
    if os.path.realpath(root) == os.path.realpath(os.sep):
        raise UsageError("ema mcp: --root / would let a client name any path; name your project's directory (T5)")
    try:
        # Lazy (AR3, 0061); the ignore is for a branch or an install without ema.mcp.
        from ema.mcp.server import serve  # type: ignore[import-not-found,import-untyped,unused-ignore]
    except ImportError as error:
        _err(f"{EXTRA_MISSING} ({error})")
        return 2
    try:
        serve(root=os.path.normpath(root), workspace=args.workspace)
    except PathRefused as error:  # open_workspace(root=) refused the root, or the workspace under it (T5)
        _err(f"ema mcp: {error}")
        return 2
    return 0


COMMANDS: dict[str, Callable[[Workspace, argparse.Namespace], None]] = {
    "model": _model,
    "models": _models,
    "diagnostics": _diagnostics,
    "price": _price,
    "run": _run,
    "results": _results,
    "report": _report,
    "failed-runs": _failed_runs,
    "run-dirs": _run_dirs,
    "reproduce": _reproduce,
    "export": _export,
}


# -- the parser ------------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    """Build ``ema``'s argument parser: architecture.md §8's 13 commands and the global ``--workspace``."""
    workspace = _Parser(add_help=False)
    workspace.add_argument("--workspace", metavar="DIR", default=argparse.SUPPRESS,
                           help="the workspace's directory (default: ema_workspace)")  # fmt: skip
    top = _Parser(prog="ema", description="EMA: diagnostics that find exploitable structure in computational models.")
    top.add_argument("--workspace", metavar="DIR", default="ema_workspace",
                     help="the workspace's directory (default: ema_workspace)")  # fmt: skip
    commands = top.add_subparsers(dest="command", metavar="COMMAND", parser_class=_Parser)

    def command(name: str, help: str) -> argparse.ArgumentParser:
        return commands.add_parser(name, help=help, description=help, parents=[workspace])

    model = command("model", "add a model spec, or test a model at its nominal point")
    actions = model.add_subparsers(dest="action", metavar="ACTION", required=True, parser_class=_Parser)
    add = actions.add_parser("add", help="load a model spec (W1)", parents=[workspace])
    add.add_argument("path", metavar="PATH", help="the model spec's file, model.json")
    test = actions.add_parser("test", help="run the model once at its nominal point, after your yes",
                              parents=[workspace])  # fmt: skip
    test.add_argument("name", metavar="NAME")
    test.add_argument("--yes", action="store_true", help="approve in advance: still priced, shown, and recorded")

    command("models", "list the models, or describe one").add_argument("name", metavar="NAME", nargs="?")
    command("diagnostics", "list the diagnostics, or describe one").add_argument("name", metavar="NAME", nargs="?")

    for name, help in (("price", "price a diagnostic evaluation: run nothing, ask nothing"),
                       ("run", "run a diagnostic evaluation, after your yes to its new runs")):  # fmt: skip
        sub = command(name, help)
        sub.add_argument("model", metavar="MODEL")
        sub.add_argument("diagnostic", metavar="DIAGNOSTIC")
        sub.add_argument("--space", metavar="FILE", help="the model parameter space, designs.md's JSON form")
        sub.add_argument("--param", metavar="K=V", action="append",
                         help="a diagnostic parameter: a JSON value, or a bare string (repeatable)")  # fmt: skip
        sub.add_argument("--prediction", metavar="P", help="the model prediction (default: the only one)")
        sub.add_argument("--retry-failed", action="store_true", help="run the design's failed points again")
        if name == "run":
            sub.add_argument("--yes", action="store_true", help="approve in advance: still priced, shown, and recorded")

    results = command("results", "show a diagnostic result, or list them")
    results.add_argument("id", metavar="ID", nargs="?")
    results.add_argument("--model", metavar="M")
    results.add_argument("--model-version", metavar="V")
    results.add_argument("--diagnostic", metavar="D")
    results.add_argument("--prediction", metavar="P")

    report = command("report", "print a result's report (Markdown); its path on stderr")
    report.add_argument("id", metavar="ID")
    report.add_argument("--pdf", action="store_true", help="also make the PDF, through pandoc")
    command("failed-runs", "list the runs not usable for a result").add_argument("id", metavar="ID")
    run_dirs = command("run-dirs", "show a run's directories, or a result's runs at a point")
    run_dirs.add_argument("id", metavar="ID", help="a run's id; or, with --point, a result's")
    run_dirs.add_argument("--point", metavar="FILE", help="a JSON object of model parameter values")
    command("reproduce", "replay a result from its provenance and compare it").add_argument("id", metavar="ID")
    export = command("export", "export a result's runs, design, result, and report")
    export.add_argument("id", metavar="ID")
    export.add_argument("directory", metavar="DIR", help="a new or empty directory")
    export.add_argument("--pdf", action="store_true", help="also write the report as a PDF, report/report.pdf")

    mcp = command("mcp", "start the MCP server, confined to a root directory (needs ema[mcp])")
    mcp.add_argument("--root", metavar="DIR", required=True,
                     help="the one directory its paths may name: absolute, not /, outside any workspace")  # fmt: skip
    return top


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``ema`` with ``argv`` (default: the command line's) and return the exit code (architecture.md §8).

    Parameters
    ----------
    argv
        The arguments after ``ema``.

    Returns
    -------
    int
        0 success; 1 an ``EMAError``, a declined approval included, or an ``OSError``; 2 bad usage, or ``ema mcp``'s root refused at
        start; 130 Ctrl-C, with every finished run stored (C49).
    """
    top = parser()
    progress = ProgressLine()
    try:
        try:
            args = top.parse_args(argv)
        except SystemExit as done:  # --help
            return done.code if isinstance(done.code, int) else 0
        if args.command is None:
            top.print_usage(sys.stderr)
            _err("ema: name a command; ema --help lists them")
            return 2
        if args.command == "mcp":
            return _mcp(args)
        args.progress = progress
        with open_workspace(args.workspace) as ws:
            COMMANDS[args.command](ws, args)
        return 0
    except UsageError as error:
        _err(str(error))
        return 2
    except EMAError as error:
        _err(f"ema: {error}")
        return 1
    except OSError as error:  # a workspace that can't be made or read, say: its reason, not a traceback (m2)
        _err(f"ema: {error}")
        return 1
    except KeyboardInterrupt:
        progress.end()
        at = f" at {progress.last.text}" if progress.last is not None else ""
        _err(f"Stopped{at}: every finished run is stored.")
        return 130
