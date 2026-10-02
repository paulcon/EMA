"""The workspace's paths (data_model.md §1, Workspace layout; architecture.md §5)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    """Where a workspace keeps its database, its run lock, and its directories, all absolute.

    Attributes
    ----------
    root : str
        The workspace's directory.
    db : str
        ``ema.db``, the database.
    lock : str
        ``run.lock``, held while a process makes runs (data_model.md §10).
    runs : str
        ``runs/``: run directories and batch directories beside them (0020, 0025).
    files : str
        ``files/``: shared model files, ``files/<sha256>/<name>`` (0030).
    results : str
        ``results/``: each diagnostic result's report, PNGs, and data cards (§6).
    """

    root: str
    db: str
    lock: str
    runs: str
    files: str
    results: str

    @classmethod
    def of(cls, root: str | os.PathLike[str]) -> "Layout":
        """Return the layout of the workspace at ``root``, made absolute; nothing is read or created."""
        top = os.path.abspath(os.fspath(root))
        join = os.path.join
        return cls(
            top, join(top, "ema.db"), join(top, "run.lock"), join(top, "runs"), join(top, "files"), join(top, "results")
        )

    def run_dir(self, run_id: str) -> str:
        """Return ``runs/<run id>/``, a run's directory, or a batch call's by its id (0020, 0025).

        Whether it is kept is read from the file system: a directory deleted by hand reads as not kept (§5.6).
        """
        return os.path.join(self.runs, run_id)

    def result_dir(self, result_id: str) -> str:
        """Return ``results/<result id>/``, a diagnostic result's directory (§6)."""
        return os.path.join(self.results, result_id)
