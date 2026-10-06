"""Check exclusive ownership, migration gates and namespace-limited delegation."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
import tempfile
from unittest.mock import patch
from render_delivery import main, render

RELEASE = {"source_revision": "a" * 40, "image": "ghcr.io/example/report@sha256:" + "b" * 64,
           "capabilities": ["schema-check", "cloud-queue-object-v1"]}
ROLLOUT_HEALTH = [{
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "current": "has(status.observedGeneration) && has(status.updatedReplicas) "
               "&& has(status.readyReplicas) && has(status.availableReplicas) "
               "&& status.observedGeneration == metadata.generation "
               "&& status.updatedReplicas == spec.replicas "
               "&& status.readyReplicas == spec.replicas "
               "&& status.availableReplicas == spec.replicas",
}]


class DeliveryTests(unittest.TestCase):
    def render_flux_graph(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            release = root / "release.json"
            release.write_text(json.dumps(RELEASE))
            output = root / "profile"
            with patch("sys.argv", ["render", "--release", str(release), "--owner", "flux",
                                    "--storage-class", "standard", "--output", str(output)]):
                main()
            return json.loads((output / "root/resources.json").read_text())["items"]

    def test_generated_trees_have_one_migration_owner_and_flux_order(self):
        for owner in ("config-sync", "flux"):
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                release = root / "release.json"
                release.write_text(json.dumps(RELEASE))
                output = root / "profile"
                with patch("sys.argv", ["render", "--release", str(release), "--owner", owner,
                                        "--storage-class", "standard", "--output", str(output)]):
                    main()
                owned = []
                for group in ("platform", "migrations", "apps"):
                    path = output / group / "resources.json"
                    if path.exists():
                        owned += json.loads(path.read_text())["items"]
                self.assertEqual(sum(i["kind"] == "Job" for i in owned), 1)
                identities = {(i["apiVersion"], i["kind"], i["metadata"].get("namespace"),
                               i["metadata"]["name"]) for i in owned}
                self.assertEqual(len(identities), len(owned))
                if owner == "flux":
                    graph = json.loads((output / "root/resources.json").read_text())["items"]
                    self.assertEqual(graph[1]["spec"]["dependsOn"], [{"name": "report-platform"}])
                    self.assertEqual(graph[2]["spec"]["dependsOn"], [{"name": "report-migrations"}])
                    self.assertTrue(all(i["spec"]["wait"] for i in graph))
                    self.assertNotIn("has(status)", graph[0]["spec"]["healthCheckExprs"][0]["current"])
                    self.assert_flux_app_health(graph)
                else:
                    self.assertFalse((output / "root").exists())

    def assert_flux_app_health(self, graph):
        apps = [item for item in graph if item["metadata"]["name"] == "report-apps"]
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["spec"].get("healthCheckExprs"), ROLLOUT_HEALTH)

    def test_flux_app_health_rejects_missing_or_weakened_checks(self):
        graph = self.render_flux_graph()
        missing = deepcopy(graph)
        missing[2]["spec"].pop("healthCheckExprs")
        weakened = deepcopy(graph)
        weakened[2]["spec"]["healthCheckExprs"][0]["current"] = "true"
        for invalid in (missing, weakened):
            with self.subTest(expression=invalid[2]["spec"].get("healthCheckExprs")):
                with self.assertRaises(AssertionError):
                    self.assert_flux_app_health(invalid)

    def test_disjoint_owners_and_gate(self):
        for owner in ("config-sync", "flux"):
            profile = render(release=RELEASE, owner=owner, storage_class="standard")
            sets = []
            for group in ("platform", "migrations", "apps"):
                identities = {(i["apiVersion"], i["kind"], i["metadata"].get("namespace"),
                               i["metadata"]["name"]) for i in profile[group]}
                self.assertEqual(len(identities), len(profile[group]))
                sets.append(identities)
            self.assertFalse(sets[0] & sets[1] or sets[1] & sets[2] or sets[0] & sets[2])
            role = next(i for i in profile["platform"] if i["kind"] == "Role")
            permitted = {r for rule in role["rules"] for r in rule["resources"]}
            self.assertTrue({"jobs", "deployments", "services"} <= permitted)
            self.assertFalse({"secrets", "serviceaccounts", "namespaces", "roles", "clusters"} & permitted)
            for deployment in (i for i in profile["apps"] if i["kind"] == "Deployment"):
                self.assertEqual(deployment["spec"]["template"]["spec"]["initContainers"][0]["args"], ["schema-check"])

    def test_rejects_legacy_release_or_cloud_owner_mismatch(self):
        with self.assertRaises(ValueError):
            render(release={**RELEASE, "capabilities": []}, owner="flux", storage_class="standard")
        with self.assertRaises(ValueError):
            render(release=RELEASE, owner="flux", backend="gcp", storage_class="standard")

    def test_cloud_identity_is_assigned_only_to_worker(self):
        cases = (
            ("config-sync", "gcp", {
                "GCP_PROJECT": "portfolio-lab",
                "PUBSUB_TOPIC": "report-jobs",
                "PUBSUB_SUBSCRIPTION": "report-jobs-sub",
                "REPORT_BUCKET": "report-portfolio-bucket",
                "GCP_SERVICE_ACCOUNT": "report-worker@portfolio-lab.iam.gserviceaccount.com",
            }),
            ("flux", "aws", {
                "AWS_REGION": "eu-west-2",
                "SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/report-jobs",
                "REPORT_BUCKET": "report-portfolio-bucket",
                "AWS_ROLE_ARN": "arn:aws:iam::123456789012:role/report-worker",
            }),
        )
        for owner, backend, settings in cases:
            with self.subTest(backend=backend):
                profile = render(release=RELEASE, owner=owner, storage_class="standard",
                                 backend=backend, settings=settings)
                accounts = {item["metadata"]["name"]: item for item in profile["platform"]
                            if item["kind"] == "ServiceAccount"}
                self.assertTrue({"report-api", "report-worker", "report-migrate"}
                                <= set(accounts))
                linked = [name for name, account in accounts.items()
                          if "iam.gke.io/gcp-service-account" in
                          account["metadata"].get("annotations", {})]
                self.assertEqual(linked, ["report-worker"] if backend == "gcp" else [])

                deployments = {item["metadata"]["name"]: item for item in profile["apps"]
                               if item["kind"] == "Deployment"}
                api_pod = deployments["report-api"]["spec"]["template"]["spec"]
                worker_pod = deployments["report-worker"]["spec"]["template"]["spec"]
                migrate = profile["migrations"][0]["spec"]["template"]["spec"]
                self.assertEqual(api_pod["serviceAccountName"], "report-api")
                self.assertEqual(worker_pod["serviceAccountName"], "report-worker")
                self.assertEqual(migrate["serviceAccountName"], "report-migrate")
                for pod in (api_pod, migrate):
                    self.assertFalse(pod["automountServiceAccountToken"])
                    self.assertFalse(pod.get("volumes"))
                    env_names = {entry["name"] for container in pod["containers"]
                                 for entry in container.get("env", [])}
                    self.assertFalse(env_names & (set(settings) - {"GCP_SERVICE_ACCOUNT"}))
                    self.assertFalse(env_names & {"AWS_WEB_IDENTITY_TOKEN_FILE"})
                worker_env = {entry["name"]: entry.get("value")
                              for entry in worker_pod["containers"][0]["env"]}
                if backend == "gcp":
                    self.assertEqual(accounts["report-worker"]["metadata"]["annotations"][
                        "iam.gke.io/gcp-service-account"], settings["GCP_SERVICE_ACCOUNT"])
                    self.assertEqual(worker_env["GCP_PROJECT"], settings["GCP_PROJECT"])
                    self.assertNotIn("GCP_PROJECT", {entry["name"]
                                     for entry in api_pod["containers"][0]["env"]})
                else:
                    self.assertEqual(worker_env["AWS_ROLE_ARN"], settings["AWS_ROLE_ARN"])
                    self.assertEqual(worker_pod["volumes"][0]["projected"]["sources"][0]
                                     ["serviceAccountToken"]["audience"], "sts.amazonaws.com")
                expected_worker_settings = set(settings) - {"GCP_SERVICE_ACCOUNT"}
                self.assertTrue(expected_worker_settings <= set(worker_env))
