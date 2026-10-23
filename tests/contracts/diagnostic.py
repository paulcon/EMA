"""The diagnostic contract: C1-C19 (contracts.md, Diagnostic contract), over every registered diagnostic and the toy.

Each check runs on run batches built directly (contracts.md, The contract model; ``tests/support/diagnostics.py``),
through ``ema.diagnostics.base.evaluate``, as the workspace calls it. The toy (``Toy``) keeps every promise; each
check has at least one broken toy, which differs from it in one way and fails that check (the meta-test, with the
failure it must give). C7 also repeats each diagnostic's compute with its input arrays at 8 memory offsets and
numpy's small-block cache emptied (record 0068 item 1; P4).

The checks that read only numbers and notes run the diagnostic without its figures (``NoFigures``); C1, C7, C11,
and C12 draw them. The checks that don't test the intervals themselves (C2-C6, C10, C16, C17, and C7's recomputations
at memory offsets) give a diagnostic with intervals the lean fake (``LEAN``: 25 resamples of its own estimators, the
range; record 0084, Review round 1); C1, C7's two evaluations, C8, C9, C11, C12, and C18 keep the registry's
bootstrap.
"""

from __future__ import annotations

import contextlib
import copy
import dataclasses
import inspect
import json
import math
import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest

from ema.designs import generators
from ema.designs.uniform import Uniform
from ema.diagnostics import base
from ema.diagnostics.base import Computation, Transform
from ema.numerics import intervals
from ema.report import EXPLAIN_INTERVALS, render
from ema.types.identity import hex_ids, sha256_hex
from ema.types.results import DiagnosticResult, Estimate, MeasuredNoisy, Note, Observation, ObservationTable
from ema.types.runs import FailureKind, RunBatch, RunStatus
from ema.types.text import fmt
from tests.support import diagnostics as sd
from tests.support.diagnostics import NoFigures, Toy
from tests.support.fakes import FakeIntervalMethod, LeanIntervalMethod, registered_interval_method
from tests.support.numerics import OFFSETS, scramble_heap

#: contracts.md, Named constants.
UNITS_SCALES = (2.0**-40, 2.0**40)
UNITS_RTOL = 1e-9
UNITS_LOG_TOL = 1e-12
RATE_SHIFT_TOL = 1e-5
OFFSET_RTOL = 1e-6
ROUNDING_WIGGLE = 1e-15
#: One evaluation at d = 20 with the defaults, wall-clock. The polynomial model's, both refits per resample (as drawn,
#: and on distinct runs for LOO), took 91 s of CPU (62 s wall) at a load average of 5-9 on 8 cores: twice that
#: (record 0079 item 17, Review round 1; contracts.md's 60 s counted the refits as drawn only).
D20_SECONDS = 180.0
#: Under y + b, a number in y's units can't be closer than the rounding the shift itself makes: a few units in the
#: last place of |b| + max|y| (record 0075 item 14). Far below UNITS_RTOL·range but for the point run's fixture.
SHIFT_ULPS = 16
#: C6's one exemption (contracts.md, C6; 0061): the point run's fixture replicates differ in their last bits, which
#: the offset merges; C5 still holds for it. Any other diagnostic whose values the offset merges fails C6.
C6_EXEMPT = ("point_run",)
#: C6's numbers left out as computed through a logarithm (contracts.md, C6: "the observations that a cutoff at a
#: fraction of a line's range decides"): lines' k* and rates (record 0077 items 4, 15; Review round 1). Any other
#: diagnostic that declares a number through a logarithm fails C6 until it is named here.
C6_LOG_SKIP = ("coordinate_lines", "lines")
#: C10's other label form, "Of the n runs at the point" (contracts.md, C10): the point run's only.
C10_RUNS_LABEL = ("point_run",)

#: The lean interval method of the checks that don't test the intervals (record 0084, Review round 1).
LEAN = LeanIntervalMethod()

KINDS = [FailureKind.ERROR, FailureKind.TIMEOUT, FailureKind.UNREAD]
REASONS = [f"exited with code {i}" for i in range(1, 8)]


# --------------------------------------------------------------------------------------------------------------
# Helpers


def masks(case: sd.Case) -> dict[str, np.ndarray]:
    """contracts.md, Degenerate cases: every 7th run; a contiguous block (the middle quarter of the first varied
    model parameter's range, or of the replicates); one end (its top 30%)."""
    u = case.first_varied
    rows = np.arange(len(case.design))
    return {"random": rows % 7 == 0, "block": np.abs(u) <= 0.25, "end": u > 0.4}


def run(diagnostic: Any, out: Path, **kw: Any) -> tuple[sd.Case, RunBatch, DiagnosticResult]:
    """Prepare, build the batch, and evaluate (``run_in``), without the directory."""
    return run_in(diagnostic, out, **kw)[:3]


def run_in(
    diagnostic: Any,
    out: Path,
    *,
    d: int = 3,
    figures: bool = False,
    params: dict[str, Any] | None = None,
    prediction: str = "y",
    measured_noisy: tuple[MeasuredNoisy, ...] = (),
    interval_method: Any = None,
    lean: bool = False,
    **batch: Any,
) -> tuple[sd.Case, RunBatch, DiagnosticResult, Path]:
    """Prepare, build the batch, and evaluate, into a fresh directory under ``out``, which it returns.

    With ``lean``, a diagnostic with intervals gets ``LEAN`` in place of its registered method (record 0084)."""
    target = diagnostic if figures else NoFigures(diagnostic)
    if lean and interval_method is None and diagnostic.interval_method is not None:
        interval_method = LEAN
    case = sd.prepare(
        target, d, params=params, prediction=prediction, measured_noisy=measured_noisy, interval_method=interval_method
    )
    made = sd.batch(case, **{k: (v(case) if callable(v) else v) for k, v in batch.items()})
    directory = out / f"r{len(list(out.iterdir())) if out.exists() else 0}"
    return case, made, sd.evaluate(case, made, directory), directory


def numbers(result: DiagnosticResult) -> list[tuple[str, Any]]:
    """Every estimate (value and interval) and observation, with where it is; a run's kind left out."""
    found: list[tuple[str, Any]] = []
    for t in result.estimates:
        for i, e in enumerate(t.estimates):
            found.append((f"{t.key}/{i}/{e.key}", (e.value, e.interval)))
    for t in result.observations:
        for r, row in enumerate(t.rows):
            for i, o in enumerate(row):
                if o.key != "kind":
                    found.append((f"{t.key}/{r}/{i}/{o.key}", o.value))
    return found


