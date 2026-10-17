import { bindDiscoveryContext } from "../../../lib/discovery-index";
import { getFarm } from "../../../lib/discovery-server";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  bindDiscoveryContext(undefined, request.url);
  const { id } = await context.params;
  const farm = await getFarm(id);
  if (!farm) return Response.json({ error: "Farm not found" }, { status: 404 });
  return Response.json({ farm }, {
    headers: { "Cache-Control": "public, max-age=300, stale-while-revalidate=900" },
  });
}
