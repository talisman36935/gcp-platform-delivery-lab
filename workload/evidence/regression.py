"""Compare compiled local variants, then restore the exact baseline worker image."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

from record import timestamp
from trace_profile import request, submit, wait_job

COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f",
           "compose.tracing.yaml", "--profile", "observability"]
DOCUMENTS = ["observable reliable platforms " * 10000, "retries preserve work " * 10000]
FIXTURE_HASH = hashlib.sha256(json.dumps(DOCUMENTS, separators=(",", ":")).encode()).hexdigest()
EXPECTED = {"documents": 2, "tokens": 60000, "unique_tokens": 6,
            "duplicate_documents": 0, "input_sha256": FIXTURE_HASH}


def run(*args):
    return subprocess.run(list(args), check=True, capture_output=True, text=True).stdout.strip()


def worker_image():
    container = run(*COMPOSE, "ps", "-q", "worker")
    if not container or "\n" in container:
        raise RuntimeError("expected one local worker")
    owner = run("docker", "inspect", "--format",
                '{{index .Config.Labels "com.docker.compose.project"}}', container)
    if owner != "report-workshop":
        raise ValueError("experiment requires its dedicated report-workshop project")
    image = run("docker", "inspect", "--format", "{{.Image}}", container)
    tag = run("docker", "inspect", "--format", "{{.Config.Image}}", container)
    if not tag.startswith("report-workshop-worker"):
        raise ValueError("unexpected worker image tag")
    return image, tag


def ready(variant, revision):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            _, body = request(19091, "/metrics")
            metrics = body.decode()
            if (f'workshop_analysis_variant_info{{variant="{variant}"}} 1' in metrics
                and f'workshop_build_info{{revision="{revision}",role="worker"}} 1' in metrics):
                return
        except OSError:
            pass
        time.sleep(0.2)
    raise TimeoutError("worker identity did not become ready")


def phase(name, variant, revision, count, output):
    ready(variant, revision)
    for _ in range(2):
        job, _ = submit("batch-v1")
        wait_job(job)
    durations = []
    started = timestamp()
    deadline = time.monotonic() + 60
    with ThreadPoolExecutor(max_workers=1) as pool:
        profile = pool.submit(request, 19091, "/debug/pprof/profile?seconds=5")
        for _ in range(count):
            if time.monotonic() >= deadline:
                raise TimeoutError("phase exceeded its bound")
            job, _ = submit("batch-v1")
            wait_job(job)
            _, report = request(18080, "/v1/jobs/" + job + "/report")
            if json.loads(report) != EXPECTED:
                raise ValueError("variant changed the golden report")
            _, raw = request(18080, "/v1/jobs/" + job)
            state = json.loads(raw)
            accepted = datetime.fromisoformat(state["created_at"].replace("Z", "+00:00"))
            completed = datetime.fromisoformat(state["completed_at"].replace("Z", "+00:00"))
            elapsed = (completed - accepted).total_seconds()
            if not 0 <= elapsed <= 15:
                raise ValueError("invalid completion interval")
            durations.append(elapsed)
        _, cpu = profile.result()
    name_profile = name + "-cpu.pprof"
    with (output / name_profile).open("xb") as stream:
        stream.write(cpu)
    image, _ = worker_image()
    return {"phase": name, "variant": variant, "image_id": image,
            "started_at": started, "finished_at": timestamp(),
            "completion_seconds": durations, "median_seconds": statistics.median(durations),
            "golden_reports_match": True,
            "profile": {"file": name_profile, "bytes": len(cpu),
                        "sha256": hashlib.sha256(cpu).hexdigest()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision) or not 6 <= args.count <= 12:
        parser.error("supply a 40-character revision and count between 6 and 12")
    output = Path("output")
    output.mkdir(exist_ok=True)
    destination = output / "regression-recovery.json"
    if destination.exists():
        parser.error("refusing to overwrite an existing experiment")
    result = {
        "verification": "local-compose", "source_revision": args.revision,
        "scenario": "compiled-variant-regression",
        "fixture_sha256": FIXTURE_HASH, "requested_per_phase": args.count,
        "load": "sequential-closed-loop", "warmup_per_phase": 2,
        "criteria": {"regression_min_ratio": 1.5, "regression_min_delta_seconds": 0.05,
                     "recovery_max_ratio": 2.0, "recovery_jitter_seconds": 0.1},
        "started_at": timestamp(), "result": "failed", "phases": [],
        "errors": [], "baseline_image_restored": False, "cloud_provisioned": False,
    }
    baseline_image = None
    baseline_tag = None
    try:
        baseline_image, baseline_tag = worker_image()
        result["phases"].append(phase("baseline", "baseline", args.revision, args.count, output))
        environment = {**os.environ, "APP_REVISION": args.revision}
        subprocess.run([*COMPOSE, "build", "--build-arg", "REVISION=" + args.revision,
                        "--build-arg", "ANALYSIS_VARIANT=regressed", "worker"],
                       check=True, env=environment, timeout=300)
        run(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "worker")
        result["phases"].append(phase("regressed", "regressed", args.revision, args.count, output))
        run("docker", "image", "tag", baseline_image, baseline_tag)
        run(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "worker")
        result["phases"].append(phase("recovered", "baseline", args.revision, args.count, output))
        baseline, regressed, recovered = result["phases"]
        if not (baseline["image_id"] == recovered["image_id"] == baseline_image
                and regressed["image_id"] != baseline_image):
            raise ValueError("image identity did not change and recover correctly")
        b = baseline["median_seconds"]
        if regressed["median_seconds"] < max(b * 1.5, b + 0.05):
            raise ValueError("regression did not meet the declared minimum")
        if recovered["median_seconds"] > b * 2.0 + 0.1:
            raise ValueError("recovery exceeded its declared tolerance")
        result["result"] = "passed"
    except Exception as exc:
        result["errors"].append(type(exc).__name__)
    finally:
        if baseline_image and baseline_tag:
            try:
                run("docker", "image", "tag", baseline_image, baseline_tag)
                run(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "worker")
                ready("baseline", args.revision)
                if worker_image()[0] != baseline_image:
                    raise ValueError("baseline image was not restored")
                result["baseline_image_restored"] = True
            except Exception as exc:
                result["result"] = "failed"
                result["errors"].append(type(exc).__name__)
    result["finished_at"] = timestamp()
    with destination.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(result["result"] + ": local regression/recovery observation")
    if result["result"] != "passed" or not result["baseline_image_restored"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
