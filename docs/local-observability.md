# Local metrics and baseline observations

This slice adds metrics and an explicit evidence gate. It is **not** the completed
OTel/Loki/Tempo/Pyroscope stack, a load benchmark, or the final public bundle format.

## Run

From a clean checkout of the revision you intend to measure:

```sh
cd workload
export APP_REVISION="$(git rev-parse HEAD)"
docker compose --profile observability up --build -d
python3 smoke.py
python3 -m pip install jsonschema==4.23.0
python3 evidence/record.py --revision "$APP_REVISION" --output output/baseline.json
python3 evidence/validate.py output/baseline.json
docker compose --profile observability down
```

Use a Python virtual environment if your OS manages its Python installation.
The recorder refuses to overwrite an existing result. Archive it or choose a new
output filename on each run. It checks both running processes' build-info revision
against the supplied SHA. That detects mismatched builds, not dishonest build
arguments or dirty working trees; signatures/provenance remain future work.

All exposed listeners bind only to localhost:

| Port | Purpose |
| --- | --- |
| 18080 | Application HTTP |
| 19090 | API metrics |
| 19091 | Worker metrics |
| 19092 | Prometheus UI and query API |

Prometheus uses a two-second scrape interval, a memory-backed data directory,
one-hour retention, and bounded CPU/memory. History is intentionally disposable;
export before stopping. No host Docker socket, credentials or public ingress are
mounted. Metrics listeners are disabled outside Compose unless METRICS_ADDR is set.

## Metric semantics

- HTTP count: bounded route template, GET/HEAD/POST/OTHER method, numeric status.
  Unknown paths use `unmatched`; job IDs and raw URLs never become labels.
- HTTP histogram: handler duration in seconds, including database work.
- Worker iterations: completed/idle/error; a polling error is not necessarily a
  terminal job failure.
- Successful worker duration: dispatch + claim + computation + completion commit,
  not pure algorithm time or accepted-to-completed latency.
- Completed/retried-completed counters: process-local committed completions and
  completions with attempt token greater than one. Restart resets counters.
- Build info: one role/revision series per process. Go/process collectors provide
  runtime/CPU/memory signals.

The [official Prometheus Go guide](https://prometheus.io/docs/guides/go-application/)
informed registry/handler usage; client_golang v1.24.1 and Prometheus v3.15.0 are
pinned. Prometheus image inputs are digest-pinned. No upstream example code was
copied.

## Evidence boundary and missing data

`local-baseline-v1` records a small sequential synthetic workload, source revision,
timestamps, golden fixture hash, raw accepted-to-completed durations from database
timestamps, counts, and telemetry availability. It does not measure saturation,
compare clouds, calculate an SLO, assert teardown, or claim distributed tracing.
The recorder exports an allowlisted record, never raw logs/metrics/error text.

Schema validation rejects unknown fields and cloud/teardown claims. Semantic
validation rejects passing records with missing metrics, partial completion,
incorrect counts, unmatched reports or backwards timestamps. A recording failure
still emits a failed record and returns a nonzero exit status.

CI also stops Prometheus, completes one further job, and asserts that the workload
passes while evidence fails. This exercises the local collector-availability gate,
not all of EXP-06 (export drops, trace sampling and stale retained data remain).

Uploaded CI artifacts expire after 30 days and are not the durable publication
channel for Labs. Immutable signed bundles, image digests, dependency/config
provenance, regression/recovery comparisons and website ingestion remain pending.

## Cloud access reminder

Before any cloud activation, prompt Miles for the approved account/project,
region, budget, maximum run lifetime and scoped access setup. Prefer federated
short-lived access; do not request pasted access keys or service-account JSON.
No part of this local profile needs GCP or AWS credentials.
