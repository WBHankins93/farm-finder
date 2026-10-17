import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Client } from "pg";
import { storeFeedback } from "../app/lib/feedback-store";
import { FeedbackReviewConflictError, FeedbackReviewNotFoundError, FeedbackReviewValidationError, listFeedbackForReview, parseReviewDecision, reviewFeedback } from "../app/lib/feedback-review-store";

const actor = { subject: "curator-123", email: "curator@example.com" };
const decision = { decision: "approve" as const, expectedRevision: 0, reason: "Confirmed by a recent firsthand visit." };
test("review decisions validate revisions, explanations and evidence links", () => {
  assert.ok(parseReviewDecision(decision).decision);
  for (const input of [null, [], { ...decision, decision: "publish" }, { ...decision, expectedRevision: -1 }, { ...decision, expectedRevision: 0.5 }, { ...decision, reason: "yes" }, { ...decision, evidenceUrl: "javascript:alert(1)" }, { ...decision, evidenceUrl: "https://user:secret@example.com" }]) assert.ok(parseReviewDecision(input).fieldErrors);
  const parsed = parseReviewDecision({ ...decision, actor: { email: "forged@example.com" } });
  assert.ok(parsed.decision);
  assert.ok(!Object.hasOwn(parsed.decision, "actor"));
});
test("review queue rejects invalid filters before connecting", async () => {
  for (const limit of [0, -1, 51, 1.5, NaN]) await assert.rejects(listFeedbackForReview("invalid", "pending", limit), FeedbackReviewValidationError);
  for (const offset of [-1, 10_001, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) await assert.rejects(listFeedbackForReview("invalid", "pending", 25, offset), FeedbackReviewValidationError);
  await assert.rejects(reviewFeedback("invalid", "invalid", decision, actor), FeedbackReviewNotFoundError);
});

// Owns its schema: use a different disposable database from intake/worker tests.
const connectionString = process.env.FEEDBACK_REVIEW_TEST_DATABASE_URL;
test("private review storage integration", { skip: !connectionString }, async (t) => {
  const database = new Client({ connectionString });
  await database.connect();
  const submit = () => storeFeedback(connectionString!, {
    idempotencyKey: randomUUID(), farmName: "Review Farm", city: "Baton Rouge", state: "LA",
    type: "closure", details: "The owner reported a seasonal closure.", relationship: "visitor", email: "reporter@example.com",
  }, "release-review-test");
  try {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    for (const migration of ["0004_feedback.sql", "0005_feedback_review.sql"]) await database.query(await readFile(new URL(`../packages/db/migrations/${migration}`, import.meta.url), "utf8"));
    await t.test("simultaneous reviewers have one winner and no stale audit events", async () => {
      const { receipt } = await submit();
      const original = await database.query("SELECT payload, release_id FROM feedback_private.submissions WHERE receipt=$1", [receipt]);
      const results = await Promise.allSettled([
        reviewFeedback(connectionString!, receipt, decision, actor),
        reviewFeedback(connectionString!, receipt, { ...decision, decision: "reject" }, actor),
      ]);
      assert.equal(results.filter((result) => result.status === "fulfilled").length, 1);
      const failure = results.find((result) => result.status === "rejected");
      assert.ok(failure?.status === "rejected" && failure.reason instanceof FeedbackReviewConflictError);
      await assert.rejects(reviewFeedback(connectionString!, receipt, decision, actor), FeedbackReviewConflictError);
      assert.equal((await database.query("SELECT count(*) FROM feedback_private.review_events WHERE receipt=$1", [receipt])).rows[0].count, "1");
      assert.deepEqual((await database.query("SELECT payload, release_id FROM feedback_private.submissions WHERE receipt=$1", [receipt])).rows, original.rows);
      const records = await listFeedbackForReview(connectionString!, "resolved");
      assert.equal(records.length, 1);
      assert.equal(records[0].revision, 1);
      assert.equal(records[0].history[0].actorEmail, actor.email);
      assert.equal(records[0].history[0].reason, decision.reason);
      assert.ok(!JSON.stringify(records).includes("reporter@example.com"));
      for (const key of ["idempotency_key", "payload_hash", "contacts", "email"]) assert.ok(!Object.hasOwn(records[0], key));
      assert.ok(!Object.hasOwn(records[0].payload, "email"));
    });
    await t.test("information requests and resolution preserve ordered history", async () => {
      const { receipt } = await submit();
      assert.deepEqual(await reviewFeedback(connectionString!, receipt, { ...decision, decision: "needs_information" }, actor), { receipt, revision: 1, status: "reviewing", outcome: "needs_information" });
      assert.equal((await listFeedbackForReview(connectionString!, "reviewing"))[0].receipt, receipt);
      await reviewFeedback(connectionString!, receipt, { ...decision, expectedRevision: 1, evidenceUrl: "https://example.com/farm-status" }, actor);
      const resolved = (await listFeedbackForReview(connectionString!, "resolved")).find((row) => row.receipt === receipt)!;
      assert.deepEqual(resolved.history.map((entry) => entry.revision), [1, 2]);
      assert.equal(resolved.history[1].evidenceUrl, "https://example.com/farm-status");
      await assert.rejects(reviewFeedback(connectionString!, randomUUID(), decision, actor), FeedbackReviewNotFoundError);
    });
    await t.test("queue is bounded and oldest first", async () => {
      const first = await submit();
      await database.query("UPDATE feedback_private.submissions SET created_at=now()-interval '1 day' WHERE receipt=$1", [first.receipt]);
      const second = await submit();
      const queue = await listFeedbackForReview(connectionString!, "pending", 1);
      assert.equal(queue.length, 1);
      assert.equal(queue[0].receipt, first.receipt);
      const next = await listFeedbackForReview(connectionString!, "pending", 1, 1);
      assert.deepEqual(next.map((row) => row.receipt), [second.receipt]);
      assert.deepEqual(await listFeedbackForReview(connectionString!, "pending", 1, 2), []);
      assert.deepEqual(await listFeedbackForReview(connectionString!, "pending", 1, 10_000), []);
    });
    await t.test("failed audit insertion rolls back disposition", async () => {
      const { receipt } = await submit();
      await database.query("ALTER TABLE feedback_private.review_events ADD CONSTRAINT simulated_failure CHECK(false) NOT VALID");
      try { await assert.rejects(reviewFeedback(connectionString!, receipt, decision, actor)); }
      finally { await database.query("ALTER TABLE feedback_private.review_events DROP CONSTRAINT simulated_failure"); }
      const record = (await listFeedbackForReview(connectionString!)).find((row) => row.receipt === receipt)!;
      assert.equal(record.revision, 0);
      assert.equal(record.status, "pending");
      assert.equal(record.history.length, 0);
    });
  } finally {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    await database.end();
  }
});
