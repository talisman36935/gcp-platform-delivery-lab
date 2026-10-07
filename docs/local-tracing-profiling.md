# Local trace correlation and Go profiles

This profile builds on the local Prometheus setup. It adds OpenTelemetry traces,
one collector distribution, Tempo and bounded CPU/heap capture. Structured API
and worker logs carry the same trace ID. Loki/Pyroscope ingestion and a Grafana
investigation dashboard remain later work.

## Reproduce the investigation

Use a clean checkout, Docker Compose, Go 1.27.1 and Python 3. Extra localhost port
19093 is required. Run from `workload/`:

```sh
export APP_REVISION="$(git rev-parse HEAD)"
export WORKSHOP_RUN_ID="local-$(date -u +%Y%m%dT%H%M%SZ)"
docker compose -f compose.yaml -f compose.tracing.yaml --profile observability up --build -d
python3 smoke.py
python3 evidence/trace_profile.py --revision "$APP_REVISION"
python3 -m pip install jsonschema==4.23.0
python3 evidence/check_trace_profile.py
go tool pprof -top output/worker-cpu.pprof
go tool pprof -top output/worker-heap.pprof
docker compose -f compose.yaml -f compose.tracing.yaml --profile observability logs api worker
docker compose -f compose.yaml -f compose.tracing.yaml --profile observability down
```

The recorder submits a fixture, reads its trace ID from the response, waits for
completion, then queries Tempo at localhost:19093. It requires spans from both
processes and checks that the worker's parent is the persisted submission span.
It next captures five seconds of CPU activity under a bounded batch-fixture load
and one heap profile. CI parses the profiles with Go's tool and requires actual
analysis frames in the CPU sample.

The additional checker validates the observation schema and profile byte lengths/
SHA-256 hashes, then reads Compose logs locally and requires the selected trace ID
in both API and worker records. It exports only service/count correlation metadata;
raw log records stay out of the observation bundle.

Profiles and Tempo/collector data are local development artifacts. The recorder
refuses to overwrite its observation file. Select a fresh output directory/run or
archive the previous result before rerunning. Tempo and collector storage are
memory-backed; stopping them removes their history. Profile files remain under
the ignored output directory until explicitly removed.

## Trace ownership and privacy

Application code uses a small observer port. The telemetry adapter owns SDK,
exporter, resource identity, HTTP instrumentation and repository wrapping.
The optional tracing profile sets `DEPLOYMENT_ENVIRONMENT_NAME=local` and uses
`WORKSHOP_RUN_ID` (with a local fallback for convenience). When an OTLP endpoint
is configured, both values are required and validated before export; the resource
includes `deployment.environment.name` and `workshop.run_id` alongside service
name/version. Cloud profiles must supply an explicit non-local environment and a
unique run ID; local defaults are not valid cloud evidence. When the endpoint is
unset, tracing remains a no-op and does not require these values. The durable record
stores only W3C traceparent; baggage, authorization headers, raw URLs, document
contents and database error text are excluded.

The HTTP span parents a transaction span whose context is stored atomically
with the job/outbox. A worker attempt continues that parent after dispatch,
with analysis and report-commit child spans. Retry attempts are siblings under
the same durable parent and have separate attempt attributes. Trace/job IDs
appear in logs/spans and stay out of metric labels.

An idempotent repeat keeps the original stored parent; it must not overwrite
the initial submission's provenance. Tests verify the durable field, retry
relationships and private-header exclusion.

Local tracing uses parent-based always-on sampling. The collector's memory
limiter and batch processor export to Tempo and a bounded OTLP JSON file.
Exporter availability does not decide application readiness. Backpressure,
dropped-span counters, sampling qualification and cloud queue propagation still
require further experiments. API/job clocks still determine completion latency;
trace gaps alone do not establish queue delay.

## Profiling boundary

CPU/heap routes are registered only when PROFILE_ENABLED=true, on the separate
private telemetry listener. CPU requests require an explicit 1–5 second duration.
The public application router has no profiling routes. The tracing Compose
extension opts the worker in; the ordinary profile leaves it disabled.

CPU sampling is aggregate process evidence. This slice does not implement a
trace-to-profile bridge or continuous Pyroscope ingestion. A single small run
does not establish profiling overhead or a release performance regression.

## Pinned references

- [OTel Go exporters](https://opentelemetry.io/docs/languages/go/exporters/):
  SDK/OTLP HTTP exporter v1.47.0.
- [Collector file exporter v0.161.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.161.0/exporter/fileexporter/README.md):
  locally retained OTLP JSON and bounded rotation; upstream marks it alpha.
- [Tempo local example v2.10.8](https://github.com/grafana/tempo/blob/v2.10.8/example/docker-compose/local/tempo.yaml):
  local storage/OTLP patterns. This lab authors a smaller configuration.
- [Go diagnostics](https://go.dev/doc/diagnostics): sampling profiles and tooling.

Collector v0.161.0 was selected because its official image is available and
digest-resolved; v0.162.0 release metadata existed but its image was unavailable
at inspection. Tempo v2.10.8 keeps this small monolithic profile on the 2.x
configuration model. Both image digests are in the Compose extension.
