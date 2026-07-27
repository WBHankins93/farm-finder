import assert from "node:assert/strict";
import test from "node:test";
import type { Farm } from "../app/lib/farms";
import {
  DEFAULT_ORIGIN,
  farmDistanceKm,
  haversineKm,
  nearestFarms,
} from "../app/lib/nearby";

/** Minimal Farm stub — only the fields the location layer reads matter here. */
function farm(over: Partial<Farm> & { id: string }): Farm {
  return {
    id: over.id,
    name: over.name ?? over.id,
    category: "Produce",
    region: "",
    parish: "",
    state: "LA",
    city: "",
    productsText: "",
    products: [],
    marketPresence: "",
    website: "",
    hasWebsite: false,
    onlineStore: false,
    facebook: false,
    instagram: false,
    farmersMarket: false,
    csa: false,
    ships: false,
    onFarm: false,
    contact: "",
    notes: "",
    source: "",
    latitude: 0,
    longitude: 0,
    geoPrecision: "city",
    ...over,
  };
}

test("haversineKm is ~0 for the same point", () => {
  assert.ok(haversineKm(DEFAULT_ORIGIN, DEFAULT_ORIGIN) < 0.001);
});

test("haversineKm matches a known distance (New Orleans → Baton Rouge ≈ 121 km)", () => {
  const nola = { lat: 29.95, lng: -90.07 };
  const br = { lat: 30.45, lng: -91.19 };
  const d = haversineKm(nola, br);
  assert.ok(d > 115 && d < 127, `expected ~121 km, got ${d.toFixed(1)}`);
});

test("DEFAULT_ORIGIN is in South Louisiana (launch market)", () => {
  assert.ok(DEFAULT_ORIGIN.lat > 29 && DEFAULT_ORIGIN.lat < 31);
  assert.ok(DEFAULT_ORIGIN.lng > -94 && DEFAULT_ORIGIN.lng < -89);
});

test("farmDistanceKm returns Infinity for ungeocoded farms so they sort last", () => {
  const f = farm({ id: "x", geoPrecision: "ungeocoded", latitude: 0, longitude: 0 });
  assert.equal(farmDistanceKm(DEFAULT_ORIGIN, f), Number.POSITIVE_INFINITY);
});

test("farmDistanceKm measures real distance for a geocoded farm", () => {
  const f = farm({ id: "x", latitude: 30.45, longitude: -91.19 });
  const d = farmDistanceKm({ lat: 29.95, lng: -90.07 }, f);
  assert.ok(d > 115 && d < 127);
});

test("nearestFarms sorts by ascending distance, ungeocoded last", () => {
  const origin = { lat: 30.0, lng: -90.0 };
  const near = farm({ id: "near", latitude: 30.1, longitude: -90.1 });
  const far = farm({ id: "far", latitude: 34.0, longitude: -84.0 });
  const nowhere = farm({ id: "nowhere", geoPrecision: "ungeocoded" });
  const sorted = nearestFarms(origin, [far, nowhere, near]);
  assert.deepEqual(sorted.map((f) => f.id), ["near", "far", "nowhere"]);
});

test("nearestFarms does not mutate the input array", () => {
  const origin = DEFAULT_ORIGIN;
  const input = [
    farm({ id: "b", latitude: 34.0, longitude: -84.0 }),
    farm({ id: "a", latitude: 30.1, longitude: -91.3 }),
  ];
  const order = input.map((f) => f.id);
  nearestFarms(origin, input);
  assert.deepEqual(input.map((f) => f.id), order);
});
