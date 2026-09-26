import type { StyleSpecification } from "maplibre-gl";

/**
 * The two basemaps the explorer offers.
 *
 * `guide` is the default: a hand-authored, deliberately cartoon-flat style in
 * the spirit of a driving app — saturated land, bold rounded road casings, and
 * almost no labels competing with the farm pins. It is also the fast one: 19
 * layers against the 111 in Liberty, which is what keeps panning smooth when
 * the map is carrying thousands of server-side clusters.
 *
 * `detailed` is the full OpenFreeMap Liberty style with its building extrusions
 * re-painted so height reads (see `detailPaint`). It is for someone who has
 * picked a farm and is now working out the last mile, so the map also tilts and
 * unlocks street-level zoom when it is selected.
 *
 * Both read the same OpenMapTiles vector source, so switching styles reuses
 * tiles already in the cache instead of refetching geography.
 */
export type BasemapId = "guide" | "detailed";

export const basemaps: { id: BasemapId; label: string; hint: string }[] = [
  { id: "guide", label: "Field guide", hint: "Simplified and fast — built for scanning farm pins" },
  { id: "detailed", label: "Full detail", hint: "Street names, landmarks, and tilted 3D buildings" },
];

export const detailedStyleUrl = "https://tiles.openfreemap.org/styles/liberty";

/**
 * Whether the map has to swap its style to show `requested`.
 *
 * `applied` is the basemap whose style the map was last given — at
 * construction, then at each swap — not the one the viewer last clicked.
 * Keying on it rather than on "did the effect run" is what keeps the first
 * load to one style load: the effect first runs when the map becomes ready,
 * on the style the map just finished loading, and re-applying it would throw
 * the style and the farm overlay away and (for Full detail) refetch Liberty.
 * A switch made before the map was ready still differs from `applied`, so it
 * is honoured the moment the map can take it.
 */
export function needsStyleSwap(applied: BasemapId, requested: BasemapId): boolean {
  return applied !== requested;
}

const vectorSource = "https://tiles.openfreemap.org/planet";
const glyphs = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";

const palette = {
  land: "#eeead9",
  green: "#cbe0a8",
  greenDeep: "#b4d48c",
  water: "#8ecbe6",
  waterLine: "#6fb9da",
  built: "#e4ddc7",
  motorway: "#ffbe3d",
  motorwayCase: "#d18f18",
  major: "#ffffff",
  majorCase: "#cdc4a8",
  minor: "#fdfcf6",
  minorCase: "#ddd3b6",
  rail: "#cfc5ab",
  label: "#3f4a3d",
  labelHalo: "#fdfdf7",
  boundary: "#c4b99c",
};

/** Road width ramps, shared by a road and its casing so the casing reads as an outline. */
function roadWidth(stops: [number, number][], multiplier = 1) {
  return [
    "interpolate", ["linear"], ["zoom"],
    ...stops.flatMap(([zoom, width]) => [zoom, width * multiplier]),
  ] as unknown as StyleSpecification["layers"][number]["paint"];
}

const motorwayStops: [number, number][] = [[5, 0.8], [8, 2.4], [11, 6.5], [14, 14], [18, 32]];
const majorStops: [number, number][] = [[7, 0.5], [10, 2.1], [13, 5.8], [16, 14], [18, 27]];
const minorStops: [number, number][] = [[12, 0.8], [14, 2.8], [16, 6.5], [18, 16]];

/**
 * Build the simplified basemap.
 *
 * Layer order matters: land, then water and parks, then road casings, then road
 * fills, then the very small label set. Farm pins are added on top by
 * `farm-map.tsx` after the style loads.
 */
