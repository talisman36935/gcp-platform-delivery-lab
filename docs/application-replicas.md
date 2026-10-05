# Application replicas and crash recovery

The application uses shared durable idempotency/outbox state and fenced worker
leases rather than process-local coordination. Replica correctness and database
availability are separate contracts.

## Local process experiment

Hosted CI starts a second API process, submits one synthetic job through both APIs
with the same key, and requires a single job ID. It gates completion at a database
advisory lock, observes the first worker's durable running claim, then sends an
actual SIGKILL and checks exit code 137. No production fault switch is introduced.
The test also stops the original API and submits through the survivor.

A second worker recovers the accepted job after the real 30-second lease expires;
the test does not shorten or manually expire the lease. It requires attempt two,
the golden report, and history with incomplete attempt one/completed attempt two.
Finally it removes the test trigger/session, removes replica containers and
restores the baseline processes. Failures retain allowlisted observations and
cause CI failure. Always-run Compose cleanup includes both replica services.

Run only against this lab's disposable synthetic Compose database:

```sh
cd workload
# Start the baseline tracing profile as documented first; use built source SHA.
python3 evidence/replica_recovery.py --revision SOURCE_COMMIT_SHA
python3 evidence/validate_replica_recovery.py output/replica-recovery.json
```

The observation explicitly rejects database/cloud HA claims. This is a local
single-database process continuity test, not Kubernetes scheduling, AZ failure,
queue redelivery or PostgreSQL primary failover qualification.

## Dormant Kubernetes profile

The independent renderer produces namespaced ServiceAccount, API/worker Deployments,
ClusterIP services, PDBs and a revision-named migration Job. It is not connected to
the active RepoSync/Flux source and cannot deploy merely because CI renders it.

```sh
python3 workload/deploy/render_ha.py \
  --image REGISTRY/IMAGE@sha256:MANIFEST_DIGEST \
  --revision SOURCE_COMMIT_SHA --namespace report-dev
```

Mutable image tags, branch names and unrelated namespaces are rejected. Each role
has three replicas, hard same-role host anti-affinity, zone spread and a PDB with
two available replicas. Rolling updates use zero surge and one unavailable replica.
Runtime limits, read-only/non-root security and explicit probes are included.
Worker readiness checks its listener, not cloud queue/database processing health.
PDBs constrain voluntary evictions, not arbitrary machine or zone loss.

The platform owner must create the namespace and an externally managed
report-database Secret with a URI key. No credentials are emitted by the renderer.
Database credentials, HA database/storage, network-policy egress, workload cloud
identity and telemetry endpoints must be qualified before activation. Await the
migration Job before workload assertions; incompatible migrations block delivery.
Do not copy this renderer into the current source without expanding the bounded
namespace Role, quotas and policies under their existing owners.

Hard anti-affinity intentionally leaves a replacement pending after a worker loss:
two replicas should continue serving, rather than falsely claim three fault domains
on two nodes. Verify surviving-node capacity, placement and behavior in a live run.
No instance count or static manifest establishes end-to-end HA.
