import type { ExpressionSpecification } from "maplibre-gl";
import { categoryColors } from "./farms";
import type { BasemapId } from "./map-styles";

/**
 * Everything the viewer can change about the map, and the paint that follows
 * from it.
 *
 * This module is deliberately free of MapLibre instances and React: the only
 * thing it does is turn a small settings object into style expressions. That
 * keeps the interesting part — what the map looks like at 68,618 farms — under
 * unit test, because the failure mode here is not a crash, it is a map that
 * renders as an unreadable mat of dots and nobody notices until it ships.
 *
 * The governing rule for every option below: **nothing removes a farm.** A
 * spotlight dims, density summarises, labels add. A viewer who filters the
 * directory does that in the filter sheet, where the result count changes with
 * it and the page says so.
 */

/** How farm points are drawn. Density is a summary of the same points, not a subset. */
export type PinMode = "pins" | "density" | "both";

/** Whether the detailed basemap is allowed to tilt. `flat` pins pitch at 0. */
export type TiltMode = "auto" | "flat";

export type MapOptions = {
  basemap: BasemapId;
  pins: PinMode;
  /** A `farm.category`, or "" for no spotlight. Never filters; only dims the rest. */
  spotlight: string;
  /** Farm names drawn beside their pins once the map is zoomed in enough to fit them. */
  labels: boolean;
  tilt: TiltMode;
  scale: boolean;
};

export const defaultMapOptions: MapOptions = {
  basemap: "guide",
  pins: "pins",
  spotlight: "",
  labels: false,
  tilt: "auto",
  scale: false,
};

export const pinModes: { id: PinMode; label: string; hint: string }[] = [
  { id: "pins", label: "Pins", hint: "One dot per farm" },
  { id: "density", label: "Density", hint: "Where farms cluster, without the dots" },
  { id: "both", label: "Both", hint: "Density underneath, pins on top" },
];

export const spotlightCategories = Object.keys(categoryColors);

const storageKey = "farmfinder.map-options";

/**
 * Read stored options, keeping anything unrecognised out.
 *
 * Per-viewer convenience only. A browser with site data blocked, a private
 * window, or a stored shape from an older build all resolve to the defaults
 * rather than throwing — the map has to draw either way.
 */
export function readMapOptions(): MapOptions {
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return defaultMapOptions;
    return coerceMapOptions(JSON.parse(raw));
  } catch {
    return defaultMapOptions;
  }
}

export function writeMapOptions(options: MapOptions): void {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(options));
  } catch {
    /* storage unavailable */
  }
}

/** Narrow an unknown stored value to `MapOptions`, field by field. */
export function coerceMapOptions(value: unknown): MapOptions {
  if (!value || typeof value !== "object") return defaultMapOptions;
  const raw = value as Record<string, unknown>;
  return {
    basemap: raw.basemap === "detailed" ? "detailed" : "guide",
    pins: raw.pins === "density" || raw.pins === "both" ? raw.pins : "pins",
    spotlight: typeof raw.spotlight === "string" && spotlightCategories.includes(raw.spotlight) ? raw.spotlight : "",
    labels: raw.labels === true,
    tilt: raw.tilt === "flat" ? "flat" : "auto",
    scale: raw.scale === true,
  };
}

/** Category → pin colour, as a MapLibre `match` over the published category values. */
export const categoryExpression: ExpressionSpecification = [
  "match", ["get", "category"],
  ...(Object.entries(categoryColors).flatMap(([category, color]) => [category, color]) as [string, string]),
  "#596b60",
] as ExpressionSpecification;

/**
 * Pin radius and opacity, as one zoom ramp whose stops are data-driven.
 *
 * The shape matters: MapLibre allows exactly **one** zoom-based `interpolate`
 * per expression, so `["case", spotlit, <zoom ramp>, <zoom ramp>]` is rejected
 * — and rejected paint is dropped, which shows up as a map that ignores the
 * option rather than as an error anyone sees. The valid form is the other way
 * round: one zoom ramp, each stop a `case`.
 *
 * The numbers: the old ramp went 4.5px at z3 to 8px at z10 with a flat 2px
 * ring, which is why a metro search read as a rust-coloured mat. At z8 a
 * 50-mile radius puts several hundred 12px discs (8px plus two 2px rings)
 * inside a few hundred pixels, so the overlaps merge into one shape. Smaller
 * dots, thinner rings and some transparency at low zoom let overlap read as
 * density — two farms on a pixel are darker than one — and everything grows
 * back to a comfortable target by the zoom where you are picking one out.
 */
const radiusStops: [number, number][] = [[3, 2.6], [6, 3.4], [9, 5], [12, 7], [16, 9]];
const opacityStops: [number, number][] = [[3, 0.62], [8, 0.78], [11, 0.96]];

