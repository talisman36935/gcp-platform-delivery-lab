"""Check the database durability intent without claiming runtime failover."""

import unittest

from render_database import render

IMAGE = "ghcr.io/cloudnative-pg/postgresql:18.4@sha256:" + "a" * 64


class DatabaseTests(unittest.TestCase):
    def test_durability_contract(self):
        spec = render(image=IMAGE, storage_class="lab-db")["spec"]
        self.assertEqual(spec["instances"], 3)
        self.assertEqual(spec["affinity"]["topologyKey"], "topology.kubernetes.io/zone")
        self.assertEqual(spec["affinity"]["podAntiAffinityType"], "required")
        self.assertEqual(spec["postgresql"]["synchronous"], {
            "method": "any", "number": 1, "dataDurability": "required",
            "failoverQuorum": True})
        self.assertFalse(spec["enableSuperuserAccess"])
        self.assertNotIn("secret", spec["bootstrap"]["initdb"])

    def test_rejects_unpinned_images(self):
        with self.assertRaises(ValueError):
            render(image="postgres:latest", storage_class="lab-db")


if __name__ == "__main__":
    unittest.main()
