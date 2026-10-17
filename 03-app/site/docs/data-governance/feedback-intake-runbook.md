# Feedback intake foundation

This first implementation accepts private reports and creates a pending job in
the same PostgreSQL transaction. It includes the feedback page and conditional
entry points from the homepage and farm profiles. It is disabled by default.
The optional [private review workflow](feedback-review-runbook.md) adds curator
authentication, audited decisions, and manually triggered triage. Neither workflow
changes canonical records or trains a model. Publication and evaluation remain
subsequent steps in the [approved plan](../product/community-feedback-plan.md).

## Local verification

Use a **disposable PostgreSQL database**: the integration tests create and drop
the entire `feedback_private` schema. Never point the test variable at a shared
or production database. PostgreSQL 14 or newer is sufficient for this standalone
migration; no PostGIS extension or canonical farm import is needed for intake.

From `03-app/site/`, with the disposable URL supplied in the shell environment:

```sh
npm ci
FEEDBACK_TEST_DATABASE_URL="$DISPOSABLE_DATABASE_URL" npm test
```

The tests cover parallel submissions, payload-bound retries, rollback,
private-contact separation, intake quota, HTTP receipts, disabled UI, and
server-secret exclusion. Database tests explicitly skip if the test URL is not
provided; the regular unit and build checks are not substitutes for those tests.

For a local form preview, apply
`packages/db/migrations/0004_feedback.sql` once to a separate local database:

```sh
psql "$LOCAL_FEEDBACK_DATABASE_URL" -v ON_ERROR_STOP=1 -f packages/db/migrations/0004_feedback.sql
FEEDBACK_ENABLED=true FEEDBACK_DATABASE_URL="$LOCAL_FEEDBACK_DATABASE_URL" npm run start
```

Build first with `npm run build`. `vinext start` runs the built Node server,
which can reach a loopback PostgreSQL instance. Use synthetic reports only.
For deployed Cloudflare Workers, use a remotely reachable PostgreSQL database,
the existing Node compatibility flag, and runtime secrets. Do not put the
connection string in client configuration or a `NEXT_PUBLIC_` variable.

## Stored records and access

`feedback_private.submissions` stores report content, server-selected release,
receipt, payload hash, and a unique retry key. `contacts` stores optional email
separately. `processing_jobs` holds one pending job for every accepted report.
Submitted free text is still private and may contain personal information; email
separation is not a general-purpose redaction policy for later model use.

The migration revokes `PUBLIC` access. Deploy with a dedicated intake login
that has schema usage, `SELECT` and `INSERT` on submissions, and `INSERT` on
contacts and processing jobs. It needs no access to canonical tables and no
ability to update/delete reports. Migration and curator roles remain separate.
The intake role can read private submission content for retry validation and
quota enforcement; never expose that role or its connection string publicly.

There is no public report listing endpoint. A receipt only acknowledges durable
storage; it does not mean a correction is approved. Anonymous submissions do
not prove farm ownership. A new report is validated against the current listing
index; an already-stored retry returns its original receipt even when that
listing has since disappeared.

New intake is capped at 120 reports per rolling hour across the database.
Transactions serialize admission so concurrent workers cannot exceed the cap.
Exact retries bypass the cap. This limits storage growth for a pilot; it is not
a per-person anti-abuse system and a malicious sender can exhaust the quota.
Add edge rate limiting before public activation. Cross-origin browser requests,
non-JSON bodies, oversized bodies, invalid fields, and conflicting retries are
rejected. Submitted URLs are retained as evidence links and are not fetched.

## Activation gates and next PRs

Keep `FEEDBACK_ENABLED` unset or false in production until these are complete:

1. Provision managed PostgreSQL, verify encrypted connectivity and least-privilege
   roles, and test backup restoration. Use production secrets only at runtime.
2. Deploy and verify authenticated curator review, assign a review operator, and add explicit
   retention/deletion handling. Public activation must not create an unattended inbox.
3. Deploy and verify leased/retryable processing, then add backlog/failure monitoring and edge
   abuse controls. Preserve reporter privacy in logs and model input.
4. Connect reviewed changes to the existing QA and canonical publication path.
   Fix source reconciliation in the serial tooling lane before scheduling refreshes.

The API and form require both the explicit enable flag and a database URL.
An unreachable database returns a generic retryable error and preserves form
contents. Configuration presence is not a health/readiness check: operational
verification remains required before enabling the entry points.

After public launch, accept feedback continuously. Broad source refreshes remain
monthly by default, with every-other-month refreshes acceptable. No scheduled
collection job or automatic data promotion is introduced by this PR.
