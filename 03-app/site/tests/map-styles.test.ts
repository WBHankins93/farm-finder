import assert from "node:assert/strict";
import test from "node:test";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import { basemaps, detailedStyleUrl, detailPaint, detailPitch, detailZoom, guideStyle } from "../app/lib/map-styles";

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

/**
 * The detailed basemap is Liberty, which this repository does not own. The
 * overrides below are applied to layers Liberty ships, so the risk is not a
 * malformed style — it is Liberty renaming or dropping a layer and the
 * overrides silently doing nothing. These tests pin the assumptions; a fetch of
 * the live style is deliberately not made here, because a unit test that needs
 * the network fails for reasons that have nothing to do with the code.
 */

test("the detailed overrides target Liberty's own layers, never new ones", () => {
  // Every override must be a paint change to an existing layer id. Adding a
  // layer whose id Liberty already uses is refused by MapLibre, which is how an
  // earlier pass shipped an extrusion override that never applied.
  assert.ok(detailPaint.length > 0, "detailed mode must actually change something");
  for (const override of detailPaint) {
    assert.equal(override.layer, "building-3d", "Liberty's extrusion layer is the only one being re-painted");
    assert.match(override.property, /^fill-extrusion-/, `${override.property} is not a fill-extrusion paint property`);
    assert.notEqual(override.value, undefined);
  }

  const targets = detailPaint.map((override) => `${override.layer}.${override.property}`);
  assert.equal(new Set(targets).size, targets.length, "two overrides must not fight over one property");
});

test("the detailed overrides do not collide with the guide style's layers", () => {
  // The guide style is hand-authored here, so an id shared with an override
  // would mean the two basemaps were quietly editing each other.
  const guideIds = new Set(guideStyle().layers.map((layer) => layer.id));
  for (const override of detailPaint) {
    assert.ok(!guideIds.has(override.layer), `${override.layer} exists in both basemaps`);
  }
});

test("each override is a valid MapLibre expression for its property", () => {
  // Validate them in place on a real layer rather than in isolation: a bad
  // interpolate or a colour ramp that never resolves to a colour renders as
  // nothing, which review does not catch.
  const probe = {
    ...guideStyle(),
    layers: [
      ...guideStyle().layers,
      {
        id: "building-3d",
        type: "fill-extrusion",
        source: "openmaptiles",
        "source-layer": "building",
        minzoom: 14,
        paint: Object.fromEntries(detailPaint.map((override) => [override.property, override.value])),
      },
    ],
  };
  assert.deepEqual(validateStyleMin(probe as never).map((error) => `${error.message}`), []);
});

test("the tilt only applies where Liberty has massing to show", () => {
  // Liberty draws flat fills below z14 and extrusions above it; its POI labels
  // start at z15. Tilting below that costs a horizon of tiles for nothing.
  assert.ok(detailZoom >= 14, "tilting below Liberty's extrusion zoom shows flat ground");
  assert.ok(detailZoom <= 16, "tilting only past z16 would put 3D out of practical reach");
  assert.ok(detailPitch > 0 && detailPitch <= 60, "a pitch past 60 shows more horizon than ground");
});
