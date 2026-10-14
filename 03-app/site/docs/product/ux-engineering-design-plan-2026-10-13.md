# FarmFinder UX, engineering, and design improvement plan

> Status: first two implementation passes complete; pilots and regression automation remain
> Date: 2026-10-13
> Scope: consumer directory experience under `03-app/site/`

## Product direction

FarmFinder should become the source-backed discovery layer for buying food from
independent farms: useful before a visit, honest about uncertainty, and specific
enough to help a person take the next step. It is not a marketplace and should
not imply live inventory, exact private farm-gate locations, or endorsement of
unverified claims.

The visual idea is an **editorial field guide wrapped around a practical search
workbench**. Warm paper, tomato, field green, documentary photography, crop-row
rhythm, crate-label geometry, and handwritten field marks provide identity.
Decoration must remain quiet around controls and data.

## Design principles

1. **Answer before atmosphere.** Location, products, ways to buy, confidence,
   and the next action lead every operational surface.
2. **Specific, never synthetic.** Use agricultural forms tied to the subject;
   avoid generic gradients, random blobs, fake farm seals, or invented logos.
3. **Layer without clutter.** Depth comes from paper tones, inset panels,
   borders, overlap, and restrained marks rather than heavy shadows.
4. **Keep uncertainty visible.** Approximate locations and incomplete records
   remain plainly labeled.
5. **Motion confirms interaction.** Small icon and underline movement may
   respond to hover or focus; all motion respects reduced-motion settings.
6. **Identity is permissioned.** A real farm logo is shown only after source,
   ownership, usage rights, and approval are recorded. Category marks remain
   the default fallback.

## Now — this implementation

### 1. Preserve the user’s search context

- The Ask experience reads an existing `near` and `radiusMiles` from the URL.
- Ask requests and result links retain that location context.
- Copy distinguishes nationwide text matching from location-refined results.
- Acceptance: a question asked from a New Orleans, Louisiana search never
  silently sends the user back to an unscoped national result.

### 2. Make farm records easier to scan

- Normalize presentation-only product text into concise, deduplicated labels.
- Keep canonical source data untouched and preserve the full record for audit.
- Extract the farm result card from the discovery controller so rendering and
  orchestration can evolve independently.
- Acceptance: repeated semicolon/comma fragments do not appear as duplicate
  chips or summary prose; missing data is still labeled rather than hidden.

### 3. Add subject-grounded visual depth

- Turn the search area into a clear workbench: location is the first boundary,
  food/farm is the second question, radius is an explicit refinement.
- Use subtle crop-row and produce-label motifs only on editorial backgrounds.
- Give Ask, About, and profile surfaces layered paper/inset-panel structure.
- Reduce map-detail obstruction and strengthen selected-result continuity.
- Add restrained hover/focus movement to service and category marks.
- Acceptance: controls remain high-contrast, keyboard-visible, responsive, and
  calmer than surrounding editorial sections.

### 4. Record logo architecture without publishing logos

- See the research set and permission workflow in
  [`../design/farm-logo-pilot.md`](../design/farm-logo-pilot.md).
- Reuse the existing `media_assets` model and object storage; never hotlink.
- Require provenance, rights status, review status, and farm/owner approval.
- Roll out profile header first, list cards second, and never use logos as map
  pins. Fall back to category marks at every stage.
- The current research pilot is discovery only; no candidate logo is a licensed
  production asset until permission is documented.

## Next

- Run a permissioned five-farm logo pilot, starting with candidates that have a
  clear official source and reachable owner.
- Correct source-data issues found during research in the appropriate data lane:
  category mismatch, newer contact paths, rebrands, and dead domains.
- Introduce screenshot-based visual regression coverage for desktop and mobile
  hero, Ask, explorer, map detail, and farm profile states.
- Add a small identity/media resolver once storage and moderation workflow are
  available; keep application components storage-provider agnostic.
- Review mobile search ergonomics with five task-based usability sessions.

