# Two clouds, two control-plane models

Strategy proposal, 2026-10-02. Proposed choices below are not completed work or
approved cloud expenditure. Source requirements: Linear TAL-81 (including its
ephemeral AWS and profiling extensions), TAL-183, and the request to expand the
two public demo repositories. TAL-81 remains complete for the portfolio foundation.

The user endorsed this direction and requested a detailed plan on 2026-10-02.
The following specifications turn the strategy into implementation work. Defaults
are recommendations to implement and test; open account/spending decisions remain
explicit. This documentation does not report either lab as built.

## Detailed implementation plan

Read in this order:

1. [Application specification](portfolio-demos/application.md): domain, API,
   architecture, message processing, testing and shared release ownership.
2. [Platform specification](portfolio-demos/platforms.md): GCP and AWS ownership,
   identities, bootstrap, GitOps, promotion, rollback and teardown.
3. [Evidence and Labs specification](portfolio-demos/evidence-and-labs.md):
   telemetry, experiments, measurements, artifact contracts and presentation.
4. [Delivery plan](portfolio-demos/delivery-plan.md): milestones, acceptance,
   verification, documentation, decision register and handoff.
5. [Annotated reference catalogue](portfolio-demos/references.md): public exemplars,
   maintainer examples, technical sources, applicability and reuse boundaries.

## Engineering argument

Use the same application, immutable release and experiment protocol to explain
two platform models: Terraform plus Config Sync on GCP, and Flux plus CAPI/CAPA
and ACK on AWS. Demonstrate delivery, drift, diagnosis, recovery and deletion.
Separate application readiness from infrastructure/controller readiness.

## Recommended application: document processing and report generation

Working concept: a small Go application that accepts a synthetic document batch,
creates an asynchronous job, calculates a deterministic report and stores the
result. A compact UI shows job progress, retry state and the completed report.
Use seeded text/CSV fixtures; no real personal documents or external content APIs.

Start with two deployable processes from one Go module:

- API/UI: validate submissions, expose job status and report retrieval.
- Worker: claim jobs, process documents and write report objects.
- PostgreSQL: job metadata and a transactional outbox.
- Queue: Pub/Sub on GCP, SQS on AWS, and a local implementation for development.
- Object storage: GCS on GCP, S3 on AWS, and a local development adapter.

Keep domain and use-case code independent of SDKs. Define narrow ports for job
storage, message delivery and object storage; keep provider adapters at the
boundary. Share HTTP/job schemas, deterministic fixtures and load scenarios.
Do not claim queue semantics are identical: explicitly test redelivery,
acknowledgement, visibility/lease expiry, ordering assumptions and idempotency.
Use an outbox dispatcher mode in the worker and a reconciler for incomplete
result publication; test crash windows across DB, queue and object store.

In-cluster PostgreSQL is sufficient for the initial disposable cloud runs; it
does not establish managed-database HA. Evaluate Cloud SQL/RDS in a later
persistence/recovery experiment. Use tiny fixture data and bounded processing.

The application supplies meaningful signals: accepted-to-completed latency,
queue age, retries, throughput, failed jobs, database waits and CPU/allocation
profiles. A second immutable revision deliberately regresses document analysis
without changing its output. Fault configuration is controlled by the experiment
runner, not exposed as a public administration endpoint.

## GCP ownership and delivery

Terraform owns cloud APIs, networking, GKE, Artifact Registry, GCS, Pub/Sub,
IAM/federation, fleet membership and Config Sync bootstrap. Keep bootstrap state
and environment state distinct; record state storage, locking, recovery and
deletion behavior. Cloud provisioning is reviewed plan/apply automation with
scheduled drift detection; it is not a continuously reconciling controller.

Config Sync owns Kubernetes desired state after bootstrap. RootSync manages
platform configuration and delegates application namespaces through RepoSync.
Use Kustomize bases/overlays, namespace RBAC, quotas, network policy, telemetry
configuration and immutable image references. Bootstrap-owned RootSync fields
remain owned through the Google API/Terraform path.

Describe this as Config Sync with ACM lineage. Policy Controller is a separate
policy capability; Config Connector manages cloud resources and is not another
name for Config Sync. Do not add Config Connector to the baseline while Terraform
owns those same resources.

