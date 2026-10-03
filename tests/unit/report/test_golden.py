"""Each diagnostic spec's mock report, rebuilt by hand as a diagnostic result and rendered (S1-S4; 0044; record 0073).

The results hold the mocks' numbers; the rendered report must match the mock by ``tests/support/reports.py``'s
comparison (structure, and numbers within one unit in the 4th digit). This checks the renderer's shape against
every mock; each diagnostic's own golden report test, on its reference model, is its step's (09-13).

The mocks carry record 0073's conventions (Unicode symbols, a table's title opening the line under it, the
Provenance line's "runs: N") and record 0085's (the fits' relative residual and R² as observations, with the line
under the per-level table), so each is compared as written.
"""

import math
import re

import pytest

from ema.report import render
from ema.types.results import Figure, Note
from tests.support.reports import IN_SAMPLE, differences, mock_report, parse
from tests.support.results import etable, make_result, make_spec, otable, shared

PI = math.pi


def figures(names, caption):
    return [Figure(n, f"{n}.png", f"{n}.json", caption) for n in names]


def scatter_r2():
    spec = make_spec("r2", [("x1", "", 0.0), ("x2", "", 0.0), ("x3", "", 0.0)])
    space = {f"x{i}": [-PI, PI] for i in (1, 2, 3)}
    est = {"n_usable": 200, "seed": 1}
    return spec, make_result(
        spec,
        diagnostic="scatter",
        title="Scatter",
        space=space,
        params={"n": 200, "sampler": "random", "seed": 1},
        kind="uniform",
        design_params={"n": 200},
        seed=1,
        sampler="random",
        rows=200,
        runs=200,
        new=200,
        usable=200,
        estimates=[
            etable(
                "moments",
                ("Model prediction", "Estimate", "Variability interval"),
                [("Mean", 3.582, 2.906, 4.232), ("Standard deviation", 3.826, 3.275, 4.299)],
                **est,
            ),
            etable(
                "rank_correlation",
                ("Model parameter", "Rank correlation ρ", "Variability interval"),
                [("x1", 0.4185, 0.2651, 0.5489), ("x2", 0.02173, -0.1663, 0.1955), ("x3", -0.009447, -0.2193, 0.1803)],
                **est,
            ),
            etable(
                "binned_index",
                ("Model parameter", "Binned first-order index Sᵢ", "Variability interval"),
                [("x1", 0.2944, 0.1888, 0.4248), ("x2", 0.4068, 0.2816, 0.5257), ("x3", -0.004922, -0.07658, 0.103)],
                title="14 bins.",
                distinct="the index",
                **est,
            ),
        ],
        observations=[shared(200, "y", -9.094, 12.85, 1.708)],
        figures=figures(
            ["scatter_x1", "scatter_x2", "scatter_x3"],
            "y against each model parameter, with the means of the 14 bins of the binned index.",
        )
        + figures(["scatter_histogram"], "y over the 200 usable runs, 14 bins."),
    )


BOREHOLE = [
    ("rw", "m", 0.1, [0.05, 0.15]),
    ("r", "m", 25050.0, {"range": [100, 5e4], "scale": "log"}),
    ("Tu", "m²/yr", 89335.0, [63070, 115600]),
    ("Hu", "m", 1050.0, [990, 1110]),
    ("Tl", "m²/yr", 89.55, [63.1, 116]),
    ("Hl", "m", 760.0, [700, 820]),
    ("L", "m", 1400.0, [1120, 1680]),
    ("Kw", "m/yr", 10950.0, [9855, 12045]),
]
FLOW = ("y", "m³/yr", "water flow through the borehole")


def r3():
    return make_spec("r3", [(n, u, v) for n, u, v, _ in BOREHOLE], FLOW), {n: r for n, _, _, r in BOREHOLE}


