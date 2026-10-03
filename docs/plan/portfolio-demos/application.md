# Shared application specification

Status: implementation plan, 2026-10-02. Parent: [strategy](../portfolio-demo-strategy-2026-10-02.md).

## Product and scope

Working name: **Report Workshop**. The name is provisional; the domain is a small
document analysis service with asynchronous report generation. A visitor/operator
selects a seeded synthetic dataset, submits a batch, sees progress and retrieves
a report containing document counts, token statistics, duplicate counts and a
deterministic summary. No language model or external content API is required.

The product makes slow processing, retries and recovery visible without requiring
knowledge of Kubernetes. Platform documentation explains the infrastructure behind
that experience. Portfolio Labs primarily presents recorded runs; a public live
submission endpoint is outside the initial scope.

First release:

- Go API with a small server-rendered interface and JSON endpoints.
- Go worker process containing independent dispatcher and consumer loops.
- PostgreSQL job state and transactional outbox.
- One deterministic text analysis algorithm and bounded synthetic fixture batches.
- Local queue/object adapters plus GCP and AWS adapters.
- Metrics, traces, structured logs and continuous profiles from the first slice.

Deferred: user accounts, billing, arbitrary uploads, OCR/PDF parsing, AI summaries,
document search, collaborative editing, multiple business microservices and a
general developer portal. Each would add product work without being needed for
the first platform experiments.

## User journey and interfaces

1. Choose a named fixture and processing profile.
2. Submit with an idempotency key; receive a job identifier and status URL.
3. Observe pending/running/retrying/succeeded/failed state.
4. Open the report or a useful bounded failure explanation.
5. Inspect the technical run separately through the operator evidence workflow.

Proposed API, captured in OpenAPI before cloud deployment:

| Endpoint | Behavior |
| --- | --- |
| `POST /v1/jobs` | Accept allowlisted fixture ID and algorithm version; require idempotency key; return 202 and Location |
| `GET /v1/jobs/{id}` | Return public job state, progress and report availability |
| `GET /v1/jobs/{id}/report` | Stream completed bounded report; return a documented not-ready/error response otherwise |
| `GET /healthz` | Process liveness without cloud dependency checks |
| `GET /readyz` | Bounded check of initialization and dependencies required to accept work |
| `GET /metrics` | Internal metrics endpoint, excluded from public ingress |

Use request/body/time limits, structured error codes and context cancellation.
Unknown fixtures and invalid algorithm versions fail before job creation. A repeat
idempotency key with the same normalized request returns the existing job; the same
key with a different request returns 409. Missing, malformed and oversize requests
have explicit tests. Returning 202 means durably accepted, not completed.

Dependency outages should not trigger restart storms. A queue outage can leave the
API able to accept durable outbox work until a configured backlog limit is reached.
Document the acceptance/readiness policy separately from worker ability to finish.
Report retrieval authorization becomes mandatory before any non-synthetic public
deployment; opaque identifiers alone are not access control.

## Clean architecture

```text
HTTP/UI adapter -> application use cases -> domain
                         |
                  narrow interfaces
                         |
       PostgreSQL | queue adapters | object adapters

queue adapter -> processing use case -> pure analysis functions
```

Domain owns job transitions, analysis rules and error categories. Application owns
submit, dispatch, process, complete and recover use cases. Adapters implement
database transactions, Pub/Sub/SQS delivery and GCS/S3 storage. Entrypoints own
configuration, dependency injection, process lifetime and graceful shutdown.
Cloud SDK imports must stay out of domain packages.

Proposed source layout:

```text
cmd/api/                 HTTP server and composition root
cmd/worker/              dispatcher, consumer and recovery loops
cmd/labctl/              bounded fixture/load/evidence helper
internal/domain/         state transitions and pure report computation
internal/application/    orchestration and port definitions
internal/adapters/       postgres, local, gcp, aws, http and telemetry
internal/config/         validated typed configuration
api/openapi.yaml         public API contract
migrations/              versioned SQL migrations
fixtures/                seeded inputs and expected report hashes
deploy/                  portable Kubernetes base and local Compose
experiments/             provider-neutral load/scenario definitions
schemas/                 queue envelopes and evidence contracts
docs/                    decisions, operation and developer instructions
```

Prefer explicit small interfaces over a general cloud abstraction framework. Queue
ports expose delivery receipt/acknowledgement and lease extension capabilities;
adapters document differing provider limits and failure behavior.

## Data and state model

Proposed tables:

| Table | Purpose and invariants |
| --- | --- |
| `jobs` | Unique ID and scoped idempotency key; request hash, fixture hash, algorithm version, state, timestamps, selected result key/hash and processing lease |
| `outbox` | Transactionally created work intent; publication attempts, next retry, published timestamp and versioned event payload |
| `attempts` | Attempt ordinal, worker revision, fencing token, start/end, bounded error category and trace reference |

