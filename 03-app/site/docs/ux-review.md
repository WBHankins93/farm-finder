# UX review — FarmFinder

> 2026-07-27. Goal restated by the owner: *simplified layout, a user should
> never have to question how to do something; less "AI/editorial-luxury" feel;
> imagery is the missing piece.*

## What this PR changed

| Area | Before | After |
|---|---|---|
| **Type** | Newsreader **serif** display (editorial-luxury, "AI-forward") | **Plus Jakarta Sans + DM Sans** — the approved "Market Stand" pair, weight-driven, no serif |
| **Copy** | "Louisiana + Mississippi", "Search 299 farms" (stale) | "Local farms in all 50 states", `68,618` formatted, national stats (states covered / on the map) |
| **Imagery** | none (color blocks + a placeholder credit) | image layer wired on product cards + field-story with **graceful color fallback**; curated free-source kit in `imagery-kit.md` |
| **Map** | crashed on load (`maplibregl.supported()`) | fixed in PR1; clusters natively |
| **Data** | 299 hardcoded | real 68,618, nearest-first (PR1) |

## Is all functionality working?

- ✅ Search, category / product / service filters, list, "show more", profiles, "Nearest me", the "Ask" box.
- ✅ Data renders (68,618, location-first).
- ⚠️ **Map basemap** needs a networked browser — the tile host (`tiles.openfreemap.org`) is blocked in the sandbox; verified crash-free, not visually rendered here. Confirm in a real browser; if the free tile host is flaky in production, switch providers.
- ⚠️ **"Ask the field guide"** is a keyword matcher, not the RAG the vision promises. It works but sets an expectation it can't fully meet.

## Recommended simplifications (highest value first)

1. **Lead with location.** The hero is a manifesto; the product's job is "farms near me." Put the location prompt (GPS / ZIP) *in the hero*, above the fold, so step one is obvious. "Nearest me" is currently a small button inside the results.
2. **One primary action per screen.** The landing page stacks Ask → Browse → Filters → List/Map. For a first-time user that's four "starts." Collapse to: *set location → see nearby farms*, with Ask/Browse as secondary.
3. **Drop in the imagery.** Category tiles and a hero photo (kit ready) will do more for "visually appealing" than any layout change. It's wired — just add the files.
4. **Set the Ask expectation** or upgrade it. Either label it "keyword search" honestly, or make it real retrieval over the directory.
5. **Payload.** The 45 MB feed is a slow first paint on mobile; the `nearbyFarms` seam is the path to loading only nearby farms (documented in PR1).

## Not changed here (scoped out)

Real RAG for Ask, nearby-only data loading, and a full hero redesign are their
own PRs — this one targets type, copy, and the imagery foundation.
