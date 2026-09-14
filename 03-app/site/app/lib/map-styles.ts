import type { StyleSpecification } from "maplibre-gl";

/**
 * The two basemaps the explorer offers.
 *
 * `guide` is the default: a hand-authored, deliberately cartoon-flat style in
 * the spirit of a driving app — saturated land, bold rounded road casings, and
 * almost no labels competing with the farm pins. It is also the fast one: ~22
 * layers against the 111 in a full OSM style, which is what keeps panning
 * smooth when the map is carrying thousands of server-side clusters.
 *
 * `detailed` swaps in the full OpenFreeMap Liberty style for people who want
 * street names, buildings, and POIs while planning an actual trip to a farm.
 *
 * Both read the same OpenMapTiles vector source, so switching styles reuses
 * tiles already in the cache instead of refetching geography.
 */
export type BasemapId = "guide" | "detailed";

export const basemaps: { id: BasemapId; label: string; hint: string }[] = [
  { id: "guide", label: "Field guide", hint: "Simplified, faster, fewer labels" },
  { id: "detailed", label: "Full detail", hint: "Street names, buildings, and places" },
];

export const detailedStyleUrl = "https://tiles.openfreemap.org/styles/liberty";

const vectorSource = "https://tiles.openfreemap.org/planet";
const glyphs = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";

const palette = {
  land: "#f2efe3",
  green: "#d8e3c4",
  greenDeep: "#c6d8ac",
  water: "#a9d3e4",
  waterLine: "#8cc2d8",
  built: "#eae5d5",
  motorway: "#ffc95c",
  motorwayCase: "#e0a52f",
  major: "#ffffff",
  majorCase: "#d9d2bd",
  minor: "#faf8f0",
  minorCase: "#e2dbc6",
  rail: "#d5cdb8",
  label: "#4a5347",
  labelHalo: "#fbfcf6",
  boundary: "#cfc6ae",
};

/** Road width ramps, shared by a road and its casing so the casing reads as an outline. */
function roadWidth(stops: [number, number][], multiplier = 1) {
  return [
    "interpolate", ["linear"], ["zoom"],
    ...stops.flatMap(([zoom, width]) => [zoom, width * multiplier]),
  ] as unknown as StyleSpecification["layers"][number]["paint"];
}

const motorwayStops: [number, number][] = [[5, 0.6], [8, 1.8], [11, 5], [14, 11], [18, 26]];
const majorStops: [number, number][] = [[7, 0.4], [10, 1.6], [13, 4.5], [16, 11], [18, 22]];
const minorStops: [number, number][] = [[12, 0.6], [14, 2.2], [16, 5], [18, 13]];

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
