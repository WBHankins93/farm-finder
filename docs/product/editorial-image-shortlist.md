# Editorial image shortlist

Status: shortlist only; no production implementation is included in this PR.
Creative review ranks FF-GEN-001 as the first integration candidate, FF-GEN-002
as the secondary candidate, and FF-GEN-004 as a reserve because the exchange
scene reads as staged.

The current local generation log records 21 approved previews (14 landscape,
7 portrait). The selected previews are conceptual, generated scenes. They do
not depict a named FarmFinder farm, a verified producer, or current product
availability. Keep that distinction in captions, alt text, and nearby copy.

## Candidates

| Preview / proposed placement | Local asset path | Dimensions, format, file size | Provenance and usage permission evidence | Crop guidance | Suggested alt text |
|---|---|---|---|---|---|
| **1. FF-GEN-001 — Honest harvest** · existing home field-story image | `/Users/benhankins/.codex/generated_images/01a04530-68f9-7b53-b732-1ea17307a7ff/exec-26bcb92c-4d38-49bc-b868-f5defb9cf3e9.png` | 1536 × 1024; PNG; 2,681,095 bytes (2.56 MiB) | Generated locally; the local generation log labels this preview approved and describes mixed seasonal produce on a working table. A separate rights record is not present in the manifest. | Landscape 3:2 source. A 16:9 crop can keep the produce grouping centered; square crops should retain the leafy greens and root vegetables. Avoid cropping to imply a particular farm or this week’s harvest. | “Generated editorial scene of leafy greens, roots, squash, and tomatoes arranged on a wooden worktable.” |
| **2. FF-GEN-002 — Farm as workplace** · existing home hero image rotation | `/Users/benhankins/.codex/generated_images/01a04530-68f9-7b53-b732-1ea17307a7ff/exec-070cc9ce-eb61-4a65-9a46-44fcf0252576.png` | 1536 × 1024; PNG; 2,714,207 bytes (2.59 MiB) | Generated locally; the local generation log labels this preview approved and describes a worker tending diversified rows beside a high tunnel. A separate rights record is not present in the manifest. | Landscape 3:2 source. For a 16:9 hero, retain the worker and high tunnel; use a focal point near 48% horizontal and 52% vertical. Check mobile crop separately so the worker stays visible. | “Generated editorial scene of a worker tending covered vegetable rows beside a high tunnel.” |
| **Reserve · FF-GEN-004 — Buying is a conversation** · existing home hero image rotation | `/Users/benhankins/.codex/generated_images/01a04530-68f9-7b53-b732-1ea17307a7ff/exec-a37c8b2f-fc01-4552-adb0-db564c9319a5.png` | 1536 × 1024; PNG; 2,505,615 bytes (2.39 MiB) | Generated locally; the local generation log labels this preview approved and describes a farmer and customer exchanging a CSA box. A separate rights record is not present in the manifest. | Landscape 3:2 source. Keep both people and the box in wide crops; for mobile, center the exchange rather than either person alone. Do not associate the fictional people with a listed farm. | “Generated editorial scene of a grower handing a box of produce to a customer at a market table.” |

The local generation log is
`/Users/benhankins/.codex/generated_images/01a04530-68f9-7b53-b732-1ea17307a7ff/farmfinder-local-generation-log.md`.
The listed approval status records editorial review. Images remain outside the
repository; no binary was copied or edited for this shortlist. If an image is
purely decorative when implemented, use empty alt text instead of the suggested
descriptive text.

The existing placements are visible in `03-app/site/app/globals.css` (hero
rotation and field-story image) and `03-app/site/app/page.tsx`. A creative
reviewer should confirm the final image and crop against the live page before
any separate implementation change.
