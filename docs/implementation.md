# Implementation record — 2026-10-03

## Continuation — 2026-10-06

The ADRs below preserve the initial implementation state. They are not the current
completion checklist. Cloud adapters now implement Pub/Sub/GCS and SQS/S3 behind
application ports, with leased outbox publication, immutable attempt/hash objects,
fenced reference/JSONB completion and acknowledgement after commit. HTTP still
reads JSONB. Publication and consumption run independently. Actual SDK protocol
doubles and real PostgreSQL tests pass; live cloud services are unqualified.
See [adapter contracts](cloud-adapters.md) and the
[exact-source validation audit](observations/0e0a613/adapter-qualification.md).

Opt-in Config Sync/Flux profiles add disjoint ownership, schema readiness gates
and restricted application RBAC. They deliberately remain blocked pending provider
network/identity qualification; existing GitOps roots have not been switched.
See [delivery boundaries](gitops-delivery.md). Hosted image/HA evidence is recorded
separately in [image qualification](image-and-ha-qualification.md).
Independent teardown/TTL, approved cost protection, live cloud HA, full telemetry
and durable portfolio ingestion remain incomplete. No cloud resources were created.

The companion's hosted Flux experiment now qualifies actual application delivery,
configuration promotion/rollback/drift repair, controller denial and one local
network allow/deny path with twelve phase-local golden jobs and cleanup.
See [delivery verification and cloud boundaries](gitops-delivery.md). It uses
explicit local networking/rollout-health extensions; neither generic cloud root
nor Config Sync runtime is thereby activated or qualified. Binary/schema rollback
and signed durable portfolio evidence remain separate gates.

## ADR 001: two repositories, one application source

The initial build stays within the two requested public repositories. This repo's
`workload/` owns the Go application; AWS will consume the same immutable source
and, later, released image digest. There is no independent AWS application copy.
A separate app repository remains possible if release ownership warrants it.
This supersedes the third-repository recommendation in the original proposal.

## ADR 002: establish durable local semantics before cloud adapters

The domain package performs deterministic fixture analysis with no infrastructure
dependencies. The HTTP adapter validates requests; PostgreSQL owns job state,
idempotency, outbox and local queue. The process entry point wires API or worker.
Application ports depend only on domain types; neither the HTTP adapter nor
worker use case imports PostgreSQL or its driver. Storage translates missing
rows into domain errors. This keeps infrastructure details at the boundary
before adding cloud adapters.

Job submission and outbox insertion share a transaction. The local dispatcher
atomically inserts a durable queue entry and marks its outbox row published.
Workers use row locks with SKIP LOCKED, a 30-second lease and incrementing attempt
tokens. Completion checks token, running state and unexpired lease in one
transaction, so an old worker cannot overwrite a newer result. Five exhausted
attempts become terminal failure. Reports are currently JSONB in the same DB
transaction; they are **not yet objects in GCS/S3**.

Database availability remains a dependency. One worker handles one job at a time.
No backoff/DLQ UI, cloud queue context propagation, object reconciler, retention
job or versioned migration framework exists yet. Tests expire leases explicitly;
that proves the fencing contract. Hosted replica recovery additionally kills a
real worker before completion and verifies takeover after natural lease expiry;
see [application replicas](application-replicas.md). Database failover remains
unqualified.

## ADR 003: GCP foundation with explicit activation gate

Terraform owns APIs, network, NAT, GKE, nodes, fleet and Config Sync bootstrap.
The GKE Standard configuration uses a regional control plane and three London
worker zones with one node per zone. This does not establish workload/database HA. NAT,
GKE, disks and Config Sync may incur charges. An exact Config Sync version and
root source commit must be supplied; provider schema validation is not runtime
compatibility qualification.

RootSync owns the namespace, quota, default-deny network policy, namespace Role/
RoleBinding and RepoSync. The namespace reconciler can manage only ConfigMaps.
RepoSync follows main to demonstrate desired-state changes; record the observed
commit during a real run. It currently owns only the contract ConfigMap.
The root source is pinned through Terraform; changing it requires a reviewed
plan/apply. Do not let a second owner modify fleet-managed RootSync fields.

The default-deny policy deliberately blocks workload traffic until explicit DNS,
database, telemetry and cloud egress rules accompany the actual workload.
Cloud Deploy will use a separate namespace/profile, never these same app objects.

## Evidence and next slice

CI is credential-free. It checks Go formatting/vet/race tests against real
PostgreSQL, builds the image and executes HTTP/worker assertions, validates
Terraform and checks rendered resource ownership. A green run proves only those
checks, not GKE readiness or cloud IAM.

Local metrics and a strict baseline recorder now exist, including a CI check that
collector unavailability fails evidence while the application still completes work.
See [local observability](local-observability.md) for scope and reproduction.

The application now serves an embedded OpenAPI 3.1 contract at /openapi.json.
CI validates actual HTTP responses against its schemas. Optional local tracing
persists W3C traceparent through the durable job path and retries, then verifies
API/worker correlation in Tempo. Bounded CPU/heap capture and matching log IDs
provide the next investigation slice.

Compiled baseline/regressed worker variants now provide a local comparison with
unchanged output, declared thresholds, per-phase profiles and original-image
recovery. The hosted experiment is the qualification gate for that comparison.

Next: finish full artifact contracts, backend log/continuous profile integration
and trace-to-profile correlation; qualify profiling overhead and durable portfolio
evidence ingestion. Then, after account-scoped identity, hard budget controls,
alerts, lifetime and independent teardown are explicitly approved, qualify a
bounded London cloud create/run/destroy cycle. Live Pub/Sub/GCS and SQS/S3 service
behavior, GCP Config Sync runtime, AWS EKS/CAPA/ACK, physical-zone, storage, IAM
and cloud telemetry behavior, budget enforcement and independent teardown remain
unqualified. Local hosted evidence does not remove those activation gates.
