"use client";

import { FormEvent, useState } from "react";
import type { FarmSearchResponse } from "../lib/discovery-contract";
import { buildAskExploreUrl, buildAskRequestUrl, formatAskFarmLocation, parseAskLocationContext, type AskLocationContext } from "../lib/ask-continuity";

const noLocation: AskLocationContext = { near: "", radiusMiles: null };

export default function AskDirectory() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<FarmSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [submittedContext, setSubmittedContext] = useState<AskLocationContext>(noLocation);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const query = question.trim();
    if (!query) return;
    const context = parseAskLocationContext(window.location.search);
    setSubmittedQuestion(query);
    setSubmittedContext(context);
    setLoading(true);
    setError("");
    try {
      const response = await fetch(buildAskRequestUrl(query, context));
      if (!response.ok) throw new Error(`search ${response.status}`);
      setResult(await response.json() as FarmSearchResponse);
    } catch {
      setError("The directory search is unavailable. Try the farm explorer below.");
    } finally {
      setLoading(false);
    }
  }

  const exploreHref = buildAskExploreUrl(submittedQuestion, submittedContext);
  const resultIsNearby = result?.scope.mode === "nearby";

  return (
    <div className="ask-workspace ask-workspace-v2">
      <form className="ask-form" onSubmit={submit}>
        <label htmlFor="field-question">Ask the directory</label>
        <div>
          <input
            id="field-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Who sells goat cheese?"
          />
          <button type="submit" disabled={loading}>{loading ? "Searching…" : "Ask →"}</button>
        </div>
        <p>This searches listing descriptions, not live inventory. Your current explorer location stays applied; without one, results are nationwide. Fewer words usually find more farms.</p>
      </form>

      <div className={`ask-answer ${result || error ? "has-answer" : ""}`} aria-live="polite">
        <div className="answer-mark" aria-hidden="true">{error ? "!" : result ? result.total : "?"}</div>
        <div className={`answer-copy ${result ? "" : "empty"}`}>
          {error ? (
            <><span>Search interrupted</span><h3>Keep browsing</h3><p>{error}</p></>
          ) : result ? (
            <>
              <span>{resultIsNearby ? `Matches near ${result.scope.label}` : "Nationwide directory matches"}</span>
              <h3>{result.total.toLocaleString()} {result.total === 1 ? "farm matches" : "farms match"}</h3>
              <p>
                {resultIsNearby
                  ? `These listing-text matches are within ${result.scope.radiusMiles} miles of ${result.scope.label}. Refine products and ways to buy in the explorer.`
                  : "These are nationwide listing-text matches. Add a location in the explorer to find genuinely local options."}
              </p>
              <div className="answer-farms">
                {result.items.map((farm) => <a href={buildAskExploreUrl(submittedQuestion, submittedContext, farm.id)} key={farm.id}><small>{formatAskFarmLocation(farm.city, farm.state)}</small>{farm.name}</a>)}
              </div>
              <a className="answer-action" href={exploreHref}>Explore all {result.total.toLocaleString()} matches →</a>
            </>
          ) : (
            <><span>Built for practical questions</span><h3>Food, farms, and ways to buy</h3><p>Name a product or a farm. Add your city in the explorer for genuinely local results.</p></>
          )}
        </div>
      </div>
    </div>
  );
}
