"use client";

import { FormEvent, useState } from "react";
import type { FarmSearchResponse } from "../lib/discovery-contract";

export default function AskDirectory() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<FarmSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const query = question.trim();
    if (!query) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/v1/farms?q=${encodeURIComponent(query)}&sort=relevance&limit=6`);
      if (!response.ok) throw new Error(`search ${response.status}`);
      setResult(await response.json() as FarmSearchResponse);
    } catch {
      setError("The directory search is unavailable. Try the farm explorer below.");
    } finally {
      setLoading(false);
    }
  }

  const queryString = `q=${encodeURIComponent(question.trim())}`;
  const exploreHref = `/?${queryString}#discover`;

  return (
    <div className="ask-workspace ask-workspace-v2">
      <form className="ask-form" onSubmit={submit}>
        <label htmlFor="field-question">Ask the directory</label>
        <div>
          <input
            id="field-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Who sells eggs near New Orleans?"
          />
          <button type="submit" disabled={loading}>{loading ? "Searching…" : "Ask →"}</button>
        </div>
        <p>Results come from listing descriptions, not live inventory. Confirm the trip with the farm.</p>
      </form>

      <div className={`ask-answer ${result || error ? "has-answer" : ""}`} aria-live="polite">
        <div className="answer-mark" aria-hidden="true">{error ? "!" : result ? result.total : "?"}</div>
        <div className={`answer-copy ${result ? "" : "empty"}`}>
          {error ? (
            <><span>Search interrupted</span><h3>Keep browsing</h3><p>{error}</p></>
          ) : result ? (
            <>
              <span>Directory matches</span>
              <h3>{result.total.toLocaleString()} {result.total === 1 ? "farm matches" : "farms match"}</h3>
              <p>Review the closest matches, then use the explorer to add a location and shopping preferences.</p>
              <div className="answer-farms">
                {result.items.map((farm) => <a href={`/?${queryString}&farm=${encodeURIComponent(farm.id)}#discover`} key={farm.id}><small>{farm.city}, {farm.state}</small>{farm.name}</a>)}
              </div>
              <a className="answer-action" href={exploreHref}>Explore all {result.total.toLocaleString()} matches →</a>
            </>
          ) : (
            <><span>Built for practical questions</span><h3>Food, farms, and ways to buy</h3><p>Ask for a product or farm name here. Add your city in the explorer for genuinely local results.</p></>
          )}
        </div>
      </div>
    </div>
  );
}
