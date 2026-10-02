"""The model adapter contract (contracts.md, C31–C45), over a Python function, a batch, and a command-line model.

Step 03 writes C33, the model version: M3, and files compared as files (P3, 0029). Its implementation is how a
model is loaded (``load_spec``), run over the three test models in ``tests/models`` (``tests.support.models``);
steps 04 and 05 add the checks that run a model. Three broken toys fail ``check_model_version``: one hashes the
files' paths instead of their contents (contracts.md's negative control), one covers the settings, and one covers
the model's location. ``test_every_check_fails_on_its_broken_toy`` is the meta-test.
"""

from __future__ import annotations

import inspect
import json
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from ema.models.spec import LoadedModel, load_spec
from ema.types.identity import TrackedFile, canonical_json, sha256_hex, version_hash
from tests.support.models import KINDS, copy_model


@dataclass(frozen=True)
class Adapter:
    """One test model, and how it is loaded."""

    kind: str
    load: Callable[[str], LoadedModel] = load_spec


def tracked_names(spec: dict[str, Any]) -> list[str]:
    """The files a spec's model version covers, read from its JSON (model_interface.md, Versions)."""
    names = [spec["function"].rpartition(":")[0]] if "function" in spec else []
    names += [deck["template"] for deck in spec.get("input_decks", [])]
    names += [f if isinstance(f, str) else f["path"] for f in spec.get("files", [])]
    return list(dict.fromkeys(names))


def covered_changes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Specs that differ from ``spec`` in one covered field each (M3, 0029)."""
    out = []

    def changed(edit: Callable[[dict[str, Any]], None]) -> None:
        copy = json.loads(json.dumps(spec))
        edit(copy)
        out.append(copy)

    changed(lambda s: s.update(name=s["name"] + "_2"))
    changed(lambda s: s.update(description=s["description"] + "."))
    changed(lambda s: s["parameters"][0].update(units="km"))
    changed(lambda s: s["parameters"][0].update(nominal=s["parameters"][0]["nominal"] + 0.25))
    changed(lambda s: s["parameters"][0].update(description="another"))
    changed(lambda s: s["parameters"][1].update(limits={"lt": 100}))
    changed(lambda s: s["predictions"][0].update(description="another"))
    changed(lambda s: s["predictions"][0].update(units="km"))
    changed(lambda s: s.update(env={**s.get("env", {}), "X_FLAG": "1"}))
    changed(lambda s: s.update(pass_env=[*s.get("pass_env", []), "X_HOST"]))
    changed(
        lambda s: s.update(
            files=[
                {"path": "mesh.dat", "shared": False} if f == {"path": "mesh.dat", "shared": True} else f
                for f in s["files"]
            ]
        )
    )
    if spec["interface"] == "python_function":
        changed(lambda s: s.update(function="model.py:g"))
        changed(lambda s: s.update(batch=not s.get("batch", False), batch_size=None))
    else:
        changed(lambda s: s.update(command=[*s["command"], "--fast"]))
        changed(lambda s: s["predictions"][0]["parser"].update(key="z"))
    return out


def settings_changes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Specs that differ from ``spec`` only in settings, defaults written out, or key order (M3, 0029)."""
    out = [
        {**spec, "keep": "none"},
        {**spec, "timeout_s": 1},
        {**spec, "noisy": False, "pass_env": spec.get("pass_env", [])},
    ]
    if spec.get("batch"):
        out.append({**spec, "batch_size": 7})
    out.append(dict(reversed(list(spec.items()))))
    return out


def check_model_version(adapter: Any) -> None:
    """C33: M3 (a tracked file's byte, or a covered field, changes the model version; the directory's location,
    ``keep``, ``batch_size``, and ``timeout_s`` don't), and files compared as files (their contents, however the
    spec and the files are reached)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        spec_path = copy_model(adapter.kind, root / "a")
        model_dir = spec_path.parent
        original = json.loads(spec_path.read_text())

        def version(path: Path = spec_path) -> str:
            return adapter.load(str(path)).model_version_id

        base = version()
        assert version() == base, "loading twice gave two model versions"

        shutil.copytree(model_dir, root / "moved")
        assert version(root / "moved" / "model.json") == base, "moving the model's directory changed its version"
        (root / "alias").symlink_to(model_dir)
        assert version(root / "alias" / "model.json") == base, "a link to the directory changed the version"
        assert version(model_dir / ".." / model_dir.name / "model.json") == base
        (root / "elsewhere").mkdir()
        (root / "elsewhere" / "linked.json").symlink_to(spec_path)
        assert version(root / "elsewhere" / "linked.json") == base, "a link to the spec changed the model version"

        for variant in settings_changes(original):
            spec_path.write_text(json.dumps(variant, indent=4))
            assert version() == base, f"a setting or a default changed the model version: {variant}"

        seen = {base}
        for variant in covered_changes(original):
            spec_path.write_text(json.dumps(variant))
            changed = version()
            assert changed not in seen, f"a covered field didn't change the model version: {variant}"
            seen.add(changed)
        spec_path.write_text(json.dumps(original))
        assert version() == base

        for name in tracked_names(original):
            path = model_dir / name
            content = path.read_bytes()
            path.write_bytes(content + b" ")
            changed = version()
            assert changed not in seen, f"one byte changed in {name} didn't change the model version"
            seen.add(changed)
            path.write_bytes(content)
        assert version() == base

        outside = root / "data" / "mesh.dat"
        outside.parent.mkdir()
        shutil.copyfile(model_dir / "mesh.dat", outside)
        (model_dir / "mesh.dat").unlink()
        (model_dir / "mesh.dat").symlink_to(outside)
        assert version() == base, "a link to a file with the same contents changed the model version"
        outside.write_bytes(outside.read_bytes() + b"1")
        assert version() not in seen, "editing a linked file's target didn't change the model version"


# --------------------------------------------------------------------------------------------------------------
# Broken toys


def load_hashing_paths(path: str) -> LoadedModel:
    """Hashes the files' paths, not their contents."""
    model = load_spec(path)
    files = tuple(TrackedFile(f.path, sha256_hex(f.path), f.shared) for f in model.files)
    return replace(model, files=files, model_version_id=version_hash(model.spec, files))


def load_hashing_settings(path: str) -> LoadedModel:
    """Covers ``keep``, ``batch_size``, and ``timeout_s``."""
    model = load_spec(path)
    return replace(model, model_version_id=sha256_hex(model.spec.to_json() + model.model_version_id))


def load_hashing_location(path: str) -> LoadedModel:
    """Covers the model's directory."""
    model = load_spec(path)
    return replace(model, model_version_id=sha256_hex(canonical_json([model.model_dir, model.model_version_id])))


BROKEN: dict[str, list[Any]] = {
    "check_model_version": [
        Adapter("command_line", load_hashing_paths),
        Adapter("python", load_hashing_settings),
        Adapter("batch", load_hashing_location),
    ],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=KINDS)
def adapter(request: pytest.FixtureRequest) -> Adapter:
    return Adapter(request.param)


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str) -> None:
    """The meta-test (contracts.md, Negative controls)."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for broken in BROKEN[check]:
        with pytest.raises(AssertionError):
            CHECKS[check](broken)
