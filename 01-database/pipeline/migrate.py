"""Migration — fold the 15,703 already-collected rows into the canonical model.

One-time bridge from the 47-column `research/state-expansions/<ST>/entities.csv`
governance schema to the flat `model.Farm`. It:

  1. maps every entity row -> Farm (seeding eligibility from the *existing*
     human promotion decision — prior QA is respected, never overridden),
  2. runs the cleanse stage (classify + dedupe; integrity demotion only),
  3. applies the in-repo geo fallback (county-centroid placement),
  4. applies the privacy gate (contacts held internal by default),
  5. partitions QA residue (no auto-promotion — see run_qa rules=[]),
  6. writes canonical + app + residue + report to build/.

Nothing is overwritten in the app or the research tree; all output lands in
`01-database/pipeline/build/` (git-ignored). Cutover is a separate, later step.

    python3 01-database/pipeline/migrate.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cleanse import classify_category, parse_bool, parse_products  # noqa: E402
from geo import apply_geo_fallback  # noqa: E402
from model import Contact, Farm, Geo, Provenance, normalized_name, slugify  # noqa: E402
from privacy import apply_privacy  # noqa: E402
from publish import write_app_json  # noqa: E402
from qa import rule_reclear_now_geocoded, run_qa  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXPANSIONS = ROOT / "research" / "state-expansions"
BUILD = Path(__file__).resolve().parent / "build"

ELIGIBLE_STATUS = "promotion_eligible_reviewed"


def _float(v: str) -> float | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _first(v: str) -> str:
    """Sources pack multiple values with '; ' — take the first for the single
    provenance field, keeping the rest discoverable in the full string."""
    return (v or "").split(";")[0].strip()


def _clean_note(v: str) -> str:
    """Drop the staged evidence-grade boilerplate — it's provenance plumbing,
    not something a directory visitor should read."""
    note = (v or "").strip()
    if note.lower().startswith("fields are selected by evidence grade") or note.lower().startswith(
        "fields selected by evidence grade"
    ):
        return ""
    return note


def load_region_map() -> dict[str, str]:
    data = json.loads((Path(__file__).resolve().parent / "regions.json").read_text())
    return {st: name for name, r in data["regions"].items() for st in r["states"]}


def map_row(row: dict, region: str) -> Farm:
    products_text = row.get("products", "")
    business_types = row.get("business_types", "")
    channel_text = f"{products_text} {business_types}".lower()
    eligible = row.get("promotion_status", "") == ELIGIBLE_STATUS
    blockers = (row.get("promotion_blockers", "") or "").strip()
    # Privacy: rows classified county-only must never publish a precise
    # coordinate (it may derive from a private address). Drop the coords so the
    # geo fallback places them at a reduced-precision county centroid instead.
    county_only = row.get("public_location_classification", "") == "county_only_no_public_address"
    lat = None if county_only else _float(row.get("latitude", ""))
    lng = None if county_only else _float(row.get("longitude", ""))
    return Farm(
        id="",  # assigned globally after dedupe to guarantee uniqueness
        name=row.get("farm_name", "").strip(),
        state=row.get("state", "").strip(),
        region=region,
        county=row.get("county_equivalent", "").strip(),
        city=row.get("city", "").strip(),
        category=classify_category(products_text, business_types),
        products=parse_products(products_text),
        products_text=products_text,
        website=row.get("website_url", "").strip(),
        facebook_url=row.get("facebook_url", "").strip(),
        instagram_url=row.get("instagram_url", "").strip(),
        on_farm=parse_bool(row.get("on_farm_sales")),
        farmers_market=parse_bool(row.get("farmers_market_sales")),
        csa="csa" in channel_text or "farm share" in channel_text,
        online_store=parse_bool(row.get("online_sales")),
        ships=parse_bool(row.get("local_delivery")),
        u_pick=parse_bool(row.get("u_pick")),
        contact=Contact(
            phone=row.get("phone_internal", "").strip(),
            email=row.get("email_internal", "").strip(),
            address=row.get("address_internal", "").strip(),
            public=False,
        ),
        geo=Geo(
            latitude=lat,
            longitude=lng,
            precision="city" if lat is not None else "ungeocoded",
        ),
        notes=_clean_note(row.get("notes", "")),
        provenance=Provenance(
            source=_first(row.get("source_names", "")),
            source_url=_first(row.get("source_urls", "")),
            retrieved=row.get("last_retrieved", "").strip(),
        ),
        eligible=eligible,
        qa_reason="" if eligible else (blockers or "research_or_qa_queue: reason not specified upstream"),
    )


def dedupe_preserving_qa(farms: list[Farm]) -> tuple[list[Farm], int]:
    """Merge same-identity rows within (state, county) without changing the
    prior eligibility decision. A merge is eligible if either side was."""
    groups: dict[tuple[str, str, str], Farm] = {}
    order: list = []
    merged = 0
    for f in farms:
        key = (f.state, f.county.lower(), normalized_name(f.name))
        if key in groups:
            p = groups[key]
            p.city = p.city or f.city
            p.website = p.website or f.website
            p.facebook_url = p.facebook_url or f.facebook_url
            p.instagram_url = p.instagram_url or f.instagram_url
            p.products = p.products or f.products
            p.products_text = p.products_text or f.products_text
            for chan in ("on_farm", "farmers_market", "csa", "online_store", "ships", "u_pick"):
                setattr(p, chan, getattr(p, chan) or getattr(f, chan))
            p.contact.phone = p.contact.phone or f.contact.phone
            p.contact.email = p.contact.email or f.contact.email
            p.contact.address = p.contact.address or f.contact.address
            if p.geo.latitude is None and f.geo.latitude is not None:
                p.geo = f.geo
            if p.category == "Mixed" and f.category != "Mixed":
                p.category = f.category
            p.eligible = p.eligible or f.eligible
            if p.eligible:
                p.qa_reason = ""
            merged += 1
        else:
            groups[key] = f
            order.append(key)
    return [groups[k] for k in order], merged


def assign_ids(farms: list[Farm]) -> None:
    used: set[str] = set()
    for f in farms:
        base = slugify(f.name) or "farm"
        stem = f"{base}-{f.state.lower()}"
        cand, n = stem, 2
        while cand in used:
            cand, n = f"{stem}-{n}", n + 1
        used.add(cand)
        f.id = cand


def integrity_demote(farms: list[Farm]) -> int:
    """Only ever *demotes*: an 'eligible' row missing a name or state can't be
    published. Never promotes — that would override human QA."""
    demoted = 0
    for f in farms:
        if f.eligible and (not f.name or not f.state):
            f.eligible, f.qa_reason = False, "integrity: missing name or state"
            demoted += 1
    return demoted


def build_state_canonical(state_code: str, region_map: dict | None = None) -> list[Farm]:
    """Map one state's entities.csv into pre-geo/pre-qa canonical Farm rows
    (mapped, deduped, id'd, integrity-checked). Shared by the full migration and
    by the orchestrator's staged bridge, so both speak the same canonical."""
    region_map = region_map or load_region_map()
    region = region_map.get(state_code, "unassigned")
    path = EXPANSIONS / state_code / "entities.csv"
    farms = [map_row(r, region) for r in csv.DictReader(path.open())]
    farms, _ = dedupe_preserving_qa(farms)
    assign_ids(farms)
    integrity_demote(farms)
    return farms


def run() -> dict:
    region_map = load_region_map()
    farms: list[Farm] = []
    per_state: dict[str, int] = {}
    for csv_path in sorted(EXPANSIONS.glob("*/entities.csv")):
        st = csv_path.parent.name
        per_state[st] = sum(1 for _ in csv.DictReader(csv_path.open()))
        farms.extend(build_state_canonical(st, region_map))

    ingested = sum(per_state.values())
    merged = ingested - len(farms)
    demoted = sum(1 for f in farms if not f.eligible and f.qa_reason.startswith("integrity:"))
    geo_stats = apply_geo_fallback(farms)
    privacy_stats = apply_privacy(farms)

    BUILD.mkdir(parents=True, exist_ok=True)
    # Preserve prior human QA except for the one agreed automation: rows blocked
    # purely on geography auto-clear once a real geocode places them (stream C).
    qa_stats = run_qa(farms, residue_path=BUILD / "qa-residue.csv", rules=[rule_reclear_now_geocoded])
    app_stats = write_app_json(farms, BUILD / "app-farms.json", eligible_only=True)
    (BUILD / "canonical.json").write_text(
        json.dumps([f.to_record() for f in farms], indent=2, ensure_ascii=False) + "\n"
    )

    report = {
        "ingested_rows": ingested,
        "per_state": per_state,
        "after_dedupe": len(farms),
        "merged": merged,
        "integrity_demoted": demoted,
        "geo": geo_stats,
        "privacy": privacy_stats,
        "qa": qa_stats,
        "publish": app_stats,
    }
    (BUILD / "migration-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    rep = run()
    q, g, pub = rep["qa"], rep["geo"], rep["publish"]
    print("FarmFinder migration —", rep["ingested_rows"], "rows in,", rep["after_dedupe"], "canonical after dedupe")
    print(f"  eligible (prior QA preserved): {q['eligible']}   residue: {q['residue']}")
    print(f"  geography-only residue (auto-clearable once geocoded): {q['geography_only_residue']}")
    print(f"  mappable: {g['mappable_before']} -> {g['mappable_after']}  (+{g['filled_county_approx']} county-approx, {g['counties_with_centroid']} counties)")
    print(f"  published to app: {pub['written']}  ({pub['mappable']} mappable, {pub['with_contact']} public contacts)")
    print("  build/ ->", ", ".join(sorted(p.name for p in BUILD.glob("*"))))
