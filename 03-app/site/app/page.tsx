import type { CSSProperties } from "react";
import AskDirectory from "./components/ask-directory";
import DiscoveryWorkspace from "./components/discovery-workspace";
import LegacyHome from "./legacy-page";
import stats from "./data/directory-stats.json";
import { productGuides } from "./lib/directory-config";
import { Mark, markForProduct } from "./lib/marks";

export default function Home() {
  if (process.env.EXPLORER_V2 !== "true") return <LegacyHome />;

  return (
    <div className="site-shell">
      <a className="skip-link" href="#discover">Skip to farm search</a>
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>FarmFinder<small>U.S. farm field guide</small></span></a>
        <nav aria-label="Primary navigation"><a href="#ask">Ask</a><a href="#products">Browse</a><a href="#discover">Explore</a><a className="farmer-link" href="#discover">Find farms</a></nav>
      </header>

      <main id="top">
        <section className="hero hero-nearby" aria-labelledby="hero-title">
          <p className="hero-kicker">Independent farms across the United States · Search by place</p>
          <h1 id="hero-title">Find the farms<br /><em>behind your <span>food.</span></em></h1>
          <p className="hero-copy">Start with your city. See nearby farms, what they grow or raise, and the best confirmed way to buy.</p>
          <form className="hero-location" action="/" method="get">
            <label htmlFor="hero-near">City or town</label>
            <div><input id="hero-near" name="place" placeholder="Try Madison, WI" autoComplete="address-level2" /><button type="submit">Find nearby farms →</button></div>
          </form>
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
            {productGuides.slice(0, 8).map((guide, index) => (
              <article className="product-guide-card" key={guide.id} style={{ "--product-color": guide.color, "--tile-img": `url(/images/products/${guide.id}.webp)` } as CSSProperties}>
                <div className="product-card-media" aria-hidden="true">{markForProduct(guide.id) ? <Mark name={markForProduct(guide.id)!} className="mark product-card-glyph" /> : null}</div>
                <div className="product-card-top"><span>{String(index + 1).padStart(2, "0")}</span><strong>{stats.products[guide.id as keyof typeof stats.products].toLocaleString()}</strong></div>
                <h3>{guide.label}</h3><p>{guide.description}</p>
                <a href={`/?product=${guide.id}#discover`}>Browse matching farms →</a>
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

      <footer><a className="brand footer-brand" href="#top"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span><span>FarmFinder<small>Find food closer to home.</small></span></a><p>Source-backed farm discovery, one region at a time.</p><div><a href="#ask">Ask</a><a href="#products">Products</a><a href="#discover">Explore</a><a href="#about">About</a></div><small>© 2026 FarmFinder</small></footer>
      <nav className="mobile-dock" aria-label="Mobile navigation"><a href="#ask">Ask</a><a href="#products">Browse</a><a href="#discover">Search</a></nav>
    </div>
  );
}
