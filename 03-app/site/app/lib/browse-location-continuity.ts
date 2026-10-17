import { parseDiscoveryUrl, serializeDiscoveryUrl } from "./discovery-client";

export type DiscoverySearchInput =
  | string
  | URLSearchParams
  | Record<string, string | string[] | undefined>;

function toSearchParams(input: DiscoverySearchInput) {
  if (typeof input === "string") return new URLSearchParams(input);
  if (input instanceof URLSearchParams) return new URLSearchParams(input);

  const params = new URLSearchParams();
  Object.entries(input).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else if (value !== undefined) params.set(key, value);
  });
  return params;
}

function discoveryUrl(params: URLSearchParams) {
  return `/${params.size ? `?${params.toString()}` : ""}#discover`;
}

/**
 * Changes the explicit food choice without throwing away the user's current
 * search area or compatible refinements. A category and selected farm belong
 * to the previous result set, so neither follows a new product choice.
 */
export function buildProductBrowseUrl(product: string, currentSearch: DiscoverySearchInput) {
  const current = parseDiscoveryUrl(toSearchParams(currentSearch));
  const next = serializeDiscoveryUrl({
    ...current,
    category: "",
    product,
    farmId: "",
  });
  return discoveryUrl(next);
}

/**
 * Moves the current search to a named place while retaining compatible food,
 * question and service filters. A named place replaces map bounds and browser
 * geolocation; neither raw coordinates nor a farm selected in the old area may
 * leak into the shareable URL.
 */
export function buildHeroPlaceUrl(placeSlug: string, currentSearch: DiscoverySearchInput) {
  const current = parseDiscoveryUrl(toSearchParams(currentSearch));
  const next = serializeDiscoveryUrl({
    ...current,
    near: placeSlug,
    bbox: null,
    sort: current.q ? "relevance" : "distance",
    browseAll: false,
    farmId: "",
  });
  return discoveryUrl(next);
}
