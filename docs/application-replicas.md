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

The independent renderer produces separate namespaced `report-api`,
`report-worker` and `report-migrate` ServiceAccounts, API/worker Deployments,
ClusterIP services, PDBs and a revision-named migration Job. Service-account token
automount is disabled by default; provider identity is attached only to the worker
in an opt-in backend profile. It is not connected to
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

The platform owner must create the namespace and qualify the database operator.
The companion database profile lets CloudNativePG generate the report-db-app
Secret with a URI key for its non-superuser application owner. The app references
that secret; neither renderer emits credentials or duplicates secret ownership.
Database credentials, HA database/storage, network-policy egress, workload cloud
identity and telemetry endpoints must be qualified before activation. Await the
migration Job before workload assertions; incompatible migrations block delivery.
Do not copy this renderer into the current source without expanding the bounded
namespace Role, quotas and policies under their existing owners.

Hard anti-affinity intentionally leaves a replacement pending after a worker loss:
two replicas should continue serving, rather than falsely claim three fault domains
on two nodes. Verify surviving-node capacity, placement and behavior in a live run.
No instance count or static manifest establishes end-to-end HA.

## Database durability profile

The dormant database renderer targets CloudNativePG v1.30.1: three PostgreSQL 18
instances, required cross-zone anti-affinity, 10 GiB per instance and bounded
CPU/memory. It requests quorum synchronous replication to one standby with required
durability and failover quorum enabled. Loss of sufficient standbys should block
writes rather than silently relax durability. This is a requested policy, not a
measured zero-data-loss guarantee.

```sh
python3 workload/deploy/render_database.py \
  --image ghcr.io/cloudnative-pg/postgresql:18.MINOR@sha256:MANIFEST_DIGEST \
  --storage-class QUALIFIED_STORAGE_CLASS --namespace report-dev
```

An actual compatible image digest and CSI storage class must be qualified separately
for each cloud/architecture. CI uses a synthetic digest for schema checks, not a
published image assertion. The operator/CRD artifact is checksum-pinned for the
served-schema check; signature trust, CEL/webhook admission and runtime behavior
remain separate gates. No operator is installed by these renderers.

The separate [hosted image/HA qualification](image-and-ha-qualification.md) now
installs the pinned operator and an actual dual-architecture PostgreSQL image.
It passed primary promotion, primary-worker loss with outstanding jobs, golden
report preservation and cluster cleanup. This uses local-path storage and three
simulated zones on one runner; cloud CSI/admission/network/zone qualification
remains outstanding. The Compose baseline still uses a single PostgreSQL instance.

Activation order: platform CRDs/operator and storage policy, database readiness and
secret generation, migration completion, app rollout, then workload assertions.
Qualify operator replication/control-plane egress and app database/DNS/telemetry
policies without broadening the existing default-deny by accident. Record primary
identity, replication state, acknowledged job IDs, failover latency and any lost
accepted jobs during primary/zone failure. Audit all three volumes and any snapshots
during teardown; retain neither credentials nor raw database contents as evidence.
