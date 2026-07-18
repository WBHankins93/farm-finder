"""Canonical FarmFinder data model — the one schema every pipeline stage speaks.

This replaces the 47-column, governance-shaped `entities.csv` with a flat
product + provenance record. Provenance is preserved (`source`, `source_url`);
the evidence-grade lattice, the append-only decision ledgers, and the promotion
contract that enforced them are gone. A record carries exactly what the product
needs plus where it came from.

Stages consume and produce `Farm` instances:
    collect  -> raw Farm (eligible unknown)
    cleanse  -> normalized, categorized, deduped, eligibility decided
    qa       -> eligible partition published, residue exported
    publish  -> Farm.to_app_record() feeds the web/app directory

Design note: the app already ships a `Farm` TypeScript type
(`03-app/site/app/lib/farms.ts`). `to_app_record()` is the contract between this
model and that type — keep them in lockstep.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

# The product's fixed category vocabulary (mirrors categoryColors in farms.ts).
CATEGORIES = (
    "Produce",
    "Mixed",
    "Meat",
    "Honey/Specialty",
    "Dairy",
    "Seafood",
    "Rice",
    "Urban Farm",
    "Value-Added",
)

# Geo precision, coarsest-trusted last. `county-approx` is our in-repo fallback
# (a county centroid synthesized from geocoded siblings); `ungeocoded` never
# reaches the map layer.
GEO_PRECISION = ("point", "address", "city", "county-approx", "ungeocoded")


@dataclass
class Provenance:
    """Where a record came from. One source name + URL replaces the entire
    evidence-grade / source-observation apparatus."""

    source: str = ""
    source_url: str = ""
    retrieved: str = ""  # ISO date, e.g. "2026-07-16"

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "source_url": self.source_url, "retrieved": self.retrieved}


@dataclass
class Contact:
    """Contact details are privacy-gated. `public` starts False for everything
    migrated in; the publish step only ever emits a public contact string when
    `public` is True (privacy rule: internal_until_public_use_review)."""

    phone: str = ""
    email: str = ""
    address: str = ""
    public: bool = False

    def public_string(self) -> str:
        """What the directory is allowed to show. Address is never published
        verbatim — only phone/email once a record is cleared for public use."""
        if not self.public:
            return ""
        return self.phone or self.email or ""


@dataclass
class Geo:
    latitude: float | None = None
    longitude: float | None = None
    precision: str = "ungeocoded"

    @property
    def mappable(self) -> bool:
        return (
            self.latitude is not None
            and self.longitude is not None
            and self.precision != "ungeocoded"
        )


@dataclass
class Farm:
    """One farm / local-food producer. The unit every stage passes along."""

    id: str
    name: str
    state: str
    region: str = ""  # pipeline region (southeast, ...) — see regions.json
    county: str = ""  # county-equivalent (parish in LA)
    city: str = ""
    category: str = "Mixed"
    products: list[str] = field(default_factory=list)
    products_text: str = ""
    website: str = ""
    facebook_url: str = ""
    instagram_url: str = ""

    # sales channels
    on_farm: bool = False
    farmers_market: bool = False
    csa: bool = False
    online_store: bool = False
    ships: bool = False
    u_pick: bool = False

    contact: Contact = field(default_factory=Contact)
    geo: Geo = field(default_factory=Geo)
    notes: str = ""
    provenance: Provenance = field(default_factory=Provenance)

    # pipeline state — the whole of what used to be promotion_status + blockers
    eligible: bool = False
    qa_reason: str = ""

    # ---- serialization -------------------------------------------------

    def market_presence(self) -> str:
        labels = [
            (self.farmers_market, "Farmers market"),
            (self.on_farm, "On-farm sales"),
            (self.u_pick, "U-pick"),
            (self.csa, "CSA"),
            (self.ships, "Delivery"),
            (self.online_store, "Online store"),
        ]
        return ", ".join(label for flag, label in labels if flag)

    def to_app_record(self) -> dict[str, Any]:
        """Emit the exact shape `03-app/site/app/lib/farms.ts::Farm` expects.

        This is the publish contract. Only privacy-cleared contact is included;
        geo is emitted with its precision so the map can skip `ungeocoded`.
        """
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category if self.category in CATEGORIES else "Mixed",
            "region": self.region_display(),
            "parish": self.county,
            "state": self.state,
            "city": self.city,
            "productsText": self.products_text,
            "products": self.products,
            "marketPresence": self.market_presence(),
            "website": self.website,
            "hasWebsite": bool(self.website),
            "onlineStore": self.online_store,
            "facebook": bool(self.facebook_url),
            "instagram": bool(self.instagram_url),
            "farmersMarket": self.farmers_market,
            "csa": self.csa,
            "ships": self.ships,
            "onFarm": self.on_farm,
            "contact": self.contact.public_string(),
            "notes": self.notes,
            "source": self.provenance.source,
            "latitude": self.geo.latitude if self.geo.latitude is not None else 0.0,
            "longitude": self.geo.longitude if self.geo.longitude is not None else 0.0,
            "geoPrecision": self.geo.precision,
        }

    def region_display(self) -> str:
        """The app's `region` field is a sub-state locality label. We don't have
        curated sub-state regions for migrated rows, so fall back to the county.
        (Refining these is a downstream enrichment task, not a schema concern.)"""
        return self.county or self.region

    def to_record(self) -> dict[str, Any]:
        """Full canonical serialization — round-trips losslessly via from_record."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "region": self.region,
            "county": self.county,
            "city": self.city,
            "category": self.category,
            "products": self.products,
            "products_text": self.products_text,
            "website": self.website,
            "facebook_url": self.facebook_url,
            "instagram_url": self.instagram_url,
            "on_farm": self.on_farm,
            "farmers_market": self.farmers_market,
            "csa": self.csa,
            "online_store": self.online_store,
            "ships": self.ships,
            "u_pick": self.u_pick,
            "contact": {
                "phone": self.contact.phone,
                "email": self.contact.email,
                "address": self.contact.address,
                "public": self.contact.public,
            },
            "geo": {
                "latitude": self.geo.latitude,
                "longitude": self.geo.longitude,
                "precision": self.geo.precision,
            },
            "notes": self.notes,
            "provenance": self.provenance.to_dict(),
            "eligible": self.eligible,
            "qa_reason": self.qa_reason,
        }

    @classmethod
    def from_record(cls, r: dict[str, Any]) -> "Farm":
        c = r.get("contact", {}) or {}
        g = r.get("geo", {}) or {}
        p = r.get("provenance", {}) or {}
        return cls(
            id=r["id"],
            name=r["name"],
            state=r["state"],
            region=r.get("region", ""),
            county=r.get("county", ""),
            city=r.get("city", ""),
            category=r.get("category", "Mixed"),
            products=list(r.get("products", [])),
            products_text=r.get("products_text", ""),
            website=r.get("website", ""),
            facebook_url=r.get("facebook_url", ""),
            instagram_url=r.get("instagram_url", ""),
            on_farm=bool(r.get("on_farm", False)),
            farmers_market=bool(r.get("farmers_market", False)),
            csa=bool(r.get("csa", False)),
            online_store=bool(r.get("online_store", False)),
            ships=bool(r.get("ships", False)),
            u_pick=bool(r.get("u_pick", False)),
            contact=Contact(
                phone=c.get("phone", ""),
                email=c.get("email", ""),
                address=c.get("address", ""),
                public=bool(c.get("public", False)),
            ),
            geo=Geo(
                latitude=g.get("latitude"),
                longitude=g.get("longitude"),
                precision=g.get("precision", "ungeocoded"),
            ),
            notes=r.get("notes", ""),
            provenance=Provenance(
                source=p.get("source", ""),
                source_url=p.get("source_url", ""),
                retrieved=p.get("retrieved", ""),
            ),
            eligible=bool(r.get("eligible", False)),
            qa_reason=r.get("qa_reason", ""),
        )

    def copy(self, **changes: Any) -> "Farm":
        return replace(self, **changes)


# ---- identity ----------------------------------------------------------

_slug_strip = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Stable, URL-safe id stem. Matches the style of the shipped ids
    (e.g. "2 Guys Honey" -> "2-guys-honey")."""
    s = _slug_strip.sub("-", name.strip().lower()).strip("-")
    return s or "farm"


def normalized_name(name: str) -> str:
    """Identity key for dedupe: lowercased, punctuation-stripped, de-suffixed."""
    s = name.strip().lower()
    s = re.sub(r"\b(llc|inc|l\.?l\.?c\.?|co|farms?|farm|the)\b", " ", s)
    s = _slug_strip.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()
