"""Scatter's rank correlation and binned first-order index (scatter.md, Computation)."""

import math

import numpy as np
import pytest
from scipy import stats

from ema.numerics.stats import average_ranks, binned_index, binned_indices, rank_correlation, rank_correlations
from tests.support.numerics import OFFSETS, at_offset, r2_unit

#: The scatter mock report's design (scatter.md, Mock report; docs/checks/scatter.py): R2, n = 200, seed 1.
MOCK_Z = 2 * np.random.default_rng(1).random((200, 3)) - 1
MOCK_Y = r2_unit(MOCK_Z)


def test_spearman_with_average_ranks() -> None:
    """Spearman's rho with average ranks for ties, as scipy's."""
    rng = np.random.default_rng(0)
    x = rng.integers(0, 5, 40).astype(float)
    y = x**2 + rng.standard_normal(40)
    assert rank_correlation(x, y) == pytest.approx(stats.spearmanr(x, y).statistic, abs=1e-15)
    assert rank_correlation(np.arange(5.0), np.exp(np.arange(5.0))) == pytest.approx(1.0, abs=1e-15)
    assert rank_correlation(np.arange(5.0), -np.arange(5.0)) == pytest.approx(-1.0, abs=1e-15)


def test_rank_correlation_undefined_on_constant_y() -> None:
    """uncertainty.md, per diagnostic: rho is undefined (0/0) on a constant y."""
    assert math.isnan(rank_correlation(np.arange(4.0), np.full(4, 2.0)))


def test_binned_index_by_hand() -> None:
    """scatter.md: B groups of a stable sort, array_split sizes; eta^2; adjusted 1 - (1 - eta^2)(n - 1)/(n - B)."""
    x = np.array([5.0, 0, 3, 1, 4, 2, 6])
    y = np.array([3.0, 1, 2, 1, 4, 2, 5])
    # sorted by x: y = 1, 1, 2, 2, 4, 3, 5; groups of 3, 2, 2: means 4/3, 3, 4; ybar = 18/7
    ybar = 18 / 7
    between = 3 * (4 / 3 - ybar) ** 2 + 2 * (3 - ybar) ** 2 + 2 * (4 - ybar) ** 2
    total = math.fsum((y - ybar) ** 2)
    want = 1 - (1 - between / total) * 6 / 4
    assert binned_index(x, y, 3) == pytest.approx(want, rel=1e-14)


def test_binned_index_ties_keep_the_design_order() -> None:
    """A stable sort: tied x values keep the design's order, so the groups are the runs' first, then later."""
    x = np.zeros(4)
    y = np.array([1.0, 1.0, 3.0, 3.0])
    assert binned_index(x, y, 2) == pytest.approx(1.0)


def test_binned_index_undefined() -> None:
    """Undefined on a constant y (0/0), and with fewer than 2 distinct runs (n - B = 0)."""
    assert math.isnan(binned_index(np.arange(9.0), np.ones(9), 3))
    assert math.isnan(binned_index(np.arange(20.0), np.full(20, 0.1), 4))  # the mean rounds; still 0/0
    assert math.isnan(rank_correlation(np.arange(20.0), np.full(20, 0.1)))
    assert math.isnan(binned_index(np.array([0.5]), np.array([2.0]), 1))


def test_binned_index_can_be_negative() -> None:
    """scatter.md, step 5: reported as computed, not clipped."""
    rng = np.random.default_rng(3)
    values = [binned_index(rng.random(50), rng.random(50), 7) for _ in range(20)]
    assert min(values) < 0


def test_mock_report_point_estimates() -> None:
    """scatter.md, Mock report (R2, n = 200, seed 1), 4 significant digits; docs/checks/scatter.out."""
    B = math.isqrt(200)
    rho = [rank_correlation(MOCK_Z[:, j], MOCK_Y) for j in range(3)]
    S = [binned_index(MOCK_Z[:, j], MOCK_Y, B) for j in range(3)]
    assert [f"{v:.4g}" for v in rho] == ["0.4185", "0.02173", "-0.009447"]
    assert [f"{v:.4g}" for v in S] == ["0.2944", "0.4068", "-0.004922"]


def test_scaling_is_exact() -> None:
    """P6: y -> 2^40 y leaves rho and S unchanged, exactly."""
    for j in range(3):
        assert rank_correlation(MOCK_Z[:, j], 2.0**40 * MOCK_Y) == rank_correlation(MOCK_Z[:, j], MOCK_Y)
        assert binned_index(MOCK_Z[:, j], 2.0**40 * MOCK_Y, 14) == binned_index(MOCK_Z[:, j], MOCK_Y, 14)


def test_refusals() -> None:
    with pytest.raises(ValueError):
        binned_index(np.arange(4.0), np.arange(4.0), 0)
    with pytest.raises(ValueError):
        rank_correlation(np.arange(4.0), np.arange(3.0))


def test_r4b_wiggle_has_estimates() -> None:
    """0035; scatter.md, Expected answers: R4b, 2.5 + 1e-12 sin(40 (a + b + c)), is not constant: rho and S are
    finite for each model parameter."""
    Z = 2 * np.random.default_rng(0).random((200, 3)) - 1
    y = 2.5 + 1e-12 * np.sin(40 * Z.sum(axis=1))
    for j in range(3):
        assert math.isfinite(rank_correlation(Z[:, j], y)) and math.isfinite(binned_index(Z[:, j], y, 14))


# Record 0076: the column-wise forms scatter's bootstrap calls


def test_average_ranks_are_scipys() -> None:
    """``average_ranks`` gives scipy's "average" ranks exactly, row by row, ties included."""
    rng = np.random.default_rng(3)
    for _ in range(100):
        A = rng.integers(0, 6, (int(rng.integers(1, 5)), int(rng.integers(1, 40)))).astype(float)
        assert np.array_equal(average_ranks(A), stats.rankdata(A, axis=1))


def test_the_column_wise_forms_equal_the_scalar_ones_at_every_offset() -> None:
    """``rank_correlations`` and ``binned_indices`` give each column's ``rank_correlation`` and ``binned_index``, bit
    for bit, ties and a constant column included, and the same bytes at 8 memory offsets (P4; record 0068 item 1)."""
    rng = np.random.default_rng(4)
    keep: list[object] = []
    for n in (10, 37, 200):
        X = rng.random((n, 3))
        X[:, 1] = np.round(X[:, 1], 1)  # ties
        X[:, 2] = 0.5  # constant: rho is NaN
        y = np.sin(7 * X[:, 0]) + X[:, 1]
        B = math.isqrt(n)
        rho, S = rank_correlations(X, y), binned_indices(X, y, B)
        for j in range(3):
            assert np.array_equal(rho[j], rank_correlation(X[:, j], y), equal_nan=True)
            assert S[j] == binned_index(X[:, j], y, B)
        assert math.isnan(rho[2]) and not math.isnan(S[2])
        assert len({rank_correlations(at_offset(X, o, keep), at_offset(y, o, keep)).tobytes() for o in OFFSETS}) == 1
        assert len({binned_indices(at_offset(X, o, keep), at_offset(y, o, keep), B).tobytes() for o in OFFSETS}) == 1
    assert np.isnan(rank_correlations(rng.random((9, 2)), np.full(9, 0.1))).all()
    assert np.isnan(binned_indices(rng.random((9, 2)), np.full(9, 0.1), 3)).all()
