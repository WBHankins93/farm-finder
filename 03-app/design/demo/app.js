/* FarmFinder app demo — vanilla JS, real directory data */
const $ = (sel) => document.querySelector(sel);
const CAT_COLORS = {
  Produce: "#55734d", Mixed: "#6e7f4f", Meat: "#8b3e30", "Honey/Specialty": "#bd8628",
  Dairy: "#557a78", Seafood: "#39738c", Rice: "#99835c", "Urban Farm": "#5f7d62", "Value-Added": "#7d5b7f",
};
const GUIDES = [
  { id: "vegetables", label: "Vegetables", emoji: "🥬", color: "#55734d", tokens: ["vegetable", "produce", "greens", "lettuce", "tomato", "okra", "squash", "peas", "cucumber", "microgreen", "herbs"] },
  { id: "fruit", label: "Fruit & citrus", emoji: "🍓", color: "#b65f39", tokens: ["fruit", "berry", "berries", "blueberr", "strawberr", "peach", "watermelon", "melon", "citrus", "satsuma", "orchard"] },
  { id: "eggs", label: "Eggs", emoji: "🥚", color: "#c08a2e", tokens: ["egg"] },
  { id: "beef", label: "Beef", emoji: "🐄", color: "#8b3e30", tokens: ["beef", "cattle", "wagyu"] },
  { id: "pork", label: "Pork", emoji: "🐖", color: "#a95246", tokens: ["pork", "hog", "berkshire", "bacon", "sausage"] },
  { id: "poultry", label: "Poultry", emoji: "🐔", color: "#9a6936", tokens: ["chicken", "poultry", "turkey", "duck", "broiler"] },
  { id: "honey", label: "Honey", emoji: "🍯", color: "#bd8628", tokens: ["honey", "apiar", "bee", "beeswax"] },
  { id: "dairy", label: "Dairy", emoji: "🧀", color: "#557a78", tokens: ["dairy", "milk", "cheese", "creamery", "yogurt"] },
  { id: "seafood", label: "Seafood", emoji: "🦐", color: "#39738c", tokens: ["seafood", "crawfish", "shrimp", "crab", "fish", "oyster"] },
  { id: "rice", label: "Rice & grains", emoji: "🌾", color: "#99835c", tokens: ["rice", "grain", "grits", "cornmeal"] },
  { id: "flowers", label: "Flowers", emoji: "💐", color: "#7d5b7f", tokens: ["flower", "nursery", "plant", "seedling"] },
  { id: "mushrooms", label: "Mushrooms", emoji: "🍄", color: "#6f665c", tokens: ["mushroom", "fungi"] },
];
const SERVICES = [
  { key: "farmersMarket", label: "Farmers markets" },
  { key: "onFarm", label: "On-farm sales" },
  { key: "csa", label: "CSA shares" },
  { key: "ships", label: "Delivery / ships" },
  { key: "onlineStore", label: "Order online" },
];

let farms = [];
let map = null, miniMap = null, mapReady = false;
let activeGuide = "All";
let selectedId = null;
let saved = new Set(JSON.parse(localStorage.getItem("ff-saved") || "[]"));

const matchesGuide = (farm, guideId) => {
  if (guideId === "All") return true;
  const guide = GUIDES.find((g) => g.id === guideId);
  const hay = `${farm.productsText} ${farm.category} ${farm.notes}`.toLowerCase();
  return guide.tokens.some((t) => hay.includes(t));
};
const currentQuery = () => ($("#home-search").value || "").trim().toLowerCase();
const matchesFilters = (farm) => {
  if (!matchesGuide(farm, activeGuide)) return false;
  const q = currentQuery();
  if (!q) return true;
  const hay = `${farm.name} ${farm.productsText} ${farm.city} ${farm.parish} ${farm.region} ${farm.notes}`.toLowerCase();
  return hay.includes(q);
};
const summary = (f) =>
  `${f.name} is listed as a ${f.category.toLowerCase()} producer in ${f.city}, ${f.state}. Known products include ${f.productsText}.` +
  (f.marketPresence ? ` Customers connect through ${f.marketPresence.toLowerCase()}.` : "");

