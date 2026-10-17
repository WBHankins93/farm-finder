import assert from "node:assert/strict";
import test from "node:test";
import { parseFeedback } from "../app/lib/feedback-contract";
import { handleFeedback } from "../app/lib/feedback-handler";

const valid = { idempotencyKey: "7a2ce124-7380-4dbe-8307-1296c50936a2", farmName: "Example Farm", city: "Baton Rouge", state: "LA", type: "correction", details: "The farm offers a seasonal CSA program.", relationship: "visitor", email: "private@example.com" };
function request(body: unknown = valid, headers: Record<string, string> = {}) {
  return new Request("https://farmfinder.example/v1/feedback", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
}
function dependencies(overrides: Partial<Parameters<typeof handleFeedback>[1]> = {}) {
  return { enabled: true, releaseId: "release-test", farmExists: async () => true, store: async (_submission: unknown, _release: string, validateNew: () => Promise<void>) => { await validateNew(); return { receipt: "opaque-receipt", replayed: false }; }, isConflict: (error: unknown) => error instanceof Error && error.name === "FeedbackConflictError", ...overrides };
}

test("validation rejects invalid dates, credentials, unsupported states and oversized details", () => {
  for (const patch of [{ observedOn: "2026-02-30" }, { observedOn: "2999-01-01" }, { sourceUrl: "javascript:alert(1)" }, { sourceUrl: "https://user:password@example.com" }, { state: "XX" }, { details: "a".repeat(4001) }, { email: "bad" }, { idempotencyKey: "wrong" }]) assert.ok(parseFeedback({ ...valid, ...patch }).fieldErrors);
  assert.ok(parseFeedback(null).fieldErrors);
  assert.equal(parseFeedback({ ...valid, state: "la" }).submission?.state, "LA");
});

test("disabled endpoint never calls storage, and methods are limited", async () => {
  const deps = dependencies({ enabled: false, store: async () => { throw new Error("must not call"); } });
  assert.equal((await handleFeedback(request(), deps)).status, 503);
  assert.equal((await handleFeedback(new Request("https://farmfinder.example/v1/feedback"), deps)).status, 405);
});

test("rejects cross-origin, non-JSON and invalid reports before writing", async () => {
  let writes = 0;
  const deps = dependencies({ store: async () => { writes++; return { receipt: "r", replayed: false }; } });
  assert.equal((await handleFeedback(request(valid, { origin: "https://other.example" }), deps)).status, 403);
  assert.equal((await handleFeedback(request(valid, { "sec-fetch-site": "cross-site" }), deps)).status, 403);
  assert.equal((await handleFeedback(request(valid, { "content-type": "text/plain" }), deps)).status, 415);
  assert.equal((await handleFeedback(request({}), deps)).status, 400);
  assert.equal(writes, 0);
});

test("actual streamed bytes are bounded even without Content-Length", async () => {
  const body = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(12000)); controller.enqueue(new Uint8Array(12001)); controller.close(); } });
  const streamed = new Request("https://farmfinder.example/v1/feedback", { method: "POST", headers: { "content-type": "application/json" }, body, duplex: "half" } as RequestInit);
  assert.equal((await handleFeedback(streamed, dependencies())).status, 413);
});

test("pins the server release, ignores supplied release, and returns no private report fields", async () => {
  const response = await handleFeedback(request({ ...valid, releaseId: "attacker-release" }), dependencies({ store: async (submission, releaseId) => {
    assert.equal(releaseId, "release-test");
    assert.equal(submission.email, valid.email);
    assert.equal("releaseId" in submission, false);
    return { receipt: "opaque-receipt", replayed: false };
  } }));
  assert.equal(response.status, 201);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { receipt: "opaque-receipt", status: "received" });
  assert.equal((await handleFeedback(request(), dependencies({ store: async () => ({ receipt: "opaque-receipt", replayed: true }) }))).status, 200);
});

test("unknown farm, conflicting retry, quota and database failure never acknowledge success", async () => {
  assert.equal((await handleFeedback(request({ ...valid, farmId: "unknown" }), dependencies({ farmExists: async () => false }))).status, 400);
  for (const [name, expected] of [["FeedbackConflictError", 409], ["FeedbackRateLimitError", 429], ["Error", 503]] as const) {
    const response = await handleFeedback(request(), dependencies({ store: async () => { const error = new Error("secret connection details"); error.name = name; throw error; } }));
    assert.equal(response.status, expected);
    if (expected === 429) assert.equal(response.headers.get("retry-after"), "3600");
    assert.ok(!(await response.text()).includes("secret"));
  }
});
