import type { Farm } from "./farms";

export const serviceKeys = ["farmersMarket", "onFarm", "csa", "ships", "onlineStore"] as const;

export type ServiceKey = (typeof serviceKeys)[number];
export type SortMode = "distance" | "relevance" | "name";
export type ViewMode = "list" | "map";
export type LatLng = { lat: number; lng: number };
export type MapBounds = [west: number, south: number, east: number, north: number];

export type DiscoveryQuery = {
  q: string;
  near: string;
  origin: LatLng | null;
  radiusMiles: 25 | 50 | 100;
  bbox: MapBounds | null;
  category: string;
  product: string;
  services: ServiceKey[];
  sort: SortMode;
  cursor: string;
  limit: number;
};

export type DiscoveryScope = {
  mode: "all" | "nearby" | "area";
  label: string;
  origin: LatLng | null;
  radiusMiles: number | null;
  bounds: MapBounds | null;
};

export type FarmSummary = Pick<
  Farm,
  | "id"
  | "name"
  | "category"
  | "region"
  | "parish"
  | "state"
  | "city"
  | "productsText"
  | "products"
  | "marketPresence"
  | "website"
  | "contact"
  | "farmersMarket"
  | "onFarm"
  | "csa"
  | "ships"
  | "onlineStore"
  | "latitude"
  | "longitude"
  | "geoPrecision"
> & {
  distanceMiles: number | null;
};

export type PlaceSuggestion = {
  slug: string;
  name: string;
  state: string;
  label: string;
  centroid: LatLng;
  farmCount: number;
};

export type FarmSearchResponse = {
  items: FarmSummary[];
  total: number;
  nextCursor: string | null;
  scope: DiscoveryScope;
  sort: SortMode;
  releaseId: string;
};

export type FarmMapPoint = {
  kind: "farm";
  id: string;
  name: string;
  category: string;
  longitude: number;
  latitude: number;
  geoPrecision: string;
};

export type FarmMapCluster = {
  kind: "cluster";
  id: string;
  longitude: number;
  latitude: number;
  count: number;
  bounds: MapBounds;
  terminal: boolean;
  farmIds?: string[];
};

export type FarmMapFeature = FarmMapPoint | FarmMapCluster;

export type FarmMapResponse = {
  features: FarmMapFeature[];
  total: number;
  scope: DiscoveryScope;
  releaseId: string;
};

export type PlaceSearchResponse = {
  items: PlaceSuggestion[];
  releaseId: string;
};

export type ApiError = {
  error: string;
  details?: string[];
};
