"""Tests for allowlisted Cloud Logging lifecycle notifications."""

import json
import subprocess
import unittest
from unittest.mock import Mock

from notify_lifecycle import EVENTS, entry, publish


class LifecycleNotificationTests(unittest.TestCase):
    def test_every_documented_event_is_valid(self):
        for event in EVENTS:
            with self.subTest(event=event):
                item = entry(
                    "portfolio-lab-123",
                    "lab-demo-1",
                    event,
                    "2026-10-06T12:00:00Z",
                )
                self.assertEqual(item["event"], event)
                self.assertEqual(item["schema"], "portfolio.lifecycle.v1")

    def test_rejects_unscoped_or_malformed_events(self):
        for project, run_id, event in [
            ("", "lab-demo", "ready"),
            ("portfolio-lab-123", "*", "ready"),
            ("portfolio-lab-123", "lab-demo", "shell;bad"),
        ]:
            with self.subTest(project=project, run_id=run_id, event=event):
                with self.assertRaises(ValueError):
                    entry(project, run_id, event, "2026-10-06T12:00:00Z")

    def test_publisher_uses_argv_and_json_payload_without_shell(self):
        runner = Mock()
        publish("portfolio-lab-123", "lab-demo-1", "teardown-failed", runner=runner)
        args, kwargs = runner.call_args
        self.assertEqual(
            args[0][0:4],
            ["gcloud", "logging", "write", "portfolio-lifecycle"],
        )
        self.assertTrue(kwargs["check"])
        self.assertTrue(kwargs["capture_output"])
        self.assertNotIn("shell", kwargs)
        payload = json.loads(args[0][4])
        self.assertEqual(payload["event"], "teardown-failed")
        self.assertEqual(args[0][-1], "--project=portfolio-lab-123")

    def test_delivery_errors_fail_closed_without_raw_provider_output(self):
        runner = Mock(
            side_effect=subprocess.CalledProcessError(
                1, ["gcloud"], stderr="private detail"
            )
        )
        with self.assertRaisesRegex(RuntimeError, "delivery to Cloud Logging failed"):
            publish("portfolio-lab-123", "lab-demo-1", "ready", runner=runner)


if __name__ == "__main__":
    unittest.main()