## Later

- Owner claim and correction workflow with approval audit trail.
- Seasonal and regional editorial modules driven by verified location and
  product data, without narrowing the national product identity to one region.
- Production image library using original, rights-cleared photographs and
  generated imagery that passed agricultural accuracy review.
- Personalized saved searches or availability notifications only after data
  freshness can support those promises.

## Engineering boundaries

- No canonical farm data changes are part of this app-design lane.
- No downloaded farm logos, image binaries, or unlicensed previews are added.
- URL state remains shareable and is the source of truth for search context.
- Presentation cleanup is pure and unit-tested.
- The discovery controller owns state and data loading; extracted view
  components receive typed data and callbacks.
- Existing privacy, public-location precision, attribution, and data-gate rules
  remain intact.

## Delegated work and review gates

| Work package | Exclusive files | Review gate |
|---|---|---|
| Ask continuity | `ask-directory.tsx` plus focused tests/helper | Location and radius survive request, farm link, and all-results link |
| Farm presentation | `farm-presentation.ts`, focused tests, `farm-profile-dialog.tsx` | Deduplication is display-only; empty and mixed delimiters are covered |
| Result-card boundary | `farm-result-card.tsx`, `discovery-workspace.tsx` | No behavioral change; controller shrinks; keyboard/hover behavior remains |
| Visual integration | `globals.css` | Desktop/mobile, contrast, focus, reduced motion, and map obstruction reviewed |

The primary agent reviews every package for scope, product truthfulness,
accessibility, responsive behavior, and test coverage before integration.

## Implementation ledger

- [x] Ask keeps the explorer's location and radius through requests and result
  links, while distinguishing nearby from nationwide matches.
- [x] Cards and profiles share presentation-only product normalization without
  rewriting canonical data.
- [x] The result card and discovery controls are typed view boundaries; the
  discovery workspace remains the state and data-loading controller.
- [x] Map detail, cards, and profiles now use the same clean location and
  product presentation, including explicit missing-data language.
- [x] City suggestions implement the ARIA combobox keyboard path: Up/Down,
  Enter, Escape, active-option announcement, and focus-safe pointer selection.
- [x] Search status updates are scoped to a dedicated status node so the
  adjacent action does not get repeatedly announced.
- [x] Desktop and 390px mobile checks confirmed city selection, suggestion
  dismissal, status messaging, a 44px map-detail close target, and a map sheet
  that stays within the mobile viewport width.
- [ ] Add reproducible visual-regression baselines after Chrome/font versions,
  dynamic map regions, ownership, and baseline-update rules are pinned.
- [ ] Run the permissioned five-farm logo pilot; research links are not
  production assets and remain blocked on documented rights and approval.

The current screenshot harness remains a review tool, not a pixel-diff gate.
That distinction is intentional: an unowned or unstable baseline creates noisy
approvals rather than trustworthy regression coverage. The staged path is
recorded in [`../testing-report.md`](../testing-report.md).

## User-flow critique backlog

This backlog records the first-time-user review completed after the first two
implementation passes. “Working” means the core path can be completed today;
it does not mean every transition is yet as direct or legible as it should be.

### Current flow assessment

The core journey is sound: choose a city → filter by food → compare farms → use
the map → open a profile, website, contact path, or directions. The hero makes
the product legible quickly, the search model is understandable, and location
uncertainty is represented honestly. The remaining work is concentrated at
transitions between these surfaces and at the point where a farm record should
become a confident next step.

