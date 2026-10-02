"""The model versions' children, owned by the workspace and passed to ``execute`` (architecture.md §5; 0026, M9).

One long-lived child per model version, started on its first call (``ema.models.sandbox.Child``). At most
``MAX_CHILDREN`` are kept; the least recently used is stopped first. ``close`` stops them all, and so does the
interpreter's exit, so no child outlives EMA.
"""

import weakref
from collections import OrderedDict

from ema.models.sandbox import Child
from ema.models.spec import LoadedModel
from ema.types.model import PythonFunction

#: Children kept alive at once, one per model version; the least recently used is stopped (as v1's).
MAX_CHILDREN = 4


def _stop(children: "OrderedDict[str, Child]") -> None:
    while children:
        children.popitem()[1].close()


class ModelProcesses:
    """The children of the Python model versions a workspace runs (0026).

    Not frozen; not shared between threads. ``execute`` takes a model version's child from it.
    """

    def __init__(self) -> None:
        self._children: OrderedDict[str, Child] = OrderedDict()
        self._finalizer = weakref.finalize(self, _stop, self._children)

    def child(self, model: LoadedModel) -> Child:
        """Return the model version's child, created (not yet started) when it has none.

        Raises
        ------
        TypeError
            For a model that isn't a Python function.
        """
        interface = model.spec.interface
        if not isinstance(interface, PythonFunction):
            raise TypeError(f"model {model.spec.name} is not a Python function; it has no child")
        key = model.model_version_id
        if key in self._children:
            self._children.move_to_end(key)
            return self._children[key]
        child = self._children[key] = Child(
            model.model_dir,
            interface.function,
            interface.batch,
            tuple(p.name for p in model.spec.parameters),
            tuple(p.name for p in model.spec.predictions),
        )
        while len(self._children) > MAX_CHILDREN:
            self._children.popitem(last=False)[1].close()
        return child

    def close(self) -> None:
        """Stop every model version's child (0026)."""
        _stop(self._children)
