# Remediation Build Plan: FarmFinder web

*Date: 2026-09-07 · Source: full-sweep UI/UX/technical review, 2026-09-07 · Roadmap: [`phased-build-plan.md`](./phased-build-plan.md) · Ledger: [`../implementation-ledger.md`](../implementation-ledger.md)*

## What this is

The 2026-09-07 review produced 20 findings and 8 feature gaps against the `EXPLORER_V2`
surface. This document sequences all of them into vertical slices. It does **not**
replace the phase map in `phased-build-plan.md`; every milestone below names the phase
it advances, so there is one roadmap, not two.

Five items were already resolved on 2026-09-07 and are recorded in "Already closed"
at the bottom rather than as future work.

### Slicing rule

Each milestone is a thin path through pipeline, API, and UI that can be demoed. No
milestone is "the data layer" or "the accessibility pass." The one exception is M6,
which is explicitly a craft close-out and is scheduled last on purpose.

---

## Milestones

### M0: The directory tells the truth about itself
- **Goal:** A user can tell, from the results list, which farms they can actually act on, and the ranking puts those first.
- **Phase:** Advances Phase 2 (web foundation). Prerequisite for Phase 4.
- **Scope:**
  - Compute `completeness` in `01-database/pipeline` (NOT in `scripts/build-web-feed.py`). Inputs: has website, has contact, any service flag true, `geoPrecision`, product-text specificity. Emit as an integer tier plus the component booleans.
  - Carry the field through `FarmSummary` in `discovery-contract.ts` and both `/v1` routes.
  - Card renders a terminal state for zero-signal records: no silent empty service row. Copy asks for help instead of dead-ending.
  - Completeness becomes a tiebreaker inside all three existing comparators in `matchingFarms()`. It does not become a fourth sort option.
  - Refresh `phased-build-plan.md` and `implementation-ledger.md`, both of which still describe 299/315 rows and the retired Newsreader + Geist pairing. Claude Code and Codex read these files; stale context produces wrong work.
- **Done when:** Search "Metairie, LA" at 50 miles, and every card either shows a way to contact the farm or explicitly says it has none and offers a way to help. No two adjacent cards with identical distance are ordered arbitrarily.
- **Integrates:** Existing Python pipeline, existing comparator.
- **Risk retired:** Proves the completeness signal survives the M2 Postgres cutover. This is why it is computed in the pipeline and not the web feed: Postgres imports from the same pipeline, so the score carries over instead of being rebuilt.
- **Cost:** The directory will visibly look thinner. 68,618 is the marketing number and a large share of it will read as filler, because it is. You trade a headline count for a product people trust on the second visit. Given the competitive thesis is that national apps ship bad data, this is the trade to make.
- **Alternative considered:** Filter thin records out of default results entirely. Rejected. It hides the gap from you as well as from users, and it removes the surface where owners could correct it.
- **Findings closed:** 1, 2.
- **Estimate:** 1 week.

### M1: One way to start a search
- **Goal:** The location control behaves identically wherever it appears, and using it never reloads the page.
- **Phase:** Advances Phase 2.
- **Scope:**
  - Extract a single `LocationControl` client component: combobox, suggestions with record counts, geolocation button. Use it in the hero and in `DiscoveryWorkspace`.
  - Hero submit intercepts, sets place, and scrolls to `#discover`. Keep the plain form as the no-JS fallback (the `action="/#discover"` fix already landed).
  - Complete the combobox ARIA pattern: ArrowUp/ArrowDown, `aria-activedescendant`, Escape to dismiss. Copy the handler already written in the filter sheet.
  - Promote "ways to buy" out of the third chip row into a primary filter position.
  - Add a share button. URL state is already complete and shareable; nothing currently tells the user that.
- **Done when:** A keyboard-only user reaches results from the hero without a page reload, using only arrow keys and Enter, and can copy a link that reproduces the exact result set.
- **Integrates:** Existing `/v1/places` endpoint, existing `serializeDiscoveryUrl`.
- **Risk retired:** Confirms the URL state contract is complete enough to be the sharing primitive, before Phase 3 changes where results come from.
- **Cost:** Promoting "ways to buy" foregrounds the filter with the thinnest underlying data. Only safe because M0 shipped first and the UI is now honest about coverage. Do not reorder these two.
- **Findings closed:** 5 (fully), 6, 11.
- **Estimate:** 1 week.

