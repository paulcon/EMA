"""EMA's MCP server, 10 tools and three resources, each one workspace call (layer 5; architecture.md §8).

It offers what the workspace does to an MCP client, such as an AI agent (U9; records 0016, 0019, 0053, 0056, 0057, 0061, 0081). Every run and
save is asked of the user, by elicitation (trust.md, T4); path arguments are confined to the root, and resources looked
up by name (T5); the protocol stream carries nothing else (T9). Every tool returns the envelope, has a description for
every schema field, and marks an error ``retryable`` or not (contracts.md, C55).

Presentation only (AR3): it imports ``ema.workspace`` and ``ema.types``, the standard library, and the mcp SDK. Every
number it shows is EMA's: ``text`` is the text the workspace rendered, and ``data`` the returned type as strict JSON
(P1). The workspace is synchronous and the SDK asynchronous, so the server keeps two ``Workspace`` objects on the
same directory, each on a dedicated one-worker thread: one for the tools that may run or write, one for the rest and
the resources, so reads and prices answer while a run goes on (data_model.md §10). A question blocks its worker
thread while it is asked on the event loop; so does each progress notification.
"""

import asyncio
import base64
import concurrent.futures
import dataclasses
import json
import logging
import math
import os
import re
import signal
import threading
import time
import urllib.parse
from collections.abc import Callable, Mapping
from datetime import datetime
from enum import Enum
from importlib import metadata, resources
from typing import Any

import anyio
from mcp import types
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.runner import serve_loop
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError
from mcp.shared.message import SessionMessage

from ema.types.errors import CannotAsk, EMAError, NotFound, PathRefused, RequestError, Stopped
from ema.types.model import ModelSpec
from ema.types.requests import ApprovalRequest, Approver, ConfirmationRequest, Progress
from ema.types.results import DiagnosticResult
from ema.types.summaries import DiagnosticSummary
from ema.types.text import timestamp_text
from ema.workspace import Workspace, open_workspace

__all__ = ["ELICITATION_TIMEOUT_S", "PROGRESS_INTERVAL_S", "TOOLS", "EmaServer", "Stopped", "serve"]

#: Seconds an approval or a confirmation waits for its answer; unanswered, it is a no, and the run lock is freed (§8).
ELICITATION_TIMEOUT_S = 900
#: The least seconds between two progress notifications of one call; the first and the last of a phase always go.
PROGRESS_INTERVAL_S = 0.2
#: MCP's error code for a resource that isn't there.
RESOURCE_NOT_FOUND = -32002

logger = logging.getLogger(__name__)

_STRING = {"type": "string"}
_OBJECT = {"type": "object"}
_SPEC = {"type": ["object", "string"]}
_REQUEST = {
    "model": (_STRING, True),
    "diagnostic": (_STRING, True),
    "space": (_OBJECT, False),
    "params": (_OBJECT, False),
    "prediction": (_STRING, False),
    "retry_failed": ({"type": "boolean"}, False),
}
#: Each tool's arguments: name to (JSON schema, required). Their descriptions are tools.md's (0019).
TOOLS: Mapping[str, Mapping[str, tuple[Mapping[str, Any], bool]]] = {
    "models": {"name": (_STRING, False)},
    "diagnostics": {"name": (_STRING, False)},
    "propose_model": {"spec": (_SPEC, True), "path": (_STRING, True)},
    "save_model": {"spec": (_SPEC, True), "path": (_STRING, True)},
    "test_model": {"name": (_STRING, True)},
    "price": _REQUEST,
    "run_diagnostic": _REQUEST,
    "results": {k: (_STRING, False) for k in ("id", "model", "model_version", "diagnostic", "prediction")},
    "failed_runs": {"id": (_STRING, True)},
    "export": {"id": (_STRING, True), "directory": (_STRING, True), "pdf": ({"type": "boolean"}, False)},
}
#: The tools that may run a model or write a file: they share the writing workspace's thread (§8).
_WRITES = frozenset({"save_model", "test_model", "run_diagnostic", "export"})
_JSON_TYPES: Mapping[str, type | tuple[type, ...]] = {"string": str, "object": dict, "boolean": bool}

