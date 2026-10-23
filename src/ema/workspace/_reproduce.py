"""``reproduce``: replay a diagnostic result from its provenance and the stored runs, and compare (U8).

architecture.md §7 (``reproduce``); data_model.md §9, Replay; records 0054, 0055, 0062, 0063, 0080. Writes nothing:
the replay runs into a temporary directory, with no W5. Its design is built from the stored runs' points and the
provenance's design structure (``replay_batch``), so it recomputes what was computed, across generator versions
too; when the identity's generator and sampler versions are today's, the design is also rebuilt and compared, per
range, and rows beyond the tolerance are named among the provenance's differences. It never raises for either.
"""

import dataclasses
import json
import math
import os
import tempfile
from typing import Any

import numpy as np

from ema.designs import generators, samplers
from ema.designs.generators import GOLDEN_UNIT_TOL
from ema.diagnostics import base
from ema.store import Store
from ema.types.design import Design
from ema.types.errors import EMAError, NotFound
from ema.types.identity import reuse_key, sha256_hex
from ema.types.model import ModelSpec
from ema.types.results import DiagnosticResult, Provenance, Reproduction
from ema.types.space import ModelParameterSpace, Scale
from ema.workspace import _evaluate

#: The most design rows named in a difference; the rest are counted.
_ROWS_SHOWN = 10


def _names(result: DiagnosticResult) -> list[str]:
    """Name the files of a result's directory compared byte for byte: the report and the data cards (S10)."""
    return ["report.md", *(f.card for f in result.figures)]


def _files(directory: str, result: DiagnosticResult) -> dict[str, bytes]:
    """Read the report and the data cards of a result's directory, by name (S10); a missing one as no bytes."""
    out = {}
    for name in _names(result):
        try:
            with open(os.path.join(directory, name), "rb") as f:
                out[name] = f.read()
        except OSError:
            out[name] = b""
    return out


def _cells(tables: list[dict[str, Any]], field: str) -> list[str]:
    if field == "rows":
        return [json.dumps(c, sort_keys=True) for t in tables for row in t["rows"] for c in row]
    return [json.dumps(c, sort_keys=True) for t in tables for c in t[field]]


def _count(a: list[str], b: list[str]) -> int:
    return sum(x != y for x, y in zip(a, b, strict=False)) + abs(len(a) - len(b))


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def differences(original: DiagnosticResult, replayed: DiagnosticResult) -> list[str]:
    """Name what differs between two results' numbers and notes: "2 estimates", "notes", "counts" (U8)."""
    a, b = json.loads(original.to_json()), json.loads(replayed.to_json())
    out = []
    for key, field, word in (("estimates", "estimates", "estimate"), ("observations", "rows", "observation"),
                             ("extra", "estimates", "extra estimate")):  # fmt: skip
        n = _count(_cells(a[key], field), _cells(b[key], field))
        if n:
            out.append(_plural(n, word))
        heads = ([{k: v for k, v in t.items() if k != field} for t in r[key]] for r in (a, b))
        if next(heads) != next(heads):
            out.append(f"{key} tables")
    for key, name in (("title", "title"), ("counts", "counts"), ("header_rows", "header"), ("notes", "notes"),
                      ("figures", "figures"), ("measured_noisy", "measured-noisy record")):  # fmt: skip
        if a[key] != b[key]:
            out.append(name)
    return out


def _tolerance(r: Any) -> float:
    """Return a coordinate's tolerance in unit coordinates (0063): linear, ``GOLDEN_UNIT_TOL``; log, wider by the logs."""
    if r.scale is not Scale.LOG:
        return GOLDEN_UNIT_TOL
    lo, hi = math.log(r.lo), math.log(r.hi)
    return max(GOLDEN_UNIT_TOL, 32 * 2.0**-52 * (1 + abs(lo) + abs(hi)) / (hi - lo))


def _rows(bad: np.ndarray) -> str:
    rows = [str(i) for i in np.flatnonzero(bad)[:_ROWS_SHOWN]]
    more = int(bad.sum()) - len(rows)
    return ", ".join(rows) + (f", and {more} more" if more else "")


def compare_designs(stored: Design, rebuilt: Design, spec: ModelSpec, space: ModelParameterSpace) -> list[str]:
    """Compare a rebuilt design with the stored one, coordinate by coordinate, per range (0062, 0063)."""
    if len(stored) != len(rebuilt):
        return [f"design sizes differ: {len(stored)} rows stored, {len(rebuilt)} rebuilt"]
    out = []
    if stored.levels != rebuilt.levels:
        out.append("design levels differ")
    for k, (a, b) in enumerate(zip(stored.lines or (), rebuilt.lines or (), strict=False)):
        if a.rows != b.rows:
            out.append(f"line {k}'s rows differ")
    if len(stored.lines or ()) != len(rebuilt.lines or ()):
        out.append("design lines differ")
    bad = stored.replicates != rebuilt.replicates
    varied = space.varied(spec)
    names = [p.name for p in spec.parameters]
    for j, name in enumerate(names):
        if name not in varied:  # held: exactly, every bit
            bad |= stored.points[:, j].view(np.int64) != rebuilt.points[:, j].view(np.int64)
    if varied:
        za, zb = space.to_unit(spec, stored.points), space.to_unit(spec, rebuilt.points)
        tol = np.array([_tolerance(space.ranges[name]) for name in varied])
        bad |= (np.abs(za - zb) > tol).any(axis=1)
    if bad.any():
        out.append(f"design points differ at rows {_rows(bad)}")
    return out


