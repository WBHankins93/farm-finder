/**
 * Capture the explorer in a real WebGL context.
 *
 * Claude Code's built-in browser pane, and most CI sandboxes, have no WebGL,
 * so MapLibre never draws there and the map falls back to its list-only path.
 * That fallback is correct, but it means the map itself was repeatedly shipped
 * without anyone seeing it. This drives headless Chrome with SwiftShader — a
 * software WebGL implementation — over the DevTools protocol, so the basemaps,
 * pins and panels actually render.
 *
 *   npm run dev                         # the explorer on :3000
 *   node dev/screenshots.mjs [outDir]   # writes PNGs, prints what it measured
 *
 * No npm dependencies: Node 22's global WebSocket and fetch are enough.
 * Frame rates from software rendering are meaningless; layout and pixels are
 * not.
 */
import { spawn } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const BASE = process.env.FARMFINDER_URL ?? "http://localhost:3000";
const CHROME = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = path.resolve(process.argv[2] ?? "dev/screenshots");
const PORT = 9300 + Math.floor(Math.random() * 400);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function launch() {
  const profile = await mkdtemp(path.join(tmpdir(), "farmfinder-chrome-"));
  const chrome = spawn(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ], { stdio: "ignore" });

  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const version = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
      if (version.webSocketDebuggerUrl) return { chrome, profile };
    } catch { /* not up yet */ }
    await sleep(250);
  }
  chrome.kill();
  throw new Error(`Chrome did not expose DevTools on :${PORT}`);
}