Build once using BuildKit, test, scan and publish a signed image with provenance
and SBOM. CI proposes a digest change in the environment configuration. Merge
changes desired state; Config Sync reconciles it. Promote that same digest and
roll back with a Git revert plus observed recovery. Use OIDC/federation for CI and
workload identity for application access.

TAL-81 also requests Cloud Deploy. Preserve it as a second documented delivery
profile: Config Sync owns the platform baseline, Cloud Deploy owns application
objects in explicitly excluded namespaces. Never have both manage the same
objects. This profile demonstrates Cloud Deploy promotion/rollback but is not
described as end-to-end pull reconciliation. Default proposal is the Config Sync
application path because the new request explicitly prioritizes full GitOps.

Start with dev/staging namespaces in one temporary GKE cluster and label their
shared failure boundary. Separate clusters/projects are a later isolation test.

## AWS ownership and lifecycle

Use KROPS as credited architectural inspiration, pinning the reviewed reference
commit before implementation. Author our own manifests, lifecycle automation,
workload integration and evidence exporter. KROPS is a composition of controllers;
there is no extra KROPS controller to install.

Default: temporary kind management cluster, Flux, CAPI/CAPA, one temporary EKS
workload cluster, workload Flux and selected ACK controllers. Keep cloud resource
controllers and their privileges in the management plane where practical.
CAPA owns cluster infrastructure; ACK owns application S3/SQS resources. Specify
IAM/bootstrap ownership separately and never let multiple tools own a resource.
Validate the selected ACK APIs and controller/CRD versions in a compatibility spike.

Bootstrap is an explicit finite exception to reconciliation: account preparation,
initial credentials, controller installation and Git source trust must exist
before controllers can act. Use bounded credentials and document expiry/refresh
for controllers running in kind; CI OIDC alone does not solve controller identity.

Git changes drive dependencies through Flux readiness gates: CRDs/controllers,
cloud resources, workload configuration, application and smoke assertions.
Capture the applied source revision and each controller's conditions/events to
explain which dependency prevents readiness.

Full pivot is a separate experiment: kind -> temporary EKS management cluster ->
ownership transfer -> EKS workload cluster. Prove ownership and continued
reconciliation, then recover and tear down. Do not silently adopt the reference's
multiple persistent clusters or credentials.

Deletion is part of acceptance: stop production of new jobs, preserve evidence,
remove consumers/resources in dependency order, retain functioning controllers
and credentials until finalizers complete, then remove clusters/management.
Independently query AWS for leftover scoped billable resources. Failed cleanup
produces a failed/incomplete run record, not a successful green run. An independent
TTL janitor survives runner or management-cluster failure. Record retained shared
resources separately from per-run resources, and measure cost with estimate/actual
labels and billing delay. Dormant is the normal AWS state.

## Observability and experiments

Application telemetry travels through Alloy/OTel Collector to Prometheus-compatible
metrics, Loki and Tempo; Go profiles go to Pyroscope. Provide a local Compose
stack and Kubernetes deployment configuration. Export evidence before deleting
temporary telemetry storage. Hosted backends remain an optional deployment choice.

Stable service identities carry immutable application revision, configuration
revision, environment and run metadata. Keep job IDs in logs/traces, not metric
labels. Bound run/revision label retention and cardinality. Propagate context
through the queue; use span links where retries or batching need them. Profile
CPU, allocations and goroutines; evaluate trace-to-profile linking with the
supported Go bridge and preserve aggregate comparison if linking is unavailable.

Required experiments:

1. Baseline -> regressed application revision -> diagnosis -> Git rollback ->
   recovered completion latency. Inspect metrics, trace, logs and profile diff.
2. Invalid desired state or missing resource permission -> visible reconciliation
   stall -> corrected Git state -> readiness with measured stage durations.
3. Out-of-band Kubernetes drift -> correction or prevention -> attributed event.
4. Worker crash/message redelivery -> idempotent completion and bounded retry.
5. Telemetry outage -> explicit missing evidence while application health is
   measured independently.
6. Teardown failure -> resource leak detection -> scoped cleanup verification.

