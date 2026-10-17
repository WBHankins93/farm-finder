# FarmFinder development guide

This guide covers local setup, verification, and the repository workflow. Data
collection and publication tasks have additional scope rules in the
[data guide](../data/README.md#workflow-router).

## On this page

- [Prerequisites](#prerequisites)
- [Local web setup](#local-web-setup)
- [Local database](#local-database)
- [Repository checks](#repository-checks)
- [Contribution workflow](#contribution-workflow)
- [Documentation changes](#documentation-changes)

<a id="prerequisites"></a>
## Prerequisites

- Node.js `>=22.13.0`
- Python 3
- Docker Desktop when working with PostgreSQL/PostGIS
- Access to the private repository

Commands below start at the repository root unless the section says otherwise.

<a id="local-web-setup"></a>
## Local web setup

```bash
cd 03-app/site
npm install
npm run data:setup
npm run data:validate
npm run dev
```

`npm run data:setup` creates an ignored `.venv` and installs the pinned Python
dependencies used by the data validators. The development server runs the
static-first directory against `app/data/farms.json`.

Common site commands:

| Command | Purpose |
|---|---|
| `npm run dev` | Start local development. |
| `npm run build` | Build the vinext application. |
| `npm run lint` | Run ESLint. |
| `npm test` | Build and run the rendered-site smoke tests. |
| `npm run data:validate` | Validate the pre-cutover application data release. |

For application-specific auth headers and runtime details, read the
[site README](../../03-app/site/README.md#current-shape).

<a id="local-database"></a>
## Local PostgreSQL/PostGIS

From `03-app/site/`:

```bash
npm run db:up
npm run db:verify
npm run db:test
```

The local database binds to `127.0.0.1:54329` by default. The integration suite
tests spatial queries and key integrity invariants inside a rolled-back
transaction.

Stop the database and preserve its volume:

```bash
npm run db:down
```

`npm run db:reset` deletes the local database volume. Use it only for an
intentional clean rebuild; it is not a routine troubleshooting step.

<a id="repository-checks"></a>
## Repository checks

Every pull request must pass these commands from the repository root:

```bash
python3 01-database/tools/assess_pr_scope.py
python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
```

If the change touches `03-app/site/`, also run from that directory:

```bash
npm run data:validate
npm run lint
npm test
```

Database changes should also run `npm run db:verify` and `npm run db:test` with
the local database running. A task-specific pipeline runbook may add checks; its
acceptance criteria are required in addition to this baseline.

<a id="contribution-workflow"></a>
## Contribution workflow

1. Read [AGENTS.md](../../AGENTS.md) and identify the exclusive scope and lane.
2. Branch from the latest `main` on the day the pull request is opened. Do not
   stack work on another unmerged branch.
3. Keep the change focused. Data-lane work owns one state, one adapter, or one
   region; tooling-lane work runs serially.
4. Preserve provenance, candidate retention, and privacy boundaries.
5. Run the repository baseline and any task-specific checks.
6. Open a pull request that explains the decision, verification, trade-offs,
   and rollback where relevant.

CI rejects more than 20 changed files or 15,000 additions unless the pull
request has the `large-reviewed-change` label.

When a release count changes, update every document that cites it in the same
pull request. Applied production schemas change through migrations, never by
editing prior migrations in place.

<a id="documentation-changes"></a>
## Documentation changes

- Keep the root README as an entry point, not a complete manual.
- Update the guide closest to the system being changed.
- Link to existing policy rather than restating it in multiple places.
- Add stable explicit anchors to sections that other pages should target.
- Verify relative links and anchor fragments before opening the pull request.
- Include documentation in the same change when behavior, commands, authority,
  or published counts change.

The [documentation hub](../README.md#documentation-conventions) lists the full
organization and writing conventions.
