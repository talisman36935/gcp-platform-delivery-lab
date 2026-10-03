"""Validate strict fields and semantic invariants before consuming local evidence."""

from datetime import datetime
import json
import math
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = Path(__file__).with_name("local-baseline.schema.json")


def validate(record: dict) -> None:
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    if any(not math.isfinite(value) for value in record["completion_seconds"]):
        raise ValueError("non-finite measurements are not valid evidence")
    if len(record["completion_seconds"]) != record["completed_jobs"]:
        raise ValueError("measurement count disagrees with completed count")
    if record["completed_jobs"] > record["requested_jobs"]:
        raise ValueError("completed exceeds requested")
    start = datetime.fromisoformat(record["started_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(record["finished_at"].replace("Z", "+00:00"))
    if end < start:
        raise ValueError("timestamps out of order")
    if record["result"] == "passed" and (
        record["completed_jobs"] != record["requested_jobs"]
        or not record["golden_reports_match"]
        or not all(record["telemetry"].values())
        or record["errors"]
    ):
        raise ValueError("passing record lacks complete qualifying observations")
    if record["result"] == "failed" and not record["errors"]:
        raise ValueError("failed record requires an error category")


if __name__ == "__main__":
    validate(json.loads(Path(sys.argv[1]).read_text()))
    print("Valid local baseline record; no cloud or teardown qualification.")
