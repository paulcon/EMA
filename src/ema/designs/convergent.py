"""The convergent design (designs.md, Convergent; G7, G8, G18; 0047)."""

import math
import re
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any

import numpy as np

from ema.designs._common import check_identity, read_params, rows, sampler_of, space_of
from ema.designs.generators import MAX_DESIGN_POINTS, register
from ema.types._values import as_int
from ema.types.design import Design, DesignIdentity
from ema.types.errors import DesignTooLarge, RequestError
from ema.types.identity import decimal_fraction
from ema.types.model import ModelSpec

#: The float estimate of n_min f^l is trusted only when the interval of this relative width around it holds no
#: integer; its error is below 200 ulps (about 4.4e-14), so the size is the exact rule's (0067, review round 1).
_GUARD = 1e-12
#: Levels estimated together, as one array.
_CHUNK = 1 << 16
#: Beyond this, the last level's size is refused without being computed (its estimate, from the logarithms).
_LOG_HUGE = 62 * math.log(2)


#: A decimal number's text (0047): digits, an optional point, an optional exponent; no spaces, no "1/3".
_DECIMAL = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
#: Below 10^this, alpha is read only as "tiny": n_1 >= alpha^(-1/r) > 10^1000, far over the cap, and its exact
#: fraction would be about as many digits as its exponent's value ("1e-10000000"), so it isn't built (0067).
_TINY_EXPONENT = -1000
#: An echoed alpha text is cut to this many characters.
_ECHO = 40


def _echo(value: Any) -> str:
    """Return alpha as given, cut to ``_ECHO`` characters, for a message."""
    text = repr(value) if isinstance(value, str) else str(value)
    return text if len(text) <= _ECHO else text[:_ECHO] + "…"


def _alpha(value: Any) -> Fraction | None:
    """Return alpha as the decimal it is written as (0047); None when it is below 10^-1000.

    The text is read first as a ``Decimal``, whose exponent is kept as an integer, not expanded: the range and the
    size of the exponent are checked before any ``Fraction`` is built, so no text costs more than its length.
    """
    if isinstance(value, np.floating):
        value = float(value)
    not_a_number = RequestError(f"convergent: alpha must be a decimal number in (0, 1), not {_echo(value)}")
    if isinstance(value, bool) or not isinstance(value, (float, int, str)):
        raise not_a_number
    if isinstance(value, str) and not _DECIMAL.fullmatch(value):
        raise not_a_number
    try:
        number = Decimal(repr(value) if isinstance(value, float) else value)
    except (InvalidOperation, ValueError):  # an exponent past Decimal's 10^18
        raise not_a_number from None
    if not (number.is_finite() and 0 < number < 1):
        raise RequestError(f"convergent: alpha must be in (0, 1), not {_echo(value)}")
    if number.adjusted() < _TINY_EXPONENT:
        return None
    return decimal_fraction(value)


def _power_bounds(num: int, den: int, level: int, bits: int) -> tuple[int, int]:
    """Return integers lo <= (num/den)^level 2^bits <= hi, by squaring in fixed point, rounding down and up."""
    one = 1 << bits
    base_lo, base_hi = (num << bits) // den, -(-(num << bits) // den)
    lo = hi = one
    while level:
        if level & 1:
            lo, hi = (lo * base_lo) >> bits, -(-(hi * base_hi) >> bits)
        level >>= 1
        if level:
            base_lo, base_hi = (base_lo * base_lo) >> bits, -(-(base_hi * base_hi) >> bits)
    return lo, hi


