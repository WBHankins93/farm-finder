# FarmFinder visual language: research + build plan

> Scope: visual cues, iconography, imagery, shapes, color, gradients, fluid
> animation, and scroll-driven animation — for **web** (live Next.js site) and
> **mobile** (Expo/React Native, not yet built). Ends in a phased plan to gather
> content, produce imagery, and ship updates on both platforms.

## TL;DR

- We already have a strong, opinionated system — **Field Journal × Living Atlas**
  ("Market Stand" warmth): atmospheric palette, rust as the single accent,
  ledger rules instead of shadows, a CSS-drawn atlas hero, restrained motion.
  The job is **not** a redesign. It is to make the visual layer richer and more
  alive **without** importing 2026 slop (saturated gradients, glossy 3D icons,
  blanket fade-up, continuous parallax).
- **Biggest gap:** the imagery layer is wired but empty. `field-story-photo` and
  the product tiles reference `/images/*` and `/local-farm-images/*` that don't
  exist yet, so they silently fall back to flat color. There is no icon system —
  categories are color dots only.
- **Adopt the technique, reject the trend.** Use 2026's genuinely better
  mechanics — CSS scroll-driven animations (compositor-only, zero main-thread
  JS), variable/adaptive icons, dark-mode-aware assets, Reanimated UI-thread
  gestures on mobile — and hold the line on the existing anti-generic rules.
- Deliverables: one **field-mark icon set** (13 categories + 5 ways-to-buy),
  a **licensed photo kit** (hero + category tiles + a few editorial farm shots),
  a **motion spec** upgraded to scroll-timeline, and a **mobile visual token +
  component pass** so the Expo app launches on-system, not stacked-web.

---

## 1. Current state (audit)

| Layer | Web (live) | Mobile (planned) |
|---|---|---|
| Visual cues | Ledger rules, section numbers, index counters, location/confidence stamps, category **color dots** | Wireframes only; cues implied, no assets |
| Icons | None. Color dots + text labels; hand-CSS brand mark, CSS search glyph | None |
| Images | Wired but **absent** (`/images/hero.webp`, category tiles, `field-story-photo`) → degrade to flat color | None |
| Shapes | Circles (pins/stamps), fine 1px rules, pills, blobby CSS atlas contours | Native sheets/cards implied |
| Color | 10 tokens in `globals.css`, `color-scheme: light` only | Tokens to be shared via `packages/design-tokens` |
| Gradients | Subtle, structural only (grid lines, radial map texture, 108° paper split). No saturated gradients — by policy | n/a |
| Fluid animation | `atlas-pulse` pins, hover micro-moves, `map-spin`. Reduced-motion honored | Reanimated recommended, not built |
| Scroll animation | **None by policy** ("no blanket fade-up"). `scroll-behavior: smooth` only | n/a |

**Hard constraints (do not relitigate — from design system + owner feedback):**
- Type: **Plus Jakarta Sans** (display) + **DM Sans** (body/UI) only. Serif /
  script / novelty faces are **banned** (Fraunces, Outfit, Bricolage, Nunito,
  Caveat). Note: the older `web-design-system.md` still says "Newsreader/Geist" —
  that is **stale**; the shipped code and owner decision are Jakarta + DM Sans.
- One accent (**rust `--rust #c65e36`**) marks selection or a single key action.
  Green is structure. Category color always travels with text, never alone as
  the sole signal.
- Rules and shared edges replace floating shadows. Radius reserved for pills,
  stamps, pins.
- Motion belongs to a field notebook: annotation reveals, not template
  animation. No continuous parallax, no bounce, no motion that delays search.
- No image ships without license, attribution, dimensions, and responsive
  variants. Performance first (map is lazy; marks are CSS/SVG, not an icon lib).

---

## 2. Research synthesis (2026 practice → FarmFinder decisions)

Each subsection: what current practice says → what we take → what we refuse.

