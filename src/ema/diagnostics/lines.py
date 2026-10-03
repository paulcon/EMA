"""Lines: the model prediction along m random lines, or along given lines, and each line's Gram spectrum.

lines.md: LN1-LN9; U2's finer line; records 0012, 0038, 0048, 0049, 0058, 0077. Two modes, one request: ``lines`` given,
the design is those lines; otherwise m random lines from the request's seed (the design's streams; the diagnostic draws
nothing). Each line is analyzed as a coordinate line is (``_lines.py``), in its own parameter s; its length in unit
coordinates is an observation, and a table says where each line runs. No summary across lines.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from ema.designs import generators
from ema.diagnostics._lines import COORD_MIN_N, LinesDiagnostic
from ema.diagnostics.base import (
    AnalysisContext,
    DiagnosticParameter,
    GivenLines,
    Integer,
    Transform,
    identity,
    register,
    seed_parameter,
)
from ema.types.design import DesignIdentity, Line
from ema.types.errors import RequestError
from ema.types.model import ModelSpec
from ema.types.results import Observation, ObservationTable
from ema.types.runs import RunBatch
from ema.types.space import ModelParameterSpace
from ema.types.text import fmt

#: The default number of random lines: 85 runs at n = 17.
LINES_M = 5
#: The default number of points per line, in both modes.
LINES_N = 17
#: The most lines in one table of ends: more lines make more tables.
LINES_TABLE_COLUMNS = 5


@dataclass(frozen=True)
class _OptionalInteger:
    """An integer >= ``minimum``, or None: ``m``, which is none when lines are given."""

    minimum: int

    def read(self, value: Any, what: str) -> int | None:
        """Return the value as an ``int``, or None."""
        return None if value is None else Integer(self.minimum).read(value, what)

    def schema(self) -> Mapping[str, Any]:
        """Return an integer >= ``minimum``, or null."""
        return {"anyOf": [Integer(self.minimum).schema(), {"type": "null"}]}


def _m(d: int, others: Mapping[str, Any]) -> int | None:
    """Return m's default: 5 random lines; none when lines are given (lines.md, Two modes; 0077 item 10)."""
    return None if others.get("lines") is not None else LINES_M


