# Directory maintenance and community feedback

Owner decision: 2026-10-13. Target a monthly directory refresh; every other
month is acceptable when source activity and review capacity warrant it.
Feedback intake remains available between refreshes. This is the operating
policy, not a claim that an automated refresh job is already running.

## Refresh and review

- Review configured sources monthly, or every other month by an explicit
  operating decision. Prioritize changed sources and overdue verification.
- Compare incoming observations with existing canonical farms. Preserve named
  candidates and prior evidence when a source fails or stops listing a farm.
  Missing observations create a QA reason; they do not prove closure.
- Run normalization, identity matching, eligibility, geography, and privacy
  checks. Automation handles clear cases; ambiguous cases join QA residue.
- Confirm consequential changes against dated evidence. Distinguish permanent
  closure, temporary closure, seasonal inactivity, relocation, and unknown
  operating status. A dead website alone is insufficient closure evidence.
- Retain confirmed closed farms internally with their evidence and decision;
  exclude them from active discovery rather than erasing their history.
- Publish reviewed changes through the canonical pipeline, regenerate the app
  feed and displayed counts, and run the required release checks.
- Keep source retrieval dates separate from verification dates. Re-fetching a
  directory page does not confirm that a farm is still operating.

Do not enable unattended state refreshes until the collector reconciles with
the existing committed state store and preserves records through source
failures. The current replacement-write path needs that safeguard first.

## Community input

Provide a feedback section on the directory and a “Suggest an update” entry
point from each farm profile. Owners, staff, customers, and other people with
firsthand knowledge can report information; reporting does not grant direct
editing rights or establish verified ownership. A user account is not required
for initial intake.

Support these report types:

- Add a missing farm.
- Correct products, ways to buy, website, or other listing information.
- Report a permanent or temporary closure, seasonal change, or reopening.
- Report relocation or a duplicate listing.
- Share another correction.

Collect the existing farm ID when available, farm name and city/state, report
type, proposed change, relationship to the farm, and when the person observed
the information. Accept a firsthand account without requiring a public URL;
offer a supporting source URL and optional private email for follow-up.
Do not request home addresses or other unnecessary private information.

Reports go through a submission API to private server-side storage and review,
never directly to public listings. See the
[community feedback implementation plan](../product/community-feedback-plan.md)
for the backend, review workflow, and improvement loop.
Show a receipt only after durable intake succeeds; if submission fails, retain
the form contents and offer a retry. Do not imply that a report was verified or
published merely because it was received.

Verify owner identity before giving an owner correction precedence over an
older directory source. Corroborate consequential visitor reports, especially
closure and identity changes. Preserve the report, evidence, review decision,
and resulting canonical change. Keep reporter contact details private and out
of public exports and retrieval prompts.

Review reports between scheduled refreshes. Confirmed closures and material
corrections may ship earlier through the same publication checks; they need
not wait for a complete national collection cycle. Repeated reports about one
farm should be grouped for review, not treated as independent corroboration.

## Retrieval and answers

Public answers use approved published facts and permitted source passages.
Unreviewed community submissions are not evidence for public answers. When a
correction is published, update the relevant search material and invalidate
affected cached answers. Respect current status, source dates, and privacy
rules in retrieval; do not present stale hours or seasonal availability as
live information.

## Delivery status

- Monthly baseline and every-other-month option: agreed operating policy.
- Existing automated eligibility/privacy checks and QA residue: implemented.
- Safe recurring reconciliation, operating-status history, and scheduling:
  follow-up implementation work.
- Feedback destination: private backend storage and review, agreed direction;
  the first implementation adds PostgreSQL intake, durable receipts, pending
  processing jobs, and a gated form. It remains disabled pending managed
  infrastructure and verified production access; see the
  [intake runbook](feedback-intake-runbook.md). Authenticated curator review,
  audited decisions, and leased triage are now implemented in PR #131; see the
  [review runbook](feedback-review-runbook.md). Approval does not yet publish corrections.
- Grounded generated answers: planned; the current Ask UI searches listing text.
