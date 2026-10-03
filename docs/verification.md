# Verification record

## Initial foundation — 2026-10-03

Source: `23b9632`.
[Hosted run 37145048417](https://github.com/talisman36935/gcp-platform-delivery-lab/actions/runs/37145048417)
passed:

- Go formatting, vet and race tests against an isolated PostgreSQL service.
- Concurrent idempotency, conflict rejection, lease exclusion, stale completion
  rejection, successful retry and five-attempt exhaustion.
- Container build and Compose API/worker smoke test.
- Terraform format/init/validate and disjoint Config Sync ownership.

Observed golden report:

```json
{
  "documents": 3,
  "tokens": 11,
  "unique_tokens": 6,
  "duplicate_documents": 1,
  "input_sha256": "2522de9d1c28cf3a163c3703dbabb2b63009e5daa6a8d98f2aac85f577307bd5"
}
```

This record preserves the assertion/result after CI log retention expires.
It is an authored test record, not a signed portfolio evidence bundle. It proves
local behavior, not cloud IAM, GKE deployment or performance. Subsequent commits
have their own Validate runs; do not transfer this result to untested revisions.
