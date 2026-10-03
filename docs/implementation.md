# Implementation record — 2026-10-03

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
No backoff/DLQ UI, queue-message context propagation, object reconciler, retention
job or versioned migration framework exists yet. Tests expire leases explicitly;
that proves the fencing contract, not a completed process-kill experiment.

## ADR 003: GCP foundation with explicit activation gate

Terraform owns APIs, network, NAT, GKE, nodes, fleet and Config Sync bootstrap.
The initial GKE Standard configuration uses one zone/node and is not HA. NAT,
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

Next: finish application ports/OpenAPI and artifact contracts; add local metrics,
traces and profiles; capture baseline/regression/recovery; implement cloud
adapters; then qualify a bounded GCP create/run/destroy cycle. The original
M0/M1 milestones are partial; M2–M6 remain outstanding.