def linear_r3():
    spec, space = r3()
    est = {"n_usable": 72, "seed": 3}
    coefficients = [
        ("Intercept", 78.27, 74.39, 82.02),
        ("rw", 69.19, 62.31, 77.66),
        ("r", 3.089, -4.032, 9.424),
        ("Tu", 0.7283, -7.785, 7.972),
        ("Hu", 9.323, 1.944, 16.68),
        ("Tl", -0.2023, -6.665, 5.679),
        ("Hl", -16.3, -23.51, -10.14),
        ("L", -11.39, -18.83, -4.943),
        ("Kw", 7.478, 1.701, 14.31),
    ]
    levels = [
        ("Usable runs", "18 of 18", "36 of 36", "72 of 72"),
        ("Intercept", 79.67, 77.82, 78.27),
        ("rw", 69.78, 71.31, 69.19),
        ("r", 6.095, 1.948, 3.089),
        ("Tu", 5.239, -1.636, 0.7283),
        ("Hu", 18.79, 12.09, 9.323),
        ("Tl", -4.137, -5.668, -0.2023),
        ("Hl", -21.19, -16.9, -16.3),
        ("L", -18.25, -14.83, -11.39),
        ("Kw", 12.38, 8.034, 7.478),
        ("Relative residual", 0.1408, 0.2038, 0.2335),
        ("R²", 0.9802, 0.9584, 0.9455),
        ("Leave-one-out error", 0.2934, 0.2879, 0.2716),
    ]
    return spec, make_result(
        spec,
        diagnostic="linear_model",
        title="Linear model",
        space=space,
        params={"n_min": 18, "alpha": "0.7072", "level": 2, "sampler": "random", "seed": 3},
        kind="convergent",
        design_params={"n_min": 18, "alpha": "0.7072", "level": 2},
        seed=3,
        sampler="random",
        rows=72,
        runs=72,
        new=72,
        usable=72,
        levels=(18, 36, 72),
        estimates=[
            etable(
                "coefficients",
                ("Coefficient", "Estimate", "Variability interval"),
                coefficients,
                units="m³/yr",
                title="y ≈ intercept + Σ slope·u, u the unit coordinates in [-1, 1] (r through its logarithm).",
                **est,
            ),
            etable(
                "loo",
                ("Held out", "Estimate", "Variability interval"),
                [("Leave-one-out error, relative", 0.2716, 0.2168, 0.336)],
                distinct="the error",
                **est,
            ),
        ],
        observations=[
            shared(72, "y", 10.24, 181.9, 0.9437, units="m³/yr"),
            otable(
                "levels",
                ("The fit at each level", "Level 0", "Level 1", "Level 2"),
                levels,
                title="Coefficients in m³/yr. Each level is fitted on the usable runs among its first points. "
                + IN_SAMPLE,
            ),
        ],
        figures=figures(
            ["linear_model_shadow"],
            "y against w·u, the unit coordinates projected on the direction of the slopes, with the fitted line.",
        )
        + figures(["linear_model_coefficients"], "Each slope with its variability interval, in m³/yr per half-range.")
        + figures(["linear_model_residuals"], "The residuals of the 72 usable runs, 8 bins."),
    )


