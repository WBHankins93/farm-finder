# FarmFinder web design system and wireframe

## Project context

- **Product:** standalone public farm-discovery directory and local-food field guide.
- **Audience:** shoppers looking for nearby products and ways to buy; farmers reviewing or eventually managing their listing.
- **Primary job:** get from “I want this food near this place” to a trustworthy farm result with the next buying step.
- **Archetype:** Field Journal × Living Atlas.
- **Palette in materials:** river slate, chlorophyll ink, weathered seed paper, cane fiber, persimmon stamp, and oyster-shell white.
- **Current media constraint:** no production farm-image pipeline yet. The map, contour lines, category marks, farm data, and typography form the visual plate.

The aesthetic risk is an image-light editorial hero whose “picture” is a living agricultural atlas rather than stock farm photography. This is specific to FarmFinder, improves first-load performance, and remains honest about the current dataset.

## Core composition

The page behaves like a field notebook opened over a survey map:

- A persistent ruled header is the notebook binding.
- The hero is an asymmetrical atlas plate with contour rings, parcel lines, one oversized editorial title, a discreet action, and a coverage ledger.
- Question answering is a dark “field desk” inset rather than an AI chat bubble.
- Products appear as a crop index, not a generic equal-card feature grid.
- Discovery becomes the primary instrument panel: search and filters above a synchronized ledger/map split.
- Profiles read like verified field records with provenance and location-confidence stamps.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ FARMFINDER / GULF SOUTH FIELD GUIDE   Ask  Harvest  Explore    Find farms  │
├──────────────────────────────────────────────────────────────────────────────┤
│ LA · MS · GROWING OUTWARD                    [FIELD RECORD / JUL 2026]       │
│                                                                              │
│ THE GULF SOUTH,                                                            ○ │
│        BY THE FIELD.                 contour rings / parcel lines / pins     │
│                                                                              │
│       Find growers, markets, pickup, and ordering paths near you.            │
│       [ FIND FOOD NEAR YOU ↓ ]                                               │
│──────────────────────────────────────────────────────────────────────────────│
│ 311 mapped       239 Louisiana       72 Mississippi       source ledger      │
├──────────────────────────────────────────────────────────────────────────────┤
│ ASK THE FIELD GUIDE          [ practical question________________ ] [ASK →]  │
│                              suggested questions + grounded answer register  │
├──────────────────────────────────────────────────────────────────────────────┤
│ HARVEST INDEX                                                               │
│ 01 Vegetables  02 Fruit  03 Eggs  04 Beef ... horizontal/stepped crop rows │
├──────────────────────────────────────────────────────────────────────────────┤
│ EXPLORE  [ search food, farm, town________________________ ] [LA|MS|ALL]     │
│ category chips / product chips / ways-to-buy                                │
│ ┌──────────────────── result ledger ────────┬──────── living map ──────────┐ │
│ │ 001 Farm / place / products / paths       │ clusters, pins, confidence   │ │
│ │ 002 Farm / place / products / paths       │ selected field-record card   │ │
│ │ ...                                       │ map tools                     │ │
│ └───────────────────────────────────────────┴───────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ RELEASE NOTES / SOURCE CONFIDENCE / FARM PARTICIPATION                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Mobile web wireframe

```text
┌─────────────────────────────┐
│ FARMFINDER       FIND FARMS │
├─────────────────────────────┤
│ LA · MS                     │
│ THE GULF                    │
│ SOUTH, BY                   │
│ THE FIELD.              ○   │
│ Find food closer to home.   │
│ [ FIND FOOD NEAR YOU ↓ ]    │
│ 311 mapped · 2 states       │
├─────────────────────────────┤
│ ASK                         │
│ [ What do you need?_______] │
│ [ Ask → ]                   │
│ grounded answer register    │
├─────────────────────────────┤
│ HARVEST INDEX → horizontal  │
├─────────────────────────────┤
│ EXPLORE                     │
│ [ Search__________________] │
│ [ All ][ LA ][ MS ]         │
│ filter chips → scroll       │
│ [ LIST 24 ][ MAP ]          │
│ ┌─────────────────────────┐ │
│ │ result ledger OR map    │ │
│ │ selected record sheet   │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ Ask · Harvest · Explore     │
└─────────────────────────────┘
```

Mobile is recomposed, not merely stacked: the crop index becomes a horizontal sequence, list/map are mutually exclusive, filters scroll in one line before expanding, and profile details open as a full-height sheet.

## Tokens

### Color