/* ---------- boot ---------- */
fetch("farms.json").then((r) => r.json()).then((data) => {
  farms = data;
  const la = farms.filter((f) => f.state === "LA").length;
  const ms = farms.filter((f) => f.state === "MS").length;
  $("#ob-farms").textContent = farms.length;
  $("#stat-la").textContent = la;
  $("#stat-ms").textContent = ms;
  $("#stat-mkt").textContent = farms.filter((f) => f.farmersMarket).length;
  $("#stat-csa").textContent = farms.filter((f) => f.csa).length;
  const hour = new Date().getHours();
  $("#greeting").textContent = hour < 12 ? "Good morning 👋" : hour < 17 ? "Good afternoon 👋" : "Good evening 👋";
  renderChips($("#harvest-chips"), true);
  renderChips($("#map-chips"), false);
  renderFeatured();
  renderSaved();
  renderPrompts();
});

/* ---------- navigation ---------- */
function go(name) {
  document.querySelectorAll(".screen").forEach((s) => (s.hidden = true));
  $(`#screen-${name}`).hidden = false;
  document.querySelectorAll(".dock button").forEach((b) => b.classList.toggle("active", b.dataset.nav === name));
  if (name === "explore") initMap();
}
document.addEventListener("click", (e) => {
  const nav = e.target.closest("[data-nav]");
  if (nav) go(nav.dataset.nav);
});
$("#ob-start").addEventListener("click", () => $("#onboarding").classList.add("hide"));

/* ---------- chips ---------- */
function renderChips(el, withCounts) {
  const all = document.createElement("button");
  all.className = "h-chip active";
  all.innerHTML = `<span class="emoji">🧺</span>All`;
  all.onclick = () => setGuide("All");
  el.appendChild(all);
  for (const g of GUIDES) {
    const count = farms.filter((f) => matchesGuide(f, g.id)).length;
    const b = document.createElement("button");
    b.className = "h-chip";
    b.dataset.guide = g.id;
    b.style.setProperty("--chip-color", g.color);
    b.innerHTML = `<span class="emoji">${g.emoji}</span>${g.label}${withCounts ? ` <small>${count}</small>` : ""}`;
    b.onclick = () => setGuide(g.id);
    el.appendChild(b);
  }
}
function setGuide(id) {
  activeGuide = activeGuide === id ? "All" : id;
  document.querySelectorAll(".h-chip").forEach((c) => {
    const target = c.dataset.guide || "All";
    c.classList.toggle("active", target === activeGuide);
  });
  renderFeatured();
  if (mapReady) refreshMapData();
  renderCarousel();
}

