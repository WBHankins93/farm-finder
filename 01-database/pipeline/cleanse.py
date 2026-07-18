"""Cleanse stage — deterministic normalization, classification, dedupe, and the
single eligibility decision.

This is the load-bearing stage. It replaces the evidence-grade gate and the
per-row human promotion decision with rules that run in code:

    normalize  -> parse products, sales channels, urls
    classify   -> derive the product category from free text
    dedupe     -> merge same-identity rows within a state
    decide     -> eligible: bool + qa_reason: str  (one call, no ledger)

Everything here is pure and testable; no I/O, no network.
"""
from __future__ import annotations

import re

from model import CATEGORIES, Farm, normalized_name

# --- value parsing ------------------------------------------------------

_TRUE = {"true", "t", "yes", "y", "1"}


def parse_bool(v: str | bool | None) -> bool:
    if isinstance(v, bool):
        return v
    return str(v or "").strip().lower() in _TRUE


def parse_products(text: str) -> list[str]:
    """Free-text product string -> deduped, trimmed list. Sources delimit with
    commas, semicolons, or ' and '."""
    if not text:
        return []
    raw = text.replace(";", ",").replace(" and ", ",")
    seen: list[str] = []
    for part in raw.split(","):
        p = part.strip(" .;")
        if p and p.lower() not in {s.lower() for s in seen}:
            seen.append(p)
    return seen


# --- category classification -------------------------------------------
# Ordered most-specific first; first hit wins. The product record has no
# category column upstream, so we derive it here from products + business type.
# Matching is on WORD BOUNDARIES — substring matching wrongly fires "bee" inside
# "beef" and "tea" inside "steak". Meat precedes Honey/Specialty so "beef" is
# decided before any specialty token can be considered.

_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Seafood", ("shrimp", "crawfish", "crawdad", "oyster", "oysters", "seafood", "fish", "catfish", "aquaculture", "shellfish")),
    ("Rice", ("rice",)),
    ("Dairy", ("dairy", "milk", "cheese", "creamery", "yogurt")),
    ("Meat", ("beef", "cattle", "pork", "hog", "hogs", "poultry", "chicken", "lamb", "goat", "goats", "bison", "meat", "livestock", "egg", "eggs")),
    ("Honey/Specialty", ("honey", "apiary", "beekeeper", "pollinator", "jam", "jelly", "preserves", "soap", "candle", "candles", "herb", "herbs", "tea", "coffee")),
    ("Urban Farm", ("urban", "rooftop", "hydroponic", "hydroponics", "aquaponic", "aquaponics", "microgreens")),
    ("Value-Added", ("value-added", "value added", "bakery", "baked", "milled", "flour", "wine", "winery", "cidery", "processed")),
    ("Produce", ("vegetable", "vegetables", "produce", "fruit", "fruits", "berry", "berries", "orchard", "nursery", "flower", "flowers", "pumpkin", "pumpkins", "melon", "melons", "u-pick", "u pick", "greenhouse", "peach", "peaches", "apple", "apples", "citrus")),
]

# Precompile a word-boundary regex per category.
_CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (cat, re.compile(r"\b(?:" + "|".join(re.escape(t) for t in toks) + r")\b", re.I))
    for cat, toks in _CATEGORY_RULES
]


def classify_category(products_text: str, business_types: str = "") -> str:
    hay = f"{products_text} {business_types}"
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(hay):
            return category
    return "Mixed"


# --- eligibility --------------------------------------------------------


def decide_eligibility(farm: Farm) -> tuple[bool, str]:
    """The whole promotion decision, in code.

    A named producer is eligible to list when it has an identity and a place.
    Missing data produces a routable `qa_reason`, never a silent drop
    (non-deletion policy). Geography that is missing but recoverable is a soft
    blocker the geo stage can later clear.
    """
    if not farm.name.strip():
        return False, "missing name"
    if not farm.state.strip():
        return False, "missing state"
    if not (farm.county.strip() or farm.city.strip()):
        return False, "missing geography: no county or city"
    if not farm.provenance.source.strip():
        return False, "missing provenance: no source"
    return True, ""


# --- dedupe -------------------------------------------------------------


def _merge(primary: Farm, other: Farm) -> Farm:
    """Fold `other` into `primary`, preferring populated fields and OR-ing the
    boolean sales channels. Provenance keeps the primary's source but appends the
    other's name so the merge is traceable."""
    p = primary
    p.city = p.city or other.city
    p.county = p.county or other.county
    p.website = p.website or other.website
    p.facebook_url = p.facebook_url or other.facebook_url
    p.instagram_url = p.instagram_url or other.instagram_url
    p.products = p.products or other.products
    p.products_text = p.products_text or other.products_text
    for chan in ("on_farm", "farmers_market", "csa", "online_store", "ships", "u_pick"):
        setattr(p, chan, getattr(p, chan) or getattr(other, chan))
    p.contact.phone = p.contact.phone or other.contact.phone
    p.contact.email = p.contact.email or other.contact.email
    p.contact.address = p.contact.address or other.contact.address
    if p.geo.latitude is None and other.geo.latitude is not None:
        p.geo = other.geo
    if other.provenance.source and other.provenance.source not in p.provenance.source:
        p.provenance.source = f"{p.provenance.source}; {other.provenance.source}".strip("; ")
    if p.category == "Mixed" and other.category != "Mixed":
        p.category = other.category
    return p


def dedupe(farms: list[Farm]) -> tuple[list[Farm], int]:
    """Merge same-identity rows within each (state, county). Returns the deduped
    list and the number of rows collapsed. Same name in *different* counties is
    kept distinct — that split is deliberate (cross-county identity is a real
    separate operation until proven otherwise)."""
    groups: dict[tuple[str, str, str], Farm] = {}
    order: list[tuple[str, str, str]] = []
    collapsed = 0
    for f in farms:
        key = (f.state, f.county.lower(), normalized_name(f.name))
        if key in groups:
            _merge(groups[key], f)
            collapsed += 1
        else:
            groups[key] = f
            order.append(key)
    return [groups[k] for k in order], collapsed


# --- top-level cleanse pass --------------------------------------------


def cleanse(farms: list[Farm]) -> dict[str, int]:
    """Run in place: (re)classify, dedupe, decide eligibility. Returns a summary.
    Callers pass the deduped result back out via the returned list on `farms`."""
    for f in farms:
        if f.category == "Mixed" or f.category not in CATEGORIES:
            f.category = classify_category(f.products_text, "")
    deduped, collapsed = dedupe(farms)
    eligible = 0
    for f in deduped:
        f.eligible, f.qa_reason = decide_eligibility(f)
        eligible += f.eligible
    farms[:] = deduped
    return {"total": len(deduped), "merged": collapsed, "eligible": eligible, "residue": len(deduped) - eligible}
