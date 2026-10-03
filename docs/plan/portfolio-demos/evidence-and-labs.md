# Observability, experiments and portfolio evidence

Status: implementation plan, 2026-10-02. Parent: [strategy](../portfolio-demo-strategy-2026-10-02.md).

## Questions the system must answer

- Which application/configuration revision produced this report?
- Where did time go between accepted job and completed report?
- Did a release change processing cost, dependency latency or both?
- Which infrastructure dependency prevents the workload becoming ready?
- Did rollback restore the measured behavior?
- Was teardown complete, and what did the run cost?

Collect evidence to answer these questions before adding additional dashboards.
App health, controller health, telemetry health and cloud cleanup are separate
results; none implies the others.

## Telemetry architecture

```text
API / worker -> OTLP -> Alloy or OTel Collector -> Tempo / metrics backend
structured logs -> chosen single collection path -> Loki
Go profiling -> Pyroscope
controller metrics / conditions / events -> collector and run recorder
load generator + independent cloud audit -> run recorder
run recorder -> sanitized immutable evidence -> portfolio build
```

Choose one collector distribution for the first implementation and document why.
Use the same export contract in Compose and Kubernetes. Local backends provide
credential-free reproduction. For cloud runs, use temporary in-cluster backends or
an explicitly selected external destination, measuring the resource/cost effect.
Keep telemetry backend credentials out of the application.

Logs have one ingestion route to avoid duplicates: either structured stdout collected
once, or an explicitly selected OTLP log path. Standard fields include UTC timestamp,
severity, service, immutable revision, operation, job/attempt ID, trace/span ID and
bounded error category. Exclude document contents, secrets and provider credentials.

Metrics use bounded labels such as service, environment, operation, outcome and
error category. Run/revision identity may use a separate info series and exported
manifest rather than multiplying every time series. Job IDs and trace IDs belong
in logs/traces or supported exemplars. Capture the metric schema and cardinality
budget in documentation.

### Required signals

| Layer | Signals | Diagnostic purpose |
| --- | --- | --- |
| API | request rate/errors/duration, accepted/rejected jobs | Admission and caller experience |
| Processing | completion duration/rate, retries, failures, oldest pending age | Actual business outcome and backlog |
| Dependencies | DB operation/pool wait, queue operations, object writes | Separate compute from waiting |
| Runtime | CPU, memory, goroutines, allocation profiles | Explain code/resource changes |
| Delivery | source revision, reconciliation condition, rollout readiness | Connect Git to observed deployment |
| Infrastructure | CAPA/ACK conditions, Config Sync errors, Kubernetes events | Find the blocking dependency |
| Telemetry | collector drops/errors, export lag and backend availability | Detect unreliable/missing evidence |
| Lifecycle | stage duration, remaining inventory, audit result, cost basis | Explain repeatability and cleanup |

Proposed spans: submit job, persist job/outbox, publish event, receive event,
claim attempt, analyze document batch, write report and commit completion. Preserve
context across publication; use appropriate links for redelivery and asynchronous
relationships. Never infer queue delay from a gap in an unrelated trace alone.

Use stable Pyroscope service names with revision/environment labels. Start with
CPU, allocation and goroutine profiles. Trace-to-profile linking is an explicit
compatibility test using supported Go instrumentation; short spans may yield no
useful samples. Preserve aggregate deployment comparisons as a documented fallback.

### Dashboards and alerts

Create three focused provisioned dashboards: application outcomes, delivery/
reconciliation, and experiment comparison. Each query states its window and units.
Overlay deployment/config changes, link a representative trace to logs and profiles,
and display missing data clearly.

Initial alerts target stalled completion, excessive retry/error rate, sustained
queue age and stalled reconciliation. Define load-conditioned thresholds during
local calibration and freeze them before a recorded run. Alerting should have a
documented action and recovery condition. Short experiments support scenario-level
objectives; they cannot establish a production monthly availability SLO.

## Experiment protocol

Every scenario file declares ID/version, hypothesis, scope, prerequisites, fixture
hash, app/config digests, load settings, sampling, thresholds, maximum duration,
fault trigger, expected observation, recovery and cleanup assertions.

Warm up before measurement; hold fixture, resources and request schedule constant.
Capture generator throughput, rejected jobs and generator saturation. A closed-loop
client can hide overload, so record offered versus achieved load and outstanding
work. Compare repeat runs where practical; include raw count, elapsed window and
variation. Define accepted-to-completed latency using application job timestamps,
and verify clocks before comparing timestamps from different machines.

Capture the baseline, regressed and recovered revisions explicitly. Configure
sampling so the selected investigation is retained, recording any sampling bias.
Treat incomplete windows, missing signals or clock problems as inconclusive.

