"""The MCP server with a scripted client (step 15; architecture.md §8; U9; T4, T5, T9; C50, C55; records 0016, 0019,
0053, 0056, 0057, 0081). No LLM, so no API cost: each test drives the server through the SDK's own client over
in-memory streams, or a real ``python -m ema.mcp`` subprocess over stdio, on millisecond reference models.
"""

import asyncio
import base64
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp import Client

import ema.reference_models
from ema.mcp import server as mcp_server
from ema.mcp.server import ELICITATION_TIMEOUT_S, TOOLS, EmaServer, _Call, tool_list
from ema.store import Store
from ema.types.errors import PathRefused, Stopped
from ema.types.requests import Progress
from ema.workspace import open_workspace
from tests.support.mcp import Elicited, StdioPeer, envelope, scripted
from tests.support.workspace import PI_SPACE, copy_reference

PI = {k: list(v) for k, v in PI_SPACE.items()}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A project directory with R2 and R5 copied in, and loaded into its workspace, ``ema_workspace``."""
    project = tmp_path / "project"
    project.mkdir()
    with open_workspace("ema_workspace", root=project) as ws:
        for rid in ("R2", "R5"):
            ws.load_model(copy_reference(rid, project / "models"))
    return project


@pytest.fixture
def server(root: Path):
    s = EmaServer(root=str(root))
    try:
        yield s
    finally:
        s.close()


def runs_in(root: Path) -> int:
    return len(os.listdir(root / "ema_workspace" / "runs"))


def stored(root: Path, result_id: str) -> dict[str, Any]:
    with Store.open(root / "ema_workspace") as store:
        data = json.loads(store.get_result(result_id).to_json())
    data["provenance"].pop("run_ids")
    return data


async def call(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    return envelope(await client.call_tool(tool, arguments))


# -- the tools' descriptions and the envelope (C55; 0019) -------------------------------------------------------


def test_ten_tools_each_with_a_description_for_every_schema_field(server):
    """C55, 0016/0053/0056: 10 tools of 10, each described in tools.md, every argument described, the envelope's
    output schema; the server's instructions are tools.md's and ask the client to quote EMA's text (0019)."""

    async def script(client: Client) -> Any:
        return (await client.list_tools()).tools, client.instructions

    tools, instructions = scripted(server, script)
    assert [t.name for t in tools] == list(TOOLS) and len(tools) == 10
    for tool in tools:
        assert tool.description and tool.output_schema == mcp_server.ENVELOPE_SCHEMA
        assert set(tool.input_schema["properties"]) == set(TOOLS[tool.name])
        assert all(p["description"] for p in tool.input_schema["properties"].values()), tool.name
    assert "Quote EMA's `text`" in instructions and "quoted model output" in instructions


def test_tools_md_and_the_served_tools_must_agree(monkeypatch):
    """0019: a tool or an argument without a description in tools.md is refused when the server starts."""
    real = mcp_server._read_tools_md
    instructions, described = real()
    described = dict(described)
    described["price"] = (described["price"][0], {k: v for k, v in described["price"][1].items() if k != "space"})
    monkeypatch.setattr(mcp_server, "_read_tools_md", lambda: (instructions, described))
    with pytest.raises(RuntimeError, match="price's arguments"):
        tool_list()
    del described["export"]
    with pytest.raises(RuntimeError, match="tools.md describes"):
        tool_list()


