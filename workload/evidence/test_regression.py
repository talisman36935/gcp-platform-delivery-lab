"""Reject comparisons that would misrepresent regression or recovered artifacts."""

from copy import deepcopy
import unittest

from validate_regression import qualify


class RegressionTests(unittest.TestCase):
    def setUp(self):
        phases = []
        for index, (name, variant, duration, image) in enumerate([
            ("baseline", "baseline", 0.1, "a"),
            ("regressed", "regressed", 0.5, "b"),
            ("recovered", "baseline", 0.11, "a"),
        ]):
            phases.append({
                "phase": name, "variant": variant, "image_id": "sha256:" + image * 64,
                "started_at": f"2026-10-04T12:00:{index * 10:02d}+00:00",
                "finished_at": f"2026-10-04T12:00:{index * 10 + 5:02d}+00:00",
                "completion_seconds": [duration] * 6, "median_seconds": duration,
                "golden_reports_match": True,
                "profile": {"file": name + "-cpu.pprof", "bytes": 1, "sha256": "a" * 64},
            })
        self.fixture = {
            "verification": "local-compose", "source_revision": "a" * 40,
            "scenario": "compiled-variant-regression",
            "fixture_sha256": "0f237c6f846e4f742fb9a0b89195b8f76dbd269470edb28e786c999eb15b91de",
            "requested_per_phase": 6, "load": "sequential-closed-loop",
            "warmup_per_phase": 2,
            "criteria": {"regression_min_ratio": 1.5, "regression_min_delta_seconds": 0.05,
                         "recovery_max_ratio": 2.0, "recovery_jitter_seconds": 0.1},
            "started_at": "2026-10-04T12:00:00+00:00",
            "finished_at": "2026-10-04T12:00:30+00:00",
            "result": "passed", "phases": phases, "errors": [],
            "baseline_image_restored": True, "cloud_provisioned": False,
        }

    def test_qualified_fixture(self):
        qualify(self.fixture)

    def test_rejects_wrong_recovery_image(self):
        fixture = deepcopy(self.fixture)
        fixture["phases"][2]["image_id"] = "sha256:" + "c" * 64
        with self.assertRaises(ValueError):
            qualify(fixture)

    def test_rejects_unobserved_regression(self):
        fixture = deepcopy(self.fixture)
        fixture["phases"][1]["completion_seconds"] = [0.1] * 6
        fixture["phases"][1]["median_seconds"] = 0.1
        with self.assertRaises(ValueError):
            qualify(fixture)

    def test_rejects_unrecovered_latency(self):
        fixture = deepcopy(self.fixture)
        fixture["phases"][2]["completion_seconds"] = [0.5] * 6
        fixture["phases"][2]["median_seconds"] = 0.5
        with self.assertRaises(ValueError):
            qualify(fixture)


if __name__ == "__main__":
    unittest.main()