def codes(result: DiagnosticResult) -> list[str]:
    return [n.code for n in result.notes]


#: A number in a note's text, or a 12-hex-digit id (contracts.md, C5: "the same notes").
_NOTE_VALUE = re.compile(r"\b[0-9a-f]{12}\b|-?\d+(?:\.\d+)?(?:e[+-]\d+)?")


def same_notes(result: DiagnosticResult) -> list[tuple[str, str]]:
    """Each note's code and its text with its numbers and ids left out: C5's "the same notes" (record 0075, Review
    round 1: a number in a note is printed to 4 digits, so its value in y's units isn't compared here)."""
    return [(n.code, _NOTE_VALUE.sub("#", n.text)) for n in result.notes]


def usable_y(run_batch: RunBatch, prediction: str = "y") -> np.ndarray:
    return run_batch.runs.values[prediction][run_batch.usable(prediction)]


def kind_text(run_batch: RunBatch, row: int, prediction: str = "y") -> str | None:
    """A row's run as a cell that reports its kind shows it (point_run.md): "failed (error)", "missing", or None."""
    if run_batch.runs.status[row] == RunStatus.FAILED.code:
        return f"failed ({FailureKind.from_code(int(run_batch.runs.kind[row])).value})"  # type: ignore[union-attr]
    return None if run_batch.usable(prediction)[row] else "missing"


def expected(value: float, transform: Transform, a: float, b: float) -> float | None:
    """A number under y -> a·y + b, as declared; None where the declaration says nothing (a·y only, under a shift)."""
    if transform is Transform.UNCHANGED:
        return value
    if transform is Transform.SCALED:
        return a * value
    if transform is Transform.AFFINE:
        return a * value + b
    return value if b == 0 else None


def assert_transformed(
    diagnostic: Any,
    got: DiagnosticResult,
    ref: DiagnosticResult,
    a: float,
    b: float,
    tol: Callable[..., float],
    *,
    skip_log: bool = False,
) -> None:
    """Each estimate (and its interval) and observation of ``got`` is ``ref``'s transformed as declared, within
    ``tol(transform, through_log, value)``; with ``skip_log``, a number declared through a logarithm is left out (C6:
    lines' rates and their k*, decided at a cutoff of a line's range; record 0077)."""
    assert [t.key for t in got.estimates] == [t.key for t in ref.estimates], "other estimates tables"
    assert [t.key for t in got.observations] == [t.key for t in ref.observations], "other observations tables"

    def same(where: str, v: Any, w: Any, transform: Transform, log: bool) -> None:
        if skip_log and log:
            assert diagnostic.name in C6_LOG_SKIP, f"{where}: C6 skips a number through a logarithm of lines' only"
            return
        if isinstance(w, str) or isinstance(v, str):
            assert v == w, f"{where}: {v!r}, not {w!r}"
            return
        want = expected(float(w), transform, a, b)
        if want is None:
            return
        if isinstance(w, int) and transform is Transform.UNCHANGED:
            assert v == w, f"{where}: {v}, not {w}"
            return
        limit = tol(transform, log, want)
        assert abs(float(v) - want) <= limit, f"{where} ({transform.value}): {v!r}, expected {want!r} within {limit:g}"

    for tg, tr in zip(got.estimates, ref.estimates, strict=True):
        assert len(tg.estimates) == len(tr.estimates)
        for eg, er in zip(tg.estimates, tr.estimates, strict=True):
            transform, log = diagnostic.transform(tr.key, er.key)
            same(f"{tr.key}/{er.key}", eg.value, er.value, transform, log)
            assert (eg.interval is None) == (er.interval is None), f"{er.key}: an interval appeared or went"
            if eg.interval is not None and er.interval is not None:
                for vg, vr in zip(eg.interval, er.interval, strict=True):
                    same(f"{tr.key}/{er.key} interval", vg, vr, transform, log)
    for tg, tr in zip(got.observations, ref.observations, strict=True):
        assert len(tg.rows) == len(tr.rows), f"{tr.key}: other rows"
        for rg, rr in zip(tg.rows, tr.rows, strict=True):
            for og, orr in zip(rg, rr, strict=True):
                transform, log = diagnostic.transform(tr.key, orr.key)
                same(f"{tr.key}/{orr.label}", og.value, orr.value, transform, log)


def shift_tolerance(a: float, b: float, y_range: float, top: float) -> Callable[..., float]:
    """C5 under y + b: UNITS_RTOL relative to a·range in y's units (and the shift's own rounding), absolute
    when dimensionless; RATE_SHIFT_TOL for a number computed through a logarithm."""

    def tol(transform: Transform, log: bool, value: float) -> float:
        if log:
            return RATE_SHIFT_TOL
        if transform is Transform.UNCHANGED:
            return UNITS_RTOL
        return UNITS_RTOL * a * y_range + SHIFT_ULPS * np.finfo(float).eps * (abs(b) + a * top)

    return tol


def exact(transform: Transform, log: bool, value: float) -> float:
    """C5 under a power of 2: bit for bit, but a number computed through a logarithm."""
    return UNITS_LOG_TOL * max(abs(value), 1.0) if log else 0.0


def sections(report: str) -> list[str]:
    return [line[3:] for line in report.split("\n") if line.startswith("## ")]


def note(result: DiagnosticResult, code: str) -> str:
    texts = [n.text for n in result.notes if n.code == code]
    assert len(texts) == 1, f"{len(texts)} notes {code}, not 1: {codes(result)}"
    return texts[0]


def every(diagnostic: Any) -> list[Any]:
    """The registered diagnostics and the toy (C8's tags are unique among them)."""
    return [base.get(name) for name in base.names()] + [Toy()]


class Spy(FakeIntervalMethod):
    """The fake interval method (V7), counting its calls."""

    def __init__(self) -> None:
        self.calls = 0

    def intervals(self, *args: Any, **kwargs: Any) -> dict[str, tuple[Any, ...]]:
        self.calls += 1
        return super().intervals(*args, **kwargs)


# --------------------------------------------------------------------------------------------------------------
# The checks


