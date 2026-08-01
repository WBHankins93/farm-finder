import { rm } from "node:fs/promises";

// The static rollback explorer still needs this ignored local artifact. The v2
// explorer uses bounded /v1 endpoints, and Sites rejects the 45 MB legacy feed.
if (process.env.EXPLORER_V2 === "true") {
  await rm(new URL("../dist/client/farms.json", import.meta.url), { force: true });
}
