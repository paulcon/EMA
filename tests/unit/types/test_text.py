"""``fmt`` (S3, 0044) and ``duration`` (U2; 0061, 0062, 0063)."""

import math

import pytest

from ema.types.text import duration, fmt


@pytest.mark.parametrize(
    ("x", "text"),
    [
        (0.0, "0"),
        (1.0, "1"),
        (-0.559, "-0.559"),
        (1234.5678, "1235"),
        (12345.678, "1.235e+04"),
        (0.000123456, "0.0001235"),
        (2.0 / 3.0, "0.6667"),
        (-1e-12, "-1e-12"),
    ],
)
def test_fmt_four_significant_digits_ascii_minus(x, text):
    assert fmt(x) == text
    assert "−" not in fmt(x)


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        # The eleven known answers (architecture.md §3; 0063 item 3).
        (0.004, "under 0.01 s"),
        (0.04, "about 0.04 s"),
        (0.2, "about 0.2 s"),
        (2.5, "about 3 s"),
        (4.4, "about 4 s"),
        (9.96, "about 10 s"),
        (59.7, "about 1 min"),
        (90, "about 2 min"),
        (3599, "about 1 h"),
        (7200, "about 2 h"),
        (11_520, "about 3 h 12 min"),
        # More edges of the same rule.
        (0.0, "under 0.01 s"),
        (0.0099999, "under 0.01 s"),
        (0.01, "about 0.01 s"),
        (0.095, "about 0.1 s"),
        (0.25, "about 0.3 s"),
        (1.0, "about 1 s"),
        (12.5, "about 13 s"),
        (2400, "about 40 min"),
        (4800, "about 1 h 20 min"),
        (86_400, "about 24 h"),
    ],
)
def test_duration(seconds, text):
    assert duration(seconds) == text


@pytest.mark.parametrize("bad", [-1.0, math.nan, math.inf])
def test_duration_refuses_what_isnt_a_time(bad):
    with pytest.raises(ValueError):
        duration(bad)