def check_all_failed(diagnostic: Any, tmp_path: Path) -> None:
    """C1: with every run failed, of each kind: the counts by kind and the note; no estimates and no observations;
    the report has its sections (C11)."""
    for kind in KINDS:  # the figures drawn once: they cost about 0.1 s each
        case, _made, result = run(diagnostic, tmp_path, figures=kind is KINDS[0],
                                 failed=lambda c: np.ones(len(c.design), bool), kinds=[kind])  # fmt: skip
        assert result.counts.failed[kind] == result.counts.runs and result.counts.usable == 0
        assert "not_usable" in codes(result) and "all_failed" in codes(result), codes(result)
        assert not result.estimates and not result.observations, "estimates or observations of no usable run"
        found = sections(render(result, case.spec))
        assert "Estimates" not in found and "Observations" not in found and found[0] == "Notes", found


def check_partial_failures(diagnostic: Any, tmp_path: Path) -> None:
    """C2: failures at random, in a block, at one end, and z missing where y is read: the counts by kind; the note
    with at most 5 reasons (S7); nothing from the usable runs changes when a run that isn't usable changes (its kind,
    reason, or other model predictions), nor do the runs that aren't usable move a number under a shift of the
    usable ones; a cell that reports a run's kind shows the new kind."""
    for name, mask in masks(sd.prepare(diagnostic)).items():
        case, made, first = run(diagnostic, tmp_path, lean=True, failed=mask, kinds=KINDS, reasons=REASONS)
        _, firsts = np.unique(made.runs.run_ids, return_index=True)  # distinct runs: a shared anchor is one (0077)
        failed_kinds = made.runs.kind[firsts]
        for kind in FailureKind:
            assert first.counts.failed[kind] == int((failed_kinds == kind.code).sum()), f"{name}: counts of {kind}"
        text = note(first, "not_usable")
        listed = text.split("Most frequent reasons:\n", 1)[1].split("\n")[:-1]
        assert 1 <= len(listed) <= base.NOTE_MAX_REASONS + 1, f"{name}: {len(listed)} reason lines"
        assert all(line.split(None, 1)[1] in REASONS or "other reasons" in line for line in listed), listed
        y = case.f()
        shift = 3.0 * float(np.max(np.abs(y[~mask])))
        _, _shifted_batch, shifted = run(diagnostic, tmp_path, lean=True, y=y + shift, failed=mask, kinds=KINDS)
        usable = usable_y(made)
        tol = shift_tolerance(1.0, shift, float(np.ptp(usable)), float(np.max(np.abs(usable))))
        assert_transformed(diagnostic, shifted, first, 1.0, shift, tol)
        if name != "random":
            continue  # the runs that aren't usable changed, on one mask: four more evaluations each
        _, other, second = run(
            diagnostic, tmp_path, lean=True, failed=mask, kinds=KINDS[::-1], reasons=REASONS[3:] + ["x"]
        )
        assert numbers(second) == numbers(first), f"{name}: a failed run's kind or reason moved a number"
        shown = [o.value for t in second.observations for row in t.rows for o in row if o.key == "kind"]
        if shown:  # the point run's Replicate 0 row (point_run.md): its run's new kind, exactly (record 0075, m3)
            row0 = int(np.flatnonzero(other.design.replicates == 0)[0])
            assert kind_text(made, row0) != kind_text(other, row0), "the fixture didn't change replicate 0's kind"
            assert shown == [kind_text(other, row0)], f"{name}: {shown}, not replicate 0's new kind"
        _, _, missing = run(diagnostic, tmp_path, lean=True, missing_y=mask)
        assert numbers(missing) == numbers(first), f"{name}: an ok run missing y moved a number"
        _, _, other_z = run(diagnostic, tmp_path, lean=True, missing_y=mask, z=lambda c: 1000.0 * c.f() + 5.0)
        assert numbers(other_z) == numbers(missing), f"{name}: z of a run missing y moved a number"
    case, made, z = run(diagnostic, tmp_path, lean=True, prediction="z")
    _, firsts = np.unique(made.runs.run_ids, return_index=True)  # counted over distinct runs (0077)
    usable_z = int(made.usable("z")[firsts].sum())
    want = int((made.runs.status[firsts] == RunStatus.OK.code).sum()) - usable_z
    assert z.counts.missing == want and z.counts.usable == usable_z, "z's missing runs"


def check_minimum(diagnostic: Any, tmp_path: Path) -> None:
    """C3: one below the declared minimum: counts, the note naming it, no estimates (C1's case when it is 1); at it:
    estimates, or the observations of a diagnostic with none."""
    case = sd.prepare(diagnostic)
    minimum, _why = diagnostic.min_runs(len(case.ctx.space.varied(case.spec)), case.request.params)
    ids = sd.batch(case).runs.run_ids
    _, firsts = np.unique(ids, return_index=True)
    order = ids[np.sort(firsts)]
    for k in (minimum - 1, minimum):
        _, _, result = run(diagnostic, tmp_path, lean=True, failed=~np.isin(ids, order[:k]))
        assert result.counts.usable == k
        if k < minimum:
            assert not result.estimates, f"estimates from {k} usable runs, below the minimum {minimum}"
            if k == 0:
                assert "all_failed" in codes(result)
            else:
                assert f"needs at least {minimum}" in note(result, "too_few")
        elif diagnostic.has_estimates:
            assert result.estimates, f"no estimates at the minimum {minimum}"
        else:
            assert result.observations, f"no observations at the minimum {minimum}"


def check_constant(diagnostic: Any, tmp_path: Path) -> None:
    """C4: the same double in every usable run: the constant note (not the point run's, PT6), the shared observations,
    no estimates; constant to rounding (10⁻¹⁵ relative): no constant note, and estimates (or observations)."""
    _, _, constant = run(diagnostic, tmp_path, lean=True, y=lambda c: np.full(len(c.design), 7.0))
    assert not constant.estimates
    assert ("constant" in codes(constant)) == diagnostic.constant_note, codes(constant)
    assert constant.observations and constant.observations[0].key == "shared"
    _, _, wiggle = run(diagnostic, tmp_path, lean=True, y=lambda c: 7.0 * (1.0 + ROUNDING_WIGGLE * c.f()))
    assert "constant" not in codes(wiggle), "constant to rounding is not constant (0035)"
    assert wiggle.estimates if diagnostic.has_estimates else wiggle.observations


