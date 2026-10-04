"""Validate actual local HTTP responses against the application contract."""

import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

from jsonschema import Draft202012Validator, FormatChecker


def request(path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    data = None if body is None else json.dumps(body).encode()
    try:
        with urlopen(Request("http://127.0.0.1:18080" + path, data=data,
                             headers=headers), timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


status, deployed = request("/openapi.json")
source = json.loads(Path("internal/httpapi/openapi.json").read_text())
assert status == 200 and deployed == source, "deployed API specification differs"


def check(value, name):
    schema = {"$ref": "#/components/schemas/" + name,
              "components": source["components"]}
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


for path in ("/healthz", "/readyz"):
    status, health = request(path)
    assert status == 200
    check(health, "Health")
status, missing = request("/v1/jobs/" + "f" * 32)
assert status == 404
check(missing, "Error")
key = "contract-" + uuid.uuid4().hex
body = {"fixture": "tiny-v1", "algorithm": "tokens-v1"}
check(body, "Submission")
status, job = request("/v1/jobs", body, key)
assert status == 202
check(job, "Job")
status, conflict = request("/v1/jobs", {**body, "fixture": "batch-v1"}, key)
assert status == 409
check(conflict, "Error")
for _ in range(100):
    status, state = request("/v1/jobs/" + job["id"])
    assert status == 200
    check(state, "Job")
    if state["state"] == "succeeded":
        break
    time.sleep(0.1)
else:
    raise AssertionError("contract job did not complete")
status, report = request("/v1/jobs/" + job["id"] + "/report")
assert status == 200
check(report, "Report")
print("Live health, submission, job, report and error responses match OpenAPI schemas.")
