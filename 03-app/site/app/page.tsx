"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import farmsData from "./data/farms.json";
import { categoryColors, serviceLabels, type Farm } from "./lib/farms";

const MapCanvas = dynamic(() => import("./components/farm-map"), {
  ssr: false,
  loading: () => (
    <div className="map-wrap map-placeholder" role="status">
      <span />
      <strong>Preparing the field map…</strong>
      <small>The farm list is ready while geography loads.</small>
    </div>
  ),
});

type ServiceKey = "farmersMarket" | "onFarm" | "csa" | "ships" | "onlineStore";
type ViewMode = "list" | "map";
type ProductGuide = {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  season: string;
  tokens: string[];
  color: string;
};
type AskAnswer = {
  title: string;
  summary: string;
  detail: string;
  farmIds: string[];
  productId?: string;
};

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

const productGuides: ProductGuide[] = [
  {
    id: "vegetables",
    label: "Vegetables & greens",
    shortLabel: "Vegetables",
    description: "Everyday produce, leafy greens, tomatoes, squash, okra, peas, herbs, and microgreens.",
    season: "Cool-season greens and roots give way to tomatoes, peppers, okra, squash, and field peas as the Gulf South warms.",
    tokens: ["vegetable", "produce", "greens", "lettuce", "tomato", "okra", "squash", "peas", "cucumber", "microgreen", "herbs"],
    color: "#55734d",
  },
  {
    id: "fruit",
    label: "Fruit, berries & citrus",
    shortLabel: "Fruit & citrus",
    description: "Blueberries, strawberries, peaches, melons, orchard fruit, and Louisiana citrus.",
    season: "Berries and peaches arrive from spring into summer; melons peak in the heat; satsumas and other citrus follow in fall and winter.",
    tokens: ["fruit", "berry", "berries", "blueberr", "strawberr", "peach", "watermelon", "melon", "citrus", "satsuma", "orchard"],
    color: "#b65f39",
  },
  {
    id: "eggs",
    label: "Eggs",
    shortLabel: "Eggs",
    description: "Chicken, duck, and other farm eggs from mixed farms, homesteads, and poultry producers.",
    season: "Eggs may be available year-round, but laying and market supply can change with heat, daylight, flock size, and farm schedules.",
    tokens: ["egg"],
    color: "#c08a2e",
  },
  {
    id: "beef",
    label: "Beef & cattle",
    shortLabel: "Beef",
    description: "Grass-fed, grass-finished, grain-finished, and pasture-raised beef sold by the cut or share.",
    season: "Frozen cuts can be available year-round; bulk beef and processor dates often require advance reservations.",
    tokens: ["beef", "cattle", "wagyu"],
    color: "#8b3e30",
  },
  {
    id: "pork",
    label: "Pork",
    shortLabel: "Pork",
    description: "Pastured pork, heritage hogs, sausage, and whole- or half-animal shares.",
    season: "Cuts may be stocked year-round, while bulk orders and specialty products often follow processing schedules.",
    tokens: ["pork", "hog", "berkshire", "bacon", "sausage"],
    color: "#a95246",
  },
  {
    id: "poultry",
    label: "Chicken & poultry",
    shortLabel: "Poultry",
    description: "Pastured chicken, turkey, duck, and other poultry sold fresh, frozen, or by pre-order.",
    season: "Many small flocks process on set dates, so asking about reservations and pickup windows is especially useful.",
    tokens: ["chicken", "poultry", "turkey", "duck", "broiler"],
    color: "#9a6936",
  },
  {
    id: "honey",
    label: "Honey & bee products",
    shortLabel: "Honey",
    description: "Raw honey, comb honey, beeswax goods, and apiary products from across the region.",
    season: "Honey stores well and is often sold year-round, but varietals and fresh harvests follow local bloom cycles.",
    tokens: ["honey", "apiar", "bee", "beeswax"],
    color: "#bd8628",
  },
  {
    id: "dairy",
    label: "Milk, cheese & dairy",
    shortLabel: "Dairy",
    description: "Cow and goat milk, artisan cheeses, creamery goods, and farmstead dairy products.",
    season: "Availability depends on herd cycles, licensing, and production schedules; confirm products and pickup rules directly.",
    tokens: ["dairy", "milk", "cheese", "creamery", "yogurt"],
    color: "#557a78",
  },
  {
    id: "seafood",
    label: "Seafood & crawfish",
    shortLabel: "Seafood",
    description: "Crawfish, shrimp, crab, fish, oysters, and direct-from-the-water Gulf products.",
    season: "Catch and harvest windows shift with weather, water conditions, regulation, and species—call before making the trip.",
    tokens: ["seafood", "crawfish", "shrimp", "crab", "fish", "oyster"],
    color: "#39738c",
  },
  {
    id: "rice",
    label: "Rice & grains",
    shortLabel: "Rice",
    description: "Louisiana-grown rice, specialty varieties, milled grains, and farm-direct pantry staples.",
    season: "Milled rice is generally shelf-stable and available beyond harvest; specialty varieties may sell out between crops.",
    tokens: ["rice", "grain", "grits", "cornmeal"],
    color: "#99835c",
  },
  {
    id: "flowers",
    label: "Flowers & nursery",
    shortLabel: "Flowers",
    description: "Cut flowers, edible flowers, native plants, seedlings, and small-farm nursery goods.",
    season: "Flower and plant availability is highly seasonal; spring and fall often bring the widest nursery selection.",
    tokens: ["flower", "nursery", "plant", "seedling"],
    color: "#7d5b7f",
  },
  {
    id: "mushrooms",
    label: "Mushrooms",
    shortLabel: "Mushrooms",
    description: "Fresh culinary mushrooms, specialty varieties, grow kits, and fungi-based products.",
    season: "Cultivated mushrooms may be produced year-round, but weekly harvests and varieties change quickly.",
    tokens: ["mushroom", "fungi"],
    color: "#6f665c",
  },
];


