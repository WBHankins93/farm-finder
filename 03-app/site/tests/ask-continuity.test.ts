import assert from "node:assert/strict";
import test from "node:test";
import { buildAskExploreUrl, buildAskRequestUrl, formatAskFarmLocation, parseAskLocationContext } from "../app/lib/ask-continuity";

test("Ask location context uses the current nearby search and defaults missing or invalid radii safely", () => {
  assert.deepEqual(parseAskLocationContext("?near=new-orleans-la&radiusMiles=25"), {
    near: "new-orleans-la",
    radiusMiles: 25,
  });
  assert.deepEqual(parseAskLocationContext("?near=new-orleans-la"), {
    near: "new-orleans-la",
    radiusMiles: 50,
  });
  assert.deepEqual(parseAskLocationContext("?near=new-orleans-la&radiusMiles=500"), {
    near: "new-orleans-la",
    radiusMiles: 50,
  });
  assert.deepEqual(parseAskLocationContext("?radiusMiles=100"), { near: "", radiusMiles: null });
});

test("Ask request keeps the question, Louisiana location slug, and radius", () => {
  const url = buildAskRequestUrl("  goat cheese  ", { near: "new-orleans-la", radiusMiles: 50 });
  const parsed = new URL(url, "https://farmfinder.example");

  assert.equal(parsed.pathname, "/v1/farms");
  assert.equal(parsed.searchParams.get("q"), "goat cheese");
  assert.equal(parsed.searchParams.get("near"), "new-orleans-la");
  assert.equal(parsed.searchParams.get("radiusMiles"), "50");
  assert.equal(parsed.searchParams.get("sort"), "relevance");
  assert.equal(parsed.searchParams.get("limit"), "6");
});

test("Ask result and all-results links preserve submitted context without inventing one", () => {
  const context = { near: "new-orleans-la", radiusMiles: 100 as const };
  const resultUrl = new URL(buildAskExploreUrl("pastured eggs", context, "black-creek-farm-llc-ms"), "https://farmfinder.example");
  assert.equal(resultUrl.searchParams.get("q"), "pastured eggs");
  assert.equal(resultUrl.searchParams.get("near"), "new-orleans-la");
  assert.equal(resultUrl.searchParams.get("radiusMiles"), "100");
  assert.equal(resultUrl.searchParams.get("farm"), "black-creek-farm-llc-ms");
  assert.equal(resultUrl.hash, "#discover");

  const nationwideUrl = new URL(buildAskExploreUrl("citrus", { near: "", radiusMiles: null }), "https://farmfinder.example");
  assert.equal(nationwideUrl.searchParams.get("q"), "citrus");
  assert.equal(nationwideUrl.searchParams.has("near"), false);
  assert.equal(nationwideUrl.searchParams.has("radiusMiles"), false);
});

test("Ask result locations never render dangling punctuation", () => {
  assert.equal(formatAskFarmLocation("New Orleans", "LA"), "New Orleans, LA");
  assert.equal(formatAskFarmLocation("", "MS"), "MS");
  assert.equal(formatAskFarmLocation("Picayune", ""), "Picayune");
  assert.equal(formatAskFarmLocation("", ""), "Location not listed");
});
