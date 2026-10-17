import assert from "node:assert/strict";
import test from "node:test";
import { createLatestRequestGuard, mergeCursorPage, parseDiscoveryUrl, requestApproximateLocation, retainSelectedFarm, serializeDiscoveryUrl } from "../app/lib/discovery-client";
import type { FarmMapFeature, FarmSearchResponse, FarmSummary } from "../app/lib/discovery-contract";

const farm = (id: string): FarmSummary => ({
  id, name: id, category: "Produce", region: "", parish: "", state: "LA", city: "Testville", productsText: "Produce", products: ["Produce"], marketPresence: "", website: "", contact: "",
  farmersMarket: false, onFarm: false, csa: false, ships: false, onlineStore: false, latitude: 30, longitude: -90, geoPrecision: "city", distanceMiles: null,
});

const response = (items: FarmSummary[], nextCursor: string | null): FarmSearchResponse => ({
  items, total: 3, nextCursor, scope: { mode: "all", label: "all covered areas", origin: null, radiusMiles: null, bounds: null }, sort: "name", releaseId: "test",
});

test("URL state round-trips filters, map bounds, view, and selection", () => {
  const original = parseDiscoveryUrl(new URLSearchParams("q=eggs&bbox=-91.12345,29,-89,31.98765&category=Produce&product=eggs&services=onFarm,csa&sort=relevance&view=map&farm=farm-1"));
  const roundTrip = parseDiscoveryUrl(serializeDiscoveryUrl(original));
  assert.deepEqual(roundTrip, { ...original, bbox: [-91.1235, 29, -89, 31.9876] });
});

test("URL state defaults nearby searches to 50 miles and never serializes raw GPS coordinates", () => {
  const state = parseDiscoveryUrl(new URLSearchParams("near=new-orleans-la"));
  assert.equal(state.radiusMiles, 50);
  assert.equal(state.sort, "distance");
  const serialized = serializeDiscoveryUrl(state);
  assert.equal(serialized.has("lat"), false);
  assert.equal(serialized.has("lng"), false);
});

test("cursor accumulation de-duplicates defensive overlaps", () => {
  const merged = mergeCursorPage(response([farm("one"), farm("two")], "Mg"), response([farm("two"), farm("three")], null));
  assert.deepEqual(merged.items.map((item) => item.id), ["one", "two", "three"]);
  assert.equal(merged.nextCursor, null);
});

test("superseded requests are aborted and cannot publish stale results", () => {
  const guard = createLatestRequestGuard();
  const first = guard.begin();
  const second = guard.begin();
  assert.equal(first.signal.aborted, true);
  assert.equal(first.isLatest(), false);
  assert.equal(second.signal.aborted, false);
  assert.equal(second.isLatest(), true);
  second.cancel();
  assert.equal(second.signal.aborted, true);
});

test("selection persists only while represented by the list or a leaf map point", () => {
  const selected = farm("selected");
  const leaf: FarmMapFeature = { kind: "farm", id: "selected", name: "selected", category: "Produce", latitude: 30, longitude: -90, geoPrecision: "city" };
  assert.equal(retainSelectedFarm(selected, [], [leaf]), selected);
  assert.equal(retainSelectedFarm(selected, [selected], []), selected);
  assert.equal(retainSelectedFarm(selected, [], []), null);
});

test("location denial resolves cleanly and successful coordinates are rounded", async () => {
  assert.equal(await requestApproximateLocation(null), null);
  const denied = { getCurrentPosition: (_success: unknown, error: () => void) => error() };
  assert.equal(await requestApproximateLocation(denied), null);
  const allowed = { getCurrentPosition: (success: (value: { coords: { latitude: number; longitude: number } }) => void) => success({ coords: { latitude: 30.123456, longitude: -90.987654 } }) };
  assert.deepEqual(await requestApproximateLocation(allowed), { lat: 30.123, lng: -90.988 });
});
