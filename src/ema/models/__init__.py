"""Layer 2: what a model is to EMA, and running it (model_interface.md; architecture.md §5).

Loading (``spec.py``), the model's files (``files.py``), and the children the workspace owns (``processes.py``) are
re-exported here. The execute phase is never imported or re-exported here: only ``ema.runner`` imports
``ema.models.execute`` (AR4). The other phases, the parsers, and the sandbox are imported from their modules.
"""

from ema.models.files import check_files, hash_files, is_within, remove_tree, same_file
from ema.models.processes import ModelProcesses
from ema.models.spec import LoadedModel, load_spec, resolve_program, save_spec, stored_model

__all__ = [
    "LoadedModel",
    "ModelProcesses",
    "check_files",
    "hash_files",
    "is_within",
    "load_spec",
    "remove_tree",
    "resolve_program",
    "same_file",
    "save_spec",
    "stored_model",
]
