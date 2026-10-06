# Opt-in workload delivery profiles

The shared delivery renderer splits platform, migration and application identities.
It consumes one immutable release record with explicit `schema-check` and cloud
adapter capabilities; older HA releases are rejected rather than silently using
commands they do not implement. Generated trees are **blocked candidates**, not
cloud deployments. Current Config Sync and Flux roots remain contract-only.

```sh
python3 workload/deploy/render_delivery.py \
  --release output/image-release.json --owner config-sync \
  --storage-class QUALIFIED_CSI_CLASS --output profiles/delivery
# AWS consumes the same renderer from its verified shared-source checkout:
# --owner flux --backend aws --settings NONSECRET_RESOURCE_HANDOFF.json
```

The output directory must not already exist. Review/commit the output and activate
its root source explicitly; this command performs no Kubernetes/cloud operation.
Flux paths deliberately assume `profiles/delivery/` in the destination repository.
Config Sync's RepoSync path uses that same destination. Neither controller follows
an arbitrary temporary render directory.

## Exclusive ownership and readiness

Platform owns namespace, quota, default-deny/DNS/database-egress policies, database
CR, app identity, reconciler Role/RoleBinding and source delegation. Quota reserves
headroom for three DB instances, six application replicas and migration; it is not
a tested cloud capacity guarantee. CNPG operator/CRDs must be separately installed
by the platform owner first, not by an application reconciler.

Application delegation permits only ConfigMaps, Services, Deployments, Jobs and
PDBs inside the one namespace. It does not permit Secrets, ServiceAccounts, RBAC,
PVCs, namespaces or cluster resources. Cloud identity is platform-owned. AWS workers
receive an explicit projected audience-scoped token, scoped role ARN and disabled
EC2 metadata fallback; API/migration pods do not receive cloud credential settings.
GCP identity annotation is checked against the selected project. Trust/IAM remains
external, scoped and unqualified until cloud preflight.

Config Sync gives the app reconciler the migration Job and app objects together;
read-only `schema-check` init containers block app start until the additive Job
migration finishes. Reconciliation order alone is not treated as a migration gate.
Flux emits a root graph with `platform -> migrations -> apps`, `wait: true`, bounded
timeouts and explicit DB ready-instance health expression. Migration/app reconcilers
use the delegated namespace identity; platform reconciliation requires separately
authorized bootstrap ownership. There is no application cluster-admin grant.
The health expression guards `status.readyInstances`, not top-level `has(status)`;
Flux/CEL cannot use that macro on a top-level property. A resource without status
remains unready until the controller writes it, bounded by the reconciliation timeout.
See the [Flux health-check contract](https://fluxcd.io/flux/components/kustomize/kustomizations/#health-check-expressions).

## Fail-closed activation boundaries

The emitted default-deny is intentional. Database peer/control-plane/DNS policies,
provider/CNI-specific API destinations, workload HTTPS/metadata and telemetry egress,
API ingress, actual CSI, controller health and workload identity require a reviewed
provider overlay. The generic profile does **not** substitute allow-all egress or
pretend a local render is runnable in either cloud. IAM and network qualification
must precede the source-root change.

Unit tests prove disjoint identities, immutable release inputs, no legacy capability
fallback, schema init gates, owner/backend matching and limited application RBAC.
Rendered manifests, IAM token projections and Flux readiness expressions are not
live Config Sync/Flux authorization/admission evidence. Existing hosted Flux contract
drift/cleanup remains the only current reconciliation runtime proof. A hosted app
delivery/rollback/negative-permission experiment is the next credential-free gate.

Ordinary rollback reverts the app digest/config; it does not reverse additive DB
migrations. Do not let RootSync and Flux or Cloud Deploy own the same identities.
Before cloud activation, resolve budget hard-cap coverage, alert recipients, maximum
lifetime and retained bootstrap/state policy, and implement independent cleanup.
