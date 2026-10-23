"""Runs, run keys, resolutions, run columns, run batches, and the price (architecture.md §3, runs.py; record 0070).

data_model.md §4.3 (the enumerations), §5.6 and §5.8 (a run's checks; 0043), Q1, Q2, Q7, Q15; C47, C56; U1–U3.
"""

import math
from types import MappingProxyType

import numpy as np
import pytest

from ema.types.design import Design
from ema.types.identity import ID_DTYPE, id_array, point_hash, run_id
from ema.types.runs import FailureKind, Price, Resolution, Run, RunBatch, RunColumns, RunKey, RunStatus

MV = "ab" * 32
ID = "cd" * 32


def make_run(**kw):
    fields = {
        "run_id": ID,
        "model_version_id": MV,
        "point": (1, 2.5),
        "replicate": 0,
        "attempt": 0,
        "status": RunStatus.OK,
        "kind": None,
        "reason": None,
        "stderr_tail": None,
        "exit_code": 0,
        "predictions": {"y": 1.5, "z": None},
        "missing": {"z": "plate.out: pattern not found"},
        "time_s": 0.25,
        "batch_call_id": None,
        "host": "localhost",
        "program": "/usr/bin/python3",
        "approval_id": "ef" * 32,
    }
    fields.update(kw)
    return Run(**fields)


class TestEnums:
    def test_values(self):
        """§4.3: ok, failed; error, timeout, unread."""
        assert [s.value for s in RunStatus] == ["ok", "failed"]
        assert [k.value for k in FailureKind] == ["error", "timeout", "unread"]

    def test_codes_round_trip(self):
        """Record 0070, item 2: a code is the member's index."""
        assert [s.code for s in RunStatus] == [0, 1]
        assert [k.code for k in FailureKind] == [0, 1, 2]
        assert all(RunStatus.from_code(s.code) is s for s in RunStatus)
        assert all(FailureKind.from_code(k.code) is k for k in FailureKind)
        assert FailureKind.from_code(-1) is None

    @pytest.mark.parametrize(("enum", "code"), [(FailureKind, -2), (FailureKind, 3), (RunStatus, -1), (RunStatus, 2)])
    def test_unknown_codes_refused(self, enum, code):
        """Record 0070, item 2 (review round 1): a code no member has is refused, not decoded."""
        with pytest.raises(ValueError):
            enum.from_code(code)


class TestRun:
    def test_point_as_doubles_and_mappings_read_only(self):
        run = make_run()
        assert run.point == (1.0, 2.5) and isinstance(run.point[0], float)
        assert isinstance(run.predictions, MappingProxyType) and isinstance(run.missing, MappingProxyType)
        with pytest.raises(TypeError):
            run.predictions["y"] = 2.0  # type: ignore[index]

    def test_failed_run(self):
        """§5.6: kind and reason null exactly when ok; §5.8: a failed run has no model predictions."""
        run = make_run(
            status=RunStatus.FAILED,
            kind=FailureKind.ERROR,
            reason="exited with code 2",
            exit_code=2,
            predictions={},
            missing={},
        )
        assert run.kind is FailureKind.ERROR

    @pytest.mark.parametrize(
        "kw",
        [
            {"status": RunStatus.FAILED, "predictions": {}, "missing": {}},  # no kind or reason
            {"status": RunStatus.FAILED, "kind": FailureKind.ERROR, "predictions": {}, "missing": {}},  # no reason
            {"kind": FailureKind.ERROR, "reason": "x"},  # ok with a kind
            {"status": RunStatus.FAILED, "kind": FailureKind.ERROR, "reason": "x"},  # failed with predictions
            {"predictions": {"y": None}, "missing": {"y": "not read"}},  # ok with nothing read (0043)
            {"predictions": {"y": 1.0, "z": None}, "missing": {}},  # missing without its reason
            {"predictions": {"y": 1.0}, "missing": {"y": "x"}},  # a reason for a value read
            {"predictions": {"y": math.nan}, "missing": {}},  # NaN is never a value (§3.2)
            {"replicate": -1},
            {"attempt": -1},
            {"time_s": -1.0},
        ],
    )
    def test_refusals(self, kw):
        with pytest.raises(ValueError):
            make_run(**kw)


