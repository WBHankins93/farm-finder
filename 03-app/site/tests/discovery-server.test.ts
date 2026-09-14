import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { discoveryDatasetSummary, getFarm, isMappableFarm, mapFarms, parseDiscoveryQuery, searchFarms, searchPlaces } from "../app/lib/discovery-server";

const expectedStates = [
  "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD",
  "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH",
  "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
];

function query(value = "") {
  return parseDiscoveryQuery(new URLSearchParams(value));
}

test("discovery uses the complete governed national release", async () => {
  const summary = await discoveryDatasetSummary();
  assert.equal(summary.total, 68_618);
  assert.deepEqual(summary.states, expectedStates);
  assert.equal(summary.states.includes("ZZ"), false);
});

test("normalizes discovery query defaults, bounds, services, and limits", () => {
  const parsed = query("q=eggs&radiusMiles=71&bbox=-91,29,-89,31&services=onFarm,csa&services=csa&limit=999");
  assert.equal(parsed.radiusMiles, 50);
  assert.deepEqual(parsed.bbox, [-91, 29, -89, 31]);
  assert.deepEqual(parsed.services, ["onFarm", "csa"]);
  assert.equal(parsed.limit, 50);
  assert.equal(parsed.sort, "relevance");
});

test("rejects invalid bounds and coordinates", () => {
  const parsed = query("bbox=10,20,5,25&lat=120&lng=-90&limit=-3");
  assert.equal(parsed.bbox, null);
  assert.equal(parsed.origin, null);
  assert.equal(parsed.limit, 1);
});

test("nearby browsing returns a normalized 50-mile scope in nearest order", async () => {
  const result = await searchFarms(query("near=new-orleans-la&sort=distance&limit=50"));
  assert.equal(result.scope.mode, "nearby");
  assert.equal(result.scope.label, "New Orleans, LA");
  assert.equal(result.scope.radiusMiles, 50);
  const distances = result.items.map((farm) => farm.distanceMiles ?? Number.POSITIVE_INFINITY);
  assert.deepEqual(distances, [...distances].sort((a, b) => a - b));
});

test("cursor pagination is stable, accumulates without duplicates, and uses opaque cursors", async () => {
  const first = await searchFarms(query("sort=name&limit=7"));
  assert.ok(first.nextCursor);
  assert.doesNotMatch(first.nextCursor, /^\d+$/);
  const second = await searchFarms(query(`sort=name&limit=7&cursor=${encodeURIComponent(first.nextCursor!)}`));
  const combined = [...first.items, ...second.items];
  assert.equal(new Set(combined.map((farm) => farm.id)).size, 14);
  const reference = await searchFarms(query("sort=name&limit=14"));
  assert.deepEqual(combined.map((farm) => farm.id), reference.items.map((farm) => farm.id));
});

test("filters use AND across category, product, and each service", async () => {
  const result = await searchFarms(query("category=Produce&product=vegetables&services=onFarm,csa&limit=50"));
  assert.ok(result.total > 0);
  for (const farm of result.items) {
    assert.equal(farm.category, "Produce");
    assert.equal(farm.onFarm, true);
    assert.equal(farm.csa, true);
  }
});

test("list count and map count agree for a bounded public area", async () => {
  const parsed = query("bbox=-91,29,-89,31&product=vegetables&services=onFarm&limit=50");
  const list = await searchFarms(parsed);
  const map = await mapFarms(parsed, 9);
  assert.equal(map.total, list.total);
  assert.ok(map.features.every((feature) => Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude)));
});

test("shared approximate coordinates remain terminal clusters at maximum zoom", async () => {
  const map = await mapFarms(query("bbox=-91,29,-89,31"), 16);
  const cluster = map.features.find((feature) => feature.kind === "cluster" && feature.terminal);
  assert.ok(cluster && cluster.kind === "cluster");
  assert.ok(cluster.count > 1);
  assert.equal(cluster.bounds[0], cluster.bounds[2]);
  assert.equal(cluster.bounds[1], cluster.bounds[3]);
  assert.equal(cluster.farmIds?.length, cluster.count);
});

test("zero, missing, non-finite, and explicitly ungeocoded coordinates are never mappable", async () => {
  const base = (await getFarm("vintage-garden-farms-la"))!;
  assert.equal(isMappableFarm({ ...base, latitude: 0, longitude: 0 }), false);
  assert.equal(isMappableFarm({ ...base, latitude: Number.NaN }), false);
  assert.equal(isMappableFarm({ ...base, geoPrecision: "ungeocoded" }), false);
  assert.equal(isMappableFarm(base), true);
});

test("place suggestions are governed, bounded, and profile lookup does not depend on a list page", async () => {
  const places = await searchPlaces("new", 99);
  assert.ok(places.items.length > 0 && places.items.length <= 8);
  assert.equal(places.items[0].label, "New Orleans, LA");
  const farm = await getFarm("vintage-garden-farms-la");
  assert.equal(farm?.name, "Vintage Garden Farms");
  assert.equal(await getFarm("missing-farm"), null);
});

test("public summaries tolerate long names and missing contact paths", async () => {
  const result = await searchFarms(query("limit=50"));
  const missingContact = result.items.find((farm) => !farm.contact && !farm.website);
  assert.ok(missingContact);
  const longest = result.items.reduce((current, farm) => farm.name.length > current.name.length ? farm : current);
  assert.ok(longest.name.length > 20);
  assert.equal(typeof longest.productsText, "string");
});

test("the question the Ask box suggests actually returns farms", async () => {
  // Text search requires every token, so conversational framing words must be
  // stripped. Before they were, this exact placeholder returned zero results.
  const asked = await searchFarms(query(`q=${encodeURIComponent("Who sells goat cheese?")}&sort=relevance&limit=6`));
  assert.ok(asked.total > 0, "the placeholder question must match farms");

  const bare = await searchFarms(query("q=goat%20cheese&sort=relevance&limit=6"));
  assert.equal(asked.total, bare.total, "question words must not change the result set");
});

test("free-text search folds case and diacritics the way the index was built", async () => {
  const plain = await searchFarms(query("q=cafe&limit=5"));
  const accented = await searchFarms(query(`q=${encodeURIComponent("Café")}&limit=5`));
  assert.equal(accented.total, plain.total);
});

test("product browse counts equal the product filter's own result count", async () => {
  // The homepage tiles show these totals, so a drift here is a visible lie.
  const stats = JSON.parse(
    await readFile(new URL("../app/data/directory-stats.generated.json", import.meta.url), "utf8"),
  ) as { products: Record<string, number> };

  for (const product of Object.keys(stats.products)) {
    const filtered = await searchFarms(query(`product=${product}&limit=1`));
    assert.equal(filtered.total, stats.products[product], `${product} tile disagrees with its filter`);
  }
});

test("no published record exposes a contact without a farm-published website", async () => {
  // The privacy gate promotes a contact only for farms that publish their own
  // website; walk a wide page of the feed rather than trusting the build alone.
  for (const sort of ["name", "relevance"] as const) {
    const page = await searchFarms(query(`sort=${sort}&limit=50`));
    for (const farm of page.items) {
      if (farm.contact) assert.notEqual(farm.website, "", `${farm.id} leaks a contact`);
    }
  }
});
