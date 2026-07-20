# FarmFinder GTM copy, confidence, and typography review

> Review date: 2026-07-20
>
> Scope: public consumer website and landing-page journey
>
> Primary audience: shoppers trying to find local food and decide whether a farm is worth contacting or visiting

## Executive verdict

FarmFinder has a stronger visual identity than most early-stage directories. The field-journal concept, editorial serif, map language, visible counts, and source-aware profiles feel considered rather than templated. The core proposition is understandable within a few seconds: find nearby farms and learn what they sell.

Before this pass, the experience looked trustworthy but asked too much of the reader. Small uppercase labels, dense product cards, repeated navigation choices, internal data language, and a few overconfident promises weakened buyer confidence. The site was visually above average but only moderately easy to scan.

After the implemented changes, the working assessment is **8.4/10 buyer confidence**, up from **7.1/10**. This is a heuristic design assessment, not a measured conversion result. It should be validated with usability sessions and behavioral analytics.

| Dimension | Before | After-pass estimate | Reason |
|---|---:|---:|---|
| Two-second clarity | 7.5 | 8.6 | The hero now states the useful outcome and the CTA names the directory size. |
| Trust | 7.4 | 8.4 | Source visibility, map accuracy, freshness, and availability limits are stated earlier and more plainly. |
| Readability | 6.1 | 8.2 | Core interface text moved out of the 7–11px danger zone; tracking and all-caps use were reduced. |
| Buyer intent match | 7.3 | 8.5 | “Search farms,” “Browse food,” and “View profile” map to real shopper goals. |
| Distinctiveness | 8.4 | 8.5 | Newsreader and the atlas remain the memorable signature; interface decoration was quieted. |
| Overall confidence | **7.1** | **8.4** | Clearer promises and calmer scanning reduce uncertainty without making the site generic. |

## What already attracted buyers

- **“Find the farms behind your food.”** is memorable, specific to the category, and emotionally useful. It creates curiosity without sounding like generic “shop local” advertising.
- **Real directory counts** make the product tangible. A shopper can see this is an operating resource, not a waitlist or concept page.
- **Products, places, and ways to buy** match the questions people naturally bring to a farm directory.
- **Location confidence and source details** are unusually strong trust signals for a map product. They show restraint instead of pretending every pin is exact.
- **The field-guide voice** gives FarmFinder a reason to be remembered and shared. It feels like a useful local artifact rather than a marketplace template.
- **No account wall** supports first-visit trust and low-friction discovery.

## Wording that hurt confidence

### 1. Internal process language

“Canonical workbook,” “one-row-per-entity,” “duplicate groups,” and “retained in the source log” describe governance work, not shopper value. They make the product feel unfinished and force a consumer to translate database operations into a reason to trust the listing.

**Change:** explain the outcome: the directory contains distinct farms, each listing keeps its source, and details can be checked and corrected.

### 2. Promises broader than the data

“Learn exactly how to buy” sounded stronger than the dataset could always support. Some listings lack a confirmed website or sales schedule, and inventory is not live.

**Change:** “the best confirmed way to buy” and a direct reminder to check current products, hours, and pickup details with the farm.

### 3. Self-congratulatory claims

“FarmFinder is the clearest searchable description available” was not verifiable and asked the reader to accept a superiority claim. Trust grows faster from showing sources and limitations than from declaring leadership.

**Change:** describe the actual contact paths a profile may contain and tell the shopper how to verify them.

### 4. Poetic labels where task labels were needed

“Harvest” is attractive brand language, but it is less immediately clear than “Browse food” in primary navigation. “Explore” is also weaker than “Search” when a shopper has intent.

**Change:** keep the field-guide voice in headings and use plain outcome language in navigation and controls.

### 5. Interface actions that named the wrong surface

“Show all on the map” privileged a presentation mode even though the list is the reliable discovery path and mobile users may be in list view.

**Change:** “Show matching farms.” The product decides how to present them.

### 6. Future-only calls to action

A “submission details” link led to text saying a form was planned. That behaves like a CTA without delivering an action.

**Change:** label the current destination honestly as “How the directory works,” and state that correction tools are in progress.

## Implemented copy changes

