/**
 * Fill `map-review.template.html` and write `map-review.html`.
 *
 * The template is a side-by-side of the two basemaps the explorer offers, so it
 * has to read the same style module the app does rather than a copy: a review
 * that drifts from the shipped style is worse than no review. The pins are real
 * published farms from the current release for the same reason — a synthetic
 * scatter hides exactly the label collisions and pin-density problems the
 * review exists to find.
 *
 *   node --import tsx dev/build-map-review.mjs     (or: npm run map:review)
 *
 * Output is a generated artifact and is not committed, per AGENTS.md.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { detailPaint, detailPitch, guideStyle } from "../app/lib/map-styles.ts";
import { defaultMapOptions, densityPaint, farmPointPaint } from "../app/lib/map-options.ts";

const here = dirname(fileURLToPath(import.meta.url));
const feedPath = resolve(here, "../../../01-database/pipeline/build/app-farms.json");

/**
 * Three cameras that break a basemap in different ways: sparse rural roads with
 * far-apart pins, a dense grid where labels and pins fight, and a coastline
 * where the land/water edge carries the legibility.
 */
const places = {
  "rural-wi": { center: { lat: 43.0731, lng: -89.4012 } },
  "dense-ca": { center: { lat: 34.0522, lng: -118.2437 } },
  "coastal-la": { center: { lat: 29.9511, lng: -90.0715 } },
};

const pinsPerPlace = 50;

function milesBetween(a, b) {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 7917.5 * Math.asin(Math.min(1, Math.sqrt(h)));
}

let feed;
try {
  feed = JSON.parse(readFileSync(feedPath, "utf8"));
} catch {
  console.error(
    `Could not read ${feedPath}.\n` +
      "It is a reproducible pipeline artifact, not a committed file. Build it with:\n" +
      "  python3 01-database/pipeline/run.py --publish",
  );
  process.exit(1);
}

// Only rows the public map would actually draw: the feed also carries listed
// farms with no usable location, and putting those on a review map would
// overstate density.
const mappable = feed.filter(
  (farm) => farm.geoPrecision !== "ungeocoded" && Number.isFinite(farm.latitude) && Number.isFinite(farm.longitude) && !(farm.latitude === 0 && farm.longitude === 0),
);

const samples = {};
for (const [key, place] of Object.entries(places)) {
  const nearest = mappable
    .map((farm) => ({ farm, miles: milesBetween(place.center, { lat: farm.latitude, lng: farm.longitude }) }))
    .sort((a, b) => a.miles - b.miles)
    .slice(0, pinsPerPlace);
  if (nearest.length < pinsPerPlace) {
    console.warn(`${key}: only ${nearest.length} mappable farms found`);
  }
  samples[key] = {
    center: place.center,
    // Short keys: this object is inlined into the page, and 150 farms of full
    // records would dwarf the style it is there to review.
    farms: nearest.map(({ farm }) => ({ n: farm.name, c: farm.category, lat: farm.latitude, lng: farm.longitude })),
  };
}

const template = readFileSync(resolve(here, "map-review.template.html"), "utf8");
const filled = template
  .replace("__PINS__", JSON.stringify(samples))
  .replace("__GUIDE_STYLE__", JSON.stringify(guideStyle()))
  .replace("__DETAIL_PAINT__", JSON.stringify(detailPaint))
  .replace("__DETAIL_PITCH__", JSON.stringify(detailPitch))
  .replace("__PIN_PAINT__", JSON.stringify(farmPointPaint(defaultMapOptions)))
  .replace("__DENSITY_PAINT__", JSON.stringify(densityPaint({ ...defaultMapOptions, pins: "both" })));

for (const token of ["__PINS__", "__GUIDE_STYLE__", "__DETAIL_PAINT__", "__DETAIL_PITCH__", "__PIN_PAINT__", "__DENSITY_PAINT__"]) {
  if (filled.includes(token)) throw new Error(`template placeholder ${token} was not replaced`);
}

const out = resolve(here, "map-review.html");
writeFileSync(out, filled);
const totals = Object.entries(samples).map(([key, value]) => `${key} ${value.farms.length}`).join(", ");
console.log(`wrote ${out} — ${guideStyle().layers.length} guide layers, ${detailPaint.length} detail overrides, pins: ${totals}`);
