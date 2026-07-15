# Shared packages

`packages/` contains versioned code shared by deployable applications. Packages are not deployed independently.

| Package | Purpose |
|---|---|
| `db` | PostgreSQL schema, migrations, roles, indexes, and database access |
| `contracts` | Versioned API request/response schemas and generated OpenAPI types |
| `query-tools` | Allowlisted, read-only farm query tools used by search and question answering |
| `auth` | Role and permission checks shared by API endpoints and jobs |
| `observability` | Trace propagation, redaction, latency, token, and cost measurements |

Database packages own persistence mechanics. Query packages own business-safe queries such as `count_farms`, `search_farms`, and `nearby_farms`. They must not expose arbitrary SQL to a language model.

The first implemented package is `db`. Other packages are added when their first real consumer is built; their documented boundaries are commitments, not empty scaffolding requirements.
