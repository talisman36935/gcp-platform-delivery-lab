"""Verify local API replicas and recovery after a real worker SIGKILL."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.request import Request, urlopen
import uuid

COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f",
           "compose.tracing.yaml", "-f", "compose.replicas.yaml",
           "--profile", "observability"]
EXPECTED = {"documents": 3, "tokens": 11, "unique_tokens": 6,
            "duplicate_documents": 1,
            "input_sha256": "2522de9d1c28cf3a163c3703dbabb2b63009e5daa6a8d98f2aac85f577307bd5"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          timeout=30).stdout.strip()


def sql(query):
    return run(*COMPOSE, "exec", "-T", "db", "psql", "-U", "workshop",
               "-d", "workshop", "-At", "-v", "ON_ERROR_STOP=1", "-c", query)


def request(port, path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = None if body is None else json.dumps(body).encode()
    with urlopen(Request(f"http://127.0.0.1:{port}" + path, data=data,
                         headers=headers), timeout=3) as response:
        return json.load(response)


def wait(check, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except OSError:
            pass
        time.sleep(0.1)
    raise TimeoutError("bounded observation did not become true")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("supply the exact source revision")
    output = Path("output/replica-recovery.json")
    if output.exists():
        parser.error("refusing to overwrite an observation")
    owner = run(*COMPOSE, "ps", "-q", "db")
    if not owner or run("docker", "inspect", "--format",
                        '{{index .Config.Labels "com.docker.compose.project"}}',
                        owner) != "report-workshop":
        parser.error("requires the dedicated synthetic Compose database")
    record = {"verification": "local-compose", "source_revision": args.revision,
              "scenario": "replica-worker-crash", "started_at": stamp(),
              "result": "failed", "api_replica_idempotency": False,
              "surviving_api_accepts": False, "worker_sigkill": False,
              "worker_exit_code": None, "source_images_match": False,
              "recovered_attempt": None, "golden_report_match": False,
              "attempt_history": [], "test_gate_removed": False,
              "baseline_restored": False, "database_ha_verified": False,
              "cloud_provisioned": False, "errors": []}
    gate = None
    try:
        for service in ("api", "worker"):
            container = run(*COMPOSE, "ps", "-q", service)
            built = run("docker", "inspect", "--format",
                        '{{index .Config.Labels "org.opencontainers.image.revision"}}',
                        run("docker", "inspect", "--format", "{{.Image}}", container))
            if built != args.revision:
                raise ValueError("source image revision mismatch")
        record["source_images_match"] = True
        run(*COMPOSE, "up", "-d", "--no-deps", "api-replica")
        wait(lambda: request(18081, "/readyz"), 20)
        run(*COMPOSE, "stop", "worker", "worker-replica")
        key = "replicas-" + uuid.uuid4().hex
        payload = {"fixture": "tiny-v1", "algorithm": "tokens-v1"}
        job = request(18080, "/v1/jobs", payload, key)
        duplicate = request(18081, "/v1/jobs", payload, key)
        if job["id"] != duplicate["id"] or not re.fullmatch(r"[0-9a-f]{32}", job["id"]):
            raise ValueError("replica idempotency failed")
        record["api_replica_idempotency"] = True
        job_id = job["id"]
        # A database-only gate ensures the kill happens after a durable claim
        # and before completion, without adding production sleep/fault switches.
        sql("CREATE FUNCTION replica_test_gate() RETURNS trigger LANGUAGE plpgsql AS $$ "
            f"BEGIN IF NEW.id='{job_id}' AND NEW.state='succeeded' AND NEW.attempt=1 "
            "THEN PERFORM pg_advisory_xact_lock(194002); END IF; RETURN NEW; END $$; "
            "CREATE TRIGGER replica_test_gate BEFORE UPDATE ON jobs "
            "FOR EACH ROW EXECUTE FUNCTION replica_test_gate();")
        gate = subprocess.Popen(
            [*COMPOSE, "exec", "-T", "db", "psql", "-U", "workshop", "-d",
             "workshop", "-c", "SET application_name='replica-test-gate'; "
             "SELECT pg_advisory_lock(194002); SELECT pg_sleep(90);"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        wait(lambda: sql("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a "
                         "ON a.pid=l.pid WHERE a.application_name='replica-test-gate' "
                         "AND l.locktype='advisory' AND l.granted") == "1", 10)
        run(*COMPOSE, "start", "worker")
        wait(lambda: sql("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a "
                         "ON a.pid=l.pid WHERE l.locktype='advisory' AND NOT l.granted")
             == "1", 10)
        before = request(18081, "/v1/jobs/" + job_id)
        if before["state"] != "running" or before["attempt"] != 1:
            raise ValueError("worker not observed before completion")
        worker = run(*COMPOSE, "ps", "-q", "worker")
        run(*COMPOSE, "kill", "-s", "SIGKILL", "worker")
        exit_code = int(run("docker", "inspect", "--format", "{{.State.ExitCode}}", worker))
        if exit_code != 137:
            raise ValueError("worker SIGKILL exit was not observed")
        record["worker_exit_code"] = exit_code
        record["worker_sigkill"] = True
        record["killed_at"] = stamp()
        sql("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE application_name='replica-test-gate'; "
            "DROP TRIGGER replica_test_gate ON jobs; DROP FUNCTION replica_test_gate();")
        record["test_gate_removed"] = True
        run(*COMPOSE, "stop", "api")
        repeat = request(18081, "/v1/jobs", payload, key)
        if repeat["id"] != job_id:
            raise ValueError("surviving API lost accepted job")
        record["surviving_api_accepts"] = True
        run(*COMPOSE, "up", "-d", "--no-deps", "worker-replica")
        def recovered():
            state = request(18081, "/v1/jobs/" + job_id)
            return state if state["state"] == "succeeded" else None
        done = wait(recovered, 45)
        record["recovered_at"] = stamp()
        record["recovered_attempt"] = done["attempt"]
        report = request(18081, "/v1/jobs/" + job_id + "/report")
        record["golden_report_match"] = report == EXPECTED
        history = sql(f"SELECT token || ':' || (completed_at IS NOT NULL)::text "
                      f"FROM attempts WHERE job_id='{job_id}' ORDER BY token")
        record["attempt_history"] = history.splitlines()
        if (done["attempt"] != 2 or report != EXPECTED
                or record["attempt_history"] != ["1:false", "2:true"]):
            raise ValueError("crash recovery invariant failed")
        record["result"] = "passed"
    except Exception as exc:
        record["errors"].append(type(exc).__name__)
    finally:
        try:
            sql("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE application_name='replica-test-gate'; "
                "DROP TRIGGER IF EXISTS replica_test_gate ON jobs; "
                "DROP FUNCTION IF EXISTS replica_test_gate();")
            record["test_gate_removed"] = True
            run(*COMPOSE, "rm", "-s", "-f", "api-replica", "worker-replica")
            run(*COMPOSE, "start", "api", "worker")
            wait(lambda: request(18080, "/readyz"), 20)
            worker = run(*COMPOSE, "ps", "-q", "worker")
            if not worker or run("docker", "inspect", "--format", "{{.State.Running}}",
                                 worker) != "true":
                raise ValueError("baseline worker not restored")
            record["baseline_restored"] = True
        except Exception as exc:
            record["errors"].append(type(exc).__name__)
            record["result"] = "failed"
        if gate:
            try:
                gate.wait(timeout=5)
            except subprocess.TimeoutExpired:
                gate.kill()
                gate.wait(timeout=5)
        record["finished_at"] = stamp()
        output.parent.mkdir(exist_ok=True)
        with output.open("x") as stream:
            json.dump(record, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(record["result"] + ": local replica/crash recovery")
    if record["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
