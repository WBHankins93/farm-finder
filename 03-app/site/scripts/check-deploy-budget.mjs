/**
 * Post-build deployment gate for the Cloudflare target.
 *
 * The national dataset makes two platform limits load-bearing, and both are
 * invisible until a deploy actually fails:
 *
 *   - a Worker script may not exceed 10 MiB compressed on the Paid plan
 *     (3 MiB on Free), and
 *   - a single static asset may not exceed 25 MiB.
 *
 * The 45 MB rollback feed breaches the second, which is why it is pruned from
 * a default build rather than shipped. This script asserts both limits so a
 * regression fails here instead of at `wrangler deploy`.
 */
import { gzipSync } from "node:zlib";
import { readFile, readdir, rm, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const MIB = 1024 * 1024;
const WORKER_LIMIT_PAID = 10 * MIB;
const WORKER_LIMIT_FREE = 3 * MIB;
const ASSET_LIMIT = 25 * MIB;

const mb = (bytes) => `${(bytes / MIB).toFixed(2)} MiB`;

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((entry) => {
      const full = path.join(directory, entry.name);
      return entry.isDirectory() ? walk(full) : Promise.resolve([full]);
    }),
  );
  return files.flat();
}

// The rollback explorer's 45 MB client feed is larger than a Cloudflare asset
// may be. It exists only for a local `EXPLORER_LEGACY=true` run.
if (process.env.EXPLORER_LEGACY !== "true") {
  await rm(new URL("../dist/client/farms.json", import.meta.url), { force: true });
}

const failures = [];
const warnings = [];

const serverFiles = (await walk(path.join(dist, "server"))).filter((file) => file.endsWith(".js"));
let workerBytes = 0;
for (const file of serverFiles) {
  workerBytes += gzipSync(await readFile(file), { level: 9 }).byteLength;
}

if (workerBytes > WORKER_LIMIT_PAID) {
  failures.push(
    `worker script is ${mb(workerBytes)} compressed, over the ${mb(WORKER_LIMIT_PAID)} Paid-plan limit`,
  );
} else if (workerBytes > WORKER_LIMIT_FREE) {
  warnings.push(
    `worker script is ${mb(workerBytes)} compressed — fits the ${mb(WORKER_LIMIT_PAID)} Paid-plan limit but exceeds the ${mb(WORKER_LIMIT_FREE)} Free-plan limit`,
  );
}

const clientFiles = await walk(path.join(dist, "client"));
let largestAsset = { file: "", size: 0 };
for (const file of clientFiles) {
  const { size } = await stat(file);
  if (size > largestAsset.size) largestAsset = { file: path.relative(dist, file), size };
  if (size > ASSET_LIMIT) {
    failures.push(`asset ${path.relative(dist, file)} is ${mb(size)}, over the ${mb(ASSET_LIMIT)} limit`);
  }
}

const indexAsset = clientFiles.find((file) => file.endsWith("national-index.bin"));
if (!indexAsset) {
  failures.push("dist/client/national-index.bin is missing — /v1 discovery would 500 at runtime");
}

console.log("deploy budget:");
console.log(`  worker script (gzip) ${mb(workerBytes)} / ${mb(WORKER_LIMIT_PAID)} paid, ${mb(WORKER_LIMIT_FREE)} free`);
console.log(`  largest asset        ${mb(largestAsset.size)} / ${mb(ASSET_LIMIT)} — ${largestAsset.file}`);
console.log(`  client files         ${clientFiles.length}`);
for (const warning of warnings) console.log(`  WARNING: ${warning}`);

if (failures.length > 0) {
  console.error(`\nDEPLOY BUDGET FAILED:\n  - ${failures.join("\n  - ")}`);
  process.exit(1);
}
