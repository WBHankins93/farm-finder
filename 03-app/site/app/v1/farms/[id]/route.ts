import { getFarm } from "../../../lib/discovery-server";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const farm = getFarm(id);
  if (!farm) return Response.json({ error: "Farm not found" }, { status: 404 });
  return Response.json({ farm }, {
    headers: { "Cache-Control": "public, max-age=300, stale-while-revalidate=900" },
  });
}
