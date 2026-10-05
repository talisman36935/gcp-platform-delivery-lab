# Image release and hosted HA qualification

The manually dispatched Publish and qualify HA workflow accepts only a reviewed
main SHA with a successful Validate push run. It builds the source into a small
non-root multi-command image for AMD64 and ARM64 using native cross-compilation,
publishes to GHCR, then records the index/platform digests and build attestations.
The sha tag is a convenience; consumers must pin the immutable digest.

The workflow uses short-lived repository-scoped GitHub tokens. Ordinary/fork
validation does not publish packages or receive package-write permission.
Build provenance/SBOM generation is not a verified signature claim.
The ARM job runs migration, API, worker and golden assertions on a native ARM host.

GHCR initially creates a private package. Until the owner changes its visibility
and anonymous pulls are tested, release records explicitly do not claim public
pull access. Hosted qualification uses a temporary scoped image-pull secret,
passed in memory and removed with the cluster; no token or DB secret enters artifacts.

## Hosted Kubernetes experiment

The kind profile has one control plane and three workers labelled as simulated
zones on ONE GitHub runner. This is real Kubernetes/PostgreSQL process behavior,
not independent physical zones, cloud networking/storage, or cloud HA qualification.
All image/operator/schema inputs are version/digest/checksum pinned.

Two leader-electing CloudNativePG operator replicas occupy distinct workers.
Three database instances use required zone anti-affinity, persistent local-path
volumes, ANY1 required synchronous durability and failover quorum. Migration must
complete before the three API/worker replica Deployments are applied.

The test observes actual placement, ready replicas, immutable image references,
synchronous_standby_names and successful reports. It deletes the primary pod under
normal Kubernetes deletion semantics, requires promotion to a different primary
and validates previously acknowledged reports and new work.

It then queues twenty durably accepted jobs, observes outstanding work and abruptly
stops only the kind worker hosting the current primary. It requires another primary
promotion, two surviving API/worker replicas, recovery of accepted work and golden
reports. The worker container is restarted and full three-instance/replica readiness
must return. The recorded recovery interval includes control-plane detection and
operator observation; it is not a zero-downtime or universal zero-data-loss promise.

Local host-path PVCs are not zonal cloud disks. This experiment does not establish
CSI failover, partition safety, backup/restore, GCP/EKS IAM or provider cleanup.
The cleanup owner restores any stopped worker, deletes only the named disposable
cluster and removes its temporary kubeconfig. Failed cleanup cannot produce pass.
Artifacts contain allowlisted summaries, never raw secrets or database contents.

Before cloud execution: qualify CSI/storage deletion, network policies and workload
identity, image access, capacity during a node loss, full costs and spending protections.
Budget/lifetime settings remain an explicit approval gate. This workflow provisions
no GCP/AWS resources and is not automatically run on documentation changes.
