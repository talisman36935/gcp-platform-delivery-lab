"""Record a bounded local baseline. Never qualifies a cloud or performance claim."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

GOLDEN_HASH = "2522de9d1c28cf3a163c3703dbabb2b63009e5daa6a8d98f2aac85f577307bd5"


def fetch(port: int, path: str, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = None if body is None else json.dumps(body).encode()
    with urlopen(Request(f"http://127.0.0.1:{port}{path}", data=data,
                         headers=headers), timeout=5) as response:
        return response.read().decode()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(revision: str, count: int) -> dict:
    run_id = "local-" + uuid.uuid4().hex
    result = {
        "schema_version": "local-baseline-v1",
        "run_id": run_id,
        "verification": "local-compose",
        "scenario": "baseline-smoke",
        "source_revision": revision,
        "started_at": timestamp(),
        "finished_at": timestamp(),
        "result": "failed",
        "requested_jobs": count,
        "completed_jobs": 0,
        "completion_seconds": [],
        "fixture_sha256": GOLDEN_HASH,
        "golden_reports_match": False,
        "telemetry": {"api_metrics": False, "worker_metrics": False,
                      "prometheus_targets": False},
        "errors": [],
        "cloud_provisioned": False,
        "teardown": "not_checked",
    }
    try:
        for index in range(count):
            job = json.loads(fetch(18080, "/v1/jobs",
                                   {"fixture": "tiny-v1", "algorithm": "tokens-v1"},
                                   f"{run_id}-{index}"))
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                job = json.loads(fetch(18080, "/v1/jobs/" + job["id"]))
                if job["state"] == "succeeded":
                    break
                if job["state"] == "failed":
                    raise RuntimeError("job failed")
                time.sleep(0.1)
            else:
                raise TimeoutError("job completion deadline")
            report = json.loads(fetch(18080, "/v1/jobs/" + job["id"] + "/report"))
            expected = {"documents": 3, "tokens": 11, "unique_tokens": 6,
                        "duplicate_documents": 1, "input_sha256": GOLDEN_HASH}
            if report != expected:
                raise ValueError("golden report mismatch")
            accepted = datetime.fromisoformat(job["created_at"].replace("Z", "+00:00"))
            completed = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
            duration = (completed - accepted).total_seconds()
            if not 0 <= duration <= 60:
                raise ValueError("invalid completion interval")
            result["completion_seconds"].append(duration)
            result["completed_jobs"] += 1
        result["golden_reports_match"] = True
        for service, port in (("api", 19090), ("worker", 19091)):
            metrics = fetch(port, "/metrics")
            identity = f'workshop_build_info{{revision="{revision}",role="{service}"}} 1'
            if identity not in metrics:
                raise ValueError("running revision mismatch")
            result["telemetry"][service + "_metrics"] = True
        query = urlencode({"query": 'up{job="report-workshop"}'})
        for _ in range(20):
            response = json.loads(fetch(19092, "/api/v1/query?" + query))
            series = response["data"]["result"]
            up = {item["metric"].get("service") for item in series
                  if item["value"][1] == "1"}
            if up == {"api", "worker"}:
                result["telemetry"]["prometheus_targets"] = True
                break
            time.sleep(0.5)
        if not result["telemetry"]["prometheus_targets"]:
            raise RuntimeError("collector targets missing")
        result["result"] = "passed"
    except Exception as exc:
        # Public evidence contains bounded categories, never raw response/URL/error text.
        result["errors"].append(type(exc).__name__)
    result["finished_at"] = timestamp()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision) or not 1 <= args.count <= 100:
        parser.error("supply a 40-character revision and count between 1 and 100")
    if args.output.exists():
        parser.error("refusing to overwrite an existing run record")
    result = record(args.revision, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{result['result']}: {args.output}")
    if result["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
