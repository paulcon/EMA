"""The terminology test (record 0008; the glossary's header; 0042, 0065).

It checks two things only: the public identifiers in ``ema`` (modules, classes, functions, their arguments, and
dataclass fields) for ``qoi``, ``box``, and ``DiagnosticRun``; and the text EMA generates for users (here, every
string literal in ``ema``'s source that isn't a docstring: error messages so far; report templates, figure labels,
and CLI text as later steps add them) for the generated-text list. Documents are not scanned.
"""

import ast
import dataclasses
import importlib
import inspect
import pkgutil
import re
from pathlib import Path

import pytest

import ema

SOURCE = Path(ema.__file__).resolve().parent
IDENTIFIER_WORDS = ("qoi", "box")
IDENTIFIER_NAMES = ("DiagnosticRun",)
#: Case-sensitive where the word's case is what makes it wrong ("CI", "QoI"); the rest in any case.
TEXT_WORDS = [
    (r"confidence interval", re.IGNORECASE),
    (r"\bCI\b", 0),
    (r"credible interval", re.IGNORECASE),
    (r"error bar", re.IGNORECASE),
    (r"\bQoI\b", 0),
    (r"\bbox\b", re.IGNORECASE),
    (r"\banalyst", re.IGNORECASE),
    (r"user code", re.IGNORECASE),
    (r"model code", re.IGNORECASE),
    (r"model program", re.IGNORECASE),
]
#: The one sentence each report with estimates opens its Estimates section with may say "confidence interval"
#: (EXPLAIN_INTERVALS, diagnostics/shared.md; 0042). It comes with ema.report.
ALLOWED_TEXT_OWNERS = {"EXPLAIN_INTERVALS"}


def modules() -> list[str]:
    names = ["ema"]
    for info in pkgutil.walk_packages([str(SOURCE)], prefix="ema."):
        if ".reference_models" not in info.name:
            names.append(info.name)
    return names


def words(identifier: str) -> list[str]:
    """An identifier's words: split on underscores and on camel case."""
    parts = []
    for chunk in identifier.split("_"):
        parts += re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", chunk)
    return [p.lower() for p in parts]


def bad_identifier(identifier: str) -> bool:
    return any(w in IDENTIFIER_WORDS for w in words(identifier)) or any(n in identifier for n in IDENTIFIER_NAMES)


def public_identifiers() -> set[str]:
    found: set[str] = set()
    for module_name in modules():
        module = importlib.import_module(module_name)
        found.update(module_name.split("."))
        for name, obj in vars(module).items():
            if name.startswith("_") or getattr(obj, "__module__", module_name) != module_name:
                continue
            found.add(name)
            if inspect.isclass(obj):
                if dataclasses.is_dataclass(obj):
                    found.update(f.name for f in dataclasses.fields(obj))
                for member, value in vars(obj).items():
                    if not member.startswith("_"):
                        found.add(member)
                        if inspect.isfunction(value):
                            found.update(inspect.signature(value).parameters)
            elif inspect.isfunction(obj):
                found.update(inspect.signature(obj).parameters)
    return {f for f in found if not f.startswith("_")}


def generated_text() -> list[tuple[str, str]]:
    """Every string literal in ``ema``'s source that isn't a docstring, with where it is."""
    texts = []
    for path in sorted(SOURCE.rglob("*.py")):
        if "reference_models" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    docstrings.add(id(body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in ALLOWED_TEXT_OWNERS for t in node.targets
            ):
                docstrings.update(id(n) for n in ast.walk(node.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                texts.append((f"{path.relative_to(SOURCE)}:{node.lineno}", node.value))
    return texts


def test_public_identifiers():
    found = public_identifiers()
    assert {"ModelParameterSpace", "DesignIdentity", "unregister", "anchor"} <= found, "the scan found too little"
    bad = sorted(f for f in found if bad_identifier(f))
    assert not bad, f"identifiers using a retired word: {bad}"


def test_generated_text():
    texts = generated_text()
    assert any("comes in a later version" in t for _, t in texts), "the scan found too little"
    bad = [(where, text) for where, text in texts for pattern, flags in TEXT_WORDS if re.search(pattern, text, flags)]
    assert not bad, f"generated text using a retired word: {bad}"


@pytest.mark.parametrize(
    ("identifier", "bad"),
    [
        ("input_box", True),
        ("BoxSpace", True),
        ("qoi", True),
        ("my_DiagnosticRun", True),
        ("boxes", False),
        ("inbox_count", False),
        ("model_parameter_space", False),
    ],
)
def test_the_identifier_rule(identifier, bad):
    assert bad_identifier(identifier) is bad


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("a 95% CI", True),
        ("the analyst's model", True),
        ("user code", True),
        ("QoI", True),
        ("the box", True),
        ("CIRCLE", False),
        ("a model parameter space", False),
        ("variability interval", False),
    ],
)
def test_the_text_rule(text, bad):
    assert any(re.search(p, text, f) for p, f in TEXT_WORDS) is bad
