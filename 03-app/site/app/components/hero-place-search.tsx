"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { PlaceSearchResponse, PlaceSuggestion } from "../lib/discovery-contract";
import { choiceCaption, choosePlace, fallbackPlaceQueries } from "../lib/place-match";

type Status =
  | { tone: "idle" }
  | { tone: "working" }
  | { tone: "choose"; caption: string }
  | { tone: "missing"; query: string; suggestions: PlaceSuggestion[] };

async function lookup(term: string, limit: number, signal?: AbortSignal): Promise<PlaceSuggestion[]> {
  const response = await fetch(`/v1/places?q=${encodeURIComponent(term)}&limit=${limit}`, { signal });
  if (!response.ok) throw new Error(`places ${response.status}`);
  return (await response.json() as PlaceSearchResponse).items;
}

/**
 * The hero's city search.
 *
 * It used to be a bare GET form: a spelling the place lookup did not know
 * produced no result and no message, and even a good one reloaded the page at
 * the top with the explorer 3,600px below. Now it suggests as you type, goes
 * straight to an unambiguous city, asks when a city exists in several states,
 * and says so out loud when nothing matches.
 *
 * It hands off to the explorer through the URL the explorer already reads
 * (`?near=…#discover`) plus a `popstate`, which is the event the explorer
 * already listens for on back/forward. That keeps one way in, not two.
 *
 * Without JavaScript the form still submits `?place=` to `/#discover`, and the
 * explorer resolves it with the same tolerant matching.
 */
export default function HeroPlaceSearch() {
  const listId = useId();
  const statusId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [status, setStatus] = useState<Status>({ tone: "idle" });

  // Type-ahead. Debounced, and each keystroke aborts the request before it so
  // a slow early response can never overwrite a later one.
  useEffect(() => {
    const term = value.trim();
    if (term.length < 2) {
      const clear = window.setTimeout(() => { setSuggestions([]); setOpen(false); }, 0);
      return () => window.clearTimeout(clear);
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const items = await lookup(term, 6, controller.signal);
        setSuggestions(items);
        setActive(-1);
        setOpen(items.length > 0 && document.activeElement === inputRef.current);
      } catch {
        /* aborted or offline — the submit path reports real failures */
      }
    }, 150);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [value]);

  function go(place: PlaceSuggestion) {
    setOpen(false);
    setValue(place.label);
    setStatus({ tone: "idle" });
    const url = `/?near=${encodeURIComponent(place.slug)}&radiusMiles=50&sort=distance#discover`;
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const section = document.getElementById("discover");
    section?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    // Move focus with the scroll, so keyboard and screen-reader users land where
    // sighted users are now looking instead of back at the hero.
    const heading = document.getElementById("discover-title");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (open && active >= 0 && suggestions[active]) {
      go(suggestions[active]);
      return;
    }
    const query = value.trim();
    if (!query) {
      inputRef.current?.focus();
      return;
    }

    setStatus({ tone: "working" });
    try {
      const matches = await lookup(query, 8);
      const decision = choosePlace(query, matches);
      if (decision.kind === "go") {
        go(decision.place);
        return;
      }
      if (decision.kind === "choose") {
        setSuggestions(decision.places);
        setActive(0);
        setOpen(true);
        setStatus({ tone: "choose", caption: choiceCaption(query, decision.places) });
        inputRef.current?.focus();
        return;
      }

      // Nothing matched. Look for what they probably meant before giving up.
      let near: PlaceSuggestion[] = [];
      for (const fallback of fallbackPlaceQueries(query)) {
        near = await lookup(fallback, 4);
        if (near.length) break;
      }
      setOpen(false);
      setStatus({ tone: "missing", query, suggestions: near });
      inputRef.current?.focus();
    } catch {
      setStatus({ tone: "missing", query, suggestions: [] });
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActive((current) => (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp" && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActive((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
    }
  }

  const expanded = open && suggestions.length > 0;
  const activeId = expanded && active >= 0 ? `${listId}-option-${active}` : undefined;

  return (
    <form className="hero-location" action="/#discover" method="get" onSubmit={submit} role="search" aria-label="Find farms near a city">
      <label htmlFor="hero-near">City or town</label>
      <div className="hero-field">
        <input
          ref={inputRef}
          id="hero-near"
          name="place"
          value={value}
          placeholder="Try Madison, WI"
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-activedescendant={activeId}
          aria-describedby={statusId}
          aria-invalid={status.tone === "missing" || undefined}
          onChange={(event) => {
            setValue(event.target.value);
            if (status.tone !== "idle" && status.tone !== "working") setStatus({ tone: "idle" });
          }}
          onKeyDown={onKeyDown}
          onFocus={() => { if (suggestions.length) setOpen(true); }}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        />
        <button type="submit" disabled={status.tone === "working"}>
          {status.tone === "working" ? "Finding…" : "Find nearby farms →"}
        </button>
        <div className="hero-suggestions" hidden={!expanded}>
          {status.tone === "choose" ? (
            // Visible prompt for sighted users; the status region below says
            // the same thing to assistive tech without being covered by this.
            <p className="hero-suggestions-caption" aria-hidden="true">
              {status.caption} Pick the one you mean.
            </p>
          ) : null}
          <ul id={listId} role="listbox" aria-label="Matching cities">
            {suggestions.map((place, index) => (
              <li
                key={place.slug}
                id={`${listId}-option-${index}`}
                role="option"
                aria-selected={index === active}
                className={index === active ? "active" : ""}
                // Keep focus in the field so the list does not close under the click.
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => go(place)}
              >
                <span>{place.label}</span>
                <small>{place.farmCount.toLocaleString()} {place.farmCount === 1 ? "farm" : "farms"}</small>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div id={statusId} className={`hero-status hero-status-${status.tone}`} role="status" aria-live="polite">
        {status.tone === "choose" ? (
          // Covered by the open list, so announced rather than shown.
          <p className="sr-only">{status.caption} Use the arrow keys to pick the one you mean.</p>
        ) : status.tone === "missing" ? (
          <>
            <p><strong>No city matches “{status.query}”.</strong> {status.suggestions.length ? "Did you mean:" : "Try a city and state, like Madison, WI."}</p>
            {status.suggestions.length ? (
              <div className="hero-did-you-mean">
                {status.suggestions.map((place) => (
                  <button type="button" key={place.slug} onClick={() => go(place)}>{place.label}</button>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </form>
  );
}
