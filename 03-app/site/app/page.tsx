import type { CSSProperties } from "react";
import AskDirectory from "./components/ask-directory";
import DiscoveryWorkspace from "./components/discovery-workspace";
import FarmTicker from "./components/farm-ticker";
import HeroPlaceSearch from "./components/hero-place-search";
import stats from "./data/directory-stats.generated.json";
import { productGuides } from "./lib/directory-config";
import { tickerFarms } from "./lib/discovery-server";
import { BrandMark, Mark, markForProduct } from "./lib/marks";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  // The national explorer is the product. `EXPLORER_LEGACY=true` is the
  // rollback switch to the superseded 299-row workbook explorer; it is never
  // set in a deployed build (its 45 MB client feed exceeds the asset limit).
  // Dynamic so the rollback explorer and its client bundle stay out of a
  // default build entirely, rather than riding along as dead weight.
  if (process.env.EXPLORER_LEGACY === "true") {
    const { default: LegacyHome } = await import("./legacy-page");
    return <LegacyHome />;
  }

  // Server-rendered so the band is populated at first paint: a ticker that
  // arrives empty and fills in later is worse than no ticker. `near` comes
  // from the URL the hero search writes, so a shared link stays personalised.
  const params = await searchParams;
  const near = typeof params.near === "string" ? params.near : "";
  const ticker = await tickerFarms(near);

  return (
    <div className="site-shell">
      <a className="skip-link" href="#discover">Skip to farm search</a>
      <header className="topbar">
        <a className="brand" href="#top"><BrandMark className="brand-mark" /><span>FarmFinder<small>U.S. farm field guide</small></span></a>
        <nav aria-label="Primary navigation"><a href="#ask">Ask</a><a href="#products">Browse</a><a href="#discover">Explore</a><a className="farmer-link" href="#discover">Find farms</a></nav>
      </header>

      <main id="top">
        <section className="hero hero-nearby" aria-labelledby="hero-title">
          <div className="hero-copy-col">
            <p className="hero-kicker">Independent farms across the United States</p>
            <h1 id="hero-title">Find the farms<br /><em>behind your <span>food.</span></em></h1>
            <p className="hero-copy">Start with your city. See nearby farms, what they grow or raise, and the confirmed way to buy from each one.</p>
            <HeroPlaceSearch />
            {/* Three steps, because the product does not sell anything and a
                visitor who expects a checkout will bounce at the farm's phone
                number. Saying so up front is cheaper than disappointing them. */}
            <ol className="hero-steps">
              <li><Mark name="pin" aria-hidden="true" /><span><strong>Enter your city</strong>We search the directory around it.</span></li>
              <li><Mark name="basket" aria-hidden="true" /><span><strong>See what they grow</strong>Products and ways to buy, farm by farm.</span></li>
              <li><Mark name="market" aria-hidden="true" /><span><strong>Contact the farm</strong>Confirm hours and availability yourself.</span></li>
            </ol>
          </div>
          <div className="hero-photo" role="img" aria-label="Shoppers at an outdoor farmers market browsing crates of vegetables">
            <span className="hero-photo-credit">USDA farmers market · public domain</span>
          </div>
          <FarmTicker farms={ticker.farms} place={ticker.label} />
          <div className="hero-stats">
            <div><strong>{stats.total.toLocaleString()}</strong><span>farms in the directory</span></div>
            <div><strong>{stats.states}</strong><span>states and districts</span></div>
            <div><strong>{stats.mappable.toLocaleString()}</strong><span>public map locations</span></div>
            <p>Locations range from farm-gate points to city-level approximations. Confirm before visiting.</p>
          </div>
        </section>

        <section className="ask-section" id="ask" aria-labelledby="ask-title">
          <div className="ask-heading"><p className="section-number">Ask the field guide</p><h2 id="ask-title">Start with a practical question.</h2><p>Search listing descriptions for a food or farm, then refine the results by location.</p></div>
          <AskDirectory />
        </section>

        <section className="products-section" id="products" aria-labelledby="products-title">
          <div className="products-heading"><div><p className="section-number">Browse the harvest</p><h2 id="products-title">Start with what<br /><em>you want to eat.</em></h2></div><p>Counts reflect current directory descriptions, not live inventory.</p></div>
          <div className="product-guide-grid product-guide-grid-compact">
            {productGuides.slice(0, 8).map((guide) => (
              <article className="product-guide-card" key={guide.id} style={{ "--product-color": guide.color, "--tile-img": `url(/images/products/${guide.id}.webp)` } as CSSProperties}>
                <div className="product-card-media">
                  {markForProduct(guide.id) ? <span className="product-card-badge" aria-hidden="true"><Mark name={markForProduct(guide.id)!} className="mark product-card-glyph" /></span> : null}
                  <strong className="product-card-count">{stats.products[guide.id as keyof typeof stats.products].toLocaleString()}<span>farms</span></strong>
                </div>
                <h3>{guide.label}</h3><p>{guide.description}</p>
                <a href={`/?product=${guide.id}#discover`}>Browse matching farms <span aria-hidden="true">→</span></a>
              </article>
            ))}
          </div>
        </section>

        <section className="field-story" aria-labelledby="field-story-title">
          <div className="field-story-photo" role="img" aria-label="A farm harvest of radishes, kale, and lettuce on a wooden table"><span>Fresh farm produce · USDA ARS (public domain)</span></div>
          <div className="field-story-copy"><p className="section-number">A useful field guide, not a promise of live stock</p><h2 id="field-story-title">Find the farm.<br /><em>Confirm the trip.</em></h2><p>Compare products and ways to buy, then contact the farm for this week’s availability, hours, and pickup details.</p><a href="#discover">Search farms near you →</a></div>
        </section>

        <DiscoveryWorkspace />

        <section className="updates-section" id="updates" aria-labelledby="updates-title">
          <div className="updates-heading"><p className="section-number">Directory field notes</p><h2 id="updates-title">What the map<br />can tell you.</h2><p>{stats.updatedLabel} · Every listing keeps its source so details can be checked and corrected.</p></div>
          <div className="update-ledger">
            <article className="update-lead"><span>Coverage</span><strong>{stats.total.toLocaleString()}</strong><h3>farm and producer records</h3><p>Nearby search now narrows the national directory before it reaches your browser.</p></article>
            <article><span>Map confidence</span><strong>{stats.mappable.toLocaleString()}</strong><h3>public map locations</h3><p>Approximate points stay labeled honestly and never imply a private farm-gate address.</p></article>
            <article><span>How to buy</span><strong>{stats.services.onFarm.toLocaleString()}</strong><h3>on-farm sales listings</h3><p>Compare pickup, farmers market, CSA, delivery, and online-order paths.</p></article>
            <article><span>Contact paths</span><strong>{stats.withoutWebsite.toLocaleString()}</strong><h3>without a confirmed website</h3><p>Some farms rely on market rosters, directories, phones, or social pages.</p></article>
          </div>
        </section>

        <section className="about" id="about" aria-labelledby="about-title"><p className="section-number">About this field guide</p><div className="about-grid"><h2 id="about-title">A living directory,<br />built from the ground up.</h2><div><p>FarmFinder catalogs independent farms so buying local takes less detective work.</p><p>Some pins represent a city or county center rather than a farm gate. Always contact a farm before visiting.</p></div><aside><strong>Grow the map</strong><p>Own a farm, know one we missed, or see a detail that needs fixing?</p><span>Correction and submission tools are in progress.</span></aside></div></section>
      </main>

      <footer><a className="brand footer-brand" href="#top"><BrandMark className="brand-mark" /><span>FarmFinder<small>Find food closer to home.</small></span></a><p>Source-backed farm discovery, one region at a time.</p><div><a href="#ask">Ask</a><a href="#products">Products</a><a href="#discover">Explore</a><a href="#about">About</a></div><small>© 2026 FarmFinder</small></footer>
      <nav className="mobile-dock" aria-label="Mobile navigation"><a href="#ask">Ask</a><a href="#products">Browse</a><a href="#discover">Search</a></nav>
    </div>
  );
}
