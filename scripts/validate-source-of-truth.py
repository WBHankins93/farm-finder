from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:
    print(
        "Missing spreadsheet dependencies. Run `npm run data:setup` first.",
        file=sys.stderr,
    )
    raise SystemExit(2)


SITE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_ROOT / "config" / "source-of-truth.json"


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def is_missing(series: pd.Series) -> pd.Series:
    normalized = series.fillna("").astype(str).str.strip().str.casefold()
    return normalized.isin({"", "nan", "n/a", "unknown"})


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text())
    release = manifest["release"]
    workbook = (SITE_ROOT / release["workspacePath"]).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not workbook.is_file():
        errors.append(f"canonical workbook does not exist: {workbook}")
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1

    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    if digest != release["sha256"]:
        errors.append(
            f"checksum mismatch: manifest={release['sha256']} actual={digest}"
        )

    try:
        frame = pd.read_excel(workbook, sheet_name=release["sheet"], dtype=object)
    except ValueError as exc:
        errors.append(str(exc))
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1

    required_columns = set(manifest["requiredColumns"])
    actual_columns = set(frame.columns.astype(str))
    missing_columns = sorted(required_columns - actual_columns)
    unexpected_columns = sorted(actual_columns - required_columns)
    if missing_columns:
        errors.append(f"missing required columns: {missing_columns}")
    if unexpected_columns:
        warnings.append(f"unregistered columns: {unexpected_columns}")

    if len(frame) != release["sourceRowCount"]:
        errors.append(
            f"source row count mismatch: manifest={release['sourceRowCount']} "
            f"actual={len(frame)}"
        )

    for column in manifest["requiredNonEmptyColumns"]:
        if column not in frame:
            continue
        missing_count = int(is_missing(frame[column]).sum())
        if missing_count:
            errors.append(f"{column!r} has {missing_count} missing values")

    if "State" in frame:
        actual_states = set(frame["State"].fillna("").astype(str).str.strip())
        invalid_states = sorted(actual_states - set(release["allowedStates"]))
        if invalid_states:
            errors.append(f"states outside manifest allowlist: {invalid_states}")

    duplicate_groups: list[str] = []
    candidate_count = 0
    if "Farm Name" in frame:
        keys = frame["Farm Name"].map(normalized_name)
        candidate_count = int(keys.nunique())
        duplicate_groups = sorted(keys[keys.duplicated(keep=False)].unique().tolist())
        if candidate_count != release["candidateEntityCount"]:
            errors.append(
                "candidate entity count mismatch: "
                f"manifest={release['candidateEntityCount']} actual={candidate_count}"
            )

        expected_duplicates = sorted(manifest["identity"]["knownDuplicateGroups"])
        if duplicate_groups != expected_duplicates:
            errors.append(
                "duplicate groups changed: "
                f"manifest={expected_duplicates} actual={duplicate_groups}"
            )
        elif duplicate_groups:
            warnings.append(
                f"{len(duplicate_groups)} known duplicate groups require identity review"
            )

    report = {
        "status": "failed" if errors else "passed",
        "dataset": manifest["dataset"],
        "release": release["id"],
        "authorityMode": manifest["authorityMode"],
        "workbook": str(workbook),
        "sha256": digest,
        "sourceRows": len(frame),
        "candidateEntities": candidate_count,
        "duplicateGroups": duplicate_groups,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