def test_every_tool_returns_the_envelope_and_errors_say_whether_retrying_helps(server, root):
    """C55: each of the 10 tools returns {ok, data, text, see, error}, on success and on an error, an error with
    ``retryable``; unknown and mistyped arguments are refused as errors, not protocol failures."""
    asked = Elicited(action="decline")

    async def script(client: Client) -> list[dict[str, Any]]:
        out = [
            await call(client, "models"),
            await call(client, "models", name="ishigami"),
            await call(client, "diagnostics"),
            await call(client, "diagnostics", name="nope"),
            await call(client, "propose_model", spec={"name": "x"}, path="x.json"),
            await call(client, "save_model", spec={"name": "x"}, path="x.json"),
            await call(client, "test_model", name="ishigami"),
            await call(client, "price", model="ishigami", diagnostic="point_run"),
            await call(client, "run_diagnostic", model="ishigami", diagnostic="point_run"),
            await call(client, "results"),
            await call(client, "failed_runs", id="abcd"),
            await call(client, "export", id="abcd", directory="out"),
            await call(client, "price", model="ishigami", diagnostic="point_run", n=3),
            await call(client, "price", model=1, diagnostic="point_run"),
            await call(client, "price", model="ishigami", diagnostic="point_run", params='{"repeats": 1}'),
            await call(client, "price", model="ishigami", diagnostic="point_run", params="[1"),
        ]
        return out

    got = scripted(server, script, elicit=asked)
    ok = [e["ok"] for e in got]
    assert ok == [
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        True,
        False,
    ]
    assert got[14]["data"]["new"] == 2 and "JSON object" in got[15]["error"]["message"]  # params as JSON text
    for e in got:
        if e["ok"]:
            assert e["error"] is None and isinstance(e["text"], str)
        else:
            assert e["data"] is None and isinstance(e["error"]["retryable"], bool) and e["error"]["message"]
    assert got[6]["error"]["retryable"] and "declined" in got[6]["error"]["message"]  # ApprovalDeclined
    assert "no argument 'n'" in got[12]["error"]["message"] and "JSON string" in got[13]["error"]["message"]
    assert got[1]["data"]["spec"]["name"] == "ishigami" and got[1]["text"].startswith("ishigami@")
    assert runs_in(root) == 0


def test_diagnostics_name_gives_each_parameters_json_schema(server, root):
    """C55: ``diagnostics(name)`` returns each diagnostic parameter with its JSON schema, as the workspace has it,
    and the object ``params`` must meet; the resource ``ema://diagnostics/{name}`` holds the same."""

    async def script(client: Client) -> Any:
        e = await call(client, "diagnostics", name="scatter")
        r = await client.read_resource("ema://diagnostics/scatter")
        return e, json.loads(r.contents[0].text)  # type: ignore[union-attr]

    e, resource = scripted(server, script)
    with open_workspace("ema_workspace", root=root) as ws:
        expected = {
            p.name: json.loads(json.dumps(dict(p.json_schema))) for p in ws.describe_diagnostic("scatter").parameters
        }
    assert {p["name"]: p["json_schema"] for p in e["data"]["parameters"]} == expected
    assert e["data"]["params_schema"]["properties"] == expected and set(expected) >= {"n", "seed"}
    assert resource["data"] == e["data"] and resource["text"] == e["text"]


# -- approvals by elicitation (P3; T4; 0016) -------------------------------------------------------------------


def test_price_then_run_the_point_run_asks_by_elicitation_and_sends_progress(server, root):
    """§8: ``price`` asks nothing; ``run_diagnostic`` asks the price by elicitation with the terminal's text, runs,
    and sends progress notifications; every number in the result equals the stored value (P1, U9)."""
    asked = Elicited()
    progress: list[tuple[float, float | None, str | None]] = []

    async def on_progress(value: float, total: float | None, message: str | None) -> None:
        progress.append((value, total, message))

    async def script(client: Client) -> Any:
        price = await call(client, "price", model="ishigami", diagnostic="point_run", params={"repeats": 2})
        n_asked = len(asked.messages)
        arguments = {"model": "ishigami", "diagnostic": "point_run", "params": {"repeats": 2}}
        result = envelope(await client.call_tool("run_diagnostic", arguments, progress_callback=on_progress))
        return price, n_asked, result

    price, n_asked, result = scripted(server, script, elicit=asked)
    assert n_asked == 0 and price["text"] == "3 new runs, 0 reused, time unknown"
    assert (price["data"]["new"], price["data"]["reused"]) == (3, 0)
    assert len(asked.messages) == 1 and "3 new runs, 0 reused, time unknown" in asked.messages[0]
    assert result["ok"] and result["text"].startswith("Diagnostic result ")
    assert result["data"]["short_id"] in result["text"]
    assert {k: v for k, v in result["data"].items() if k not in ("short_id", "model_version")} == stored(
        root, result["data"]["result_id"]
    )
    assert result["see"][0] == f"ema://results/{result['data']['result_id']}/report"
    messages = [m for _, _, m in progress]  # the first and the last always go; between, at most every 0.2 s
    assert messages[0] == "0/3 runs" and messages[-1] == "3/3 runs" and progress[-1][:2] == (3.0, 3.0)
    values = [v for v, _, _ in progress]
    assert values == sorted(set(values))  # strictly increasing (MCP)


