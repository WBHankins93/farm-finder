"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type ExpressionSpecification, type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import { categoryColors, serviceLabels, type Farm } from "../lib/farms";

const categoryExpression: ExpressionSpecification = [
  "match",
  ["get", "category"],
  "Produce",
  categoryColors.Produce,
  "Mixed",
  categoryColors.Mixed,
  "Meat",
  categoryColors.Meat,
  "Honey/Specialty",
  categoryColors["Honey/Specialty"],
  "Dairy",
  categoryColors.Dairy,
  "Seafood",
  categoryColors.Seafood,
  "Rice",
  categoryColors.Rice,
  "Urban Farm",
  categoryColors["Urban Farm"],
  "Value-Added",
  categoryColors["Value-Added"],
  "#596b60",
];

function toFeatures(items: Farm[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: items.map((farm) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [farm.longitude, farm.latitude] },
      properties: { id: farm.id, name: farm.name, category: farm.category },
    })),
  };
}

export type FarmMapProps = {
  visibleFarms: Farm[];
  selectedFarm: Farm | null;
  onSelect: (id: string | null) => void;
  onOpenProfile: (id: string) => void;
};

export default function FarmMap({
  visibleFarms,
  selectedFarm,
  onSelect,
  onOpenProfile,
}: FarmMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const initialVisibleFarmsRef = useRef(visibleFarms);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState("");
  const [locationMessage, setLocationMessage] = useState("");

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // `maplibregl.supported()` was removed in newer MapLibre versions; guard the
    // call so its absence doesn't throw. WebGL failures still surface via the
    // try/catch around map construction below.
    const supportsMap = (maplibregl as { supported?: () => boolean }).supported;
    if (typeof supportsMap === "function" && !supportsMap()) {
      // WebGL capability is the external browser state synchronized by this effect.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMapError("The interactive map is unavailable in this browser.");
      return;
    }

    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [-91.3, 31.45],
        zoom: 5.35,
        minZoom: 4,
        maxZoom: 16,
        attributionControl: false,
      });
    } catch {
      // MapLibre initialization is the external synchronization attempted by this effect.
      setMapError("The interactive map is unavailable in this browser.");
      return;
    }

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(
      new maplibregl.AttributionControl({ compact: true, customAttribution: "Farm locations are approximate" }),
      "bottom-right",
    );

    map.on("load", () => {
      map.addSource("farms", {
        type: "geojson",
        data: toFeatures(initialVisibleFarmsRef.current),
        cluster: true,
        clusterMaxZoom: 10,
        clusterRadius: 46,
      });
      map.addSource("selected-farm", { type: "geojson", data: toFeatures([]) });

      map.addLayer({
        id: "clusters-halo",
        type: "circle",
        source: "farms",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "rgba(251, 252, 246, .88)",
          "circle-radius": ["step", ["get", "point_count"], 22, 20, 28, 60, 34],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#173f2c",
        },
      });
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "farms",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 12,
        },
        paint: { "text-color": "#173f2c" },
      });
      map.addLayer({
        id: "farm-points",
        type: "circle",
        source: "farms",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": categoryExpression,
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 5.5, 10, 8],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fbfcf6",
          "circle-opacity": 0.96,
        },
      });
      map.addLayer({
        id: "selected-ring",
        type: "circle",
        source: "selected-farm",
        paint: {
          "circle-radius": 14,
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-width": 3,
          "circle-stroke-color": "#c65e36",
        },
      });

      map.on("click", "clusters-halo", async (event) => {
        const feature = map.queryRenderedFeatures(event.point, { layers: ["clusters-halo"] })[0];
        const clusterId = Number(feature?.properties?.cluster_id);
        const source = map.getSource("farms") as GeoJSONSource;
        if (!feature || Number.isNaN(clusterId)) return;
        const zoom = await source.getClusterExpansionZoom(clusterId);
        const coordinates = (feature.geometry as Point).coordinates as [number, number];
        map.easeTo({ center: coordinates, zoom, duration: 650 });
      });

      map.on("click", "farm-points", (event) => {
        const id = event.features?.[0]?.properties?.id;
        if (id) onSelect(String(id));
      });

      for (const layer of ["clusters-halo", "farm-points"]) {
        map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
      }

      setMapReady(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onSelect]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const source = mapRef.current.getSource("farms") as GeoJSONSource | undefined;
    source?.setData(toFeatures(visibleFarms));
  }, [visibleFarms, mapReady]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const source = mapRef.current.getSource("selected-farm") as GeoJSONSource | undefined;
    source?.setData(toFeatures(selectedFarm ? [selectedFarm] : []));
    if (selectedFarm) {
      mapRef.current.flyTo({
        center: [selectedFarm.longitude, selectedFarm.latitude],
        zoom: Math.max(mapRef.current.getZoom(), 9),
        offset: [0, 60],
        duration: 800,
      });
    }
  }, [selectedFarm, mapReady]);

  function fitVisible() {
    const map = mapRef.current;
    if (!map || visibleFarms.length === 0) return;
    const bounds = new maplibregl.LngLatBounds();
    visibleFarms.forEach((farm) => bounds.extend([farm.longitude, farm.latitude]));
    map.fitBounds(bounds, { padding: 58, maxZoom: 10, duration: 700 });
  }

  function useLocation() {
    if (!navigator.geolocation) {
      setLocationMessage("Location is not available in this browser.");
      return;
    }
    setLocationMessage("Finding you…");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        mapRef.current?.flyTo({ center: [coords.longitude, coords.latitude], zoom: 9, duration: 800 });
        setLocationMessage("Map centered near you.");
      },
      () => setLocationMessage("We couldn’t access your location."),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-canvas" aria-label="Interactive map of farms" />
      {mapError ? (
        <div className="map-fallback" role="status">
          <span aria-hidden="true">⌁</span>
          <strong>Keep browsing in the farm list.</strong>
          <p>{mapError} Search, filters, and full profiles still work.</p>
        </div>
      ) : !mapReady ? (
        <div className="map-loading" role="status"><span />Preparing the field map…</div>
      ) : null}
      {!mapError && <div className="map-tools" aria-label="Map tools">
          <button type="button" onClick={fitVisible}>Fit results</button>
          <button type="button" onClick={useLocation}>Use my location</button>
        </div>}
      {locationMessage && <div className="location-toast" role="status">{locationMessage}</div>}
      {!mapError && <div className="map-key" aria-label="Map legend">
        <span><i className="key-dot produce" /> Produce</span>
        <span><i className="key-dot meat" /> Meat</span>
        <span><i className="key-dot mixed" /> Mixed</span>
        <span><i className="key-dot more" /> More</span>
      </div>}
      {!mapError && selectedFarm && (
        <aside className="map-detail" aria-label={`${selectedFarm.name} details`}>
          <button className="detail-close" type="button" onClick={() => onSelect(null)} aria-label="Close farm details">×</button>
          <div className="detail-kicker">
            <i style={{ background: categoryColors[selectedFarm.category] || "#596b60" }} />
            {selectedFarm.category}
          </div>
          <h3>{selectedFarm.name}</h3>
          <p className="detail-place">{selectedFarm.city}, {selectedFarm.state} · {selectedFarm.parish} {selectedFarm.state === "LA" ? "Parish" : "County"}</p>
          <p className="detail-products">{selectedFarm.productsText}</p>
          {selectedFarm.marketPresence && (
            <div className="buy-note"><span>How to buy</span>{selectedFarm.marketPresence}</div>
          )}
          <div className="detail-tags">
            {serviceLabels(selectedFarm).map((label) => <span key={label}>{label}</span>)}
          </div>
          <div className="detail-actions">
            <button type="button" onClick={() => onOpenProfile(selectedFarm.id)}>Full profile →</button>
            {selectedFarm.website && <a href={selectedFarm.website} target="_blank" rel="noreferrer">Visit website ↗</a>}
            {selectedFarm.contact && <span>{selectedFarm.contact}</span>}
          </div>
          <p className="precision-note">{selectedFarm.geoPrecision === "city" ? "City-level location" : "Approximate area"} · Confirm before visiting</p>
        </aside>
      )}
    </div>
  );
}
