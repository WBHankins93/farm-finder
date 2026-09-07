# FarmFinder regional imagery production plan

> Working plan for original GPT-generated photography. Generated previews stay
> local until they are reviewed and deliberately selected for production use.
> This document tracks art direction and approval status, not production assets.

## Purpose

Build a nationwide image library that makes local food feel connected to real
people, work, seasons, and places. The images should look like candid editorial
agriculture photography from independent farms and producers—not generic produce
advertising, agribusiness symbolism, or a collection of regional stereotypes.

The shared visual language is documentary warmth, natural light, restrained
color, visible texture, ordinary tools, and believable working scale. Regional
specificity comes from accurate crops, species, terrain, weather, infrastructure,
and seasonal work rather than flags, signs, costumes, or landmarks.

The [photo reference board](photo-reference-board.md) defines the inspiration
sources and synthesis briefs. Those Shutterstock images remain thematic
references only and are never image-generation inputs.

## Local-only workflow

- Generated previews remain outside this repository and are not placed under
  `public/` or any other application directory.
- Every candidate receives a stable `FF-GEN-###` identifier. A local manifest
  maps that identifier to the generated file without putting machine-specific
  paths in product documentation.
- A checked item means the candidate passed the full self-approval gate below;
  it does not mean the image has been selected for the website.
- Failed candidates are not silently replaced. Record them as **revise** or
  **reject**, describe the defect, and generate a new version with a new stable
  identifier when the change is substantial.
- Repository integration, output optimization, accessibility text, and final
  editorial selection are separate future steps.

## What every image should communicate

1. **Provenance:** food is visibly connected to a producer, place, or process.
2. **Independent scale:** the environment is plausible for a small or midsize
   independent operation.
3. **Competence:** people are absorbed in credible work rather than performing a
   rural identity for the camera.
4. **Regional truth:** crops, animals, equipment, season, landscape, and weather
   belong together.
5. **Nationwide breadth:** Louisiana receives specific coverage, but the full
   library represents varied U.S. regions. `LA` always means Louisiana.
6. **Editorial usefulness:** portrait and landscape compositions include clear
   subjects, flexible crops, and occasional natural negative space.

## Self-approval gate

Inspect every candidate at full resolution. Mark it **approved** only when all
checks pass.

- [ ] **Source grounding:** consult current authoritative material when the
  subject is regional, biological, seasonal, regulated, or technically niche.
  Prefer USDA, state agriculture departments, university Extension, Sea Grant,
  or equivalent primary institutional sources.
- [ ] **Agricultural accuracy:** crop morphology, animal behavior, food stage,
  handling method, tools, protective equipment, and infrastructure are
  plausible together.
- [ ] **Human accuracy:** hands, fingers, limbs, faces, posture, grip, clothing,
  and physical effort are anatomically and mechanically coherent.
- [ ] **Geographic and seasonal accuracy:** terrain, soil, vegetation, climate,
  crop stage, harvest window, and regional production practice agree.
- [ ] **Scene logic:** weight, gravity, scale, container construction, machinery,
  wiring, water, shadows, reflections, and object contact make physical sense.
- [ ] **FarmFinder art direction:** candid documentary warmth, natural light,
  restrained color, visible texture, and independent-farm scale are present.
- [ ] **Rights, privacy, and claims:** people and properties are fictional and
  unidentifiable; there are no logos, readable private details, copied stock
  compositions, certification claims, or unsupported product claims.
- [ ] **Editorial utility:** subject hierarchy is clear, the orientation is
  useful, critical content survives likely crops, and no accidental text or
  watermark is present.

Approval outcomes:

- **Approved:** all eight checks pass after full-resolution inspection.
- **Revise:** the concept is useful, but a targeted correction is required.
- **Reject:** the underlying anatomy, agriculture, geography, or composition is
  unreliable enough that a new generation is safer than an edit.

## Approved foundation set

These previews are local-only. Checkmarks record the assistant's visual and
subject-matter approval; the user still controls final selection.

