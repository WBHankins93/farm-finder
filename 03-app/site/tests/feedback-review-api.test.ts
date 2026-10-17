import assert from "node:assert/strict";
import test from "node:test";
import { FeedbackAuthError } from "../app/lib/feedback-auth";
import { handleFeedbackReview } from "../app/lib/feedback-review-handler";
import { FeedbackReviewConflictError, FeedbackReviewNotFoundError, FeedbackReviewValidationError } from "../app/lib/feedback-review-store";

type Dependencies = NonNullable<Parameters<typeof handleFeedbackReview>[2]>;
const actor = { subject: "verified-subject", email: "curator@example.com" };
const receipt = "7a2ce124-7380-4dbe-8307-1296c50936a2";
const valid = { receipt, decision: "approve", expectedRevision: 0, reason: "Confirmed against the farm's own published information." };
const counts = { completed: 1, failed: 0, retried: 0, claimed: 1 };
function dependencies(overrides: Partial<Dependencies> = {}): Dependencies {
  return {
    authenticate: async () => actor,
    list: async () => [],
    decide: async () => ({ receipt, revision: 1, status: "resolved", outcome: "approve" }),
    process: async () => counts,
    ...overrides,
  };
}
function post(body: unknown = valid, extraHeaders: Record<string, string> = {}) {
  return new Request("https://farmfinder.example/v1/feedback/review", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json", ...extraHeaders } });
}
function assertPrivate(response: Response) {
  assert.equal(response.headers.get("cache-control"), "private, no-store");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(response.headers.get("vary"), "Cf-Access-Jwt-Assertion");
}

test("every review/process method authenticates before parsing or touching storage", async () => {
  let calls = 0;
  const never = async (): Promise<never> => { calls++; throw new Error("Storage must not be called"); };
  for (const status of [401, 403, 503] as const) {
    for (const mode of ["review", "process"] as const) {
      for (const method of ["GET", "POST", "DELETE"]) {
        const request = new Request("https://farmfinder.example/v1/feedback/review?status=invalid", { method, ...(method === "POST" ? { body: "not JSON" } : {}) });
        const response = await handleFeedbackReview(request, mode, dependencies({ authenticate: async () => { throw new FeedbackAuthError(status); }, list: never, decide: never, process: never }));
        assert.equal(response.status, status);
        assert.equal(request.bodyUsed, false);
        assertPrivate(response);
      }
    }
  }
  assert.equal(calls, 0);
});

test("list defaults to pending and validates status before queries", async () => {
  const seen: string[] = [];
  const deps = dependencies({ list: async (status) => { seen.push(status); return []; } });
  for (const status of ["", "?status=pending", "?status=reviewing", "?status=resolved"]) {
    const response = await handleFeedbackReview(new Request(`https://farmfinder.example/v1/feedback/review${status}`), "review", deps);
    assert.equal(response.status, 200);
    assertPrivate(response);
    assert.deepEqual(await response.json(), { reports: [] });
  }
  assert.equal((await handleFeedbackReview(new Request("https://farmfinder.example/v1/feedback/review?status=private"), "review", deps)).status, 400);
  assert.deepEqual(seen, ["pending", "pending", "reviewing", "resolved"]);
});

test("decision uses verified identity and ignores body-supplied actor fields", async () => {
  let writes = 0;
  const response = await handleFeedbackReview(post({ ...valid, actor: { subject: "forged", email: "attacker@example.com" }, actorEmail: "forged@example.com", subject: "forged" }), "review", dependencies({
    decide: async (id, decision, reviewer) => {
      writes++;
      assert.equal(id, receipt);
      assert.deepEqual(reviewer, actor);
      assert.deepEqual(decision, { decision: "approve", expectedRevision: 0, reason: valid.reason, evidenceUrl: undefined });
      return { receipt, revision: 1, status: "resolved", outcome: "approve" };
    },
  }));
  assert.equal(response.status, 200);
  assert.equal(writes, 1);
  assertPrivate(response);
});

test("cross-origin review and process actions are rejected without writes", async () => {
  let writes = 0;
  const never = async (): Promise<never> => { writes++; throw new Error(); };
  for (const mode of ["review", "process"] as const) {
    const crossOriginHeaders: Record<string, string>[] = [{ origin: "https://attacker.example" }, { "sec-fetch-site": "cross-site" }];
    for (const headers of crossOriginHeaders) {
      const response = await handleFeedbackReview(post(valid, headers), mode, dependencies({ decide: never, process: never }));
      assert.equal(response.status, 403);
      assertPrivate(response);
    }
  }
  assert.equal(writes, 0);
});

test("invalid decisions, receipts, body types and oversized streams never write", async () => {
  let writes = 0;
  const deps = dependencies({ decide: async () => { writes++; throw new Error(); } });
  for (const input of [null, [], {}, { ...valid, receipt: "wrong" }, { ...valid, decision: "publish" }, { ...valid, expectedRevision: -1 }, { ...valid, reason: "short" }, { ...valid, evidenceUrl: "javascript:alert(1)" }]) {
    assert.equal((await handleFeedbackReview(post(input), "review", deps)).status, 400);
  }
  assert.equal((await handleFeedbackReview(post(valid, { "content-type": "text/plain" }), "review", deps)).status, 415);
  assert.equal((await handleFeedbackReview(post(valid, { "content-length": "8193" }), "review", deps)).status, 413);
  assert.equal((await handleFeedbackReview(post({ ...valid, reason: "x".repeat(9000) }), "review", deps)).status, 413);
  for (const body of ["{", ""]) {
    assert.equal((await handleFeedbackReview(new Request("https://farmfinder.example/v1/feedback/review", { method: "POST", body, headers: { "content-type": "application/json" } }), "review", deps)).status, 400);
  }
  assert.equal(writes, 0);
});

test("known storage failures map to safe errors; unexpected failures expose no details", async () => {
  for (const [error, status] of [[new FeedbackReviewConflictError(), 409], [new FeedbackReviewNotFoundError(), 404], [new FeedbackReviewValidationError({ reason: "Provide evidence." }), 400], [new Error("postgres://private-secret@example.invalid"), 503]] as const) {
    const response = await handleFeedbackReview(post(), "review", dependencies({ decide: async () => { throw error; } }));
    assert.equal(response.status, status);
    assertPrivate(response);
    assert.ok(!(await response.text()).includes("private-secret"));
  }
  for (const mode of ["review", "process"] as const) {
    const fail = async (): Promise<never> => { throw new Error("private-secret"); };
    const response = await handleFeedbackReview(mode === "review" ? new Request("https://farmfinder.example/v1/feedback/review") : post(), mode, dependencies({ list: fail, process: fail }));
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), { error: "Feedback review is temporarily unavailable." });
  }
});