def check_units(diagnostic: Any, tmp_path: Path) -> None:
    """C5: y -> a·y (a = 2⁻⁴⁰, 2⁴⁰) bit for bit, and y -> y + b (b = 3·max|y|) within UNITS_RTOL: notes, counts, and
    usable runs unchanged; each number transformed as declared."""
    case, made, ref = run(diagnostic, tmp_path, lean=True)
    y = case.f()
    for a in UNITS_SCALES:
        _, _, got = run(diagnostic, tmp_path, lean=True, y=a * y)
        assert same_notes(got) == same_notes(ref) and got.counts == ref.counts, f"a = {a}: other notes or counts"
        assert_transformed(diagnostic, got, ref, a, 0.0, exact)
    usable = usable_y(made)
    shift = 3.0 * float(np.max(np.abs(usable)))
    _, _, got = run(diagnostic, tmp_path, lean=True, y=y + shift)
    assert same_notes(got) == same_notes(ref) and got.counts == ref.counts, "a shift changed the notes or counts"
    tol = shift_tolerance(1.0, shift, float(np.ptp(usable)), float(np.max(np.abs(usable))))
    assert_transformed(diagnostic, got, ref, 1.0, shift, tol)


def check_large_offset(diagnostic: Any, tmp_path: Path) -> None:
    """C6: 10⁶ + 10⁻³·f: no constant note, and each number equals f's transformed, within OFFSET_RTOL of the range
    (absolute when dimensionless); but the relative spread, the numbers a cutoff at a fraction of a line's range
    decides (lines' k* and rates, declared through a logarithm; record 0077), and a fixture whose distinct values the
    offset merges (the point run's, 0061)."""
    case, made, ref = run(diagnostic, tmp_path, lean=True)
    y = case.f()
    offset = 1e6 + 1e-3 * y
    usable = made.usable("y")
    if len(np.unique(offset[usable])) < len(np.unique(y[usable])):
        assert diagnostic.name in C6_EXEMPT, f"{diagnostic.name}'s fixture: the offset merges its distinct values"
        pytest.skip(f"C6: the offset merges {diagnostic.name}'s fixture's distinct values (contracts.md, C6; 0061)")
    _, _, got = run(diagnostic, tmp_path, lean=True, y=offset)
    assert "constant" not in codes(got)
    y_range = float(np.ptp(offset[usable]))

    def tol(transform: Transform, log: bool, value: float) -> float:
        return OFFSET_RTOL if transform is Transform.UNCHANGED else OFFSET_RTOL * y_range

    assert_transformed(diagnostic, got, ref, 1e-3, 1e6, tol, skip_log=True)


def check_deterministic(diagnostic: Any, tmp_path: Path) -> None:
    """C7: the same request and batch give an identical result, byte-identical data cards and report; and the same
    computation with the input arrays at 8 memory offsets and the heap scrambled (record 0068 item 1; P4)."""
    case = sd.prepare(diagnostic)
    made = sd.batch(case, failed=masks(case)["random"], kinds=KINDS)
    one = sd.evaluate(case, made, tmp_path / "one")
    two = sd.evaluate(case, made, tmp_path / "two")
    assert one.to_json() == two.to_json(), "two evaluations of one batch differ"
    assert render(one, case.spec) == render(two, case.spec)
    for figure in one.figures:
        assert (tmp_path / "one" / figure.card).read_bytes() == (tmp_path / "two" / figure.card).read_bytes()
    lean = dataclasses.replace(case.ctx, interval_method=LEAN) if diagnostic.interval_method else case.ctx  # 0084
    first = repr(diagnostic.compute(made, lean, estimates_allowed=True))
    for offset in OFFSETS:
        keep: list[Any] = []
        placed = sd.batch_at_offset(made, offset, keep)
        scramble_heap(offset, keep)
        assert repr(diagnostic.compute(placed, lean, estimates_allowed=True)) == first, f"offset {offset}"


def check_spawn_tag(diagnostic: Any, tmp_path: Path) -> None:
    """C8: spawn tags >= 2³², unique among the diagnostics, recorded; another tag moves the intervals and not the
    design; with no tag, another seed on the same batch gives the same numbers."""
    tags = [t for d in every(diagnostic) for t in d.spawn_tags]
    assert len(tags) == len(set(tags)), "two diagnostics share a spawn tag"
    assert all(base.SPAWN_TAG_BASE <= t < 2**64 for t in diagnostic.spawn_tags)
    case, made, ref = run(diagnostic, tmp_path)
    assert ref.provenance.spawn_tags == tuple(diagnostic.spawn_tags)
    if diagnostic.spawn_tags:
        moved = copy.copy(diagnostic)
        moved.spawn_tags = tuple(t + 1000 for t in diagnostic.spawn_tags)
        other = sd.prepare(NoFigures(moved))
        assert np.array_equal(other.design.points, case.design.points), "a spawn tag moved the design"
        got = sd.evaluate(other, made, tmp_path / "moved")
        intervals_of = [[e.interval for e in t.estimates] for t in ref.estimates]
        assert intervals_of != [[e.interval for e in t.estimates] for t in got.estimates], "another tag, same draws"
    else:
        seed = int(case.request.params["seed"])
        other = sd.prepare(NoFigures(diagnostic), params={"seed": seed + 1})
        got = sd.evaluate(other, made, tmp_path / "seed")
        assert numbers(got) == numbers(ref), "a diagnostic with no draws of its own changed with the seed"


def check_never_empty(diagnostic: Any, tmp_path: Path) -> None:
    """C9: every degenerate case gives an estimate, an observation, or a note; a diagnostic that promises estimates
    gives estimates or a note."""
    cases: dict[str, dict[str, Any]] = {
        "ordinary": {},
        "all failed": {"failed": lambda c: np.ones(len(c.design), bool)},
        "one usable": {"failed": lambda c: np.arange(len(c.design)) > 0},
        "constant": {"y": lambda c: np.full(len(c.design), 7.0)},
        "rounding": {"y": lambda c: 7.0 * (1.0 + ROUNDING_WIGGLE * c.f())},
        "z nowhere": {"prediction": "z", "z": lambda c: np.full(len(c.design), np.nan)},
        **{name: {"failed": (lambda c, n=name: masks(c)[n])} for name in ("random", "block", "end")},
    }
    for name, kw in cases.items():
        _, _, result = run(diagnostic, tmp_path, **kw)
        assert result.estimates or result.observations or result.notes, f"{name}: an empty result"
        if diagnostic.has_estimates:
            assert result.estimates or result.notes, f"{name}: no estimates and no note saying why"


