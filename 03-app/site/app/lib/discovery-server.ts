import productVocabulary from "../data/product-vocabulary.json";
import { foldAscii, loadDiscoveryIndex, type DiscoveryIndex } from "./discovery-index";
import { normalizePlace, normalizePlaceQuery, placeRank, placeWordsMatch } from "./place-match";
import type {
  DiscoveryQuery,
  DiscoveryScope,
  FarmMapCluster,
  FarmMapFeature,
  FarmMapResponse,
  FarmSearchResponse,
  FarmSummary,
  LatLng,
  MapBounds,
  PlaceSearchResponse,
  PlaceSuggestion,
  ServiceKey,
  SortMode,
} from "./discovery-contract";
import { serviceKeys } from "./discovery-contract";
import type { Farm } from "./farms";

/**
 * Bounded discovery queries over the national feed.
 *
 * Every query runs against the column-oriented index in `discovery-index.ts`
 * rather than an array of expanded records: full records are materialized only
 * for the rows a response actually returns. See that module for why.
 */

const milesPerKilometer = 0.621371;
const earthKilometers = 6371;
const defaultLimit = 30;
const maximumLimit = 50;
const mapLeafLimit = 2_000;

// Shared with scripts/build-web-feed.py via app/data/product-vocabulary.json so
// a browsed product count can never disagree with the filtered result.
const queryStopWords = new Set<string>(productVocabulary.queryStopWords);

function toRadians(value: number) {
  return (value * Math.PI) / 180;
}

function distanceMiles(origin: LatLng, latitude: number, longitude: number) {
  const latitudeDelta = toRadians(latitude - origin.lat);
  const longitudeDelta = toRadians(longitude - origin.lng);
  const value =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(toRadians(origin.lat)) *
      Math.cos(toRadians(latitude)) *
      Math.sin(longitudeDelta / 2) ** 2;
  return earthKilometers * 2 * Math.asin(Math.min(1, Math.sqrt(value))) * milesPerKilometer;
}

export function isMappableFarm(farm: Pick<Farm, "geoPrecision" | "latitude" | "longitude">) {
  return (
    farm.geoPrecision !== "ungeocoded" &&
    Number.isFinite(farm.latitude) &&
    Number.isFinite(farm.longitude) &&
    !(farm.latitude === 0 && farm.longitude === 0)
  );
}

function parseNumber(value: string | null) {
  if (value === null || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseRadius(value: string | null): 25 | 50 | 100 {
  const parsed = Number(value);
  return parsed === 25 || parsed === 100 ? parsed : 50;
}

function parseBounds(value: string | null): MapBounds | null {
  if (!value) return null;
  const numbers = value.split(",").map(Number);
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item))) return null;
  const [west, south, east, north] = numbers;
  if (west >= east || south >= north || west < -180 || east > 180 || south < -90 || north > 90) return null;
  return [west, south, east, north];
}

function parseServices(params: URLSearchParams): ServiceKey[] {
  const requested = params
    .getAll("services")
    .flatMap((value) => value.split(","))
    .filter((value): value is ServiceKey => serviceKeys.includes(value as ServiceKey));
  return Array.from(new Set(requested));
}

function parseSort(value: string | null, hasQuery: boolean, hasOrigin: boolean): SortMode {
  if (value === "name" || value === "relevance" || value === "distance") return value;
  if (hasQuery) return "relevance";
  return hasOrigin ? "distance" : "name";
}

/**
 * Parse a query without touching the index, so request parsing stays
 * synchronous. `near` is resolved to an origin during the query itself.
 */
