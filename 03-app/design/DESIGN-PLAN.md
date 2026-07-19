# FarmFinder UI Design Plan — v2 "Market Stand"

Synthesized from the nine reference shots in `ui-design-farm-finder/` and grounded in the
existing product shape (`03-app/site/ARCHITECTURE.md`, `03-app/app-vision.md`). One design
system drives two surfaces: the **mobile app** (primary) and the **website** (same tokens,
desktop-first layout).

## 0 · Why v1 was scrapped

v1 leaned on Fraunces italic serif + deep forest surfaces + frosted glass — it read as
luxury-florist editorial ("bougie"), not a comfortable farm-fresh experience, and the
Fraunces/Outfit pairing clashed. v2 keeps the interaction architecture (screens, sheet,
map, dock) and replaces the visual language entirely.

**Archetype: Field journal / farmers-market stand.** The emotional target is a sunny
Saturday market: kraft paper, chalk-marker signage, awning stripes, morning light —
comfortable and hand-made, never glossy or fashion-editorial.

## 1 · What the references teach us (unchanged)

- Garden AI phones → stat chips over imagery, dashed field-plot linework.
- fryd → floating dock with expanding active pill, soft warm page background, big cards.
- Lime → map-first explore: clusters, filter chips, bottom card carousel synced to pins.
- K-Halal finder → farm detail as segmented Info / Buy / Map tabs + trust/source rows.
- Wess → chip rows, list cards with distance + actions.
- FIRION → only its restraint: one deep accent used sparingly, not as full dark theme.

Recurring grammar kept: very large radii, prominent search pill, horizontal chip rows,
floating bottom nav, bottom sheets, save-heart affordance.

## 2 · Design language — "Market Stand"

### Materials → color tokens

Described as materials first: sun-washed butter cream, kraft paper, market-awning green,
tomato-crate red, squash-blossom honey, soil-brown ink.

```
--butter-50:  #FBF7EB   page background (morning light)
--cream-100:  #F6EFDC   raised cards
--kraft-100:  #F1E7CE   kraft paper panels
--kraft-300:  #DFCFA8   borders, dividers
--awning-700: #33632F   deep market-awning green (buttons, dock, footer)
--awning-600: #457F3C   primary green
--leaf-200:   #DCE9C6   soft green fills
--tomato-500: #D95F43   accent: hearts, highlights, hand annotations
--honey-500:  #E0A33C   ratings, seasonal highlights
--soil-900:   #2E2921   ink (warm brown-black, never pure black)
--soil-600:   #6E6355   secondary text
```

Category/product accent colors still mirror `app/lib/farms.ts` for map-pin continuity.

### Type

- **Display + UI:** Bricolage Grotesque — sturdy, warm, characterful grotesque (ink traps,
  friendly weight range). Handles both poster-size headlines and chip labels.
- **Body:** Nunito Sans — comfortable humanist body text.
- **Hand notes:** Caveat, used sparingly for kickers/annotations ("picked this morning",
  arrows) — the chalk-marker voice of a market sign. Never for UI controls.

### Motifs

- **Awning stripe**: thin repeating green/cream stripe band under the top bar and on
  brand moments — the single strongest farmers-market signal.
- **Kraft stamp cards**: solid cream/kraft chips with soil text (replaces v1 glass).
  `backdrop-filter` survives only over the live map.
- **Hand-drawn accents**: dashed field-plot SVG lines, squiggle underlines under key words,
  Caveat annotations in tomato.
- Shape: cards 20–24px radius, pills fully round; soft warm shadow, single elevation level.

### Motion (unchanged)

150–250ms ease-out; sheets slide, dock pill expands, map flyTo. Respect reduced motion.

## 3 · Mobile app — screens (architecture unchanged from v1)

Dock: **Home · Explore · Ask · Saved** (fryd pattern).

1. **Onboarding** — sunrise-over-rows illustration in morning light, kraft stat stamps
   (299 farms / 2 states / 12 guides), one green CTA.
2. **Home** — Caveat greeting, Bricolage headline, search pill, harvest chip row with
   emoji + counts, featured farm cards, coverage stats on kraft.
3. **Explore** — full-screen MapLibre, category-colored pins + green clusters, chip
   overlay, bottom card carousel synced with selection.
4. **Farm detail** — sheet with segmented **Info / Buy / Map** tabs, product tags,
   ways-to-buy grid, contact actions, source/confidence/verified trust rows.
5. **Ask** — directory-grounded question box + suggested prompts.
6. **Saved** — hearted farms (localStorage in demo).

Honesty rules: availability never claimed live; approximate pins labeled; answers always
point back to directory records.

## 4 · Website — same system, desktop grammar

Single-page IA kept (hero → harvest → explore → updates). Sunny butter hero with poster
headline + squiggle underline + Caveat annotation, awning-stripe band, kraft update
ledger, awning-green footer. Identical tokens, pins, and card anatomy as the app.

## 5 · Implementation

- `03-app/design/tokens.css` — single source of tokens for both demos.
- `03-app/design/demo/app.html|css|js` — mobile app demo (vanilla JS + MapLibre CDN).
- `03-app/design/demo/index.html` — website demo.
- `03-app/design/demo/farms.json` — minified copy of the real 299-record dataset
  (data artifact, not hand-written code).
- Production later ports `tokens.css` into `03-app/site/globals.css` and componentizes.
