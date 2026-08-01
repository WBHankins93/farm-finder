"use client";

import { useEffect, useRef } from "react";
import { serviceFilters } from "../lib/directory-config";
import { categoryColors, type Farm } from "../lib/farms";
import { Mark, markForCategory } from "../lib/marks";

type Props = {
  farm: Farm;
  onClose: () => void;
  onShowMap: () => void;
};

function farmSummary(farm: Farm) {
  const selling = farm.marketPresence
    ? `Current sales information lists ${farm.marketPresence.toLocaleLowerCase()}.`
    : "A confirmed sales schedule is not listed yet.";
  return `${farm.name} is a ${farm.category.toLocaleLowerCase()} producer near ${farm.city}, ${farm.state}. Known products include ${farm.productsText}. ${selling}`;
}

export default function FarmProfileDialog({ farm, onClose, onShowMap }: Props) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    closeRef.current?.focus();
    document.body.classList.add("dialog-open");

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter((element) => !element.hasAttribute("disabled"));
      if (focusable.length === 0) return;
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

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.classList.remove("dialog-open");
      previousFocus?.focus();
    };
  }, [onClose]);

  const digits = farm.contact.replace(/\D/g, "");
  const contactHref = farm.contact.includes("@") ? `mailto:${farm.contact}` : digits.length >= 10 ? `tel:${digits}` : "";

  return (
    <div className="profile-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <article ref={dialogRef} className="profile-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-title">
        <header className="profile-header">
          <div>
            <p className="profile-kicker"><Mark name={markForCategory(farm.category)} style={{ color: categoryColors[farm.category] }} />{farm.category} · Farm profile</p>
            <h2 id="profile-title">{farm.name}</h2>
            <p>{farm.city}, {farm.state} · {farm.parish || "Area not listed"}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Close farm profile">×</button>
        </header>

        <div className="profile-body">
          <section className="profile-summary"><span>Directory summary</span><p>{farmSummary(farm)}</p></section>
          <div className="profile-columns">
            <div className="profile-main">
              <section className="profile-section"><h3>Products & specialties</h3><p>{farm.productsText || "Products have not been listed yet."}</p><div className="profile-product-tags">{farm.products.map((product) => <span key={product}>{product}</span>)}</div></section>
              <section className="profile-section"><h3>How to buy</h3><p>{farm.marketPresence || "A confirmed sales schedule has not been added yet."}</p><div className="profile-service-grid">{serviceFilters.map(({ key, label }) => <div className={farm[key] ? "available" : "unknown"} key={key}><i>{farm[key] ? "✓" : "—"}</i><span>{label}</span><small>{farm[key] ? "Listed" : "Not confirmed"}</small></div>)}</div></section>
              <section className="profile-section"><h3>Directory notes</h3><p>{farm.notes || "No additional field notes have been recorded yet."}</p></section>
            </div>
            <aside className="profile-sidebar">
              <div className="profile-actions"><button type="button" onClick={onShowMap}>Show on map →</button>{farm.website ? <a href={farm.website} target="_blank" rel="noreferrer">Visit website ↗</a> : null}{contactHref ? <a href={contactHref}>Contact farm ↗</a> : null}</div>
              <div className="profile-fact"><span>Location confidence</span><strong>{farm.geoPrecision === "point" ? "Public point" : farm.geoPrecision === "city" ? "City-level approximation" : "Approximate area"}</strong><small>Confirm before visiting</small></div>
              <div className="profile-fact"><span>Directory source</span><strong>{farm.source || "Source retained internally"}</strong></div>
            </aside>
          </div>
        </div>
      </article>
    </div>
  );
}
