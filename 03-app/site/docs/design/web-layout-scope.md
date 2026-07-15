# FarmFinder website wireframe scope

> Status: wireframe-only alignment artifact · 2026-07-15

Editable wireframes: [FarmFinder Website — IA & Wireframes](https://www.figma.com/design/HNsqERLxjf46p1tKbmJMPz)

This document scopes the website layout before visual refinement or implementation changes. It is intentionally separate from farm data, map behavior, database cutover, and mobile app work.

## Product boundary

FarmFinder is a public continental-U.S. farm-discovery directory and field guide. Louisiana and Mississippi are the first current coverage release, not the product boundary.

The website's primary job is:

```text
question or search → filter → trustworthy farm result → farm record → next buying step
```

The website is not a marketplace in this scope. Do not add ordering, checkout, live inventory, guaranteed hours, payments, or separate-company branding.

## Website information architecture

Keep the current single-page public discovery model, with explicit anchors and a profile overlay rather than inventing a new application shell.

| Area | Purpose | Required content |
|---|---|---|
| Header | Orient and provide direct entry to discovery | FarmFinder identity, Ask, Harvest, Explore, Find farms action |
| Home / atlas hero | Explain the product and coverage honestly | Product thesis, current release coverage, one discovery CTA |
| Ask the field guide | Turn practical questions into directory-backed results | Question input, suggested prompts, grounded answer, show matching farms |
| Harvest index | Provide browse shortcuts by product | Product categories, counts, season/context entry point |
| Explore workspace | Make the database usable at scale | Search, filters, result count, list, map, selected record |
| Farm profile | Support the next buying decision | Products, sales paths, public contacts/links, location confidence, provenance |
| Release/trust ledger | Explain freshness and limitations | Release key/date, source confidence, approximate locations, correction path status |

The website does not need a permanent sign-in surface for public discovery. Authentication can be introduced later for claims, corrections, or synchronized saved features without changing the public information architecture.

## Desktop layout

Target the first wireframe at a 1440px canvas with an intentional 1024px tablet composition. Use the existing visual system in `docs/design/web-design-system.md`: Newsreader for editorial display and Geist for interface/data.

### Home / discovery

1. Sticky ruled header.
2. Editorial atlas hero with one primary “Find food near you” action.
3. Coverage ledger showing current published release facts, not manually typed marketing numbers.
4. Dark question desk with grounded-answer states.
5. Harvest index as a browse shortcut, not an unrelated feature-card grid.
6. Explore anchor that lands on the synchronized directory workspace.

### Explore workspace

- Search and filters sit above the list/map split.
- List width is the stable reading surface; map occupies the secondary context surface.
- Result rows contain farm name, place, products, sales paths, and a clear profile action.
- The selected row and selected map record share one farm ID and one visual selected state.
- The list supports pagination/cursor loading in the API-backed future; it must not assume that all national records are in one browser payload.
- Profile opens as a right-side drawer on desktop and a full-height route/sheet on smaller screens.

## Map and data alignment rules

These are the most important constraints for the next implementation pass.

1. The list is the reliable discovery path. If map tiles, WebGL, or map data fail, search, filters, results, and profiles remain usable.
2. Map rendering is a projection of the active result set, not a second source of truth. It must derive from the same farm IDs currently rendered in the list.
3. Map loading is lazy and independent from page content. A map placeholder must not block initial list content.
4. Map failure must produce a clear retry action and preserve the list. Do not replace the whole explorer with a generic error screen.
5. Empty, stale, and release-mismatch states are visible and truthful. Never silently show an older or different dataset release as if it were current.
6. Approximate/city/region location precision is shown in profile and map context. Do not imply an exact farm-gate location where the source does not support it.
7. “Near me” on the website uses foreground browser geolocation only after an explicit user action. A denied permission falls back to normal search and state filters.
8. Map pins and clusters never imply live inventory, current opening hours, or product availability.
9. The current site may continue using the static JSON adapter while API work is separate, but the UI contract should already include release metadata, stable IDs, precision, and freshness fields.

## Wireframe states included

The Figma file includes these implementation states:

- Home / discovery default.
- Explore with list, filters, clustered map, and selected record.
- Explore with map unavailable while the list remains active.
- Farm profile drawer with public data, provenance, location confidence, and next step.
- Empty results, stale release notice, and independent loading/skeleton state.
- Tablet layout where the list remains primary and the map remains secondary.

## Current data contract assumptions

The website can safely wireframe and display the fields currently represented in the public farm model:

- Farm name, category, state, city, parish/county, region.
- Products and product text.
- Public website, social presence, online store, contact visibility, and sales paths.
- Public map coordinates plus `geoPrecision`.
- Source/provenance and verification/freshness metadata when available.

Do not add structured hours to the website wireframe as if that data already exists. The current farm model does not provide reliable structured hours. Until a source-backed hours model is added, use “Contact before visiting” and source-backed schedule notes only.

## Interaction contracts

### Search and filters

- Search covers farm name, products, town, parish/county, state, region, notes, and sales paths.
- Filters can combine state, broad category, specific product, and way-to-buy values.
- Clear-all resets the query, filters, selected farm, and question-result scope.
- The active result count is announced to assistive technology.
- Result state is URL-ready so a filtered view can be shared or restored.

### List and map

- Selecting a list row selects the matching map record and scrolls/focuses the row.
- Selecting a map point selects the matching list row and opens the compact map detail card.
- Cluster activation expands the cluster; it does not open an arbitrary farm.
- “Fit results” fits only the active result set.
- “Use my location” centers the map and reports permission/error status without persisting exact coordinates by default.
- “Full profile” opens the farm drawer; closing it returns to the prior list/map selection and camera state.

### Ask

- Ask answers are directory-grounded, not live inventory or availability answers.
- Every answer exposes matching farm IDs through a “Show farms” action.
- No-match answers offer a broader search or directory reset.
- Loading and failure states preserve the input and provide retry.

## Content and edge-case requirements

- Long farm names wrap or truncate without hiding the profile action.
- Missing website, phone, email, products, or sales paths use explicit “not listed” language; do not render empty controls.
- Missing or approximate coordinates never remove the farm from the list.
- Stale data shows release key/date and a retry/continue-browsing choice.
- Empty results provide one obvious recovery action.
- Map tile or WebGL failure never blocks the list.
- Data release mismatch is a visible trust issue for staging and must be logged for investigation; it is not a visual-only problem.

## Accessibility and responsive behavior

- Use semantic landmarks, one `h1`, ordered heading levels, and a skip link.
- Keyboard focus must remain visible through sticky header, filters, list selection, map controls, and profile drawer.
- The map has a complete list alternative and is never the only path to a farm.
- Dialog/drawer focus is trapped while open, closes with Escape, and returns focus to the triggering control.
- Maintain AA contrast and 44px minimum interactive targets on touch layouts.
- Respect reduced motion; disable nonessential atlas motion and smooth transitions.
- At tablet widths, reduce hero complexity and keep list/map side by side when space allows.
- At small widths, switch list/map explicitly rather than forcing a tiny simultaneous split; farm profiles become full-height sheets.

## Wireframe-only staging acceptance

This wireframe scope is aligned when:

1. A user can reach Explore from the header or hero in one action.
2. A user can search/filter the directory without an account.
3. A user can understand which release and coverage set they are viewing.
4. A map failure leaves a complete usable directory path.
5. A selected farm has one consistent identity across list, map, and profile.
6. Missing/approximate data is represented honestly instead of being hidden or invented.
7. The layout works at desktop, tablet, and small widths without changing the product boundary.

## Separation of work

This website wireframe change should be its own PR/commit and must not include:

- Farm data edits, workbook changes, generated JSON changes, or state-release changes.
- MapLibre fixes, tile-provider changes, geocoding, or database/API implementation.
- Authentication, notes, claims, or marketplace work.
- Mobile app wireframes or native implementation.

Those changes should be reviewed and committed separately so a data correction cannot silently change layout scope and a map fix cannot silently change the public product boundary.
