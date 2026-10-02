"""What import-linter can't express (architecture.md §10): AR7, no module in ``ema`` imports the root package.

AR3's part (``ema.cli`` imports ``ema.mcp`` only in its ``mcp`` command) and ``ema/models/__init__.py`` not
importing ``execute`` (AR4) are added with those packages.
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
