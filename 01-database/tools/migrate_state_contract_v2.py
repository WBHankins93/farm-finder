#!/usr/bin/env python3
"""Consolidate a version-1 state directory into the four-file contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from state_policy import AFFIRMATIVE_EXCLUSION_REASONS, RESEARCH_STATUS


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
OLD_FILES = {
    "state-config.json", "sources.json", "manual-decisions.csv",
    "county-coverage.csv", "completion-report.md", "release-manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def exclusion_reason(row: dict[str, str]) -> str:
    text = " ".join((row.get("decision_basis", ""), row.get("notes", ""))).casefold()
    if re.search(r"out of|outside|relocat|moved|wrong state|new mexico|oklahoma|new york|south carolina", text):
        return "outside_jurisdiction"
    if re.search(r"duplicate|same operation|alias", text):
        return "duplicate_identity"
    if re.search(r"closed|ceased|no longer operating", text):
        return "confirmed_closed"
    return "confirmed_nonfarm"


def migrate(state: str) -> dict[str, Any]:
    state = state.upper()
    state_dir = STATE_ROOT / state
    config = json.loads((state_dir / "state-config.json").read_text(encoding="utf-8"))
    sources = json.loads((state_dir / "sources.json").read_text(encoding="utf-8"))
    manifest = json.loads((state_dir / "release-manifest.json").read_text(encoding="utf-8"))
    coverage = read_csv(state_dir / "county-coverage.csv")
    entities = read_csv(state_dir / "entities.csv")
    decisions = read_csv(state_dir / "manual-decisions.csv")

    entity_fields = list(entities[0]) if entities else []
    if "county" in entity_fields:
        entity_fields[entity_fields.index("county")] = "county_equivalent"
    for row in entities:
        row["county_equivalent"] = row.pop("county", "")
    write_csv(state_dir / "entities.csv", entities, entity_fields)

    decision_fields = list(decisions[0]) if decisions else [
        "review_id", "farm_name", "normalized_name", "decision", "evidence_grade",
        "verified_entity_type", "county", "city", "postal_code", "products",
        "business_types", "website_url", "source_url", "retrieved_date",
        "decision_basis", "notes",
    ]
    if "county" in decision_fields:
        decision_fields[decision_fields.index("county")] = "county_equivalent"
    for field in ("exclusion_reason", "supersedes_review_id"):
        if field not in decision_fields:
            decision_fields.append(field)
    for row in decisions:
        row["county_equivalent"] = row.pop("county", "")
        row["exclusion_reason"] = exclusion_reason(row) if row.get("decision") == "exclude" else ""
        row["supersedes_review_id"] = row.get("supersedes_review_id", "")
    write_csv(state_dir / "decisions.csv", decisions, decision_fields)

    report_path = state_dir / "report.md"
    report_path.write_text((state_dir / "completion-report.md").read_text(encoding="utf-8"), encoding="utf-8")
    counts = dict(manifest.get("counts", {}))
    counts["excludedEntityGroups"] = sum(row.get("decision") == "exclude" for row in decisions)
    role_map = {
        "observations": "observations",
        "raw_source_records": "source_records",
        "request_log": "collection_log",
    }
    artifacts = []
    for artifact in manifest.get("artifacts", []):
        if artifact.get("role") in role_map:
            artifacts.append({**artifact, "role": role_map[str(artifact["role"])]})
    unresolved = [
        row.get("county", "") for row in coverage
        if row.get("status") in {"source_blocked", "follow_up_required"}
    ]
    document = {
        "contractVersion": 2,
        "state": {
            "code": state,
            "name": config["state"]["name"],
            "countyEquivalentLabel": config["state"].get("countyLabel", "county"),
            "countyEquivalentCount": config["state"]["countyCount"],
        },
        "policy": {
            "version": "2026-07-15",
            "missingDataDisposition": RESEARCH_STATUS,
            "affirmativeExclusionReasons": sorted(AFFIRMATIVE_EXCLUSION_REASONS),
        },
        "collection": {
            "requiredPasses": config["collection"]["requiredPasses"],
            "sources": sources.get("datasets", []),
            "coverage": {
                "countyEquivalentsReviewed": len(coverage),
                "countyEquivalentsWithCandidates": counts.get("countiesWithCandidates", 0),
                "countyEquivalentsWithEligibleEntities": counts.get("countiesWithEligibleEntities", 0),
                "unresolvedCountyEquivalents": unresolved,
            },
        },
        "repositoryPolicy": {
            "requiredFiles": ["state.yaml", "entities.csv", "decisions.csv", "report.md"],
            "maxTrackedBytes": config.get("repositoryPolicy", {}).get("maxTrackedBytes", 5_000_000),
        },
        "release": {
            "id": manifest.get("releaseId"),
            "status": manifest.get("status"),
            "generatedAt": manifest.get("generatedAt"),
            "promotionReady": manifest.get("promotionReady", False),
            "promotionBlockReason": manifest.get("promotionBlockReason"),
            "counts": counts,
            "repositoryFiles": {
                name: {"sha256": sha256_file(state_dir / name), "bytes": (state_dir / name).stat().st_size}
                for name in ("entities.csv", "decisions.csv", "report.md")
            },
            "evidenceStorage": manifest.get("evidenceStorage", {}),
            "artifacts": artifacts,
            "canonicalBoundary": manifest.get("canonicalBoundary", {}),
            "approval": manifest.get("approval", {}),
        },
    }
    (state_dir / "state.yaml").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for name in OLD_FILES:
        (state_dir / name).unlink()
    return {
        "state": state,
        "entities": len(entities),
        "decisions": len(decisions),
        "exclusions": counts["excludedEntityGroups"],
        "files": sorted(path.name for path in state_dir.iterdir() if path.is_file()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("states", nargs="+", help="Two-letter state codes")
    args = parser.parse_args()
    print(json.dumps([migrate(state) for state in args.states], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
