"""No ids of any kind in text users see (record 0086 item 6; record 0087 item 2).

The diagnostic parameters' meanings (``info()``, ``ema diagnostic describe``, the MCP tools' JSON schema), the MCP
server's instructions and tool descriptions, and every message a user can cause (each string literal in ``ema``'s
source that isn't a docstring, but those of the errors only a programming error raises) cite no record and no spec
id: "(0032)" and "(G9)" mean nothing to a user. Docstrings, comments, tests, and ``ValueError``, ``TypeError``, and
``AssertionError`` messages keep their ids. A heuristic: a programming error of another type, a number such as
0.0001 in a message, or a parenthesized label such as "(R2)" that is data, not a citation, would need this test
changed.
"""

import ast
import re
from pathlib import Path

import ema
from ema.diagnostics import base
from ema.mcp import server

SOURCE = Path(ema.__file__).resolve().parent
#: A record id: four digits starting with 0 ("0032"), or "record" and a number.
RECORD_ID = re.compile(r"\b0\d{3}\b|\brecord \d")
#: A spec id (P3, G9, AR3, OD-2, R4a), the way the specs write one.
_SPEC = r"(?:AR|OD-|[PUMGSVCQWITER])\d+[a-z]?\b"
#: A spec id cited (0087 item 2): a parenthesized list of ids that holds one ("(G9)", "(I2, I4)", "(0057; T5)"),
#: or a section ("§3"). A list that goes on in words, "(R9, a real simulator, comes later)", names data.
SPEC_ID = re.compile(rf"\((?:[^()]*[;,] )?{_SPEC}(?:[;,] (?:{_SPEC}|0\d{{3}}\b))*\)|§ ?\d")
#: Either kind of id.
ANY_ID = re.compile(f"{RECORD_ID.pattern}|{SPEC_ID.pattern}")
#: The errors only a programming error raises: their messages keep their ids (0086 item 6; 0087 item 2).
PROGRAMMING_ERRORS = {"ValueError", "TypeError", "AssertionError"}


def test_the_pattern():
    assert RECORD_ID.search("the sampler (0032).") and RECORD_ID.search("(record 0070, item 2)")
    assert not RECORD_ID.search("0123456789") and not RECORD_ID.search("2.0.0.dev1, 1e-12, 600 s, ₀₁₂")
    cited = ["the point (G9).", "(I2, I4)", "the root (T5; 0057, 0061)", "(see 0019, C55)", "(AR3)", "§8", "(R4a)"]
    assert all(SPEC_ID.search(t) for t in cited)
    data = ["R², R2, r2", "(R9, a real simulator, comes later)", "(C)", "(P3 and more)", "V32", "(x1)", "(m/s)"]
    assert not any(SPEC_ID.search(t) for t in data)


def test_parameter_meanings_cite_no_id():
    """0086 item 6, 0087 item 2: every diagnostic's parameter meanings, as ``describe`` and the JSON schema give them."""
    assert len(base.names()) >= 6, "the scan found too little"
    found = []
    for name in base.names():
        d = base.get(name)
        summary = base.describe(d)
        texts = [summary.text, d.summary, *(p.meaning for p in summary.parameters)]
        texts += [str(p.json_schema.get("description", "")) for p in summary.parameters]
        found += [(name, t) for t in texts if ANY_ID.search(t)]
    assert not found, f"ids in text users see: {found}"


def test_the_mcp_servers_text_cites_no_id():
    """0086 item 6, 0087 item 2: the server's instructions, each tool's description, and each argument's."""
    instructions, _ = server._read_tools_md()
    texts = [instructions]
    for tool in server.tool_list():
        texts += [tool.description or "", *(a["description"] for a in tool.input_schema["properties"].values())]
    assert len(texts) > 20, "the scan found too little"
    found = [t for t in texts if ANY_ID.search(t)]
    assert not found, f"ids in the MCP server's text: {found}"


def _raised(node: ast.AST, parents: dict[int, ast.AST]) -> str | None:
    """The name of the exception whose raise statement holds ``node``, if one does."""
    while id(node) in parents:
        node = parents[id(node)]
        if isinstance(node, ast.Raise) and node.exc is not None:
            exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            return ast.unparse(exc).rpartition(".")[2]
    return None


def user_text() -> list[tuple[str, str]]:
    """Every string literal in ``ema``'s source but docstrings and programming errors' messages, with where it is."""
    texts = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {id(child): node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        bodies = [body for node in ast.walk(tree) if isinstance(body := getattr(node, "body", None), list)]
        docstrings = {
            id(statement.value)
            for body in bodies
            for statement in body
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) in docstrings:
                continue
            if _raised(node, parents) not in PROGRAMMING_ERRORS:
                texts.append((f"{path.relative_to(SOURCE)}:{node.lineno}", node.value))
    return texts


def test_messages_a_user_can_cause_cite_no_id():
    """0086 item 6, 0087 item 2: loading, requests, the workspace, the CLI, and the MCP server's messages and printed lines."""
    texts = user_text()
    assert any("comes in a later version" in t for _, t in texts), "the scan found too little"
    found = [(where, text) for where, text in texts if ANY_ID.search(text)]
    assert not found, f"ids in text users see: {found}"