#: The envelope every tool returns (C55; 0017): ``see`` names resources and tools, never advice.
ENVELOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "description": "Whether the call succeeded."},
        "data": {"description": "The returned type as strict JSON, with full and short ids; null on an error."},
        "text": {"type": ["string", "null"], "description": "EMA's rendering of the result: quote it."},
        "see": {"type": "array", "items": {"type": "string"}, "description": "Resources and tools holding more."},
        "error": {
            "type": ["object", "null"],
            "properties": {"message": {"type": "string"}, "retryable": {"type": "boolean"}},
            "description": "Why the call failed, and whether trying again can help; null on success.",
        },
    },
    "required": ["ok", "data", "text", "see", "error"],
}
#: An elicitation's form: one boolean, checked by default, so Accept on the form showing the price is a yes; decline,
#: cancel, ``approve`` false, or anything else is a no (P3; 0016; record 0081 item 6, amended in Review round 1).
_YES_SCHEMA = {
    "type": "object",
    "properties": {
        "approve": {
            "type": "boolean",
            "title": "Approve",
            "description": "Yes: go ahead. No: nothing.",
            "default": True,
        }
    },
    "required": ["approve"],
}
#: ``run``'s and ``price``'s own arguments, which ``params`` can't name (each is a tool argument, or none at all).
_NOT_PARAMS = {
    "model": "the tool's own `model` argument",
    "diagnostic": "the tool's own `diagnostic` argument",
    "space": "the tool's own `space` argument",
    "prediction": "the tool's own `prediction` argument",
    "retry_failed": "the tool's own `retry_failed` argument",
    "approve": "no argument: the user approves through EMA's question",
    "on_progress": "no argument: progress comes as notifications",
    "self": "no argument",
}
_STOPPED = "stopped: the client cancelled the call or left, or the server is stopping; every finished run is stored"
_ID = r"([0-9a-fA-F]{4,64})"
_REPORT_URI = re.compile(rf"ema://results/{_ID}/report")
_FIGURE_URI = re.compile(rf"ema://results/{_ID}/figures/([^/]+)\.(png|json)")
_DIAGNOSTIC_URI = re.compile(r"ema://diagnostics/([^/]+)")


def _read_tools_md() -> tuple[str, dict[str, tuple[str, dict[str, str]]]]:
    """Read tools.md (0019): the server's instructions, and each tool's description and arguments' descriptions."""
    text = resources.files("ema.mcp").joinpath("tools.md").read_text(encoding="utf-8")
    instructions, _, tools_text = text.partition("\n## Instructions\n")[2].partition("\n## Tools\n")
    described: dict[str, tuple[str, dict[str, str]]] = {}
    for block in re.split(r"^### ", tools_text, flags=re.MULTILINE)[1:]:
        name, _, body = block.partition("\n")
        arguments = dict(re.findall(r"^- `(\w+)`: (.+)$", body, flags=re.MULTILINE))
        prose = body.split("\n- `", 1)[0]
        described[name.strip()] = (" ".join(prose.split()), arguments)
    return instructions.strip(), described


def tool_list() -> list[types.Tool]:
    """Return the 10 tools, each with tools.md's description and a description for every schema field (C55).

    Raises
    ------
    RuntimeError
        For a tool or an argument tools.md doesn't describe, or describes but the server doesn't serve (0019).
    """
    _, described = _read_tools_md()
    if set(described) != set(TOOLS):
        raise RuntimeError(f"tools.md describes {sorted(described)}, the server serves {sorted(TOOLS)}")
    tools = []
    for name, arguments in TOOLS.items():
        description, argument_text = described[name]
        if set(argument_text) != set(arguments):
            raise RuntimeError(
                f"tools.md describes {name}'s arguments {sorted(argument_text)}, not {sorted(arguments)}"
            )
        schema = {
            "type": "object",
            "properties": {arg: {**s, "description": argument_text[arg]} for arg, (s, _) in arguments.items()},
            "required": [arg for arg, (_, required) in arguments.items() if required],
            "additionalProperties": False,
        }
        read_only = name not in _WRITES
        annotations = types.ToolAnnotations(read_only_hint=read_only, destructive_hint=False, open_world_hint=False)
        tools.append(types.Tool(name=name, description=description, input_schema=schema,
                                output_schema=ENVELOPE_SCHEMA, annotations=annotations))  # fmt: skip
    return tools