/* ---------- cards ---------- */
function badgeRow(f) {
  const badges = [];
  if (f.onlineStore) badges.push(`<span class="badge-web">Orders on website</span>`);
  else if (f.hasWebsite) badges.push(`<span class="badge-web">Website</span>`);
  for (const s of SERVICES) {
    if (s.key === "onlineStore" || !f[s.key]) continue;
    if (badges.length >= 3) break;
    badges.push(`<span>${s.label}</span>`);
  }
  return badges.join("");
}
function farmCard(f, { compact } = {}) {
  const card = document.createElement("article");
  card.className = "farm-card";
  card.dataset.id = f.id;
  const products = f.products.length ? f.products : [f.productsText];
  const shown = products.slice(0, 3).join(" · ");
  const extra = products.length > 3 ? ` +${products.length - 3} more` : "";
  card.innerHTML = `
    <div class="card-top">
      <p class="card-cat"><i style="background:${CAT_COLORS[f.category] || "#59604c"}"></i>${f.category}</p>
      <button class="heart ${saved.has(f.id) ? "on" : ""}" aria-label="Save ${f.name}">${saved.has(f.id) ? "♥" : "♡"}</button>
    </div>
    <h3>${f.name}</h3>
    <p class="card-place">${f.city}, ${f.state} · ${f.parish} ${f.state === "LA" ? "Parish" : "County"}</p>
    ${compact ? "" : `<p class="card-products">${shown}${extra}</p>`}
    <div class="card-badges">${badgeRow(f)}</div>
    ${compact ? `<button class="card-more" type="button">Details →</button>` : ""}`;
  card.querySelector(".heart").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleSave(f.id);
  });
  card.addEventListener("click", () => openSheet(f.id));
  return card;
}
function renderFeatured() {
  const list = $("#featured-list");
  list.innerHTML = "";
  const pool = farms.filter(matchesFilters);
  const featured = [...pool].sort((a, b) => Number(b.hasWebsite) - Number(a.hasWebsite) || Number(b.farmersMarket) - Number(a.farmersMarket)).slice(0, 6);
  $("#featured-count").textContent = `${pool.length} match${pool.length === 1 ? "" : "es"}`;
  featured.forEach((f) => list.appendChild(farmCard(f)));
  if (pool.length > featured.length) {
    const more = document.createElement("button");
    more.className = "see-all";
    more.textContent = `See all ${pool.length} on the map →`;
    more.onclick = () => go("explore");
    list.appendChild(more);
  }
  if (pool.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-note";
    empty.textContent = "No farms match that search yet — try a broader product or place.";
    list.appendChild(empty);
  }
}
function onSearchChange() {
  renderFeatured();
  if (mapReady) refreshMapData();
  renderCarousel();
  updateQueryChip();
}
function updateQueryChip() {
  const chip = $("#map-query");
  const q = currentQuery();
  chip.hidden = !q;
  if (q) chip.textContent = `Search: “${q}” ✕`;
}
$("#map-query").addEventListener("click", () => {
  $("#home-search").value = "";
  onSearchChange();
});
$("#home-search").addEventListener("input", onSearchChange);
$("#home-search-go").addEventListener("click", () => go("explore"));

/* ---------- saved ---------- */
function toggleSave(id) {
  saved.has(id) ? saved.delete(id) : saved.add(id);
  localStorage.setItem("ff-saved", JSON.stringify([...saved]));
  document.querySelectorAll(`.farm-card[data-id="${CSS.escape(id)}"] .heart`).forEach((h) => {
    h.classList.toggle("on", saved.has(id));
    h.textContent = saved.has(id) ? "♥" : "♡";
  });
  const sheetHeart = $("#sheet-heart");
  if (sheetHeart.dataset.id === id) {
    sheetHeart.classList.toggle("on", saved.has(id));
    sheetHeart.textContent = saved.has(id) ? "♥" : "♡";
  }
  renderSaved();
}
function renderSaved() {
  const list = $("#saved-list");
  list.innerHTML = "";
  const items = farms.filter((f) => saved.has(f.id));
  $("#saved-empty").hidden = items.length > 0;
  items.forEach((f) => list.appendChild(farmCard(f)));
}

