from galois import GF2
import numpy as np

import randextract
from randextract import (
    RandomnessExtractor,
    ToeplitzHashing
)

# alice_reconciled_key = 
# bob_reconciled_key = 

# out_len = calculate_finite_key_length(
#     qber=qber,
#     key_length=len(alice_reconciled_key)
# )

# ext = RandomnessExtractor.create(
#     extractor_type="toeplitz",
#     input_length=len(alice_reconciled_key),
#     output_length=out_len
# )

# ext_seed = GF2.Random(ext.seed_length)

# alice_final_key = ext.extract(
#     GF2(alice_reonciled_key),
#     ext_seed
# )

# bob_final_key = ext.extract(
#     GF2(bob_reconciled_key),
#     ext_seed
# )

alice_key = [1,0,1,1,0,1,0,1,1,0,0,1]
key = GF2(alice_key)

print(key)
print(type(key))

out_len = 8

ext = RandomnessExtractor.create(
    extractor_type="toeplitz",
    input_length=len(key),
    output_length=out_len
)

ext_seed = GF2.Random(ext.seed_length)

print(ext.seed_length)
print(ext_seed)

final_key = ext.extract(
    key,
    ext_seed
)

print(final_key)

print(ext.extract(key,ext_seed))

alice_key[3] ^= 1
key = GF2(alice_key)

print(key)
print(type(key))

out_len = 8

ext = RandomnessExtractor.create(
    extractor_type="toeplitz",
    input_length=len(key),
    output_length=out_len
)

ext_seed = GF2.Random(ext.seed_length)

print(ext.seed_length)
print(ext_seed)

final_key = ext.extract(
    key,
    ext_seed
)

print(final_key)

print(ext.extract(key,ext_seed))

def make_fake_input(n_bits=1000, seed=42):
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n_bits)
    return bits

protocol = BB84Protocol()

alice_bits = make_fake_input(1000, 42)
bob_bits = alice_bits.copy()


