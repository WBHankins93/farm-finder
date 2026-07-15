# FarmFinder mobile layout scope

> Status: staging-quality product and wireframe scope · 2026-07-15

## Outcome

The first mobile release should make one job feel effortless: find a nearby farm, understand how to buy from it, and save it for later.

The mobile app is a native client of the FarmFinder API. It is not a direct PostgreSQL client, a marketplace, or a WebView wrapper. Public discovery remains available without an account. An account is required only when a user wants synchronized favorites, private notes, or future contribution flows.

Editable low-fidelity wireframes: [FarmFinder Mobile — IA & Wireframes](https://www.figma.com/design/W3bxjlZKEwLI7cXYU35xIu)

## Primary information architecture

Use four persistent tabs. Keep detail, filters, authentication, notes, settings, and future correction flows in native stack routes.

| Tab | Job | Primary actions |
|---|---|---|
| Discover | Start nearby discovery with useful context | Search, request location, choose radius, open nearby results |
| Map | Explore geography and clusters | Pan/zoom, select a farm, change radius, switch to list |
| All farms | Browse the complete published directory | Search, filter, sort, paginate/virtualize, open a farm |
| Saved | Return to favorites and personal notes | Sign in, open saved farm, add/edit/delete private note |

Stack routes:

```text
/farm/:slug                 Farm detail
/filters                    Filter bottom sheet
/search                     Search results, reachable from Discover and All farms
/auth/sign-in               Account gate; browsing can continue without sign-in
/saved/:farmId/note         Private note editor
/account                    Session, privacy, deletion, sign out
```

The existing “Ask” concept is useful, but it is not required for this staging mobile scope. Keep it as a later route or web capability until the core discovery loop is instrumented and stable.

## Core interaction decisions

### Location and radius

- Ask for location in context when the user taps “Near me,” not on cold launch.
- Default radius is **25 miles**.
- Allow radius changes through a filter sheet or map control. Recommended staging options: 5, 10, 25, 50, and 100 miles, plus a custom value later if the API supports it safely.
- Send the current coordinate and radius to the API for nearby queries. Do not persist exact device coordinates by default.
- If permission is denied, keep the app useful: show the all-farms directory, allow town/state search, and explain how to re-enable permission.
- Display distance only when it is computed from a user-approved location. Never imply a farm is open or available because it is nearby.

### Search, filters, and scale

- Search covers farm name, products, town, parish/county, state, and sales channels.
- Filters are applied in a bottom sheet and committed with an explicit **Apply** action to avoid request churn.
- Directory results use cursor pagination or another bounded server-side pagination strategy. Never load the continental dataset into the mobile client.
- Lists are virtualized. Map results are clustered and bounded to the current viewport/radius.
- Preserve search, filters, sort, radius, and map camera state when navigating to a farm and back.

### Saved farms and notes

- Tapping Save while signed out opens the sign-in gate and preserves the farm the user intended to save.
- Tapping Save while signed in is optimistic, reversible, and gives a visible confirmation.
- Notes are private to the signed-in user, editable, deletable, and separate from public farm facts.
- Sign-out clears private cached data from the device. Public farm cache may remain.
- A note editor needs loading, offline, retry, validation, conflict, and deletion states even if the first release supports one note per farm.

## Farm detail layout

The farm page should answer “Is this the farm I want, and how do I buy from it?” in the first viewport.

1. Header: back, farm name, save action, listing/verification state.
2. Location: city/state and parish/county; distance when location permission is active; clear approximate-location language when applicable.
3. Products: normalized product tags plus availability qualifier when source-backed.
4. How to buy: farmers market, on-farm sales, CSA, delivery/shipping, online store.
5. Contact actions: call, website, social/store links, and map/directions where public and available.
6. Before you go: freshness disclaimer and any source-backed schedule or access notes.
7. Trust: last reviewed/verified date, source/provenance link or summary, location precision, and correction entry point.
8. Personal layer: saved state and private note affordance.

Hours are not currently present in `app/data/farms.json` or the canonical farm model. Do not render fabricated hours or a blank “hours” section. Add structured, source-backed hours before making hours a committed UI requirement:

```text
farm_hours: farm_id, day_of_week, opens_at, closes_at, status,
            source_record_id, verified_at
```

Until then, use “Contact before visiting” and display only source-backed schedule notes.

## Staging-quality requirements beyond the four tabs

The following are required to make the layout implementation-ready, even though they are not additional navigation tabs.

### Data and API contracts

- `GET /v1/farms` with cursor pagination, text search, normalized filters, sort, and stable release metadata.
- `GET /v1/farms/nearby` with latitude, longitude, radius, bounded result count, and distance; reject invalid or excessive radii.
- `GET /v1/farms/:slug` with products, sales channels, public contacts/links, location precision, verification, and provenance summary.
- Filter-facet response so the UI can show counts without shipping the full database.
- `GET/POST/DELETE /v1/me/saved-farms` with idempotent save/delete behavior.
- `GET/PUT/DELETE /v1/me/farm-notes/:farmId` for private notes.
- One consistent error envelope for validation, permission, authentication, rate-limit, offline, and server failures.
- API responses must include dataset release key and `last_verified_at`/freshness data where relevant.

### Current foundation gaps to close

- `saved_farms` exists in the database foundation, but private farm notes need a user-owned relation; the current `documents` table has no `user_id`.
- The current generated farm JSON has contact, website, social, sales-channel, coordinate, and precision fields, but not structured hours.
- The current app reads static JSON. Mobile staging needs a versioned read-only API or an explicit fixture adapter with the same contract before device work begins.
- The current mobile directory target is 299 mapped listings. The contract must already support state-by-state expansion and must not assume Louisiana/Mississippi-sized payloads.
- Exact farm addresses and farm-gate coordinates remain privacy-sensitive. Public location rendering must respect `geoPrecision` and visibility policy.

### Auth, privacy, and security

- OIDC Authorization Code + PKCE through the system browser.
- Tokens only in platform secure storage; no access/refresh tokens in AsyncStorage or logs.
- Protected API operations enforce authorization server-side; the client must not be the policy boundary.
- Private notes are never included in public farm responses, analytics payloads, crash reports, or shared screenshots.
- Provide sign out, session revocation, account deletion, and privacy policy paths before pilot release.
- Do not request background location. Use foreground location only for an explicit nearby action.

### Required states for every primary screen

- Initial loading skeleton.
- Loaded state.
- Empty results with a clear next action.
- Offline/read-only state with last-updated metadata.
- Location permission not requested, denied, unavailable, and granted.
- Authentication required, expired session, and sign-in failure.
- API validation, rate-limit, and server error with retry.
- Long names, missing websites, missing phone/email, approximate coordinates, zero products, and seasonal/unknown availability.

### Accessibility and device quality

- VoiceOver and TalkBack labels must identify farm name, location, distance, save state, map selection, and location precision.
- Touch targets are at least platform-recommended minimums; do not make the heart/save icon the only tiny target.
- Support Dynamic Type/font scaling without clipping farm names or filter controls.
- Provide a list alternative for all map content; the map is never the only way to reach a farm.
- Respect reduced motion and high-contrast settings.
- Test iOS and Android on a representative small phone, current standard phone, and a slower mid-range Android device.

## Staging release slice

### Must be in staging

- Expo Router shell with the four tabs and stack routes above.
- Fixture-backed Discover, Map, All farms, Filters, Farm detail, Sign in, Saved, and Note editor screens.
- Versioned read-only API contract with pagination, nearby query, detail query, and filter facets.
- Foreground location permission flow with 25-mile default and adjustable radius.
- Clustered map plus list toggle and an accessible list alternative.
- Authenticated saved-farm sync and private notes, including sign-out cache clearing.
- Loading, empty, denied-permission, offline, stale-data, auth-expired, and server-error states.
- Accessibility pass, device smoke tests, analytics events, error logging, and a preview/staging build profile.

### Explicitly out of staging scope

- Ordering, checkout, payments, live inventory, or guaranteed availability.
- Background location or continuous location tracking.
- Bulk offline map tiles.
- Farm-owner claims, editing, image uploads, or public corrections unless the web authorization policy is already proven.
- Push notifications.
- AI/Ask experience as a primary tab.

## Acceptance criteria

The scope is ready for visual design and implementation when a tester can:

1. Open the app without signing in and find a farm through search, the map, or All farms.
2. Grant location, see nearby farms within the default 25-mile radius, change the radius, and recover cleanly from denial.
3. Open a farm detail page and find products, sales paths, public contact links, location confidence, and freshness/provenance context.
4. Save a farm, sign in when prompted, see it in Saved, add a private note, edit/delete it, and confirm it is gone from the device after sign-out.
5. Use the same journeys with no network and receive truthful read-only/stale-state messaging.
6. Complete the journeys with VoiceOver/TalkBack and without relying on map gestures alone.

## Implementation order

1. Finalize API contracts, note persistence, location privacy, and auth/session policy.
2. Create shared TypeScript contracts, semantic tokens, telemetry vocabulary, and sanitized fixtures.
3. Build the Expo Router shell and fixture-backed screens from the Figma wireframes.
4. Add the read-only API, pagination, radius query, caching, and offline metadata.
5. Add authentication, saved-farm sync, notes, account deletion, and session revocation.
6. Run accessibility, device, privacy, performance, and staging smoke checks before visual polish.
