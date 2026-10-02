"""Spawned random streams, shared by ``ema.designs`` and ``ema.diagnostics`` (architecture.md §3; P4)."""

import numpy as np


def spawned(seed: int, *key: int) -> np.random.Generator:
    """Make the stream for a seed and a spawn key: ``Generator(PCG64(SeedSequence(seed, spawn_key=key)))``.

    Random lines draw line j from key ``(j,)`` (designs.md, Random lines); a diagnostic's own draws use a key
    of its tag, at least 2**32 (diagnostics/shared.md).

    Parameters
    ----------
    seed
        The request's seed, an integer >= 0.
    *key
        The spawn key.

    Returns
    -------
    numpy.random.Generator
        A new generator, independent of every other key's.
    """
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=key)))
