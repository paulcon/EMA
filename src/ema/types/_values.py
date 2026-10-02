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


def _finite(value: Any) -> bool:
    """Tell whether a number is finite as a double; an integer too large for one isn't (0069, review item 7)."""
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def as_double(value: Any, what: str, error: type[EMAError] = RequestError) -> float:
    """Return ``value`` as a double; raise ``error`` naming ``what`` when it isn't a finite number."""
    if not is_number(value) or not _finite(value):
        raise error(f"{what}: {value!r} is not a finite number")
    return float(value)


def as_int(value: Any, what: str, minimum: int, error: type[EMAError] = RequestError) -> int:
    """Return ``value`` as an integer >= ``minimum``; raise ``error`` naming ``what`` otherwise."""
    if is_number(value) and _finite(value) and float(value) == int(value):
        number = int(value)
        if number >= minimum:
            return number
    raise error(f"{what} must be an integer >= {minimum}, not {value!r}")
