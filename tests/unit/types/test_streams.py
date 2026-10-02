"""``spawned`` (architecture.md §3; designs.md, Random lines; P4)."""

import numpy as np

from ema.types.streams import spawned


def test_spawned_is_pcg64_from_a_seed_sequence_with_a_spawn_key():
    for seed, key in ((0, (0,)), (1, (3,)), (20261001, (2**32, 5)), (7, ())):
        expected = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed, spawn_key=key)))
        assert np.array_equal(spawned(seed, *key).random(5), expected.random(5))


def test_keys_give_independent_streams():
    assert not np.array_equal(spawned(0, 1).random(4), spawned(0, 2).random(4))
    assert not np.array_equal(spawned(0, 1).random(4), spawned(1, 1).random(4))
