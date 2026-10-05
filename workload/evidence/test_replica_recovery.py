"""Ensure incomplete observations cannot become successful HA evidence."""

from copy import deepcopy
import unittest

from validate_replica_recovery import validate


def fixture():
    return {"verification": "local-compose", "scenario": "replica-worker-crash",
            "source_revision": "a" * 40, "result": "passed",
            "started_at": "2026-10-05T00:00:00+00:00",
            "killed_at": "2026-10-05T00:00:01+00:00",
            "recovered_at": "2026-10-05T00:00:31+00:00",
            "finished_at": "2026-10-05T00:00:32+00:00",
            "api_replica_idempotency": True, "surviving_api_accepts": True,
            "worker_sigkill": True, "worker_exit_code": 137, "source_images_match": True,
            "recovered_attempt": 2, "golden_report_match": True,
            "attempt_history": ["1:false", "2:true"], "test_gate_removed": True,
            "baseline_restored": True, "database_ha_verified": False,
            "cloud_provisioned": False, "errors": []}


class EvidenceTests(unittest.TestCase):
    def test_complete_local_proof(self):
        validate(fixture())

    def test_false_claims_rejected(self):
        for key, value in (("worker_exit_code", 0), ("recovered_attempt", 1),
                           ("baseline_restored", False), ("test_gate_removed", False),
                           ("database_ha_verified", True), ("cloud_provisioned", True),
                           ("errors", ["credential contents"]),
                           ("attempt_history", ["1:true", "2:true"])):
            record = deepcopy(fixture())
            record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(record)


if __name__ == "__main__":
    unittest.main()
