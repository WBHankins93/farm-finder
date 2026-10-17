import assert from "node:assert/strict";
import test from "node:test";
import { buildHeroPlaceUrl, buildProductBrowseUrl } from "../app/lib/browse-location-continuity";

function parse(url: string) {
  return new URL(url, "https://farmfinder.example");
}

test("product browse keeps the active Louisiana location and compatible refinements", () => {
  const url = parse(buildProductBrowseUrl("vegetables", {
    near: "new-orleans-la",
    radiusMiles: "25",
    q: "organic",
    category: "Meat",
    services: "onFarm,csa,onFarm,not-a-service",
    sort: "relevance",
    view: "map",
    farm: "old-selection",
  }));

  assert.equal(url.searchParams.get("product"), "vegetables");
  assert.equal(url.searchParams.get("near"), "new-orleans-la");
  assert.equal(url.searchParams.get("radiusMiles"), "25");
  assert.equal(url.searchParams.get("q"), "organic");
  assert.equal(url.searchParams.get("services"), "onFarm,csa");
  assert.equal(url.searchParams.get("sort"), "relevance");
  assert.equal(url.searchParams.get("view"), "map");
  assert.equal(url.searchParams.has("category"), false);
  assert.equal(url.searchParams.has("farm"), false);
  assert.equal(url.hash, "#discover");
});

test("product browse retains a valid map boundary and never carries raw coordinates", () => {
  const url = parse(buildProductBrowseUrl("fruit", "?bbox=-91,29,-89,31&lat=30.12&lng=-90.45&services=ships"));

  assert.equal(url.searchParams.get("bbox"), "-91.0000,29.0000,-89.0000,31.0000");
  assert.equal(url.searchParams.get("product"), "fruit");
  assert.equal(url.searchParams.get("services"), "ships");
  assert.equal(url.searchParams.has("lat"), false);
  assert.equal(url.searchParams.has("lng"), false);
});

test("hero city choice replaces geographic scope and retains product, question, and services", () => {
  const url = parse(buildHeroPlaceUrl(
    "madison-wi",
    "?q=goat+cheese&product=dairy&category=Dairy&services=onFarm,csa&bbox=-91,29,-89,31&lat=30.12&lng=-90.45&radiusMiles=100&sort=name&view=map&all=1&farm=old-selection",
  ));

  assert.equal(url.searchParams.get("near"), "madison-wi");
  assert.equal(url.searchParams.get("radiusMiles"), "100");
  assert.equal(url.searchParams.get("q"), "goat cheese");
  assert.equal(url.searchParams.get("product"), "dairy");
  assert.equal(url.searchParams.get("category"), "Dairy");
  assert.equal(url.searchParams.get("services"), "onFarm,csa");
  assert.equal(url.searchParams.get("sort"), "relevance");
  assert.equal(url.searchParams.get("view"), "map");
  assert.equal(url.searchParams.has("bbox"), false);
  assert.equal(url.searchParams.has("lat"), false);
  assert.equal(url.searchParams.has("lng"), false);
  assert.equal(url.searchParams.has("all"), false);
  assert.equal(url.searchParams.has("farm"), false);
  assert.equal(url.hash, "#discover");
});

test("hero city choice defaults invalid radius and uses distance sorting without a question", () => {
  const url = parse(buildHeroPlaceUrl("new-orleans-la", "?product=vegetables&radiusMiles=500&sort=name"));

  assert.equal(url.searchParams.get("near"), "new-orleans-la");
  assert.equal(url.searchParams.get("radiusMiles"), "50");
  assert.equal(url.searchParams.get("product"), "vegetables");
  assert.equal(url.searchParams.get("sort"), "distance");
});
