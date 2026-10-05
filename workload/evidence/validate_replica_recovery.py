"""Fail closed on incomplete or falsely successful replica recovery records."""

from datetime import datetime
import json
from pathlib import Path
import re
import sys


def validate(record: dict) -> None:
    fields = {"verification", "source_revision", "scenario", "started_at", "finished_at",
              "result", "api_replica_idempotency", "surviving_api_accepts", "worker_sigkill",
              "worker_exit_code", "source_images_match", "recovered_attempt",
              "golden_report_match", "attempt_history", "test_gate_removed",
              "baseline_restored", "database_ha_verified", "cloud_provisioned", "errors"}
    if set(record) - fields - {"killed_at", "recovered_at"} or not fields <= set(record):
        raise ValueError("unexpected or missing fields")
    if (record["verification"] != "local-compose"
            or record["scenario"] != "replica-worker-crash"
            or not re.fullmatch(r"[0-9a-f]{40}", record["source_revision"])
            or record["cloud_provisioned"] is not False
            or record["database_ha_verified"] is not False):
        raise ValueError("invalid provenance or unsupported HA claim")
    start, end = [datetime.fromisoformat(record[key]) for key in ("started_at", "finished_at")]
    if not start.tzinfo or not end.tzinfo or start > end:
        raise ValueError("invalid observation interval")
    flags = ("api_replica_idempotency", "surviving_api_accepts", "worker_sigkill",
             "source_images_match", "golden_report_match", "test_gate_removed",
             "baseline_restored")
    if any(type(record[key]) is not bool for key in flags):
        raise ValueError("observation flags must be booleans")
    if not isinstance(record["errors"], list) or any(
            not isinstance(error, str) or not re.fullmatch(r"[A-Za-z]+(?:Error|Expired)", error)
            for error in record["errors"]):
        raise ValueError("only bounded error categories may be published")
    if record["result"] not in {"passed", "failed"}:
        raise ValueError("unknown result")
    if record["result"] == "passed":
        if (not all(record[key] for key in flags) or record["errors"]
                or record["worker_exit_code"] != 137 or record["recovered_attempt"] != 2
                or record["attempt_history"] != ["1:false", "2:true"]):
            raise ValueError("incomplete crash/recovery proof")
        killed, recovered = [datetime.fromisoformat(record[key])
                             for key in ("killed_at", "recovered_at")]
        if not killed.tzinfo or not recovered.tzinfo or not start <= killed < recovered <= end:
            raise ValueError("invalid recovery ordering")


if __name__ == "__main__":
    validate(json.loads(Path(sys.argv[1]).read_text()))
    print("Replica/crash observation validated; no database or cloud HA claim.")
