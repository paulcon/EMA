"""The MCP tools' contract (contracts.md C55; C53's U9; architecture.md §8, §9): every tool returns the envelope, has
a description for every schema field, marks its errors ``retryable`` or not, and every number in a tool result
equals the stored value it names (P1, record 0019). ``check_tool`` is parametrized over the 10 tools; its negative
control is a tool that rounds a number itself. ``check_use_case_u9`` runs U9 as written on R2 (slow tier).
"""

import json
import math
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

import ema.reference_models
from ema.mcp.server import TOOLS, EmaServer
from ema.store import Store
from ema.workspace import Workspace, open_workspace
from tests.support.mcp import Elicited, envelope, scripted
from tests.support.workspace import PI_SPACE, Asked, copy_reference

PI = {k: list(v) for k, v in PI_SPACE.items()}
R2_SPEC = json.loads(Path(ema.reference_models.path("R2")).read_text())


def numbers(data: Any, path: tuple[Any, ...] = ()) -> list[tuple[tuple[Any, ...], float]]:
    """Every number in a tool result's ``data``, with its path (P1)."""
    if isinstance(data, bool) or data is None or isinstance(data, str):
        return []
    if isinstance(data, (int, float)):
        return [(path, data)]
    if isinstance(data, Mapping):
        return [n for k, v in data.items() for n in numbers(v, (*path, k))]
    return [n for i, v in enumerate(data) for n in numbers(v, (*path, i))]


def at(obj: Any, path: Sequence[Any]) -> Any:
    """The value at a path in what the workspace returned or the store holds: keys, indexes, and attributes."""
    for key in path:
        if isinstance(obj, (Mapping, list, tuple)):
            obj = obj[key]
        else:
            obj = getattr(obj, key)
    return obj


def numbers_match(data: Any, source: Any, *, derived: tuple[str, ...] = ()) -> None:
    """C55's last clause: each number in ``data`` equals the value at its path in ``source`` exactly."""
    for path, value in numbers(data):
        if any(k in derived for k in path):
            continue
        expected = at(source, path)
        expected = getattr(expected, "value", expected)
        assert isinstance(expected, (int, float)) and not isinstance(expected, bool), (path, expected)
        assert value == expected and (math.copysign(1, value) == math.copysign(1, expected)), (path, value, expected)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with R2 and R5 loaded, and a point run and an R5 scatter stored (with failed runs)."""
    root = tmp_path / "project"
    root.mkdir()
    with open_workspace("ema_workspace", root=root) as ws:
        ws.load_model(copy_reference("R2", root / "models"))
        ws.load_model(copy_reference("R5", root / "models"))
        ws.test_model("ishigami", approve=Asked())
        ws.run("ishigami", "point_run", approve=Asked(), repeats=1)
        ws.run("r5", "scatter", {"a": [-1.0, 1.0], "b": [-1.0, 1.0]}, prediction="y", n=30, seed=2, approve=Asked())
    return root


def _cases(root: Path, result_id: str) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """Each tool's call that succeeds and one that fails (C55)."""
    shutil.copy(root / "models" / "r2" / "ishigami.py", root / "drafted.py")
    drafted = {**R2_SPEC, "name": "drafted", "function": "drafted.py:f"}
    request = {"model": "ishigami", "diagnostic": "scatter", "space": PI, "params": {"n": 12, "seed": 3}}
    return {
        "models": ({"name": "ishigami"}, {"name": "nope"}),
        "diagnostics": ({"name": "scatter"}, {"name": "nope"}),
        "propose_model": ({"spec": drafted, "path": "drafted.json"}, {"spec": drafted, "path": "/etc/x.json"}),
        "save_model": ({"spec": drafted, "path": "drafted.json"}, {"spec": {"name": "x"}, "path": "x.json"}),
        "test_model": ({"name": "ishigami"}, {"name": "nope"}),
        "price": (request, {**request, "space": {"x1": [1, "a"]}}),
        "run_diagnostic": (request, {**request, "diagnostic": "nope"}),
        "results": ({"id": result_id}, {"id": "zzzz"}),
        "failed_runs": ({"id": result_id}, {"id": "0000"}),
        "export": ({"id": result_id, "directory": "out"}, {"id": result_id, "directory": "../out"}),
    }


def _source(ws: Workspace, store: Store, tool: str, arguments: dict[str, Any], data: Any) -> Any:
    """What the tool's numbers name: the store's result, or the workspace's own return (P1)."""
    if tool in ("run_diagnostic", "results"):
        return json.loads(store.get_result(data["result_id"]).to_json())
    if tool == "price":
        a = arguments
        return ws.price(a["model"], a["diagnostic"], a["space"], **a["params"])
    if tool == "failed_runs":
        return ws.failed_runs(arguments["id"])
    if tool == "test_model":
        return ws.run_dirs(data["run_id"])[0]
    if tool == "models":
        return {"spec": json.loads(ws.describe_model(arguments["name"]).spec.to_json())}
    if tool == "diagnostics":
        return ws.describe_diagnostic(arguments["name"])
    return data  # propose_model, save_model, export: no number to name but the spec's, which the spec holds