| Token | Material | Value | Use |
|---|---|---|---|
| `--paper` | weathered seed paper | `#eef0e6` | page canvas |
| `--paper-deep` | pressed cane fiber | `#d9ddce` | selected and secondary surfaces |
| `--cream` | oyster-shell white | `#fbfcf6` | readable records and controls |
| `--ink` | wet field ink | `#17251d` | primary type and rules |
| `--green` | chlorophyll ink | `#173f2c` | deep sections and active state |
| `--green-2` | leaf ledger | `#4d735b` | produce and secondary state |
| `--river` | river slate | `#557681` | map and water-related context |
| `--rust` | persimmon stamp | `#c65e36` | focus, selected record, critical action |
| `--brass` | dry cane | `#a28745` | honey, counts, subtle warmth |
| `--rule` | pressed-paper edge | `#bcc5b8` | dividers and control boundaries |

Color is atmospheric and evidence-bearing. Rust marks the current selection or one important action; green represents FarmFinder structure; category colors always accompany text.

### Type

- **Display/editorial:** Newsreader, restrained to large titles, farm names, and explanatory prose.
- **Interface/data:** Geist, used for navigation, filters, counts, labels, and controls.
- Hero title uses `clamp()` with tight tracking and deliberate line breaks.
- Labels are small, uppercase, and widely tracked only when they function as metadata.
- Body copy remains sentence case and conversational.

### Space and shape

- Fluid outer gutter: `clamp(20px, 6vw, 96px)`.
- Rules and shared edges replace floating shadows.
- Radius is reserved for pills, circular location/record stamps, and map pins.
- Cards are flat ledger rows or crop-index sheets; no generic raised card grid.
- Touch controls are at least 44px high on small screens.

## Component inventory

| Component | Responsibility | State requirements |
|---|---|---|
| `SiteHeader` | Identity, primary anchors, direct find action | desktop, compact mobile, focus states |
| `AtlasHero` | Product thesis, coverage, one action | responsive title, reduced motion |
| `QuestionDesk` | Practical question input and grounded response | empty, loading, answer, no-match, error |
| `HarvestIndex` | Product education and browse shortcuts | count, season detail, selected |
| `ExplorerControls` | Search and filter state | URL-ready, active count, clear-all |
| `ResultLedger` | Farm list and selection | loading, results, empty, selected |
| `FarmMap` | Clustered geography and selected record | lazy loading, tile failure, geolocation denial |
| `FarmRecord` | Detailed profile and evidence | public fields, missing contact, approximate location |
| `ReleaseLedger` | Coverage and freshness transparency | release date and source confidence |
| `ParticipationNote` | Future correction/claim path | disabled/planned until secure flow exists |

## Motion

- Hero contour lines use a single slow ink-drift or mask reveal, never continuous parallax.
- Selection moves like a field-note annotation: a short rule draws in and the selected surface changes.
- Map/list transitions are direct and under 300ms.
- No blanket fade-up on scroll.
- `prefers-reduced-motion` disables smooth scrolling and all nonessential animation.

## Performance rules

- No hero raster asset until object storage, responsive variants, attribution, and rights exist.
- MapLibre is dynamically imported only when the map island renders.
- Server Components own static content and future data fetching; client state stays in interactive islands.
- Product and category marks use CSS, text, or tiny SVG rather than icon libraries.
- Avoid hydration work for release notes, about copy, and other static sections as the page is componentized.

## Six-step reusable design workflow

The prompts below are complete and can be reused when visual assets or future sections are commissioned.

### Step 1: Visual reference

**Tool:** GPT Image 2
**Input:** None

> Create one horizontal 16:9 website hero design reference for FarmFinder, a standalone Gulf South farm-discovery directory, but do not use a conventional website hero layout. Use a Field Journal × Living Atlas archetype. Build an asymmetrical full-canvas agricultural survey composition from abstract parcel lines, river curves, topographic contours, crop-row marks, and a few precise map pins; do not use stock-photo people or a left-copy/right-image split. Integrate oversized readable editorial serif type like a field-guide cover, with small-caps navigation and quiet edge captions. Include only “FARMFINDER,” “THE GULF SOUTH, BY THE FIELD,” and one discreet “FIND FOOD NEAR YOU” editorial stamp. Palette: river slate, chlorophyll ink, weathered seed paper, cane fiber, persimmon stamp, oyster-shell white. No eyebrow/headline/subheadline/two-button stack, no centered SaaS hero, no purple gradient, no equal cards. The layout must remain recognizable if all text disappears. Buttons are fine-bordered transparent pills, never bright blocks. Responsive intent must preserve the atlas composition rather than stack generic columns.

**What to look for:** A unique atlas silhouette, one clear action, strong type tension, and enough quiet space for real coded text.

### Step 2: Background plate

**Tool:** GPT Image 2
**Input:** Approved Step 1 reference