def test_a_declined_elicitation_runs_nothing(server, root):
    """T4: a declined elicitation is a no: ``ApprovalDeclined``, retryable, no run made; the no is recorded (W3)."""

    async def script(client: Client) -> Any:
        return await call(client, "run_diagnostic", model="ishigami", diagnostic="scatter", space=PI,
                          params={"n": 10, "seed": 1})  # fmt: skip

    for answer in (Elicited(action="decline"), Elicited(action="cancel"), Elicited(approve=False)):
        e = scripted(server, script, elicit=answer)
        assert not e["ok"] and e["error"]["retryable"] and "declined" in e["error"]["message"]
        assert len(answer.messages) == 1 and runs_in(root) == 0
    with Store.open(root / "ema_workspace") as store:
        assert [a.answer for a in store.approvals()] == [False, False, False]


def test_a_client_without_elicitation_is_refused_before_any_question(server, root):
    """§8, T4: no elicitation: ``save_model``, ``test_model``, and a run with new runs are refused before any
    question, and nothing is recorded; reads and prices work."""

    spec = json.loads(Path(ema.reference_models.path("R2")).read_text())

    async def script(client: Client) -> Any:
        return [
            await call(client, "price", model="ishigami", diagnostic="point_run"),
            await call(client, "run_diagnostic", model="ishigami", diagnostic="point_run"),
            await call(client, "test_model", name="ishigami"),
            await call(client, "save_model", spec=spec, path="models/r2/again.json"),
        ]

    price, run, test, save = scripted(server, script, elicit=None)
    assert price["ok"]
    for e in (run, test, save):
        assert not e["ok"] and e["error"]["message"].startswith("this client can't ask the user")
        assert e["error"]["retryable"] is False
    assert runs_in(root) == 0 and not (root / "models" / "r2" / "again.json").exists()
    with Store.open(root / "ema_workspace") as store:
        assert store.approvals() == () and store.confirmations() == ()


def test_a_repeated_request_asks_nothing_even_without_elicitation(server, root):
    """C50: the same request again returns the stored result and asks nothing, so a client without elicitation
    gets it too."""
    asked = Elicited()
    request = {"model": "ishigami", "diagnostic": "point_run", "params": {"repeats": 1}}

    async def first(client: Client) -> Any:
        return await call(client, "run_diagnostic", **request)

    async def again(client: Client) -> Any:
        return await call(client, "run_diagnostic", **request)

    one = scripted(server, first, elicit=asked)
    before = runs_in(root)
    two = scripted(server, again, elicit=None)
    assert len(asked.messages) == 1 and runs_in(root) == before
    assert two["ok"] and two["data"] == one["data"]


