# Validation and activation runbook

## Minimal cloud execution policy

Follow the [minimal infrastructure and cost policy](plan/portfolio-demos/minimal-infrastructure.md)
before activation. London is selected; budget alerts and immediate cleanup are
required. £2/run and one hour remain proposals, not approved limits. Verified
spending protection and bootstrap retention decisions remain activation gates.
Existing topology/intent validators do not yet enforce this complete policy.

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
terraform -chdir=infrastructure/lab init -backend=false -input=false -lockfile=readonly
terraform -chdir=infrastructure/lab validate
python3 scripts/check-ownership.py
```

The integration URL is illustrative: start a dedicated PostgreSQL test instance
or use the hosted workflow's isolated service. The default application Compose
database intentionally has no published host port.

## Before any cloud apply

This is not yet an executable end-to-end cloud runbook. Do not run apply merely
because validate passes. Required outstanding gates:

1. Confirm a dedicated project, billing scope, region/zone, operator egress CIDR,
   per-run budget and maximum lifetime.
2. Activate and qualify the [separate state/federation bootstrap](cloud-bootstrap.md).
   Never commit state, plans, service-account keys or environment credentials.
3. Qualify the selected GKE/Config Sync versions and fleet RBAC behavior.
4. Add application cloud IAM, Pub/Sub/GCS resources and adapters, image release
   provenance, network policies and workload deployment.
5. Implement run-scoped inventory, evidence export and independently verifiable
   teardown. API enablement is retained deliberately; cluster deletion protection
   must be changed explicitly for approved teardown.

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
