# Annotated reference catalogue

Purpose: preserve the examples behind the shared demo application, GCP delivery
lab, AWS reconciliation lab and portfolio Labs presentation. Parent:
[strategy and specifications](../portfolio-demo-strategy-2026-10-02.md).

Research date: 2026-10-02. These are selected primary sources: project maintainers,
official documentation and engineers describing their own portfolios. Inclusion
means a useful reference for a named purpose, not certification of its security,
production readiness or measured outcomes. No third-party lab was executed here.

Review depth:

- **Reviewed**: substantive README, documentation or case-study content inspected.
- **Located**: relevant project/document and entry point inspected; deeper source
  review remains implementation work.
- **Follow-up**: recorded from a relevant source; detailed verification still needed.

Priorities are our assessment of relevance. Prefer a few directly applicable
examples per implementation decision over combining every stack in this list.

## Recommended starting set

1. KROPS for AWS controller composition and lifecycle.
2. Google Config Sync architecture and ACM samples for GCP configuration ownership.
3. Podinfo for a small well-instrumented Go service's operational behavior.
4. OpenTelemetry Demo for fault/investigation scenarios.
5. Flux's multi-environment example for repository/reconciliation organization.
6. Pyroscope span-profile documentation for the trace/profile compatibility test.
7. Dan Hughes for the separation of experiments and engineering notes.
8. Outsight for claim-to-source mapping and reproducible case-study presentation.

## Precedent and the proposed combination

The user asked whether others have built this kind of portfolio integration.
The researched answer is yes for the constituent patterns, with several examples
combining more than one. This table records the basis for that answer:

| Existing pattern | Reference | What our plan takes from it |
| --- | --- | --- |
| Interactive engineering experiments alongside notes and public source | P01, Dan Hughes | Separate short explanations, exploration and implementation detail |
| Public platform observations through a restricted telemetry interface | P04, Sean Johnson | An understandable view into platform behavior with private backends |
| Delivery, telemetry release gates, recovery and claim-to-source evidence | P02, Outsight | A reproducible operational story with verification instructions |
| Instrumented distributed application and controlled diagnostic scenarios | A02–A04, OpenTelemetry Demo | Guided exploration of related signals around a deliberate fault |
| GitOps-driven cloud resource and cluster lifecycles | K01, KROPS | Controller composition, dependency diagnosis and lifecycle ownership |

Within the examples reviewed, we did not identify the exact proposed combination:
one shared application on GCP and AWS, deliberately different control-plane models,
and a portfolio explorer retaining deployment, diagnosis, recovery and teardown
evidence after the environments are shut down. This is a bounded research finding,
not a claim of invention, uniqueness or an exhaustive survey of public portfolios.

