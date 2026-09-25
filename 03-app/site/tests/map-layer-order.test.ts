import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

/**
 * MapLibre draws layers in the order they are added, and getting it wrong does
 * not throw — it just paints one thing over another. Pins added after the
 * cluster layers covered the cluster counts on dense views, which only showed
 * up in a rendered screenshot. This pins the order down at the source.
 */
test("the farm overlay stacks density, pins, clusters, then highlights", async () => {
  const source = await readFile(new URL("../app/components/farm-map.tsx", import.meta.url), "utf8");
  const overlay = source.slice(source.indexOf("function installFarmOverlay"), source.indexOf("installOverlayRef.current = installFarmOverlay"));
  const order = [...overlay.matchAll(/addLayer\(\{ id: "([^"]+)"/g)].map((match) => match[1]);

  const at = (id: string) => {
    const index = order.indexOf(id);
    assert.notEqual(index, -1, `${id} is missing from the overlay`);
    return index;
  };

  assert.ok(at("farm-density") < at("farm-points"), "density is ground the pins stand on");
  assert.ok(at("farm-points") < at("server-clusters"), "pins must not paint over cluster discs");
  assert.ok(at("farm-labels") < at("server-cluster-count"), "farm names must not paint over cluster counts");
  assert.ok(at("server-cluster-count") < at("selected-ring"), "the selected farm's ring stays on top of everything");
});
