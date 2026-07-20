import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
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
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>FarmFinder — Find the farms behind your food<\/title>/i);
  assert.match(html, /<nav[^>]+aria-label="Primary navigation"/i);
  assert.match(html, /<main id="top">/i);
  assert.match(html, /<section[^>]+id="ask"/i);
  assert.match(html, /<section[^>]+id="discover"/i);
  assert.match(html, /299[^<]*<\/strong><span>unique farms mapped/i);
  assert.match(html, /directory includes[\s\S]{0,80}299[\s\S]{0,80}distinct farms and producers/i);
  assert.match(html, /Each listing keeps its source so details can be checked and corrected/i);
  assert.match(html, /Sources shown in every profile/i);
  assert.doesNotMatch(html, /Your site is taking shape|Codex is working/i);
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
