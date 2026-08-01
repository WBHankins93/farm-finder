"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DiscoveryScope, FarmMapResponse, FarmSearchResponse, FarmSummary, LatLng, MapBounds, PlaceSearchResponse, PlaceSuggestion, ServiceKey, SortMode, ViewMode } from "../lib/discovery-contract";
import { categories, productGuides, serviceFilters } from "../lib/directory-config";
import { categoryColors, type Farm } from "../lib/farms";
import { Mark, markForCategory, markForProduct } from "../lib/marks";
import FarmProfileDialog from "./farm-profile-dialog";

const MapCanvas = dynamic(() => import("./farm-map"), {
  ssr: false,
  loading: () => <div className="map-wrap map-placeholder" role="status"><span /><strong>Preparing the field map…</strong><small>The farm list stays available while geography loads.</small></div>,
});

const emptySearch: FarmSearchResponse = { items: [], total: 0, nextCursor: null, scope: { mode: "all", label: "all covered areas", origin: null, radiusMiles: null, bounds: null }, sort: "name", releaseId: "" };
const emptyMap: FarmMapResponse = { features: [], total: 0, scope: emptySearch.scope, releaseId: "" };

function fullFarmToSummary(farm: Farm): FarmSummary {
  return {
    id: farm.id, name: farm.name, category: farm.category, region: farm.region, parish: farm.parish, state: farm.state, city: farm.city,
    productsText: farm.productsText, products: farm.products, marketPresence: farm.marketPresence, website: farm.website, contact: farm.contact,
    farmersMarket: farm.farmersMarket, onFarm: farm.onFarm, csa: farm.csa, ships: farm.ships, onlineStore: farm.onlineStore,
    latitude: farm.latitude, longitude: farm.longitude, geoPrecision: farm.geoPrecision, distanceMiles: null,
  };
}

function serializeBounds(bounds: MapBounds) {
  return bounds.map((value) => value.toFixed(4)).join(",");
}