/** A minimal CDP session over one page target. */
async function openPage() {
  // Drive Chrome's own foreground tab. A tab opened with /json/new is a
  // background tab: it reports visibilityState "hidden" and pauses
  // requestAnimationFrame, and MapLibre waits for a frame before it even
  // requests its style — so the map sits on "Preparing" forever, silently.
  const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const target = targets.find((item) => item.type === "page")
    ?? await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" })).json();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });

  let nextId = 0;
  const pending = new Map();
  const listeners = new Map();
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(`${message.error.message} (${message.error.code})`));
      else resolve(message.result);
    } else if (message.method) {
      for (const listener of listeners.get(message.method) ?? []) listener(message.params);
    }
  };

  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const once = (method) => new Promise((resolve) => {
    const handlers = listeners.get(method) ?? [];
    const handler = (params) => { listeners.set(method, handlers.filter((item) => item !== handler)); resolve(params); };
    handlers.push(handler);
    listeners.set(method, handlers);
  });

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  // MapLibre fetches tiles and parses styles inside web workers, which a page
  // session cannot see. Attach to them so a stalled map explains itself.
  listeners.set("Target.attachedToTarget", [({ sessionId, targetInfo }) => {
    workers.push(`${targetInfo.type}:${targetInfo.url.slice(0, 80)}`);
    // Instrument before letting it run, so a startup error is not missed.
    Promise.allSettled([send("Runtime.enable", {}, sessionId), send("Network.enable", {}, sessionId)])
      .then(() => send("Runtime.runIfWaitingForDebugger", {}, sessionId))
      .catch(() => {});
  }]);
  await send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: true, flatten: true });
  // Belt and braces: keep the page foregrounded and focused throughout.
  await send("Page.bringToFront");
  await send("Emulation.setFocusEmulationEnabled", { enabled: true });

  // Kept for diagnostics: a map that never loads is almost always a failed
  // tile/style request or a thrown error, and both are invisible otherwise.
  const problems = [];
  const workers = [];
  const requests = new Map();
  const listen = (method, handler) => listeners.set(method, [...(listeners.get(method) ?? []), handler]);
  const tileTraffic = { sent: 0, finished: 0 };
  listen("Network.requestWillBeSent", ({ requestId, request }) => {
    requests.set(requestId, request.url);
    if (request.url.includes("openfreemap")) tileTraffic.sent += 1;
  });
  listen("Network.loadingFinished", ({ requestId }) => {
    if ((requests.get(requestId) ?? "").includes("openfreemap")) tileTraffic.finished += 1;
  });
  listen("Network.loadingFailed", ({ requestId, errorText, canceled }) => {
    if (!canceled) problems.push(`request failed: ${errorText} ${requests.get(requestId) ?? requestId}`);
  });
  listen("Network.responseReceived", ({ response }) => {
    if (response.status >= 400) problems.push(`HTTP ${response.status} ${response.url}`);
  });
  listen("Runtime.exceptionThrown", ({ exceptionDetails }) =>
    problems.push(`exception: ${exceptionDetails.exception?.description?.split("\n")[0] ?? exceptionDetails.text}`));
  listen("Runtime.consoleAPICalled", ({ type, args }) => {
    if (type === "error" || type === "warning") problems.push(`console.${type}: ${args.map((arg) => arg.value ?? arg.description ?? "").join(" ").slice(0, 240)}`);
  });

  const page = {
    send,
    async viewport(width, height, mobile = false) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
      await send("Emulation.setTouchEmulationEnabled", { enabled: mobile });
    },
    async goto(url) {
      const loaded = once("Page.loadEventFired");
      await send("Page.navigate", { url });
      await loaded;
    },
    async eval(expression) {
      const { result, exceptionDetails } = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
      return result.value;
    },
    /** Poll a page expression until it is truthy. */
    async waitFor(expression, timeout = 30000) {
      const started = Date.now();
      while (Date.now() - started < timeout) {
        if (await page.eval(`Boolean(${expression})`)) return;
        await sleep(200);
      }
      throw new Error(`timed out waiting for: ${expression}`);
    },
    /**
     * Wait until React has hydrated an element. Typing into server-rendered
     * markup before that changes the DOM but never reaches component state.
     */
    async hydrated(selector, timeout = 30000) {
      await page.waitFor(`(() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        return el && Object.keys(el).some((key) => key.startsWith("__reactProps"));
      })()`, timeout);
    },
    async type(selector, text) {
      await page.eval(`document.querySelector(${JSON.stringify(selector)}).focus()`);
      await send("Input.insertText", { text });
    },
    async key(key, code = key, keyCode = 0) {
      const base = { key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode };
      await send("Input.dispatchKeyEvent", { type: "rawKeyDown", ...base });
      if (key === "Enter") await send("Input.dispatchKeyEvent", { type: "char", text: "\r", ...base });
      await send("Input.dispatchKeyEvent", { type: "keyUp", ...base });
    },
    /** Wait until every MapLibre instance on the page has drawn its tiles. */
    async mapIdle(timeout = 45000) {
      try {
        await page.waitFor(`document.querySelector(".map-canvas canvas")`, timeout);
        await page.waitFor(`(() => {
          const canvas = document.querySelector(".map-canvas canvas");
          return canvas && canvas.width > 0 && !document.querySelector(".map-loading");
        })()`, timeout);
      } catch (error) {
        // Say *why* the map never settled instead of just that it did not.
        const state = await page.eval(`({
          placeholder: document.querySelector(".map-placeholder")?.innerText ?? null,
          loading: document.querySelector(".map-loading")?.innerText ?? null,
          fallback: document.querySelector(".map-fallback")?.innerText ?? null,
          canvases: [...document.querySelectorAll("canvas")].map((c) => c.width + "x" + c.height),
          view: new URLSearchParams(location.search).get("view"),
        })`);
        // Missing fonts and product images are real but never stop a map; list
        // everything else first so the actual cause is not scrolled away.
        const noise = /\.woff2|\/images\/products\/|favicon/;
        const unique = [...new Set(problems)];
        const recent = [...unique.filter((line) => !noise.test(line)), ...unique.filter((line) => noise.test(line)).slice(0, 2)]
          .slice(-20).join("\n  ");
        const frames = await page.eval(`(async () => ({
          visibility: document.visibilityState,
          hasFocus: document.hasFocus(),
          raf: await Promise.race([new Promise((r) => requestAnimationFrame(() => r("fires"))), new Promise((r) => setTimeout(() => r("PAUSED"), 1500))]),
        }))()`);
        const gl = await page.eval(`(() => { const c = document.querySelector(".map-canvas canvas"); const g = c && (c.getContext("webgl2") || c.getContext("webgl")); return g ? { version: g.getParameter(g.VERSION), lost: g.isContextLost() } : null; })()`);
        throw new Error(`${error.message}\nmap state: ${JSON.stringify(state)}\nframes: ${JSON.stringify(frames)}\nmap GL: ${JSON.stringify(gl)}\ntile traffic: ${JSON.stringify(tileTraffic)}\nworkers attached: ${JSON.stringify(workers)}\nrecent problems:\n  ${recent || "(none)"}`);
      }
      await sleep(2500);
    },
    async shot(name, clip) {
      const params = { format: "png", captureBeyondViewport: false };
      if (clip) params.clip = { ...clip, scale: 1 };
      const { data } = await send("Page.captureScreenshot", params);
      const file = path.join(OUT, `${name}.png`);
      await writeFile(file, Buffer.from(data, "base64"));
      console.log(`  ✓ ${path.relative(process.cwd(), file)}`);
      return file;
    },
    close: () => socket.close(),
  };
  return page;
}

