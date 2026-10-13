# Farm logo pilot

> Status: research complete; publishing blocked on permission workflow
> Reviewed: 2026-10-13

## Decision

FarmFinder may show an authentic farm logo only when the image has an official
source, documented ownership, explicit reuse approval, and an approved
`media_assets` record. Finding a logo online establishes authenticity, not a
right to republish it. The application must never hotlink a logo or substitute
a generated imitation.

Until those requirements are met, category marks remain the production
fallback. No candidate asset listed below has been downloaded or added to the
site.

## First research set

| Farm | Research result | Production status |
|---|---|---|
| Sprout | Strong official identity candidate; current branding reflects a rebrand | Await owner confirmation and rights record |
| VEGGI Farmers Cooperative | Strong official identity candidate; a newer contact path was found | Await owner confirmation and rights record |
| Wetland Bee Company | Strong official identity candidate; listing category needs separate data review | Await owner confirmation and rights record |
| Cicada Calling Farm | Strong official identity candidate | Await owner confirmation and rights record |
| CRISP Farms | Strong candidate; official HTTPS presence and logo treatment found | Await owner confirmation and rights record |
| White Sand Homestead | Strong official identity candidate | Await owner confirmation and rights record |
| River Queen Greens | Strong official identity candidate | Await owner confirmation and rights record |
| Black Creek Farm | Authentic identity evidence found; an older listed domain is no longer reliable | Await owner confirmation and a current source |
| T & R Dairy | Only a composite/third-party treatment was found | Do not use; request a standalone owner-supplied file |
| Know Dat Grow Dat | No sufficiently authoritative reusable logo source found | Keep category fallback |
| 3R Land & Livestock | No sufficiently authoritative reusable logo source found | Keep category fallback |
| Homestyle Natural Beef | No sufficiently authoritative reusable logo source found | Keep category fallback |

The research also surfaced possible listing corrections: a Sprout rebrand, a
Wetland Bee category mismatch, a newer VEGGI contact path, and a dead/older
Black Creek domain. Those are data-lane candidates, not app-design edits, and
must be verified under the pipeline's evidence rules before changing records.

## Storage and rendering contract

- Reuse the existing `media_assets` model in
  `packages/db/migrations/0002_core_schema.sql` rather than placing logo URLs
  directly on a farm record.
- Store approved files in controlled object storage; do not hotlink official
  sites or social networks.
- Record the source URL, retrieval date, rights/permission basis, reviewer,
  approval state, farm identity, dimensions, media type, and checksum.
- Generate safe display derivatives while retaining the approved original.
- Render order: approved farm logo → category mark. Broken or pending assets
  always fall back without shifting layout.
- Roll out to profile headers first, search-result cards second, and never map
  pins. Logos on dense maps reduce category legibility and can falsely imply
  verification.

## Five-farm permission pilot

Start with five farms from the strong-candidate set that have a current,
owner-controlled contact path. For each farm:

1. Confirm that the farm identity and listing refer to the same operation.
2. Request a standalone SVG or high-resolution PNG plus written display
   permission for FarmFinder's directory and map-adjacent profile surfaces.
3. Record the permission and source metadata before importing a file.
4. Review legibility on cream and green profile surfaces at mobile sizes.
5. Publish to the profile header only, verify fallback behavior, and collect
   owner feedback before allowing logos in result cards.

Success means all five profiles render approved assets without hotlinks,
layout shift, map-pin changes, or ambiguity about FarmFinder verification.