def polynomial_r3():
    spec, space = r3()
    est = {"n_usable": 360, "seed": 3}
    sobol = [
        ("rw", 0.8304, 0.8248, 0.8361, 0.8673, 0.8625, 0.8721),
        ("r", 5.622e-06, 1.007e-07, 6.983e-05, 4.257e-05, 1.703e-05, 0.0002161),
        ("Tu", 3.38e-06, 1.725e-07, 8.413e-05, 4.465e-05, 1.64e-05, 0.0002891),
        ("Hu", 0.04188, 0.03938, 0.04421, 0.05421, 0.05085, 0.05717),
        ("Tl", 1.369e-06, 3.161e-08, 5.496e-05, 1.397e-05, 8.325e-06, 0.0002055),
        ("Hl", 0.04149, 0.03906, 0.04369, 0.05415, 0.05143, 0.0564),
        ("L", 0.03857, 0.03655, 0.04051, 0.05012, 0.04713, 0.05265),
        ("Kw", 0.009238, 0.00811, 0.01044, 0.01251, 0.01103, 0.01412),
    ]
    levels = [
        ("Usable runs", "90 of 90", "180 of 180", "360 of 360"),
        ("Relative residual", 0.02633, 0.03296, 0.03526),
        ("R²", 0.9993, 0.9989, 0.9988),
        ("Leave-one-out error", 0.05555, 0.04664, 0.04192),
        ("Total index of rw", 0.8705, 0.8651, 0.8673),
        ("r", 0.0003875, 0.0001167, 4.257e-05),
        ("Tu", 0.0008148, 7.24e-05, 4.465e-05),
        ("Hu", 0.04762, 0.05401, 0.05421),
        ("Tl", 0.0003035, 2.474e-05, 1.397e-05),
        ("Hl", 0.05415, 0.05433, 0.05415),
        ("L", 0.04878, 0.05239, 0.05012),
        ("Kw", 0.01158, 0.01201, 0.01251),
    ]
    return spec, make_result(
        spec,
        diagnostic="polynomial_model",
        title="Polynomial model",
        space=space,
        params={
            "degree": 2,
            "basis": "total_degree",
            "n_min": 90,
            "alpha": "0.7072",
            "level": 2,
            "sampler": "random",
            "seed": 3,
        },
        kind="convergent",
        design_params={"n_min": 90, "alpha": "0.7072", "level": 2},
        seed=3,
        sampler="random",
        rows=360,
        runs=360,
        new=288,
        usable=360,
        levels=(90, 180, 360),
        header_rows=[("Fit", "degree 2, total_degree basis: 45 terms")],
        estimates=[
            etable(
                "loo",
                ("Held out", "Estimate", "Variability interval"),
                [("Leave-one-out error, relative", 0.04192, 0.03645, 0.05058)],
                distinct="the error",
                **est,
            ),
            etable(
                "sobol",
                (
                    "Sobol indices of the fitted polynomial",
                    "First-order",
                    "Variability interval",
                    "Total",
                    "Variability interval",
                ),
                sobol,
                title="Of the degree-2 polynomial fitted to the runs, under the uniform distribution in unit "
                "coordinates (r through its logarithm).",
                **est,
            ),
            etable(
                "decay",
                ("Total degree k", "Terms", "Root energy √E_k", "Variability interval"),
                [("1\t8", 44.67, 44.22, 45.08), ("2\t36", 10.37, 9.843, 10.96)],
                units="m³/yr",
                title="√E_k: the standard deviation of the fitted polynomial's terms of total degree k.",
                **est,
            ),
        ],
        observations=[
            shared(360, "y", 10.24, 225.2, 0.9545, units="m³/yr"),
            otable(
                "levels",
                ("The fit at each level", "Level 0", "Level 1", "Level 2"),
                levels,
                title="Each level is fitted on the usable runs among its first points. " + IN_SAMPLE,
            ),
        ],
        figures=figures(
            ["polynomial_model_fit"],
            "y against the fitted polynomial (left) and against each run's held-out prediction (right), with the "
            "line y = ŷ.",
        )
        + figures(
            ["polynomial_model_sobol"],
            "The first-order and total Sobol indices of the fitted polynomial, with their variability intervals.",
        )
        + figures(["polynomial_model_decay"], "√E_k against the total degree k, with variability intervals, in m³/yr.")
        + figures(["polynomial_model_residuals"], "The residuals of the 360 usable runs, 18 bins."),
    )


def point_run_r6a():
    spec = make_spec("r6a", [("a", "", 1.0), ("b", "", 0.0), ("c", "", 15.0), ("k", "", 10.0)])
    title = "Of the 5 runs at the point"
    rows = [
        ("Replicate 0", 10.03),
        ("Mean", 9.982),
        ("Standard deviation (ddof 1)", 0.03903),
        ("Distinct values", 5),
        ("Minimum", 9.939),
        ("Maximum", 10.03),
        ("(max - min) / max|y|", 0.009281),
    ]
    return spec, make_result(
        spec,
        diagnostic="point_run",
        title="Point run",
        space=None,
        params={"x": {}, "repeats": 4, "seed": 0},
        kind="point",
        design_params={"x": {}, "repeats": 4},
        seed=0,
        rows=5,
        runs=5,
        new=4,
        usable=5,
        observations=[otable("point", (title, "y"), rows)],
        figures=figures(["point_run"], "y - y(replicate 0) against the replicate number, 0 to 4."),
        noisy=True,
    )


LINE_TITLE = (
    "Decay rate: minus the least-squares slope of log₁₀ of the Gram spectrum's tail against the degree, over the "
    "degrees whose tail is above 10⁻¹⁰ of the line's range, at most K = 8. Observations of the 17 runs on each line; "
    "no variability intervals."
)
SPECTRUM_CAPTION = "the line's Gram spectrum, |c_k| / range, with the tail fit and the floor of 10⁻¹⁰."


