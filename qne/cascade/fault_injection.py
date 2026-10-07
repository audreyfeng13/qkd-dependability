"""
Silent Data Corruption (SDC) fault injection for classical BB84 post-processing.

Models five independent, mechanistically distinct injection points:
  1. reconciliation_state    -- corrupts Bob's key mid-Cascade, right after a real
                                 correction is applied. Can only ever touch a bit
                                 Cascade is actively correcting, and once it fires
                                 it's permanent -- no later pass goes looking for it.
  2. arbitrary_bit            -- corrupts Bob's key at a uniformly random position,
                                 once per Cascade pass, independent of whether
                                 Cascade is touching anything. Unlike reconciliation_state,
                                 this CAN be caught by a later pass's parity check.
  3. toeplitz_matrix          -- corrupts the hashing matrix during PA's multiplication
  4. final_key                -- corrupts the already-correct final key, after PA completes
  5. verification_digest      -- corrupts the post-PA verification hash digest itself,
                                  after it has been correctly computed from the
                                  (possibly already-corrupted) final key

Each is independently toggleable via its own probability, so isolated and
joint fault studies use the same object.
"""

import numpy as np
from collections import Counter
from galois import GF2


class SDCFaultInjector:
    def __init__(self, toeplitz_matrix_prob=0.0, final_key_prob=0.0,
                 reconciliation_state_prob=0.0, verification_digest_prob=0.0,
                 arbitrary_bit_prob=0.0, seed=None):
        self.toeplitz_matrix_prob = toeplitz_matrix_prob
        self.final_key_prob = final_key_prob
        self.reconciliation_state_prob = reconciliation_state_prob
        self.verification_digest_prob = verification_digest_prob
        self.arbitrary_bit_prob = arbitrary_bit_prob
        self.rng = np.random.default_rng(seed)
        self.injected_faults = []   # log of every fault that actually fired

    # --- 1. Reconciliation state ---
    def maybe_flip_reconciliation_state_bit(self, key_obj, bit_nr, context=""):
        """Call from inside Reconciliation.correct_orig_key_bit(), right after
        the legitimate correction, to model a fault striking mid-Cascade."""
        if self.rng.random() < self.reconciliation_state_prob:
            key_obj.flip_bit(bit_nr)
            self.injected_faults.append(("reconciliation_state", bit_nr, context))

    # --- 2. Arbitrary bit (genuinely random SDC, independent of correction path) ---
    def maybe_flip_arbitrary_bit(self, reconciliation, context=""):
        """Call from Reconciliation.reconcile(), once per pass, BEFORE that
        pass's Iteration is constructed. Flips a uniformly random bit in
        Bob's live key buffer, independent of whether Cascade is currently
        touching it -- unlike maybe_flip_reconciliation_state_bit, this can
        land on ANY bit:
          - one that's currently correct -> introduces a brand-new error
          - one that's currently a still-uncorrected real error -> a binary
            flip on a wrong bit necessarily makes it match Alice's bit, so
            this accidentally FIXES it rather than breaking anything.
        Both outcomes are legitimate; the predictive model accounts for the
        split between them, so this method doesn't need to special-case it.
        """
        if self.rng.random() >= self.arbitrary_bit_prob:
            return
        bit_nr = int(self.rng.integers(0, reconciliation.nr_key_bits))
        reconciliation.reconciled_key.flip_bit(bit_nr)
        # Only PRE-EXISTING iterations need their cached block parities
        # updated -- the iteration for the pass about to start hasn't been
        # constructed yet, so it will read the already-corrupted key directly
        # when it computes its own initial block parities.
        for iteration in reconciliation.iterations:
            iteration.flip_parity_in_all_blocks_containing_bit(bit_nr)
        self.injected_faults.append(("arbitrary_bit", bit_nr, context))

    # --- 3. Toeplitz matrix ---
    def toeplitz_extract_with_fault(self, ext, input_gf2, seed_gf2, context=""):
        """Explicit matrix-based Toeplitz extraction (via ext.to_matrix()),
        with a possible fault injected into one matrix entry before the
        multiplication. Returns a plain numpy array (the final key bits)."""
        T = ext.to_matrix(seed_gf2)
        T_arr = np.array(T).copy()

        if self.rng.random() < self.toeplitz_matrix_prob:
            i = int(self.rng.integers(0, T_arr.shape[0]))
            j = int(self.rng.integers(0, T_arr.shape[1]))
            T_arr[i, j] ^= 1
            self.injected_faults.append(("toeplitz_matrix", (i, j), context))

        T_corrupted = GF2(T_arr)
        output = T_corrupted @ input_gf2
        return np.array(output)

    def fast_toeplitz_extract_with_fault(self, ext, input_gf2, seed_gf2, context=""):
        """Mathematically equivalent to toeplitz_extract_with_fault, but avoids
        ever materializing the full Toeplitz matrix -- uses randextract's fast
        extraction path, then applies the algebraic effect of a matrix-entry
        flip directly to the correct output (flipping T[i,j] XORs input[j]
        into output row i). Use this for real-scale output lengths, where
        to_matrix()'s per-cell construction is prohibitively slow."""
        input_arr = np.array(input_gf2)
        correct_output = np.array(ext.extract(input_gf2, seed_gf2)).copy()

        if self.rng.random() < self.toeplitz_matrix_prob:
            i = int(self.rng.integers(0, len(correct_output)))
            j = int(self.rng.integers(0, len(input_arr)))
            correct_output[i] ^= int(input_arr[j])
            self.injected_faults.append(("toeplitz_matrix", (i, j), context))

        return correct_output

    # --- 4. Final key ---
    def maybe_flip_final_key_bit(self, output_arr, context=""):
        """Call immediately after a correct extraction, on the final key
        array, to model corruption of already-correct key material (e.g.
        an SEU in memory holding the key post-PA)."""
        output_arr = output_arr.copy()
        if self.rng.random() < self.final_key_prob:
            idx = int(self.rng.integers(0, len(output_arr)))
            output_arr[idx] ^= 1
            self.injected_faults.append(("final_key", idx, context))
        return output_arr

    # --- 5. Verification digest ---
    def maybe_flip_verification_digest_bit(self, digest_arr, context=""):
        """Call immediately after computing the post-PA verification hash
        digest, on the digest array itself -- models corruption of the
        verification computation/memory holding the digest, distinct from
        and downstream of any final_key corruption already present in the
        bits that were hashed to produce it."""
        digest_arr = digest_arr.copy()
        if self.rng.random() < self.verification_digest_prob:
            idx = int(self.rng.integers(0, len(digest_arr)))
            digest_arr[idx] ^= 1
            self.injected_faults.append(("verification_digest", idx, context))
        return digest_arr

    def summary(self):
        return dict(Counter(f[0] for f in self.injected_faults))
