import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Client } from "pg";
import { processFeedbackBatch, triageFeedback } from "../app/lib/feedback-worker";

test("triage normalizes candidate groups and prioritizes consequential reports", async () => {
  const first = await triageFeedback({ farmName: " Test  Farm ", city: "Baton Rouge", state: "LA", type: "closure" });
  const second = await triageFeedback({ farmName: "test farm", city: "baton rouge", state: "la", type: "correction" });
  assert.equal(first.relatedGroup, second.relatedGroup);
  assert.equal(first.priority, "high");
  assert.equal(second.priority, "normal");
  assert.notEqual(first.relatedGroup, (await triageFeedback({ farmId: "farm-123" })).relatedGroup);
});
test("worker rejects unbounded batches before connecting", async () => {
  for (const limit of [0, 11, 1.5, NaN, Infinity]) await assert.rejects(processFeedbackBatch("invalid", { limit }));
});

const connectionString = process.env.FEEDBACK_WORKER_TEST_DATABASE_URL;
test("leased feedback worker (disposable PostgreSQL)", { skip: !connectionString }, async (t) => {
  const database = new Client({ connectionString });
  await database.connect();
  const clear = () => database.query("TRUNCATE feedback_private.submissions CASCADE");
  const seed = async () => {
    const receipt = randomUUID();
    await database.query("INSERT INTO feedback_private.submissions (receipt,idempotency_key,payload_hash,payload,release_id) VALUES ($1,$2,$3,$4,'test')", [receipt, randomUUID(), "a".repeat(64), JSON.stringify({ farmName: "Test Farm", city: "Baton Rouge", state: "LA", type: "closure" })]);
    await database.query("INSERT INTO feedback_private.processing_jobs (receipt) VALUES ($1)", [receipt]);
    return receipt;
  };
  const job = async (receipt: string) => (await database.query("SELECT * FROM feedback_private.processing_jobs WHERE receipt=$1", [receipt])).rows[0];
  try {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    for (const migration of ["0004_feedback.sql", "0005_feedback_review.sql"]) {
      await database.query(await readFile(new URL(`../packages/db/migrations/${migration}`, import.meta.url), "utf8"));
    }
    await t.test("concurrent workers claim once, preserve review decisions, and never read contacts", async () => {
      const receipts = await Promise.all(Array.from({ length: 8 }, seed));
      await database.query("UPDATE feedback_private.submissions SET status='resolved',review_outcome='reject',review_revision=1");
      await database.query("ALTER TABLE feedback_private.contacts RENAME TO contacts_unavailable");
      try {
        const results = await Promise.all([processFeedbackBatch(connectionString!, { limit: 5 }), processFeedbackBatch(connectionString!, { limit: 5 })]);
        assert.equal(results.reduce((sum, row) => sum + row.claimed, 0), 8);
        assert.equal(results.reduce((sum, row) => sum + row.completed, 0), 8);
        for (const receipt of receipts) assert.equal((await job(receipt)).attempts, 1);
        for (const row of (await database.query("SELECT status,review_outcome,review_revision,triage FROM feedback_private.submissions")).rows) {
          assert.equal(row.status, "resolved");
          assert.equal(row.review_revision, 1);
          assert.equal(row.review_outcome, "reject");
          assert.equal(row.triage.priority, "high");
        }
        assert.equal((await database.query("SELECT count(*) FROM feedback_private.review_events")).rows[0].count, "0");
        // Canonical directory tables do not exist in this isolated database.
      } finally { await database.query("ALTER TABLE feedback_private.contacts_unavailable RENAME TO contacts"); }
    });
    await t.test("expired leases recover and crashed fifth attempts become terminal", async () => {
      await clear();
      const recover = await seed();
      const exhausted = await seed();
      await database.query("UPDATE feedback_private.processing_jobs SET status='processing', attempts=2,lease_token=$1,lease_expires_at=now()-interval '1 minute'", [randomUUID()]);
      await database.query("UPDATE feedback_private.processing_jobs SET attempts=5 WHERE receipt=$1", [exhausted]);
      assert.deepEqual(await processFeedbackBatch(connectionString!), { claimed: 1, completed: 1, failed: 1, retried: 0 });
      assert.equal((await job(recover)).attempts, 3);
      assert.equal((await job(exhausted)).status, "failed");
      assert.equal((await job(exhausted)).last_error_code, "attempts_exhausted");
    });
    for (const fails of [false, true]) {
      await t.test(`stale ${fails ? "failure" : "completion"} cannot change a reclaimed job`, async () => {
        await clear();
        const receipt = await seed();
        let started!: () => void;
        let release!: () => void;
        const entered = new Promise<void>((resolve) => { started = resolve; });
        const blocked = new Promise<void>((resolve) => { release = resolve; });
        const old = processFeedbackBatch(connectionString!, { process: async () => {
          started(); await blocked;
          if (fails) throw new Error("stale failure");
          return { source: "stale" };
        } });
        await entered;
        try {
          await database.query("UPDATE feedback_private.processing_jobs SET lease_expires_at=now()-interval '1 second' WHERE receipt=$1", [receipt]);
          assert.equal((await processFeedbackBatch(connectionString!, { process: async () => ({ source: "current" }) })).completed, 1);
        } finally { release(); }
        assert.deepEqual(await old, { claimed: 1, completed: 0, failed: 0, retried: 0 });
        assert.equal((await job(receipt)).status, "completed");
        assert.equal((await database.query("SELECT triage FROM feedback_private.submissions WHERE receipt=$1", [receipt])).rows[0].triage.source, "current");
      });
    }
    await t.test("failures back off, redact errors, and stop after five attempts", async () => {
      await clear();
      const receipt = await seed();
      const process = async () => { throw new Error("sensitive reporter data"); };
      for (let attempt = 1; attempt <= 5; attempt++) {
        const result = await processFeedbackBatch(connectionString!, { process });
        assert.equal(result[attempt === 5 ? "failed" : "retried"], 1);
        const current = await job(receipt);
        assert.equal(current.attempts, attempt);
        assert.equal(current.last_error_code, "processing_failed");
        assert.equal(current.lease_token, null);
        assert.ok(current.available_at.getTime() - Date.now() >= 30 * 2 ** (attempt - 1) * 1000 - 2000);
        assert.equal((await processFeedbackBatch(connectionString!, { process })).claimed, 0);
        await database.query("UPDATE feedback_private.processing_jobs SET available_at=now()-interval '1 second' WHERE receipt=$1", [receipt]);
      }
      assert.equal((await processFeedbackBatch(connectionString!, { process })).claimed, 0);
      assert.equal((await database.query("SELECT triage FROM feedback_private.submissions WHERE receipt=$1", [receipt])).rows[0].triage, null);
    });
  } finally {
    await database.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    await database.end();
  }
});
