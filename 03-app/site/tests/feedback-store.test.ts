import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Client } from "pg";
import type { FeedbackSubmission } from "../app/lib/feedback-contract";
import { FeedbackConflictError, FeedbackRateLimitError, storeFeedback } from "../app/lib/feedback-store";

// Explicitly opt into a disposable database: this suite owns feedback_private.
const connectionString = process.env.FEEDBACK_TEST_DATABASE_URL;
test("feedback storage integration (disposable PostgreSQL)", { skip: !connectionString }, async (t) => {
  const database = new Client({ connectionString });
  await database.connect();
  const sample = (): FeedbackSubmission => ({
    idempotencyKey: randomUUID(), farmName: "Test Farm", city: "Baton Rouge", state: "LA",
    type: "correction", details: "The market opens on Saturday.", relationship: "visitor",
    email: "visitor@example.com",
  });
  const clear = () => database.query("TRUNCATE feedback_private.submissions CASCADE");
  try {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    await database.query(await readFile(new URL("../packages/db/migrations/0004_feedback.sql", import.meta.url), "utf8"));
    await t.test("concurrent identical retries create one receipt, contact and pending job", async () => {
      const submission = sample();
      const results = await Promise.all(Array.from({ length: 6 }, () => storeFeedback(connectionString!, submission, "release-a")));
      assert.equal(new Set(results.map((result) => result.receipt)).size, 1);
      assert.equal(results.filter((result) => !result.replayed).length, 1);
      assert.notEqual(results[0].receipt, submission.idempotencyKey);
      const rows = await database.query("SELECT s.*, c.email, j.status AS job_status FROM feedback_private.submissions s JOIN feedback_private.contacts c USING (receipt) JOIN feedback_private.processing_jobs j USING (receipt)");
      assert.equal(rows.rows.length, 1);
      assert.equal(rows.rows[0].payload.email, undefined);
      assert.equal(rows.rows[0].email, submission.email);
      assert.equal(rows.rows[0].job_status, "pending");
      assert.equal(rows.rows[0].release_id, "release-a");
      await assert.rejects(storeFeedback(connectionString!, { ...submission, email: "different@example.com" }, "release-a"), FeedbackConflictError);
      const replay = await storeFeedback(connectionString!, submission, "release-b", async () => { throw new Error("Listing no longer exists"); });
      assert.equal(replay.receipt, results[0].receipt);
    });
    await t.test("concurrent different payloads cannot reuse one retry key", async () => {
      await clear();
      const submission = sample();
      const results = await Promise.allSettled([
        storeFeedback(connectionString!, submission, "release-a"),
        storeFeedback(connectionString!, { ...submission, details: "A conflicting report." }, "release-a"),
      ]);
      assert.equal(results.filter((result) => result.status === "fulfilled").length, 1);
      const failure = results.find((result) => result.status === "rejected");
      assert.ok(failure && failure.status === "rejected" && failure.reason instanceof FeedbackConflictError);
    });
    await t.test("invalid new listing rolls back without creating a report", async () => {
      await clear();
      await assert.rejects(storeFeedback(connectionString!, sample(), "release-a", async () => { throw new Error("Unknown farm"); }));
      assert.equal((await database.query("SELECT count(*) FROM feedback_private.submissions")).rows[0].count, "0");
    });
    await t.test("processing failure rolls back report and private contact", async () => {
      await clear();
      await database.query("ALTER TABLE feedback_private.processing_jobs ADD CONSTRAINT simulate_failure CHECK (false) NOT VALID");
      try {
        await assert.rejects(storeFeedback(connectionString!, sample(), "release-a"));
        for (const table of ["submissions", "contacts", "processing_jobs"]) {
          assert.equal((await database.query(`SELECT count(*) FROM feedback_private.${table}`)).rows[0].count, "0");
        }
      } finally {
        await database.query("ALTER TABLE feedback_private.processing_jobs DROP CONSTRAINT simulate_failure");
      }
    });
    await t.test("global hourly cap permits retries and expires old reports", async () => {
      await clear();
      const submission = sample();
      const first = await storeFeedback(connectionString!, submission, "release-a");
      for (let index = 0; index < 119; index++) {
        await database.query("INSERT INTO feedback_private.submissions (receipt,idempotency_key,payload_hash,payload,release_id) VALUES ($1,$2,$3,'{}','fixture')", [randomUUID(), randomUUID(), "a".repeat(64)]);
      }
      await assert.rejects(storeFeedback(connectionString!, sample(), "release-a"), FeedbackRateLimitError);
      assert.deepEqual(await storeFeedback(connectionString!, submission, "release-a"), { receipt: first.receipt, replayed: true });
      assert.equal((await database.query("SELECT count(*) FROM feedback_private.submissions")).rows[0].count, "120");
      await database.query("UPDATE feedback_private.submissions SET created_at = now() - interval '2 hours'");
      assert.equal((await storeFeedback(connectionString!, sample(), "release-a")).replayed, false);
    });
    await t.test("PUBLIC has no schema or table grants", async () => {
      const schema = await database.query("SELECT count(*) FROM pg_namespace n, aclexplode(n.nspacl) a WHERE n.nspname = 'feedback_private' AND a.grantee = 0");
      assert.equal(schema.rows[0].count, "0");
      const tables = await database.query("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE n.nspname = 'feedback_private' AND a.grantee = 0");
      assert.equal(tables.rows[0].count, "0");
      await assert.rejects(database.query("INSERT INTO feedback_private.submissions (receipt,idempotency_key,payload_hash,payload,release_id) VALUES ($1,$2,$3,$4,'fixture')", [randomUUID(), randomUUID(), "b".repeat(64), JSON.stringify({ email: "private@example.com" })]));
    });
  } finally {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    await database.end();
  }
});