| ID | Scenario | Required evidence and pass condition |
| --- | --- | --- |
| EXP-01 | Normal job completion | Golden report hash, accepted/completed counts and a correlated request path |
| EXP-02 | Computation regression and rollback | Same input/output; increased work visible in profile and latency; Git recovery returns to predeclared tolerance |
| EXP-03 | Duplicate delivery/worker crash | Multiple attempts allowed; one selected successful result; no stranded job after recovery |
| EXP-04 | Kubernetes drift | Observed change corrected, or admission rejects it in prevention mode; source revision attributed |
| EXP-05 | Reconciliation failure | Invalid config or scoped permission fault blocks expected dependency; Git correction leads to readiness |
| EXP-06 | Telemetry pipeline outage | Workload independently observed; release/evidence gate does not report missing data as healthy |
| EXP-07 | Teardown failure | Controlled dependency/finalizer problem detected; repair plus independent scoped audit succeeds |
| EXP-08 | Profiling overhead | Matched profiled/unprofiled runs; measured overhead and uncertainty recorded |
| EXP-09 | Cloud Deploy delivery profile | Separate ownership, identical artifact promotion and documented rollback verification |
| EXP-10 | CAPI pivot | Ownership transfer and subsequent reconciliation verified; interrupted-pivot recovery documented |

EXP-01/02/03/08 start locally. EXP-04/05 run on both cloud platforms as appropriate.
AWS qualification includes EXP-07 before the full lifecycle is claimed complete.
EXP-09/10 are later milestones. Always distinguish an intentional expected fault
from an unexpected test failure; recovery and cleanup must still meet their gates.

## Evidence bundle contract

Versioned JSON Schema will be authored in the shared source repository. Proposed
major version 1 uses these logical groups:

| Group | Required information |
| --- | --- |
| `identity` | schema version, unique run ID, scenario/version, capture time |
| `source` | app/config/infrastructure commits, image digest, tool/controller versions |
| `environment` | provider, region, CPU architecture, resource sizing, isolation limits |
| `protocol` | fixture checksum, offered load, concurrency, warm-up/window, sampling and thresholds |
| `stages` | bootstrap, readiness, experiment, recovery, export, teardown and audit outcomes/times |
| `assertions` | named expectation, observed result, passed/failed/inconclusive and artifact reference |
| `measurements` | values with units, counts/windows and collection method |
| `artifacts` | relative path, media type, size, SHA-256 and provenance/source relation |
| `cost` | currency, estimate/actual status, time window, included/excluded services |
| `cleanup` | declared retained resources, audit coverage/results and remaining-resource categories |
| `limitations` | unavailable evidence, compatibility blockers and scope constraints |

Use null/unavailable with a reason when evidence is missing; never synthesize zero
latency, zero cost or success. Schema validation includes semantic checks: timestamp
ordering, required successful stages, valid artifact references and compatible
schema versions. Published examples are labeled fixtures and cannot receive a cloud
verified badge.

Keep separate axes for experiment outcome, evidence qualification and environment
lifecycle. A successfully completed historical experiment can have a dormant
environment; a successful application run can have failed cleanup. The UI must
show both outcomes instead of collapsing everything into one green status.

Cost actuals can arrive after initial publication. Keep original evidence immutable;
publish a linked addendum or new version with provenance to the initial run. A
mutable latest pointer is permitted only to point to validated immutable bundles.

### Export, privacy and publication

1. Capture private raw diagnostic evidence before cleanup, with defined retention.
2. Transform through an allowlist to public schemas; redact provider/account IDs,
   private hostnames, credentials and unnecessary user-specific information.
3. Preserve consistent replacement aliases where relationships need to remain visible.
4. Validate schema, file sizes/types, checksums and secret scans; inspect initial
   representative exports manually.
5. Complete cleanup/audit fields, validate qualification and publish immutable bundle.
6. Propose a portfolio manifest update pinning the bundle and checksum.

Reject unsafe paths, HTML/script payloads, external fetch instructions and unbounded
files. Portfolio ingestion is allowlisted to the lab's artifact sources. Validate
checksums and provenance at build time; an artifact does not become trusted merely
because a release URL is reachable. Render strings as text.

Select durable artifact storage during the implementation spike: versioned object
storage or a suitable retained release location. Record retention/cost and verify
anonymous retrieval of reviewed public files. Expiring CI logs are supplementary.
The portfolio build should include the small reviewed datasets it needs so ordinary
reading works independently of temporary cloud environments and remote backends.

## Portfolio integration

The user endorsed this integration direction on 2026-10-02. Labs is an interactive
record of engineering work, readable at three depths: a one-minute project story,
a five-minute guided investigation, and source/runbooks for reproduction.

### Catalogue and entry experience

Keep the existing Cloudflare experiments and add a prominent section titled
"Two clouds, two control-plane models". Introduce the shared Report Workshop
application once, then offer three connected entry points:

