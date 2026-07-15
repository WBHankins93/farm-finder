#!/usr/bin/env python3
"""Validate every committed FarmFinder state against contract version 1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from state_release_urls import is_valid_website


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
LOCAL_RELEASE_ROOT = ROOT / "data" / "source-releases" / "state-expansions"
CANONICAL_MANIFEST = ROOT / "03-app" / "site" / "config" / "source-of-truth.json"

REQUIRED_ARTIFACT_ROLES = {
    "observations", "raw_source_records", "request_log", "qa_queue",
    "identity_review", "exclusions", "geography_errors",
}
ALLOWED_COVERAGE_STATUSES = {
    "candidates_found", "searched_none_found", "source_blocked", "follow_up_required",
}
ALLOWED_RELEASE_STATUSES = {
    "researching", "collected", "coverage_reviewed", "record_verified", "approved", "promoted",
}
ELIGIBLE_REQUIRED_FIELDS = [
    "entity_id", "farm_name", "entity_type", "identity_decision", "state",
    "county", "city", "products", "public_location_classification",
    "contact_visibility", "source_urls", "last_retrieved",
]
MANUAL_REQUIRED_FIELDS = {
    "review_id", "farm_name", "normalized_name", "decision", "evidence_grade",
    "source_url", "retrieved_date", "decision_basis",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("states", nargs="*", help="Two-letter states; defaults to every state directory")
    parser.add_argument("--require-local-artifacts", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_fingerprint(manifest: dict[str, Any]) -> str:
    """Fingerprint the immutable repository inputs and private evidence identities."""
    payload = {
        "contractVersion": manifest.get("contractVersion"),
        "state": manifest.get("state"),
        "releaseId": manifest.get("releaseId"),
        "repositoryFiles": manifest.get("repositoryFiles", {}),
        "artifacts": [
            {
                "role": row.get("role"),
                "objectKey": row.get("objectKey"),
                "versionId": row.get("versionId"),
                "sha256": row.get("sha256"),
                "bytes": row.get("bytes"),
                "rows": row.get("rows"),
            }
            for row in sorted(manifest.get("artifacts", []), key=lambda item: str(item.get("role")))
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def compressed_row_count(path: Path) -> int:
    executable = shutil.which("zstd")
    if not executable:
        raise RuntimeError("zstd is required to validate local state artifacts")
    result = subprocess.run([executable, "-q", "-dc", str(path)], check=True, capture_output=True)
    if path.name.endswith(".csv.zst"):
        return sum(1 for _ in csv.DictReader(io.StringIO(result.stdout.decode("utf-8"))))
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def read_compressed_csv(path: Path) -> list[dict[str, str]]:
    executable = shutil.which("zstd")
    if not executable:
        raise RuntimeError("zstd is required to validate local state artifacts")
    result = subprocess.run([executable, "-q", "-dc", str(path)], check=True, capture_output=True)
    return list(csv.DictReader(io.StringIO(result.stdout.decode("utf-8"))))


def validate_state(state: str, require_local_artifacts: bool) -> dict[str, Any]:
    state_dir = STATE_ROOT / state
    errors: list[str] = []
    warnings: list[str] = []
    try:
        config = json.loads((state_dir / "state-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((state_dir / "release-manifest.json").read_text(encoding="utf-8"))
        sources = json.loads((state_dir / "sources.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {"state": state, "status": "failed", "errors": [str(exc)], "warnings": []}

    required_files = set(config.get("repositoryPolicy", {}).get("requiredFiles", []))
    actual_files = {path.name for path in state_dir.iterdir() if path.is_file() and not path.name.startswith(".")}
    require(config.get("contractVersion") == 1, "state config contractVersion must be 1", errors)
    require(manifest.get("contractVersion") == 1, "release manifest contractVersion must be 1", errors)
    require(sources.get("contractVersion") == 1, "source catalog contractVersion must be 1", errors)
    require(config.get("state", {}).get("code") == state, "state-config code mismatch", errors)
    require(manifest.get("state") == state, "release-manifest state mismatch", errors)
    require(sources.get("state") == state, "sources state mismatch", errors)
    require(actual_files == required_files,
            f"state directory must contain exactly {sorted(required_files)}; found {sorted(actual_files)}", errors)
    total_bytes = sum(path.stat().st_size for path in state_dir.iterdir() if path.is_file())
    require(total_bytes <= int(config["repositoryPolicy"]["maxTrackedBytes"]),
            "state directory exceeds tracked-byte budget", errors)

    for filename, metadata in manifest.get("repositoryFiles", {}).items():
        path = state_dir / filename
        require(filename in required_files - {"release-manifest.json"},
                f"manifest references non-contract repository file {filename}", errors)
        if path.is_file():
            require(path.stat().st_size == metadata.get("bytes"), f"{filename} byte count changed", errors)
            require(sha256_file(path) == metadata.get("sha256"), f"{filename} checksum changed", errors)
    require(set(manifest.get("repositoryFiles", {})) == required_files - {"release-manifest.json"},
            "manifest repository-file set is incomplete", errors)

    entities = read_csv(state_dir / "entities.csv")
    coverage = read_csv(state_dir / "county-coverage.csv")
    manual = read_csv(state_dir / "manual-decisions.csv")
    counts = manifest.get("counts", {})
    eligible = [row for row in entities if row.get("promotion_status") == "promotion_eligible_reviewed"]
    qa = [row for row in entities if row.get("promotion_status") == "research_or_qa_queue"]
    require(len(entities) == counts.get("proposedEntities"), "entity count does not reconcile", errors)
    require(len(eligible) == counts.get("promotionEligibleEntities"), "eligible count does not reconcile", errors)
    require(len(qa) == counts.get("researchOrQaEntities"), "QA entity count does not reconcile", errors)
    require(len(entities) == len({row.get("entity_id") for row in entities}), "duplicate entity ID", errors)
    require(len(entities) == len({(row.get("normalized_name"), row.get("county")) for row in entities}),
            "duplicate normalized-name/county key", errors)
    require(all(row.get("state") == state for row in entities), "entity has wrong state", errors)
    require(all(row.get("entity_id", "").startswith(state + "-") for row in entities),
            "entity ID has wrong state prefix", errors)
    for row in eligible:
        missing = [field for field in ELIGIBLE_REQUIRED_FIELDS if not row.get(field)]
        require(not missing, f"eligible {row.get('entity_id')} missing {', '.join(missing)}", errors)
        grades = set(row.get("evidence_grades", "").split("; "))
        require("F" not in grades and grades != {"E"},
                f"eligible {row.get('entity_id')} has insufficient evidence", errors)
        require(not row.get("promotion_blockers"), f"eligible {row.get('entity_id')} has blockers", errors)

    expected_counties = int(config["state"]["countyCount"])
    require(len(coverage) == expected_counties == counts.get("countyCoverageRows"),
            "county denominator does not reconcile", errors)
    require(len({row.get("county") for row in coverage}) == expected_counties,
            "county coverage names are not unique", errors)
    require(all(row.get("status") in ALLOWED_COVERAGE_STATUSES for row in coverage),
            "county coverage has an invalid status", errors)
    require(sum(int(row.get("candidate_entities", 0)) for row in coverage) ==
            sum(bool(row.get("county")) for row in entities), "county candidate totals do not reconcile", errors)
    require(sum(bool(int(row.get("candidate_entities", 0))) for row in coverage) ==
            counts.get("countiesWithCandidates"), "counties-with-candidates count changed", errors)
    require(sum(bool(int(row.get("promotion_eligible_entities", 0))) for row in coverage) ==
            counts.get("countiesWithEligibleEntities"), "eligible-county count changed", errors)

    require(len(manual) == counts.get("manualDecisions"), "manual-decision count does not reconcile", errors)
    require(len(manual) == len({row.get("review_id") for row in manual}), "duplicate manual review ID", errors)
    for row in manual:
        missing = sorted(field for field in MANUAL_REQUIRED_FIELDS if not row.get(field))
        require(not missing, f"manual decision {row.get('review_id')} missing {', '.join(missing)}", errors)
        require(row.get("decision") in {"corroborate", "exclude", "merge", "correct"},
                f"manual decision {row.get('review_id')} has invalid action", errors)
    entity_keys = {row.get("normalized_name") for row in entities}
    eligible_keys = {row.get("normalized_name") for row in eligible}
    excluded_keys = {row.get("normalized_name") for row in manual if row.get("decision") == "exclude"}
    corroborated_keys = {row.get("normalized_name") for row in manual if row.get("decision") == "corroborate"}
    require(not (entity_keys & excluded_keys), "manually excluded entity remains staged", errors)
    require(corroborated_keys <= eligible_keys, "manual corroboration did not clear its entity", errors)

    datasets = sources.get("datasets", [])
    require(len(datasets) == config["collection"]["expectedPrimaryDatasets"] == counts.get("sourceDatasets"),
            "primary source-dataset count does not reconcile", errors)
    require({row.get("pass") for row in datasets} == set(config["collection"]["requiredPasses"]),
            "source catalog does not cover every required pass", errors)
    require(len(datasets) == len({row.get("sourceId") for row in datasets}), "duplicate source ID", errors)
    require(all(row.get("decision") and (row.get("sourceUrl") or row.get("repositoryPath")) for row in datasets),
            "source catalog entry lacks decision or location", errors)

    artifacts = manifest.get("artifacts", [])
    by_role = {row.get("role"): row for row in artifacts}
    require(set(by_role) == REQUIRED_ARTIFACT_ROLES, "artifact role set is incomplete or duplicated", errors)
    storage = manifest.get("evidenceStorage", {})
    release_status = str(manifest.get("status", ""))
    promotion_ready = manifest.get("promotionReady") is True
    require(release_status in ALLOWED_RELEASE_STATUSES, "release manifest has invalid lifecycle status", errors)
    require(storage.get("provider") == "s3-compatible", "evidence provider must be S3-compatible", errors)
    require(storage.get("versioningRequired") is True, "evidence storage must require versioning", errors)
    if release_status in {"researching", "collected", "coverage_reviewed"}:
        require(not promotion_ready, f"{release_status} release must not be promotion-ready", errors)
    if release_status in {"record_verified", "approved", "promoted"}:
        require(not qa, f"{release_status} release still has QA entities", errors)
    if release_status == "record_verified":
        require(not promotion_ready, "record-verified release requires explicit approval", errors)
    if release_status in {"approved", "promoted"}:
        require(promotion_ready, f"{release_status} release must be promotion-ready", errors)
        require(storage.get("environment") not in {None, "", "local-staging"},
                f"{release_status} release evidence is not in managed storage", errors)
        require(storage.get("managedCopyRequiredBeforePromotion") is False,
                f"{release_status} release still requires a managed evidence copy", errors)
        approval = manifest.get("approval", {})
        require(approval.get("decision") == "approved", "release lacks an approval decision", errors)
        require(bool(approval.get("approvedBy")), "release lacks an approver", errors)
        require(bool(approval.get("approvedAt")), "release lacks an approval timestamp", errors)
        require(approval.get("releaseFingerprint") == release_fingerprint(manifest),
                "approval fingerprint does not match the immutable release", errors)
    elif storage.get("environment") == "local-staging":
        require(storage.get("managedCopyRequiredBeforePromotion") is True,
                "local staging must retain the managed-copy promotion guard", errors)
    prefix = storage.get("prefix", "")
    for role, artifact in by_role.items():
        require(artifact.get("objectKey", "").startswith(prefix), f"{role} object key is outside release prefix", errors)
        require(bool(artifact.get("versionId")), f"{role} lacks immutable object version", errors)
        require(len(str(artifact.get("sha256", ""))) == 64, f"{role} lacks SHA-256", errors)
        require(int(artifact.get("bytes", 0)) > 0, f"{role} has no stored bytes", errors)
        require(int(artifact.get("rows", -1)) >= 0, f"{role} has invalid row count", errors)
    if by_role:
        require(by_role["observations"].get("rows") == counts.get("sourceObservations"),
                "observation artifact count does not reconcile", errors)
        require(by_role["qa_queue"].get("rows") == counts.get("researchOrQaEntities"),
                "QA artifact count does not reconcile", errors)
        require(by_role["identity_review"].get("rows") == counts.get("identityReviewGroups"),
                "identity artifact count does not reconcile", errors)
        require(by_role["exclusions"].get("rows") == counts.get("excludedObservations"),
                "exclusion artifact count does not reconcile", errors)
        require(sum(int(row.get("source_observation_count", 0)) for row in entities) +
                int(by_role["exclusions"].get("rows", 0)) == counts.get("sourceObservations"),
                "entity observation totals plus exclusions do not reconcile", errors)

    local_dir = LOCAL_RELEASE_ROOT / state / str(manifest.get("releaseId"))
    local_observations: list[dict[str, str]] | None = None
    for role, artifact in by_role.items():
        path = local_dir / str(artifact.get("filename"))
        if not path.is_file():
            message = f"local evidence artifact is unavailable: {path.relative_to(ROOT)}"
            if require_local_artifacts:
                errors.append(message)
            else:
                warnings.append(message)
            continue
        require(path.stat().st_size == artifact.get("bytes"), f"local {role} byte count changed", errors)
        require(sha256_file(path) == artifact.get("sha256"), f"local {role} checksum changed", errors)
        try:
            require(compressed_row_count(path) == artifact.get("rows"), f"local {role} row count changed", errors)
            if role == "observations":
                local_observations = read_compressed_csv(path)
        except RuntimeError as exc:
            errors.append(str(exc))

    if local_observations is not None:
        observation_ids = [row.get("observation_id") for row in local_observations]
        require(len(observation_ids) == len(set(observation_ids)), "duplicate observation ID", errors)
        require(all(row.get("state") == state for row in local_observations),
                "observation has wrong state", errors)
        require(all(row.get("farm_name") and row.get("source_name") and row.get("source_url") and
                    row.get("retrieved_date") for row in local_observations),
                "observation lacks name, source, URL, or retrieval date", errors)
    for row in entities:
        if row.get("website_url"):
            require(is_valid_website(row["website_url"]),
                    f"entity {row.get('entity_id')} has a map, social, shared asset, or malformed website", errors)

    canonical = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))["release"]
    boundary = manifest.get("canonicalBoundary", {})
    require(canonical.get("allowedStates") == boundary.get("allowedStates"),
            "state manifest does not match canonical allowed states", errors)
    require(canonical.get("sourceRowCount") == boundary.get("sourceRowCount"),
            "state manifest does not match canonical row count", errors)
    if release_status != "promoted":
        require(state not in canonical.get("allowedStates", []),
                "unpromoted state is already inside the canonical boundary", errors)
    else:
        require(state in canonical.get("allowedStates", []),
                "promoted state is absent from the canonical boundary", errors)

    return {
        "state": state,
        "status": "passed" if not errors else "failed",
        "releaseId": manifest.get("releaseId"),
        "releaseStatus": release_status,
        "promotionReady": promotion_ready,
        "releaseFingerprint": release_fingerprint(manifest),
        "entities": len(entities),
        "eligible": len(eligible),
        "qa": len(qa),
        "counties": len(coverage),
        "trackedBytes": total_bytes,
        "artifactBytes": sum(int(row.get("bytes", 0)) for row in artifacts),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    states = [value.upper() for value in args.states] or sorted(
        path.name for path in STATE_ROOT.iterdir() if path.is_dir() and len(path.name) == 2
    )
    results = [validate_state(state, args.require_local_artifacts) for state in states]
    status = "passed" if all(row["status"] == "passed" for row in results) else "failed"
    print(json.dumps({"status": status, "contractVersion": 1, "states": results}, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
