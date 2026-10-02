"""The model version's hash (data_model.md §3.4; architecture.md §3, identity.py; M3, 0029)."""

import hashlib
import json

from ema.types.identity import TrackedFile, version_hash
from ema.types.model import ModelSpec
from tests.unit.types.test_model_json import BEAM, HEAT, edited

FILES = (
    TrackedFile("solver.cfg", "b" * 64, False),
    TrackedFile("mesh.dat", "a" * 64, True),
    TrackedFile("heat_solver", "c" * 64, False),
)


def test_known_answer():
    """The SHA-256 of the canonical JSON of {"spec": the versioned spec, "files": [[path, sha256, shared], ...]}."""
    spec = ModelSpec.from_json(json.dumps(HEAT))
    expected_text = json.dumps(
        {
            "spec": json.loads(spec.versioned_json()),
            "files": [["heat_solver", "c" * 64, False], ["mesh.dat", "a" * 64, True], ["solver.cfg", "b" * 64, False]],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    assert version_hash(spec, FILES) == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()


def test_files_order_does_not_matter_and_settings_are_not_covered():
    spec = ModelSpec.from_json(json.dumps(HEAT))
    other_settings = ModelSpec.from_json(edited(HEAT, keep="none", timeout_s=1))
    assert version_hash(spec, FILES) == version_hash(other_settings, tuple(reversed(FILES)))


def test_each_part_is_covered():
    spec = ModelSpec.from_json(json.dumps(BEAM))
    base = version_hash(spec, ())
    changed = {
        version_hash(ModelSpec.from_json(edited(BEAM, description="another")), ()),
        version_hash(ModelSpec.from_json(edited(BEAM, env={"OMP_NUM_THREADS": "2"})), ()),
        version_hash(ModelSpec.from_json(edited(BEAM, pass_env=["LM_LICENSE_FILE"])), ()),
        version_hash(spec, (TrackedFile("beam.py", "0" * 64, False),)),
        version_hash(spec, (TrackedFile("beam.py", "1" * 64, False),)),
        version_hash(spec, (TrackedFile("beam.py", "1" * 64, True),)),
    }
    assert base not in changed and len(changed) == 6
