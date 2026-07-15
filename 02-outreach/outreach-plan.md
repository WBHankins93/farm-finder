# Sproutflow Studios — Farm Outreach Plan (v1)

> Goal: turn offline South Louisiana farms into Sproutflow clients through Sproutflow's separate website-service business. FarmFinder listing corrections are optional, governed contributions rather than a sales deliverable.

> **Scope boundary:** This is private Sproutflow company planning, not FarmFinder app functionality, the FarmFinder product roadmap, or the FarmFinder business model. Any correction or voluntary listing information learned through this work enters FarmFinder only through its consent, provenance, privacy, and verification process.

## Positioning

"Most farms around here aren't findable online. We build simple, affordable farm websites — so your extra produce reaches the community instead of going to waste." Sproutflow's nature-adjacent name is a built-in trust signal; lead with local + agricultural framing, never "web agency."

## Service tiers

| Tier | What | Reference | Notes |
|---|---|---|---|
| 1. Presence | 1-page static site: who/where/what/when, map, phone, photos | — | The default. Fast to build, near-zero maintenance. Most farms need only this. |
| 2. Storefront-lite | Static site + product list, seasonal availability, order-by-form or Square/Stripe payment links | — | For farms with steady surplus. Avoid full e-commerce complexity. |
| 3. Full ordering | Catalog + cart + fulfillment (pickup/market/delivery slots) | rareseeds.com (aspirational ceiling, not the template) | Only for farms with real volume. Few will need this — don't upsell into it. |

**Pricing: OPEN QUESTION.** Options: (a) one-time build + cheap hosting pass-through — easiest yes, no recurring revenue; (b) low monthly ($25–75/mo hosted, includes updates) — recurring revenue and an ongoing relationship that keeps database data fresh, but a harder sell to cash-tight farms; (c) hybrid: small setup fee + small monthly. Recommend (c), but validate against the first 5 pilots' reactions before standardizing.

## Outreach approach

Farms are a face-first, low-trust-of-tech audience. Channel priority:

1. **In person** — farmers markets, farm stands. Buy something first. This is the channel that will actually convert.
2. **Referral** — every client asks "which other farms should be online?" This also enriches the database.
3. **Phone** — second-best for the offline majority (they have no email to cold-email).
4. Facebook groups / ag extension newsletters — awareness only.

### Pilot (first 5 farms)

- Pick 5 from the database with: surplus production, market presence, zero web presence.
- Offer: pilot pricing (or 1 free flagship build) in exchange for a testimonial + referral intros.
- Every conversation, regardless of outcome, updates the farm's database record (`outreach_status`, contact, products).

### Talk track (draft)

- Open: local, specific, not salesy — "I'm building a directory of farms around [parish]. Wanted to make sure you're in it."
- The directory ask is the wedge: it's free, it's flattering, and it opens the website conversation naturally: "You're one of about 9 in 10 farms here with no website — when someone Googles 'eggs near me', you don't exist. I fix that for farms specifically."
- ⚠️ Don't quote the 90% figure as fact until we've verified it (see AGENTS.md open questions). Until then: "most farms around here."

## What this optimizes for / sacrifices

Optimizes: trust-based local growth, database enrichment as a side effect, low delivery cost per client (static sites). Sacrifices: speed and scale — in-person outreach doesn't parallelize; revenue per client is small. Alternative: paid ads / cold email at scale would be faster but would burn trust with exactly the audience the app track later depends on. Wrong trade for this niche.

## Risks

- Farms churn on monthly billing → keep tier 1 cheap enough that churn is rare.
- Maintenance requests creep on "static" sites → scope updates into the monthly fee explicitly (e.g., seasonal updates 2×/yr).
- Database consent: get explicit OK to list each farm publicly — needed before the app ships.

## Metrics

Contacts/week, contact→client rate, avg revenue/client, database records added per outreach hour, % of region covered.