/** How far a farm outside the spotlight is pushed back. Never to nothing. */
const dimRadius = 0.72;
const dimOpacity = 0.22;

function zoomRamp(
  stops: [number, number][],
  dim: (value: number) => number,
  spotlit: ExpressionSpecification | null,
): ExpressionSpecification {
  return [
    "interpolate", ["linear"], ["zoom"],
    ...stops.flatMap(([zoom, value]) => [
      zoom,
      spotlit ? (["case", spotlit, value, dim(value)] as ExpressionSpecification) : value,
    ]),
  ] as unknown as ExpressionSpecification;
}

/**
 * Paint for the farm-point layer under the current options.
 *
 * With a spotlight set this returns `case` expressions keyed on the farm's own
 * category, so matching farms keep full size and opacity and the rest fade to a
 * background texture. Every farm stays on the map and stays clickable.
 */
export function farmPointPaint(options: MapOptions) {
  const spotlit = options.spotlight
    ? (["==", ["get", "category"], options.spotlight] as ExpressionSpecification)
    : null;

  return {
    "circle-color": categoryExpression,
    "circle-radius": zoomRamp(radiusStops, (value) => Number((value * dimRadius).toFixed(2)), spotlit),
    "circle-opacity": zoomRamp(opacityStops, () => dimOpacity, spotlit),
    // The ring is what separates touching pins. It has to scale with the dot,
    // or at low zoom the rings alone merge into a pale sheet.
    "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 3, 0.6, 9, 1.1, 13, 1.8] as ExpressionSpecification,
    "circle-stroke-color": "#fbfcf6",
    "circle-stroke-opacity": spotlit
      ? (["case", spotlit, 1, 0.25] as ExpressionSpecification)
      : 1,
  };
}

/**
 * Paint for the density underlay.
 *
 * A heatmap over the same source as the pins — it summarises them, it does not
 * replace them. The weight is flat because every farm counts once; this is a
 * count of farms, not an importance ranking, and shading it any other way would
 * be inventing a claim the data does not make. Server-side clusters carry a
 * `count`, so they are weighted by it and the two stay comparable.
 */
export function densityPaint(options: MapOptions) {
  // In "both" the heat is a hint under the dots; alone it is the whole picture.
  const peak = options.pins === "both" ? 0.5 : 0.85;
  return {
    "heatmap-weight": ["coalesce", ["get", "count"], 1] as ExpressionSpecification,
    "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 3, 0.7, 9, 1.3, 13, 2] as ExpressionSpecification,
    "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 12, 8, 24, 13, 42] as ExpressionSpecification,
    // Ends transparent so the basemap shows through where there are no farms;
    // the ramp runs through the directory's own greens into its rust accent.
    "heatmap-color": [
      "interpolate", ["linear"], ["heatmap-density"],
      0, "rgba(255,250,240,0)",
      0.2, "rgba(190,209,170,0.55)",
      0.45, "rgba(125,163,120,0.72)",
      0.7, "rgba(198,142,54,0.8)",
      1, "rgba(198,94,54,0.88)",
    ] as ExpressionSpecification,
    "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 3, peak, 12, peak, 14, 0] as ExpressionSpecification,
  };
}

/**
 * Layout for the optional farm-name labels.
 *
 * `text-allow-overlap` stays false: where names cannot all fit, MapLibre drops
 * the ones that collide. That hides a *label*, never a farm — the pin it
 * belongs to is drawn by a separate layer that always renders every point.
 */
export function farmLabelLayout() {
  return {
    "text-field": ["get", "name"] as ExpressionSpecification,
    "text-font": ["Noto Sans Regular"] as string[],
    "text-size": ["interpolate", ["linear"], ["zoom"], 12, 10, 16, 13] as ExpressionSpecification,
    "text-offset": [0, 1] as [number, number],
    "text-anchor": "top" as const,
    "text-max-width": 9,
    "text-padding": 4,
    "text-optional": true,
    "text-allow-overlap": false,
  };
}

/** Which layers should be on the map for a given pin mode. */
export function layerVisibility(options: MapOptions) {
  return {
    "farm-density": options.pins === "density" || options.pins === "both",
    "farm-points": options.pins !== "density",
    "farm-labels": options.labels && options.pins !== "density",
  };
}

/** One-line summary of the active options, for the map's status region. */
export function describeMapOptions(options: MapOptions, basemapLabel: string): string {
  const parts = [`${basemapLabel} basemap`, pinModes.find((mode) => mode.id === options.pins)?.label.toLowerCase() ?? ""];
  if (options.spotlight) parts.push(`${options.spotlight} highlighted, other farms dimmed but still shown`);
  if (options.labels) parts.push("farm names shown");
  if (options.tilt === "flat") parts.push("tilt off");
  return `${parts.filter(Boolean).join(", ")}.`;
}