function farmMatchesProduct(farm: Farm, productId: string) {
  if (productId === "All") return true;
  const guide = productGuides.find((item) => item.id === productId);
  if (!guide) return true;
  const haystack = `${farm.productsText} ${farm.category} ${farm.notes}`.toLocaleLowerCase();
  return guide.tokens.some((token) => haystack.includes(token));
}

function farmSummary(farm: Farm) {
  const place = `${farm.city}, ${farm.state}`;
  const howToBuy = farm.marketPresence
    ? `The directory says customers connect with this producer through ${farm.marketPresence.toLocaleLowerCase()}.`
    : "The current record does not yet include a confirmed sales schedule.";
  const note = farm.notes && !farm.notes.toLocaleLowerCase().includes("no web") ? ` ${farm.notes}.` : "";
  return `${farm.name} is listed as a ${farm.category.toLocaleLowerCase()} producer in ${place}. Its known products include ${farm.productsText}. ${howToBuy}${note}`;
}

function answerFarmQuestion(question: string): AskAnswer {
  const normalized = question.trim().toLocaleLowerCase();
  if (!normalized) {
    return {
      title: "Ask about a food, place, or way to buy",
      summary: "Try asking who sells eggs near New Orleans, where to find crawfish in Acadiana, or which farms offer CSA shares.",
      detail: "Answers are generated from the FarmFinder directory and will always point back to matching farm records.",
      farmIds: [],
    };
  }

  const namedFarm = [...farms]
    .sort((a, b) => b.name.length - a.name.length)
    .find((farm) => normalized.includes(farm.name.toLocaleLowerCase()));
  if (namedFarm) {
    return {
      title: namedFarm.name,
      summary: farmSummary(namedFarm),
      detail: namedFarm.contact || namedFarm.website
        ? "Open the full profile for contact details, directory notes, and location confidence."
        : "This record has limited contact information; confirm details through its listed market or source directory.",
      farmIds: [namedFarm.id],
    };
  }

  const product = productGuides.find((guide) => guide.tokens.some((token) => normalized.includes(token)));
  const asksSeason = normalized.includes("season") || normalized.includes("available now") || normalized.includes("fresh now");
  const asksDefinition = normalized.includes("what is") || normalized.includes("what's a") || normalized.includes("explain");

  if (asksDefinition && normalized.includes("csa")) {
    const csaFarms = farms.filter((farm) => farm.csa);
    return {
      title: "CSA means Community Supported Agriculture",
      summary: "A CSA usually lets customers commit to a farm for a season and receive a recurring share of its harvest. Exact payment, pickup, contents, and schedule vary by farm.",
      detail: `FarmFinder currently identifies ${csaFarms.length} farms with a CSA in their directory record. Contact the farm to confirm whether shares are currently open.`,
      farmIds: csaFarms.map((farm) => farm.id),
    };
  }

  let locationTerm = "";
  let stateCode = "";
  if (normalized.includes("mississippi")) stateCode = "MS";
  if (normalized.includes("louisiana")) stateCode = "LA";
  const locationCandidates = Array.from(
    new Set(farms.flatMap((farm) => [farm.city, farm.parish, farm.region]).filter((item) => item.length > 3)),
  ).sort((a, b) => b.length - a.length);
  locationTerm = locationCandidates.find((item) => normalized.includes(item.toLocaleLowerCase())) || "";

  let service: ServiceKey | "" = "";
  if (normalized.includes("csa") || normalized.includes("farm share")) service = "csa";
  else if (normalized.includes("market")) service = "farmersMarket";
  else if (normalized.includes("pick up") || normalized.includes("pickup") || normalized.includes("farm stand")) service = "onFarm";
  else if (normalized.includes("deliver") || normalized.includes("ship")) service = "ships";
  else if (normalized.includes("online") || normalized.includes("order")) service = "onlineStore";

  const matches = farms.filter((farm) => {
    const locationHaystack = `${farm.city} ${farm.parish} ${farm.region}`.toLocaleLowerCase();
    return (
      (!product || farmMatchesProduct(farm, product.id)) &&
      (!stateCode || farm.state === stateCode) &&
      (!locationTerm || locationHaystack.includes(locationTerm.toLocaleLowerCase())) &&
      (!service || farm[service])
    );
  });

  if (asksSeason && product) {
    return {
      title: `${product.label}: a seasonal field note`,
      summary: product.season,
      detail: `The directory contains ${matches.length} matching producers${locationTerm ? ` around ${locationTerm}` : ""}. FarmFinder does not yet receive live inventory, so contact a farm to ask what was harvested or landed this week.`,
      farmIds: matches.map((farm) => farm.id),
      productId: product.id,
    };
  }

  if (!product && !locationTerm && !stateCode && !service) {
    const searchTerms = normalized
      .split(/[^a-z0-9]+/)
      .filter((term) => term.length > 2 && !["who", "what", "where", "which", "farm", "farms", "find", "near", "sell", "sells", "have", "with", "from", "about"].includes(term));
    const keywordMatches = farms.filter((farm) => {
      const haystack = `${farm.name} ${farm.productsText} ${farm.city} ${farm.parish} ${farm.region} ${farm.notes}`.toLocaleLowerCase();
      return searchTerms.some((term) => haystack.includes(term));
    });
    if (keywordMatches.length) {
      return {
        title: `I found ${keywordMatches.length} possible ${keywordMatches.length === 1 ? "match" : "matches"}`,
        summary: "These records contain terms from your question. Review the profiles to confirm the product and current availability.",
        detail: "FarmFinder searches farm names, products, places, notes, and ways to buy.",
        farmIds: keywordMatches.map((farm) => farm.id),
      };
    }
  }

  if (!matches.length || (!product && !locationTerm && !stateCode && !service)) {
    return {
      title: "I couldn’t find a verified match",
      summary: "Try naming one product, place, or shopping preference—for example, “blueberries near Hattiesburg” or “farms that deliver.”",
      detail: "The answer tool stays inside the directory instead of inventing availability or farm details.",
      farmIds: [],
    };
  }

  const marketCount = matches.filter((farm) => farm.farmersMarket).length;
  const pickupCount = matches.filter((farm) => farm.onFarm).length;
  const onlineCount = matches.filter((farm) => farm.onlineStore).length;
  const subject = product?.label.toLocaleLowerCase() || (service ? serviceFilters.find((item) => item.key === service)?.label.toLocaleLowerCase() : "matching farms");
  return {
    title: `I found ${matches.length} ${matches.length === 1 ? "farm" : "farms"}`,
    summary: `${locationTerm ? `Around ${locationTerm}, ` : ""}${matches.length} directory ${matches.length === 1 ? "record matches" : "records match"} your question about ${subject}.`,
    detail: `${marketCount} sell at farmers markets, ${pickupCount} list on-farm sales, and ${onlineCount} have online ordering. Availability is not live—contact the farm before visiting.`,
    farmIds: matches.map((farm) => farm.id),
    productId: product?.id,
  };
}

