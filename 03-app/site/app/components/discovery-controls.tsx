"use client";

import { useId, useState, type KeyboardEvent, type RefObject } from "react";
import type { PlaceSuggestion } from "../lib/discovery-contract";

type SearchRadius = 25 | 50 | 100;

export interface DiscoveryControlsModel {
  placeInput: string;
  selectedPlaceSlug: string | null;
  suggestions: PlaceSuggestion[];
  suggestionsOpen: boolean;
  locating: boolean;
  query: string;
  radius: SearchRadius;
  radiusEnabled: boolean;
  locationMessage: string;
  searchEnabled: boolean;
}

export interface DiscoveryControlsActions {
  onPlaceInputChange: (value: string) => void;
  onPlaceInputFocus: () => void;
  onDismissSuggestions: () => void;
  onChoosePlace: (place: PlaceSuggestion) => void;
  onLocate: () => void;
  onQueryChange: (value: string) => void;
  onClearQuery: () => void;
  onRadiusChange: (radius: SearchRadius) => void;
  onBrowseNationwide: () => void;
  onStartOver: () => void;
}

interface DiscoveryControlsProps {
  inputRef: RefObject<HTMLInputElement | null>;
  model: DiscoveryControlsModel;
  actions: DiscoveryControlsActions;
}

export default function DiscoveryControls({ inputRef, model, actions }: DiscoveryControlsProps) {
  const suggestionsId = useId();
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const suggestionsExpanded = model.suggestionsOpen && model.suggestions.length > 0;
  const activeSuggestionId = suggestionsExpanded && activeSuggestion >= 0
    ? `${suggestionsId}-option-${activeSuggestion}`
    : undefined;

  function handlePlaceKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && model.suggestions.length) {
      event.preventDefault();
      actions.onPlaceInputFocus();
      setActiveSuggestion((current) => (current + 1) % model.suggestions.length);
    } else if (event.key === "ArrowUp" && model.suggestions.length) {
      event.preventDefault();
      actions.onPlaceInputFocus();
      setActiveSuggestion((current) => current <= 0 ? model.suggestions.length - 1 : current - 1);
    } else if (event.key === "Enter" && suggestionsExpanded && activeSuggestion >= 0) {
      event.preventDefault();
      actions.onChoosePlace(model.suggestions[activeSuggestion]);
      setActiveSuggestion(-1);
    } else if (event.key === "Escape" && suggestionsExpanded) {
      event.preventDefault();
      actions.onDismissSuggestions();
      setActiveSuggestion(-1);
    }
  }

  return (
    <>
      <div className="discovery-controls">
        <div className="location-control">
          <label htmlFor="near-place">City or town</label>
          <div className="location-input-row">
            <input
              ref={inputRef}
              id="near-place"
              value={model.placeInput}
              onChange={(event) => {
                setActiveSuggestion(-1);
                actions.onPlaceInputChange(event.target.value);
              }}
              onFocus={() => model.suggestions.length && actions.onPlaceInputFocus()}
              onBlur={() => window.setTimeout(actions.onDismissSuggestions, 120)}
              onKeyDown={handlePlaceKeyDown}
              placeholder="Madison, WI"
              autoComplete="off"
              role="combobox"
              aria-autocomplete="list"
              aria-controls={suggestionsExpanded ? suggestionsId : undefined}
              aria-expanded={suggestionsExpanded}
              aria-activedescendant={activeSuggestionId}
            />
            <button type="button" onClick={actions.onLocate} disabled={model.locating}>
              {model.locating ? "Finding you…" : "Use my location"}
            </button>
          </div>
          {suggestionsExpanded ? (
            <div id={suggestionsId} className="place-suggestions" role="listbox" aria-label="Place suggestions">
              {model.suggestions.map((suggestion, index) => (
                <button
                  id={`${suggestionsId}-option-${index}`}
                  type="button"
                  role="option"
                  aria-selected={activeSuggestion === index || model.selectedPlaceSlug === suggestion.slug}
                  tabIndex={-1}
                  key={suggestion.slug}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveSuggestion(index)}
                  onClick={() => {
                    actions.onChoosePlace(suggestion);
                    setActiveSuggestion(-1);
                  }}
                >
                  <span>{suggestion.label}</span>
                  <small>{suggestion.farmCount.toLocaleString()} directory records</small>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <label className="directory-query">
          <span>Farm or food</span>
          <div>
            <input value={model.query} onChange={(event) => actions.onQueryChange(event.target.value)} placeholder="Eggs, tomatoes, farm name…" type="search" />
            {model.query ? <button type="button" onClick={actions.onClearQuery} aria-label="Clear farm search">×</button> : null}
          </div>
        </label>

        <div className="radius-control" role="group" aria-label="Search radius">
          <span>Field boundary</span>
          <div>
            {([25, 50, 100] as const).map((miles) => (
              <button
                type="button"
                key={miles}
                className={model.radius === miles ? "active" : ""}
                aria-pressed={model.radius === miles}
                disabled={!model.radiusEnabled}
                onClick={() => actions.onRadiusChange(miles)}
              >
                {miles} mi
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="location-status">
        <span role="status">{model.locationMessage || "Choose a city to begin nearby search."}</span>
        {!model.searchEnabled ? (
          <button type="button" onClick={actions.onBrowseNationwide}>Browse all farms instead</button>
        ) : (
          <button type="button" onClick={actions.onStartOver}>Start over</button>
        )}
      </div>
    </>
  );
}
