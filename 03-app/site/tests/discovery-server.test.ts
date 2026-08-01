import assert from "node:assert/strict";
import test from "node:test";
import { getFarm, isMappableFarm, mapFarms, parseDiscoveryQuery, searchFarms, searchPlaces } from "../app/lib/discovery-server";

function query(value = "") {
  return parseDiscoveryQuery(new URLSearchParams(value));
}

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

test("nearby browsing returns a normalized 50-mile scope in nearest order", () => {
  const result = searchFarms(query("near=new-orleans-la&sort=distance&limit=50"));
  assert.equal(result.scope.mode, "nearby");
  assert.equal(result.scope.label, "New Orleans, LA");
  assert.equal(result.scope.radiusMiles, 50);
  const distances = result.items.map((farm) => farm.distanceMiles ?? Number.POSITIVE_INFINITY);
  assert.deepEqual(distances, [...distances].sort((a, b) => a - b));
});

test("cursor pagination is stable, accumulates without duplicates, and uses opaque cursors", () => {
  const first = searchFarms(query("sort=name&limit=7"));
  assert.ok(first.nextCursor);
  assert.doesNotMatch(first.nextCursor, /^\d+$/);
  const second = searchFarms(query(`sort=name&limit=7&cursor=${encodeURIComponent(first.nextCursor!)}`));
  const combined = [...first.items, ...second.items];
  assert.equal(new Set(combined.map((farm) => farm.id)).size, 14);
  const reference = searchFarms(query("sort=name&limit=14"));
  assert.deepEqual(combined.map((farm) => farm.id), reference.items.map((farm) => farm.id));
});

test("filters use AND across category, product, and each service", () => {
  const result = searchFarms(query("category=Produce&product=vegetables&services=onFarm,csa&limit=50"));
  assert.ok(result.total > 0);
  for (const farm of result.items) {
    assert.equal(farm.category, "Produce");
    assert.equal(farm.onFarm, true);
    assert.equal(farm.csa, true);
  }
});

test("list count and map count agree for a bounded public area", () => {
  const parsed = query("bbox=-91,29,-89,31&product=vegetables&services=onFarm&limit=50");
  const list = searchFarms(parsed);
  const map = mapFarms(parsed, 9);
  assert.equal(map.total, list.total);
  assert.ok(map.features.every((feature) => Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude)));
});

test("shared approximate coordinates remain terminal clusters at maximum zoom", () => {
  const map = mapFarms(query("bbox=-91,29,-89,31"), 16);
  const cluster = map.features.find((feature) => feature.kind === "cluster" && feature.terminal);
  assert.ok(cluster && cluster.kind === "cluster");
  assert.ok(cluster.count > 1);
  assert.equal(cluster.bounds[0], cluster.bounds[2]);
  assert.equal(cluster.bounds[1], cluster.bounds[3]);
  assert.equal(cluster.farmIds?.length, cluster.count);
});

test("zero, missing, non-finite, and explicitly ungeocoded coordinates are never mappable", () => {
  const base = getFarm("vintage-garden-farms")!;
  assert.equal(isMappableFarm({ ...base, latitude: 0, longitude: 0 }), false);
  assert.equal(isMappableFarm({ ...base, latitude: Number.NaN }), false);
  assert.equal(isMappableFarm({ ...base, geoPrecision: "ungeocoded" }), false);
  assert.equal(isMappableFarm(base), true);
});

test("place suggestions are governed, bounded, and profile lookup does not depend on a list page", () => {
  const places = searchPlaces("new", 99);
  assert.ok(places.items.length > 0 && places.items.length <= 8);
  assert.equal(places.items[0].label, "New Orleans, LA");
  const farm = getFarm("vintage-garden-farms");
  assert.equal(farm?.name, "Vintage Garden Farms");
  assert.equal(getFarm("missing-farm"), null);
});

test("public summaries tolerate long names and missing contact paths", () => {
  const result = searchFarms(query("limit=50"));
  const missingContact = result.items.find((farm) => !farm.contact && !farm.website);
  assert.ok(missingContact);
  const longest = result.items.reduce((current, farm) => farm.name.length > current.name.length ? farm : current);
  assert.ok(longest.name.length > 20);
  assert.equal(typeof longest.productsText, "string");
});