def design_check(
    provenance: Provenance, spec: ModelSpec, stored: Design
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Rebuild the design when its generator's and sampler's versions are today's, as a check (0062, 0063).

    Returns the versions that differ, as (name, here, there), and the rebuilt design's differences; never raises:
    any exception of a generator, a sampler, or the comparison is a sentence (0062, 0063; record 0080, Review
    round 1).
    """
    try:
        return _design_check(provenance, spec, stored)
    except Exception as error:  # noqa: BLE001  (a registered generator or sampler may raise anything: §7)
        why = str(error) if isinstance(error, EMAError) else f"{type(error).__name__}: {error}"
        return [], [f"the design could not be rebuilt: {why}"]


def _design_check(
    provenance: Provenance, spec: ModelSpec, stored: Design
) -> tuple[list[tuple[str, str, str]], list[str]]:
    identity = provenance.design
    try:
        generator = generators.get(identity.kind)
    except EMAError:
        return [], [f"no design generator {identity.kind} here: the design was not rebuilt"]
    versions = []
    if generator.version != identity.generator_version:
        versions.append((f"design generator {identity.kind}", generator.version, identity.generator_version))
    if identity.sampler is not None:
        try:
            here = samplers.get(identity.sampler).version
        except EMAError:
            return versions, [f"no sampler {identity.sampler} here: the design was not rebuilt"]
        if here != identity.sampler_version:
            versions.append((f"sampler {identity.sampler}", here, str(identity.sampler_version)))
    if versions:
        return versions, []
    rebuilt = generator.build(identity, spec)
    space = ModelParameterSpace.parse(identity.canonical()["space"])
    return [], compare_designs(stored, rebuilt, spec, space)


def reproduce(store: Store, original: DiagnosticResult | None, provenance: Provenance) -> Reproduction:
    """Replay a result from its provenance, compare it with the original when there is one, and write nothing (U8).

    Parameters
    ----------
    store
        The workspace's store.
    original
        The result given or stored; None for a provenance alone whose result is deleted.
    provenance
        What is replayed.
    """
    p = provenance
    there = {"ema": p.ema, "numpy": p.numpy, "scipy": p.scipy, "matplotlib": p.matplotlib}
    result_id = sha256_hex(reuse_key(p.model_version_id, p.request, p.run_ids, there))
    if original is not None:
        result_id = original.result_id
    spec = store.model_version(p.model_version_id).spec
    here = base.library_versions()
    versions = [(name, here[name], there[name]) for name in ("ema", "numpy", "scipy", "matplotlib")
                if here[name] != there[name]]  # fmt: skip
    with tempfile.TemporaryDirectory(prefix="ema-replay-") as tmp:
        replay_dir, original_dir = os.path.join(tmp, "replay"), os.path.join(tmp, "original")
        os.mkdir(replay_dir)
        replayed, batch = _evaluate.replay(store, p, result_id, replay_dir)
        rebuilt_versions, design_differences = design_check(p, spec, batch.design)
        found: list[str] = []
        if original is not None:
            found = differences(original, replayed)
            directory = store.layout.result_dir(result_id)
            if not all(os.path.isfile(os.path.join(directory, n)) for n in _names(original)):
                os.mkdir(original_dir)  # the original's files, drawn again from it and its runs (S10)
                ctx = _evaluate.context(p.request, spec, p.measured_noisy_read, None)
                drawn = dataclasses.replace(original, figures=())  # as evaluate draws them (P1)
                base.get(original.diagnostic).figures(batch, drawn, ctx, original_dir)
                _evaluate.write_report(original_dir, original, spec)
                directory = original_dir
            want, got = _files(directory, original), _files(replay_dir, replayed)
            for name in want:
                if want[name] != got.get(name):
                    found.append("report" if name == "report.md" else f"data card {name.removesuffix('.json')}")
    try:
        short = store.short("result", result_id)
    except NotFound:
        short = result_id[:12]
    return Reproduction.make(
        replayed,
        result_id=result_id,
        short_id=short,
        identical=None if original is None else not found,
        differences=tuple(found),
        versions=tuple(versions + rebuilt_versions),
        design_differences=tuple(design_differences),
    )
