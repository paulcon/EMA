"""The approval id, the reuse key, id arrays, and timestamps (data_model.md §3.2, §3.4; 0054, 0062; record 0070)."""

import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from ema.types.identity import ID_DTYPE, approval_id, batch_call_id, hex_ids, id_array, reuse_key
from ema.types.requests import Request, TestRunRequest
from ema.types.text import parse_timestamp, timestamp_text

MV = "ab" * 32
VERSIONS = {"ema": "2.0.0", "numpy": "2.5.3", "scipy": "1.16.0", "matplotlib": "3.10.0"}


def request(**kw):
    fields = {
        "diagnostic": "scatter",
        "prediction": "y",
        "space": {"a": {"range": [0.0, 1.0], "scale": "linear"}},
        "params": {"n": 200, "seed": 1},
    }
    fields.update(kw)
    return Request(**fields)


class TestIdArrays:
    def test_round_trip_and_dtype(self):
        ids = ["00" * 32, "ff" * 31 + "00", "0123456789abcdef" * 4]
        arr = id_array(ids)
        assert arr.dtype == ID_DTYPE == np.dtype("V32") and arr.shape == (3,)
        assert hex_ids(arr) == tuple(ids)

    def test_trailing_zero_bytes_kept(self):
        """An S32 element would drop them; V32 keeps all 32 bytes (record 0070, item 1)."""
        arr = id_array(["11" * 31 + "00"])
        assert arr[0].tobytes() == bytes.fromhex("11" * 31 + "00")

    def test_refuses_a_non_id(self):
        with pytest.raises(ValueError):
            id_array(["abc"])

    def test_batch_call_id_takes_the_array(self):
        ids = ["0a" * 32, "0b" * 32]
        assert batch_call_id(id_array(ids)) == batch_call_id(ids)


class TestApprovalId:
    def test_bytes_rule(self):
        """§3.4: the SHA-256 of the canonical JSON of the six-key object (0062)."""
        r = request()
        expected = json.dumps(
            {
                "model_version_id": MV,
                "asked_for": "diagnostic_evaluation",
                "request": {
                    "diagnostic": "scatter",
                    "prediction": "y",
                    "space": {"a": {"range": [0.0, 1.0], "scale": "linear"}},
                    "params": {"n": 200, "seed": 1},
                },
                "new": 200,
                "reused": 0,
                "n_before": 3,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        got = approval_id(MV, "diagnostic_evaluation", r, 200, 0, 3)
        assert got == hashlib.sha256(expected.encode("utf-8")).hexdigest()

    def test_test_run(self):
        t = TestRunRequest(point=(1.0, 2.5))
        text = f'{{"asked_for":"test_run","model_version_id":"{MV}","n_before":0,"new":1,'
        text += '"request":{"test_run":{"point":[1.0,2.5]}},"reused":0}'
        assert approval_id(MV, "test_run", t, 1, 0, 0) == hashlib.sha256(text.encode()).hexdigest()

    def test_each_field_changes_it(self):
        base = approval_id(MV, "diagnostic_evaluation", request(), 200, 0, 0)
        assert approval_id(MV, "diagnostic_evaluation", request(), 200, 0, 1) != base
        assert approval_id(MV, "diagnostic_evaluation", request(), 199, 1, 0) != base
        assert approval_id("cd" * 32, "diagnostic_evaluation", request(), 200, 0, 0) != base
        assert approval_id(MV, "diagnostic_evaluation", request(params={"n": 200, "seed": 2}), 200, 0, 0) != base

    @pytest.mark.parametrize(
        ("asked_for", "req"),
        [("test_run", request()), ("diagnostic_evaluation", TestRunRequest(point=(1.0,))), ("other", request())],
    )
    def test_asked_for_must_match_the_request(self, asked_for, req):
        with pytest.raises(ValueError):
            approval_id(MV, asked_for, req, 1, 0, 0)

    def test_negative_counts_refused(self):
        with pytest.raises(ValueError):
            approval_id(MV, "diagnostic_evaluation", request(), -1, 0, 0)


class TestReuseKey:
    def test_canonical_json_of_the_four_keys(self):
        """§3.4, C50: the key is canonical JSON; the result id is its hash."""
        ids = ["0a" * 32, "0b" * 32, "0a" * 32]
        key = reuse_key(MV, request(), ids, VERSIONS)
        assert json.loads(key) == {
            "model_version_id": MV,
            "request": request().canonical(),
            "run_ids": ids,
            "versions": VERSIONS,
        }
        assert key == json.dumps(json.loads(key), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def test_ids_as_array_or_hex_give_one_key(self):
        ids = ["0a" * 32, "0b" * 32]
        assert reuse_key(MV, request(), id_array(ids), VERSIONS) == reuse_key(MV, request(), ids, VERSIONS)

    def test_order_and_versions_matter(self):
        ids = ["0a" * 32, "0b" * 32]
        key = reuse_key(MV, request(), ids, VERSIONS)
        assert reuse_key(MV, request(), ids[::-1], VERSIONS) != key
        assert reuse_key(MV, request(), ids, {**VERSIONS, "numpy": "2.4.0"}) != key

    @pytest.mark.parametrize("versions", [{"ema": "2"}, {**VERSIONS, "pandas": "3"}])
    def test_versions_must_be_the_four(self, versions):
        with pytest.raises(ValueError):
            reuse_key(MV, request(), ["0a" * 32], versions)

    def test_int_and_float_spaces_agree(self):
        """0061: values in model parameter units are doubles before hashing."""
        a = request(space={"a": {"range": [0.0, 1.0], "scale": "linear"}})
        b = request(space={"a": {"range": [0, 1], "scale": "linear"}})
        assert reuse_key(MV, a, ["0a" * 32], VERSIONS) == reuse_key(MV, b, ["0a" * 32], VERSIONS)


class TestTimestamps:
    def test_utc_to_the_millisecond(self):
        """§3.2: ISO 8601 in UTC, to the millisecond: 2026-10-01T14:03:07.123Z."""
        dt = datetime(2026, 10, 1, 14, 3, 7, 123456, tzinfo=UTC)
        assert timestamp_text(dt) == "2026-10-01T14:03:07.123Z"
        assert parse_timestamp("2026-10-01T14:03:07.123Z") == datetime(2026, 10, 1, 14, 3, 7, 123000, tzinfo=UTC)

    def test_other_zones_converted(self):
        dt = datetime(2026, 10, 1, 16, 3, 7, 5000, tzinfo=timezone(timedelta(hours=2)))
        assert timestamp_text(dt) == "2026-10-01T14:03:07.005Z"

    def test_naive_refused(self):
        with pytest.raises(ValueError):
            timestamp_text(datetime(2026, 10, 1))  # noqa: DTZ001

    @pytest.mark.parametrize(
        "text", ["2026-10-01T14:03:07Z", "2026-10-01 14:03:07.123", "2026-10-01T14:03:07.123+00:00"]
    )
    def test_parse_refuses_other_forms(self, text):
        with pytest.raises(ValueError):
            parse_timestamp(text)
