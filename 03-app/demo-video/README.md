# FarmFinder — UX demo video (Remotion)

A ~48-second animated walkthrough of the FarmFinder consumer UX, built with
[Remotion](https://remotion.dev). It recreates the real product screens using
the **Market Stand** design system (see `../site/docs/design/web-design-system.md`)
and **real farm records** pulled from `../site/app/data/farms.json`.

Nothing here connects to the running app — it's a self-contained, deterministic
recreation, so it renders identically anywhere and never depends on live data or
map tiles.

## Scenes

| # | Scene | What it shows |
|---|-------|---------------|
| 1 | Intro | Field-desk open: contour rings ink in, thesis title |
| 2 | Hero | Atlas hero + coverage ledger (299 / 220 LA / 79 MS counting up) |
| 3 | Ask | "Ask the field guide" — a question is typed, grounded answer resolves to 3 real CSA farms |
| 4 | Harvest | Harvest index crop rows with the selected row's season detail |
| 5 | Explore | Search + filters over a synchronized result ledger / living map, ending on a selected field record |
| 6 | Outro | Coverage summary + "expanding region by region" |

## Commands

```bash
npm install
npm run studio     # open the interactive Remotion preview
npm run render     # → out/farmfinder-demo.mp4 (1920×1080, 30fps, h264)
npm run still      # render a single still frame
```

Render a specific frame while iterating:

```bash
npx remotion still FarmFinderDemo out/frame.png --frame=470
```

## Structure

- `src/theme.ts` — design tokens (colors, category colors, fonts) mirrored from the web design system.
- `src/data/farms.ts` — curated real records + the lat/long → panel projection.
- `src/components/` — reusable atoms (`AppFrame`, `AtlasPlate`, `MapPanel`, `Cursor`, `Typewriter`, `atoms`).
- `src/scenes/` — one file per scene.
- `src/FarmFinderDemo.tsx` — sequences the scenes with crossfades; owns the total timeline.
- `src/Root.tsx` — registers the composition (1920×1080 @ 30fps).

## Editing notes

- Fonts (Newsreader for display, Geist for interface) load via `@remotion/google-fonts`.
- Scene durations live in the `scenes` array in `src/FarmFinderDemo.tsx`; adjacent
  scenes overlap by `XFADE` frames for the crossfade.
- Cursor motion in `Ask`/`Explore` is keyframed in **body-relative** coordinates
  (inside `AppFrame`, i.e. below the browser chrome + site header).
