"use client";

import { useEffect, useRef, useState } from "react";
import type { TickerFarm } from "../lib/discovery-server";

/**
 * The hero ticker: a slow band of farm names and places under the search.
 *
 * It exists to make 68,618 records feel like a place full of farms rather than
 * a number, so it shows the two things that do that — a name and where it is —
 * and nothing else.
 *
 * How the motion works: the list is rendered twice and the track translates by
 * exactly half its width, so the loop is seamless with no JavaScript per frame.
 * The animation runs on `transform` only, which keeps it on the compositor, and
 * it pauses on hover and on keyboard focus so nobody has to chase a moving
 * target. Under `prefers-reduced-motion: reduce` the animation is off entirely
 * and the band becomes an ordinary horizontal scroller — the farms are still
 * there, they just stop moving.
 *
 * The second copy is `aria-hidden`: a screen reader should hear the roster
 * once, not twice.
 */
export default function FarmTicker({ farms, place }: { farms: TickerFarm[]; place: string }) {
  const [roster, setRoster] = useState(farms);
  const [label, setLabel] = useState(place);
  const requestedRef = useRef("");

  // Personalisation. The server renders a national spread (or the farms around
  // a `?near=` place when the URL already carries one). Once the visitor picks
  // a city, or shares a location, the explorer writes it to the URL — so the
  // ticker follows the same signal rather than asking for permission itself.
  useEffect(() => {
    function sync() {
      const params = new URLSearchParams(window.location.search);
      const near = params.get("near") ?? "";
      const lat = params.get("lat");
      const lng = params.get("lng");
      const key = near || (lat && lng ? `${lat},${lng}` : "");
      if (!key || key === requestedRef.current) return;
      requestedRef.current = key;

      const query = new URLSearchParams({ radiusMiles: "50", sort: "distance", limit: "42" });
      if (near) query.set("near", near);
      if (!near && lat && lng) { query.set("lat", lat); query.set("lng", lng); }

      fetch(`/v1/farms?${query}`)
        .then((response) => (response.ok ? (response.json() as Promise<{ items?: TickerFarm[]; scope?: { label?: string } }>) : null))
        .then((data) => {
          const items = (data?.items ?? []).filter((farm) => farm.name && farm.state);
          // Below a handful the band would visibly repeat itself; the national
          // roster is better scenery than six farms on a loop.
          if (items.length < 6) return;
          setRoster(items.map((farm) => ({ id: farm.id, name: farm.name, city: farm.city, state: farm.state })));
          setLabel(data?.scope?.label ?? "");
        })
        .catch(() => {
          /* Scenery. A failed fetch leaves the national roster in place. */
        });
    }

    sync();
    window.addEventListener("popstate", sync);
    // The explorer rewrites the URL with replaceState as filters change, which
    // fires no event, so the ticker checks back rather than staying stale.
    const poll = window.setInterval(sync, 2500);
    return () => {
      window.removeEventListener("popstate", sync);
      window.clearInterval(poll);
    };
  }, []);

  if (roster.length < 6) return null;

  const entries = roster.map((farm) => (
    <li key={farm.id}>
      <strong>{farm.name}</strong>
      <span>{[farm.city, farm.state].filter(Boolean).join(", ")}</span>
    </li>
  ));

  return (
    <div className="farm-ticker" role="region" aria-label={label ? `Farms near ${label}` : "Farms across the directory"}>
      <p className="farm-ticker-label">
        <span className="farm-ticker-dot" aria-hidden="true" />
        {label ? `Near ${label}` : "In the directory"}
      </p>
      <div className="farm-ticker-viewport">
        <div className="farm-ticker-track">
          <ul>{entries}</ul>
          <ul aria-hidden="true">{entries}</ul>
        </div>
      </div>
    </div>
  );
}
