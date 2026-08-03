# FarmFinder — UX review & design recommendations

_Reviewed: 2026-08-02 · Scope: the recent explorer redesign (PR #111 “Redesign the farm map and
list explorer”, plus the visual-language work in #104–#109) against common map-app conventions._

## Implementation status (2026-08-02)

A first pass of the full sequence has landed, scoped to **calm the explorer, keep the brand in
marketing** (per direction). Verified: `tsc` clean, `eslint` clean, unit 23/23, SSR render test
4/4, no horizontal overflow.

- ✅ §2 Full-height split; list is a fixed 340–400px column, map takes the rest.
- ✅ §3 Calm/dense cards (title 25px → 17px, tighter padding, tabular numbers on all counts/distances).
- ✅ §4 Hairlines + soft elevation replace hard ink borders / offset poster-shadows — explorer only.
- ✅ §5 Hue-separated category palette (`farms.ts`) + bigger map pins + complete collapsible legend.
- ✅ §1/§6 Hero city search now deep-links into the explorer (`?place=` resolves + scrolls).
- ✅ Motion: results stagger-in, sheet slide-ups, mobile list⇄map **View Transitions** crossfade
  (list→map hover-ring already existed). All behind `prefers-reduced-motion`.
- ✅ §8 Mobile: floating Map⇄List pill over a taller map.
- ✅ Fonts: kept the documented Plus Jakarta + DM Sans pairing; added tabular figures + stopped
  tight tracking on small text (Inter/Geist intentionally **not** adopted — would fight the
  documented “Market Stand” decision in `layout.tsx`).
- ⏳ Not yet done (larger follow-ups): a true **draggable** bottom sheet (peek/half/full) on
  mobile — current version is a floating toggle + full-height panels; an optional **imagery**
  pass for product tiles; per-category map **hover→row** linking (row→pin exists).

All of it is contained in a clearly-commented “CALM EXPLORER LAYER” block in `globals.css` plus
small component edits, so it’s easy to tune or revert.

## TL;DR

The recent work actually did **two** things at once:

1. **Real functionality upgrades** (the part you wanted) — nearby-first search, place
   autocomplete, radius control, a bounded `/v1` data path, server clustering + a shared-point
   “cluster sheet”, “search this area”, a filter sheet, skeleton loaders, URL state sync,
   geolocation, focus-trapping, and `content-visibility` list virtualization.
2. **A full brand redesign** (the part that feels like “too much”) — a deliberate
   *Field Journal × Living Atlas* system: 130px editorial headlines, hard 1px ink borders,
   offset “poster” shadows, atlas/contour motifs, a `RELEASE 001` stamp, vertical-rl labels.

Point 2 isn’t codex going rogue — it’s executing `docs/design/web-design-system.md`
(“Archetype: Field Journal × Living Atlas”) and `visual-language-research-and-plan.md` to the
letter. So the question isn’t “was this a mistake” — it’s **“how much editorial brand do we
want standing between a user and the map?”** A farm finder is a *utility*. Below are the specific
places where the editorial system fights convenient use, with fixes, ordered by impact.

Nothing here requires throwing the brand away. Most fixes *dial it back* in the utility surfaces
(the explorer) while keeping the atlas identity in the marketing surfaces (hero, about).

---

## How the leading map/finder apps are structured (the conventions we’re measured against)

Google Maps, Zillow/Redfin, Airbnb, AllTrails, Yelp all converge on the same pattern:

- **The map + results are the landing surface**, not something you scroll to. Search is a single
  bar pinned over the map.
- **Full-viewport split**: results list on the left (~1/3), map filling the rest, both scrolling
  independently to the window height.
- **One search field** with scope built in (place) and an optional query, plus a compact filter
  row with an active-count and a one-tap “clear”.
- **Dense, scannable rows** — small photo/thumb, title ~16px, 2–3 metadata lines, a price/distance
  chip. 6–10 results visible above the fold.
- **Hover-linking** between list and map (hover a row → the pin lifts; hover a pin → the row
  highlights).
- **Mobile**: full-screen map with a **draggable bottom sheet** of results and a floating
  **Map ⇄ List** toggle — not a full marketing shell.
- **Restrained chrome, high-contrast pins**, soft hairline dividers and soft shadows.

FarmFinder has the *machinery* for most of this already; the editorial layer is what obscures it.

---

## Findings & recommendations (highest impact first)

### 1. The map is buried under a full marketing page ⭐ biggest win
The explorer lives at `#discover`, after hero → Ask → Browse products → field-story
(`app/page.tsx:20-61`). A utility’s core surface should be reachable in ~0 scrolls.

**Recommend:** Make the explorer the primary landing view. Two options:
- **A (convention):** `/` opens straight into the split explorer with a compact header; move
  hero/Ask/Browse/field-story to a `/about` or below-the-fold “learn more”.
- **B (compromise, keeps brand moment):** Keep a *short* hero (headline + the single city
  search), then the explorer immediately — cut Ask + Browse + field-story from the critical path
  and link them from the nav. The hero currently is `min-height: 720px` (`globals.css:593`); a
  utility hero should be ~40–50vh max.

### 2. Explorer doesn’t use the viewport; map is cramped
`.explorer-v2` is `height: min(780px, 100vh-108px)` with the map at `58fr` under **two** stacked
sticky bars (86px topbar + controls at `top:85px`) (`globals.css:610,647`).

**Recommend:** In the explorer route, drop the page chrome to a single slim bar; let the split
fill `100dvh`. Give the map the majority width (list 380–420px fixed, map flexes). Merge the
sticky control stack into one bar.

### 3. Type scale is tuned for a poster, not for scanning
Headlines reach `clamp(72px,8.7vw,132px)/.82` with `-.065em` tracking (`globals.css:74`); section
headings 78–92px. Card titles are `600 25px` (`globals.css:211`) and rows are tall, so only a few
farms show per screen.

**Recommend:** Reserve the giant display type for the hero only. In the explorer use a calm scale:
section label 11px, card title 16–18px, metadata 13px. Tighten card vertical padding (currently
`21px 18px 14px`) to fit ~7–9 results above the fold. Enable tabular figures on all
counts/distances: `font-feature-settings:"tnum"` (see §Fonts).

### 4. Hard borders + offset shadows read “brutalist poster,” not “trustworthy tool”
`1px solid var(--ink)` grids and `box-shadow: 7px 7px 0` / `8px 9px 0` are everywhere
(hero-location `globals.css:597`, map-tools `:239`, cluster-sheet `:671`, filter-sheet `:681`).

**Recommend:** In the explorer, swap the poster shadows for soft elevation
(`0 1px 2px rgba(0,0,0,.06), 0 4px 16px rgba(23,37,29,.10)`) and hard ink borders for hairlines
(`1px solid rgba(23,37,29,.12)`). Keep the hard-edged treatment only in the marketing sections so
the brand still shows up where it doesn’t cost usability.

### 5. Map pins are hard to tell apart, legend is incomplete
Category colors are close-hue earth tones — Produce `#55734d`, Rice `#99835c`, Honey `#bd8628`,
Poultry `#9a6936` — at `circle-radius` 4.5–8px (`farm-map.tsx:113`). The legend shows only 4 of 9
categories (`farm-map.tsx:212`).

**Recommend:**
- Adopt a higher-contrast categorical palette (rotate hue, not just value). See the `dataviz`
  skill for a validated colorblind-safe set; map the 9 categories onto distinct hues.
- Bump min pin size to ~6–9px and add a subtle white halo (already present) + hover scale.
- Either show the full legend (collapsible) or drop the legend and label category on
  hover/selection — don’t show a partial key.

### 6. Three overlapping search entry points
Hero “City or town” (`page.tsx:26`), explorer “City or town” + “Farm or food” (`discovery-workspace.tsx:473,477`),
and the separate “Ask the directory” search (`ask-directory.tsx`). Users won’t know which to use.

**Recommend:** Collapse to **one** model everywhere: a place field (scope) + a query field
(“eggs, tomatoes, farm name”). The hero search should deep-link into the explorer with that scope
pre-applied (the URL state machine in `discovery-client.ts` already supports this). Fold “Ask” in
as a query, or demote it to a labeled example-chips helper — not a third search box.

### 7. Filters are spread across three rows + a sheet + a separate sort
Product chips row, service chips row, “All filters” sheet, and a separate sort select
(`discovery-workspace.tsx:483-494`). It works but it’s a lot of chrome above the results.

**Recommend:** One filter bar: `[ Filters ▾ (2) ]  [ product chips … ]   Sort ▾`. Put category +
services + product inside the sheet; keep only the top ~4 product chips inline. Show a single
active-filter count and one “Clear”. You already compute a live `draftTotal` — surface it on the
inline bar too (“See 128 farms”).

### 8. Mobile chrome stacks up
Mobile has a bottom `mobile-dock` (`globals.css:416`) **and** a `mobile-view-switch`
(`:397`) **and** the sticky controls. That’s three layers of navigation over a small map.

**Recommend:** On mobile, go full-screen map with a **draggable bottom sheet** for results
(peek → half → full) and a single floating **Map ⇄ List** pill. Drop the bottom dock inside the
explorer. This is the dominant mobile-map pattern (Google/Zillow/AllTrails) and frees vertical
space.

### 9. Two different detail surfaces
Selecting a pin shows a bottom-left card (`farm-map.tsx:213`); “View profile” opens a right-side
drawer (`farm-profile-dialog.tsx`). That’s fine and conventional — just make the transition
between them feel continuous (see Motion §, View Transitions).

### Things that are already good — keep them
- Skeleton loaders, empty states, and inline error recovery (`discovery-workspace.tsx:501-508`).
- Nearby-first “don’t load the whole country” model and the honest precision labeling.
- `content-visibility:auto` on cards, lazy map activation via IntersectionObserver.
- `prefers-reduced-motion` handling (`globals.css:489`) and focus-trapping in the filter sheet.
- Free, no-key **OpenFreeMap “liberty”** basemap (`farm-map.tsx:91`).

---

## Motion — smooth movement through the app

You already have a good, compositor-only foundation: scroll-driven `section-number` draw and a
topbar scroll-progress bar (`globals.css:570-590`), `atlas-pulse`, and map `easeTo`/`fitBounds`
transitions at 420–550ms (`farm-map.tsx:129,167,190`). Build on it — don’t add a heavy library.

Recommended additions (all must sit behind `@media (prefers-reduced-motion: no-preference)`):

1. **List ⇄ map hover linking.** On row hover, scale the matching pin (`circle-radius` transition
   via a feature-state) and vice-versa highlight the row. ~120ms, ease-out. This is the single
   biggest “feels alive” upgrade for a map app.
2. **Selection pulse.** When a farm is selected, a one-shot ring pulse on its pin (you already
   `easeTo` the camera — add a marker pop).
3. **View Transitions API** (built into Next 16 / React 19 — no dependency) for:
   - list ⇄ map view switch on mobile (crossfade + slide),
   - opening the profile drawer (the map card can morph into the drawer header).
   Use `document.startViewTransition(() => setState(...))` with `view-transition-name` on the
   shared elements; it degrades gracefully where unsupported.
4. **Results stagger-in.** New search results fade/translate in with a 20–30ms stagger, capped at
   ~8 items. Pure CSS (`animation-delay` by `:nth-child`) or WAAPI.
5. **Bottom sheet spring** (mobile). A draggable sheet with a spring snap between peek/half/full.
   CSS scroll-snap + a small pointer handler, or a ~4KB helper.
6. **Filter sheet / cluster sheet** already appear instantly — give them a 180–220ms slide-up +
   backdrop fade to match the app’s calm pacing.

Library guidance: prefer **CSS + WAAPI + View Transitions** (zero deps, matches the current
approach). If you want spring physics for the bottom sheet and richer orchestration, add
**`motion`** (motion.dev, the successor to Framer Motion — tree-shakeable, ~5–15KB) rather than
anything heavier. Keep the reduced-motion gate on everything.

---

## Fonts — better choices for a map utility

The current pairing is **Plus Jakarta Sans** (display) + **DM Sans** (body) — both free
(Google Fonts, OFL) and both good. The problem is *scale and tracking in the utility*, not the
faces. Two paths:

- **Keep the pairing, fix the usage** (lowest effort): reserve Plus Jakarta Sans for the hero and
  section headings; use DM Sans for everything in the explorer; turn on tabular numbers for all
  counts/distances/radii: `font-feature-settings:"tnum" 1, "cv..." ` (DM Sans supports `tnum`).

- **Switch the UI face to a purpose-built UI sans** (recommended for a “map app” feel):
  - **Inter** (OFL, free) — the de-facto UI/data face; superb at 12–16px, has tabular figures,
    a slashed zero, and optical sizing. Use for all list/controls/labels.
  - or **Geist** (OFL, free, by Vercel) — pairs cleanly with Next and reads very “product.”
  Keep **Plus Jakarta Sans** for the few big display moments so the brand voice survives.

Whichever path: enable `tnum` on numerics, set explorer body to 15–16px/1.5, and stop the
negative letter-spacing below ~24px (tight tracking hurts small-text legibility).

Loading: self-host via `next/font` (already the `--font-*` pattern) to avoid layout shift and
external requests.

---

## Free images — license-safe sources to gather from

Current state: the field-story photo is **USDA ARS, public domain** (`globals.css:542-551`) —
exactly the right instinct. Product tiles are flat color + a line glyph with a photo overlay
fallback (`globals.css:532-541`), which is clean and fast; photos are optional.

Sources (all free, commercial-OK — always keep the credit/license in `docs/imagery-kit.md`):

- **USDA ARS Image Gallery** — public domain, US ag/produce/livestock. Best default (no
  attribution required, but keep the credit line you already use).
- **Openverse** (openverse.org) — CC-search across Flickr/Wikimedia; filter to CC0 / “commercial
  + modification”.
- **Unsplash** and **Pexels** — free license; strong “farmers market”, “CSA box”, “produce”,
  “pasture” collections. Prefer daylight, un-stylized, regionally plausible shots.
- **StockSnap.io** — CC0.
- **Wikimedia Commons** — verify per-file license (mix of PD/CC).

Recommendations:
- If you add product-tile photos, keep them optional (the glyph fallback already handles missing
  files) and ship **WebP/AVIF**, ~128px tall, `background-position:center`, with the existing
  inset gradient so overlaid glyphs/text stay legible.
- For the **basemap**, OpenFreeMap “liberty” is fine, but a **muted/monochrome** style makes
  colored pins pop — consider OpenFreeMap “positron”-like or a custom pale style. Free, no key.
- Don’t stock-photo the hero — the atlas plate is a deliberate, honest, fast choice per the design
  system. Leave it.

---

## Suggested sequencing

1. **Explorer-first layout** (§1, §2) + **calm the type/borders in the explorer only** (§3, §4).
   Biggest perceived-convenience jump; keeps the brand in marketing sections.
2. **Unify search + filters** (§6, §7) and **fix pins + legend** (§5).
3. **Motion**: hover-linking + View Transitions + result stagger (§Motion 1,3,4).
4. **Mobile bottom sheet** (§8) + **fonts** (tnum + UI face) + optional **imagery** pass.

Each step is independent and reversible, so we can stop at the amount of change you actually want.
