"""Exercise the running API/worker pair using only synthetic data."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

BASE = "http://127.0.0.1:18080"


def request(path, body=None, key=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    with urlopen(Request(BASE + path, data=data, headers=headers), timeout=5) as response:
        return response.status, json.load(response)


for attempt in range(60):
    try:
        request("/readyz")
        break
    except (URLError, TimeoutError):
        time.sleep(1)
else:
    raise SystemExit("API did not become ready")

key = "smoke-" + uuid.uuid4().hex
payload = {"fixture": "tiny-v1", "algorithm": "tokens-v1"}
status, job = request("/v1/jobs", payload, key)
assert status == 202, status
_, duplicate = request("/v1/jobs", payload, key)
assert duplicate["id"] == job["id"], "duplicate submission created a second job"
try:
    request("/v1/jobs", {**payload, "fixture": "batch-v1"}, key)
except HTTPError as error:
    assert error.code == 409, error.code
else:
    raise AssertionError("conflicting request was accepted")

for attempt in range(60):
    _, result = request("/v1/jobs/" + job["id"])
    if result["state"] == "succeeded":
        break
    assert result["state"] != "failed", result
    time.sleep(0.5)
else:
    raise SystemExit("Worker did not complete the job")

_, report = request("/v1/jobs/" + job["id"] + "/report")
assert report["documents"] == 3, report
assert report["tokens"] == 11, report
assert report["unique_tokens"] == 6, report
assert report["duplicate_documents"] == 1, report
assert len(report["input_sha256"]) == 64, report
print(json.dumps({"verification": "local-compose", "result": "passed", "report": report}))
