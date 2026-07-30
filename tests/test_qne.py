# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Komal Thareja & Audrey Feng

import unittest
import socket
import threading
import time
import numpy as np

from qne.photon import PhotonPacket, Basis, State
from qne.detector import Detector
from qne.bb84 import BB84Protocol, AliceRecord, BobRecord
from qne.config import ScenarioConfig
from qne.channel import ClassicalServer, ClassicalClient


class TestQNE(unittest.TestCase):

    def test_photon_packet_serialization(self):
        """Test encoding and decoding of custom photon Ethernet frames."""
        pkt = PhotonPacket(basis=Basis.Z, state=State.ZERO, sequence_num=42, wavelength=1)
        encoded = pkt.to_bytes()
        self.assertGreater(len(encoded), 14)  # Ethernet header + Photon payload

        decoded = PhotonPacket.from_bytes(encoded)
        self.assertEqual(decoded.basis, Basis.Z)
        self.assertEqual(decoded.state, State.ZERO)
        self.assertEqual(decoded.sequence_num, 42)
        self.assertEqual(decoded.wavelength, 1)

    def test_detector_ideal(self):
        """Test ideal detector with 100% efficiency and 0 dark counts."""
        det = Detector(efficiency=1.0, dark_count_rate=0.0, polarization_error=0.0, seed=42)
        pkt = PhotonPacket(basis=0, state=1, sequence_num=0)
        event = det.detect(pkt)
        self.assertTrue(event.detected)
        self.assertEqual(event.bit_value, 1)

    def test_detector_efficiency(self):
        """Test detector photon loss based on efficiency."""
        det = Detector(efficiency=0.0, dark_count_rate=0.0, seed=42)
        pkt = PhotonPacket(basis=0, state=1, sequence_num=0)
        event = det.detect(pkt)
        self.assertFalse(event.detected)

    def test_bb84_sifting_and_qber(self):
        """Test BB84 sifting logic and QBER estimation."""
        protocol = BB84Protocol(sample_fraction=0.2, seed=42)

        alice_log = []
        bob_log = []
        # Generate 100 matching basis records
        for i in range(100):
            alice_log.append(AliceRecord(sequence_num=i, basis=0, bit_value=i % 2))
            bob_log.append(BobRecord(sequence_num=i, basis=0, bit_value=i % 2))

        sifted = protocol.sift(alice_log, bob_log)
        self.assertEqual(sifted.sifted_count, 100)

        qber_est = protocol.estimate_qber(sifted)
        self.assertEqual(qber_est.qber, 0.0)

        key_rate = protocol.compute_key_rate(sifted, qber_est, num_photons_sent=200)
        self.assertGreater(key_rate.secure_key_rate, 0.0)

    def test_classical_channel_tcp(self):
        """Test TCP classical channel message exchange between server and client."""
        server = ClassicalServer(host="127.0.0.1", port=15100)
        server.start()

        received_msg = {}

        def server_thread():
            conn = server.accept()
            msg = conn.recv_message()
            received_msg.update(msg)
            conn.send_message({"status": "ack"})
            conn.close()

        t = threading.Thread(target=server_thread)
        t.start()

        time.sleep(0.1)
        client_conn = ClassicalClient.connect("127.0.0.1", port=15100, max_retries=5, retry_delay=0.1)
        client_conn.send_message({"hello": "world"})
        response = client_conn.recv_message()
        client_conn.close()

        t.join()
        server.close()

        self.assertEqual(received_msg, {"hello": "world"})
        self.assertEqual(response, {"status": "ack"})


if __name__ == "__main__":
    unittest.main()
