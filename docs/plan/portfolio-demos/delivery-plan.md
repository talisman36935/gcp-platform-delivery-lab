# Delivery plan and acceptance gates

Status: implementation plan, 2026-10-02. Parent: [strategy](../portfolio-demo-strategy-2026-10-02.md).

## Definition of the first complete portfolio release

Both cloud repositories are public and independently understandable. They deploy
the same released Go workload, capture an application investigation and a platform
failure/recovery story, and publish reproducible evidence consumed by Labs. AWS
returns to its declared dormant state with an independent teardown audit. GCP's
retained resources and teardown outcome are also explicit. Local reproduction works
without credentials. Documentation and evidence accompany the implementation.

The first complete release does not require Cloud Deploy, CAPI pivot, managed DB
HA, multi-region operation or a visitor-triggered cloud environment. Those remain
visible follow-up milestones. Cloud Deploy remains part of the overall original
scope and must not disappear from the backlog when the default Config Sync path ships.

## Work sequence

| Milestone | Deliverables | Exit evidence |
| --- | --- | --- |
| M0 Contracts and foundations | Source ownership, repo conventions, OpenAPI, event/evidence schema, first ADRs, local tooling | Schemas validate, ownership matrix reviewed, clean credential-free checks |
| M1 Local application | API/worker/PostgreSQL, durable local adapters, fixture report, crash recovery | Fresh quickstart, golden result, duplicate/crash tests and cleanup |
| M2 Local investigation | Telemetry stack, load protocol, regressed release, comparison exporter | EXP-01/02/03/08 artifacts and documented limitations |
| M3 GCP vertical slice | Terraform bootstrap/environment, actual Config Sync, queue/storage identities, app delivery | Fresh creation, app completion, digest promotion, drift and Git rollback, export/teardown |
| M4 AWS vertical slice | kind/Flux/CAPI/CAPA/ACK, identity/output handoff, independent janitor/audit | Fresh run, readiness timeline, reconciliation fault/recovery, audited deletion |
| M5 Evidence and Labs | Validated artifact publication, historical run UI and case studies | Public pages match artifacts, mobile/accessibility/failure-state gates pass |
| M6 Extended comparisons | Cloud Deploy profile, CAPI pivot, managed DB recovery experiments | Separate real run records and updated ADRs, cost and teardown evidence |

M3 and the M4 compatibility investigation can overlap after M2 fixes the workload
and evidence interfaces. Complete one thin cloud create/run/destroy loop before
expanding that platform. Labs fixture development can start after M0, but measured
status waits for qualified cloud bundles. Avoid building both full cloud platforms
before verifying the first workload investigation locally.

## Suggested scoped implementation work items

These are planning identifiers, not existing Linear ticket IDs. Create follow-ups
when implementation begins and link them to TAL-81/TAL-183 without reopening the
completed foundation. Each item includes code, tests, documentation and evidence.

| ID | Work item | Dependency |
| --- | --- | --- |
| PLAN-01 | Scaffold shared app and two platform repos; configure checks and contribution docs | Source ownership decision |
| APP-01 | Domain/OpenAPI/job storage/outbox and deterministic report | PLAN-01 |
| APP-02 | Durable local dispatch, fencing and crash-window tests | APP-01 |
| OBS-01 | Collector/backends, telemetry conventions and investigation dashboard | APP-01 |
| RUN-01 | Seeded load, regression release and local evidence exporter | APP-02, OBS-01 |
| GCP-01 | Terraform state/federation/environment and Config Sync bootstrap | PLAN-01, account decisions |
| GCP-02 | GCP adapters, workload identity and delegated GitOps | GCP-01, APP-02 |
| GCP-03 | Promotion/drift/rollback experiment and cleanup | GCP-02, RUN-01 |
| AWS-01 | KROPS/CAPA/ACK compatibility and bootstrap identity spike | PLAN-01, account decisions |
| AWS-02 | Cluster/resource reconciliation and workload Flux handoff | AWS-01, APP-02 |
| AWS-03 | Scoped lifecycle recorder, TTL janitor and independent cloud audit | AWS-01 |
| AWS-04 | Reconciliation failure/recovery and teardown qualification | AWS-02, AWS-03, RUN-01 |
| PUB-01 | Evidence schema/allowlist/provenance validation and durable publication | RUN-01 |
| WEB-01 | Labs routes, run explorer and accessible static fallbacks | PUB-01 |
| DOC-01 | Cloud case studies and claim-to-artifact maps | GCP-03, AWS-04, WEB-01 |
| ADV-01 | Cloud Deploy profile with disjoint ownership | GCP-03 |
| ADV-02 | CAPI management pivot and recovery drill | AWS-04 |

The EXP prefix is reserved for scenarios in evidence-and-labs.md. RUN-01 is the
implementation work that builds the shared experiment runner.

## Definition of done per change