def _ceil_size(n_min: int, factor: Fraction, level: int, bits: int = 128) -> int:
    """Return ceil(n_min factor^level), exactly, at a cost that grows with log(level), not level.

    For a small power, the exact integers; otherwise the bounds of ``_power_bounds``, refined until both round
    up to the same integer, from ``bits`` bits, doubling. That ends: here den >= 2 (with den = 1 the size would
    be at least n_min 2^64, which no caller asks for), so den^level > n_min, and n_min factor^level, in lowest
    terms, isn't an integer.
    """
    num, den = factor.numerator, factor.denominator
    if den == 1 or level < 64 or level * (num.bit_length() + den.bit_length()) <= 8192:
        return -(-n_min * num**level // den**level)
    while True:
        lo, hi = _power_bounds(num, den, level, bits)
        size_lo, size_hi = -(-(n_min * lo) >> bits), -(-(n_min * hi) >> bits)
        if size_lo == size_hi:
            return size_lo
        bits *= 2


def _log_factor(factor: Fraction) -> float:
    """ln(factor) as a double, to a few ulps (log1p near 1, where ln num - ln den would cancel)."""
    if factor < 2:
        return math.log1p(float(factor - 1))
    return math.log(float(factor)) if factor < 2**1000 else math.inf


def _estimates(n_min: int, factor: Fraction, log_factor: float, start: int, stop: int) -> Iterator[int]:
    """Yield levels [start, stop)'s sizes in turn, each the exact rule's.

    A float estimate where that is safe, exact arithmetic elsewhere, computed only when reached, so a caller that
    stops early pays for no more.
    """
    levels = np.arange(start, stop, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        x = n_min * np.exp(levels * log_factor)
        low, high = np.ceil(x * (1.0 - _GUARD)), np.ceil(x * (1.0 + _GUARD))
    safe = ((low == high) & (x <= 2.0**52)).tolist()
    estimates = np.where(safe, high, 0.0).astype(np.int64).tolist()
    for i, (n_l, sure) in enumerate(zip(estimates, safe, strict=True)):
        yield n_l if sure else _ceil_size(n_min, factor, start + i)


def _shown(n: int) -> str:
    return f"{n:,}" if n < 2**62 else f"more than 2^{n.bit_length() - 1}"


class Convergent:
    """Levels 0 … L, nested: level l is the first n_l points of one uniform design of n_L points.

    The levels share the seed, space, and sampler. Its parameters are ``n_min`` (an integer >= 1), ``alpha`` (the
    error factor, in (0, 1), read as the decimal it is written as: its decimal string; 0047), and ``level``
    (L >= 0).

    The sizes are n_l = ceil(n_min alpha^(-l/r)), each from n_min, rounded up with no tolerance; r is the
    sampler's rate, and 1/r must be an integer (0065). Each is the exact rational rule's, computed cheaply: a
    float estimate where no integer is near it, exact arithmetic elsewhere (0067). Refused: alpha outside (0, 1),
    sizes not strictly increasing, and a sampler that isn't nested (G8); and, as too large, n_min + L over the
    cap, since strictly increasing sizes give n_L >= n_min + L, and alpha below 10^-1000 with L >= 1 (G5).
    """

    name: str = "convergent"
    version: str = "1"

    def levels(self, identity: DesignIdentity, spec: ModelSpec) -> tuple[tuple[int, ...], int]:
        """Return the level sizes n_0 … n_L, and n_L; the sizes stop at the first one over the cap."""
        check_identity(self.name, self.version, identity, uses_sampler=True)
        sampler = sampler_of(self.name, identity)
        space_of(self.name, identity, spec)
        params = read_params(self.name, identity.params, ("n_min", "alpha", "level"))
        n_min = as_int(params["n_min"], "n_min", 1)
        level = as_int(params["level"], "level", 0)
        alpha = _alpha(params["alpha"])
        if not sampler.nested:
            raise RequestError(f"convergent: sampler {sampler.name} isn't nested, so its levels can't share points")
        k = 1 / Fraction(sampler.rate)
        if k.denominator != 1:
            raise RequestError(
                f"convergent: sampler {sampler.name} has rate r = {sampler.rate}, and 1/r isn't an "
                "integer; its rounding rule comes with its record"
            )
        if n_min + level > MAX_DESIGN_POINTS:
            raise DesignTooLarge(
                f"the design would have at least n_min + level = {n_min + level:,} points if its sizes strictly "
                f"increase, over the cap of {MAX_DESIGN_POINTS:,}"
            )
        if alpha is None:  # alpha < 10^-1000
            if level == 0:
                return (n_min,), n_min
            raise DesignTooLarge(
                f"the design has more than 10^{-_TINY_EXPONENT * int(k)} points: alpha = {_echo(params['alpha'])} is below "
                f"10^{_TINY_EXPONENT}, so its level 1 alone has n_min alpha^(-{k}) points, over the cap of "
                f"{MAX_DESIGN_POINTS:,}"
            )
        factor = (1 / alpha) ** int(k)
        log_factor = _log_factor(factor)
        sizes: list[int] = []
        start = 0
        while start <= level and (not sizes or sizes[-1] <= MAX_DESIGN_POINTS):
            stop = min(level + 1, start + _CHUNK)
            for n_l in _estimates(n_min, factor, log_factor, start, stop):
                if sizes and n_l <= sizes[-1]:
                    shown = ", ".join(map(str, [*sizes[-5:], n_l]))
                    raise RequestError(
                        f"convergent: the sizes {'..., ' if len(sizes) > 5 else ''}{shown} aren't strictly "
                        f"increasing (n_min = {n_min}, alpha = {_echo(params['alpha'])}); raise n_min or lower alpha"
                    )
                sizes.append(n_l)
                if n_l > MAX_DESIGN_POINTS:
                    break
            start = stop
        if len(sizes) == level + 1:
            return tuple(sizes), sizes[-1]
        if math.log(n_min) + level * log_factor > _LOG_HUGE:
            raise DesignTooLarge(
                f"the design has more than 2^62 points: its level {len(sizes) - 1} alone has "
                f"{_shown(sizes[-1])}, over the cap of {MAX_DESIGN_POINTS:,}"
            )
        return tuple(sizes), _ceil_size(n_min, factor, level)

    def size(self, identity: DesignIdentity, spec: ModelSpec) -> int:
        """n_L (G3)."""
        return self.levels(identity, spec)[1]

    def build(self, identity: DesignIdentity, spec: ModelSpec, start: int = 0, stop: int | None = None) -> Design:
        """Rows [start, stop) of the uniform design of n_L points, with the level sizes (G7)."""
        sizes, n = self.levels(identity, spec)
        start, stop = rows(n, start, stop)
        space = space_of(self.name, identity, spec)
        seed = check_identity(self.name, self.version, identity, uses_sampler=True)
        unit = sampler_of(self.name, identity).unit_rows(seed, len(space.varied(spec)), start, stop)
        return Design(
            identity=identity,
            points=space.from_cube(spec, unit),
            replicates=np.zeros(stop - start, dtype=np.int64),
            levels=sizes,
            lines=None,
        )


register(Convergent())
