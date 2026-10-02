"""The toy function (tests/models/README.md)."""

from helper import scale


def f(a, b):
    y = a + 2 * b + scale()
    return {"y": y, "z": y + 1}
