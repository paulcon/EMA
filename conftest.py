"""The test tiers (contracts.md, Test tiers; record 0059, item 4).

The fast tier runs by default. Tests marked ``slow`` run only with ``--slow``. The reference models and the test
models (``tests/models``) are programs and data, with file names that repeat, so pytest never collects them.
"""

import pytest

collect_ignore = ["src/ema/reference_models", "tests/models"]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--slow", action="store_true", default=False, help="also run the slow tier")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: the slow tier (contracts.md); runs only with --slow")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--slow"):
        return
    skip = pytest.mark.skip(reason="slow tier: run with --slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
