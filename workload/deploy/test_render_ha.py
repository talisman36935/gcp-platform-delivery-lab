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
        for item in items:
            self.assertEqual(item["metadata"]["namespace"], "report-dev")
            self.assertNotIn(item["kind"], {"Secret", "Namespace", "ClusterRole"})
            if item["kind"] == "PodDisruptionBudget":
                self.assertEqual(item["spec"]["minAvailable"], 2)
            if item["kind"] == "Service":
                self.assertEqual(item["spec"]["type"], "ClusterIP")

    def test_rejects_mutable_or_unscoped_inputs(self):
        for values in ({"image": "report:latest", "revision": REVISION},
                       {"image": IMAGE, "revision": "main"},
                       {"image": IMAGE, "revision": REVISION, "namespace": "default"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                render(**values)


if __name__ == "__main__":
    unittest.main()
