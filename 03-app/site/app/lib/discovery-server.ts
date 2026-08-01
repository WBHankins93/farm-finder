import sourceFarms from "../data/farms.json";
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

const farms = sourceFarms as Farm[];
const farmById = new Map(farms.map((farm) => [farm.id, farm]));
const releaseId = `legacy-web-${farms.length}`;
const milesPerKilometer = 0.621371;
const earthKilometers = 6371;
const defaultLimit = 30;
const maximumLimit = 50;
const mapLeafLimit = 2_000;

const productTokens: Record<string, string[]> = {
  vegetables: ["vegetable", "produce", "greens", "lettuce", "tomato", "okra", "squash", "peas", "cucumber", "microgreen", "herbs"],
  fruit: ["fruit", "berry", "berries", "blueberr", "strawberr", "peach", "watermelon", "melon", "citrus", "satsuma", "orchard"],
  eggs: ["egg"],
  beef: ["beef", "cattle", "wagyu"],
  pork: ["pork", "hog", "berkshire", "bacon", "sausage"],
  poultry: ["chicken", "poultry", "turkey", "duck", "broiler"],
  honey: ["honey", "apiar", "bee", "beeswax"],
  dairy: ["dairy", "milk", "cheese", "creamery", "yogurt"],
  seafood: ["seafood", "crawfish", "shrimp", "crab", "fish", "oyster"],
  rice: ["rice", "grain", "grits", "cornmeal"],
  flowers: ["flower", "nursery", "plant", "seedling"],
  mushrooms: ["mushroom", "fungi"],
};

const queryStopWords = new Set(["a", "an", "and", "farm", "farms", "find", "from", "in", "me", "near", "of", "or", "the", "with"]);

function slugify(value: string) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function isMappable(farm: Farm) {
  return (
    farm.geoPrecision !== "ungeocoded" &&
    Number.isFinite(farm.latitude) &&
    Number.isFinite(farm.longitude) &&
    !(farm.latitude === 0 && farm.longitude === 0)
  );
}

function toRadians(value: number) {
  return (value * Math.PI) / 180;
}

function distanceMiles(origin: LatLng, farm: Pick<Farm, "latitude" | "longitude">) {
  const latitudeDelta = toRadians(farm.latitude - origin.lat);
  const longitudeDelta = toRadians(farm.longitude - origin.lng);
  const value =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(toRadians(origin.lat)) *
      Math.cos(toRadians(farm.latitude)) *
      Math.sin(longitudeDelta / 2) ** 2;
  return earthKilometers * 2 * Math.asin(Math.min(1, Math.sqrt(value))) * milesPerKilometer;
}

function placeKey(city: string, state: string) {
  return `${slugify(city)}-${state.toLocaleLowerCase()}`;
}

function buildPlaces(): PlaceSuggestion[] {
  const grouped = new Map<
    string,
    { city: string; state: string; latitude: number; longitude: number; mappable: number; farms: number }
  >();

  for (const farm of farms) {
    const city = farm.city.trim();
    const state = farm.state.trim().toLocaleUpperCase();
    if (!city || !state) continue;
    const key = placeKey(city, state);
    const current = grouped.get(key) ?? { city, state, latitude: 0, longitude: 0, mappable: 0, farms: 0 };
    current.farms += 1;
    if (isMappable(farm)) {
      current.latitude += farm.latitude;
      current.longitude += farm.longitude;
      current.mappable += 1;
    }
    grouped.set(key, current);
  }

  return Array.from(grouped.entries())
    .filter(([, value]) => value.mappable > 0)
    .map(([slug, value]) => ({
      slug,
      name: value.city,
      state: value.state,
      label: `${value.city}, ${value.state}`,
      centroid: {
        lat: value.latitude / value.mappable,
        lng: value.longitude / value.mappable,
      },
      farmCount: value.farms,
    }))
    .sort((a, b) => b.farmCount - a.farmCount || a.label.localeCompare(b.label));
}

const places = buildPlaces();
const placeBySlug = new Map(places.map((place) => [place.slug, place]));

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