> Create a clean 16:9 FarmFinder hero art plate from the approved Field Journal × Living Atlas reference. Remove all readable UI, navigation, titles, captions, logo, and button text. Keep the asymmetrical parcel geometry, river curves, contour rings, crop marks, pins, paper fibers, lighting, depth, and the river-slate/chlorophyll/seed-paper/cane/persimmon palette. Do not redesign, add photography, center the composition, create a left/right split, add transparency, or crop tightly. Leave a purposeful quiet field for coded editorial typography. Preserve the recognizable atlas composition on desktop and enough central contrast for a mobile crop. No generic gradients or decorative card shapes.

**What to look for:** The same visual world with no baked-in words and stable focal areas for desktop/mobile crops.

### Step 3: Next.js build

**Tool:** Codex
**Input:** Reference, background plate if used, this art bible, current FarmFinder repository

> Build the FarmFinder hero and public discovery shell in Next.js 16 App Router with React 19 and accessible CSS. First write a concise visual spec covering the atlas composition, grid, title scale and breaks, quiet navigation, one CTA, contour placement, overlays, palette, responsive recomposition, and fidelity rules. Then implement it without redesigning. Use Server Components for static presentation and push client boundaries down to filters, dialogs, geolocation, and map interaction. Dynamically import MapLibre so it is absent from initial JavaScript. No left-copy/right-image hero, centered marketing stack, eyebrow/subheadline/two-button pattern, equal feature cards, generic rounded cards, saturated gradient, or Inter-for-everything. Use Newsreader for editorial display and Geist for interface/data. Keep one discreet pill/stamp action, fine rules, asymmetric negative space, and field-journal motion under 800ms with reduced-motion support. If no approved background asset exists, construct the atlas plate with CSS and the actual map/data; do not source new imagery. Preserve keyboard access, semantic headings, 44px mobile targets, loading/empty/error states, and current farm search behavior.

**What to look for:** Useful content at first paint, map code split from initial load, and a composition that still reads as FarmFinder without text.

### Step 4: Visual QA

**Tool:** Codex + browser screenshot
**Input:** Desktop and mobile screenshots plus Step 1 reference/art bible

> Compare the coded FarmFinder screenshots with the approved Field Journal × Living Atlas reference and art bible. List the largest mismatches in composition, hierarchy, spacing, type scale, palette, contrast, atlas focal point, control density, mobile recomposition, focus visibility, text fit, hover states, and perceived speed. Correct the code without making it more generic. Reject left/right marketing structure, centered CTA stacks, equal floating cards, excessive rounded corners, stock imagery, blanket fade-up motion, or saturated accents. Preserve the actual search/map/profile behavior, one-action hierarchy, lazy map loading, reduced motion, and readable farm data. The goal is the same visual feeling with better real-world usability, not pixel imitation.

**What to look for:** Fewer visual accessories, clearer first action, stronger field-atlas identity, and no mobile overflow.

### Step 5: Motion polish

**Tool:** Codex
**Input:** Approved coded layout

> Add only motion that belongs to a Field Journal × Living Atlas. Permit one short contour-mask or ink-rule reveal in the hero, a 2–4px annotation movement for selected records, direct list/map transitions under 300ms, and subtle map-state feedback. Do not use generic fade-up-on-scroll, bounce, continuous parallax, simultaneous entrances, or motion that delays search. Keep animation GPU-light, avoid layout shift, and disable all nonessential movement under `prefers-reduced-motion`. Buttons remain fine-bordered quiet pills; hover may darken the surface and move an arrow by 2px.

**What to look for:** Motion feels like marking a field notebook, never like a template animation library.

### Step 6: Art-bible maintenance

**Tool:** Codex or design review
**Input:** Finished hero and current art bible

> Review the finished FarmFinder experience and update the reusable art bible: palette tokens, Newsreader/Geist type roles, spacing, atlas composition, image policy, rule/border language, button and navigation styles, motion, map/list selection, mobile recomposition, accessibility states, performance constraints, and patterns future sections must avoid. Preserve the Field Journal × Living Atlas identity. Explicitly reject generic SaaS hero structure, equal feature-card grids, decorative numbering without meaning, bright CTA blocks, stock farm-photo mosaics, and motion unrelated to mapping or field notes. Every future component must directly support discovery, trust, participation, or platform operation.

**What to look for:** A short enforceable system that another contributor can apply without inventing a new visual language.

## Acceptance checklist

- The first action reaches farm discovery in one click.
- Search, list, and map remain usable without an account.
- Desktop, tablet, and small-mobile compositions are intentionally different where necessary.
- Keyboard focus never disappears behind sticky UI or dialogs.
- Map load failure leaves search and list usable.
- Text and controls meet AA contrast.
- No separate-company branding or dependency appears.
- No image is introduced without rights, attribution, dimensions, and responsive variants.
- Lint, typecheck/build, smoke tests, responsive screenshots, and reduced-motion checks pass.
