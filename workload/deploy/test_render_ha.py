"""Check explicit HA placement, immutable release inputs and privilege bounds."""

import unittest

from render_ha import render

IMAGE = "ghcr.io/example/report@sha256:" + "a" * 64
REVISION = "b" * 40


class ProfileTests(unittest.TestCase):
    def test_ha_contract(self):
        items = render(image=IMAGE, revision=REVISION)["items"]
        deployments = [i for i in items if i["kind"] == "Deployment"]
        self.assertEqual(len(deployments), 2)
        accounts = {i["metadata"]["name"]: i for i in items
                    if i["kind"] == "ServiceAccount"}
        self.assertEqual(set(accounts), {"report-api", "report-worker", "report-migrate"})
        self.assertTrue(all(not account["automountServiceAccountToken"]
                            for account in accounts.values()))
        for deployment in deployments:
            self.assertEqual(deployment["spec"]["replicas"], 3)
            pod = deployment["spec"]["template"]["spec"]
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertTrue(pod["securityContext"]["runAsNonRoot"])
            self.assertEqual(pod["topologySpreadConstraints"][0]["whenUnsatisfiable"],
                             "DoNotSchedule")
            self.assertIn("requiredDuringSchedulingIgnoredDuringExecution",
                          pod["affinity"]["podAntiAffinity"])
            self.assertEqual(pod["containers"][0]["image"], IMAGE)
            role = deployment["metadata"]["name"].removeprefix("report-")
            self.assertEqual(pod["serviceAccountName"], "report-" + role)
            probes = pod["containers"][0]
            if role == "worker":
                self.assertEqual(probes["livenessProbe"]["tcpSocket"]["port"], "metrics")
                self.assertEqual(probes["readinessProbe"]["httpGet"],
                                 {"path": "/readyz", "port": "metrics"})
            else:
                self.assertEqual(probes["readinessProbe"]["httpGet"],
                                 {"path": "/readyz", "port": "http"})
        for item in items:
            self.assertEqual(item["metadata"]["namespace"], "report-dev")
            self.assertNotIn(item["kind"], {"Secret", "Namespace", "ClusterRole"})
            if item["kind"] == "PodDisruptionBudget":
                self.assertEqual(item["spec"]["minAvailable"], 2)
            if item["kind"] == "Service":
                self.assertEqual(item["spec"]["type"], "ClusterIP")
            if item["kind"] == "Job":
                self.assertEqual(item["spec"]["template"]["spec"]["serviceAccountName"],
                                 "report-migrate")

    def test_rejects_mutable_or_unscoped_inputs(self):
        for values in ({"image": "report:latest", "revision": REVISION},
                       {"image": IMAGE, "revision": "main"},
                       {"image": IMAGE, "revision": REVISION, "namespace": "default"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                render(**values)


if __name__ == "__main__":
    unittest.main()
