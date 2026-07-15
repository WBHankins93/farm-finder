#!/usr/bin/env python3
"""Produce one human review surface from the seven-file state contract."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from validate_state_releases import (
    CANONICAL_MANIFEST,
    STATE_ROOT,
    release_fingerprint,
    validate_state,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("states", nargs="+", help="Two-letter state codes")
    parser.add_argument("--require-local-artifacts", action="store_true")
    parser.add_argument("--require-promotable", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def gate(name: str, passed: bool, detail: str, blocking: bool = True) -> dict[str, Any]:
    return {
        "gate": name,
        "status": "passed" if passed else "blocked",
        "blocking": blocking,
        "detail": detail,
    }


def state_status(state: str, require_local_artifacts: bool = False) -> dict[str, Any]:
    state = state.upper()
    state_dir = STATE_ROOT / state
    validation = validate_state(state, require_local_artifacts)
    manifest = json.loads((state_dir / "release-manifest.json").read_text(encoding="utf-8"))
    entities = read_csv(state_dir / "entities.csv")
    coverage = read_csv(state_dir / "county-coverage.csv")
    qa = [row for row in entities if row.get("promotion_status") == "research_or_qa_queue"]
    unresolved_counties = [
        row["county"] for row in coverage
        if row.get("status") in {"source_blocked", "follow_up_required"}
    ]
    storage = manifest.get("evidenceStorage", {})
    fingerprint = release_fingerprint(manifest)
    approval = manifest.get("approval", {})
    canonical = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))["release"]
    release_status = str(manifest.get("status", ""))

    checks = [
        gate(
            "contract",
            validation["status"] == "passed",
            "seven files, schemas, counts, hashes, URLs, and evidence reconcile"
            if validation["status"] == "passed" else "; ".join(validation["errors"]),
        ),
        gate(
            "coverage",
            not unresolved_counties,
            "all counties have a final searched status" if not unresolved_counties
            else f"{len(unresolved_counties)} counties remain blocked or need follow-up",
        ),
        gate(
            "record_verification",
            not qa,
            "no candidate remains in QA" if not qa else f"{len(qa)} entities remain in QA",
        ),
        gate(
            "managed_evidence",
            storage.get("environment") not in {None, "", "local-staging"}
            and storage.get("managedCopyRequiredBeforePromotion") is False,
            "immutable evidence is in managed versioned storage"
            if storage.get("environment") not in {None, "", "local-staging"}
            and storage.get("managedCopyRequiredBeforePromotion") is False
            else "immutable evidence still requires a managed-storage copy",
        ),
        gate(
            "approval",
            approval.get("decision") == "approved"
            and approval.get("releaseFingerprint") == fingerprint
            and bool(approval.get("approvedBy"))
            and bool(approval.get("approvedAt")),
            "approval is recorded against the current release fingerprint"
            if approval.get("decision") == "approved" and approval.get("releaseFingerprint") == fingerprint
            else "no valid approval is recorded for the current release fingerprint",
        ),
        gate(
            "canonical_promotion",
            release_status == "promoted" and state in canonical.get("allowedStates", []),
            "state is present in the canonical release"
            if release_status == "promoted" and state in canonical.get("allowedStates", [])
            else "state remains isolated from the canonical release",
            blocking=False,
        ),
    ]
    promotable = all(row["status"] == "passed" for row in checks[:5])
    return {
        "state": state,
        "releaseId": manifest.get("releaseId"),
        "lifecycleStatus": release_status,
        "promotionReady": manifest.get("promotionReady") is True,
        "promotable": promotable,
        "releaseFingerprint": fingerprint,
        "counts": {
            "entities": len(entities),
            "eligible": len(entities) - len(qa),
            "qa": len(qa),
            "counties": len(coverage),
            "unresolvedCounties": len(unresolved_counties),
        },
        "humanReviewSurface": str((state_dir / "completion-report.md").relative_to(STATE_ROOT.parent.parent)),
        "machineInputs": sorted(path.name for path in state_dir.iterdir() if path.is_file()),
        "gates": checks,
    }


def main() -> int:
    args = parse_args()
    results = [state_status(state, args.require_local_artifacts) for state in args.states]
    structural_ok = all(result["gates"][0]["status"] == "passed" for result in results)
    promotable = all(result["promotable"] for result in results)
    print(json.dumps({
        "status": "passed" if structural_ok else "failed",
        "requirePromotable": args.require_promotable,
        "states": results,
    }, indent=2))
    return 0 if structural_ok and (promotable or not args.require_promotable) else 1


if __name__ == "__main__":
    raise SystemExit(main())