def check_shared_observations(diagnostic: Any, tmp_path: Path) -> None:
    """C10: with a usable run, the shared observations (minimum, maximum, relative spread), labeled with what they are
    of ("Of the n usable runs"; the point run's "Of the n runs at the point")."""
    for kw in ({}, {"failed": lambda c: np.arange(len(c.design)) > 0}):
        _, made, result = run(diagnostic, tmp_path, lean=True, **kw)
        y = usable_y(made)
        table = result.observations[0]
        n = result.counts.usable
        label = (
            rf"Of the {result.counts.runs} runs at the point" if diagnostic.name in C10_RUNS_LABEL else rf"Of the {n} "
        )
        assert table.key == "shared" and re.match(label, table.title), table.title
        rows = {row[0].key: row[0].value for row in table.rows}
        top = float(np.max(np.abs(y)))
        assert rows.get("min") == float(np.min(y)) and rows.get("max") == float(np.max(y)), rows
        assert rows.get("spread") == ((float(np.max(y)) - float(np.min(y))) / top if top else 0.0), rows


def check_report(diagnostic: Any, tmp_path: Path) -> None:
    """C11: S1's sections in order, Estimates only with estimates; the header's rows; numbers by S3; a line under each
    estimates table and EXPLAIN_INTERVALS the only "confidence interval" (S4); a "none" interval with its reason."""
    order = ["Notes", "Estimates", "Observations", "Figures", "Provenance"]
    for k, kw in enumerate(({"failed": lambda c: masks(c)["random"], "kinds": KINDS}, {})):
        case, _, result = run(diagnostic, tmp_path, figures=k == 0, **kw)
        report = render(result, case.spec)
        found = sections(report)
        assert found == [s for s in order if s in found] and found[-1] == "Provenance", found
        assert ("Estimates" in found) == bool(result.estimates)
        assert not (result.estimates and not diagnostic.has_estimates), "estimates from a diagnostic with none"
        assert report.lower().count("confidence interval") == (1 if result.estimates else 0)
        assert report.count(EXPLAIN_INTERVALS) == (1 if result.estimates else 0)
        assert report.count("Variability intervals:") == len(result.estimates)
        header = report.split("\n## ", 1)[0]
        labels = [line.split(" | ")[0][2:] for line in header.split("\n") if line.startswith("| ") and " | " in line]
        want = ["Model version", "Model prediction", "Space"] + (["Held"] if diagnostic.takes_space else [])
        want += ["Design", *[label for label, _ in result.header_rows], "Runs"]
        assert labels[1:] == want, labels
        assert all(label in diagnostic.header_rows for label, _ in result.header_rows), "an undeclared header row"
        body = report.split("\n## Provenance", 1)[0]
        for number in re.findall(r"(?<![\w.])-?\d+\.\d+(?:e[+-]\d+)?(?![\w.])|(?<![\w.])-?\d+e[+-]\d+(?![\w.])", body):
            digits = number.lstrip("-").split("e")[0].replace(".", "").lstrip("0")
            assert len(digits) <= 4, f"{number} has more than 4 significant digits (S3)"
        for table in result.estimates:
            for e in table.estimates:
                if e.interval is None:
                    assert str(e.reason) in report.replace("\\", ""), "a none interval without its reason"


def check_figures(diagnostic: Any, tmp_path: Path) -> None:
    """C12: each figure has a PNG and a data card; each point from a run has its run id; axes `name [units]`; no
    panel for a held model parameter; each strip holds each of its panel's runs that isn't usable, once, with its
    kind; the strip of a panel over every run has the header's count."""
    for kw in ({"failed": lambda c: masks(c)["random"], "kinds": KINDS,
                "missing_y": lambda c: (np.arange(len(c.design)) % 7) == 3},):  # fmt: skip
        case, made, result, directory = run_in(diagnostic, tmp_path, figures=True, **kw)
        ids = hex_ids(made.runs.run_ids)
        usable = made.usable("y")
        held = [p.name for p in case.spec.parameters if p.name not in case.ctx.space.ranges]
        strips = diagnostic.strips(made, result)
        assert result.figures, "no figure"
        for figure in result.figures:
            assert (directory / figure.png).stat().st_size > 0, f"no {figure.png}"
            card = json.loads((directory / figure.card).read_text(encoding="utf-8"))
            for k, panel in enumerate(card["panels"]):
                for which in ("x", "y"):
                    ax = panel[which]
                    assert ax["label"].endswith(f" [{ax['units']}]") if ax["units"] else "[" not in ax["label"], ax
                assert panel["x"]["label"].split(" [")[0] not in held, f"a panel for held {panel['x']['label']}"
                for point in panel.get("points", []):
                    if "run_id" in point:
                        assert point["run_id"] in ids, "a point's run id isn't a run of the batch"
                mask = strips.get((figure.name, k))
                if mask is None:
                    continue
                want = {ids[i] for i in np.flatnonzero(mask & ~usable)}
                got = [entry["run_id"] for entry in panel["not_usable"]]
                assert sorted(got) == sorted(want) and len(got) == len(set(got)), f"{figure.name} panel {k}'s strip"
                for entry in panel["not_usable"]:
                    row = ids.index(entry["run_id"])
                    kind = made.runs.kind[row]
                    assert entry["kind"] == (FailureKind.from_code(int(kind)).value if kind >= 0 else "missing")
                if mask.all():
                    assert len(got) == result.counts.runs - result.counts.usable


def check_price(diagnostic: Any, tmp_path: Path) -> None:
    """C13: the design's size, from the request before building, equals its rows; its distinct (point, replicate)
    keys are the runs the price counts (0011)."""
    for d in (3, 1):
        case = sd.prepare(NoFigures(diagnostic), d)
        generator = generators.get(case.identity.kind)
        assert generator.size(case.identity, case.spec) == len(case.design), "size isn't the design's rows"
        keys = {(row.tobytes(), int(r)) for row, r in zip(case.design.points, case.design.replicates, strict=True)}
        assert len(keys) == len(np.unique(sd.batch(case).runs.run_ids)), "keys aren't the distinct runs"