def test_scatter_results_resources_and_export(server, root):
    """§8: scatter on R2 with approval; ``results`` lists it and returns it without run ids; the report resource is
    byte-identical to the file (U9); a figure and its data card are the files; export writes inside the root only
    (E7); a figure resource named out of the result is not found (T5)."""
    asked = Elicited()

    async def script(client: Client) -> Any:
        run = await call(client, "run_diagnostic", model="ishigami", diagnostic="scatter", space=PI,
                         params={"n": 20, "seed": 1})  # fmt: skip
        rid = run["data"]["result_id"]
        listed = await call(client, "results")
        one = await call(client, "results", id=rid[:6])
        report = await client.read_resource(f"ema://results/{rid}/report")
        figure = run["data"]["figures"][0]["name"]
        png = await client.read_resource(f"ema://results/{rid}/figures/{figure}.png")
        card = await client.read_resource(f"ema://results/{rid}/figures/{figure}.json")
        resources = (await client.list_resources()).resources
        templates = (await client.list_resource_templates()).resource_templates
        missing = []
        for uri in (f"ema://results/{rid}/figures/..%2F..%2Fx.png", f"ema://results/{rid}/figures/../../x.png",
                    "ema://results/ffff/report", "ema://other"):  # fmt: skip
            try:
                await client.read_resource(uri)
            except Exception as error:  # noqa: BLE001
                missing.append(str(error))
        exported = await call(client, "export", id=rid, directory="exports/first")
        outside = await call(client, "export", id=rid, directory="../elsewhere")
        climbing = await call(client, "export", id=rid, directory="exports/../../elsewhere")
        in_workspace = await call(client, "export", id=rid, directory="ema_workspace/results/x")
        failed = await call(client, "failed_runs", id=rid)
        return run, listed, one, report, png, card, resources, templates, missing, exported, outside, climbing, \
            in_workspace, failed  # fmt: skip

    (run, listed, one, report, png, card, resources, templates, missing, exported, outside, climbing, in_workspace,
     failed) = scripted(server, script, elicit=asked)  # fmt: skip
    rid = run["data"]["result_id"]
    assert len(asked.messages) == 1 and "Price: 20 new runs, 0 reused, time unknown" in asked.messages[0]
    assert listed["data"][0]["result_id"] == rid and listed["data"][0]["short_id"] in listed["text"]
    assert one["data"] == run["data"] and "run_ids" not in one["data"]["provenance"]
    directory = root / "ema_workspace" / "results" / rid
    assert report.contents[0].text.encode("utf-8") == (directory / "report.md").read_bytes()
    figure = run["data"]["figures"][0]
    assert base64.b64decode(png.contents[0].blob) == (directory / figure["png"]).read_bytes()
    assert card.contents[0].text.encode("utf-8") == (directory / figure["card"]).read_bytes()
    uris = {r.uri for r in resources}
    assert f"ema://results/{rid}/report" in uris and "ema://diagnostics/scatter" in uris
    assert {t.uri_template for t in templates} >= {"ema://results/{id}/report", "ema://diagnostics/{name}"}
    assert len(missing) == 4
    assert exported["ok"] and (root / "exports" / "first" / "runs.csv").is_file()
    for refused in (outside, climbing, in_workspace):
        message = refused["error"]["message"]
        assert not refused["ok"] and ("outside the root" in message or "inside the workspace" in message), message
    assert not (root.parent / "elsewhere").exists()
    assert failed["ok"] and failed["data"] == []


def test_failed_runs_quotes_the_models_reasons(server, root):
    """U3 through MCP: R5's failed runs come back with their reasons, as data and EMA's text (trust.md)."""

    async def script(client: Client) -> Any:
        run = await call(
            client,
            "run_diagnostic",
            model="r5",
            diagnostic="scatter",
            space={"a": [-1.0, 1.0], "b": [-1.0, 1.0]},
            prediction="y",
            params={"n": 30, "seed": 2},
        )
        return run, await call(client, "failed_runs", id=run["data"]["short_id"])  # fmt: skip

    run, failed = scripted(server, script, elicit=Elicited())
    assert run["ok"] and failed["ok"] and failed["data"]
    assert all(r["reason"] for r in failed["data"]) and failed["data"][0]["short_id"] in failed["text"]
    assert any(s.startswith("failed_runs(") for s in run["see"])


# -- U9: a model set up through MCP (0016) ----------------------------------------------------------------------


def test_u9_propose_save_test_and_run(server, root):
    """U9 on R2 (n = 20 here; the slow tier runs n = 200): propose_model saves nothing; save_model asks with the
    absolute path and the full text, then loads; test_model asks "1 new, 0 reused, time unknown"; scatter asks its
    price; the elicitations come in that order; only the spec file is written in the project (no code)."""
    project = root / "beam"
    project.mkdir()
    shutil.copy(Path(ema.reference_models.path("R2")).parent / "ishigami.py", project / "beam.py")
    spec = {**json.loads(Path(ema.reference_models.path("R2")).read_text()), "name": "beam", "function": "beam.py:f"}
    asked = Elicited()
    before = sorted(p for p in root.rglob("*") if "ema_workspace" not in p.parts)

    async def script(client: Client) -> Any:
        proposed = await call(client, "propose_model", spec=spec, path="beam/beam.json")
        n0 = len(asked.messages)
        saved = await call(client, "save_model", spec=spec, path="beam/beam.json")
        tested = await call(client, "test_model", name="beam")
        run = await call(client, "run_diagnostic", model="beam", diagnostic="scatter", space=PI,
                         params={"n": 20, "seed": 1})  # fmt: skip
        return proposed, n0, saved, tested, run

    proposed, n0, saved, tested, run = scripted(server, script, elicit=asked)
    assert proposed["ok"] and n0 == 0 and "nothing saved yet" in proposed["text"]
    assert saved["ok"] and saved["text"].startswith("Loaded beam@") and tested["ok"] and run["ok"]
    confirm, test, scatter = asked.messages
    assert str((project / "beam.json").resolve()) in confirm and proposed["data"]["spec_text"] in confirm
    assert "1 new run, 0 reused, time unknown" in test and "20 new runs, 0 reused" in scatter
    after = sorted(p for p in root.rglob("*") if "ema_workspace" not in p.parts and "__pycache__" not in p.parts)
    assert sorted(set(after) - set(before)) == [project / "beam.json"]
    assert (project / "beam.json").read_text(encoding="utf-8") == proposed["data"]["spec_text"]


