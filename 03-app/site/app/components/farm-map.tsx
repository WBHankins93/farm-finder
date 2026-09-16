"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { DiscoveryScope, FarmMapFeature, FarmSummary, LatLng, MapBounds } from "../lib/discovery-contract";
import { categoryColors } from "../lib/farms";
import { basemaps, detailedStyleUrl, detailPaint, detailPitch, detailZoom, guideStyle } from "../lib/map-styles";
import { densityPaint, describeMapOptions, farmLabelLayout, farmPointPaint, layerVisibility, pinModes, readMapOptions, spotlightCategories, writeMapOptions, type MapOptions, type PinMode } from "../lib/map-options";
import { Mark, markForCategory } from "../lib/marks";

function toFeatures(items: FarmMapFeature[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: items.map((item) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] },
      properties: item.kind === "farm"
        ? { kind: "farm", id: item.id, name: item.name, category: item.category, geoPrecision: item.geoPrecision }
        : { kind: "cluster", id: item.id, count: item.count, bounds: JSON.stringify(item.bounds), terminal: item.terminal, farmIds: JSON.stringify(item.farmIds ?? []) },
    })),
  };
}

function selectedFeature(farm: FarmSummary | null): FeatureCollection<Point> {
  if (!farm || farm.geoPrecision === "ungeocoded" || (farm.latitude === 0 && farm.longitude === 0)) return { type: "FeatureCollection", features: [] };
  return { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: [farm.longitude, farm.latitude] }, properties: { id: farm.id } }] };
}

function userFeature(origin: LatLng | null): FeatureCollection<Point> {
  if (!origin) return { type: "FeatureCollection", features: [] };
  return { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: [origin.lng, origin.lat] }, properties: {} }] };
}

function summaryServices(farm: FarmSummary) {
  return [farm.farmersMarket && "Market", farm.onFarm && "Farm pickup", farm.csa && "CSA", farm.ships && "Delivery", farm.onlineStore && "Order online"].filter(Boolean) as string[];
}

export type FarmMapProps = {
  features: FarmMapFeature[];
  selectedFarm: FarmSummary | null;
  hoveredFarm: FarmSummary | null;
  userOrigin: LatLng | null;
  scope: DiscoveryScope | null;
  searchAreaAvailable: boolean;
  onSearchArea: () => void;
  onCameraChange: (bounds: MapBounds, zoom: number) => void;
  onSelect: (id: string) => void;
  onSelectCluster: (farmIds: string[]) => void;
  onOpenProfile: (id: string) => void;
};

