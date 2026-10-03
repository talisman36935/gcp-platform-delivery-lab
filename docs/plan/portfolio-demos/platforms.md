# Platform architecture and operating contracts

Status: implementation plan, 2026-10-02. Parent: [strategy](../portfolio-demo-strategy-2026-10-02.md).

## Shared delivery contract

Cloud repos own infrastructure, environment configuration and experiment execution.
The application repo owns application releases and provider-neutral contracts.
The portfolio owns presentation. Record app commit, config commit, infrastructure
revision and image digest separately; they need not be the same Git revision.

Default workflow: proposed change -> static checks -> review -> desired-state merge
-> relevant apply/reconciliation -> observed readiness -> workload assertion.
An exit code from a deployment command is insufficient for readiness. Bootstrap,
emergency intervention and final cleanup have explicit ownership exceptions.

CI for ordinary/fork pull requests has no cloud credentials. Privileged lifecycle
workflows run reviewed revisions under separate identities and serialized per-environment
locks. Canceling an experiment must not cancel its cleanup owner. Cloud tests are
bounded run workflows; they do not execute on every documentation change.

## Ownership matrix

| Resource | GCP owner | AWS owner |
| --- | --- | --- |
| Initial account/project trust and CI identity | Bootstrap Terraform state | Explicit bootstrap stack/script, pinned and recorded |
| VPC, cluster, node lifecycle | Environment Terraform state | CAPA, using a documented network ownership mode |
| Queue and result bucket | Terraform | ACK SQS/S3 controllers |
| Application IAM | Terraform | Explicit bootstrap IAM initially; optional ACK IAM exercise later |
| GitOps installation and initial trust | Terraform/fleet bootstrap | Bootstrap procedure, followed by documented Flux ownership |
| Kubernetes platform resources | Config Sync RootSync | Management/workload Flux as scoped |
| App objects and migration Job | Config Sync RepoSync | Workload Flux |
| Cloud Deploy profile app objects | Cloud Deploy exclusively | Not applicable |
| Job/report data | Application | Application |
| Public evidence bundles | Export/publish workflow | Export/publish workflow |

Every resource inventory must record owner, environment/run ID, deletion policy and
whether it is retained/shared. CI should detect overlapping rendered Kubernetes
object identities between owners. Establish equivalent checks for cloud naming
and Terraform/controller overlap. Do not rely on folder names as proof of ownership.

## GCP repository layout

```text
bootstrap/terraform/        state storage and CI federation prerequisites
infrastructure/modules/     small modules by lifecycle/security boundary
infrastructure/envs/lab/    temporary GKE and app cloud resources
gitops/platform/            root configuration, RBAC, quotas, telemetry
gitops/apps/report/         app base references and dev/staging overlays
profiles/cloud-deploy/      separate Cloud Deploy delivery experiment
telemetry/                  provisioned dashboards/rules/export configuration
experiments/                scenarios and expected observations
scripts/                    preflight, orchestration and verification
evidence/                   schemas/references; no raw secrets or state
docs/                       runbooks, ADRs and case studies
```

### Terraform boundary

Keep state backend/federation bootstrap independently recoverable from lab teardown.
Use remote state with supported locking and restricted access; plan output and state
can contain sensitive values and do not belong in public evidence. Pin providers and
module versions. Save plans against an exact commit and reject stale plans after
configuration/state changes. Record changes and observe provider state after apply.

Enable necessary APIs, provision GKE/fleet membership, Artifact Registry, queue,
storage and IAM, then configure supported Config Sync installation/bootstrap.
Choose GKE Standard versus Autopilot in an ADR after validating controller, profiling,
resource-limit and cost requirements. Do not assert that the lowest apparent node
price determines the cheapest complete run.

Start with one project/cluster and dev/staging namespaces. Separate workload service
accounts and quotas; clearly label shared nodes, database and control-plane failure
domains. Advanced isolation requires separate projects/clusters and a new evidence run.

### Config Sync and ACM demonstration

Demonstrate centralized platform policy/configuration with delegated application
configuration: RootSync owns namespaces, delegated RBAC, quota, network policy and
RepoSync declarations; RepoSync owns application resources inside its namespace.
Initial fleet-managed RootSync fields remain Terraform/API-owned. Test that a namespace
reconciler cannot modify unrelated namespaces or cluster-scoped objects.

Use native Pod Security Admission for the minimal baseline. A Policy Controller
experiment adds an explicit policy use case and a denied/allowed deployment pair.
This extends the ACM story without confusing policy enforcement with synchronization.
Record policy engine/version, selected constraint and the actual admission result.

Prove desired-state delivery, drift remediation and an invalid-config failure.
Drift prevention is a separate scenario: test rejection, not correction, when it is
enabled. Collect reconciler source revision, error conditions and readiness timestamps.

### Promotion and Cloud Deploy

CI builds the shared application once. Promotion changes only its approved digest
and environment-specific configuration through Git. First apply to dev, run assertions,
then propose the same digest for staging. Ordinary rollback reverts Git and observes
Config Sync plus application recovery. Database compatibility is a release prerequisite.

Keep Cloud Deploy as a second profile with separate namespace/resource ownership.
Terraform provisions its pipeline/targets; Cloud Deploy delivers application objects;
Config Sync retains only non-overlapping platform objects. Document that profile's
release IDs, verification jobs, approvals and rollback semantics. Switching profiles
is an ownership migration and must not accidentally prune live application resources.
Use a fresh dedicated namespace for the first comparison.

## AWS repository layout