Job transition path: pending -> running -> succeeded. Transient failures release or
expire the processing lease and allow another attempt; the UI derives retrying
from pending state plus attempt history. Permanent input errors or exhausted
attempts produce failed. Terminal transitions require conditional writes. Queue
delivery alone never decides whether a job may enter a terminal state.

Store fixture version and analysis algorithm version in the job so a later worker
cannot silently process it with incompatible behavior. Store worker image/revision
on each attempt. Keep test fixtures compatible across baseline/regression/recovery.

Initial limits, to calibrate locally: 1 MiB fixture batch, 100 documents per job,
four worker jobs concurrently, five processing attempts and a bounded backlog.
Configuration changes are versioned with experiments. These are design defaults,
not measured capacity claims.

## At-least-once processing and crash windows

Submission inserts job and outbox intent in one database transaction. Dispatcher
claims outbox rows using short leases, publishes outside the transaction and marks
publication afterward. A crash after publication causes duplicate delivery; the
consumer must tolerate it. Do not promise exactly-once message delivery.

Consumer conditionally claims a job with a lease and monotonically increasing
fencing token. It records an attempt, processes the fixture, stores an immutable
attempt-specific report object, then conditionally commits the result reference
using the current fencing token. A stale worker cannot overwrite completion.
Only acknowledge delivery after durable completion or deliberate terminal handling.

| Crash/failure point | Required recovery |
| --- | --- |
| Job transaction fails | No accepted job or publishable outbox row |
| Commit succeeds, publish fails | Dispatcher retries durable outbox row |
| Publish succeeds, marking published fails | Duplicate message; existing job/lease controls processing |
| Consumer dies during computation | Lease expiry/redelivery permits a new fenced attempt |
| Object write succeeds, DB completion fails | Retry/recover; orphan object remains attributable and is swept after a grace period |
| DB completion succeeds, acknowledgement fails | Redelivery recognizes terminal job and acknowledges without recomputing |
| Old worker returns after lease loss | Conditional completion rejected; orphan result cannot become selected report |
| Poison message or invalid envelope | Bounded handling and explicit dead-letter/quarantine outcome |

Use exponential backoff with jitter and bounded attempts. Classify rate limits,
temporary dependency errors and permanent request errors. Include schema version,
job ID and propagated trace context in messages; do not put document content or
credentials in telemetry. Independent recovery periodically checks expired leases
and unpublished outbox rows. Resource sweeps must retain objects referenced by
successful jobs and select only lab-owned orphan candidates.

## Adapter contracts

Local development uses PostgreSQL plus a durable local queue adapter and filesystem
object store with a named data directory. An in-memory adapter is allowed only in
unit tests. Local queue tests must exercise redelivery/expiry; they cannot establish
SQS or Pub/Sub compatibility. Provider integration suites use disposable resources
to verify API permissions, envelope limits, lease behavior and deletion semantics.

GCP: Pub/Sub topic/subscription, GCS bucket, workload identity. AWS: SQS queue and
dead-letter configuration, S3 bucket, dedicated workload identity. Use explicit
resource names supplied by configuration. The application never provisions them.
Validate selected controller resources and permissions during the platform spike.

Start with in-cluster PostgreSQL and persistent volumes in temporary environments.
A single database instance is an explicit availability limitation. Record schema
version and migration revision in evidence. A migration Job has one owner and
blocks incompatible application startup. Baseline migrations use expand/contract
compatibility so application Git rollback does not require destructive down-migration.

## Release and comparison

Recommend a shared repository provisionally named `observable-report-workload`.
Both platform repos consume its released image and portable deployment base pinned
to immutable revisions. Do not create separate copies of application source.

Build one multi-command image or two images from the same commit; choose the simpler
single-image/two-command option initially. Publish checksums, SBOM and provenance.
Replicate to Artifact Registry/ECR if required and verify digest preservation; if
manifest conversion changes a digest, record both identities and their relationship.
For direct cross-cloud comparison use the same CPU architecture and platform image
digest, not merely the same multi-architecture tag.

The regressed revision changes a real computation path (for example repeated
tokenization instead of one pass) while preserving report output. Keep the regression
as an immutable documented experiment release; normal main remains the healthy
implementation. Avoid sleep-only profiling demonstrations. A separate injected
dependency delay can demonstrate traces and must be labeled as such.

## Verification and first acceptance

Unit tests cover pure analysis and legal state transitions. Integration tests use
real PostgreSQL, concurrency and fault injection to verify the crash-window table.
Adapter contract tests share behavioral expectations while keeping provider-specific
assertions visible. Run Go race tests for worker coordination and graceful shutdown.

First acceptance requires a fresh local start, successful report retrieval, matching
golden output, duplicate submission and redelivery checks, a worker crash/recovery,
and a two-revision profile/trace comparison. All run without cloud credentials.
Document startup resource needs and measured run duration after execution.
