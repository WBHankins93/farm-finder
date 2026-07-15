# Deployable applications

`apps/` is for independently deployable processes. It is not limited to user interfaces.

| App | Responsibility | May access PostgreSQL? | Publicly reachable? |
|---|---|---:|---:|
| `web` | Consumer and farmer UI, server rendering, accessibility, maps | Through the API only | Yes |
| `api` | REST boundary, authentication, authorization, validated query tools | Yes | Yes |
| `worker` | Imports, geocoding, deduplication, retries, document processing | Yes | No |

The current web application remains at the repository root during the foundation phase. It will move to `apps/web` only after the workspace and deployment configuration can be changed in one verified migration. The API and worker should begin as modules in one TypeScript codebase and deploy separately only when their runtime needs differ.

## Boundary rules

- The browser never receives database credentials and never queries PostgreSQL directly.
- The web app calls versioned API contracts from `packages/contracts`.
- Only the API handles public requests and authorization decisions.
- Only the worker performs imports, bulk geocoding, deduplication, embedding generation, and retryable background work.
- Neither the API nor worker may invent a new canonical farm without preserving its source record and dataset release.
