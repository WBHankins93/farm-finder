#!/usr/bin/env python3
"""Validate the private Alabama coverage-reviewed state release."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research" / "al-expansion"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    summary = json.loads((DATA / "collection-summary.json").read_text(encoding="utf-8"))
    observations = read_csv("alabama-source-observations.csv")
    entities = read_csv("alabama-candidate-entities.csv")
    coverage = read_csv("county-coverage.csv")
    qa = read_csv("qa-queue.csv")
    excluded = read_csv("excluded-observations.csv")
    source_log = json.loads((DATA / "source-pass-log.json").read_text(encoding="utf-8"))

    eligible = [row for row in entities if row["promotion_status"] == "promotion_eligible_reviewed"]
    require(summary.get("status") == "coverage_reviewed", "summary status is not coverage_reviewed", errors)
    require(summary.get("collection_passes_completed") == [1, 2, 3], "three collection passes are not complete", errors)
    require(len(observations) == summary.get("source_observations"), "observation count does not reconcile", errors)
    require(len(entities) == summary.get("proposed_entities"), "entity count does not reconcile", errors)
    require(len(eligible) == summary.get("promotion_eligible_entities"), "eligible count does not reconcile", errors)
    require(len(qa) == summary.get("open_qa_items"), "QA count does not reconcile", errors)
    require(len(excluded) == summary.get("excluded_or_grade_f_observations"), "exclusion count does not reconcile", errors)
    require(sum(int(row["source_observation_count"]) for row in entities) + len(excluded) == len(observations),
            "entity observation counts plus standalone exclusions do not reconcile", errors)

    observation_ids = [row["observation_id"] for row in observations]
    entity_ids = [row["entity_id"] for row in entities]
    require(len(observation_ids) == len(set(observation_ids)), "duplicate observation IDs", errors)
    require(len(entity_ids) == len(set(entity_ids)), "duplicate entity IDs", errors)
    require(len(entities) == len({(row["normalized_name"], row["county"]) for row in entities}),
            "duplicate normalized-name/county entity keys", errors)
    require(all(row["state"] == "AL" for row in observations), "non-AL observation state value", errors)
    require(all(row["source_url"] and row["retrieved_date"] and row["farm_name"] for row in observations),
            "observation missing source URL, retrieval date, or name", errors)

    required = ["entity_id", "farm_name", "entity_type", "identity_decision", "state", "county", "city",
                "products", "public_location_classification", "contact_visibility", "source_urls", "last_retrieved"]
    for row in eligible:
        missing = [field for field in required if not row.get(field)]
        require(not missing, f"eligible {row['entity_id']} missing: {', '.join(missing)}", errors)
        require(row["state"] == "AL", f"eligible {row['entity_id']} has wrong state", errors)
        grades = set(row["evidence_grades"].split("; "))
        require("F" not in grades, f"eligible {row['entity_id']} contains grade F evidence", errors)
        require(grades != {"E"}, f"eligible {row['entity_id']} relies only on grade E", errors)
        require(not row["promotion_blockers"], f"eligible {row['entity_id']} has blockers", errors)

    counties = [row["county"] for row in coverage]
    require(len(coverage) == 67 and len(set(counties)) == 67, "county coverage is not exactly 67 unique counties", errors)
    require(all(row["status"] in {"candidates_found", "searched_none_found", "source_blocked", "follow_up_required"} for row in coverage),
            "invalid county status", errors)
    require(all(int(row["candidate_entities"]) > 0 for row in coverage), "one or more counties have no candidate entity", errors)
    require(sum(int(row["candidate_entities"]) for row in coverage) == len(entities), "county entity counts do not reconcile", errors)

    primary_logs = [row for row in source_log if row.get("source_name") not in {"FCC Census Area API", "U.S. Census Geocoder"}]
    require(len(primary_logs) == 14, "expected 14 evaluated primary/channel datasets", errors)
    require({int(row["pass"]) for row in primary_logs} == {1, 2, 3}, "source log does not cover all three passes", errors)
    require(not [row for row in primary_logs if row.get("error")], "one or more primary source datasets failed", errors)
    require(all(row.get("source_decision") for row in primary_logs), "primary source decision missing", errors)

    actual_source_counts = Counter(row["source_name"] for row in observations)
    require(dict(sorted(actual_source_counts.items())) == summary.get("source_observations_by_source"),
            "per-source observation counts do not reconcile", errors)

    manifest = json.loads((ROOT / "03-app/site/config/source-of-truth.json").read_text(encoding="utf-8"))
    release = manifest.get("release", {})
    require(release.get("allowedStates") == ["LA", "MS"], "Alabama staging unexpectedly changed canonical allowed states", errors)
    require(release.get("sourceRowCount") == 311, "canonical manifest row count changed during Alabama staging", errors)

    result = {
        "status": "passed" if not errors else "failed",
        "release_id": summary.get("release_id"),
        "observations": len(observations), "entities": len(entities), "eligible": len(eligible),
        "qa_items": len(qa), "excluded": len(excluded), "counties": len(coverage),
        "primary_datasets": len(primary_logs), "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
