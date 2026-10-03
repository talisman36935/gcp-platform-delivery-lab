"""Check rendered Kubernetes identities for overlapping Config Sync owners."""

import subprocess

import yaml


def identities(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path],
        check=True, capture_output=True, text=True,
    )
    objects = list(yaml.safe_load_all(result.stdout))
    return {
        (obj["apiVersion"].split("/")[0] if "/" in obj["apiVersion"] else "",
         obj["kind"], obj["metadata"].get("namespace", ""), obj["metadata"]["name"])
        for obj in objects
    }


overlap = identities("gitops/platform") & identities("gitops/apps/report")
if overlap:
    raise SystemExit(f"Competing owners: {sorted(overlap)}")
print("RootSync and RepoSync rendered object identities are disjoint.")
