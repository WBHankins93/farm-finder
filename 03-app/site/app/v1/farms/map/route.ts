import { mapFarms, parseDiscoveryQuery } from "../../../lib/discovery-server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const requestedZoom = Number(url.searchParams.get("zoom"));
  const zoom = Number.isFinite(requestedZoom) ? requestedZoom : 7;
  return Response.json(mapFarms(parseDiscoveryQuery(url.searchParams), zoom), {
    headers: { "Cache-Control": "public, max-age=30, stale-while-revalidate=120" },
  });
}