| Area | Previous direction | Implemented direction | Conversion effect |
|---|---|---|---|
| Header | Ask / Harvest / Explore / Updates / Find farms | Ask / Browse food / About / Search farms | Fewer choices; verbs match shopper intent. |
| Hero support | Broad promise to learn exactly how to buy | See products and the best confirmed buying path | Specific without overpromising. |
| Hero CTA | Find food near you | Search 299 farms | Concrete scope and direct action. |
| Hero trust | General source sentence | Sources shown, approximate pins labeled, update month | Answers “why should I trust this?” before the first click. |
| Ask introduction | Dense explanation of record grounding | Short task-based explanation | Reduces reading before interaction. |
| Ask disclaimer | Abstract “likely matches” language | Check current products and hours with the farm | Gives the shopper a practical next step. |
| Product section | Data-centric explanation | “Browse by what you want to bring home” | Frames categories around a purchase outcome. |
| Product grid | All 12 guides immediately visible | Six guides, then an explicit expand control | Preserves depth without overwhelming first-time visitors. |
| Search heading | “What are you looking for?” | “Find food from a farm near you.” | Restates value at the moment of action. |
| Farm card | Full profile | View profile | Shorter and more familiar. |
| Update ledger | Workbook and deduplication terminology | Distinct listings with traceable sources | Makes governance meaningful to consumers. |
| About / corrections | Planned submission form | Correction tools in progress | Honest status without presenting a dead end as a feature. |

## Typography research

The common pattern among high-performing consumer products is not one magic font. It is a disciplined system:

1. A legible sans-serif carries navigation, controls, pricing, and dense information.
2. Brand personality appears in a controlled display role or a bespoke family.
3. The number of families is kept low and the hierarchy is created with size, weight, spacing, and context.
4. Small type does not become more premium merely by adding tracking and uppercase styling.

