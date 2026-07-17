#!/usr/bin/env python3
"""Assemble review-only corroboration proposals for a state release.

The assistant has two deliberately conservative passes:

* website liveness fetches an eligible or QA entity's farm-owned site three
  times and reuses :func:`audit_operation_evidence.dated_active_excerpt`;
* cross-directory matching compares the normalized entity view against other
  already-collected source identities in the same state.

The output is a proposed-evidence bundle.  It never writes a state contract,
never excludes a candidate, and never changes promotion status.  A human
curator must apply any accepted observation and append-only decision to the
state release together.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlparse

from audit_operation_evidence import dated_active_excerpt, fetch
from state_release_urls import is_valid_website


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "source-releases" / "work"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
QA_STATUS = "research_or_qa_queue"
CORROBORATION_GRADE = "C"
REQUIRED_FETCH_ATTEMPTS = 3
QA_BLOCKER = "single grade-E discovery listing needs corroboration"

# These hosts are source directories or profile platforms, not farm-owned
# sites.  Hosts found in the state's source plan are added at runtime too.
KNOWN_DIRECTORY_HOSTS = {
    "arkansasgrown.org",
    "arfarmtoschool.org",
    "eatwild.com",
    "farmandfoodsystem.uada.edu",
    "hipcamp.com",
    "localharvest.org",
    "pickyourown.org",
    "yelp.com",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state code")
    parser.add_argument(
        "--entities",
        type=Path,
        help="Read-only normalized entity CSV; defaults to the state's entities.csv",
    )
    parser.add_argument(
        "--blocker",
        action="append",
        help="Restrict targets to rows containing this exact blocker; may repeat",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Proposal JSON path; defaults to data/source-releases/work/<STATE>/corroboration-assistant.json",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            if None in row:
                raise ValueError(f"{path}: row {reader.line_num} has more values than the header")
            rows.append({key: value or "" for key, value in row.items()})
        return rows


def split_values(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(" | ") if item.strip()]


def split_evidence_grades(value: str) -> list[str]:
    """Read both legacy pipe-delimited and current semicolon-delimited grades."""

    return [item.strip() for item in re.split(r"\s*(?:\||;)\s*", str(value or "")) if item.strip()]


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[1:] if len(digits) == 11 and digits.startswith("1") else digits


def normalize_email(value: str) -> str:
    return str(value or "").strip().casefold()


def parse_year_date(value: str) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else text


def host(value: str) -> str:
    try:
        return (urlparse(value).hostname or "").casefold()
    except ValueError:
        return ""


def host_matches(value: str, domains: Iterable[str]) -> bool:
    current = host(value)
    return bool(current) and any(current == domain or current.endswith("." + domain) for domain in domains)


def source_plan_hosts(state_document: Mapping[str, Any]) -> set[str]:
    hosts = set(KNOWN_DIRECTORY_HOSTS)
    for source in state_document.get("collection", {}).get("sources", []):
        source_host = host(str(source.get("sourceUrl") or ""))
        if source_host:
            hosts.add(source_host)
    return hosts


def is_farm_owned_website(url: str, directory_hosts: set[str]) -> tuple[bool, str]:
    if not is_valid_website(url):
        return False, "invalid or shared website URL"
    try:
        parsed_host = urlparse(url).hostname or ""
    except ValueError:
        return False, "invalid or shared website URL"
    if "%" in parsed_host:
        return False, "invalid or shared website URL"
    if host_matches(url, directory_hosts):
        return False, "directory or profile-platform host"
    return True, ""


def stable_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:20]}"


def fetch_attempts(
    url: str,
    attempts: int = REQUIRED_FETCH_ATTEMPTS,
    fetcher: Callable[[str], dict[str, Any]] = fetch,
) -> list[dict[str, Any]]:
    if attempts != REQUIRED_FETCH_ATTEMPTS:
        raise ValueError(f"the corroboration contract requires exactly {REQUIRED_FETCH_ATTEMPTS} fetch attempts")
    return [fetcher(url) for _ in range(attempts)]


def liveness_result(
    entity: Mapping[str, str],
    state: str,
    directory_hosts: set[str],
    fetcher: Callable[[str], dict[str, Any]] = fetch,
) -> dict[str, Any]:
    url = entity.get("website_url", "").strip()
    owned, skip_reason = is_farm_owned_website(url, directory_hosts)
    result: dict[str, Any] = {
        "entity_id": entity.get("entity_id", ""),
        "farm_name": entity.get("farm_name", ""),
        "website_url": url,
        "eligible_for_fetch": owned,
        "skip_reason": skip_reason,
        "attempts": [],
        "response_sha256": [],
        "reachable_attempts": 0,
        "active_signal_attempts": 0,
        "proposal": None,
    }
    if not owned:
        return result

    attempts = fetch_attempts(url, fetcher=fetcher)
    result["attempts"] = attempts
    result["response_sha256"] = [item.get("responseSha256", "") for item in attempts if item.get("responseSha256")]
    result["reachable_attempts"] = sum(bool(item.get("reachable")) for item in attempts)
    active = [item for item in attempts if item.get("currentYearActiveSignal") and item.get("activeEvidenceExcerpt")]
    result["active_signal_attempts"] = len(active)
    if not active:
        return result

    best = active[0]
    retrieved_date = parse_year_date(best.get("retrievedAt", "")) or datetime.now(timezone.utc).date().isoformat()
    observation_id = stable_id("coroobs", state, "website_liveness", entity.get("entity_id", ""), url)
    observation = make_observation(
        entity,
        observation_id=observation_id,
        source_name="FarmFinder automated corroboration — website liveness",
        source_url=best.get("finalUrl") or url,
        retrieved_date=retrieved_date,
        evidence_grade=CORROBORATION_GRADE,
        method="website_liveness",
        details={
            "dated_active_year": best.get("currentYearActiveSignal", ""),
            "dated_active_excerpt": best.get("activeEvidenceExcerpt", ""),
            "response_sha256": result["response_sha256"],
            "fetch_attempts": len(attempts),
            "reachable_attempts": result["reachable_attempts"],
        },
    )
    result["proposal"] = proposal_bundle(
        entity,
        observation,
        decision_basis=(
            "A farm-owned website returned current-year activity language near "
            "sales, season, ordering, harvest, visiting, or availability terms; "
            "three hashed fetch attempts are retained for curator review."
        ),
    )
    return result


def make_observation(
    entity: Mapping[str, str],
    *,
    observation_id: str,
    source_name: str,
    source_url: str,
    retrieved_date: str,
    evidence_grade: str,
    method: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "entity_id": entity.get("entity_id", ""),
        "state": entity.get("state", ""),
        "farm_name": entity.get("farm_name", ""),
        "normalized_name": entity.get("normalized_name", ""),
        "source_name": source_name,
        "source_url": source_url,
        "retrieved_date": retrieved_date,
        "evidence_grade": evidence_grade,
        "method": method,
        "proposal_status": "proposed_for_human_review",
        **dict(details),
    }


def entity_patch(entity: Mapping[str, str], observation: Mapping[str, Any]) -> dict[str, Any]:
    old_grades = split_evidence_grades(entity.get("evidence_grades", ""))
    new_grades = sorted(set(old_grades + [str(observation["evidence_grade"])]), key="ABCDEF".index)
    old_ids = split_values(entity.get("source_observation_ids", ""))
    old_sources = split_values(entity.get("source_names", ""))
    old_urls = split_values(entity.get("source_urls", ""))
    return {
        "entity_id": entity.get("entity_id", ""),
        "operation": "append_observation_and_refresh_grades",
        "base_source_observation_count": int(entity.get("source_observation_count", "0") or 0),
        "proposed_source_observation_count": int(entity.get("source_observation_count", "0") or 0) + 1,
        "base_source_observation_ids": old_ids,
        "proposed_source_observation_ids": old_ids + [observation["observation_id"]],
        "base_source_names": old_sources,
        "proposed_source_names": old_sources + [observation["source_name"]],
        "base_source_urls": old_urls,
        "proposed_source_urls": old_urls + [observation["source_url"]],
        "base_evidence_grades": old_grades,
        "proposed_evidence_grades": new_grades,
        "base_promotion_status": entity.get("promotion_status", ""),
        "proposed_promotion_status": entity.get("promotion_status", ""),
        "human_review_required": True,
    }


def decision_row(
    entity: Mapping[str, str],
    observation: Mapping[str, Any],
    decision_basis: str,
    *,
    peer_entity_id: str = "",
) -> dict[str, Any]:
    return {
        "review_id": stable_id("cororeview", observation["observation_id"]),
        "entity_id": entity.get("entity_id", ""),
        "observation_id": observation["observation_id"],
        "peer_entity_id": peer_entity_id,
        "farm_name": entity.get("farm_name", ""),
        "normalized_name": entity.get("normalized_name", ""),
        "decision": "corroborate",
        "evidence_grade": observation.get("evidence_grade", CORROBORATION_GRADE),
        "verified_entity_type": entity.get("entity_type", "farm"),
        "county_equivalent": entity.get("county_equivalent", ""),
        "city": entity.get("city", ""),
        "postal_code": entity.get("postal_code", ""),
        "products": entity.get("products", ""),
        "business_types": entity.get("business_types", ""),
        "website_url": entity.get("website_url", ""),
        "source_url": observation.get("source_url", ""),
        "retrieved_date": observation.get("retrieved_date", ""),
        "decision_basis": decision_basis,
        "notes": "Draft only; human curator must review and append this decision with its paired entity observation.",
        "target_normalized_name": "",
        "exclusion_reason": "",
        "supersedes_review_id": "",
    }


def proposal_bundle(entity: Mapping[str, str], observation: dict[str, Any], decision_basis: str, *, peer_entity_id: str = "") -> dict[str, Any]:
    return {
        "observation": observation,
        "decision": decision_row(entity, observation, decision_basis, peer_entity_id=peer_entity_id),
        "entity_patch": entity_patch(entity, observation),
    }


def name_similarity(left: str, right: str) -> float:
    left_text = normalize_name(left)
    right_text = normalize_name(right)
    if not left_text or not right_text:
        return 0.0
    if left_text == right_text:
        return 1.0
    left_tokens, right_tokens = set(left_text.split()), set(right_text.split())
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return max(overlap, SequenceMatcher(None, left_text, right_text).ratio())


def contact_matches(left: Mapping[str, str], right: Mapping[str, str]) -> list[str]:
    matches: list[str] = []
    left_phone, right_phone = normalize_phone(left.get("phone_internal", "")), normalize_phone(right.get("phone_internal", ""))
    if left_phone and right_phone and left_phone == right_phone:
        matches.append("phone_internal")
    left_email, right_email = normalize_email(left.get("email_internal", "")), normalize_email(right.get("email_internal", ""))
    if left_email and right_email and left_email == right_email:
        matches.append("email_internal")
    return matches


def geography_comparison(left: Mapping[str, str], right: Mapping[str, str]) -> dict[str, Any]:
    fields = ("county_equivalent", "city", "postal_code")
    conflicts = [
        {"field": field, "left": left.get(field, ""), "right": right.get(field, "")}
        for field in fields
        if left.get(field, "").strip() and right.get(field, "").strip()
        and normalize_text(left.get(field, "")) != normalize_text(right.get(field, ""))
    ]
    matches = [
        field for field in fields
        if left.get(field, "").strip() and right.get(field, "").strip()
        and normalize_text(left.get(field, "")) == normalize_text(right.get(field, ""))
    ]
    return {"consistent": bool(matches) and not conflicts, "matching_fields": matches, "conflicts": conflicts}


def source_url_for_peer(peer: Mapping[str, str], target_sources: set[str]) -> tuple[str, str]:
    names = split_values(peer.get("source_names", ""))
    urls = split_values(peer.get("source_urls", ""))
    for name, url in zip(names, urls):
        if name not in target_sources and url:
            return name, url
    for name in names:
        if name not in target_sources:
            return name, urls[0] if urls else ""
    return "", urls[0] if urls else ""


def cross_directory_candidates(target: Mapping[str, str], peers: Iterable[Mapping[str, str]]) -> list[dict[str, Any]]:
    target_sources = set(split_values(target.get("source_names", "")))
    candidates: list[dict[str, Any]] = []
    for peer in peers:
        if peer.get("entity_id") == target.get("entity_id"):
            continue
        peer_sources = set(split_values(peer.get("source_names", "")))
        independent_source = peer_sources - target_sources
        if not independent_source:
            continue
        contacts = contact_matches(target, peer)
        similarity = name_similarity(target.get("farm_name", ""), peer.get("farm_name", ""))
        if not contacts or similarity < 0.45:
            continue
        geography = geography_comparison(target, peer)
        source_name, source_url = source_url_for_peer(peer, target_sources)
        candidates.append({
            "peer": peer,
            "independent_source": source_name or sorted(independent_source)[0],
            "source_url": source_url,
            "contact_matches": contacts,
            "name_similarity": round(similarity, 3),
            "geography": geography,
            "machine_corroborable": bool(geography["consistent"] and source_url),
        })
    return sorted(candidates, key=lambda item: (-item["machine_corroborable"], -item["name_similarity"], item["peer"].get("entity_id", "")))


def cross_directory_result(entity: Mapping[str, str], peers: Iterable[Mapping[str, str]], state: str) -> dict[str, Any]:
    candidates = cross_directory_candidates(entity, peers)
    proposals: list[dict[str, Any]] = []
    qa_items: list[dict[str, Any]] = []
    for candidate in candidates:
        peer = candidate["peer"]
        geography = candidate["geography"]
        if candidate["machine_corroborable"]:
            observation_id = stable_id(
                "coroobs", state, "cross_directory", entity.get("entity_id", ""), peer.get("entity_id", ""), candidate["independent_source"]
            )
            observation = make_observation(
                entity,
                observation_id=observation_id,
                source_name=f"FarmFinder automated corroboration — {candidate['independent_source']}",
                source_url=candidate["source_url"],
                retrieved_date=peer.get("last_retrieved", "") or datetime.now(timezone.utc).date().isoformat(),
                evidence_grade=CORROBORATION_GRADE,
                method="cross_directory_match",
                details={
                    "peer_entity_id": peer.get("entity_id", ""),
                    "peer_farm_name": peer.get("farm_name", ""),
                    "independent_source": candidate["independent_source"],
                    "matched_contact_fields": candidate["contact_matches"],
                    "matched_geography_fields": geography["matching_fields"],
                    "name_similarity": candidate["name_similarity"],
                    "peer_evidence_grades": peer.get("evidence_grades", ""),
                },
            )
            proposals.append(proposal_bundle(
                entity,
                observation,
                decision_basis=(
                    f"The candidate matches an independently collected {candidate['independent_source']} "
                    f"record by {', '.join(candidate['contact_matches'])} and "
                    f"{', '.join(geography['matching_fields'])}; the name similarity is "
                    f"{candidate['name_similarity']:.3f}."
                ),
                peer_entity_id=peer.get("entity_id", ""),
            ))
        elif geography["conflicts"]:
            qa_items.append({
                "entity_id": entity.get("entity_id", ""),
                "farm_name": entity.get("farm_name", ""),
                "peer_entity_id": peer.get("entity_id", ""),
                "peer_farm_name": peer.get("farm_name", ""),
                "independent_source": candidate["independent_source"],
                "contact_matches": candidate["contact_matches"],
                "name_similarity": candidate["name_similarity"],
                "conflict_fields": geography["conflicts"],
                "recommended_action": "route_to_human_qa",
                "blocker": "cross-directory geography conflict; no corroborate decision drafted",
            })
    return {"candidates": candidates, "proposals": proposals, "qa_items": qa_items}


def target_rows(rows: Iterable[Mapping[str, str]], blockers: list[str] | None = None) -> list[dict[str, str]]:
    allowed_blockers = set(blockers or [])
    selected = []
    for row in rows:
        if row.get("promotion_status") not in {ELIGIBLE_STATUS, QA_STATUS}:
            continue
        # A source can emit duplicate observations.  The enrichment plan's
        # single-source gate is about distinct independent sources, not the
        # raw observation count.
        if len(set(split_values(row.get("source_names", "")))) != 1:
            continue
        if allowed_blockers and row.get("promotion_blockers", "") not in allowed_blockers:
            continue
        selected.append(dict(row))
    return sorted(
        selected,
        key=lambda row: (0 if row.get("promotion_status") == QA_STATUS else 1, row.get("entity_id", "")),
    )


def run_assistant(
    state: str,
    entities: list[dict[str, str]],
    state_document: Mapping[str, Any],
    *,
    blockers: list[str] | None = None,
    fetcher: Callable[[str], dict[str, Any]] = fetch,
) -> dict[str, Any]:
    state = state.upper()
    targets = target_rows(entities, blockers)
    directory_hosts = source_plan_hosts(state_document)
    liveness: list[dict[str, Any]] = []
    cross_directory: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    qa_items: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for entity in targets:
        live = liveness_result(entity, state, directory_hosts, fetcher=fetcher)
        liveness.append(live)
        if live["proposal"]:
            proposals.append({"pass": "website_liveness", **live["proposal"]})
        cross = cross_directory_result(entity, entities, state)
        cross_directory.append({
            "entity_id": entity.get("entity_id", ""),
            "farm_name": entity.get("farm_name", ""),
            **cross,
        })
        for item in cross["qa_items"]:
            pair = tuple(sorted((item["entity_id"], item["peer_entity_id"])))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                qa_items.append(item)
        for item in cross["proposals"]:
            pair = tuple(sorted((item["observation"]["entity_id"], item["decision"]["peer_entity_id"])))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            proposals.append({"pass": "cross_directory_match", **item})

    liveness_fetchable = sum(item["eligible_for_fetch"] for item in liveness)
    liveness_hits = sum(bool(item["proposal"]) for item in liveness)
    cross_hits = sum(item.get("pass") == "cross_directory_match" for item in proposals)
    unique_hit_entities = {
        item["observation"].get("entity_id")
        for item in proposals
        if item.get("observation", {}).get("entity_id")
    }
    return {
        "schema_version": 1,
        "state": state,
        "source_of_truth": "read-only normalized entities.csv plus state.yaml source plan",
        "review_only": True,
        "contract_files_modified": [],
        "selection": {
            "rows_considered": len(targets),
            "single_source_statuses": [ELIGIBLE_STATUS, QA_STATUS],
            "blocker_filter": blockers or [],
        },
        "hit_rate": {
            "denominator": len(targets),
            "website_liveness_fetchable": liveness_fetchable,
            "website_liveness_hits": liveness_hits,
            "website_liveness_rate_over_denominator": round(liveness_hits / len(targets), 4) if targets else 0.0,
            "website_liveness_rate_over_fetchable": round(liveness_hits / liveness_fetchable, 4) if liveness_fetchable else 0.0,
            "cross_directory_hits": cross_hits,
            "cross_directory_rate_over_denominator": round(cross_hits / len(targets), 4) if targets else 0.0,
            "unique_entities_with_any_hit": len(unique_hit_entities),
            "combined_unique_hit_rate": round(len(unique_hit_entities) / len(targets), 4) if targets else 0.0,
        },
        "proposed_observations": [item["observation"] for item in proposals],
        "draft_decisions": [item["decision"] for item in proposals],
        "entity_patches": [item["entity_patch"] for item in proposals],
        "qa_review_items": qa_items,
        "website_liveness": liveness,
        "cross_directory": cross_directory,
        "notes": [
            "A proposal is not a verification, approval, canonical promotion, or exclusion.",
            "Every draft corroborate decision is paired with an append-observation entity patch.",
            "Conflicting geography is named in qa_review_items and never receives a corroborate decision.",
        ],
    }


def main() -> int:
    args = parse_args()
    state = args.state.upper()
    entities_path = (args.entities or STATE_ROOT / state / "entities.csv").resolve()
    state_path = STATE_ROOT / state / "state.yaml"
    entities = read_csv(entities_path)
    state_document = json.loads(state_path.read_text(encoding="utf-8"))
    result = run_assistant(state, entities, state_document, blockers=args.blocker)
    output = (args.output or DEFAULT_OUTPUT_ROOT / state / "corroboration-assistant.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {"state": state, "output": str(output), **result["selection"], **result["hit_rate"], "qa_review_items": len(result["qa_review_items"]), "proposals": len(result["proposed_observations"])}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