export function guideStyle(): StyleSpecification {
  return {
    version: 8,
    name: "FarmFinder field guide",
    glyphs,
    sources: {
      openmaptiles: { type: "vector", url: vectorSource },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": palette.land } },

      {
        id: "landcover-green",
        type: "fill",
        source: "openmaptiles",
        "source-layer": "landcover",
        filter: ["match", ["get", "class"], ["wood", "grass", "farmland"], true, false],
        paint: { "fill-color": palette.green, "fill-opacity": 0.85 },
      },
      {
        id: "park",
        type: "fill",
        source: "openmaptiles",
        "source-layer": "park",
        paint: { "fill-color": palette.greenDeep, "fill-opacity": 0.7 },
      },
      {
        id: "residential",
        type: "fill",
        source: "openmaptiles",
        "source-layer": "landuse",
        filter: ["match", ["get", "class"], ["residential", "suburb", "neighbourhood"], true, false],
        paint: { "fill-color": palette.built, "fill-opacity": 0.8 },
      },

      {
        id: "water",
        type: "fill",
        source: "openmaptiles",
        "source-layer": "water",
        filter: ["!=", ["get", "brunnel"], "tunnel"],
        paint: { "fill-color": palette.water },
      },
      {
        id: "waterway",
        type: "line",
        source: "openmaptiles",
        "source-layer": "waterway",
        minzoom: 7,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": palette.waterLine,
          "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2.6, 18, 6],
        },
      },

      // Casings first so every road reads as one continuous outlined ribbon.
      {
        id: "road-minor-casing",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        minzoom: 12,
        filter: ["match", ["get", "class"], ["minor", "service", "track"], true, false],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.minorCase, "line-width": roadWidth(minorStops, 1.8) },
      },
      {
        id: "road-major-casing",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        filter: ["match", ["get", "class"], ["primary", "secondary", "tertiary", "trunk"], true, false],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.majorCase, "line-width": roadWidth(majorStops, 1.7) },
      },
      {
        id: "road-motorway-casing",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        filter: ["==", ["get", "class"], "motorway"],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.motorwayCase, "line-width": roadWidth(motorwayStops, 1.55) },
      },

      {
        id: "rail",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        minzoom: 11,
        filter: ["==", ["get", "class"], "rail"],
        paint: {
          "line-color": palette.rail,
          "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.6, 16, 2],
        },
      },

      {
        id: "road-minor",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        minzoom: 12,
        filter: ["match", ["get", "class"], ["minor", "service", "track"], true, false],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.minor, "line-width": roadWidth(minorStops) },
      },
      {
        id: "road-major",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        filter: ["match", ["get", "class"], ["primary", "secondary", "tertiary", "trunk"], true, false],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.major, "line-width": roadWidth(majorStops) },
      },
      {
        id: "road-motorway",
        type: "line",
        source: "openmaptiles",
        "source-layer": "transportation",
        filter: ["==", ["get", "class"], "motorway"],
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": palette.motorway, "line-width": roadWidth(motorwayStops) },
      },

      {
        id: "boundary-state",
        type: "line",
        source: "openmaptiles",
        "source-layer": "boundary",
        filter: ["all", ["<=", ["get", "admin_level"], 4], [">=", ["get", "admin_level"], 3]],
        layout: { "line-join": "round" },
        paint: {
          "line-color": palette.boundary,
          "line-dasharray": [3, 2],
          "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.7, 8, 1.5],
        },
      },
      {
        id: "boundary-country",
        type: "line",
        source: "openmaptiles",
        "source-layer": "boundary",
        filter: ["<=", ["get", "admin_level"], 2],
        layout: { "line-join": "round" },
        paint: {
          "line-color": "#b9ae92",
          "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.8, 8, 2],
        },
      },

      // A deliberately sparse label set: the farm pins are the subject here, so
      // the basemap only names places big enough to orient by.
      {
        id: "place-city",
        type: "symbol",
        source: "openmaptiles",
        "source-layer": "place",
        filter: ["match", ["get", "class"], ["city", "town"], true, false],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Bold"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 4, 10, 10, 15],
          "text-max-width": 8,
          "text-padding": 14,
        },
        paint: {
          "text-color": palette.label,
          "text-halo-color": palette.labelHalo,
          "text-halo-width": 1.6,
        },
      },
      {
        id: "place-state",
        type: "symbol",
        source: "openmaptiles",
        "source-layer": "place",
        maxzoom: 7,
        filter: ["==", ["get", "class"], "state"],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 3, 9, 6, 13],
          "text-transform": "uppercase",
          "text-letter-spacing": 0.12,
          "text-padding": 18,
        },
        paint: {
          "text-color": "#7d8a79",
          "text-halo-color": palette.labelHalo,
          "text-halo-width": 1.4,
        },
      },
      {
        id: "place-village",
        type: "symbol",
        source: "openmaptiles",
        "source-layer": "place",
        minzoom: 10,
        filter: ["match", ["get", "class"], ["village", "hamlet"], true, false],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 11,
          "text-padding": 12,
        },
        paint: {
          "text-color": "#6a7367",
          "text-halo-color": palette.labelHalo,
          "text-halo-width": 1.4,
        },
      },
      {
        id: "road-label",
        type: "symbol",
        source: "openmaptiles",
        "source-layer": "transportation_name",
        minzoom: 13,
        filter: ["match", ["get", "class"], ["motorway", "trunk", "primary"], true, false],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 10,
          "symbol-placement": "line",
          "text-rotation-alignment": "map",
          "symbol-spacing": 320,
        },
        paint: {
          "text-color": "#8a8f83",
          "text-halo-color": palette.labelHalo,
          "text-halo-width": 1.4,
        },
      },
    ],
  } as StyleSpecification;
}

/**
 * The zoom at which the detailed basemap starts paying for itself.
 *
 * Liberty draws flat building fills to z14 and switches to its own
 * `building-3d` extrusion layer from z14 up; its POI label layers start at z15.
 * Below this, "full detail" is just a busier version of the same geography, so
 * the map does not tilt and there is nothing extra to tune.
 */
export const detailZoom = 15;

/** The tilt applied in detailed mode so building massing reads as massing. */
export const detailPitch = 52;

/**
 * Paint overrides applied to the detailed basemap once Liberty has loaded.
 *
 * An earlier pass added a new `building-3d` fill-extrusion layer and a
 * `poi-landmark` symbol layer on top of Liberty. Both were redundant and one
 * was inert: Liberty already ships `building-3d` reading `render_height` and
 * `render_min_height` from the same tiles, and it already labels POIs from z15
 * through three rank-banded layers. MapLibre refuses a second layer with an id
 * that is already taken, so the extrusion override never applied at all.
 *
 * What Liberty does *not* do is make that massing readable: it paints every
 * building one flat grey and snaps the whole layer to 80% opacity the instant
 * z14 is crossed. These overrides keep the original intent — height you can
 * read, arriving without a pop — and drop the duplicate POI layer, because the
 * farm pins are installed above the basemap and were never at risk of being
 * buried by it.
 */
export const detailPaint: { layer: string; property: string; value: unknown }[] = [
  {
    layer: "building-3d",
    property: "fill-extrusion-color",
    // Lift the tint with height so massing reads without needing shadows.
    value: ["interpolate", ["linear"], ["coalesce", ["get", "render_height"], 5], 0, "#ded7c6", 60, "#cfc7b2", 200, "#bdb49d"],
  },
  {
    layer: "building-3d",
    // Fade in rather than popping a whole city into 3D at the zoom edge.
    property: "fill-extrusion-opacity",
    value: ["interpolate", ["linear"], ["zoom"], 14, 0, 15.5, 0.85],
  },
];
