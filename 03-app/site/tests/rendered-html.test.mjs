import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const stats = JSON.parse(
  await readFile(new URL("../app/data/directory-stats.generated.json", import.meta.url), "utf8"),
);
const contract = JSON.parse(
  await readFile(new URL("../app/data/feed-contract.json", import.meta.url), "utf8"),
);

/**
 * Serve the built client directory the way Cloudflare's ASSETS binding does.
 * The discovery index is a static asset, so a stub that 404s everything would
 * silently exercise a different code path than production.
 */
const assetBinding = {
  async fetch(request) {
    const { pathname } = new URL(request.url);
    try {
      const body = await readFile(new URL(`../dist/client${pathname}`, import.meta.url));
      return new Response(body, { status: 200 });
    } catch {
      return new Response("Not found", { status: 404 });
    }
  },
};

async function request(path = "/", { legacy = false } = {}) {
  const previous = process.env.EXPLORER_LEGACY;
  if (legacy) process.env.EXPLORER_LEGACY = "true";
  else delete process.env.EXPLORER_LEGACY;

  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${Math.random()}`);
  const { default: worker } = await import(workerUrl.href);

  try {
    return await worker.fetch(
      new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
      { ASSETS: assetBinding },
      { waitUntil() {}, passThroughOnException() {} },
    );
  } finally {
    if (previous === undefined) delete process.env.EXPLORER_LEGACY;
    else process.env.EXPLORER_LEGACY = previous;
  }
}

test("the default build server-renders the national discovery shell", async () => {
  const response = await request();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<nav[^>]+aria-label="Primary navigation"/i);
  assert.match(html, /<main id="top">/i);
  assert.match(html, /<section[^>]+id="ask"/i);
  assert.match(html, /<section[^>]+id="discover"/i);
  assert.match(html, /City or town/i);
  assert.doesNotMatch(html, /Your site is taking shape|Codex is working/i);

  // The superseded 299-row workbook explorer must not be what a visitor gets.
  assert.doesNotMatch(html, /unique farms across two states/i);
  assert.doesNotMatch(html, /src=["'][^"']*farms\.json/i);
  assert.doesNotMatch(html, /\bfarms\.json\b/i);
});

test("displayed coverage language comes from the generated feed stats", async () => {
  const html = await request().then((response) => response.text());

  // Every headline number on the page must be the number the publish run
  // produced, not a figure typed into the markup.
  assert.match(html, new RegExp(`${stats.total.toLocaleString("en-US")}`));
  assert.match(html, new RegExp(`${stats.mappable.toLocaleString("en-US")}`));
  assert.match(html, new RegExp(`>${stats.states}<`));
  assert.match(html, new RegExp(stats.updatedLabel));

  // A stale hand-maintained total would show up here.
  assert.equal(stats.total >= contract.floors.total, true);
  assert.equal(stats.states, contract.expectedStates.length);
  assert.equal(stats.releaseId, contract.releaseId);
});

test("planned capabilities are not described as working ones", async () => {
  const html = await request().then((response) => response.text());
  // PostGIS and hybrid search are gated; the public page must not imply either
  // is live. Guard the specific claims, not the words themselves.
  assert.doesNotMatch(html, /powered by (postgres|postgis)/i);
  assert.doesNotMatch(html, /(ai|semantic|hybrid)[- ]powered search/i);
  assert.doesNotMatch(html, /real[- ]time (inventory|availability|stock)/i);
});

test("serves bounded discovery HTTP contracts with cache policy", async () => {
  const list = await request("/v1/farms?near=new-orleans-la&radiusMiles=50&sort=distance&limit=3");
  assert.equal(list.status, 200);
  assert.match(list.headers.get("cache-control") ?? "", /stale-while-revalidate/);
  const payload = await list.json();
  assert.equal(payload.items.length, 3);
  assert.equal(payload.scope.mode, "nearby");
  assert.equal(payload.sort, "distance");
  assert.ok(payload.total >= payload.items.length);
  assert.equal(payload.releaseId, contract.releaseId);

  const map = await request("/v1/farms/map?bbox=-91,29,-89,31&zoom=16");
  assert.equal(map.status, 200);
  const mapPayload = await map.json();
  assert.ok(mapPayload.features.every((feature) => feature.latitude !== 0 || feature.longitude !== 0));

  const missing = await request("/v1/farms/not-a-farm");
  assert.equal(missing.status, 404);
});

test("the /v1 list response exposes only public fields", async () => {
  const payload = await request("/v1/farms?limit=50").then((response) => response.json());
  const allowed = new Set([
    "id", "name", "category", "region", "parish", "state", "city", "productsText",
    "products", "marketPresence", "website", "contact", "farmersMarket", "onFarm",
    "csa", "ships", "onlineStore", "latitude", "longitude", "geoPrecision", "distanceMiles",
  ]);

  for (const farm of payload.items) {
    for (const key of Object.keys(farm)) {
      assert.equal(allowed.has(key), true, `unexpected public field "${key}"`);
    }
    // The privacy gate promotes a contact only for a farm that publishes its
    // own website. A contact without one means the gate was bypassed.
    if (farm.contact) assert.notEqual(farm.website, "", `${farm.id} exposes a contact with no website`);
    assert.doesNotMatch(farm.contact ?? "", /\d{1,6}\s+[\w.'\- ]{2,40}\s+(street|st|road|rd|ave|avenue|hwy|highway|lane|ln|drive|dr)\b/i);
  }
});

test("the rollback explorer still renders behind EXPLORER_LEGACY", async () => {
  const response = await request("/", { legacy: true });
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /unique farms across two states/i);
  assert.match(html, /Each listing keeps its source so details can be checked and corrected/i);
});

test("the superseded workbook artifact stays internally consistent but unused", async () => {
  const farms = JSON.parse(
    await readFile(new URL("../app/data/farms.json", import.meta.url), "utf8"),
  );

  assert.equal(farms.length, 299);
  assert.equal(new Set(farms.map((farm) => farm.id)).size, farms.length);
  assert.equal(farms.filter((farm) => farm.state === "LA").length, 220);
  assert.equal(farms.filter((farm) => farm.state === "MS").length, 79);

  // It is historical provenance evidence, so it must never be mistaken for the
  // national release.
  assert.ok(farms.length < stats.total);
  assert.equal(new Set(farms.map((farm) => farm.state)).size, 2);
});
