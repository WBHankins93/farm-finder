-- Private review and leased triage; canonical directory records are untouched.
BEGIN;
ALTER TABLE feedback_private.submissions
  ADD COLUMN review_revision integer NOT NULL DEFAULT 0 CHECK (review_revision >= 0),
  ADD COLUMN triage jsonb CHECK (jsonb_typeof(triage) = 'object'),
  ADD COLUMN review_outcome text CHECK (review_outcome IN ('approve', 'reject', 'needs_information', 'duplicate'));

CREATE TABLE feedback_private.review_events (
  id uuid PRIMARY KEY,
  receipt uuid NOT NULL REFERENCES feedback_private.submissions(receipt),
  revision integer NOT NULL CHECK (revision > 0),
  actor_subject text NOT NULL,
  actor_email text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('approve', 'reject', 'needs_information', 'duplicate')),
  reason text NOT NULL,
  evidence_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (receipt, revision)
);
ALTER TABLE feedback_private.processing_jobs
  ADD COLUMN lease_token uuid,
  ADD COLUMN lease_expires_at timestamptz,
  ADD COLUMN last_error_code text;
CREATE INDEX feedback_jobs_expired ON feedback_private.processing_jobs (lease_expires_at)
  WHERE status = 'processing';
REVOKE ALL ON SCHEMA feedback_private FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA feedback_private FROM PUBLIC;
COMMIT;
