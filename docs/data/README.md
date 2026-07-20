# FarmFinder data guide

Use this page to choose the correct data workflow. The pipeline's own README,
source schema, and handoff runbooks remain the detailed implementation
authorities.

## On this page

- [Workflow router](#workflow-router)
- [Authority boundaries](#authority-boundaries)
- [Run the pipeline](#run-the-pipeline)
- [State source configs](#state-source-configs)
- [Source adapters](#source-adapters)
- [Geocode backfill](#geocode-backfill)
- [QA and candidate retention](#qa-and-retention)
- [Publication and cutover](#publication-and-cutover)
- [Legacy state-release validation](#legacy-release-validation)

<a id="workflow-router"></a>
## Workflow router

| Change | Lane and scope | Owning instructions |
|---|---|---|
| Change pipeline engine, model, QA, privacy, or tests | Tooling lane; serial | [Pipeline README](../../01-database/pipeline/README.md) and [AGENTS.md](../../AGENTS.md) |
| Add or update one state source config | Data lane; one state | [Source config schema](../../01-database/pipeline/sources/SCHEMA.md#fields) |
| Add one source adapter | Data lane; one adapter | [Pipeline adapter handoff](../../01-database/pipeline/README.md) |
| Backfill coordinates | Data lane; one region | [Geocode runbook](../../01-database/pipeline/handoff/stream-c-geocode-backfill.md) |
| Wire a state to live sources | Data lane; one state | [Source wiring runbook](../../01-database/pipeline/handoff/stream-b-wire-sources.md) |
| Cut over publication or PostgreSQL | Tooling lane; gated | [Cutover runbook](../../03-app/site/docs/data-governance/cutover-runbook.md#remaining-promotion-gates) |

Never combine states or cross tooling and data lanes in one session. Before a
data-lane change, confirm that no tooling-lane change is in flight and claim the
exclusive state, adapter, or region scope.

<a id="authority-boundaries"></a>
## Authority boundaries

During the transition:

1. `01-database/pipeline/` owns the engine, canonical model, and pipeline rules.
2. `research/state-expansions/<ST>/` is read-only staged input until cutover.
3. `03-app/site/app/data/farms.json` is the canonical pre-cutover application
   data.
4. `01-database/pipeline/sources/<region>/<ST>.json` owns each state's source
   definitions.
5. `01-database/pipeline/build/` is reproducible output and is never committed.

The older contract-v2 validator remains only to keep existing staged releases
intact during the transition. Do not extend legacy governance when the same rule
belongs in the pipeline model, QA engine, source config, or privacy gate.

<a id="run-the-pipeline"></a>
## Run the pipeline

Run commands from the repository root:

```bash
# Collect one configured state into the pipeline's canonical state store.
python3 01-database/pipeline/run.py --state KY

# Collect every state with a source config.
python3 01-database/pipeline/run.py --all

# Build the aggregate app artifact under the ignored build directory.
python3 01-database/pipeline/run.py --publish

# Run the pipeline test suite.
python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
```

`run.py --publish` writes a build artifact; it does not update the application's
canonical `farms.json` or promote data into PostgreSQL. See the
[pipeline output contract](../../01-database/pipeline/README.md#run).

<a id="state-source-configs"></a>
## State source configs

A state is a JSON config, not a collector. Work on exactly one file under
`01-database/pipeline/sources/<region>/<ST>.json` and validate it against the
[source config schema](../../01-database/pipeline/sources/SCHEMA.md#fields).

For an existing staged state:

1. Read its source list under `research/state-expansions/<ST>/state.yaml`.
2. Verify each source's adapter assignment in the state config.
3. Replace the transitional `staged` source only when live adapters cover its
   records.
4. Run the pipeline tests and the runbook-specific acceptance checks.

For exact scope, branch, and evidence requirements, use the
[state source-wiring runbook](../../01-database/pipeline/handoff/stream-b-wire-sources.md).

<a id="source-adapters"></a>
## Source adapters

An adapter implements one source type for every state that uses it. Keep one
adapter change isolated from state config and engine changes, and follow the
owning workstream's exact file scope and acceptance checks.

Adapters receive a source definition and collection context, then emit raw
canonical `Farm` objects. The engine owns cleansing, geography fallback, QA,
privacy, and publication. Start with the adapter template in
[`adapters/__init__.py`](../../01-database/pipeline/adapters/__init__.py) and the
[adapter workstream](../../01-database/pipeline/README.md).

<a id="geocode-backfill"></a>
## Geocode backfill

Geocode work is scoped to one region. It fills coordinates that remain missing
after the in-repository county-centroid fallback, then lets the automated QA
rule clear records whose only blocker was geography.

Follow the [geocode backfill runbook](../../01-database/pipeline/handoff/stream-c-geocode-backfill.md)
exactly. It defines the editable files, input/output contract, coordinate source,
privacy handling, and acceptance checks.

<a id="qa-and-retention"></a>
## QA and candidate retention

QA is automation-first. Humans review only `build/qa-residue.csv` after the
rules in `pipeline/qa.py` have handled deterministic cases.

- Missing information creates a `qa_reason`; it does not erase a named candidate.
- Deletion requires cited evidence of a non-farm, closure, out-of-jurisdiction
  identity, or duplicate identity.
- Exact private locations and contact details remain internal until
  `pipeline/privacy.py` clears them for public use.
- Eligible does not mean verified, approved, or published.

<a id="publication-and-cutover"></a>
## Publication and cutover

There are two distinct publication actions:

1. `run.py --publish` creates the reproducible aggregate artifact in
   `01-database/pipeline/build/`.
2. Cutover deliberately replaces the app artifact and later promotes an
   approved release into PostgreSQL/PostGIS.

Do not copy build output into `03-app/site/app/data/farms.json`, alter the
source-of-truth manifest, or load PostgreSQL as a side effect of ordinary
collection work. Those are gated tooling-lane changes. Follow the
[PostgreSQL cutover runbook](../../03-app/site/docs/data-governance/cutover-runbook.md#local-execution)
and reconcile counts, provenance, privacy, tests, and rollback before promotion.

<a id="legacy-release-validation"></a>
## Legacy state-release validation

Existing staged state releases remain protected until cutover. Run from the
repository root:

```bash
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
```

These checks preserve the staged four-file releases; they do not make the
legacy contract the architecture for new pipeline work.

Return to the [documentation hub](../README.md#documentation-by-task).