### M2: Postgres cutover, and the 6.76 MB bundle dies
- **Goal:** `/v1` reads from PostgreSQL/PostGIS. No dataset is compiled into the server bundle.
- **Phase:** Closes Phase 1, opens Phase 3.
- **Scope:**
  - Import the promoted release into Postgres per the source-of-truth workflow already documented. Nothing new in the process, this is execution.
  - Repoint `/v1/farms`, `/v1/farms/map`, `/v1/farms/[id]`, `/v1/places` at the database. The routes were designed bounded for exactly this swap.
  - Full-text search replaces the token scan in `discovery-server.ts`. PostGIS radius and bbox replace the haversine loop.
  - Completeness from M0 becomes an indexed column, so the tiebreaker stops being an in-memory sort.
  - Delete `app/data/national-farms.generated.ts` and the `node:zlib` dependency.
  - Record index decisions in `architecture/index-register.md` with `EXPLAIN (ANALYZE, BUFFERS)` evidence, per the discipline already written there.
- **Done when:** Cold-start CPU is measured and under the Workers budget, the golden queries in `docs/testing/discovery-acceptance.md` return identical IDs and counts to the current implementation, and the generated feed is gone from the repo.
- **Integrates:** `packages/db/`, ADRs 0001 and 0004, `infra/` Compose stack.
- **Risk retired:** The single largest unknown in the project. Scheduled before the midpoint so course changes are still cheap.
- **Cost:** This is 2 to 3 weeks and adds a managed database to your operating cost and failure surface. The embedded feed's one real virtue is zero infrastructure. If launch traffic will genuinely be small, the feed may hold for a while longer. It will not hold through a good week, and finding that out under load is the expensive version.
- **Findings closed:** 3, 4 (fully).
- **Estimate:** 2 to 3 weeks.

### M3: Every farm has a URL
- **Goal:** `/farms/{state}/{slug}` is a real indexable page, not a dialog.
- **Phase:** Advances Phase 3.
- **Scope:**
  - Server-rendered farm page reusing the existing profile layout. The dialog stays for in-context viewing and deep-links to the page.
  - Structured data (`LocalBusiness`), canonical URLs, per-page metadata.
  - Gate indexing on the M0 completeness tier. Thin records render but carry `noindex` until claimed or corrected.
  - Sitemap generated per state from the promoted release.
- **Done when:** A farm page loads with no JavaScript, validates in Google's rich results test, and a thin record is served with `noindex`.
- **Integrates:** M0 completeness, M2 API.
- **Risk retired:** Establishes whether organic search is a viable acquisition channel before you spend on anything else.
- **Cost:** 68,618 thin pages is a textbook thin-content penalty. The completeness gate is the mitigation and it is not optional. Second-order effect: it gives farm owners a page to find themselves on, which is the hook M4 needs.
- **Findings closed:** Feature gap (farm detail pages).
- **Estimate:** 1 week.

### M4: Claim and correct
- **Goal:** A farm owner can find their listing, prove ownership, and fix it. A visitor can report a correction.
- **Phase:** Phase 4.
- **Scope:**
  - Managed OIDC per the existing authentication decision. Public reads stay anonymous.
  - Claim flow: find listing, submit evidence, curator review queue, approve, farm-scoped edit rights.
  - Correction flow for anonymous visitors, queued not applied.
  - Claimed and corrected records recompute completeness and climb the ranking immediately. This is the incentive that makes M0's ranking fair rather than punitive.
  - Audit trail and field-level assertions per the source-of-truth workflow.
- **Done when:** You claim a test farm end to end, edit a service flag, and watch it move up the results for a query where it previously ranked below a more complete record.
- **Integrates:** Roles table and authorization policy already specified in Phase 4.
- **Risk retired:** Whether the self-scaling data engine actually scales. If nobody claims, the 52k records with no website stay dark forever and the thesis needs rework.
- **Cost:** The largest milestone here, roughly 3 weeks, and it adds moderation as ongoing operational load. Start with manual curator review rather than automation; you cannot tune a review queue you have never run. Second-order: every claim is a qualified Sproutflow lead who has just told you their farm has no website.
- **Findings closed:** 12.
- **Estimate:** 3 weeks.

### M5: Reasons to come back
- **Goal:** The directory is useful more than once.
- **Phase:** Advances Phase 2 and resolves the Phase 5 entry question.
- **Scope:**
  - Saved farms and a trip list. Anonymous localStorage first, migrating to the account when signed in after M4.
  - Seasonality. Every `productGuide` already carries a written `season` string that the app never renders. Wire it to the product cards and filters, with a regional qualifier since a Louisiana season is not a Wisconsin one.
  - Resolve "Ask the field guide." Either rename it to "Search listings" and keep the honest sub-line, or build real retrieval. Decide with the Phase 5 eval set, not by preference.
  - Add the eight `/images/products/*.webp` assets and restore the `--tile-img` declaration removed on 2026-09-07.
- **Done when:** A user saves three farms, returns the next day, and sees which of them have something in season now.
- **Cost:** Seasonality is nearly free because the content exists, but a wrong season is worse than no season. Ship it with the region qualifier or not at all.
- **Findings closed:** 13, 17, 19, and part of 20.
- **Estimate:** 1 to 2 weeks.