def test_u9_a_declined_confirmation_saves_nothing_and_paths_outside_the_root_are_refused(server, root, tmp_path):
    """T4, T5: a declined confirmation saves no spec; a path outside the root, climbing out, inside a workspace, or
    with U+202E is refused before anything is asked or written."""
    spec = json.loads(Path(ema.reference_models.path("R2")).read_text())
    asked = Elicited(action="decline")

    async def script(client: Client) -> Any:
        out = [await call(client, "save_model", spec=spec, path="models/r2/copy.json")]
        for path in (str(tmp_path / "outside.json"), "../outside.json", "ema_workspace/x.json",
                     "models/r2/" + chr(0x202E) + "x.json"):  # fmt: skip
            out.append(await call(client, "save_model", spec=spec, path=path))
            out.append(await call(client, "propose_model", spec=spec, path=path))
        return out

    declined, *refused = scripted(server, script, elicit=asked)
    assert not declined["ok"] and len(asked.messages) == 1
    assert not (root / "models" / "r2" / "copy.json").exists() and not (tmp_path / "outside.json").exists()
    assert all(not e["ok"] for e in refused) and len(asked.messages) == 1


# -- the root, the protocol eras, cancellation, and stdout (T5, T9; 0081) ---------------------------------------


def test_the_root_is_refused_before_anything_is_served(tmp_path, root):
    """T5, 0061: a relative root, ``/``, a root that isn't a directory, and one inside a workspace: PathRefused;
    ``python -m ema.mcp`` says so on stderr and exits 2, with nothing on stdout."""
    for bad in ("relative/dir", "/", str(tmp_path / "missing"), str(root / "ema_workspace" / "runs")):
        with pytest.raises(PathRefused):
            EmaServer(root=bad)
    done = subprocess.run(
        [sys.executable, "-m", "ema.mcp", "--root", "relative"], capture_output=True, text=True, check=False
    )
    assert done.returncode == 2 and done.stdout == "" and "relative" in done.stderr


def test_a_client_in_auto_mode_falls_back_to_the_handshake_and_is_asked(server, root):
    """0081 item 2: the server speaks the handshake era only, where it can ask while a run waits; a client that
    probes the 2026 era first falls back to ``initialize``, and elicitation works."""
    asked = Elicited()

    async def script(client: Client) -> Any:
        return client.protocol_version, await call(client, "test_model", name="ishigami")

    version, tested = scripted(server, script, elicit=asked, mode="auto")
    assert version == "2025-11-25" and tested["ok"] and len(asked.messages) == 1


def test_a_cancelled_call_stops_at_its_next_progress_and_its_question_is_a_no():
    """0080: raising in ``on_progress`` is the cancellation hook; a cancelled call's question is answered no."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        c = _Call(ctx=None, loop=loop, can_ask=True)  # type: ignore[arg-type]
        c.cancel()
        with pytest.raises(Stopped):
            c.progress(Progress.of_runs(1, 3))
        assert c.approver(SimpleNamespace(text="a question")) is False  # type: ignore[misc, arg-type]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
    assert ELICITATION_TIMEOUT_S == 900


NOISY = """
import sys
print("hello from import")
sys.stdout.write("more at import\\n")
sys.stdout.flush()


