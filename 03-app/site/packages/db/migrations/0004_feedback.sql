-- Private community reports only: this migration never alters canonical farms.
-- Standalone so intake can be provisioned before the directory's Postgres cutover.
BEGIN;
CREATE SCHEMA feedback_private;
REVOKE ALL ON SCHEMA feedback_private FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA feedback_private REVOKE ALL ON TABLES FROM PUBLIC;

CREATE TABLE feedback_private.submissions (
  receipt uuid PRIMARY KEY,
  idempotency_key uuid NOT NULL UNIQUE,
  payload_hash text NOT NULL CHECK (payload_hash ~ '^[a-f0-9]{64}$'),
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object' AND NOT (payload ? 'email')),
  release_id text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewing', 'resolved')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX feedback_submissions_created ON feedback_private.submissions (created_at);

-- Contact details are segregated from the material processed for corrections.
CREATE TABLE feedback_private.contacts (
  receipt uuid PRIMARY KEY REFERENCES feedback_private.submissions(receipt) ON DELETE CASCADE,
  email text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- An outbox ensures a stored report cannot be lost between intake and processing.
CREATE TABLE feedback_private.processing_jobs (
  receipt uuid PRIMARY KEY REFERENCES feedback_private.submissions(receipt) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  available_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX feedback_jobs_pending ON feedback_private.processing_jobs (available_at)
  WHERE status = 'pending';
REVOKE ALL ON ALL TABLES IN SCHEMA feedback_private FROM PUBLIC;
COMMIT;
