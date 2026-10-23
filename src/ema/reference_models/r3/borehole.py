"""R3 (reference_models.md): the water flow through a borehole, in m³/yr (Harper and Gupta, 1983).

Ported from EMA v1 at v1-final: src/ema/testfunctions/library.py (borehole), reviewed against reference_models.md.
"""

import numpy as np


def f(rw, r, Tu, Hu, Tl, Hl, L, Kw):
    log_ratio = np.log(r / rw)
    return float(2 * np.pi * Tu * (Hu - Hl) / (log_ratio * (1 + 2 * L * Tu / (log_ratio * rw**2 * Kw) + Tu / Tl)))
