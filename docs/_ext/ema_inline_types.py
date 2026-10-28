"""Keep napoleon from reading an attribute's first line as a type (plan 18, review round 1).

Napoleon reads an attribute's, a module constant's, or a property's docstring whose first line holds a colon as
"type: description", and renders the words before the colon as its type ("Type: The largest design built"). EMA's
docstrings give no inline types (the annotations do), so a ``:type:`` line napoleon adds is always a misreading: this
extension saves each such docstring before napoleon runs, and restores it when napoleon has added one.
"""

from typing import Any

from sphinx.application import Sphinx

#: The kinds of object napoleon parses as an attribute.
_KINDS = ("attribute", "data", "property")

#: Each docstring as it was before napoleon, by object name.
_before: dict[str, list[str]] = {}


def _has_type(lines: list[str]) -> bool:
    return any(line.lstrip().startswith(":type:") for line in lines)


def _save(app: Sphinx, what: str, name: str, obj: object, options: object, lines: list[str]) -> None:
    if what in _KINDS:
        _before[name] = list(lines)


def _restore(app: Sphinx, what: str, name: str, obj: object, options: object, lines: list[str]) -> None:
    before = _before.pop(name, None)
    if before is not None and _has_type(lines) and not _has_type(before):
        lines[:] = before


def setup(app: Sphinx) -> dict[str, Any]:
    """Save before napoleon (priority 500), after the citations are dropped (400); restore after it."""
    app.connect("autodoc-process-docstring", _save, priority=450)
    app.connect("autodoc-process-docstring", _restore, priority=600)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
