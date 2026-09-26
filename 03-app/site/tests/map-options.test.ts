import assert from "node:assert/strict";
import test from "node:test";
import { createPropertyExpression, latest, validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import {
  coerceMapOptions,
  defaultMapOptions,
  densityPaint,
  describeMapOptions,
  farmLabelLayout,
  farmPointMinZoom,
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

/**
 * Evaluate one paint property the way MapLibre would, at a zoom, for a farm of
 * a category. Going through the real expression engine matters: a ramp that
 * reads fine as JSON can still resolve to 0 at a zoom nobody looked at.
 */
function evaluatePaint(layer: "circle" | "heatmap", property: string, value: unknown, zoom: number, category = "Produce"): number {
  const spec = (latest as unknown as Record<string, Record<string, unknown>>)[`paint_${layer}`][property];
  const parsed = createPropertyExpression(value as never, spec as never);
  assert.equal(parsed.result, "success", `${property} does not parse: ${JSON.stringify(parsed.value)}`);
  const expression = parsed.value as unknown as { evaluate: (globals: { zoom: number }, feature: unknown) => number };
  return expression.evaluate({ zoom }, { type: 1, properties: { kind: "farm", category } });
}

test("nothing removes a farm at any zoom, in any pin mode", () => {
  // Checking one zoom is how this broke: density's heatmap fades to nothing
  // by z14, and with the pins hidden a visitor who zoomed in to a farm saw an
  // empty map. Sweep the whole zoom range the map allows, and require that at
  // every step some layer draws every farm, highlighted or not.
  for (const mode of pinModes) {
    for (const spotlight of ["", "Dairy"]) {
      const current = options({ pins: mode.id, spotlight });
      const visible = layerVisibility(current);
      const points = farmPointPaint(current);
      const density = densityPaint(current);
      for (let zoom = 2.5; zoom <= 18; zoom += 0.5) {
        for (const category of ["Produce", "Dairy"]) {
          const pin = visible["farm-points"] ? evaluatePaint("circle", "circle-opacity", points["circle-opacity"], zoom, category) : 0;
          const heat = visible["farm-density"] ? evaluatePaint("heatmap", "heatmap-opacity", density["heatmap-opacity"], zoom, category) : 0;
          assert.ok(pin > 0 || heat > 0, `${mode.id}${spotlight ? ` + ${spotlight} highlight` : ""}: a ${category} farm draws nothing at z${zoom}`);
        }
      }
    }
  }
});

test("density hands over to pins by street zoom", () => {
  const current = options({ pins: "density" });
  assert.equal(layerVisibility(current)["farm-points"], true, "density must keep the pin layer, to hand over to it");
  const points = farmPointPaint(current);
  const density = densityPaint(current);
  const at = (zoom: number) => ({
    pin: evaluatePaint("circle", "circle-opacity", points["circle-opacity"], zoom),
    ring: evaluatePaint("circle", "circle-stroke-opacity", points["circle-stroke-opacity"], zoom),
    heat: evaluatePaint("heatmap", "heatmap-opacity", density["heatmap-opacity"], zoom),
  });

  // Street zoom: the heatmap is gone and every farm is a full-strength pin.
  const street = at(15);
  assert.equal(street.heat, 0);
  assert.ok(street.pin >= 0.9, `pins at z15 are ${street.pin}`);
  assert.equal(street.ring, 1);
  // Regional zoom: density alone, no dots on top of it — that is the mode.
  const regional = at(8);
  assert.equal(regional.pin, 0);
  assert.equal(regional.ring, 0);
  // In between they crossfade rather than overlapping at full strength.
  const mid = at(13);
  assert.ok(mid.pin > 0 && mid.pin < 0.9, `pins at z13 are ${mid.pin}`);
  assert.ok(mid.heat > 0 && mid.heat < at(8).heat, `heat at z13 is ${mid.heat}`);

  // A pin nobody can see must not take clicks: below the handover the layer
  // is out of its zoom range. The other modes draw pins at every zoom.
  const minZoom = farmPointMinZoom(current);
  assert.ok(minZoom > 8 && minZoom <= 13, `density pins start at z${minZoom}`);
  assert.equal(evaluatePaint("circle", "circle-opacity", points["circle-opacity"], minZoom), 0, "pins become clickable before they are visible");
  assert.equal(farmPointMinZoom(options({ pins: "pins" })), 0);
  assert.equal(farmPointMinZoom(options({ pins: "both" })), 0);
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
    options({ pins: "density", spotlight: "Meat" }),
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