export function parseDiscoveryQuery(params: URLSearchParams): DiscoveryQuery {
  const latitude = parseNumber(params.get("lat"));
  const longitude = parseNumber(params.get("lng"));
  const near = params.get("near")?.trim().slice(0, 120) ?? "";
  const coordinateOrigin =
    latitude !== null && longitude !== null &&
    latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
      ? { lat: latitude, lng: longitude }
      : null;
  const q = params.get("q")?.trim().slice(0, 120) ?? "";
  const requestedLimit = Math.trunc(parseNumber(params.get("limit")) ?? defaultLimit);

  return {
    q,
    near,
    origin: coordinateOrigin,
    radiusMiles: parseRadius(params.get("radiusMiles")),
    bbox: parseBounds(params.get("bbox")),
    category: params.get("category")?.trim().slice(0, 80) ?? "",
    product: params.get("product")?.trim().slice(0, 80) ?? "",
    services: parseServices(params),
    sort: parseSort(params.get("sort"), Boolean(q), Boolean(coordinateOrigin) || Boolean(near)),
    cursor: params.get("cursor")?.trim() ?? "",
    limit: Math.min(maximumLimit, Math.max(1, requestedLimit)),
  };
}

/** Resolve `near` against the index, leaving an explicit lat/lng untouched. */
function resolveQuery(index: DiscoveryIndex, query: DiscoveryQuery): DiscoveryQuery {
  const place = query.near ? index.placeBySlug.get(query.near) : null;
  const origin = query.origin ?? (place ? { lat: place.lat, lng: place.lng } : null);
  return { ...query, near: place?.slug ?? "", origin };
}

function queryTokens(query: string) {
  return foldAscii(query)
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 1 && !queryStopWords.has(token));
}

type Match = { row: number; distance: number | null; relevance: number };

/**
 * Score a record against the query tokens using the packed search blob.
 *
 * Weights match the previous per-field implementation: a name prefix beats a
 * name substring, which beats a product, a place, then anything else.
 */
function relevanceScore(index: DiscoveryIndex, row: number, tokens: string[]) {
  const start = index.textStart[row];
  const nameEnd = index.textNameEnd[row];
  const productsEnd = index.textProductsEnd[row];
  const placeEnd = index.textPlaceEnd[row];
  const end = index.textStart[row + 1];

  let score = 0;
  for (const token of tokens) {
    if (index.search.startsWith(token, start)) score += 12;
    else {
      const inName = index.search.indexOf(token, start);
      if (inName !== -1 && inName < nameEnd) score += 8;
    }
    const inProducts = index.search.indexOf(token, nameEnd);
    if (inProducts !== -1 && inProducts < productsEnd) score += 5;
    const inPlace = index.search.indexOf(token, productsEnd);
    if (inPlace !== -1 && inPlace < placeEnd) score += 4;
    const inOther = index.search.indexOf(token, placeEnd);
    if (inOther !== -1 && inOther < end) score += 1;
  }
  return score;
}

function withinBounds(index: DiscoveryIndex, row: number, bounds: MapBounds) {
  const latitude = index.latitude[row];
  const longitude = index.longitude[row];
  return longitude >= bounds[0] && latitude >= bounds[1] && longitude <= bounds[2] && latitude <= bounds[3];
}

function resolvedScope(index: DiscoveryIndex, query: DiscoveryQuery): DiscoveryScope {
  if (query.bbox) {
    return { mode: "area", label: "this map area", origin: null, radiusMiles: null, bounds: query.bbox };
  }
  if (query.origin) {
    const place = query.near ? index.placeBySlug.get(query.near) : null;
    return {
      mode: "nearby",
      label: place?.label ?? "your location",
      origin: query.origin,
      radiusMiles: query.radiusMiles,
      bounds: null,
    };
  }
  return { mode: "all", label: "all covered areas", origin: null, radiusMiles: null, bounds: null };
}