- [x] **FF-GEN-001 — Honest harvest, landscape.** Mixed seasonal produce on a
  working table; approved for recognizable produce, restrained abundance,
  natural side light, texture, and crop space.
- [x] **FF-GEN-002 — Farm as workplace, landscape.** Worker tending diversified
  rows beside a practical high tunnel; approved for credible row cover,
  irrigation, tools, scale, and candid activity.
- [x] **FF-GEN-003 — Food carried by hands, portrait.** Small Yukon Gold potatoes
  in weathered hands; replacement approved for realistic tuber morphology,
  anatomy, soil, and harvest context.
- [x] **FF-GEN-004 — Buying is a conversation, landscape.** Farmer and customer
  exchanging a modest CSA box; approved for hand anatomy, box construction,
  product readability, eye-lines, and an unbranded market setting.
- [x] **FF-GEN-005 — Apiary inspection, portrait.** Beekeeper examining a
  Langstroth frame; approved for frame and hive structure, comb pattern, bee
  scale, smoker, PPE, and handling posture.
- [x] **FF-GEN-006 — Louisiana Gulf white shrimp, landscape.** Dockside sorting
  aboard a modest shrimp boat; approved for raw shrimp color and anatomy,
  handling equipment, vessel context, and coastal Louisiana marsh geography.
- [x] **FF-GEN-007 — Southwest Louisiana rice, landscape.** Farmer checking
  mature long-grain rice before first-crop harvest; approved for drooping
  branched panicles, drained field conditions, flat terrain, season, and scale.
- [x] **FF-GEN-008 — Central Florida citrus, portrait.** Manual Hamlin orange
  harvest; approved for tree and fruit morphology, picking sack, moderate crop
  load, harvest bin, flat grove alley, and mild-winter workwear.
- [x] **FF-GEN-009 — Northern urban microgreens, landscape.** Radish microgreen
  harvest in a converted workshop; approved for growth stage, nursery trays,
  neutral-white LEDs, sanitation, safe harvesting, airflow, and electrical
  routing.

### Accuracy references for approved technical images