test("process requires authentication and POST, then calls only the bounded worker", async () => {
  const sequence: string[] = [];
  const deps = dependencies({ authenticate: async () => { sequence.push("authenticate"); return actor; }, process: async () => { sequence.push("process"); return counts; }, list: async () => { throw new Error("not list"); }, decide: async () => { throw new Error("not decide"); } });
  const rejected = await handleFeedbackReview(new Request("https://farmfinder.example/v1/feedback/process"), "process", deps);
  assert.equal(rejected.status, 405);
  const response = await handleFeedbackReview(post({}, { origin: "https://farmfinder.example" }), "process", deps);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), counts);
  assert.deepEqual(sequence, ["authenticate", "authenticate", "process"]);
  assertPrivate(response);
  assert.equal((await handleFeedbackReview(new Request("https://farmfinder.example/v1/feedback/review", { method: "DELETE" }), "review", dependencies())).status, 405);
});

test("pagination defaults to zero and rejects malformed or excessive offsets before querying", async () => {
  const offsets: number[] = [];
  const deps = dependencies({ list: async (_status, offset) => { offsets.push(offset); return []; } });
  for (const query of ["", "?offset=25", "?offset=10000"]) {
    assert.equal((await handleFeedbackReview(new Request(`https://farmfinder.example/v1/feedback/review${query}`), "review", deps)).status, 200);
  }
  for (const offset of ["", "-1", "1.5", "NaN", "Infinity", "10001", "9007199254740992", "1e3", " 25"]) {
    const request = new Request(`https://farmfinder.example/v1/feedback/review?offset=${encodeURIComponent(offset)}`);
    assert.equal((await handleFeedbackReview(request, "review", deps)).status, 400);
  }
  assert.deepEqual(offsets, [0, 25, 10000]);
});
