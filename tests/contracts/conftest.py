"""Collect the contract modules (architecture.md §9; contracts.md, What a contract is here).

Each module in this directory that isn't a ``test_*.py`` file and doesn't start with ``_`` is one interface's
contract: ``design.py``, ``sampler.py``, and later ``diagnostic.py``, ``basis.py``, ``interval.py``,
``model.py``, ``store.py``, ``workspace.py``, and ``tools.py``. Its ``check_*`` functions are collected as tests,
with its ``test_*`` functions (the meta-test, the toy's own tests), and nothing else is. The checks are only
collected here: a ``check_*`` function imported elsewhere (a later ``ema.models.files.check_files``) is never
collected, since pytest's own patterns stay ``test_*``.

A check takes the implementation as its argument, so it is a test parametrized over the implementations (by a
fixture or ``pytest_generate_tests`` in its module), and can also be called directly with a broken toy (the
meta-test).
"""

from pathlib import Path

import pytest

CHECK_PREFIXES = ("check_", "test_")


class ContractModule(pytest.Module):
    """A contract module: its ``check_*`` and ``test_*`` functions are tests."""

    def funcnamefilter(self, name: str) -> bool:
        return name.startswith(CHECK_PREFIXES)

    def classnamefilter(self, name: str) -> bool:
        return name.startswith("Test")


def is_contract_module(path: Path) -> bool:
    return (
        path.suffix == ".py"
        and path.parent == Path(__file__).parent
        and not path.name.startswith(("_", "test_"))
        and path.name != "conftest.py"
    )


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> pytest.Module | None:
    if is_contract_module(file_path):
        return ContractModule.from_parent(parent, path=file_path)
    return None