export function parseDiscoveryQuery(params: URLSearchParams): DiscoveryQuery {
  const latitude = parseNumber(params.get("lat"));
  const longitude = parseNumber(params.get("lng"));
  const near = params.get("near")?.trim() ?? "";
  const place = near ? placeBySlug.get(near) : null;
  const coordinateOrigin = latitude !== null && longitude !== null && latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
    ? { lat: latitude, lng: longitude }
    : null;
  const origin = coordinateOrigin ?? place?.centroid ?? null;
  const q = params.get("q")?.trim().slice(0, 120) ?? "";
  const requestedLimit = Math.trunc(parseNumber(params.get("limit")) ?? defaultLimit);

  return {
    q,
    near: place?.slug ?? "",
    origin,
    radiusMiles: parseRadius(params.get("radiusMiles")),
    bbox: parseBounds(params.get("bbox")),
    category: params.get("category")?.trim().slice(0, 80) ?? "",
    product: params.get("product")?.trim().slice(0, 80) ?? "",
    services: parseServices(params),
    sort: parseSort(params.get("sort"), Boolean(q), Boolean(origin)),
    cursor: params.get("cursor")?.trim() ?? "",
    limit: Math.min(maximumLimit, Math.max(1, requestedLimit)),
  };
}

function queryTokens(query: string) {
  return query
    .toLocaleLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 1 && !queryStopWords.has(token));
}

function farmSearchFields(farm: Farm) {
  return {
    name: farm.name.toLocaleLowerCase(),
    products: `${farm.productsText} ${farm.products.join(" ")}`.toLocaleLowerCase(),
    place: `${farm.city} ${farm.state} ${farm.parish} ${farm.region}`.toLocaleLowerCase(),
    other: `${farm.category} ${farm.marketPresence} ${farm.notes}`.toLocaleLowerCase(),
  };
}

function relevanceScore(farm: Farm, tokens: string[]) {
  if (tokens.length === 0) return 0;
  const fields = farmSearchFields(farm);
  let score = 0;
  for (const token of tokens) {
    if (fields.name.startsWith(token)) score += 12;
    else if (fields.name.includes(token)) score += 8;
    if (fields.products.includes(token)) score += 5;
    if (fields.place.includes(token)) score += 4;
    if (fields.other.includes(token)) score += 1;
  }
  return score;
}

function matchesText(farm: Farm, tokens: string[]) {
  if (tokens.length === 0) return true;
  const fields = farmSearchFields(farm);
  const haystack = `${fields.name} ${fields.products} ${fields.place} ${fields.other}`;
  return tokens.every((token) => haystack.includes(token));
}

function matchesProduct(farm: Farm, product: string) {
  if (!product) return true;
  const tokens = productTokens[product];
  if (!tokens) return true;
  const haystack = `${farm.productsText} ${farm.products.join(" ")} ${farm.category} ${farm.notes}`.toLocaleLowerCase();
  return tokens.some((token) => haystack.includes(token));
}

function withinBounds(farm: Farm, bounds: MapBounds) {
  return farm.longitude >= bounds[0] && farm.latitude >= bounds[1] && farm.longitude <= bounds[2] && farm.latitude <= bounds[3];
}