def f(x):
    print("a call at", x)
    sys.stdout.write("{not json\\n")
    return 2.0 * x
"""


def test_stdio_carries_only_protocol_messages_with_a_model_that_prints(tmp_path):
    """T9 under a real ``python -m ema.mcp`` subprocess: a model that prints at import and in each call leaves
    stdout valid JSON-RPC, line by line; the server answers initialize and tools/list; U9's save, test, and a run
    with progress notifications work over stdio, with every elicitation answered yes."""
    root = tmp_path / "project"
    (root / "noisy").mkdir(parents=True)
    (root / "noisy" / "noisy.py").write_text(NOISY)
    spec = {"name": "noisy", "description": "prints to stdout", "interface": "python_function",
            "function": "noisy.py:f", "parameters": [{"name": "x", "units": "", "nominal": 1.0, "description": ""}],
            "predictions": [{"name": "y", "units": "", "description": ""}]}  # fmt: skip
    peer = StdioPeer(root)
    try:
        init = peer.initialize()
        assert init["serverInfo"]["name"] == "ema" and init["protocolVersion"] == "2025-06-18"
        assert len(peer.request("tools/list")["tools"]) == 10
        saved = peer.call("save_model", {"spec": spec, "path": "noisy/noisy.json"})
        tested = peer.call("test_model", {"name": "noisy"})
        run = peer.call("run_diagnostic", {"model": "noisy", "diagnostic": "point_run", "params": {"repeats": 2}},
                        progress="p1")  # fmt: skip
    finally:
        code = peer.close()
    assert saved["ok"] and tested["ok"] and run["ok"], (saved, tested, run)
    assert len(peer.elicited) == 3 and code == 0
    assert any(n["method"] == "notifications/progress" and n["params"]["progressToken"] == "p1" for n in peer.notes)
    assert run["data"]["counts"]["usable"] == 3


# -- review round 1 (record 0081, Review round 1) -----------------------------------------------------------------


def test_save_model_loads_a_hand_written_spec_with_the_same_spec(server, root):
    """Ruling A (T6; U9): ``save_model`` with a reference model's own hand-written ``model.json`` (as its text, or as
    an object) asks "already saved, unchanged: load it?" with the file's text, loads it after the yes, and leaves
    the file unchanged byte for byte; a different spec at the path is refused before asking."""
    spec_path = copy_reference("R3", root / "more")
    original = spec_path.read_bytes()
    asked = Elicited()

    async def script(client: Client) -> Any:
        text, path = original.decode(), "more/r3/model.json"
        return [
            await call(client, "propose_model", spec=text, path="more/r3/model.json"),
            await call(client, "save_model", spec=text, path="more/r3/model.json"),
            await call(client, "save_model", spec=json.loads(text), path="more/r3/model.json"),
            await call(client, "save_model", spec={**json.loads(text), "description": "other"}, path=path),
        ]

    proposed, saved, again, other = scripted(server, script, elicit=asked)
    assert proposed["ok"] and proposed["data"]["spec_text"].encode() == original
    assert saved["ok"] and saved["text"].startswith("Loaded r3@") and again["ok"]
    assert len(asked.messages) == 2 and all("already saved, unchanged: load it?" in m for m in asked.messages)
    assert original.decode() in asked.messages[0]
    assert not other["ok"] and "another spec" in other["error"]["message"]
    assert spec_path.read_bytes() == original


def test_accept_on_the_form_is_a_yes_by_its_default(server, root):
    """Ruling B (record 0081 item 6, amended): the form's ``approve`` is checked by default, so Accept with the field
    left out is a yes; ``approve`` false, or not a boolean, is a no."""
    schemas: list[Any] = []

    class Seen(Elicited):
        async def __call__(self, context: Any, params: Any) -> Any:
            schemas.append(params.requested_schema)
            return await super().__call__(context, params)

    async def script(client: Client) -> Any:
        return await call(client, "run_diagnostic", model="ishigami", diagnostic="point_run", params={"repeats": 1})

    for content, yes in (({"approve": "true"}, False), ({"approve": False}, False), ({}, True)):
        e = scripted(server, script, elicit=Seen(content=content))
        assert e["ok"] is yes, (content, e)
    assert schemas[0]["properties"]["approve"]["default"] is True and schemas[0]["required"] == ["approve"]


def test_params_naming_a_tools_own_argument_is_a_request_error(server, root):
    """m2: ``params`` naming ``space``, ``model``, ``diagnostic``, ``self``, ``prediction``, ``retry_failed``,
    ``approve``, or ``on_progress`` is an EMA error envelope saying where it goes, never a ``TypeError``; n5:
    ``results`` with an id and a filter is refused, as the CLI refuses it."""
    names = ("space", "model", "diagnostic", "self", "prediction", "retry_failed", "approve", "on_progress")

    async def script(client: Client) -> Any:
        out = []
        for tool in ("price", "run_diagnostic"):
            for name in names:
                out.append(await call(client, tool, model="ishigami", diagnostic="point_run", params={name: 1}))
        out.append(await call(client, "results", id="abcd", model="ishigami"))
        return out

    *got, both = scripted(server, script, elicit=Elicited())
    for e, name in zip(got, names * 2, strict=True):
        message = e["error"]["message"]
        assert not e["ok"] and message.startswith(f"{name} isn't a diagnostic parameter"), message
        assert "TypeError" not in message and "unexpectedly" not in message
    assert "it goes in the tool's own `space` argument, not in params" in got[0]["text"]
    assert not both["ok"] and "not both" in both["error"]["message"]
    assert runs_in(root) == 0


def test_a_cancel_landing_before_the_question_is_waited_on_is_not_lost():
    """n1: a cancel that lands after the check but before the question's future is kept still stops the call at
    once (``_waiting`` is set before ``cancelled`` is checked again); the question is a no."""

    class Late(threading.Event):
        checks = 0

        def is_set(self) -> bool:
            Late.checks += 1
            return Late.checks > 1  # the first check sees no cancel; it lands just after

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        c = _Call(ctx=None, loop=loop, can_ask=True)  # type: ignore[arg-type]
        c.cancelled = Late()
        with pytest.raises(Stopped):
            c._on_loop(asyncio.sleep(3600), timeout=5)
        Late.checks = 0
        assert c._ask(SimpleNamespace(text="q")) is False  # type: ignore[arg-type]
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.05), loop).result()  # the cancelled tasks end
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()


def test_a_queued_call_cancelled_at_disconnect_records_nothing(server, root):
    """n2 (T3: only questions asked are recorded): a call cancelled before it starts never calls the workspace."""
    c = _Call(ctx=None, loop=None, can_ask=True)  # type: ignore[arg-type]
    c.cancel()
    arguments = {"model": "ishigami", "diagnostic": "point_run"}
    e = server._writer.submit(server._dispatch, server._write_ws, "run_diagnostic", arguments, c).result()
    assert not e["ok"] and e["error"]["message"].startswith("stopped")
    with Store.open(root / "ema_workspace") as store:
        assert store.approvals() == ()


def test_plain_refuses_a_non_finite_number():
    """n6 (P1, C55): EMA's types hold finite numbers only; a non-finite one is an error, never null or text."""
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match="non-finite"):
            mcp_server._plain({"x": [bad]})


