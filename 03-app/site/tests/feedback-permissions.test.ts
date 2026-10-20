import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Client } from "pg";

// Invoked sequentially after review integration by the required runner.
test("feedback runtime grants deny private data and unauthorized writes", { skip: !process.env.FEEDBACK_REVIEW_TEST_DATABASE_URL }, async () => {
  const db = new Client({ connectionString: process.env.FEEDBACK_REVIEW_TEST_DATABASE_URL });
  await db.connect();
  const prefix = `feedback_test_${randomUUID().replaceAll("-", "")}`;
  const roles = ["intake", "review", "worker"].map((role) => `${prefix}_${role}`);
  try {
    await db.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    for (const file of ["0004_feedback.sql", "0005_feedback_review.sql"]) {
      await db.query(await readFile(new URL(`../packages/db/migrations/${file}`, import.meta.url), "utf8"));
    }
    for (const role of roles) {
      await db.query(`CREATE ROLE ${role} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`);
      await db.query(`GRANT USAGE ON SCHEMA feedback_private TO ${role}`);
    }
    await db.query(`GRANT SELECT, INSERT ON feedback_private.submissions TO ${roles[0]}`);
    await db.query(`GRANT INSERT ON feedback_private.contacts, feedback_private.processing_jobs TO ${roles[0]}`);
    await db.query(`GRANT SELECT (receipt,payload,release_id,status,review_revision,triage,review_outcome,created_at), UPDATE (review_revision,status,review_outcome) ON feedback_private.submissions TO ${roles[1]}`);
    await db.query(`GRANT SELECT (receipt,revision,decision,reason,evidence_url,actor_email,created_at), INSERT (id,receipt,revision,actor_subject,actor_email,decision,reason,evidence_url) ON feedback_private.review_events TO ${roles[1]}`);
    await db.query(`GRANT SELECT (receipt,payload), UPDATE (triage) ON feedback_private.submissions TO ${roles[2]}`);
    await db.query(`GRANT SELECT (receipt,status,attempts,available_at,lease_token,lease_expires_at), UPDATE (status,attempts,available_at,lease_token,lease_expires_at,last_error_code) ON feedback_private.processing_jobs TO ${roles[2]}`);
    for (const [index, role] of roles.entries()) {
      await db.query(`SET ROLE ${role}`);
      await db.query("SELECT receipt,payload FROM feedback_private.submissions");
      for (const sql of [
        "SELECT * FROM feedback_private.contacts",
        "DELETE FROM feedback_private.submissions",
        "UPDATE feedback_private.review_events SET reason='tampered'",
        "CREATE TABLE feedback_private.unauthorized (id int)",
        ...(index === 1 || index === 2 ? ["SELECT idempotency_key,payload_hash FROM feedback_private.submissions"] : []),
        ...(index !== 1 ? ["UPDATE feedback_private.submissions SET review_outcome='approve'"] : []),
        ...(index !== 2 ? ["UPDATE feedback_private.submissions SET triage='{}'"] : []),
      ]) {
        await assert.rejects(db.query(sql), (error: unknown) => (error as { code?: string }).code === "42501", `${role.split("_").at(-1)} unexpectedly permitted: ${sql}`);
      }
      await db.query("RESET ROLE");
    }
  } finally {
    await db.query("RESET ROLE");
    await db.query("DROP SCHEMA IF EXISTS feedback_private CASCADE");
    for (const role of roles) await db.query(`DROP ROLE IF EXISTS ${role}`);
    await db.end();
  }
});
