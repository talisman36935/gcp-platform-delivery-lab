# Queue and immutable object delivery

The shared image has opt-in `WORK_BACKEND=gcp` and `WORK_BACKEND=aws` worker paths;
empty/local retains the credential-free PostgreSQL queue. Neither path creates
cloud resources. Domain/use cases import no cloud SDK. API acceptance and report
retrieval still use PostgreSQL; a queue outage can leave durable outbox work pending.
Committed JSONB remains the HTTP report source; object download/export is separate.

## Crash and duplicate semantics

Submission writes the job/outbox together. A dispatcher claims an independently
fenced thirty-second outbox lease, commits it, publishes outside the transaction,
then marks publication only with its live token. Lost publish/mark responses can
cause duplicate messages. They cannot grant processing ownership.

Version-one envelopes contain only a validated job ID. Trace provenance is read
from the durable job, never trusted from a message. The worker acquires the existing
thirty-second DB processing lease and monotonic attempt token. It creates
`reports/JOB/attempt-TOKEN/SHA256.json`, then selects its object reference and JSONB
report in the same fenced completion transaction. Only then does it acknowledge.

GCS uses a generation-zero condition; S3 uses `If-None-Match: *`. An existing object
is accepted only after reading and comparing bounded exact bytes. No overwrite or
public ACL is requested. Failed writes/commits are not acknowledged; object-before-
commit can leave an attributable orphan. Commit-before-ack redelivery recognizes
terminal state and acknowledges without another calculation/upload. Stale receipts
cannot acknowledge newer attempts. Poison/unknown deliveries stay unacknowledged
with a bounded retry deadline; provider DLQ/redrive permissions/configuration remain
an activation prerequisite, not a completed quarantine feature.

SQS receipt visibility/PubSub ack deadline is sixty seconds at receive; retries use
thirty seconds. Provider delivery limits and job attempt limits are independent.
One worker processes one delivery at a time, with a ten-second iteration deadline.
There is no live-resource provisioning, lease heartbeat, orphan sweeper or independent
recovery scanner yet. Never purge a live queue: its published outbox rows will not
automatically republish. Backend switching on a live backlog is not supported.

## Explicit existing-resource configuration

| Worker backend | Required nonsecret settings |
| --- | --- |
| GCP | `GCP_PROJECT`, `PUBSUB_TOPIC`, `PUBSUB_SUBSCRIPTION`, `REPORT_BUCKET` |
| AWS | `AWS_REGION=eu-west-2`, `SQS_QUEUE_URL`, `REPORT_BUCKET` |

Names must use the `report-` prefix; AWS queue URLs must use the London regional
endpoint and a twelve-digit account. Pub/Sub calls use the London endpoint.
Actual bucket location, ownership, queue DLQ and workload identity require live
preflight. SDK default identity chains support federated workload credentials;
do not paste keys, mount long-lived credential JSON or export raw provider errors.
GCP's optional storage-client metrics are disabled to avoid a hidden telemetry
dependency. Ordinary CI has no cloud identity.

The `schema-check` command performs read-only additive-schema readiness. Delivery
profiles use it as an init gate; only the versioned migration Job performs DDL.

## Evidence boundary

Hosted CI exercises real PostgreSQL publication/processing fences, use-case fault
contracts and SDK requests against local HTTP/gRPC protocol doubles. Conditional
object retries, corrupt-object rejection, receipt operations, poison handling and
commit-before-ack are tested. These are not cloud IAM, actual service redelivery,
DLQ, regional placement, object durability or deletion qualification. Real cloud
tests remain blocked behind account, cost-cap coverage, alerts and lifetime approval.
