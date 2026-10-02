"""A local package, not listed (M17); importing it writes a marker file (T4)."""

import os

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "IMPORTED_PKG"), "w") as m:
    m.write("imported")
