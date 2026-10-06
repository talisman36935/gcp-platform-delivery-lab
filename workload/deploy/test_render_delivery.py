"""Check exclusive ownership, migration gates and namespace-limited delegation."""

import unittest
from render_delivery import render

RELEASE = {"source_revision": "a" * 40, "image": "ghcr.io/example/report@sha256:" + "b" * 64,
           "capabilities": ["schema-check", "cloud-queue-object-v1"]}


class DeliveryTests(unittest.TestCase):
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
