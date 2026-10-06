# Validation and activation runbook

## Ephemeral HA cloud execution policy

Follow the [ephemeral HA architecture and cost policy](architecture-cost.md)
before activation. London multi-zone HA, 4 GiB minimum-first nodes, layered
provider-specific alerts, a £5 gross per-run planning ceiling, £10 total for the
first GCP+AWS attempts, 60-minute maximum lifetime and immediate audited cleanup
are the approved starting policy. These are not provider-guaranteed monetary caps;
preflight cost coverage and alert delivery must pass before apply. Existing
topology/intent validators do not yet enforce the complete policy.

## Credential-free checks

Use Go 1.27.1, Terraform 1.16.4, kubectl with Kustomize, Python 3 and PyYAML 6.0.2.
The provider lock contains Linux amd64 and arm64 checksums.

```sh
cd workload
go test ./...
go vet ./...
# Integration tests skip unless TEST_DATABASE_URL is set.
# Use ONLY a disposable database: the suite truncates the jobs table.
TEST_DATABASE_URL='postgres://workshop:local-demo-only@127.0.0.1:5432/workshop?sslmode=disable' go test -race ./...
cd ..
terraform fmt -check -recursive infrastructure
terraform -chdir=infrastructure/lab init -input=false -lockfile=readonly
terraform -chdir=infrastructure/lab validate
python3 scripts/check-ownership.py
```

The integration URL is illustrative: start a dedicated PostgreSQL test instance
or use the hosted workflow's isolated service. The default application Compose
database intentionally has no published host port.

## Before any cloud apply

This is not yet an executable end-to-end cloud runbook. Do not run apply merely
because validate passes. Required outstanding gates:

1. Confirm the dedicated project, billing scope, region/zone, operator egress CIDR,
   GBP billing currency, £5 per-run budget and 60-minute expiry.
   Configure and test the GCP cost-alert email plus the 25/50/75/90/100% actual
   and 75/100% forecast thresholds before provisioning.
2. Activate and qualify the [separate identity/alert bootstrap](cloud-bootstrap.md).
   Terraform state is local to a trusted operator or short-lived run workspace;
   never upload it as an artifact/cache or commit it. Never commit plans,
   service-account keys or environment credentials.
3. Qualify the selected GKE/Config Sync versions and fleet RBAC behavior.
4. Add application cloud IAM, Pub/Sub/GCS resources and adapters, image release
   provenance, network policies and workload deployment.
5. Implement run-scoped inventory, evidence export and an independent expiry
   janitor. Job-local Terraform state is not a replacement: runner loss must still
   permit exact-scope cleanup from ownership labels. Cluster deletion protection
   must be changed explicitly for approved teardown.

The bootstrap Terraform root includes six opt-in event-specific Monitoring log
alerts plus the [`notify_lifecycle.py`](../scripts/notify_lifecycle.py) publisher. Once
bootstrapped, emit only the allowlisted `created`, `ready`, `expiry-warning`,
`teardown-started`, `teardown-passed` and `teardown-failed` events. A scheduler or
workflow must call the 15-minute expiry warning; no scheduler or cloud-run workflow
is implemented yet. Alert creation and delivery have not been cloud-tested.
The emitting identity needs `logging.logWriter` on the exact lab project; do not
grant broad Monitoring administration to the run workflow.

No workflow in this repo has cloud credentials or performs Terraform apply.
Budget intent is not a spending cap. A future cloud plan must list all billable
resources including NAT, disks, logging and any retained artifacts.

## Local failure diagnosis

- API not ready: inspect database health and `docker compose logs migrate api`.
- Job remains running: observe lease expiry, worker logs and next attempt;
  after five expired attempts expect terminal failure.
- 409 on submit: the key was already used for different input; use a new key.
- 409 on report: the report is not yet committed; poll the job state.
- Failed migration: stop and inspect; do not erase retained data to hide failure.

The schema bootstrap uses an advisory lock and idempotent creation. It is not a
general migration engine and must be replaced before schema-changing releases.
