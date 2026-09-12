import numpy as np

class Shuffle:
    """A random permutation of bit positions, used to re-randomize which bits
    fall into which block on each cascade iteration."""

    def __init__(self, nr_bits, seed=None):
        self.nr_bits = nr_bits
        rng = np.random.default_rng(seed)
        self.perm = rng.permutation(nr_bits)          # shuffled -> orig
        self.inv_perm = np.argsort(self.perm)          # orig -> shuffled

    def shuffle_to_orig(self, shuffled_bit_nr):
        return int(self.perm[shuffled_bit_nr])

    def orig_to_shuffle(self, orig_bit_nr):
        return int(self.inv_perm[orig_bit_nr])


class ShuffledKey:
    """A view of a Key through a Shuffle's permutation -- lets Block code
    address bits by their shuffled position without copying the underlying key."""

    def __init__(self, key, shuffle):
        self.key = key
        self.shuffle = shuffle

    def get_shuffle(self):
        return self.shuffle

    def get_bit(self, shuffled_bit_nr):
        return self.key.get_bit(self.shuffle.shuffle_to_orig(shuffled_bit_nr))

    def compute_range_parity(self, start_bit_nr, end_bit_nr):
        parity = 0
        for b in range(start_bit_nr, end_bit_nr + 1):
            parity ^= self.get_bit(b)
        return parity