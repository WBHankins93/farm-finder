# FarmFinder imagery kit

> Research + drop-in plan for the photography the app is missing. Everything
> here is **free for commercial use**; verify each individual image's license
> before shipping (they vary).

## Where to get free, on-brand photography

| Source | License | Best for | Notes |
|---|---|---|---|
| **USDA** (via [rawpixel.com/usda](https://www.rawpixel.com/usda), [USDA Flickr](https://www.flickr.com/photos/usdagov), ARS Image Gallery) | **Public domain** (US federal works) | Farmers markets, produce, growers, livestock | Most on-brand + safest. Commercial OK. |
| **Unsplash** ([unsplash.com](https://unsplash.com)) | Unsplash License — free, commercial, no attribution required | Hero, editorial farm/field shots | Deep, high quality. |
| **Pexels** ([pexels.com](https://pexels.com)) | Pexels License — free, commercial | Category tiles, people-at-market | |
| **Public Domain Pictures** ([publicdomainpictures.net](https://www.publicdomainpictures.net)) | Public domain | Fillers, textures | |
| **Wikimedia Commons** | PD / CC (check per file) | Regional / specific crops | Attribution for CC-BY. |

**Avoid:** the USDA **SNAP-Ed** photo gallery — those are restricted to
**non-commercial** use. Stick to core USDA/ARS PD photos.

## What to pull (search terms per slot)

The app is wired for these files. Fetch one image per slot, then run the
optimize step below.

**Hero** → `public/images/hero.jpg` — a wide, warm field/market at golden hour.
Search: *"farmers market morning"*, *"vegetable field rows sunrise"*.

**Category tiles** → `public/images/categories/<id>.jpg` (used by the "Browse
the harvest" cards):

| File | Search term |
|---|---|
| `produce.jpg` | market vegetables crates |
| `mixed.jpg` | small mixed farm barn |
| `meat.jpg` | pasture cattle / butcher case |
| `honey.jpg` | honey jars / beekeeper frames |
| `dairy.jpg` | dairy cows / creamery |
| `seafood.jpg` | gulf shrimp / oysters dock |
| `rice.jpg` | rice paddy field |
| `urban.jpg` | rooftop / greenhouse microgreens |
| `value-added.jpg` | jams / bread / farm kitchen |

## Optimize before committing (keep the repo + payload light)

Target ~1600px hero / ~800px tiles, WebP, ~72 quality. With `cwebp` or
ImageMagick:

```bash
# tiles
for f in public/images/categories/*.jpg; do
  cwebp -q 72 -resize 800 0 "$f" -o "${f%.jpg}.webp"
done
# hero
cwebp -q 72 -resize 1600 0 public/images/hero.jpg -o public/images/hero.webp
```

Commit the optimized `.webp` (a tile is ~30–60 KB). `public/images/` is **not**
git-ignored — these are curated assets, unlike the generated feed.

## How it's wired (already in this PR)

- Category cards read `--tile-img: url(/images/categories/<id>.webp)` with the
  category color as the fallback layer, so **missing images degrade to the
  current color design — no broken image icons.**
- Add `public/images/hero.webp` and the hero picks it up the same way.

Drop the files in, redeploy — no code changes needed.
