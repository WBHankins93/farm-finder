# FarmFinder brand: Market Stand

> Adopted 2026-10-09. Supersedes the palette and imagery sections of
> [`web-design-system.md`](./web-design-system.md); everything that document
> says about layout, components and performance still holds. Photo sourcing
> rules live in [`../imagery-kit.md`](../imagery-kit.md), credits in
> [`imagery-credits.md`](./imagery-credits.md).

## Why it changed

The previous identity — "Field Journal × Living Atlas" — was coherent and
deliberately restrained: grey-green paper, one rust accent, hairline rules
instead of cards, and no photography by policy. It read as an archive. For a
product whose job is to make someone want to go and buy food this weekend,
that restraint was the problem, not the style.

Two things decided the direction, both evidenced rather than assumed:

- **What shoppers need.** Across the consumer research, the things that move
  people are finding local food at all, trusting the farm, and knowing before
  they go. Availability is the strongest direct predictor of whether someone
  buys local; trust in the producer is what makes them believe the food is good.
  None of that is served by a quieter grey.
- **What the category looks like.** Market Wagon, LocalHarvest and Farmles all
  lead with green and a leaf or sprout. A greener FarmFinder would be a less
  distinguishable FarmFinder.

So: lead with warm cream and a ripe tomato, keep field green for structure, and
put real food on the screen.

## Palette

| Token | Value | Role |
| --- | --- | --- |
| `--paper` | `#fbf6ec` | page canvas, warm cream |
| `--paper-deep` | `#f3e9d4` | kraft, secondary surfaces |
| `--cream` | `#fffdf7` | cards and controls |
| `--ink` | `#2b211c` | soil — body text and dark bands |
| `--muted` | `#6b5e54` | supporting text |
| `--green` | `#1f5136` | structure, trust, active state |
| `--rust` | `#c0392b` | **text-safe** tomato: links, labels, small accents |
| `--tomato` | `#d9482b` | brand tomato: fills, the logo, large type |
| `--sun` | `#f4c95d` | butter — distance pills, step markers, highlights |
| `--brass` | `#8a6a1c` | honey, counts, warm secondary |
| `--river` / `--sky` | `#3f6b78` / `#cfe3ea` | water and quiet information |
| `--rule` | `#e2d6bd` | dividers |

**`--rust` and `--tomato` are not interchangeable.** The brand tomato is only
3.97:1 on cream — fine for a logo or a 40px headline, not for an 11px label.
Small text uses `--rust` at 5.05:1. Every text-bearing token above clears
4.5:1 on both `--paper` and `--cream`; recompute before changing one.

## Type

Plus Jakarta Sans for display, DM Sans for interface and data — unchanged, and
deliberately so. A warm serif was considered and rejected: the repository had
already retired display serifs, and the warmth this brand needed came from
colour, photography and shape rather than from letterforms. Headlines came down
from 132px to a 46–76px clamp, because the hero now shares the screen with a
photograph and a search field.

## The mark

An awning inside a map pin, in `app/lib/marks.tsx` as `BrandMark`. Tomato pin,
cream awning, butter stripes; two flat colours and no stroke, so it survives a
favicon. It replaced a CSS circle with three leaves — a leaf is the one thing
every competitor already uses.

## Imagery

Real photographs, public domain and CC0 only, sourced per
[`../imagery-kit.md`](../imagery-kit.md) and credited in
[`imagery-credits.md`](./imagery-credits.md).

Three rules:

1. **No photograph is presented as a listed farm.** Hero, harvest tiles and
   editorial bands are category images. A farm's own photo appears only on its
   own listing, and only when the farm supplies it.
2. **Photographs go where they carry information**, which is not everywhere.
   NN/g's mobile research is that list thumbnails only help when they differ
   from each other — so result rows get a category colour-and-mark tile, not
   the same stock photo forty times.
3. **Missing imagery degrades to colour.** Tiles read `--tile-img` over the
   category colour; an absent file loses the photo, never the layout.

## Components

- **Shape.** Market stands are crates and awnings: `--radius-sm` 10px,
  `--radius` 14px, `--radius-lg` 20px. Flat ledger rows are gone from the
  harvest grid and the cards.
- **Icons.** Every category, product and way-to-buy has a mark
  (`app/lib/marks.tsx`), and a mark never travels without its text label.
- **Missing data is written out.** "Products not listed", "No way to buy
  listed", "Approximate location — the pin is a city or county centre". 45.8%
  of the release has no product text and 75.8% has no website; a blank space
  reads as a bug, a sentence reads as honesty.
- **One primary action per surface.** Tomato fill, everything else outlined.

## Phone first

Most of this product's use is a phone, so the phone layout is the real one:
the hero stacks photograph → headline → search, harvest tiles are two-up, the
farm sheet clears the fixed dock, and nothing on the map is under 44px.