@pytest.mark.parametrize("tool", list(TOOLS))
def check_tool(tool: str, project: Path) -> None:
    """C55: the tool returns the envelope on success and on an error, with ``retryable``; its schema describes every
    field; every number in its result equals the stored value it names."""
    with Store.open(project / "ema_workspace") as store:
        result_id = store.list_results("r5", None, None, None)[0].result_id
    good, bad = _cases(project, result_id)[tool]
    server = EmaServer(root=str(project))

    async def script(client: Client) -> Any:
        listed = {t.name: t for t in (await client.list_tools()).tools}
        return listed[tool], envelope(await client.call_tool(tool, good)), envelope(await client.call_tool(tool, bad))

    try:
        described, ok, failed = scripted(server, script, elicit=Elicited())
    finally:
        server.close()
    assert described.description and all(p["description"] for p in described.input_schema["properties"].values())
    assert ok["ok"] and ok["error"] is None and isinstance(ok["text"], str) and isinstance(ok["see"], list), ok
    assert not failed["ok"] and failed["data"] is None and isinstance(failed["error"]["retryable"], bool), failed
    with open_workspace(project / "ema_workspace") as ws, Store.open(project / "ema_workspace") as store:
        source = _source(ws, store, tool, good, ok["data"])
        numbers_match(ok["data"], source, derived=("params_schema",))


def test_a_tool_that_rounds_a_number_fails_the_check(project: Path) -> None:
    """C55's negative control: a result whose numbers a tool rounded itself fails ``numbers_match`` (meta-test)."""
    with Store.open(project / "ema_workspace") as store:
        result = store.get_result(store.list_results("r5", None, None, None)[0].result_id)
    stored = json.loads(result.to_json())
    rounded = json.loads(json.dumps(stored), parse_float=lambda s: round(float(s), 3))
    numbers_match(stored, stored)
    assert numbers(rounded) != numbers(stored)
    with pytest.raises(AssertionError):
        numbers_match(rounded, stored)


@pytest.mark.slow
def check_use_case_u9(tmp_path: Path) -> None:
    """C53's U9 on R2: the scripted client starts the server with a root naming the project; propose, save, test,
    and scatter (n = 200, seed 1) ask three elicitations in that order with U1's prices; a declined one saves or runs
    nothing; every number in a tool result equals the stored value; the report read through its resource is
    byte-identical to U1's report on R2; no tool writes a file that EMA runs."""
    project = tmp_path / "beam_project"
    project.mkdir()
    shutil.copy(Path(ema.reference_models.path("R2")).parent / "ishigami.py", project / "ishigami.py")
    before = {p for p in project.rglob("*")}
    server = EmaServer(root=str(project))
    declined, asked = Elicited(action="decline"), Elicited()

    async def no(client: Client) -> Any:
        return await client.call_tool("save_model", {"spec": R2_SPEC, "path": "ishigami.json"})

    async def yes(client: Client) -> Any:
        proposed = envelope(await client.call_tool("propose_model", {"spec": R2_SPEC, "path": "ishigami.json"}))
        saved = envelope(await client.call_tool("save_model", {"spec": R2_SPEC, "path": "ishigami.json"}))
        tested = envelope(await client.call_tool("test_model", {"name": "ishigami"}))
        run = envelope(
            await client.call_tool(
                "run_diagnostic",
                {"model": "ishigami", "diagnostic": "scatter", "space": PI, "params": {"n": 200, "seed": 1}},
            )
        )
        got = envelope(await client.call_tool("results", {"id": run["data"]["short_id"]}))
        report = await client.read_resource(f"ema://results/{run['data']['result_id']}/report")
        return proposed, saved, tested, run, got, report.contents[0].text  # type: ignore[union-attr]

    try:
        refused = envelope(scripted(server, no, elicit=declined))
        assert not refused["ok"] and not (project / "ishigami.json").exists()
        proposed, saved, tested, run, got, report = scripted(server, yes, elicit=asked)
    finally:
        server.close()
    assert all(e["ok"] for e in (proposed, saved, tested, run, got))
    confirm, test, scatter = asked.messages
    assert str(project.resolve() / "ishigami.json") in confirm and "x1" in confirm and "ishigami.py" in confirm
    assert "Price: 1 new run, 0 reused, time unknown" in test
    assert "Price: 200 new runs, 0 reused, about " in scatter
    with Store.open(project / "ema_workspace") as store:
        stored = json.loads(store.get_result(run["data"]["result_id"]).to_json())
        directory = Path(store.layout.root) / "results" / run["data"]["result_id"]
    numbers_match(run["data"], stored, derived=())
    numbers_match(got["data"], stored, derived=())
    assert report.encode("utf-8") == (directory / "report.md").read_bytes()
    with open_workspace(tmp_path / "u1") as ws:  # U1's steps on R2, in Python
        ws.load_model(ema.reference_models.path("R2"))
        ws.test_model("ishigami", approve=Asked())
        u1 = ws.run("ishigami", "scatter", PI_SPACE, n=200, seed=1, approve=Asked())
        assert ws.report(u1).markdown == report
    written = {p for p in project.rglob("*")} - before
    assert {p for p in written if "ema_workspace" not in p.relative_to(project).parts} == {project / "ishigami.json"}