SLOW = "import time\n\n\ndef f(x):\n    time.sleep(0.3)\n    return 2.0 * x\n"


def _children(pid: int) -> list[int]:
    found = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False).stdout
    return [int(p) for p in found.split()]


def _gone(pids: list[int], timeout: float = 10) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        alive = []
        for p in pids:
            try:
                os.kill(p, 0)
                alive.append(p)
            except ProcessLookupError:
                pass
        if not alive:
            return True
        time.sleep(0.1)
    return False


def test_stdio_a_call_cancelled_during_its_form_runs_nothing(root):
    """m4 (P3; T4): a call cancelled while its form is shown runs nothing, even after a late yes; its question is
    recorded as a no, and the server goes on answering."""
    peer = StdioPeer(root, hold=True)
    try:
        peer.initialize()
        arguments = {"model": "ishigami", "diagnostic": "scatter", "space": PI, "params": {"n": 7, "seed": 9}}
        rid = peer.start("tools/call", peer.tool_params("run_diagnostic", arguments))
        peer.pump(lambda: peer.held, 60)
        peer.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": rid}})
        time.sleep(0.5)
        late = peer.held.pop()
        peer.send({"jsonrpc": "2.0", "id": late["id"], "result": {"action": "accept", "content": {"approve": True}}})
        peer.hold = False
        listed = peer.call("results", {})
    finally:
        code = peer.close()
    assert rid not in peer.responses and listed["ok"] and code == 0
    assert runs_in(root) == 0
    with Store.open(root / "ema_workspace") as store:
        assert [a.answer for a in store.approvals()] == [False]


