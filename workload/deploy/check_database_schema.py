"""Qualify the database render against a pinned served CloudNativePG CRD."""

import hashlib
from urllib.request import urlopen

from jsonschema import Draft4Validator
import yaml

from render_database import render

URL = "https://github.com/cloudnative-pg/cloudnative-pg/releases/download/v1.30.1/cnpg-1.30.1.yaml"
SHA256 = "37237f145d8138256ea25ae830f87759255665ff08f8d552fdd8224a5ec032fb"
with urlopen(URL, timeout=30) as response:
    data = response.read()
if hashlib.sha256(data).hexdigest() != SHA256:
    raise SystemExit("CloudNativePG artifact checksum mismatch")
schema = None
for document in yaml.safe_load_all(data):
    if (document and document.get("kind") == "CustomResourceDefinition"
            and document["spec"]["names"]["kind"] == "Cluster"):
        for version in document["spec"]["versions"]:
            if version["name"] == "v1" and version["served"]:
                schema = version["schema"]["openAPIV3Schema"]
if schema is None:
    raise SystemExit("Pinned served database schema missing")
Draft4Validator(schema).validate(render(
    image="ghcr.io/cloudnative-pg/postgresql:18.4@sha256:" + "a" * 64,
    storage_class="lab-db"))
print("Three-instance database render matches CloudNativePG v1.30.1 served CRD.")
print("No admission/CEL, image existence, storage or runtime failover qualification.")