/* ---------- explore map ---------- */
function geojson() {
  return {
    type: "FeatureCollection",
    features: farms
      .filter((f) => f.latitude && f.longitude && matchesFilters(f))
      .map((f) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [f.longitude, f.latitude] },
        properties: { id: f.id, category: f.category },
      })),
  };
}
function initMap() {
  if (map) { map.resize(); return; }
  map = new maplibregl.Map({
    container: "map",
    style: "https://tiles.openfreemap.org/styles/liberty",
    center: [-90.9, 30.7],
    zoom: 6.1,
    attributionControl: false,
  });
  map.on("load", () => {
    mapReady = true;
    map.addSource("farms", { type: "geojson", data: geojson(), cluster: true, clusterRadius: 46 });
    const catMatch = ["match", ["get", "category"]];
    Object.entries(CAT_COLORS).forEach(([k, v]) => catMatch.push(k, v));
    catMatch.push("#59604c");
    map.addLayer({
      id: "clusters", type: "circle", source: "farms", filter: ["has", "point_count"],
      paint: { "circle-color": "#4c8c2b", "circle-radius": ["step", ["get", "point_count"], 16, 12, 21, 40, 27], "circle-stroke-width": 3, "circle-stroke-color": "#f8f5ec" },
    });
    map.addLayer({
      id: "cluster-count", type: "symbol", source: "farms", filter: ["has", "point_count"],
      layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Noto Sans Bold"] },
      paint: { "text-color": "#f8f5ec" },
    });
    map.addLayer({
      id: "points", type: "circle", source: "farms", filter: ["!", ["has", "point_count"]],
      paint: { "circle-color": catMatch, "circle-radius": 7.5, "circle-stroke-width": 2.5, "circle-stroke-color": "#f8f5ec" },
    });
    map.addLayer({
      id: "selected", type: "circle", source: "farms", filter: ["==", ["get", "id"], "__none__"],
      paint: { "circle-color": catMatch, "circle-radius": 11, "circle-stroke-width": 4, "circle-stroke-color": "#14301e" },
    });
    map.on("click", "points", (e) => selectFarm(e.features[0].properties.id, { fly: false }));
    map.on("click", "clusters", (e) => {
      map.getSource("farms").getClusterExpansionZoom(e.features[0].properties.cluster_id).then((zoom) =>
        map.easeTo({ center: e.features[0].geometry.coordinates, zoom }));
    });
    map.on("mouseenter", "points", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "points", () => (map.getCanvas().style.cursor = ""));
    renderCarousel();
  });
  $("#map-reset").addEventListener("click", () => {
    selectFarm(null);
    map.easeTo({ center: [-90.9, 30.7], zoom: 6.1 });
    $("#map-reset").hidden = true;
  });
}
function refreshMapData() {
  map.getSource("farms")?.setData(geojson());
}
function selectFarm(id, { fly = true } = {}) {
  selectedId = id;
  if (mapReady) map.setFilter("selected", ["==", ["get", "id"], id || "__none__"]);
  document.querySelectorAll(".map-carousel .farm-card").forEach((c) => c.classList.toggle("selected", c.dataset.id === id));
  if (!id) return;
  $("#map-reset").hidden = false;
  const f = farms.find((x) => x.id === id);
  if (fly && mapReady && f?.longitude) map.flyTo({ center: [f.longitude, f.latitude], zoom: Math.max(map.getZoom(), 9), speed: 1.4 });
  const card = document.querySelector(`.map-carousel .farm-card[data-id="${CSS.escape(id)}"]`);
  card?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}
function renderCarousel() {
  const el = $("#map-carousel");
  el.innerHTML = "";
  farms.filter((f) => matchesFilters(f) && f.latitude).slice(0, 40).forEach((f) => {
    const card = farmCard(f, { compact: true });
    // First tap selects + flies to the pin; "Details →" (or a second tap) opens the sheet.
    card.addEventListener("click", (e) => {
      if (e.target.closest(".card-more") || selectedId === f.id) return;
      e.stopPropagation();
      selectFarm(f.id);
    }, { capture: true });
    el.appendChild(card);
  });
}

