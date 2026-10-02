"""The wheel build (slow tier; record 0059, item 2): ``uv build`` makes a wheel holding ``ema`` and its modules.

The package's data files (``schema.sql``, ``tools.md``, the reference models) are checked here as their steps
add them.
"""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = [
    "ema/__init__.py",
    "ema/types/__init__.py",
    "ema/types/errors.py",
    "ema/types/text.py",
    "ema/types/streams.py",
    "ema/types/identity.py",
    "ema/types/model.py",
    "ema/types/space.py",
    "ema/types/design.py",
    "ema/designs/__init__.py",
    "ema/designs/samplers.py",
    "ema/designs/generators.py",
    "ema/designs/point.py",
    "ema/designs/uniform.py",
    "ema/designs/convergent.py",
    "ema/designs/lines.py",
]
#: The store (step 06): its modules, and its schema as package data (data_model.md §10).
MODULES += [
    "ema/store/__init__.py",
    "ema/store/schema.sql",
    "ema/store/records.py",
    "ema/store/layout.py",
    "ema/store/lock.py",
    "ema/store/migrations.py",
    "ema/store/store.py",
]
#: The runner and approval (step 07).
MODULES += ["ema/runner.py", "ema/approval.py"]


@pytest.mark.slow
def test_the_wheel_holds_ema_and_its_modules(tmp_path):
    uv = shutil.which("uv")
    assert uv, "uv is not on PATH"
    subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path), str(ROOT)], check=True, capture_output=True, text=True
    )
    (wheel,) = tmp_path.glob("ema-*.whl")
    names = set(zipfile.ZipFile(wheel).namelist())
    missing = [m for m in MODULES if m not in names]
    assert not missing, f"not in the wheel: {missing}"
    assert any(n.endswith(".dist-info/licenses/LICENSE") for n in names), "the license is not in the wheel"
    assert not any(n.startswith(("tests/", "docs/")) for n in names)
