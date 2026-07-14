"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import farmsData from "./data/farms.json";

type Farm = {
  id: string;
  name: string;
  category: string;
  region: string;
  parish: string;
  state: string;
  city: string;
  productsText: string;
  products: string[];
  marketPresence: string;
  website: string;
  hasWebsite: boolean;
  onlineStore: boolean;
  facebook: boolean;
  instagram: boolean;
  farmersMarket: boolean;
  csa: boolean;
  ships: boolean;
  onFarm: boolean;
  contact: string;
  notes: string;
  source: string;
  latitude: number;
  longitude: number;
  geoPrecision: string;
};

type ServiceKey = "farmersMarket" | "onFarm" | "csa" | "ships" | "onlineStore";
type ViewMode = "list" | "map";

const farms = farmsData as Farm[];
const categories = [
  "All",
  "Produce",
  "Mixed",
  "Meat",
  "Honey/Specialty",
  "Dairy",
  "Seafood",
  "Rice",
  "Urban Farm",
  "Value-Added",
];

const serviceFilters: { key: ServiceKey; label: string }[] = [
  { key: "farmersMarket", label: "At farmers markets" },
  { key: "onFarm", label: "On-farm sales" },
  { key: "csa", label: "CSA shares" },
  { key: "ships", label: "Delivery / ships" },
  { key: "onlineStore", label: "Order online" },
];

const categoryColors: Record<string, string> = {
  Produce: "#55734d",
  Mixed: "#b65f39",
  Meat: "#8b3e30",
  "Honey/Specialty": "#c08a2e",
  Dairy: "#557a78",
  Seafood: "#39738c",
  Rice: "#99835c",
  "Urban Farm": "#6b6c3b",
  "Value-Added": "#7d5b7f",
};

