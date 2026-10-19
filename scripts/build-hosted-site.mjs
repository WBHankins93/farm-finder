import { spawnSync } from "node:child_process";
import { cp, readFile, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";

const root = new URL("../", import.meta.url);
const site = new URL("03-app/site/", root);
const readManifest = async (base) => JSON.parse(await readFile(new URL(".openai/hosting.json", base), "utf8"));
// The publisher opens the repository root; Vite builds from the app directory.
// Refuse to deploy if these entrypoints point to different Sites or bindings.
if (!isDeepStrictEqual(await readManifest(root), await readManifest(site))) {
  throw new Error("Root and app hosting manifests disagree; reconcile them before building.");
}
await rm(new URL("dist/", root), { recursive: true, force: true });
const result = spawnSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], {
  cwd: fileURLToPath(site), stdio: "inherit", env: process.env,
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
await cp(new URL("dist/", site), new URL("dist/", root), { recursive: true });
console.log("Hosted artifact staged at repository-root dist/ (generated, ignored).");
