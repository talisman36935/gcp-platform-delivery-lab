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

The release for source `6a6e522b0f67925e2e5fab476c61350582aadf1e` is publicly
pullable at
`ghcr.io/talisman36935/report-workshop@sha256:ff32688b7c8f2764ea46a32e8813d8e45585615d494c116324dfc5f2b7307d9f`.
Native ARM migration/API/worker golden smoke passed in
[37392244169](https://github.com/talisman36935/gcp-platform-delivery-lab/actions/runs/37392244169).
The separate [anonymous-pull observation](observations/6a6e522/anonymous-pull.json)
verifies both manifests, configs and every runtime layer by digest without an
account credential. The original release artifact records what was known at
publication time; it is not rewritten to backdate later checks.

Recheck public content with bounded downloads (32 MiB per blob, 64 MiB total):

```sh
python3 workload/deploy/verify_anonymous_image.py \
  --image ghcr.io/talisman36935/report-workshop@sha256:ff32688b7c8f2764ea46a32e8813d8e45585615d494c116324dfc5f2b7307d9f \
  --output output/anonymous-pull.json
```

The verifier never uses local Docker/account credentials and drops registry
authorization on blob-storage redirects. This proves pullable runtime content,
not signature authenticity or Kubernetes/cloud runtime behavior.

## Hosted Kubernetes experiment

[Run 37392244169](https://github.com/talisman36935/gcp-platform-delivery-lab/actions/runs/37392244169)
passed all three jobs. The [runtime observation](observations/6a6e522/kubernetes-ha.json)
records primary `report-db-1` to `report-db-2` in 59.726 seconds (including full
database readiness), then primary-worker loss and promotion back to `report-db-1`
in 88.477 seconds (including surviving-app access). Two API/worker replicas
survived. All twenty queued jobs were outstanding at fault time; five baseline,
twenty queued and six recovery reports matched the golden output. The bounded
completion trigger was removed, full readiness restored and cluster deletion
confirmed. These are this experiment's observation intervals, not production SLOs.

Earlier [release audit](observations/0a387dd/release-qualification.md) and
[failed runtime observation](observations/6db97f0/kubernetes-ha.json) remain
preserved. Operator installation uses server-side apply for large CRDs. The
pod-deletion harness needed an explicit grace instead of timing out against
the operator's default 1,800-second shutdown allowance.

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
an explicit thirty-second termination grace (without force deletion), requires
promotion to a different primary
and validates previously acknowledged reports and new work.

It installs a bounded, test-only ten-second completion trigger, then queues twenty
durably accepted jobs, observes outstanding work and abruptly
stops only the kind worker hosting the current primary. It requires another primary
promotion, two surviving API/worker replicas, recovery of accepted work and golden
reports. The trigger/function are removed on the promoted primary before recovery
assertions; this changes no application image. The worker container is restarted
and full three-instance/replica readiness
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