function matchingRows(index: DiscoveryIndex, query: DiscoveryQuery, mappableOnly = false): Match[] {
  const tokens = queryTokens(query.q);

  // One blob scan per token, then an intersection, instead of re-scanning the
  // dataset once per record.
  let textHits: Uint8Array | null = null;
  for (const token of tokens) {
    const hits = index.recordsContaining(token);
    if (textHits === null) textHits = hits;
    else for (let i = 0; i < textHits.length; i += 1) textHits[i] &= hits[i];
  }

  const categoryCode = query.category ? index.categories.indexOf(query.category) : -1;
  if (query.category && categoryCode === -1) return [];
  const productBit = query.product ? index.productIds.indexOf(query.product) : -1;
  const productMask = productBit === -1 ? 0 : 1 << productBit;
  let serviceMask = 0;
  for (const service of query.services) serviceMask |= 1 << index.flag[service];

  const mappableBit = 1 << index.flag.mappable;
  const matched: Match[] = [];

  for (let row = 0; row < index.count; row += 1) {
    if (textHits && textHits[row] === 0) continue;
    const flags = index.flags[row];
    const mappable = (flags & mappableBit) !== 0;
    if (mappableOnly && !mappable) continue;
    if (categoryCode !== -1 && index.category[row] !== categoryCode) continue;
    if (productMask && (index.productMask[row] & productMask) === 0) continue;
    if (serviceMask && (flags & serviceMask) !== serviceMask) continue;
    if (query.bbox && (!mappable || !withinBounds(index, row, query.bbox))) continue;

    const distance =
      query.origin && mappable
        ? distanceMiles(query.origin, index.latitude[row], index.longitude[row])
        : null;
    if (!query.bbox && query.origin && (distance === null || distance > query.radiusMiles)) continue;

    matched.push({ row, distance, relevance: tokens.length ? relevanceScore(index, row, tokens) : 0 });
  }

  const infinity = Number.POSITIVE_INFINITY;
  matched.sort((a, b) => {
    if (query.sort === "distance") {
      return (a.distance ?? infinity) - (b.distance ?? infinity) || index.nameRank[a.row] - index.nameRank[b.row];
    }
    if (query.sort === "relevance") {
      return (
        b.relevance - a.relevance ||
        (a.distance ?? infinity) - (b.distance ?? infinity) ||
        index.nameRank[a.row] - index.nameRank[b.row]
      );
    }
    return index.nameRank[a.row] - index.nameRank[b.row];
  });
  return matched;
}

function farmSummary(index: DiscoveryIndex, match: Match): FarmSummary {
  const farm = index.record(match.row);
  return {
    id: farm.id,
    name: farm.name,
    category: farm.category,
    region: farm.region,
    parish: farm.parish,
    state: farm.state,
    city: farm.city,
    productsText: farm.productsText,
    products: farm.products,
    marketPresence: farm.marketPresence,
    website: farm.website,
    contact: farm.contact,
    farmersMarket: farm.farmersMarket,
    onFarm: farm.onFarm,
    csa: farm.csa,
    ships: farm.ships,
    onlineStore: farm.onlineStore,
    latitude: farm.latitude,
    longitude: farm.longitude,
    geoPrecision: farm.geoPrecision,
    distanceMiles: match.distance === null ? null : Math.round(match.distance * 10) / 10,
  };
}

function decodeCursor(cursor: string) {
  if (!cursor) return 0;
  try {
    const offset = Number(atob(cursor.replace(/-/g, "+").replace(/_/g, "/")));
    return Number.isInteger(offset) && offset >= 0 ? offset : 0;
  } catch {
    return 0;
  }
}

