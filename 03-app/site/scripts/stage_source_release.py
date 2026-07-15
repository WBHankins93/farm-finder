#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from urllib.parse import quote

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from cutover_common import (
    SITE_ROOT,
    candidate_entity_count,
    duplicate_groups,
    ensure_versioned_bucket,
    load_manifest,
    runtime_settings,
    sha256_file,
    source_records,
    storage_client,
    upload_immutable_release,
    workbook_path,
)


def stage_database(
    *,
    settings,
    manifest: dict,
    records: list[dict],
    object_details: dict,
) -> dict:
    release = manifest["release"]
    release_identity = (
        manifest["dataset"],
        release["id"],
        object_details["uri"],
        release["sha256"],
        release["sourceRowCount"],
        release["candidateEntityCount"],
    )
    idempotency_key = (
        f"source-release:{manifest['dataset']}:{release['id']}:{release['sha256']}"
    )
    stored_manifest = dict(manifest)
    stored_manifest["storedObject"] = object_details

    with psycopg.connect(settings.database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, source_uri, source_sha256, source_row_count,
                           candidate_entity_count, status
                      FROM dataset_releases
                     WHERE dataset_code = %s AND release_key = %s
                    """,
                    release_identity[:2],
                )
                existing_release = cursor.fetchone()
                if existing_release:
                    existing_identity = (
                        existing_release[1],
                        existing_release[2],
                        existing_release[3],
                        existing_release[4],
                    )
                    if existing_identity != release_identity[2:]:
                        raise RuntimeError(
                            "database release key already exists with different immutable identity"
                        )
                    release_id = existing_release[0]
                else:
                    cursor.execute(
                        """
                        INSERT INTO dataset_releases (
                            dataset_code, release_key, source_uri, source_sha256,
                            source_row_count, candidate_entity_count, manifest
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (*release_identity, Jsonb(stored_manifest)),
                    )
                    release_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO data_sources (
                        code, name, source_type, terms_notes
                    )
                    VALUES (
                        'farmfinder-curated-workbook',
                        'FarmFinder governed workbook releases',
                        'curator',
                        'Composite release; row-level origin is retained in raw_data Source Tab.'
                    )
                    ON CONFLICT (code) DO UPDATE
                       SET updated_at = now()
                    RETURNING id
                    """
                )
                source_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO import_batches (
                        dataset_release_id, source_id, idempotency_key, metadata
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        release_id,
                        source_id,
                        idempotency_key,
                        Jsonb(
                            {
                                "sheet": release["sheet"],
                                "storedObject": object_details,
                                "duplicateGroups": duplicate_groups(records),
                            }
                        ),
                    ),
                )
                inserted_batch = cursor.fetchone()
                if inserted_batch:
                    batch_id = inserted_batch[0]
                    batch_status = "queued"
                else:
                    cursor.execute(
                        """
                        SELECT id, status, dataset_release_id, source_id
                          FROM import_batches
                         WHERE idempotency_key = %s
                        """,
                        (idempotency_key,),
                    )
                    batch_id, batch_status, batch_release_id, batch_source_id = (
                        cursor.fetchone()
                    )
                    if batch_release_id != release_id or batch_source_id != source_id:
                        raise RuntimeError("idempotency key belongs to a different import")

        if batch_status == "succeeded":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM source_records WHERE import_batch_id = %s",
                    (batch_id,),
                )
                stored_count = cursor.fetchone()[0]
            if stored_count != len(records):
                raise RuntimeError(
                    f"completed batch has {stored_count} rows; expected {len(records)}"
                )
            return {
                "releaseId": str(release_id),
                "importBatchId": str(batch_id),
                "sourceRows": stored_count,
                "idempotentReplay": True,
            }

        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE import_batches
                           SET status = 'running', started_at = now(),
                               completed_at = NULL, error_summary = NULL
                         WHERE id = %s
                        """,
                        (batch_id,),
                    )
                    cursor.executemany(
                        """
                        INSERT INTO source_records (
                            import_batch_id, source_id, source_record_key,
                            record_hash, raw_data
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (import_batch_id, source_record_key) DO NOTHING
                        """,
                        [
                            (
                                batch_id,
                                source_id,
                                row["source_record_key"],
                                row["record_hash"],
                                Jsonb(row["raw_data"]),
                            )
                            for row in records
                        ],
                    )
                    cursor.execute(
                        "SELECT count(*) FROM source_records WHERE import_batch_id = %s",
                        (batch_id,),
                    )
                    stored_count = cursor.fetchone()[0]
                    if stored_count != len(records):
                        raise RuntimeError(
                            f"staged {stored_count} rows; expected {len(records)}"
                        )
                    cursor.execute(
                        """
                        UPDATE import_batches
                           SET status = 'succeeded', completed_at = now(),
                               source_record_count = %s
                         WHERE id = %s
                        """,
                        (stored_count, batch_id),
                    )
                    cursor.execute(
                        """
                        UPDATE dataset_releases
                           SET status = 'validated', validated_at = now(), manifest = %s
                         WHERE id = %s AND status <> 'promoted'
                        """,
                        (Jsonb(stored_manifest), release_id),
                    )
        except Exception as exc:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE import_batches
                           SET status = 'failed', completed_at = now(),
                               error_summary = %s
                         WHERE id = %s
                        """,
                        (str(exc)[:2000], batch_id),
                    )
            raise

    return {
        "releaseId": str(release_id),
        "importBatchId": str(batch_id),
        "sourceRows": len(records),
        "idempotentReplay": False,
    }


def main() -> int:
    validation = subprocess.run(
        [sys.executable, str(SITE_ROOT / "scripts" / "validate-source-of-truth.py")],
        cwd=SITE_ROOT,
        check=False,
    )
    if validation.returncode:
        return validation.returncode

    manifest = load_manifest()
    release = manifest["release"]
    path = workbook_path(manifest)
    digest = sha256_file(path)
    if digest != release["sha256"]:
        raise RuntimeError("workbook changed after validation")

    frame = pd.read_excel(path, sheet_name=release["sheet"], dtype=object)
    records = source_records(frame.to_dict(orient="records"))
    if len(records) != release["sourceRowCount"]:
        raise RuntimeError("source row count changed after validation")
    if candidate_entity_count(records) != release["candidateEntityCount"]:
        raise RuntimeError("candidate entity count changed after validation")

    settings = runtime_settings()
    storage = release["storage"]
    bucket = settings.source_release_bucket or storage["bucket"]
    client = storage_client(settings)
    ensure_versioned_bucket(client, bucket, settings.object_storage_region)
    version_id = upload_immutable_release(
        client,
        bucket=bucket,
        object_key=storage["objectKey"],
        path=path,
        sha256=digest,
        content_type=storage["contentType"],
    )
    object_details = {
        "provider": "s3-compatible",
        "bucket": bucket,
        "key": storage["objectKey"],
        "versionId": version_id,
        "sha256": digest,
        "uri": (
            f"s3://{bucket}/{storage['objectKey']}"
            f"?versionId={quote(version_id, safe='')}"
        ),
    }

    database = stage_database(
        settings=settings,
        manifest=manifest,
        records=records,
        object_details=object_details,
    )
    duplicate_group_names = duplicate_groups(records)
    report = {
        "status": "staged",
        "authorityMode": manifest["authorityMode"],
        "promotionBlocked": True,
        "promotionBlockReason": (
            "known duplicate groups require identity review"
            if duplicate_group_names
            else "normalization, privacy, provenance, and promotion review remain incomplete"
        ),
        "dataset": manifest["dataset"],
        "release": release["id"],
        "sourceObject": object_details,
        "candidateEntities": release["candidateEntityCount"],
        "duplicateGroups": duplicate_group_names,
        **database,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