| Experience | Visitor's question | Lead evidence |
| --- | --- | --- |
| GCP Platform Delivery | How does a reviewed change become a working release? | Terraform foundation, Config Sync reconciliation, promotion and recovery |
| AWS Kubernetes Reconciliation | How does Git become AWS infrastructure, and why might it stall? | Dependency conditions, readiness timeline and teardown audit |
| Observability Investigation | Why did processing become slower, and how was it diagnosed? | Baseline/regression/recovery with metrics, trace, logs and profiles |

Cards show a brief finding only when measured, latest verified run date and
qualification (planned, locally verified or cloud verified). Display lifecycle
separately: "Cloud verified; environment shut down" is a valid state. A lack of
new runs does not invalidate historical evidence; show its age and tested versions.

Open each experience with the application outcome: a synthetic document batch,
recorded processing progress and its generated report. Label this as a replay of
a specific experiment, with date and revision. It is not a new live submission.
Keep operational controls out of the public preview.

### Guided investigation behavior

The baseline/regression/recovery selection coordinates the completion-latency and
backlog chart, selected trace, correlated log excerpts, profile comparison and
release timeline. Selecting a release highlights its actual measurement window and
associated revision. Selecting a trace/span opens only artifacts whose recorded
identities match; do not imply correlation just because timestamps are nearby.

Example walkthrough: select regressed release -> observe slower completion ->
inspect worker span -> read related log events -> compare the CPU hot path ->
inspect Git rollback -> verify the recovered window. Each step explains the
observation in plain language and links to its source/assertion. Missing spans or
profiles show an explicit unavailable state with the retained aggregate fallback.

For AWS, use the recorded dependency sequence: Git change -> Flux -> CAPA/ACK ->
resource readiness -> workload readiness -> teardown audit. Selecting a stalled
stage reveals the captured condition, blocked dependency, diagnostic explanation
and corrective Git change. Distinguish controller observations from our inference
about their cause. Include failure and cleanup outcomes even when app readiness
was successful.

Architecture diagrams are compact authored models with selectable components.
Selecting Config Sync explains its ownership, inputs and configuration source;
selecting the queue explains its application role and cloud adapter. Label diagrams
as models and link them to exact source revisions. The existing measured codebase
explorer remains a separate view of implementation structure.

### Integration and release sequence

The data path is lab run -> sanitized export -> validated versioned bundle ->
reviewed portfolio manifest update -> Astro build. The browser consumes normalized
reviewed evidence and links larger artifacts; it does not query private Grafana or
privileged cloud APIs. Pages work while both cloud environments are shut down.

Ship progressively:

1. Flagship cards, shared application introduction and authored architecture pages,
   all displaying their actual planned/implementation state.
2. One complete local regression investigation using real collected evidence,
   explicitly qualified as local.
3. GCP and AWS run timelines when their cloud experiments pass qualification.
4. Cross-cloud comparison once comparable evidence exists. Compare deployment,
   diagnosis, recovery, cost and teardown under recorded conditions; do not rank
   provider performance from unmatched workloads or infrastructure.

### Routes and presentation

Proposed routes, subject to the existing site's routing conventions:

- `/labs/`: existing catalogue with accurate qualification and last-run date.
- `/labs/gcp-delivery/`: GCP case study, ownership and experiment evidence.
- `/labs/aws-reconciliation/`: AWS case study, dependency state and lifecycle.
- `/labs/report-workshop/`: shared application and observability investigation.

Each case study offers a short explanation, one useful architecture diagram,
highlighted result with units and scope, guided investigation, and source/runbook
links. Maintain current English/German navigation and translation conventions.
Technical artifacts may remain English if the page labels that clearly.

The run explorer provides a baseline/regression/recovery selector, stage timeline,
selected metric window, accessible trace view, related log excerpts and profile
comparison. Give charts equivalent data tables, keyboard interaction, responsive
layouts and reduced-motion behavior. Provide a useful static default without JS.

Keep existing synthetic demos visibly labeled. New measured data replaces them only
after schema/qualification checks; historical examples can remain as teaching tools.
Use exact source links for application revision, configuration change and experiment
definition. A small video with transcript may supplement the evidence after a real
run, but cannot be its sole representation.

### Browser and content acceptance

Test planned/local/cloud-verified, dormant, failed cleanup, missing artifact,
incompatible schema and partial telemetry states. Exercise mobile widths, keyboard,
screen-reader labels, light/dark themes, no-JS and current bilingual reflow gates.
No public interaction starts paid cloud resources. Verify every displayed number
back to a bundle field; fabricated illustrative values stay in fixture-only tests.

## Case-study template

Each published experiment answers: What question? What changed? What did we observe?
Why do the signals support the explanation? How did recovery work? What remains
uncertain? How can a reviewer reproduce it? Link each claim to a source revision,
assertion and artifact. Avoid claims about production customer impact from a lab.
