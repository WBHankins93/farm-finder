# Research

- `../01-database/pipeline/data/<ST>.json` — the current pre-cutover canonical store: 72,396 governed records across all 50 states; 68,618 currently pass the public eligibility/privacy projection.
- `local_farm_database_final.xlsx` — superseded 299-row LA/MS workbook retained only as immutable cutover evidence. Its historical release is pinned by `../03-app/site/config/source-of-truth.json`; it is not a national runtime or count source.
- `market-opportunity-brief.md` — current FarmFinder opportunity assessment, including governed segment counts, evidence gates, and product sequencing.
- `state-expansions/` — the enforced four-file contract for every coverage-reviewed state. Detailed evidence is private, compressed, checksum-pinned, and stored outside Git.
- `collection-inputs/<ST>/referrals.csv` — additive cross-state collection inputs generated from `outside_jurisdiction` evidence. These are not a fifth state-release contract file; the home-state collector consumes open referrals as QA candidates.

Older workbook and dashboard files are historical snapshots. Do not promote one by renaming it; update the source-of-truth manifest and pass its validator.

Pending: files from earlier FarmFinder chats can be added here when Ben re-attaches them, provided they stay within FarmFinder's standalone product boundary.
