"""Coordinate lines: the model prediction along a line per varied model parameter, and each line's spectrum.

coordinate_lines.md: CL1-CL10; U2; records 0038, 0048, 0051, 0058, 0077. Observations only, no interval method and no
random draws: the seed is recorded and changes nothing (0061). The per-line computation and figure are ``_lines.py``'s,
shared with lines.
"""

from collections.abc import Mapping
from typing import Any

import numpy as np

from ema.designs import generators
from ema.diagnostics._lines import COORD_MIN_N, LinesDiagnostic
from ema.diagnostics.base import (
    AnalysisContext,
    DiagnosticParameter,
    Integer,
    Point,
    identity,
    register,
    seed_parameter,
)
from ema.types.design import DesignIdentity, Line
from ema.types.model import ModelSpec
from ema.types.runs import RunBatch
from ema.types.space import ModelParameterSpace, Scale

#: The default number of points per line: U2's; 2⁴ + 1, so reruns at 33 and 65 reuse every run (G11).
COORD_N = 17


class CoordinateLines(LinesDiagnostic):
    """Coordinate lines (coordinate_lines.md): one line per varied model parameter, in the model spec's order."""

    name = "coordinate_lines"
    title = "Coordinate lines"
    summary = "the model prediction along one line per varied model parameter through an anchor, and its spectrum"
    parameters = (
        DiagnosticParameter(
            "n",
            "integer ≥ 7",
            COORD_N,
            str(COORD_N),
            "the number of points on each line, end to end.",
            "yes",
            17,
            Integer(COORD_MIN_N),
        ),
        DiagnosticParameter(
            "anchor",
            "mapping of model parameter names to values",
            {},
            "{} (the nominal point)",
            "the point every line passes through; unnamed model parameters at their nominal values, held ones at "
            "their held values.",
            "yes",
            {"a": 0.3},
            Point(),
        ),
        seed_parameter("recorded; coordinate lines make no random draws (0061).", "no"),
    )
    nesting = ("n",)

    def example_request(self, d: int) -> Mapping[str, Any]:
        """Return n = 9 through the nominal point: small, and 17 = 2·9 - 1 nests it (C15)."""
        return {"n": 9, "anchor": {}, "seed": 0}

    def design_identity(
        self, space: ModelParameterSpace | None, params: Mapping[str, Any], spec: ModelSpec, model_version_id: str
    ) -> DesignIdentity:
        """Return the coordinate lines' identity, checked by the generator before anything is built (CL1; 0051).

        Raises
        ------
        RequestError
            For a space with no varied model parameter, an anchor outside the space, or an anchor equal to a point
            of a line along which it is off center, naming the model parameter.
        """
        if space is None:
            raise ValueError("coordinate lines need a model parameter space")
        params_ = {"n": int(params["n"]), "anchor": dict(params["anchor"])}
        made = identity(self.name, space, params_, spec, model_version_id, seed=int(params["seed"]))
        generators.get(made.kind).size(made, spec)
        return made

    def _parameter(self, line: Line, ctx: AnalysisContext) -> str:
        """Return the varied model parameter a coordinate line runs along: its direction's one nonzero component."""
        return ctx.space.varied(ctx.spec)[int(np.flatnonzero(np.asarray(line.direction))[0])]

    def label(self, j: int, line: Line, ctx: AnalysisContext) -> tuple[str, str]:
        """Return the model parameter's name, as the row label and after "along"."""
        name = self._parameter(line, ctx)
        return name, name

    def title_of(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return the model parameter's name (coordinate_lines.md, Figures)."""
        return self._parameter(line, ctx)

    def figure_name(self, j: int, line: Line, ctx: AnalysisContext) -> str:
        """Return ``coordinate_lines_<name>``."""
        return f"coordinate_lines_{self._parameter(line, ctx)}"

    def caption(self, ctx: AnalysisContext) -> str:
        """Return the figures' one caption, as the mock writes it."""
        return (
            f"{ctx.request.prediction} along each model parameter through the anchor (dotted), and the line's Gram "
            "spectrum, |c_k| / range, with the tail fit and the floor of 10⁻¹⁰."
        )

    def position(
        self, batch: RunBatch, j: int, line: Line, ctx: AnalysisContext
    ) -> tuple[np.ndarray, str, str, bool, float | None]:
        """Return the model parameter's values, in its units, on a log axis for a log range; the anchor's value."""
        name = self._parameter(line, ctx)
        column = [p.name for p in ctx.spec.parameters].index(name)
        x = np.asarray(batch.design.points[slice(*line.rows), column], dtype=float)
        log = ctx.space.ranges[name].scale is Scale.LOG
        return x, name, ctx.spec.parameter(name).units, log, float(line.anchor[column])

    def line_card(self, j: int, line: Line, ctx: AnalysisContext) -> dict[str, Any]:
        """Return the model parameter, the anchor, and the ends, in model parameter units."""
        return {"model_parameter": self._parameter(line, ctx), "anchor": line.anchor, "ends": line.ends}


register(CoordinateLines())