def check_design_parameters(diagnostic: Any, tmp_path: Path) -> None:
    """C14: a diagnostic parameter marked "no" leaves the design bit for bit; one marked "yes" changes it, or is
    refused; `prediction` leaves it.

    The declaration is exactly "no" or "yes", or "yes (...)" where the spec qualifies a yes (lines' seed, the
    polynomial model's degree), checked as a yes on the example request; nothing else, so a qualifier can't take a
    "no" past the check. A "no" whose other value is refused as "comes in a later version" passes (the polynomial
    model's basis, with one basis registered); that promise is the diagnostic's own C29 test, with a second basis
    registered (record 0079, Review round 1)."""
    case = sd.prepare(NoFigures(diagnostic))

    def same(other: sd.Case) -> bool:
        a, b = case.design, other.design
        return (
            a.points.shape == b.points.shape
            and np.array_equal(a.points, b.points)
            and np.array_equal(a.replicates, b.replicates)
            and a.levels == b.levels
            and a.lines == b.lines
        )

    assert same(sd.prepare(NoFigures(diagnostic), prediction="z")), "prediction moved the design"
    for p in diagnostic.parameters:
        declared = p.changes_design
        assert declared in ("yes", "no") or re.fullmatch(r"yes \([^()]+\)", declared), (
            f"{p.name}'s Changes the design? is {declared!r}, not yes or no"
        )
        assert p.parse(p.other_value) != case.request.params[p.name], f"{p.name}'s other value is its example's"
        try:
            other = sd.prepare(NoFigures(diagnostic), params={p.name: p.other_value})
        except base.RequestError as refused:
            assert declared != "no" or "comes in a later version" in str(refused), (
                f"{p.name} changes no design, and its other value is refused: {refused}"
            )
            continue
        if declared == "no":
            assert same(other), f"{p.name} is declared not to change the design, and changed it"
        else:
            assert not same(other), f"{p.name} is declared to change the design, and didn't"


def check_nesting(diagnostic: Any, tmp_path: Path) -> None:
    """C15: each nesting the diagnostic claims: the smaller request's points are points of the larger, bit for bit."""
    example = sd.prepare(NoFigures(diagnostic)).request.params
    for name in diagnostic.nesting:
        p = next(q for q in diagnostic.parameters if q.name == name)
        small, big = sorted([example[name], p.parse(p.other_value)])
        assert small != big
        a = sd.prepare(NoFigures(diagnostic), params={name: small}).design
        b = sd.prepare(NoFigures(diagnostic), params={name: big}).design
        rows = {(row.tobytes(), int(r)) for row, r in zip(b.points, b.replicates, strict=True)}
        for row, r in zip(a.points, a.replicates, strict=True):
            assert (row.tobytes(), int(r)) in rows, f"{name} = {small}: a point that isn't one of {name} = {big}'s"


def check_noisy_note(diagnostic: Any, tmp_path: Path) -> None:
    """C16: measured noisy in this model prediction: the note, with the standard deviation as a fraction of this
    result's range; measured in another model prediction: no note."""
    spec = sd.MODELS[3][0]
    nominal = tuple(p.nominal for p in spec.parameters)
    mv = sd.model_version_id(spec)
    record = MeasuredNoisy(sha256_hex("a point run"), mv, "y", nominal, 11, 0.01, None)
    _, made, result = run(diagnostic, tmp_path, lean=True, measured_noisy=(record,))
    text = note(result, "measured_noisy")
    y = usable_y(made)
    assert fmt(0.01 / float(np.ptp(y))) in text and "nominal point" in text, text
    other = MeasuredNoisy(sha256_hex("a point run"), mv, "z", nominal, 11, 0.01, None)
    _, _, result = run(diagnostic, tmp_path, lean=True, measured_noisy=(other,))
    assert "measured_noisy" not in codes(result), "a note from another model prediction's point run"


def check_round_trip(diagnostic: Any, tmp_path: Path) -> None:
    """C17: the result is strict JSON and loads back equal, its provenance's design structure included; a "none"
    interval is null, with its reason."""

    def strict(constant: str) -> Any:
        raise AssertionError(f"not strict JSON: {constant}")

    for kw in ({}, {"failed": lambda c: masks(c)["block"], "kinds": KINDS}):
        _, _, result = run(diagnostic, tmp_path, lean=True, **kw)
        text = result.to_json()
        data = json.loads(text, parse_constant=strict)
        back = DiagnosticResult.from_json(text)
        assert back == result and back.to_json() == text
        assert back.provenance.design_structure == result.provenance.design_structure
        for table in data["estimates"]:
            for e in table["estimates"]:
                assert (e["interval"] is None) == (e["reason"] is not None)


def check_dimensions(diagnostic: Any, tmp_path: Path) -> None:
    """C18: d = 1 and d = 20 give a diagnostic result on the example request, each within D20_SECONDS (the fast
    tier; the polynomial model's defaults at d = 20 are timed in the slow tier, record 0079 item 1, against the
    bound item 17 sets)."""
    for d in (1, 20):
        start = time.perf_counter()
        _, _, result = run(diagnostic, tmp_path, d=d)
        assert result.estimates or result.observations, f"d = {d}: no numbers"
        assert time.perf_counter() - start < D20_SECONDS


def check_interval_seam(diagnostic: Any, tmp_path: Path) -> None:
    """C19: a diagnostic with intervals takes them from the interval-method interface: a fake replaces the
    bootstrap, and its name is in the result and the line under each table."""
    if diagnostic.interval_method is None:
        _, _, result = run(diagnostic, tmp_path)
        assert not result.estimates, "estimates with no interval method"
        return
    with registered_interval_method(Spy()) as fake:
        case, _, result = run(diagnostic, tmp_path, interval_method=fake)
    assert result.estimates
    assert fake.calls, "the intervals didn't come from the interval method given"
    for table in result.estimates:
        assert table.interval.method == fake.name, f"{table.key}'s intervals are {table.interval.method}'s"
    shown = render(result, case.spec).replace("\\", "")  # as rendered: the report escapes "_" (T10)
    assert shown.count(f"Variability intervals: {fake.name} over") == len(result.estimates)


# --------------------------------------------------------------------------------------------------------------
# The broken toys: the toy with one promise broken each


class BrokenNaNObservations(Toy):
    """C1: reports the minimum and maximum of no runs as NaN observations."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        if not run_batch.usable("y").any():
            row = (Observation("min", "Minimum", math.nan, ""),)
            return Computation(observations=(ObservationTable("toy_counts", "t", ("t", "y"), (row,)),))
        return super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)


class BrokenFillsZero(Toy):
    """C2: fills failed runs' y with 0."""

    def values(self, run_batch: RunBatch, ctx: Any) -> tuple[np.ndarray, np.ndarray]:
        y = run_batch.runs.values[ctx.request.prediction]
        return np.nan_to_num(y), np.arange(len(y))


