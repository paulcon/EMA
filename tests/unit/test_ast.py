"""What import-linter can't express (architecture.md §10): AR7, no module in ``ema`` imports the root package.

``ema/models/__init__.py`` doesn't import ``execute`` (AR4), so the package's re-exports can't bypass it. AR3's part
(``ema.cli`` imports ``ema.mcp`` only in its ``mcp`` command) is added with those packages.
"""

import ast
from pathlib import Path

import ema

SOURCE = Path(ema.__file__).resolve().parent


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SOURCE.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports_of(path: Path) -> list[tuple[int, str]]:
    """The modules a file imports, absolute, with their lines; ``from X import a`` gives X and X.a."""
    name = module_name(path)
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - node.level + 1]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            found.append((node.lineno, target))
    return found


def root_imports() -> list[str]:
    bad = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path == SOURCE / "__init__.py" or "reference_models" in path.parts:
            continue
        for line, target in imports_of(path):
            if target == "ema":
                bad.append(f"{path.relative_to(SOURCE.parent)}:{line}")
    return bad


def test_ar7_no_module_imports_the_root_package():
    assert not root_imports()


def test_the_scan_sees_relative_and_absolute_root_imports(tmp_path):
    """A negative control for the scan itself."""
    pkg = tmp_path / "ema" / "types"
    pkg.mkdir(parents=True)
    (pkg / "x.py").write_text("from .. import errors\nimport ema\nfrom ema import types\nfrom ema.types import y\n")
    global SOURCE
    saved, SOURCE = SOURCE, tmp_path / "ema"
    try:
        found = [t for _, t in imports_of(pkg / "x.py")]
    finally:
        SOURCE = saved
    assert found == ["ema", "ema", "ema", "ema.types"]


def execute_imports(source: str) -> list[str]:
    """The imports in ``source`` that name a module called ``execute``, absolute or relative."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            names += [module] + [f"{module}.{alias.name}" for alias in node.names]
    return [n for n in names if "execute" in n.replace("..", ".").split(".")]


def test_ar4_the_models_package_does_not_import_execute():
    assert not execute_imports((SOURCE / "models" / "__init__.py").read_text(encoding="utf-8"))


def test_the_execute_scan_sees_each_form():
    """A negative control for the scan itself."""
    for source in ("from . import execute", "from .execute import x", "import ema.models.execute",
                   "from ema.models import execute as e"):  # fmt: skip
        assert execute_imports(source), source
    assert not execute_imports("from ema.models.spec import load_spec\nimport executor")
