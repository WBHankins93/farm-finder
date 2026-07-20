# FarmFinder documentation

This directory is the project-level map for FarmFinder documentation. Detailed
instructions stay beside the code or data they govern; these pages connect them
without creating a second source of truth.

## On this page

- [Sources of truth](#sources-of-truth)
- [Documentation by task](#documentation-by-task)
- [Documentation by system](#documentation-by-system)
- [Historical and transitional material](#transitional-material)
- [Documentation conventions](#documentation-conventions)

<a id="sources-of-truth"></a>
## Sources of truth

When two documents disagree, use this authority order:

| Authority | Location | Validation |
|---|---|---|
| Pipeline engine, model, and rules | [`01-database/pipeline/`](../01-database/pipeline/README.md#layout) | Pipeline unit tests |
| Staged farm data until cutover | [`research/state-expansions/<ST>/`](../research/state-expansions/README.md) | State-release validator |
| Canonical pre-cutover app data | [`farms.json`](../03-app/site/app/data/farms.json) | `npm run data:validate` |
| Per-state source definitions | [`pipeline/sources/`](../01-database/pipeline/sources/SCHEMA.md#fields) | Source config schema |
| Product and platform documentation | Root README and [`03-app/site/docs/`](../03-app/site/docs/architecture/README.md) | Maintainer review |

Repository-wide working rules live in [AGENTS.md](../AGENTS.md). That file takes
priority for scope, branch discipline, privacy, deletions, and required checks.

<a id="documentation-by-task"></a>
## Documentation by task

### Build and verify locally

- [Install and run the web application](development/README.md#local-web-setup)
- [Start PostgreSQL/PostGIS](development/README.md#local-database)
- [Run repository and application checks](development/README.md#repository-checks)
- [Prepare a focused pull request](development/README.md#contribution-workflow)

### Work with farm data

- [Choose the correct data workflow](data/README.md#workflow-router)
- [Run the config-driven pipeline](data/README.md#run-the-pipeline)
- [Author a state source config](data/README.md#state-source-configs)
- [Implement a source adapter](data/README.md#source-adapters)
- [Backfill geocodes](data/README.md#geocode-backfill)
- [Understand publishing and cutover](data/README.md#publication-and-cutover)

### Work on the product

- [Review the phased build plan](../03-app/site/docs/product/phased-build-plan.md#phase-map)
- [Understand the web layout scope](../03-app/site/docs/design/web-layout-scope.md#website-information-architecture)
- [Use the web design system](../03-app/site/docs/design/web-design-system.md#tokens)
- [Review mobile architecture](../03-app/site/docs/mobile/mobile-architecture-and-wireframes.md#recommendation)

<a id="documentation-by-system"></a>
## Documentation by system

### Project architecture

- [Current and target system shape](architecture/README.md#system-shape)
- [Data lifecycle](architecture/README.md#data-lifecycle)
- [Query and answer paths](architecture/README.md#query-architecture)
- [Security and privacy boundaries](architecture/README.md#security-and-privacy)

### Data platform

- [Pipeline engine](../01-database/pipeline/README.md)
- [Pipeline handoff runbooks](../01-database/pipeline/handoff/README.md#runbooks)
- [Source config schema](../01-database/pipeline/sources/SCHEMA.md#fields)
- [Canonical farm model](../01-database/pipeline/model.py)
- [Pipeline enrichment plan](../01-database/pipeline-enrichment-plan.md#sequencing)

### Web and production platform

- [Web application guide](../03-app/site/README.md#quick-start)
- [Production architecture](../03-app/site/docs/architecture/README.md#responsibilities)
- [Architecture decisions](../03-app/site/docs/architecture/decisions/0001-platform-foundation.md#decision)
- [PostgreSQL index register](../03-app/site/docs/architecture/index-register.md#review-procedure)
- [Infrastructure contract](../03-app/site/infra/README.md)
- [Evaluation strategy](../03-app/site/evals/README.md)
- [Implementation ledger](../03-app/site/docs/implementation-ledger.md)

### Product, research, and outreach

- [App vision](../03-app/app-vision.md)
- [Phased build plan](../03-app/site/docs/product/phased-build-plan.md#phase-map)
- [Market opportunity brief](../research/market-opportunity-brief.md)
- [Research inventory](../research/README.md)
- [Outreach plan](../02-outreach/outreach-plan.md)

### Data governance

- [Source-of-truth workflow](../03-app/site/docs/data-governance/source-of-truth.md#authority-modes)
- [PostgreSQL cutover runbook](../03-app/site/docs/data-governance/cutover-runbook.md#local-execution)
- [State expansion and verification](../01-database/state-expansion-and-verification.md#scope)
- [State release contract](../01-database/state-release-contract.md#purpose)

<a id="transitional-material"></a>
## Historical and transitional material

The config-driven pipeline is the current engine. The older contract-v2 tools
and state-expansion documents remain only to validate existing staged releases
until PostgreSQL cutover. Historical dashboards, workbooks, `outputs/`, and
`.codex-work/` are reference material, not editable authorities.

If a transitional document conflicts with `01-database/pipeline/`, follow the
pipeline. If it conflicts with [AGENTS.md](../AGENTS.md), follow `AGENTS.md`.

<a id="documentation-conventions"></a>
## Documentation conventions

- Keep the root README short: explain the product, show first success, and route
  readers to the owning guide.
- Put instructions beside the system they operate whenever possible.
- Link to a canonical explanation instead of copying it.
- Add a short table of contents to long pages.
- Give important sections an explicit, stable HTML anchor such as
  `<a id="publication-and-cutover"></a>` and link directly to that anchor.
- When a published count changes, update every document that cites it in the
  same pull request.
- Include the command, working directory, expected effect, and destructive or
  privacy implications in operational instructions.

Return to the [project README](../README.md#documentation).
