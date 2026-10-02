"""A function file that loading must read, never import (T4, M17): importing it writes a marker file."""

import os

import listed
import numpy as np
import pkg.sub
from helper import twice

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "IMPORTED"), "w") as marker:
    marker.write("imported")


def f(a):
    return twice(listed.one() * a) + pkg.sub.zero() + float(np.zeros(1)[0])
