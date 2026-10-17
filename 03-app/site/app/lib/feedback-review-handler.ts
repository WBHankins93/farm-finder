import { authenticateCurator, FeedbackAuthError, type FeedbackCurator } from "./feedback-auth";
import { listFeedbackForReview, reviewFeedback, parseReviewDecision, FeedbackReviewConflictError, FeedbackReviewNotFoundError, FeedbackReviewValidationError, type ReviewStatus, type ReviewDecisionInput } from "./feedback-review-store";
import { processFeedbackBatch } from "./feedback-worker";

type Dependencies = {
  authenticate: (headers: Headers) => Promise<FeedbackCurator>;
  list: (status: ReviewStatus, offset: number) => ReturnType<typeof listFeedbackForReview>;
  decide: (receipt: string, decision: ReviewDecisionInput, actor: FeedbackCurator) => ReturnType<typeof reviewFeedback>;
  process: () => ReturnType<typeof processFeedbackBatch>;
};
function database(key: string) {
  const url = process.env[key];
  if (!url) throw new Error("Review database unavailable");
  return url;
}
const defaults: Dependencies = {
  authenticate: authenticateCurator,
  list: (status, offset) => listFeedbackForReview(database("FEEDBACK_REVIEW_DATABASE_URL"), status, 25, offset),
  decide: (receipt, decision, actor) => reviewFeedback(database("FEEDBACK_REVIEW_DATABASE_URL"), receipt, decision, actor),
  process: () => processFeedbackBatch(database("FEEDBACK_WORKER_DATABASE_URL")),
};
export function privateResponse(body: object, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Vary": "Cf-Access-Jwt-Assertion" } });
}
class RequestError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function readDecision(request: Request): Promise<Record<string, unknown>> {
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") throw new RequestError(415, "Use application/json.");
  if (Number(request.headers.get("content-length")) > 8192) throw new RequestError(413, "Decision is too large.");
  const reader = request.body?.getReader();
  if (!reader) throw new RequestError(400, "Provide a decision.");
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8192) { await reader.cancel(); throw new RequestError(413, "Decision is too large."); }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const value: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error();
    return value as Record<string, unknown>;
  } catch (error) {
    if (error instanceof RequestError) throw error;
    throw new RequestError(400, "Provide valid JSON.");
  } finally { reader.releaseLock(); }
}
/** Both private endpoints authenticate before reading bodies or accessing storage. */
export async function handleFeedbackReview(request: Request, mode: "review" | "process" = "review", deps: Dependencies = defaults) {
  try {
    const actor = await deps.authenticate(request.headers);
    if (request.method === "GET" && mode === "review") {
      const status = new URL(request.url).searchParams.get("status") ?? "pending";
      if (!["pending", "reviewing", "resolved"].includes(status)) throw new RequestError(400, "Select a valid report status.");
      const rawOffset = new URL(request.url).searchParams.get("offset") ?? "0";
      const offset = Number(rawOffset);
      if (!/^\d+$/.test(rawOffset) || !Number.isSafeInteger(offset) || offset > 10_000) throw new RequestError(400, "Select a valid queue offset.");
      return privateResponse({ reports: await deps.list(status as ReviewStatus, offset) });
    }
    if (request.method !== "POST") return privateResponse({ error: "Method not allowed." }, 405);
    const origin = request.headers.get("origin");
    if ((origin && origin !== new URL(request.url).origin) || request.headers.get("sec-fetch-site") === "cross-site") throw new RequestError(403, "Submit this action from the review page.");
    if (mode === "process") return privateResponse(await deps.process());
    const input = await readDecision(request);
    if (typeof input.receipt !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(input.receipt)) throw new RequestError(400, "Provide a valid report receipt.");
    const parsed = parseReviewDecision(input);
    if (parsed.fieldErrors) return privateResponse({ fieldErrors: parsed.fieldErrors }, 400);
    return privateResponse(await deps.decide(input.receipt, parsed.decision, actor));
  } catch (error) {
    if (error instanceof FeedbackAuthError || error instanceof RequestError) return privateResponse({ error: error.message }, error.status);
    if (error instanceof FeedbackReviewValidationError) return privateResponse({ fieldErrors: error.fieldErrors }, 400);
    if (error instanceof FeedbackReviewConflictError) return privateResponse({ error: error.message }, 409);
    if (error instanceof FeedbackReviewNotFoundError) return privateResponse({ error: error.message }, 404);
    return privateResponse({ error: "Feedback review is temporarily unavailable." }, 503);
  }
}
