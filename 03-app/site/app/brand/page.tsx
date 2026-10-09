import type { CSSProperties } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { brandPalette, brandRadii, brandType, contrastRatio } from "../lib/brand";
import { categoryColors } from "../lib/farms";
import { productGuides, serviceFilters } from "../lib/directory-config";
import { BrandMark, Mark, markForCategory, markForProduct, markForService } from "../lib/marks";

/**
 * The brand sheet.
 *
 * A palette only produces consistency if people can see it without reading
 * CSS, so this page renders the real tokens, the real marks and the real
 * components — not a picture of them. If a swatch here looks wrong, the
 * product is wrong, because there is no second copy of these values.
 *
 * Not indexed: it is a working reference for whoever is building, not a page
 * anyone should land on from a search for local farms.
 */
export const metadata: Metadata = {
  title: "FarmFinder brand sheet",
  description: "Market Stand palette, type, marks and components.",
  robots: { index: false, follow: false },
};

const surfaces = [
  { name: "paper", value: "#fbf6ec" },
  { name: "cream", value: "#fffdf7" },
];

export default function BrandSheet() {
  return (
    <div className="site-shell brand-sheet">
      <header className="topbar">
        <Link className="brand" href="/"><BrandMark className="brand-mark" /><span>FarmFinder<small>Brand sheet</small></span></Link>
        <nav aria-label="Primary navigation"><Link href="/">Back to the directory</Link></nav>
      </header>

      <main id="top">
        <section className="brand-intro">
          <p className="section-number">Market Stand</p>
          <h1>One palette,<br /><em>every page.</em></h1>
          <p>
            These are the live tokens from <code>app/globals.css</code>, read through{" "}
            <code>app/lib/brand.ts</code>. A test fails the build if the two drift apart, or if a colour
            meant for text stops clearing 4.5:1 on the surfaces it is used on.
          </p>
        </section>

        {brandPalette.map((group) => (
          <section className="brand-section" key={group.title}>
            <div className="brand-section-head">
              <h2>{group.title}</h2>
              <p>{group.note}</p>
            </div>
            <div className="brand-swatches">
              {group.tokens.map((token) => (
                <article className="brand-swatch" key={token.name}>
                  <div className="brand-chip" style={{ background: token.value }} />
                  <h3>{token.label}</h3>
                  <code>--{token.name}</code>
                  <code className="brand-hex">{token.value}</code>
                  <p>{token.role}</p>
                  <ul className="brand-contrast">
                    {surfaces.map((surface) => {
                      const ratio = contrastRatio(token.value, surface.value);
                      const required = token.onSurfaces.includes(surface.name);
                      return (
                        <li key={surface.name} className={required ? (ratio >= 4.5 ? "pass" : "fail") : ""}>
                          <span>on {surface.name}</span>
                          <strong>{ratio.toFixed(2)}:1</strong>
                          {required ? <small>text</small> : null}
                        </li>
                      );
                    })}
                  </ul>
                </article>
              ))}
            </div>
          </section>
        ))}

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>Type</h2>
            <p>Two faces, weight-driven hierarchy. Display is for names and numbers; interface carries everything you operate.</p>
          </div>
          <div className="brand-type">
            {brandType.map((entry) => (
              <article key={entry.role}>
                <span>{entry.role} · {entry.face}</span>
                <p className={entry.role === "Display" ? "brand-type-display" : "brand-type-ui"}>{entry.sample}</p>
                <small>{entry.usage}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>Shape</h2>
            <p>Crates and awnings. Radius is a scale, not a free choice.</p>
          </div>
          <div className="brand-radii">
            {brandRadii.map((radius) => (
              <article key={radius.name}>
                <div style={{ borderRadius: radius.value }} />
                <code>--{radius.name}</code>
                <small>{radius.value} · {radius.role}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>The mark</h2>
            <p>An awning inside a map pin. Two flat colours, no stroke, legible at favicon size.</p>
          </div>
          <div className="brand-marks-row">
            {[64, 40, 28, 18].map((size) => <BrandMark key={size} size={size} />)}
          </div>
        </section>

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>Field marks</h2>
            <p>Every category, product and way to buy has one. A mark never travels without its label.</p>
          </div>
          <div className="brand-marks">
            {Object.keys(categoryColors).map((category) => (
              <span key={category} style={{ "--mark-color": categoryColors[category] } as CSSProperties}>
                <Mark name={markForCategory(category)} />{category}
              </span>
            ))}
          </div>
          <div className="brand-marks">
            {productGuides.map((guide) => {
              const mark = markForProduct(guide.id);
              return mark ? (
                <span key={guide.id} style={{ "--mark-color": guide.color } as CSSProperties}>
                  <Mark name={mark} />{guide.shortLabel}
                </span>
              ) : null;
            })}
          </div>
          <div className="brand-marks">
            {serviceFilters.map(({ key, label }) => {
              const mark = markForService(key);
              return mark ? (
                <span key={key} style={{ "--mark-color": "var(--green)" } as CSSProperties}>
                  <Mark name={mark} />{label}
                </span>
              ) : null;
            })}
          </div>
        </section>

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>Components</h2>
            <p>One primary action per surface. Everything else is outlined or quiet.</p>
          </div>
          <div className="brand-components">
            <div className="brand-component">
              <span className="brand-component-label">Primary action</span>
              <button type="button" className="brand-demo-primary">Find nearby farms →</button>
            </div>
            <div className="brand-component">
              <span className="brand-component-label">Filter chip</span>
              <div className="brand-demo-chips">
                <button type="button" className="active">All products</button>
                <button type="button"><Mark name="leaf" />Vegetables</button>
              </div>
            </div>
            <div className="brand-component">
              <span className="brand-component-label">Distance</span>
              <span className="card-heading"><Mark name="heading" style={{ transform: "rotate(135deg)" }} />0.8 mi SE</span>
            </div>
            <div className="brand-component">
              <span className="brand-component-label">Ways to buy</span>
              <ul className="card-services">
                {serviceFilters.slice(0, 3).map(({ key, label }) => {
                  const mark = markForService(key);
                  return mark ? <li key={key} title={label}><Mark name={mark} /></li> : null;
                })}
              </ul>
            </div>
            <div className="brand-component">
              <span className="brand-component-label">Missing data</span>
              <p className="is-missing">Products not listed</p>
            </div>
          </div>
        </section>

        <section className="brand-section">
          <div className="brand-section-head">
            <h2>Imagery</h2>
            <p>Public domain and CC0 only, credited in <code>docs/design/imagery-credits.md</code>. No photograph is ever presented as a listed farm.</p>
          </div>
          <div className="brand-photos">
            {["vegetables", "eggs", "honey", "dairy"].map((id) => (
              <figure key={id}><div style={{ backgroundImage: `url(/images/products/${id}.webp)` }} /><figcaption>{id}.webp</figcaption></figure>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
