import { randomUUID } from "node:crypto";
import { Client } from "pg";
import type { FeedbackSubmission } from "./feedback-contract";

export type ReviewDecision = "approve" | "reject" | "needs_information" | "duplicate";
export type ReviewStatus = "pending" | "reviewing" | "resolved";
export type ReviewDecisionInput = { decision: ReviewDecision; expectedRevision: number; reason: string; evidenceUrl?: string };
export type FeedbackReviewRecord = {
  receipt: string; payload: Omit<FeedbackSubmission, "email" | "idempotencyKey">;
  releaseId: string; status: ReviewStatus; revision: number;
  triage: Record<string, unknown> | null; outcome: ReviewDecision | null; createdAt: string;
  history: { revision: number; decision: ReviewDecision; reason: string; evidenceUrl: string | null; actorEmail: string; createdAt: string }[];
};
export class FeedbackReviewConflictError extends Error {
  constructor() { super("This report was changed by another reviewer. Reload before deciding."); this.name = "FeedbackReviewConflictError"; }
}
export class FeedbackReviewNotFoundError extends Error {
  constructor() { super("Feedback report not found."); this.name = "FeedbackReviewNotFoundError"; }
}
export class FeedbackReviewValidationError extends Error {
  constructor(public fieldErrors: Record<string, string>) { super("Review decision is invalid."); this.name = "FeedbackReviewValidationError"; }
}

export function parseReviewDecision(input: unknown):
  { decision: ReviewDecisionInput; fieldErrors?: never } | { decision?: never; fieldErrors: Record<string, string> } {
  if (!input || typeof input !== "object" || Array.isArray(input)) return { fieldErrors: { form: "Provide a JSON object." } };
  const value = input as Record<string, unknown>;
  const errors: Record<string, string> = {};
  const decision = value.decision as ReviewDecision;
  if (!["approve", "reject", "needs_information", "duplicate"].includes(decision)) errors.decision = "Select a review decision.";
  if (!Number.isSafeInteger(value.expectedRevision) || (value.expectedRevision as number) < 0) errors.expectedRevision = "Provide the current report revision.";
  const reason = typeof value.reason === "string" ? value.reason.trim() : "";
  if (reason.length < 20 || reason.length > 4000 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(reason)) errors.reason = "Explain your decision in 20–4000 characters.";
  let evidenceUrl: string | undefined;
  if (value.evidenceUrl !== undefined && value.evidenceUrl !== "") {
    try {
      if (typeof value.evidenceUrl !== "string" || value.evidenceUrl.length > 2048) throw new Error();
      evidenceUrl = value.evidenceUrl.trim();
      const url = new URL(evidenceUrl);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || /[\u0000-\u0020]/.test(evidenceUrl)) throw new Error();
    } catch { errors.evidenceUrl = "Use an http or https evidence URL without credentials."; }
  }
  return Object.keys(errors).length ? { fieldErrors: errors } : { decision: { decision, expectedRevision: value.expectedRevision as number, reason, evidenceUrl } };
}

const connect = (connectionString: string) => new Client({ connectionString, connectionTimeoutMillis: 5_000, query_timeout: 10_000, statement_timeout: 8_000, application_name: "farmfinder-feedback-review" });

/** Curator-only view: deliberately never joins private contacts or returns retry credentials. */
export async function listFeedbackForReview(connectionString: string, status: ReviewStatus = "pending", limit = 25, offset = 0): Promise<FeedbackReviewRecord[]> {
  if (!["pending", "reviewing", "resolved"].includes(status) || !Number.isInteger(limit) || limit < 1 || limit > 50) throw new FeedbackReviewValidationError({ form: "Use a valid status and a limit between 1 and 50." });
  if (!Number.isSafeInteger(offset) || offset < 0 || offset > 10_000) throw new FeedbackReviewValidationError({ offset: "Use an offset between 0 and 10000." });
  const client = connect(connectionString);
  try {
    await client.connect();
    const result = await client.query<FeedbackReviewRecord>(
      `SELECT s.receipt, s.payload - 'email' - 'idempotencyKey' AS payload,
        s.release_id AS "releaseId", s.status, s.review_revision AS revision, s.triage,
        s.review_outcome AS outcome, s.created_at::text AS "createdAt",
        COALESCE((SELECT jsonb_agg(jsonb_build_object('revision', e.revision, 'decision', e.decision,
          'reason', e.reason, 'evidenceUrl', e.evidence_url, 'actorEmail', e.actor_email,
          'createdAt', e.created_at) ORDER BY e.revision)
          FROM feedback_private.review_events e WHERE e.receipt = s.receipt), '[]'::jsonb) AS history
       FROM feedback_private.submissions s WHERE s.status = $1
       ORDER BY s.created_at, s.receipt LIMIT $2 OFFSET $3`, [status, limit, offset]);
    return result.rows;
  } finally { await client.end().catch(() => undefined); }
}

/** Audit and disposition are one transaction. Approval never publishes or edits canonical farms. */
export async function reviewFeedback(connectionString: string, receipt: string, input: ReviewDecisionInput, actor: { subject: string; email: string }): Promise<{ receipt: string; revision: number; status: ReviewStatus; outcome: ReviewDecision }> {
  const parsed = parseReviewDecision(input);
  if (parsed.fieldErrors) throw new FeedbackReviewValidationError(parsed.fieldErrors);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(receipt)) throw new FeedbackReviewNotFoundError();
  if (!actor.subject.trim() || !actor.email.trim()) throw new FeedbackReviewValidationError({ actor: "Authenticated reviewer identity is required." });
  const decision = parsed.decision;
  const client = connect(connectionString);
  let transaction = false;
  try {
    await client.connect();
    await client.query("BEGIN");
    transaction = true;
    const current = await client.query<{ review_revision: number }>("SELECT review_revision FROM feedback_private.submissions WHERE receipt = $1 FOR UPDATE", [receipt]);
    if (!current.rows[0]) throw new FeedbackReviewNotFoundError();
    if (current.rows[0].review_revision !== decision.expectedRevision) throw new FeedbackReviewConflictError();
    const revision = decision.expectedRevision + 1;
    const status: ReviewStatus = decision.decision === "needs_information" ? "reviewing" : "resolved";
    await client.query(`INSERT INTO feedback_private.review_events
      (id, receipt, revision, actor_subject, actor_email, decision, reason, evidence_url)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
    [randomUUID(), receipt, revision, actor.subject, actor.email, decision.decision, decision.reason, decision.evidenceUrl ?? null]);
    await client.query("UPDATE feedback_private.submissions SET review_revision = $2, status = $3, review_outcome = $4 WHERE receipt = $1", [receipt, revision, status, decision.decision]);
    await client.query("COMMIT");
    transaction = false;
    return { receipt, revision, status, outcome: decision.decision };
  } catch (error) {
    if (transaction) await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally { await client.end().catch(() => undefined); }
}
