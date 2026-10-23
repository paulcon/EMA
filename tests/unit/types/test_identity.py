"""Canonical JSON, the point hash, the run id, the batch call id, and alpha (data_model.md §3.4; 0047, 0061)."""

import hashlib
import json
import math
import struct
from fractions import Fraction

import numpy as np
import pytest

from ema.types.identity import (
    TrackedFile,
    batch_call_id,
    canonical_json,
    decimal_fraction,
    model_version_label,
    point_hash,
    run_id,
    sha256_hex,
)


class TestCanonicalJson:
    def test_sorted_keys_and_compact(self):
        assert canonical_json({"b": 1, "a": [1.5, None, True], "c": {"z": "x", "y": 2}}) == (
            '{"a":[1.5,null,true],"b":1,"c":{"y":2,"z":"x"}}'
        )

    def test_non_ascii_kept(self):
        assert canonical_json({"name": "Ω≈α"}) == '{"name":"Ω≈α"}'

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_nan_and_infinity_refused(self, bad):
        with pytest.raises(ValueError):
            canonical_json({"x": bad})

    @pytest.mark.parametrize("x", [-0.0, 5e-324, 2.2250738585072014e-308 / 3, 0.1, 1e300, 45.0])
    def test_doubles_round_trip_bit_for_bit(self, x):
        back = json.loads(canonical_json([x]))[0]
        assert struct.pack("<d", back) == struct.pack("<d", x)

    def test_integers_stay_integers(self):
        assert canonical_json({"n": 45, "x": 45.0}) == '{"n":45,"x":45.0}'

    def test_tuples_as_lists(self):
        assert canonical_json((1, (2.0, "a"))) == '[1,[2.0,"a"]]'


def test_sha256_hex_of_text_is_of_its_utf8():
    assert sha256_hex("Ω") == hashlib.sha256("Ω".encode()).hexdigest()
    assert sha256_hex(b"\x00\x01") == hashlib.sha256(b"\x00\x01").hexdigest()


class TestPointHash:
    def test_little_endian_doubles(self):
        point = [1.0, -2.5, 1e-300]
        assert point_hash(point) == hashlib.sha256(struct.pack("<3d", *point)).hexdigest()
        assert point_hash(np.array(point)) == point_hash(point)

    def test_eight_bytes_per_double(self):
        assert point_hash([0.5] * 7) == hashlib.sha256(struct.pack("<7d", *[0.5] * 7)).hexdigest()

    def test_negative_zero_is_another_point(self):
        assert point_hash([0.0, 1.0]) != point_hash([-0.0, 1.0])

    def test_big_endian_input_hashes_the_same(self):
        assert point_hash(np.array([1.5, 2.5], dtype=">f8")) == point_hash([1.5, 2.5])


class TestRunId:
    def test_bytes(self):
        mv, ph = "ab" * 32, point_hash([1.0])
        expected = hashlib.sha256(mv.encode() + ph.encode() + struct.pack("<q", 3) + struct.pack("<q", 1))
        assert run_id(mv, ph, 3, 1) == expected.hexdigest()

    def test_replicate_and_attempt_matter(self):
        mv, ph = "ab" * 32, point_hash([1.0])
        assert len({run_id(mv, ph, 0, 0), run_id(mv, ph, 1, 0), run_id(mv, ph, 0, 1)}) == 3

    def test_negative_counts_refused(self):
        with pytest.raises(ValueError):
            run_id("ab" * 32, point_hash([1.0]), -1, 0)


class TestBatchCallId:
    ids = tuple(sha256_hex(str(i)) for i in range(3))

    def test_hex_text_concatenated(self):
        assert batch_call_id(self.ids) == hashlib.sha256("".join(self.ids).encode()).hexdigest()

    def test_bytes_and_hex_hash_the_same(self):
        raw = [bytes.fromhex(i) for i in self.ids]
        as_rows = np.array([list(r) for r in raw], dtype=np.uint8)
        as_fixed = np.array(raw, dtype="S32")
        assert batch_call_id(raw) == batch_call_id(self.ids)
        assert batch_call_id(as_rows) == batch_call_id(self.ids)
        assert batch_call_id(as_fixed) == batch_call_id(self.ids)
        assert batch_call_id(np.array(self.ids)) == batch_call_id(self.ids)

    def test_trailing_zero_bytes_kept(self):
        trailing = "ab" * 31 + "00"
        assert batch_call_id(np.array([bytes.fromhex(trailing)], dtype="S32")) == batch_call_id([trailing])

    def test_order_matters(self):
        assert batch_call_id(self.ids) != batch_call_id(self.ids[::-1])

    def test_not_an_id_refused(self):
        with pytest.raises(ValueError):
            batch_call_id(["xyz"])


class TestDecimalFraction:
    def test_float_is_its_shortest_decimal(self):
        assert decimal_fraction(0.7072) == Fraction(7072, 10000)
        assert decimal_fraction(0.1) == Fraction(1, 10)

    def test_text_is_read_exactly(self):
        assert decimal_fraction("0.9") == Fraction(9, 10)
        assert decimal_fraction("0.70710678") == Fraction(70710678, 10**8)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, "abc", True])
    def test_refused(self, bad):
        with pytest.raises((ValueError, TypeError)):
            decimal_fraction(bad)


def test_model_version_label():
    assert model_version_label("heat", "b204" + "0" * 60) == "heat@b20400000000"


def test_tracked_file():
    f = TrackedFile(path="dir/a.py", sha256="0" * 64, shared=False)
    assert f.path == "dir/a.py" and not f.shared
