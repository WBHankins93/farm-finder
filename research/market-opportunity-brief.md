# FarmFinder market opportunity and farmer-value strategy

> Updated 2026-08-30. FarmFinder is a standalone consumer-discovery product.
> Commercial services, customer records, and third-party promotions remain
> outside this repository and outside FarmFinder's product workflows.

## Decision summary

Release FarmFinder as a free, responsive web product and use real consumer
behavior to determine whether a native app or farmer-paid software is justified.
Do not charge farms for exposure until FarmFinder can show recurring consumer
demand, attributable contacts, or operational value that works independently of
audience size.

The near-term product job is simple: help a consumer find a relevant nearby
farm, understand what it produces, and reach a confirmed way to buy. The
near-term farmer job is equally simple: claim or correct a free listing and see
whether FarmFinder sends useful attention.

## Verified data asset

The committed canonical state store contains **72,396 unique records** across
all 50 states. **68,618** currently pass QA and privacy publication gates;
**3,778** named candidates remain durable in the QA residue.

Within the eligible feed:

| Documented attribute | Records | Share of eligible feed |
|---|---:|---:|
| Captured website | 16,634 | 24.2% |
| No captured website | 51,984 | 75.8% |
| Captured online store | 1,489 | 2.2% |
| Explicit direct-selling signal | 12,213 | 17.8% |
| Direct-selling signal and no online store | 10,724 | 15.6% |
| Direct-selling signal and no website | 6,891 | 10.0% |
| Website plus direct sales but no store | 4,008 | 5.8% |

These are discovery and enrichment counts, not final sales-prospect counts.
Empty website and channel fields can mean “not captured” rather than verified
absence because channel booleans currently default to false. Any market-sizing
or outreach use must first re-verify a representative sample against current
public business sources.

## Why free comes first

A farm should not pay $49 or $99 per month merely to appear before a small or
unproven audience. Exposure becomes chargeable only after FarmFinder can show a
repeatable result such as qualified website visits, calls, directions requests,
inquiries, or orders.

Free participation creates the useful initial flywheel:

1. Consumers get a broad, trustworthy directory without an account.
2. Farms can claim and correct listings without paying.
3. Better farm information improves search usefulness and trust.
4. Consumer usage produces evidence about which locations, products, and
   purchase paths have real demand.
5. Only then can FarmFinder evaluate paid capabilities that produce measurable
   value rather than selling speculative exposure.

## Web product before native app

Farm discovery is usually an occasional, search-led task. A responsive website
is easier to find through search, easier to share, and asks for no installation.
It should remain the primary product until repeat behavior proves that a native
app would improve retention.

A native app becomes justified only when at least two of these conditions hold:

- a meaningful cohort returns monthly to saved farms or alerts;
- consumers repeatedly use location-based discovery while away from home;
- farms publish source-backed availability often enough to support alerts;
- account retention shows value beyond one-time search traffic;
- push notifications or offline market navigation measurably improve outcomes.

Until then, invest in the responsive web app or PWA, indexed farm pages, fast
nearby search, saved links, and privacy-safe analytics.

## Farmer value ladder

### Free foundation

- Verified, claimable listing
- Correct products, purchase methods, public links, and service area
- Shareable farm profile
- Source and location-confidence transparency
- Basic privacy-safe views, outbound clicks, calls, and directions metrics
- Correction and freshness reminders

### Paid only after traffic evidence

- Enhanced attribution and conversion reporting
- Availability or event publishing with consumer alerts
- Inquiry or preorder capture tied to a farm's existing workflow
- Customer-list tools that the farm owns and can export
- Integrations with existing storefront, payment, CSA, or POS providers

### Separate operational software opportunity

Order entry, inventory, subscriptions, pickup scheduling, traceability,
accounting, and settlements can create value without FarmFinder traffic. They
also create a much larger vertical-SaaS obligation: onboarding, support,
payments, migrations, compliance, and uptime. FarmFinder should enter that
category only after interviews and paid pilots identify one narrow operational
problem that existing products do not solve affordably.

## Monetization gates

Do not launch a farmer subscription until FarmFinder can demonstrate:

- at least 1,000 monthly active consumers in a concentrated launch market;
- at least 100 measurable contact or outbound-commerce actions per month;
- at least 25 claimed farms updating or confirming their listing;
- a six-week cohort in which farms can identify useful leads or saved time;
- five or more farms willing to pay after seeing their own results.

The thresholds are decision gates, not forecasts. They prevent the product from
charging for theoretical value.

## Next experiments

1. Remove stale national-count and runtime-source inconsistencies.
2. Launch the free web directory with event instrumentation for searches,
   profiles, outbound links, calls, directions, claims, and corrections.
3. Re-verify a stratified sample of 200 direct-selling records with no captured
   store to estimate true website/store gaps.
4. Recruit 25 farms into a free listing-claim and analytics pilot.
5. Interview consumers and farms after six weeks using observed behavior rather
   than hypothetical feature interest.
6. Revisit native mobile and paid farmer tools only against the gates above.

## Privacy and business boundary

FarmFinder data exists to support governed farm discovery. Exact private
locations and uncleared contacts remain internal. FarmFinder listings, claims,
corrections, and analytics must never silently become another business's leads,
customer records, or promotions. Any activity outside FarmFinder requires its
own public-source verification, consent, records, and opt-out process.
