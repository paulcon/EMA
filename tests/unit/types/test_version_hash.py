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


def test_pinned_digests():
    """Literal digests, so a change to the canonical JSON, the field order, or a default is caught (review item 8).

    The shape was confirmed independently in the review of step 03 (record 0069, Review round 1)."""
    heat = ModelSpec.from_json(json.dumps(HEAT))
    assert version_hash(heat, FILES) == "4c36c2a8f16e4f16153ba65163ba9804f7eca61fe51c89df29e1d58b13a75176"
    beam = ModelSpec.from_json(json.dumps(BEAM))
    assert version_hash(beam, ()) == "e49d0b5babe2733729e48662a9a2f792a3a98ba5637753a827614eeaa665a3bf"


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
