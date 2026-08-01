import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function request(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${path}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the FarmFinder directory shell", async () => {
  const response = await request();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>FarmFinder — Find the farms behind your food<\/title>/i);
  assert.match(html, /<nav[^>]+aria-label="Primary navigation"/i);
  assert.match(html, /<main id="top">/i);
  assert.match(html, /<section[^>]+id="ask"/i);
  assert.match(html, /<section[^>]+id="discover"/i);
  assert.match(html, /299<\/strong><h3>unique farms across two states/i);
  assert.match(html, /directory includes[\s\S]{0,80}distinct farms and producers/i);
  assert.match(html, /Each listing keeps its source so details can be checked and corrected/i);
  assert.match(html, /Sources shown in every profile/i);
  assert.doesNotMatch(html, /Your site is taking shape|Codex is working/i);
});

test("server-renders the flagged nearby-first discovery shell", async () => {
  const previousFlag = process.env.EXPLORER_V2;
  process.env.EXPLORER_V2 = "true";
  try {
    const response = await request();
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /Find food from a farm near you/i);
    assert.match(html, /City or town/i);
    assert.match(html, /Set your field boundary/i);
    assert.match(html, /Browse all farms instead/i);
    assert.doesNotMatch(html, /src=["'][^"']*farms\.json/i);
  } finally {
    if (previousFlag === undefined) delete process.env.EXPLORER_V2;
    else process.env.EXPLORER_V2 = previousFlag;
  }
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

  const map = await request("/v1/farms/map?bbox=-91,29,-89,31&zoom=16");
  assert.equal(map.status, 200);
  const mapPayload = await map.json();
  assert.ok(mapPayload.features.every((feature) => feature.latitude !== 0 || feature.longitude !== 0));

  const missing = await request("/v1/farms/not-a-farm");
  assert.equal(missing.status, 404);
});

test("ships one internally consistent public farm artifact", async () => {
  const farms = JSON.parse(
    await readFile(new URL("../app/data/farms.json", import.meta.url), "utf8"),
  );

  assert.equal(farms.length, 299);
  assert.equal(new Set(farms.map((farm) => farm.id)).size, farms.length);
  assert.equal(farms.filter((farm) => farm.state === "LA").length, 220);
  assert.equal(farms.filter((farm) => farm.state === "MS").length, 79);

  for (const farm of farms) {
    assert.ok(farm.id);
    assert.ok(farm.name);
    assert.ok(farm.parish);
    assert.ok(farm.productsText);
    assert.ok(farm.source);
    assert.ok(Number.isFinite(farm.latitude));
    assert.ok(Number.isFinite(farm.longitude));
    assert.ok(farm.geoPrecision);
  }
});
