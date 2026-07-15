#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json

import psycopg

from cutover_common import (
    candidate_entity_count,
    duplicate_groups,
    load_manifest,
    runtime_settings,
    source_records,
    storage_client,
)


def main() -> int:
    manifest = load_manifest()
    release = manifest["release"]
    settings = runtime_settings()
    errors: list[str] = []

    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, status, source_uri, source_sha256, manifest
                  FROM dataset_releases
                 WHERE dataset_code = %s AND release_key = %s
                """,
                (manifest["dataset"], release["id"]),
            )
            release_row = cursor.fetchone()
            if not release_row:
                errors.append("dataset release is not registered")
                stored_object = None
                raw_rows = []
            else:
                release_id, release_status, source_uri, stored_sha, stored_manifest = (
                    release_row
                )
                if release_status != "validated":
                    errors.append(f"release status is {release_status!r}, expected 'validated'")
                if stored_sha != release["sha256"]:
                    errors.append("database release checksum differs from manifest")
                stored_object = stored_manifest.get("storedObject")
                if not stored_object or source_uri != stored_object.get("uri"):
                    errors.append("database source URI does not match stored object metadata")

                cursor.execute(
                    """
                    SELECT id, status, source_record_count
                      FROM import_batches
                     WHERE dataset_release_id = %s
                     ORDER BY created_at DESC
                     LIMIT 1
                    """,
                    (release_id,),
                )
                batch_row = cursor.fetchone()
                if not batch_row:
                    errors.append("release has no import batch")
                    raw_rows = []
                else:
                    batch_id, batch_status, recorded_count = batch_row
                    if batch_status != "succeeded":
                        errors.append(
                            f"import batch status is {batch_status!r}, expected 'succeeded'"
                        )
                    cursor.execute(
                        """
                        SELECT raw_data
                          FROM source_records
                         WHERE import_batch_id = %s
                         ORDER BY source_record_key
                        """,
                        (batch_id,),
                    )
                    raw_rows = [row[0] for row in cursor.fetchall()]
                    if recorded_count != len(raw_rows):
                        errors.append("batch count differs from stored source rows")
                    if len(raw_rows) != release["sourceRowCount"]:
                        errors.append("stored source-row count differs from manifest")

    observed_duplicates = duplicate_groups(source_records(raw_rows))
    observed_candidate_count = candidate_entity_count(source_records(raw_rows))
    expected_duplicates = sorted(manifest["identity"]["knownDuplicateGroups"])
    if observed_duplicates != expected_duplicates:
        errors.append("stored duplicate groups differ from manifest")
    if observed_candidate_count != release["candidateEntityCount"]:
        errors.append("stored candidate-entity count differs from manifest")

    if stored_object:
        client = storage_client(settings)
        response = client.get_object(
            Bucket=stored_object["bucket"],
            Key=stored_object["key"],
            VersionId=stored_object["versionId"],
        )
        digest = hashlib.sha256()
        for chunk in iter(lambda: response["Body"].read(1024 * 1024), b""):
            digest.update(chunk)
        response["Body"].close()
        if digest.hexdigest() != release["sha256"]:
            errors.append("stored object bytes differ from release checksum")

    report = {
        "status": "failed" if errors else "passed",
        "dataset": manifest["dataset"],
        "release": release["id"],
        "releaseState": release_row[1] if release_row else None,
        "sourceRows": len(raw_rows),
        "candidateEntities": observed_candidate_count,
        "duplicateGroups": observed_duplicates,
        "objectVersion": stored_object.get("versionId") if stored_object else None,
        "promotionReady": False,
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
