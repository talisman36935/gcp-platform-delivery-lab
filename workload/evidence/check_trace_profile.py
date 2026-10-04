"""Validate actual profile hashes, local trace evidence and safe log correlation."""

import hashlib
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator, FormatChecker

output = Path("output")
observation = json.loads((output / "trace-profile.json").read_text())
schema = json.loads(Path(__file__).with_name("local-trace-profile.schema.json").read_text())
Draft202012Validator(schema, format_checker=FormatChecker()).validate(observation)
if observation["result"] != "passed":
    raise SystemExit("Trace/profile observation failed")
for name in ("worker-cpu.pprof", "worker-heap.pprof"):
    data = (output / name).read_bytes()
    if len(data) != observation[name]["bytes"] or hashlib.sha256(data).hexdigest() != observation[name]["sha256"]:
        raise SystemExit("Profile does not match the recorded hash/length")
logs = subprocess.run(
    ["docker", "compose", "-f", "compose.yaml", "-f", "compose.tracing.yaml",
     "--profile", "observability", "logs", "--no-log-prefix", "--no-color",
     "api", "worker"], check=True, capture_output=True, text=True,
)
matches = {"api": 0, "worker": 0}
for line in logs.stdout.splitlines():
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get("trace_id") == observation["trace_id"] and record.get("service") in matches:
        matches[record["service"]] += 1
if not all(matches.values()):
    raise SystemExit("Selected trace was not correlated with both process logs")
summary = {"verification": "local-compose", "source_revision": observation["source_revision"],
           "trace_id": observation["trace_id"], "matched_log_records": matches}
with (output / "trace-log-correlation.json").open("x") as stream:
    json.dump(summary, stream, indent=2)
    stream.write("\n")
print("Trace/profile hashes valid; selected trace observed in API and worker logs.")
