import assert from "node:assert/strict";
import test from "node:test";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import {
  coerceMapOptions,
  defaultMapOptions,
  densityPaint,
  describeMapOptions,
  farmLabelLayout,
  farmPointPaint,
  layerVisibility,
  pinModes,
  spotlightCategories,
  type MapOptions,
} from "../app/lib/map-options";
import { guideStyle } from "../app/lib/map-styles";
import { categoryColors } from "../app/lib/farms";
import { compassBearing, compassPoint, relativeHeading } from "../app/lib/nearby";

const options = (patch: Partial<MapOptions> = {}): MapOptions => ({ ...defaultMapOptions, ...patch });

/**
 * These options decide what 68,618 farms look like. The failure mode is not an
 * exception — it is a map that renders as an unreadable mat, or one that
 * quietly stops drawing farms, and neither throws.
 */

test("no option ever stops the pins from being drawn for some farms", () => {
  // The promise the panel makes in words: highlighting dims, it does not
  // filter. A `filter` on the layer would break that silently, so the paint
  // must never contain one and the dim must never reach zero.
  for (const category of ["", ...spotlightCategories]) {
    const paint = farmPointPaint(options({ spotlight: category })) as Record<string, unknown>;
    assert.ok(!("filter" in paint), "spotlight must not filter the farm layer");
    const flat = JSON.stringify(paint["circle-opacity"]);
    assert.ok(!/(^|[^.\d])0([^.\d]|$)/.test(flat.replace(/"[^"]*"/g, "")) || flat.includes("0.2"), flat);
  }

  const dimmed = JSON.stringify(farmPointPaint(options({ spotlight: "Produce" })));
  assert.match(dimmed, /0\.22/, "unhighlighted farms must stay visible, not disappear");
});

test("a spotlight changes paint, not which layers exist", () => {
  const plain = layerVisibility(options());
  const spotlit = layerVisibility(options({ spotlight: "Dairy" }));
  assert.deepEqual(plain, spotlit, "highlighting must not hide a layer");
  assert.equal(plain["farm-points"], true);
});

test("every pin mode keeps at least one layer that shows farms", () => {
  for (const mode of pinModes) {
    const visible = layerVisibility(options({ pins: mode.id }));
    assert.ok(visible["farm-points"] || visible["farm-density"], `${mode.id} draws nothing`);
  }
  // Labels are an annotation on the pins; with the pins gone they would float
  // over a heatmap with nothing to attach to.
  assert.equal(layerVisibility(options({ pins: "density", labels: true }))["farm-labels"], false);
  assert.equal(layerVisibility(options({ pins: "pins", labels: true }))["farm-labels"], true);
});

test("the paint every option produces is a valid MapLibre style", () => {
  // Validate in place on real layers: a malformed interpolate or a colour ramp
  // that never resolves renders as nothing at all, which review does not catch.
  const cases: MapOptions[] = [
    options(),
    options({ spotlight: "Produce" }),
    options({ pins: "density" }),
    options({ pins: "both", labels: true, spotlight: "Seafood" }),
  ];

  for (const current of cases) {
    const base = guideStyle();
    const style = {
      ...base,
      sources: { ...base.sources, farms: { type: "geojson", data: { type: "FeatureCollection", features: [] } } },
      layers: [
        ...base.layers,
        { id: "farm-density", type: "heatmap", source: "farms", paint: densityPaint(current) },
        { id: "farm-points", type: "circle", source: "farms", paint: farmPointPaint(current) },
        { id: "farm-labels", type: "symbol", source: "farms", layout: farmLabelLayout(), paint: { "text-color": "#3f4a3d" } },
      ],
    };
    assert.deepEqual(
      validateStyleMin(style as never).map((error) => `${error.message}`),
      [],
      `invalid style for ${JSON.stringify(current)}`,
    );
  }
});

test("pin colours cover every published category", () => {
  // A category missing from the match expression falls through to the grey
  // default, which reads as "uncategorised" on a map whose legend says
  // otherwise.
  const expression = JSON.stringify(farmPointPaint(options())["circle-color"]);
  for (const [category, color] of Object.entries(categoryColors)) {
    assert.ok(expression.includes(JSON.stringify(category)), `${category} has no pin colour`);
    assert.ok(expression.includes(color), `${category}'s colour is missing`);
  }
});

test("stored options are narrowed field by field", () => {
  // localStorage is viewer-writable and survives deploys, so a stale or hostile
  // shape must resolve to something drawable rather than reaching MapLibre.
  assert.deepEqual(coerceMapOptions(null), defaultMapOptions);
  assert.deepEqual(coerceMapOptions("guide"), defaultMapOptions);
  assert.deepEqual(coerceMapOptions({ basemap: "satellite", pins: "sprinkles", spotlight: "Yachts", tilt: 7 }), defaultMapOptions);
  assert.deepEqual(
    coerceMapOptions({ basemap: "detailed", pins: "both", spotlight: "Dairy", labels: true, tilt: "flat", scale: true }),
    { basemap: "detailed", pins: "both", spotlight: "Dairy", labels: true, tilt: "flat", scale: true },
  );
});

test("the spoken description says a highlight is not a filter", () => {
  // Someone using a screen reader gets no visual cue that the other farms are
  // still there, so the status line has to say it.
  const spoken = describeMapOptions(options({ spotlight: "Produce" }), "Field guide");
  assert.match(spoken, /still shown/i);
  assert.match(describeMapOptions(options(), "Field guide"), /^Field guide basemap, pins\./);
});

test("a heading is distance plus the direction you would drive", () => {
  const madison = { lat: 43.07, lng: -89.4 };
  assert.equal(compassPoint(compassBearing(madison, { lat: 44.07, lng: -89.4 })), "N");
  assert.equal(compassPoint(compassBearing(madison, { lat: 43.07, lng: -88.4 })), "E");
  assert.equal(compassPoint(compassBearing(madison, { lat: 42.07, lng: -89.4 })), "S");
  assert.equal(compassPoint(compassBearing(madison, { lat: 43.07, lng: -90.4 })), "W");
  assert.equal(compassPoint(compassBearing(madison, { lat: 43.77, lng: -88.4 })), "NE");

  assert.equal(relativeHeading(madison, { lat: 44.07, lng: -89.4 }, 69)?.label, "69 mi N");
  // Under ten miles a whole number throws away the difference between "just
  // down the road" and "across town".
  assert.equal(relativeHeading(madison, { lat: 43.08, lng: -89.4 }, 0.8)?.label, "0.8 mi N");
  assert.equal(relativeHeading(madison, { lat: 43.08, lng: -89.4 }, 5.0)?.label, "5 mi N");
  // No origin: still say how far, just not which way.
  assert.equal(relativeHeading(null, { lat: 43.08, lng: -89.4 }, 12)?.label, "12 mi");
  assert.equal(relativeHeading(null, null, null), null);
});
