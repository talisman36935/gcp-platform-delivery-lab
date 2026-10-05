"""Validate rendered objects against a checksum-pinned Kubernetes API schema."""

import hashlib
import json
from urllib.request import urlopen

from jsonschema import Draft4Validator

from render_ha import render

URL = "https://raw.githubusercontent.com/kubernetes/kubernetes/v1.35.8/api/openapi-spec/swagger.json"
SHA256 = "483500149ee52ce5753d75f5639101d985bb4f5e902cc05b1ba7627465d62446"
with urlopen(URL, timeout=30) as response:
    data = response.read()
if hashlib.sha256(data).hexdigest() != SHA256:
    raise SystemExit("Kubernetes schema checksum mismatch")
definitions = json.loads(data)["definitions"]


def normalize_int_or_string(value):
    # Kubernetes OpenAPI v2 encodes this union as type:string plus a special
    # format. Ordinary JSON Schema validators need its actual integer union.
    if isinstance(value, dict):
        if value.get("format") == "int-or-string":
            value["type"] = ["integer", "string"]
        for child in value.values():
            normalize_int_or_string(child)
    elif isinstance(value, list):
        for child in value:
            normalize_int_or_string(child)


normalize_int_or_string(definitions)
groups = {"v1": "core.v1", "apps/v1": "apps.v1",
          "batch/v1": "batch.v1", "policy/v1": "policy.v1"}
objects = render(image="ghcr.io/example/report@sha256:" + "a" * 64,
                 revision="b" * 40)["items"]
for obj in objects:
    definition = "io.k8s.api." + groups[obj["apiVersion"]] + "." + obj["kind"]
    Draft4Validator({"$ref": "#/definitions/" + definition,
                     "definitions": definitions}).validate(obj)
print(f"Validated {len(objects)} HA objects against Kubernetes v1.35.8 schemas.")
print("Static schema check only; no admission, scheduling or cloud qualification.")
