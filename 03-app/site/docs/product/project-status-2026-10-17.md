# FarmFinder status review — 17 October 2026

## Verdict

FarmFinder has a functioning national responsive web directory and a tested private feedback-review foundation. It is suitable for a clearly described product demonstration. It is not yet a fully operated, continuously maintained directory, a production RAG assistant, or a released native mobile app. Repository merges alone do not confirm production deployment.

## Three most recent project chats

- **Explain data review and RAG**: established monthly refresh policy (every other month acceptable), private feedback intake (#129), and authenticated curator review with leased triage (#131). Activation, correction publication, safe recurring reconciliation, and RAG remain separate work.
- **Review and merge PR, test app**: reviewed merged #130 at desktop and 390×844 mobile sizes. Search, product filters, profiles, map navigation, and Ask-to-search continuity worked. Reported misleading vegetable classifications, approximate Directions destinations, low-information initial results, unavailable correction tools by default, and engineering language in the empty map.
- **Gather Shutterstock product photos**: delivered #127, #128, and #130: location-preserving product browsing, compact mobile scope, useful card activation, accessible filter state, keyboard city suggestions, contact hierarchy, safe farm website links, and normalized presentation. Permissioned farm logos, more imagery, visual regression baselines, and usability sessions remain planned.

The first chat's latest handoff said #131 was ready, not merged; this review merged it after fresh verification. The previous walkthrough tested a local build, not a production deployment.

## Web

Working in the current source: nationwide directory; city typeahead and disambiguation; radius/product/purchasing filters; bounded list/map APIs; URL-preserved search state; map clusters and farm details; farm profiles; source/precision disclosures; and listing-grounded Ask searches. Product imagery, brand typography, reduced-motion behavior, and keyboard support are implemented.

The runtime reads a generated compact national index. PostgreSQL/PostGIS migrations, local integration infrastructure, and an eligible-feed sink exist, but canonical authority remains the committed state JSON store. The 299-row workbook-era artifact is rollback/provenance only. `data:validate` still checks that legacy workbook contract and is not the national feed test; feed generation and data gates validate the national publication.

Ask currently parses/searches directory information. It is not a deployed hybrid RAG system with generated, citation-backed answers. There is no evidence here of model training on reports, live inventory, checkout, or verified current opening hours.

## Imagery

The recent imagery chat and its local manifest record 21 approved generated images (14 landscape, 7 portrait), covering the initial category set and Louisiana module. They remain local and are not integrated into public assets. The regional production plan tracks the remaining national anchors and production curation. Eight strong official-logo candidates were researched for a five-farm pilot, but permissioned acquisition and publication remain outstanding. These assets are separate from the product photography already shipped in the web app.

## Mobile

The responsive website is implemented and has prior successful 390×844 browser walkthrough coverage. Mobile search retains location and filters; the compact scope can be edited; mapped card taps switch to map detail; unmapped farms open profiles. List access remains available without relying on map gestures.

Native iOS/Android remains a plan and prototype. There is no Expo application package, native build configuration, or device/store release verified in this repository. Existing architecture recommends Expo/React Native and four tabs: Discover, Map, All farms, Saved. Authenticated saved farms, private notes, secure token storage, offline states, native location flows, VoiceOver/TalkBack device checks, and distribution builds remain implementation requirements. Historical HTML demos are not native apps.

The mobile documents now distinguish native planning from implemented responsive web and replace the obsolete 299-listing payload assumption with generated national coverage. The remaining architecture is a target, not deployed behavior.

## Data and trust

Fresh feed generation reproduced 72,396 collected records across 50 states, 68,618 eligible public records, and 3,778 retained QA candidates. Of the public records, 54,821 are mappable and 13,797 are not. 10,308 have privacy-cleared public contacts; 51,984 lack a captured website. Missing websites are not evidence of closure or absence of a real website.

Generated public location classifications include 46,111 points, 4,993 city approximations, and 3,717 county approximations. Those categories alone are not proof of a currently visitable farm entrance. Publication tests found no prohibited contact/address/internal-field leakage in their checked rules, and every published row carried provenance.

The feed's release label is still July 2026. Rebuilding that feed today does not independently verify that every farm is still operating today.

## Feedback and maintenance

Implemented: private intake, durable idempotent receipts, separate contact storage, authenticated curator review, signed Cloudflare Access identity verification, audited revision-checked decisions, queue pagination, and bounded leased triage with retry and crash recovery. Approval deliberately does not alter the public directory.

Before activation: provision/verify managed storage and connectivity, apply migrations and restricted-role grants, configure Access issuer/audience/curator allowlist, set feature gates, assign operators and retention, verify backup/recovery and abuse controls, and exercise deployed end-to-end intake/review. No live activation or external user submission was performed during this review.

Still to build: safe refresh reconciliation preserving named candidates and corrections when sources fail; dated operating-status evidence; approved-decision-to-canonical publication; scheduling and operational monitoring; and a held-out retrieval/evaluation suite before generated answers.

## Dependency audit

A fresh `npm audit --json` reports 33 findings: 2 critical, 24 high, 6 moderate, and 1 low. The critical entries include direct dependencies MapLibre GL and Next. This is an audit inventory, not a runtime exploitability assessment. CI passing does not clear these findings. Dependency upgrades and reachability triage need a dedicated tested pass before a broad public launch; no automated force-upgrade was applied during backlog reconciliation.

## Prioritized remaining work

1. Correct food-filter evidence: nursery/flower-only descriptions currently enter vegetable results. Retain candidates and provenance; do not silently drop farms.
2. Map action wording is corrected in this cleanup: approximate points say “View approximate area”; point locations say “View on Google Maps.” Neither action promises a confirmed visit entrance. Screenshot inspection also caught and fixed a later CSS rule clearing the primary action background while leaving white text.
3. Activate feedback only after its documented infrastructure/operator gates pass, then connect reviewed corrections to governed publication.
4. Make initial results more useful through evidence-backed enrichment and an actionable-listings option; incomplete records should remain durable.
5. Empty-map language is corrected in this cleanup to ask visitors to choose a city. Anchor targets also clear the restored sticky header.
6. Finish safe reconciliation before scheduling refreshes. Add monitored freshness rather than a misleading last-verified date.
7. Establish visual baselines, real-device accessibility/performance checks, permissioned identity media, and task-based usability sessions.
8. Build native mobile after the API/auth/save contracts are stable; keep it distinct from mobile-web readiness.

## Verification boundaries

This review reran pipeline/tooling suites (48 and 3 passing tests), legacy release validation, source validation, 17 publication gates, lint, production builds, deployment budgets, and application/HTTP tests. The final general run passed 130 of 133 unit tests and 11 of 12 HTTP tests; the other four were optional database tests skipped without their environment variables. No test failed. The worker was 0.71 MiB compressed and the largest static asset 8.00 MiB, within the enforced budgets. The feedback storage/review/worker integration run passed all 22 tests against disposable local PostgreSQL databases. The general suite skips database tests unless explicitly configured; skipped tests are not counted as passes.

A fresh Chromium/WebGL run completed 14 desktop (1440×900) and mobile (390×844) captures covering typeahead, ambiguous cities, typo recovery, list/map discovery, basemaps, density controls, and farm selection. Mobile city controls measured 50–52 CSS pixels high. A second targeted browser pass confirmed the final approximate-map label at both widths, no horizontal overflow, anchor clearance below the sticky header, and the new empty-map instruction. This remains browser emulation, not native-device certification. No production deployment, live feedback activation, real phone purchase journey, native device test, or app-store release is claimed.

## PR and local-work inventory

- #131 merged: authenticated private feedback review and leased triage.
- #117 merged after conflict resolution: remaining focus, sticky containment, small-label, and dynamic mobile viewport fixes. Current search, imagery, and feedback code were retained.
- #92 merged after removing unrelated Arkansas QA changes: historical design system and standalone browser demos, explicitly labeled as a former 299-row prototype.
- #114 merged as historical explorer usability documentation. Later production map/discovery changes superseded its old runtime patch.
- #115 merged as five historical walkthrough screenshots and an index. Current icons, photos, dependencies, README, and production UI were retained.
- This follow-up records current status, corrects stale mobile/feedback documentation, clarifies approximate map links and empty-map text, and adds anchor clearance for the restored sticky header.

The older worktree commits for data expansion, README restructuring, and typography were already merged in #99, #100, and #101. The primary checkout's governance edits and plan files are older copies of material already in main; its handoff note references an obsolete branch state. Those local files were preserved, not republished as new implementation or overwritten. Some old worktree Git pointer files still reference the previous repository location; this review inspected their registered Git metadata without modifying those checkouts.
