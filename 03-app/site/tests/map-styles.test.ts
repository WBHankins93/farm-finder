import assert from "node:assert/strict";
import test from "node:test";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import { basemaps, detailedStyleUrl, guideStyle } from "../app/lib/map-styles";

/**
 * The simplified basemap is hand-authored, so nothing upstream validates it.
 * A malformed expression or a layer pointing at a missing source-layer renders
 * as a silently blank map rather than an error, which is exactly the failure a
 * person would not notice in review.
 */

test("the simplified basemap is a valid MapLibre style", () => {
  const errors = validateStyleMin(guideStyle());
  assert.deepEqual(
    errors.map((error) => `${error.message}`),
    [],
    "guideStyle() must validate against the MapLibre style spec",
  );
});

test("the simplified basemap stays small enough to be the fast option", () => {
  const style = guideStyle();
  // The point of this style is that it is cheap to draw. Full OSM styles run
  // past 100 layers; if this one drifts up there it has lost its reason to
  // exist and the toggle is just two detailed maps.
  assert.ok(style.layers.length <= 30, `expected a lean layer set, got ${style.layers.length}`);
  assert.ok(style.layers.length >= 12, "a usable basemap needs land, water, roads, and labels");

  const ids = style.layers.map((layer) => layer.id);
  assert.equal(new Set(ids).size, ids.length, "layer ids must be unique");
});

test("both basemaps read the same vector source so a swap reuses cached tiles", () => {
  const style = guideStyle();
  assert.deepEqual(Object.keys(style.sources), ["openmaptiles"]);
  const source = style.sources.openmaptiles as { type: string; url: string };
  assert.equal(source.type, "vector");
  assert.match(source.url, /^https:\/\/tiles\.openfreemap\.org\//);
  assert.match(detailedStyleUrl, /^https:\/\/tiles\.openfreemap\.org\//);
});

test("every layer points at a source-layer the OpenMapTiles schema defines", () => {
  // Names taken from the schema the detailed style reads; a typo here is a
  // layer that simply never draws.
  const schema = new Set([
    "aerodrome_label", "aeroway", "boundary", "building", "landcover", "landuse",
    "park", "place", "poi", "transportation", "transportation_name", "water",
    "water_name", "waterway",
  ]);

  for (const layer of guideStyle().layers) {
    if (layer.type === "background") continue;
    const sourceLayer = (layer as { "source-layer"?: string })["source-layer"];
    assert.ok(sourceLayer, `layer ${layer.id} must name a source-layer`);
    assert.ok(schema.has(sourceLayer!), `layer ${layer.id} uses unknown source-layer "${sourceLayer}"`);
  }
});

test("road fills draw above their casings so roads read as outlined ribbons", () => {
  const ids = guideStyle().layers.map((layer) => layer.id);
  for (const road of ["road-minor", "road-major", "road-motorway"]) {
    const casing = ids.indexOf(`${road}-casing`);
    const fill = ids.indexOf(road);
    assert.notEqual(casing, -1, `${road}-casing is missing`);
    assert.notEqual(fill, -1, `${road} is missing`);
    assert.ok(casing < fill, `${road}-casing must be drawn before ${road}`);
  }
});

test("the toggle offers exactly the two documented options", () => {
  assert.deepEqual(basemaps.map((option) => option.id), ["guide", "detailed"]);
  for (const option of basemaps) {
    assert.ok(option.label.length > 0);
    assert.ok(option.hint.length > 0, "each option needs a hint for its tooltip");
  }
});
