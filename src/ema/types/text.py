"""Numbers and durations as users read them (S3, 0044; U2; 0061, 0062, 0063)."""

import math
from fractions import Fraction


def fmt(x: float) -> str:
    """Write a computed number as every report does: four significant digits, with an ASCII minus (S3, 0044).

    Parameters
    ----------
    x
        The stored double.

    Returns
    -------
    str
        ``format(x, ".4g")``.

    Examples
    --------
    >>> fmt(-0.5590169943749475)
    '-0.559'
    >>> fmt(12345.678)
    '1.235e+04'
    """
    return format(x, ".4g")


def _half_up(x: Fraction) -> int:
    """Round ``x`` >= 0 to an integer, half up."""
    return math.floor(x + Fraction(1, 2))


def _decimal(q: int, e: int) -> str:
    """Write q * 10**e as decimal text, for 1 <= q <= 9 or e >= 0."""
    if e >= 0:
        return str(q * 10**e)
    return "0." + "0" * (-e - 1) + str(q)


def duration(seconds: float) -> str:
    """Write a duration as the price does (U2): one rule, rounded first, then the unit chosen (0061-0063).

    Under 10 s, one significant digit; under a minute, whole seconds; under an hour, whole minutes; otherwise
    hours and whole minutes. Each rounding is half up on the decimal ``repr`` of the value, and a value that
    rounds to its unit's limit is written in the next unit. Below 0.01 s, before rounding: "under 0.01 s".

    Parameters
    ----------
    seconds
        A finite, non-negative number of seconds.

    Returns
    -------
    str
        "under 0.01 s", or "about ..." in s, min, or h and min.

    Raises
    ------
    ValueError
        For a negative or non-finite value.

    Examples
    --------
    >>> duration(9.96), duration(59.7), duration(3599), duration(11_520)
    ('about 10 s', 'about 1 min', 'about 1 h', 'about 3 h 12 min')
    """
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"a duration must be a finite number of seconds >= 0, not {seconds!r}")
    value = Fraction(repr(float(seconds)))
    if value < Fraction(1, 100):
        return "under 0.01 s"
    if value < 10:
        e = 0
        while Fraction(10) ** e > value:
            e -= 1
        while Fraction(10) ** (e + 1) <= value:
            e += 1
        q = _half_up(value / Fraction(10) ** e)
        if q == 10:
            q, e = 1, e + 1
        if Fraction(q) * Fraction(10) ** e < 10:
            return f"about {_decimal(q, e)} s"
    whole = _half_up(value)
    if whole < 60:
        return f"about {whole} s"
    minutes = _half_up(value / 60)
    if minutes < 60:
        return f"about {minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"about {hours} h {rest} min" if rest else f"about {hours} h"