/* ---------- farm sheet ---------- */
function openSheet(id) {
  const f = farms.find((x) => x.id === id);
  if (!f) return;
  $("#sheet-cat i").style.background = CAT_COLORS[f.category] || "#59604c";
  $("#sheet-cat span").textContent = `${f.category} · Farm profile`;
  $("#sheet-name").textContent = f.name;
  $("#sheet-place").textContent = `${f.city}, ${f.state} · ${f.region}`;
  const heart = $("#sheet-heart");
  heart.dataset.id = id;
  heart.classList.toggle("on", saved.has(id));
  heart.textContent = saved.has(id) ? "♥" : "♡";
  heart.onclick = () => toggleSave(id);
  $("#sheet-summary").textContent = summary(f);
  $("#sheet-products").innerHTML = (f.products.length ? f.products : [f.productsText]).map((p) => `<span>${p}</span>`).join("");
  $("#sheet-notes").textContent = f.notes || "No additional field notes recorded yet.";
  $("#sheet-trust").innerHTML = `
    <div><span>Directory source</span><strong>${f.source || "—"}</strong></div>
    <div><span>Location confidence</span><strong>${f.geoPrecision === "city" ? "City-level" : `${f.geoPrecision || "Regional"} approximation`}</strong></div>
    <div><span>Last verified</span><strong>${f.lastVerified || "—"}</strong></div>`;
  $("#sheet-presence").textContent = f.marketPresence || "A confirmed sales schedule has not been added to this listing yet.";
  $("#sheet-services").innerHTML = SERVICES.map((s) =>
    `<div class="${f[s.key] ? "" : "off"}"><i>${f[s.key] ? "✓" : "—"}</i>${s.label}</div>`).join("");
  const digits = (f.contact || "").replace(/\D/g, "");
  const links = [];
  if (f.website) links.push(`<a href="${f.website}" target="_blank" rel="noreferrer">Visit website ↗</a>`);
  if (f.contact?.includes("@")) links.push(`<a href="mailto:${f.contact}">Email farm</a>`);
  else if (digits.length >= 10) links.push(`<a href="tel:${digits}">Call farm</a>`);
  if (f.contact) links.push(`<span>${f.contact}</span>`);
  $("#sheet-contacts").innerHTML = links.join("");
  $("#sheet-geo-note").textContent = f.geoPrecision === "city"
    ? "Pin shows the listed city — confirm the exact address with the farm before visiting."
    : "This location is approximate. Contact the farm before making the trip.";
  setSheetTab("info");
  $("#farm-sheet").hidden = false;
  $("#sheet-backdrop").hidden = false;
  requestAnimationFrame(() => {
    $("#farm-sheet").classList.add("show");
    $("#sheet-backdrop").classList.add("show");
  });
  $("#farm-sheet").dataset.id = id;
}
function closeSheet() {
  $("#farm-sheet").classList.remove("show");
  $("#sheet-backdrop").classList.remove("show");
  setTimeout(() => {
    $("#farm-sheet").hidden = true;
    $("#sheet-backdrop").hidden = true;
    if (miniMap) { miniMap.remove(); miniMap = null; }
  }, 260);
}
function setSheetTab(tab) {
  document.querySelectorAll("#sheet-tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  ["info", "buy", "map"].forEach((t) => ($(`#pane-${t}`).hidden = t !== tab));
  if (tab === "map") {
    const f = farms.find((x) => x.id === $("#farm-sheet").dataset.id);
    if (!f?.longitude) return;
    if (miniMap) { miniMap.remove(); miniMap = null; }
    miniMap = new maplibregl.Map({
      container: "mini-map",
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [f.longitude, f.latitude], zoom: 10.5,
      attributionControl: false, interactive: false,
    });
    new maplibregl.Marker({ color: CAT_COLORS[f.category] || "#4c8c2b" }).setLngLat([f.longitude, f.latitude]).addTo(miniMap);
  }
}
$("#sheet-close").addEventListener("click", closeSheet);
$("#sheet-backdrop").addEventListener("click", closeSheet);
$("#sheet-tabs").addEventListener("click", (e) => e.target.dataset.tab && setSheetTab(e.target.dataset.tab));

/* ---------- ask ---------- */
const PROMPTS = [
  "What farms sell crawfish in Acadiana?",
  "Who offers CSA shares?",
  "Where can I order beef online?",
  "When is citrus in season?",
  "Who sells eggs near New Orleans?",
];
function renderPrompts() {
  $("#ask-prompts").innerHTML = "";
  PROMPTS.forEach((p) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = p;
    b.onclick = () => { $("#ask-input").value = p; runAsk(p); };
    $("#ask-prompts").appendChild(b);
  });
}
function runAsk(q) {
  const n = q.trim().toLowerCase();
  if (!n) return;
  const named = [...farms].sort((a, b) => b.name.length - a.name.length).find((f) => n.includes(f.name.toLowerCase()));
  let title, sum, detail, ids = [];
  if (named) {
    title = named.name; sum = summary(named);
    detail = "Open the profile for contact details, notes, and location confidence.";
    ids = [named.id];
  } else {
    const guide = GUIDES.find((g) => g.tokens.some((t) => n.includes(t)));
    let stateCode = n.includes("mississippi") ? "MS" : n.includes("louisiana") ? "LA" : "";
    const places = [...new Set(farms.flatMap((f) => [f.city, f.parish, f.region]).filter((p) => p && p.length > 3))].sort((a, b) => b.length - a.length);
    const place = places.find((p) => n.includes(p.toLowerCase())) || "";
    let service = "";
    if (n.includes("csa") || n.includes("farm share")) service = "csa";
    else if (n.includes("market")) service = "farmersMarket";
    else if (n.includes("pickup") || n.includes("pick up") || n.includes("farm stand")) service = "onFarm";
    else if (n.includes("deliver") || n.includes("ship")) service = "ships";
    else if (n.includes("online") || n.includes("order")) service = "onlineStore";
    const matches = farms.filter((f) => {
      const locHay = `${f.city} ${f.parish} ${f.region}`.toLowerCase();
      return (!guide || matchesGuide(f, guide.id)) && (!stateCode || f.state === stateCode) &&
        (!place || locHay.includes(place.toLowerCase())) && (!service || f[service]);
    });
    if (!guide && !place && !stateCode && !service) {
      title = "Try naming a product, place, or way to buy";
      sum = "For example: “blueberries near Hattiesburg”, “farms that deliver”, or a farm’s name.";
      detail = "Answers stay inside the directory instead of inventing availability.";
    } else if (n.includes("season") && guide) {
      title = `${guide.label}: seasonal note`;
      sum = `Seasonal availability shifts across the Gulf South — the directory lists ${matches.length} producers matching ${guide.label.toLowerCase()}.`;
      detail = "FarmFinder doesn’t receive live inventory; ask the farm what was harvested this week.";
      ids = matches.map((f) => f.id);
    } else {
      title = `I found ${matches.length} ${matches.length === 1 ? "farm" : "farms"}`;
      const mkt = matches.filter((f) => f.farmersMarket).length;
      const online = matches.filter((f) => f.onlineStore).length;
      sum = `${place ? `Around ${place}, ` : ""}${matches.length} directory record${matches.length === 1 ? " matches" : "s match"} your question.`;
      detail = `${mkt} sell at farmers markets and ${online} take online orders. Availability is not live — confirm with the farm.`;
      ids = matches.map((f) => f.id);
    }
  }
  $("#answer-title").textContent = title;
  $("#answer-summary").textContent = sum;
  $("#answer-detail").textContent = detail;
  const wrap = $("#answer-farms");
  wrap.innerHTML = "";
  ids.slice(0, 5).forEach((id) => {
    const f = farms.find((x) => x.id === id);
    const b = document.createElement("button");
    b.innerHTML = `<small>${f.city}, ${f.state}</small>${f.name}`;
    b.onclick = () => openSheet(id);
    wrap.appendChild(b);
  });
  if (ids.length > 5) {
    const more = document.createElement("span");
    more.textContent = `+ ${ids.length - 5} more matches`;
    wrap.appendChild(more);
  }
  $("#ask-answer").hidden = false;
}
$("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); runAsk($("#ask-input").value); });