class TestRunKey:
    def test_make_computes_hash_and_id(self):
        """§3.4: the run id from the model version id, the point hash, the replicate, the attempt."""
        key = RunKey.make(MV, (1, 2.5), 3, 1)
        assert key.point == (1.0, 2.5)
        assert key.point_hash == point_hash([1.0, 2.5])
        assert key.run_id == run_id(MV, point_hash([1.0, 2.5]), 3, 1)
        assert (key.replicate, key.attempt) == (3, 1)

    def test_negative_refused(self):
        with pytest.raises(ValueError):
            RunKey.make(MV, (1.0,), -1, 0)


def design(n=4):
    return Design(
        identity=None, points=np.arange(2.0 * n).reshape(n, 2), replicates=np.zeros(n), levels=None, lines=None
    )


class TestResolution:
    def test_rows_and_keys(self):
        """Q1: a stored row has its run id and key -1; a new row zeros and its key's index."""
        keys = (RunKey.make(MV, (2.0, 3.0), 0, 0), RunKey.make(MV, (6.0, 7.0), 0, 0))
        row_runs = id_array(["0a" * 32, "00" * 32, "0b" * 32, "00" * 32])
        res = Resolution(design(), MV, row_runs, np.array([-1, 0, -1, 1]), keys, reused_failed=1)
        assert res.row_runs.dtype == ID_DTYPE and not res.row_runs.flags.writeable
        assert not res.row_keys.flags.writeable

    @pytest.mark.parametrize(
        ("row_runs", "row_keys"),
        [
            (["0a" * 32] * 3, [-1, -1, -1]),  # wrong length
            (["0a" * 32] * 4, [-1, -1, -1, 2]),  # a key index past new_keys
            (["0a" * 32] * 4, [-1, 0, -1, -1]),  # a new row with a stored id
            (["0a" * 32, "00" * 32, "00" * 32, "0a" * 32], [-1, 0, -1, -1]),  # a stored row with zeros
            (["0a" * 32, "00" * 32, "0b" * 32, "0a" * 32], [-1.0, 0.0, -1.0, -1.0]),  # float keys
        ],
    )
    def test_refusals(self, row_runs, row_keys):
        keys = (RunKey.make(MV, (2.0, 3.0), 0, 0),)
        with pytest.raises(ValueError):
            Resolution(design(), MV, id_array(row_runs), np.array(row_keys), keys, reused_failed=0)


def columns(n=4, **kw):
    fields = {
        "run_ids": id_array([f"{i:02x}" * 32 for i in range(n)]),
        "points": None,
        "replicates": np.zeros(n, dtype=np.int64),
        "status": np.array([0, 0, 1, 0][:n]),
        "kind": np.array([-1, -1, 1, -1][:n]),
        "values": {"y": np.array([1.0, 2.0, np.nan, 4.0][:n]), "z": np.array([1.0, np.nan, np.nan, 3.0][:n])},
        "reasons": {"02" * 32: "timeout after 600 s"},
        "stderr_tails": {},
        "missing": {"z": {"01" * 32: "plate.out: pattern not found"}},
        "time_s": np.ones(n),
        "host": np.array(["h"] * n),
        "program": np.array(["p"] * n),
        "batch_call_ids": np.zeros(n, dtype=ID_DTYPE),
        "approval_ids": id_array(["ef" * 32] * n),
    }
    fields.update(kw)
    return RunColumns(**fields)


class TestRunColumns:
    def test_read_only(self):
        cols = columns()
        for name in ("run_ids", "replicates", "status", "kind", "time_s", "batch_call_ids", "approval_ids"):
            assert not getattr(cols, name).flags.writeable, name
        assert not cols.values["y"].flags.writeable
        assert isinstance(cols.values, MappingProxyType) and isinstance(cols.missing["z"], MappingProxyType)

    @pytest.mark.parametrize(
        "kw",
        [
            {"replicates": np.zeros(3)},
            {"values": {"y": np.ones(3)}},
            {"points": np.zeros((3, 2))},
            {"kind": np.array([-1, 0, 1, -1])},  # an ok run with a kind
            {"run_ids": np.zeros(4)},  # not ids
            {"status": np.array([0, 0, 7, 0]), "kind": np.array([-1, -1, 1, -1])},  # no status 7
            {"kind": np.array([-1, -1, 9, -1])},  # no kind 9
            {"replicates": np.zeros(4)},  # integers, not doubles
            {"replicates": np.array([2**63, 0, 0, 0], dtype=np.uint64)},  # over int64's max (0070, review round 2)
            {"values": {"y": np.array([1.0, 2.0, 3.0, 4.0])}},  # a failed run's value isn't NaN (architecture §3)
        ],
    )
    def test_refusals(self, kw):
        with pytest.raises(ValueError):
            columns(**kw)


