"""
Validates the QFabricClassicalSession / alice_handle_ask_parities message
protocol using two local processes communicating over localhost -- before
attempting this over real FABRIC infrastructure.

Usage:
    Terminal 1: python3 test_real_channel_local.py --role bob
    Terminal 2: python3 test_real_channel_local.py --role alice
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from qne.cascade import Key, ORIGINAL, Reconciliation
from qne.cascade.classical_session import QFabricClassicalSession, alice_handle_ask_parities
from qne.channel import ClassicalClient, ClassicalServer

HOST = "127.0.0.1"
PORT = 5300
N_BITS = 1000
QBER = 0.02
SEED = 42


def run_bob():
    alice_key = Key(nr_bits=N_BITS, seed=SEED)
    bob_key = alice_key.copy()
    bob_key.apply_noise(bit_error_rate=QBER, seed=SEED + 1)

    n_injected_errors = alice_key.nr_bits_different(bob_key)
    print(f"Bob: {n_injected_errors} errors injected into noisy key")

    server = ClassicalServer(HOST, PORT)
    server.start()
    print("Bob: waiting for Alice...")
    channel = server.accept()
    print("Bob: Alice connected, starting reconciliation")

    try:
        session = QFabricClassicalSession(channel)
        reconciliation = Reconciliation(
            algorithm=ORIGINAL, classical_session=session,
            noisy_key=bob_key, estimated_bit_error_rate=QBER, seed=SEED + 100,
            correct_key=alice_key,  # enables BAD CORRECTION diagnostic
        )
        bob_reconciled = reconciliation.reconcile()
        remaining = alice_key.nr_bits_different(bob_reconciled)
        print(f"Bob: reconciliation complete. Remaining errors vs Alice's true key: {remaining}")
        print(f"Bob: total corrections made: {len(reconciliation.corrected_bit_positions)}")
    finally:
        channel.close()
        server.close()


def run_alice():
    alice_key = Key(nr_bits=N_BITS, seed=SEED)
    print("Alice: connecting to Bob...")
    channel = ClassicalClient.connect(HOST, PORT)
    try:
        for i in range(2000):
            try:
                alice_handle_ask_parities(channel, alice_key)
            except Exception as e:
                print(f"Alice: responder stopped after {i} requests: {e}")
                break
    finally:
        channel.close()
    print("Alice: done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["alice", "bob"], required=True)
    args = parser.parse_args()

    if args.role == "bob":
        run_bob()
    else:
        run_alice()