# -- the envelope and strict JSON (C55; P1) --------------------------------------------------------------------


def _plain(x: Any) -> Any:
    """Return a value EMA returned as strict JSON data, leaving each number as it is (P1); ``text`` is the envelope's."""
    if x is None or isinstance(x, (bool, int, str)):
        return x
    if isinstance(x, float):  # EMA's types hold finite numbers only, so a non-finite one is a bug (0081, n6)
        if not math.isfinite(x):
            raise ValueError(f"a non-finite number, {x!r}, where EMA's types hold finite ones")
        return x
    if isinstance(x, Enum):
        return x.value
    if isinstance(x, datetime):
        return timestamp_text(x)
    if isinstance(x, ModelSpec):
        return json.loads(x.to_json())
    if isinstance(x, DiagnosticResult):
        return _result_data(x)
    if isinstance(x, Mapping):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        data = {f.name: _plain(getattr(x, f.name)) for f in dataclasses.fields(x) if f.name != "text"}
        if isinstance(x, DiagnosticSummary):  # the object ``params`` must meet (C55)
            properties = {p.name: _plain(p.json_schema) for p in x.parameters}
            data["params_schema"] = {"type": "object", "properties": properties, "additionalProperties": False}
        return data
    raise TypeError(f"no JSON form for {type(x).__name__}")


def _result_data(result: DiagnosticResult) -> dict[str, Any]:
    """Return a result as its JSON, without the run ids (an export holds them), with its short id (§8)."""
    data = json.loads(result.to_json())
    data["provenance"].pop("run_ids", None)
    if result.shown is not None:
        data["short_id"] = result.shown.short_id
        data["model_version"] = result.shown.model_version
    return data


def _envelope(data: Any = None, text: str | None = None, see: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "text": text, "see": see or [], "error": None}


def _failure(message: str, retryable: bool) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "text": message,
        "see": [],
        "error": {"message": message, "retryable": retryable},
    }


def _tool_result(envelope: Mapping[str, Any]) -> types.CallToolResult:
    """Return the envelope as structured content, and as its JSON text for clients that read only text."""
    text = json.dumps(envelope, ensure_ascii=False, allow_nan=False)
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)],
                                structured_content=dict(envelope), is_error=not envelope["ok"])  # fmt: skip


def _report_uri(result_id: str) -> str:
    return f"ema://results/{result_id}/report"


def _figure_uri(result_id: str, name: str, kind: str) -> str:
    return f"ema://results/{result_id}/figures/{urllib.parse.quote(name, safe='')}.{kind}"


def _see(result: DiagnosticResult) -> list[str]:
    """Name the resources holding a result's report and figures, and the tool holding its failed runs (§8)."""
    rid = result.result_id
    see = [_report_uri(rid)]
    for figure in result.figures:
        see += [_figure_uri(rid, figure.name, "png"), _figure_uri(rid, figure.name, "json")]
    if result.counts.usable < result.counts.rows:
        see.append(f'failed_runs(id="{rid}")')
    return see