### 2.1 Visual cues (hierarchy, wayfinding, trust)
Directory/marketplace products in 2026 lean on *scannable single-signal* cues and
"variable/adaptive" elements that respond to context. We already do the
evidence-bearing version of this (record IDs, confidence stamps, source ledger).
- **Take:** formalize a small cue vocabulary — index number, category field-mark,
  ways-to-buy chips, location-confidence stamp, freshness/"updated" stamp — and
  reuse it identically on web and mobile so the two clients read as one product.
- **Take:** dual-encode every category (icon **+** color **+** text) so color is
  never the only signal (accessibility + honesty).
- **Refuse:** decorative badges, trust theater, gamified marketplace stickers.

### 2.2 Iconography
2026 icon trends split into (a) hyper-minimal thin-line geometry and (b) glossy
gradient/3D app icons. Only (a) fits a field guide.
- **Decision:** commission **field-marks** — a single-weight, ~1.75px stroke,
  24px-grid **line-icon set** drawn like surveyor/field-guide glyphs, not generic
  UI icons. Monochrome (inherits `currentColor`), so one file works on paper,
  cream, or green and adapts to dark mode by inheritance.
- **Coverage (13 category marks):** vegetables, fruit, eggs, beef, pork, poultry,
  honey, dairy, seafood/crawfish, rice/grains, flowers/nursery, mushrooms, mixed.
  **(5 ways-to-buy marks):** farmers market (stall), on-farm sales (gate/barn),
  CSA (box), delivery/ships (truck), order online (screen/bag).
- **Refuse:** an icon *library* dependency (bundle cost, off-brand metaphors),
  gradients/3D, duotone, filled pictograms, emoji.
- **Delivery:** inline SVG sprite (`public/marks.svg` + `<use>`), tree-shaken;
  React Native gets the same paths via `react-native-svg`.

### 2.3 Imagery / photography
The system is deliberately image-light ("the atlas is the picture"). That stays
true for the hero, but honest, warm photography earns its place in the **field
story** band and **category education**, where a real market/field builds trust.
- **Decision:** a **small, curated, public-domain-first** photo kit (see §3.2),
  color-graded toward the palette, always paired with a caption/credit. Duotone
  or a green ink-wash overlay keeps photos from fighting the atlas.
- **Refuse:** stock-photo hero people, equal photo-card mosaics, AI farm photos
  presented as real places, uncredited or unlicensed images.