export default function DiscoveryWorkspace() {
  const [initialized, setInitialized] = useState(false);
  const [query, setQuery] = useState("");
  const [deferredQuery, setDeferredQuery] = useState("");
  const [placeInput, setPlaceInput] = useState("");
  const [place, setPlace] = useState<PlaceSuggestion | null>(null);
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [userOrigin, setUserOrigin] = useState<LatLng | null>(null);
  const [locationMessage, setLocationMessage] = useState("");
  const [locating, setLocating] = useState(false);
  const [radius, setRadius] = useState<25 | 50 | 100>(50);
  const [bbox, setBbox] = useState<MapBounds | null>(null);
  const [pendingCamera, setPendingCamera] = useState<{ bounds: MapBounds; zoom: number } | null>(null);
  const [mapZoom, setMapZoom] = useState(7);
  const [category, setCategory] = useState("");
  const [product, setProduct] = useState("");
  const [services, setServices] = useState<ServiceKey[]>([]);
  const [sort, setSort] = useState<SortMode>("name");
  const [view, setView] = useState<ViewMode>("list");
  const [browseAll, setBrowseAll] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [draftCategory, setDraftCategory] = useState("");
  const [draftServices, setDraftServices] = useState<ServiceKey[]>([]);
  const [draftTotal, setDraftTotal] = useState(0);
  const [searchResult, setSearchResult] = useState<FarmSearchResponse>(emptySearch);
  const [mapResult, setMapResult] = useState<FarmMapResponse>(emptyMap);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedFarm, setSelectedFarm] = useState<FarmSummary | null>(null);
  const [hoveredFarm, setHoveredFarm] = useState<FarmSummary | null>(null);
  const [profileFarm, setProfileFarm] = useState<Farm | null>(null);
  const [clusterFarms, setClusterFarms] = useState<FarmSummary[]>([]);
  const [mapActivated, setMapActivated] = useState(false);
  const placeInputRef = useRef<HTMLInputElement>(null);
  const filtersButtonRef = useRef<HTMLButtonElement>(null);
  const filtersDialogRef = useRef<HTMLElement>(null);
  const mapShellRef = useRef<HTMLDivElement>(null);
  const requestSequence = useRef(0);
  const hasWrittenUrl = useRef(false);

  const hydrateFromUrl = useCallback(async () => {
    const params = new URLSearchParams(window.location.search);
    const rawQuery = params.get("q") ?? "";
    const rawPlace = params.get("near") ?? params.get("place") ?? "";
    const rawRadius = Number(params.get("radiusMiles"));
    const rawServices = (params.get("services") ?? "").split(",").filter((value): value is ServiceKey => serviceFilters.some((filter) => filter.key === value));
    const rawBounds = (params.get("bbox") ?? "").split(",").map(Number);
    setQuery(rawQuery);
    setDeferredQuery(rawQuery);
    setRadius(rawRadius === 25 || rawRadius === 100 ? rawRadius : 50);
    setCategory(params.get("category") ?? "");
    setProduct(params.get("product") ?? "");
    setServices(rawServices);
    setSort((params.get("sort") as SortMode) || (rawQuery ? "relevance" : rawPlace ? "distance" : "name"));
    setView(params.get("view") === "map" ? "map" : "list");
    setBrowseAll(params.get("all") === "1");
    if (rawBounds.length === 4 && rawBounds.every(Number.isFinite)) setBbox(rawBounds as MapBounds);
    if (rawPlace) {
      const lookup = rawPlace.includes(",") ? rawPlace : rawPlace.replace(/-([a-z]{2})$/i, ", $1").replace(/-/g, " ");
      setPlaceInput(lookup);
      try {
        const response = await fetch(`/v1/places?q=${encodeURIComponent(lookup)}&limit=8`);
        const data = await response.json() as PlaceSearchResponse;
        const match = data.items.find((item) => item.slug === rawPlace) ?? data.items[0] ?? null;
        if (match) {
          setPlace(match);
          setPlaceInput(match.label);
          setSort(rawQuery ? "relevance" : "distance");
        }
      } catch {
        setLocationMessage("Choose a city from the suggestions to search nearby.");
      }
    }
    const rawFarmId = params.get("farm");
    if (rawFarmId) {
      try {
        const response = await fetch(`/v1/farms/${encodeURIComponent(rawFarmId)}`);
        if (response.ok) {
          const record = await response.json() as { farm: Farm };
          setSelectedFarm(fullFarmToSummary(record.farm));
        }
      } catch {
        setLocationMessage("The selected farm could not be restored.");
      }
    } else {
      setSelectedFarm(null);
    }
    setInitialized(true);
  }, []);

  useEffect(() => {
    const initialHydration = window.setTimeout(() => void hydrateFromUrl(), 0);
    window.addEventListener("popstate", hydrateFromUrl);
    return () => {
      window.clearTimeout(initialHydration);
      window.removeEventListener("popstate", hydrateFromUrl);
    };
  }, [hydrateFromUrl]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDeferredQuery(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!initialized || place || placeInput.trim().length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/v1/places?q=${encodeURIComponent(placeInput.trim())}&limit=8`, { signal: controller.signal });
        const data = await response.json() as PlaceSearchResponse;
        setSuggestions(data.items);
        setSuggestionsOpen(true);
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") setSuggestions([]);
      }
    }, 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [placeInput, place, initialized]);

  const hasFilters = Boolean(deferredQuery || category || product || services.length);
  const hasScope = Boolean(place || userOrigin || bbox);
  const searchEnabled = initialized && (hasScope || hasFilters || browseAll);
  const serviceKey = services.join(",");
  const bboxKey = bbox ? serializeBounds(bbox) : "";

  const makeParams = useCallback((cursor = "") => {
    const params = new URLSearchParams();
    if (deferredQuery) params.set("q", deferredQuery);
    if (place && !bbox) params.set("near", place.slug);
    if (userOrigin && !bbox) {
      params.set("lat", userOrigin.lat.toFixed(3));
      params.set("lng", userOrigin.lng.toFixed(3));
    }
    if ((place || userOrigin) && !bbox) params.set("radiusMiles", String(radius));
    if (bbox) params.set("bbox", serializeBounds(bbox));
    if (category) params.set("category", category);
    if (product) params.set("product", product);
    if (services.length) params.set("services", services.join(","));
    params.set("sort", sort);
    params.set("limit", "30");
    if (cursor) params.set("cursor", cursor);
    return params;
  }, [deferredQuery, place, userOrigin, radius, bbox, category, product, services, sort]);

  useEffect(() => {
    if (!searchEnabled) return;
    const sequence = ++requestSequence.current;
    const controller = new AbortController();
    const params = makeParams();
    const mapParams = new URLSearchParams(params);
    mapParams.delete("limit");
    mapParams.set("zoom", String(mapZoom));
    queueMicrotask(() => {
      setError("");
      setRefreshing(searchResult.items.length > 0);
      setLoading(searchResult.items.length === 0);
    });

    Promise.all([
      fetch(`/v1/farms?${params}`, { signal: controller.signal }).then((response) => response.ok ? response.json() as Promise<FarmSearchResponse> : Promise.reject(new Error(`search ${response.status}`))),
      fetch(`/v1/farms/map?${mapParams}`, { signal: controller.signal }).then((response) => response.ok ? response.json() as Promise<FarmMapResponse> : Promise.reject(new Error(`map ${response.status}`))),
    ]).then(([list, map]) => {
      if (sequence !== requestSequence.current) return;
      setSearchResult(list);
      setMapResult(map);
      setSelectedFarm((current) => current && (list.items.some((farm) => farm.id === current.id) || map.features.some((feature) => feature.kind === "farm" && feature.id === current.id)) ? current : null);
    }).catch((caught) => {
      if ((caught as Error).name !== "AbortError") setError("Farm results could not be refreshed. Try again.");
    }).finally(() => {
      if (sequence === requestSequence.current) {
        setLoading(false);
        setRefreshing(false);
      }
    });
    return () => controller.abort();
  // Primitive keys keep user typing and transient map movement from restarting requests.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchEnabled, deferredQuery, place?.slug, userOrigin?.lat, userOrigin?.lng, radius, bboxKey, category, product, serviceKey, sort, mapZoom]);

  useEffect(() => {
    if (!initialized) return;
    const params = new URLSearchParams();
    if (deferredQuery) params.set("q", deferredQuery);
    if (place && !userOrigin && !bbox) params.set("near", place.slug);
    if ((place || userOrigin) && !bbox) params.set("radiusMiles", String(radius));
    if (bbox) params.set("bbox", serializeBounds(bbox));
    if (category) params.set("category", category);
    if (product) params.set("product", product);
    if (services.length) params.set("services", services.join(","));
    if (sort !== "name") params.set("sort", sort);
    if (view !== "list") params.set("view", view);
    if (browseAll) params.set("all", "1");
    if (selectedFarm) params.set("farm", selectedFarm.id);
    const url = `${window.location.pathname}${params.size ? `?${params}` : ""}${window.location.hash || "#discover"}`;
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (url !== currentUrl) {
      window.history[hasWrittenUrl.current ? "pushState" : "replaceState"](null, "", url);
    }
    hasWrittenUrl.current = true;
  }, [initialized, deferredQuery, place, userOrigin, bbox, radius, category, product, services, sort, view, browseAll, selectedFarm]);

  useEffect(() => {
    const shell = mapShellRef.current;
    if (!shell || mapActivated) return;
    if (!("IntersectionObserver" in window)) {
      const activation = globalThis.setTimeout(() => setMapActivated(true), 0);
      return () => globalThis.clearTimeout(activation);
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setMapActivated(true);
        observer.disconnect();
      }
    }, { rootMargin: "320px" });
    observer.observe(shell);
    return () => observer.disconnect();
  }, [mapActivated]);

  useEffect(() => {
    if (!filtersOpen) return;
    const dialog = filtersDialogRef.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : filtersButtonRef.current;
    dialog?.querySelector<HTMLElement>("button")?.focus();

    function handleFilterKeys(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setFiltersOpen(false);
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>('button, select, input, [href], [tabindex]:not([tabindex="-1"])')).filter((element) => !element.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", handleFilterKeys);
    return () => {
      window.removeEventListener("keydown", handleFilterKeys);
      previousFocus?.focus();
    };
  }, [filtersOpen]);

  useEffect(() => {
    if (!filtersOpen) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      const params = makeParams();
      params.delete("category");
      params.delete("services");
      if (draftCategory) params.set("category", draftCategory);
      if (draftServices.length) params.set("services", draftServices.join(","));
      params.set("limit", "1");
      try {
        const response = await fetch(`/v1/farms?${params}`, { signal: controller.signal });
        if (response.ok) setDraftTotal(((await response.json()) as FarmSearchResponse).total);
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") setDraftTotal(searchResult.total);
      }
    }, 150);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [filtersOpen, draftCategory, draftServices, makeParams, searchResult.total]);

  async function locate() {
    setLocating(true);
    setLocationMessage("Finding your approximate location…");
    if (!navigator.geolocation) {
      setLocating(false);
      setLocationMessage("Location is unavailable. Enter a city or town instead.");
      placeInputRef.current?.focus();
      return;
    }
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      setUserOrigin({ lat: Math.round(coords.latitude * 1000) / 1000, lng: Math.round(coords.longitude * 1000) / 1000 });
      setPlace(null);
      setPlaceInput("Current location");
      setBbox(null);
      setPendingCamera(null);
      setBrowseAll(false);
      setSort(query.trim() ? "relevance" : "distance");
      setLocationMessage("Showing farms near your approximate location.");
      setLocating(false);
    }, () => {
      setLocating(false);
      setLocationMessage("Location permission was not available. Enter a city or town instead.");
      placeInputRef.current?.focus();
    }, { enableHighAccuracy: false, timeout: 8000 });
  }

  function choosePlace(nextPlace: PlaceSuggestion) {
    setPlace(nextPlace);
    setPlaceInput(nextPlace.label);
    setSuggestionsOpen(false);
    setSuggestions([]);
    setUserOrigin(null);
    setBbox(null);
    setPendingCamera(null);
    setBrowseAll(false);
    setSort(query.trim() ? "relevance" : "distance");
    setLocationMessage(`Showing farms within ${radius} miles of ${nextPlace.label}.`);
  }

  function updatePlaceInput(value: string) {
    setPlaceInput(value);
    setPlace(null);
    setUserOrigin(null);
    setBbox(null);
    setPendingCamera(null);
    setBrowseAll(false);
    setSort(query.trim() ? "relevance" : "name");
    if (value.trim().length < 2) {
      setSuggestions([]);
      setSuggestionsOpen(false);
    }
  }

  function browseNationwide() {
    setBrowseAll(true);
    setPlace(null);
    setUserOrigin(null);
    setBbox(null);
    setPlaceInput("");
    setSort(query.trim() ? "relevance" : "name");
    setLocationMessage("Browsing all covered areas. Add a city for nearby results.");
  }

  function toggleService(service: ServiceKey) {
    setServices((current) => current.includes(service) ? current.filter((item) => item !== service) : [...current, service]);
  }

  function openFilters() {
    setDraftCategory(category);
    setDraftServices(services);
    setDraftTotal(searchResult.total);
    setFiltersOpen(true);
  }

  function toggleDraftService(service: ServiceKey) {
    setDraftServices((current) => current.includes(service) ? current.filter((item) => item !== service) : [...current, service]);
  }

  function applyDraftFilters() {
    setCategory(draftCategory);
    setServices(draftServices);
    setFiltersOpen(false);
  }

  function clearFilters() {
    setQuery("");
    setDeferredQuery("");
    setCategory("");
    setProduct("");
    setServices([]);
    setSort(hasScope ? "distance" : "name");
  }

  function startOver() {
    clearFilters();
    setPlace(null);
    setUserOrigin(null);
    setBbox(null);
    setPendingCamera(null);
    setPlaceInput("");
    setBrowseAll(false);
    setSelectedFarm(null);
    setSearchResult(emptySearch);
    setMapResult(emptyMap);
    setLocationMessage("");
    placeInputRef.current?.focus();
  }

  async function loadMore() {
    if (!searchResult.nextCursor) return;
    const response = await fetch(`/v1/farms?${makeParams(searchResult.nextCursor)}`);
    if (!response.ok) {
      setError("More farms could not be loaded. Try again.");
      return;
    }
    const next = await response.json() as FarmSearchResponse;
    setSearchResult((current) => ({ ...next, items: [...current.items, ...next.items] }));
  }

  const fetchFarm = useCallback(async (id: string) => {
    const response = await fetch(`/v1/farms/${encodeURIComponent(id)}`);
    if (!response.ok) throw new Error(`farm ${response.status}`);
    return (await response.json() as { farm: Farm }).farm;
  }, []);

  const selectFarm = useCallback(async (id: string) => {
    if (!id) {
      setSelectedFarm(null);
      return;
    }
    const loaded = searchResult.items.find((farm) => farm.id === id) ?? clusterFarms.find((farm) => farm.id === id);
    if (loaded) {
      setSelectedFarm(loaded);
      return;
    }
    try {
      setSelectedFarm(fullFarmToSummary(await fetchFarm(id)));
    } catch {
      setError("That farm profile could not be loaded.");
    }
  }, [searchResult.items, clusterFarms, fetchFarm]);

  const openProfile = useCallback(async (id: string) => {
    try {
      setProfileFarm(await fetchFarm(id));
    } catch {
      setError("That farm profile could not be loaded.");
    }
  }, [fetchFarm]);

  const selectCluster = useCallback(async (ids: string[]) => {
    try {
      const records = await Promise.all(ids.slice(0, 50).map(fetchFarm));
      setClusterFarms(records.map(fullFarmToSummary));
    } catch {
      setError("Farms at this approximate location could not be loaded.");
    }
  }, [fetchFarm]);

  const selectedOutsidePage = selectedFarm && !searchResult.items.some((farm) => farm.id === selectedFarm.id) ? selectedFarm : null;
  const scope = searchEnabled ? (searchResult.scope as DiscoveryScope) : null;
  const scopeText = scope?.mode === "nearby" ? `within ${scope.radiusMiles} miles of ${scope.label}` : scope?.mode === "area" ? "in this map area" : "across all covered areas";
  const sortLabel = sort === "distance" ? "Nearest" : sort === "relevance" ? "Best match" : "Farm name";

  return (
    <section className="discovery discovery-v2" id="discover" aria-labelledby="discover-title">
      <div className="discovery-heading"><div><p className="section-number">Search the directory</p><h2 id="discover-title">Find food from a farm near you.</h2></div><p>Choose a city or share an approximate location. The directory loads only the farms relevant to your search.</p></div>

      <div className="discovery-controls">
        <div className="location-control">
          <label htmlFor="near-place">City or town</label>
          <div className="location-input-row"><input ref={placeInputRef} id="near-place" value={placeInput} onChange={(event) => updatePlaceInput(event.target.value)} onFocus={() => suggestions.length && setSuggestionsOpen(true)} placeholder="Madison, WI" autoComplete="off" /><button type="button" onClick={locate} disabled={locating}>{locating ? "Finding you…" : "Use my location"}</button></div>
          {suggestionsOpen && suggestions.length ? <div className="place-suggestions" role="listbox" aria-label="Place suggestions">{suggestions.map((suggestion) => <button type="button" role="option" aria-selected={place?.slug === suggestion.slug} key={suggestion.slug} onMouseDown={(event) => event.preventDefault()} onClick={() => choosePlace(suggestion)}><span>{suggestion.label}</span><small>{suggestion.farmCount.toLocaleString()} directory records</small></button>)}</div> : null}
        </div>
        <label className="directory-query"><span>Farm or food</span><div><input value={query} onChange={(event) => { setQuery(event.target.value); setSort(event.target.value.trim() ? "relevance" : hasScope ? "distance" : "name"); }} placeholder="Eggs, tomatoes, farm name…" type="search" />{query ? <button type="button" onClick={() => setQuery("")} aria-label="Clear farm search">×</button> : null}</div></label>
        <div className="radius-control" aria-label="Search radius"><span>Field boundary</span><div>{([25, 50, 100] as const).map((miles) => <button type="button" key={miles} className={radius === miles ? "active" : ""} disabled={!place && !userOrigin} onClick={() => { setRadius(miles); setBbox(null); setPendingCamera(null); }}>{miles} mi</button>)}</div></div>
      </div>

      <div className="location-status" aria-live="polite"><span>{locationMessage || "Choose a city to begin nearby search."}</span>{!searchEnabled ? <button type="button" onClick={browseNationwide}>Browse all farms instead</button> : <button type="button" onClick={startOver}>Start over</button>}</div>

      <div className="primary-filters" aria-label="Quick filters">
        <div className="quick-filter-scroll"><button type="button" className={!product ? "active" : ""} onClick={() => setProduct("")}>All products</button>{productGuides.slice(0, 8).map((guide) => <button type="button" key={guide.id} className={product === guide.id ? "active" : ""} onClick={() => setProduct(product === guide.id ? "" : guide.id)} aria-pressed={product === guide.id}>{markForProduct(guide.id) ? <Mark name={markForProduct(guide.id)!} style={{ color: guide.color }} /> : null}{guide.shortLabel}</button>)}</div>
        <div className="quick-service-row">{serviceFilters.slice(0, 3).map(({ key, shortLabel }) => <button type="button" key={key} className={services.includes(key) ? "active" : ""} onClick={() => toggleService(key)} aria-pressed={services.includes(key)}>{services.includes(key) ? "✓ " : "+ "}{shortLabel}</button>)}<button ref={filtersButtonRef} className="all-filters-button" type="button" onClick={openFilters}>All filters {category || services.length > 3 ? "•" : ""}</button>{hasFilters ? <button className="clear-filters" type="button" onClick={clearFilters}>Clear filters</button> : null}</div>
      </div>

      {filtersOpen ? <div className="filter-sheet-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setFiltersOpen(false)}><section ref={filtersDialogRef} className="filter-sheet" role="dialog" aria-modal="true" aria-labelledby="filter-sheet-title"><header><div><span>Refine the field</span><h3 id="filter-sheet-title">All filters</h3></div><button type="button" onClick={() => setFiltersOpen(false)} aria-label="Close filters">×</button></header><div className="filter-sheet-group"><h4>Farm category</h4><div><button type="button" className={!draftCategory ? "active" : ""} onClick={() => setDraftCategory("")}>Any category</button>{categories.map((item) => <button type="button" className={draftCategory === item ? "active" : ""} onClick={() => setDraftCategory(draftCategory === item ? "" : item)} key={item}><Mark name={markForCategory(item)} style={{ color: categoryColors[item] }} />{item}</button>)}</div></div><div className="filter-sheet-group"><h4>Ways to buy</h4><div>{serviceFilters.map(({ key, label }) => <button type="button" className={draftServices.includes(key) ? "active" : ""} onClick={() => toggleDraftService(key)} key={key}>{draftServices.includes(key) ? "✓ " : "+ "}{label}</button>)}</div></div><footer><button type="button" onClick={() => { setDraftCategory(""); setDraftServices([]); }}>Reset these filters</button><button type="button" onClick={applyDraftFilters}>See {draftTotal.toLocaleString()} farms</button></footer></section></div> : null}

      <div className="results-toolbar">
        <p aria-live="polite"><strong>{searchResult.total.toLocaleString()}</strong> {searchResult.total === 1 ? "farm" : "farms"} {searchEnabled ? scopeText : "ready to search"}{refreshing ? <span> · Updating…</span> : null}</p>
        <label>Sort<select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}><option value="distance" disabled={!hasScope}>Nearest</option><option value="relevance" disabled={!deferredQuery}>Best match</option><option value="name">Farm name</option></select></label>
        <span>{sortLabel}</span>
      </div>

      <div className="mobile-view-switch" aria-label="Choose list or map view"><button type="button" className={view === "list" ? "active" : ""} aria-pressed={view === "list"} onClick={() => setView("list")}>List <span>{searchResult.total.toLocaleString()}</span></button><button type="button" className={view === "map" ? "active" : ""} aria-pressed={view === "map"} onClick={() => setView("map")}>Map <span>{mapResult.total.toLocaleString()}</span></button></div>

      <div className={`explorer explorer-v2 view-${view}`}>
        <div className="farm-list-panel">
          <div className="farm-list" aria-busy={loading || refreshing}>
            {!searchEnabled ? <div className="empty-state nearby-empty"><span aria-hidden="true">◎</span><h3>Set your field boundary.</h3><p>Choose a city or use your approximate location to see nearby farms without loading the whole country.</p><button type="button" onClick={() => placeInputRef.current?.focus()}>Enter a city</button></div> : null}
            {loading ? <div className="result-skeletons" role="status" aria-label="Loading farm results">{[1, 2, 3, 4].map((item) => <div key={item}><i /><span /><span /></div>)}</div> : null}
            {error && !loading ? <div className="inline-error" role="alert"><strong>Results paused</strong><p>{error}</p><button type="button" onClick={() => setMapZoom((current) => current + 0.0001)}>Try again</button></div> : null}
            {selectedOutsidePage ? <div className="selected-result-label">Selected farm</div> : null}
            {selectedOutsidePage ? <FarmCard farm={selectedOutsidePage} selected onSelect={selectFarm} onShowMap={(farm) => { setSelectedFarm(farm); setView("map"); }} onOpenProfile={openProfile} onHover={setHoveredFarm} /> : null}
            {!loading ? searchResult.items.map((farm) => <FarmCard farm={farm} selected={selectedFarm?.id === farm.id} key={farm.id} onSelect={selectFarm} onShowMap={(item) => { setSelectedFarm(item); setView("map"); }} onOpenProfile={openProfile} onHover={setHoveredFarm} />) : null}
            {!loading && searchEnabled && searchResult.total === 0 ? <div className="empty-state"><span aria-hidden="true">○</span><h3>No farms match this field yet.</h3><p>Remove a filter or expand the radius. The directory will not widen the search without asking.</p>{radius < 100 && hasScope ? <button type="button" onClick={() => setRadius(100)}>Expand to 100 miles</button> : <button type="button" onClick={clearFilters}>Clear filters</button>}</div> : null}
            {searchResult.nextCursor ? <button type="button" className="load-more" onClick={loadMore}>Load more farms</button> : null}
          </div>
        </div>
        <div className="map-panel" ref={mapShellRef}>
          {mapActivated ? <MapCanvas features={mapResult.features} selectedFarm={selectedFarm} hoveredFarm={hoveredFarm} userOrigin={userOrigin} scope={scope} searchAreaAvailable={Boolean(pendingCamera)} onSearchArea={() => { if (!pendingCamera) return; setBbox(pendingCamera.bounds); setMapZoom(pendingCamera.zoom); setPendingCamera(null); setPlace(null); setUserOrigin(null); setLocationMessage("Showing farms in the selected map area."); }} onCameraChange={(bounds, zoom) => setPendingCamera({ bounds, zoom })} onSelect={(id) => void selectFarm(id)} onSelectCluster={(ids) => void selectCluster(ids)} onOpenProfile={(id) => void openProfile(id)} /> : <div className="map-wrap map-placeholder" role="status"><span /><strong>Map waits until you need it.</strong><small>The list stays on the critical path.</small></div>}
          {clusterFarms.length ? <aside className="cluster-sheet" aria-label="Farms at this approximate location"><header><div><span>Shared map point</span><strong>{clusterFarms.length} farms in this area</strong></div><button type="button" onClick={() => setClusterFarms([])} aria-label="Close shared location results">×</button></header><div>{clusterFarms.map((farm) => <button type="button" key={farm.id} onClick={() => { setClusterFarms([]); void selectFarm(farm.id); }}><small>{farm.category}</small><strong>{farm.name}</strong><span>{farm.city}, {farm.state}</span></button>)}</div></aside> : null}
        </div>
      </div>

      {profileFarm ? <FarmProfileDialog farm={profileFarm} onClose={() => setProfileFarm(null)} onShowMap={() => { setProfileFarm(null); setSelectedFarm(fullFarmToSummary(profileFarm)); setView("map"); }} /> : null}
    </section>
  );
}

function FarmCard({ farm, selected, onSelect, onShowMap, onOpenProfile, onHover }: { farm: FarmSummary; selected: boolean; onSelect: (id: string) => void; onShowMap: (farm: FarmSummary) => void; onOpenProfile: (id: string) => void; onHover: (farm: FarmSummary | null) => void }) {
  const services = [farm.farmersMarket && "Market", farm.onFarm && "Farm pickup", farm.csa && "CSA", farm.ships && "Delivery", farm.onlineStore && "Order online"].filter(Boolean) as string[];
  return <article className={`farm-card ${selected ? "selected" : ""}`} onMouseEnter={() => onHover(farm)} onMouseLeave={() => onHover(null)} onFocus={() => onHover(farm)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) onHover(null); }}><button className="farm-card-main" type="button" onClick={() => onSelect(farm.id)} aria-label={`Select ${farm.name}`}><div className="card-body"><p className="card-category"><Mark name={markForCategory(farm.category)} style={{ color: categoryColors[farm.category] || "#59604c" }} />{farm.category}{farm.distanceMiles !== null ? <span className="card-distance">{Math.round(farm.distanceMiles)} mi</span> : null}</p><h3>{farm.name}</h3><p className="card-place">{farm.city}, {farm.state} <span>·</span> {farm.parish || "Area not listed"}</p><p className="card-products">{farm.products.slice(0, 4).join(" · ") || farm.productsText}</p><div className="card-services">{services.slice(0, 3).map((label) => <span key={label}>{label}</span>)}</div></div><span className="card-arrow" aria-hidden="true">↗</span></button><div className="card-contact"><button type="button" onClick={() => onOpenProfile(farm.id)}>View profile</button>{farm.geoPrecision !== "ungeocoded" ? <button type="button" onClick={() => onShowMap(farm)}>Show on map</button> : <span>Location not mapped</span>}{farm.website ? <a href={farm.website} target="_blank" rel="noreferrer">Website ↗</a> : null}</div></article>;
}
