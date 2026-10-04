"""Check the local investigation contract's critical qualification boundaries."""

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from trace_profile import spans


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        schema = json.loads(Path(__file__).with_name("local-trace-profile.schema.json").read_text())
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.failed = {
            "verification": "local-compose", "source_revision": "a" * 40,
            "started_at": "2026-10-04T12:00:00Z",
            "finished_at": "2026-10-04T12:00:01Z",
            "result": "failed", "errors": ["RuntimeError"],
            "cloud_provisioned": False,
        }

    def test_failed_observation_is_retained(self):
        self.validator.validate(self.failed)

    def test_partial_or_cloud_success_rejected(self):
        for changes in ({"result": "passed", "errors": []},
                        {"cloud_provisioned": True}, {"credentials": "forbidden"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.validator.validate({**self.failed, **changes})

    def test_tempo_and_otlp_layouts_are_both_readable(self):
        resource = {
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": "report-workshop-api"}},
                {"key": "service.version", "value": {"stringValue": "a" * 40}},
            ]},
            "scopeSpans": [{"spans": [{"name": "POST /v1/jobs"}]}],
        }
        for key in ("batches", "resourceSpans"):
            parsed = list(spans({key: [resource]}))
            self.assertEqual(parsed[0][0]["service.name"], "report-workshop-api")
            self.assertEqual(parsed[0][1]["name"], "POST /v1/jobs")


if __name__ == "__main__":
    unittest.main()
