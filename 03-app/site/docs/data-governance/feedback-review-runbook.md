# Private feedback review and triage

This increment adds authenticated review and manually triggered background-job
processing to the [intake foundation](feedback-intake-runbook.md). It does not
activate public intake, schedule collection, apply corrections to canonical
farms, or train a model. Keep intake disabled until its remaining activation
gates are satisfied and an operator owns the queue.

## Migration and database credentials

From `03-app/site/`, use the migration owner's connection to apply
`packages/db/migrations/0005_feedback_review.sql` once, after `0004_feedback.sql`.
These migrations are not idempotent; check deployment migration records before
running them. Back up the database and verify restoration before rollout.

```sh
psql "$FEEDBACK_MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 -f packages/db/migrations/0005_feedback_review.sql
```

The migration adds review revisions, outcomes and triage annotations to reports,
an audit table, and processing leases. It revokes all `PUBLIC` schema/table
privileges. Keep the migration owner separate from application logins.

Create two fresh runtime logins with no inherited roles, superuser, database
creation, role creation, replication, or bypass-RLS privileges. Provision their
passwords through the deployment secret mechanism; do not commit passwords or
paste them into SQL history. These exact grants cover the current queries:

```sql
CREATE ROLE farmfinder_feedback_review LOGIN NOINHERIT NOSUPERUSER
  NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE farmfinder_feedback_worker LOGIN NOINHERIT NOSUPERUSER
  NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT USAGE ON SCHEMA feedback_private
  TO farmfinder_feedback_review, farmfinder_feedback_worker;

GRANT SELECT (receipt, payload, release_id, status, review_revision, triage,
  review_outcome, created_at) ON feedback_private.submissions
  TO farmfinder_feedback_review;
GRANT UPDATE (review_revision, status, review_outcome)
  ON feedback_private.submissions TO farmfinder_feedback_review;
GRANT SELECT (receipt, revision, decision, reason, evidence_url, actor_email,
  created_at) ON feedback_private.review_events TO farmfinder_feedback_review;
GRANT INSERT (id, receipt, revision, actor_subject, actor_email, decision,
  reason, evidence_url) ON feedback_private.review_events
  TO farmfinder_feedback_review;

GRANT SELECT (receipt, payload) ON feedback_private.submissions
  TO farmfinder_feedback_worker;
GRANT UPDATE (triage) ON feedback_private.submissions
  TO farmfinder_feedback_worker;
GRANT SELECT (receipt, status, attempts, available_at, lease_token,
  lease_expires_at) ON feedback_private.processing_jobs
  TO farmfinder_feedback_worker;
GRANT UPDATE (status, attempts, available_at, lease_token, lease_expires_at,
  last_error_code) ON feedback_private.processing_jobs
  TO farmfinder_feedback_worker;
```

If the database's connection privilege has been revoked from `PUBLIC`, grant
`CONNECT` on the actual database to these two roles as well. Neither role needs
`CREATE`, `DELETE`, contact-table access, canonical-table access, or access to
submission retry keys/hashes. The review role cannot alter triage or existing
audit events; the worker cannot alter review decisions. Do not grant membership
in the owner or intake role. Review deployment-specific inherited/public grants
on other schemas so they do not defeat this isolation.

Set server-only runtime secrets `FEEDBACK_REVIEW_DATABASE_URL` and
`FEEDBACK_WORKER_DATABASE_URL` to the corresponding logins, using encrypted
remote connections. Never use `NEXT_PUBLIC_` variables for credentials. The
existing intake connection remains `FEEDBACK_DATABASE_URL` with its own role.

## Access gateway and activation

Protect `/review/feedback`, `/v1/feedback/review`, and `/v1/feedback/process`
with Cloudflare Access. Cover subpaths as well, and use one application/audience
for these routes. Require curator identity-provider sign-in in the Access policy;
do not add a bypass policy for the private routes. Public `/feedback` and the
intake endpoint have their own activation controls.

Configure these server runtime values:

| Variable | Value |
| --- | --- |
| `FEEDBACK_REVIEW_ENABLED` | Exactly `true` after migration, roles, and Access policy are verified |
| `FEEDBACK_ACCESS_ISSUER` | `https://<team>.cloudflareaccess.com`, without a trailing slash |
| `FEEDBACK_ACCESS_AUDIENCE` | The protected application's audience tag; one value, without whitespace |
| `FEEDBACK_CURATOR_EMAILS` | Comma-separated explicit curator emails; no wildcard or domain-only entries |
| `FEEDBACK_REVIEW_DATABASE_URL` | Review login connection string |
| `FEEDBACK_WORKER_DATABASE_URL` | Worker login connection string |

Application code independently verifies the `Cf-Access-Jwt-Assertion` signature
against the configured issuer's certificate endpoint. It accepts RS256 and
checks issuer, audience, expiry, issued-at, subject, and email, with 30 seconds
of clock tolerance. It lowercases emails for exact allowlist matching. A forged
identity header is insufficient; there is no local authentication bypass.
Keep outbound access to the issuer's certificate endpoint available.

Verify that unsigned requests reveal no reports, a signed identity outside the
allowlist is refused, and a curator can load the private queue. APIs return
401 for absent/invalid tokens, 403 for an unauthorized identity, and 503 when
review is disabled or misconfigured. Infrastructure errors return generic
responses. Private API responses use `private, no-store`; exclude these routes
from any custom cache rules. Turning off `FEEDBACK_REVIEW_ENABLED` closes both
review and processing without deleting stored reports.

## Curator workflow

