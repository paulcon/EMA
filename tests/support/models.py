"""The test models in ``tests/models`` (contracts.md, the model adapter contract's millisecond models).

- ``python``: a Python function with a listed helper module and a shared file;
- ``batch``: the same function as a batch;
- ``command_line``: a program run by Python, with an input deck and a shared file, read by the JSON parser;
- ``imports``: a function file whose imports resolve to unlisted files (M17), and which writes a marker file when
  imported (T4: loading never imports it).

A test copies a model into a temporary directory before changing or loading it, so nothing is written beside the
originals.
"""

from __future__ import annotations

import shutil
from pathlib import Path

MODELS = Path(__file__).resolve().parent.parent / "models"
KINDS = ("python", "batch", "command_line")


def copy_model(kind: str, directory: Path) -> Path:
    """Copy the test model ``kind`` into ``directory``; return its spec's path."""
    target = directory / kind
    shutil.copytree(MODELS / kind, target)
    return target / "model.json"
