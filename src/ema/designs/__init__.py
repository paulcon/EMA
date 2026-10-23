"""Layer 1: samplers and design generators (designs.md; architecture.md §4).

Pure functions of a design's identity and a model spec (AR2): every random draw comes from the identity's seed.
Importing the package registers the ``random`` sampler and the six generators: ``point``, ``uniform``,
``convergent``, ``lines`` (given lines), ``coordinate_lines``, and ``random_lines``.
"""

from ema.designs import convergent, generators, lines, point, samplers, uniform

__all__ = ["convergent", "generators", "lines", "point", "samplers", "uniform"]
