#!/usr/bin/env python3
"""Export eligible state records and state-scoped QA queues.

The source contract remains the four committed state files. These exports are
derived handoff artifacts: eligible records can move to the next pipeline stage
without treating unresolved candidates as verified or deleting them from QA.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from state_release_status import STATE_ROOT
from validate_state_releases import release_fingerprint, validate_state


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "data" / "exports" / "state-pipeline"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
QA_STATUS = "research_or_qa_queue"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("states", nargs="*", help="Two-letter state codes; defaults to every state directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-local-artifacts", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> dict[str, Any]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size, "rows": len(rows)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def states_to_export(states: list[str]) -> list[str]:
    if states:
        return sorted({state.upper() for state in states})
    return sorted(path.name for path in STATE_ROOT.iterdir() if path.is_dir() and (path / "state.yaml").is_file())


def export_state(state: str, output_dir: Path, require_local_artifacts: bool = False) -> dict[str, Any]:
    state_dir = STATE_ROOT / state
    validation = validate_state(state, require_local_artifacts)
    if validation["status"] != "passed":
        raise RuntimeError(f"{state} contract validation failed: {'; '.join(validation['errors'])}")

    document = json.loads((state_dir / "state.yaml").read_text(encoding="utf-8"))
    release = document["release"]
    coverage = document.get("collection", {}).get("coverage", {})
    unresolved = coverage.get("unresolvedCountyEquivalents", [])
    if unresolved:
        raise RuntimeError(f"{state} has unresolved county coverage: {', '.join(unresolved)}")

    entities = read_csv(state_dir / "entities.csv")
    eligible = [row for row in entities if row.get("promotion_status") == ELIGIBLE_STATUS]
    qa = [row for row in entities if row.get("promotion_status") == QA_STATUS]
    if not eligible:
        raise RuntimeError(f"{state} has no eligible records to hand off")

    state_output = output_dir / state
    eligible_meta = write_csv(state_output / "eligible-entities.csv", eligible)
    qa_meta = write_csv(state_output / "qa-queue.csv", qa)
    handoff = {
        "state": state,
        "releaseId": release["id"],
        "releaseFingerprint": release_fingerprint(document),
        "status": "eligible_staged",
        "sourceLifecycleStatus": release["status"],
        "eligibleCount": len(eligible),
        "qaCount": len(qa),
        "qaPolicy": "deferred_state_scoped_review",
        "canonicalPromotion": "blocked_until_record_verified_and_approved",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "files": {
            "eligibleEntities": {"filename": "eligible-entities.csv", **eligible_meta},
            "qaQueue": {"filename": "qa-queue.csv", **qa_meta},
        },
    }
    state_output.joinpath("handoff.json").write_text(
        json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return handoff


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    handoffs = [export_state(state, output_dir, args.require_local_artifacts) for state in states_to_export(args.states)]

    eligible_rows: list[dict[str, str]] = []
    qa_rows: list[dict[str, str]] = []
    for handoff in handoffs:
        state = handoff["state"]
        state_output = output_dir / state
        eligible_rows.extend({"state": state, **row} for row in read_csv(state_output / "eligible-entities.csv"))
        qa_rows.extend({"state": state, **row} for row in read_csv(state_output / "qa-queue.csv"))
    consolidated = {
        "status": "eligible_staged",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "states": [handoff["state"] for handoff in handoffs],
        "eligibleCount": len(eligible_rows),
        "qaCount": len(qa_rows),
        "qaPolicy": "deferred_state_scoped_review",
        "files": {
            "eligibleEntities": write_csv(output_dir / "eligible-entities.csv", eligible_rows),
            "qaQueue": write_csv(output_dir / "qa-queue.csv", qa_rows),
        },
        "stateHandoffs": handoffs,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(consolidated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(consolidated, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
