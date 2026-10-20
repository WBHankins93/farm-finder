/** Required CI entrypoint. All four databases must be disposable: suites drop schemas. */
import { spawnSync } from "node:child_process";

const variables = [
  "FEEDBACK_TEST_DATABASE_URL",
  "FEEDBACK_REVIEW_TEST_DATABASE_URL",
  "FEEDBACK_WORKER_TEST_DATABASE_URL",
  "FEEDBACK_HTTP_TEST_DATABASE_URL",
];
const databases = variables.map((name) => {
  // Do not print connection strings, including on parse errors.
  let url;
  try { url = new URL(process.env[name]); } catch { throw new Error(`${name} is required and must be a PostgreSQL URL`); }
  if (!["postgres:", "postgresql:"].includes(url.protocol) || !/^\/ff_feedback_ci_[a-z0-9_]+$/.test(url.pathname)) {
    throw new Error(`${name} must name an explicitly disposable ff_feedback_ci_ database`);
  }
  return decodeURIComponent(url.pathname);
});
if (new Set(databases).size !== variables.length) throw new Error("Feedback suites require four distinct disposable databases");

function requiredTests(files, env = process.env) {
  const result = spawnSync(process.execPath, ["--import", "tsx", "--test", "--test-reporter=tap", ...files], {
    env, encoding: "utf8", maxBuffer: 16 * 1024 * 1024,
  });
  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  if (result.error || result.status !== 0) throw new Error("Required feedback integration process failed");
  const output = result.stdout;
  if (!/^# tests [1-9]\d*$/m.test(output) || !/^# skipped 0$/m.test(output) || !/^# todo 0$/m.test(output) || /^\s*(?:not )?ok .*# (?:SKIP|TODO)\b/im.test(output)) {
    throw new Error("Required feedback integrations must execute tests with zero skips or TODOs");
  }
}

requiredTests(["tests/feedback-store.test.ts", "tests/feedback-review-store.test.ts", "tests/feedback-worker.test.ts"]);
requiredTests(["tests/feedback-permissions.test.ts"]);
// The HTTP suite owns a fourth schema and runs against the built server.
requiredTests(["tests/rendered-html.test.mjs"], {
  ...process.env, FEEDBACK_TEST_DATABASE_URL: process.env.FEEDBACK_HTTP_TEST_DATABASE_URL,
});
