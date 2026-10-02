"""Helpers for the workspace's tests (step 14): an approver that records each question, the contract's toy
diagnostic registered for a test, copies of reference models, and a workspace that runs before it asks (C53's
negative control).

The toy (``tests.support.diagnostics.Toy``: a mean and standard deviation with bootstrap intervals on a uniform
design) stands in for scatter wherever a use case only needs "a diagnostic over a space", so the workspace's order
is tested end to end before the other diagnostics are merged (record 0080).
"""

from __future__ import annotations

import math
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ema.reference_models
from ema.diagnostics import base
from ema.types.requests import ApprovalRequest, ConfirmationRequest
from ema.workspace import Workspace, _evaluate
from tests.support.diagnostics import Toy

PI_SPACE = {"x1": (-math.pi, math.pi), "x2": (-math.pi, math.pi), "x3": (-math.pi, math.pi)}


@dataclass
class Asked:
    """An approver that records each question and answers ``answer`` (P3: every question is seen by a test)."""

    answer: bool = True
    questions: list[ApprovalRequest | ConfirmationRequest] = field(default_factory=list)
    runs_dir: Path | None = None
    stored_when_asked: list[int] = field(default_factory=list)

    def __call__(self, question: ApprovalRequest | ConfirmationRequest) -> bool:
        self.questions.append(question)
        if self.runs_dir is not None:  # C53's negative control: how many runs existed when the question came
            self.stored_when_asked.append(len(list(self.runs_dir.iterdir())) if self.runs_dir.exists() else 0)
        return self.answer

    @property
    def prices(self) -> list[str]:
        return [q.price.text for q in self.questions if isinstance(q, ApprovalRequest)]


@contextmanager
def toy_registered() -> Iterator[Toy]:
    """Register the contract's toy diagnostic for the duration of a block."""
    toy = Toy()
    base.register(toy)
    try:
        yield toy
    finally:
        base.unregister(toy.name)


def copy_reference(id: str, directory: Path) -> Path:
    """Copy a reference model's directory, so a test may edit its files; return its spec's path."""
    source = Path(ema.reference_models.path(id)).parent
    target = directory / source.name
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target / "model.json"


def registered(name: str) -> bool:
    """Whether a diagnostic is registered (scatter and the others are built on parallel branches)."""
    return name in base.names()


class RunsBeforeAsking(Workspace):
    """A broken workspace: it makes a diagnostic evaluation's runs with a yes nobody gave, then asks (C53)."""

    def run(self, model: str, diagnostic: str, space: Any = None, *, approve: Any, **kwargs: Any) -> Any:
        prepared = _evaluate.prepare(self._store, model, diagnostic, space, kwargs.get("prediction"),
                                     {k: v for k, v in kwargs.items() if k not in ("prediction", "retry_failed",
                                                                                   "on_progress")})  # fmt: skip
        _evaluate.run(self._store, self._processes, prepared, retry_failed=False, approve=lambda q: True,
                      on_progress=None)  # fmt: skip
        return super().run(model, diagnostic, space, approve=approve, **kwargs)