export default function FarmMap(props: FarmMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const propsRef = useRef(props);
  const suppressMoveRef = useRef(false);
  const lastScopeKeyRef = useRef("");
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState("");
  const [panelOpen, setPanelOpen] = useState(false);
  // Read once, lazily. `farm-map` is a `dynamic(..., { ssr: false })` import,
  // so this only ever runs in the browser and there is no server render for it
  // to disagree with.
  const [options, setOptions] = useState<MapOptions>(readMapOptions);
  const optionsRef = useRef(options);
  const basemap = options.basemap;
  const basemapRef = useRef(basemap);
  const installOverlayRef = useRef<((map: MapLibreMap) => void) | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const panelButtonRef = useRef<HTMLButtonElement>(null);

  function update(patch: Partial<MapOptions>) {
    setOptions((current) => {
      const next = { ...current, ...patch };
      writeMapOptions(next);
      return next;
    });
  }


  useEffect(() => {
    propsRef.current = props;
  }, [props]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const supportsMap = (maplibregl as { supported?: () => boolean }).supported;
    if (typeof supportsMap === "function" && !supportsMap()) {
      const unsupportedNotice = window.setTimeout(() => setMapError("The interactive map is unavailable in this browser."), 0);
      return () => window.clearTimeout(unsupportedNotice);
    }

    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: basemapRef.current === "detailed" ? detailedStyleUrl : guideStyle(),
        center: [-98.5, 38.2],
        zoom: 3.35,
        minZoom: 2.5,
        // The detailed basemap only earns its name at street level: Liberty's
        // building extrusions start at z14 and its POI labels at z15. Stopping
        // at 16 left the last mile — driveways, barn footprints, the entrance
        // you actually turn into — out of reach of the toggle that promises it.
        maxZoom: 18,
        attributionControl: false,
        // Panning stays smooth over a dense national result set: no cross-fade
        // between tile zooms, a larger tile cache so a pan-back is instant, and
        // no duplicate worlds to rasterise at low zoom.
        fadeDuration: 0,
        maxTileCacheSize: 220,
        renderWorldCopies: false,
      });
    } catch {
      queueMicrotask(() => setMapError("The interactive map is unavailable in this browser."));
      return;
    }

    // The compass is the only way back to north-up once the detailed basemap
    // tilts the camera (or a two-finger drag rotates it), so it has to be here.
    // `visualizePitch` also makes the current tilt legible at a glance.
    //
    // Top-right, not bottom-right: the bottom of the map belongs to the farm
    // detail sheet, which on mobile is full-width and would sit straight on top
    // of the zoom buttons. Attribution stays at the bottom, where the sheet
    // clears it — it is a licence requirement and must stay readable.
    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Farm locations may be approximate" }), "bottom-right");

    // Liberty owns these layers, so this re-paints them in place rather than
    // stacking duplicates on top. It runs on every style load because
    // `setStyle` throws the previous style — and these overrides — away.
    function applyDetailPaint(target: MapLibreMap) {
      if (basemapRef.current !== "detailed") return;
      for (const override of detailPaint) {
        if (!target.getLayer(override.layer)) continue;
        // `styledata` fires repeatedly as sources resolve; re-setting an
        // identical paint value would repaint the map each time.
        if (JSON.stringify(target.getPaintProperty(override.layer, override.property)) === JSON.stringify(override.value)) continue;
        target.setPaintProperty(override.layer, override.property, override.value);
      }
    }

    function installFarmOverlay(target: MapLibreMap) {
      applyDetailPaint(target);
      if (target.getSource("farms")) return;
      const current = propsRef.current;
      const current2 = optionsRef.current;
      const visible = layerVisibility(current2);
      target.addSource("farms", { type: "geojson", data: toFeatures(current.features) });
      target.addSource("selected-farm", { type: "geojson", data: selectedFeature(current.selectedFarm) });
      target.addSource("hovered-farm", { type: "geojson", data: selectedFeature(current.hoveredFarm) });
      target.addSource("user-origin", { type: "geojson", data: userFeature(current.userOrigin) });

      // Density sits under everything so it reads as ground the farms stand on,
      // never as something drawn over them. It summarises the same source.
      target.addLayer({ id: "farm-density", type: "heatmap", source: "farms", layout: { visibility: visible["farm-density"] ? "visible" : "none" }, paint: densityPaint(current2) });
      target.addLayer({ id: "server-clusters", type: "circle", source: "farms", filter: ["==", ["get", "kind"], "cluster"], paint: { "circle-color": "rgba(251,252,246,.96)", "circle-radius": ["step", ["get", "count"], 20, 20, 25, 75, 31], "circle-stroke-width": 2, "circle-stroke-color": "#173f2c" } });
      target.addLayer({ id: "server-cluster-count", type: "symbol", source: "farms", filter: ["==", ["get", "kind"], "cluster"], layout: { "text-field": ["get", "count"], "text-size": 12, "text-font": ["Noto Sans Bold"] }, paint: { "text-color": "#173f2c" } });
      target.addLayer({ id: "farm-points", type: "circle", source: "farms", filter: ["==", ["get", "kind"], "farm"], layout: { visibility: visible["farm-points"] ? "visible" : "none" }, paint: farmPointPaint(current2) });
      target.addLayer({ id: "farm-labels", type: "symbol", source: "farms", filter: ["==", ["get", "kind"], "farm"], minzoom: 11, layout: { ...farmLabelLayout(), visibility: visible["farm-labels"] ? "visible" : "none" }, paint: { "text-color": "#3f4a3d", "text-halo-color": "#fdfdf7", "text-halo-width": 1.5 } });
      target.addLayer({ id: "hovered-ring", type: "circle", source: "hovered-farm", paint: { "circle-radius": 12, "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 2, "circle-stroke-color": "#173f2c" } });
      target.addLayer({ id: "selected-ring", type: "circle", source: "selected-farm", paint: { "circle-radius": 14, "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 3, "circle-stroke-color": "#c65e36" } });
      target.addLayer({ id: "user-halo", type: "circle", source: "user-origin", paint: { "circle-radius": 12, "circle-color": "rgba(255,250,240,.5)", "circle-stroke-width": 1, "circle-stroke-color": "#173f2c" } });
      target.addLayer({ id: "user-point", type: "circle", source: "user-origin", paint: { "circle-radius": 5, "circle-color": "#173f2c", "circle-stroke-width": 2, "circle-stroke-color": "#fbfcf6" } });
    }
    installOverlayRef.current = installFarmOverlay;

    map.on("load", () => {
      installFarmOverlay(map);

      map.on("click", "server-clusters", (event) => {
        const properties = event.features?.[0]?.properties;
        if (!properties) return;
        const terminal = properties.terminal === true || properties.terminal === "true";
        if (terminal) {
          const ids = JSON.parse(String(properties.farmIds || "[]")) as string[];
          propsRef.current.onSelectCluster(ids);
          return;
        }
        const bounds = JSON.parse(String(properties.bounds)) as MapBounds;
        map.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]], { padding: 72, maxZoom: 15, duration: 500 });
      });
      map.on("click", "farm-points", (event) => {
        const id = event.features?.[0]?.properties?.id;
        if (id) propsRef.current.onSelect(String(id));
      });
      for (const layer of ["server-clusters", "farm-points"]) {
        map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
      }
      // `setStyle` drops custom sources and layers; re-install after each swap.
      map.on("styledata", () => installFarmOverlay(map));
      map.on("moveend", () => {
        if (suppressMoveRef.current) {
          suppressMoveRef.current = false;
          return;
        }
        const bounds = map.getBounds();
        propsRef.current.onCameraChange([bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()], map.getZoom());
      });
      setMapReady(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    (mapRef.current.getSource("farms") as GeoJSONSource | undefined)?.setData(toFeatures(props.features));
  }, [props.features, mapReady]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    (mapRef.current.getSource("selected-farm") as GeoJSONSource | undefined)?.setData(selectedFeature(props.selectedFarm));
    if (props.selectedFarm && props.selectedFarm.geoPrecision !== "ungeocoded") {
      suppressMoveRef.current = true;
      mapRef.current.easeTo({ center: [props.selectedFarm.longitude, props.selectedFarm.latitude], offset: [0, 42], duration: 420 });
    }
  }, [props.selectedFarm, mapReady]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    (mapRef.current.getSource("hovered-farm") as GeoJSONSource | undefined)?.setData(selectedFeature(props.hoveredFarm));
  }, [props.hoveredFarm, mapReady]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    (mapRef.current.getSource("user-origin") as GeoJSONSource | undefined)?.setData(userFeature(props.userOrigin));
  }, [props.userOrigin, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !props.scope) return;
    const key = JSON.stringify(props.scope);
    if (lastScopeKeyRef.current === key) return;
    lastScopeKeyRef.current = key;
    suppressMoveRef.current = true;
    if (props.scope.mode === "nearby" && props.scope.origin) {
      const zoom = props.scope.radiusMiles === 25 ? 8.8 : props.scope.radiusMiles === 100 ? 6.8 : 7.8;
      map.easeTo({ center: [props.scope.origin.lng, props.scope.origin.lat], zoom, duration: 550 });
    } else if (props.scope.bounds) {
      map.fitBounds([[props.scope.bounds[0], props.scope.bounds[1]], [props.scope.bounds[2], props.scope.bounds[3]]], { padding: 56, maxZoom: 12, duration: 550 });
    }
  }, [props.scope, mapReady]);

  // Everything except the basemap can be applied to the live map: no style
  // reload, no tile refetch, no camera move. Only the paint changes.
  useEffect(() => {
    optionsRef.current = options;
    const map = mapRef.current;
    if (!mapReady || !map || !map.getLayer("farm-points")) return;
    const visible = layerVisibility(options);
    for (const [layer, on] of Object.entries(visible)) {
      if (map.getLayer(layer)) map.setLayoutProperty(layer, "visibility", on ? "visible" : "none");
    }
    for (const [property, value] of Object.entries(farmPointPaint(options))) {
      map.setPaintProperty("farm-points", property, value);
    }
    if (map.getLayer("farm-density")) {
      for (const [property, value] of Object.entries(densityPaint(options))) {
        map.setPaintProperty("farm-density", property, value);
      }
    }
  }, [options, mapReady]);

  // The scale bar is a control, not paint, so it is added and removed rather
  // than toggled.
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    if (!options.scale) return;
    const control = new maplibregl.ScaleControl({ maxWidth: 110, unit: "imperial" });
    map.addControl(control, "bottom-left");
    return () => {
      map.removeControl(control);
    };
  }, [options.scale, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    basemapRef.current = basemap;
    if (!mapReady || !map) return;
    // Both styles read the same vector source, so the swap reuses cached tiles
    // and only re-rasterises. `diff: false` avoids a slow layer-level diff
    // against a style with a completely different layer set.
    map.setStyle(basemap === "detailed" ? detailedStyleUrl : guideStyle(), { diff: false });
    map.once("styledata", () => installOverlayRef.current?.(map));

    // Extrusions at pitch 0 are just tinted footprints, so detailed mode tilts
    // — but only from `detailZoom` up, where there is massing to see and the
    // person is plainly doing last-mile work. Tilting a regional view would
    // pull in a horizon of tiles and win nothing, and a camera that moves on
    // its own while you are scanning pins is worse than flat buildings.
    // Switching back always flattens; the compass undoes it either way, and
    // `easeTo` is instant under reduced motion by MapLibre's own rule.
    const wantsTilt = basemap === "detailed" && options.tilt === "auto" && map.getZoom() >= detailZoom;
    const target = wantsTilt ? detailPitch : 0;
    if (Math.abs(map.getPitch() - target) > 0.5) {
      suppressMoveRef.current = true;
      map.easeTo({ pitch: target, bearing: basemap === "detailed" ? map.getBearing() : 0, duration: 420 });
    }
    // `options.tilt` is read, not depended on: flipping it should not re-run a
    // style swap. The dedicated effect below handles that flip on its own.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basemap, mapReady]);

  // Turning tilt off flattens immediately; turning it back on waits for the
  // next basemap switch rather than tilting a map nobody asked to move.
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || options.tilt !== "flat" || map.getPitch() === 0) return;
    suppressMoveRef.current = true;
    map.easeTo({ pitch: 0, duration: 380 });
  }, [options.tilt, mapReady]);


  // A panel that covers the map has to be dismissible without hunting for the
  // toggle again: Escape returns focus to the button, a click outside just
  // closes it.
  useEffect(() => {
    if (!panelOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setPanelOpen(false);
      panelButtonRef.current?.focus();
    }
    function onPointer(event: MouseEvent) {
      if (panelRef.current?.contains(event.target as Node)) return;
      setPanelOpen(false);
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [panelOpen]);

  function fitVisible() {
    const map = mapRef.current;
    const points = props.features;
    if (!map || points.length === 0) return;
    const bounds = new maplibregl.LngLatBounds();
    points.forEach((point) => bounds.extend([point.longitude, point.latitude]));
    suppressMoveRef.current = true;
    map.fitBounds(bounds, { padding: 64, maxZoom: 11, duration: 500 });
  }

  const selected = props.selectedFarm;
  const activeBasemap = basemaps.find((option) => option.id === basemap) ?? null;
  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-canvas" role="region" aria-label="Interactive map of farm results" />
      {mapError ? <div className="map-fallback" role="status"><span aria-hidden="true">⌁</span><strong>Keep browsing in the farm list.</strong><p>{mapError} Search, filters, and profiles still work.</p></div> : !mapReady ? <div className="map-loading" role="status"><span />Preparing the field map…</div> : null}
      {!mapError ? (
        <div className="map-options" ref={panelRef}>
          <button
            type="button"
            ref={panelButtonRef}
            className={`map-options-toggle ${panelOpen ? "open" : ""}`}
            aria-expanded={panelOpen}
            aria-controls="map-options-panel"
            onClick={() => setPanelOpen((open) => !open)}
          >
            <Mark name="layers" aria-hidden="true" />
            Map options
          </button>
          {panelOpen ? (
            <div className="map-options-panel" id="map-options-panel" role="group" aria-label="Map options">
              <fieldset>
                <legend>Basemap</legend>
                <div className="option-row">
                  {basemaps.map((option) => (
                    <button key={option.id} type="button" className={basemap === option.id ? "active" : ""} aria-pressed={basemap === option.id} aria-describedby={`basemap-hint-${option.id}`} onClick={() => update({ basemap: option.id })}>
                      {option.label}
                    </button>
                  ))}
                </div>
                {/* `title` is a hover tooltip and reaches neither keyboard nor
                    touch, so the hint is shown as text and referenced by id. */}
                <p className="option-hint" id={`basemap-hint-${basemap}`}>{activeBasemap?.hint}</p>
              </fieldset>

              <fieldset>
                <legend>Farms</legend>
                <div className="option-row">
                  {pinModes.map((mode) => (
                    <button key={mode.id} type="button" className={options.pins === mode.id ? "active" : ""} aria-pressed={options.pins === mode.id} aria-describedby={`pin-hint-${options.pins}`} onClick={() => update({ pins: mode.id as PinMode })}>
                      {mode.label}
                    </button>
                  ))}
                </div>
                <p className="option-hint" id={`pin-hint-${options.pins}`}>{pinModes.find((mode) => mode.id === options.pins)?.hint}</p>
              </fieldset>

              <fieldset>
                <legend>Highlight a category</legend>
                <div className="option-row option-wrap">
                  <button type="button" className={options.spotlight === "" ? "active" : ""} aria-pressed={options.spotlight === ""} onClick={() => update({ spotlight: "" })}>All</button>
                  {spotlightCategories.map((category) => (
                    <button key={category} type="button" className={options.spotlight === category ? "active" : ""} aria-pressed={options.spotlight === category} onClick={() => update({ spotlight: category })}>
                      <Mark name={markForCategory(category)} style={{ color: categoryColors[category] }} aria-hidden="true" />
                      {category}
                    </button>
                  ))}
                </div>
                {/* Said out loud because "highlight" and "filter" look the same
                    from the outside, and this one does not change the results. */}
                <p className="option-hint">Dims the other farms. Nothing is removed, and the result count does not change — use <strong>All filters</strong> to narrow the directory itself.</p>
              </fieldset>

              <fieldset>
                <legend>Detail</legend>
                <label className="option-check">
                  <input type="checkbox" checked={options.labels} onChange={(event) => update({ labels: event.target.checked })} />
                  Farm names on the map
                  <span>From zoom 11. Names that collide are dropped; every pin still draws.</span>
                </label>
                <label className="option-check">
                  <input type="checkbox" checked={options.tilt === "auto"} onChange={(event) => update({ tilt: event.target.checked ? "auto" : "flat" })} />
                  Tilt for 3D buildings
                  <span>Full detail only, from zoom {detailZoom} up.</span>
                </label>
                <label className="option-check">
                  <input type="checkbox" checked={options.scale} onChange={(event) => update({ scale: event.target.checked })} />
                  Scale bar
                </label>
              </fieldset>
            </div>
          ) : null}
        </div>
      ) : null}
      {/* Changing an option redraws the map and otherwise says nothing. */}
      {!mapError ? <p className="sr-only" role="status">{activeBasemap ? describeMapOptions(options, activeBasemap.label) : ""}</p> : null}
      {!mapError ? <div className="map-tools" role="group" aria-label="Map tools"><button type="button" onClick={fitVisible}>Fit results</button>{props.searchAreaAvailable ? <button className="search-area-button" type="button" onClick={props.onSearchArea}>Search this area</button> : null}</div> : null}
      {!mapError ? (
        // The legend was four static swatches. Since the panel already knows how
        // to highlight a category, the swatches may as well be the shortcut to
        // it — and the fourth opens the panel, where the other six live.
        <div className="map-key" role="group" aria-label="Map legend and category highlight">
          {["Produce", "Meat", "Mixed"].map((category) => (
            <button
              key={category}
              type="button"
              className={options.spotlight === category ? "active" : ""}
              aria-pressed={options.spotlight === category}
              onClick={() => update({ spotlight: options.spotlight === category ? "" : category })}
            >
              <i className="key-dot" style={{ background: categoryColors[category] }} />
              {category}
            </button>
          ))}
          <button type="button" className="key-more" onClick={() => { setPanelOpen(true); panelButtonRef.current?.focus(); }}>
            <i className="key-dot more" />
            More…
          </button>
        </div>
      ) : null}
      {!mapError && selected ? (
        <aside className="map-detail map-detail-sheet" role="region" aria-live="polite" aria-label={`${selected.name} details`}>
          <button className="detail-close" type="button" onClick={() => props.onSelect("")} aria-label="Close farm details">×</button>
          <div className="detail-kicker"><Mark name={markForCategory(selected.category)} style={{ color: categoryColors[selected.category] || "#596b60" }} />{selected.category}</div>
          <h3>{selected.name}</h3><p className="detail-place">{selected.city}, {selected.state} · {selected.parish || "Area not listed"}</p><p className="detail-products">{selected.productsText}</p>
          <div className="detail-tags">{summaryServices(selected).map((label) => <span key={label}>{label}</span>)}</div>
          <div className="detail-actions"><button type="button" onClick={() => props.onOpenProfile(selected.id)}>Full profile →</button>{selected.website ? <a href={selected.website} target="_blank" rel="noreferrer">Website ↗</a> : null}</div>
          <p className="precision-note">{selected.geoPrecision === "point" ? "Public point" : "Approximate location"} · Confirm before visiting</p>
        </aside>
      ) : null}
    </div>
  );
}
