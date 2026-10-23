"""R5 (reference_models.md): y = a + b², z = a - b, failing in known regions.

a + b > 1: raises ValueError("no convergence") (failed, error); a < -0.8 and b < -0.8: sleeps 5 s (failed, timeout,
with the spec's timeout_s of 0.2); b > 0.8, elsewhere: z is NaN (missing, with its reason).
"""

import math
import time


def f(a, b):
    if a + b > 1:
        raise ValueError("no convergence")
    if a < -0.8 and b < -0.8:
        time.sleep(5.0)
    return {"y": a + b**2, "z": math.nan if b > 0.8 else a - b}