def coordinate_lines_r8():
    names = ["a", "b", "c", "e", "f", "g"]
    spec = make_spec("r8", [(n, "", 0.0) for n in names])
    rates = [
        ("a", "17 of 17", 0.4, "8 of 8", 0.1811),
        ("b", "17 of 17", 1.0, "8 of 8", 0.06916),
        ("c", "17 of 17", 0.8, "8 of 8", 0.1957),
        ("e", "17 of 17", 0.4, "8 of 8", 0.1811),
        ("f", "17 of 17", 0.0, "0 of 8", "none: constant"),
        ("g", "17 of 17", 0.0, "0 of 8", "none: constant"),
    ]
    columns = ("Model parameter", "Usable", "Range", "Degrees above the floor", "Decay rate (decades per degree)")
    return spec, make_result(
        spec,
        diagnostic="coordinate_lines",
        title="Coordinate lines",
        space={n: [-1, 1] for n in names},
        params={"n": 17, "anchor": {}, "seed": 0},
        kind="coordinate_lines",
        design_params={"n": 17, "anchor": {}},
        seed=0,
        rows=102,
        runs=97,
        new=56,
        usable=97,
        notes=[Note("constant_line", f"y is the same in all 17 usable runs along {n}: 1.") for n in ("f", "g")],
        observations=[shared(97, "y", 0.2, 2.0, 0.9), otable("line_rates", columns, rates, title=LINE_TITLE)],
        figures=figures(
            [f"coordinate_lines_{n}" for n in names],
            "y along each model parameter through the anchor (dotted), and " + SPECTRUM_CAPTION,
        ),
    )


def lines_r7():
    names = ["a", "b", "c", "e"]
    spec = make_spec("r7", [(n, "", 0.0) for n in names])
    ends = [
        ("a", "0.6198 → 1", "-1 → 1", "1 → -1", "-1 → 1", "0.2123 → 0.783"),
        ("b", "-0.4175 → -0.3458", "-0.1497 → -0.6877", "-0.9938 → 0.003045", "-0.1718 → 0.3618", "-0.2506 → -0.8688"),
        ("c", "0.1892 → 0.5543", "-0.1069 → 0.381", "0.1505 → 0.6742", "-0.1998 → 0.1157", "-1 → 1"),
        ("e", "-1 → -0.6411", "0.9332 → -0.672", "0.3123 → 0.8897", "-0.3275 → -0.8983", "0.0431 → 0.7265"),
    ]
    rates = [
        ("0", "17 of 17", 0.6417, 0.4261, "8 of 8", 0.8166),
        ("1", "17 of 17", 2.665, 0.3665, "8 of 8", 0.6447),
        ("2", "17 of 17", 2.367, 1.274, "8 of 8", 0.2184),
        ("3", "17 of 17", 2.17, 1.132, "8 of 8", 0.07052),
        ("4", "17 of 17", 2.275, 1.102, "8 of 8", 0.1891),
    ]
    columns = ("Line", "Usable", "Length", "Range", "Degrees above the floor", "Decay rate (decades per degree)")
    return spec, make_result(
        spec,
        diagnostic="lines",
        title="Lines",
        space={n: [-1, 1] for n in names},
        params={"m": 5, "n": 17, "seed": 0},
        kind="random_lines",
        design_params={"m": 5, "n": 17},
        seed=0,
        rows=85,
        runs=85,
        new=85,
        usable=85,
        observations=[
            shared(85, "y", 0.2, 1.995, 0.8997),
            otable("ends", ("Model parameter", *(f"Line {j}" for j in range(5))), ends),
            otable("line_rates", columns, rates, title="Length: in unit coordinates. " + LINE_TITLE),
        ],
        figures=figures(
            [f"lines_{j}" for j in range(5)], "y against the distance along each line, and " + SPECTRUM_CAPTION
        ),
    )


CASES = {
    "scatter": (scatter_r2, lambda: mock_report("scatter")),
    "linear_model": (linear_r3, lambda: mock_report("linear_model")),
    "polynomial_model": (polynomial_r3, lambda: mock_report("polynomial_model")),
    "point_run": (point_run_r6a, lambda: mock_report("point_run")),
    "coordinate_lines": (coordinate_lines_r8, lambda: mock_report("coordinate_lines")),
    "lines": (lines_r7, lambda: mock_report("lines")),
}


@pytest.mark.parametrize("name", list(CASES))
def test_the_mock_report(name):
    """S1-S4 and the Provenance line against each spec's mock report (0044; record 0073 item 6)."""
    build, mock = CASES[name]
    spec, result = build()
    report = render(result, spec)
    assert differences(report, mock()) == []


@pytest.mark.parametrize("name", list(CASES))
def test_the_comparison_finds_a_changed_number(name):
    """A negative control: a number off by a few units in its 4th digit, or a dropped section, is found."""
    build, mock = CASES[name]
    spec, result = build()
    report = render(result, spec)
    golden = mock()
    off = re.sub(r"(\| Minimum \| )(-?[\d.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) * 1.003 + 0.01:.4g}", golden)
    assert off != golden
    assert differences(report, off) != []
    without = report.split("## Figures")[0] + "## Provenance" + report.split("## Provenance")[1]
    assert differences(without, golden) != []
    assert parse(report).sections["Observations"]
