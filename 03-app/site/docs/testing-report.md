# Testing report — FarmFinder

> Snapshot: 2026-07-27 · Question asked: *"Is testing set up throughout the app?"*

## Short answer

**Backend: yes, well-covered. Frontend: barely — now improving.** The data
pipeline has a real suite; the web app had a single smoke test until this PR.

## Coverage by area

| Area | Before | Now | Gap |
|---|---|---|---|
| Pipeline (Python) | 48 unit tests (`01-database/pipeline/tests`) — model, cleanse, geo, privacy, QA, dedupe, orchestrator | same | Solid. Deterministic, no network. |
| Web — location logic | none | **7 unit tests** (`tests/nearby.test.ts`) — haversine, distance, nearest sort, immutability | — |
| Web — server render | 1 smoke (`tests/rendered-html.test.mjs`, builds + fetches `/`) | same | Renders only; no assertions on interactive state |
| Web — components | **none** | none | `farm-map`, filters, list, "Ask" untested |
| Web — flows (e2e) | **none** | none | search → nearest → profile never exercised |

## Why this matters — a bug that shipped

The map crashed on mount in production: `maplibregl.supported()` was removed in
the installed MapLibre version and threw *outside* the component's try/catch,
blanking the map. **No component test existed to catch it.** It was found only by
manually opening the app. That is the cost of the frontend gap, concretely.

## What this PR adds (zero new dependencies)

- `tests/nearby.test.ts` — real unit tests for the location layer, run through
  the already-present `tsx` loader + Node's built-in test runner.
- `npm run test:unit` — fast, no build required.
- `npm test` now runs unit tests, then the build + render smoke.

## Recommended next (own PRs)

1. **Component tests** — add `vitest` + `@testing-library/react` + `jsdom`
   (registry reachable). Cover `farm-map` (the guard that just failed), the
   filter reducer, the list cap / "show more", and `answerFarmQuestion`.
2. **One e2e** — `playwright` smoke of the core path: load → "Nearest me" →
   filter → open a profile. This is the flow a user actually performs.
3. **CI** — run `test:unit` + `states:test` on every PR (a `.github/workflows`
   job); today only the pipeline contract + PR-scope run in CI.
4. **Feed contract test** — assert `public/farms.json` records match the `Farm`
   type (25 keys) so a pipeline change can't silently break the app.
