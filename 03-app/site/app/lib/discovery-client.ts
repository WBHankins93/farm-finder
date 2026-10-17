import type { FarmMapFeature, FarmSearchResponse, FarmSummary, LatLng, MapBounds, ServiceKey, SortMode, ViewMode } from "./discovery-contract";
import { serviceKeys } from "./discovery-contract";

export type DiscoveryUrlState = {
  q: string;
  near: string;
  radiusMiles: 25 | 50 | 100;
  bbox: MapBounds | null;
  category: string;
  product: string;
  services: ServiceKey[];
  sort: SortMode;
  view: ViewMode;
  browseAll: boolean;
  farmId: string;
};

function parseBounds(value: string | null): MapBounds | null {
  if (!value) return null;
  const bounds = value.split(",").map(Number);
  if (bounds.length !== 4 || bounds.some((item) => !Number.isFinite(item))) return null;
  const [west, south, east, north] = bounds;
  if (west >= east || south >= north || west < -180 || east > 180 || south < -90 || north > 90) return null;
  return [west, south, east, north];
}

export function parseDiscoveryUrl(params: URLSearchParams): DiscoveryUrlState {
  const q = params.get("q")?.trim() ?? "";
  const near = params.get("near") ?? params.get("place") ?? "";
  const requestedRadius = Number(params.get("radiusMiles"));
  const services = (params.get("services") ?? "")
    .split(",")
    .filter((value): value is ServiceKey => serviceKeys.includes(value as ServiceKey));
  const requestedSort = params.get("sort");
  const sort: SortMode = requestedSort === "distance" || requestedSort === "relevance" || requestedSort === "name"
    ? requestedSort
    : q ? "relevance" : near ? "distance" : "name";

  return {
    q,
    near,
    radiusMiles: requestedRadius === 25 || requestedRadius === 100 ? requestedRadius : 50,
    bbox: parseBounds(params.get("bbox")),
    category: params.get("category") ?? "",
    product: params.get("product") ?? "",
    services: Array.from(new Set(services)),
    sort,
    view: params.get("view") === "map" ? "map" : "list",
    browseAll: params.get("all") === "1",
    farmId: params.get("farm") ?? "",
  };
}

export function serializeDiscoveryUrl(state: DiscoveryUrlState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  if (state.near && !state.bbox) params.set("near", state.near);
  if (state.near && !state.bbox) params.set("radiusMiles", String(state.radiusMiles));
  if (state.bbox) params.set("bbox", state.bbox.map((value) => value.toFixed(4)).join(","));
  if (state.category) params.set("category", state.category);
  if (state.product) params.set("product", state.product);
  if (state.services.length) params.set("services", state.services.join(","));
  if (state.sort !== "name") params.set("sort", state.sort);
  if (state.view !== "list") params.set("view", state.view);
  if (state.browseAll) params.set("all", "1");
  if (state.farmId) params.set("farm", state.farmId);
  return params;
}

export function mergeCursorPage(current: FarmSearchResponse, next: FarmSearchResponse): FarmSearchResponse {
  const seen = new Set(current.items.map((farm) => farm.id));
  return { ...next, items: [...current.items, ...next.items.filter((farm) => !seen.has(farm.id))] };
}

export function retainSelectedFarm(current: FarmSummary | null, items: FarmSummary[], features: FarmMapFeature[]) {
  if (!current) return null;
  return items.some((farm) => farm.id === current.id) || features.some((feature) => feature.kind === "farm" && feature.id === current.id)
    ? current
    : null;
}

export function createLatestRequestGuard() {
  let sequence = 0;
  let activeController: AbortController | null = null;
  return {
    begin() {
      activeController?.abort();
      activeController = new AbortController();
      const requestSequence = ++sequence;
      const controller = activeController;
      return {
        signal: controller.signal,
        isLatest: () => requestSequence === sequence,
        cancel: () => controller.abort(),
      };
    },
    cancel() {
      activeController?.abort();
    },
  };
}

type GeolocationLike = {
  getCurrentPosition(
    success: (position: { coords: { latitude: number; longitude: number } }) => void,
    error: () => void,
    options: { enableHighAccuracy: boolean; timeout: number },
  ): void;
};

export function requestApproximateLocation(geolocation: GeolocationLike | null): Promise<LatLng | null> {
  return new Promise((resolve) => {
    if (!geolocation) {
      resolve(null);
      return;
    }
    geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: Math.round(coords.latitude * 1000) / 1000, lng: Math.round(coords.longitude * 1000) / 1000 }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: 8_000 },
    );
  });
}
