#!/usr/bin/env python3
"""Package one state release without committing detailed evidence to Git.

The script migrates legacy collector output or packages the standardized local work
directory, compresses immutable evidence, optionally uploads it to versioned
S3-compatible storage, and writes the four-file repository contract.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from state_policy import effective_decisions


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
LOCAL_RELEASE_ROOT = ROOT / "data" / "source-releases" / "state-expansions"
SITE_SCRIPTS = ROOT / "03-app" / "site" / "scripts"
BUCKET = "farmfinder-source-releases"

STATE_FILES = {
    "AL": {
        "legacy_dir": ROOT / "research" / "al-expansion",
        "observations": ["observations.csv", "alabama-source-observations.csv"],
        "entities": ["entities.csv", "alabama-candidate-entities.csv"],
        "summary": ["summary.json", "collection-summary.json"],
        "report": ["completion-report.md", "alabama-completion-report.md"],
    },
    "TX": {
        "legacy_dir": ROOT / "research" / "tx-expansion",
        "observations": ["observations.csv", "texas-source-observations.csv"],
        "entities": ["entities.csv", "texas-candidate-entities.csv"],
        "summary": ["summary.json", "collection-summary.json"],
        "report": ["completion-report.md", "texas-completion-report.md"],
    },
}

MANUAL_HEADER = [
    "review_id", "farm_name", "normalized_name", "decision", "evidence_grade",
    "verified_entity_type", "county", "city", "postal_code", "products",
    "business_types", "website_url", "source_url", "retrieved_date",
    "decision_basis", "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, help="Two-letter state code")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--upload", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_file(source_dir: Path, names: list[str], *, required: bool = True) -> Path | None:
    for name in names:
        path = source_dir / name
        if path.is_file():
            return path
    if required:
        raise FileNotFoundError(f"none of {names!r} exists under {source_dir}")
    return None


def find_across(directories: list[Path], names: list[str], *, required: bool = True) -> Path | None:
    for directory in directories:
        path = find_file(directory, names, required=False)
        if path:
            return path
    if required:
        raise FileNotFoundError(f"none of {names!r} exists under {[str(path) for path in directories]}")
    return None


def copy_file(source: Path, destination: Path) -> None:
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)


def csv_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def json_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected a JSON list in {path}")
    return value


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
    return len(rows)


def compress_zstd(source: Path, destination: Path) -> None:
    executable = shutil.which("zstd")
    if not executable:
        raise RuntimeError("zstd is required to package state-release evidence")
    subprocess.run(
        [executable, "-q", "-f", "-19", str(source), "-o", str(destination)],
        check=True,
    )


def source_catalog(state: str, logs: list[dict[str, Any]]) -> dict[str, Any]:
    if state == "AL":
        primary = [
            row for row in logs
            if row.get("source_name") not in {"FCC Census Area API", "U.S. Census Geocoder"}
        ]
    else:
        primary = [
            row for row in logs
            if row.get("source_decision") not in {"request_component", "county_enrichment"}
        ]
    datasets = []
    for row in primary:
        name = str(row.get("source_name", ""))
        source_url = str(row.get("url", ""))
        repository_path = None
        if name == "FarmFinder curator verification decisions":
            source_url = ""
            repository_path = "manual-decisions.csv"
        stable = f"{state}|{row.get('pass')}|{name}|{source_url}".encode()
        datasets.append({
            "sourceId": f"{state.lower()}src-{hashlib.sha256(stable).hexdigest()[:12]}",
            "name": name,
            "pass": int(row.get("pass", 0)),
            "sourceUrl": source_url or None,
            "repositoryPath": repository_path,
            "decision": row.get("source_decision"),
            "recordsParsed": int(row.get("records_parsed", 0)),
            "retrievedAt": row.get("retrieved_at"),
            "responseSha256": row.get("sha256") or None,
            "notes": row.get("note") or None,
        })
    datasets.sort(key=lambda row: (row["pass"], row["name"], row["sourceId"]))
    return {"contractVersion": 1, "state": state, "datasets": datasets}


def storage_helpers():
    sys.path.insert(0, str(SITE_SCRIPTS))
    from cutover_common import (  # type: ignore
        ensure_versioned_bucket,
        runtime_settings,
        storage_client,
        upload_immutable_release,
    )
    return ensure_versioned_bucket, runtime_settings, storage_client, upload_immutable_release


def normalized_entity_copy(source: Path, destination: Path) -> None:
    """Promote collector output to the national county-equivalent column name."""
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(handle and (rows[0].keys() if rows else []))
    if "county" in fields:
        fields[fields.index("county")] = "county_equivalent"
    for row in rows:
        row["county_equivalent"] = row.pop("county", row.get("county_equivalent", ""))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def package_v2(args: argparse.Namespace, state: str, state_dir: Path, source_dir: Path) -> int:
    """Package the deterministic version-2 four-file state release."""
    document = json.loads((state_dir / "state.yaml").read_text(encoding="utf-8"))
    observations = find_file(source_dir, ["observations.csv"])
    entities = find_file(source_dir, ["entities.csv"])
    summary_path = find_file(source_dir, ["summary.json"])
    coverage_path = find_file(source_dir, ["county-coverage.csv"])
    raw_path = find_file(source_dir, ["raw-source-records.json"])
    request_path = find_file(source_dir, ["request-log.json", "source-pass-log.json"])
    report_path = find_file(source_dir, ["completion-report.md", "report.md"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") not in {"coverage_reviewed", "record_verified"}:
        raise RuntimeError("only a coverage-reviewed or record-verified state may be packaged")

    normalized_entity_copy(entities, state_dir / "entities.csv")
    copy_file(report_path, state_dir / "report.md")
    decisions_path = state_dir / "decisions.csv"
    if not decisions_path.is_file():
        raise FileNotFoundError("decisions.csv must exist before packaging")
    coverage = read_csv_rows(coverage_path)
    requests = json_list(request_path)
    sources = source_catalog(state, requests)
    release_id = str(summary["release_id"])
    bundle_dir = LOCAL_RELEASE_ROOT / state / release_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix=f"farmfinder-{state.lower()}-") as temporary:
        temp = Path(temporary)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_jsonl = temp / "source-records.jsonl"
        raw_count = write_jsonl(raw_jsonl, [{"dataset": key, "records": raw[key]} for key in sorted(raw)])
        request_jsonl = temp / "collection-log.jsonl"
        request_count = write_jsonl(request_jsonl, requests)
        inputs = [
            ("observations", observations, "observations.csv.zst", csv_count(observations)),
            ("source_records", raw_jsonl, "source-records.jsonl.zst", raw_count),
            ("collection_log", request_jsonl, "collection-log.jsonl.zst", request_count),
        ]
        for role, source, filename, rows in inputs:
            destination = bundle_dir / filename
            compress_zstd(source, destination)
            checksum = sha256_file(destination)
            artifacts.append({
                "role": role,
                "filename": filename,
                "objectKey": f"state-expansions/{state}/{release_id}/{filename}",
                "sha256": checksum,
                "bytes": destination.stat().st_size,
                "rows": rows,
                "contentType": "application/zstd",
                "visibility": "private",
                "versionId": f"local:{checksum[:24]}",
            })

    storage_status = "local_bundle_only"
    bucket = BUCKET
    environment = "local-staging"
    managed_copy_required = True
    if args.upload:
        ensure_bucket, runtime_settings, storage_client, upload = storage_helpers()
        settings = runtime_settings()
        client = storage_client(settings)
        bucket = settings.source_release_bucket or BUCKET
        ensure_bucket(client, bucket, settings.object_storage_region)
        for artifact in artifacts:
            artifact["versionId"] = upload(
                client,
                bucket=bucket,
                object_key=artifact["objectKey"],
                path=bundle_dir / artifact["filename"],
                sha256=artifact["sha256"],
                content_type=artifact["contentType"],
            )
        storage_status = "versioned_managed_copy"
        environment = "managed"
        managed_copy_required = False

    decisions = read_csv_rows(decisions_path)
    excluded_groups = sum(row.get("decision") == "exclude" for row in effective_decisions(decisions))
    release = document.setdefault("release", {})
    counts = {
        "sourceObservations": int(summary["source_observations"]),
        "proposedEntities": int(summary["proposed_entities"]),
        "promotionEligibleEntities": int(summary["promotion_eligible_entities"]),
        "researchOrQaEntities": int(summary["research_or_qa_entities"]),
        "excludedObservations": int(summary["excluded_or_grade_f_observations"]),
        "excludedEntityGroups": excluded_groups,
        "identityReviewGroups": int(summary["identity_review_groups"]),
        "countyCoverageRows": len(coverage),
        "countiesWithCandidates": int(summary["counties_with_candidates"]),
        "countiesWithEligibleEntities": int(summary["counties_with_promotion_eligible_entities"]),
        "sourceDatasets": len(sources["datasets"]),
        "manualDecisions": len(decisions),
    }
    if "canonical_baseline_observations" in summary:
        counts.update({
            "canonicalBaselineObservations": int(summary["canonical_baseline_observations"]),
            "currentSourceObservations": int(summary["current_source_observations"]),
        })
    unresolved = [
        row.get("county", "") for row in coverage
        if row.get("status") in {"source_blocked", "follow_up_required"}
    ]
    document["collection"]["sources"] = sources["datasets"]
    document["collection"]["coverage"] = {
        "countyEquivalentsReviewed": len(coverage),
        "countyEquivalentsWithCandidates": counts["countiesWithCandidates"],
        "countyEquivalentsWithEligibleEntities": counts["countiesWithEligibleEntities"],
        "unresolvedCountyEquivalents": unresolved,
    }
    release.update({
        "id": release_id,
        "status": summary["status"],
        "generatedAt": summary.get("generated_at"),
        "promotionReady": False,
        "promotionBlockReason": "state approval and canonical promotion remain separate gates",
        "counts": counts,
        "evidenceStorage": {
            "provider": "s3-compatible",
            "environment": environment,
            "status": storage_status,
            "bucket": bucket,
            "prefix": f"state-expansions/{state}/{release_id}/",
            "versioningRequired": True,
            "managedCopyRequiredBeforePromotion": managed_copy_required,
        },
        "artifacts": artifacts,
        "approval": {},
    })
    canonical_rebuild = release.get("canonicalRebuild", {})
    if canonical_rebuild.get("enabled") is True:
        canonical_rebuild.update({
            "baselineStateRows": int(summary["canonical_baseline_observations"]),
            "rediscoveredRows": int(summary["canonical_rows_rediscovered"]),
            "possibleAliasRows": int(summary["canonical_rows_possible_alias"]),
            "baselineOnlyRows": int(summary["canonical_rows_baseline_only"]),
        })
        release["canonicalRebuild"] = canonical_rebuild
    release["repositoryFiles"] = {
        name: {"sha256": sha256_file(state_dir / name), "bytes": (state_dir / name).stat().st_size}
        for name in ("entities.csv", "decisions.csv", "report.md")
    }
    write_json(state_dir / "state.yaml", document)
    print(json.dumps({
        "status": "packaged",
        "state": state,
        "releaseId": release_id,
        "repositoryFiles": 4,
        "artifacts": 3,
        "artifactBytes": sum(row["bytes"] for row in artifacts),
        "storageStatus": storage_status,
    }, indent=2))
    return 0


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    args = parse_args()
    state = args.state.upper()
    spec = STATE_FILES.get(state, {
        "legacy_dir": ROOT / "research" / f"{state.lower()}-expansion",
        "observations": ["observations.csv"],
        "entities": ["entities.csv"],
        "summary": ["summary.json"],
        "report": ["completion-report.md"],
    })
    work_dir = ROOT / "data" / "source-releases" / "work" / state
    default_source = work_dir if work_dir.is_dir() else spec["legacy_dir"]
    source_dir = (args.source_dir or default_source).resolve()
    state_dir = STATE_ROOT / state
    if (state_dir / "state.yaml").is_file():
        return package_v2(args, state, state_dir, source_dir)
    lookup_dirs = [source_dir, state_dir]
    config = json.loads((state_dir / "state-config.json").read_text(encoding="utf-8"))

    observations = find_across(lookup_dirs, spec["observations"])
    entities = find_across(lookup_dirs, spec["entities"])
    summary_path = find_across(lookup_dirs, spec["summary"])
    report = find_across(lookup_dirs, spec["report"])
    coverage = find_across(lookup_dirs, ["county-coverage.csv"])
    raw_path = find_across(lookup_dirs, ["raw-source-records.json"])
    request_path = find_across(lookup_dirs, ["request-log.json", "source-pass-log.json"])
    qa_path = find_across(lookup_dirs, ["qa-queue.csv"])
    identity_path = find_across(lookup_dirs, ["identity-review.csv"])
    exclusions_path = find_across(lookup_dirs, ["exclusions.csv", "excluded-observations.csv"])
    lookup_path = find_across(lookup_dirs, ["county-lookup-errors.json"], required=False)
    conflicts_path = find_across(lookup_dirs, ["geography-conflicts.csv"], required=False)
    manual_source = find_across(lookup_dirs, ["manual-decisions.csv", "manual-verification-decisions.csv"], required=False)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    release_id = str(summary["release_id"])
    if summary.get("status") != "coverage_reviewed":
        raise RuntimeError("only a coverage-reviewed state release may be packaged")

    copy_file(entities, state_dir / "entities.csv")
    copy_file(coverage, state_dir / "county-coverage.csv")
    copy_file(report, state_dir / "completion-report.md")
    if manual_source:
        copy_file(manual_source, state_dir / "manual-decisions.csv")
    elif not (state_dir / "manual-decisions.csv").exists():
        with (state_dir / "manual-decisions.csv").open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(MANUAL_HEADER)

    request_logs = json_list(request_path)
    sources = source_catalog(state, request_logs)
    if len(sources["datasets"]) != config["collection"]["expectedPrimaryDatasets"]:
        raise RuntimeError("source catalog count does not match state-config.json")
    write_json(state_dir / "sources.json", sources)

    bundle_dir = LOCAL_RELEASE_ROOT / state / release_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix=f"farmfinder-{state.lower()}-") as temporary:
        temp = Path(temporary)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        raw_rows = [{"dataset": key, "records": raw[key]} for key in sorted(raw)]
        raw_jsonl = temp / "raw-source-records.jsonl"
        raw_count = write_jsonl(raw_jsonl, raw_rows)

        request_jsonl = temp / "request-log.jsonl"
        request_count = write_jsonl(request_jsonl, request_logs)

        geography_rows: list[dict[str, Any]] = []
        if lookup_path:
            for row in json_list(lookup_path):
                geography_rows.append({"errorType": "county_lookup", **row})
        if conflicts_path:
            with conflicts_path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    geography_rows.append({"errorType": "source_county_conflict", **row})
        geography_jsonl = temp / "geography-errors.jsonl"
        geography_count = write_jsonl(geography_jsonl, geography_rows)

        artifact_inputs = [
            ("observations", observations, "observations.csv.zst", csv_count(observations)),
            ("raw_source_records", raw_jsonl, "raw-source-records.jsonl.zst", raw_count),
            ("request_log", request_jsonl, "request-log.jsonl.zst", request_count),
            ("qa_queue", qa_path, "qa-queue.csv.zst", csv_count(qa_path)),
            ("identity_review", identity_path, "identity-review.csv.zst", csv_count(identity_path)),
            ("exclusions", exclusions_path, "exclusions.csv.zst", csv_count(exclusions_path)),
            ("geography_errors", geography_jsonl, "geography-errors.jsonl.zst", geography_count),
        ]
        for role, source, filename, rows in artifact_inputs:
            destination = bundle_dir / filename
            compress_zstd(source, destination)
            artifacts.append({
                "role": role,
                "filename": filename,
                "objectKey": f"state-expansions/{state}/{release_id}/{filename}",
                "sha256": sha256_file(destination),
                "bytes": destination.stat().st_size,
                "rows": rows,
                "contentType": "application/zstd",
                "visibility": "private",
                "versionId": None,
            })

    storage_status = "local_bundle_only"
    if args.upload:
        ensure_bucket, runtime_settings, storage_client, upload = storage_helpers()
        settings = runtime_settings()
        client = storage_client(settings)
        bucket = settings.source_release_bucket or BUCKET
        ensure_bucket(client, bucket, settings.object_storage_region)
        for artifact in artifacts:
            artifact["versionId"] = upload(
                client,
                bucket=bucket,
                object_key=artifact["objectKey"],
                path=bundle_dir / artifact["filename"],
                sha256=artifact["sha256"],
                content_type=artifact["contentType"],
            )
        storage_status = "versioned_local_s3_staging"
    else:
        bucket = BUCKET

    repository_files = {}
    for name in config["repositoryPolicy"]["requiredFiles"]:
        if name == "release-manifest.json":
            continue
        path = state_dir / name
        repository_files[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}

    counts = {
        "sourceObservations": int(summary["source_observations"]),
        "proposedEntities": int(summary["proposed_entities"]),
        "promotionEligibleEntities": int(summary["promotion_eligible_entities"]),
        "researchOrQaEntities": int(summary["research_or_qa_entities"]),
        "excludedObservations": int(summary["excluded_or_grade_f_observations"]),
        "identityReviewGroups": int(summary["identity_review_groups"]),
        "countyCoverageRows": config["state"]["countyCount"],
        "countiesWithCandidates": int(summary["counties_with_candidates"]),
        "countiesWithEligibleEntities": int(summary["counties_with_promotion_eligible_entities"]),
        "sourceDatasets": len(sources["datasets"]),
        "manualDecisions": csv_count(state_dir / "manual-decisions.csv"),
    }
    manifest = {
        "contractVersion": 1,
        "state": state,
        "releaseId": release_id,
        "status": "coverage_reviewed",
        "generatedAt": summary.get("generated_at"),
        "promotionReady": False,
        "promotionBlockReason": "record-level QA and managed evidence storage remain incomplete",
        "counts": counts,
        "repositoryFiles": repository_files,
        "evidenceStorage": {
            "provider": "s3-compatible",
            "environment": "local-staging",
            "status": storage_status,
            "bucket": bucket,
            "prefix": f"state-expansions/{state}/{release_id}/",
            "versioningRequired": True,
            "managedCopyRequiredBeforePromotion": True,
        },
        "artifacts": artifacts,
        "canonicalBoundary": {
            "authorityMode": "pre_cutover_workbook",
            "allowedStates": ["LA", "MS"],
            "sourceRowCount": 311,
        },
    }
    write_json(state_dir / "release-manifest.json", manifest)
    print(json.dumps({
        "status": "packaged",
        "state": state,
        "releaseId": release_id,
        "repositoryFiles": len(config["repositoryPolicy"]["requiredFiles"]),
        "artifacts": len(artifacts),
        "artifactBytes": sum(row["bytes"] for row in artifacts),
        "storageStatus": storage_status,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
