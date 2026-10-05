"""Qualify real PostgreSQL promotion/node loss in a disposable hosted kind cluster."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen
import uuid

import yaml

from render_database import render as database
from render_ha import render as application

NAME = "portfolio-ha"
NAMESPACE = "report-ha"
NODE_IMAGE = "kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0"
DB_IMAGE = "ghcr.io/cloudnative-pg/postgresql:18.4@sha256:6138f19539304b585c6cafd1af82ca407f184139459a8e06f0880df4556d3588"
OPERATOR_IMAGE = "ghcr.io/cloudnative-pg/cloudnative-pg:1.30.1@sha256:923c267ec29636db3bee20f993d0ec4973fa22998e1adad37da79e4d32b5bc07"
OPERATOR_URL = "https://github.com/cloudnative-pg/cloudnative-pg/releases/download/v1.30.1/cnpg-1.30.1.yaml"
OPERATOR_HASH = "37237f145d8138256ea25ae830f87759255665ff08f8d552fdd8224a5ec032fb"
EXPECTED = {"documents": 3, "tokens": 11, "unique_tokens": 6,
            "duplicate_documents": 1,
            "input_sha256": "2522de9d1c28cf3a163c3703dbabb2b63009e5daa6a8d98f2aac85f577307bd5"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def run(*args, data=None, timeout=90):
    return subprocess.run(args, input=data, check=True, capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def kube(*args, **kwargs):
    return run("kubectl", "--context", "kind-" + NAME, *args, **kwargs)


def get(kind, name=None):
    return json.loads(kube("-n", NAMESPACE, "get", kind,
                           *([name] if name else []), "-o", "json"))


def apply(obj):
    # In-memory stdin/captured output keeps registry and generated DB secrets
    # out of argv, files, logs and the allowlisted observation artifact.
    kube("apply", "-f", "-", data=json.dumps(obj))


def wait(check, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, subprocess.CalledProcessError):
            pass
        time.sleep(2)
    raise TimeoutError("bounded qualification condition not observed")


def ready_instances():
    cluster = get("clusters.postgresql.cnpg.io", "report-db")
    return cluster if cluster.get("status", {}).get("readyInstances") == 3 else None


def primary():
    return get("clusters.postgresql.cnpg.io", "report-db").get("status", {}).get("currentPrimary")


def sql(query):
    return kube("-n", NAMESPACE, "exec", primary(), "-c", "postgres", "--",
                "psql", "-U", "postgres", "-d", "workshop", "-At", "-c", query)


def ready_pods(role, exclude_node=None):
    return [pod for pod in get("pods")["items"]
            if pod["metadata"].get("labels", {}).get("app.kubernetes.io/component") == role
            and pod["spec"].get("nodeName") != exclude_node
            and not pod["metadata"].get("deletionTimestamp")
            and any(c["type"] == "Ready" and c["status"] == "True"
                    for c in pod.get("status", {}).get("conditions", []))]


def start_forward(exclude_node=None):
    pod = wait(lambda: ready_pods("api", exclude_node), 90)[0]
    process = subprocess.Popen([
        "kubectl", "--context", "kind-" + NAME, "-n", NAMESPACE,
        "port-forward", "pod/" + pod["metadata"]["name"], "18080:8080"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait(lambda: request("/readyz"), 30)
    except Exception:
        stop_forward(process)
        raise
    return process


def stop_forward(process):
    if process:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def request(path, payload=None, key=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    with urlopen(Request("http://127.0.0.1:18080" + path, data=data,
                         headers=headers), timeout=5) as response:
        return json.load(response)


def submit():
    key = "kind-ha-" + uuid.uuid4().hex
    payload = {"fixture": "tiny-v1", "algorithm": "tokens-v1"}
    job = request("/v1/jobs", payload, key)
    if request("/v1/jobs", payload, key)["id"] != job["id"]:
        raise ValueError("idempotency changed")
    def completed():
        state = request("/v1/jobs/" + job["id"])
        return state if state["state"] == "succeeded" else None
    wait(completed, 90)
    if request("/v1/jobs/" + job["id"] + "/report") != EXPECTED:
        raise ValueError("golden report changed")
    return job["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    profile = application(image=args.image, revision=args.revision, namespace=NAMESPACE)
    if os.getenv("GITHUB_ACTIONS") != "true":
        parser.error("heavy qualification is hosted-CI only")
    if NAME in run("kind", "get", "clusters").splitlines():
        parser.error("refusing to overwrite an existing cluster")
    output = Path("output/kubernetes-ha.json")
    if output.exists():
        parser.error("refusing to overwrite observations")
    record = {"verification": "hosted-kind", "source_revision": args.revision,
              "image": args.image, "database_image": DB_IMAGE,
              "operator_image": OPERATOR_IMAGE, "started_at": stamp(),
              "result": "failed", "simulation": "three labelled workers on one host",
              "cloud_provisioned": False, "cloud_zone_failure_verified": False,
              "primary_promotion": None, "node_failure": None,
              "baseline_jobs": [], "fault_queue_jobs": [], "pending_before_node_failure": 0,
              "recovery_jobs": [], "accepted_reports_preserved": False,
              "cluster_deleted": False, "errors": []}
    forward = None
    stopped_node = None
    created = False
    original_config = os.environ.get("KUBECONFIG")
    with tempfile.TemporaryDirectory(prefix="portfolio-ha-") as scratch:
        os.environ["KUBECONFIG"] = str(Path(scratch) / "kubeconfig")
        try:
            created = True
            run("kind", "create", "cluster", "--name", NAME, "--config",
                str(Path(__file__).with_name("kind-ha.yaml")), "--image", NODE_IMAGE,
                "--wait", "180s", timeout=300)
            apply({"apiVersion": "v1", "kind": "Namespace", "metadata": {
                "name": NAMESPACE, "labels": {"pod-security.kubernetes.io/enforce": "restricted"}}})
            credential = base64.b64encode((os.environ["REGISTRY_USER"] + ":" +
                                          os.environ["GH_TOKEN"]).encode()).decode()
            config = json.dumps({"auths": {"ghcr.io": {"auth": credential}}})
            apply({"apiVersion": "v1", "kind": "Secret", "metadata": {
                "name": "ci-image-pull", "namespace": NAMESPACE},
                "type": "kubernetes.io/dockerconfigjson",
                "data": {".dockerconfigjson": base64.b64encode(config.encode()).decode()}})
            with urlopen(OPERATOR_URL, timeout=30) as response:
                operator = response.read()
            if hashlib.sha256(operator).hexdigest() != OPERATOR_HASH:
                raise ValueError("operator release checksum differs")
            documents = [d for d in yaml.safe_load_all(operator) if d]
            for obj in documents:
                if obj["kind"] == "Deployment":
                    obj["spec"]["replicas"] = 2
                    pod = obj["spec"]["template"]["spec"]
                    pod["affinity"] = {"podAntiAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": [{
                            "labelSelector": obj["spec"]["selector"],
                            "topologyKey": "kubernetes.io/hostname"}]}}
                    for container in pod["containers"]:
                        container["image"] = OPERATOR_IMAGE
                        for env in container.get("env", []):
                            if env["name"] == "OPERATOR_IMAGE_NAME":
                                env["value"] = OPERATOR_IMAGE
            apply({"apiVersion": "v1", "kind": "List", "items": documents})
            kube("wait", "--for=condition=Established", "crd/clusters.postgresql.cnpg.io",
                 "--timeout=120s", timeout=150)
            kube("-n", "cnpg-system", "rollout", "status", "deployment/cnpg-controller-manager",
                 "--timeout=180s", timeout=200)
            apply(database(image=DB_IMAGE, storage_class="standard", namespace=NAMESPACE))
            wait(ready_instances, 480)
            for obj in profile["items"]:
                if obj["kind"] == "ServiceAccount":
                    obj["imagePullSecrets"] = [{"name": "ci-image-pull"}]
            migrations = [i for i in profile["items"] if i["kind"] == "Job"]
            bootstrap = [i for i in profile["items"] if i["kind"] == "ServiceAccount"]
            apply({"apiVersion": "v1", "kind": "List", "items": bootstrap + migrations})
            kube("-n", NAMESPACE, "wait", "--for=condition=Complete",
                 "job/" + migrations[0]["metadata"]["name"], "--timeout=120s", timeout=150)
            apply({"apiVersion": "v1", "kind": "List", "items": [
                i for i in profile["items"] if i["kind"] not in {"Job", "ServiceAccount"}]})
            for role in ("api", "worker"):
                kube("-n", NAMESPACE, "rollout", "status", "deployment/report-" + role,
                     "--timeout=180s", timeout=200)
                pods = ready_pods(role)
                if len(pods) != 3 or len({p["spec"]["nodeName"] for p in pods}) != 3:
                    raise ValueError("replicas did not occupy three distinct workers")
                if any(p["spec"]["containers"][0]["image"] != args.image for p in pods):
                    raise ValueError("deployed image differs from release")
            forward = start_forward()
            record["baseline_jobs"] = [submit() for _ in range(5)]
            record["synchronous_standby_names"] = sql("SHOW synchronous_standby_names")
            if not record["synchronous_standby_names"].startswith("ANY 1"):
                raise ValueError("synchronous replication not observed")
            old_primary = primary()
            started = time.monotonic()
            kube("-n", NAMESPACE, "delete", "pod", old_primary, "--timeout=90s", timeout=100)
            changed = wait(lambda: primary() if primary() and primary() != old_primary else None, 180)
            wait(ready_instances, 240)
            record["primary_promotion"] = {"old": old_primary, "new": changed,
                                           "seconds": round(time.monotonic() - started, 3),
                                           "fault": "controlled primary pod deletion"}
            for job in record["baseline_jobs"]:
                if request("/v1/jobs/" + job + "/report") != EXPECTED:
                    raise ValueError("acknowledged report missing after promotion")
            record["recovery_jobs"].append(submit())
            old_primary = primary()
            stopped_node = get("pod", old_primary)["spec"]["nodeName"]
            if not re.fullmatch(r"portfolio-ha-worker[0-9]*", stopped_node):
                raise ValueError("fault target must be this cluster's worker")
            # A bounded, test-only completion delay makes outstanding work
            # deterministic without changing the published application image.
            sql("CREATE FUNCTION ha_test_gate() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN IF NEW.state='succeeded' AND OLD.state<>'succeeded' "
                "THEN PERFORM pg_sleep(10); END IF; RETURN NEW; END $$; "
                "CREATE TRIGGER ha_test_gate BEFORE UPDATE ON jobs "
                "FOR EACH ROW EXECUTE FUNCTION ha_test_gate()")
            for _ in range(20):
                job = request("/v1/jobs", {"fixture": "tiny-v1", "algorithm": "tokens-v1"},
                              "fault-queue-" + uuid.uuid4().hex)["id"]
                if not re.fullmatch(r"[0-9a-f]{32}", job):
                    raise ValueError("invalid accepted job identifier")
                record["fault_queue_jobs"].append(job)
            identifiers = ",".join("'" + job + "'" for job in record["fault_queue_jobs"])
            record["pending_before_node_failure"] = int(sql(
                "SELECT count(*) FROM jobs WHERE state IN ('pending','running') "
                "AND id IN (" + identifiers + ")"))
            if record["pending_before_node_failure"] == 0:
                raise ValueError("no outstanding accepted work observed before fault")
            stop_forward(forward)
            forward = None
            started = time.monotonic()
            run("docker", "stop", "--time", "0", stopped_node)
            if run("docker", "inspect", "--format", "{{.State.Running}}", stopped_node) != "false":
                raise ValueError("worker did not stop")
            changed = wait(lambda: primary() if primary() and primary() != old_primary else None, 240)
            wait(lambda: len(ready_pods("api", stopped_node)) >= 2
                 and len(ready_pods("worker", stopped_node)) >= 2, 120)
            forward = start_forward(stopped_node)
            sql("DROP TRIGGER ha_test_gate ON jobs; DROP FUNCTION ha_test_gate()")
            record["test_completion_gate_removed"] = True
            record["node_failure"] = {"node": stopped_node, "old_primary": old_primary,
                                      "new_primary": changed,
                                      "seconds": round(time.monotonic() - started, 3),
                                      "surviving_api_replicas": len(ready_pods("api", stopped_node)),
                                      "surviving_worker_replicas": len(ready_pods("worker", stopped_node))}
            record["recovery_jobs"] += [submit() for _ in range(5)]
            for job in record["fault_queue_jobs"]:
                wait(lambda: request("/v1/jobs/" + job)["state"] == "succeeded", 90)
            for job in record["baseline_jobs"] + record["fault_queue_jobs"] + record["recovery_jobs"]:
                if request("/v1/jobs/" + job + "/report") != EXPECTED:
                    raise ValueError("accepted report lost")
            record["accepted_reports_preserved"] = True
            run("docker", "start", stopped_node)
            stopped_node = None
            wait(ready_instances, 300)
            wait(lambda: len(ready_pods("api")) == 3 and len(ready_pods("worker")) == 3, 180)
            record["result"] = "passed"
        except Exception as exc:
            record["errors"].append(type(exc).__name__)
            # Metadata/status diagnostics only, never secrets or credential files.
            for kind in ("pods", "clusters.postgresql.cnpg.io", "events"):
                try:
                    print(kube("-n", NAMESPACE, "get", kind))
                except Exception:
                    pass
        finally:
            stop_forward(forward)
            if stopped_node:
                try:
                    run("docker", "start", stopped_node)
                except Exception:
                    pass
            if created:
                try:
                    run("kind", "delete", "cluster", "--name", NAME, timeout=120)
                    record["cluster_deleted"] = NAME not in run("kind", "get", "clusters").splitlines()
                except Exception as exc:
                    record["errors"].append(type(exc).__name__)
            if not record["cluster_deleted"]:
                record["result"] = "failed"
            record["finished_at"] = stamp()
            output.parent.mkdir(exist_ok=True)
            with output.open("x") as stream:
                json.dump(record, stream, indent=2, allow_nan=False)
                stream.write("\n")
            if original_config is None:
                os.environ.pop("KUBECONFIG", None)
            else:
                os.environ["KUBECONFIG"] = original_config
    print(record["result"] + ": hosted kind database/workload qualification")
    if record["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
