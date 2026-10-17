# Testing report — FarmFinder

> Snapshot: 2026-10-13

## Short answer

The data and publication layers are strongly gated. The application now has a
substantial pure-logic suite and rendered-shell coverage, plus a real-WebGL
browser review harness. The remaining weakness is automated interaction and
visual regression: critical flows are reviewed in a browser, but a pull request
does not yet fail when their interactive or visual behavior regresses.

## Coverage by area

| Area | Current gate | What it protects | Remaining gap |
|---|---|---|---|
| Pipeline | 48 Python tests | Model, cleanse, geography, privacy, QA, dedupe, orchestration | Network source behavior is intentionally outside deterministic tests |
| Publication | `data:validate` plus 17 data gates | Eligibility, privacy, provenance, counts, encoded national index | Generated artifacts remain local by design |
| Web logic | 98 Node/TypeScript tests | Search, URLs, Ask continuity, place matching, maps, presentation, brand tokens | React interaction itself is not mounted in a test DOM |
| Rendered shell | 8 post-build checks | Public route, counts, rollback boundary, asset and record-shape assumptions | Hydrated interaction is not exercised |
| Browser review | `dev/screenshots.mjs` | Desktop/mobile hero, explorer, WebGL maps, map options, error diagnostics | Manual invocation; PNGs are review artifacts rather than baselines |
| PostGIS | `npm run db:test` in database-capable environments | Spatial query integrity, indexes, pagination, list/map agreement | Requires local or CI database infrastructure |

`npm test` runs the 98 unit tests, a production build with deployment-budget
checks, and the 8 rendered-shell checks. Repository policy separately requires
the pipeline, tooling, legacy-release, validation, gate, and lint suites for
any pull request that touches the site.

## Current browser findings

The 2026-10-13 follow-up pass exercised the hydrated discovery controls rather
than relying only on source inspection:

- Arrow keys select a city suggestion and expose an active descendant.
- Enter chooses the active city; Escape dismisses the list.
- The location status is the only live region in its row.
- A selected farm's map sheet uses the same normalized location and product
  summary as the list and profile.
- At 390 × 844, the selected-farm sheet stays within viewport width and its
  close control measures 44 × 44 CSS pixels.

These observations are evidence for the current change, not a replacement for
repeatable browser tests.

## Visual-regression rollout

Use the existing dependency-free Chrome DevTools harness as the starting point;
do not commit an ad hoc set of screenshots and call them a gate.

1. **Stabilize the capture contract.** Pin a Chrome major version and fonts,
   freeze the governed data release, disable ticker/crossfade motion, and wait
   for fonts and map idle. Mask only dynamic tile labels and attribution timing,
   never FarmFinder content.
2. **Define owned states.** Capture desktop 1440 × 900 and mobile 390 × 844 for
   hero, Ask result, explorer list, explorer map detail, filter dialog, and farm
   profile. Include reduced-motion runs for motion-bearing surfaces.
3. **Add semantic assertions first.** Before pixel comparison, fail on missing
   focus targets, overflow, unexpected horizontal scroll, sub-44px critical
   controls, and console/runtime errors.
4. **Introduce image diffs deliberately.** Store approved baselines with the
   Chrome/font/data manifest, use a small documented threshold, and require a
   design owner to approve baseline changes in the same pull request.
5. **Run and retain artifacts in CI.** Upload current, baseline, and diff images
   on failure; do not require reviewers to reproduce a workstation-only path.

## Recommended next slices

1. Add a browser smoke for city search → filter → map selection → profile,
   including back/forward restoration and keyboard-only operation.
2. Add mounted component tests for the discovery controls and modal focus
   boundaries once a DOM test runtime is selected.
3. Promote the semantic checks above into the screenshot harness, then adopt
   pixel baselines only after the environment contract is reproducible.
4. Keep real logo/media work behind provenance, rights, moderation, and owner
   approval; visual tests must use only committed, licensed production assets.
