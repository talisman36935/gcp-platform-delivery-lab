"""Check exclusive ownership, migration gates and namespace-limited delegation."""

import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from render_delivery import main, render

RELEASE = {"source_revision": "a" * 40, "image": "ghcr.io/example/report@sha256:" + "b" * 64,
           "capabilities": ["schema-check", "cloud-queue-object-v1"]}


class DeliveryTests(unittest.TestCase):
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