def test_arrays_do_not_alias_their_sources():
    """Record 0070, item 8 (review round 1): a source owning its data is made read-only; a writable view copied."""
    run_ids = id_array([f"{i:02x}" * 32 for i in range(4)])
    owner = np.zeros(8)
    cols = columns(run_ids=run_ids, time_s=owner[:4])
    assert not run_ids.flags.writeable and np.shares_memory(cols.run_ids, run_ids)
    owner[0] = 5.0
    assert cols.time_s[0] == 0.0
    shared = columns(run_ids=cols.run_ids)  # a read-only array is shared, not copied
    assert np.shares_memory(shared.run_ids, run_ids)


def test_unsigned_integers_within_int64_are_read():
    """0070, review round 2: a uint64 array is read when its values fit, refused (above) when they don't."""
    cols = columns(replicates=np.array([0, 1, 2, 2**63 - 1], dtype=np.uint64))
    assert cols.replicates.dtype == np.int64 and cols.replicates[-1] == 2**63 - 1


class TestRunBatch:
    def test_usable_and_run_id(self):
        """0022: usable is ok and read, per model prediction."""
        batch = RunBatch(design(), columns(), new=np.array([True, False, True, False]))
        assert batch.usable("y").tolist() == [True, True, False, True]
        assert batch.usable("z").tolist() == [True, False, False, True]
        assert batch.run_id(2) == "02" * 32
        assert not batch.new.flags.writeable

    def test_unknown_prediction(self):
        batch = RunBatch(design(), columns(), new=np.zeros(4, dtype=bool))
        with pytest.raises(KeyError):
            batch.usable("w")

    def test_lengths_must_agree(self):
        with pytest.raises(ValueError):
            RunBatch(design(3), columns(), new=np.zeros(4, dtype=bool))


class TestPrice:
    @pytest.mark.parametrize(
        ("kw", "text"),
        [
            # U1, U2, the guides: the test run's price
            ({"new": 1, "reused": 0, "time_s": None, "from_runs": 0}, "1 new run, 0 reused, time unknown"),
            # architecture.md §3, U2
            (
                {"new": 96, "reused": 1, "time_s": 11_520.0, "from_runs": 1},
                "96 new runs, 1 reused, about 3 h 12 min (from 1 stored run)",
            ),
            (
                {"new": 56, "reused": 41, "time_s": 6720.0, "from_runs": 41},
                "56 new runs, 41 reused, about 1 h 52 min (from 41 stored runs)",
            ),
            # U1's second price
            (
                {"new": 200, "reused": 0, "time_s": 0.2, "from_runs": 1},
                "200 new runs, 0 reused, about 0.2 s (from 1 stored run)",
            ),
            # 0010, C47: reused failed runs counted
            (
                {"new": 100, "reused": 200, "reused_failed": 34, "time_s": 500.0, "from_runs": 200},
                "100 new runs, 200 reused, of which 34 failed, about 8 min (from 200 stored runs)",
            ),
        ],
    )
    def test_text(self, kw, text):
        price = Price.make(**kw)
        assert price.text == text and str(price) == text
        assert price.reused_failed == kw.get("reused_failed", 0)

    @pytest.mark.parametrize(
        "kw",
        [
            {"new": -1, "reused": 0, "time_s": None, "from_runs": 0},
            {"new": 1, "reused": 0, "reused_failed": 1, "time_s": None, "from_runs": 0},
            {"new": 1, "reused": 0, "time_s": 1.0, "from_runs": 0},  # a time from no stored run
            {"new": 1, "reused": 0, "time_s": None, "from_runs": 3},  # stored runs and no time
            {"new": 1, "reused": 0, "time_s": math.inf, "from_runs": 3},
            # Q2 counts every stored run, the reused included (review round 1)
            {"new": 1, "reused": 4, "time_s": 1.0, "from_runs": 3},
            {"new": 1, "reused": 1, "time_s": None, "from_runs": 0},
        ],
    )
    def test_refusals(self, kw):
        with pytest.raises(ValueError):
            Price.make(**kw)