Our intended contribution is the coherent connection between those established
patterns: a reviewer follows a Git change through operational consequences to a
supported engineering decision, then can reproduce the experiment. Evaluate the
result by clarity, reproducibility and trustworthy evidence, not novelty claims.
The concrete interaction contract is in
[Evidence and Labs](evidence-and-labs.md#portfolio-integration).

## Portfolio and presentation exemplars

### P01 — Dan Hughes engineering portfolio

- Source: <https://github.com/danielshughes/portfolio>
- Depth: Reviewed README and repository structure; earlier local portfolio audit
  also exists at ../portfolio-reference-audit-2026-09-30.md.
- Use: separate personal homepage, notes and experiments; local credential-free
  operation; explicit behavior when a feature needs deployed provider access.
- Apply to: Labs information architecture, truthful data states and runbooks.
- Caveat: do not inherit its optional Cloudflare services without a specific need.
  GitHub identified no repository license in the metadata check; treat as design
  inspiration and independently author our code unless reuse permission is established.

### P02 — Outsight multi-tenant GitOps lab

- Case study: <https://syedtashfin.vercel.app/case-studies/cicd-gitops-multitenant-kubernetes-saas>
- Source: <https://github.com/SyedTashfin/Outsight-MultiTenant-GitOps-Lab>
- Linked CI example: <https://github.com/SyedTashfin/Outsight-MultiTenant-GitOps-Lab/actions/runs/22077433770>
- Depth: Reviewed case study and linked repository/CI entry points.
- Use: explanation of promotion, operational verification commands, explicit
  limitations and evidence map connecting claims to repository paths.
- Apply to: each cloud case study and the portfolio's short guided investigation.
- Caveat: its documented no-traffic-as-zero gate and direct Helm recovery are
  useful critique points. Our gates need missing-data handling and normal Git-based
  recovery. A linked CI page is not independent verification of a cloud run.
  GitHub license metadata was unidentified; do not presume permission to copy code.

### P03 — Dattaram Miruke EKS build story

- Source: <https://dmiruke-ai.github.io/platform-engineering-lab-public/blog-cluster-build-story.html>
- Depth: Reviewed build-story sections and documentation structure.
- Use: cold bring-up, ordering bugs, identity problems and failed destruction
  documented as engineering work, with deeper reference material linked separately.
- Apply to: AWS lifecycle field notes and short end-to-end implementation slices.
- Caveat: do not adopt its full stack or published spend figures as our sizing or
  budget assumptions. Its account/networking choices differ from our bounded lab.

### P04 — Sean Johnson platform portfolio

- Source: <https://s34nj0hn.dev/>
- Depth: Reviewed public page text and architecture explanation; live dynamic
  telemetry health was not verified.
- Use: aggregate public platform observations through a narrow Worker interface.
- Apply to: public-safe evidence presentation and clear backend trust boundaries.
- Caveat: historical bundles suit our dormant cloud environments better than a
  permanently running cluster heartbeat. Preserve time/availability distinctions.

### P05 — T-Py-T Kubernetes GitOps homelab

- Source: <https://github.com/T-Py-T/kubernetes-gitops-homelab>
- Depth: Reviewed README ownership layers and public/private boundary.
- Use: readable layer responsibilities, reconciliation order and recovery framing.
- Apply to: architecture documentation and protection of unrelated private estate.
- Caveat: our synthetic demo should be reproducible from public inputs; a private
  downstream configuration requirement would weaken that goal.

### P06 — Stackcouture GKE portfolio

- Source: <https://github.com/stackcouture/cloud-native-gke>
- Depth: Reviewed published README/capability presentation.
- Use: small recognizable workload, visible delivery demonstrations and separate
  infrastructure/application/operations responsibilities.
- Apply to: scoping and reviewer orientation.
- Caveat: tool counts and broad capability lists are not measured outcomes. The
  Argo CD design is not our Config Sync requirement. Verify any claimed behavior
  in source before treating it as an implementation example.

### P07 — Janus Chung platform engineering portfolio

- Source: <https://januschung.github.io/>
- Depth: Located portfolio and engineering article index.
- Use: readable technical notes and runbooks alongside project work.
- Apply to: publication cadence and linking a concise project to deeper learning.
- Caveat: individual articles remain follow-up reading; do not infer cloud cost or
  reproducibility from the homepage's summary claims.

## Application and observability examples

| ID | Source | Depth | What to study | Application and limits |
| --- | --- | --- | --- | --- |
| A01 | [Podinfo](https://github.com/stefanprodan/podinfo) | Reviewed README/API catalogue | Go service health, shutdown, instrumentation, bounded failure tooling, image release practices | Operational behavior reference for Report Workshop; do not expose diagnostic env/config/fault endpoints publicly |
| A02 | [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo) and [docs](https://opentelemetry.io/docs/demo/) | Reviewed docs; repository metadata checked | Correlated telemetry and understandable distributed application | Learn conventions; full polyglot stack is an alternative workload, not a required dependency |
| A03 | [OTel Demo architecture](https://opentelemetry.io/docs/demo/requirements/architecture/) | Reviewed | Application and failure-flag design | Shape explicit scenarios with observable outcomes |
| A04 | [OTel feature flags/scenarios](https://opentelemetry.io/docs/demo/feature-flags/) | Located | Reproducible faults and investigation entry points | Select a narrow analogous scenario; keep our faults operator-controlled |
| A05 | [AWS Retail Store](https://github.com/aws-containers/retail-store-sample-app) | Reviewed README | Existing UI, provider backends, metrics/tracing and load generation | Strong existing-app alternative if speed matters more than controlled Go authorship |
| A06 | [Google Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) | Located README/project | Understandable multi-service application and load generator | Compare workload/presentation choices; its broad service set exceeds initial scope |
| A07 | [Bank of Anthos](https://github.com/GoogleCloudPlatform/bank-of-anthos) | Located README/project | Business workflow and stateful service demonstration | Reference for visible outcomes/state; banking domain and service breadth are unnecessary here |
| A08 | [Grafana Docker OTel LGTM](https://github.com/grafana/docker-otel-lgtm) | Located README/project | Compact local telemetry backend | Candidate developer harness; verify included components/version and add profiling separately where needed |
| A09 | [Pyroscope span profiles](https://grafana.com/docs/pyroscope/latest/configure-client/trace-span-profiles/) | Reviewed entry documentation | Supported trace/profile correlation | Must test Go compatibility and sampling; do not promise useful profiles for every span |
| A10 | [Tempo setup](https://grafana.com/docs/tempo/latest/set-up-for-tracing/) | Follow-up from TAL-81 | Trace ingestion/backend setup | Verify exact pinned version's configuration during OBS-01 |
| A11 | [Collector to Tempo](https://grafana.com/docs/tempo/latest/set-up-for-tracing/instrument-send/set-up-collector/otel-collector/) | Follow-up from TAL-81 | Collector export configuration | Use as protocol guidance, qualify runtime configuration locally |
| A12 | [Grafana trace-to-profile configuration](https://grafana.com/docs/grafana/latest/datasources/pyroscope/configure-traces-to-profiles/) | Follow-up from TAL-81 | Data-source correlation settings | Test navigation using our retained revision/trace metadata |
| A13 | [Google SRE Workbook](https://sre.google/workbook/table-of-contents/) | Located contents | SLOs, monitoring, alerting and incident practice | Select chapters while defining experiment objectives; a short lab run cannot prove monthly reliability |

The attempted deep link to Pyroscope's golang-push example did not return usable
content during this review. Use A09 as the authoritative entry point and locate
the current SDK examples during the compatibility spike rather than copying an
unverified old path.

## GCP and configuration-management references

| ID | Source | Depth | What to study | Application and limits |
| --- | --- | --- | --- | --- |
| G01 | [Config Sync architecture](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/concepts/architecture) | Reviewed | RootSync/RepoSync, reconciliation, fleet-managed fields | Authoritative ownership model for platform/app configuration |
| G02 | [Config Sync overview](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/overview) | Reviewed | Configuration sources and reconciliation purpose | Explain ACM lineage and concrete Config Sync capability without confusing it with Config Connector |
| G03 | [ACM samples](https://github.com/GoogleCloudPlatform/anthos-config-management-samples) | Located repository and linked examples | Official configuration patterns | Inspect selected sample at a pinned commit before adaptation |
| G04 | [Multi-environment Config Sync](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/tutorials/multiple-environments-config-sync) | Reviewed tutorial entry | Kustomize environment structure and automated rendering | Apply to dev/staging overlays; preserve actual isolation limitations |
| G05 | [Multi-repository quickstart](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/tutorials/config-sync-multi-repo) | Located | Namespace delegation and root/app split | Test least privilege, not merely successful synchronization |
| G06 | [Terraform GKE modules](https://github.com/terraform-google-modules/terraform-google-kubernetes-engine) | Reviewed README | Cluster module structure and documented requirements | Pin compatible versions and minimize granted permissions |
| G07 | [Terraform example foundation](https://github.com/terraform-google-modules/terraform-example-foundation) | Located | Staged foundation composition and ownership | Learn boundaries; full enterprise organization scaffolding is too broad for our first lab |
| G08 | [Config Sync installation](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/how-to/installing-config-sync) | Reviewed relevant configuration guidance | Supported bootstrap/source configuration | Use current fleet/API semantics; historical ACM Terraform blog examples need revalidation |
| G09 | [Managing Config Sync objects](https://docs.cloud.google.com/kubernetes-engine/config-sync/docs/how-to/managing-objects) | Reviewed relevant ownership text | Ownership markers and managed-field behavior | Support overlap checks and drift experiment interpretation |

Cloud Deploy's exact pipeline/verification implementation requires a dedicated
official-documentation review in ADV-01. The current plan defines its ownership
boundary but does not imply an unverified Config Sync/Cloud Deploy integration.

## AWS, GitOps and lifecycle references

| ID | Source | Depth | What to study | Application and limits |
| --- | --- | --- | --- | --- |
| K01 | [KROPS](https://github.com/polarsquad/krops) | Reviewed README and documented structure | Flux, CAPI/CAPA, ACK, management/workload split, bootstrap/pivot/teardown | Primary architectural inspiration; independent implementation with one temporary workload cluster by default |
| K02 | [KROPS AWS guide](https://github.com/polarsquad/krops/blob/main/docs/aws.md) | Follow-up; web retrieval failed | Current AWS lifecycle and constraints | Read via pinned Git source before implementation; do not assume README alone qualifies operations |
| K03 | [KROPS IAM guide](https://github.com/polarsquad/krops/blob/main/docs/aws-iam.md) | Located/search extract | Controller identity and privilege tradeoffs | Upstream content changes; inspect current source and design our own bounded credential path |
| K04 | [CAPA book](https://cluster-api-aws.sigs.k8s.io/) | Reviewed overview/navigation | EKS support, identities, compatibility and garbage collection | Version-specific authority for selected APIs; run our own lifecycle tests |
| K05 | [ACK overview](https://aws-controllers-k8s.github.io/community/docs/community/overview/) | Located | Service-controller model | Follow through to selected S3/SQS controller API/release docs before pinning |
| K06 | [Flux multi-environment example](https://github.com/fluxcd/flux2-kustomize-helm-example) | Located README/project | Apps, infrastructure and environment layering | Strong source for repo shape; adapt dependency/readiness gates to CAPA/ACK |
| K07 | [OpenGitOps principles](https://opengitops.dev/) | Reviewed principles entry | Declarative, versioned, pulled and reconciled desired state | Describe full GitOps accurately; Terraform plan/apply remains a separate execution model |

Older TAL-81 material names `polarsquad/knr-ops`; the current user-provided reference
is `polarsquad/krops`. Record that lineage, but pin the actual KROPS source used.
Do not assume old search-index IAM/controller placement descriptions match current
main. CAPI move/pivot details require selected-version official documentation in ADV-02.

## Build tooling reference

- [Original Google Kaniko](https://github.com/GoogleContainerTools/kaniko): reviewed
  archive notice; this is why the proposed baseline uses BuildKit instead of the
  historical brief's original Kaniko option.
- [Maintained Kaniko fork](https://github.com/osscontainertools/kaniko): located
  maintenance statement; possible alternative only after an actual requirement
  and supply-chain review, not selected for this project.

## Repository license metadata snapshot

GitHub API metadata checked 2026-10-02. This is discovery metadata, not a complete
license audit. Review LICENSE/NOTICE, file-specific terms, bundled assets and
dependencies at the exact commit before copying implementation. All repositories
below reported archived=false at that check.

| Repository | Reported license |
| --- | --- |
| polarsquad/krops | Apache-2.0 |
| danielshughes/portfolio | Unidentified |
| stefanprodan/podinfo | Apache-2.0 |
| fluxcd/flux2-kustomize-helm-example | Apache-2.0 |
| GoogleCloudPlatform/anthos-config-management-samples | Apache-2.0 |
| terraform-google-modules/terraform-google-kubernetes-engine | Apache-2.0 |
| terraform-google-modules/terraform-example-foundation | Apache-2.0 |
| open-telemetry/opentelemetry-demo | Apache-2.0 |
| aws-containers/retail-store-sample-app | MIT-0 |
| GoogleCloudPlatform/microservices-demo | Apache-2.0 |
| GoogleCloudPlatform/bank-of-anthos | Apache-2.0 |
| grafana/docker-otel-lgtm | Apache-2.0 |
| SyedTashfin/Outsight-MultiTenant-GitOps-Lab | Unidentified |
| T-Py-T/kubernetes-gitops-homelab | MIT |
| stackcouture/cloud-native-gke | MIT |

## Reuse and maintenance ledger

For every selected implementation example, record: reference ID/URL, exact commit
or documentation version, date inspected, relevant paths, what was learned, what
was copied/adapted (if anything), license/notice requirements, local owner and
verification performed. Put attribution in the consuming repo's THIRD_PARTY_NOTICES
and relevant ADR, not only in this catalogue. Preserve original attribution for
third-party code embedded inside an example.

Do not copy personal portfolio prose, artwork, private identifiers or unlicensed
source. Use ideas to author our own explanation. No third-party implementation has
been copied into the lab repos by this planning task.

This catalogue intentionally leaves version pins open until implementation review;
it is a research map, not a dependency lockfile. Recheck official version-specific
docs when adopting a component. Record concrete compatibility findings back into
the relevant repo and retain the reference link here.