function resolvedScope(query: DiscoveryQuery): DiscoveryScope {
  if (query.bbox) {
    return { mode: "area", label: "this map area", origin: null, radiusMiles: null, bounds: query.bbox };
  }
  if (query.origin) {
    const place = query.near ? placeBySlug.get(query.near) : null;
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

type MatchedFarm = { farm: Farm; distance: number | null; relevance: number };

function matchingFarms(query: DiscoveryQuery, mappableOnly = false): MatchedFarm[] {
  const tokens = queryTokens(query.q);
  const radius = query.radiusMiles;
  const matched: MatchedFarm[] = [];

  for (const farm of farms) {
    if (mappableOnly && !isMappable(farm)) continue;
    if (query.category && farm.category !== query.category) continue;
    if (!matchesProduct(farm, query.product)) continue;
    if (!query.services.every((service) => farm[service])) continue;
    if (!matchesText(farm, tokens)) continue;
    if (query.bbox && (!isMappable(farm) || !withinBounds(farm, query.bbox))) continue;

    const distance = query.origin && isMappable(farm) ? distanceMiles(query.origin, farm) : null;
    if (!query.bbox && query.origin && (distance === null || distance > radius)) continue;
    matched.push({ farm, distance, relevance: relevanceScore(farm, tokens) });
  }

  matched.sort((a, b) => {
    if (query.sort === "distance") return (a.distance ?? Number.POSITIVE_INFINITY) - (b.distance ?? Number.POSITIVE_INFINITY) || a.farm.id.localeCompare(b.farm.id);
    if (query.sort === "relevance") return b.relevance - a.relevance || (a.distance ?? Number.POSITIVE_INFINITY) - (b.distance ?? Number.POSITIVE_INFINITY) || a.farm.id.localeCompare(b.farm.id);
    return a.farm.name.localeCompare(b.farm.name) || a.farm.id.localeCompare(b.farm.id);
  });
  return matched;
}

function farmSummary(item: MatchedFarm): FarmSummary {
  const { farm } = item;
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
    distanceMiles: item.distance === null ? null : Math.round(item.distance * 10) / 10,
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

export function searchFarms(query: DiscoveryQuery): FarmSearchResponse {
  const matched = matchingFarms(query);
  const offset = Math.min(decodeCursor(query.cursor), matched.length);
  const items = matched.slice(offset, offset + query.limit).map(farmSummary);
  const nextOffset = offset + items.length;
  return {
    items,
    total: matched.length,
    nextCursor: nextOffset < matched.length ? encodeCursor(nextOffset) : null,
    scope: resolvedScope(query),
    sort: query.sort,
    releaseId,
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

function clusterFarms(items: MatchedFarm[], zoom: number): FarmMapFeature[] {
  const groups = new Map<string, MatchedFarm[]>();
  const safeZoom = Math.min(16, Math.max(2, Math.trunc(zoom)));
  for (const item of items) {
    const key = items.length <= mapLeafLimit
      ? `exact:${item.farm.longitude}:${item.farm.latitude}`
      : (() => {
          const pixel = worldPixel({ lat: item.farm.latitude, lng: item.farm.longitude }, safeZoom);
          return `${Math.floor(pixel.x / 64)}:${Math.floor(pixel.y / 64)}`;
        })();
    const group = groups.get(key);
    if (group) group.push(item);
    else groups.set(key, [item]);
  }

  return Array.from(groups.entries()).map(([cell, group]) => {
    if (group.length === 1) {
      const farm = group[0].farm;
      return {
        kind: "farm" as const,
        id: farm.id,
        name: farm.name,
        category: farm.category,
        longitude: farm.longitude,
        latitude: farm.latitude,
        geoPrecision: farm.geoPrecision,
      };
    }

    let west = 180;
    let south = 90;
    let east = -180;
    let north = -90;
    let longitude = 0;
    let latitude = 0;
    for (const { farm } of group) {
      west = Math.min(west, farm.longitude);
      south = Math.min(south, farm.latitude);
      east = Math.max(east, farm.longitude);
      north = Math.max(north, farm.latitude);
      longitude += farm.longitude;
      latitude += farm.latitude;
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
      ...(terminal ? { farmIds: group.slice(0, maximumLimit).map(({ farm }) => farm.id) } : {}),
    };
    return cluster;
  });
}

export function mapFarms(query: DiscoveryQuery, zoom: number): FarmMapResponse {
  const matched = matchingFarms(query, true);
  return {
    features: clusterFarms(matched, zoom),
    total: matched.length,
    scope: resolvedScope(query),
    releaseId,
  };
}

export function searchPlaces(term: string, requestedLimit: number): PlaceSearchResponse {
  const normalized = term.trim().toLocaleLowerCase();
  const limit = Math.min(8, Math.max(1, requestedLimit || 8));
  if (normalized.length < 2) return { items: [], releaseId };
  const items = places
    .filter((place) => place.label.toLocaleLowerCase().includes(normalized))
    .sort((a, b) => {
      const aStarts = a.label.toLocaleLowerCase().startsWith(normalized) ? 1 : 0;
      const bStarts = b.label.toLocaleLowerCase().startsWith(normalized) ? 1 : 0;
      return bStarts - aStarts || b.farmCount - a.farmCount || a.label.localeCompare(b.label);
    })
    .slice(0, limit);
  return { items, releaseId };
}

export function getFarm(id: string) {
  return farmById.get(id) ?? null;
}
