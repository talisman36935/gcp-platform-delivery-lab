"""Render a dormant, namespaced API/worker HA profile with an immutable image."""

import argparse
from copy import deepcopy
import json
import re


def render(*, image: str, revision: str, namespace: str = "report-dev") -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}", image):
        raise ValueError("image must be an immutable repository digest")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must identify the reviewed source")
    if not re.fullmatch(r"report-[a-z0-9-]{1,40}", namespace):
        raise ValueError("select a dedicated report namespace")
    items = []

    def obj(api, kind, name, spec=None):
        value = {"apiVersion": api, "kind": kind, "metadata": {
            "name": name, "namespace": namespace,
            "labels": {"app.kubernetes.io/name": "report-workshop"},
            "annotations": {"portfolio.whitt.uk/source-revision": revision}}}
        if spec is not None:
            value["spec"] = spec
        items.append(value)
        return value

    obj("v1", "ServiceAccount", "report-workshop")["automountServiceAccountToken"] = False
    for role in ("api", "worker"):
        labels = {"app.kubernetes.io/name": "report-workshop",
                  "app.kubernetes.io/component": role}
        selector = {"matchLabels": labels}
        container = {
            "name": role, "image": image, "args": [role],
            "env": [{"name": "DATABASE_URL", "valueFrom": {"secretKeyRef": {
                "name": "report-database", "key": "uri"}}},
                {"name": "METRICS_ADDR", "value": "0.0.0.0:9090"}],
            "ports": [{"name": "metrics", "containerPort": 9090}],
            "resources": {"requests": {"cpu": "100m" if role == "api" else "250m",
                                      "memory": "128Mi" if role == "api" else "256Mi"},
                          "limits": {"cpu": "1", "memory": "512Mi"}},
            "securityContext": {"allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]}},
        }
        if role == "api":
            container["env"].append({"name": "LISTEN_ADDR", "value": "0.0.0.0:8080"})
            container["ports"].append({"name": "http", "containerPort": 8080})
            live = {"httpGet": {"path": "/healthz", "port": "http"}}
            ready = {"httpGet": {"path": "/readyz", "port": "http"}}
        else:
            live = {"tcpSocket": {"port": "metrics"}}
            ready = deepcopy(live)
        container["startupProbe"] = {**deepcopy(live), "periodSeconds": 2,
                                     "failureThreshold": 30}
        container["livenessProbe"] = {**live, "periodSeconds": 10}
        container["readinessProbe"] = {**ready, "periodSeconds": 5}
        obj("apps/v1", "Deployment", "report-" + role, {
            "replicas": 3, "selector": selector,
            "strategy": {"type": "RollingUpdate", "rollingUpdate": {
                "maxSurge": 0, "maxUnavailable": 1}},
            "template": {"metadata": {"labels": labels}, "spec": {
                "serviceAccountName": "report-workshop",
                "automountServiceAccountToken": False,
                "terminationGracePeriodSeconds": 45,
                "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                                    "runAsGroup": 65532,
                                    "seccompProfile": {"type": "RuntimeDefault"}},
                "topologySpreadConstraints": [{"maxSkew": 1,
                    "topologyKey": "topology.kubernetes.io/zone",
                    "whenUnsatisfiable": "DoNotSchedule", "labelSelector": selector}],
                "affinity": {"podAntiAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": [{
                        "labelSelector": selector,
                        "topologyKey": "kubernetes.io/hostname"}]}},
                "containers": [container],
            }},
        })
        obj("policy/v1", "PodDisruptionBudget", "report-" + role,
            {"minAvailable": 2, "selector": selector})
        obj("v1", "Service", "report-" + role, {
            "type": "ClusterIP", "selector": labels,
            "ports": ([{"name": "http", "port": 8080, "targetPort": "http"}]
                      if role == "api" else []) + [
                {"name": "metrics", "port": 9090, "targetPort": "metrics"}],
        })
    obj("batch/v1", "Job", "report-migrate-" + revision[:12], {
        "backoffLimit": 2, "activeDeadlineSeconds": 120,
        "template": {"spec": {
            "restartPolicy": "Never", "serviceAccountName": "report-workshop",
            "automountServiceAccountToken": False,
            "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                                "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": [{"name": "migrate", "image": image, "args": ["migrate"],
                "env": [{"name": "DATABASE_URL", "valueFrom": {"secretKeyRef": {
                    "name": "report-database", "key": "uri"}}}],
                "resources": {"requests": {"cpu": "100m", "memory": "128Mi"},
                              "limits": {"cpu": "500m", "memory": "256Mi"}},
                "securityContext": {"allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}},
            }],
        }},
    })
    return {"apiVersion": "v1", "kind": "List", "items": items}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--namespace", default="report-dev")
    args = parser.parse_args()
    try:
        result = render(image=args.image, revision=args.revision, namespace=args.namespace)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