@pytest.mark.parametrize("how", ["disconnect", "SIGTERM"])
def test_stdio_leaving_during_a_run_stops_it_and_its_children(root, how):
    """m1, m4 (C49; 0026): a client that leaves during a run, or a SIGTERM, stops the evaluation between two runs,
    every finished run stored; the server exits (by the signal, for SIGTERM), its model children stop, and the run
    lock is free."""
    (root / "slow").mkdir()
    (root / "slow" / "slow.py").write_text(SLOW)
    spec = {"name": "slow", "description": "", "interface": "python_function", "function": "slow.py:f",
            "parameters": [{"name": "x", "units": "", "nominal": 0.5, "description": ""}],
            "predictions": [{"name": "y", "units": "", "description": ""}]}  # fmt: skip
    (root / "slow" / "model.json").write_text(json.dumps(spec))
    with open_workspace("ema_workspace", root=root) as ws:
        ws.load_model("slow/model.json")
    peer = StdioPeer(root)
    peer.initialize()
    arguments = {"model": "slow", "diagnostic": "scatter", "space": {"x": [0.0, 1.0]}, "params": {"n": 20, "seed": 1}}
    peer.start("tools/call", peer.tool_params("run_diagnostic", arguments, progress="p"))
    peer.pump(lambda: any(n["params"].get("progress", 0) >= 1 for n in peer.notes), 60)
    children = _children(peer.proc.pid)
    assert children
    if how == "SIGTERM":
        peer.proc.send_signal(signal.SIGTERM)
        code = peer.proc.wait(timeout=60)
        peer.stderr.close()
    else:
        code = peer.close()
    assert code == (-signal.SIGTERM if how == "SIGTERM" else 0)
    assert _gone(children), "a model child outlived the server"
    assert 1 <= runs_in(root) < 20
    with open_workspace("ema_workspace", root=root) as ws:  # the lock is free: a run goes
        assert ws.run("ishigami", "point_run", repeats=1, approve=lambda q: True).counts.new == 2


def test_stdio_malformed_answers_are_a_no_at_once(root):
    """m3, m4 (P3; record 0081 item 6): a reply whose result isn't an object, an ``approve`` that isn't the boolean
    true, an unknown action, and a client error are each a no at once, nothing run; Accept with ``{}`` or no content
    takes the form's default, a yes."""
    replies: list[dict[str, Any]] = [
        {"result": "yes"},
        {"result": None},
        {"result": {"action": "accept", "content": {"approve": "true"}}},
        {"result": {"action": "accept", "content": {"approve": 1}}},
        {"result": {"action": "yes", "content": {"approve": True}}},
        {"error": {"code": -32603, "message": "client blew up"}},
        {"result": {"action": "accept", "content": {}}},
        {"result": {"action": "accept"}},
    ]
    peer = StdioPeer(root, replies=replies)
    got = []
    started = time.monotonic()
    try:
        peer.initialize()
        for seed in (1, 1, 1, 1, 1, 1, 1, 2):
            arguments = {"model": "ishigami", "diagnostic": "scatter", "space": PI, "params": {"n": 5, "seed": seed}}
            got.append(peer.call("run_diagnostic", arguments))
    finally:
        code = peer.close()
    assert time.monotonic() - started < 60 and code == 0  # none waited ELICITATION_TIMEOUT_S
    assert [e["ok"] for e in got] == [False] * 6 + [True, True]
    assert all("declined" in e["error"]["message"] for e in got[:6])
    assert peer.forms[0]["requestedSchema"]["properties"]["approve"]["default"] is True
    with Store.open(root / "ema_workspace") as store:
        assert [a.answer for a in store.approvals()] == [False] * 6 + [True, True]