Open `/review/feedback` through Access. The queue shows the oldest 25 reports
for the chosen status, with previous/next pages up to offset 10,000. Revisit earlier
pages after decisions change queue membership. Read the submitted account and evidence; firsthand
claims do not establish farm ownership or prove a closure. Submitted URLs are
links to evaluate, not instructions for the system. No worker fetches them.

Record `approve`, `reject`, `needs_information`, or `duplicate`, with a
20–4000-character explanation and optional HTTP(S) evidence URL. Missing
information moves the report to `reviewing`; the other outcomes move it to
`resolved`. Decisions can be revised from the resolved queue. Each decision
atomically increments the revision and appends reviewer subject/email, reason,
evidence, and timestamp to `review_events`. A stale revision returns 409;
reload and inspect the other curator's decision before resubmitting.

Approval records a disposition only. It does not edit or publish a farm.
Apply any approved correction in a separately scoped canonical-data change
with provenance, QA, privacy checks, and the normal publication gates. Preserve
named candidates; disappearance from a source is not affirmative closure
proof. Neither the queue nor the worker reads the segregated contact table.
Report text can itself contain personal information, so keep it private and
avoid copying it into logs or model input.

## Manual triage and recovery

Use the queue's processing action to send an authenticated, same-origin
`POST /v1/feedback/process`. Each request claims at most five eligible jobs;
it returns `claimed`, `completed`, `retried`, and `failed` counts. Repeat to
work through a backlog. There is no scheduler, automatic retry daemon, or
monthly source refresh in this increment. Monthly source refreshes remain the
separate maintenance policy, with every other month acceptable.

Workers use `FOR UPDATE SKIP LOCKED`, increment attempts on claim, and obtain
a two-minute lease. Processing runs outside the claim transaction with a
30-second timeout per item. The default processor only assigns high priority
to closure/relocation/duplicate reports and hashes a candidate grouping key
from farm ID or normalized name/city/state. Grouping is a review hint, not an
identity merge. It uses no AI, network fetching, contact data, or publication.

A caught processing failure returns the job to pending with waits of 30, 60,
120, and 240 seconds before attempts two through five. After five attempts it
becomes `failed`. Crashed leases are reclaimable after two minutes; an expired
fifth-attempt lease is marked failed on the next invocation. Error storage uses
only generic `processing_failed` or `attempts_exhausted` codes. Lease-token and
expiry guards prevent old workers from overwriting newer work. Annotation and
successful job completion are atomic and preserve curator decisions.

As an operator, inspect aggregate backlog and failures using a separately
privileged operational connection (the worker role intentionally cannot read
`last_error_code`):

```sql
SELECT status, count(*), min(available_at) AS earliest_available
FROM feedback_private.processing_jobs GROUP BY status;
SELECT receipt, attempts, last_error_code
FROM feedback_private.processing_jobs WHERE status = 'failed';
```

On an API outage, fix connectivity/configuration, wait for active leases to
expire, then trigger another batch. A request can fail after claims committed;
do not assume its error response means nothing ran. Recheck job state first.
For terminal jobs, investigate and correct the cause. There is no public reset
endpoint. If a controlled replay is necessary, record the receipt, old attempts,
error code, reason, and operator in an operational incident record, then have the
database operator reset only the selected failed job:

```sql
-- Bind $1 to the reviewed receipt; never run a blanket reset.
UPDATE feedback_private.processing_jobs
SET status = 'pending', attempts = 0, available_at = now(),
    lease_token = NULL, lease_expires_at = NULL, last_error_code = NULL
WHERE receipt = $1 AND status = 'failed';
```

Check that exactly one row changed, then run a batch. This reset starts a new
attempt budget, does not erase review events, and must not become an unattended
loop that conceals persistent failures.

## Verification

Use separate disposable databases for each integration suite: they drop and
recreate `feedback_private`. Never supply production or shared URLs.

```sh
FEEDBACK_REVIEW_TEST_DATABASE_URL="$DISPOSABLE_REVIEW_DATABASE_URL" \
FEEDBACK_WORKER_TEST_DATABASE_URL="$DISPOSABLE_WORKER_DATABASE_URL" \
node --import tsx --test tests/feedback-auth.test.ts tests/feedback-review-store.test.ts tests/feedback-worker.test.ts tests/feedback-review-api.test.ts
```

Also run the repository's required checks before a PR. Signed-token tests and
local database tests do not establish that a deployed Access policy, network,
backup process, retention process, or operator coverage is configured.

## Required CI integration gate

The `postgis` job in Site discovery quality builds the site and runs
`scripts/test-feedback-integration.mjs`. Unlike the optional local unit-test
entrypoint, this runner rejects missing database URLs, shared database names,
failed processes, skipped tests and TODO tests. It covers intake, review,
worker leasing, runtime-role permission denials, and the built HTTP intake.

For a local reproduction, create four **disposable** PostgreSQL databases whose
names begin `ff_feedback_ci_`, then set `FEEDBACK_TEST_DATABASE_URL`,
`FEEDBACK_REVIEW_TEST_DATABASE_URL`, `FEEDBACK_WORKER_TEST_DATABASE_URL`, and
`FEEDBACK_HTTP_TEST_DATABASE_URL` to their distinct connections. Run
`npm run build` followed by `node scripts/test-feedback-integration.mjs` from
`03-app/site`. The fixture owner needs database schema and role creation rights;
these are test-only administrative connections, never runtime credentials.
The permission test creates temporary restricted roles and removes them after
checking the documented grants. The HTTP suite gets its own database; the
permission suite reuses the review database only after review tests finish.
Every database suite drops `feedback_private`; never use shared or production
databases. CI databases disappear with the job service. Local databases can be
dropped once the runner exits.