Applicable formatting, type/static checks and tests pass; meaningful failure paths
are exercised; source/config versions are pinned; docs reflect actual behavior;
claimed outcomes have durable evidence. A cloud change additionally verifies live
resource behavior and cleanup. A frontend change verifies rendered interaction.
Report unverified claims as remaining work. Do not equate a mocked provider test,
successful image build or successful apply with a complete cloud demonstration.

Local CI should cover Go behavior, SQL migrations, schemas, rendered Kustomize/Helm,
Terraform validation and policy checks without cloud secrets. Hosted cloud workflows
verify identities, actual reconciliation and resource deletion. Test failure cases
that can invalidate the lab claim, not mirrors of every configuration field.

Dependency updates use pinned versions and automated proposals, qualified against
the compatibility matrix. A tool upgrade can invalidate collected evidence about
current behavior; historical runs remain valid for their recorded versions.

## Documentation deliverables

| Document | Reader and question |
| --- | --- |
| README | Reviewer: what does this prove and how do I try it? |
| Architecture/ownership | Engineer: which component owns each resource and why? |
| Local quickstart | Contributor: can I reproduce the application without cloud access? |
| Cloud runbook | Operator: how do I preflight, run and verify one bounded experiment? |
| Recovery/teardown | Operator: what survives failure and how do I verify cleanup? |
| Identity/threat model | Reviewer: where do credentials, privilege and trust boundaries sit? |
| Experiment protocol | Reviewer: what was held constant and what did the result establish? |
| Evidence schema | Integrator: how do I validate and consume a run? |
| Case study | Recruiter/engineer: what did we discover and how did we respond? |
| Reference/attribution ledger | Contributor: what inspired or supplied this implementation? |

ADRs should cover application scope, repository ownership, Config Sync versus Cloud
Deploy, Terraform/controller boundaries, management-plane lifetime, identity,
queue semantics/idempotency, data durability, telemetry placement, evidence
publication and cost/teardown policy. Each ADR records context, alternatives,
decision, consequences, verification and conditions for revisiting it.

Keep documentation close to code. README links deeper material; portfolio links
the relevant version of the repository docs. Validate internal links, executable
quickstarts, schema examples and generated diagrams where appropriate. Design
diagrams are labeled authored models until tied to measured runtime evidence.

## Decisions and recommended defaults

| Decision | Recommended default | When resolved |
| --- | --- | --- |
| Application | Small Go document/report processor | Direction endorsed; finalize naming at M0 |
| Source ownership | Third small shared app repo, provisional name observable-report-workload | Before repo creation |
| GCP path | Terraform cloud foundation plus Config Sync workload reconciliation | Default implementation |
| Cloud Deploy | Additional delivery profile with exclusive app ownership | M6 |
| AWS path | Disposable kind management plus one temporary EKS workload cluster | Default implementation |
| Application DB | Single in-cluster PostgreSQL for initial cloud runs | M1/M3, document availability limits |
| Go build | BuildKit and immutable release artifacts | M0 |
| GitOps packaging | Kustomize for owned manifests; pinned Helm releases where justified | M0/M3 |
| Cloud accounts/projects/regions | Dedicated lab scope selected from verified available accounts | Before cloud operations |
| Spend and maximum run lifetime | Explicit per-run budget and TTL, with independent janitor | Before cloud operations |
| GKE mode and AWS sizing | Small compatible setup selected after spike | M3/M4 |
| Collector/backend placement | One distribution and credential-free local stack; cloud placement measured | M2/M3 |
| Artifact storage | Immutable durable public bundles, portfolio pins checksums | PUB-01 |
| Controller/runtime versions | Verified compatible pinned versions | AWS-01/GCP-01 |
| Public interactive execution | Historical evidence explorer initially | M5 |

Routine implementation decisions should be captured in ADRs as work progresses.
Cloud budget/account choices need actual user constraints; elapsed time or an
existing credential does not supply a spending policy.

## Risks and concrete responses

- Application scope grows: freeze one analysis and two process roles for M1/M2.
- Queue abstraction hides differences: run provider-specific contract suites.
- GitOps owner conflict: validate object identities and keep Cloud Deploy separate.
- Management credentials expire: test refresh and independent cleanup identity.
- Cloud controller support differs from examples: perform the minimal live spike.
- Reported health relies on absent telemetry: require evidence freshness and counts.
- Cleanup loses its controllers: preserve dependency order and external inventory.
- Public artifacts expose private fields: allowlist export and qualify examples.
- Comparison implies unfair performance ranking: publish configuration and limit
  conclusions to tested operational behavior.
- Portfolio becomes dependent on live clusters: build from validated retained bundles.

## Handoff checklist

Before M0 implementation: read the master strategy, four specifications and reference
catalogue; verify current repo/ticket state; resolve source ownership. Before each
cloud milestone: verify identity/region, spending/TTL, compatibility and cleanup
path. Before public evidence: verify artifact provenance, qualification and privacy.
Record actual progress in scoped follow-ups and durable repo docs, keeping this
plan's proposed status separate from implementation evidence.
