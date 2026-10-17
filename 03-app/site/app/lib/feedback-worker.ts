import { createHash, randomUUID } from "node:crypto";
import { Client } from "pg";

type Payload = Record<string, unknown>;
type Job = { receipt: string; attempts: number; lease_token: string; payload: Payload };

/** Group possible matches for review, without treating a group as identity proof. */
export async function triageFeedback(payload: Payload): Promise<Record<string, unknown>> {
  const normalize = (value: unknown) => typeof value === "string" ? value.normalize("NFKC").trim().toLowerCase().replace(/\s+/g, " ") : "";
  const identity = payload.farmId
    ? ["id", payload.farmId]
    : ["name", normalize(payload.farmName), normalize(payload.city), normalize(payload.state)];
  return {
    version: 1,
    priority: ["closure", "relocation", "duplicate"].includes(String(payload.type)) ? "high" : "normal",
    relatedGroup: createHash("sha256").update(JSON.stringify(identity)).digest("hex"),
  };
}

async function boundedProcess(process: (payload: Payload) => Promise<Record<string, unknown>>, payload: Payload) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      Promise.resolve().then(() => process(payload)),
      new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error("processing_timeout")), 30_000); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

/** Manually triggered, bounded private triage. No publication or contact access. */
export async function processFeedbackBatch(
  connectionString: string,
  options: { limit?: number; process?: (payload: Payload) => Promise<Record<string, unknown>> } = {},
): Promise<{ completed: number; failed: number; retried: number; claimed: number }> {
  const limit = options.limit ?? 5;
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) throw new Error("Invalid feedback batch size.");
  const client = new Client({ connectionString, connectionTimeoutMillis: 5_000, query_timeout: 10_000, statement_timeout: 8_000, application_name: "farmfinder-feedback-worker" });
  const counts = { completed: 0, failed: 0, retried: 0, claimed: 0 };
  let inTransaction = false;
  try {
    await client.connect();
    await client.query("BEGIN");
    inTransaction = true;
    // Exhausted crash leases are terminal too, even if no processor caught an error.
    const exhausted = await client.query(`UPDATE feedback_private.processing_jobs SET status = 'failed',
      lease_token = NULL, lease_expires_at = NULL, last_error_code = 'attempts_exhausted'
      WHERE attempts >= 5 AND (status = 'pending' OR (status = 'processing' AND lease_expires_at <= now()))`);
    counts.failed += exhausted.rowCount ?? 0;
    const jobs = await client.query<Job>(`WITH candidates AS (
      SELECT receipt FROM feedback_private.processing_jobs
      WHERE attempts < 5 AND ((status = 'pending' AND available_at <= now())
        OR (status = 'processing' AND lease_expires_at <= now()))
      ORDER BY available_at, receipt LIMIT $1 FOR UPDATE SKIP LOCKED
    ), claimed AS (
      UPDATE feedback_private.processing_jobs j SET status = 'processing', attempts = attempts + 1,
        lease_token = $2, lease_expires_at = now() + interval '2 minutes', last_error_code = NULL
      FROM candidates c WHERE j.receipt = c.receipt RETURNING j.receipt, j.attempts, j.lease_token
    ) SELECT c.*, s.payload FROM claimed c JOIN feedback_private.submissions s USING (receipt)`, [limit, randomUUID()]);
    await client.query("COMMIT");
    inTransaction = false;
    counts.claimed = jobs.rows.length;
    // Run together: the last item must not wait behind the other items' timeouts.
    const results = await Promise.all(jobs.rows.map(async (job) => {
      try {
        const triage = await boundedProcess(options.process ?? triageFeedback, job.payload);
        if (!triage || typeof triage !== "object" || Array.isArray(triage)) throw new Error("invalid_triage");
        return { job, triage: JSON.stringify(triage) };
      } catch {
        return { job, triage: undefined };
      }
    }));
    for (const { job, triage } of results) {
      if (triage !== undefined) {
        // One statement makes the lease check, completion, and annotation atomic.
        const finished = await client.query(`WITH owned AS (
          UPDATE feedback_private.processing_jobs SET status = 'completed', lease_token = NULL, lease_expires_at = NULL
          WHERE receipt = $1 AND status = 'processing' AND lease_token = $2 AND lease_expires_at > now()
          RETURNING receipt
        ) UPDATE feedback_private.submissions s SET triage = $3::jsonb FROM owned o WHERE s.receipt = o.receipt`,
        [job.receipt, job.lease_token, triage]);
        counts.completed += finished.rowCount ?? 0;
      } else {
        const terminal = job.attempts >= 5;
        const failed = await client.query(`UPDATE feedback_private.processing_jobs SET status = $3,
          available_at = now() + ($4 * interval '1 second'), lease_token = NULL, lease_expires_at = NULL,
          last_error_code = 'processing_failed'
          WHERE receipt = $1 AND status = 'processing' AND lease_token = $2 AND lease_expires_at > now()`,
        [job.receipt, job.lease_token, terminal ? "failed" : "pending", 30 * 2 ** (job.attempts - 1)]);
        counts[terminal ? "failed" : "retried"] += failed.rowCount ?? 0;
      }
    }
    return counts;
  } catch (error) {
    if (inTransaction) await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally {
    await client.end().catch(() => undefined);
  }
}
