"""
Alice-side Cascade reconciliation responder + Toeplitz extraction, with
post-PA verification (hash-digest comparison), for real FABRIC deployment.
Output filenames are auto-suffixed with a timestamp to prevent silent
overwrites across different sweeps.
"""
import sys
import argparse
import json
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from galois import GF2
from randextract import ToeplitzHashing

from qne.cascade.key import key_from_sifted_json
from qne.channel import ClassicalClient
from qne.netem import arm_cascade_netem, disarm_cascade_netem


def make_unique_output_path(base_output, seed):
    base = Path(base_output)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return base.parent / f"{base.stem}_seed{seed}_{timestamp}{base.suffix}"


def run_alice(alice_key, host, port, output_path, seed, max_requests=2000,
              cascade_iface=None, cascade_delay_ms=0.0, cascade_jitter_ms=0.0,
              cascade_loss_pct=0.0):
    print(f"Alice: connecting to Bob at {host}:{port}...")
    channel = ClassicalClient.connect(host, port)
    netem_info = {}
    # armed tracks whether netem is CURRENTLY on, so the finally block
    # doesn't double-disarm after the pa_setup transition already did it.
    cascade_netem_requested = bool(cascade_delay_ms or cascade_loss_pct)
    armed = False
    try:
        if cascade_netem_requested:
            netem_info["arm"] = arm_cascade_netem(
                cascade_iface, port, delay_ms=cascade_delay_ms,
                jitter_ms=cascade_jitter_ms, loss_pct=cascade_loss_pct,
            )
            armed = True
        for i in range(max_requests):
            try:
                msg_peek = channel.recv_message()
            except Exception as e:
                print(f"Alice: channel closed during Cascade phase: {e}")
                return

            if msg_peek["type"] == "cascade_ask_parities":
                from qne.cascade.shuffle import Shuffle, ShuffledKey
                shuffle_cache = {}
                parities = []
                for start, end, iteration_nr, shuffle_seed in msg_peek["blocks"]:
                    if iteration_nr not in shuffle_cache:
                        shuffle_cache[iteration_nr] = Shuffle(alice_key.get_nr_bits(), seed=shuffle_seed)
                    shuffle = shuffle_cache[iteration_nr]
                    shuffled_alice_key = ShuffledKey(alice_key, shuffle)
                    parities.append(shuffled_alice_key.compute_range_parity(start, end))
                channel.send_message({"type": "cascade_parities_result", "parities": parities})

            elif msg_peek["type"] == "pa_setup":
                if armed:
                    # Disarm the instant the Cascade phase ends -- PA/verification
                    # below must run un-impaired.
                    netem_info["disarm"] = disarm_cascade_netem(cascade_iface)
                    armed = False
                pa_seed = GF2(msg_peek["seed"])
                verify_seed = GF2(msg_peek["verify_seed"])
                out_len_total = msg_peek["out_len"]
                ell = msg_peek["ell"]
                t_verify = msg_peek["t_verify"]
                digest_length = msg_peek["digest_length"]
                n_bits = alice_key.get_nr_bits()

                ext = ToeplitzHashing(input_length=n_bits, output_length=out_len_total)
                alice_full = np.array(ext.extract(GF2(alice_key.bits), pa_seed))

                alice_secret = alice_full[:ell]
                alice_verify_bits = alice_full[ell:ell + t_verify]

                verify_ext = ToeplitzHashing(input_length=t_verify, output_length=digest_length)
                alice_digest = np.array(verify_ext.extract(GF2(alice_verify_bits), verify_seed))

                channel.send_message({"type": "verify_digest", "digest": alice_digest.tolist()})

                result_msg = channel.recv_message()
                assert result_msg["type"] == "verify_result"
                verification_passed = result_msg["passed"]

                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump({
                        "alice_final_key": np.array(alice_secret).tolist(),
                        "alice_bits": alice_key.bits.tolist(),
                        "verification_passed": verification_passed,
                        "output_path": str(output_path),
                        "cascade_netem": netem_info,
                    }, f)
                print(f"Alice: PA + verification complete ({'PASSED' if verification_passed else 'FAILED'}), "
                      f"final key written to {output_path}")
                return
            else:
                print(f"Alice: unexpected message type: {msg_peek['type']}")
                return
    finally:
        # Safety net: if we exit (channel closed, unexpected message,
        # exception) before ever seeing pa_setup, netem may still be armed.
        # This must never leave the interface impaired for whatever runs
        # on this node next.
        if armed:
            netem_info["disarm"] = disarm_cascade_netem(cascade_iface)
        channel.close()
    print("Alice: done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-json", required=True)
    parser.add_argument("--bob-host", required=True)
    parser.add_argument("--port", type=int, default=5200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="results/alice_final_key.json")
    parser.add_argument("--no-unique-suffix", action="store_true")
    parser.add_argument("--cascade-iface", default=None,
                         help="Local network device name (e.g. eth1) on THIS node to impair "
                              "for TCP:<port> traffic, symmetric with bob_cascade_driver.py's "
                              "own --cascade-iface on Bob's node. Required if any --cascade-* "
                              "delay/loss arg is set.")
    parser.add_argument("--cascade-delay-ms", type=float, default=0.0)
    parser.add_argument("--cascade-jitter-ms", type=float, default=0.0)
    parser.add_argument("--cascade-loss-pct", type=float, default=0.0)
    args = parser.parse_args()
    if (args.cascade_delay_ms or args.cascade_loss_pct) and not args.cascade_iface:
        parser.error("--cascade-iface is required when --cascade-delay-ms/--cascade-loss-pct is set")

    output_path = args.output if args.no_unique_suffix else str(make_unique_output_path(args.output, args.seed))

    alice_key, _ = key_from_sifted_json(args.key_json, "alice_bits")
    print(f"Alice: loaded key with {alice_key.get_nr_bits()} bits")
    run_alice(alice_key, args.bob_host, args.port, output_path, args.seed,
              cascade_iface=args.cascade_iface, cascade_delay_ms=args.cascade_delay_ms,
              cascade_jitter_ms=args.cascade_jitter_ms, cascade_loss_pct=args.cascade_loss_pct)