function encodeCursor(offset: number) {
  return btoa(String(offset)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export async function searchFarms(rawQuery: DiscoveryQuery): Promise<FarmSearchResponse> {
  const index = await loadDiscoveryIndex();
  const query = resolveQuery(index, rawQuery);
  const matched = matchingRows(index, query);
  const offset = Math.min(decodeCursor(query.cursor), matched.length);
  const items = matched.slice(offset, offset + query.limit).map((match) => farmSummary(index, match));
  const nextOffset = offset + items.length;
  return {
    items,
    total: matched.length,
    nextCursor: nextOffset < matched.length ? encodeCursor(nextOffset) : null,
    scope: resolvedScope(index, query),
    sort: query.sort,
    releaseId: index.releaseId,
  };
}

function worldPixel(point: LatLng, zoom: number) {
  const scale = 256 * 2 ** zoom;
  const sine = Math.min(0.9999, Math.max(-0.9999, Math.sin(toRadians(point.lat))));
  return {
    x: ((point.lng + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * scale,
  };
}

function clusterFarms(index: DiscoveryIndex, items: Match[], zoom: number): FarmMapFeature[] {
  const groups = new Map<string, Match[]>();
  const safeZoom = Math.min(16, Math.max(2, Math.trunc(zoom)));
  for (const item of items) {
    const latitude = index.latitude[item.row];
    const longitude = index.longitude[item.row];
    const key =
      items.length <= mapLeafLimit
        ? `exact:${longitude}:${latitude}`
        : (() => {
            const pixel = worldPixel({ lat: latitude, lng: longitude }, safeZoom);
            return `${Math.floor(pixel.x / 64)}:${Math.floor(pixel.y / 64)}`;
          })();
    const group = groups.get(key);
    if (group) group.push(item);
    else groups.set(key, [item]);
  }

  return Array.from(groups.entries()).map(([cell, group]) => {
    if (group.length === 1) {
      const row = group[0].row;
      const farm = index.record(row);
      return {
        kind: "farm" as const,
        id: farm.id,
        name: farm.name,
        category: farm.category,
        longitude: index.longitude[row],
        latitude: index.latitude[row],
        geoPrecision: index.precisionOf(row),
      };
    }

    let west = 180;
    let south = 90;
    let east = -180;
    let north = -90;
    let longitude = 0;
    let latitude = 0;
    for (const { row } of group) {
      west = Math.min(west, index.longitude[row]);
      south = Math.min(south, index.latitude[row]);
      east = Math.max(east, index.longitude[row]);
      north = Math.max(north, index.latitude[row]);
      longitude += index.longitude[row];
      latitude += index.latitude[row];
    }
    const terminal = safeZoom >= 16 || (west === east && south === north);
    const cluster: FarmMapCluster = {
      kind: "cluster",
      id: `z${safeZoom}-${cell}`,
      longitude: longitude / group.length,
      latitude: latitude / group.length,
      count: group.length,
      bounds: [west, south, east, north],
      terminal,
      ...(terminal
        ? { farmIds: group.slice(0, maximumLimit).map(({ row }) => index.record(row).id) }
        : {}),
    };
    return cluster;
  });
}

export async function mapFarms(rawQuery: DiscoveryQuery, zoom: number): Promise<FarmMapResponse> {
  const index = await loadDiscoveryIndex();
  const query = resolveQuery(index, rawQuery);
  const matched = matchingRows(index, query, true);
  return {
    features: clusterFarms(index, matched, zoom),
    total: matched.length,
    scope: resolvedScope(index, query),
    releaseId: index.releaseId,
  };
}

function toPlaceSuggestion(place: DiscoveryIndex["places"][number]): PlaceSuggestion {
  return {
    slug: place.slug,
    name: place.name,
    state: place.state,
    label: place.label,
    centroid: { lat: place.lat, lng: place.lng },
    farmCount: place.farmCount,
  };
}

// Place labels never change within an isolate, so normalize them once rather
// than on every autocomplete keystroke (≈11 ms → well under 1 ms per request).
type PlaceLabel = { label: string; words: string[] };
const normalizedPlaceLabels = new WeakMap<DiscoveryIndex["places"], PlaceLabel[]>();

function placeLabels(places: DiscoveryIndex["places"]): PlaceLabel[] {
  let labels = normalizedPlaceLabels.get(places);
  if (!labels) {
    labels = places.map((place) => {
      const label = normalizePlace(place.label);
      return { label, words: label.split(" ") };
    });
    normalizedPlaceLabels.set(places, labels);
  }
  return labels;
}

export async function searchPlaces(term: string, requestedLimit: number): Promise<PlaceSearchResponse> {
  const index = await loadDiscoveryIndex();
  // Punctuation- and state-name-tolerant: "madison wi" and "madison wisconsin"
  // both reach "Madison, WI". See app/lib/place-match.ts.
  const query = normalizePlaceQuery(term.slice(0, 120));
  const limit = Math.min(8, Math.max(1, requestedLimit || 8));
  if (query.replace(/ /g, "").length < 2) return { items: [], releaseId: index.releaseId };
  const labels = placeLabels(index.places);
  const queryWords = query.split(" ");
  const matches: { place: DiscoveryIndex["places"][number]; rank: number }[] = [];
  index.places.forEach((place, position) => {
    const { label, words } = labels[position];
    if (placeWordsMatch(words, queryWords)) matches.push({ place, rank: placeRank(label, query) });
  });
  const items = matches
    .sort((a, b) =>
      a.rank - b.rank ||
      b.place.farmCount - a.place.farmCount ||
      a.place.label.localeCompare(b.place.label))
    .slice(0, limit)
    .map(({ place }) => toPlaceSuggestion(place));
  return { items, releaseId: index.releaseId };
}

export async function getFarm(id: string): Promise<Farm | null> {
  const index = await loadDiscoveryIndex();
  const row = index.positionOf(id);
  return row === -1 ? null : index.record(row);
}

/** Totals for callers that need the dataset's shape without querying it. */
export async function discoveryDatasetSummary() {
  const index = await loadDiscoveryIndex();
  return { total: index.count, states: index.states, releaseId: index.releaseId };
}

export type TickerFarm = { id: string; name: string; city: string; state: string };

/**
 * Names the hero ticker will not showcase.
 *
 * Nothing is removed from the directory — a named candidate is durable, and
 * these records stay searchable. This is about what the front page *features*:
 * a national sample surfaced "Wakulla County Tax Collector's Office", and an
 * operator roster lifted from a licence register leaves rows shaped like
 * "HERSCHBERGER, LEVI U.". Both are real entries worth fixing in the data
 * lane; neither is a farm anyone wants to see scrolling under the headline.
 */
const notFeaturable = [
  /\b(tax collector|county clerk|clerk of court|city of|town of|county of|department of|district office|chamber of commerce|extension (service|office)|university|school district|public library)\b/i,
  /^[A-Z][A-Z'\-]+(?: (?:JR|SR|I{1,3}|IV))?, [A-Z][A-Z'\-]+/,
];

function featurable(name: string) {
  return name.length > 2 && !notFeaturable.some((pattern) => pattern.test(name));
}

/**
 * A short roster of farms for the hero ticker — names and places only.
 *
 * Two modes, and the fallback is the interesting one. With a place it is the
 * nearest farms to that place, which is the personalised case. Without one it
 * walks the index at a fixed stride instead of taking the first N rows: the
 * index is ordered by name, so `slice(0, 42)` would be forty-two farms
 * beginning with "A" from whichever states happen to sort first, which reads
 * as a bug. A stride spreads the sample across the whole country.
 *
 * Returns display text only. The ticker is scenery; it has no business
 * carrying coordinates, contacts or service flags into the page payload.
 */
export async function tickerFarms(near: string, limit = 42): Promise<{ label: string; farms: TickerFarm[] }> {
  const take = Math.min(60, Math.max(6, Math.trunc(limit)));

  if (near) {
    const nearby = await searchFarms(
      parseDiscoveryQuery(new URLSearchParams({ near, radiusMiles: "50", sort: "distance", limit: String(take) })),
    );
    const named = nearby.items.filter((farm) => farm.name && farm.state && featurable(farm.name));
    // Only when the place actually resolved. An unrecognised `near` falls back
    // to an unscoped search, which would label the band "Near all covered
    // areas" over the alphabetical head of the index — wrong twice over.
    if (nearby.scope.mode === "nearby" && named.length >= 6) {
      return {
        label: nearby.scope.label,
        farms: named.map((farm) => ({ id: farm.id, name: farm.name, city: farm.city, state: farm.state })),
      };
    }
  }

  const index = await loadDiscoveryIndex();
  // One slot per stride, and a rejected row is replaced from within its own
  // stride rather than by moving the whole window. Shrinking the stride to
  // refill the quota would pull every entry out of the alphabetical head of
  // the index — forty farms from A to F, which is not a national sample.
  const stride = Math.max(1, Math.floor(index.count / take));
  const farms: TickerFarm[] = [];
  for (let slot = 0; slot < take; slot += 1) {
    const start = slot * stride;
    for (let row = start; row < Math.min(start + stride, index.count); row += 1) {
      const farm = index.record(row);
      // An entry with no place reads as half a thought; try the next row.
      if (!farm.name || !farm.state || !farm.city || !featurable(farm.name)) continue;
      farms.push({ id: farm.id, name: farm.name, city: farm.city, state: farm.state });
      break;
    }
  }
  return { label: "", farms };
}
