# Vegetable filter evidence

Verified against the committed canonical dataset on 2026-10-19.

The vegetable filter now matches bounded vegetable aliases in `productsText`
and `products` only. Category `Produce` also covers fruit and nurseries, and
administrative notes can describe registration programs rather than products;
neither is vegetable evidence. Generic `produce` and `producer` do not imply
vegetables. Existing other product facets retain their rules.

Missing aliases include asparagus, eggplant, peppers, artichokes, beets and
irregular plurals such as tomatoes and potatoes. New phrases such as sweet
corn and green beans avoid broadly treating grain/forage corn or all beans as
vegetables. Every alias uses word boundaries, so evergreens do not match greens.

A complete publication-path comparison preserved all 68,618 eligible IDs and
all non-vegetable product masks. Vegetable memberships changed as follows:

| Scope | Before | After | Removed memberships | Added memberships |
|---|---:|---:|---:|---:|
| National | 17,346 | 9,838 | 7,893 | 385 |
| Louisiana | 772 | 88 | 686 | 2 |

These are rule changes, not a measured false-positive rate or closures. Records
with only generic produce evidence remain searchable in the directory. Product
counts are generated from the same masks used by filtering. Historical dated
reports retain their checkpoint counts; current UI counts are never hardcoded.

A deterministic review of 50 added and 50 removed memberships prompted removal
of bare corn, green, singular herb/pea and generic bean aliases. It also added
`veggie`. This was a stored-text review, not farm inventory verification.
Remaining limitations include negation, cover-crop radishes, processed vegetable
products, and mixed narrative scraped into product fields. Keyword matching
cannot prove current stock, on-farm retail access or absence of a product.
Follow-up evidence review and canonical classification work remain necessary.

Regression tests cover nursery-only/fruit-only/generic-producer evidence,
administrative notes, evergreen boundaries, explicit aliases, mixed products,
other-facet preservation, counts/mask parity and the documented negation limit.
Deploy or roll back the application, generated index and generated stats as one
coherent bundle. No canonical data, privacy policy or eligibility changed.
