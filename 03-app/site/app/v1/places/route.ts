import { bindDiscoveryContext } from "../../lib/discovery-index";
import { searchPlaces } from "../../lib/discovery-server";

export async function GET(request: Request) {
  bindDiscoveryContext(undefined, request.url);
  const url = new URL(request.url);
  const result = await searchPlaces(url.searchParams.get("q") ?? "", Number(url.searchParams.get("limit")));
  return Response.json(result, {
    headers: { "Cache-Control": "public, max-age=60, stale-while-revalidate=300" },
  });
}
