# Featured-readiness review — 2026-09-15

> Point-in-time review of the production candidate on branch
> `claude/map-design-upgrade-finish`, done by walking the running app as a
> first-time visitor trying to find a farm. Companion to
> [`deployment-readiness-2026-09-14.md`](./deployment-readiness-2026-09-14.md),
> which covers the serving layer; this file covers what a visitor actually gets.
> Map-design intent is recorded separately in
> [`../design/map-basemaps.md`](../design/map-basemaps.md).

## Verdict

**Ready after named fixes** — two of them now, both small, both on the path a
Featured link puts people on. The map work in this branch is done and verified,
and the result cards were rebuilt in a follow-up pass (item 3 below is fixed).
What is not ready is the twenty seconds *before* the map: a visitor who types a
city can currently see nothing happen at all.

A third item is not a fix but a constraint on the claim: for the flagship query,
most records carry no products and no website. That shapes what the post can
honestly say, and it is a data-lane problem, not a site bug. The cards now name
those gaps out loud rather than showing blank space, which is the most the site
can do about it.

## How this was checked

The built-in browser pane has no WebGL, so MapLibre cannot run in it. Everything
below was measured in headless Chrome 1440×900 and 390×844 with SwiftShader,
driven over CDP against the local dev server on the current release
(72,396 collected → 68,618 eligible). Screenshots were taken at both widths.

The no-WebGL pane turned out to be useful evidence in its own right: the map
degrades correctly there, showing "Keep browsing in the farm list" with search,
filters and profiles still working, and hiding the basemap switch rather than
leaving it inert.

## What a first-time visitor hits, in order

### 1. Typing a city can fail silently — blocker

Type `madison wi` (no comma) and press the button. The URL becomes
`?sort=distance`, the page does not move, and the only feedback is a status line
**3,604px below the fold** reading "Choose a city to begin nearby search."
Nothing visible happens.

The cause is a place lookup that needs the comma: `/v1/places?q=` returns 4
matches for `Madison`, 1 for `Madison, WI`, and **0 for `madison wi`**. The hero
field is a bare `<input>` — no suggestion list, no `<datalist>`, no combobox
role — so nothing steers the visitor toward a spelling that works, and nothing
tells them when theirs did not.

### 2. Even a successful search does not move the page — blocker

Submit `Madison, WI`. The query is right, the results load, the URL becomes
`?near=madison-wi&radiusMiles=50&sort=distance#discover` — and `scrollY` stays
at **0** with `#discover` 3,604px below. The hero looks identical before and
after. Pressing Enter in the field does nothing at all; only the button submits.

### 3. Every result card is rendered into a 35px column — fixed 2026-09-15

`.farm-card-main` declares `grid-template-columns: 35px 1fr auto` — three tracks,
for a card index, the body and the arrow. `FarmCard` in
`app/components/discovery-workspace.tsx` renders **two** children. The body
therefore lands in the 35px index track and the arrow takes the 1fr track.
Measured: `gridTemplateColumns: "35px 459.578px 0px"`, body width **35px** inside
a 555px card. The text only remains readable because it overflows, which is why
"Madison, WI · Area not listed" wraps one word per line in every screenshot.
`.card-contact { margin-left: 65px }` is aligned to the same absent column.

This was the first thing anyone saw on a Featured link, and it read as broken.

**Fixed**, along with the density problem underneath it. The card now declares
the two tracks it renders, and the layout was rebuilt around what a person is
actually comparing: an icon-led meta line, the name clamped to two lines, and a
compass needle rotated to the farm's real bearing beside the distance
("↘ 0.8 mi SE"). Where data is missing it says so — "Products not listed",
"No way to buy listed" — instead of leaving a blank. Measured at 1440×900: card
height 139px against roughly 250px, body width 435px against 35px, and 5.5
results visible per panel against about 3.

### 4. The flagship query returns names and little else — claim constraint

`/v1/farms?near=madison-wi&radiusMiles=50` returns 30 rows on page one. Of those,
**4 carry any product text and 0 carry a website.** The first result, Dane County
Farmers' Market, has empty `productsText`, empty `marketPresence`, and every
service flag false. The hero promises "what they grow or raise, and the best
confirmed way to buy"; for 26 of those 30 rows the page can answer neither.

Across the whole published release:

| Measure | Rows | Share |
| --- | --- | --- |
| No product text at all | 31,435 | 45.8% |
| No website | 51,984 | 75.8% |
| Neither | 27,606 | 40.2% |