Start with experiments 1 and 2. Define thresholds before measurement, plus load
seed/rate/concurrency, dataset hash, warm-up, sampling, versions and resource limits.
Measure profiling overhead with comparable profiled/unprofiled runs. Report sample
size and uncertainty. Infrastructure readiness and application Git-to-ready latency
are different measurements. GKE/EKS machine and queue differences prevent a blanket
cloud performance ranking; the central comparison is operational behavior.

## Repository boundaries

Keep the two platform repositories independently understandable and runnable.
Recommend a small third application repository, with a versioned Go module,
container releases and shared fixture/evidence schemas. Both platform repositories
pin the same application source and image digest. This is a proposed scope choice,
not permission to create another repository. If exactly two repositories are
preferred, one must be the explicit application owner; the other consumes its
versioned artifact. Avoid independent drifting copies.

Each platform repository contains bootstrap/, infrastructure/, gitops/, telemetry/,
experiments/, evidence/ and docs/ as needed, with an obvious local quickstart.
Separate validation CI from privileged cloud lifecycle workflows. Tests cover
domain behavior, provider contracts, rendered manifests, meaningful lifecycle
failures and the evidence schema. Local tests never count as proof of cloud IAM
or a real CAPA/ACK provisioning run.

## Portfolio Labs contract