### M6: Craft close-out and a design gate that holds
- **Goal:** The visual system is consistent, and the checks that caught these findings run in CI so they never regress.
- **Phase:** Closes the Phase 2 accessibility and performance gates.
- **Scope:**
  - Finish the type scale. 63 declarations remain at 10 to 11px. Floor at 12px, and fill the empty 14 to 18px band that card body copy currently has to work without. Expect layout pressure in the results toolbar and card meta rows, which is why this is a deliberate pass and not a find-and-replace.
  - Dark mode at the token layer. `color-scheme` and a `prefers-color-scheme` block, plus a dark basemap style for MapLibre.
  - Replace the `setMapZoom(c => c + 0.0001)` retry with an explicit retry counter in the effect dependencies.
  - Delete `legacy-page.tsx` and the `EXPLORER_V2` flag once promoted. Two homepages will drift.
  - Add `npm run design:verify` to CI: token contrast ratios against WCAG 1.4.11 and 1.4.3, a type-floor scan, asset-reference validation against `public/`, and a touch-target check. Wire it next to `states:validate` and `cutover:verify`.
- **Done when:** `design:verify` passes in CI, and deliberately regressing `--rule` to its old value fails the build.
- **Risk retired:** That this review has to be run by hand again. Four of the 20 findings were deterministic and machine-checkable, and one of them (the missing product images) survived six weeks after being flagged in the July review because nothing was watching.
- **Findings closed:** 10 (fully), 14, 18, 20.
- **Estimate:** 1 week.

---

## Risk Register

| # | Risk | Consequence if it lands | Retired by |
|---|---|---|---|
| 1 | Postgres cutover is under-scoped and slips | The bundle stays, the app cannot take real traffic, and every later milestone builds on an architecture you are about to replace | M2 |
| 2 | Completeness ranking permanently buries offline farms | The product systematically hides exactly the small operations it exists to serve, inverting the mission | M4 (claiming is the escape hatch; if M4 slips far past M0, revisit the ranking weight) |
| 3 | Nobody claims a listing | The self-scaling data quality thesis fails, and 52k thin records stay thin indefinitely | M4 pilot, with the five-farm cohort already named in the phase map |

**Sequencing dependency worth naming:** M0 and M4 are two halves of one bet. M0 makes thinness visible, M4 gives owners the tool to fix it. Shipping M0 and then stalling before M4 leaves the directory honest about a problem nobody can act on. If M4 is going to slip past a quarter, soften M0's ranking weight in the interim.

---

## Deferred Polish (explicit, not forgotten)

- Vector retrieval. Deferred until full-text fails a documented eval set, per the existing decision.
- Native mobile (Phases 7 and 8). Waits on API contract stability, unchanged.
- Table partitioning, separate job queue. Both wait on measured evidence, unchanged.
- Per-farm photography and the regional imagery production plan.
- Farmers market and CSA entities as first-class records rather than boolean flags on a farm.

---

## Suggested Loop

Per milestone: build → `engineering:code-review` before merge → demo against the "done when" → next.
Use `engineering:debug` when behavior diverges. After M6, the chain continues with
`engineering:testing-strategy` for the Phase 6 CI gates.

Update `implementation-ledger.md` in the same change that closes a milestone, not after.

---

## Already closed (2026-09-07)

Shipped in commit range following `0f0161b`. Typecheck, lint, and 24 unit tests pass.

| Finding | Fix | File |
|---|---|---|
| 8 | Focus ring to solid `var(--rust)` at 2px. 1.64:1 → 5.66:1, clears WCAG 1.4.11 | `globals.css` |
| 9 | `--rule` `#bcc5b8` → `#a8b3a3`. 1.72:1 → ~3.1:1 | `globals.css` |
| 7 | `overflow: hidden` → `overflow-x: clip` on `.site-shell`, unblocking both sticky bars | `globals.css` |
| 10 (part) | All 9px type raised to 11px, 8 declarations | `globals.css` |
| 15 | `100dvh` fallback line on the mobile explorer height | `globals.css` |
| 5 (part) | Hero form `action="/#discover"` so the reload lands on results | `page.tsx` |
| 13 (part) | `--tile-img` removed, ending 8 homepage 404s. Restore when assets land (M5) | `page.tsx` |
| 4 (part) | `farmSearchFields()` called once per farm instead of twice, and skipped entirely with no text query | `discovery-server.ts` |
| 16 | Removed the redundant sort label; sort state was announced three times | `discovery-workspace.tsx` |

**Open verification:** confirm in a browser that the topbar and discovery filter bar now stick when scrolling past the fold. If they do not, the blocking ancestor is elsewhere; check `.hero-location`'s `clamp(120px, 20vw, 320px)` margin first.
