"""Contract and redaction checks use explicit synthetic fixtures, not run evidence."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from record import GOLDEN_HASH, record
from validate import validate


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {
            "schema_version": "local-baseline-v1",
            "run_id": "local-" + "a" * 32,
            "verification": "local-compose",
            "scenario": "baseline-smoke",
            "source_revision": "a" * 40,
            "started_at": "2026-10-03T12:00:00Z",
            "finished_at": "2026-10-03T12:00:01Z",
            "result": "passed",
            "requested_jobs": 1,
            "completed_jobs": 1,
            "completion_seconds": [0.2],
            "fixture_sha256": GOLDEN_HASH,
            "golden_reports_match": True,
            "telemetry": {"api_metrics": True, "worker_metrics": True,
                          "prometheus_targets": True},
            "errors": [],
            "cloud_provisioned": False,
            "teardown": "not_checked",
        }

    def test_valid_fixture(self):
        validate(self.fixture)

    def test_rejects_cloud_and_extra_fields(self):
        for key, value in (("verification", "cloud"), ("secret", "forbidden"),
                           ("cloud_provisioned", True), ("teardown", "clean")):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validate({**self.fixture, key: value})

    def test_rejects_false_success(self):
        for key, value in (("completed_jobs", 0), ("golden_reports_match", False),
                           ("completion_seconds", []), ("errors", ["HTTPError"]),
                           ("finished_at", "2026-10-03T11:00:00Z")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate({**self.fixture, key: value})
        missing = deepcopy(self.fixture)
        missing["telemetry"]["prometheus_targets"] = False
        with self.assertRaises(ValueError):
            validate(missing)

    def test_failure_preserved_without_private_error_text(self):
        with patch("record.fetch", side_effect=RuntimeError("SECRET connection details")):
            result = record("a" * 40, 1)
        validate(result)
        self.assertEqual(result["result"], "failed")
        self.assertEqual(result["errors"], ["RuntimeError"])
        self.assertNotIn("SECRET", str(result))


if __name__ == "__main__":
    unittest.main()