function FarmProfileDialog({
  farm,
  onClose,
  onShowMap,
  onOpenFarm,
}: {
  farm: Farm;
  onClose: () => void;
  onShowMap: (id: string) => void;
  onOpenFarm: (id: string) => void;
}) {
  const related = farms
    .filter((item) => item.id !== farm.id && (item.region === farm.region || item.category === farm.category))
    .sort((a, b) => Number(b.region === farm.region) - Number(a.region === farm.region))
    .slice(0, 3);
  const contactDigits = farm.contact.replace(/\D/g, "");
  const contactHref = farm.contact.includes("@")
    ? `mailto:${farm.contact}`
    : contactDigits.length >= 10
      ? `tel:${contactDigits}`
      : "";
  const questions = [
    "What is available this week?",
    farm.farmersMarket ? "Which market will you attend next?" : "Do you sell directly to visitors?",
    farm.csa ? "When does the next CSA share open?" : "Is a pre-order required?",
    farm.onFarm ? "What are your pickup hours?" : "Where is the best pickup point?",
  ];

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    document.body.classList.add("dialog-open");
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      document.body.classList.remove("dialog-open");
    };
  }, [onClose]);

  return (
    <div className="profile-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <article className="profile-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-title">
        <header className="profile-header">
          <div>
            <p className="profile-kicker"><i style={{ background: categoryColors[farm.category] || "#59604c" }} />{farm.category} · Farm profile</p>
            <h2 id="profile-title">{farm.name}</h2>
            <p>{farm.city}, {farm.state} · {farm.parish} {farm.state === "LA" ? "Parish" : "County"}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close farm profile">×</button>
        </header>

        <div className="profile-body">
          <section className="profile-summary">
            <span>Directory summary</span>
            <p>{farmSummary(farm)}</p>
          </section>

          <div className="profile-columns">
            <div className="profile-main">
              <section className="profile-section">
                <h3>Products & specialties</h3>
                <p>{farm.productsText}</p>
                <div className="profile-product-tags">
                  {farm.products.map((product) => <span key={product}>{product}</span>)}
                </div>
              </section>

              <section className="profile-section">
                <h3>How to buy</h3>
                <p>{farm.marketPresence || "A confirmed sales schedule has not been added to this listing yet."}</p>
                <div className="profile-service-grid">
                  {serviceFilters.map(({ key, label }) => (
                    <div className={farm[key] ? "available" : "unknown"} key={key}>
                      <i>{farm[key] ? "✓" : "—"}</i><span>{label}</span><small>{farm[key] ? "Listed" : "Not confirmed"}</small>
                    </div>
                  ))}
                </div>
              </section>

              <section className="profile-section">
                <h3>Directory notes</h3>
                <p>{farm.notes || "No additional field notes have been recorded for this farm yet."}</p>
              </section>

              <section className="profile-section ask-the-farm">
                <h3>Good questions to ask the farm</h3>
                <ol>{questions.map((question) => <li key={question}>{question}</li>)}</ol>
              </section>
            </div>

            <aside className="profile-sidebar">
              <div className="profile-actions">
                <button type="button" onClick={() => onShowMap(farm.id)}>Show on map →</button>
                {farm.website && <a href={farm.website} target="_blank" rel="noreferrer">Visit website ↗</a>}
                {contactHref && <a href={contactHref}>Contact farm ↗</a>}
              </div>
              {farm.contact && <div className="profile-fact"><span>Contact</span><strong>{farm.contact}</strong></div>}
              <div className="profile-fact"><span>Region</span><strong>{farm.region}</strong></div>
              <div className="profile-fact"><span>Location confidence</span><strong>{farm.geoPrecision === "city" ? "City-level" : `${farm.geoPrecision || "Regional"} approximation`}</strong><small>Confirm before visiting</small></div>
              <div className="profile-fact"><span>Online presence</span><strong>{farm.hasWebsite ? "Website listed" : farm.facebook || farm.instagram ? "Social only" : "No confirmed web presence"}</strong></div>
              <div className="profile-fact"><span>Directory source</span><strong>{farm.source}</strong><small>Dataset updated July 2026</small></div>
            </aside>
          </div>

          {related.length > 0 && (
            <section className="related-farms">
              <span>Keep exploring</span>
              <h3>Related farms</h3>
              <div>
                {related.map((item) => (
                  <button type="button" key={item.id} onClick={() => onOpenFarm(item.id)}>
                    <small>{item.category} · {item.city}</small><strong>{item.name}</strong><span>{item.products.slice(0, 3).join(" · ")}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </article>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [product, setProduct] = useState("All");
  const [state, setState] = useState("ALL");
  const [services, setServices] = useState<ServiceKey[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskAnswer | null>(null);
  const [askFarmIds, setAskFarmIds] = useState<string[] | null>(null);
  const [mapActivated, setMapActivated] = useState(false);
  const mapShellRef = useRef<HTMLDivElement>(null);

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
        farmMatchesProduct(farm, product) &&
        (state === "ALL" || farm.state === state) &&
        services.every((service) => farm[service]) &&
        (!askFarmIds || askFarmIds.includes(farm.id))
      );
    });
  }, [query, category, product, state, services, askFarmIds]);

  const selectedFarm = selectedId ? farms.find((farm) => farm.id === selectedId) || null : null;
  const profileFarm = profileId ? farms.find((farm) => farm.id === profileId) || null : null;
  const louisianaCount = farms.filter((farm) => farm.state === "LA").length;
  const mississippiCount = farms.filter((farm) => farm.state === "MS").length;
  const websiteGap = farms.filter((farm) => !farm.hasWebsite).length;
  const cityLevelCount = farms.filter((farm) => farm.geoPrecision === "city").length;
  const marketCount = farms.filter((farm) => farm.farmersMarket).length;
  const csaCount = farms.filter((farm) => farm.csa).length;
  const productCounts = useMemo(
    () => Object.fromEntries(productGuides.map((guide) => [guide.id, farms.filter((farm) => farmMatchesProduct(farm, guide.id)).length])),
    [],
  );

  useEffect(() => {
    if (selectedId && !filteredFarms.some((farm) => farm.id === selectedId)) {
      // Filtering invalidates the selection; clearing it is the synchronization this effect performs.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedId(null);
    }
  }, [filteredFarms, selectedId]);

  useEffect(() => {
    const shell = mapShellRef.current;
    if (!shell || mapActivated) return;
    if (!("IntersectionObserver" in window)) {
      // This fallback mirrors the observer callback for browsers without the API.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMapActivated(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setMapActivated(true);
        observer.disconnect();
      },
      { rootMargin: "480px 0px" },
    );
    observer.observe(shell);
    return () => observer.disconnect();
  }, [mapActivated]);

  function toggleService(service: ServiceKey) {
    setServices((current) =>
      current.includes(service) ? current.filter((item) => item !== service) : [...current, service],
    );
  }

  function clearFilters() {
    setQuery("");
    setCategory("All");
    setProduct("All");
    setState("ALL");
    setServices([]);
    setAskFarmIds(null);
    setSelectedId(null);
  }

  const selectFarm = useCallback((id: string | null) => {
    setSelectedId(id);
    if (id && window.innerWidth < 860) setViewMode("map");
  }, []);

  const closeProfile = useCallback(() => setProfileId(null), []);
  const openProfile = useCallback((id: string) => setProfileId(id), []);

  function runQuestion(text = question) {
    setQuestion(text);
    setAnswer(answerFarmQuestion(text));
  }

  function applyAnswerResults() {
    if (!answer?.farmIds.length) return;
    setAskFarmIds(answer.farmIds);
    if (answer.productId) setProduct(answer.productId);
    document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" });
  }

  function browseProduct(productId: string) {
    setProduct(productId);
    setAskFarmIds(null);
    document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" });
  }

  function showProfileOnMap(id: string) {
    setProfileId(null);
    setAskFarmIds(null);
    selectFarm(id);
    document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="site-shell">
      <a className="skip-link" href="#discover">Skip to farm search</a>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="FarmFinder home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>FarmFinder<small>U.S. farm field guide</small></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#ask">Ask</a>
          <a href="#products">Harvest</a>
          <a href="#discover">Explore farms</a>
          <a href="#updates">Updates</a>
          <a className="farmer-link" href="#discover">Find farms</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-atlas" aria-hidden="true">
            <span className="atlas-line atlas-line-one" />
            <span className="atlas-line atlas-line-two" />
            <i className="atlas-pin atlas-pin-one" />
            <i className="atlas-pin atlas-pin-two" />
            <i className="atlas-pin atlas-pin-three" />
          </div>
          <div className="hero-stamp" aria-hidden="true">Release 001<br />July 2026</div>
          <p className="hero-kicker">Now mapping Louisiana · Mississippi · Expanding region by region</p>
          <h1 id="hero-title">Find the farms<br /><em>behind your food.</em></h1>
          <p className="hero-copy">Find the people growing, raising, catching, and making food near you—then learn exactly how to buy from them.</p>
          <a className="hero-cta" href="#discover">Find food near you <span>↓</span></a>
          <div className="hero-stats" aria-label="Directory coverage">
            <div><strong>{farms.length}</strong><span>unique farms mapped</span></div>
            <div><strong>{louisianaCount}</strong><span>Louisiana listings</span></div>
            <div><strong>{mississippiCount}</strong><span>Mississippi listings</span></div>
            <p>Built from regional directories, market rosters, and field research. Updated July 2026.</p>
          </div>
        </section>

        <section className="ask-section" id="ask" aria-labelledby="ask-title">
          <div className="ask-heading">
            <p className="section-number">01 / Ask the field guide</p>
            <h2 id="ask-title">Start with a question.</h2>
            <p>Ask about a product, place, farm, season, or way to buy. Answers stay grounded in FarmFinder’s 299 directory records and clearly flag what still needs confirmation.</p>
          </div>

          <div className="ask-workspace">
            <form className="ask-form" onSubmit={(event) => { event.preventDefault(); runQuestion(); }}>
              <label htmlFor="farm-question">What would you like to find?</label>
              <div>
                <input
                  id="farm-question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Who sells eggs near New Orleans?"
                />
                <button type="submit">Ask →</button>
              </div>
              <p>Farm availability is not live. Answers identify likely matches and what to confirm directly.</p>
            </form>

            <div className="ask-prompts" aria-label="Suggested questions">
              <span>Try asking</span>
              {["What farms sell crawfish in Acadiana?", "Who offers CSA shares?", "Where can I order beef online?", "What does Covey Rise Farm sell?", "When is citrus in season?"].map((prompt) => (
                <button type="button" key={prompt} onClick={() => runQuestion(prompt)}>{prompt}</button>
              ))}
            </div>

            <div className={`ask-answer ${answer ? "has-answer" : ""}`} aria-live="polite">
              {answer ? (
                <>
                  <div className="answer-mark" aria-hidden="true">A</div>
                  <div className="answer-copy">
                    <span>FarmFinder answer</span>
                    <h3>{answer.title}</h3>
                    <p>{answer.summary}</p>
                    <p className="answer-detail">{answer.detail}</p>
                    {answer.farmIds.length > 0 && (
                      <div className="answer-farms">
                        {answer.farmIds.slice(0, 6).map((id) => {
                          const farm = farms.find((item) => item.id === id);
                          return farm ? <button type="button" key={id} onClick={() => openProfile(id)}><small>{farm.city}, {farm.state}</small>{farm.name}</button> : null;
                        })}
                        {answer.farmIds.length > 6 && <span>+ {answer.farmIds.length - 6} more matches</span>}
                      </div>
                    )}
                    {answer.farmIds.length > 0 && <button className="answer-action" type="button" onClick={applyAnswerResults}>Show all {answer.farmIds.length} on the map →</button>}
                  </div>
                </>
              ) : (
                <>
                  <div className="answer-mark" aria-hidden="true">?</div>
                  <div className="answer-copy empty">
                    <span>Built for practical questions</span>
                    <h3>Products, places, seasons, and farms</h3>
                    <p>FarmFinder can explain a CSA, summarize a farm, surface producers carrying a product, and narrow matches by region or shopping method.</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        <section className="products-section" id="products" aria-labelledby="products-title">
          <div className="products-heading">
            <div>
              <p className="section-number">02 / Browse the harvest</p>
              <h2 id="products-title">Start with what<br /><em>you want to eat.</em></h2>
            </div>
            <p>These product guides translate the farm records into useful paths. Counts show farms whose current directory description mentions that product—not live inventory.</p>
          </div>
          <div className="product-guide-grid">
            {productGuides.map((guide, index) => (
              <article className="product-guide-card" key={guide.id} style={{ "--product-color": guide.color } as React.CSSProperties}>
                <div className="product-card-top"><span>{String(index + 1).padStart(2, "0")}</span><strong>{productCounts[guide.id]}</strong></div>
                <h3>{guide.label}</h3>
                <p>{guide.description}</p>
                <details>
                  <summary>Seasonal field note</summary>
                  <p>{guide.season}</p>
                </details>
                <button type="button" onClick={() => browseProduct(guide.id)}>Browse {productCounts[guide.id]} matching farms →</button>
              </article>
            ))}
          </div>
        </section>

        <section className="discovery" id="discover" aria-labelledby="discover-title">
          <div className="discovery-heading">
            <div>
              <p className="section-number">03 / Find your farmer</p>
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

          <div className="filter-label"><span>Farm category</span><small>What kind of producer?</small></div>
          <div className="category-row" aria-label="Filter by farm category">
            {categories.map((item) => (
              <button key={item} type="button" className={category === item ? "active" : ""} onClick={() => setCategory(item)} aria-pressed={category === item}>
                {item !== "All" && <i style={{ background: categoryColors[item] }} />}{item}
              </button>
            ))}
          </div>

          <div className="filter-label product-filter-label"><span>Specific product</span><small>What do you want to buy?</small></div>
          <div className="category-row product-filter-row" aria-label="Filter by specific product">
            <button type="button" className={product === "All" ? "active" : ""} onClick={() => { setProduct("All"); setAskFarmIds(null); }} aria-pressed={product === "All"}>All products</button>
            {productGuides.map((guide) => (
              <button key={guide.id} type="button" className={product === guide.id ? "active" : ""} onClick={() => { setProduct(guide.id); setAskFarmIds(null); }} aria-pressed={product === guide.id}>
                <i style={{ background: guide.color }} />{guide.shortLabel} <small>{productCounts[guide.id]}</small>
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
            {askFarmIds && <span className="question-filter">Question results: {askFarmIds.length}</span>}
            {(query || category !== "All" || product !== "All" || state !== "ALL" || services.length > 0 || askFarmIds) && <button className="clear-filters" type="button" onClick={clearFilters}>Clear all</button>}
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
                    <div className="card-contact">
                        <button type="button" onClick={() => openProfile(farm.id)}>Full profile →</button>
                        {farm.website && <a href={farm.website} target="_blank" rel="noreferrer">Website ↗</a>}
                        {farm.contact && <span>{farm.contact}</span>}
                    </div>
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
            <div className="map-panel" ref={mapShellRef}>
              {mapActivated ? (
                <MapCanvas visibleFarms={filteredFarms} selectedFarm={selectedFarm} onSelect={selectFarm} onOpenProfile={openProfile} />
              ) : (
                <div className="map-wrap map-placeholder" role="status">
                  <span />
                  <strong>Map waits until you need it.</strong>
                  <small>Search and browse the farm list while geography stays off the critical path.</small>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="updates-section" id="updates" aria-labelledby="updates-title">
          <div className="updates-heading">
            <p className="section-number">04 / Latest directory update</p>
            <h2 id="updates-title">What changed,<br />and what comes next.</h2>
            <p>July 2026 · The canonical workbook now contains 299 one-row-per-entity listings. Four duplicate groups were evidence-reviewed, merged, and retained in the source log.</p>
          </div>
          <div className="update-ledger">
            <article className="update-lead">
              <span>Coverage expanded</span>
              <strong>299</strong>
              <h3>unique farms across two states</h3>
              <p>The directory now spans all Louisiana regions plus South, Central, and North Mississippi, with Louisiana remaining the densest starting market.</p>
            </article>
            <article><span>Map confidence</span><strong>{cityLevelCount}</strong><h3>city-level locations</h3><p>The remaining {farms.length - cityLevelCount} pins represent a parish, area, metro, or regional center until a farm-gate address is confirmed.</p></article>
            <article><span>How to buy</span><strong>{marketCount}</strong><h3>farms at markets</h3><p>{csaCount} records mention CSA shares. Pickup, delivery, and ordering filters make those sales paths easier to compare.</p></article>
            <article><span>Digital gap</span><strong>{websiteGap}</strong><h3>without a confirmed website</h3><p>For many listings, FarmFinder is the clearest searchable description available outside social media or a market roster.</p></article>
          </div>
          <div className="update-notes">
            <div><span>Now live</span><p>Detailed profiles, specific product browsing, combined category filters, directory-grounded questions, and clearer location confidence.</p></div>
            <div><span>Being improved</span><p>Farm-gate addresses, weekly availability, market schedules, certifications, seasonal inventory, and farmer-verified stories.</p></div>
            <div><span>How to help</span><p>Farmers and shoppers will be able to submit corrections, richer descriptions, product updates, or missing listings through a dedicated FarmFinder form.</p><a href="#about">Submission details ↓</a></div>
          </div>
        </section>

        <section className="about" id="about" aria-labelledby="about-title">
          <p className="section-number">05 / About this field guide</p>
          <div className="about-grid">
            <h2 id="about-title">A living directory,<br />built from the ground up.</h2>
            <div>
              <p>FarmFinder is cataloging independent farms across the continental United States so buying local takes less detective work. Louisiana and Mississippi are the first coverage area, built from public directories, farmers-market rosters, extension resources, and direct research.</p>
              <p>Some pins represent a city or regional center rather than a farm gate. Always contact a farm before visiting; availability, hours, and harvests change with the season.</p>
            </div>
            <aside>
              <strong>Grow the map</strong>
              <p>Own a farm, know one we missed, or see a detail that needs fixing?</p>
              <span>A dedicated FarmFinder submission form is planned.</span>
            </aside>
          </div>
        </section>
      </main>

      <footer>
        <a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>FarmFinder<small>Find food closer to home.</small></span></a>
        <p>Louisiana → Mississippi → the continental U.S., one region at a time.</p>
        <div><a href="#ask">Ask</a><a href="#products">Products</a><a href="#discover">Explore</a><a href="#about">About</a></div>
        <small>© 2026 FarmFinder</small>
      </footer>
      <nav className="mobile-dock" aria-label="Mobile navigation">
        <a href="#ask">Ask</a>
        <a href="#products">Harvest</a>
        <a href="#discover">Explore</a>
      </nav>
      {profileFarm && <FarmProfileDialog farm={profileFarm} onClose={closeProfile} onShowMap={showProfileOnMap} onOpenFarm={openProfile} />}
    </div>
  );
}