class Lines(LinesDiagnostic):
    """Lines (lines.md): random lines, numbered by their stream j, or given lines, in the order given."""

    name = "lines"
    title = "Lines"
    summary = "the model prediction along random or given lines, and each line's Gram spectrum and decay rate"
    parameters = (
        DiagnosticParameter(
            "m", "integer ≥ 1", _m, "5; none with lines", "the number of random lines.", "yes", 3, _OptionalInteger(1)
        ),
        DiagnosticParameter(
            "lines",
            'list of lines, each {"anchor": {...}, "direction": {...}}',
            None,
            "none",
            "given lines, in place of random ones: the anchor in model parameter units, the direction in unit "
            "coordinates.",
            "yes",
            [{"direction": {"a": 1.0}}],
            GivenLines(),
        ),
        DiagnosticParameter(
            "n",
            "integer ≥ 7",
            LINES_N,
            str(LINES_N),
            "the number of points on each line, end to end.",
            "yes",
            17,
            Integer(COORD_MIN_N),
        ),
        seed_parameter("the random lines' seed; recorded, and unused, with given lines.", "yes (random lines)"),
    )
    nesting = ("m", "n")
    row_head = "Line"
    extra_columns = ("Length",)
    title_lead = "Length: in unit coordinates. "

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return 2 random lines of 9 points: small; 3 lines and 17 points nest them (C15)."""
        return {"m": 2, "n": 9, "seed": 0}

    def transform(self, table_key: str, key: str) -> tuple[Transform, bool]:
        """Return the declared change; the ends tables' cells don't depend on y (C5)."""
        if table_key.startswith("ends_"):
            return Transform.UNCHANGED, False
        return super().transform(table_key, key)

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the random or given lines' identity, checked by the generator before anything is built (LN1).

        Raises
        ------
        RequestError
            For both ``m`` and ``lines``, or neither, a space with no varied model parameter, or G14's cases (an
            anchor outside the space, a zero direction, a direction naming a held model parameter or an unknown name).
        """
        if space is None:
            raise ValueError("lines need a model parameter space")
        given, m, n, seed = params["lines"], params["m"], int(params["n"]), int(params["seed"])
        if given is not None and m is not None:
            raise RequestError("lines: give m (random lines) or lines (given lines), not both")
        if given is None and m is None:
            raise RequestError("lines: give m (random lines) or lines (given lines)")
        if given is not None:
            made = identity("lines", space, {"lines": [dict(g) for g in given], "n": n}, spec, model_version_id,
                            seed=seed)  # fmt: skip
        else:
            made = identity("random_lines", space, {"m": int(m), "n": n}, spec, model_version_id, seed=seed)
        generators.get(made.kind).size(made, spec)
        return made

    @staticmethod
    def _unit(line: Line, ctx: AnalysisContext) -> tuple[np.ndarray, np.ndarray, float]:
        """Return the line's ends in unit coordinates, and its length (0049)."""
        z = ctx.space.to_unit(ctx.spec, np.array(line.ends, dtype=float))
        step = z[1] - z[0]
        return z[0], z[1], float(np.sqrt(np.sum(step * step)))

    def label(self, j: int, line: Line, ctx: AnalysisContext) -> tuple[str, str]:
        """Return "j", and "line j" after "along"."""
        return str(j), f"line {j}"

    def title_of(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return "line j"."""
        return f"line {j}"

    def figure_name(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return ``lines_<j>``."""
        return f"lines_{j}"

    def caption(self, ctx: AnalysisContext) -> str:
        """Return the figures' one caption, as the mock writes it."""
        return (
            f"{ctx.request.prediction} against the distance along each line, and the line's Gram spectrum, "
            "|c_k| / range, with the tail fit and the floor of 10⁻¹⁰."
        )

    def position(
        self, batch: RunBatch, j: int, line: Line, ctx: AnalysisContext
    ) -> tuple[np.ndarray, str, str, bool, float | None]:
        """Return each point's distance from the line's start, 0 to its length; a given line's anchor's (LN6)."""
        z0, z1, length = self._unit(line, ctx)
        n = line.rows[1] - line.rows[0]
        x = length * np.arange(n) / (n - 1)
        mark = None
        if batch.design.identity is not None and batch.design.identity.kind == "lines":
            anchor = ctx.space.to_unit(ctx.spec, np.array([line.anchor], dtype=float))[0]
            mark = float(np.sum((anchor - z0) * (z1 - z0))) / length
        return x, f"distance along line {j} (unit coordinates)", "", False, mark

    def line_card(self, j: int, line: Line, ctx: AnalysisContext) -> dict[str, Any]:
        """Return the anchor, the direction (unit coordinates), the ends (both), and the length."""
        z0, z1, length = self._unit(line, ctx)
        return {"anchor": line.anchor, "direction": line.direction, "ends": line.ends, "ends_unit": [z0, z1],
                "length": length}  # fmt: skip

    def extra(
        self, batch: RunBatch, ctx: AnalysisContext
    ) -> tuple[tuple[ObservationTable, ...], list[tuple[Observation, ...]]]:
        """Return the ends tables (at most 5 lines each), and each line's length (LN3, LN4)."""
        lines = batch.design.lines or ()
        names = [p.name for p in ctx.spec.parameters]
        tables = []
        for t, start in enumerate(range(0, len(lines), LINES_TABLE_COLUMNS)):
            block = range(start, min(start + LINES_TABLE_COLUMNS, len(lines)))
            rows = []
            for name in ctx.space.varied(ctx.spec):
                i, units = names.index(name), ctx.spec.parameter(name).units
                rows.append(
                    tuple(
                        Observation("ends", name, f"{fmt(lines[j].ends[0][i])} → {fmt(lines[j].ends[1][i])}", units)
                        for j in block
                    )
                )
            columns = ("Model parameter", *(f"Line {j}" for j in block))
            tables.append(ObservationTable(f"ends_{t}", "Model parameter", columns, tuple(rows)))
        lengths: list[tuple[Observation, ...]] = [
            (Observation("length", str(j), self._unit(line, ctx)[2], ""),) for j, line in enumerate(lines)
        ]
        return tuple(tables), lengths


register(Lines())
