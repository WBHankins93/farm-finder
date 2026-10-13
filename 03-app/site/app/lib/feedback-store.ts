import { createHash, randomUUID } from "node:crypto";
import { Client } from "pg";
import type { FeedbackSubmission } from "./feedback-contract";

export class FeedbackConflictError extends Error {
  constructor() {
    super("This retry key was already used for different feedback.");
    this.name = "FeedbackConflictError";
  }
}

export class FeedbackRateLimitError extends Error {
  constructor() {
    super("Feedback intake is temporarily at capacity.");
    this.name = "FeedbackRateLimitError";
  }
}

/** Persist validated feedback, its private contact and processing job atomically. */
export async function storeFeedback(
  connectionString: string,
  submission: FeedbackSubmission,
  releaseId: string,
  validateNew: () => Promise<void> = async () => {},
): Promise<{ receipt: string; replayed: boolean }> {
  // Explicit field order makes retries independent of incoming JSON key order.
  const payload = {
    farmId: submission.farmId,
    farmName: submission.farmName,
    city: submission.city,
    state: submission.state,
    type: submission.type,
    details: submission.details,
    relationship: submission.relationship,
    observedOn: submission.observedOn,
    sourceUrl: submission.sourceUrl,
  };
  const payloadHash = createHash("sha256")
    .update(JSON.stringify({ ...payload, email: submission.email }))
    .digest("hex");
  const client = new Client({
    connectionString,
    connectionTimeoutMillis: 5_000,
    query_timeout: 10_000,
    statement_timeout: 8_000,
    application_name: "farmfinder-feedback",
  });
  let inTransaction = false;
  try {
    await client.connect();
    await client.query("BEGIN");
    inTransaction = true;
    // Serialize admission across worker instances without collecting IP addresses.
    await client.query("SELECT pg_advisory_xact_lock(19088743, 120)");
    const receipt = randomUUID();
    const inserted = await client.query<{ receipt: string }>(
      `INSERT INTO feedback_private.submissions
        (receipt, idempotency_key, payload_hash, payload, release_id)
       VALUES ($1, $2, $3, $4::jsonb, $5)
       ON CONFLICT (idempotency_key) DO NOTHING RETURNING receipt`,
      [receipt, submission.idempotencyKey, payloadHash, JSON.stringify(payload), releaseId],
    );
    if (inserted.rows.length === 0) {
      // A separate statement sees the winner after a concurrent INSERT commits.
      const existing = await client.query<{ receipt: string; payload_hash: string }>(
        "SELECT receipt, payload_hash FROM feedback_private.submissions WHERE idempotency_key = $1",
        [submission.idempotencyKey],
      );
      if (!existing.rows[0] || existing.rows[0].payload_hash !== payloadHash) {
        throw new FeedbackConflictError();
      }
      await client.query("COMMIT");
      inTransaction = false;
      return { receipt: existing.rows[0].receipt, replayed: true };
    }
    const volume = await client.query<{ count: string }>(
      "SELECT count(*) FROM feedback_private.submissions WHERE created_at >= now() - interval '1 hour'",
    );
    // Includes this transaction's new report; retries returned above bypass the cap.
    if (Number(volume.rows[0].count) > 120) throw new FeedbackRateLimitError();
    // Existing retries return above even if the referenced listing has changed.
    await validateNew();
    if (submission.email) {
      await client.query(
        "INSERT INTO feedback_private.contacts (receipt, email) VALUES ($1, $2)",
        [receipt, submission.email],
      );
    }
    await client.query(
      "INSERT INTO feedback_private.processing_jobs (receipt) VALUES ($1)",
      [receipt],
    );
    await client.query("COMMIT");
    inTransaction = false;
    return { receipt, replayed: false };
  } catch (error) {
    if (inTransaction) await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally {
    // One connection per request, including failed connect/query/rollback paths.
    await client.end().catch(() => undefined);
  }
}