def _arguments(tool: str, given: Mapping[str, Any]) -> dict[str, Any]:
    """Check a call's arguments against the tool's schema: names, required ones, and JSON types (RequestError)."""
    expected = TOOLS[tool]
    unknown = sorted(set(given) - set(expected))
    if unknown:
        raise RequestError(f"{tool} takes no argument {unknown[0]!r}; its arguments are {', '.join(expected)}")
    out = {}
    for name, (schema, required) in expected.items():
        value = given.get(name)
        if value is None:
            if required:
                raise RequestError(f"{tool} needs the argument {name}")
            continue
        kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if kinds == ["object"] and isinstance(value, str):  # an object sent as its JSON text (0081 item 16)
            try:
                value = json.loads(value)
            except ValueError:
                pass
        if not any(isinstance(value, _JSON_TYPES[k]) for k in kinds):
            raise RequestError(f"{tool}'s argument {name} is a JSON {' or '.join(kinds)}, not {value!r}")
        out[name] = value
    return out


# -- one call: its questions and progress, from the worker thread to the event loop ----------------------------


def _answered(item: Any) -> Any:
    """Turn a client's reply that the SDK can't read (its result not an object) into an error reply for its id.

    The SDK drops such a line, leaving the question waiting ``ELICITATION_TIMEOUT_S``; as an error, the question is
    a no at once (record 0081, Review round 1, m3). Anything else passes through.
    """
    errors = getattr(item, "errors", None)
    if not isinstance(item, Exception) or not callable(errors):
        return item
    try:
        raws = [e.get("input") for e in errors()]
    except Exception:  # noqa: BLE001  (not pydantic's error: leave it to the SDK)
        return item
    for raw in raws:
        if isinstance(raw, dict) and "method" not in raw and "error" not in raw:
            rid = raw.get("id")
            if isinstance(rid, (int, str)) and not isinstance(rid, bool):
                error = types.ErrorData(code=types.INVALID_REQUEST, message="the reply's result isn't a JSON object")
                return SessionMessage(types.JSONRPCError(jsonrpc="2.0", id=rid, error=error))
    return item


class _Call:
    """One tool call's link to the event loop: questions by elicitation, progress by notification (§8)."""

    def __init__(self, ctx: ServerRequestContext[Any], loop: asyncio.AbstractEventLoop, can_ask: bool) -> None:
        self.ctx, self.loop, self.can_ask = ctx, loop, can_ask
        self.cancelled = threading.Event()
        self._waiting: concurrent.futures.Future[Any] | None = None
        self._last = (0.0, -1.0, 0.0, "")  # (time, value, offset, phase)

    def cancel(self) -> None:
        """Stop the call at its next question or progress; a question being asked is answered no."""
        self.cancelled.set()
        waiting = self._waiting
        if waiting is not None:
            waiting.cancel()

    def _on_loop(self, coroutine: Any, timeout: float) -> Any:
        if self.cancelled.is_set():
            coroutine.close()
            raise Stopped(_STOPPED)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        self._waiting = future
        try:
            if self.cancelled.is_set():  # checked again once ``_waiting`` is set, so a cancel between isn't lost (n1)
                future.cancel()
                raise Stopped(_STOPPED)
            return future.result(timeout=timeout)
        except concurrent.futures.CancelledError:
            raise Stopped(_STOPPED) from None
        finally:
            self._waiting = None

    @property
    def approver(self) -> Approver | None:
        """The approver: an elicitation; None for a client without elicitation (refused before any question; §8)."""
        return self._ask if self.can_ask else None

    def _ask(self, question: ApprovalRequest | ConfirmationRequest) -> bool:
        try:
            return self._on_loop(self._elicit(question.text), ELICITATION_TIMEOUT_S + 30) is True
        except Stopped:
            return False  # a cancelled call's question is a no, recorded as asked (W3)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"no answer within ELICITATION_TIMEOUT_S, {ELICITATION_TIMEOUT_S} s") from None

    async def _elicit(self, message: str) -> bool:
        try:
            async with asyncio.timeout(ELICITATION_TIMEOUT_S):
                answer = await self.ctx.session.elicit_form(
                    message=message, requested_schema=_YES_SCHEMA, related_request_id=self.ctx.request_id
                )
        except TimeoutError:
            raise TimeoutError(f"no answer within ELICITATION_TIMEOUT_S, {ELICITATION_TIMEOUT_S} s") from None
        return answer.action == "accept" and (answer.content or {}).get("approve", True) is True  # the default

    def progress(self, progress: Progress) -> None:
        """Send a progress notification, its message EMA's text; raising here stops the evaluation (0080)."""
        if self.cancelled.is_set():
            raise Stopped("stopped: the client cancelled the call or left; every finished run is stored")
        now = time.monotonic()
        when, last, offset, phase = self._last
        if phase and phase != progress.phase:
            offset = last
        value = offset + progress.done
        ends = progress.done in (0, progress.total)
        if value <= last or (not ends and now - when < PROGRESS_INTERVAL_S):
            return
        self._last = (now, value, offset, progress.phase)
        try:
            self._on_loop(self.ctx.session.report_progress(value, offset + progress.total, progress.text), 10)
        except Stopped:
            raise
        except Exception:
            logger.debug("progress notification not sent", exc_info=True)


