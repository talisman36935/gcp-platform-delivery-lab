"""Validate experiment qualification and actual recorded profile files."""

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

from jsonschema import Draft202012Validator, FormatChecker


def qualify(record: dict) -> None:
    schema = json.loads(Path(__file__).with_name("local-regression.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    previous_end = datetime.fromisoformat(record["started_at"])
    for index, phase in enumerate(record["phases"]):
        if phase["phase"] != ("baseline", "regressed", "recovered")[index]:
            raise ValueError("phase sequence changed")
        expected_variant = "regressed" if index == 1 else "baseline"
        if phase["variant"] != expected_variant:
            raise ValueError("phase variant mismatched")
        durations = phase["completion_seconds"]
        if len(durations) != record["requested_per_phase"] or not all(math.isfinite(v) for v in durations):
            raise ValueError("missing or non-finite observations")
        median = phase["median_seconds"]
        if not math.isfinite(median) or not math.isclose(median, statistics.median(durations), rel_tol=1e-12):
            raise ValueError("median disagrees with raw observations")
        start = datetime.fromisoformat(phase["started_at"])
        end = datetime.fromisoformat(phase["finished_at"])
        if start < previous_end or end < start:
            raise ValueError("phase timestamps out of order")
        previous_end = end
    if datetime.fromisoformat(record["finished_at"]) < previous_end:
        raise ValueError("run ends before observations")
    if record["result"] == "passed":
        baseline, regressed, recovered = record["phases"]
        if not (baseline["image_id"] == recovered["image_id"] != regressed["image_id"]):
            raise ValueError("original image not recovered")
        b = baseline["median_seconds"]
        if regressed["median_seconds"] < max(b * 1.5, b + 0.05):
            raise ValueError("regression threshold not met")
        if recovered["median_seconds"] > b * 2 + 0.1:
            raise ValueError("recovery threshold not met")


if __name__ == "__main__":
    path = Path(sys.argv[1])
    record = json.loads(path.read_text())
    qualify(record)
    for phase in record["phases"]:
        profile = phase["profile"]
        data = (path.parent / profile["file"]).read_bytes()
        if len(data) != profile["bytes"] or hashlib.sha256(data).hexdigest() != profile["sha256"]:
            raise SystemExit("Profile differs from its observation")
    print("Valid local comparison with recorded images, thresholds and profile hashes.")
