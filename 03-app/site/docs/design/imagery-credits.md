# Imagery credits

> Every photograph shipped in `public/images/`. Sourced 2026-10-09 via Wikimedia
> Commons, restricted to **public domain and CC0 only** — no attribution chain
> and no share-alike obligation on a cropped, re-encoded derivative. Credits are
> recorded here anyway, because a directory that asks farms to be traceable
> should be traceable itself.
>
> Sourcing rule, per [`../imagery-kit.md`](../imagery-kit.md): U.S. federal works
> (USDA, ARS, NRCS) first, then CC0. **No photograph may be presented as a
> specific listed farm.** These are category and editorial images; a farm's own
> photo only appears on its own listing, and only when the farm provides it.

| Slot | File | Photograph | Credit | Licence | Source |
| --- | --- | --- | --- | --- | --- |
| Home hero band | `images/hero.webp` (218 KB) | USDA Farmers Market Rainy Opening (9128285098) | USDAgov | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:USDA_Farmers_Market_Rainy_Opening_(9128285098).jpg) |
| Harvest tile — Vegetables & greens | `images/products/vegetables.webp` (27 KB) | Healthy Harvest (Unsplash) | Brooke Cagle brookecagle | CC0 | [Commons](https://commons.wikimedia.org/wiki/File:Healthy_Harvest_(Unsplash).jpg) |
| Harvest tile — Fruit, berries & citrus | `images/products/fruit.webp` (42 KB) | 20180830-FAS-PJK-0696 TONED (43654764574) | U.S. Department of Agriculture Preston Keres/Office of Communications-Photography Service | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:20180830-FAS-PJK-0696_TONED_(43654764574).jpg) |
| Harvest tile — Eggs | `images/products/eggs.webp` (92 KB) | Fresh Eggs (Unsplash) | Autumn Mott autumnmott | CC0 | [Commons](https://commons.wikimedia.org/wiki/File:Fresh_Eggs_(Unsplash).jpg) |
| Harvest tile — Beef & cattle | `images/products/beef.webp` (122 KB) | Cattle grazing, Fillmore County, Minnesota | Y1997xf11 | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Cattle_grazing,_Fillmore_County,_Minnesota.jpg) |
| Harvest tile — Pork | `images/products/pork.webp` (149 KB) | Food Hub- Keenbell Farm (20110506-RD-LSC-1391) | USDAgov | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Food_Hub-_Keenbell_Farm_(20110506-RD-LSC-1391).jpg) |
| Harvest tile — Chicken & poultry | `images/products/poultry.webp` (89 KB) | Nick's Organic Farm (20130712-AMS-LSC-0717) | USDAgov | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Nick%27s_Organic_Farm_(20130712-AMS-LSC-0717).jpg) |
| Harvest tile — Honey & bee products | `images/products/honey.webp` (31 KB) | Small Honey Jar with Honeycomb | Alabama Extension | CC0 | [Commons](https://commons.wikimedia.org/wiki/File:Small_Honey_Jar_with_Honeycomb.jpg) |
| Harvest tile — Milk, cheese & dairy | `images/products/dairy.webp` (61 KB) | 20130911-OC-RBN-3764 Agriculture in the United States | USDAgov | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:20130911-OC-RBN-3764_Agriculture_in_the_United_States.jpg) |

`images/field-story.webp` predates this pass: a USDA ARS public-domain produce
photograph, credited in the page itself.

## Replacing one

```bash
# 800x600 tile, ~70 quality, WebP
magick <source>.jpg -resize 800x800^ -gravity center -crop 800x600+0+0 +repage \
  -quality 70 public/images/products/<id>.webp
```

Tiles degrade to the category colour when a file is absent, so a slot can be
emptied without breaking the page. Record any replacement in the table above in
the same change.
