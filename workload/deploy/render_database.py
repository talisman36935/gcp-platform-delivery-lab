"""Render a dormant three-instance PostgreSQL profile; no credentials emitted."""

import argparse
import json
import re


def render(*, image: str, storage_class: str, namespace: str = "report-dev") -> dict:
    if not re.fullmatch(r"ghcr\.io/cloudnative-pg/postgresql:18\.[0-9]+@sha256:[0-9a-f]{64}",
                        image):
        raise ValueError("pin a compatible PostgreSQL 18 CNPG image tag and digest")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", storage_class):
        raise ValueError("select an explicit qualified storage class")
    if not re.fullmatch(r"report-[a-z0-9-]{1,40}", namespace):
        raise ValueError("select a dedicated report namespace")
    return {"apiVersion": "postgresql.cnpg.io/v1", "kind": "Cluster",
            "metadata": {"name": "report-db", "namespace": namespace},
            "spec": {
                "instances": 3, "imageName": image,
                "enableSuperuserAccess": False,
                "bootstrap": {"initdb": {"database": "workshop", "owner": "workshop"}},
                "storage": {"size": "10Gi", "storageClass": storage_class},
                "resources": {"requests": {"cpu": "250m", "memory": "512Mi"},
                              "limits": {"cpu": "1", "memory": "1Gi"}},
                "affinity": {"enablePodAntiAffinity": True,
                             "podAntiAffinityType": "required",
                             "topologyKey": "topology.kubernetes.io/zone"},
                "postgresql": {
                    "parameters": {"shared_buffers": "128MB", "max_connections": "100"},
                    "synchronous": {"method": "any", "number": 1,
                                    "dataDurability": "required", "failoverQuorum": True},
                },
            }}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--storage-class", required=True)
    parser.add_argument("--namespace", default="report-dev")
    args = parser.parse_args()
    try:
        result = render(image=args.image, storage_class=args.storage_class,
                        namespace=args.namespace)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
