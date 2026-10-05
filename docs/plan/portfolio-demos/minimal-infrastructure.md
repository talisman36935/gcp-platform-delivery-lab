# Ephemeral HA architecture and cost policy — 2026-10-05

This supersedes the earlier one-node/minimal-feature proposal. The user wants the
complex architecture, HA and full observability on the cheapest viable machines,
for extremely brief runs. Minimize cost/lifetime, not architectural capabilities.
The existing filename is retained so old links continue to resolve.

## Target topology and evidence

- London: GCP europe-west2 / AWS eu-west-2. One cloud experiment at a time.
- GCP: regional GKE Standard control plane, three workers across three zones,
  Terraform and fleet-managed Config Sync RootSync/delegated RepoSync.
  Explicitly select one node per zone, not the regional nine-node default.
- AWS: EKS multi-AZ control plane, three workers across three AZs, temporary kind
  management with Flux/CAPI/CAPA and ACK S3/SQS. Management remains until cleanup.
- Preserve clean application ports, replicated API/workers, durable PostgreSQL,
  Pub/Sub/GCS or SQS/S3, scoped identities and complete GitOps delivery/recovery.
- Include topology spread/anti-affinity, disruption budgets, probes, controlled
  failover and metrics/logs/traces/profiles/dashboards.
- Database HA requires a qualified replication/failover and storage design with
  measured recovery/data-loss criteria. Multiple nodes/API replicas do not prove
  end-to-end HA; the current single PostgreSQL deployment is not HA.
- Keep networking/NAT, ingress/load balancing and policy components needed to
  substantiate the architecture; cost them rather than remove them by default.
  Avoid gratuitous duplicate clusters. Cloud Deploy and CAPI pivot remain later
  separately owned experiments, not prerequisites for every HA run.
- The portfolio shows both complete design and exact tested deployment, clearly
  separating intended capabilities from observed failover/recovery/cost/cleanup.

## London instance comparison

Snapshot checked 2026-10-05. Linux on-demand USD before tax/credits, excluding
CPU-credit surcharges; no reserved/committed-use purchases for temporary labs.

| Candidate | vCPU / RAM | Node/hour | Three nodes/hour |
| --- | --- | ---: | ---: |
| AWS t4g.small (ARM) | 2 / 2 GiB | $0.0188 | $0.0564 |
| AWS t4g.medium (ARM) | 2 / 4 GiB | $0.0376 | $0.1128 |
| AWS t3a.medium (x86) | 2 / 4 GiB | $0.0425 | $0.1275 |
| AWS t4g.large (ARM) | 2 / 8 GiB | $0.0752 | $0.2256 |
| AWS t3a.large (x86) | 2 / 8 GiB | $0.0850 | $0.2550 |
| GCP e2-medium (shared CPU) | 2 / 4 GiB | $0.04316778 | $0.12950334 |
| GCP e2-standard-2 | 2 / 8 GiB | $0.08633556 | $0.25900668 |

Preferred qualification candidates: three AWS t4g.large after checking all
images/AMIs support ARM, otherwise t3a.large; three GCP e2-standard-2.
These are affordable candidates, not guaranteed capacity or a proven global
cheapest choice. Measure reservations/pod requests and surviving two-node capacity;
test 4 GiB alternatives only if those gates pass. Do not assume 2 GiB is sufficient.

Including the $0.10/hour standard managed control-plane fee gives preferred
node/control-plane subtotals of $0.3256/hour AWS and $0.35900668/hour GCP,
approximately $0.16/$0.18 for 30 minutes at steady topology.
These are NOT complete run estimates: add disks, HA database, NAT/IPs/LBs, transfer,
telemetry, Config Sync feature fees where applicable, queues/storage, registry,
retained bootstrap and provisioning/deletion/surge-node time.

Start on-demand for repeatable qualification. Compare live Spot offers for a
separate interruption profile, not a fixed assumed discount. Burstable AWS CPU
credit charges/throttling need explicit load-test treatment. Recheck pricing and
regional/version availability before apply.

Sources:
- [Official AWS London EC2 price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-west-2/index.csv)
- [GCP VM prices: London selection](https://cloud.google.com/products/compute/pricing/general-purpose)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [GKE pricing and feature fees](https://cloud.google.com/kubernetes-engine/pricing)
- [GKE regional node defaults](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/regional-clusters)
- [AWS T4g CPU-credit pricing](https://aws.amazon.com/ec2/instance-types/t4/)
- [AWS NAT billing: partial hours round up](https://aws.amazon.com/vpc/pricing/)
- [GCP NAT pricing](https://cloud.google.com/nat/pricing)

## Cost safeguards and immediate teardown

Budget alerts are required. Track gross usage before trial credits alongside net
charges; verify actual trial/service eligibility. Alerts are delayed billing
signals, not guaranteed caps. The requested hard-cap protection remains an
activation gate until coverage is verified for every selected billable service.
Resource limits, deadlines and cleanup must not be called a monetary hard cap.

Earlier £2/cloud/run, £0.50/£1/£2 alerts and one-hour lifetime remain unapproved
proposals, not validated HA allowances. Agree complete cost estimate, currency,
recipient and maximum lifetime before activation. Brief workload time does not
mean instant provisioning/deletion; reserve cleanup time within the deadline.
Refuse an over-budget plan rather than silently increase the allowance.

Capture evidence, then immediately delete on success, failure, cancellation or
expiry. Keep external scoped inventory and independent cleanup capability.
Audit compute/clusters, disks/snapshots, NAT/LBs, interfaces/IPs, buckets/object
versions, queues and run-scoped logs/images. Insufficient audit permissions mean
incomplete cleanup evidence. Record eventual deletion and delayed billing separately.

Private state/federation bootstrap currently survives normal lab teardown by design,
but no retention exception is approved. Keep it recoverable through cleanup, then
follow the agreed deletion/retention policy. No silently retained billable resources.
Portfolio evidence is sanitized historical data, not live control/credentials.

## Implementation gap

This is the target, not an implementation claim. GCP Terraform still models the
earlier single-zone/one-node foundation; AWS rendering still models one worker and
an x86 AMI. HA placement, ARM selection, replicated services/database, networking,
failover evidence and spending controls require implementation and qualification.
No cloud resource or billing setting is changed by this documentation update.