const categoryExpression: maplibregl.ExpressionSpecification = [
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
  "#59604c",
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

function serviceLabels(farm: Farm) {
  return [
    farm.farmersMarket && "Market",
    farm.onFarm && "Farm pickup",
    farm.csa && "CSA",
    farm.ships && "Delivery",
    farm.onlineStore && "Order online",
  ].filter(Boolean) as string[];
}

function MapCanvas({
  visibleFarms,
  selectedFarm,
  onSelect,
}: {
  visibleFarms: Farm[];
  selectedFarm: Farm | null;
  onSelect: (id: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [locationMessage, setLocationMessage] = useState("");

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [-91.3, 31.45],
      zoom: 5.35,
      minZoom: 4,
      maxZoom: 16,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(
      new maplibregl.AttributionControl({ compact: true, customAttribution: "Farm locations are approximate" }),
      "bottom-right",
    );

    map.on("load", () => {
      map.addSource("farms", {
        type: "geojson",
        data: toFeatures(visibleFarms),
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
          "circle-color": "rgba(248, 244, 232, .84)",
          "circle-radius": ["step", ["get", "point_count"], 22, 20, 28, 60, 34],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#263d31",
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
        paint: { "text-color": "#263d31" },
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
          "circle-stroke-color": "#fffaf0",
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
          "circle-stroke-color": "#b94f2e",
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
      <div className="map-tools" aria-label="Map tools">
        <button type="button" onClick={fitVisible}>Fit results</button>
        <button type="button" onClick={useLocation}>Use my location</button>
      </div>
      {locationMessage && <div className="location-toast" role="status">{locationMessage}</div>}
      <div className="map-key" aria-label="Map legend">
        <span><i className="key-dot produce" /> Produce</span>
        <span><i className="key-dot meat" /> Meat</span>
        <span><i className="key-dot mixed" /> Mixed</span>
        <span><i className="key-dot more" /> More</span>
      </div>
      {selectedFarm && (
        <aside className="map-detail" aria-label={`${selectedFarm.name} details`}>
          <button className="detail-close" type="button" onClick={() => onSelect(null)} aria-label="Close farm details">×</button>
          <div className="detail-kicker">
            <i style={{ background: categoryColors[selectedFarm.category] || "#59604c" }} />
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
            {selectedFarm.website && <a href={selectedFarm.website} target="_blank" rel="noreferrer">Visit website ↗</a>}
            {selectedFarm.contact && <span>{selectedFarm.contact}</span>}
          </div>
          <p className="precision-note">{selectedFarm.geoPrecision === "city" ? "City-level location" : "Approximate area"} · Confirm before visiting</p>
        </aside>
      )}
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [state, setState] = useState("ALL");
  const [services, setServices] = useState<ServiceKey[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  const filteredFarms = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return farms.filter((farm) => {
      const searchable = [
        farm.name,
        farm.category,
        farm.productsText,
        farm.city,
        farm.parish,
        farm.region,
        farm.marketPresence,
        farm.notes,
      ].join(" ").toLocaleLowerCase();
      return (
        (!term || searchable.includes(term)) &&
        (category === "All" || farm.category === category) &&
        (state === "ALL" || farm.state === state) &&
        services.every((service) => farm[service])
      );
    });
  }, [query, category, state, services]);

  const selectedFarm = selectedId ? farms.find((farm) => farm.id === selectedId) || null : null;
  const louisianaCount = farms.filter((farm) => farm.state === "LA").length;
  const mississippiCount = farms.filter((farm) => farm.state === "MS").length;

  useEffect(() => {
    if (selectedId && !filteredFarms.some((farm) => farm.id === selectedId)) setSelectedId(null);
  }, [filteredFarms, selectedId]);

  function toggleService(service: ServiceKey) {
    setServices((current) =>
      current.includes(service) ? current.filter((item) => item !== service) : [...current, service],
    );
  }

  function clearFilters() {
    setQuery("");
    setCategory("All");
    setState("ALL");
    setServices([]);
    setSelectedId(null);
  }

  const selectFarm = useCallback((id: string | null) => {
    setSelectedId(id);
    if (id && window.innerWidth < 860) setViewMode("map");
  }, []);

  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FarmFinder home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>FarmFinder<small>Gulf South field guide</small></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#discover">Explore farms</a>
          <a href="#about">About the directory</a>
          <a className="farmer-link" href="mailto:hello@sproutflow.com?subject=Add%20or%20update%20my%20FarmFinder%20listing">Add your farm ↗</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-stamp" aria-hidden="true">Field notes<br />No. 001</div>
          <p className="hero-kicker">Louisiana · Mississippi · Growing outward</p>
          <h1 id="hero-title">The Gulf South,<br /><em>by the field.</em></h1>
          <p className="hero-copy">Find the people growing, raising, catching, and making food near you—then learn exactly how to buy from them.</p>
          <a className="hero-cta" href="#discover">Open the farm map <span>↓</span></a>
          <div className="hero-stats" aria-label="Directory coverage">
            <div><strong>{farms.length}</strong><span>unique farms mapped</span></div>
            <div><strong>{louisianaCount}</strong><span>Louisiana listings</span></div>
            <div><strong>{mississippiCount}</strong><span>Mississippi listings</span></div>
            <p>Built from regional directories, market rosters, and field research. Updated July 2026.</p>
          </div>
        </section>

        <section className="discovery" id="discover" aria-labelledby="discover-title">
          <div className="discovery-heading">
            <div>
              <p className="section-number">01 / Find your farmer</p>
              <h2 id="discover-title">What are you looking for?</h2>
            </div>
            <p>Search by food, farm, town, parish, or county. Every marker represents a known farm or producer.</p>
          </div>

          <div className="search-row">
            <label className="search-box">
              <span className="search-icon" aria-hidden="true" />
              <span className="sr-only">Search farms</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Try “eggs near Covington” or “crawfish”"
                type="search"
              />
              {query && <button type="button" onClick={() => setQuery("")} aria-label="Clear search">×</button>}
            </label>
            <div className="state-switch" aria-label="Filter by state">
              {[["ALL", "All"], ["LA", "Louisiana"], ["MS", "Mississippi"]].map(([value, label]) => (
                <button key={value} type="button" className={state === value ? "active" : ""} onClick={() => setState(value)} aria-pressed={state === value}>{label}</button>
              ))}
            </div>
          </div>

          <div className="category-row" aria-label="Filter by farm category">
            {categories.map((item) => (
              <button key={item} type="button" className={category === item ? "active" : ""} onClick={() => setCategory(item)} aria-pressed={category === item}>
                {item !== "All" && <i style={{ background: categoryColors[item] }} />}{item}
              </button>
            ))}
          </div>

          <div className="filter-row">
            <span>Shop your way</span>
            <div>
              {serviceFilters.map(({ key, label }) => (
                <button key={key} type="button" className={services.includes(key) ? "active" : ""} onClick={() => toggleService(key)} aria-pressed={services.includes(key)}>
                  <i aria-hidden="true">{services.includes(key) ? "✓" : "+"}</i>{label}
                </button>
              ))}
            </div>
            {(query || category !== "All" || state !== "ALL" || services.length > 0) && <button className="clear-filters" type="button" onClick={clearFilters}>Clear all</button>}
          </div>

          <div className="mobile-view-switch" aria-label="Choose list or map view">
            <button type="button" className={viewMode === "list" ? "active" : ""} onClick={() => setViewMode("list")}>List <span>{filteredFarms.length}</span></button>
            <button type="button" className={viewMode === "map" ? "active" : ""} onClick={() => setViewMode("map")}>Map</button>
          </div>

          <div className={`explorer view-${viewMode}`}>
            <div className="farm-list-panel">
              <div className="results-meta">
                <p aria-live="polite"><strong>{filteredFarms.length}</strong> {filteredFarms.length === 1 ? "farm" : "farms"} found</p>
                <span>Alphabetical</span>
              </div>
              <div className="farm-list">
                {filteredFarms.map((farm, index) => (
                  <article className={`farm-card ${selectedId === farm.id ? "selected" : ""}`} key={farm.id}>
                    <button className="farm-card-main" type="button" onClick={() => selectFarm(farm.id)} aria-label={`Show ${farm.name} on the map`}>
                      <span className="card-index">{String(index + 1).padStart(3, "0")}</span>
                      <div className="card-body">
                        <p className="card-category"><i style={{ background: categoryColors[farm.category] || "#59604c" }} />{farm.category}</p>
                        <h3>{farm.name}</h3>
                        <p className="card-place">{farm.city}, {farm.state} <span>·</span> {farm.parish}</p>
                        <p className="card-products">{farm.products.slice(0, 4).join(" · ") || farm.productsText}</p>
                        <div className="card-services">
                          {serviceLabels(farm).slice(0, 3).map((label) => <span key={label}>{label}</span>)}
                        </div>
                      </div>
                      <span className="card-arrow" aria-hidden="true">↗</span>
                    </button>
                    {(farm.website || farm.contact) && (
                      <div className="card-contact">
                        {farm.website && <a href={farm.website} target="_blank" rel="noreferrer">Website ↗</a>}
                        {farm.contact && <span>{farm.contact}</span>}
                      </div>
                    )}
                  </article>
                ))}
                {filteredFarms.length === 0 && (
                  <div className="empty-state">
                    <span aria-hidden="true">○</span>
                    <h3>No farms match those filters—yet.</h3>
                    <p>Try a broader place or product, or remove one of the shopping options.</p>
                    <button type="button" onClick={clearFilters}>Reset the directory</button>
                  </div>
                )}
              </div>
            </div>
            <div className="map-panel">
              <MapCanvas visibleFarms={filteredFarms} selectedFarm={selectedFarm} onSelect={selectFarm} />
            </div>
          </div>
        </section>

        <section className="about" id="about" aria-labelledby="about-title">
          <p className="section-number">02 / About this field guide</p>
          <div className="about-grid">
            <h2 id="about-title">A living directory,<br />built from the ground up.</h2>
            <div>
              <p>FarmFinder is cataloging independent farms across the Gulf South so buying local takes less detective work. This first map combines public directories, farmers-market rosters, extension resources, and direct research.</p>
              <p>Some pins represent a city or regional center rather than a farm gate. Always contact a farm before visiting; availability, hours, and harvests change with the season.</p>
            </div>
            <aside>
              <strong>Grow the map</strong>
              <p>Own a farm, know one we missed, or see a detail that needs fixing?</p>
              <a href="mailto:hello@sproutflow.com?subject=FarmFinder%20listing%20update">Send an update ↗</a>
            </aside>
          </div>
        </section>
      </main>

      <footer>
        <a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>FarmFinder<small>Find food closer to home.</small></span></a>
        <p>Louisiana → Mississippi → one region at a time.</p>
        <div><a href="#discover">Explore</a><a href="#about">About</a><a href="mailto:hello@sproutflow.com">Contact</a></div>
        <small>© 2026 FarmFinder · A Sproutflow initiative</small>
      </footer>
    </div>
  );
}
