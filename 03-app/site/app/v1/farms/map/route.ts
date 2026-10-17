import { bindDiscoveryContext } from "../../../lib/discovery-index";
import { mapFarms, parseDiscoveryQuery } from "../../../lib/discovery-server";

export async function GET(request: Request) {
  bindDiscoveryContext(undefined, request.url);
  const url = new URL(request.url);
  const requestedZoom = Number(url.searchParams.get("zoom"));
  const zoom = Number.isFinite(requestedZoom) ? requestedZoom : 7;
  return Response.json(await mapFarms(parseDiscoveryQuery(url.searchParams), zoom), {
    headers: { "Cache-Control": "public, max-age=30, stale-while-revalidate=120" },
  });
}
