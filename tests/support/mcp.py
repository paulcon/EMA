"""Helpers for the MCP server's tests (step 15): a scripted client over the SDK's in-memory streams, an elicitation
that records each question and answers as told, and a stdio peer that speaks JSON-RPC by hand to a real ``python -m
ema.mcp`` subprocess, checking that every line it writes to stdout is a protocol message (T9). No LLM: no API cost.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from mcp import Client, types
from mcp.shared.memory import create_client_server_memory_streams

from ema.mcp.server import EmaServer

ENVELOPE_KEYS = {"ok", "data", "text", "see", "error"}


@dataclass
class Elicited:
    """An elicitation callback: records each question's message and answers ``action`` (with ``approve``)."""

    action: str = "accept"
    approve: bool = True
    content: dict[str, Any] | None = None  # with accept, sent as is in place of {"approve": approve}
    messages: list[str] = field(default_factory=list)

    async def __call__(self, context: Any, params: types.ElicitRequestParams) -> types.ElicitResult:
        self.messages.append(params.message)
        given = {"approve": self.approve} if self.content is None else self.content
        content = given if self.action == "accept" else None
        return types.ElicitResult(action=self.action, content=content)  # type: ignore[arg-type]


@asynccontextmanager
async def _memory(server: EmaServer) -> AsyncIterator[Any]:
    async with (
        create_client_server_memory_streams() as (client_streams, server_streams),
        anyio.create_task_group() as tg,
    ):
        tg.start_soon(server.run, *server_streams)
        yield client_streams
        tg.cancel_scope.cancel()


def scripted(server: EmaServer, script: Callable[[Client], Any], *, elicit: Elicited | None = None,
             mode: str = "legacy") -> Any:  # fmt: skip
    """Connect a client to the server in process and run ``script(client)`` (an async function); return its value.

    ``elicit=None`` makes a client without elicitation (it declares no such capability).
    """

    async def main() -> Any:
        async with Client(_memory(server), mode=mode, elicitation_callback=elicit) as client:
            return await script(client)

    return anyio.run(main)


def envelope(result: types.CallToolResult) -> dict[str, Any]:
    """Return a tool result's envelope, checking that its text block is the same JSON as its structured content."""
    data = result.structured_content
    assert isinstance(data, dict) and set(data) == ENVELOPE_KEYS, data
    assert len(result.content) == 1 and json.loads(result.content[0].text) == data  # type: ignore[union-attr]
    assert result.is_error == (not data["ok"])
    return data


class StdioPeer:
    """A real ``python -m ema.mcp`` subprocess, spoken to line by line: every stdout line must be JSON-RPC (T9).

    Server requests (``elicitation/create``) are answered, in order, from ``replies`` (each a raw reply body,
    ``{"result": ...}`` or ``{"error": ...}``), then with ``answer``; with ``hold``, they are kept in ``held``,
    unanswered. Notifications are kept in ``notes``; responses to the calls ``start`` sends, in ``responses``.
    """

    def __init__(self, root: Path, *, answer: bool = True, capabilities: dict[str, Any] | None = None,
                 replies: list[dict[str, Any]] | None = None, hold: bool = False) -> None:  # fmt: skip
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        self.stderr = open(root.parent / "server_stderr.txt", "w+")  # noqa: SIM115
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "ema.mcp", "--root", str(root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, env=env,
        )  # fmt: skip
        self.answer, self.next_id = answer, 0
        self.replies = list(replies or [])
        self.hold = hold
        self.held: list[dict[str, Any]] = []
        self.lines: list[dict[str, Any]] = []
        self.notes: list[dict[str, Any]] = []
        self.elicited: list[str] = []
        self.forms: list[dict[str, Any]] = []
        self.responses: dict[int, dict[str, Any]] = {}
        self.capabilities = {"elicitation": {}} if capabilities is None else capabilities

    def send(self, message: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        self.proc.stdin.flush()

    _send = send

    def _read(self, timeout: float) -> dict[str, Any]:
        assert self.proc.stdout is not None
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        assert ready, "the server wrote nothing in time"
        line = self.proc.stdout.readline()
        assert line, "the server closed stdout"
        message = json.loads(line)  # a stray print would fail here (T9)
        assert message.get("jsonrpc") == "2.0", line
        self.lines.append(message)
        return message

    def _handle(self, message: dict[str, Any]) -> None:
        if "method" in message and "id" in message:  # the server asks
            assert message["method"] == "elicitation/create", message
            self.elicited.append(message["params"]["message"])
            self.forms.append(message["params"])
            if self.hold:
                self.held.append(message)
                return
            if self.replies:
                reply = self.replies.pop(0)
            else:
                reply = {"result": {"action": "accept", "content": {"approve": True}} if self.answer
                         else {"action": "decline"}}  # fmt: skip
            self.send({"jsonrpc": "2.0", "id": message["id"], **reply})
        elif "method" in message:
            self.notes.append(message)
        else:
            self.responses[message["id"]] = message

    def pump(self, until: Callable[[], Any], timeout: float = 120) -> None:
        """Read and handle messages until ``until()`` is true."""
        deadline = time.monotonic() + timeout
        while not until():
            self._handle(self._read(max(deadline - time.monotonic(), 0.1)))

    def start(self, method: str, params: dict[str, Any] | None = None) -> int:
        """Send a request and return its id, without waiting for its response."""
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": self.next_id, "method": method, **({"params": params} if params else {})})
        return self.next_id

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 120) -> dict[str, Any]:
        """Send a request; answer the server's own requests meanwhile; return the response's result."""
        mine = self.start(method, params)
        self.pump(lambda: mine in self.responses, timeout)
        message = self.responses[mine]
        assert "error" not in message, message
        return message["result"]

    def initialize(self) -> dict[str, Any]:
        result = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": self.capabilities,
                                             "clientInfo": {"name": "scripted", "version": "0"}})  # fmt: skip
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    @staticmethod
    def tool_params(tool: str, arguments: dict[str, Any], progress: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"name": tool, "arguments": arguments}
        if progress is not None:
            params["_meta"] = {"progressToken": progress}
        return params

    def call(self, tool: str, arguments: dict[str, Any], *, progress: str | None = None) -> dict[str, Any]:
        return self.request("tools/call", self.tool_params(tool, arguments, progress))["structuredContent"]

    def close(self) -> int:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.close()
        rest = self.proc.stdout.read()
        code = self.proc.wait(timeout=60)
        for line in rest.splitlines():  # anything after the last response must be protocol too
            assert json.loads(line).get("jsonrpc") == "2.0", line
        self.stderr.close()
        return code
