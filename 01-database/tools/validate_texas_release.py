#!/usr/bin/env python3
"""Validate the private Texas coverage-reviewed staging release."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research" / "tx-expansion"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    summary = json.loads((DATA / "collection-summary.json").read_text(encoding="utf-8"))
    raw = json.loads((DATA / "raw-source-records.json").read_text(encoding="utf-8"))
    observations = read_csv("texas-source-observations.csv")
    entities = read_csv("texas-candidate-entities.csv")
    coverage = read_csv("county-coverage.csv")
    qa = read_csv("qa-queue.csv")
    excluded = read_csv("excluded-observations.csv")
    identity = read_csv("identity-review.csv")
    conflicts = read_csv("geography-conflicts.csv")
    lookup_errors = json.loads((DATA / "county-lookup-errors.json").read_text(encoding="utf-8"))
    source_log = json.loads((DATA / "source-pass-log.json").read_text(encoding="utf-8"))

    eligible = [row for row in entities if row["promotion_status"] == "promotion_eligible_reviewed"]
    require(summary.get("status") == "coverage_reviewed", "summary status is not coverage_reviewed", errors)
    require(summary.get("collection_passes_completed") == [1, 2, 3], "three collection passes are not complete", errors)
    require(len(observations) == summary.get("source_observations"), "observation count does not reconcile", errors)
    require(len(entities) == summary.get("proposed_entities"), "entity count does not reconcile", errors)
    require(len(eligible) == summary.get("promotion_eligible_entities"), "eligible count does not reconcile", errors)
    require(len(qa) == summary.get("open_qa_items"), "QA count does not reconcile", errors)
    require(len(excluded) == summary.get("excluded_or_grade_f_observations"), "exclusion count does not reconcile", errors)
    require(len(identity) == summary.get("identity_review_groups"), "identity-review count does not reconcile", errors)
    require(len(conflicts) == summary.get("source_county_conflicts"), "geography-conflict count does not reconcile", errors)
    require(len(lookup_errors) == summary.get("unresolved_county_observations"), "unresolved county count does not reconcile", errors)
    require(sum(int(row["source_observation_count"]) for row in entities) + len(excluded) == len(observations),
            "entity observation counts plus standalone exclusions do not reconcile", errors)

    observation_ids = [row["observation_id"] for row in observations]
    entity_ids = [row["entity_id"] for row in entities]
    require(len(observation_ids) == len(set(observation_ids)), "duplicate observation IDs", errors)
    require(len(entity_ids) == len(set(entity_ids)), "duplicate entity IDs", errors)
    require(len(entities) == len({(row["normalized_name"], row["county"]) for row in entities}),
            "duplicate normalized-name/county entity keys", errors)
    require(all(row["state"] == "TX" for row in observations), "non-TX observation state value", errors)
    require(all(row["source_url"] and row["retrieved_date"] and row["farm_name"] for row in observations),
            "observation missing source URL, retrieval date, or name", errors)
    require(not any(any(ord(char) < 32 or ord(char) == 127 for char in row["farm_name"]) for row in observations),
            "farm name contains a control character", errors)
    rejected_website_hosts = ("facebook.com", "instagram.com", "twitter.com", "x.com", "pinterest.com",
                              "mapquest.com", "google.com", "goo.gl", "g.page", "csaware.com",
                              "imapbuilder.com", "gstatic.com", "googleapis.com")
    for row in observations:
        if row["website_url"]:
            parsed = urlparse(row["website_url"])
            host = (parsed.hostname or "").casefold()
            require(parsed.scheme in {"http", "https"} and bool(host) and "." in host and not parsed.username,
                    f"observation {row['observation_id']} has malformed website URL", errors)
            blocked_host = (any(host == domain or host.endswith("." + domain) for domain in rejected_website_hosts)
                            or host.startswith("lh-images."))
            require(not blocked_host,
                    f"observation {row['observation_id']} has a map/social/shared-asset URL in website field", errors)

    required = ["entity_id", "farm_name", "entity_type", "identity_decision", "state", "county", "city",
                "products", "public_location_classification", "contact_visibility", "source_urls", "last_retrieved"]
    for row in eligible:
        missing = [field for field in required if not row.get(field)]
        require(not missing, f"eligible {row['entity_id']} missing: {', '.join(missing)}", errors)
        require(row["state"] == "TX", f"eligible {row['entity_id']} has wrong state", errors)
        require(row["entity_type"] == "farm", f"eligible {row['entity_id']} still requires entity-type review", errors)
        require(not row["city"].casefold().endswith((", tx", ", texas")),
                f"eligible {row['entity_id']} city redundantly contains state", errors)
        grades = set(row["evidence_grades"].split("; "))
        require("F" not in grades, f"eligible {row['entity_id']} contains grade F evidence", errors)
        require(grades != {"E"}, f"eligible {row['entity_id']} relies only on grade E", errors)
        require(not row["promotion_blockers"], f"eligible {row['entity_id']} has blockers", errors)

    counties = [row["county"] for row in coverage]
    county_set = set(counties)
    require(len(coverage) == 254 and len(county_set) == 254, "county coverage is not exactly 254 unique counties", errors)
    require(all(row["status"] in {"candidates_found", "searched_none_found"} for row in coverage), "invalid county status", errors)
    require(sum(int(row["candidate_entities"]) for row in coverage) == sum(bool(row["county"]) for row in entities),
            "county entity counts do not reconcile", errors)
    require(all(not row["county"] or row["county"] in county_set for row in entities), "entity contains an invalid county", errors)
    require(all(row["county"] in county_set for row in eligible), "eligible entity county is invalid", errors)

    primary_logs = [row for row in source_log if row.get("source_decision") not in {"request_component", "county_enrichment"}]
    component_logs = [row for row in source_log if row.get("source_decision") == "request_component"]
    geocoder_logs = [row for row in source_log if row.get("source_decision") == "county_enrichment"]
    require(len(primary_logs) == summary.get("source_datasets_evaluated") == 28,
            "expected 28 evaluated primary/channel/reference datasets", errors)
    require({int(row["pass"]) for row in primary_logs} == {1, 2, 3}, "source log does not cover all three passes", errors)
    require(not [row for row in primary_logs if row.get("error")], "one or more primary source datasets failed", errors)
    require(not [row for row in component_logs if row.get("error")], "one or more component source requests failed", errors)
    require(len([row for row in source_log if row.get("source_name") == "LocalHarvest — county-seat search request"]) == 254,
            "LocalHarvest does not have exactly 254 county-seat search requests", errors)
    require(len([row for row in source_log if row.get("source_name") == "LocalHarvest — farm profile request"]) == 302,
            "LocalHarvest profile-request count is not 302", errors)
    require(len([row for row in source_log if row.get("source_name") == "Texas Center for Local Food — profile request"]) == 254,
            "Texas Center for Local Food profile-request count is not 254", errors)
    require(len([row for row in source_log if row.get("source_name") == "Shop Texas Farms — profile request"]) == 56,
            "Shop Texas Farms profile-request count is not 56", errors)
    require(len([row for row in source_log if row.get("source_name") == "Shop Texas Farms — directory page request"]) == 3,
            "Shop Texas Farms directory-page count is not three", errors)
    require(len([row for row in primary_logs if row.get("source_name", "").startswith("PickYourOwn —")]) == 14,
            "PickYourOwn index plus 13-region log is incomplete", errors)
    require(len(geocoder_logs) == summary.get("geography_enrichment_requests"), "geocoder request count does not reconcile", errors)
    require(sum(bool(row.get("error")) for row in geocoder_logs) == summary.get("geography_enrichment_request_failures"),
            "geocoder failure count does not reconcile", errors)
    require(summary.get("failed_source_requests") == 0, "one or more collection source requests failed", errors)

    actual_source_counts = Counter(row["source_name"] for row in observations)
    require(dict(sorted(actual_source_counts.items())) == summary.get("source_observations_by_source"),
            "per-source observation counts do not reconcile", errors)
    require(actual_source_counts["Texas Department of Agriculture — GO TEXAN Farm And Ranch"] == 100,
            "GO TEXAN observation count changed", errors)
    require(actual_source_counts["Texas Center for Local Food — Farms & Ranches"] == 254,
            "Texas Center for Local Food observation count changed", errors)
    require(actual_source_counts["LocalHarvest — Texas county-seat gap search"] == 302,
            "LocalHarvest observation count changed", errors)
    require(len(raw.get("texas_local_food_profiles", [])) == 254 and not raw.get("texas_local_food_profile_failures"),
            "Texas Center for Local Food raw profile evidence is incomplete", errors)
    require(len(raw.get("shop_texas_farms_profiles", [])) == 56 and not raw.get("shop_texas_farms_failures"),
            "Shop Texas Farms raw profile evidence is incomplete", errors)
    require(len(raw.get("localharvest_profiles", [])) == 302 and not raw.get("localharvest_profile_failures")
            and not raw.get("localharvest_county_seat_search_failures"), "LocalHarvest raw evidence is incomplete", errors)

    manifest = json.loads((ROOT / "03-app/site/config/source-of-truth.json").read_text(encoding="utf-8"))
    release = manifest.get("release", {})
    require(release.get("allowedStates") == ["LA", "MS"], "Texas staging unexpectedly changed canonical allowed states", errors)
    require(release.get("sourceRowCount") == 311, "canonical manifest row count changed during Texas staging", errors)
    public_farms = json.loads((ROOT / "03-app/site/app/data/farms.json").read_text(encoding="utf-8"))
    require(len(public_farms) == 311, "public LA/MS farm count changed during Texas staging", errors)

    result = {
        "status": "passed" if not errors else "failed", "release_id": summary.get("release_id"),
        "observations": len(observations), "entities": len(entities), "eligible": len(eligible),
        "qa_items": len(qa), "excluded": len(excluded), "counties": len(coverage),
        "primary_datasets": len(primary_logs), "component_requests": len(component_logs),
        "geocoder_requests": len(geocoder_logs), "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
