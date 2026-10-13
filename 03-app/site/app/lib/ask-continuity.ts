export type AskLocationContext = {
  near: string;
  radiusMiles: 25 | 50 | 100 | null;
};

const supportedRadii = new Set([25, 50, 100]);

export function parseAskLocationContext(search: string): AskLocationContext {
  const params = new URLSearchParams(search);
  const near = params.get("near")?.trim() ?? "";
  if (!near) return { near: "", radiusMiles: null };

  const requestedRadius = Number(params.get("radiusMiles"));
  const radiusMiles = supportedRadii.has(requestedRadius)
    ? requestedRadius as 25 | 50 | 100
    : 50;

  return { near, radiusMiles };
}

function addLocationContext(params: URLSearchParams, context: AskLocationContext) {
  if (!context.near || context.radiusMiles === null) return;
  params.set("near", context.near);
  params.set("radiusMiles", String(context.radiusMiles));
}

export function buildAskRequestUrl(query: string, context: AskLocationContext) {
  const params = new URLSearchParams({ q: query.trim(), sort: "relevance", limit: "6" });
  addLocationContext(params, context);
  return `/v1/farms?${params.toString()}`;
}

export function buildAskExploreUrl(query: string, context: AskLocationContext, farmId = "") {
  const params = new URLSearchParams({ q: query.trim(), sort: "relevance" });
  addLocationContext(params, context);
  if (farmId) params.set("farm", farmId);
  return `/?${params.toString()}#discover`;
}

export function formatAskFarmLocation(city: string, state: string) {
  const location = [city.trim(), state.trim()].filter(Boolean).join(", ");
  return location || "Location not listed";
}
