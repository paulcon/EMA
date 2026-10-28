"""The diagnostics and their shared precheck (layer 3b; architecture.md §6; diagnostics/shared.md).

``base`` holds the interface, the diagnostic parameters, the registry, and ``evaluate``. Every other public module
in this package is one diagnostic, which registers itself when imported; importing the package imports each of them
(record 0075 item 1), so adding a diagnostic is one module, and nothing else to edit.
"""

import importlib
import pkgutil

from ema.diagnostics import base

for _module in pkgutil.iter_modules(__path__):
    if not _module.name.startswith("_") and _module.name != "base":
        importlib.import_module(f"{__name__}.{_module.name}")

__all__ = ["base"]
