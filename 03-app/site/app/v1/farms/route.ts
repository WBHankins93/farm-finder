import { bindDiscoveryContext } from "../../lib/discovery-index";
import { parseDiscoveryQuery, searchFarms } from "../../lib/discovery-server";

export async function GET(request: Request) {
  bindDiscoveryContext(undefined, request.url);
  const url = new URL(request.url);
  return Response.json(await searchFarms(parseDiscoveryQuery(url.searchParams)), {
    headers: { "Cache-Control": "public, max-age=60, stale-while-revalidate=300" },
  });
}
