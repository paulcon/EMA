"""The reference models (docs/design/reference_models.md): R1-R8, R10, and R11, each a model spec with its files.

Data beside the layers: no module in ``ema`` imports this package (architecture.md §1, §10). Each model is a
directory holding ``model.json`` (its model spec), its Python function file or program, and ``space.json``, the
model parameter space its expected answers are for, in its JSON form (designs.md). R9, a real simulator, comes later.
"""

import json
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent

#: The reference models' ids, as the reference models' spec names them (reference_models.md).
IDS = ("R1", "R2", "R3", "R4a", "R4b", "R5", "R6a", "R6b", "R7", "R8", "R10", "R11")


def _directory(id: str) -> Path:
    key = {i.lower(): i for i in IDS}.get(str(id).lower())
    if key is None:
        later = " (R9, a real simulator, comes later)" if str(id).upper() == "R9" else ""
        raise ValueError(f"no reference model {id!r}{later}; the reference models are {', '.join(IDS)}")
    return _HERE / key.lower()


def path(id: str) -> str:
    """Return the path of a reference model's spec, ``model.json`` (architecture.md §11; 0060).

    Raises
    ------
    ValueError
        For an id that isn't a reference model's, naming them.

    Examples
    --------
    >>> path("R2").endswith("r2/model.json")
    True
    """
    return str(_directory(id) / "model.json")


def space(id: str) -> dict[str, Any]:
    """Return the model parameter space of a reference model's expected answers, in its JSON form (designs.md)."""
    return json.loads((_directory(id) / "space.json").read_text(encoding="utf-8"))
