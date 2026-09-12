"""
Bob-side Cascade reconciliation + Toeplitz PA driver for real FABRIC
deployment, with optional SDC fault injection at all four points, plus a
post-PA verification step (hash-digest comparison of a sacrificed subset
of the extracted output).

n_bits here is the GENERATION string length (n = m - k), where k is the
parameter-estimation sample size recorded for this key pair during
collect_key_pairs. k must be passed explicitly (--k) so the finite-key
calculation uses the real PE split rather than assuming k=0.

Output filenames are auto-suffixed with a timestamp + fault parameters
to prevent silent overwrites across different sweeps.
"""
import sys
import argparse
import json
import math
import time
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from galois import GF2
from randextract import ToeplitzHashing

from qne.cascade.key import key_from_sifted_json
from qne.cascade import ORIGINAL, Reconciliation
from qne.cascade.classical_session import QFabricClassicalSession
from qne.cascade.fault_injection import SDCFaultInjector
from qne.cascade.finite_key import finite_key_output_length, asymptotic_key_length
from qne.channel import ClassicalServer
from qne.netem import arm_cascade_netem, disarm_cascade_netem


def make_unique_output_path(base_output, toeplitz_prob, final_key_prob,
                              reconciliation_prob, verify_digest_prob, seed):
    """Appends a timestamp + the actual fault parameters to the requested
    output filename, so re-running with different parameters (or at a
    different time) never silently overwrites a previous result."""
    base = Path(base_output)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = (f"tp{toeplitz_prob}_fk{final_key_prob}_rp{reconciliation_prob}_"
              f"vd{verify_digest_prob}_seed{seed}_{timestamp}")
    return base.parent / f"{base.stem}_{suffix}{base.suffix}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-json", required=True)
    parser.add_argument("--alice-key-json", required=False, default=None)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5200)
    parser.add_argument("--qber", type=float, required=True,
                         help="QBER measured over the PE sample ONLY (from "
                              "collect_key_pairs), not the full sifted key.")
    parser.add_argument("--k", type=int, required=True,
                         help="PE sample size recorded for this key pair "
                              "during collect_key_pairs (m = n_bits + k).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--toeplitz-prob", type=float, default=0.0)
    parser.add_argument("--final-key-prob", type=float, default=0.0)
    parser.add_argument("--reconciliation-prob", type=float, default=0.0)
    parser.add_argument("--verify-digest-prob", type=float, default=0.0)
    parser.add_argument("--arbitrary-bit-prob", type=float, default=0.0)
    parser.add_argument("--output", default="results/bob_reconciled.json")
    parser.add_argument("--length-mode", choices=["placeholder", "finite_key", "asymptotic"],
                         default="placeholder",
                         help="How to compute the PA output length: 'placeholder' (current "
                              "QFabric default, relative_source_entropy=0.5), 'finite_key' "
                              "(Tomamichel-Leverrier corrected), or 'asymptotic' (Shor-Preskill limit).")
    parser.add_argument("--no-unique-suffix", action="store_true",
                         help="Disable automatic unique filename suffixing (not recommended).")
    parser.add_argument("--cascade-iface", default=None,
                         help="Local network device name (e.g. eth1) on THIS node to impair "
                              "for TCP:<port> traffic. Required if any --cascade-* delay/loss "
                              "arg is set. tc is armed immediately before reconciliation.reconcile() "
                              "and disarmed immediately after -- PA/verification are never impaired.")
    parser.add_argument("--cascade-delay-ms", type=float, default=0.0)
    parser.add_argument("--cascade-jitter-ms", type=float, default=0.0)
    parser.add_argument("--cascade-loss-pct", type=float, default=0.0)
    parser.add_argument("--force-non-convergent", action="store_true",
                         help="TEST-ONLY: monkeypatches Reconciliation._service_all_pending_work's "
                              "max_loops down to 1, guaranteeing reconcile() raises RuntimeError "
                              "immediately. Use this to validate the disarm-on-failure path when "
                              "the real fault injector doesn't naturally produce a non-convergent "
                              "case (it didn't, 0/1200, in the existing real-channel sweep) -- "
                              "NEVER use this in an actual sweep, it doesn't represent a real fault.")
    args = parser.parse_args()
    cascade_netem_requested = bool(args.cascade_delay_ms or args.cascade_loss_pct)
    if cascade_netem_requested and not args.cascade_iface:
        parser.error("--cascade-iface is required when --cascade-delay-ms/--cascade-loss-pct is set")
    if args.no_unique_suffix:
        output_path = args.output
    else:
        output_path = str(make_unique_output_path(
            args.output, args.toeplitz_prob, args.final_key_prob,
            args.reconciliation_prob, args.verify_digest_prob, args.seed))

    bob_key, _ = key_from_sifted_json(args.key_json, "bob_bits")
    alice_key = None
    if args.alice_key_json:
        alice_key, _ = key_from_sifted_json(args.alice_key_json, "alice_bits")

    t0 = time.time()
    non_convergent = False
    error_msg = None
    verification_passed = None
    netem_info = {}
    reconciliation_elapsed_seconds = None

    injector = SDCFaultInjector(
        toeplitz_matrix_prob=args.toeplitz_prob,
        final_key_prob=args.final_key_prob,
        reconciliation_state_prob=args.reconciliation_prob,
        verification_digest_prob=args.verify_digest_prob,
        arbitrary_bit_prob=args.arbitrary_bit_prob,
        seed=args.seed + 2,
    )

    server = ClassicalServer(args.host, args.port)
    server.start()
    print(f"Bob: waiting for Alice on {args.host}:{args.port}...")
    channel = server.accept()
    print("Bob: Alice connected, starting reconciliation")

    result = {
        "toeplitz_prob": args.toeplitz_prob, "final_key_prob": args.final_key_prob,
        "reconciliation_prob": args.reconciliation_prob,
        "verify_digest_prob": args.verify_digest_prob,
        "seed": args.seed, "output_path": output_path, "k_pe": args.k,
    }

    session = QFabricClassicalSession(channel)
    reconciliation = Reconciliation(
        algorithm=ORIGINAL, classical_session=session,
        noisy_key=bob_key, estimated_bit_error_rate=args.qber, seed=args.seed,
        correct_key=alice_key, fault_injector=injector,
    )
    # Deliberately OUTSIDE the try/except RuntimeError below: a netem/tc
    # failure here must crash the script loudly, never be reclassified as
    # a genuine Cascade non-convergence result.
    if cascade_netem_requested:
        netem_info["arm"] = arm_cascade_netem(
            args.cascade_iface, args.port,
            delay_ms=args.cascade_delay_ms, jitter_ms=args.cascade_jitter_ms,
            loss_pct=args.cascade_loss_pct,
        )

    try:
        t_reconcile_start = time.time()
        if args.force_non_convergent:
            import functools
            reconciliation._service_all_pending_work = functools.partial(
                reconciliation._service_all_pending_work, max_loops=1
            )
        try:
            bob_reconciled = reconciliation.reconcile()
        finally:
            # Disarm the instant reconciliation returns OR raises (e.g. the
            # known non-convergent case) -- PA/verification below this point
            # must run un-impaired regardless of how reconcile() exited.
            reconciliation_elapsed_seconds = time.time() - t_reconcile_start
            if cascade_netem_requested:
                netem_info["disarm"] = disarm_cascade_netem(args.cascade_iface)
        n_bits = bob_reconciled.get_nr_bits()

        if args.length_mode == "finite_key":
            ell, _, t, _ = finite_key_output_length(n_bits, args.k, args.qber)
        elif args.length_mode == "asymptotic":
            ell = asymptotic_key_length(n_bits, args.qber)
            t = max(1, int(math.ceil(-math.log2(1e-10))))  # same fallback t as placeholder mode
        else:  # placeholder
            ell = ToeplitzHashing.calculate_length(
                extractor_type="quantum", input_length=n_bits,
                relative_source_entropy=0.5, error_bound=1e-6,
            )
            t = max(1, int(math.ceil(-math.log2(1e-10))))

        ell = int(max(0, round(ell)))
        t = int(max(1, round(t)))

        # Verification digest length d is set to the SAME t already used in
        # the finite-key formula (realizing eps_ec = 2^-t, Theorem 2,
        # Tomamichel & Leverrier). t_verify is the number of raw PA-output
        # bits sacrificed and fed into the small verification hash before
        # being discarded. t_verify = t directly -- no extra x2/floor-32
        # padding. That padding inflated the sacrificed fraction of
        # bob_full, which also perturbs how toeplitz-matrix and final-key
        # faults land (both act on bob_full = bob_secret + bob_verify_bits
        # before the ell/t_verify split).
        digest_length = max(1, int(np.ceil(t)))
        t_verify = t
        out_len_total = ell + t_verify

        ext = ToeplitzHashing(input_length=n_bits, output_length=out_len_total)
        pa_seed = GF2.Random(ext.seed_length)

        verify_ext = ToeplitzHashing(input_length=t_verify, output_length=digest_length)
        verify_seed = GF2.Random(verify_ext.seed_length)

        # Send everything Alice needs to independently reproduce the exact
        # same extraction and split -- avoids any risk of the two sides
        # silently disagreeing on lengths.
        channel.send_message({
            "type": "pa_setup",
            "seed": np.array(pa_seed).tolist(),
            "verify_seed": np.array(verify_seed).tolist(),
            "out_len": out_len_total, "ell": ell, "t_verify": t_verify,
            "digest_length": digest_length,
        })

        # Bob's own extraction: full out_len_total bits, with Toeplitz-matrix
        # and final-key faults applied exactly as before.
        bob_full = injector.fast_toeplitz_extract_with_fault(ext, GF2(bob_reconciled.bits), pa_seed, "bob")
        bob_full = injector.maybe_flip_final_key_bit(bob_full, "bob")

        bob_secret = bob_full[:ell]                 # the actual usable secret key
        bob_verify_bits = bob_full[ell:ell + t_verify]  # sacrificed, hashed, then discarded

        bob_digest = np.array(verify_ext.extract(GF2(bob_verify_bits), verify_seed))
        bob_digest = injector.maybe_flip_verification_digest_bit(bob_digest, "bob")

        # Wait for Alice's digest, compare, tell her the outcome.
        alice_msg = channel.recv_message()
        assert alice_msg["type"] == "verify_digest"
        alice_digest = np.array(alice_msg["digest"], dtype=np.uint8)

        verification_passed = bool(np.array_equal(bob_digest, alice_digest))
        channel.send_message({"type": "verify_result", "passed": verification_passed})

        result.update({
            "total_corrections": len(reconciliation.corrected_bit_positions),
            "secure_key_length": ell,
            "t_verify": t_verify, "digest_length": digest_length,
            "verification_passed": verification_passed,
            # Only the usable secret portion is ever saved -- the sacrificed
            # verification bits (bob_verify_bits) are never retained here,
            # since they've been publicly hashed and must not be treated as
            # secret key material going forward.
            "bob_final_key": np.array(bob_secret).tolist(),
            "bob_reconciled_bits": bob_reconciled.bits.tolist(),
        })
        if alice_key is not None:
            result["remaining_errors_after_reconciliation"] = int(alice_key.nr_bits_different(bob_reconciled))
    except RuntimeError as e:
        non_convergent = True
        error_msg = str(e)
        result.update({
            "total_corrections": None, "secure_key_length": None, "bob_final_key": None,
            "verification_passed": None, "t_verify": None, "digest_length": None,
        })
    finally:
        channel.close()
        server.close()

    result["non_convergent"] = non_convergent
    result["error"] = error_msg
    result["elapsed_seconds"] = time.time() - t0
    result["faults_fired"] = injector.summary()
    result["length_mode"] = args.length_mode
    result["cascade_netem"] = netem_info
    result["reconciliation_elapsed_seconds"] = reconciliation_elapsed_seconds

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f)
    print(f"Bob: done. Result written to {output_path}")
    print(json.dumps({k: v for k, v in result.items()
                        if k not in ("bob_final_key", "bob_reconciled_bits")}, indent=2))