| ID | Finding | Acceptance condition | Status |
|---|---|---|---|
| UF-01 | Product browse links replace the current query string, silently dropping a chosen place and radius | Product navigation preserves valid `near`, `radiusMiles`, and other compatible discovery context while changing only the product | Complete · verified |
| UF-02 | The results toolbar repeats the selected sort value beside the native select | One visible, labeled sort control communicates the current value | Complete · verified |
| UF-03 | Tapping the main body of a result card on mobile only selects it while its detail sheet remains in the hidden map view | A mobile card activation produces an immediate visible outcome; desktop list/map continuity remains intact | Complete · verified |
| UF-04 | Some visual toggle states do not expose their selected state to assistive technology | Every product, category, and service toggle reports `aria-pressed` consistently | Complete · verified |
| UF-05 | The full location/query/radius workbench consumes most of the screen after a mobile scope is established | A compact mobile scope summary appears after selection, preserves the active values, and offers an explicit Edit action | Complete · verified |
| UF-06 | Ask can legitimately return nationwide results before a visitor establishes location, but that is rarely the intended meaning of “Who sells…” | Ask either carries an established scope or offers a direct location refinement without forcing a trip down and back up the page | Next pass |
| UF-07 | The profile reads as a database record rather than the conclusion of discovery; contact, website, and map actions compete equally | The profile presents a clear “next step” hierarchy without inventing contact paths or freshness | Complete · verified |
| UF-08 | Repeated “not listed” language is honest but erodes confidence when source records are sparse | Data enrichment and owner correction reduce missing product and purchase-path fields while keeping explicit unknown states | Data/owner workflow |
| UF-09 | Farms, farmers markets, and related organizations can appear visually equivalent | Product ownership decides the entity taxonomy; the interface then labels each type explicitly | Product decision |
| UF-10 | Listing freshness is not visible to consumers | Show a verified or source-updated date only after a governed field and update policy exist | Data-model dependency |
| UF-11 | Some source-kept farm websites are bare domains, which browsers otherwise interpret as broken internal links | Qualify plausible bare domains as HTTPS and reject malformed or unsafe schemes everywhere the app renders a website action | Complete · verified |

### Product questions retained for decision

1. Is the primary successful outcome contacting the farm, visiting its website,
   or getting directions? Analytics and action hierarchy should follow one
   declared outcome.
2. Are farmers markets and related organizations first-class peers of farms, or
   distinct result types within the same directory?
3. Is location the default boundary for every consumer journey, or is national
   research an equally important mode?
4. What governed event is allowed to reset a listing’s “verified” date?
5. When does owner correction/claim become part of the public product rather
   than an internal enrichment process?

### Verification matrix for this pass

| Risk | Verification |
|---|---|
| Location disappears when browsing by product | Pure URL-helper tests plus hydrated browser navigation from a Louisiana-scoped page |
| Mobile card activation has no visible result | Browser check at 390 × 844 confirming the Map view and selected sheet become visible |
| Compact summary hides or misstates active scope | Browser checks for selection, Edit, place/radius/query text, and desktop non-regression |
| Toggle state is visual only | Source assertions and keyboard/accessibility-tree inspection for `aria-pressed` |
| Profile invents unavailable actions | Unit/type checks plus browser review of records with and without contact and website fields |
| App-wide regression | Repository-required data, pipeline, lint, build, rendered, and real-WebGL screenshot gates |

### Implementation review · 2026-10-14

The work was split into three exclusive implementation scopes: location and
product continuity, results/filter interaction, and mobile/profile hierarchy.
Integration review found and corrected two boundary cases before approval:
unmapped result cards now open their profile rather than promising a map, and
source-kept bare-domain websites are safely qualified for external navigation.

Browser verification covered the New Orleans, Louisiana flow on desktop and at
390 × 844. It confirmed retained place/radius context, one visible sort control,
announced toggle states, the compact scope summary and Edit focus return, mapped
card → map-sheet continuity, the unmapped-card profile fallback, and profile
actions for records with and without a public contact path or map point.

## Completion checks

Run the repository-required checks from `AGENTS.md`, including all pipeline and
legacy validation commands, then from `03-app/site/` run `npm run
data:validate`, `npm run data:gates`, `npm run lint`, and `npm test`. Finish with
`git diff --check` and an interactive desktop/mobile review of the changed
states.
