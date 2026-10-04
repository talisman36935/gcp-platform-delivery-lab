"""Observe durable API/worker trace correlation and capture local Go profiles."""

from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import time
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

from record import timestamp


def request(port, path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    with urlopen(Request(f"http://127.0.0.1:{port}{path}", data=data,
                         headers=headers or {}), timeout=15) as response:
        return response.headers, response.read()


def submit(fixture):
    key = "trace-" + uuid.uuid4().hex
    headers, data = request(18080, "/v1/jobs",
                            {"fixture": fixture, "algorithm": "tokens-v1"},
                            {"Content-Type": "application/json", "Idempotency-Key": key})
    return json.loads(data)["id"], headers.get("Trace-Id")


def wait_job(job_id):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        _, data = request(18080, "/v1/jobs/" + job_id)
        job = json.loads(data)
        if job["state"] == "succeeded":
            return
        if job["state"] == "failed":
            raise RuntimeError("job failed")
        time.sleep(0.1)
    raise TimeoutError("job did not complete")


def spans(payload):
    # Tempo's trace-by-id JSON uses the OTLP resource/scope layout.
    for resource in payload.get("batches", payload.get("resourceSpans", [])):
        attrs = {a["key"]: a["value"].get("stringValue")
                 for a in resource.get("resource", {}).get("attributes", [])}
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                yield attrs, span


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("supply an immutable 40-character source revision")
    output = Path("output")
    output.mkdir(exist_ok=True)
    if (output / "trace-profile.json").exists():
        raise SystemExit("refusing to overwrite a trace/profile observation")
    observation = {"verification": "local-compose", "source_revision": args.revision,
                   "started_at": timestamp(),
                   "result": "failed", "errors": [], "cloud_provisioned": False}
    try:
        job_id, trace_id = submit("tiny-v1")
        if not trace_id or len(trace_id) != 32:
            raise ValueError("submission trace ID missing")
        wait_job(job_id)
        deadline = time.monotonic() + 30
        trace = None
        while time.monotonic() < deadline:
            try:
                _, data = request(19093, "/api/traces/" + trace_id,
                                  headers={"Accept": "application/json"})
                candidate = json.loads(data)
                observed = list(spans(candidate))
                names = {span["name"] for _, span in observed}
                services = {attrs.get("service.name") for attrs, _ in observed}
                revisions = {attrs.get("service.version") for attrs, _ in observed}
                if {"POST /v1/jobs", "persist job and outbox", "process job",
                    "analyze documents", "commit report"} <= names and {
                    "report-workshop-api", "report-workshop-worker"} <= services and revisions == {args.revision}:
                    trace = observed
                    break
            except (HTTPError, URLError):
                pass
            time.sleep(0.5)
        if trace is None:
            raise RuntimeError("correlated spans not observed in Tempo")
        persisted = next(span for _, span in trace if span["name"] == "persist job and outbox")
        worker = next(span for _, span in trace if span["name"] == "process job")
        if worker["parentSpanId"] != persisted["spanId"]:
            raise ValueError("worker parent does not match durable submission")
        observation["trace_id"] = trace_id
        observation["span_names"] = sorted({span["name"] for _, span in trace})
        observation["services"] = sorted({attrs["service.name"] for attrs, _ in trace})
        observation["durable_parent_matches"] = True

        # Keep the worker computing during a bounded five-second CPU capture.
        with ThreadPoolExecutor(max_workers=1) as pool:
            profile = pool.submit(request, 19091, "/debug/pprof/profile?seconds=5")
            jobs = []
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline and len(jobs) < 100:
                job, _ = submit("batch-v1")
                jobs.append(job)
                time.sleep(0.04)
            for job in jobs:
                wait_job(job)
            _, cpu = profile.result()
        _, heap = request(19091, "/debug/pprof/heap")
        for name, data in (("worker-cpu.pprof", cpu), ("worker-heap.pprof", heap)):
            with (output / name).open("xb") as stream:
                stream.write(data)
            observation[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        observation["profile_load_jobs"] = len(jobs)
        observation["result"] = "passed"
    except Exception as exc:
        observation["errors"].append(type(exc).__name__)
    observation["finished_at"] = timestamp()
    with (output / "trace-profile.json").open("x") as stream:
        json.dump(observation, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(observation["result"] + ": local trace/profile observation")
    if observation["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
