# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Komal Thareja & Audrey Feng

import unittest
from pathlib import Path

from validation.scenario import ValidationScenario, ValidationResult
from validation.run_qfabric import run_qfabric_bb84_simulated
from validation.reference_bb84 import reference_bb84
from validation.compare import compare_results, backend_status


class TestValidation(unittest.TestCase):

    def setUp(self):
        self.scenario = ValidationScenario(
            name="test_scenario",
            distance_km=1.0,
            attenuation_db_per_km=0.2,
            detector_efficiency=0.8,
            dark_count_rate_hz=10.0,
            polarization_fidelity=1.0,
            num_photons=10_000,
            sample_fraction=0.1,
            seed=42,
        )

    def test_expected_loss(self):
        """Test fiber loss probability formula."""
        # P(loss) = 1 - 10^(-0.2 * 1.0 / 10) = 1 - 10^(-0.02)
        expected = 1.0 - (10 ** -0.02)
        self.assertAlmostEqual(self.scenario.expected_loss_probability, expected, places=5)

    def test_run_qfabric_simulated(self):
        """Test running QFabric BB84 simulation mode."""
        res = run_qfabric_bb84_simulated(self.scenario)
        self.assertEqual(res.platform, "qfabric")
        self.assertGreater(res.photons_received, 0)
        self.assertGreater(res.sifted_bits, 0)
        self.assertGreaterEqual(res.qber, 0.0)

    def test_reference_bb84(self):
        """Test reference analytic Monte Carlo."""
        res = reference_bb84(self.scenario, platform="reference")
        self.assertEqual(res.platform, "reference")
        self.assertGreater(res.photons_received, 0)
        self.assertGreater(res.sifted_bits, 0)

    def test_compare_results(self):
        """Test statistical agreement comparison between QFabric and Reference."""
        res_qfabric = run_qfabric_bb84_simulated(self.scenario)
        res_ref = reference_bb84(self.scenario, platform="reference")

        comp = compare_results([res_qfabric, res_ref])
        self.assertTrue(comp["all_passed"])
        self.assertEqual(len(comp["comparisons"]), 1)

    def test_backend_status(self):
        """Test status classification of backend results."""
        ok_res = ValidationResult(platform="test", scenario_name="test", sifted_bits=100, qber=0.01)
        status, _ = backend_status(ok_res)
        self.assertEqual(status, "ok")

        err_res = ValidationResult(platform="test", scenario_name="test", extra={"error": "failed"})
        status, _ = backend_status(err_res)
        self.assertEqual(status, "unavailable")


if __name__ == "__main__":
    unittest.main()
