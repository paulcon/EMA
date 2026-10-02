"""Layer 2: what a model is to EMA, and running it (model_interface.md; architecture.md §5).

Loading (``spec.py``) and the model's files (``files.py``) are re-exported here. The execute phase is never
imported or re-exported here: only ``ema.runner`` imports ``ema.models.execute`` (AR4).
"""

from ema.models.files import check_files, hash_files, is_within, same_file
from ema.models.spec import LoadedModel, load_spec, save_spec, stored_model

__all__ = [
    "LoadedModel",
    "check_files",
    "hash_files",
    "is_within",
    "load_spec",
    "same_file",
    "save_spec",
    "stored_model",
]
