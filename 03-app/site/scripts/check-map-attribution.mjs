/** Browser regression for GHSA-jrc7-96c5-q579. Run with CHROME_PATH if needed. */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const dir = mkdtempSync(join(tmpdir(), "farmfinder-attribution-"));
try {
  const fixture = join(dir, "attribution.html");
  const library = pathToFileURL(resolve("node_modules/maplibre-gl/dist/maplibre-gl.mjs")).href;
  // Consecutive unsafe attributes reproduce the mutation-during-iteration bug.
  // Values are inert: this asserts removal without executing an exploit.
  writeFileSync(fixture, `<!doctype html><meta charset="utf-8"><body><script type="module">
    import * as maplibregl from "${library}";
    const payload = '<a onclick="void 0" onmouseover="void 0" href="javascript:void 0">unsafe</a><a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
    const map = {
      style: {tileManagers: {remote: {used: true, getSource: () => ({attribution: payload})}}},
      _getUIString: () => 'Attribution',
      getCanvasContainer: () => ({offsetWidth: 1024}), on() {}, off() {}
    };
    const control = new maplibregl.AttributionControl({compact: false});
    const element = control.onAdd(map);
    const unsafe = element.querySelector('[onclick], [onmouseover], [href^="javascript:"]');
    const credit = element.querySelector('a[href="https://www.openstreetmap.org/copyright"]');
    document.body.dataset.result = !unsafe && credit ? 'pass' : 'fail';
    document.body.append(element);
  </script>`);
  const html = execFileSync(chrome, ["--headless=new", "--no-first-run", "--no-default-browser-check", "--allow-file-access-from-files", `--user-data-dir=${join(dir, "profile")}`, "--dump-dom", pathToFileURL(fixture).href], {encoding: "utf8", timeout: 30000, stdio: ["ignore", "pipe", "ignore"]});
  assert.match(html, /data-result="pass"/, "source attribution must remove all unsafe attributes while retaining credit links");
  console.log("MapLibre browser attribution regression passed (unsafe adjacent attributes removed; credit link retained).");
} finally {
  rmSync(dir, {recursive: true, force: true});
}