class BrokenUsesMissing(Toy):
    """C2: uses an ok run missing this model prediction (its other model prediction instead)."""

    def values(self, run_batch: RunBatch, ctx: Any) -> tuple[np.ndarray, np.ndarray]:
        runs = run_batch.runs
        y, z = runs.values[ctx.request.prediction], runs.values["z"]
        ok = runs.status == RunStatus.OK.code
        y = np.where(ok & np.isnan(y), z, y)
        return y, np.flatnonzero(ok & ~np.isnan(y))


class BrokenIgnoresMinimum(Toy):
    """C3: makes estimates one run below its declared minimum."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        n = int(run_batch.usable(ctx.request.prediction).sum())
        return super().compute(run_batch, ctx, estimates_allowed=n >= 2)


class _OwnConstant(Toy):
    """Calls y constant by its own test, with its own note and no estimates."""

    def flat(self, y: np.ndarray) -> bool:
        raise NotImplementedError

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        y, idx = self.values(run_batch, ctx)
        if len(idx) and self.flat(y[idx]):
            return Computation(notes=(Note("constant", "y is constant"),))
        return super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)


class BrokenRelativeConstant(_OwnConstant):
    """C4: calls a range below 10⁻¹⁰ of max|y| constant."""

    def flat(self, y: np.ndarray) -> bool:
        return bool(np.ptp(y) < 1e-10 * np.max(np.abs(y)))


class BrokenAbsoluteConstant(_OwnConstant):
    """C5: a constant test with an absolute tolerance (range < 10⁻⁸)."""

    def flat(self, y: np.ndarray) -> bool:
        return bool(np.ptp(y) < 1e-8)


class BrokenVariance(Toy):
    """C6: the variance as mean(y²) - mean(y)²."""

    def moments(self, y: np.ndarray, idx: np.ndarray) -> np.ndarray:
        v = y[idx]
        n = len(v)
        var = (np.mean(v * v) - np.mean(v) ** 2) * n / (n - 1)
        return np.array([np.mean(v), math.sqrt(max(var, 0.0))])


class BrokenSkipsByLog(Toy):
    """C6: declares its standard deviation computed through a logarithm, so C6 would leave it out (record 0077,
    Review round 1: C6's skip is lines' k* and rates only)."""

    TRANSFORMS = MappingProxyType({**Toy.TRANSFORMS, ("moments", "std"): (Transform.SCALED, True)})


class BrokenClock(Toy):
    """C7: seeds its draws from the clock."""

    def stream(self, ctx: Any) -> np.random.Generator:
        return np.random.default_rng(time.perf_counter_ns())


class BrokenSeedPlusOne(Toy):
    """C8: draws from default_rng(seed + 1), not its spawned stream."""

    def stream(self, ctx: Any) -> np.random.Generator:
        return np.random.default_rng(ctx.seed + 1)


class BrokenNoTag(Toy):
    """C8: declares no tag, and draws from the seed."""

    spawn_tags = ()

    def stream(self, ctx: Any) -> np.random.Generator:
        return np.random.default_rng(ctx.seed)


class BrokenNoEstimates(Toy):
    """C9: promises estimates, and gives neither estimates nor a note."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        return dataclass_replace(super().compute(run_batch, ctx, estimates_allowed=estimates_allowed), estimates=())


class BrokenScope(Toy):
    """C10: labels the shared observations with nothing of what they are of."""

    def observation_scope(self, n_usable: int, run_batch: RunBatch) -> str:
        return "Observations"


class BrokenSixDigits(Toy):
    """C11: numbers to 6 digits (in its own header row)."""

    header_rows = ("Fit",)

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        found = super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)
        y, idx = self.values(run_batch, ctx)
        value = float(np.mean(y[idx])) if len(idx) else 0.0
        return dataclass_replace(found, header_rows=(("Fit", f"mean {value:.6g}"),))


class BrokenNotConfidence(Toy):
    """C11: "Not confidence intervals." under each table."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        found = super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)
        tables = tuple(dataclass_replace(t, title="Not confidence intervals.") for t in found.estimates)
        return dataclass_replace(found, estimates=tables)


class BrokenStrip(Toy):
    """C12: leaves failed runs out of the strip."""

    def not_usable(self, usable: np.ndarray) -> np.ndarray:
        return np.zeros_like(usable)


class _OffByOne:
    """The uniform design generator, with a size one more than its rows."""

    name = "toy_off_by_one"
    version = Uniform.version

    def size(self, identity: Any, spec: Any) -> int:
        return Uniform().size(dataclass_replace(identity, kind="uniform"), spec) + 1

    def build(self, identity: Any, spec: Any, start: int = 0, stop: int | None = None) -> Any:
        return Uniform().build(dataclass_replace(identity, kind="uniform"), spec, start, stop)


class BrokenSize(Toy):
    """C13: a size off by one (a design generator whose size is one more than its rows)."""

    def design_identity(self, space: Any, params: Any, spec: Any, model_version_id: str) -> Any:
        return dataclass_replace(super().design_identity(space, params, spec, model_version_id), kind="toy_off_by_one")


@contextlib.contextmanager
def off_by_one() -> Iterator[None]:
    generators.register(_OffByOne())
    try:
        yield
    finally:
        generators.unregister("toy_off_by_one")


class BrokenSeedChangesNothing(Toy):
    """C14: declares that its seed changes no design (it seeds the uniform design)."""

    parameters = (Toy.parameters[0], base.seed_parameter("the design's seed.", "no"))


class BrokenQualifiedNo(Toy):
    """C14: qualifies a "no" in parentheses, so a parameter that changes the design is declared "no (...)"."""

    parameters = (Toy.parameters[0], base.seed_parameter("the design's seed.", "no (but it seeds the design)"))


class BrokenRefusedNo(Toy):
    """C14: declares "no" for its seed, and refuses the other value in words other than "comes in a later version"."""

    parameters = (Toy.parameters[0], base.seed_parameter("the design's seed.", "no"))

    def design_identity(self, space: Any, params: Any, spec: Any, model_version_id: str) -> Any:
        if params["seed"] != self.example_request(3)["seed"]:
            raise base.RequestError("seed: only the example's")
        return super().design_identity(space, params, spec, model_version_id)


class BrokenReseeds(Toy):
    """C15: reseeds when n changes."""

    def design_identity(self, space: Any, params: Any, spec: Any, model_version_id: str) -> Any:
        return super().design_identity(space, {**params, "seed": params["seed"] + params["n"]}, spec, model_version_id)


class BrokenOwnNoisyNote(Toy):
    """C16: builds its noisy note without the precheck's."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        found = super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)
        own = tuple(Note("measured_noisy", f"noisy: {m.std}") for m in ctx.measured_noisy)
        return dataclass_replace(found, notes=found.notes + own)


