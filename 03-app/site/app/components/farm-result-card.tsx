import type { CSSProperties } from "react";
import { serviceKeys, type FarmSummary, type LatLng, type ServiceKey } from "../lib/discovery-contract";
import { categoryColors } from "../lib/farms";
import { productLabelsForFarm } from "../lib/farm-presentation";
import { Mark, markForCategory, markForService } from "../lib/marks";
import { relativeHeading } from "../lib/nearby";

/** Service key → the words a screen reader and a tooltip get for its icon. */
const serviceNames: Record<ServiceKey, string> = {
  farmersMarket: "Sells at a farmers market",
  onFarm: "Farm pickup",
  csa: "CSA subscription",
  ships: "Delivers or ships",
  onlineStore: "Online store",
};

type FarmResultCardProps = {
  farm: FarmSummary;
  selected: boolean;
  index: number | null;
  origin: LatLng | null;
  onSelect: (id: string) => void;
  onShowMap: (farm: FarmSummary) => void;
  onOpenProfile: (id: string) => void;
  onHover: (farm: FarmSummary | null) => void;
};

/**
 * One result.
 *
 * Dense on purpose. The previous card gave a 25px display name four lines, a
 * pill row, and a separate action strip, so three results filled the panel and
 * most of each card was empty — and 45.8% of the release has no product text,
 * so a lot of that emptiness was a blank space where an answer should be. This
 * version leads with the two things a person is actually comparing (how far,
 * which way) and says so in words when the data is missing.
 *
 * The services are icons rather than text pills because there are up to five of
 * them and their labels ("Market", "Farm pickup", "CSA") are longer than the
 * information they carry. Each keeps a visible-on-focus text label for anyone
 * not reading by shape.
 */
export default function FarmResultCard({ farm, selected, index, origin, onSelect, onShowMap, onOpenProfile, onHover }: FarmResultCardProps) {
  const services = serviceKeys.filter((key) => farm[key]);
  const mapped = farm.geoPrecision !== "ungeocoded";
  const heading = mapped ? relativeHeading(origin, { lat: farm.latitude, lng: farm.longitude }, farm.distanceMiles) : null;
  const products = productLabelsForFarm(farm).slice(0, 3);
  const cityAndState = [farm.city.trim(), farm.state.trim()].filter(Boolean).join(", ");
  const place = cityAndState ? `${cityAndState}${farm.parish.trim() ? ` · ${farm.parish.trim()}` : ""}` : farm.parish.trim() || "Area not listed";
  const color = categoryColors[farm.category] || "#59604c";

  return (
    <article className={`farm-card ${selected ? "selected" : ""}`} onMouseEnter={() => onHover(farm)} onMouseLeave={() => onHover(null)} onFocus={() => onHover(farm)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) onHover(null); }}>
      <button className="farm-card-main" type="button" onClick={() => onSelect(farm.id)} aria-label={`Select ${farm.name}`}>
        {/* A colour-and-mark tile, not a photograph. NN/g's finding on mobile
            list thumbnails is that they only help when they differ from each
            other; the same category stock photo on forty cards is page weight
            with no signal — and it would also imply the photo is this farm. */}
        <span className="card-tile" style={{ "--tile-color": color } as CSSProperties} aria-hidden="true">
          <Mark name={markForCategory(farm.category)} />
        </span>
        <div className="card-body">
          <p className="card-category">
            {farm.category}
            {index !== null ? <span className="card-index">#{index}</span> : null}
          </p>
          <h3>{farm.name}</h3>
          <p className="card-place">
            <Mark name="pin" aria-hidden="true" />
            {/* 1,300-odd published rows carry a state but no city, and
                ", WI" on its own reads as a bug rather than a gap. */}
            <span>{place}</span>
          </p>
          <p className={`card-products ${products.length ? "" : "is-missing"}`}>
            <Mark name="basket" aria-hidden="true" />
            {products.length ? products.join(" · ") : "Products not listed"}
          </p>
        </div>
        <div className="card-aside">
          {/* A mapped farm with no heading just has no search origin to be
              relative to (browsing a state or a map area); that is not a
              missing location, so it must not say "Not mapped". */}
          {heading ? (
            <span className="card-heading">
              {/* The needle points where the farm actually is. Rotating one
                  glyph is the difference between "12 mi" and "12 mi, that
                  way" — and it costs nothing to draw. */}
              <Mark name="heading" aria-hidden="true" style={heading.bearing === null ? undefined : { transform: `rotate(${Math.round(heading.bearing)}deg)` }} />
              {heading.label}
            </span>
          ) : !mapped ? (
            <span className="card-heading is-missing"><Mark name="approximate" aria-hidden="true" />Not mapped</span>
          ) : null}
          {mapped && farm.geoPrecision !== "point" ? <span className="card-precision">Approximate</span> : null}
        </div>
      </button>
      <div className="card-contact">
        <ul className="card-services" aria-label={services.length ? "Ways to buy" : undefined}>
          {services.map((key) => {
            const mark = markForService(key);
            return mark ? <li key={key} title={serviceNames[key]}><Mark name={mark} aria-hidden="true" /><span className="sr-only">{serviceNames[key]}</span></li> : null;
          })}
          {services.length === 0 ? <li className="is-missing">No way to buy listed</li> : null}
        </ul>
        <span className="card-links">
          <button type="button" onClick={() => onOpenProfile(farm.id)}>Profile</button>
          {mapped ? <button type="button" onClick={() => onShowMap(farm)}>Map</button> : null}
          {farm.website ? <a href={farm.website} target="_blank" rel="noreferrer">Site<Mark name="link" aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span></a> : null}
        </span>
      </div>
    </article>
  );
}