- **FF-GEN-005:** [USDA ERS on removable Langstroth frames](https://ers.usda.gov/sites/default/files/_laserfiche/publications/88117/ERR-246.pdf),
  [Penn State Extension beekeeping equipment](https://extension.psu.edu/beekeeping-honey-bees),
  and [University of Minnesota Extension inspection guidance](https://extension.umn.edu/event/hiving-packages-and-overwintered-hive-inspection).
- **FF-GEN-006:** [Louisiana Sea Grant, *Shrimping in Louisiana*](https://www.seagrantfish.lsu.edu/pdfs/lifecycle_shrimp.pdf).
- **FF-GEN-007:** [LSU AgCenter, Louisiana rice harvest](https://www.lsuagcenter.com/articles/page1754415445710)
  and [rice management guidance](https://www.lsuagcenter.com/profiles/astrahan/articles/page1701362113346).
- **FF-GEN-008:** [UF/IFAS, *Florida Citrus Production Guide*](https://edis.ifas.ufl.edu/publication/CG101/pdf)
  and [USDA NASS citrus season and production context](https://www.nass.usda.gov/Statistics_by_State/Florida/Publications/Annual_Statistical_Bulletin/2024/CitrusAndAvocado.pdf).
- **FF-GEN-009:** [Penn State Extension, *Growing Microgreens*](https://extension.psu.edu/growing-microgreens).

## Regional production map

Each regional module should begin with a landscape establishing image and a
closer human/process image. Add product portraits only after the growing or
harvesting context is represented. Exact states are recorded in metadata; avoid
putting place names inside an image.

### 1. Louisiana and the Gulf Coast

Focus: Gulf shrimp and oysters, rice, crawfish–rice rotations, sugarcane,
satsumas, humid market gardens, coastal docks, and urban food production.

Regional cues: flat delta and prairie landscapes, marsh horizons, Gulf humidity,
drainage and levee infrastructure, working docks, and subtropical light. Do not
blend seafood, bayou, rice, and citrus into a single fantasy scene.

- [x] Louisiana Gulf white shrimp handling — FF-GEN-006
- [x] Southwest Louisiana rice maturity check — FF-GEN-007
- [ ] Crawfish–rice rotation during a documented seasonal task
- [ ] Sugarcane planting or harvest at independent-farm scale
- [ ] Plaquemines-area satsuma harvest
- [ ] Gulf oyster handling at a working dock
- [ ] Louisiana diversified market garden after summer heat
- [ ] Louisiana urban farm or community growing operation

### 2. Southeast

Focus: peanuts, peaches, pecans, collards and other greens, pasture poultry,
small ruminants, sweet potatoes, and high-tunnel vegetables.

Regional cues: humid light, red or sandy soils where appropriate, pine and
hardwood edges, heat management, and long growing seasons. Avoid plantation
nostalgia, decorative barns, and treating the entire Southeast as subtropical.

- [ ] Orchard or perennial-crop landscape
- [ ] Human-scale harvest or husbandry scene
- [ ] Seasonal market or packing scene
- [ ] Portrait crop with one regionally grounded product

### 3. Northeast

Focus: apples, maple, dairy, shellfish, diversified vegetables, winter storage,
and protected-season growing.

Regional cues: glaciated soils and stone only where locally appropriate,
deciduous seasonality, compact fields, cold-weather infrastructure, and working
waterfronts. Avoid turning every scene into autumn tourism.

- [ ] Orchard or maple landscape
- [ ] Dairy, shellfish, or winter-growing process
- [ ] Cold-season CSA packing or market exchange
- [ ] Portrait crop with accurate winter workwear

### 4. Midwest and Great Lakes

Focus: diversified vegetable farms, dairy, pasture livestock, orchards, grain
handling, winter CSA operations, and urban agriculture.

Regional cues: deep soils, humid continental seasons, windbreaks, practical
outbuildings, lake-influenced weather where relevant, and strong seasonal
contrast. Avoid reducing the region to endless corn-and-soy aerials.

- [ ] Diversified farm landscape
- [ ] Dairy or pasture husbandry scene
- [ ] Winter storage, packing, or greenhouse work
- [ ] Great Lakes orchard or market scene

### 5. Great Plains

Focus: dryland grains, cattle, hay, pulses, irrigation where locally supported,
wind protection, and small-town food networks.

Regional cues: large skies, wind, level-to-rolling grasslands, moisture limits,
and seasonally severe working conditions. Use wide space honestly without making
every farm look industrial.

- [ ] Dryland crop or grassland establishing view
- [ ] Livestock or water-management process
- [ ] Harvest, storage, or local-market interaction
- [ ] Weather-specific portrait crop

### 6. Mountain West

Focus: ranching, hay, high-elevation vegetables, hoop houses, orchards in
suitable valleys, dryland grains, and water-conscious production.

Regional cues: elevation, short seasons, irrigation ditches where appropriate,
intense daylight, cold nights, and valley-specific vegetation. Avoid placing
every subject directly against a dramatic mountain postcard.

- [ ] Valley farm or range establishing view
- [ ] High-elevation growing or husbandry process
- [ ] Water-management or season-extension scene
- [ ] Close product portrait with restrained landscape context

### 7. Pacific Northwest

Focus: berries, hazelnuts, apples, pears, hops, diversified farms, cool-season
vegetables, fisheries, and coastal shellfish.

Regional cues: wet-season soils, maritime cloud, irrigation differences east
of the Cascades, orchard structures, and regional coastal equipment. Avoid
making the whole region evergreen forest or permanently rainy.

- [ ] West-side diversified farm or berry landscape
- [ ] East-side orchard, hop, or dryland process
- [ ] Coastal fishery or shellfish handling
- [ ] Market or packing interaction

### 8. California and the Southwest

Focus: citrus, dates, specialty vegetables, vineyards, dryland ranching,
desert-adapted crops, and water-efficient production.

Regional cues: distinguish coastal, Central Valley, desert, and highland
systems; show irrigation and heat management accurately; represent water limits
without turning every scene into crisis imagery. Avoid generic mission-style or
desert-lifestyle staging.

- [x] Central Florida citrus provides national citrus contrast — FF-GEN-008
- [ ] California orchard or specialty-crop landscape
- [ ] Southwest water-conscious growing process
- [ ] Desert crop or ranching scene
- [ ] Market or packing scene representing regional diversity

### 9. Alaska

Focus: fisheries, cold-climate greenhouses, short-season vegetables, peonies,
reindeer or other livestock only where verified, and remote food logistics.

Regional cues: extreme seasonality, long summer light, cold soils, working
waterfronts, and practical protected growing. Avoid wilderness tourism imagery
that erases production work or Indigenous context.

- [ ] Working fishery or dock process
- [ ] Short-season or protected-growing scene
- [ ] Food handling or distribution scene
- [ ] Regionally grounded portrait crop

### 10. Hawaii

Focus: taro, tropical fruit, coffee, cacao, diversified vegetables, livestock,
and fisheries, selected with state and local cultural guidance.

Regional cues: island-specific rainfall, elevation, volcanic soils, crop
systems, and cultural context. Avoid resort imagery, generic tropical abundance,
or using Native Hawaiian practices as decoration.

- [ ] Culturally and geographically researched crop landscape
- [ ] Harvest or production process
- [ ] Fishery, livestock, or market scene
- [ ] Regionally grounded portrait crop

## Production sequence

### Phase A — Complete category coverage

Finish obvious gaps in the nationwide foundation before expanding every region.

- [ ] Collected eggs in a pasture-hen context
- [ ] Dairy cattle displaying normal pasture behavior
- [ ] Simple honey or value-added product portrait without a fake label
- [ ] Livestock husbandry beyond dairy
- [ ] Farm pickup or CSA delivery with protected private details
- [ ] A second honest-harvest image in portrait orientation

### Phase B — Complete the Louisiana module

Research and generate the six unchecked Louisiana/Gulf Coast scenes above. Pair
each crop or product with its real season and subregion. Keep this module
explicitly Louisiana while continuing national work in parallel sequence.

### Phase C — Establish nationwide breadth

Generate two approved anchors per remaining region: one environmental landscape
and one human/process image. Alternate portrait and landscape orientations so no
region is represented by only one type of crop.

### Phase D — Add depth by directory rollout

As FarmFinder expands state by state, create a small state visual dossier before
generation: authoritative sources, priority products, seasonal windows,
landscape and infrastructure cues, cultural cautions, and visual gaps. Generate
only the images needed for that release rather than filling a generic quota.

### Phase E — Curate for production

After user review, select candidates for actual site roles, create intentional
aspect-ratio variants, optimize files, write accurate alt text, and record image
provenance. This phase is the first point at which generated files may enter the
repository.

## Per-image record template

Copy this block for every new candidate:

```markdown
### FF-GEN-### — Short descriptive title

- **Status:** planned | generated | revise | rejected | approved
- **Region/state:**
- **Subject and task:**
- **Season/crop stage:**
- **Orientation/intended crop:**
- **Authoritative grounding:**
- **Prompt synthesis:** reference-board traits combined, never a stock replica
- **Accuracy review:** agriculture/biology; human anatomy; geography/season;
  scene logic
- **Art-direction review:** light; palette; texture; mood; independent scale
- **Safety/rights review:** fictional people/property; no brands, private text,
  claims, watermark, or copied composition
- **Decision and notes:**
```

## Completion definition

The regional plan is complete when every planned candidate has a recorded
outcome, every approved image passes all eight checks, each region has at least
one landscape and one human/process anchor, major FarmFinder categories are
covered, portrait and landscape crops are balanced, and Louisiana depth sits
inside—not in place of—a genuinely nationwide library.