[Apple’s typography guidance](https://developer.apple.com/design/human-interface-guidelines/typography) recommends readable default sizes, avoiding light weights at small sizes, and minimizing the number of typefaces. Apple pairs the functional SF family with the more editorial New York family. [Airbnb’s account of Cereal](https://medium.com/airbnb-design/working-type-81294544608b) describes one type system carried consistently across product touchpoints. [Spotify’s design-system history](https://spotify.design/article/reimagining-design-systems-at-spotify) similarly ties its Circular typeface to a unified product system. [Amazon’s official typography guidance](https://www.developer.amazon.com/en-US/alexa/branding/echo-guidelines/identity-guidelines/typography) separates display use from body copy, recommends sentence case, restrained line length, and generous whitespace.

The broader web has also moved toward owned, performance-conscious font delivery. The [2025 Web Almanac font chapter](https://almanac.httparchive.org/en/2025/fonts) found web fonts on roughly 88% of sites and self-hosted fonts on about 72%. This supports using a deliberate variable-font system, but it does not justify adding families that make the experience slower or less consistent.

### FarmFinder font decision

**Keep Newsreader + Geist.**

- **Newsreader** is the shareable, memorable voice. Its editorial forms make FarmFinder feel like a field guide and work especially well for the hero, section headings, farm names, and short explanatory passages.
- **Geist** is the workhorse. Its open forms, variable weights, and neutral rhythm make filters, controls, provenance, and map details easy to scan.
- Replacing both with a fashionable geometric sans would make the product less distinctive. Adding a third display face would make the hierarchy noisier.
- A future custom face is not a priority. FarmFinder will gain more buyer confidence from current verification dates, richer contact paths, and farmer-confirmed stories than from proprietary typography.

### Readability rules now applied

- Core actions and meaningful metadata target **11–14px**, compact secondary labels stay at **10px or above**, body copy sits at **14–17px**, and larger editorial text is reserved for headings.
- Uppercase is limited to short category or ledger labels; actions and navigation use sentence case or normal capitalization.
- Letter spacing on actionable text was reduced from as much as `.12em–.17em` to roughly `.01em–.03em`.
- Body copy uses comfortable leading, with key explanatory text at about `1.55–1.65` line height.
- The serif is not used for tiny interface labels.
- Variable-font optical sizing is enabled.
- Text remains resizable and the layout must tolerate the spacing overrides described by [WCAG 2.2 text-spacing guidance](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html).

[Google’s Lexend readability case study](https://design.google/library/lexend-readability) is also a useful reminder that crowding and overly tight spacing can impair reading. FarmFinder does not need Lexend specifically; it needs the same discipline around size, spacing, and line length.

## Words and patterns to use

- **Concrete nouns:** farm, food, eggs, beef, berries, market, pickup, source, town.
- **Outcome verbs:** search, browse, compare, contact, visit, confirm, order.
- **Bounded trust language:** listed, confirmed, source-backed, updated, approximate, not yet listed.
- **Helpful expectation setting:** “Check this week’s availability with the farm.”
- **Local proof:** real listing counts, named places, visible product counts, update dates.
- **Human but restrained tone:** “Find the farm. Confirm the trip.”

## Words and patterns to avoid

- Internal governance jargon such as canonical, entity, ingestion, dedupe, schema, pipeline, or source log on consumer pages.
- Unsupported superlatives: best, most complete, clearest, definitive, guaranteed.
- Marketplace implications when there is no checkout: buy now, in stock, reserve, delivery today.
- Vague CTA labels: learn more, submit, get started, explore, discover more.
- Repeated “verified” claims unless the page defines what was verified and when.
- Long sequences of uppercase text, especially below 12px.
- Aspirational features presented as available actions.

## Buyer confidence gaps that copy alone cannot solve

The remaining gap from 8.4 to a truly category-leading experience is operational:

1. Add a working correction and missing-farm form.
2. Show a per-listing “last checked” date when the data model supports it.
3. Increase confirmed public contact paths and sales schedules.
4. Add farmer-confirmed stories and photography rather than generic farm imagery where permission is available.
5. Measure the funnel: hero-to-search click, search-to-profile open, profile-to-website/contact click, zero-result rate, and return visits.
6. Add saved farms or a lightweight revisit mechanism only after first-session search quality is proven.

## Photography direction

Photography should increase appetite and human confidence, not make the page feel like a stock-photo farm brand. The site therefore uses one strong editorial photo window in the current local preview and keeps the atlas hero intact. Additional images are staged for specific future roles instead of being presented as a mosaic.

Selection rules:

- Prefer real work, products, tools, animals, and market exchange over posed portraits.
- Avoid romantic claims about sustainability, organic production, or animal welfare unless the pictured farm and listing support them.
- Never imply that a generic image depicts a listed FarmFinder producer.
- Use a caption or contextual label when the image could be mistaken for a specific farm.
- Keep text off busy image areas; preserve the readable paper-and-ink surfaces for core actions.
- Replace stock imagery with farmer-cleared local photography as the directory matures.

The local image directory is `03-app/site/public/local-farm-images/`. It is ignored by Git and will not upload to GitHub. The CSS includes a color fallback, so the tracked site remains usable when local assets are absent. Before production publication, approved files should move to a managed image host or another explicitly approved delivery path.

## Local-only image manifest

| Local filename | Source / creator | Dimensions | Intended use |
|---|---|---:|---|
| `farmers-market-produce.jpg` | [Pexels 27592996](https://www.pexels.com/photo/a-farmer-s-market-with-vegetables-and-other-produce-27592996/) · Natalia S | 1800×2400 | Current field-story photo; buyer/market connection. |
| `cattle-pasture.jpg` | [Pexels 8633334](https://www.pexels.com/photo/cattle-in-a-pasture-at-a-farm-8633334/) · Julissa Pires | 1800×2700 | Meat/dairy guide or farmer-story feature. |
| `beekeeper-honeycomb.jpg` | [Pexels 5247996](https://www.pexels.com/photo/unrecognizable-farmer-collecting-honey-from-beehive-5247996/) · Anete Lusina | 1800×2696 | Honey guide or producer-craft story. |
| `farm-eggs.jpg` | [Pexels 6420](https://www.pexels.com/photo/eggs-in-the-metal-basket-6420/) · Karolina Grabowska | 1800×1200 | Egg guide or seasonal editorial callout. |
| `field-rows-aerial.jpg` | [Unsplash hnpRPJ6uvFs](https://unsplash.com/photos/aerial-view-of-agricultural-fields-with-rows-of-crops-hnpRPJ6uvFs) · Bernd Dittrich | 1800×2462 | Atlas/coverage editorial or release story. |

Pexels files are covered by the [Pexels license](https://www.pexels.com/license/); the Unsplash file is marked free under the [Unsplash license](https://unsplash.com/license). Attribution is retained here even when the license does not require an on-page credit.

## Validation plan

For the next evidence pass, recruit five to eight local-food shoppers across mobile and desktop. Ask them to:

1. Explain what FarmFinder does after five seconds.
2. Find eggs near a named city.
3. Decide whether a farm is worth contacting.
4. Explain what they believe the map pin means.
5. State whether inventory and hours are live.
6. Find the source and the best next buying action.

Success means at least 80% complete the farm search without help, no participant assumes live inventory, and most can explain why a listing is trustworthy in their own words.