```text
bootstrap/                  identity prerequisites and kind/Flux entry point
management/controllers/     CAPI/CAPA/ACK installation, CRDs, identities
management/clusters/        temporary EKS desired state
management/resources/       S3/SQS CRs and readiness/config handoff
workload/platform/          workload Flux, namespaces, telemetry and policy
workload/apps/              report app and environment overlays
profiles/pivot/             additional EKS management-cluster experiment
lifecycle/                  state machine, inventory, teardown and janitor
experiments/                reconciliation/runtime/deletion scenarios
docs/                       operating contracts and KROPS attribution
```

### Compatibility spike before broad implementation

Pin and record the KROPS reference commit. Inspect actual source for controller
placement, bootstrap ownership and cleanup dependencies; upstream main is not a
version contract. Validate CAPI/CAPA/Kubernetes versions, selected ACK SQS/S3 APIs,
Flux readiness expressions and supported cloud authentication paths.

Produce the smallest real vertical slice: kind -> controller ready -> EKS ready ->
one ACK resource ready -> workload identity/resource access -> complete deletion.
Separate local render/mock results from actual AWS results. Keep a compatibility
table with versions, test date, outcome and blocking issue.

### Bootstrap and credential lifetime

Bootstrap account identity/trust, create kind, install initial controllers and
establish the Git source. Flux then owns the declared management configuration.
The runner retains management access until export and teardown finish.

CI exchanges OIDC for a short-lived session. Controllers running in kind need a
separate explicit usable credential path; passing one expiring session and hoping
it lasts is inadequate. Initial design may inject a scoped session for a run whose
maximum duration is shorter than credential validity, with verified refresh before
cleanup. A refreshable federation path is preferable when supported. Test expiration
during a failed experiment and ensure the janitor has independent credentials.

EKS workloads receive narrowly scoped identity to use their queue and bucket.
Bootstrap IAM owns those roles initially; do not introduce broad ACK IAM permissions
merely to remove a bootstrap step. Revisit ACK IAM only as a separately measured
controller-governance experiment.

### Reconciliation dependencies and outputs

Flux delivers CRDs/controllers before custom resources, cluster definitions before
workload add-ons, and resource configuration before application readiness checks.
Rendered manifest validity is not external-resource readiness. Observe the selected
controllers' actual conditions and external identifiers.

Prefer predeclared deterministic run-scoped bucket/queue names. Where providers
assign outputs, use a documented status-to-configuration handoff or supported ACK
binding feature verified in the spike. Never manually copy console values into
Git. Keep credentials out of that handoff. Record generated configuration digest
and provenance so it can be related to the source commit.

Ensure workload Flux receives its correct repository path and identity. Use
read-only access for reconciliation; a separate promotion identity writes Git.
Cluster bootstrap may seed Flux once, but repeating it must not create competing
owners or silently reset desired state.

### Run lifecycle

```text
preflight -> bootstrap -> infrastructure-ready -> workload-ready
          -> baseline -> experiment -> recovery -> evidence-export
          -> teardown -> independent-audit -> publication
```

Every stage records start/end, inputs, timeout, output evidence and failure reason.
On failure, preserve diagnostic evidence and enter cleanup. Publication can produce
a failed-run record; only a fully qualified run receives verified status. Keep a
recoverable run inventory outside the disposable management cluster.

Preflight verifies target account/region, caller identity, resource ownership tags,
quotas, permissions, version pins, time budget and remaining credential lifetime.
Serialize runs initially to simplify ownership and cost attribution.

### Teardown and failure recovery

1. Stop the load generator and block new jobs; drain or mark remaining work.
2. Export telemetry, controller conditions, inventories and application results.
3. Commit/remove or suspend the relevant Git desired state so Flux cannot recreate
   resources during teardown; record the cleanup revision and suspension scope.
4. Remove application consumers and run-scoped stored data under the declared
   retention policy; allow controllers to delete app cloud resources.
5. Delete workload-cluster resources while CAPA and management access still work.
6. Observe external deletion; remove temporary management resources last.
7. Independently query AWS and reconcile findings with the pre-run inventory.

Audit scoped EKS/node compute, load balancers, NAT gateways, volumes/snapshots,
network interfaces/IP allocations, storage and queue resources, and retained logs
or images according to the run's declared resource types. Some resources are
discovered through API relationships because tags are not universal. Report audit
coverage, permissions and eventual-consistency wait window; absence of matches
with insufficient permissions is inconclusive.

Do not automatically strip finalizers to make deletion appear complete. Diagnose
missing permissions/dependencies and repair the controller path first. If management
is lost, use the external inventory and scoped emergency deletion runbook, then
repeat the provider-side audit. Never use account-wide unscoped cleanup.

An independently operated janitor discovers only declared lab-owned expired runs,
checks active run leases, and applies a documented cleanup policy. Budget alerts
are an additional signal, not a hard spending stop. Cost records distinguish shared
baseline, per-run estimate and delayed billed actuals.

### Pivot experiment

Add a temporary EKS management cluster only in the pivot profile. Freeze conflicting
reconciliation during ownership transfer, preserve credentials/secrets deliberately,
verify CAPI ownership objects and controller health at the destination, then retire
kind. Prove a subsequent Git change reconciles through the new management plane.
Document interrupted-pivot recovery and the reverse teardown dependency graph.

## First cloud acceptance

GCP: fresh Terraform apply, actual Config Sync source reconciliation, delegated
permission negative test, successful processing, promotion of an identical digest,
drift correction, Git rollback, telemetry export and scoped teardown.

AWS: fresh bounded lifecycle, observable controller/resource readiness, successful
processing, one controlled reconciliation failure/recovery, evidence export and
independent clean teardown. The first implementation must finish this complete
slice before multiplying environments or adding optional controllers.