# -- the server ----------------------------------------------------------------------------------------------


class EmaServer:
    """The MCP server over one workspace: two ``Workspace`` objects, each on its own thread (§8).

    Parameters
    ----------
    root
        The one directory path arguments may name: absolute, not ``/``, not inside a workspace (T5; 0057, 0061).
    workspace
        The workspace's directory; a relative one resolves against the root (trust.md, The MCP server's root).

    Raises
    ------
    PathRefused
        For a root that is relative or ``/``, or that ``open_workspace`` refuses: before anything is served.
    """

    def __init__(self, *, root: str, workspace: str = "ema_workspace") -> None:
        if not os.path.isabs(root):
            raise PathRefused(f"the root {root} is relative; name an absolute directory (--root)")
        if os.path.dirname(os.path.realpath(root)) == os.path.realpath(root):
            raise PathRefused(f"the root {root} is the file system's root; name a project directory (--root)")
        self.instructions, _ = _read_tools_md()
        self.tools = tool_list()
        self._writer = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="ema-mcp-write")
        self._reader = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="ema-mcp-read")
        self._calls: set[_Call] = set()
        self._stopping = False
        self._closing = threading.Lock()
        try:
            self._write_ws = self._writer.submit(open_workspace, workspace, root=root).result()
            self._read_ws = self._reader.submit(open_workspace, workspace, root=root).result()
        except BaseException:
            self.close()
            raise
        self.server: Server[Any] = Server(
            "ema", version=metadata.version("ema"), instructions=self.instructions,
            on_list_tools=self._list_tools, on_call_tool=self._call_tool, on_list_resources=self._list_resources,
            on_list_resource_templates=self._list_templates, on_read_resource=self._read_resource,
        )  # fmt: skip

    def stop(self) -> None:
        """Stop serving: each open call stops between two runs, its question answered no; a new call is refused."""
        self._stopping = True
        self._cancel_calls()

    def _cancel_calls(self) -> None:
        for call in list(self._calls):
            call.cancel()

    def close(self) -> None:
        """Stop, then close both workspaces on their threads once their calls end; then the threads.

        Closing releases the run lock and stops the model children (0026). Safe from any thread, and again.
        """
        self.stop()
        with self._closing:
            for pool, name in ((self._writer, "_write_ws"), (self._reader, "_read_ws")):
                ws = getattr(self, name, None)
                if ws is not None:
                    pool.submit(ws.close).result()
                    setattr(self, name, None)
                pool.shutdown(wait=True)

    def terminate(self, signum: int, frame: Any = None) -> None:
        """SIGTERM's handler (``serve``): stop as at a disconnect, close, then end the process by the signal.

        Each open call stops between two runs (the model call under way finishes and is stored), a question waiting
        is answered no, the run lock is released, and the model children are stopped; a second SIGTERM ends the
        process at once (record 0081, Review round 1, m1).
        """
        signal.signal(signum, signal.SIG_DFL)
        self.stop()

        def close_then_end() -> None:
            try:
                self.close()
            finally:
                os.kill(os.getpid(), signum)

        threading.Thread(target=close_then_end, name="ema-mcp-terminate", daemon=True).start()

    async def run(self, read_stream: Any, write_stream: Any) -> None:
        """Serve one client over a stream pair until it leaves: the handshake era only (0081 item 2).

        A reply the SDK can't read becomes an error for its id, a no at once (``_answered``). When the client
        leaves, every open call stops between two runs, and one queued never starts.
        """
        relay_send, relay_read = anyio.create_memory_object_stream[Any](0)

        async def relay() -> None:
            async with relay_send, read_stream:
                async for item in read_stream:
                    await relay_send.send(_answered(item))

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(relay)
                async with self.server.lifespan(self.server) as state:
                    await serve_loop(self.server, relay_read, write_stream, lifespan_state=state,
                                     init_options=self.server.create_initialization_options())  # fmt: skip
                tg.cancel_scope.cancel()
        finally:
            self._cancel_calls()

    async def run_stdio(self) -> None:
        """Serve over stdin and stdout; the SDK points fd 1 at stderr meanwhile, so nothing else reaches it (T9)."""
        async with stdio_server() as (read_stream, write_stream):
            await self.run(read_stream, write_stream)

    async def _on(self, pool: concurrent.futures.ThreadPoolExecutor, fn: Callable[..., Any], *args: Any) -> Any:
        return await asyncio.wrap_future(pool.submit(fn, *args))

    # -- tools ---------------------------------------------------------------------------------------------------

    async def _list_tools(self, ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=self.tools)

    async def _call_tool(self, ctx: ServerRequestContext[Any], params: types.CallToolRequestParams) -> Any:
        name = params.name
        if name not in TOOLS:
            return _tool_result(_failure(f"no tool {name!r}; the tools are {', '.join(TOOLS)}", False))
        if self._stopping:
            return _tool_result(_failure(_STOPPED, False))
        capabilities = ctx.session.client_capabilities
        can_ask = capabilities is not None and capabilities.elicitation is not None and ctx.session.can_send_request
        call = _Call(ctx, asyncio.get_running_loop(), can_ask)
        writes = name in _WRITES
        pool, ws = (self._writer, self._write_ws) if writes else (self._reader, self._read_ws)
        self._calls.add(call)
        try:
            envelope = await self._on(pool, self._dispatch, ws, name, dict(params.arguments or {}), call)
        except BaseException:
            call.cancel()
            raise
        finally:
            self._calls.discard(call)
        return _tool_result(envelope)

    def _dispatch(self, ws: Workspace, name: str, arguments: dict[str, Any], call: _Call) -> dict[str, Any]:
        """Run one tool on its thread, and return its envelope; an error becomes the envelope's (C55).

        A call cancelled while queued never calls the workspace, so nothing is asked or recorded (T3; n2).
        """
        if call.cancelled.is_set():
            return _failure(_STOPPED, False)
        try:
            data, text, see = getattr(self, f"_tool_{name}")(ws, _arguments(name, arguments), call)
            return _envelope(data, text, see)
        except CannotAsk as error:
            return _failure(f"this client can't ask the user (it has no elicitation): {error}", error.retryable)
        except EMAError as error:
            return _failure(str(error), error.retryable)
        except Exception as error:
            logger.exception("tool %s failed", name)
            return _failure(f"EMA failed unexpectedly: {type(error).__name__}: {error}", False)

    def _tool_models(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        if "name" in a:
            described = ws.describe_model(a["name"])
            return _plain(described), described.text, []
        models = ws.list_models()
        return _plain(models), "\n".join(m.text for m in models) or "No model is loaded.", []

    def _tool_diagnostics(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        if "name" in a:
            described = ws.describe_diagnostic(a["name"])
            return _plain(described), described.text, [f"ema://diagnostics/{described.name}"]
        listed = ws.list_diagnostics()
        return _plain(listed), "\n\n".join(d.text for d in listed), [f"ema://diagnostics/{d.name}" for d in listed]

    def _tool_propose_model(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        proposal = ws.propose_model(a["spec"], a["path"])
        return _plain(proposal), proposal.text, []

    def _tool_save_model(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        loaded = ws.save_model(a["spec"], a["path"], confirm=call.approver)
        return _plain(loaded), loaded.text, []

    def _tool_test_model(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        run = ws.test_model(a["name"], approve=call.approver)
        return _plain(run), run.text, []

    @staticmethod
    def _request(a: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
        keywords = {"prediction": a.get("prediction"), "retry_failed": bool(a.get("retry_failed", False))}
        params = a.get("params") or {}
        clash = sorted(set(params) & set(_NOT_PARAMS))
        if clash:  # never the workspace's TypeError (0081, Review round 1, m2)
            raise RequestError(f"{clash[0]} isn't a diagnostic parameter: it goes in {_NOT_PARAMS[clash[0]]}, "
                               "not in params")  # fmt: skip
        return (a["model"], a["diagnostic"], a.get("space")), {**keywords, **params}

    def _tool_price(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        args, keywords = self._request(a)
        price = ws.price(*args, **keywords)
        return _plain(price), price.text, []

    def _tool_run_diagnostic(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        args, keywords = self._request(a)
        result = ws.run(*args, approve=call.approver, on_progress=call.progress, **keywords)
        return _plain(result), result.shown.text if result.shown else result.result_id, _see(result)

    def _tool_results(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        if "id" in a:
            if len(a) > 1:  # as ``ema results ID`` refuses filters (0082 item 8; n5)
                raise RequestError("results: give an id, or filters to list results, not both")
            result = ws.get_result(a["id"])
            return _plain(result), result.shown.text if result.shown else result.result_id, _see(result)
        listed = ws.list_results(**a)
        text = "\n".join(s.text for s in listed) or "No diagnostic result is stored."
        return _plain(listed), text, [_report_uri(s.result_id) for s in listed]

    def _tool_failed_runs(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        runs = ws.failed_runs(a["id"])
        text = "\n\n".join(r.text for r in runs) or "Every run of the result is usable for its model prediction."
        return _plain(runs), text, [_report_uri(ws.get_result(a["id"]).result_id)]

    def _tool_export(self, ws: Workspace, a: dict[str, Any], call: _Call) -> tuple[Any, str, list[str]]:
        pdf = bool(a.get("pdf", False))
        directory = ws.export(a["id"], a["directory"], pdf=pdf)
        files = "runs.csv, result.json, report/ (with report.pdf)" if pdf else "runs.csv, result.json, report/"
        return {"directory": directory, "pdf": pdf}, f"Exported to {directory}: {files}", []

    # -- resources: looked up by name, never joined into a path from an argument (T5) ----------------------------

    async def _list_resources(self, ctx: Any, params: Any) -> types.ListResourcesResult:
        return types.ListResourcesResult(resources=await self._on(self._reader, self._resources))

    def _resources(self) -> list[types.Resource]:
        ws = self._read_ws
        listed = [types.Resource(uri=f"ema://diagnostics/{d.name}", name=f"diagnostic {d.name}",
                                 description=d.summary, mime_type="application/json")
                  for d in ws.list_diagnostics()]  # fmt: skip
        for summary in ws.list_results():
            rid = summary.result_id
            listed.append(types.Resource(uri=_report_uri(rid), name=f"report {summary.short_id}",
                                         description=summary.text, mime_type="text/markdown"))  # fmt: skip
            for figure in ws.get_result(rid).figures:
                for kind, mime in (("png", "image/png"), ("json", "application/json")):
                    listed.append(types.Resource(uri=_figure_uri(rid, figure.name, kind), mime_type=mime,
                                                 name=f"{summary.short_id} {figure.name}.{kind}",
                                                 description=figure.caption))  # fmt: skip
        return listed

    async def _list_templates(self, ctx: Any, params: Any) -> types.ListResourceTemplatesResult:
        templates = [
            types.ResourceTemplate(uri_template="ema://results/{id}/report", name="report",
                                   description="A diagnostic result's report, byte for byte.",  # (U9)
                                   mime_type="text/markdown"),
            types.ResourceTemplate(uri_template="ema://results/{id}/figures/{name}.png", name="figure",
                                   description="One of a result's figures.", mime_type="image/png"),
            types.ResourceTemplate(uri_template="ema://results/{id}/figures/{name}.json", name="data card",
                                   description="A figure's data card: the numbers it draws.",
                                   mime_type="application/json"),
            types.ResourceTemplate(uri_template="ema://diagnostics/{name}", name="diagnostic",
                                   description="A diagnostic and its parameters' JSON schemas.",  # (C55)
                                   mime_type="application/json"),
        ]  # fmt: skip
        return types.ListResourceTemplatesResult(resource_templates=templates)

    async def _read_resource(self, ctx: Any, params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
        uri = str(params.uri)
        return types.ReadResourceResult(contents=[await self._on(self._reader, self._resource, uri)])

    def _resource(self, uri: str) -> types.TextResourceContents | types.BlobResourceContents:
        ws = self._read_ws
        try:
            if m := _REPORT_URI.fullmatch(uri):
                return types.TextResourceContents(uri=uri, text=ws.report(m[1]).markdown, mime_type="text/markdown")
            if m := _FIGURE_URI.fullmatch(uri):
                result = ws.get_result(m[1])
                name = urllib.parse.unquote(m[2])
                figure = next((f for f in result.figures if f.name == name), None)
                file = None if figure is None else figure.png if m[3] == "png" else figure.card
                if file is None or os.path.basename(file) != file:
                    raise NotFound(f"result {m[1]} has no figure {name!r}")
                with open(os.path.join(os.path.dirname(ws.report(result).path), file), "rb") as f:
                    content = f.read()
                if m[3] == "png":
                    return types.BlobResourceContents(uri=uri, blob=base64.b64encode(content).decode("ascii"),
                                                      mime_type="image/png")  # fmt: skip
                return types.TextResourceContents(uri=uri, text=content.decode("utf-8"), mime_type="application/json")
            if m := _DIAGNOSTIC_URI.fullmatch(uri):
                described = ws.describe_diagnostic(urllib.parse.unquote(m[1]))
                text = json.dumps(_envelope(_plain(described), described.text), ensure_ascii=False)
                return types.TextResourceContents(uri=uri, text=text, mime_type="application/json")
        except EMAError as error:
            raise MCPError(RESOURCE_NOT_FOUND, str(error), {"uri": uri}) from None
        raise MCPError(RESOURCE_NOT_FOUND, f"no resource {uri}", {"uri": uri})


def serve(*, root: str, workspace: str = "ema_workspace") -> None:
    """Run the stdio MCP server until the client disconnects (architecture.md §8; ``ema mcp``).

    On a disconnect, Ctrl-C, or SIGTERM, each open call stops between two runs, every finished run stored; then the
    workspaces close, releasing the run lock and stopping the model children. A SIGTERM then ends the process by
    the signal (``EmaServer.terminate``).

    Parameters
    ----------
    root
        The one directory the tools' path arguments may name: absolute (T5, E7; 0057).
    workspace
        The workspace's directory; a relative one, and the default, resolve against the root.

    Raises
    ------
    PathRefused
        For a root refused, before anything is served (``ema mcp`` exits 2; 0061).
    """
    server = EmaServer(root=root, workspace=workspace)
    main = threading.current_thread() is threading.main_thread()
    previous = signal.signal(signal.SIGTERM, server.terminate) if main else None
    try:
        anyio.run(server.run_stdio)
    finally:
        server.close()
        if previous is not None and signal.getsignal(signal.SIGTERM) == server.terminate:
            signal.signal(signal.SIGTERM, previous)