class BrokenNaNEstimate(Toy):
    """C17: stores a NaN estimate."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        found = super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)
        if found.estimates:
            nan = Estimate("nan", "NaN", math.nan, None, "undefined")
            table = found.estimates[0]
            found = dataclass_replace(found, estimates=(dataclass_replace(table, estimates=(nan,)),))
        return found


class BrokenAssumesTwo(Toy):
    """C18: assumes d >= 2."""

    def compute(self, run_batch: RunBatch, ctx: Any, *, estimates_allowed: bool) -> Computation:
        ctx.space.varied(ctx.spec)[1]
        return super().compute(run_batch, ctx, estimates_allowed=estimates_allowed)


class BrokenCallsBootstrap(Toy):
    """C19: calls the bootstrap directly."""

    def method(self, ctx: Any) -> Any:
        return intervals.Bootstrap()


dataclass_replace = dataclasses.replace


# --------------------------------------------------------------------------------------------------------------
# The meta-test and the toy's own test (contracts.md, Negative controls)


@dataclass(frozen=True)
class Broken:
    """A broken toy, the failure it must give, and what must be registered while it runs."""

    toy: Any
    raises: type[BaseException] = AssertionError
    match: str | None = None
    setup: Callable[[], contextlib.AbstractContextManager[Any]] = contextlib.nullcontext


BROKEN: dict[str, list[Broken]] = {
    "check_all_failed": [Broken(BrokenNaNObservations(), ValueError, "finite")],
    "check_partial_failures": [Broken(BrokenFillsZero(), match="expected"), Broken(BrokenUsesMissing(), match="moved")],
    "check_minimum": [Broken(BrokenIgnoresMinimum(), ValueError, "below its minimum")],
    "check_constant": [Broken(BrokenRelativeConstant(), match="constant to rounding")],
    "check_units": [Broken(BrokenAbsoluteConstant(), match="other notes")],
    "check_large_offset": [
        Broken(BrokenVariance(), match="expected"),
        Broken(BrokenSkipsByLog(), match="through a logarithm of lines' only"),
    ],
    "check_deterministic": [Broken(BrokenClock(), match="differ")],
    "check_spawn_tag": [Broken(BrokenSeedPlusOne(), match="another tag"), Broken(BrokenNoTag(), match="seed")],
    "check_never_empty": [Broken(BrokenNoEstimates(), match="no estimates and no note")],
    "check_shared_observations": [Broken(BrokenScope(), match="Observations")],
    "check_report": [Broken(BrokenSixDigits(), match="significant digits"), Broken(BrokenNotConfidence())],
    "check_figures": [Broken(BrokenStrip(), match="strip")],
    "check_price": [Broken(BrokenSize(), match="size", setup=off_by_one)],
    "check_design_parameters": [
        Broken(BrokenSeedChangesNothing(), match="declared not to change"),
        Broken(BrokenQualifiedNo(), match="not yes or no"),
        Broken(BrokenRefusedNo(), match="its other value is refused"),
    ],
    "check_nesting": [Broken(BrokenReseeds(), match="isn't one of")],
    "check_noisy_note": [Broken(BrokenOwnNoisyNote(), match="notes measured_noisy")],
    "check_round_trip": [Broken(BrokenNaNEstimate(), ValueError, "finite")],
    "check_dimensions": [Broken(BrokenAssumesTwo(), IndexError)],
    "check_interval_seam": [Broken(BrokenCallsBootstrap(), match="didn't come")],
}

CHECKS = {
    name: fn for name, fn in inspect.getmembers(sys.modules[__name__], inspect.isfunction) if name.startswith("check_")
}


@pytest.fixture(params=["toy", *base.names()])
def diagnostic(request: pytest.FixtureRequest) -> Any:
    """Every registered diagnostic, and the toy (not registered)."""
    return Toy() if request.param == "toy" else base.get(request.param)


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_every_check_fails_on_its_broken_toy(check: str, tmp_path: Path) -> None:
    """The meta-test (contracts.md, Negative controls): each broken toy fails its check, for its reason."""
    assert BROKEN.get(check), f"{check} has no broken toy"
    for k, broken in enumerate(BROKEN[check]):
        out = tmp_path / str(k)
        out.mkdir()
        with broken.setup(), pytest.raises(broken.raises, match=broken.match):
            CHECKS[check](broken.toy, out)


def test_the_toy_is_not_registered() -> None:
    assert "toy" not in base.names()


def test_the_toy_never_skips_c6(tmp_path: Path) -> None:
    """C6's skip is the point run's exemption only (record 0075, Review round 1, m2): the toy runs the check."""
    try:
        check_large_offset(Toy(), tmp_path)
    except pytest.skip.Exception as skipped:
        raise AssertionError(f"the toy skipped C6: {skipped}") from None


def test_lean_is_the_lean_fake_only_where_asked(tmp_path: Path) -> None:
    """Record 0084, Review round 1: ``lean`` gives a diagnostic with intervals the lean fake (25 resamples of its own
    estimators); without it, the registry's bootstrap; a diagnostic with no interval method keeps none."""
    _, _, lean = run(Toy(), tmp_path, lean=True)
    _, _, full = run(Toy(), tmp_path)
    assert [t.interval.method for t in lean.estimates] == [LEAN.name]
    assert lean.estimates[0].interval.settings["resamples"] == LeanIntervalMethod.resamples == 25
    assert [t.interval.method for t in full.estimates] == ["bootstrap"]
    assert [e.value for e in lean.estimates[0].estimates] == [e.value for e in full.estimates[0].estimates]
    case, _, _, _ = run_in(base.get("point_run"), tmp_path, lean=True)
    assert case.ctx.interval_method is None
