# GCP Platform Delivery Lab

[![Validate](https://github.com/talisman36935/gcp-platform-delivery-lab/actions/workflows/validate.yaml/badge.svg)](https://github.com/talisman36935/gcp-platform-delivery-lab/actions/workflows/validate.yaml)

A portfolio lab comparing Terraform-managed infrastructure and Config Sync
delivery with the [AWS reconciliation lab](https://github.com/talisman36935/aws-kubernetes-reconciliation-lab).
Both use **Report Workshop**, a small deterministic asynchronous Go application.

**Status: first implementation slice, not a completed cloud demonstration.**
The local application is runnable. Terraform validates without credentials.
The Config Sync source contains a namespace/delegation demonstration, not an
application deployment. No GCP project has been provisioned by this repository.

## Try the application locally

Requirements: Docker with Compose v2+, Python 3.10+, free localhost ports
18080, 19090 and 19091.
The first build downloads public images and Go dependencies.

```sh
git clone https://github.com/talisman36935/gcp-platform-delivery-lab.git
cd gcp-platform-delivery-lab/workload
docker compose up --build -d
python3 smoke.py
docker compose logs --tail=50 api worker
docker compose down
```

The API is bound to **127.0.0.1:18080**. PostgreSQL is not published to the host.
The explicitly synthetic password in Compose is local-only, not a cloud credential.
Keep this unauthenticated demonstration off public ingress.

```sh
curl -sS http://127.0.0.1:18080/v1/jobs \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: demo-001' \
  -d '{"fixture":"tiny-v1","algorithm":"tokens-v1"}'
# Use the returned id:
curl -sS http://127.0.0.1:18080/v1/jobs/JOB_ID
curl -sS http://127.0.0.1:18080/v1/jobs/JOB_ID/report
```

The golden report contains 3 documents, 11 tokens, 6 unique tokens and 1 duplicate
document. Reusing a key with identical input returns the same job; different input
returns 409. Named fixture allowlisting prevents arbitrary files/URLs being processed.

`docker compose down` retains the local database. To intentionally erase this
demo's synthetic job history, run `docker compose down --volumes` from `workload/`.
Do not use this command against another Compose project.

## What is implemented?

| Area | Current implementation | Not yet demonstrated |
| --- | --- | --- |
| Workload | API, PostgreSQL outbox/local queue, worker, fenced attempts, report | Pub/Sub/GCS adapters, object publication recovery |
| Tests | Golden output, HTTP contracts, concurrent idempotency, leases/retries, Compose smoke | Cloud queue contracts, process-kill experiment |
| GCP | Terraform lab foundation plus private-state/federated-CI bootstrap | Actual plan/apply, identity qualification and cloud teardown |
| GitOps | Root platform ownership, restricted namespace delegation, disjoint identity check | Live reconciliation, delegated negative test, promotion/rollback |
| Observability | Structured logs, metrics/Prometheus, optional OTel collector/Tempo and CPU/heap capture | Continuous profiles, log backend and investigation dashboards |
| Portfolio | Strict local baseline records, missing-collector gate, detailed Labs specification | Qualified durable cloud bundles and website ingestion |

## Navigate

- [Minimal London topology, budget gates and immediate teardown](docs/plan/portfolio-demos/minimal-infrastructure.md)

- [Current architecture and decisions](docs/implementation.md)
- [Validation and GCP activation boundary](docs/runbook.md)
- [Private state and federated CI bootstrap](docs/cloud-bootstrap.md)
- [Local metrics, evidence recorder and outage check](docs/local-observability.md)
- [Trace correlation and CPU/heap investigation](docs/local-tracing-profiling.md)
- [Controlled regression and original-image recovery](docs/local-regression-recovery.md)
- [OpenAPI 3.1 contract](workload/internal/httpapi/openapi.json) (served at /openapi.json)
- [Full strategy](docs/plan/portfolio-demo-strategy-2026-10-02.md)
- [Application specification](docs/plan/portfolio-demos/application.md)
- [Platform contracts](docs/plan/portfolio-demos/platforms.md)
- [Evidence and website Labs integration](docs/plan/portfolio-demos/evidence-and-labs.md)
- [Milestones and acceptance](docs/plan/portfolio-demos/delivery-plan.md)
- [Annotated examples and references](docs/plan/portfolio-demos/references.md)

Planning documents preserve the original proposal. Current implementation decisions
in `docs/implementation.md` take precedence when describing what actually exists.
