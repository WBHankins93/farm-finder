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
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from collect_southeast import CENSUS_PLACE_COUNTY_URL, fetch, normalized_county, normalized_name
from geocode_eligible import STATE_FIPS
from qa_triage import route
from state_policy import sufficient_promotion_evidence


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "source-releases" / "work"
QA_STATUS = "research_or_qa_queue"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
GEO_CLAUSE = re.compile(r"county requires geography review|county missing", re.I)
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


def remaining_blockers(blockers: str) -> str:
    clauses = [clause.strip() for clause in (blockers or "").split(";") if clause.strip()]
    return "; ".join(clause for clause in clauses if not GEO_CLAUSE.search(clause))


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


def resolve_state(
    state: str,
    entities: list[dict[str, str]],
    reference: dict[str, tuple[str, str, str]],
) -> dict[str, Any]:
    state = state.upper()
    today = datetime.now(timezone.utc).date().isoformat()
    proposals: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    targets = 0
    for row in entities:
        if row.get("promotion_status") != QA_STATUS:
            continue
        if route(row.get("promotion_blockers", ""))[0] != "geography":
            continue
        targets += 1
        city = (row.get("city") or "").strip()
        if not city:
            unresolved.append({"entity_id": row.get("entity_id"), "reason": "city missing; needs research"})
            continue
        match = reference.get(normalized_name(city))
        if match is None:
            unresolved.append({
                "entity_id": row.get("entity_id"),
                "reason": f"no unambiguous Census place for {city!r}; multi-county or unlisted",
            })
            continue
        _, county, county_fips = match
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
        new_blockers = remaining_blockers(row.get("promotion_blockers", ""))
        status = proposed_status(row, new_blockers, county)
        review_id = "georeview_" + hashlib.sha256(
            f"{state}|{row.get('entity_id')}|{county_fips}".encode("utf-8")
        ).hexdigest()[:20]
        proposals.append({
            "entity_patch": {
                "entity_id": row.get("entity_id"),
                "base_county_equivalent": existing,
                "proposed_county_equivalent": county,
                "base_promotion_blockers": row.get("promotion_blockers", ""),
                "proposed_promotion_blockers": new_blockers,
                "base_promotion_status": QA_STATUS,
                "proposed_promotion_status": status,
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
                "city": city,
                "postal_code": row.get("postal_code", ""),
                "products": row.get("products", ""),
                "business_types": row.get("business_types", ""),
                "website_url": row.get("website_url", ""),
                "source_url": CENSUS_PLACE_COUNTY_URL,
                "retrieved_date": today,
                "decision_basis": (
                    f"The Census national place-by-county reference places {city} wholly "
                    f"within {county} ({county_fips}); the county geography blocker is "
                    "resolved without changing operation evidence."
                ),
                "notes": "Draft only; a curator must apply this decision with its paired entity patch.",
                "target_normalized_name": "",
                "exclusion_reason": "",
                "supersedes_review_id": "",
            },
        })
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
    return parser.parse_args()


def main(fetcher: Callable[[str], tuple[str, dict[str, Any]]] = fetch) -> int:
    args = parse_args()
    state = args.state.upper()
    body, _ = fetcher(CENSUS_PLACE_COUNTY_URL)
    reference = place_reference(state, body)
    bundle = resolve_state(state, read_entities(state), reference)
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
