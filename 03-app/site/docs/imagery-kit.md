# FarmFinder visual asset kit

FarmFinder uses existing, maintained visual libraries before commissioning or
drawing new assets. This keeps the interface consistent, accessible, and easy
to extend as the directory grows.

## Icon system

Interface, product, farm-category, service, map, status, and action icons come
from [`@phosphor-icons/react`](https://github.com/phosphor-icons/react), pinned
in `package.json`. Phosphor is MIT-licensed and provides the duotone family used
throughout FarmFinder.

Rules:

- Use a Phosphor icon before drawing a new SVG.
- Use `weight="duotone"` for product and category marks; use the default weight
  for compact interface actions.
- Pair icons with visible text for actions and filters. An icon does not replace
  an accessible name.
- Use `app/lib/marks.tsx` for category, product, and service metaphors so the
  same meaning appears in cards, filters, map details, and profiles.
- Import server-rendered icons from `@phosphor-icons/react/ssr`; client
  components use `@phosphor-icons/react`.

## Photography license

The eight harvest-index photos are distributed under the
[Pexels license](https://www.pexels.com/license/). They may be used and modified
for free, including commercially. Attribution is not required, but FarmFinder
keeps the creator and source here as durable provenance. Do not sell an
unaltered copy, imply that a pictured person or brand endorses FarmFinder, or
redistribute the images as a stock library.

| Local asset | Subject | Creator | Source |
|---|---|---|---|
| `public/images/products/vegetables.webp` | Farmers-market vegetables | Natalia S | [Pexels 28991059](https://www.pexels.com/photo/vibrant-farmers-market-with-fresh-vegetables-28991059/) |
| `public/images/products/fruit.webp` | Plums, apples, pears, and honey | Vladimir Gladkov | [Pexels 6208141](https://www.pexels.com/photo/plumes-apples-and-honey-in-jar-6208141/) |
| `public/images/products/eggs.webp` | Basket of farm eggs | Betül Batmaz | [Pexels 31037330](https://www.pexels.com/photo/wicker-basket-with-fresh-farm-eggs-outdoors-31037330/) |
| `public/images/products/beef.webp` | Cattle on pasture | Julissa Pires | [Pexels 8633334](https://www.pexels.com/photo/cattle-in-a-pasture-at-a-farm-8633334/) |
| `public/images/products/pork.webp` | Pigs on pasture | Thomas P | [Pexels 17971059](https://www.pexels.com/photo/pigs-on-pasture-17971059/) |
| `public/images/products/poultry.webp` | Pastured chickens | Julissa Pires | [Pexels 4566557](https://www.pexels.com/photo/farm-chickens-pasturing-on-meadow-4566557/) |
| `public/images/products/honey.webp` | Unbranded jar of honey | Nhà Mật | [Pexels 9105959](https://www.pexels.com/photo/glass-jar-with-honey-on-wooden-table-9105959/) |
| `public/images/products/dairy.webp` | Dairy cows in an open barn | Mark Stebnicki | [Pexels 11679510](https://www.pexels.com/photo/cows-on-a-dairy-farm-11679510/) |

The field-story image at `public/images/field-story.webp` remains a USDA ARS
public-domain image, with its credit shown directly on the image.

## Production format

Harvest images are locally hosted WebP files at 960 × 640 pixels. The current
set is roughly 26–113 KB per image. Local hosting prevents third-party requests,
layout shifts, hotlink failures, and source-site tracking in the product.

The cards treat photography as decorative because the adjacent text provides
the product name and description. A tinted overlay and shared Phosphor mark
keep text-independent contrast and connect the image to the filter vocabulary.

When adding a photograph:

1. Prefer public-domain government imagery or a trusted stock library with a
   clear commercial license.
2. Avoid identifiable people, visible brands, and private-location details
   unless the usage and release are explicit.
3. Record the creator, source page, license, local filename, and crop here.
4. Crop to 3:2, export at 960 × 640 WebP, and keep the file near or below 120 KB.
5. Inspect desktop and mobile crops before merging.
