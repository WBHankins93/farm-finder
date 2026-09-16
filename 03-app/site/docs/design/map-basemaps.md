# The explorer's two basemaps

> Intent record for the map-design pass on branch `claude/map-design-upgrade-finish`,
> 2026-09-15. Code: [`app/lib/map-styles.ts`](../../app/lib/map-styles.ts),
> [`app/components/farm-map.tsx`](../../app/components/farm-map.tsx), the map
> rules in [`app/globals.css`](../../app/globals.css). Tests:
> [`tests/map-styles.test.ts`](../../tests/map-styles.test.ts).

## Why there are two

One map cannot do both jobs this directory asks of it.

**Scanning.** The common case is a bounded result set — a few hundred farm pins
and server-side clusters over a metro area — and the question is *where are they*.
A full OSM basemap fights that: 111 layers of buildings, POIs and street names
competing with the thing the page exists to show. `guide` is hand-authored for
this: 19 layers, saturated land, bold road casings, and labels only for places
big enough to orient by. It is the default and it is what the map opens on.

**Arriving.** Once someone has picked a farm, the question changes to *how do I
get in*. That needs street names, driveways, building footprints — everything
`guide` deliberately drops. `detailed` is OpenFreeMap's Liberty style, which has
all of it.

Both read the same OpenMapTiles vector source, so switching re-rasterises tiles
the browser already has rather than refetching geography.

## What this pass changed, and one thing it corrected

The in-progress work this pass picked up added two new layers on top of Liberty:
a `building-3d` fill-extrusion and a `poi-landmark` symbol layer. The intent was
right and the implementation could not work:

- **Liberty already ships `building-3d`**, a fill-extrusion over the same
  `render_height` / `render_min_height` fields, from z14. MapLibre refuses a
  second layer with an id that is already taken — it fires an error and returns —
  so the extrusion override never applied to anything.
- **Liberty already labels POIs** from z15 through three rank-banded layers
  (`poi_r1`, `poi_r7`, `poi_r20`). The added layer filtered `rank <= 12`, which
  overlaps two of them, so every landmark in that band would have been labelled
  twice. The stated worry — that POI labels would bury the farm pins — could not
  happen anyway: the pins are installed after the style loads and therefore draw
  above everything in it.

So the layers are gone and what survives is the part Liberty genuinely lacks,
expressed as paint overrides on Liberty's own layer (`detailPaint`):

| Override | Liberty's default | Why |
| --- | --- | --- |
| `fill-extrusion-color` | one flat grey for every building | a height ramp, so massing reads without shadows |
| `fill-extrusion-opacity` | `0.8`, applied the instant z14 is crossed | a 14 → 15.5 fade, so a city does not pop into 3D at the zoom edge |

Three further changes make the mode deliver what its label promises:

- **`maxZoom` 16 → 18.** Liberty's extrusions start at z14 and its POI labels at
  z15. Stopping at 16 put the last mile — the driveway, the barn, the entrance
  you actually turn into — out of reach of the toggle that advertises it.
- **The map tilts to 52° when you choose Full detail at z15 or above**
  (`detailZoom`, `detailPitch`). An extrusion at pitch 0 is a tinted roof;
  without tilt the re-paint buys nothing. The zoom condition is the whole rule:
  tilting a regional view pulls in a horizon of tiles and shows no massing, and
  a camera that moves on its own while someone is scanning pins is worse than
  flat buildings. Switching back to Field guide always flattens.
- **A compass, with `visualizePitch`.** Tilt and rotation were already reachable
  by ctrl-drag with no way back to north-up. Now there is one, and the current
  tilt is legible at a glance.

Changing the basemap deliberately does **not** count as a user camera change, so
it never arms *Search this area* and never re-queries results.

## Map furniture

The controls moved, because two of them were unreachable:

- **The basemap switch** shared the bottom-left corner with the farm detail
  card. The card is wider, taller and painted later, so selecting a farm buried
  the switch completely — and on mobile, where the card is full-width, it buried
  it there too. The switch now sits in a left rail under the map tools, with the
  category legend below it, and stays visible whatever else is open.
- **Zoom and pitch** moved to the top-right for the same reason: the bottom of
  the map belongs to the detail sheet. Attribution stays at the bottom, and both
  sheets now clear it — it is a licence requirement, not decoration.
- **The map pane was not viewport-sized at all.** `.farm-list` declared
  `overflow-y: auto` but, as a column flex item with the default
  `min-height: auto`, it sized to its content instead of scrolling. The grid row
  grew to the full result height and `.map-panel { height: 100% }` inherited it:
  a ~7,400px map pane whose canvas the browser clamped at its 4,096px limit, so
  the map rendered at the wrong aspect ratio, and whose controls sat roughly
  8,000px below the fold. `flex: 1 1 0; min-height: 0` is what makes the
  scroller scroll. Measured at 1440×900 before and after: canvas `424×4096` →
  `767×778`, basemap switch at `y=8038` → `y=1417`.
- **Mobile.** Every control on the map is at least 44px, and the explorer now
  stops above the fixed `.mobile-dock` instead of running underneath it.

## Accessibility

- Each option's hint reached only hover users, via `title`. It is now also an
  `aria-describedby` target, so it reaches keyboard and screen-reader users.
- Swapping the basemap redraws the entire map and used to say nothing; a polite
  status region now names the active basemap and what it shows.
- The tilt uses `easeTo`, which MapLibre makes instant under
  `prefers-reduced-motion: reduce`.
- Without WebGL the map is replaced by a fallback that keeps the list, filters
  and profiles usable, and the basemap switch is hidden rather than left inert.

## The review harness

`dev/map-review.template.html` is a side-by-side of the two basemaps: synced
cameras, five zoom presets from region to block, three places chosen to break a
basemap in different ways (sparse rural roads, a dense label-fighting grid, a
coastline), a pin toggle, a tilt toggle, and a pan stress test that measures FPS
rather than guessing at it. Pins are 50 real published farms near each centre,
read from the current release.

```bash
cd 03-app/site && npm run map:review     # writes dev/map-review.html
```

It reads `guideStyle()` and `detailPaint` from the same module the app imports,
so it cannot drift from what ships, and it reads farms from
`01-database/pipeline/build/app-farms.json` — a reproducible pipeline artifact,
so build it first with `python3 01-database/pipeline/run.py --publish` if it is
not there. The generated page is not committed.

**Acceptance criteria it exists to check**, in the order the template presents
them:

1. At z5–z9 the guide style stays legible under a dense national pin set, and
   pins remain the most prominent thing on it.
2. At z12 both styles name enough to orient by; the guide style's labels do not
   collide with pins.
3. At z15–z17 the detailed style shows street names, landmarks and building
   massing, and the guide style stays deliberately quiet.
4. Under the pan stress test the guide style measures a materially higher frame
   rate than the detailed style. That gap is the toggle's entire reason to
   exist; if it closes, the guide style has lost its purpose.

Run it on real hardware. Software rendering (a headless browser on SwiftShader)
gives a usable *ratio* between the panels but its absolute FPS means nothing.
