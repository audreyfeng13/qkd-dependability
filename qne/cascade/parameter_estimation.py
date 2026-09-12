"""
Parameter estimation (PE) sampling for the real-channel QKD pipeline.

Splits a freshly sifted key pair into:
  - a PE sample (k bits), revealed and compared to estimate QBER, then
    discarded and never used for key generation, and
  - a generation string (n = m - k bits), used for error correction and
    privacy amplification.

This mirrors the m = n + k split assumed by the finite-key security bound
of Tomamichel and Leverrier (arXiv:1506.08458). Critically, the PE sample
must be disjoint from the generation string -- reusing PE data for key
generation invalidates the entropy bound, since Eve has already seen
those bits (Tupkary et al., arXiv:2502.10340, Sec. 3.2.2/5.1.1).

The PE index subset is derived from a shared seed known to both parties,
rather than transmitted as an explicit index list -- functionally
equivalent to a live announcement, since both parties can independently
reconstruct the identical subset, but avoiding an extra network round
trip. This is a standard formulation (see Tupkary et al., Sec. 3.2.2).
"""
import numpy as np
from qne.cascade.key import Key


def split_pe_and_generation(alice_key: Key, bob_key: Key, sample_fraction: float, seed: int):
    """
    Given full sifted keys held by Alice and Bob (same length m, same bit
    order/index correspondence), select k = ceil(sample_fraction * m)
    indices as the PE sample, compare them to compute QBER, and return
    the REMAINING n = m - k bits per party as the generation string.
    """
    m = alice_key.get_nr_bits()
    if bob_key.get_nr_bits() != m:
        raise ValueError(f"Alice ({m}) and Bob ({bob_key.get_nr_bits()}) "
                          f"key lengths must match before PE split")

    k = max(1, int(np.ceil(sample_fraction * m)))
    if k >= m:
        raise ValueError(f"sample_fraction={sample_fraction} leaves no bits "
                          f"for generation (k={k} >= m={m})")

    rng = np.random.default_rng(seed)
    pe_indices = np.sort(rng.choice(m, size=k, replace=False))
    gen_mask = np.ones(m, dtype=bool)
    gen_mask[pe_indices] = False
    gen_indices = np.nonzero(gen_mask)[0]

    # QBER measured ONLY over the disjoint PE sample.
    errors = int(np.sum(alice_key.bits[pe_indices] != bob_key.bits[pe_indices]))
    qber = errors / k

    alice_gen = Key(bits=alice_key.bits[gen_indices].copy())
    bob_gen = Key(bits=bob_key.bits[gen_indices].copy())

    return {
        "alice_gen": alice_gen, "bob_gen": bob_gen,
        "qber": qber, "m": m, "k": k, "n": m - k,
        "pe_indices": pe_indices.tolist(), "gen_indices": gen_indices.tolist(),
    }