import numpy as np
import json

class Key:
    """Bit-string key material. Mirrors cascade-cpp's Key class, using a
    numpy array instead of manual 64-bit word packing (unnecessary in Python)."""

    def __init__(self, nr_bits=None, bits=None, seed=None):
        if bits is not None:
            self.bits = np.array(bits, dtype=np.uint8)
        else:
            rng = np.random.default_rng(seed)
            self.bits = rng.integers(0, 2, size=nr_bits, dtype=np.uint8)

    def copy(self):
        return Key(bits=self.bits.copy())

    def get_nr_bits(self):
        return len(self.bits)

    def get_bit(self, bit_nr):
        return int(self.bits[bit_nr])

    def set_bit(self, bit_nr, value):
        self.bits[bit_nr] = value

    def flip_bit(self, bit_nr):
        self.bits[bit_nr] ^= 1

    def apply_noise(self, bit_error_rate, seed=None):
        """Flip a bit_error_rate fraction of bits, chosen uniformly at random."""
        rng = np.random.default_rng(seed)
        n = len(self.bits)
        n_errors = int(round(bit_error_rate * n))
        if n_errors == 0:
            return
        error_positions = rng.choice(n, size=n_errors, replace=False)
        self.bits[error_positions] ^= 1

    def compute_range_parity(self, start_bit_nr, end_bit_nr):
        return int(np.bitwise_xor.reduce(self.bits[start_bit_nr:end_bit_nr + 1]))

    def nr_bits_different(self, other_key):
        assert self.get_nr_bits() == other_key.get_nr_bits()
        return int(np.sum(self.bits != other_key.bits))

    def to_string(self):
        return ''.join(str(b) for b in self.bits)

def key_from_sifted_json(path, bits_field):
    """Load a sifted-bits JSON file (as saved by Alice/Bob) and construct
    a Key object from it. bits_field is 'alice_bits' or 'bob_bits'."""
    with open(path) as f:
        data = json.load(f)
    bits = data[bits_field]
    return Key(bits=bits), data["matching_indices"]