/** Scroll an element to the top of the viewport and wait for it to settle. */
const scrollTo = (page, selector, offset = 0) =>
  page.eval(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - ${offset}, behavior: "instant" });
    return window.scrollY;
  })()`);

/** Click the first visible button whose text matches. */
const clickButton = (page, pattern) =>
  page.eval(`(() => {
    const button = [...document.querySelectorAll("button")]
      .find((b) => ${pattern}.test(b.innerText.trim()) && b.offsetParent !== null);
    if (!button) return false;
    button.click();
    return true;
  })()`);

/**
 * Zoom the map in by roughly `steps` levels with wheel events at its centre.
 * MapLibre keeps no global handle to its instance, and a double-click risks
 * landing on a pin, so this is how a person would do it.
 */
async function zoomMap(page, steps) {
  const box = await page.eval(`(() => { const r = document.querySelector(".map-canvas").getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  for (let step = 0; step < steps; step += 1) {
    await page.send("Input.dispatchMouseEvent", { type: "mouseWheel", x: box.x, y: box.y, deltaX: 0, deltaY: -480 });
    await sleep(650);
  }
  await sleep(1500);
}

async function run() {
  await mkdir(OUT, { recursive: true });
  const { chrome, profile } = await launch();
  const page = await openPage();
  const findings = {};

  try {
    const webgl = await page.eval(`(() => { const c = document.createElement("canvas"); const gl = c.getContext("webgl2"); return gl ? gl.getParameter(gl.VERSION) : null; })()`);
    if (!webgl) throw new Error("no WebGL even under SwiftShader — map screenshots would be meaningless");
    findings.webgl = webgl;

    // ---- Desktop 1440x900 -------------------------------------------------
    console.log("desktop 1440x900");
    await page.viewport(1440, 900);
    await page.goto(`${BASE}/`);
    await page.hydrated("#hero-near");
    await page.shot("01-desktop-hero");

    // Type-ahead: a spelling the old lookup returned nothing for.
    await page.type("#hero-near", "madison wi");
    await page.waitFor(`!document.querySelector(".hero-suggestions").hidden`);
    findings.typeaheadMadisonWi = await page.eval(`[...document.querySelectorAll(".hero-suggestions li")].map((li) => li.innerText.replace(/\\n+/g, " · "))`);
    await page.shot("02-desktop-hero-typeahead", { x: 0, y: 0, width: 1440, height: 900 });

    // An ambiguous city asks rather than guessing.
    await page.eval(`(() => { const i = document.querySelector("#hero-near"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, ""); i.dispatchEvent(new Event("input", { bubbles: true })); })()`);
    await page.type("#hero-near", "springfield");
    await sleep(400);
    await page.key("Enter", "Enter", 13);
    await page.waitFor(`document.querySelector(".hero-status-choose")`);
    findings.springfieldAsks = await page.eval(`document.querySelector(".hero-status").innerText`);
    await page.shot("03-desktop-hero-ambiguous");

    // A typo gets "did you mean", not silence.
    await page.eval(`(() => { const i = document.querySelector("#hero-near"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, ""); i.dispatchEvent(new Event("input", { bubbles: true })); })()`);
    await page.type("#hero-near", "madisonn wi");
    await sleep(400);
    await page.key("Escape", "Escape", 27);
    await page.key("Enter", "Enter", 13);
    await page.waitFor(`document.querySelector(".hero-status-missing")`);
    findings.typoMessage = await page.eval(`document.querySelector(".hero-status").innerText.replace(/\\n+/g, " ")`);
    await page.shot("04-desktop-hero-did-you-mean");

    // Enter on a good city scrolls to the explorer and loads results.
    await page.eval(`(() => { const i = document.querySelector("#hero-near"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, ""); i.dispatchEvent(new Event("input", { bubbles: true })); })()`);
    await page.type("#hero-near", "madison wisconsin");
    await sleep(400);
    await page.key("Escape", "Escape", 27);
    const before = await page.eval(`window.scrollY`);
    await page.key("Enter", "Enter", 13);
    await page.waitFor(`/farms within/.test(document.body.innerText)`, 30000);
    await sleep(1200);
    findings.enterNavigation = await page.eval(`({
      scrollBefore: ${before},
      scrollAfter: Math.round(window.scrollY),
      discoverTop: Math.round(document.getElementById("discover").getBoundingClientRect().top),
      url: location.pathname + location.search + location.hash,
      focused: document.activeElement?.id || document.activeElement?.tagName,
      count: document.body.innerText.match(/[\\d,]+ farms within[^\\n]*/)?.[0],
    })`);

    // The explorer, list and map, on the Field guide basemap.
    await page.goto(`${BASE}/?near=madison-wi&radiusMiles=50&sort=distance&view=map#discover`);
    await page.mapIdle();
    await scrollTo(page, "#discover");
    await page.shot("05-desktop-explorer-field-guide");
    findings.fieldGuide = await page.eval(`({
      canvas: (() => { const c = document.querySelector(".map-canvas canvas"); return c.clientWidth + "x" + c.clientHeight; })(),
      mapStatus: [...document.querySelectorAll('.map-wrap [role="status"], .map-panel [role="status"]')].map((el) => el.innerText.trim()).filter(Boolean).join(" | "),
      count: document.body.innerText.match(/[\\d,]+ farms within[^\\n]*/)?.[0],
    })`);

    // Street level on the Field guide, then the same camera on Full detail —
    // the only fair comparison, since Full detail's 3D massing starts at z14.
    await zoomMap(page, 8);
    await page.mapIdle();
    await page.shot("06-desktop-field-guide-street");

    const opened = await clickButton(page, /^Map options/);
    findings.mapOptionsPanel = opened;
    if (opened) {
      await page.waitFor(`document.querySelector(".map-options-panel")`);
      await sleep(400);
      await page.shot("07-desktop-map-options-panel");
      findings.fullDetailButton = await clickButton(page, /^Full detail/);
      await sleep(4500);
      await page.mapIdle();
      await clickButton(page, /^Map options/);
      await sleep(1500);
      await page.shot("08-desktop-full-detail-street");
      findings.fullDetailStatus = await page.eval(`[...document.querySelectorAll('[role="status"]')].map((el) => el.innerText.trim()).filter(Boolean).join(" | ")`);
    }

    // ---- Mobile 390x844 ---------------------------------------------------
    console.log("mobile 390x844");
    await page.viewport(390, 844, true);
    await page.eval(`localStorage.clear()`);
    await page.goto(`${BASE}/`);
    await page.hydrated("#hero-near");
    await page.type("#hero-near", "new orl");
    await page.waitFor(`!document.querySelector(".hero-suggestions").hidden`);
    await page.shot("09-mobile-hero-typeahead");
    findings.mobileTapTargets = await page.eval(`[...document.querySelectorAll(".hero-suggestions li, .hero-field > button")].map((el) => Math.round(el.getBoundingClientRect().height))`);

    await page.goto(`${BASE}/?near=madison-wi&radiusMiles=50&sort=distance#discover`);
    await page.waitFor(`/farms within/.test(document.body.innerText)`, 30000);
    await scrollTo(page, "#discover");
    await sleep(800);
    await page.shot("10-mobile-explorer-list");

    await page.goto(`${BASE}/?near=madison-wi&radiusMiles=50&sort=distance&view=map#discover`);
    await page.mapIdle();
    await scrollTo(page, ".map-panel", 8);
    await page.shot("11-mobile-explorer-map");
  } finally {
    page.close();
    // Let Chrome finish writing its profile before removing it; otherwise the
    // cleanup error replaces whatever actually went wrong above.
    const exited = new Promise((resolve) => chrome.once("exit", resolve));
    chrome.kill();
    await Promise.race([exited, sleep(5000)]);
    await rm(profile, { recursive: true, force: true }).catch(() => {});
  }

  console.log("\nmeasured:");
  console.log(JSON.stringify(findings, null, 2));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
