#!/usr/bin/env python3
"""Draft review-only county resolutions for geography-blocked QA rows.

Reads a committed state's ``entities.csv``, resolves counties for QA rows whose
city maps to exactly one county in the Census national place-by-county
reference, and writes a proposal bundle for curator review. It never edits
contract files, never resolves an ambiguous place, and never overrides a
conflicting county — conflicts are flagged for human QA.

This is the post-hoc twin of the pre-classification pass in
``collect_southeast.apply_place_reference``; it exists to drain the geography
QA debt of releases collected without that pass (see qa-operations.md).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from collect_southeast import (
    CENSUS_PLACE_COUNTY_URL,
    CENSUS_GEOCODER_URL,
    FCC_AREA_URL,
    fetch,
    normalized_county,
    normalized_name,
)
from geocode_eligible import DEFAULT_CACHE, STATE_FIPS, read_cache, write_cache
from qa_triage import route
from state_policy import sufficient_promotion_evidence


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "source-releases" / "work"
QA_STATUS = "research_or_qa_queue"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
GEO_CLAUSE = re.compile(r"county requires geography review|county missing", re.I)
SERVICE_AREA_CLAUSE = re.compile(
    r"city or safe public service area (?:requires review|missing)", re.I
)
MARKET_CLAUSE = re.compile(r"farmers?'? market|farm market|market roster", re.I)
MARKET_CLASSIFICATION = "market_circuit_service_area"
ADDRESS_PRECISION = "county_centroid"
MARKET_PRECISION = "market_location_county"
ELIGIBLE_REQUIRED_FIELDS = [
    "entity_id", "farm_name", "entity_type", "identity_decision", "state",
    "county_equivalent", "city", "products", "public_location_classification",
    "contact_visibility", "source_urls", "last_retrieved",
]


def place_reference(state: str, body: str) -> dict[str, tuple[str, str, str]]:
    """Census places that fall wholly within one county of the state.

    Multi-county places are withheld so a city name alone can never silently
    assign an ambiguous county (same rule as the collector's reference).
    """
    fips = STATE_FIPS[state]
    rows = list(csv.DictReader(io.StringIO(body.lstrip("﻿")), delimiter="|"))
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("STATEFP") != fips or not (row.get("PLACENAME") or "").strip():
            continue
        display = re.sub(r"\s+(?:city|town|village|CDP)\s*$", "", row["PLACENAME"], flags=re.I)
        grouped[normalized_name(display)].append(row)
    mapping: dict[str, tuple[str, str, str]] = {}
    for key, matches in grouped.items():
        counties = {row.get("COUNTYFP", ""): row for row in matches}
        if len(counties) != 1:
            continue
        row = next(iter(counties.values()))
        display = re.sub(r"\s+(?:city|town|village|CDP)\s*$", "", row["PLACENAME"], flags=re.I)
        mapping[key] = (
            display.strip(),
            normalized_county(row.get("COUNTYNAME", "")),
            f"{fips}{row.get('COUNTYFP', '')}",
        )
    return mapping


def remaining_blockers(blockers: str, *, clear_service_area: bool = False) -> str:
    clauses = [clause.strip() for clause in (blockers or "").split(";") if clause.strip()]
    return "; ".join(
        clause for clause in clauses
        if not GEO_CLAUSE.search(clause)
        and not (clear_service_area and SERVICE_AREA_CLAUSE.search(clause))
    )


def proposed_status(row: dict[str, str], new_blockers: str, county: str) -> str:
    """QA unless every blocker is cleared AND the row stands on its own.

    Geography evidence never upgrades operation evidence, so the status
    proposal ignores the drafted decision's grade — observation grades alone
    must pass the evidence gate.
    """
    if new_blockers:
        return QA_STATUS
    patched = {**row, "county_equivalent": county}
    if any(not patched.get(field) for field in ELIGIBLE_REQUIRED_FIELDS):
        return QA_STATUS
    if not sufficient_promotion_evidence(row.get("evidence_grades", "")):
        return QA_STATUS
    return ELIGIBLE_STATUS


def has_street_address(value: str) -> bool:
    """Require a street number so city-only and PO-box text is not geocoded."""

    return bool(re.search(r"(?:^|\s)\d{1,6}[A-Za-z]?(?:[-/]\d+)?\s+[A-Za-z]", value or ""))


def address_cache_key(state: str, address: str) -> str:
    digest = hashlib.sha256(" ".join(address.split()).casefold().encode("utf-8")).hexdigest()
    return f"address|{digest}|{state.upper()}"


def cached_county(cache: dict[str, Any], key: str) -> tuple[str, str, str] | None:
    value = cache.get(key)
    if not isinstance(value, dict) or value.get("unresolved") is True:
        return None
    county = str(value.get("county") or "").strip()
    if not county:
        return None
    return county, str(value.get("county_fips") or "").strip(), str(value.get("source") or "").strip()


def cache_county(cache: dict[str, Any], key: str, county: str, county_fips: str, source: str) -> None:
    cache[key] = {
        "county": county,
        "county_fips": county_fips,
        "precision": ADDRESS_PRECISION,
        "source": source,
    }


def cache_unresolved(cache: dict[str, Any], key: str) -> None:
    cache[key] = {"unresolved": True}


def county_fips_value(state: str, value: Any) -> str:
    fips = str(value or "").strip()
    return fips if len(fips) == 5 else f"{STATE_FIPS[state]}{fips.zfill(3)}" if fips else ""


def parse_county_result(state: str, result: dict[str, Any], source: str) -> tuple[str, str, str] | None:
    if str(result.get("state_fips") or result.get("STATE") or "").strip() != STATE_FIPS[state]:
        return None
    county = normalized_county(result.get("county_name") or result.get("NAME") or "")
    return (county, county_fips_value(state, result.get("county_fips") or result.get("COUNTY")), source) if county else None


def fcc_county_from_coordinates(
    state: str,
    latitude: Any,
    longitude: Any,
    fetcher: Callable[[str], tuple[str, dict[str, Any]]],
) -> tuple[str, str, str] | None:
    url = f"{FCC_AREA_URL}?{urllib.parse.urlencode({'lat': latitude, 'lon': longitude, 'format': 'json'})}"
    body, _ = fetcher(url)
    try:
        results = json.loads(body).get("results") or []
    except (json.JSONDecodeError, TypeError):
        results = []
    return parse_county_result(state, results[0], FCC_AREA_URL) if len(results) == 1 and isinstance(results[0], dict) else None


def address_county(
    state: str,
    row: dict[str, str],
    fetcher: Callable[[str], tuple[str, dict[str, Any]]],
) -> tuple[tuple[str, str, str, str] | None, str]:
    """Resolve an internal address to a county; never return or cache coordinates."""

    address = (row.get("address_internal") or "").strip()
    params = {
        "address": ", ".join(value for value in (address, state, row.get("postal_code", "")) if value),
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    url = f"{CENSUS_GEOCODER_URL}?{urllib.parse.urlencode(params)}"
    body, request_log = fetcher(url)
    try:
        matches = json.loads(body).get("result", {}).get("addressMatches", [])
    except (json.JSONDecodeError, TypeError):
        matches = []
    if len(matches) > 1:
        return None, "Census geocoder returned multiple address matches"
    if matches and isinstance(matches[0], dict):
        counties = (matches[0].get("geographies", {}) or {}).get("Counties", []) or []
        parsed = [parse_county_result(state, item, CENSUS_GEOCODER_URL) for item in counties if isinstance(item, dict)]
        unique = {(item[0], item[1]) for item in parsed if item}
        if len(unique) == 1:
            county, fips = next(iter(unique))
            return (county, fips, CENSUS_GEOCODER_URL, ADDRESS_PRECISION), ""
        if len(unique) > 1:
            return None, "Census geocoder returned multiple counties"
        coordinates = matches[0].get("coordinates", {}) or {}
        if coordinates.get("x") is not None and coordinates.get("y") is not None:
            fallback = fcc_county_from_coordinates(state, coordinates["y"], coordinates["x"], fetcher)
            if fallback:
                county, fips, source = fallback
                return (county, fips, source, ADDRESS_PRECISION), ""
    return None, (request_log or {}).get("error") or "Census geocoder returned no county"


def market_evidence(row: dict[str, str]) -> bool:
    sales = (row.get("farmers_market_sales") or "").strip().casefold()
    explicit = sales in {"true", "yes", "1", "y", "t"}
    documented_source = bool((row.get("source_names") or "").strip() or (row.get("source_urls") or "").strip())
    named_market = bool(MARKET_CLAUSE.search(row.get("farm_name", "")))
    roster_source = bool(MARKET_CLAUSE.search(" ".join(
        row.get(field, "") for field in ("source_names", "source_urls", "notes")
    )))
    return explicit or (named_market and documented_source) or roster_source


def market_location_candidates(
    row: dict[str, str],
    reference: dict[str, tuple[str, str, str]],
) -> list[dict[str, str]]:
    """Extract only source-named Census places/counties from a market record."""

    text = " ".join(row.get(field, "") for field in ("market_location", "market_city", "market_county", "farm_name"))
    normalized_text = normalized_name(text)
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for place_key, (display, county, county_fips) in reference.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(place_key)}(?![a-z0-9])", normalized_text):
            key = (county, county_fips)
            if key not in seen:
                seen.add(key)
                candidates.append({"city": display, "county": county, "county_fips": county_fips})
    county_names = {normalized_name(county): (county, fips) for _, (_, county, fips) in reference.items()}
    for county_key, (county, county_fips) in county_names.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(county_key)}(?: county)?(?![a-z0-9])", normalized_text):
            key = (county, county_fips)
            if key not in seen:
                seen.add(key)
                candidates.append({"city": "", "county": county, "county_fips": county_fips})
    return candidates


def append_proposal(
    proposals: list[dict[str, Any]],
    state: str,
    row: dict[str, str],
    county: str,
    county_fips: str,
    source_url: str,
    precision: str,
    new_blockers: str,
    *,
    proposed_city: str = "",
    proposed_classification: str | None = None,
    decision_basis: str,
) -> None:
    existing = (row.get("county_equivalent") or "").strip()
    status_row = {**row, "county_equivalent": county}
    if proposed_city:
        status_row["city"] = proposed_city
    if proposed_classification:
        status_row["public_location_classification"] = proposed_classification
    status = proposed_status(status_row, new_blockers, county)
    review_id = "georeview_" + hashlib.sha256(
        f"{state}|{row.get('entity_id')}|{county_fips}|{precision}".encode("utf-8")
    ).hexdigest()[:20]
    proposals.append({
        "entity_patch": {
            "entity_id": row.get("entity_id"),
            "base_county_equivalent": existing,
            "proposed_county_equivalent": county,
            "base_city": row.get("city", ""),
            "proposed_city": proposed_city or row.get("city", ""),
            "base_promotion_blockers": row.get("promotion_blockers", ""),
            "proposed_promotion_blockers": new_blockers,
            "base_promotion_status": QA_STATUS,
            "proposed_promotion_status": status,
            "base_public_location_classification": row.get("public_location_classification", ""),
            "proposed_public_location_classification": proposed_classification or row.get("public_location_classification", ""),
            "base_geography_precision": row.get("geography_precision", ""),
            "proposed_geography_precision": precision,
            "human_review_required": True,
        },
        "decision": {
            "review_id": review_id,
            "farm_name": row.get("farm_name", ""),
            "normalized_name": row.get("normalized_name", ""),
            "decision": "correct",
            "evidence_grade": "B",
            "verified_entity_type": row.get("entity_type", ""),
            "county_equivalent": county,
            "city": proposed_city or row.get("city", ""),
            "postal_code": row.get("postal_code", ""),
            "products": row.get("products", ""),
            "business_types": row.get("business_types", ""),
            "website_url": row.get("website_url", ""),
            "source_url": source_url,
            "retrieved_date": datetime.now(timezone.utc).date().isoformat(),
            "decision_basis": decision_basis,
            "notes": "Draft only; a curator must apply this decision with its paired entity patch.",
            "target_normalized_name": "",
            "exclusion_reason": "",
            "supersedes_review_id": "",
            "geography_precision": precision,
        },
    })


def resolve_state(
    state: str,
    entities: list[dict[str, str]],
    reference: dict[str, tuple[str, str, str]],
    *,
    fetcher: Callable[[str], tuple[str, dict[str, Any]]] = fetch,
    cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state.upper()
    cache = cache if cache is not None else {}
    proposals: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    targets = 0
    occupied: dict[tuple[str, str], str] = {}
    for row in entities:
        occupied.setdefault(
            (row.get("normalized_name", ""), row.get("county_equivalent", "")),
            row.get("entity_id", ""),
        )

    address_results: dict[str, dict[str, Any]] = {}
    pending: dict[str, str] = {}
    rows_by_id = {row.get("entity_id", ""): row for row in entities}
    for row in entities:
        if (
            row.get("promotion_status") == QA_STATUS
            and route(row.get("promotion_blockers", ""))[0] == "geography"
            and not (row.get("city") or "").strip()
            and has_street_address((row.get("address_internal") or "").strip())
        ):
            entity_id = row.get("entity_id", "")
            key = address_cache_key(state, row.get("address_internal", ""))
            if key in cache:
                cached = cached_county(cache, key)
                address_results[entity_id] = {
                    "result": (*cached, ADDRESS_PRECISION) if cached else None,
                    "error": "" if cached else "cached unresolved address",
                    "cache_key": key,
                }
            else:
                pending[entity_id] = key
    if pending:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(address_county, state, rows_by_id[entity_id], fetcher): entity_id
                for entity_id in pending
            }
            for future in as_completed(futures):
                entity_id = futures[future]
                result, error = future.result()
                address_results[entity_id] = {
                    "result": result, "error": error, "cache_key": pending[entity_id],
                }

    for row in entities:
        if row.get("promotion_status") != QA_STATUS:
            continue
        if route(row.get("promotion_blockers", ""))[0] != "geography":
            continue
        targets += 1
        city = (row.get("city") or "").strip()
        if not city:
            address = (row.get("address_internal") or "").strip()
            if has_street_address(address):
                address_result = address_results.get(row.get("entity_id", ""), {})
                result = address_result.get("result")
                address_error = address_result.get("error", "")
                key = address_result.get("cache_key", address_cache_key(state, address))
                if result:
                    county, county_fips, source_url, _ = result
                    if key not in cache:
                        cache_county(cache, key, county, county_fips, source_url)
                else:
                    county = county_fips = source_url = ""
                    cache_unresolved(cache, key)
                if county:
                    peer = occupied.get((row.get("normalized_name", ""), county), "")
                    existing = (row.get("county_equivalent") or "").strip()
                    if peer and peer != row.get("entity_id"):
                        conflicts.append({
                            "entity_id": row.get("entity_id"),
                            "address_resolution": "county_only",
                            "existing_county": existing,
                            "census_county": county,
                            "colliding_entity_id": peer,
                            "recommended_action": "route_to_human_identity_qa",
                        })
                        continue
                    if existing and normalized_county(existing) != county:
                        conflicts.append({
                            "entity_id": row.get("entity_id"),
                            "address_resolution": "county_only",
                            "existing_county": existing,
                            "census_county": county,
                            "recommended_action": "route_to_human_qa",
                        })
                        continue
                    append_proposal(
                        proposals,
                        state,
                        row,
                        county,
                        county_fips,
                        CENSUS_GEOCODER_URL if source_url == CENSUS_GEOCODER_URL else FCC_AREA_URL,
                        ADDRESS_PRECISION,
                        remaining_blockers(row.get("promotion_blockers", "")),
                        decision_basis=(
                            "The Census geocoder/FCC Census Area API resolved the internal street "
                            f"address to {county}; only the county is proposed and no exact public "
                            "coordinate is emitted."
                        ),
                    )
                    continue
                if "multiple" in address_error.casefold():
                    conflicts.append({
                        "entity_id": row.get("entity_id"),
                        "address_resolution": "county_only",
                        "reason": address_error,
                        "recommended_action": "route_to_human_qa",
                    })
                else:
                    unresolved.append({"entity_id": row.get("entity_id"), "reason": address_error})
                continue

            if market_evidence(row):
                candidates = market_location_candidates(row, reference)
                if len(candidates) > 1:
                    conflicts.append({
                        "entity_id": row.get("entity_id"),
                        "market_name": row.get("farm_name", ""),
                        "candidate_locations": candidates,
                        "recommended_action": "route_to_human_qa",
                    })
                    continue
                if len(candidates) == 1:
                    market = candidates[0]
                    county, county_fips, market_city = market["county"], market["county_fips"], market["city"]
                    peer = occupied.get((row.get("normalized_name", ""), county), "")
                    existing = (row.get("county_equivalent") or "").strip()
                    if peer and peer != row.get("entity_id"):
                        conflicts.append({
                            "entity_id": row.get("entity_id"),
                            "market_name": row.get("farm_name", ""),
                            "existing_county": existing,
                            "market_county": county,
                            "colliding_entity_id": peer,
                            "recommended_action": "route_to_human_identity_qa",
                        })
                        continue
                    if existing and normalized_county(existing) != county:
                        conflicts.append({
                            "entity_id": row.get("entity_id"),
                            "market_name": row.get("farm_name", ""),
                            "existing_county": existing,
                            "market_county": county,
                            "recommended_action": "route_to_human_qa",
                        })
                        continue
                    source_url = next(
                        (value.strip() for value in (row.get("source_urls") or "").split("|") if value.strip()),
                        CENSUS_PLACE_COUNTY_URL,
                    )
                    append_proposal(
                        proposals,
                        state,
                        row,
                        county,
                        county_fips,
                        source_url,
                        MARKET_PRECISION,
                        remaining_blockers(row.get("promotion_blockers", ""), clear_service_area=True),
                        proposed_city=market_city,
                        proposed_classification=MARKET_CLASSIFICATION,
                        decision_basis=(
                            f"The documented market record names {market_city or county} as the market "
                            f"location; the Census place reference places that market location in {county}. "
                            "The producer is represented as a market-circuit service area, not at an exact "
                            "farm or market coordinate."
                        ),
                    )
                    continue

            unresolved.append({
                "entity_id": row.get("entity_id"),
                "reason": "city missing; no unambiguous address or documented market location",
            })
            continue
        match = reference.get(normalized_name(city))
        if match is None:
            unresolved.append({
                "entity_id": row.get("entity_id"),
                "reason": f"no unambiguous Census place for {city!r}; multi-county or unlisted",
            })
            continue
        _, county, county_fips = match
        peer = occupied.get((row.get("normalized_name", ""), county), "")
        if peer and peer != row.get("entity_id"):
            # Resolving the county would collide with a same-name entity from
            # another source — a duplicate-identity signal, not a geography fix.
            conflicts.append({
                "entity_id": row.get("entity_id"),
                "city": city,
                "existing_county": "",
                "census_county": county,
                "colliding_entity_id": peer,
                "recommended_action": "route_to_human_identity_qa",
            })
            continue
        existing = (row.get("county_equivalent") or "").strip()
        if existing and normalized_county(existing) != county:
            conflicts.append({
                "entity_id": row.get("entity_id"),
                "city": city,
                "existing_county": existing,
                "census_county": county,
                "recommended_action": "route_to_human_qa",
            })
            continue
        append_proposal(
            proposals,
            state,
            row,
            county,
            county_fips,
            CENSUS_PLACE_COUNTY_URL,
            ADDRESS_PRECISION,
            remaining_blockers(row.get("promotion_blockers", "")),
            proposed_city=city,
            decision_basis=(
                f"The Census national place-by-county reference places {city} wholly "
                f"within {county} ({county_fips}); the county geography blocker is "
                "resolved without changing operation evidence."
            ),
        )
    return {
        "schema_version": 1,
        "state": state,
        "review_only": True,
        "contract_files_modified": [],
        "geography_targets": targets,
        "resolved": len(proposals),
        "conflicts": len(conflicts),
        "unresolved": len(unresolved),
        "resolution_rate": round(len(proposals) / targets, 4) if targets else 0.0,
        "proposals": proposals,
        "conflict_items": conflicts,
        "unresolved_items": unresolved,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes": [
            "A proposal is not a verification or promotion; blockers other than geography remain.",
            "Status changes are proposed only when observation evidence alone passes the eligibility gate.",
            "Ambiguous places and county conflicts are never auto-resolved.",
        ],
    }


def read_entities(state: str) -> list[dict[str, str]]:
    path = STATE_ROOT / state / "entities.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state code")
    parser.add_argument("--output", type=Path, help="Bundle path; defaults under data/source-releases/work/<STATE>/")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="Privacy-safe geocode cache path")
    return parser.parse_args()


def main(fetcher: Callable[[str], tuple[str, dict[str, Any]]] = fetch) -> int:
    args = parse_args()
    state = args.state.upper()
    body, _ = fetcher(CENSUS_PLACE_COUNTY_URL)
    reference = place_reference(state, body)
    cache = read_cache(args.cache)
    bundle = resolve_state(state, read_entities(state), reference, fetcher=fetcher, cache=cache)
    write_cache(args.cache, cache)
    output = (args.output or DEFAULT_OUTPUT_ROOT / state / "geography-resolution.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {key: bundle[key] for key in (
        "state", "geography_targets", "resolved", "conflicts", "unresolved", "resolution_rate")}
    summary["output"] = str(output)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
