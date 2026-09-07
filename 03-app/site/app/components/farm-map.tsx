"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type ExpressionSpecification, type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { DiscoveryScope, FarmMapFeature, FarmSummary, LatLng, MapBounds } from "../lib/discovery-contract";
import { categoryColors } from "../lib/farms";
import { Mark, markForCategory } from "../lib/marks";

const categoryExpression: ExpressionSpecification = [
  "match", ["get", "category"],
  "Produce", categoryColors.Produce,
  "Mixed", categoryColors.Mixed,
  "Meat", categoryColors.Meat,
  "Honey/Specialty", categoryColors["Honey/Specialty"],
  "Dairy", categoryColors.Dairy,
  "Seafood", categoryColors.Seafood,
  "Rice", categoryColors.Rice,
  "Urban Farm", categoryColors["Urban Farm"],
  "Value-Added", categoryColors["Value-Added"],
  "#596b60",
];

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
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [-98.5, 38.2],
        zoom: 3.35,
        minZoom: 2.5,
        maxZoom: 16,
        attributionControl: false,
      });
    } catch {
      queueMicrotask(() => setMapError("The interactive map is unavailable in this browser."));
      return;
    }

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Farm locations may be approximate" }), "bottom-right");

    map.on("load", () => {
      map.addSource("farms", { type: "geojson", data: toFeatures(propsRef.current.features) });
      map.addSource("selected-farm", { type: "geojson", data: selectedFeature(propsRef.current.selectedFarm) });
      map.addSource("hovered-farm", { type: "geojson", data: selectedFeature(propsRef.current.hoveredFarm) });
      map.addSource("user-origin", { type: "geojson", data: userFeature(propsRef.current.userOrigin) });

      map.addLayer({ id: "server-clusters", type: "circle", source: "farms", filter: ["==", ["get", "kind"], "cluster"], paint: { "circle-color": "rgba(251,252,246,.96)", "circle-radius": ["step", ["get", "count"], 20, 20, 25, 75, 31], "circle-stroke-width": 2, "circle-stroke-color": "#173f2c" } });
      map.addLayer({ id: "server-cluster-count", type: "symbol", source: "farms", filter: ["==", ["get", "kind"], "cluster"], layout: { "text-field": ["get", "count"], "text-size": 12 }, paint: { "text-color": "#173f2c" } });
      map.addLayer({ id: "farm-points", type: "circle", source: "farms", filter: ["==", ["get", "kind"], "farm"], paint: { "circle-color": categoryExpression, "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 6, 10, 10], "circle-stroke-width": 2, "circle-stroke-color": "#fbfcf6", "circle-opacity": 0.96 } });
      map.addLayer({ id: "hovered-ring", type: "circle", source: "hovered-farm", paint: { "circle-radius": 12, "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 2, "circle-stroke-color": "#173f2c" } });
      map.addLayer({ id: "selected-ring", type: "circle", source: "selected-farm", paint: { "circle-radius": 14, "circle-color": "rgba(0,0,0,0)", "circle-stroke-width": 3, "circle-stroke-color": "#c65e36" } });
      map.addLayer({ id: "user-halo", type: "circle", source: "user-origin", paint: { "circle-radius": 12, "circle-color": "rgba(255,250,240,.5)", "circle-stroke-width": 1, "circle-stroke-color": "#173f2c" } });
      map.addLayer({ id: "user-point", type: "circle", source: "user-origin", paint: { "circle-radius": 5, "circle-color": "#173f2c", "circle-stroke-width": 2, "circle-stroke-color": "#fbfcf6" } });

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
  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-canvas" role="region" aria-label="Interactive map of farm results" />
      {mapError ? <div className="map-fallback" role="status"><span aria-hidden="true">⌁</span><strong>Keep browsing in the farm list.</strong><p>{mapError} Search, filters, and profiles still work.</p></div> : !mapReady ? <div className="map-loading" role="status"><span />Preparing the field map…</div> : null}
      {!mapError ? <div className="map-tools" role="group" aria-label="Map tools"><button type="button" onClick={fitVisible}>Fit results</button>{props.searchAreaAvailable ? <button className="search-area-button" type="button" onClick={props.onSearchArea}>Search this area</button> : null}</div> : null}
      {!mapError ? (
        <details className="map-key" aria-label="Map legend">
          <summary>Legend</summary>
          <div>{Object.entries(categoryColors).map(([label, color]) => <span key={label}><i className="key-dot" style={{ background: color }} /> {label}</span>)}</div>
        </details>
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
