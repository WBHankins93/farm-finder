import { parseFeedback, type FeedbackSubmission } from "./feedback-contract";

// Server-only configuration: never expose the connection string to a client.
export function feedbackEnabled() {
  return process.env.FEEDBACK_ENABLED === "true" && Boolean(process.env.FEEDBACK_DATABASE_URL);
}
type Dependencies = {
  enabled: boolean;
  releaseId: string;
  farmExists: (id: string) => Promise<boolean>;
  store: (submission: FeedbackSubmission, releaseId: string, validateNew: () => Promise<void>) => Promise<{ receipt: string; replayed: boolean }>;
  isConflict: (error: unknown) => boolean;
};
class MissingFarmError extends Error {}
const maxBodyBytes = 24_000;
const unavailable = "Feedback is temporarily unavailable. Please try again later.";
function json(body: object, status: number) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}

export async function handleFeedback(request: Request, deps: Dependencies): Promise<Response> {
  if (request.method !== "POST") return new Response(null, { status: 405, headers: { Allow: "POST", "Cache-Control": "no-store" } });
  if (!deps.enabled) return json({ error: unavailable }, 503);
  const origin = request.headers.get("origin");
  if ((origin && origin !== new URL(request.url).origin) || request.headers.get("sec-fetch-site") === "cross-site") return json({ error: "Submit feedback from this site." }, 403);
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") return json({ error: "Use application/json." }, 415);
  if (Number(request.headers.get("content-length")) > maxBodyBytes) return json({ error: "Report is too large." }, 413);
  const reader = request.body?.getReader();
  if (!reader) return json({ fieldErrors: { form: "Provide a report." } }, 400);
  const chunks: Uint8Array[] = [];
  let size = 0;
  let input: unknown;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBodyBytes) {
        await reader.cancel();
        return json({ error: "Report is too large." }, 413);
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    input = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch { return json({ fieldErrors: { form: "Provide valid JSON." } }, 400); }
  finally { reader.releaseLock(); }
  const parsed = parseFeedback(input);
  if (parsed.fieldErrors) return json({ fieldErrors: parsed.fieldErrors }, 400);
  try {
    const { receipt, replayed } = await deps.store(parsed.submission, deps.releaseId, async () => {
      if (parsed.submission.farmId && !await deps.farmExists(parsed.submission.farmId)) throw new MissingFarmError();
    });
    return json({ receipt, status: "received" }, replayed ? 200 : 201);
  } catch (error) {
    if (error instanceof MissingFarmError) return json({ fieldErrors: { farmId: "This listing is no longer available. You can send your report without linking to it." } }, 400);
    if (error instanceof Error && error.name === "FeedbackRateLimitError") return Response.json({ error: "Feedback is busy. Please try again later." }, { status: 429, headers: { "Retry-After": "3600", "Cache-Control": "no-store" } });
    if (deps.isConflict(error)) return json({ error: "This request identifier was already used for a different report. Start a new report." }, 409);
    return json({ error: unavailable }, 503);
  }
}