### 2.4 Shapes
Keep the established language: circles (pins, stamps, confidence), hairline rules,
pills, and the organic atlas contours.
- **Take:** extend contour/parcel geometry as **section dividers** and as the
  mobile launch/empty-state motif, so structure is recognizable with text
  removed (the system's north star).
- **Refuse:** rounded "card grid" softness, drop shadows, glassmorphism beyond the
  existing subtle sticky-bar blur.

### 2.5 Color
Palette is finished and good. Two additions:
- **Dark mode.** Site is `color-scheme: light` only; mobile app drawers and OS
  dark mode are now table stakes. Define a **dark token map** (paper→deep field
  ink, cream→warm charcoal, keep rust/green identities) as CSS custom-property
  overrides + a shared token package. Mark-set is `currentColor`, so it's free
  there.
- **Semantic tokens** (`--surface`, `--surface-raised`, `--text`, `--accent`,
  `--line`) layered over the raw material tokens, so web CSS and RN consume the
  same names.

### 2.6 Gradients
Trend = loud analogous gradients everywhere. **Policy = no.**
- **Take:** gradients remain **structural and near-invisible** — the paper split,
  grid lines, radial map texture, and one new tool: a low-contrast **duotone
  photo grade** (rust↔green or paper↔green) to unify imagery.
- **Refuse:** any saturated, decorative, or purple/SaaS gradient; gradient text;
  gradient buttons.

### 2.7 Fluid animation
2026 consensus: run animation off the main thread — compositor (`transform`/
`opacity`) on web, UI thread (Reanimated shared values + Gesture Handler) on
mobile — and test on real devices.
- **Web take:** keep motion tiny and diegetic. Allowed: one contour/ink reveal,
  2–4px annotation nudge on selection, <300ms list↔map, pin pulse, hover arrow
  nudge. Everything on `transform`/`opacity` only.
- **Mobile take:** **Reanimated + Gesture Handler** for the map result **bottom
  sheet** (drag), list momentum, and tab/press feedback; `withSpring`/`withTiming`
  in worklets; `runOnJS` only to commit React state.
- **Refuse:** anything that animates layout props (width/height/margin), blanket
  entrance choreography, or motion that blocks the first search.

### 2.8 Scroll-driven animation
The big 2026 shift: **CSS scroll-driven animations** (`animation-timeline: scroll()
/ view()`, `animation-range`) give scroll-linked effects with **zero main-thread
JS** and universal support. This is the one place we can add life the system
currently forbids — *because the objection was to janky JS fade-up, which this
removes.*
- **Decision:** a **restrained, progressive-enhancement** scroll layer:
  - Hero atlas contours draw/drift via `view-timeline` as the hero scrolls out
    (replaces any temptation for a JS parallax).
  - Section index numbers and the coverage ledger reveal on entry with a **short
    rule-draw**, not a fade-up — `@supports (animation-timeline: view())` only,
    and fully disabled under `prefers-reduced-motion`.
  - A slim **scroll-progress "survey line"** in the header (compositor-only).
- **Mobile:** the analogous effect is scroll-position-driven header/collapse and
  sheet snap via Reanimated `useAnimatedScrollHandler` — same *feeling*, native
  mechanism.
- **Refuse:** scrolljacking, pinned full-screen scrollytelling, IntersectionObserver
  fade-up on every block, GSAP/Lenis dependencies for what CSS now does natively.

---

## 3. The plan

Four workstreams. Each has an owner-facing acceptance bar. Ordered so nothing
blocks on the mobile app existing.

### Phase 0 — Foundations (design tokens + audit fixes) · web
1. Add **semantic token layer** + **dark token map** to `globals.css`
   (`:root` light, `@media (prefers-color-scheme: dark)` + `[data-theme]`
   override). No visual change in light mode.
2. Extract raw + semantic tokens into `packages/design-tokens` (per mobile
   architecture doc) as the single source for web CSS vars and RN.
3. Fix the **silent-fallback references**: either ship the assets (Phase 2) or
   point `field-story-photo`/tiles at real files; document the fallback contract
   in `imagery-kit.md`.
- **Done when:** tokens shared, dark mode defined, no reference points at a
  missing asset without an intentional color fallback.

### Phase 1 — Content gathering
Gather before generating. Two tracks:
- **1a. Copy/data cues** — per-category one-line "what/when" (season windows for
  the harvest index), ways-to-buy microcopy, confidence-stamp wording. Source
  from existing `farms.json` + LSU AgCenter notes already in the dataset.
- **1b. Imagery sourcing list** — build a spreadsheet: slot → source → URL →
  license → attribution → dimensions. Sources, **free-for-commercial, PD first**
  (see `docs/imagery-kit.md`): USDA/ARS (public domain, most on-brand),
  Unsplash, Pexels, Wikimedia (check per-file). **Avoid USDA SNAP-Ed
  (non-commercial).** Prefer Louisiana/Mississippi/Gulf-South shots where honest.
- **Done when:** every image slot in §3.2 has a cleared, attributed source row.

### Phase 2 — Imagery + icon production
- **2a. Field-mark icon set** (§2.2): draw 18 SVGs on a 24px grid, 1.75px stroke,
  `currentColor`, optical-consistency pass; assemble `public/marks.svg` sprite +
  a typed `Mark` component (web) and shared paths for `react-native-svg` (mobile).
- **2b. Photo kit** (§2.3): pull per the sourcing list, then optimize to WebP
  (`~1600px` hero, `~800px` tiles, q72) per the existing `imagery-kit.md` script;
  commit to `public/images/`. Apply the duotone/ink-wash grade for consistency.
- **2c. Hero policy:** keep the CSS atlas as the hero (no raster hero until
  storage/rights/responsive variants exist). Optionally add a **background photo
  plate** only if it passes the "layout still reads with all text removed" test.
- **Done when:** marks render at 16–24px crisp; tiles/field-story show real
  graded photos with visible credits; Lighthouse/payload not regressed.

### Phase 3 — Web integration
1. Replace category **color dots** with **mark + color + text** across: harvest
   index, explorer category row, farm cards, map key, profile header, related
   farms.
2. Wire ways-to-buy marks into service chips.
3. Add the **scroll-driven layer** (§2.8) behind `@supports` +
   `prefers-reduced-motion`, compositor-only.
4. Ship **dark mode** (toggle + system-preference) using Phase 0 tokens.
5. Visual QA pass (desktop + mobile-web screenshots) against the art bible;
   verify AA contrast, focus visibility, 44px targets, no mobile overflow.
- **Done when:** every category is dual-encoded, motion degrades cleanly, dark
  mode passes contrast, and the site still reads as FarmFinder with text hidden.

### Phase 4 — Mobile (Expo/React Native) visual system
Sequenced *after* the read-only API/token contracts, per the mobile arch doc.
1. Consume `packages/design-tokens`; build RN primitives (Surface, Rule, Chip,
   Stamp, Mark) mapping 1:1 to web cues — recomposed natively, **not** stacked web.
2. **Reanimated + Gesture Handler**: draggable map result bottom sheet, collapsing
   header on scroll, list momentum, press feedback (§2.7).
3. Field-marks via `react-native-svg`; contour motif for launch/empty states.
4. Respect Dynamic Type, dark mode, reduced motion, VoiceOver/TalkBack labels
   (farm, place, selection, confidence).
- **Done when:** Discover/Results/Map/Farm screens use the shared cue vocabulary,
  60fps sheet/scroll on a physical mid-range device, cold launch < 2.5s.

---

## 4. Acceptance checklist (whole effort)
- [ ] One cue vocabulary shared across web + mobile (index, mark, ways-to-buy,
      confidence, freshness).
- [ ] Categories dual-encoded (icon + color + text) everywhere; color never solo.
- [ ] 18 field-marks, single-weight line, `currentColor`, crisp at 16px.
- [ ] Photo kit fully licensed/attributed; WebP + responsive; duotone-graded.
- [ ] Hero remains CSS atlas unless a raster plate passes the text-removed test.
- [ ] Scroll + fluid motion are compositor/UI-thread only; disabled under
      reduced-motion; nothing delays first search.
- [ ] No saturated/decorative gradients; no shadow/card-grid drift; type stays
      Jakarta + DM Sans.
- [ ] Dark mode defined via tokens and passes AA on both platforms.
- [ ] Lint, typecheck/build, tests, responsive + reduced-motion screenshots pass.

## 5. Open decisions for the owner
1. **Dark mode now or later?** Adds token work but is cheap if done at Phase 0.
2. **Photos in the field-story band** — yes to real graded photography, or stay
   fully image-light and atlas-only?
3. **Icon commission** — hand-draw the 18 field-marks in-house, or brief it out
   to a designer against this spec?
4. **Scope of this branch** — land Phases 0–3 (web) here and split mobile
   (Phase 4) to its own branch once the API/token packages exist? (Recommended.)

## Sources
- [CSS Scroll-Driven Animations guide (2026)](https://cssawwwards.com/blog/css-scroll-driven-animations-guide-2026)
- [Mastering CSS Scroll Timeline (2026)](https://dev.to/softheartengineer/mastering-css-scroll-timeline-a-complete-guide-to-animation-on-scroll-in-2025-3g7p)
- [CSS innovations 2026: features that replace JavaScript](https://locallylost.com/guides/css-innovations-2026-features-that-replace-javascript/)
- [React Native Reanimated: smooth animations (2026)](https://oneuptime.com/blog/post/2026-01-15-react-native-reanimated/view)
- [Mastering fluid animations with Reanimated](https://react-news.com/mastering-fluid-animations-a-deep-dive-into-the-latest-react-native-reanimated-news-and-best-practices)
- [Icon design trends 2026 (Envato)](https://elements.envato.com/learn/icon-design-trends)
- [Trending icons: top icon design trends for 2026 (ManyPixels)](https://www.manypixels.co/blog/illustrations/icon-trends)
