# Infrastructure

`infra/` owns reproducible runtime dependencies and deployment configuration. The implemented local slice contains PostgreSQL/PostGIS plus a loopback-only S3-compatible object store for immutable source-release testing.

## Local cutover infrastructure

```bash
cp infra/.env.example infra/.env
npm run infra:up
npm run db:verify
npm run cutover:stage
npm run cutover:verify
npm run infra:down
```

PostgreSQL binds to `127.0.0.1:54329`; object storage and its console bind to `127.0.0.1:9000` and `127.0.0.1:9001`. Credentials in `.env.example` are local placeholders only. The local object store has versioning enabled by the importer and proves the provider-neutral S3 contract; it is not a production backup.

`npm run db:reset` deletes only the local PostgreSQL volume and preserves the versioned object-storage volume. It must never be pointed at a shared environment. `docker compose -f infra/compose.yaml down -v` would delete both volumes and should be used only when their deliberate destruction is intended.

Container initialization is only a local bootstrap mechanism. Production migrations will run as a distinct release step with a migration identity, advisory lock, timeout, and recorded migration history.

## Production infrastructure contract

| Component | Responsibility | Initial decision |
|---|---|---|
| Managed PostgreSQL | Canonical data, PostGIS, full text, jobs, outbox | Required; automated backups and point-in-time recovery |
| Object storage | Immutable source releases and future media | Local S3-compatible workflow implemented; managed provider still to be selected, with versioning, checksum, lifecycle, and signed access required |
| Web runtime | Public UI and cached rendering | Existing deployment retained during migration |
| API runtime | REST, auth, authorization, query tools | TypeScript; private DB credentials |
| Worker runtime | Imports, geocoding, dedupe, document/media processing | TypeScript worker plus bounded Python ingestion tasks |
| Secrets | Database, OIDC, object storage, model credentials | Managed secret store; never build-time public variables |
| Telemetry | Traces, logs, metrics, token and cost accounting | OpenTelemetry-compatible backend; vendor deferred |
| CI/CD | Test, migrate, deploy staging, smoke, promote | Provider deferred until repository boundary is resolved |
| IaC | Environments, roles, storage, network, telemetry, backups | OpenTofu/Terraform or provider-native equivalent after hosting decision |

## Network and role expectations

- PostgreSQL is not public. API and worker reach it over a private or tightly allowlisted connection.
- The migration identity owns schema changes but is not used by the application.
- The public query path uses a read-only role or transaction mode where possible.
- API and worker identities receive only the table operations required by their workflows.
- Object-storage uploads use short-lived signed operations and quarantine unprocessed files.
- Logs and traces redact private contacts, exact non-public coordinates, authorization headers, and model credentials.

## Backup and recovery gates

- Automated database backups plus point-in-time recovery are enabled.
- Object versioning is enabled for governed source releases and original media.
- A restore into staging is tested before production launch and periodically afterward.
- Recovery-point and recovery-time objectives are written from real product needs before the pilot.

A telemetry collector and separate message broker remain intentionally absent. Add them when their first executable workflow requires them.

See the [cutover runbook](../docs/data-governance/cutover-runbook.md) for release staging, verification, Mississippi collection isolation, and promotion gates.
