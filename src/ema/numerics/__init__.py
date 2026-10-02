"""Layer 1: pure numerics (architecture.md §4).

The basis, the Gram spectrum, fits, Sobol indices, scatter's estimates, interval methods, and P6's tolerance
function: pure functions of arrays (AR2), every random draw from a stream they are given. No vector-vector BLAS:
inner products, norms, and matrix-vector products go through ``_vector`` (record 0068 item 1). Importing the
package registers the ``total_degree`` basis and the ``bootstrap`` interval method.
"""

from ema.numerics import basis, fitting, gram, intervals, sobol, stats, tolerance

__all__ = ["basis", "fitting", "gram", "intervals", "sobol", "stats", "tolerance"]
