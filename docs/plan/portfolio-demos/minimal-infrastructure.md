# Minimal infrastructure and cost policy — 2026-10-05

This policy supersedes broader default topology suggestions in the original plan.
It records the user's London, ephemeral and minimum-infrastructure requirements.
It is a design/activation gate, not evidence that billing controls are configured.

## First demo topology

- Run one cloud at a time, one experiment at a time; no always-on demo environment.
- GCP: `europe-west2` (London), one single-zone GKE Standard cluster and one
  appropriately sized small node, Config Sync RootSync/RepoSync and Report Workshop.
- AWS: `eu-west-2` (London), temporary local/runner kind management with
  Flux/CAPI/CAPA, one EKS workload cluster and one small worker node.
- Run disposable PostgreSQL and bounded observability in the workload cluster.
  No managed database, separate monitoring cluster, HA replicas or multi-region setup.
  Capacity must fit the app plus controllers/telemetry; do not pick an undersized node
  merely to claim a lower price. Export observations before deleting local storage.
- Prefer ClusterIP services and authenticated port-forwarding. No public demo ingress,
  load balancer, custom domain or dedicated NAT gateway by default.
- Qualify supported networking and Git/image/API egress first. Avoiding NAT is a
  design goal, not permission to weaken isolation or assume a public subnet works.
  Any necessary NAT/load balancer or extra node needs explicit cost/topology review.
- Queue/object resources and ACK controllers are experiment-specific: create only
  those needed to demonstrate Pub/Sub/GCS or SQS/S3 access/reconciliation, then delete.
- Cloud Deploy, Policy Controller, CAPI pivot and additional environments stay optional
  later profiles. Promotion may use namespaces in the same cluster, not extra clusters.

## Budget and activation gates

Budget alerts are explicitly requested. Proposed, **not yet approved**, values are
£2 per cloud per run, alerts at £0.50/£1/£2 and a one-hour maximum lifetime.
Earlier £10 examples are not spending approval. Confirm amount, currency conversion
where billing uses another currency, alert recipient and lifetime before activation.
A one-hour deadline must include provisioning and cleanup reserve, not just workload time.

Estimate the complete London run before creation: control plane, nodes, disks,
IP/networking, telemetry, storage/requests, registry and any bootstrap retention.
Do not assume trial credits make usage free. Verify actual account/trial eligibility;
monitor gross usage before promotional credits as well as net charges.
Refuse an estimated over-budget run and simplify or seek an explicit revised allowance.

Alerts are delayed billing signals, not a universal guaranteed hard cap. The user's
hard-cap requirement remains an unresolved activation gate until provider/trial
spending protection and coverage for every selected billable service are verified.
Resource/count limits, deadlines, independent cleanup and alerts reduce exposure;
they must not be presented as a guaranteed monetary ceiling.

References:
- [AWS Budgets notification delay](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [GCP alerts-only budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [GCP spend-cap coverage to qualify](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)

## Immediate teardown and retention

Finish evidence capture, then immediately remove all run-scoped billable resources.
Failure, cancellation and deadline expiry also enter cleanup; teardown must remain
possible if the runner or temporary management cluster fails. Keep management access
until workload/cloud deletion is independently verified.

Audit cluster/node compute, disks/snapshots, load balancers, NAT, interfaces/IPs,
buckets/object versions, queues and run-scoped logs/images as applicable.
A failed or under-permissioned audit is incomplete, never a clean result.
Record late billing separately; deletion completion does not prove final cost.

Do not silently retain billable resources. Private Terraform state/federation bootstrap
is currently designed to persist for recoverability, but that retention exception
has **not** been approved. Declare its cost and deletion policy before apply; retain
state/identity through cleanup, then follow the agreed retention decision.
Only sanitized historical evidence belongs in the portfolio; no live public cloud
control or credentials.

## Implementation gap

Documentation changes do not modify deployed infrastructure or activate alerts.
The current GCP Terraform still declares private-node NAT; the AWS rendering spike
does not qualify NAT-free networking. Both need implementation/qualification against
this policy before cloud execution. No approved monetary limit, verified hard cap,
configured alerts or cloud deployment is claimed by this document.
