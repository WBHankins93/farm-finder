# FarmFinder web and platform foundation

The public FarmFinder directory runs on [vinext](https://github.com/cloudflare/vinext). The production foundation adds a governed dataset release, PostgreSQL/PostGIS migrations, documented indexes, database integration tests, architecture decisions, and local infrastructure without changing the static-first public release.

## Prerequisites

- Node.js `>=22.13.0`
- Python 3 with the pinned dependencies installed by `npm run data:setup`
- Docker Desktop for the local PostgreSQL/PostGIS stack

## Quick Start

```bash
npm install
npm run data:setup
npm run data:validate
npm run dev
```

This starter does not use `wrangler.jsonc`.

## Current shape

- edit site code under `app/`
- `app/data/farms.json` is the current 299-listing public build artifact
- `config/source-of-truth.json` pins the pre-cutover canonical workbook release
- `packages/db/` owns the production PostgreSQL/PostGIS migrations and index decisions
- `infra/` owns reproducible local dependencies and the production infrastructure contract
- `docs/` records architecture, data governance, and implementation state
- `evals/` contains versioned question-answering and safety expectations
- `vite.config.ts` simulates declared bindings for local development

`db/schema.ts`, `db/index.ts`, and the D1 example remain from the hosting starter and are not the production database source. They will be removed or replaced when the API is connected to PostgreSQL in one verified change.

## Workspace Auth Headers

OpenAI workspace sites can read the current user's email from
`oai-authenticated-user-email`.

SIWC-authenticated workspace sites may also receive
`oai-authenticated-user-full-name` when the user's SIWC profile has a non-empty
`name` claim. The full-name value is percent-encoded UTF-8 and is accompanied by
`oai-authenticated-user-full-name-encoding: percent-encoded-utf-8`.

Treat the full name as optional and fall back to email when it is absent:

```tsx
import { headers } from "next/headers";

export default async function Home() {
  const requestHeaders = await headers();
  const email = requestHeaders.get("oai-authenticated-user-email");
  const encodedFullName = requestHeaders.get("oai-authenticated-user-full-name");
  const fullName =
    encodedFullName &&
    requestHeaders.get("oai-authenticated-user-full-name-encoding") ===
      "percent-encoded-utf-8"
      ? decodeURIComponent(encodedFullName)
      : null;

  const displayName = fullName ?? email;
  // ...
}
```

## Optional Dispatch-Owned ChatGPT Sign-In

Import the ready-to-use helpers from `app/chatgpt-auth.ts` when the site needs
optional or required ChatGPT sign-in:

- Use `getChatGPTUser()` for optional signed-in UI.
- Use `requireChatGPTUser(returnTo)` for server-rendered pages that should send
  anonymous visitors through Sign in with ChatGPT.
- Use `chatGPTSignInPath(returnTo)` and `chatGPTSignOutPath(returnTo)` for
  browser links or actions.
- Pass a same-origin relative `returnTo` path for the destination after sign-in
  or sign-out. The helper validates and safely encodes it.
- Mark protected pages with `export const dynamic = "force-dynamic"` because
  they depend on per-request identity headers.

Dispatch owns `/signin-with-chatgpt`, `/signout-with-chatgpt`, `/callback`, the
OAuth cookies, and identity header injection. Do not implement app routes for
those reserved paths. Routes that do not import and call the helper remain
anonymous-compatible.

SIWC establishes identity only; it does not prove workspace membership. Use the
Sites hosting platform's access policy controls for workspace-wide restrictions,
or enforce explicit server-side membership or allowlist checks.

Use SIWC for account pages, user-specific dashboards, saved records, and write
actions tied to the current ChatGPT user. Leave public content anonymous.

## Useful Commands

- `npm run dev`: start local development
- `npm run build`: verify the vinext build output
- `npm test`: build and verify the rendered FarmFinder shell and 299-record artifact
- `npm run lint`: run the application linter
- `npm run data:setup`: create the ignored Python environment for workbook tooling
- `npm run data:validate`: validate the canonical workbook release manifest
- `npm run db:up`: start a healthy local PostgreSQL/PostGIS database
- `npm run db:verify`: verify required extensions, tables, and documented indexes
- `npm run db:test`: exercise spatial and integrity invariants in a rolled-back transaction
- `npm run db:down`: stop local infrastructure while preserving its volume
- `npm run db:reset`: delete the local database volume; local development only

## Learn More

- [vinext Documentation](https://github.com/cloudflare/vinext)
- [Production architecture](docs/architecture/README.md)
- [Implementation ledger](docs/implementation-ledger.md)
- [Source-of-truth workflow](docs/data-governance/source-of-truth.md)
