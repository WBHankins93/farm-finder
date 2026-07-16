#!/usr/bin/env python3
"""Apply the national 2026 operating-evidence hierarchy to staged entities."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RANK = {
    "unresolved_2026": 0,
    "reported_closed_requires_review": 1,
    "likely_operating_2026": 2,
    "currently_listed_official_2026": 3,
    "confirmed_operating_2026": 4,
}


def split_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(" | ") if item.strip()]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--state", required=True); args = parser.parse_args()
    state = args.state.upper()
    work = ROOT / "data" / "source-releases" / "work" / state
    with (work / "entities.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    policy = json.loads((ROOT / "01-database" / "operation-evidence-policy.json").read_text())
    source_rules = policy["sourceRules"]
    audits = json.loads((work / "operation-web-audit.json").read_text())
    audit_by_entity = {entity_id: row for audit in audits for entity_id in audit["entityIds"] for row in [audit]}
    aliases = {
        row["possible_alias_entity_id"] for row in csv.DictReader((work / "canonical-reconciliation.csv").open())
        if row.get("possible_alias_entity_id")
    }
    counts: dict[str, int] = {}
    for row in rows:
        status = "unresolved_2026"; basis = "No current operating evidence located"; evidence_url = ""; evidence_date = "2026-07-15"
        source_urls = split_values(row["source_urls"])
        for source in split_values(row["source_names"]):
            rule = source_rules.get(source)
            if rule and RANK[rule["status"]] > RANK[status]:
                status, basis, evidence_url = rule["status"], rule["basis"], (source_urls[0] if source_urls else "")
        audit = audit_by_entity.get(row["entity_id"])
        if audit and audit.get("reachable") and RANK[status] < RANK["likely_operating_2026"]:
            status = "likely_operating_2026"
            basis = "Farm-owned website was reachable during the July 2026 evidence audit; reachability alone is not proof of current sales"
            evidence_url = audit["finalUrl"] or audit["requestedUrl"]
        if "source reports closure" in row["promotion_blockers"] and RANK[status] < RANK["likely_operating_2026"]:
            status = "reported_closed_requires_review"
            basis = "Discovery source explicitly reports closure; no affirmative curator decision or contradictory current evidence yet"
            evidence_url = source_urls[0] if source_urls else evidence_url
        scope = "in_scope_primary_producer" if row["entity_type"] == "farm" else "farm_scope_review_required"
        identity = "identity_review_required" if row["entity_id"] in aliases or "multiple counties" in row["promotion_blockers"] else "distinct_under_current_rules"
        countable = scope == "in_scope_primary_producer" and identity == "distinct_under_current_rules"
        row.update({
            "operation_status_2026": status,
            "operation_evidence_basis": basis,
            "operation_evidence_url": evidence_url,
            "operation_evidence_date": evidence_date,
            "farm_scope_status": scope,
            "operation_identity_status": identity,
            "countable_operation_2026": "True" if countable and status in {"confirmed_operating_2026", "currently_listed_official_2026", "likely_operating_2026"} else "False",
        })
        counts[status] = counts.get(status, 0) + 1
    write_csv(work / "entities.csv", rows)
    supported = sum(row["countable_operation_2026"] == "True" and row["operation_status_2026"] in {"confirmed_operating_2026", "currently_listed_official_2026"} for row in rows)
    likely = sum(row["countable_operation_2026"] == "True" and row["operation_status_2026"] == "likely_operating_2026" for row in rows)
    summary_path = work / "summary.json"; summary = json.loads(summary_path.read_text())
    summary.update({
        "operation_status_counts": counts,
        "supported_operating_entities_2026": supported,
        "additional_likely_operating_entities_2026": likely,
        "operation_count_upper_supported_range": supported + likely,
        "operation_scope_review_entities": sum(row["farm_scope_status"] != "in_scope_primary_producer" for row in rows),
        "operation_identity_review_entities": sum(row["operation_identity_status"] != "distinct_under_current_rules" for row in rows),
    })
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    report_path = work / "completion-report.md"
    report = report_path.read_text()
    report += f"""

## 2026 operating-evidence audit

The immutable collected-name universe contains **{len(rows):,} retained candidate entities**. Evidence supports
**{supported:,} distinct, in-scope operations** through an explicit 2026 program or current official producer
listing. Another **{likely:,}** have weaker current evidence such as a reachable farm-owned website or a
recently expired grower certification. The evidence-bounded operating range is therefore **{supported:,}–{supported + likely:,}**.

This is a public-evidence directory count, not the USDA statistical count of every agricultural operation.
Missing evidence never proves closure, and every collected name remains preserved for follow-up.
"""
    report_path.write_text(report)
    print(json.dumps({"state": state, "retainedCandidates": len(rows), "statusCounts": counts, "supportedOperating": supported, "additionalLikely": likely, "supportedRangeUpper": supported + likely}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