The endorsed visitor experience and rollout sequence are detailed in
[Portfolio integration](portfolio-demos/evidence-and-labs.md#portfolio-integration).
The research basis for comparable portfolios, and the limits of any originality
claim, are recorded in
[Precedent and the proposed combination](portfolio-demos/references.md#precedent-and-the-proposed-combination).

Extend the existing static Astro Labs surface with GCP delivery, AWS reconciliation
and shared workload/investigation pages. Each starts with a 60–90 second explanation,
an architecture view and the last verified experiment. Technical detail remains
available through source, ADRs and reproducible run artifacts.

Use a versioned allowlisted evidence manifest: schema/run ID, app/config revisions,
image digest, scenario/dataset/load settings, timestamps, environment description,
assertion outcomes, latency summaries, selected sanitized telemetry, checksums,
cost basis and teardown/audit state. CI validates and publishes immutable bundles;
a reviewed portfolio update pins a bundle/checksum. Long-term evidence must not
depend on expiring CI artifacts.

The UI distinguishes planned, locally verified, cloud verified, failed/incomplete
and dormant environments, always displaying observation time. Let visitors select
a historical run, inspect its timeline and compare baseline/regression/recovery.
Link a selected trace to related logs and profile evidence. Retain existing
synthetic examples as labeled fixtures until real evidence replaces them.
Do not imply that historical telemetry is live. Public page views never provision
clusters; optional future live demos require a separate bounded design.

## Documentation and delivery gates

Deliver a short README walkthrough, architecture/ownership document, threat/identity
model, ADRs, local and cloud runbooks, teardown/recovery runbook, experiment protocol,
evidence schema, attribution/license ledger and a measured case study in each repo.
Document assumptions and limits alongside results. CI validates documentation links,
schemas and executable examples where practical. Every milestone closes with code,
verification and its matching documentation.

Suggested milestones:

1. Shared workload, local pipeline and baseline/regression evidence, plus schema.
2. GCP Terraform/Config Sync delivery, promotion, drift and rollback evidence.
3. AWS kind/Flux/CAPA/ACK lifecycle, reconciliation failure and audited teardown.
4. Portfolio ingestion and accessible historical experiment explorer.
5. Separate Cloud Deploy delivery profile, CAPI pivot and managed-database recovery.

Resolve application choice/source ownership first. Account/project, region, run
budget/TTL and telemetry hosting are required before cloud activation. Exact
provider versions and GKE mode are implementation-spike decisions.

## Portfolio exemplar review

Reviewed public documentation and selected linked source/CI pages on 2026-10-02.
These are examples of presentation and architecture, not independently reproduced
or audited implementations. No claims about their live backend health are made.

| Example | Useful pattern | Application here |
| --- | --- | --- |
| [Dan Hughes portfolio](https://github.com/danielshughes/portfolio) | Separate personal homepage, engineering notes and interactive experiments; documented local operation without account credentials | Keep Labs approachable and documentation deep; label simulated, local and cloud evidence precisely |
| [Outsight GitOps case study](https://syedtashfin.vercel.app/case-studies/cicd-gitops-multitenant-kubernetes-saas) | Problem, delivery flow, claim-to-source evidence map, verification commands, explicit limitations and linked CI | Give each of our claims a source path, immutable artifact and reproduction command |
| [Dattaram Miruke EKS build story](https://dmiruke-ai.github.io/platform-engineering-lab-public/blog-cluster-build-story.html) | Cold bring-up, dependency failures and difficult teardown explained alongside architecture | Publish a short investigation plus deeper field notes; test a complete create/run/destroy slice at each cloud milestone |
| [Sean Johnson portfolio](https://s34nj0hn.dev/) | Public aggregate telemetry through a narrow Worker API with private monitoring backends | Make evidence explorable while keeping backend credentials private; use dated historical bundles for our dormant clusters |
| [T-Py-T GitOps homelab](https://github.com/T-Py-T/kubernetes-gitops-homelab) | Clearly separated ownership layers and public architecture/private environment boundaries | Explain ownership and bootstrap dependencies; our clean-room lab should additionally be reproducible from public source |
| [Stackcouture GKE portfolio](https://github.com/stackcouture/cloud-native-gke) | Familiar small voting workload surrounded by IaC, GitOps and platform operations; rollout demonstrations | A small application is sufficient; prioritize operational outcomes over counts of tools/services |

Critical observations: Outsight explicitly documents a no-traffic-as-zero release
metric behavior and direct Helm cleanup in its failure script. Borrow the evidence
map, but require missing/stale telemetry to produce an inconclusive/failed gate and
make normal rollback flow through Git in our design. Direct emergency intervention
must be separately recorded and followed by Git reconciliation. A linked passing
CI run alone does not establish a successful live cloud experiment.

Use three reading depths: a one-minute Labs story, a five-minute guided experiment,
and a reproducible repository/runbook. Each experiment presents question, change,
observations, explanation, recovery, limitations and source links. Record a short
walkthrough after real execution, with a text transcript and equivalent evidence.

### Workload alternatives considered

| Candidate | Strength | Tradeoff |
| --- | --- | --- |
| Purpose-built Go document/report processor | Narrow domain, meaningful asynchronous failures and profiles, visible output, cloud adapters | We must author and test delivery/idempotency semantics |
| OpenTelemetry Demo | Existing distributed traces and failure scenarios; strong teaching material | Broad polyglot system increases scope and reduces focus on our Go implementation |
| AWS Retail Store sample | Recognizable UI, existing OTLP tracing/Prometheus instrumentation and cloud integrations | Larger service/dependency surface and weaker application authorship story |
| Small voting app | Immediately understandable and cheap to understand | Less useful processing work for profiling; extra features needed for the intended investigation |

Recommendation remains the Go processor, with a deliberately tiny first slice:
one deterministic analysis, two processes, seeded inputs and one regression.
Use OTel Demo for scenario conventions and AWS Retail Store for adapter/integration
ideas. Existing applications are viable if speed to a platform demonstration takes
priority over writing a controlled profiling workload. Do not copy source without
reviewing its license and recording provenance.

## Technical references

- [KROPS](https://github.com/polarsquad/krops): controller composition and lifecycle.
- [Config Sync architecture](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/concepts/architecture): ownership and reconciliation.
- [Google ACM samples](https://github.com/GoogleCloudPlatform/anthos-config-management-samples): Config Sync configuration examples.
- [GKE Terraform modules](https://github.com/terraform-google-modules/terraform-google-kubernetes-engine): cloud foundation patterns.
- [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/): scenarios and telemetry conventions.
- [AWS Retail Store](https://github.com/aws-containers/retail-store-sample-app): existing workload alternative.
- [Pyroscope span profiles](https://grafana.com/docs/pyroscope/latest/configure-client/trace-span-profiles/): trace/profile correlation.
- [Original Kaniko repository](https://github.com/GoogleContainerTools/kaniko): archived; use BuildKit as the proposed baseline.

Evaluate source licenses and retain attribution before reusing any implementation.
Reference architecture ideas do not establish that our implementation has passed
the reference project's tests or achieved its capabilities.
