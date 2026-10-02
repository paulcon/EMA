"""Reading numbers from a spec, a space, or a design's parameters (0061 item 6, 0065 item 2).

A value in model parameter units, or a direction, is refused unless it is a finite number, a bool included,
before it becomes a double; an integer parameter is refused unless it is an integer (an integral float is read
as one), never a bool. Private to layers 0 and 1.
"""

import math
from typing import Any

import numpy as np

from ema.types.errors import EMAError, RequestError


def is_number(value: Any) -> bool:
    """Tell whether ``value`` is an int or a float (numpy's included), never a bool."""
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_))


def as_double(value: Any, what: str, error: type[EMAError] = RequestError) -> float:
    """Return ``value`` as a double; raise ``error`` naming ``what`` when it isn't a finite number."""
    if not is_number(value) or not math.isfinite(float(value)):
        raise error(f"{what}: {value!r} is not a finite number")
    return float(value)


def as_int(value: Any, what: str, minimum: int, error: type[EMAError] = RequestError) -> int:
    """Return ``value`` as an integer >= ``minimum``; raise ``error`` naming ``what`` otherwise."""
    if is_number(value) and math.isfinite(float(value)) and float(value) == int(value):
        number = int(value)
        if number >= minimum:
            return number
    raise error(f"{what} must be an integer >= {minimum}, not {value!r}")


def finite_doubles(values: Any, what: str) -> tuple[float, ...]:
    """Return ``values`` as a tuple of doubles; raise ``ValueError`` naming ``what`` unless each is finite.

    For EMA's own records (a run's point, a run key's, the test run's), where a bad value is a mistake in EMA's
    code, not a user's request (record 0070).
    """
    out = tuple(float(v) if is_number(v) else math.nan for v in values)
    if not all(math.isfinite(v) for v in out):
        raise ValueError(f"{what} must be finite numbers: {tuple(values)!r}")
    return out