The 75.8% figure already appears in the 2026-09-14 report as 51,984 and is not
new. The 45.8% with no products is the one that bites, because products are what
the page is organised around.

### 5. Some records are operator names, not farm names — trust

2,115 published rows (3.1%) have ALL-CAPS names, concentrated in Louisiana (953)
and California (608). 729 of those are `SURNAME, FORENAME` shaped — 709 of them
in Louisiana. Searching New Orleans returns, as its top three results,
"ALLISON III, FRED", "AMY COULTER SCHULLY" and "BAHAM, HOMER LOUIS".

These look like operator names lifted from a licence register rather than farm
names. Nothing here breaches the privacy gate — no contacts or addresses are
exposed, and the publish-time gate passes clean — but a public directory that
presents a person's name as a farm invites the question anyway, and it is the
kind of thing a Featured audience notices.

## What this branch fixed

All verified in-browser at both widths; see
[`../design/map-basemaps.md`](../design/map-basemaps.md) for the reasoning.

| Was | Now |
| --- | --- |
| Map pane sized to the full result list (~7,400px); canvas clamped to `424×4096`, so the map drew at the wrong aspect | `767×778` at 1440×900; the list scrolls, the map fills its pane |
| Basemap switch at `y=8038`, ~8,000px below the fold | `y=1417`; reachable, and still reachable with a farm selected |
| Selecting a farm buried the basemap switch under the detail card, desktop and mobile | Switch is in a left rail; the card cannot reach it |
| Attribution and zoom buttons drawn across the farm detail card | Card outranks map furniture; attribution stays visible below it |
| Map ran under the fixed mobile dock, clipping the farm sheet | Explorer stops above the dock |
| Map tools 38px on mobile; close button 28px | No control on the map under 44px |
| `detailLayers()` added a `building-3d` MapLibre refuses and a duplicate POI layer | Paint overrides on Liberty's own extrusion layer, plus tilt and z18 so the detail is reachable |
| Option hints reachable only by hover; basemap change announced nothing | Visible hints referenced by `aria-describedby`, and a polite status region describing the whole option set |
| Result cards: body squeezed into a 35px track, ~250px tall, ~3 visible | Two-track grid, 139px tall, 5.5 visible, icon-led, with a compass needle on the distance |
| Map: one fixed pin ramp, a static four-swatch legend, no settings | A Map options panel — basemap, pins/density/both, category highlight, farm names, tilt, scale bar — over a retuned pin ramp, with the legend as a shortcut into it |

## Backlog, smallest first

1. ~~Give `.farm-card-main` the two columns it actually renders.~~ **Done**, and
   the card was made dense and icon-led at the same time — see above.
2. **Scroll to `#discover` on a successful hero submit**, and submit on Enter.
3. **Fail loudly when a place does not resolve**: keep the visitor at the hero,
   put the message next to the field, and suggest the nearest matches — the
   `/v1/places` response that returns nothing for `madison wi` returns four for
   `Madison`, so the suggestions already exist.
4. **Type-ahead on the hero field** from `/v1/places`, which removes the class of
   failure in 1–3 rather than patching it.
5. **Decide what a card says when a farm has no products and no website.**
   40.2% of the release is in that state. Either the card names the gap honestly
   or those rows sort below ones that can answer the page's question.
6. **Triage the 729 `SURNAME, FORENAME` rows**, 709 of them Louisiana. Data lane,
   one state, one session, per AGENTS.md.
7. **Run the eight browser acceptance checks** in
   [`../testing/discovery-acceptance.md`](../testing/discovery-acceptance.md),
   still outstanding from 2026-09-14. This pass covered the map's share of them
   (tap targets, reduced motion, keyboard reach, tile-failure fallback) but not
   GPS, focus trapping, or back/forward.
8. **Measure the basemap FPS gap on real hardware** with
   `npm run map:review`. Software rendering gave 9 fps (guide) against 6 fps
   (detailed) at 1600×900 — the right direction, but the absolute numbers mean
   nothing on SwiftShader.

Items 2 and 3 are the named fixes the verdict still depends on. Nothing in this
list is a redesign.

## What is genuinely good, and worth leading with

Worth saying plainly, because the list above is all problems: the parts that are
hard are the parts that work. 50 states and 68,618 published records served from
a compact index inside a 128MB isolate; privacy gates that fail the build rather
than warn; counts derived from the feed rather than typed; server-side clustering
over 54,821 mappable points; honest "approximate location" labelling; and a map
that degrades to a usable list when WebGL is missing. The gap is the last mile of
presentation, not the engineering underneath it.
