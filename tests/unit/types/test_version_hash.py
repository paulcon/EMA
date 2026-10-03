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
    """The SHA-256 of the canonical JSON of {"spec": the versioned spec, "files": [[path, sha256, shared], ...]},
    the spec's ``files`` sorted by path and ``pass_env`` by name (0086 item 4)."""
    spec = ModelSpec.from_json(edited(HEAT, pass_env=["LM_LICENSE_FILE", "A_HOST"]))
    hashed = json.loads(spec.versioned_json())
    hashed["files"] = [hashed["files"][i] for i in (0, 2, 1)]
    hashed["pass_env"] = ["A_HOST", "LM_LICENSE_FILE"]
    expected_text = json.dumps(
        {
            "spec": hashed,
            "files": [["heat_solver", "c" * 64, False], ["mesh.dat", "a" * 64, True], ["solver.cfg", "b" * 64, False]],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    assert version_hash(spec, FILES) == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()


#: HEAT's id with its ``files`` sorted by path, as the code gave it before 0086 item 4. HEAT lists its files out of
#: order, so its id changed from 4c36c2a8… to this one (0086 item 4: only a spec whose lists are out of order).
SORTED_HEAT = "676a44c4cf02c553b7cb85e766dc7a87abe0ee24a5ade59047525d015fd3f4b7"


def test_pinned_digests():
    """Literal digests, so a change to the canonical JSON, the field order, or a default is caught (review item 8).

    The shape was confirmed independently in the review of step 03 (record 0069, Review round 1)."""
    heat = ModelSpec.from_json(json.dumps(HEAT))
    assert version_hash(heat, FILES) == SORTED_HEAT
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


def test_files_and_pass_env_order_does_not_matter():
    """0086 item 4: ``files`` sorted by path and ``pass_env`` by name before hashing."""
    ids = set()
    for files, pass_env in (
        (["heat_solver", "solver.cfg", {"path": "mesh.dat", "shared": True}], ["LM_LICENSE_FILE", "A_HOST"]),
        ([{"path": "mesh.dat", "shared": True}, "solver.cfg", "heat_solver"], ["A_HOST", "LM_LICENSE_FILE"]),
    ):
        ids.add(version_hash(ModelSpec.from_json(edited(HEAT, files=files, pass_env=pass_env)), FILES))
    assert len(ids) == 1


def test_already_sorted_lists_keep_their_id():
    """0086 item 4: the ids below are the ones the code gave before the sort, for lists already in order."""
    files = ["heat_solver", {"path": "mesh.dat", "shared": True}, "solver.cfg"]
    assert version_hash(ModelSpec.from_json(edited(HEAT, files=files)), FILES) == SORTED_HEAT
    both = edited(HEAT, files=files, pass_env=["A_HOST", "LM_LICENSE_FILE"])
    assert (
        version_hash(ModelSpec.from_json(both), FILES)
        == "90f5249b07b70b4705e9365ca02f1f34d88b9a725384154b1da4e14108d71b60"
    )
