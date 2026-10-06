# GCP state and federated CI bootstrap

The bootstrap Terraform root is separate from the disposable lab root. It declares
private/versioned GCS state, GitHub federation, a CI service account and explicitly
reviewed project roles. This configuration is validated without credentials;
activation waits for the chosen project, region, budget/lifetime and access setup.

## Identity contract

The provider accepts tokens for this repository's numeric repository/owner IDs,
main branch, the named cloud-run.yaml workflow, and workflow_dispatch events.
Those IDs were verified through GitHub's repository API on 2026-10-04.
The workflow file is reserved for the later cloud lifecycle implementation;
ordinary Validate/fork jobs cannot use this trust.

The account initially receives state-bucket object access only. Project roles
default to an empty set; cloud provisioning needs an explicitly reviewed role
list. Owner/Editor are rejected. No service-account key resource is created.
Initial bootstrap still needs an authorized operator's short-lived login; GitHub
cannot federate into a provider that does not yet exist.

GitHub's current default subjects can include immutable numeric IDs for newer
repositories. The mapping uses the actual subject plus numeric attribute
conditions, rather than constructing the older name-only subject format.
AWS trust must likewise use the subject format actually emitted for its repo.

References:

- [Google deployment-pipeline federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Google federation best practices](https://docs.cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation)
- [GitHub OIDC claims/immutable subjects](https://docs.github.com/en/actions/reference/security/oidc)

## State ownership

Bootstrap owns IAM/federation/state APIs and its retained bucket. The lab root owns
GKE/network/fleet/configuration APIs. The bucket blocks public access, enables
object versioning, refuses force deletion and has Terraform prevent_destroy.
It remains outside ordinary lab teardown. IAM/federation must remain recoverable
while cloud cleanup is still pending.

The lab root declares a partial GCS backend. Future init supplies an approved
bucket and prefix through backend configuration. Ordinary CI uses backend=false
and never reads live state. Initial bootstrap starts locally, then its state must
be migrated deliberately to the separate bootstrap prefix and the local copy
handled as sensitive data. Never publish state, saved plans or credential caches.

## Activation sequence

Once cloud settings are approved and access is verified:

1. Review the bootstrap plan under the operator identity.
2. Configure the approved private cost-alert recipient, enable the project budget,
   and set its GBP amount to at most £5 with five actual and two forecast thresholds.
   Budget/email inputs and Terraform state must stay private.
3. Create the reviewed state/federation resources; record identifiers privately.
4. Migrate bootstrap state and configure the lab backend with separate prefixes.
5. Review the minimum project role set and the dedicated lifecycle workflow.
6. Test budget notification delivery and token acceptance/rejection for allowed/
   forbidden workflow contexts.
7. Only then plan the bounded lab create/run/export/delete cycle.

Provider validation does not prove claim evaluation, cloud permissions, bucket
locking/recovery or the lifecycle. Those require actual qualification. No cloud
apply workflow or cloud resources have been activated by this change.
