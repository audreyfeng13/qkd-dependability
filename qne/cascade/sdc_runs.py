"""
SDC fault-injection sweep: key agreement, undetected mismatches,
secure key length, runtime overhead -- across the four fault types,
alone and combined, including post-PA verification. Operates on real,
provided Alice/Bob key pairs (e.g., loaded from FABRIC-collected sifted
bits), not synthetic keys.
"""
import time
import numpy as np
import pandas as pd
from galois import GF2
from randextract import ToeplitzHashing
from qne.cascade import Key, ORIGINAL, Reconciliation, MockClassicalSession
from qne.cascade.fault_injection import SDCFaultInjector


def run_sdc_experiment(alice_key, bob_key, qber, seed=42,
                        toeplitz_prob=0.0, final_key_prob=0.0, reconciliation_prob=0.0,
                        verify_digest_prob=0.0, ell=None, t_verify=None, digest_length=None):
    """Run one SDC fault-injection trial on a given Alice/Bob key pair,
    including a genuine post-PA verification step (universal2-hash
    digest of a sacrificed subset, matching the real-channel drivers).

    Toeplitz-matrix and final-key faults are ONE-SIDED (Bob only), matching
    real-channel behavior: alice_cascade_responder.py has no fault-injection
    capability, so Alice's PA extraction is never faulted. Reconciliation
    and verify-digest faults were already one-sided.

    ell: usable secret-key length. If None, falls back to the placeholder
        relative_source_entropy=0.5 formula for backward compatibility
        (no verification step is performed in that fallback case, since
        there's no reserved t_verify budget).
    t_verify, digest_length: verification-step sizing. Required if ell
        is explicitly provided.
    """
    t0 = time.time()
    n_bits = alice_key.get_nr_bits()
    injector = SDCFaultInjector(
        toeplitz_matrix_prob=toeplitz_prob,
        final_key_prob=final_key_prob,
        reconciliation_state_prob=reconciliation_prob,
        verification_digest_prob=verify_digest_prob,
        seed=seed + 2,
    )
    # --- Stage 1: Cascade reconciliation (already one-sided: only bob_key
    # is ever the "noisy_key" being corrected; alice_key is the fixed
    # ground truth inside MockClassicalSession) ---
    session = MockClassicalSession(correct_key=alice_key)
    reconciliation = Reconciliation(
        algorithm=ORIGINAL, classical_session=session, noisy_key=bob_key,
        estimated_bit_error_rate=qber, seed=seed + 100, fault_injector=injector,
    )
    bob_reconciled = reconciliation.reconcile()
    qber_after_reconciliation = alice_key.nr_bits_different(bob_reconciled) / n_bits

    # --- Stage 2 + 3: Toeplitz PA ---
    if ell is None:
        out_len_total = ToeplitzHashing.calculate_length(
            extractor_type="quantum", input_length=n_bits,
            relative_source_entropy=0.5, error_bound=1e-6,
        )
        ell_used = out_len_total
        t_verify_used = 0
    else:
        ell_used = ell
        t_verify_used = t_verify
        out_len_total = ell + t_verify

    ext = ToeplitzHashing(input_length=n_bits, output_length=out_len_total)
    pa_seed = GF2.Random(ext.seed_length)

    # Alice's extraction is NEVER faulted -- matches real-channel exactly,
    # where there is no fault-injection code path on Alice's side at all.
    alice_full = np.array(ext.extract(GF2(alice_key.bits), pa_seed))

    # Only Bob's side goes through the fault injector.
    bob_full = injector.fast_toeplitz_extract_with_fault(ext, GF2(bob_reconciled.bits), pa_seed, "bob")
    bob_full = injector.maybe_flip_final_key_bit(bob_full, "bob")

    verification_passed = None
    if t_verify_used > 0:
        alice_secret = alice_full[:ell_used]
        alice_verify_bits = alice_full[ell_used:ell_used + t_verify_used]
        bob_secret = bob_full[:ell_used]
        bob_verify_bits = bob_full[ell_used:ell_used + t_verify_used]
        verify_ext = ToeplitzHashing(input_length=t_verify_used, output_length=digest_length)
        verify_seed = GF2.Random(verify_ext.seed_length)
        alice_digest = np.array(verify_ext.extract(GF2(alice_verify_bits), verify_seed))
        bob_digest = np.array(verify_ext.extract(GF2(bob_verify_bits), verify_seed))
        bob_digest = injector.maybe_flip_verification_digest_bit(bob_digest, "bob")
        verification_passed = bool(np.array_equal(alice_digest, bob_digest))
        alice_final, bob_final = alice_secret, bob_secret
    else:
        alice_final, bob_final = alice_full, bob_full

    elapsed = time.time() - t0
    keys_match = np.array_equal(alice_final, bob_final)
    n_diff_bits = int(np.sum(alice_final != bob_final))
    return {
        "toeplitz_prob": toeplitz_prob, "final_key_prob": final_key_prob,
        "reconciliation_prob": reconciliation_prob, "verify_digest_prob": verify_digest_prob,
        "qber_after_reconciliation": qber_after_reconciliation,
        "secure_key_length": ell_used, "t_verify": t_verify_used,
        "verification_passed": verification_passed,
        "keys_match": keys_match,
        "n_mismatched_bits": n_diff_bits,
        "elapsed_seconds": elapsed,
        "faults_fired": injector.summary(),
    }

def run_sdc_experiment_safe(**kwargs):
    """Wraps run_sdc_experiment, catching non-convergence (RuntimeError from
    Cascade's internal loop caps) as a recorded outcome instead of a crash."""
    try:
        result = run_sdc_experiment(**kwargs)
        result["non_convergent"] = False
        result["error"] = None
        return result
    except RuntimeError as e:
        return {
            "toeplitz_prob": kwargs.get("toeplitz_prob", 0.0),
            "final_key_prob": kwargs.get("final_key_prob", 0.0),
            "reconciliation_prob": kwargs.get("reconciliation_prob", 0.0),
            "verify_digest_prob": kwargs.get("verify_digest_prob", 0.0),
            "qber_after_reconciliation": None,
            "secure_key_length": None, "t_verify": None,
            "verification_passed": None,
            "keys_match": False,
            "n_mismatched_bits": None,
            "elapsed_seconds": None,
            "faults_fired": None,
            "non_convergent": True,
            "error": str(e),
        }